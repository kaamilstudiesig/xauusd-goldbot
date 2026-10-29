"""All routes in one place. `status` is set from research results (see reports/research_summary.md)."""
from __future__ import annotations

from .ml import LGBMBarrier
from .rules import BuyTheDipUptrend, DailyTrend, LondonBreakout, MacroFiltered, MeanReversion, TrendBreakout
from .experimental import KronosForecast


def all_routes() -> dict:
    r = {
        "daily_trend": DailyTrend(),
        "daily_trend_long": DailyTrend(long_only=True),
        "trend_breakout": TrendBreakout(),
        "trend_pullback": BuyTheDipUptrend(),
        "london_breakout": LondonBreakout(),
        "mean_reversion": MeanReversion(),
        "ml_lgbm": LGBMBarrier(),
    }
    r["daily_trend+macro"] = MacroFiltered(DailyTrend())
    r["trend_breakout+macro"] = MacroFiltered(TrendBreakout())
    r["london_breakout+macro"] = MacroFiltered(LondonBreakout())
    r["mean_reversion+macro"] = MacroFiltered(MeanReversion())
    return r


EXPERIMENTAL = {"kronos": KronosForecast}
