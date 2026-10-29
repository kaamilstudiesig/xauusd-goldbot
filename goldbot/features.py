"""Indicators and features for XAU/USD hourly bars (UTC)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["close"].shift()
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr(df, n)
    pdi = 100 * pd.Series(plus, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / a
    mdi = 100 * pd.Series(minus, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean()


def add_core(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    c = d["close"]
    d["atr"] = atr(d, 14)
    d["atr_d"] = atr(d, 24 * 5)  # ~1 week of hours, a slow volatility baseline
    d["ema20"] = c.ewm(span=20, adjust=False).mean()
    d["ema50"] = c.ewm(span=50, adjust=False).mean()
    d["ema200"] = c.ewm(span=200, adjust=False).mean()
    d["rsi"] = rsi(c, 14)
    d["adx"] = adx(d, 14)
    m = c.rolling(20).mean()
    sd = c.rolling(20).std()
    d["bb_mid"], d["bb_up"], d["bb_lo"] = m, m + 2.5 * sd, m - 2.5 * sd
    d["hour"] = d.index.hour
    d["dow"] = d.index.dayofweek
    d["vol_ratio"] = d["atr"] / d["atr_d"]
    d["range_med"] = (d["high"] - d["low"]).rolling(200, min_periods=20).median()
    return d


def add_macro(df: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    """Join daily macro data, lagged one day so only already-published values are used."""
    m = macro.copy()
    m["ry_chg20"] = m["DFII10"].diff(20)
    m["dxy_chg20"] = m["dxy"].pct_change(20)
    m["be_chg20"] = m["T10YIE"].diff(20)
    m["vix_z"] = (m["vix"] - m["vix"].rolling(250).mean()) / m["vix"].rolling(250).std()
    m = m.shift(1)  # publication lag
    day = df.index.normalize()
    cols = ["DFII10", "ry_chg20", "dxy_chg20", "be_chg20", "vix_z", "DFF"]
    m = m[~m.index.duplicated()]
    udays = day.unique()
    j = m[cols].reindex(m.index.union(udays)).ffill().reindex(day)
    j.index = df.index
    return df.join(j)


def daily_trend(df: pd.DataFrame) -> pd.Series:
    """+1 / -1 bias from the daily close vs its 50-day mean, using the previous completed day."""
    dc = df["close"].resample("D").last().dropna()
    bias = np.sign(dc - dc.rolling(50).mean()).shift(1)
    return bias.reindex(df.index.normalize()).set_axis(df.index).fillna(0)


def asian_range(df: pd.DataFrame, start: int = 0, end: int = 7) -> pd.DataFrame:
    """High/low of the Asian session (UTC hours [start, end)) for each day, known from `end` onwards."""
    asia = df[(df.index.hour >= start) & (df.index.hour < end)]
    g = asia.groupby(asia.index.normalize())
    rng = pd.DataFrame({"asia_hi": g["high"].max(), "asia_lo": g["low"].min(), "asia_n": g["high"].size()})
    out = rng.reindex(df.index.normalize())
    out.index = df.index
    out.loc[df.index.hour < end] = np.nan  # not known yet
    return out
