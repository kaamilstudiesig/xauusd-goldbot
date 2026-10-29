"""Blind forward test of the zone analyser.

The analyser is fed one completed 15m bar at a time and can only see bars up to that point.
Its orders are filled by the backtest engine on the FOLLOWING bars (next-bar open, stop-first,
realistic gold costs). Every trade is journaled with the full reason it was taken.

  .venv/bin/python scripts/blind_test.py --name oct2026 --start 2026-10-01 --end 2026-10-30
  .venv/bin/python scripts/blind_test.py --name hist --start 2023-01-01 --end 2025-07-11 --no-charts
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from goldbot import backtest as bt  # noqa: E402
from goldbot.analyser import ZoneAnalyser, ZoneParams  # noqa: E402
from goldbot.data import PROC  # noqa: E402

VARIANTS = {
    "both_smc": ZoneParams(mode="both", confirm="smc"),
    "breakout_smc": ZoneParams(mode="breakout", confirm="smc"),
    "breakout_plain": ZoneParams(mode="breakout", confirm="none"),
    "rejection_smc": ZoneParams(mode="rejection", confirm="smc"),
    "rejection_candle": ZoneParams(mode="rejection", confirm="none"),
    "breakout_smc_wide": ZoneParams(mode="breakout", confirm="smc", min_sl_atr=2.0, max_sl_atr=4.0),
    "sr_breakout_smc": ZoneParams(mode="breakout", confirm="smc", kinds=("sr1", "sr2")),
    "sr_rejection_smc": ZoneParams(mode="rejection", confirm="smc", kinds=("sr1", "sr2")),
    "sr_retest": ZoneParams(triggers=("retest",), kinds=("sr1", "sr2")),
    "retest": ZoneParams(triggers=("retest",)),
    "sweep": ZoneParams(triggers=("sweep",)),
    "retest+sweep": ZoneParams(triggers=("retest", "sweep")),
}
DB = ROOT / "journal" / "blind.db"


def load(start, end, warmup_days=20):
    d = pd.read_parquet(PROC / "xauusd_15m.parquet")
    d = d.loc[pd.Timestamp(start, tz="UTC") - pd.Timedelta(days=warmup_days): pd.Timestamp(end, tz="UTC")]
    return d[["open", "high", "low", "close", "volume", "src"]]


def run_variant(d, name, params, start, end):
    za = ZoneAnalyser(d, params)
    sig = za.run(start, end)
    frame = za.signal_frame(sig)
    frame.loc[frame.index < pd.Timestamp(start, tz="UTC"), "side"] = 0
    dd = d.copy()
    dd["atr"] = za.atr
    trades, eq = bt.run(dd, frame, bt.BTConfig(risk_pct=0.005), route=name)
    trades = trades[trades.entry_time >= pd.Timestamp(start, tz="UTC")]
    if len(sig) and len(trades):
        sig = sig.drop_duplicates("bar_time").set_index("bar_time")
        sig_time = trades["entry_time"] - pd.Timedelta(minutes=15)
        ctx = sig.reindex(pd.DatetimeIndex(sig_time))
        for col in ["trigger", "level", "tf", "kind", "wick", "body", "structure", "fvg_last3", "candle", "session", "atr15"]:
            trades[col] = ctx[col].values
    return trades, eq, sig, za


def journal(test, name, trades, sig):
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS blind_trades (test TEXT, variant TEXT, entry_time TEXT, exit_time TEXT,
        side INTEGER, entry REAL, exit REAL, sl REAL, tp REAL, pnl REAL, r REAL, reason TEXT, bars INTEGER,
        trigger TEXT, level TEXT, structure TEXT, fvg TEXT, candle TEXT, session TEXT, run_ts TEXT,
        PRIMARY KEY (test, variant, entry_time))""")
    con.execute("""CREATE TABLE IF NOT EXISTS blind_signals (test TEXT, variant TEXT, bar_time TEXT, side INTEGER,
        trigger TEXT, level TEXT, close REAL, structure TEXT, candle TEXT, PRIMARY KEY (test, variant, bar_time))""")
    now = pd.Timestamp.now(tz="UTC").isoformat()
    # a re-run replaces that test+variant entirely, so stale rows from older code never linger
    con.execute("DELETE FROM blind_trades WHERE test=? AND variant=?", (test, name))
    con.execute("DELETE FROM blind_signals WHERE test=? AND variant=?", (test, name))
    for _, t in trades.iterrows():
        con.execute("INSERT OR REPLACE INTO blind_trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (test, name, str(t.entry_time), str(t.exit_time), int(t.side), t.entry, t.exit, t.sl,
                     None if pd.isna(t.tp) else t.tp, t.pnl, t.r, t.reason, int(t.bars), t.get("trigger"),
                     t.get("level"), t.get("structure"), t.get("fvg_last3"), t.get("candle"), t.get("session"), now))
    for bt_, s in (sig.iterrows() if len(sig) else []):
        con.execute("INSERT OR REPLACE INTO blind_signals VALUES (?,?,?,?,?,?,?,?,?)",
                    (test, name, str(bt_), int(s.side), s.trigger, s.level, s.close, s.structure, s.candle))
    con.commit()
    con.close()


