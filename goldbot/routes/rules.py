"""Rule-based routes. Parameters are deliberately round, common values (not optimised) to keep the
out-of-sample test honest."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..features import asian_range, daily_trend
from .base import Route


class TrendBreakout(Route):
    name = "trend_breakout"
    family = "trend"
    thesis = ("Gold trends persistently (macro flows, central-bank buying). Buy 20-bar highs in an "
              "EMA50>EMA200 uptrend (mirror for shorts), ATR stop with a trailing exit.")
    params = {"lookback": 20, "sl_atr": 2.0, "trail_atr": 3.0, "max_bars": 120, "long_only": False}

    def signals(self, d):
        s = self.empty(d)
        hi = d["high"].rolling(self.p["lookback"]).max().shift()
        lo = d["low"].rolling(self.p["lookback"]).min().shift()
        up = d["ema50"] > d["ema200"]
        long_ = up & (d["close"] > hi)
        short = (~up) & (d["close"] < lo) & (not self.p["long_only"])
        s.loc[long_, "side"] = 1
        s.loc[short, "side"] = -1
        s["sl_dist"] = self.p["sl_atr"] * d["atr"]
        s["trail_atr"] = self.p["trail_atr"]
        s["max_bars"] = self.p["max_bars"]
        return s


class LondonBreakout(Route):
    name = "london_breakout"
    family = "session"
    thesis = ("Liquidity arrives at the London open; breaks of the quiet Asian range (00-07 UTC) "
              "tend to extend into the London/NY overlap. Exit flat before the NY close.")
    params = {"start_h": 7, "end_h": 11, "min_rng_atr": 1.0, "max_rng_atr": 6.0, "tp_x": 1.0,
              "exit_h": 20, "with_trend": True}

    def signals(self, d):
        s = self.empty(d)
        a = asian_range(d)
        rng = a["asia_hi"] - a["asia_lo"]
        h = d.index.hour
        window = (h >= self.p["start_h"]) & (h < self.p["end_h"])
        ok = (rng > self.p["min_rng_atr"] * d["atr"]) & (rng < self.p["max_rng_atr"] * d["atr"]) & (a["asia_n"] >= 6)
        bias = daily_trend(d) if self.p["with_trend"] else pd.Series(0, index=d.index)
        up = window & ok & (d["close"] > a["asia_hi"]) & (bias >= 0)
        dn = window & ok & (d["close"] < a["asia_lo"]) & (bias <= 0)
        # first break of the day only
        day = d.index.normalize()
        first = lambda m: m & (m.groupby(day).cumsum() == 1)
        up, dn = first(up), first(dn)
        s.loc[up, "side"] = 1
        s.loc[dn, "side"] = -1
        s["sl_dist"] = np.where(up, d["close"] - a["asia_lo"], a["asia_hi"] - d["close"]).clip(min=0.5)
        s["sl_dist"] = s["sl_dist"].clip(upper=3 * d["atr"])
        s["tp_dist"] = self.p["tp_x"] * rng
        s["force_exit"] = h == self.p["exit_h"]
        return s


class MeanReversion(Route):
    name = "mean_reversion"
    family = "reversion"
    thesis = ("In range regimes (low ADX) gold overshoots and snaps back to the 20-bar mean, "
              "especially in the Asian session when liquidity is thin.")
    params = {"adx_max": 20, "rsi_lo": 25, "rsi_hi": 75, "sl_atr": 1.5, "max_bars": 24}

    def signals(self, d):
        s = self.empty(d)
        calm = d["adx"] < self.p["adx_max"]
        long_ = calm & (d["close"] < d["bb_lo"]) & (d["rsi"] < self.p["rsi_lo"])
        short = calm & (d["close"] > d["bb_up"]) & (d["rsi"] > self.p["rsi_hi"])
        s.loc[long_, "side"] = 1
        s.loc[short, "side"] = -1
        s["sl_dist"] = self.p["sl_atr"] * d["atr"]
        s["tp_dist"] = (d["close"] - d["bb_mid"]).abs().clip(lower=0.5 * d["atr"])
        s["max_bars"] = self.p["max_bars"]
        return s


class MacroFiltered(Route):
    """Wraps another route and keeps only trades that agree with the macro regime:
    long gold when real yields are falling and/or the dollar is weakening; short in the opposite case."""
    family = "macro"
    thesis = ("Real yields and USD are gold's main medium-term drivers (Erb & Harvey 2013; WGC). "
              "Only take intraday signals that agree with the 20-day macro direction.")
    params = {"need": 1}

    def __init__(self, inner: Route, **kw):
        super().__init__(**kw)
        self.inner = inner
        self.name = f"{inner.name}+macro"

    def signals(self, d):
        s = self.inner.signals(d).copy()
        bull = (d["ry_chg20"] < 0).astype(int) + (d["dxy_chg20"] < 0).astype(int)
        bear = (d["ry_chg20"] > 0).astype(int) + (d["dxy_chg20"] > 0).astype(int)
        s.loc[(s["side"] > 0) & (bull < self.p["need"]), "side"] = 0
        s.loc[(s["side"] < 0) & (bear < self.p["need"]), "side"] = 0
        return s


def daily_atr(d: pd.DataFrame, n: int = 20) -> pd.Series:
    """ATR of completed daily bars, mapped back onto hourly bars (previous day's value)."""
    dd = d[["open", "high", "low", "close"]].resample("D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    pc = dd["close"].shift()
    tr = pd.concat([dd["high"] - dd["low"], (dd["high"] - pc).abs(), (dd["low"] - pc).abs()], axis=1).max(axis=1)
    a = tr.ewm(alpha=1 / n, adjust=False).mean().shift(1)
    return a.reindex(d.index.normalize()).set_axis(d.index).ffill()


class DailyTrend(Route):
    name = "daily_trend"
    family = "trend"
    thesis = ("Classic managed-futures trend following (Donchian/Turtle; Hurst, Ooi & Pedersen 2017 "
              "'A Century of Evidence on Trend-Following'). Gold is one of the best-trending markets. "
              "Enter on a close beyond the N-day channel in the direction of the 100-day mean; wide "
              "ATR stop and trailing stop, so trades last weeks.")
    params = {"days": 20, "trend_days": 100, "sl_datr": 2.5, "trail_datr": 3.0, "long_only": False,
              "check_hour": 19}

    def signals(self, d):
        s = self.empty(d)
        dc = d["close"].resample("D").last().dropna()
        dh = d["high"].resample("D").max().dropna()
        dl = d["low"].resample("D").min().dropna()
        hi = dh.rolling(self.p["days"]).max().shift(1)
        lo = dl.rolling(self.p["days"]).min().shift(1)
        sma = dc.rolling(self.p["trend_days"]).mean().shift(1)
        m = lambda x: x.reindex(d.index.normalize()).set_axis(d.index)
        hi, lo, sma = m(hi), m(lo), m(sma)
        datr = daily_atr(d)
        at = d.index.hour == self.p["check_hour"]  # evaluate once a day, 19:00 UTC, so the fill lands before the 21:00 rollover spread
        long_ = at & (d["close"] > hi) & (d["close"] > sma)
        short = at & (d["close"] < lo) & (d["close"] < sma) & (not self.p["long_only"])
        s.loc[long_, "side"] = 1
        s.loc[short, "side"] = -1
        s["sl_dist"] = self.p["sl_datr"] * datr
        # trailing stop is expressed in hourly ATR units by the backtester; convert
        s["trail_atr"] = self.p["trail_datr"] * datr / d["atr"]
        return s


class BuyTheDipUptrend(Route):
    name = "trend_pullback"
    family = "trend"
    thesis = ("In a structural bull market (2019-2026) the best risk/reward has come from buying "
              "pullbacks to the EMA50 while the daily trend is up.")
    params = {"sl_atr": 2.0, "tp_atr": 4.0, "max_bars": 72}

    def signals(self, d):
        s = self.empty(d)
        bias = daily_trend(d)
        touch = (d["low"] <= d["ema50"]) & (d["close"] > d["ema50"]) & (d["ema50"] > d["ema200"])
        rsi_ok = d["rsi"].between(35, 55)
        long_ = (bias > 0) & touch & rsi_ok
        s.loc[long_, "side"] = 1
        s["sl_dist"] = self.p["sl_atr"] * d["atr"]
        s["tp_dist"] = self.p["tp_atr"] * d["atr"]
        s["max_bars"] = self.p["max_bars"]
        return s
