from __future__ import annotations

import unittest
from unittest import mock

import pandas as pd

from stock_research.config import TickerConfig
from stock_research.radar import _compute_radar_metrics, _evaluate_radar_flags, scan_market

class RadarTests(unittest.TestCase):
    def test_compute_metrics_calculates_correctly(self) -> None:
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        hist = pd.DataFrame(
            {
                "Close": [100.0] * 19 + [110.0],
                "Volume": [1000] * 19 + [5000],
            },
            index=dates,
        )
        info = {
            "regularMarketPrice": 110.0,
            "fiftyTwoWeekHigh": 115.0,
        }
        
        metrics = _compute_radar_metrics("TEST", hist, info)
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics["current_price"], 110.0)
        self.assertEqual(metrics["high_52w"], 115.0)
        
        # dist_to_high_pct = (110 / 115 - 1) * 100 = -4.35
        self.assertAlmostEqual(metrics["dist_to_high_pct"], -4.35, places=2)
        
        # Volume: avg of 19*1000 + 5000 / 20 = 24000/20 = 1200
        # Ratio = 5000 / 1200 = 4.17
        self.assertAlmostEqual(metrics["volume_ratio"], 4.17, places=2)
        
        # MA10: avg of last 10 (9*100.0 + 110.0) / 10 = 1010/10 = 101.0
        # MA10_dev = (110.0 / 101.0 - 1) * 100 = 8.91
        self.assertAlmostEqual(metrics["ma_10_dev_pct"], 8.91, places=2)

    def test_evaluate_flags_detects_breakout_and_abnormal_volume(self) -> None:
        metrics = {
            "dist_to_high_pct": -4.35, # trigger > -5.0
            "volume_ratio": 4.17,      # trigger > 2.0
            "ma_10_dev_pct": 8.91,     # no trigger (< 10.0)
        }
        eval_result = _evaluate_radar_flags(metrics)
        self.assertIn("52-week breakout", eval_result["flags"])
        self.assertIn("Abnormal volume", eval_result["flags"])
        self.assertNotIn("Volume Climax / Overbought", eval_result["flags"])
        self.assertEqual(eval_result["risk_level"], "medium")

    @mock.patch("stock_research.radar.yf.download")
    @mock.patch("stock_research.radar.yf.Ticker")
    def test_scan_market_handles_empty_or_failed_downloads_gracefully(self, mock_ticker, mock_download) -> None:
        mock_download.return_value = pd.DataFrame()
        results = scan_market(["XYZ"])
        self.assertEqual(results, {})

if __name__ == "__main__":
    unittest.main()
