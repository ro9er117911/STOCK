from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import LOCAL_DASHBOARD_ROOT, PORTFOLIO_PRIVATE_PATH, RESEARCH_ROOT, SITE_ROOT
from .digest import build_portfolio_digest, overlay_private_positions
from .storage import write_json


def _load_template(name: str) -> str:
    template_root = Path(__file__).parent / "templates" / "dashboard"
    path = template_root / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    asset_path = template_root / "assets" / name
    if asset_path.exists():
        return asset_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Template not found: {name}")


def _site_paths(site_root: Path) -> dict[str, Path]:
    return {
        "assets": site_root / "assets",
        "data": site_root / "data",
        "data_tickers": site_root / "data" / "tickers",
        "tickers": site_root / "tickers",
        "research": site_root / "research",
    }


def _write_site(site_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    paths = _site_paths(site_root)
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    portfolio_html_tpl = _load_template("index.html")
    ticker_html_tpl = _load_template("ticker.html")
    research_html_tpl = _load_template("research.html")
    dashboard_css = _load_template("dashboard.css")
    dashboard_js = _load_template("dashboard.js")

    write_json(paths["data"] / "portfolio.json", payload)
    for card in payload["tickers"]:
        write_json(paths["data_tickers"] / f"{card['ticker']}.json", card)
        (paths["tickers"] / f"{card['ticker']}.html").write_text(
            ticker_html_tpl.format(ticker=card["ticker"]),
            encoding="utf-8",
        )
        (paths["research"] / f"{card['ticker']}.html").write_text(
            research_html_tpl.format(ticker=card["ticker"]),
            encoding="utf-8",
        )

    (site_root / "index.html").write_text(portfolio_html_tpl, encoding="utf-8")
    (site_root / ".nojekyll").write_text("", encoding="utf-8")
    (paths["assets"] / "dashboard.css").write_text(dashboard_css, encoding="utf-8")
    (paths["assets"] / "dashboard.js").write_text(dashboard_js, encoding="utf-8")
    return {
        "generated_at": payload["generated_at"],
        "site_root": str(site_root),
        "tickers": [item["ticker"] for item in payload["tickers"]],
        "has_private_positions": any(item["position"]["has_position"] for item in payload["tickers"]),
    }


def build_dashboard_site(
    research_root: Path = RESEARCH_ROOT,
    site_root: Path = SITE_ROOT,
) -> dict[str, Any]:
    payload = build_portfolio_digest(research_root)
    return _write_site(site_root, payload)


def build_local_dashboard_site(
    research_root: Path = RESEARCH_ROOT,
    local_site_root: Path = LOCAL_DASHBOARD_ROOT,
    portfolio_path: Path = PORTFOLIO_PRIVATE_PATH,
) -> dict[str, Any]:
    public_payload = build_portfolio_digest(research_root)
    local_payload = overlay_private_positions(
        public_payload,
        research_root=research_root,
        portfolio_path=portfolio_path,
        risk_policy_path=research_root / "system" / "risk_policy.json",
    )
    return _write_site(local_site_root, local_payload)


def build_dashboard_bundle(
    research_root: Path = RESEARCH_ROOT,
    public_site_root: Path = SITE_ROOT,
    local_site_root: Path = LOCAL_DASHBOARD_ROOT,
    portfolio_path: Path = PORTFOLIO_PRIVATE_PATH,
) -> dict[str, Any]:
    public_payload = build_portfolio_digest(research_root)
    public_summary = _write_site(public_site_root, public_payload)

    local_summary = build_local_dashboard_site(
        research_root=research_root,
        local_site_root=local_site_root,
        portfolio_path=portfolio_path,
    )

    return {
        "generated_at": public_summary["generated_at"],
        "public_site_root": public_summary["site_root"],
        "public_tickers": public_summary["tickers"],
        "local_site_root": local_summary["site_root"],
        "local_tickers": local_summary["tickers"],
        "has_private_overlay": local_summary["has_private_positions"],
    }
