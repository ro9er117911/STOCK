from __future__ import annotations

import json
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
import urllib.request
import urllib.error
import yfinance as yf
import pandas as pd

from .config import (
    COCKPIT_API_HOST,
    COCKPIT_API_PORT,
    LOCAL_DASHBOARD_ROOT,
    PORTFOLIO_PRIVATE_PATH,
    RESEARCH_ROOT,
)
from .dashboard import build_local_dashboard_site
from .digest import build_portfolio_digest
from .observation import (
    build_observation_workspace,
    dismiss_observation,
    ensure_observation_system_files,
    include_events,
    open_observation,
    promote_observation,
)


def _workspace_payload(research_root: Path) -> dict[str, Any]:
    portfolio_payload = build_portfolio_digest(research_root)
    workspace = build_observation_workspace(research_root, cards=portfolio_payload["tickers"])
    return {
        "generated_at": portfolio_payload["generated_at"],
        "summary": workspace["summary"],
        "items": workspace["items"],
        "watchlist_recommendations": workspace["watchlist_recommendations"],
        "observation_actions_enabled": True,
    }


def _rebuild_local_cockpit(
    research_root: Path,
    *,
    local_site_root: Path,
    portfolio_path: Path,
) -> None:
    build_local_dashboard_site(
        research_root=research_root,
        local_site_root=local_site_root,
        portfolio_path=portfolio_path,
    )


def get_observation_workspace(research_root: Path = RESEARCH_ROOT) -> dict[str, Any]:
    ensure_observation_system_files(research_root)
    return _workspace_payload(research_root)


