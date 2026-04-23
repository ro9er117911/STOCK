"""Telegram notification for Light Track verdicts.

Usage:
    python3 -m src.stock_research.notify_telegram \
        --ticker 2330 \
        --verdict-file automation/run/quick-decision.json

Requires env vars:
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
import urllib.parse


def send_verdict(verdict: dict, bot_token: str, chat_id: str) -> bool:
    icons = {"BUY": "🟢", "WAIT": "🟡", "PASS": "🔴"}
    icon = icons.get(verdict.get("status", ""), "⚪")
    status = verdict.get("status", "UNKNOWN")
    ticker = verdict.get("ticker", "")
    rationale = verdict.get("rationale", [])
    confidence = verdict.get("confidence", 0) * 100
    thesis_link = verdict.get("thesis_link", "")
    alignment = verdict.get("thesis_alignment") or verdict.get("signals", {}).get("thesis_alignment", "")
    alignment_str = {"consistent": "✅ 一致", "contradicts": "⚠️ 矛盾", "neutral": "➖ 中性"}.get(alignment, "")
    disclaimer = verdict.get("disclaimer", "")

    lines = [
        f"{icon} *{status}* | {ticker}",
        "",
    ]
    for line in rationale:
        lines.append(f"• {line}")
    lines.append(f"\n信心：{confidence:.0f}%")
    if thesis_link:
        lines.append(f"ThesisLink：`{thesis_link}` {alignment_str}")
    if disclaimer:
        lines.append(f"\n_{disclaimer}_")

    text = "\n".join(lines)

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }).encode()

    try:
        with urllib.request.urlopen(url, data=data, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--verdict-file", required=True)
    args = parser.parse_args()

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        print("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set, skipping")
        return

    with open(args.verdict_file) as f:
        verdict = json.load(f)

    ok = send_verdict(verdict, bot_token, chat_id)
    print("Telegram sent OK" if ok else "Telegram send failed")


if __name__ == "__main__":
    main()
