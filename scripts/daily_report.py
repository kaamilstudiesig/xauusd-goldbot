"""Daily paper-trading report (after the NY close). Simulation only: these are paper trades.

  .venv/bin/python scripts/daily_report.py              # -> reports/daily/YYYY-MM-DD.md (+ .png chart)
  .venv/bin/python scripts/daily_report.py --mention someone

The trading day runs from 21:00 UTC (NY close) the previous day to 21:00 UTC today.
Reads the paper journal only; it never writes trades.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from goldbot import live  # noqa: E402
from goldbot.analyser import ZoneAnalyser, ZoneParams  # noqa: E402
from goldbot.journal import read, restore_sql  # noqa: E402
from goldbot.paper import ensure_macro, load_cfg  # noqa: E402

OUT = ROOT / "reports" / "daily"
REPO = "kaamilstudiesig/xauusd-goldbot"


def fmt_side(s) -> str:
    return "LONG" if int(s) > 0 else "SHORT"


def why(ctx: str) -> str:
    try:
        c = json.loads(ctx or "{}")
    except json.JSONDecodeError:
        return ""
    if "trigger" in c:  # zone route
        parts = [c.get("trigger"), c.get("level", "").split(" wick")[0], c.get("structure") or None,
                 f"candle {c.get('candle')}" if c.get("candle") else None, c.get("session")]
        return ", ".join(p for p in parts if p)
    keys = [("rsi", "RSI {:.0f}"), ("adx", "ADX {:.0f}"), ("atr", "ATR ${:.1f}"), ("hour", "signal {:.0f}:00 UTC")]
    return ", ".join(f.format(c[k]) for k, f in keys if c.get(k) is not None)


def open_r(t, price) -> float:
    risk = abs(t["entry"] - t["sl"])
    return (price - t["entry"]) * t["side"] / risk if risk else np.nan


def levels_now(d15: pd.DataFrame, now: pd.Timestamp):
    za = ZoneAnalyser(d15.loc[now - pd.Timedelta(days=30):], ZoneParams(tfs=(("4h", 60), ("1h", 72))))
    za.refresh_levels(now)
    rows = []
    for b in za.levels:
        w, bd = b.at(now)
        rows.append({"tf": b.tf, "kind": b.kind, "side": b.side, "wick": round(w, 2), "body": round(bd, 2), "touches": b.touches})
    return pd.DataFrame(rows), za.levels


def chart(d15, levels, now, path):
    h1 = live.to_hourly(d15.loc[now - pd.Timedelta(days=6):])
    fig, ax = plt.subplots(figsize=(11, 4.6))
    x = np.arange(len(h1))
    col = np.where(h1.close >= h1.open, "#1f9e89", "#d1495b")
    ax.vlines(x, h1.low, h1.high, color=col, lw=0.8)
    ax.vlines(x, np.minimum(h1.open, h1.close), np.maximum(h1.open, h1.close), color=col, lw=2.6)
    pad = 12
    xr = np.arange(len(h1) + pad)
    j = len(h1) - 1
    for b in levels:
        if b.tf != "4h":
            continue
        w0, b0 = b.at(now)
        per = b.slope / b.tf_hours
        c = "#3d5a80" if b.kind == "channel" else "#7b6d8d" if b.kind == "box" else "#5c8d89"
        ax.plot(xr, w0 + per * (xr - j), color=c, lw=1.4, label=f"H4 {b.kind} {b.side}")
        ax.plot(xr, b0 + per * (xr - j), color=c, lw=0.8, ls="--")
    lo, hi = h1.low.min(), h1.high.max()
    ax.set_ylim(lo - (hi - lo) * 0.1, hi + (hi - lo) * 0.1)
    k = max(1, len(h1) // 8)
    ax.set_xticks(x[::k])
    ax.set_xticklabels([t.strftime("%a %H:%M") for t in h1.index[::k]], fontsize=7)
    ax.tick_params(axis="y", labelsize=7)
    ax.grid(alpha=0.15)
    ax.legend(fontsize=7, loc="upper left", ncol=3)
    ax.set_title("XAU/USD H1, last 6 days, with H4 lines (solid = wick line, dashed = body line)", fontsize=9, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mention", default="kaamilstudiesig")
    ap.add_argument("--date", help="report date YYYY-MM-DD (default: today UTC)")
    a = ap.parse_args()
    restore_sql()
    cfg = load_cfg()
    now = pd.Timestamp.now(tz="UTC").floor("15min")
    day = pd.Timestamp(a.date, tz="UTC") if a.date else now.normalize()
    d_end = day + pd.Timedelta(hours=21)
    d_start = d_end - pd.Timedelta(days=1)
    if day.dayofweek == 0:  # Monday's session starts at Sunday's open
        d_start = d_end - pd.Timedelta(days=3)
    d15 = live.bars15("2025-01-01")
    price = float(d15.close.iloc[-1])
    last_bar = d15.index[-1]
    prev = d15.close.loc[:d_start]
    chg = price - float(prev.iloc[-1]) if len(prev) else np.nan

    tr = read("SELECT * FROM trades")
    for c in ("entry_time", "exit_time"):
        tr[c] = pd.to_datetime(tr[c], utc=True)
    tr["portfolio"] = tr["weight"] > 0
    opened = tr[(tr.entry_time >= d_start) & (tr.entry_time < d_end)].sort_values("entry_time")
    closed = tr[(tr.status == "closed") & (tr.exit_time >= d_start) & (tr.exit_time < d_end)].sort_values("exit_time")
    still = tr[tr.status == "open"].sort_values("entry_time")
    al = read("SELECT * FROM allocation WHERE run_id=(SELECT MAX(run_id) FROM allocation)")
    eq = read("SELECT * FROM equity ORDER BY ts")
    runs = read("SELECT * FROM runs ORDER BY run_id DESC LIMIT 1")

    L = [f"# Gold daily report: {day:%a %d %b %Y}", "",
         f"@{a.mention} · **Paper trading only (simulated, no real money).** Trading day: {d_start:%a %H:%M} → {d_end:%a %H:%M} UTC.", "",
         f"**XAU/USD {price:,.2f}** ({chg:+,.2f} on the day) · last bar {last_bar:%a %H:%M} UTC · "
         f"data: {runs.data_source[0] if len(runs) else '-'}", ""]

    # --- today's trades
    L += ["## Today's trades", ""]
    if not len(opened) and not len(closed):
        L += ["No trades opened or closed today.", ""]
    if len(opened):
        L += ["**Opened**", "", "| Route | Side | Entry (UTC) | Entry | Stop | Target | Why |", "|---|---|---|---|---|---|---|"]
        for _, t in opened.iterrows():
            tag = "" if t.portfolio else " (shadow)"
            L.append(f"| {t.route}{tag} | {fmt_side(t.side)} | {t.entry_time:%H:%M} | {t.entry:,.2f} | {t.sl:,.2f} | "
                     f"{'-' if pd.isna(t.tp) else f'{t.tp:,.2f}'} | {why(t.context)} |")
        L.append("")
    if len(closed):
        L += ["**Closed**", "", "| Route | Side | Entry | Exit | Result | Reason |", "|---|---|---|---|---|---|"]
        for _, t in closed.iterrows():
            tag = "" if t.portfolio else " (shadow)"
            L.append(f"| {t.route}{tag} | {fmt_side(t.side)} | {t.entry:,.2f} | {t.exit:,.2f} | **{t.r:+.2f}R** (${t.pnl:+,.0f}) | {t.reason} |")
        L.append("")

    # --- open positions
    L += ["## Open positions", ""]
    if len(still):
        L += ["| Route | Side | Since (UTC) | Entry | Stop | Now | Open R | To stop |", "|---|---|---|---|---|---|---|---|"]
        for _, t in still.iterrows():
            tag = "" if t.portfolio else " (shadow)"
            L.append(f"| {t.route}{tag} | {fmt_side(t.side)} | {t.entry_time:%a %H:%M} | {t.entry:,.2f} | {t.sl:,.2f} | "
                     f"{price:,.2f} | {open_r(t, price):+.2f}R | ${abs(price - t.sl):,.2f} |")
        L.append("")
    else:
        L += ["None.", ""]

    # --- scorecard
    c_all = tr[tr.status == "closed"]
    L += ["## Scorecard", ""]
    if len(eq):
        e = eq.iloc[-1]
        L.append(f"Paper account (portfolio routes only): **${e.equity:,.2f}** (closed {e.closed_pnl:+,.2f}, open {e.open_pnl:+,.2f}) "
                 f"since {cfg['paper_start']}.")
    if len(c_all):
        g = c_all.groupby("route").agg(trades=("r", "size"), win=("r", lambda x: f"{(x > 0).mean():.0%}"),
                                       avg_r=("r", "mean"), total_r=("r", "sum")).round(2)
        L += ["", "Closed trades since the start:", "", "| Route | Trades | Win | Avg R | Total R |", "|---|---|---|---|---|"]
        L += [f"| {r} | {v.trades} | {v.win} | {v.avg_r:+.2f} | {v.total_r:+.2f} |" for r, v in g.iterrows()]
    flags = al[al.status.str.startswith("flag")] if len(al) else al
    if len(flags):
        L += ["", "Flags (you decide, by editing `config/paper.json`): " + ", ".join(f"{r.route} → {r.status}" for r in flags.itertuples())]
    L += ["", f"{len(c_all)} closed trades so far. Nothing is meaningful before ~100.", ""]

    # --- tomorrow
    h1 = live.to_hourly(d15)
    dc, dh, dl = h1.close.resample("D").last().dropna(), h1.high.resample("D").max().dropna(), h1.low.resample("D").min().dropna()
    done = dc.index < now.normalize()  # daily_trend uses completed days only
    hi20, lo20 = dh[done].rolling(20).max().iloc[-1], dl[done].rolling(20).min().iloc[-1]
    sma100 = dc[done].rolling(100).mean().iloc[-1]
    bias = "DOWN" if price < sma100 else "UP"
    L += ["## Tomorrow's prep", "",
          f"- **Daily trend bias: {bias}** (price {'below' if bias == 'DOWN' else 'above'} its 100-day average {sma100:,.2f}).",
          f"- daily_trend triggers: **long** on a 19:00 UTC close above {hi20:,.2f} (and above the 100-day average), "
          f"**short** below {lo20:,.2f} (and below it). Now {price - lo20:+,.2f} from the low trigger, {price - hi20:+,.2f} from the high."]
    macro = ensure_macro()
    if macro is not None and len(macro):
        m = macro.iloc[-1]
        dxy20 = macro["dxy"].pct_change(20).iloc[-1]
        ry20 = macro["DFII10"].diff(20).iloc[-1]
        L.append(f"- Macro ({macro.index[-1]:%d %b}): 10y real yield {m.DFII10:.2f}% ({ry20:+.2f} in 20 days), "
                 f"dollar index {dxy20:+.2%} in 20 days, VIX {m.vix:.1f}. Falling yields and a weaker dollar usually support gold.")
    lv, levels = levels_now(d15, now)
    if len(lv):
        lv = lv.assign(dist=(lv.wick - price).round(2)).sort_values("dist", key=abs)
        L += ["", "**Lines the analyser sees now** (nearest first):", "", "| TF | Kind | Side | Wick line | Body line | Touches | Distance |",
              "|---|---|---|---|---|---|---|"]
        L += [f"| {r.tf} | {r.kind} | {r.side} | {r.wick:,.2f} | {r.body:,.2f} | {r.touches} | {r.dist:+,.2f} |" for r in lv.head(8).itertuples()]
    nxt = day + pd.Timedelta(days=3 if day.dayofweek == 4 else 1)
    nfp = nxt.dayofweek == 4 and nxt.day <= 7
    L += ["", f"**Watch windows ({nxt:%a %d %b}, UTC):** London open 07:00-09:00 (fake-out risk), US data 12:30 / 13:30"
          + (" (**likely NFP day: first Friday**)" if nfp else "") + ", NY open 13:30-14:30, rollover 21:00-22:00 (wide spreads).", ""]

    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / f"{day:%Y-%m-%d}.png"
    chart(d15, levels, now, png)
    L += [f"![H4 lines](https://github.com/{REPO}/blob/main/reports/daily/{png.name}?raw=true)", "",
          "---", "Generated by the paper-trading bot. Simulation with modelled costs; not investment advice."]
    md = OUT / f"{day:%Y-%m-%d}.md"
    md.write_text("\n".join(L) + "\n")
    print(md)


if __name__ == "__main__":
    main()
