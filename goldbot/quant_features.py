"""Free quant features for each candidate setup. Each value only uses data published before the
signal candle closed.

Sources
- CFTC Commitments of Traders, COMEX gold (088691), disaggregated futures-only, via the CFTC open-data API
  (publicreporting.cftc.gov). Positions as of Tuesday, published Friday 15:30 ET, so treated as known
  from the following Saturday 00:00 UTC.
- Macro (FRED real yield, breakevens, fed funds; DXY, VIX from Yahoo), daily, lagged one day.
- Intraday structure from the 15m bars themselves (session moves, ranges, round numbers, event shocks).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .data import load_macro

ROOT = Path(__file__).resolve().parents[1]
COT_CSV = ROOT / "data" / "raw" / "cot_gold.csv"
COT_API = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"


# ---------- COT ---------------------------------------------------------------------------------
def fetch_cot(since: str = "2015-01-01") -> pd.DataFrame:
    r = requests.get(COT_API, timeout=60, params={
        "cftc_contract_market_code": "088691", "$limit": 5000, "$order": "report_date_as_yyyy_mm_dd",
        "$where": f"report_date_as_yyyy_mm_dd >= '{since}T00:00:00.000'",
        "$select": "report_date_as_yyyy_mm_dd,open_interest_all,m_money_positions_long_all,m_money_positions_short_all,"
                   "swap_positions_long_all,swap__positions_short_all,prod_merc_positions_long,prod_merc_positions_short"})
    r.raise_for_status()
    d = pd.DataFrame(r.json())
    d["report_date"] = pd.to_datetime(d.pop("report_date_as_yyyy_mm_dd")).dt.tz_localize("UTC")
    d = d.set_index("report_date").astype(float).sort_index()
    COT_CSV.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(COT_CSV)
    return d


def cot_features(refresh: bool = False) -> pd.DataFrame:
    d = fetch_cot() if refresh or not COT_CSV.exists() else pd.read_csv(COT_CSV, index_col=0, parse_dates=True)
    d.index = pd.to_datetime(d.index, utc=True)
    oi = d["open_interest_all"]
    f = pd.DataFrame(index=d.index)
    f["cot_mm_net"] = (d["m_money_positions_long_all"] - d["m_money_positions_short_all"]) / oi
    f["cot_mm_net_z"] = (f["cot_mm_net"] - f["cot_mm_net"].rolling(156, min_periods=52).mean()) / f["cot_mm_net"].rolling(156, min_periods=52).std()
    f["cot_mm_chg1w"] = f["cot_mm_net"].diff()
    f["cot_mm_chg4w"] = f["cot_mm_net"].diff(4)
    f["cot_swap_net"] = (d["swap_positions_long_all"] - d["swap__positions_short_all"]) / oi
    f["cot_oi_chg4w"] = oi.pct_change(4)
    # known from the Saturday after the Tuesday report date
    f.index = f.index + pd.Timedelta(days=4)
    return f


# ---------- macro -------------------------------------------------------------------------------
def macro_features() -> pd.DataFrame:
    m = load_macro().copy()
    f = pd.DataFrame(index=m.index)
    f["m_ry"] = m["DFII10"]
    f["m_ry_chg5"], f["m_ry_chg20"] = m["DFII10"].diff(5), m["DFII10"].diff(20)
    f["m_dxy_chg5"], f["m_dxy_chg20"] = m["dxy"].pct_change(5), m["dxy"].pct_change(20)
    f["m_be_chg20"] = m["T10YIE"].diff(20)
    f["m_vix"] = m["vix"]
    f["m_vix_z"] = (m["vix"] - m["vix"].rolling(250).mean()) / m["vix"].rolling(250).std()
    f.index = f.index + pd.Timedelta(days=1)  # a day's value is only known after that day
    return f


# ---------- intraday structure ------------------------------------------------------------------
def intraday_series(d15: pd.DataFrame) -> pd.DataFrame:
    """Per-15m-bar features (value at a bar uses that bar and earlier only)."""
    o, h, l, c = (d15[k] for k in ("open", "high", "low", "close"))
    pc = c.shift()
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
    day = d15.index.normalize()
    f = pd.DataFrame(index=d15.index)
    # daily context (completed days only)
    dd = d15.resample("D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    d_atr = (dd["high"] - dd["low"]).rolling(20).mean()
    prev = pd.DataFrame({"p_hi": dd["high"], "p_lo": dd["low"], "p_c": dd["close"], "d_atr": d_atr}).shift(1)
    prev = prev.reindex(day).set_axis(d15.index)
    f["i_day_atr_ratio"] = atr / prev["d_atr"]
    rng_today = h.groupby(day).cummax() - l.groupby(day).cummin()
    f["i_range_today"] = rng_today / prev["d_atr"]
    f["i_pos_prev_range"] = (c - prev["p_lo"]) / (prev["p_hi"] - prev["p_lo"]).replace(0, np.nan)
    f["i_ret_today"] = (c - prev["p_c"]) / prev["d_atr"]
    # move since the London open (07:00 UTC) of the same day
    lon = c.where(d15.index.hour == 7).groupby(day).transform("first")
    f["i_ret_since_london"] = ((c - lon) / atr).where(d15.index.hour >= 7)
    # realised volatility regime
    r = np.log(c).diff()
    f["i_rv_ratio"] = r.rolling(96).std() / r.rolling(96 * 20).std()
    # round numbers ($25 grid) and event shocks earlier the same day
    f["i_round_dist"] = ((c / 25).round() * 25 - c).abs() / atr
    med = (h - l).rolling(400, min_periods=50).median()
    shock = ((h - l) > 4 * med).astype(int)
    f["i_shock_today"] = shock.groupby(day).cummax()
    first_fri = (d15.index.dayofweek == 4) & (d15.index.day <= 7)
    f["i_nfp_day"] = first_fri.astype(int)
    f["i_us_data_window"] = ((d15.index.hour >= 12) & (d15.index.hour < 15)).astype(int)
    return f


def _asof(series_frame: pd.DataFrame, times: pd.Series) -> pd.DataFrame:
    s = series_frame.sort_index()
    s = s[~s.index.duplicated(keep="last")]
    idx = s.index.searchsorted(pd.DatetimeIndex(times), side="right") - 1
    out = s.iloc[np.clip(idx, 0, len(s) - 1)].reset_index(drop=True)
    out[idx < 0] = np.nan
    return out


def build(cands: pd.DataFrame, d15: pd.DataFrame, refresh_cot: bool = False) -> pd.DataFrame:
    """Quant features for each candidate (rows aligned with `cands`, which needs bar_time and side)."""
    t = pd.to_datetime(cands["bar_time"], utc=True).reset_index(drop=True)
    side = cands["side"].reset_index(drop=True).astype(float)
    close_t = t + pd.Timedelta(minutes=15)  # the signal candle's close
    parts = [_asof(cot_features(refresh_cot), close_t), _asof(macro_features(), close_t)]
    intr = intraday_series(d15).reindex(pd.DatetimeIndex(t)).reset_index(drop=True)
    parts.append(intr)
    f = pd.concat(parts, axis=1)
    # directional features expressed relative to the trade direction (+ = supports the trade)
    for k in ("cot_mm_chg1w", "cot_mm_chg4w", "i_ret_today", "i_ret_since_london"):
        f[k + "_dir"] = f[k] * side
    for k in ("m_ry_chg5", "m_ry_chg20", "m_dxy_chg5", "m_dxy_chg20"):
        f[k + "_dir"] = -f[k] * side  # falling real yields / dollar support longs
    f.index = cands.index
    return f
