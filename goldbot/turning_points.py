"""Turning-point dataset for XAU/USD 15m.

Three separate things, kept apart on purpose:
  1. PIVOTS (hindsight): ZigZag swing highs/lows. A pivot is only known after price has moved
     `rev_atr` ATRs away from it, so pivots are used for LABELS and the WHY study only, never as inputs.
  2. LABELS per candle (hindsight): "a real low (high) forms within [i-2, i+4] and this close is within
     1 ATR of it": buying (selling) here would be near the turn.
  3. FEATURES per candle (causal): only data known at the candle's close. tests/test_turning_points.py
     checks they don't change when later bars are deleted.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import quant_features as Q


def atr15(d: pd.DataFrame) -> pd.Series:
    pc = d["close"].shift()
    tr = pd.concat([d["high"] - d["low"], (d["high"] - pc).abs(), (d["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / 14, adjust=False).mean()


# ---------- 1. pivots (hindsight) --------------------------------------------------------------
def zigzag(d: pd.DataFrame, rev_atr: float = 3.0) -> pd.DataFrame:
    """Swing highs/lows: a new pivot is confirmed when price reverses rev_atr x ATR from the running extreme."""
    h, l, a = d["high"].values, d["low"].values, atr15(d).values
    piv, trend, hi_i, lo_i = [], 0, 0, 0
    for i in range(1, len(d)):
        if trend == 0:
            hi_i = i if h[i] > h[hi_i] else hi_i
            lo_i = i if l[i] < l[lo_i] else lo_i
            if hi_i < i and h[hi_i] - l[i] >= rev_atr * a[hi_i]:
                piv.append((hi_i, "high")); trend, lo_i = -1, i
            elif lo_i < i and h[i] - l[lo_i] >= rev_atr * a[lo_i]:
                piv.append((lo_i, "low")); trend, hi_i = 1, i
        elif trend == 1:  # rising: track the high until price falls rev_atr ATRs from it
            if h[i] >= h[hi_i]:
                hi_i = i
            elif h[hi_i] - l[i] >= rev_atr * a[hi_i]:
                piv.append((hi_i, "high")); trend, lo_i = -1, i
        else:  # falling: track the low until price rises rev_atr ATRs from it
            if l[i] <= l[lo_i]:
                lo_i = i
            elif h[i] - l[lo_i] >= rev_atr * a[lo_i]:
                piv.append((lo_i, "low")); trend, hi_i = 1, i
    p = pd.DataFrame(piv, columns=["i", "type"]).drop_duplicates("i")
    p["time"] = d.index[p["i"]]
    p["price"] = np.where(p["type"] == "high", h[p["i"]], l[p["i"]])
    p["atr"] = a[p["i"]]
    nxt = p["price"].shift(-1)
    p["swing_after_atr"] = (nxt - p["price"]).abs() / p["atr"]
    p["bars_to_next"] = p["i"].shift(-1) - p["i"]
    return p.set_index("time")


# ---------- 2. labels (hindsight) --------------------------------------------------------------
def labels(d: pd.DataFrame, piv: pd.DataFrame, before: int = 2, after: int = 4, near_atr: float = 1.0) -> pd.DataFrame:
    n = len(d)
    c, a = d["close"].values, atr15(d).values
    y = {"y_up": np.zeros(n, int), "y_dn": np.zeros(n, int)}
    for _, p in piv.iterrows():
        k = int(p["i"])
        for i in range(max(0, k - after), min(n, k + before + 1)):  # pivot within [i-before, i+after]
            if p["type"] == "low" and c[i] - p["price"] <= near_atr * a[i]:
                y["y_up"][i] = 1
            if p["type"] == "high" and p["price"] - c[i] <= near_atr * a[i]:
                y["y_dn"][i] = 1
    out = pd.DataFrame(y, index=d.index)
    out["y_turn"] = (out["y_up"] | out["y_dn"]).astype(int)
    return out


# ---------- 3. causal features -----------------------------------------------------------------
def rsi(c: pd.Series, n=14) -> pd.Series:
    x = c.diff()
    up = x.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-x.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def bar_features(d: pd.DataFrame) -> pd.DataFrame:
    o, h, l, c = (d[k] for k in ("open", "high", "low", "close"))
    a = atr15(d)
    f = pd.DataFrame(index=d.index)
    for k in (1, 4, 16, 96):
        f[f"r{k}"] = (c - c.shift(k)) / a
    for k in (16, 96, 480):
        f[f"dist_hi{k}"] = (h.rolling(k).max() - c) / a
        f[f"dist_lo{k}"] = (c - l.rolling(k).min()) / a
    f["rsi"] = rsi(c)
    m, sd = c.rolling(20).mean(), c.rolling(20).std()
    f["bb_pos"] = (c - m) / (2 * sd)
    rng = (h - l).replace(0, np.nan)
    f["body_frac"] = (c - o) / rng
    f["up_wick"] = (h - np.maximum(o, c)) / rng
    f["lo_wick"] = (np.minimum(o, c) - l) / rng
    f["prev_body_frac"] = f["body_frac"].shift()
    f["range_atr"] = (h - l) / a
    f["vol_regime"] = a / a.rolling(480).mean()
    f["hour"] = d.index.hour + d.index.minute / 60
    f["dow"] = d.index.dayofweek
    day = d.index.normalize()
    dd = d.resample("D").agg({"high": "max", "low": "min"}).dropna().shift(1)
    prev = dd.reindex(day).set_axis(d.index)
    hi_today, lo_today = h.groupby(day).cummax(), l.groupby(day).cummin()
    f["dist_prev_hi"] = (prev["high"] - c) / a
    f["dist_prev_lo"] = (c - prev["low"]) / a
    f["swept_prev_hi"] = (hi_today > prev["high"]).astype(int)
    f["swept_prev_lo"] = (lo_today < prev["low"]).astype(int)
    asia = d[(d.index.hour < 7)]
    ag = asia.groupby(asia.index.normalize()).agg(ah=("high", "max"), al=("low", "min"))
    ar = ag.reindex(day).set_axis(d.index)
    ar.loc[d.index.hour < 7] = np.nan  # the Asian range is only known once it has finished
    f["dist_asia_hi"] = (ar["ah"] - c) / a
    f["dist_asia_lo"] = (c - ar["al"]) / a
    f["swept_asia_hi"] = ((hi_today > ar["ah"]) & (d.index.hour >= 7)).astype(int)
    f["swept_asia_lo"] = ((lo_today < ar["al"]) & (d.index.hour >= 7)).astype(int)
    f = f.join(Q.intraday_series(d))
    t_close = pd.Series(d.index + pd.Timedelta(minutes=15))
    ext = pd.concat([Q._asof(Q.cot_features(), t_close), Q._asof(Q.macro_features(), t_close)], axis=1)
    ext.index = d.index
    return f.join(ext)


# ---------- WHY: conditions at each pivot ------------------------------------------------------
def why_table(d: pd.DataFrame, piv: pd.DataFrame, feats: pd.DataFrame) -> pd.DataFrame:
    """Conditions present at each pivot candle (descriptive: some are only visible at that candle)."""
    p = piv.copy()
    f = feats.reindex(p.index)
    hi = p["type"] == "high"
    a = p["atr"]
    w = pd.DataFrame(index=p.index)
    w["type"] = p["type"]
    w["session"] = pd.cut(p.index.hour, [-1, 6, 11, 16, 20, 24], labels=["asia", "london", "ny_overlap", "late_ny", "rollover"]).astype(str)
    mins = p.index.hour * 60 + p.index.minute
    w["news_window"] = np.isin(mins, [12 * 60 + 30, 12 * 60 + 45, 13 * 60 + 30, 13 * 60 + 45, 14 * 60, 18 * 60, 18 * 60 + 15, 19 * 60]).astype(int)
    w["shock_bar"] = (f["range_atr"] > 3).astype(int)
    w["swept_prev_day"] = np.where(hi, f["swept_prev_hi"], f["swept_prev_lo"])
    w["swept_asia"] = np.where(hi, f["swept_asia_hi"], f["swept_asia_lo"])
    w["near_round_25"] = (f["i_round_dist"] < 0.5).astype(int)
    w["near_round_100"] = ((((p["price"] / 100).round() * 100) - p["price"]).abs() < 0.5 * a).astype(int)
    w["rsi_extreme"] = np.where(hi, f["rsi"] > 70, f["rsi"] < 30).astype(int)
    w["stretched_bb"] = np.where(hi, f["bb_pos"] > 1, f["bb_pos"] < -1).astype(int)
    w["rejection_wick"] = np.where(hi, f["up_wick"] > 0.5, f["lo_wick"] > 0.5).astype(int)
    w["cot_crowded"] = np.where(hi, f["cot_mm_net_z"] > 1.5, f["cot_mm_net_z"] < -1.5).astype(int)
    w["swing_after_atr"] = p["swing_after_atr"]
    return w


def lift(why: pd.DataFrame, feats: pd.DataFrame, side: str) -> pd.DataFrame:
    """How much more often each condition appears at real turns than at ordinary candles."""
    hi = side == "high"
    f = feats
    base = pd.DataFrame(index=f.index)
    mins = f.index.hour * 60 + f.index.minute
    base["news_window"] = np.isin(mins, [750, 765, 810, 825, 840, 1080, 1095, 1140]).astype(int)
    base["shock_bar"] = (f["range_atr"] > 3).astype(int)
    base["swept_prev_day"] = f["swept_prev_hi"] if hi else f["swept_prev_lo"]
    base["swept_asia"] = f["swept_asia_hi"] if hi else f["swept_asia_lo"]
    base["near_round_25"] = (f["i_round_dist"] < 0.5).astype(int)
    base["rsi_extreme"] = (f["rsi"] > 70 if hi else f["rsi"] < 30).astype(int)
    base["stretched_bb"] = (f["bb_pos"] > 1 if hi else f["bb_pos"] < -1).astype(int)
    base["rejection_wick"] = (f["up_wick"] > 0.5 if hi else f["lo_wick"] > 0.5).astype(int)
    base["cot_crowded"] = (f["cot_mm_net_z"] > 1.5 if hi else f["cot_mm_net_z"] < -1.5).astype(int)
    w = why[why["type"] == side]
    rows = []
    for k in base.columns:
        at_turn, everywhere = w[k].mean(), base[k].mean()
        big = w[w[k] == 1]["swing_after_atr"].median() if w[k].sum() else np.nan
        rows.append({"condition": k, "at_turns": round(at_turn, 3), "all_candles": round(everywhere, 3),
                     "lift": round(at_turn / everywhere, 2) if everywhere > 0 else np.nan,
                     "median_swing_after_atr": round(big, 1) if pd.notna(big) else np.nan})
    return pd.DataFrame(rows).sort_values("lift", ascending=False)
