"""Parameter-sensitivity grid for a route: a real edge should survive nearby parameter values."""
from __future__ import annotations
import itertools, sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from goldbot import backtest as bt
from goldbot.routes.rules import DailyTrend
from scripts.research import prepared

def main():
    d = prepared()
    rows = []
    grid = {"days": [10, 20, 40, 55], "trend_days": [50, 100, 200], "sl_datr": [2.0, 3.0], "trail_datr": [2.5, 4.0], "long_only": [False, True]}
    for vals in itertools.product(*grid.values()):
        p = dict(zip(grid, vals))
        tr, eq = bt.run(d, DailyTrend(**p).signals(d), route="dt")
        tr = tr[tr.entry_time >= "2010"]
        row = dict(p)
        for per, (s, e) in {"10-18": ("2010", "2018"), "19-22": ("2019", "2022"), "23-26": ("2023", "2026")}.items():
            t = tr[(tr.entry_time >= s) & (tr.entry_time < str(int(e) + 1))]
            row[f"R_{per}"] = round(t.r.mean(), 2) if len(t) else None
        row["n"], row["avg_r"] = len(tr), round(tr.r.mean(), 3)
        rows.append(row)
    r = pd.DataFrame(rows)
    r.to_csv(ROOT / "reports" / "robustness_daily_trend.csv", index=False)
    pos_all = (r[["R_10-18", "R_19-22", "R_23-26"]] > 0).all(axis=1)
    print(f"configs: {len(r)}  positive overall: {(r.avg_r>0).mean():.0%}  positive in all 3 periods: {pos_all.mean():.0%}")
    print(r.groupby("long_only")[["avg_r", "R_10-18", "R_19-22", "R_23-26"]].median())
    print(r.groupby("days")[["avg_r"]].median().T, r.groupby("trend_days")[["avg_r"]].median().T)

if __name__ == "__main__":
    main()
