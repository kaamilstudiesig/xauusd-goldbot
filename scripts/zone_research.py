"""Zone-analyser refinement loop with a fixed development / validation / holdout split.

  DEV   2023-01 .. 2024-12   tune here only
  VAL   2025-01 .. 2025-07   check a candidate once it looks good on DEV
  HOLD  2025-08 .. 2026-10   recent months, reported once per finalised version (--holdout)

Each split is run bar by bar through scripts/blind_test.run_variant (no lookahead, next-bar fills,
realistic costs) and journaled to journal/blind.db as test "dev" / "val" / "hold".
Every run is appended to reports/iterations.csv; holdout runs also to reports/holdout_log.csv.

  .venv/bin/python scripts/zone_research.py v01_baseline_breakout          # dev + val
  .venv/bin/python scripts/zone_research.py v01_baseline_breakout --dev-only
  .venv/bin/python scripts/zone_research.py v07_final --holdout              # + holdout (logged)
"""
from __future__ import annotations

import argparse
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.blind_test import journal, load, run_variant  # noqa: E402
from scripts.zone_variants import ZV  # noqa: E402

SPLITS = {"dev": ("2023-01-01", "2025-01-01"), "val": ("2025-01-01", "2025-08-01"), "hold": ("2025-08-01", "2026-10-30")}
# split DEV into 4 half-years so a single variant runs on 4 cores
CHUNKS = {
    "dev": [("2023-01-01", "2023-07-01"), ("2023-07-01", "2024-01-01"), ("2024-01-01", "2024-07-01"), ("2024-07-01", "2025-01-01")],
    "val": [("2025-01-01", "2025-04-01"), ("2025-04-01", "2025-08-01")],
    "hold": [("2025-08-01", "2025-12-01"), ("2025-12-01", "2026-04-01"), ("2026-04-01", "2026-07-01"), ("2026-07-01", "2026-10-30")],
}


def stats(r: pd.Series) -> dict:
    if len(r) == 0:
        return {"n": 0, "win": np.nan, "avg_r": np.nan, "pf": np.nan, "tot_r": 0.0}
    w = r > 0
    gl = -r[~w].sum()
    return {"n": int(len(r)), "win": round(w.mean(), 3), "avg_r": round(r.mean(), 3),
            "pf": round(r[w].sum() / gl, 2) if gl > 0 else np.inf, "tot_r": round(r.sum(), 1)}


def _chunk(args):
    name, start, end, cs = args
    d = load(start, end, warmup_days=150)
    trades, eq, sig, za = run_variant(d, name, ZV[name], start, end, cost_scale=cs)
    return trades, sig


def run_split(name: str, split: str, pool: ProcessPoolExecutor, cost_scale=False) -> pd.DataFrame:
    parts = list(pool.map(_chunk, [(name, a, b, cost_scale) for a, b in CHUNKS[split]]))
    trades = pd.concat([p[0] for p in parts if len(p[0])], ignore_index=True) if any(len(p[0]) for p in parts) else pd.DataFrame()
    sigs = [p[1] for p in parts if len(p[1])]
    sig = pd.concat(sigs) if sigs else pd.DataFrame()
    journal(split + ("_costx" if cost_scale else ""), name, trades, sig)
    return trades


def monthly(trades: pd.DataFrame) -> pd.DataFrame:
    if not len(trades):
        return pd.DataFrame()
    m = trades.groupby(pd.to_datetime(trades.entry_time).dt.strftime("%Y-%m")).r
    return pd.DataFrame({k: stats(g) for k, g in m}).T


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="+")
    ap.add_argument("--dev-only", action="store_true")
    ap.add_argument("--holdout", action="store_true")
    ap.add_argument("--note", default="")
    ap.add_argument("--cost-scale", action="store_true", help="stress: $ costs scaled with the gold price")
    a = ap.parse_args()
    splits = ["dev"] if a.dev_only else ["dev", "val"] + (["hold"] if a.holdout else [])
    rows = []
    with ProcessPoolExecutor(4) as pool:
        for name in a.names:
            t0 = time.time()
            row = {"ts": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M"), "variant": name,
                   "note": a.note + (" [costs x price]" if a.cost_scale else "")}
            for sp in splits:
                tr = run_split(name, sp, pool, a.cost_scale)
                st = stats(tr.r if len(tr) else pd.Series(dtype=float))
                row.update({f"{sp}_{k}": v for k, v in st.items()})
                if sp in ("dev", "hold") and len(tr):
                    mm = monthly(tr)
                    row[f"{sp}_months_pos"] = f"{int((mm.avg_r > 0).sum())}/{len(mm)}"
                    row[f"{sp}_months_pf12"] = int((mm.pf >= 1.2).sum())
                    if sp == "hold":
                        mm.to_csv(ROOT / "reports" / f"holdout_monthly_{name}{'_costx' if a.cost_scale else ''}.csv")
                        print(mm.to_string())
                if sp == "dev" and len(tr):
                    yr = tr.groupby(pd.to_datetime(tr.entry_time).dt.year).r.mean().round(3).to_dict()
                    row["dev_by_year"] = str(yr)
            row["secs"] = round(time.time() - t0)
            rows.append(row)
            print({k: v for k, v in row.items() if k not in ("ts", "note")}, flush=True)
            out = ROOT / "reports" / "iterations.csv"
            pd.DataFrame([row]).to_csv(out, mode="a", header=not out.exists(), index=False)
            if a.holdout:
                hl = ROOT / "reports" / "holdout_log.csv"
                pd.DataFrame([row]).to_csv(hl, mode="a", header=not hl.exists(), index=False)


if __name__ == "__main__":
    main()
