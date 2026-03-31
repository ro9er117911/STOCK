from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from stock_research.dashboard import build_dashboard_bundle, build_dashboard_site
from stock_research.candidates import upsert_candidate_dossier
from stock_research.digest import build_ticker_digest
from stock_research.notify import send_resend_email
from stock_research.pipeline import bootstrap_baselines, draft_refreshes, poll_events, sync_research_contracts
from stock_research.postprocess import post_process_refresh_output
from stock_research.sources import fetch_feed_events
from stock_research.storage import deep_merge, read_json, read_jsonl, write_jsonl
from stock_research.config import WATCHLIST


class PipelineTests(unittest.TestCase):
    def test_bootstrap_creates_baselines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            created = bootstrap_baselines(research_root=research_root, force=True)
            self.assertIn("MSFT", created)
            msft_state = read_json(research_root / "MSFT" / "state.json")
            self.assertEqual(msft_state["thesis"]["thesis_id"], "msft-thesis-core")
            self.assertEqual(msft_state["research_stage"], "active")
            self.assertEqual(msft_state["decision_status"], "active")
            self.assertIn("radar_summary", msft_state)
            self.assertIn("thesis_change_log", msft_state)
            self.assertTrue((research_root / "MAR" / "current.md").exists())
            self.assertTrue((research_root / "MAR" / "current.zh-tw.md").exists())
            self.assertTrue((research_root / "PLTR" / "events.jsonl").exists())
            self.assertTrue((research_root / "PLTR" / "artifacts" / "review_summary.zh-tw.md").exists())
            candidate_queue = read_json(research_root / "system" / "candidates.json")
            self.assertTrue(any(item["ticker"] == "MSFT" for item in candidate_queue["items"]))

    def test_upsert_candidate_tracks_stage_progression_and_rejection_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            bootstrap_baselines(research_root=research_root, force=True)
            created = upsert_candidate_dossier(
                research_root,
                ticker="NVDA",
                company_name="NVIDIA",
                research_topic="AI capex beneficiary with valuation discipline",
                candidate_origin="manual_watchlist",
                research_stage="candidate",
                radar_flags=["52-week breakout", "Abnormal volume"],
                radar_summary="Momentum is strong, but valuation already prices in a lot of AI upside.",
                radar_risk_level="medium",
                note="Initial candidate added from the manual watchlist.",
            )
            self.assertEqual(created["research_stage"], "candidate")
            state_path = research_root / "NVDA" / "state.json"
            created_state = read_json(state_path)
            self.assertEqual(created_state["decision_status"], "pending")
            self.assertEqual(created_state["radar_flags"], ["52-week breakout", "Abnormal volume"])

            upsert_candidate_dossier(
                research_root,
                ticker="NVDA",
                company_name="NVIDIA",
                research_topic="AI capex beneficiary with valuation discipline",
                candidate_origin="manual_watchlist",
                research_stage="in_research",
                note="Primary sources collected; move into active thesis work.",
            )
            ready = upsert_candidate_dossier(
                research_root,
                ticker="NVDA",
                company_name="NVIDIA",
                research_topic="AI capex beneficiary with valuation discipline",
                candidate_origin="manual_watchlist",
                research_stage="ready_to_decide",
                note="Decision packet is ready; waiting for explicit entry rule confirmation.",
                current_action="Defer entry until the next earnings print confirms margin durability.",
            )
            self.assertEqual(ready["research_stage"], "ready_to_decide")

            rejected = upsert_candidate_dossier(
                research_root,
                ticker="NVDA",
                company_name="NVIDIA",
                research_topic="AI capex beneficiary with valuation discipline",
                candidate_origin="manual_watchlist",
                research_stage="rejected",
                note="Reject after the reward/risk deteriorated versus alternatives.",
                current_action="Do not buy; keep only as a comparison anchor.",
                invalidation_reason="Expected upside no longer clears the required bar after valuation re-rate.",
            )
            self.assertEqual(rejected["research_stage"], "rejected")
            final_state = read_json(state_path)
            self.assertEqual(final_state["decision_status"], "rejected")
            self.assertEqual(
                final_state["invalidation_reason"],
                "Expected upside no longer clears the required bar after valuation re-rate.",
            )
            self.assertGreaterEqual(len(final_state["thesis_change_log"]), 4)
            queue = read_json(research_root / "system" / "candidates.json")
            queue_item = next(item for item in queue["items"] if item["ticker"] == "NVDA")
            self.assertEqual(queue_item["research_stage"], "rejected")
            self.assertEqual(queue_item["invalidation_reason"], final_state["invalidation_reason"])

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

    def test_poll_records_source_status_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            bootstrap_baselines(research_root=research_root, force=True)
            empty = ([], "")
            with mock.patch("stock_research.pipeline.fetch_sec_events", return_value=empty), \
                mock.patch("stock_research.pipeline.fetch_price_events", return_value=empty), \
                mock.patch("stock_research.pipeline.fetch_feed_events", return_value=empty):
                summary = poll_events(research_root=research_root, trigger="event")
            source_ids = {item["source_id"] for item in summary["tickers"]["MSFT"]["source_status"]}
            self.assertTrue({"sec", "price", "investor_news"}.issubset(source_ids))

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
            def sec_stub(source, config, state):  # noqa: ANN001
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

    def test_draft_refresh_normalizes_review_schedule_and_version_log(self) -> None:
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
            automation_root = Path(tmp) / "automation"
            bootstrap_baselines(research_root=research_root, force=True)
            msft_state_path = research_root / "MSFT" / "state.json"
            original_state = read_json(msft_state_path)
            mutated_state = json.loads(json.dumps(original_state))
            mutated_state["next_review_at"] = "2026-06-10"
            mutated_state["version_log"].append(
                {
                    "version": "v999",
                    "date": "2026-03-27",
                    "reason": "Model inserted duplicate version",
                    "impact": "Should not survive normalization.",
                }
            )
            with mock.patch("stock_research.pipeline.AUTOMATION_ROOT", automation_root), \
                mock.patch("stock_research.pipeline.CONTEXT_ROOT", automation_root / "context"), \
                mock.patch("stock_research.pipeline.RUN_SUMMARY_PATH", automation_root / "poll-summary.json"), \
                mock.patch("stock_research.pipeline.DRAFT_SUMMARY_PATH", automation_root / "draft-summary.json"), \
                mock.patch("stock_research.pipeline.PR_BODY_PATH", automation_root / "pr-body.md"), \
                mock.patch("stock_research.pipeline.PR_BODY_ZH_TW_PATH", automation_root / "pr-body.zh-tw.md"), \
                mock.patch("stock_research.pipeline.TRANSLATION_SUMMARY_PATH", automation_root / "translation-summary.json"), \
                mock.patch(
                    "stock_research.pipeline.generate_refresh",
                    return_value={
                        "updated_state": mutated_state,
                        "changed_assumptions": [],
                        "action_rule_delta": [],
                        "review_summary": "Model summary",
                    },
                ), \
                mock.patch("stock_research.pipeline.translate_markdown", side_effect=lambda markdown_text, *, context_label: markdown_text):
                poll_events(
                    research_root=research_root,
                    trigger="manual",
                    fixture_name="msft_only",
                    fixture_root=fixture_root,
                )
                draft_refreshes(
                    research_root=research_root,
                    trigger="manual",
                    fixture_name="msft_only",
                )
            saved_state = read_json(msft_state_path)
            self.assertEqual(
                saved_state["next_review_at"],
                (date.today() + timedelta(days=saved_state["thresholds"]["deep_refresh_days"])).isoformat(),
            )
            self.assertEqual([item["version"] for item in saved_state["version_log"]], ["v0", "v1"])

    def test_post_process_rewrites_same_status_confidence_gain(self) -> None:
        previous_state = {
            "ticker": "MSFT",
            "current_action": "持有 / 觀望",
            "assumptions": [
                {
                    "assumption_id": "msft-a2",
                    "status": "reinforced",
                    "confidence": 0.54,
                }
            ],
        }
        updated_state = {
            "ticker": "MSFT",
            "current_action": "持有 / 觀望",
            "assumptions": [
                {
                    "assumption_id": "msft-a2",
                    "status": "reinforced",
                    "confidence": 0.66,
                }
            ],
        }
        processed = post_process_refresh_output(
            previous_state,
            {
                "updated_state": updated_state,
                "changed_assumptions": [
                    {
                        "assumption_id": "msft-a2",
                        "summary": "reinforced -> reinforced because of stronger Copilot adoption",
                    }
                ],
                "action_rule_delta": [],
                "review_summary": "raw summary",
                "summary_points": [],
            },
            {
                "material_events": [
                    {
                        "title": "Microsoft says paid Copilot enterprise penetration moved above 12%.",
                        "affected_assumption_ids": ["msft-a2"],
                    }
                ],
                "new_events": [],
            },
        )
        summary = processed["changed_assumptions"][0]["summary"]
        self.assertIn("remains reinforced, but confidence rises", summary)
        self.assertNotIn("->", summary)

    def test_build_dashboard_site_writes_json_and_pages_ready_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            site_root = Path(tmp) / "site"
            bootstrap_baselines(research_root=research_root, force=True)
            summary = build_dashboard_site(research_root=research_root, site_root=site_root)
            self.assertTrue((site_root / "index.html").exists())
            self.assertTrue((site_root / "data" / "portfolio.json").exists())
            self.assertTrue((site_root / "tickers" / "MSFT.html").exists())
            self.assertTrue((site_root / "research" / "MSFT.html").exists())
            portfolio = read_json(site_root / "data" / "portfolio.json")
            self.assertIn("portfolio_summary", portfolio)
            self.assertEqual(len(portfolio["tickers"]), 3)
            self.assertIn("MSFT", summary["tickers"])

    def test_build_dashboard_bundle_keeps_private_positions_out_of_public_site(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            public_site_root = Path(tmp) / "site"
            local_site_root = Path(tmp) / "dashboard-local"
            portfolio_path = Path(tmp) / "portfolio.private.json"
            bootstrap_baselines(research_root=research_root, force=True)
            portfolio_path.write_text(
                json.dumps(
                    {
                        "positions": [
                            {
                                "ticker": "MSFT",
                                "shares": 12,
                                "avg_cost": 401.25,
                                "target_weight_pct": 18,
                                "max_weight_pct": 22,
                                "risk_level": "core",
                                "notes": "private",
                            }
                        ]
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            market_snapshot = {
                "generated_at": "2026-03-30T00:00:00+00:00",
                "quotes": {
                    "MSFT": {"symbol": "MSFT", "price": 370.0, "previous_close": 380.0, "change_pct": -2.63, "as_of": "2026-03-30"},
                    "PLTR": {"symbol": "PLTR", "price": 150.0, "previous_close": 151.0, "change_pct": -0.66, "as_of": "2026-03-30"},
                    "MAR": {"symbol": "MAR", "price": 330.0, "previous_close": 331.0, "change_pct": -0.3, "as_of": "2026-03-30"},
                },
                "vix": {"symbol": "^VIX", "value": 31.0, "previous_close": 29.0, "change_pct": 6.9, "as_of": "2026-03-30"},
            }
            with mock.patch("stock_research.digest.fetch_market_snapshot", return_value=market_snapshot), \
                mock.patch("stock_research.risk.fetch_market_snapshot", return_value=market_snapshot):
                summary = build_dashboard_bundle(
                    research_root=research_root,
                    public_site_root=public_site_root,
                    local_site_root=local_site_root,
                    portfolio_path=portfolio_path,
                )
            public_portfolio = read_json(public_site_root / "data" / "portfolio.json")
            local_portfolio = read_json(local_site_root / "data" / "portfolio.json")
            msft_public = next(item for item in public_portfolio["tickers"] if item["ticker"] == "MSFT")
            msft_local = next(item for item in local_portfolio["tickers"] if item["ticker"] == "MSFT")
            self.assertFalse(msft_public["position"]["has_position"])
            self.assertTrue(msft_local["position"]["has_position"])
            self.assertEqual(msft_local["position"]["shares"], 12)
            self.assertIsNone(msft_public["position"]["market_value"])
            self.assertEqual(msft_local["position"]["current_price"], 370.0)
            self.assertLess(msft_local["position"]["unrealized_pnl"], 0)
            self.assertTrue(local_portfolio["portfolio_totals"]["has_private_positions"])
            self.assertTrue(summary["has_private_overlay"])

    def test_digest_preserves_exception_event_metadata_for_dashboard_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            bootstrap_baselines(research_root=research_root, force=True)
            events_path = research_root / "MSFT" / "events.jsonl"
            baseline_events = read_jsonl(events_path)
            baseline_events.append(
                {
                    "event_id": "msft-exception-1",
                    "ticker": "MSFT",
                    "source_type": "price",
                    "occurred_at": "2026-04-01",
                    "title": "[EXCEPTION] Price move -6.2% with 2.9x volume",
                    "source_url": "https://finance.yahoo.com/quote/MSFT",
                    "affected_assumption_ids": [],
                    "marginal_impact": "-",
                    "threshold_breach": True,
                    "requires_refresh": True,
                    "decision": "refresh",
                    "metadata": {
                        "is_exception": True,
                        "exception_type": "籌碼崩解 (High-Volume Selloff)",
                        "severity": "critical",
                    },
                }
            )
            write_jsonl(events_path, baseline_events)
            digest = build_ticker_digest(research_root, "MSFT")
            self.assertTrue(digest["event_timeline"][0]["metadata"]["is_exception"])
            self.assertEqual(digest["key_events"][0]["metadata"]["severity"], "critical")

    def test_public_citations_replace_local_seed_path_with_internal_research_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            bootstrap_baselines(research_root=research_root, force=True)
            digest = build_ticker_digest(research_root, "MAR")
            citations = read_json(research_root / "MAR" / "artifacts" / "citations.json")
            self.assertTrue(any(item["kind"] == "internal" for item in citations))
            self.assertFalse(any("/Users/" in item["href"] for item in citations))
            self.assertTrue(any(item["href"] == "research/MAR.html#event-timeline" for item in citations))
            self.assertFalse(any("/Users/" in item["href"] for item in digest["citations"]))

    def test_send_email_writes_preview_without_resend_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "email-preview.html"
            text_path = Path(tmp) / "email-preview.txt"
            payload_path = Path(tmp) / "notification-payload.json"
            payload = {
                "run_type": "event",
                "material_tickers": ["MSFT"],
                "dashboard_url": "https://example.com/dashboard",
                "pr_url": "https://example.com/pr/1",
                "digest_cards": [
                    {
                        "ticker": "MSFT",
                        "status_label": "偏多",
                        "thesis_confidence": 0.72,
                        "summary_blurb": "Summary",
                        "current_action": "持有 / 偏多觀望",
                        "next_review_at": "2026-04-03",
                        "next_must_check_data": "FY2026 Q3 earnings",
                        "key_events": [],
                    }
                ],
            }
            with mock.patch("stock_research.notify.EMAIL_PREVIEW_HTML_PATH", html_path), \
                mock.patch("stock_research.notify.EMAIL_PREVIEW_TEXT_PATH", text_path), \
                mock.patch("stock_research.notify.NOTIFICATION_PAYLOAD_PATH", payload_path), \
                mock.patch.dict(os.environ, {}, clear=True):
                result = send_resend_email(payload)
            self.assertFalse(result["sent"])
            self.assertTrue(html_path.exists())
            self.assertTrue(text_path.exists())
            self.assertTrue(payload_path.exists())

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
            events, cursor = fetch_feed_events(WATCHLIST["MSFT"].sources[2], WATCHLIST["MSFT"], state)
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

    def test_sync_research_contracts_backfills_workflow_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            ticker_dir = research_root / "ABC"
            artifacts_dir = ticker_dir / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            legacy_state = {
                "ticker": "ABC",
                "company_name": "ABC Corp",
                "research_topic": "Legacy state migration test",
                "research_type": "事件驅動 / 中線",
                "holding_period": "數季",
                "last_reviewed_at": "2026-03-20",
                "next_review_at": "2026-04-01",
                "current_action": "持有 / 觀望",
                "confidence": 0.55,
                "latest_delta": ["Legacy state before vNext contract migration."],
                "primary_observation_variables": ["Demand"],
                "secondary_observation_variables": ["Margins"],
                "noise_filters": ["Noise"],
                "thresholds": {
                    "price_gap_pct": 10.0,
                    "volume_ratio": 2.0,
                    "deep_refresh_days": 7,
                    "material_sec_forms": ["8-K", "10-Q", "10-K"],
                    "earnings_keywords": ["earnings"],
                    "positive_keywords": ["beat"],
                    "negative_keywords": ["miss"],
                },
                "thesis": {
                    "thesis_id": "abc-thesis-core",
                    "statement": "Legacy thesis.",
                    "core_catalyst": "Catalyst",
                    "market_blind_spot": "Blind spot",
                    "verification_date": "2026-05-01",
                    "expiry_condition": "Expiry",
                },
                "assumptions": [],
                "risks": [],
                "valuation_regime": {
                    "current_yardstick": "P/E",
                    "better_yardstick": "EV/EBITDA",
                    "switch_trigger": "Trigger",
                    "re_rating_logic": "Logic",
                    "associated_risk": "Risk",
                },
                "scenarios": [],
                "action_rules": [],
                "next_must_check_data": "Earnings",
                "research_debt": [],
                "source_manifest": [],
                "last_seen_event_cursors": {},
                "version_log": [{"version": "v0", "date": "2026-03-20", "reason": "Legacy", "impact": "Legacy"}],
            }
            (ticker_dir / "state.json").write_text(json.dumps(legacy_state, ensure_ascii=False, indent=2), encoding="utf-8")
            (ticker_dir / "current.md").write_text("# Placeholder\n", encoding="utf-8")
            (ticker_dir / "events.jsonl").write_text("", encoding="utf-8")
            (artifacts_dir / "review_summary.json").write_text(
                json.dumps(
                    {
                        "ticker": "ABC",
                        "reviewed_at": "2026-03-20",
                        "review_summary": "Legacy summary.",
                        "changed_assumptions": [],
                        "action_rule_delta": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            summary = sync_research_contracts(research_root=research_root)
            self.assertEqual(summary["rewritten_tickers"], ["ABC"])
            migrated = read_json(ticker_dir / "state.json")
            self.assertEqual(migrated["research_stage"], "in_research")
            current_markdown = (ticker_dir / "current.md").read_text(encoding="utf-8")
            self.assertIn("## Research Workflow", current_markdown)
            self.assertIn("## Radar Summary", current_markdown)


if __name__ == "__main__":
    unittest.main()
