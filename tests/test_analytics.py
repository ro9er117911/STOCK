from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from stock_research.analytics import generate_post_mortem_report

class AnalyticsTests(unittest.TestCase):
    def test_analytics_calculates_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            msft_dir = root / "MSFT"
            msft_dir.mkdir(parents=True)
            state = {
                "outcome_markers": [
                    {"resolution": "validated", "actual_outcome": "earnings beat expectation gap"},
                    {"resolution": "invalidated", "actual_outcome": "regime drift to EV/EBITDA"},
                    {"resolution": "pending", "actual_outcome": ""},
                ],
                "thesis_change_log": [
                    {"reason": "major regime drift shift"},
                ]
            }
            (msft_dir / "state.json").write_text(json.dumps(state))

            sys_dir = root / "system"
            sys_dir.mkdir(parents=True)
            (sys_dir / "state.json").write_text(json.dumps({})) # Should be ignored

            report = generate_post_mortem_report(root)
            self.assertEqual(report["total_tickers_analyzed"], 1)
            self.assertEqual(report["assumptions_resolved"], 2)
            self.assertEqual(report["assumptions_correct"], 1)
            self.assertEqual(report["hit_rate_pct"], 50.0)
            self.assertEqual(report["regime_drift_events"], 2) # 1 from outcome, 1 from change log
            self.assertEqual(report["expectation_gap_events"], 1) # from outcome

if __name__ == "__main__":
    unittest.main()
