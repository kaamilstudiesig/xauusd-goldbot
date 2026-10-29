"""Turning-point study: WHY gold turns, and whether turns can be predicted in real time.

  .venv/bin/python scripts/turning_points.py            # full run incl. one logged HOLD look
  .venv/bin/python scripts/turning_points.py --no-hold

Writes reports/turning_points_report.md, journal/turning_points.parquet (every pivot + its conditions).
Splits: DEV 2023-2024 (train), VAL Jan-Jul 2025 (choose threshold), HOLD Aug 2025 -> Oct 2026 (once).
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import lightgbm as lgb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from goldbot import backtest as bt, labelling as L, turning_points as T  # noqa: E402

REPORT = ROOT / "reports" / "turning_points_report.md"
LOG = ROOT / "reports" / "turning_points_holdout_log.csv"
PARAMS = dict(objective="binary", learning_rate=0.03, num_leaves=15, min_data_in_leaf=200, feature_fraction=0.7,
              bagging_fraction=0.8, bagging_freq=1, lambda_l2=10.0, verbose=-1, seed=7)
SPLIT = {"dev": ("2023-01-01", "2024-12-31"), "val": ("2025-01-01", "2025-07-31"), "hold": ("2025-08-01", "2026-11-01")}


def sl(df, name):
    s, e = SPLIT[name]
    return df.loc[s:e]


def auc(y, p):
    return round(roc_auc_score(y, p), 3) if y.nunique() == 2 else np.nan


def trade_frame(d, p_up, p_dn, thr_up, thr_dn, atr):
    """Long when the up-turn score clears its threshold (short likewise), London+NY hours only."""
    s = pd.DataFrame({"side": 0, "sl_dist": np.nan, "tp_dist": np.nan, "max_bars": 32.0, "trail_atr": np.nan,
                      "force_exit": (d.index.hour == 20) & (d.index.minute == 45)}, index=d.index)
    hours = (d.index.hour >= 7) & (d.index.hour < 18)
    lo4, hi4 = d["low"].rolling(4).min(), d["high"].rolling(4).max()
    up = hours & (p_up >= thr_up) & (p_up - thr_up >= p_dn - thr_dn)
    dn = hours & (p_dn >= thr_dn) & ~up
    s.loc[up, "side"], s.loc[dn, "side"] = 1, -1
    dist = np.where(up, d["close"] - lo4 + 0.2 * atr, hi4 - d["close"] + 0.2 * atr)
    s["sl_dist"] = np.clip(dist, 0.8 * atr, 3.0 * atr)
    s["tp_dist"] = 2.0 * s["sl_dist"]
    return s


def run_trades(d, frame, atr, start, end):
    dd = d.copy()
    dd["atr"] = atr
    f = frame.copy()
    f.loc[(f.index < start) | (f.index > end), "side"] = 0
    tr, _ = bt.run(dd, f, bt.BTConfig(risk_pct=0.005))
    tr = tr[(tr.entry_time >= start) & (tr.entry_time <= end)]
    return tr


def tstats(tr):
    if not len(tr):
        return {"trades": 0}
    loss = -tr.r[tr.r < 0].sum()
    return {"trades": len(tr), "win": round((tr.r > 0).mean(), 3), "avg_r": round(tr.r.mean(), 3),
            "pf": round(tr.r[tr.r > 0].sum() / loss, 2) if loss > 0 else np.nan, "total_r": round(tr.r.sum(), 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-hold", action="store_true")
    a = ap.parse_args()
    d = L.bars15().loc["2022-11-01":]
    atr = T.atr15(d)
    piv = T.zigzag(d)
    y = T.labels(d, piv)
    X = T.bar_features(d)
    out = ["# Turning points: why gold turns, and can it be predicted?", "",
           f"{len(piv)} real turns (swing >= 3 ATR afterwards) on 15m XAU/USD, {d.index[0]:%Y-%m} -> {d.index[-1]:%Y-%m}. "
           f"{y.y_turn.mean():.1%} of candles are 'near a turn' (within 1 ATR, the turn forming in the window -2..+4 candles).", ""]

    # ---- WHY ----
    why = T.why_table(d, piv, X)
    why.join(piv[["price", "atr", "bars_to_next"]]).to_parquet(ROOT / "journal" / "turning_points.parquet")
    out += ["## 1. Why: conditions at real turns vs ordinary candles", "",
            "Lift = how many times more common the condition is at a real turn than at a random candle. "
            "Most of these are only visible AT the turn candle (a sweep, a wick), so they explain turns, they don't forecast them.", ""]
    for side in ("high", "low"):
        out += [f"### Swing {side}s", "", T.lift(why, X, side).to_string(index=False), ""]
    ses = why.groupby(["session", "type"]).agg(turns=("swing_after_atr", "size"), median_swing_atr=("swing_after_atr", "median")).round(1)
    hours = pd.Series(X.index.hour).map(lambda h: "asia" if h < 7 or h >= 23 else "london" if h < 12 else "ny_overlap" if h < 17 else "late_ny" if h < 21 else "rollover")
    share = (hours.value_counts(normalize=True)).round(3).rename("share_of_all_candles")
    out += ["### By session", "", ses.to_string(), "", share.to_string(), ""]

    # ---- MODELS ----
    feats = list(X.columns)
    dev = sl(X, "dev").index[:-96]  # 1-day embargo before VAL
    out += ["## 2. Can turns be predicted from what's known at the candle?", "",
            "AUC: 0.5 = coin flip, 0.6 = weak but real, 0.7+ = useful.", ""]
    models, rows = {}, []
    for tgt in ("y_turn", "y_up", "y_dn"):
        m = lgb.train(PARAMS, lgb.Dataset(X.loc[dev, feats], y.loc[dev, tgt]), 300)
        models[tgt] = m
        pv = m.predict(sl(X, "val")[feats])
        rows.append({"target": tgt, "base_rate_val": round(sl(y, "val")[tgt].mean(), 3), "AUC_val": auc(sl(y, "val")[tgt], pv)})
    # direction only, among candles that really were near a turn
    t_dev = dev[y.loc[dev, "y_turn"] == 1]
    md = lgb.train(PARAMS, lgb.Dataset(X.loc[t_dev, feats], y.loc[t_dev, "y_up"]), 300)
    tv = sl(y, "val").index[sl(y, "val").y_turn == 1]
    rows.append({"target": "direction (given a turn): up vs down", "base_rate_val": round(y.loc[tv, "y_up"].mean(), 3),
                 "AUC_val": auc(y.loc[tv, "y_up"], md.predict(X.loc[tv, feats]))})
    out += [pd.DataFrame(rows).to_string(index=False), "",
            "Careful: these AUCs are inflated. 'Near a turn' mostly means 'near the recent high/low', which is visible "
            "in real time, but most such candles are NOT turns. The question that matters is the next one.", ""]
    # THE real question: price is at a fresh 16-candle extreme. Does it turn (>= 3 ATR reversal) or continue?
    at_hi = (X["dist_hi16"] <= 0.3)
    at_lo = (X["dist_lo16"] <= 0.3)
    q_rows = []
    for name, mask, tgt in (("at a 4h high: turns down?", at_hi, "y_dn"), ("at a 4h low: turns up?", at_lo, "y_up")):
        tr_idx = dev[mask.loc[dev].values]
        m = lgb.train(PARAMS, lgb.Dataset(X.loc[tr_idx, feats], y.loc[tr_idx, tgt]), 300)
        for per in ("val",) + (() if a.no_hold else ("hold",)):
            idx = sl(X, per).index[mask.loc[sl(X, per).index].values]
            q_rows.append({"question": name, "period": per, "candles": len(idx),
                           "turn_rate": round(y.loc[idx, tgt].mean(), 3), "AUC": auc(y.loc[idx, tgt], m.predict(X.loc[idx, feats]))})
    out += ["### The real question: at a fresh extreme, turn or continue?", "", pd.DataFrame(q_rows).to_string(index=False), ""]
    imp = pd.Series(models["y_turn"].feature_importance("gain"), index=feats).sort_values(ascending=False)
    out += ["What predicts THAT a turn is near (timing model):", "", (imp / imp.sum()).head(12).round(3).to_string(), ""]

    # ---- TRADING TEST ----
    p_up = pd.Series(models["y_up"].predict(X[feats]), index=X.index)
    p_dn = pd.Series(models["y_dn"].predict(X[feats]), index=X.index)
    vs, ve = (pd.Timestamp(x, tz="UTC") for x in SPLIT["val"])
    out += ["## 3. Trading the predictions (after costs, one position at a time)", "",
            "Long when the up-turn score is in its top quantile (short likewise), 07-18 UTC, stop beyond the last 4 candles, "
            "target 2R, max 8h, flat 20:45 UTC. Quantile chosen on VAL.", ""]
    best, vrows = None, []
    for q in (0.95, 0.97, 0.98, 0.99):
        tu, td = p_up.loc[dev].quantile(q), p_dn.loc[dev].quantile(q)
        tr = run_trades(d, trade_frame(d, p_up, p_dn, tu, td, atr), atr, vs, ve)
        st = tstats(tr)
        vrows.append({"quantile": q, **st})
        if st.get("trades", 0) >= 30 and (best is None or st["avg_r"] > best[2]):
            best = (q, (tu, td), st["avg_r"])
    out += ["VAL (Jan-Jul 2025):", "", pd.DataFrame(vrows).to_string(index=False), ""]
    if best and not a.no_hold:
        hs, he = (pd.Timestamp(x, tz="UTC") for x in SPLIT["hold"])
        tu, td = best[1]
        tr = run_trades(d, trade_frame(d, p_up, p_dn, tu, td, atr), atr, hs, he)
        st = tstats(tr)
        ph_turn = models["y_turn"].predict(sl(X, "hold")[feats])
        out += [f"HOLD (Aug 2025 -> Oct 2026), quantile {best[0]} chosen on VAL, run once:", "",
                pd.DataFrame([st]).to_string(index=False), "",
                f"Timing AUC on HOLD: {auc(sl(y, 'hold').y_turn, ph_turn)}", ""]
        if len(tr):
            mon = tr.groupby(tr.entry_time.dt.strftime("%Y-%m")).r.agg(["size", "mean", "sum"]).round(2)
            out += ["By month:", "", mon.to_string(), ""]
        ok = st.get("pf", 0) >= 1.2 and st.get("avg_r", -1) > 0
        out += [f"**Target (PF >= 1.2, avg R > 0): {'MET' if ok else 'NOT MET'}**", ""]
        pd.DataFrame([{"ts": pd.Timestamp.now(tz="UTC").isoformat(), "quantile": best[0], **st, "met": ok}]).to_csv(
            LOG, mode="a", header=not LOG.exists(), index=False)
        out += [f"HOLD looks for this study: {len(pd.read_csv(LOG))} (`{LOG.name}`).", ""]
    REPORT.write_text("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
