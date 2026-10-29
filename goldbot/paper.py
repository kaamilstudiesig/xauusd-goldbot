"""Paper trader.

Each run:
 1. collects new completed 15m XAU/USD bars (Twelve Data spot when TWELVEDATA_API_KEY is set, else
    GC=F futures minus the measured basis) into data/live/, see goldbot/live.py
 2. replays every route from the paper start date with exactly the backtest's fill rules, so paper
    and backtest results compare like-for-like:
      - hourly routes (daily_trend, ...) on hourly bars built from the 15m feed
      - zone routes (the 15m zone analyser, e.g. v18) on the 15m bars
 3. journals new signals, newly opened and newly closed trades (closed trades are frozen)
 4. re-scores routes on backtest + paper trades (recent trades weigh more, paper trades x3) and flags
    routes to pause or promote. You decide, by editing config/paper.json.

Nothing here sends orders anywhere. It's a simulation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from . import backtest as bt
from . import live
from .analyser import ZoneAnalyser
from .data import PROC, build_macro, load_macro
from .features import add_core, add_macro
from .journal import connect, dumps, read
from .routes.registry import all_routes
from .scoring import weighted_score

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "paper.json"
CONTEXT_COLS = ["close", "atr", "adx", "rsi", "vol_ratio", "ema50", "ema200", "DFII10", "ry_chg20", "dxy_chg20", "vix_z"]
ZONE_CONTEXT = ["trigger", "level", "structure", "candle", "session", "touches", "er", "bias", "sl_atr"]


def load_cfg() -> dict:
    return json.loads(CFG.read_text())


def zone_variants() -> dict:
    import sys

    sys.path.insert(0, str(ROOT))
    from scripts.zone_variants import ZV

    return ZV


def ensure_macro() -> pd.DataFrame | None:
    f = PROC / "macro_daily.parquet"
    # judged by the data's last date, not file time (CI caches restore files with a fresh mtime)
    fresh = f.exists() and load_macro().index.max() >= pd.Timestamp.now(tz="UTC").normalize() - pd.Timedelta(days=2)
    if not fresh:
        try:
            build_macro()
        except Exception as e:  # FRED / Yahoo hiccup: use what we have
            print("macro refresh failed:", e)
    return load_macro() if f.exists() else None


def spot_check(price: float) -> str:
    """Compare the last bar with a live Twelve Data spot quote when a key is set."""
    key = os.environ.get("TWELVEDATA_API_KEY")
    if not key:
        return ""
    import requests

    try:
        q = requests.get("https://api.twelvedata.com/price", params={"symbol": "XAU/USD", "apikey": key}, timeout=15).json()
        return f"spot={float(q['price']):.2f} last_bar_close={price:.2f}"
    except Exception as e:
        return f"spot check failed: {e}"


def _journal_trades(cur, run_id, name, w, in_portfolio, trades, ctx_for, summary) -> tuple[float, float]:
    """Insert/update trades for one route. Closed trades are frozen. Returns (closed_pnl, open_pnl) for the portfolio."""
    closed = opened = 0.0
    tag = "" if in_portfolio else " [shadow]"
    for _, tr in trades.iterrows():
        is_open = tr.reason == "end"
        key = (name, str(tr.entry_time))
        ex = cur.execute("SELECT status, pnl, exit FROM trades WHERE route=? AND entry_time=?", key).fetchone()
        if ex and ex[0] == "closed":
            if abs(ex[1] - tr.pnl) > 1e-6:
                cur.execute("INSERT INTO discrepancies VALUES (?,?,?,?,?,?)",
                            (pd.Timestamp.now(tz="UTC").isoformat(), name, key[1], "pnl", ex[1], float(tr.pnl)))
            closed += ex[1] if in_portfolio else 0.0
            continue
        status = "open" if is_open else "closed"
        vals = (name, key[1], None if is_open else str(tr.exit_time), int(tr.side), float(tr.entry),
                float(tr.exit), float(tr.sl), None if pd.isna(tr.tp) else float(tr.tp), float(tr.size),
                float(tr.pnl), float(tr.r), "" if is_open else tr.reason, int(tr.bars), status, w, ctx_for(tr))
        side = "LONG" if tr.side > 0 else "SHORT"
        if ex is None:
            cur.execute("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", vals + (run_id, None if is_open else run_id))
            summary["new_trades"].append(f"{name}{tag} {side} @ {tr.entry:.2f} sl {tr.sl:.2f}")
        else:
            cur.execute("""UPDATE trades SET exit_time=?, exit=?, pnl=?, r=?, reason=?, bars=?, status=?, closed_run=?
                           WHERE route=? AND entry_time=?""",
                        (vals[2], vals[5], vals[9], vals[10], vals[11], vals[12], status, None if is_open else run_id) + key)
        if is_open:
            opened += tr.pnl if in_portfolio else 0.0
            summary["open"].append(f"{name}{tag} {side} @ {tr.entry:.2f} sl {tr.sl:.2f} open P&L {tr.pnl:+.2f}")
        else:
            closed += tr.pnl if in_portfolio else 0.0
            summary["closed_trades"].append(f"{name}{tag} {tr.reason} {tr.r:+.2f}R ({tr.pnl:+.2f})")
    return closed, opened


def run_once(note: str = "") -> dict:
    cfg = load_cfg()
    info = live.update()
    d15 = live.bars15(cfg["history_from"])
    raw = live.to_hourly(d15)
    macro = ensure_macro()
    d = add_core(raw)
    d = add_macro(d, macro) if macro is not None else d
    d = d.dropna(subset=["ema200", "atr"])
    start = pd.Timestamp(cfg["paper_start"], tz="UTC")
    alloc = cfg["allocation"]
    con = connect()
    cur = con.cursor()
    last15 = d15.index.max()
    cur.execute("INSERT INTO runs (ts,last_bar,n_bars,data_source,basis,live_check,note) VALUES (?,?,?,?,?,?,?)",
                (pd.Timestamp.now(tz="UTC").isoformat(), str(last15), len(d15), f"{info['source']} (+{info['new_bars']} bars)",
                 info["basis"], spot_check(float(d15["close"].iloc[-1])), note))
    run_id = cur.lastrowid
    summary = {"run_id": run_id, "last_bar": str(last15), "price": round(float(d15["close"].iloc[-1]), 2),
               "data": info, "new_trades": [], "closed_trades": [], "open": []}
    total_closed = total_open = 0.0

    # ---- hourly routes ----
    routes = all_routes()
    for name in list(alloc) + [r for r in cfg.get("shadow", []) if r not in alloc]:
        if name not in routes:
            continue
        w = alloc.get(name, 0.0)
        in_portfolio = w > 0
        sig = routes[name].signals(d)
        sig.loc[sig.index < start, "side"] = 0
        sub = bt.BTConfig(equity0=cfg["equity"] * (w if in_portfolio else 1.0), risk_pct=cfg["risk_pct"])
        trades, _ = bt.run(d, sig, sub, route=name)
        for t, row in sig[sig["side"] != 0].iterrows():
            cur.execute("INSERT OR IGNORE INTO signals VALUES (?,?,?,?,?,?,?)",
                        (name, str(t), int(row.side), float(d.at[t, "close"]), float(row.sl_dist),
                         None if pd.isna(row.tp_dist) else float(row.tp_dist), run_id))

        def ctx_for(tr, d=d):
            b = d.index[d.index.get_loc(tr.entry_time) - 1]
            return dumps({**{c: d.at[b, c] for c in CONTEXT_COLS if c in d}, "hour": b.hour,
                          "spread_model": float(bt.DEFAULT_COSTS.spread_series(d.loc[[tr.entry_time]])[0])})

        c_, o_ = _journal_trades(cur, run_id, name, w, in_portfolio, trades, ctx_for, summary)
        total_closed, total_open = total_closed + c_, total_open + o_

    # ---- 15m zone routes ----
    zv = zone_variants() if cfg.get("zone_routes") else {}
    for name, variant in cfg.get("zone_routes", {}).items():
        w = alloc.get(name, 0.0)
        in_portfolio = w > 0
        z = d15.loc[start - pd.Timedelta(days=45):]
        za = ZoneAnalyser(z, zv[variant])
        sig = za.run(cfg["paper_start"])
        frame = za.signal_frame(sig)
        frame.loc[frame.index < start, "side"] = 0
        zz = z.copy()
        zz["atr"] = za.atr
        sub = bt.BTConfig(equity0=cfg["equity"] * (w if in_portfolio else 1.0), risk_pct=cfg["risk_pct"])
        trades, _ = bt.run(zz, frame, sub, route=name)
        trades = trades[trades.entry_time >= start]
        sig1 = sig.drop_duplicates("bar_time").set_index("bar_time") if len(sig) else pd.DataFrame()
        for t, row in sig1.iterrows():
            cur.execute("INSERT OR IGNORE INTO signals VALUES (?,?,?,?,?,?,?)",
                        (name, str(t), int(row.side), float(row.close), float(row.sl_dist), float(row.tp_dist), run_id))

        def ctx_for(tr, sig1=sig1):
            k = tr.entry_time - live.M15
            r = sig1.loc[k] if len(sig1) and k in sig1.index else {}
            return dumps({c: r[c] for c in ZONE_CONTEXT if c in r})

        c_, o_ = _journal_trades(cur, run_id, name, w, in_portfolio, trades, ctx_for, summary)
        total_closed, total_open = total_closed + c_, total_open + o_

    cur.execute("INSERT OR REPLACE INTO equity VALUES (?,?,?,?,?)",
                (str(last15), cfg["equity"] + total_closed + total_open, total_open, total_closed, run_id))
    con.commit()
    summary["equity"] = round(cfg["equity"] + total_closed + total_open, 2)
    summary["allocation"] = rescore(cfg, run_id, con)
    con.close()
    return summary


def rescore(cfg: dict, run_id: int, con) -> dict:
    """Blend backtest and paper trades with recency weighting; pause routes whose evidence decays."""
    bt_tr = pd.read_parquet(ROOT / "reports" / cfg["backtest_trades"])
    bt_tr["source"] = "backtest"
    bt_tr = bt_tr[bt_tr["exit_time"] < pd.Timestamp(cfg["paper_start"], tz="UTC")]  # no double counting
    pp = pd.read_sql_query("SELECT * FROM trades WHERE status='closed'", con)
    pp["source"] = "paper"
    if len(pp):
        pp["exit_time"] = pd.to_datetime(pp["exit_time"], utc=True)
    out = {}
    names = list(cfg["allocation"]) + [r for r in cfg.get("shadow", []) + list(cfg.get("zone_routes", {})) if r not in cfg["allocation"]]
    for name in names:
        t = pd.concat([bt_tr[bt_tr.route == name][["exit_time", "r", "source"]],
                       pp[pp.route == name][["exit_time", "r", "source"]] if len(pp) else None])
        sc = weighted_score(t, half_life_days=cfg["half_life_days"], paper_mult=cfg["paper_weight"])
        status = "active" if cfg["allocation"].get(name, 0) > 0 else "shadow"
        if status == "active" and sc["w_t"] < cfg["pause_below_t"]:
            status = "flag_pause"  # evidence decayed: surfaced in the report, you decide
        if status == "shadow" and sc["w_t"] >= cfg["promote_above_t"] and sc["w_avg_r"] > 0:
            status = "flag_promote"  # evidence now strong enough to consider adding to the portfolio
        con.execute("INSERT INTO allocation VALUES (?,?,?,?,?,?,?,?)",
                    (pd.Timestamp.now(tz="UTC").isoformat(), name, cfg["allocation"].get(name, 0.0),
                     sc["w_avg_r"], sc["eff_n"], sc["w_t"], status, run_id))
        out[name] = {**sc, "status": status}
    con.commit()
    return out


def report() -> str:
    tr = read("SELECT * FROM trades")
    eq = read("SELECT * FROM equity ORDER BY ts")
    runs = read("SELECT * FROM runs ORDER BY run_id DESC LIMIT 1")
    lines = ["# Paper trading report", ""]
    if len(runs):
        lines.append(f"Last run: {runs.ts[0]} | last bar {runs.last_bar[0]} | basis {runs.basis[0]:.2f} {runs.live_check[0] or ''}")
    if len(eq):
        lines.append(f"Equity: {eq.equity.iloc[-1]:,.2f} (closed {eq.closed_pnl.iloc[-1]:+,.2f}, open {eq.open_pnl.iloc[-1]:+,.2f})")
    al = read("SELECT * FROM allocation WHERE run_id=(SELECT MAX(run_id) FROM allocation)")
    if len(al):
        lines += ["", "## Route status (backtest + paper, recency-weighted)",
                  al[["route", "weight", "w_avg_r", "eff_n", "w_t", "status"]].to_string(index=False)]
    tr["portfolio"] = tr["weight"] > 0
    c = tr[tr.status == "closed"]
    if len(c):
        g = c.groupby(["portfolio", "route"]).agg(trades=("r", "size"), win_rate=("pnl", lambda x: (x > 0).mean()), avg_r=("r", "mean"),
                                   total_r=("r", "sum"), pnl=("pnl", "sum")).round(3)
        lines += ["", "## Closed trades by route", g.to_string()]
    o = tr[tr.status == "open"]
    if len(o):
        lines += ["", "## Open positions", o[["route", "portfolio", "entry_time", "side", "entry", "sl", "tp", "pnl"]].to_string(index=False)]
    lines += ["", f"Total closed trades: {len(c)}. Judge routes after 100+ trades, not after a month."]
    return "\n".join(lines)
