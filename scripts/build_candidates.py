"""Build the candidate pool the labeller shows you.

Every setup a permissive analyser finds (breakout / retest / sweep / rejection on H1+H4 channels,
box and S/R levels) from 2023-01 to today, each scored ON ITS OWN with the backtester's rules:
next-bar fill, stop-first, real costs, held up to 24h, flat before the weekend.
Outcomes are stored but never shown in the labeller.

  .venv/bin/python scripts/build_candidates.py              # -> journal/candidates.parquet
"""
from __future__ import annotations

import argparse
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from goldbot.analyser import ZoneAnalyser  # noqa: E402
from scripts.blind_test import load  # noqa: E402
from scripts.signal_pool import POOL, score  # noqa: E402

OUT = ROOT / "journal" / "candidates.parquet"
SPLITS = [("dev", "2023-01-01", "2025-01-01"), ("val", "2025-01-01", "2025-08-01"), ("hold", "2025-08-01", "2026-11-01")]


def period_of(ts: pd.Timestamp) -> str:
    for name, s, e in SPLITS:
        if pd.Timestamp(s, tz="UTC") <= ts < pd.Timestamp(e, tz="UTC"):
            return name
    return "other"


def _chunk(args):
    start, end = args
    d = load(start, end)
    za = ZoneAnalyser(d, POOL)
    sig = za.run(start, end)
    if not len(sig):
        return pd.DataFrame()
    sig = sig.drop_duplicates(["bar_time", "trigger", "side"])
    # v18-style exits: hold up to 24h (96 bars), no session flat
    return score(d[["open", "high", "low", "close", "volume"]], za.atr, sig, rr_list=(2.0, 3.0), max_bars=96, flat_hour=-1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2023-01-01")
    ap.add_argument("--end", default="2026-10-30")
    a = ap.parse_args()
    months = list(pd.date_range(a.start, a.end, freq="MS")) + [pd.Timestamp(a.end)]
    jobs = [(str(months[k].date()), str(months[k + 1].date())) for k in range(len(months) - 1)]
    with ProcessPoolExecutor(4) as ex:
        parts = [p for p in ex.map(_chunk, jobs) if len(p)]
    pool = pd.concat(parts, ignore_index=True).sort_values("bar_time").reset_index(drop=True)
    pool["bar_time"] = pd.to_datetime(pool["bar_time"], utc=True)
    pool["period"] = pool["bar_time"].map(period_of)
    pool["cid"] = pool["bar_time"].dt.strftime("%Y%m%d%H%M") + "_" + pool["trigger"].str[:3] + "_" + np.where(pool["side"] > 0, "L", "S")
    pool = pool.drop_duplicates("cid").reset_index(drop=True)
    # random but fixed labelling order, so every session continues where the last stopped
    pool["order"] = np.random.default_rng(7).permutation(len(pool))
    OUT.parent.mkdir(exist_ok=True)
    pool.to_parquet(OUT)
    print(len(pool), "candidates ->", OUT)
    print(pool.groupby(["period", "trigger"]).agg(n=("r2", "size"), r2=("r2", "mean"), r3=("r3", "mean")).round(3))


if __name__ == "__main__":
    main()
