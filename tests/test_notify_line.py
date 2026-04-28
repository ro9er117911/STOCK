from __future__ import annotations

import json
import urllib.parse

from stock_research import notify_line


class FakeResponse:
    def __init__(self, status: int = 200, body: bytes = b"{}") -> None:
        self.status = status
        self.body = body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_issue_stateless_channel_access_token_uses_channel_credentials(monkeypatch) -> None:
    calls = []

    def fake_urlopen(req, timeout: int = 10):
        calls.append((req, timeout))
        return FakeResponse(body=b'{"access_token":"issued-token","expires_in":900,"token_type":"Bearer"}')

    monkeypatch.setattr(notify_line.urllib.request, "urlopen", fake_urlopen)

    token = notify_line.issue_stateless_channel_access_token("123456", "secret")

    assert token == "issued-token"
    req, timeout = calls[0]
    assert timeout == 10
    assert req.full_url == "https://api.line.me/oauth2/v3/token"
    body = urllib.parse.parse_qs(req.data.decode("utf-8"))
    assert body == {
        "grant_type": ["client_credentials"],
        "client_id": ["123456"],
        "client_secret": ["secret"],
    }


def test_send_verdict_posts_push_message_to_target(monkeypatch) -> None:
    calls = []

    def fake_urlopen(req, timeout: int = 10):
        calls.append((req, timeout))
        return FakeResponse(status=200)

    monkeypatch.setattr(notify_line.urllib.request, "urlopen", fake_urlopen)

    ok = notify_line.send_verdict(
        {
            "status": "BUY",
            "ticker": "2330",
            "rationale": ["ADR premium is healthy"],
            "confidence": 0.66,
        },
        "line-token",
        target_id="U123",
    )

    assert ok is True
    req, _ = calls[0]
    assert req.full_url == "https://api.line.me/v2/bot/message/push"
    assert req.headers["Authorization"] == "Bearer line-token"
    payload = json.loads(req.data.decode("utf-8"))
    assert payload["to"] == "U123"
    assert payload["messages"][0]["type"] == "flex"
    assert "2330" in payload["messages"][0]["altText"]


def test_send_messages_refuses_missing_target_without_broadcast(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(notify_line.urllib.request, "urlopen", lambda *args, **kwargs: calls.append(args))

    ok = notify_line.send_messages([{"type": "text", "text": "hello"}], "line-token")

    assert ok is False
    assert calls == []


def test_send_messages_can_broadcast(monkeypatch) -> None:
    calls = []

    def fake_urlopen(req, timeout: int = 10):
        calls.append(req)
        return FakeResponse(status=200)

    monkeypatch.setattr(notify_line.urllib.request, "urlopen", fake_urlopen)

    ok = notify_line.send_messages([{"type": "text", "text": "hello"}], "line-token", broadcast=True)

    assert ok is True
    req = calls[0]
    assert req.full_url == "https://api.line.me/v2/bot/message/broadcast"
    assert "to" not in json.loads(req.data.decode("utf-8"))