def handle_observation_command(
    *,
    research_root: Path = RESEARCH_ROOT,
    local_site_root: Path = LOCAL_DASHBOARD_ROOT,
    portfolio_path: Path = PORTFOLIO_PRIVATE_PATH,
    route: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = payload or {}
    ensure_observation_system_files(research_root)

    if route == "/api/observations/open":
        lake = open_observation(
            research_root,
            ticker=data["ticker"],
            company_name=data.get("company_name", data["ticker"]),
            intended_horizon=data.get("intended_horizon", ""),
            opened_from=data.get("opened_from", "manual"),
            theme_ids=data.get("theme_ids", []),
            peer_refs=data.get("peer_refs", []),
            chain_refs=data.get("chain_refs", []),
            why_now=data.get("why_now", ""),
            selected_events=data.get("selected_events", []),
            notes=data.get("notes", ""),
        )
    elif route == "/api/observations/include-events":
        lake = include_events(
            research_root,
            observation_id=data["observation_id"],
            selected_events=data.get("selected_events", []),
            notes=data.get("notes", ""),
        )
    elif route == "/api/observations/promote":
        lake = promote_observation(
            research_root,
            observation_id=data["observation_id"],
            stage=data.get("stage", "candidate"),
            note=data.get("note", ""),
        )
    elif route == "/api/observations/dismiss":
        lake = dismiss_observation(
            research_root,
            observation_id=data["observation_id"],
            reason=data.get("reason", ""),
        )
    else:
        raise ValueError(f"Unknown route: {route}")

    _rebuild_local_cockpit(
        research_root,
        local_site_root=local_site_root,
        portfolio_path=portfolio_path,
    )
    return {
        "ok": True,
        "lake": lake,
        "workspace": _workspace_payload(research_root),
    }


class CockpitAPIHandler(BaseHTTPRequestHandler):
    server_version = "ObservationCockpitAPI/1.0"

    def __init__(
        self,
        *args: Any,
        research_root: Path,
        local_site_root: Path,
        portfolio_path: Path,
        **kwargs: Any,
    ) -> None:
        self.research_root = research_root
        self.local_site_root = local_site_root
        self.portfolio_path = portfolio_path
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        _ = format, args

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw.strip() else {}

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_json(200, {"ok": True})

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        ensure_observation_system_files(self.research_root)
        if path == "/api/health":
            self._send_json(
                200,
                {
                    "ok": True,
                    "host": COCKPIT_API_HOST,
                    "port": COCKPIT_API_PORT,
                },
            )
            return
        if path == "/api/observations":
            self._send_json(200, _workspace_payload(self.research_root))
            return

        if path == "/api/history":
            query = parse_qs(urlparse(self.path).query)
            ticker = query.get("ticker", [""])[0]
            start = query.get("start", [""])[0]
            end = query.get("end", [""])[0]
            if not ticker or not start or not end:
                self._send_json(400, {"error": "Missing ticker, start, or end parameter"})
                return
            try:
                # Use yfinance to fetch data which handles cookies/crumbs automatically
                df = yf.download(ticker, start=start, end=end, progress=False)
                if df.empty:
                    self._send_json(404, {"error": f"No data found for {ticker}"})
                    return
                
                # If it's a multi-index (often happens with yfinance newer versions), flatten it
                if isinstance(df.columns, pd.MultiIndex):
                    # Take the first level of the columns (Price, Close, High, etc.)
                    # and ensure we are looking at the requested ticker
                    if ticker in df.columns.levels[1]:
                        df = df.xs(ticker, axis=1, level=1)
                    else:
                        df.columns = df.columns.get_level_values(0)

                # Standardize columns for the legacy DCA tool
                df.index.name = "Date"
                # Newer yfinance might use "Close" instead of "Adj Close" depending on version/args
                if "Close" in df.columns and "Adj Close" not in df.columns:
                    df["Adj Close"] = df["Close"]
                
                # Convert DataFrame to CSV string
                csv_body = df.to_csv().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(csv_body)
            except Exception as exc:
                self._send_json(500, {"error": f"YFinance error: {str(exc)}"})
            return

        if path == "/api/proxy":
            query = parse_qs(urlparse(self.path).query)
            target_url = query.get("url", [""])[0]
            if not target_url:
                self._send_json(400, {"error": "Missing url parameter"})
                return
            try:
                # Use a basic User-Agent to avoid being blocked by simple scrapers blockers
                headers = {"User-Agent": "Mozilla/5.0"}
                req = urllib.request.Request(target_url, headers=headers)
                with urllib.request.urlopen(req) as response:
                    body = response.read()
                    self.send_response(200)
                    self.send_header("Content-Type", response.getheader("Content-Type", "application/octet-stream"))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(body)
            except urllib.error.URLError as exc:
                self._send_json(500, {"error": f"Failed to proxy content: {str(exc)}"})
            except Exception as exc:
                self._send_json(500, {"error": f"Proxy error: {str(exc)}"})
            return

        self._send_json(404, {"error": f"Unknown route: {path}"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            payload = self._read_json_body()
            ensure_observation_system_files(self.research_root)
            if path == "/api/observations/open":
                lake = open_observation(
                    self.research_root,
                    ticker=payload["ticker"],
                    company_name=payload.get("company_name", payload["ticker"]),
                    intended_horizon=payload.get("intended_horizon", ""),
                    opened_from=payload.get("opened_from", "manual"),
                    theme_ids=payload.get("theme_ids", []),
                    peer_refs=payload.get("peer_refs", []),
                    chain_refs=payload.get("chain_refs", []),
                    why_now=payload.get("why_now", ""),
                    selected_events=payload.get("selected_events", []),
                    notes=payload.get("notes", ""),
                )
            elif path == "/api/observations/include-events":
                lake = include_events(
                    self.research_root,
                    observation_id=payload["observation_id"],
                    selected_events=payload.get("selected_events", []),
                    notes=payload.get("notes", ""),
                )
            elif path == "/api/observations/promote":
                lake = promote_observation(
                    self.research_root,
                    observation_id=payload["observation_id"],
                    stage=payload.get("stage", "candidate"),
                    note=payload.get("note", ""),
                )
            elif path == "/api/observations/dismiss":
                lake = dismiss_observation(
                    self.research_root,
                    observation_id=payload["observation_id"],
                    reason=payload.get("reason", ""),
                )
            else:
                self._send_json(404, {"error": f"Unknown route: {path}"})
                return
            _rebuild_local_cockpit(
                self.research_root,
                local_site_root=self.local_site_root,
                portfolio_path=self.portfolio_path,
            )
            self._send_json(
                200,
                {
                    "ok": True,
                    "lake": lake,
                    "workspace": _workspace_payload(self.research_root),
                },
            )
        except KeyError as exc:
            self._send_json(404, {"error": str(exc)})
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover - safety net
            self._send_json(500, {"error": str(exc)})


def serve_cockpit_api(
    *,
    research_root: Path = RESEARCH_ROOT,
    host: str = COCKPIT_API_HOST,
    port: int = COCKPIT_API_PORT,
    local_site_root: Path = LOCAL_DASHBOARD_ROOT,
    portfolio_path: Path = PORTFOLIO_PRIVATE_PATH,
) -> None:
    ensure_observation_system_files(research_root)
    _rebuild_local_cockpit(
        research_root,
        local_site_root=local_site_root,
        portfolio_path=portfolio_path,
    )
    handler = partial(
        CockpitAPIHandler,
        research_root=research_root,
        local_site_root=local_site_root,
        portfolio_path=portfolio_path,
    )
    with ThreadingHTTPServer((host, port), handler) as server:
        server.serve_forever()
