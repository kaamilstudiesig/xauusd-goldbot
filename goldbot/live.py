"""Live 15m XAU/USD bars for the scheduled paper trader.

History = the Twelve Data spot chunks in data/raw/td15 (Oct 2022 -> Oct 2026) plus everything the
scheduler has collected since, stored as small monthly CSVs in data/live/ (text, so hourly git
commits stay tiny).

New bars each run come from:
  1. Twelve Data REST (XAU/USD spot, UTC) when TWELVEDATA_API_KEY is set: preferred
  2. otherwise yfinance GC=F 15m futures minus the futures/spot basis measured on the most recent
     overlap with stored spot bars (marked src=gcf_proxy; spot rows replace them when they arrive)
Only completed bars are kept.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .data import OHLC, fetch_futures, load_twelvedata_15m, trading_week_mask

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "data" / "live"
M15 = pd.Timedelta(minutes=15)


def _clean(d: pd.DataFrame) -> pd.DataFrame:
    d = d[trading_week_mask(d.index)]
    d = d[(d["high"] >= d[["open", "close"]].max(axis=1)) & (d["low"] <= d[["open", "close"]].min(axis=1))]
    d = d[d["high"] > d["low"]]  # flat filler bars
    now = pd.Timestamp.now(tz="UTC")
    return d[d.index + M15 <= now]  # completed bars only


def fetch_twelvedata(key: str, outputsize: int = 500) -> pd.DataFrame:
    r = requests.get("https://api.twelvedata.com/time_series", timeout=30, params={
        "symbol": "XAU/USD", "interval": "15min", "outputsize": outputsize, "timezone": "UTC",
        "order": "ASC", "apikey": key})
    j = r.json()
    if j.get("status") != "ok":
        raise RuntimeError(f"Twelve Data: {j.get('message', j)}")
    d = pd.DataFrame(j["values"])
    d.index = pd.to_datetime(d.pop("datetime"), utc=True)
    d = d[OHLC].astype(float)
    d["src"] = "spot_twelvedata"
    return _clean(d)


def load_live() -> pd.DataFrame:
    files = sorted(LIVE.glob("xau15_*.csv"))
    if not files:
        return pd.DataFrame(columns=OHLC + ["src"])
    d = pd.concat([pd.read_csv(f, index_col=0, parse_dates=True) for f in files])
    d.index = pd.to_datetime(d.index, utc=True)
    return d[~d.index.duplicated(keep="last")].sort_index()


def history() -> pd.DataFrame:
    td = load_twelvedata_15m()
    td["src"] = "spot_twelvedata"
    lv = load_live()
    d = pd.concat([td[OHLC + ["src"]], lv[OHLC + ["src"]]])
    # spot beats proxy on the same timestamp
    d["_rank"] = np.where(d["src"].astype(str).str.startswith("spot"), 0, 1)
    d = d.sort_values("_rank", kind="stable")
    d = d[~d.index.duplicated(keep="first")].drop(columns="_rank").sort_index()
    return d


def gcf_proxy(spot: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    fut = fetch_futures(period="60d", interval="15m")
    real = spot[spot["src"].astype(str).str.startswith("spot")]  # never measure against earlier proxy rows
    both = real[["close"]].join(fut[["close"]], rsuffix="_f", how="inner")
    both = both[both.index >= both.index.max() - pd.Timedelta(days=3)] if len(both) else both
    bfile = LIVE / "basis.txt"
    if len(both) >= 20:
        basis = float((both["close_f"] - both["close"]).median())
        LIVE.mkdir(parents=True, exist_ok=True)
        bfile.write_text(f"{basis:.4f} measured {both.index.max()}\n")
    elif bfile.exists():
        basis = float(bfile.read_text().split()[0])  # stale but better than nothing; set TWELVEDATA_API_KEY
    else:
        raise RuntimeError("no spot/futures overlap to measure the basis; set TWELVEDATA_API_KEY")
    fut[OHLC] = fut[OHLC] - basis
    fut["src"] = "gcf_proxy"
    return _clean(fut[OHLC + ["src"]]), basis


def update() -> dict:
    """Fetch new bars, append them to the monthly live CSVs. Returns info for the run log."""
    hist = history()
    key = os.environ.get("TWELVEDATA_API_KEY")
    info = {"source": "", "basis": 0.0, "new_bars": 0}
    if key:
        new = fetch_twelvedata(key, outputsize=500 if hist.index.max() > pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=4) else 5000)
        info["source"] = "twelvedata_spot"
    else:
        new, info["basis"] = gcf_proxy(hist)
        info["source"] = "gcf_proxy"
    # keep: anything newer than what we have, plus spot rows that replace earlier proxy rows
    proxy_idx = hist.index[hist["src"] == "gcf_proxy"]
    keep = new[(new.index > hist.index.max()) | (new.index.isin(proxy_idx) & new["src"].str.startswith("spot"))]
    info["new_bars"] = int(len(keep))
    if len(keep):
        LIVE.mkdir(parents=True, exist_ok=True)
        lv = pd.concat([load_live(), keep])
        lv = lv[~lv.index.duplicated(keep="last")].sort_index()
        for month, g in lv.groupby(lv.index.strftime("%Y-%m")):
            g.round(3).to_csv(LIVE / f"xau15_{month}.csv")
    return info


def bars15(since: str) -> pd.DataFrame:
    d = history().loc[since:]
    d["volume"] = 0.0
    return d


def to_hourly(d15: pd.DataFrame) -> pd.DataFrame:
    h = d15.resample("1h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    # an hour is complete only when its last 15m bar (:45) has arrived
    return h[h.index + pd.Timedelta(minutes=45) <= d15.index.max()]
