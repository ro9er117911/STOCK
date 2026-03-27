from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from stock_research.pipeline import bootstrap_baselines, draft_refreshes, poll_events
from stock_research.sources import fetch_feed_events
from stock_research.storage import deep_merge, read_json, read_jsonl
from stock_research.config import WATCHLIST


class PipelineTests(unittest.TestCase):
    def test_bootstrap_creates_baselines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            created = bootstrap_baselines(research_root=research_root, force=True)
            self.assertIn("MSFT", created)
            msft_state = read_json(research_root / "MSFT" / "state.json")
            self.assertEqual(msft_state["thesis"]["thesis_id"], "msft-thesis-core")
            self.assertTrue((research_root / "MAR" / "current.md").exists())
            self.assertTrue((research_root / "MAR" / "current.zh-tw.md").exists())
            self.assertTrue((research_root / "PLTR" / "events.jsonl").exists())
            self.assertTrue((research_root / "PLTR" / "artifacts" / "review_summary.zh-tw.md").exists())

    def test_poll_dedupes_repeated_event_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            bootstrap_baselines(research_root=research_root, force=True)
            sec_event = (
                [
                    {
                        "event_id": "msft-sec-1",
                        "ticker": "MSFT",
                        "source_type": "sec",
                        "occurred_at": "2026-04-01",
                        "title": "10-Q filed: q3.htm",
                        "source_url": "https://example.com/q3",
                        "metadata": {"form": "10-Q"},
                    }
                ],
                "0001",
            )
            empty = ([], "")
            with mock.patch("stock_research.pipeline.fetch_sec_events", return_value=sec_event), \
                mock.patch("stock_research.pipeline.fetch_price_events", return_value=empty), \
                mock.patch("stock_research.pipeline.fetch_feed_events", return_value=empty):
                poll_events(research_root=research_root, trigger="event")
                poll_events(research_root=research_root, trigger="event")
            ledger = read_jsonl(research_root / "MSFT" / "events.jsonl")
            self.assertEqual(len([row for row in ledger if row["event_id"] == "msft-sec-1"]), 1)

    def test_noise_event_only_hits_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            bootstrap_baselines(research_root=research_root, force=True)
            noise_event = (
                [
                    {
                        "event_id": "mar-news-1",
                        "ticker": "MAR",
                        "source_type": "investor_news",
                        "occurred_at": "2026-04-02",
                        "title": "Marriott opens a new lobby concept page",
                        "source_url": "https://example.com/lobby",
                        "metadata": {},
                    }
                ],
                "https://example.com/lobby",
            )
            empty = ([], "")
            def feed_stub(feed, config, state):  # noqa: ANN001
                return noise_event if config.ticker == "MAR" else empty

            with mock.patch("stock_research.pipeline.fetch_sec_events", return_value=empty), \
                mock.patch("stock_research.pipeline.fetch_price_events", return_value=empty), \
                mock.patch("stock_research.pipeline.fetch_feed_events", side_effect=feed_stub):
                summary = poll_events(research_root=research_root, trigger="event")
            self.assertNotIn("MAR", summary["material_tickers"])
            ledger = read_jsonl(research_root / "MAR" / "events.jsonl")
            self.assertTrue(any(row["event_id"] == "mar-news-1" for row in ledger))

    def test_material_event_triggers_context_and_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            bootstrap_baselines(research_root=research_root, force=True)
            sec_event = (
                [
                    {
                        "event_id": "msft-sec-2",
                        "ticker": "MSFT",
                        "source_type": "sec",
                        "occurred_at": "2026-04-03",
                        "title": "10-Q filed: q3.htm",
                        "source_url": "https://example.com/q3",
                        "metadata": {"form": "10-Q"},
                    }
                ],
                "0002",
            )
            empty = ([], "")
            def sec_stub(config, state):  # noqa: ANN001
                return sec_event if config.ticker == "MSFT" else empty

            with mock.patch("stock_research.pipeline.fetch_sec_events", side_effect=sec_stub), \
                mock.patch("stock_research.pipeline.fetch_price_events", return_value=empty), \
                mock.patch("stock_research.pipeline.fetch_feed_events", return_value=empty):
                summary = poll_events(research_root=research_root, trigger="event")
                draft_summary = draft_refreshes(research_root=research_root, trigger="event")
            self.assertIn("MSFT", summary["material_tickers"])
            self.assertEqual(draft_summary["refreshed_tickers"][0]["ticker"], "MSFT")
            self.assertTrue((research_root / "MSFT" / "artifacts" / "review_summary.md").exists())

    def test_scheduled_refresh_uses_last_review_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            bootstrap_baselines(research_root=research_root, force=True)
            msft_state_path = research_root / "MSFT" / "state.json"
            msft_state = read_json(msft_state_path)
            msft_state["last_reviewed_at"] = "2026-03-01"
            msft_state["next_review_at"] = "2026-03-02"
            msft_state_path.write_text(__import__("json").dumps(msft_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            empty = ([], "")
            with mock.patch("stock_research.pipeline.fetch_sec_events", return_value=empty), \
                mock.patch("stock_research.pipeline.fetch_price_events", return_value=empty), \
                mock.patch("stock_research.pipeline.fetch_feed_events", return_value=empty):
                summary = poll_events(research_root=research_root, trigger="scheduled")
            self.assertIn("MSFT", summary["material_tickers"])

    def test_fixture_manual_refresh_targets_only_fixture_ticker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            fixture_root = Path(tmp) / "fixtures"
            fixture_root.mkdir(parents=True, exist_ok=True)
            (fixture_root / "msft_only.json").write_text(
                json.dumps(
                    {
                        "events": [
                            {
                                "ticker": "MSFT",
                                "source_type": "fixture",
                                "occurred_at": "2026-03-27",
                                "title": "Microsoft says Copilot enterprise penetration moved above 12%.",
                                "metadata": {
                                    "force_assumption_ids": ["msft-a2"],
                                    "force_marginal_impact": "+",
                                    "force_requires_refresh": True,
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            bootstrap_baselines(research_root=research_root, force=True)
            summary = poll_events(
                research_root=research_root,
                trigger="manual",
                fixture_name="msft_only",
                fixture_root=fixture_root,
            )
            self.assertEqual(summary["fixture_name"], "msft_only")
            self.assertEqual(summary["material_tickers"], ["MSFT"])
            self.assertEqual(summary["tickers"]["PLTR"]["new_events"], 0)
            self.assertFalse(summary["tickers"]["PLTR"]["scheduled_refresh_due"])
            ledger = read_jsonl(research_root / "MSFT" / "events.jsonl")
            self.assertTrue(any(row["source_type"] == "fixture" for row in ledger))

    def test_draft_refresh_generates_localized_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            fixture_root = Path(tmp) / "fixtures"
            fixture_root.mkdir(parents=True, exist_ok=True)
            (fixture_root / "msft_only.json").write_text(
                json.dumps(
                    {
                        "events": [
                            {
                                "ticker": "MSFT",
                                "source_type": "fixture",
                                "occurred_at": "2026-03-27",
                                "title": "Microsoft guides to slower CapEx growth while Azure AI demand stays above 30%.",
                                "metadata": {
                                    "force_assumption_ids": ["msft-a1", "msft-a3"],
                                    "force_marginal_impact": "+",
                                    "force_requires_refresh": True,
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            automation_root = Path(tmp) / "automation"
            bootstrap_baselines(research_root=research_root, force=True)
            with mock.patch("stock_research.pipeline.AUTOMATION_ROOT", automation_root), \
                mock.patch("stock_research.pipeline.CONTEXT_ROOT", automation_root / "context"), \
                mock.patch("stock_research.pipeline.RUN_SUMMARY_PATH", automation_root / "poll-summary.json"), \
                mock.patch("stock_research.pipeline.DRAFT_SUMMARY_PATH", automation_root / "draft-summary.json"), \
                mock.patch("stock_research.pipeline.PR_BODY_PATH", automation_root / "pr-body.md"), \
                mock.patch("stock_research.pipeline.PR_BODY_ZH_TW_PATH", automation_root / "pr-body.zh-tw.md"), \
                mock.patch("stock_research.pipeline.TRANSLATION_SUMMARY_PATH", automation_root / "translation-summary.json"), \
                mock.patch(
                    "stock_research.pipeline.translate_markdown",
                    side_effect=lambda markdown_text, *, context_label: f"[zh-tw:{context_label}]\n{markdown_text}",
                ):
                poll_events(
                    research_root=research_root,
                    trigger="manual",
                    fixture_name="msft_only",
                    fixture_root=fixture_root,
                )
                draft_summary = draft_refreshes(
                    research_root=research_root,
                    trigger="manual",
                    fixture_name="msft_only",
                )
            self.assertEqual(draft_summary["refreshed_tickers"][0]["ticker"], "MSFT")
            current_zh_tw = (research_root / "MSFT" / "current.zh-tw.md").read_text(encoding="utf-8")
            review_zh_tw = (research_root / "MSFT" / "artifacts" / "review_summary.zh-tw.md").read_text(encoding="utf-8")
            pr_body_zh_tw = (automation_root / "pr-body.zh-tw.md").read_text(encoding="utf-8")
            self.assertTrue(current_zh_tw.startswith("[zh-tw:MSFT current research note]"))
            self.assertTrue(review_zh_tw.startswith("[zh-tw:MSFT refresh review summary]"))
            self.assertTrue(pr_body_zh_tw.startswith("[zh-tw:pull request body]"))
            self.assertIn(
                str(research_root / "MSFT" / "current.zh-tw.md"),
                draft_summary["localization"]["translated_files"],
            )

    def test_rss_feed_respects_title_keywords(self) -> None:
        state = {
            "last_seen_event_cursors": {"investor_news": ""},
        }
        rss = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Generic culture story</title>
      <link>https://example.com/1</link>
      <pubDate>Wed, 01 Jan 2025 00:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Microsoft announces quarterly earnings release date</title>
      <link>https://example.com/2</link>
      <pubDate>Thu, 02 Jan 2025 00:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""
        with mock.patch("stock_research.sources._request", return_value=rss):
            events, cursor = fetch_feed_events(WATCHLIST["MSFT"].feeds[0], WATCHLIST["MSFT"], state)
        self.assertEqual(cursor, "https://example.com/1")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["source_url"], "https://example.com/2")

    def test_deep_merge_merges_list_items_by_stable_id(self) -> None:
        base = {
            "assumptions": [
                {"assumption_id": "a1", "statement": "Base thesis", "status": "watch"},
                {"assumption_id": "a2", "statement": "Second thesis", "status": "watch"},
            ]
        }
        overlay = {"assumptions": [{"assumption_id": "a1", "status": "reinforced"}]}
        merged = deep_merge(base, overlay)
        self.assertEqual(
            merged["assumptions"],
            [
                {"assumption_id": "a1", "statement": "Base thesis", "status": "reinforced"},
                {"assumption_id": "a2", "statement": "Second thesis", "status": "watch"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
