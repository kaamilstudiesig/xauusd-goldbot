"""Signal pool: every signal a permissive analyser emits, each scored ON ITS OWN with the real
backtester rules (next-bar open fill, stop-first, costs, flat 20:45 UTC, time stop).

Used to read the journal for refinement ideas without one-position-at-a-time overlap hiding signals.
Only run it on DEVELOPMENT months; validation / holdout are scored with zone_research.py.

  .venv/bin/python scripts/signal_pool.py --start 2023-01-01 --end 2025-01-01 --out reports/tmp/pool_dev.parquet
"""
from __future__ import annotations

import argparse
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from goldbot import backtest as bt  # noqa: E402
from goldbot.analyser import ZoneAnalyser, ZoneParams  # noqa: E402
from scripts.blind_test import load  # noqa: E402

POOL = ZoneParams(confirm="none", triggers=("breakout", "retest", "sweep", "rejection"), cooldown=1)
PAD = 220  # bars before each signal so the cost model's rolling median sees the same history


def score(d: pd.DataFrame, atr: np.ndarray, sig: pd.DataFrame, rr_list=(1.0, 1.5, 2.0, 3.0), max_bars=32, flat_hour=20):
    """R outcome of each signal traded alone, for several reward:risk targets."""
    out = []
    idx = d.index
    fx_all = (idx.hour == flat_hour) & (idx.minute == 45)
    for _, s in sig.iterrows():
        i = int(s["i"])
        a, b = max(0, i - PAD), min(len(d), i + max_bars + 3)
        dd = d.iloc[a:b].copy()
        dd["atr"] = atr[a:b]
        res = {}
        for rr in rr_list:
            f = pd.DataFrame({"side": 0, "sl_dist": np.nan, "tp_dist": np.nan, "max_bars": float(max_bars),
                              "trail_atr": np.nan, "force_exit": fx_all[a:b]}, index=dd.index)
            f.iloc[i - a, :3] = [s["side"], s["sl_dist"], rr * s["sl_dist"]]
            tr, _ = bt.run(dd, f, bt.BTConfig(risk_pct=0.005))
            res[f"r{rr:g}"] = tr.r.iloc[0] if len(tr) else np.nan
        # gross (no cost) at rr 2, to measure the cost drag
        f = pd.DataFrame({"side": 0, "sl_dist": np.nan, "tp_dist": np.nan, "max_bars": float(max_bars),
                          "trail_atr": np.nan, "force_exit": fx_all[a:b]}, index=dd.index)
        f.iloc[i - a, :3] = [s["side"], s["sl_dist"], 2.0 * s["sl_dist"]]
        cfg = bt.BTConfig(risk_pct=0.005)
        from goldbot.costs import CostModel
        cfg.costs = CostModel(spread_london_ny=0, spread_asia=0, spread_rollover=0, spread_late_ny=0, commission_rt=0,
                              slippage_entry=0, slippage_stop=0, swap_long_annual=0, swap_short_annual=0)
        tr, _ = bt.run(dd, f, cfg)
        res["r2_gross"] = tr.r.iloc[0] if len(tr) else np.nan
        out.append(res)
    return pd.concat([sig.reset_index(drop=True), pd.DataFrame(out)], axis=1)


def _chunk(args):
    start, end, params = args
    d = load(start, end)
    za = ZoneAnalyser(d, params)
    sig = za.run(start, end)
    if not len(sig):
        return pd.DataFrame()
    sig = sig.drop_duplicates(["bar_time", "trigger", "side"])
    return score(d[["open", "high", "low", "close", "volume"]], za.atr, sig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2023-01-01")
    ap.add_argument("--end", default="2025-01-01")
    ap.add_argument("--out", default=str(ROOT / "reports" / "tmp" / "pool_dev.parquet"))
    a = ap.parse_args()
    months = pd.date_range(a.start, a.end, freq="MS")
    jobs = [(str(months[k].date()), str(months[k + 1].date()), POOL) for k in range(len(months) - 1)]
    with ProcessPoolExecutor(4) as ex:
        parts = [p for p in ex.map(_chunk, jobs) if len(p)]
    pool = pd.concat(parts, ignore_index=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pool.to_parquet(a.out)
    print(len(pool), "signals ->", a.out)
    print(pool.groupby("trigger")[["r1", "r1.5", "r2", "r3", "r2_gross"]].mean().round(3))


if __name__ == "__main__":
    main()
