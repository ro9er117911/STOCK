from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .config import EMAIL_PREVIEW_HTML_PATH, EMAIL_PREVIEW_TEXT_PATH, NOTIFICATION_PAYLOAD_PATH
from .storage import write_json


def render_email_subject(payload: dict[str, Any]) -> str:
    tickers = ", ".join(payload["material_tickers"])
    return f"研究更新 | {tickers}"


def render_email_text(payload: dict[str, Any]) -> str:
    lines = [
        render_email_subject(payload),
        "",
        f"執行類型：{payload['run_type']}",
        f"Dashboard：{payload['dashboard_url']}",
        f"PR：{payload['pr_url']}",
        "",
    ]
    for card in payload["digest_cards"]:
        lines.extend(
            [
                f"{card['ticker']} | {card['status_label']}",
                card["summary_blurb"],
                f"目前操作: {card['current_action']}",
                f"下次檢查: {card['next_review_at']}",
                f"必查資料: {card['next_must_check_data']}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def render_email_html(payload: dict[str, Any]) -> str:
    card_html = []
    for card in payload["digest_cards"]:
        event_items = "".join(
            f"<li><strong>{event['occurred_at']}</strong> · {event['title']}</li>"
            for event in card["key_events"][:2]
        ) or "<li>本輪沒有新增關鍵事件。</li>"
        card_html.append(
            f"""
            <section style="padding:20px 0;border-top:1px solid #d7d0c4;">
              <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
                <div>
                  <h2 style="margin:0 0 6px;font-size:20px;color:#1d3b33;">{card['ticker']}</h2>
                  <p style="margin:0;color:#5b6c66;font-size:13px;">{card['status_label']} · 信心 {card['thesis_confidence']:.2f}</p>
                </div>
                <div style="font-size:12px;color:#6b635a;">下次檢查 {card['next_review_at']}</div>
              </div>
              <p style="margin:14px 0 12px;color:#1f2422;line-height:1.65;">{card['summary_blurb']}</p>
              <p style="margin:0 0 6px;color:#1d3b33;font-weight:600;">目前操作</p>
              <p style="margin:0 0 12px;color:#1f2422;">{card['current_action']}</p>
              <p style="margin:0 0 6px;color:#1d3b33;font-weight:600;">接下來要確認</p>
              <p style="margin:0 0 12px;color:#1f2422;">{card['next_must_check_data']}</p>
              <p style="margin:0 0 8px;color:#1d3b33;font-weight:600;">關鍵事件</p>
              <ul style="margin:0;padding-left:18px;color:#1f2422;line-height:1.6;">{event_items}</ul>
            </section>
            """
        )

    return f"""
    <html lang="zh-Hant">
      <body style="margin:0;background:#f6f1e8;font-family:'Iowan Old Style','Palatino Linotype','Noto Serif TC',serif;color:#1f2422;">
        <main style="max-width:760px;margin:0 auto;padding:40px 24px 56px;">
          <header style="padding-bottom:20px;border-bottom:2px solid #1d3b33;">
            <p style="margin:0 0 10px;font-size:12px;letter-spacing:0.14em;text-transform:uppercase;color:#7b6e5b;">Stock Research Operator</p>
            <h1 style="margin:0 0 12px;font-size:32px;color:#1d3b33;">研究更新摘要</h1>
            <p style="margin:0;color:#4f5e58;line-height:1.7;">這是一封只保留決策訊號的更新信：告訴你哪一檔變了、為什麼變、下一步要看什麼。</p>
          </header>
          {''.join(card_html)}
          <footer style="margin-top:28px;padding-top:20px;border-top:1px solid #d7d0c4;color:#4f5e58;font-size:13px;line-height:1.7;">
            <p style="margin:0 0 6px;">Dashboard：<a href="{payload['dashboard_url']}" style="color:#1d3b33;">{payload['dashboard_url']}</a></p>
            <p style="margin:0;">PR：<a href="{payload['pr_url']}" style="color:#1d3b33;">{payload['pr_url']}</a></p>
          </footer>
        </main>
      </body>
    </html>
    """.strip() + "\n"


def write_email_previews(payload: dict[str, Any]) -> None:
    EMAIL_PREVIEW_TEXT_PATH.write_text(render_email_text(payload), encoding="utf-8")
    EMAIL_PREVIEW_HTML_PATH.write_text(render_email_html(payload), encoding="utf-8")
    write_json(
        NOTIFICATION_PAYLOAD_PATH,
        payload,
    )


def send_resend_email(payload: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("RESEND_FROM_EMAIL")
    to_email = os.getenv("RESEND_TO_EMAIL")
    write_email_previews(payload)
    if not (api_key and from_email and to_email):
        return {"sent": False, "reason": "Missing RESEND_API_KEY / RESEND_FROM_EMAIL / RESEND_TO_EMAIL."}

    request_payload: dict[str, Any] = {
        "from": from_email,
        "to": [item.strip() for item in to_email.split(",") if item.strip()],
        "subject": render_email_subject(payload),
        "html": render_email_html(payload),
        "text": render_email_text(payload),
    }
    request = urllib.request.Request(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(request_payload).encode("utf-8"),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return {"sent": False, "reason": f"Resend request failed: {exc}"}
    return {"sent": True, "response": response_payload}
