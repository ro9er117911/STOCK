"""LINE Messaging API notification for Light Track verdicts.

Usage:
    python3 -m src.stock_research.notify_line \
        --verdict-file automation/run/quick-decision.json

Requires env var:
    LINE_CHANNEL_ACCESS_TOKEN or LINE_CHANNEL_ID + LINE_CHANNEL_SECRET
    LINE_MESSAGING_TARGET_ID, unless LINE_MESSAGING_BROADCAST=true
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request


LINE_TOKEN_URL = "https://api.line.me/oauth2/v3/token"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def format_verdict_flex_messages(verdict: dict) -> list[dict]:
    """Format a LightVerdict as a professional Flex Message."""
    status = verdict.get("status", "UNKNOWN")
    ticker = verdict.get("ticker", "")
    rationale = verdict.get("rationale", [])
    confidence = verdict.get("confidence", 0) * 100
    thesis_link = verdict.get("thesis_link", "")
    alignment = verdict.get("thesis_alignment") or verdict.get("signals", {}).get("thesis_alignment", "")
    alignment_str = {"consistent": "✅", "contradicts": "⚠️", "neutral": "➖"}.get(alignment, "")

    # 中文化 Status
    status_tw = {"BUY": "買進", "WAIT": "觀望", "PASS": "略過"}.get(status, status)
    
    # Icons / Colors logic
    icons = {"BUY": "🟢", "WAIT": "🟡", "PASS": "🔴"}
    icon = icons.get(status, "⚪")
    
    colors = {"BUY": "#00FF9D", "WAIT": "#FFB84D", "PASS": "#FF4444"}
    theme_color = colors.get(status, "#CCCCCC")

    rationale_text = "\n".join([f"• {line}" for line in rationale])
    
    # Optional Thesis Link section
    footer_contents = [
        {
            "type": "text",
            "text": f"▍ 系統信心水準：{confidence:.0f}%",
            "size": "xs",
            "color": "#999999",
            "weight": "bold",
            "flex": 1
        }
    ]
    
    if thesis_link:
        footer_contents.append({
            "type": "text",
            "text": f"{thesis_link} {alignment_str}",
            "size": "xs",
            "color": "#999999",
            "align": "end",
            "flex": 1
        })

    flex_bubble = {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#1A1A1A",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "text",
                    "text": "QUICK PULSE 交易訊號",
                    "color": theme_color,
                    "weight": "bold",
                    "size": "xs"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "20px",
            "contents": [
                {
                    "type": "text",
                    "text": f"{icon} {status_tw} ({status}) | {ticker}",
                    "weight": "bold",
                    "size": "xl",
                    "color": "#333333"
                },
                {
                    "type": "separator",
                    "margin": "lg",
                    "color": "#EEEEEE"
                },
                {
                    "type": "text",
                    "text": rationale_text,
                    "wrap": True,
                    "color": "#666666",
                    "size": "sm",
                    "margin": "lg"
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "contents": footer_contents
        }
    }

    return [
        {
            "type": "flex",
            "altText": f"QUICK PULSE | 最新交易訊號：{ticker} ({status})",
            "contents": flex_bubble
        }
    ]


def issue_stateless_channel_access_token(channel_id: str, channel_secret: str) -> str:
    """Issue a 15-minute channel access token from Channel ID/secret."""
    data = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": channel_id,
            "client_secret": channel_secret,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        LINE_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return str(payload["access_token"])


def send_messages(
    messages: list[dict],
    access_token: str,
    *,
    target_id: str = "",
    broadcast: bool = False,
) -> bool:
    """Send messages through the LINE Messaging API."""
    if not target_id and not broadcast:
        print("LINE_MESSAGING_TARGET_ID not set, skipping")
        return False

    payload = {
        "messages": messages
    }
    url = LINE_BROADCAST_URL if broadcast else LINE_PUSH_URL
    if not broadcast:
        payload["to"] = target_id

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"LINE Messaging API send failed: {e}")
        return False


def send_verdict(
    verdict: dict,
    access_token: str,
    *,
    target_id: str = "",
    broadcast: bool = False,
) -> bool:
    return send_messages(
        format_verdict_flex_messages(verdict),
        access_token,
        target_id=target_id,
        broadcast=broadcast,
    )


def resolve_access_token() -> str:
    access_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if access_token:
        return access_token

    channel_id = os.environ.get("LINE_CHANNEL_ID", "")
    channel_secret = os.environ.get("LINE_CHANNEL_SECRET", "")
    if channel_id and channel_secret:
        return issue_stateless_channel_access_token(channel_id, channel_secret)

    return ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verdict-file", required=True, help="Path to quick-decision.json")
    args = parser.parse_args()

    access_token = resolve_access_token()
    if not access_token:
        print("LINE_CHANNEL_ACCESS_TOKEN or LINE_CHANNEL_ID/LINE_CHANNEL_SECRET not set, skipping")
        return
    target_id = os.environ.get("LINE_MESSAGING_TARGET_ID") or os.environ.get("LINE_USER_ID", "")
    broadcast = _truthy(os.environ.get("LINE_MESSAGING_BROADCAST", ""))

    with open(args.verdict_file) as f:
        verdict = json.load(f)

    ok = send_verdict(verdict, access_token, target_id=target_id, broadcast=broadcast)
    print("LINE Messaging API sent OK" if ok else "LINE Messaging API send failed")


if __name__ == "__main__":
    main()
