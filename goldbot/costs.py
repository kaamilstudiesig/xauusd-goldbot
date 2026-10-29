"""Gold trading cost model (prices in USD per ounce).

Rough raw-spread ECN conditions for XAU/USD (typical for IC Markets / Pepperstone raw accounts;
calibrate to your own broker in config):
- London / NY overlap: ~0.15-0.30
- Asia: ~0.30-0.50
- Daily rollover (21:00-22:59 UTC): 1.0+ and often gappy
- High-volatility bars (news): 3-5x normal
Commission: ~$7 per 100oz lot round trip = $0.07/oz.
Slippage: extra adverse fill on stop orders and market entries.
Swap: financing on positions held past the daily rollover.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class CostModel:
    spread_london_ny: float = 0.25
    spread_asia: float = 0.40
    spread_rollover: float = 1.20
    spread_late_ny: float = 0.35
    news_mult: float = 3.0          # applied when bar range > news_range_x * median range
    news_range_x: float = 3.0
    commission_rt: float = 0.07     # per oz, round trip
    slippage_entry: float = 0.05
    slippage_stop: float = 0.20
    swap_long_annual: float = 0.055  # financing charged on notional per night
    swap_short_annual: float = 0.010

    def spread_series(self, df: pd.DataFrame) -> np.ndarray:
        h = df.index.hour
        s = np.where((h >= 21) & (h <= 22), self.spread_rollover,
             np.where((h >= 23) | (h < 7), self.spread_asia,
             np.where(h >= 17, self.spread_late_ny, self.spread_london_ny)))
        rng = (df["high"] - df["low"]).values
        med = (df["high"] - df["low"]).rolling(200, min_periods=20).median().values
        news = rng > self.news_range_x * np.nan_to_num(med, nan=np.inf)
        return np.where(news, s * self.news_mult, s)


DEFAULT_COSTS = CostModel()
