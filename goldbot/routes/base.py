"""Route = one testable trading idea. Every route turns enriched bars into a signal frame
(see goldbot.backtest for the contract)."""
from __future__ import annotations

import numpy as np
import pandas as pd


class Route:
    name = "base"
    family = ""
    thesis = ""          # why this should work on gold, with sources in docs/routes.md
    params: dict = {}

    def __init__(self, **kw):
        self.p = {**self.params, **kw}

    def signals(self, d: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError

    @staticmethod
    def empty(d: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({"side": 0, "sl_dist": np.nan, "tp_dist": np.nan, "max_bars": np.nan,
                             "trail_atr": np.nan, "force_exit": False}, index=d.index)
