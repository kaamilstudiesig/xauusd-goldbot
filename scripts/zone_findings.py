"""Summarise all blind tests in journal/blind.db into reports/zone_findings.md."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def stats(g: pd.DataFrame) -> pd.Series:
    w = g.r > 0
    gl = -g.loc[~w, "r"].sum()
    return pd.Series({"trades": len(g), "win_rate": round(w.mean(), 2), "avg_r": round(g.r.mean(), 3),
                      "pf": round(g.loc[w, "r"].sum() / gl, 2) if gl > 0 else np.nan, "total_r": round(g.r.sum(), 1)})


def main():
    con = sqlite3.connect(ROOT / "journal" / "blind.db")
    t = pd.read_sql_query("SELECT * FROM blind_trades", con)
    t["period"] = np.where(t.test.str.startswith("hist"), "2023-01..2025-07", "Oct 2026 (blind)")
    t["tf"] = t.level.str.split().str[0]
    t["kind"] = t.level.str.split().str[1] + "_" + t.level.str.split().str[2]
    t["year"] = pd.to_datetime(t.entry_time, utc=True).dt.year
    out = ["# Zone analyser findings", ""]
    v = t.groupby(["variant", "period"]).apply(stats).unstack("period")
    out += ["## Every variant: history vs blind October", "", v.to_string(), ""]
    h = t[t.period != "Oct 2026 (blind)"]
    for col in ["year", "session", "tf", "kind", "candle"]:
        x = h.groupby(["variant", col]).apply(stats)
        x = x[x.trades >= 15]
        out += [f"## History by {col} (groups with 15+ trades)", "", x.to_string(), ""]
    (ROOT / "reports" / "zone_findings.md").write_text("\n".join(out))
    print("\n".join(out[:8 + len(v)]))


if __name__ == "__main__":
    main()
