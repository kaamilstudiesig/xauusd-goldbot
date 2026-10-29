"""Paper trader.

Each run:
 1. refreshes recent XAU/USD bars (GC=F futures minus the latest spot basis), using completed bars only
 2. replays every active route from the paper start date with exactly the backtest's fill rules,
    so paper and backtest results can be compared like-for-like
 3. journals new signals, newly opened and newly closed trades (closed trades are frozen)
 4. re-scores routes on backtest + paper trades (recent trades weigh more, paper trades x3)
    and updates the allocation; routes that decay get paused automatically

Nothing here sends orders anywhere. It's a simulation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from . import backtest as bt
from .data import PROC, fetch_futures, load_macro
from .features import add_core, add_macro
from .journal import connect, dumps, read
from .routes.registry import all_routes
from .scoring import weighted_score

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "paper.json"
CONTEXT_COLS = ["close", "atr", "adx", "rsi", "vol_ratio", "ema50", "ema200", "DFII10", "ry_chg20", "dxy_chg20", "vix_z"]


def load_cfg() -> dict:
    return json.loads(CFG.read_text())


def latest_basis() -> float:
    b = pd.read_parquet(PROC / "basis_daily.parquet")["basis"]
    return float(b.iloc[-1])


def spot_check(price_proxy: float) -> str:
    """Optional: compare the proxy with a real spot quote if a Twelve Data key is set (TWELVEDATA_API_KEY)."""
    key = os.environ.get("TWELVEDATA_API_KEY")
    if not key:
        return ""
    import requests

    try:
        q = requests.get("https://api.twelvedata.com/price", params={"symbol": "XAU/USD", "apikey": key}, timeout=15).json()
        spot = float(q["price"])
        return f"spot={spot:.2f} proxy={price_proxy:.2f} diff={price_proxy - spot:+.2f}"
    except Exception as e:  # network problems shouldn't stop the run
        return f"spot check failed: {e}"


def recent_bars(cfg: dict) -> tuple[pd.DataFrame, float]:
    """History up to the stored dataset + fresh futures-proxy bars; only completed bars."""
    hist = pd.read_parquet(PROC / "xauusd_1h.parquet")
    fut = fetch_futures(period="60d", interval="1h")
    basis = latest_basis()
    fut[["open", "high", "low", "close"]] = fut[["open", "high", "low", "close"]] - basis
    fut["src"] = "gcf_proxy_live"
    new = fut[fut.index > hist.index.max()]
    d = pd.concat([hist, new]).sort_index()
    now = pd.Timestamp.now(tz="UTC")
    d = d[d.index + pd.Timedelta(hours=1) <= now]  # drop the bar still forming
    return d.loc[cfg["history_from"]:], basis


def run_once(note: str = "") -> dict:
    cfg = load_cfg()
    raw, basis = recent_bars(cfg)
    d = add_macro(add_core(raw), load_macro()).dropna(subset=["ema200", "atr"])
    start = pd.Timestamp(cfg["paper_start"], tz="UTC")
    routes = all_routes()
    alloc = cfg["allocation"]
    con = connect()
    cur = con.cursor()
    live = spot_check(float(d["close"].iloc[-1]))
    cur.execute("INSERT INTO runs (ts,last_bar,n_bars,data_source,basis,live_check,note) VALUES (?,?,?,?,?,?,?)",
                (pd.Timestamp.now(tz="UTC").isoformat(), str(d.index[-1]), len(d), "GC=F-basis", basis, live, note))
    run_id = cur.lastrowid
    summary = {"run_id": run_id, "last_bar": str(d.index[-1]), "price": round(float(d["close"].iloc[-1]), 2),
               "new_trades": [], "closed_trades": [], "open": []}
    total_closed = total_open = 0.0
    shadow = [r for r in cfg.get("shadow", []) if r not in alloc]
    for name in list(alloc) + shadow:
        w = alloc.get(name, 0.0)
        if name not in routes:
            continue
        in_portfolio = w > 0
        sig = routes[name].signals(d)
        sig.loc[sig.index < start, "side"] = 0
        # portfolio routes get their share of capital; shadow routes run on a full-size notional account
        sub = bt.BTConfig(equity0=cfg["equity"] * (w if in_portfolio else 1.0), risk_pct=cfg["risk_pct"])
        trades, eq = bt.run(d, sig, sub, route=name)
        # signals log
        for t, row in sig[sig["side"] != 0].iterrows():
            cur.execute("INSERT OR IGNORE INTO signals VALUES (?,?,?,?,?,?,?)",
                        (name, str(t), int(row.side), float(d.at[t, "close"]), float(row.sl_dist),
                         None if pd.isna(row.tp_dist) else float(row.tp_dist), run_id))
        last = d.index[-1]
        for _, tr in trades.iterrows():
            is_open = tr.reason == "end"
            key = (name, str(tr.entry_time))
            ex = cur.execute("SELECT status, pnl, exit FROM trades WHERE route=? AND entry_time=?", key).fetchone()
            ctx_bar = d.index[d.index.get_loc(tr.entry_time) - 1]
            ctx = dumps({**{c: d.at[ctx_bar, c] for c in CONTEXT_COLS if c in d}, "hour": ctx_bar.hour,
                         "spread_model": float(bt.DEFAULT_COSTS.spread_series(d.loc[[tr.entry_time]])[0])})
            if ex and ex[0] == "closed":
                if abs(ex[1] - tr.pnl) > 1e-6:
                    cur.execute("INSERT INTO discrepancies VALUES (?,?,?,?,?,?)",
                                (pd.Timestamp.now(tz="UTC").isoformat(), name, key[1], "pnl", ex[1], float(tr.pnl)))
                total_closed += ex[1] if in_portfolio else 0.0
                continue
            status = "open" if is_open else "closed"
            vals = (name, key[1], None if is_open else str(tr.exit_time), int(tr.side), float(tr.entry),
                    float(tr.exit), float(tr.sl), None if pd.isna(tr.tp) else float(tr.tp), float(tr.size),
                    float(tr.pnl), float(tr.r), "" if is_open else tr.reason, int(tr.bars), status, w, ctx)
            if ex is None:
                cur.execute("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", vals + (run_id, None if is_open else run_id))
                summary["new_trades"].append(f"{name} {'LONG' if tr.side > 0 else 'SHORT'} @ {tr.entry:.2f} sl {tr.sl:.2f}")
            else:
                cur.execute("""UPDATE trades SET exit_time=?, exit=?, pnl=?, r=?, reason=?, bars=?, status=?, closed_run=?
                               WHERE route=? AND entry_time=?""",
                            (vals[2], vals[5], vals[9], vals[10], vals[11], vals[12], status, None if is_open else run_id) + key)
            tag = "" if in_portfolio else " [shadow]"
            if is_open:
                total_open += tr.pnl if in_portfolio else 0.0
                summary["open"].append(f"{name}{tag} {'LONG' if tr.side > 0 else 'SHORT'} @ {tr.entry:.2f} sl {tr.sl:.2f} open P&L {tr.pnl:+.2f}")
            else:
                total_closed += tr.pnl if in_portfolio else 0.0
                summary["closed_trades"].append(f"{name}{tag} {tr.reason} {tr.r:+.2f}R ({tr.pnl:+.2f})")
    cur.execute("INSERT OR REPLACE INTO equity VALUES (?,?,?,?,?)",
                (str(d.index[-1]), cfg["equity"] + total_closed + total_open, total_open, total_closed, run_id))
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
    for name in list(cfg["allocation"]) + [r for r in cfg.get("shadow", []) if r not in cfg["allocation"]]:
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
