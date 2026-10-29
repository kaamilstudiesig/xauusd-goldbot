"""Backtest every route across separate periods and write a ranked summary.

Usage:
  .venv/bin/python scripts/research.py                 # all default routes
  .venv/bin/python scripts/research.py --routes london_breakout ml_lgbm
  .venv/bin/python scripts/research.py --routes kronos --since 2024-01-01   # experimental
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goldbot import backtest as bt  # noqa: E402
from goldbot.data import load_hourly, load_macro  # noqa: E402
from goldbot.features import add_core, add_macro  # noqa: E402
from goldbot.routes.registry import EXPERIMENTAL, all_routes  # noqa: E402
from goldbot.scoring import allocate, weighted_score  # noqa: E402

PERIODS = {"2010-2018": ("2010-01-01", "2018-12-31"), "2019-2022": ("2019-01-01", "2022-12-31"),
           "2023-2026": ("2023-01-01", "2027-01-01")}
OUT = ROOT / "reports"


def prepared(since: str = "2008-01-01") -> pd.DataFrame:
    d = load_hourly().loc[since:]
    return add_macro(add_core(d), load_macro()).dropna(subset=["ema200", "atr"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--routes", nargs="*")
    ap.add_argument("--since", default="2008-01-01")
    ap.add_argument("--out", default="research", help="output file prefix inside reports/")
    a = ap.parse_args()
    d = prepared(a.since)
    routes = all_routes()
    if a.routes:
        routes = {k: (routes[k] if k in routes else EXPERIMENTAL[k]()) for k in a.routes}
    OUT.mkdir(exist_ok=True)
    rows, scores, all_trades = [], {}, []
    for name, route in routes.items():
        t0 = time.time()
        sig = route.signals(d)
        trades, eq = bt.run(d, sig, route=name)
        all_trades.append(trades)
        row = {"route": name, "family": route.family}
        for p, (s, e) in PERIODS.items():
            tp = trades[(trades.entry_time >= s) & (trades.entry_time <= e)]
            eqp = eq.loc[s:e]
            m = bt.metrics(tp, eqp) if len(eqp) else {"trades": 0}
            row.update({f"{p}:{k}": v for k, v in m.items() if k in ("trades", "win_rate", "avg_r", "pf", "sharpe", "max_dd")})
        sc = weighted_score(trades)
        scores[name] = sc
        row.update(sc)
        row["full"] = json.dumps(bt.metrics(trades.loc[trades.entry_time >= "2010"], eq.loc["2010":]))
        rows.append(row)
        print(f"{name:26s} {time.time()-t0:5.1f}s  trades={len(trades):5d}  {sc}", flush=True)
    res = pd.DataFrame(rows).sort_values("w_t", ascending=False)
    res.to_csv(OUT / f"{a.out}_results.csv", index=False)
    pd.concat(all_trades).to_parquet(OUT / f"{a.out}_trades.parquet")
    alloc = allocate(scores)
    (OUT / f"{a.out}_allocation.json").write_text(json.dumps({"generated": pd.Timestamp.now(tz="UTC").isoformat(),
                                                     "allocation": alloc, "scores": scores}, indent=2))
    print("\nallocation:", alloc)


if __name__ == "__main__":
    main()
