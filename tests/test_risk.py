from __future__ import annotations

import unittest

from stock_research.risk import (
    DEFAULT_RISK_POLICY,
    build_portfolio_totals,
    classify_vix_regime,
    evaluate_position_snapshot,
    finalize_position_weights,
)


class RiskTests(unittest.TestCase):
    def test_classify_vix_regime_boundaries(self) -> None:
        policy = DEFAULT_RISK_POLICY
        cases = [
            (19.99, "calm", 1.0),
            (20.0, "elevated", 0.9),
            (29.99, "elevated", 0.9),
            (30.0, "stress", 0.75),
            (39.99, "stress", 0.75),
            (40.0, "panic", 0.6),
        ]
        for value, expected_key, expected_multiplier in cases:
            with self.subTest(value=value):
                regime = classify_vix_regime(value, policy)
                self.assertEqual(regime["key"], expected_key)
                self.assertEqual(regime["size_multiplier"], expected_multiplier)

    def test_position_snapshot_triggers_review_de_risk_and_capital_preservation(self) -> None:
        base_position = {
            "ticker": "MSFT",
            "shares": 5.0,
            "avg_cost": 100.0,
            "target_weight_pct": 40.0,
            "max_weight_pct": 50.0,
            "risk_level": "core",
            "risk_level_label": "核心倉位",
            "summary": "5 股 @ $100.00",
            "shares_label": "5 股",
            "avg_cost_label": "$100.00",
            "target_weight_label": "40%",
            "max_weight_label": "50%",
            "notes": "",
        }
        calm = {"key": "calm", "label": "平穩", "size_multiplier": 1.0, "summary": "normal"}
        stress = {"key": "stress", "label": "壓力", "size_multiplier": 0.75, "summary": "stress"}

        review_position = evaluate_position_snapshot(
            base_position,
            quote={"price": 90.0, "as_of": "2026-03-30"},
            macro_regime=calm,
            thesis_health_score=0.72,
            key_events=[],
            policy=DEFAULT_RISK_POLICY,
        )
        self.assertTrue(any(alert["kind"] == "review" for alert in review_position["risk_alerts"]))

        de_risk_position = evaluate_position_snapshot(
            base_position,
            quote={"price": 84.0, "as_of": "2026-03-30"},
            macro_regime=stress,
            thesis_health_score=0.58,
            key_events=[],
            policy=DEFAULT_RISK_POLICY,
        )
        self.assertTrue(any(alert["kind"] == "de_risk" for alert in de_risk_position["risk_alerts"]))

        capital_preservation_position = evaluate_position_snapshot(
            base_position,
            quote={"price": 79.0, "as_of": "2026-03-30"},
            macro_regime=stress,
            thesis_health_score=0.52,
            key_events=[],
            policy=DEFAULT_RISK_POLICY,
        )
        self.assertTrue(any(alert["kind"] == "capital_preservation" for alert in capital_preservation_position["risk_alerts"]))

    def test_finalize_weights_and_portfolio_totals_reflect_actual_private_overlay(self) -> None:
        macro = {"key": "elevated", "label": "偏緊", "size_multiplier": 0.9, "summary": "tight"}
        policy = DEFAULT_RISK_POLICY
        positions = [
            evaluate_position_snapshot(
                {
                    "ticker": "MAR",
                    "shares": 10.0,
                    "avg_cost": 350.3,
                    "target_weight_pct": 30.0,
                    "max_weight_pct": 40.0,
                    "risk_level": "core",
                    "risk_level_label": "核心倉位",
                    "summary": "10 股 @ $350.30",
                    "shares_label": "10 股",
                    "avg_cost_label": "$350.30",
                    "target_weight_label": "30%",
                    "max_weight_label": "40%",
                    "notes": "",
                },
                quote={"price": 300.0, "as_of": "2026-03-30"},
                macro_regime=macro,
                thesis_health_score=0.7,
                key_events=[],
                policy=policy,
            ),
            evaluate_position_snapshot(
                {
                    "ticker": "MSFT",
                    "shares": 5.0,
                    "avg_cost": 536.98,
                    "target_weight_pct": 40.0,
                    "max_weight_pct": 50.0,
                    "risk_level": "core",
                    "risk_level_label": "核心倉位",
                    "summary": "5 股 @ $536.98",
                    "shares_label": "5 股",
                    "avg_cost_label": "$536.98",
                    "target_weight_label": "40%",
                    "max_weight_label": "50%",
                    "notes": "",
                },
                quote={"price": 470.0, "as_of": "2026-03-30"},
                macro_regime=macro,
                thesis_health_score=0.68,
                key_events=[],
                policy=policy,
            ),
            evaluate_position_snapshot(
                {
                    "ticker": "PLTR",
                    "shares": 6.0,
                    "avg_cost": 173.86,
                    "target_weight_pct": 30.0,
                    "max_weight_pct": 40.0,
                    "risk_level": "high-conviction",
                    "risk_level_label": "高信念倉位",
                    "summary": "6 股 @ $173.86",
                    "shares_label": "6 股",
                    "avg_cost_label": "$173.86",
                    "target_weight_label": "30%",
                    "max_weight_label": "40%",
                    "notes": "",
                },
                quote={"price": 140.0, "as_of": "2026-03-30"},
                macro_regime=macro,
                thesis_health_score=0.64,
                key_events=[],
                policy=policy,
            ),
        ]
        finalized = finalize_position_weights(positions)
        totals = build_portfolio_totals(finalized)
        self.assertEqual(totals["held_ticker_count"], 3)
        self.assertGreater(totals["cost_basis"], 7000)
        self.assertLess(totals["unrealized_pnl"], 0)
        self.assertTrue(any(position["portfolio_weight_pct"] is not None for position in finalized))


if __name__ == "__main__":
    unittest.main()
