from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any

from .config import DEFAULT_USER_AGENT, FeedConfig, TickerConfig
from .storage import sha1_digest


class SourceFailure(RuntimeError):
    pass


def _request(url: str, user_agent: str = DEFAULT_USER_AGENT, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except urllib.error.URLError as exc:
        raise SourceFailure(f"{url}: {exc}") from exc


def _strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value).strip()


def _normalize_date(value: str | None) -> str:
    if not value:
        return datetime.now(UTC).date().isoformat()
    try:
        parsed = parsedate_to_datetime(value)
        return parsed.astimezone(UTC).date().isoformat()
    except (TypeError, ValueError):
        pass
    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value.strip(), pattern).date().isoformat()
        except ValueError:
            continue
    match = re.search(r"(20\d{2})[-/](\d{2})[-/](\d{2})", value)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return datetime.now(UTC).date().isoformat()


def fetch_sec_events(config: TickerConfig, state: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    url = f"https://data.sec.gov/submissions/CIK{config.cik}.json"
    data = json.loads(_request(url).decode("utf-8"))
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accession_numbers = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    primary_documents = recent.get("primaryDocument", [])
    material_forms = set(state["thresholds"]["material_sec_forms"])
    previous_cursor = state["last_seen_event_cursors"].get("sec", "")
    events: list[dict[str, Any]] = []
    new_cursor = previous_cursor

    for form, accession, filing_date, primary in zip(
        forms, accession_numbers, filing_dates, primary_documents
    ):
        if not new_cursor:
            new_cursor = accession
        if accession == previous_cursor:
            break
        if form not in material_forms:
            continue
        accession_compact = accession.replace("-", "")
        filing_url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(config.cik)}/{accession_compact}/{primary}"
        )
        events.append(
            {
                "event_id": sha1_digest(config.ticker, "sec", accession, primary),
                "ticker": config.ticker,
                "source_type": "sec",
                "occurred_at": filing_date,
                "title": f"{form} filed: {primary}",
                "source_url": filing_url,
                "metadata": {"accession": accession, "form": form},
            }
        )
    return events, new_cursor


def fetch_price_events(config: TickerConfig, state: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{config.yahoo_symbol}"
        "?range=1mo&interval=1d&includePrePost=false&events=div%2Csplits"
    )
    data = json.loads(_request(url).decode("utf-8"))
    result = data["chart"]["result"][0]
    timestamps = result["timestamp"]
    quote = result["indicators"]["quote"][0]
    closes = quote["close"]
    volumes = quote["volume"]
    rows = [(ts, close, volume) for ts, close, volume in zip(timestamps, closes, volumes) if close is not None]
    if len(rows) < 2:
        return [], state["last_seen_event_cursors"].get("price", "")
    last_ts, last_close, last_volume = rows[-1]
    previous_close = rows[-2][1]
    historical_volumes = [item[2] for item in rows[-21:-1] if item[2] is not None]
    avg_volume = sum(historical_volumes) / max(len(historical_volumes), 1)
    volume_ratio = (last_volume / avg_volume) if avg_volume else 0.0
    change_pct = ((last_close - previous_close) / previous_close) * 100 if previous_close else 0.0
    occurred_at = datetime.fromtimestamp(last_ts, UTC).date().isoformat()
    previous_cursor = state["last_seen_event_cursors"].get("price", "")
    if previous_cursor == occurred_at:
        return [], occurred_at
    if abs(change_pct) < state["thresholds"]["price_gap_pct"] and volume_ratio < state["thresholds"]["volume_ratio"]:
        return [], occurred_at
    title = f"Price move {change_pct:+.2f}% with {volume_ratio:.2f}x volume"
    event = {
        "event_id": sha1_digest(config.ticker, "price", occurred_at, title),
        "ticker": config.ticker,
        "source_type": "price",
        "occurred_at": occurred_at,
        "title": title,
        "source_url": f"https://finance.yahoo.com/quote/{config.yahoo_symbol}",
        "metadata": {
            "change_pct": round(change_pct, 2),
            "volume_ratio": round(volume_ratio, 2),
            "close": round(last_close, 2),
        },
    }
    return [event], occurred_at


def _parse_rss_items(feed_bytes: bytes) -> list[dict[str, str]]:
    root = ET.fromstring(feed_bytes)
    items: list[dict[str, str]] = []
    for item in root.findall(".//item"):
        title = item.findtext("title") or ""
        link = item.findtext("link") or item.findtext("guid") or ""
        published = item.findtext("pubDate") or ""
        if title and link:
            items.append({"title": title.strip(), "link": link.strip(), "published": published.strip()})
    if items:
        return items
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", ns):
        title = entry.findtext("atom:title", default="", namespaces=ns)
        link_elem = entry.find("atom:link", ns)
        link = link_elem.get("href", "") if link_elem is not None else ""
        published = entry.findtext("atom:updated", default="", namespaces=ns)
        if title and link:
            items.append({"title": title.strip(), "link": link.strip(), "published": published.strip()})
    return items


def _extract_html_links(feed: FeedConfig, html_text: str) -> list[dict[str, str]]:
    anchor_pattern = re.compile(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL)
    results: list[dict[str, str]] = []
    seen_links: set[str] = set()
    for match in anchor_pattern.finditer(html_text):
        href, raw_title = match.groups()
        absolute_url = urllib.parse.urljoin(feed.url, unescape(href))
        title = _strip_tags(unescape(raw_title))
        if not title or absolute_url in seen_links:
            continue
        if feed.allow_patterns and not any(pattern in absolute_url for pattern in feed.allow_patterns):
            continue
        lowered = title.lower()
        if feed.title_keywords and not any(keyword in lowered for keyword in feed.title_keywords):
            continue
        context = html_text[max(match.start() - 120, 0) : match.end() + 120]
        date_match = re.search(
            r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, \d{4}|20\d{2}-\d{2}-\d{2})",
            context,
        )
        results.append(
            {
                "title": title,
                "link": absolute_url,
                "published": date_match.group(1) if date_match else "",
            }
        )
        seen_links.add(absolute_url)
        if len(results) >= 20:
            break
    return results


def fetch_feed_events(
    feed: FeedConfig,
    config: TickerConfig,
    state: dict[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    feed_bytes = _request(feed.url, timeout=25)
    if feed.kind == "rss":
        items = _parse_rss_items(feed_bytes)
    else:
        items = _extract_html_links(feed, feed_bytes.decode("utf-8", "ignore"))
    previous_cursor = state["last_seen_event_cursors"].get(feed.source_id, "")
    new_cursor = items[0]["link"] if items else previous_cursor
    events: list[dict[str, Any]] = []
    for item in items:
        if item["link"] == previous_cursor:
            break
        lowered = item["title"].lower()
        if feed.title_keywords and not any(keyword in lowered for keyword in feed.title_keywords):
            continue
        events.append(
            {
                "event_id": sha1_digest(config.ticker, feed.source_id, item["link"], item["title"]),
                "ticker": config.ticker,
                "source_type": feed.source_id,
                "occurred_at": _normalize_date(item.get("published")),
                "title": item["title"],
                "source_url": item["link"],
                "metadata": {"feed_url": feed.url},
            }
        )
    return events, new_cursor