def chart(d, za, t, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    i = d.index.get_loc(t.entry_time)
    w = d.iloc[max(0, i - 96): min(len(d), i + 40)]
    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(w))
    col = np.where(w.close >= w.open, "#2a9d8f", "#e76f51")
    ax.vlines(x, w.low, w.high, color=col, lw=0.8)
    ax.vlines(x, np.minimum(w.open, w.close), np.maximum(w.open, w.close), color=col, lw=3.5)
    # redraw the thresholds as the analyser saw them at the signal bar
    tc = t.entry_time
    za2 = ZoneAnalyser(d.loc[:tc], za.p)
    za2.refresh_levels(tc)
    for b in za2.levels:
        ys_w = [b.at(ts + pd.Timedelta(minutes=15))[0] for ts in w.index]
        ys_b = [b.at(ts + pd.Timedelta(minutes=15))[1] for ts in w.index]
        c = "#264653" if b.kind == "channel" else "#8d6cab"
        ax.plot(x, ys_w, color=c, lw=1.2, ls="-", alpha=0.8, label=f"{b.tf} {b.kind} {b.side} wick")
        ax.plot(x, ys_b, color=c, lw=0.8, ls="--", alpha=0.6)
    j = i - (len(d.loc[:w.index[0]]) - 1)
    ax.axvline(j, color="grey", lw=0.6)
    ax.hlines([t.entry], j, len(w) - 1, color="black", lw=1)
    ax.hlines([t.sl], j, len(w) - 1, color="#e63946", lw=1, ls=":")
    if not pd.isna(t.tp):
        ax.hlines([t.tp], j, len(w) - 1, color="#2a9d8f", lw=1, ls=":")
    lo, hi = w.low.min(), w.high.max()
    pad = (hi - lo) * 0.15
    ax.set_ylim(lo - pad, hi + pad)
    side = "LONG" if t.side > 0 else "SHORT"
    ax.set_title(f"{t.entry_time:%Y-%m-%d %H:%M} UTC  {side} {t.trigger}  |  {t.level}\n"
                 f"{t.structure or 'no structure event'} | candle {t.candle} | result {t.reason} {t.r:+.2f}R", fontsize=9)
    ax.set_xticks(x[::16])
    ax.set_xticklabels([ts.strftime("%m-%d %H:%M") for ts in w.index[::16]], fontsize=7, rotation=30)
    ax.legend(fontsize=6, loc="upper left", ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--variants", nargs="*", default=list(VARIANTS))
    ap.add_argument("--no-charts", action="store_true")
    ap.add_argument("--chart-variant", default="both_smc")
    a = ap.parse_args()
    d = load(a.start, a.end)
    rows, lines = [], [f"# Blind test: {a.name} ({a.start} -> {a.end})", "",
                       "Each 15m bar was revealed one at a time; orders were filled on later bars with realistic costs.", ""]
    keep = {}
    for name in a.variants:
        t0 = time.time()
        trades, eq, sig, za = run_variant(d, name, VARIANTS[name], a.start, a.end)
        journal(a.name, name, trades, sig)
        m = bt.metrics(trades, eq.loc[a.start:]) if len(trades) else {"trades": 0}
        rows.append({"variant": name, "signals": len(sig), **m})
        keep[name] = (trades, za)
        print(f"{name:18s} {time.time()-t0:6.1f}s signals={len(sig)} {m}", flush=True)
    res = pd.DataFrame(rows)
    lines += ["## Variants", "", res.to_string(index=False), ""]
    tr, za = keep.get(a.chart_variant, next(iter(keep.values())))
    if len(tr):
        by = tr.groupby("trigger").r.agg(["count", "mean", "sum"]).round(2)
        lines += [f"## {a.chart_variant}: by trigger", "", by.to_string(), "",
                  f"## {a.chart_variant}: by session", "", tr.groupby("session").r.agg(["count", "mean"]).round(2).to_string(), ""]
        if len(tr) <= 80:
            cols = ["entry_time", "side", "trigger", "tf", "kind", "entry", "sl", "tp", "exit", "reason", "r", "structure", "candle", "session"]
            lines += [f"## {a.chart_variant}: every trade", "", tr[cols].round(2).to_string(index=False), ""]
    out = ROOT / "reports" / f"blind_{a.name}.md"
    out.write_text("\n".join(lines))
    res.to_csv(ROOT / "reports" / f"blind_{a.name}_variants.csv", index=False)
    if not a.no_charts and len(tr):
        cdir = ROOT / "reports" / "charts" / a.name
        cdir.mkdir(parents=True, exist_ok=True)
        for _, t in tr.iterrows():
            chart(d, za, t, cdir / f"{t.entry_time:%m%d_%H%M}_{'L' if t.side > 0 else 'S'}_{t.trigger}.png")
        print("charts ->", cdir)
    print("report ->", out)


if __name__ == "__main__":
    main()
