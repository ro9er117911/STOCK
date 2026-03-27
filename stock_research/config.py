from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_USER_AGENT = "ro9air-stock-research/1.0 ro9er117911@users.noreply.github.com"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini-2026-03-17"
BOT_NAME = "stock-research-bot"
BOT_EMAIL = "actions@users.noreply.github.com"

REPO_ROOT = Path(".")
RESEARCH_ROOT = REPO_ROOT / "research"
SYSTEM_ROOT = RESEARCH_ROOT / "system"
AUTOMATION_ROOT = REPO_ROOT / "automation" / "run"
CONTEXT_ROOT = AUTOMATION_ROOT / "context"
RUN_SUMMARY_PATH = AUTOMATION_ROOT / "poll-summary.json"
DRAFT_SUMMARY_PATH = AUTOMATION_ROOT / "draft-summary.json"
PR_BODY_PATH = AUTOMATION_ROOT / "pr-body.md"


@dataclass(frozen=True)
class FeedConfig:
    source_id: str
    kind: str
    url: str
    title_keywords: tuple[str, ...] = ()
    allow_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class TickerConfig:
    ticker: str
    company_name: str
    cik: str
    yahoo_symbol: str
    price_gap_pct: float
    abnormal_volume_ratio: float
    deep_refresh_days: int = 7
    feeds: tuple[FeedConfig, ...] = field(default_factory=tuple)


WATCHLIST = {
    "PLTR": TickerConfig(
        ticker="PLTR",
        company_name="Palantir Technologies",
        cik="0001321655",
        yahoo_symbol="PLTR",
        price_gap_pct=10.0,
        abnormal_volume_ratio=2.2,
        feeds=(
            FeedConfig(
                source_id="investor_news",
                kind="html",
                url="https://investors.palantir.com/news-events/news-releases/",
                title_keywords=("earnings", "results", "quarter", "contract", "ai"),
                allow_patterns=("news", "releases"),
            ),
        ),
    ),
    "MSFT": TickerConfig(
        ticker="MSFT",
        company_name="Microsoft",
        cik="0000789019",
        yahoo_symbol="MSFT",
        price_gap_pct=8.0,
        abnormal_volume_ratio=2.0,
        feeds=(
            FeedConfig(
                source_id="investor_news",
                kind="rss",
                url="https://news.microsoft.com/feed/",
                title_keywords=("earnings", "microsoft cloud", "copilot", "azure", "results"),
            ),
        ),
    ),
    "MAR": TickerConfig(
        ticker="MAR",
        company_name="Marriott International",
        cik="0001048286",
        yahoo_symbol="MAR",
        price_gap_pct=8.0,
        abnormal_volume_ratio=2.0,
        feeds=(
            FeedConfig(
                source_id="investor_news",
                kind="html",
                url="https://news.marriott.com/news/",
                title_keywords=("reports", "results", "announces", "guidance", "quarter"),
                allow_patterns=("news",),
            ),
        ),
    ),
}
