from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import RESEARCH_ROOT, SITE_DATA_ROOT, SITE_ROOT, SITE_TICKER_DATA_ROOT, SITE_TICKER_PAGE_ROOT, WATCHLIST
from .digest import build_ticker_digest, localize_digest_payload
from .storage import write_json


def _load_template(name: str) -> str:
    path = Path(__file__).parent / "templates" / "dashboard" / name
    if not path.exists():
        # Fallback for assets if they are in the assets subfolder
        asset_path = Path(__file__).parent / "templates" / "dashboard" / "assets" / name
        if asset_path.exists():
            return asset_path.read_text(encoding="utf-8")
        raise FileNotFoundError(f"Template not found: {path}")
    return path.read_text(encoding="utf-8")


def _portfolio_payload(localized_cards: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "tickers": [
            {
                "ticker": card["ticker"],
                "company_name": card["company_name"],
                "status_label": card["status_label"],
                "current_action": card["current_action"],
                "thesis_confidence": card["thesis_confidence"],
                "summary_blurb": card["summary_blurb"],
                "next_review_at": card["next_review_at"],
                "detail_href": f"./tickers/{card['ticker']}.html",
            }
            for card in localized_cards
        ],
    }


def build_dashboard_site(research_root: Path = RESEARCH_ROOT, site_root: Path = SITE_ROOT) -> dict[str, Any]:
    (site_root / "assets").mkdir(parents=True, exist_ok=True)
    SITE_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    SITE_TICKER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    SITE_TICKER_PAGE_ROOT.mkdir(parents=True, exist_ok=True)

    # Load templates
    portfolio_html_tpl = _load_template("index.html")
    ticker_html_tpl = _load_template("ticker.html")
    dashboard_css = _load_template("dashboard.css")
    dashboard_js = _load_template("dashboard.js")

    localized_cards: list[dict[str, Any]] = []
    for ticker in WATCHLIST:
        card = build_ticker_digest(research_root, ticker)
        localized_card = localize_digest_payload(card, context_label=f"{ticker} dashboard digest")
        localized_card["source_status"] = [
            {
                **source,
                "status_label": {
                    "active": "啟用",
                    "polled": "已輪詢",
                    "failed": "失敗",
                    "skipped": "略過",
                    "fixture_override": "fixture 模式略過",
                    "disabled": "停用",
                }.get(source.get("status", ""), source.get("status", "")),
            }
            for source in localized_card.get("source_status", [])
        ]
        localized_cards.append(localized_card)
        write_json(SITE_TICKER_DATA_ROOT / f"{ticker}.json", localized_card)
        (SITE_TICKER_PAGE_ROOT / f"{ticker}.html").write_text(ticker_html_tpl.format(ticker=ticker), encoding="utf-8")

    portfolio_payload = _portfolio_payload(localized_cards)
    write_json(SITE_DATA_ROOT / "portfolio.json", portfolio_payload)
    (site_root / "index.html").write_text(portfolio_html_tpl, encoding="utf-8")
    (site_root / ".nojekyll").write_text("", encoding="utf-8")
    (site_root / "assets" / "dashboard.css").write_text(dashboard_css, encoding="utf-8")
    (site_root / "assets" / "dashboard.js").write_text(dashboard_js, encoding="utf-8")
    return {
        "generated_at": portfolio_payload["generated_at"],
        "site_root": str(site_root),
        "tickers": [item["ticker"] for item in localized_cards],
    }
