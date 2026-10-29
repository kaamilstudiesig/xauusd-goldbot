"""Data pipeline for XAU/USD.

Sources
- History (2004 -> Jul 2025): Hugging Face dataset ZombitX64/xauusd-gold-price-historical-data-2004-2025
  (MT-broker spot, server time = New York time + 7h).
- Recent / live: yfinance GC=F (COMEX gold futures), converted to a spot proxy by subtracting the
  futures-minus-spot basis. The basis comes from the overlap with spot history and from weekly
  spot closes (Twelve Data). Subtracting it also removes contract-roll jumps.
- Macro (daily): FRED real yield (DFII10), 10y breakeven (T10YIE); yfinance DXY and ^TNX.

All bar timestamps are UTC, labelled by bar open time.
"""
from __future__ import annotations

import io
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

OHLC = ["open", "high", "low", "close"]


# ---------- spot history ----------
def load_hf_spot(tf: str = "1h") -> pd.DataFrame:
    d = pd.read_json(RAW / f"XAU_{tf}_data.jsonl", lines=True)
    d.columns = [c.lower() for c in d.columns]
    ts = pd.to_datetime(d["date"], format="%Y.%m.%d %H:%M") - pd.Timedelta(hours=7)
    d.index = ts.dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("UTC")
    d = d[~d.index.isna()]
    d = d[OHLC + ["volume"]].sort_index()
    return d[~d.index.duplicated()]


# ---------- futures (recent + live) ----------
def fetch_futures(period: str = "730d", interval: str = "1h") -> pd.DataFrame:
    import yfinance as yf

    f = yf.download("GC=F", period=period, interval=interval, progress=False, auto_adjust=False)
    if isinstance(f.columns, pd.MultiIndex):
        f.columns = f.columns.get_level_values(0)
    f.columns = [c.lower() for c in f.columns]
    f.index = pd.to_datetime(f.index, utc=True)
    f = f[OHLC + ["volume"]].dropna()
    return f[~f.index.duplicated()].sort_index()


def basis_series(spot_h: pd.DataFrame, fut_h: pd.DataFrame) -> pd.Series:
    """Daily futures-minus-spot basis, using hourly overlap first and weekly spot closes after."""
    both = spot_h[["close"]].join(fut_h[["close"]], rsuffix="_f", how="inner")
    b_overlap = (both["close_f"] - both["close"]).resample("D").median().dropna()

    wk = pd.read_csv(RAW / "spot_weekly_twelvedata.csv", parse_dates=["date"])
    pts = {}
    fut_daily_last = fut_h["close"].resample("D").last().dropna()
    for _, r in wk.iterrows():
        day = pd.Timestamp(r["date"]).tz_localize("UTC")
        if day in fut_daily_last.index:
            pts[day] = fut_daily_last.loc[day] - r["close"]
    b_week = pd.Series(pts)
    b = pd.concat([b_overlap, b_week[b_week.index > b_overlap.index.max()]]).sort_index()
    # drop bad points (mismatched timestamps) far from the local median
    med = b.rolling(7, center=True, min_periods=1).median()
    return b[(b - med).abs() < 25]


def futures_to_spot(fut_h: pd.DataFrame, basis_daily: pd.Series) -> pd.DataFrame:
    """Subtract the daily basis (interpolated between anchor points) from futures bars."""
    out = fut_h.copy()
    days = pd.date_range(basis_daily.index.min(), fut_h.index.max().normalize(), freq="D", tz="UTC")
    b = basis_daily.reindex(days.union(basis_daily.index)).interpolate("time").ffill().bfill()
    b_h = b.reindex(fut_h.index.normalize()).values
    out[OHLC] = out[OHLC].sub(b_h, axis=0)
    return out


def build_hourly(refresh: bool = True) -> pd.DataFrame:
    spot = load_hf_spot("1h")
    fut = fetch_futures()
    b = basis_series(spot, fut)
    proxy = futures_to_spot(fut, b)
    cut = spot.index.max()
    recent = proxy[proxy.index > cut]
    h = pd.concat([spot, recent]).sort_index()
    h["src"] = np.where(h.index <= cut, "spot_hf", "gcf_proxy")
    h = h[~h.index.duplicated(keep="first")]
    h.to_parquet(PROC / "xauusd_1h.parquet")
    b.to_frame("basis").to_parquet(PROC / "basis_daily.parquet")
    return h


# ---------- macro ----------
def fred(series: str) -> pd.Series:
    r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}", timeout=30)
    s = pd.read_csv(io.StringIO(r.text))
    s.columns = ["date", series]
    s["date"] = pd.to_datetime(s["date"])
    s[series] = pd.to_numeric(s[series], errors="coerce")
    return s.set_index("date")[series].dropna()


def build_macro() -> pd.DataFrame:
    import yfinance as yf

    m = pd.concat([fred("DFII10"), fred("T10YIE"), fred("DFF")], axis=1)
    for tkr, name in [("DX-Y.NYB", "dxy"), ("^TNX", "tnx"), ("^VIX", "vix")]:
        y = yf.download(tkr, start="2004-01-01", interval="1d", progress=False, auto_adjust=False)
        if isinstance(y.columns, pd.MultiIndex):
            y.columns = y.columns.get_level_values(0)
        m[name] = y["Close"].reindex(m.index.union(y.index)).loc[m.index] if len(y) else np.nan
    m = m.sort_index().ffill()
    m.index = m.index.tz_localize("UTC")
    m.to_parquet(PROC / "macro_daily.parquet")
    return m


def load_hourly() -> pd.DataFrame:
    return pd.read_parquet(PROC / "xauusd_1h.parquet")


def load_macro() -> pd.DataFrame:
    return pd.read_parquet(PROC / "macro_daily.parquet")


if __name__ == "__main__":
    h = build_hourly()
    print("hourly", h.index.min(), "->", h.index.max(), len(h), h["src"].value_counts().to_dict())
    m = build_macro()
    print("macro", m.index.min(), "->", m.index.max(), m.columns.tolist())
