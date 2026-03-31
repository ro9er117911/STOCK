from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from stock_research.baselines import bootstrap_baselines
from stock_research.cockpit_api import get_observation_workspace, handle_observation_command
from stock_research.dashboard import build_dashboard_bundle
from stock_research.digest import build_portfolio_digest
from stock_research.observation import (
    READY_FOR_CANDIDATE_THRESHOLD,
    include_events,
    load_observation_lake,
    open_observation,
    promote_observation,
    rebuild_observation_lake,
)
from stock_research.storage import read_json


class ObservationTests(unittest.TestCase):
    def test_price_exception_events_are_capped_without_structural_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            bootstrap_baselines(research_root=research_root, force=True)
            open_observation(
                research_root,
                ticker="NVDA",
                company_name="NVIDIA",
                intended_horizon="3-12 months",
                opened_from="peer",
                theme_ids=["ai-platforms"],
                why_now="MSFT 的 AI 訊號值得延伸看 NVDA，但先只記錄價格例外。",
            )
            lake = rebuild_observation_lake(research_root)
            observation_id = next(item["observation_id"] for item in lake["items"] if item["ticker"] == "NVDA")
            include_events(
                research_root,
                observation_id=observation_id,
                selected_events=[
                    {
                        "related_ticker": "MSFT",
                        "relation_type": "peer",
                        "event_family": "price_exception",
                        "occurred_at": "2026-03-30",
                        "title": "MSFT 量價異常",
                        "summary": "只有價格例外，尚未確認基本面。",
                        "signal_strength": "critical",
                        "source_url": "https://example.com/msft-price",
                        "is_primary_source": True,
                    },
                    {
                        "related_ticker": "MSFT",
                        "relation_type": "peer",
                        "event_family": "price_exception",
                        "occurred_at": "2026-03-31",
                        "title": "MSFT 第二次量價異常",
                        "summary": "再次出現價格例外，但仍無結構事件。",
                        "signal_strength": "critical",
                        "source_url": "https://example.com/msft-price-2",
                        "is_primary_source": True,
                    },
                ],
            )
            lake = rebuild_observation_lake(research_root)
            item = next(item for item in lake["items"] if item["ticker"] == "NVDA")
            self.assertLess(item["score"], READY_FOR_CANDIDATE_THRESHOLD)
            self.assertEqual(item["status"], "open")
            self.assertFalse(item["promotion_recommendation"]["eligible"])

    def test_promote_observation_creates_candidate_with_observation_origin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            bootstrap_baselines(research_root=research_root, force=True)
            open_observation(
                research_root,
                ticker="NVDA",
                company_name="NVIDIA",
                intended_horizon="3-12 months",
                opened_from="peer",
                theme_ids=["ai-platforms"],
                peer_refs=["MSFT", "GOOGL"],
                why_now="MSFT 與 GOOGL 的 AI capex read-through 開始指向 NVDA。",
            )
            lake = rebuild_observation_lake(research_root)
            observation_id = next(item["observation_id"] for item in lake["items"] if item["ticker"] == "NVDA")
            include_events(
                research_root,
                observation_id=observation_id,
                selected_events=[
                    {
                        "related_ticker": "MSFT",
                        "relation_type": "peer",
                        "event_family": "capital_allocation",
                        "occurred_at": "2026-03-30",
                        "title": "Microsoft 持續上修 AI 基建資本支出",
                        "summary": "上游 AI 需求可能延伸到 NVDA。",
                        "signal_strength": "high",
                        "source_url": "https://example.com/msft-capex",
                        "is_primary_source": True,
                    },
                    {
                        "related_ticker": "GOOGL",
                        "relation_type": "peer",
                        "event_family": "valuation_regime_shift",
                        "occurred_at": "2026-03-31",
                        "title": "Google 對 AI 基建回報要求更高",
                        "summary": "估值體系開始偏向真正的算力瓶頸受益者。",
                        "signal_strength": "medium",
                        "source_url": "https://example.com/googl-ai",
                        "is_primary_source": True,
                    },
                ],
            )
            lake = rebuild_observation_lake(research_root)
            item = next(item for item in lake["items"] if item["ticker"] == "NVDA")
            self.assertGreaterEqual(item["score"], READY_FOR_CANDIDATE_THRESHOLD)
            self.assertEqual(item["status"], "ready_for_candidate")

            promote_observation(research_root, observation_id=observation_id)

            state = read_json(research_root / "NVDA" / "state.json")
            self.assertEqual(state["candidate_origin"], "observation_lake")
            self.assertEqual(state["research_stage"], "candidate")
            queue = read_json(research_root / "system" / "candidates.json")
            self.assertTrue(any(row["ticker"] == "NVDA" for row in queue["items"]))

            portfolio = build_portfolio_digest(research_root)
            self.assertIn("NVDA", [row["ticker"] for row in portfolio["tickers"]])

    def test_dashboard_bundle_keeps_observation_data_private_to_local_site(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            public_site_root = Path(tmp) / "site"
            local_site_root = Path(tmp) / "dashboard-local"
            portfolio_path = Path(tmp) / "portfolio.private.json"
            bootstrap_baselines(research_root=research_root, force=True)
            open_observation(
                research_root,
                ticker="NVDA",
                company_name="NVIDIA",
                intended_horizon="3-12 months",
                opened_from="peer",
                theme_ids=["ai-platforms"],
                why_now="MSFT 事件延伸出新的算力觀察。",
            )

            summary = build_dashboard_bundle(
                research_root=research_root,
                public_site_root=public_site_root,
                local_site_root=local_site_root,
                portfolio_path=portfolio_path,
            )

            public_payload = read_json(public_site_root / "data" / "portfolio.json")
            local_payload = read_json(local_site_root / "data" / "portfolio.json")
            self.assertFalse(public_payload["observation_actions_enabled"])
            self.assertEqual(public_payload["observation_items"], [])
            self.assertFalse(summary["has_private_overlay"])
            self.assertTrue(local_payload["observation_actions_enabled"])
            self.assertEqual(local_payload["observation_items"][0]["ticker"], "NVDA")
            self.assertTrue((local_site_root / "index.html").exists())

    def test_cockpit_api_command_handlers_mutate_observation_state_and_rebuild_local_site(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research_root = Path(tmp) / "research"
            local_site_root = Path(tmp) / "dashboard-local"
            portfolio_path = Path(tmp) / "portfolio.private.json"
            bootstrap_baselines(research_root=research_root, force=True)

            workspace = get_observation_workspace(research_root)
            self.assertEqual(workspace["summary"]["total_count"], 0)

            opened = handle_observation_command(
                research_root=research_root,
                local_site_root=local_site_root,
                portfolio_path=portfolio_path,
                route="/api/observations/open",
                payload={
                    "ticker": "NVDA",
                    "company_name": "NVIDIA",
                    "intended_horizon": "3-12 months",
                    "opened_from": "peer",
                    "theme_ids": ["ai-platforms"],
                    "why_now": "MSFT 事件值得延伸觀察。",
                },
            )
            self.assertTrue(opened["ok"])
            workspace = opened["workspace"]
            self.assertEqual(workspace["summary"]["total_count"], 1)
            observation_id = workspace["items"][0]["observation_id"]

            included = handle_observation_command(
                research_root=research_root,
                local_site_root=local_site_root,
                portfolio_path=portfolio_path,
                route="/api/observations/include-events",
                payload={
                    "observation_id": observation_id,
                    "selected_events": [
                        {
                            "related_ticker": "MSFT",
                            "relation_type": "peer",
                            "event_family": "capital_allocation",
                            "occurred_at": "2026-03-31",
                            "title": "Microsoft 上修 AI 基建支出",
                            "summary": "可能外溢到 NVDA。",
                            "signal_strength": "high",
                            "source_url": "https://example.com/msft",
                            "is_primary_source": True,
                        },
                        {
                            "related_ticker": "GOOGL",
                            "relation_type": "peer",
                            "event_family": "valuation_regime_shift",
                            "occurred_at": "2026-03-31",
                            "title": "Google 對 AI 投資回報要求上升",
                            "summary": "更利於具瓶頸優勢的供應商。",
                            "signal_strength": "medium",
                            "source_url": "https://example.com/googl",
                            "is_primary_source": True,
                        },
                    ],
                },
            )
            self.assertTrue(included["ok"])

            promoted = handle_observation_command(
                research_root=research_root,
                local_site_root=local_site_root,
                portfolio_path=portfolio_path,
                route="/api/observations/promote",
                payload={"observation_id": observation_id},
            )
            self.assertTrue(promoted["ok"])
            self.assertTrue((research_root / "NVDA" / "state.json").exists())

            opened_hlt = handle_observation_command(
                research_root=research_root,
                local_site_root=local_site_root,
                portfolio_path=portfolio_path,
                route="/api/observations/open",
                payload={
                    "ticker": "HLT",
                    "company_name": "Hilton Worldwide",
                    "intended_horizon": "3-12 months",
                    "opened_from": "peer",
                    "theme_ids": ["asset-light-travel"],
                    "why_now": "MAR 的 travel mix 開始有 peer read-through。",
                },
            )
            hlt_id = next(item["observation_id"] for item in opened_hlt["workspace"]["items"] if item["ticker"] == "HLT")
            dismissed = handle_observation_command(
                research_root=research_root,
                local_site_root=local_site_root,
                portfolio_path=portfolio_path,
                route="/api/observations/dismiss",
                payload={"observation_id": hlt_id, "reason": "先聚焦其他候選。"},
            )
            self.assertTrue(dismissed["ok"])
            lake = load_observation_lake(research_root / "system" / "observation_lake.json")
            self.assertTrue(any(item["status"] == "dismissed" for item in lake["items"] if item["ticker"] == "HLT"))
            self.assertTrue((local_site_root / "data" / "portfolio.json").exists())


if __name__ == "__main__":
    unittest.main()
