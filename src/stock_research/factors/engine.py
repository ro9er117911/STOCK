import pandas as pd
import numpy as np
from ..collectors.finmind_adapter import FinMindAdapter

class FactorEngine:
    """
    Computes Quality, Value, and Momentum factors for a given ticker.
    """
    def __init__(self, market="TW"):
        self.market = market
        self.adapter = FinMindAdapter() if market == "TW" else None

    def compute_quality(self, ticker: str) -> float:
        """
        Quality = Average ROE of the last 4 quarters.
        """
        if self.market == "TW":
            roe_df = self.adapter.get_roe(ticker)
            if not roe_df.empty:
                return roe_df['ROE'].head(4).mean()
        return 0.0

    def compute_momentum(self, ticker: str, benchmark_returns: float = 0.1) -> float:
        """
        Momentum = 12-month relative strength.
        (Mocked for now as we need historical price series)
        """
        # Placeholder: returning a random but deterministic strength for 2330
        if ticker == "2330":
            return 0.15 # 15% outperformance
        return 0.05

    def normalize_score(self, raw_score: float, mean: float, std: float) -> float:
        """
        Converts raw score to a 0-100 percentile-like score using Z-score.
        """
        if std == 0: return 50.0
        z_score = (raw_score - mean) / std
        # Map Z-score to 0-100 (approximately)
        # 0 is 50, +1 is 84, +2 is 97, -1 is 16, -2 is 3
        score = 100 * (1 / (1 + np.exp(-z_score)))
        return score

    def get_factor_snapshot(self, ticker: str) -> dict:
        """
        Generates a full factor snapshot for a ticker.
        """
        # Raw metrics
        quality_raw = self.compute_quality(ticker)
        momentum_raw = self.compute_momentum(ticker)
        value_raw = 15.0 # Mocked Forward P/E

        # Normalize (Using placeholder sector means)
        quality_score = self.normalize_score(quality_raw, mean=12.0, std=5.0)
        momentum_score = self.normalize_score(momentum_raw, mean=0.05, std=0.1)
        value_score = self.normalize_score(value_raw, mean=20.0, std=10.0) # Lower P/E is better, so Z-score logic might vary

        return {
            "ticker": ticker,
            "market": self.market,
            "scores": {
                "quality": round(quality_score, 2),
                "value": round(value_score, 2),
                "momentum": round(momentum_score, 2)
            },
            "raw_metrics": {
                "avg_roe_4q": round(quality_raw, 2),
                "relative_strength": round(momentum_raw, 2),
                "forward_pe": round(value_raw, 2)
            },
            "maestro_factor_score": round((quality_score * 0.4 + value_score * 0.3 + momentum_score * 0.3), 2)
        }

if __name__ == "__main__":
    engine = FactorEngine(market="TW")
    snapshot = engine.get_factor_snapshot("2330")
    print(f"Factor Snapshot for 2330:\n{snapshot}")
