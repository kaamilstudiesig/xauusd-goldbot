"""LightGBM route with triple-barrier labels and walk-forward retraining (Lopez de Prado,
Advances in Financial Machine Learning, ch. 3 & 7: triple-barrier labels, purging and embargo).

For every bar we ask: if I bought (or sold) at the next open with a 1 ATR stop and a 2 ATR
target, would the target be hit within 24 bars before the stop? Two binary classifiers learn
those probabilities. A trade is taken only when the predicted probability clearly beats the
historical base rate. Retrained every `retrain_bars` on a rolling `train_bars` window, with an
embargo gap so no label overlaps the test period.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..costs import DEFAULT_COSTS
from ..features import asian_range, daily_trend
from .base import Route

FEATS = ["r1", "r3", "r6", "r12", "r24", "r72", "r120", "d_ema20", "d_ema50", "d_ema200", "rsi", "adx",
         "vol_ratio", "bb_pos", "hour_s", "hour_c", "dow", "asia_rng", "atr_pct", "bias",
         "ry_chg20", "dxy_chg20", "be_chg20", "vix_z", "DFII10"]


def make_features(d: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame(index=d.index)
    a = d["atr"]
    for k in (1, 3, 6, 12, 24, 72, 120):
        f[f"r{k}"] = (d["close"] - d["close"].shift(k)) / a
    for e in ("ema20", "ema50", "ema200"):
        f[f"d_{e}"] = (d["close"] - d[e]) / a
    f["rsi"], f["adx"], f["vol_ratio"] = d["rsi"], d["adx"], d["vol_ratio"]
    f["bb_pos"] = (d["close"] - d["bb_mid"]) / (d["bb_up"] - d["bb_mid"])
    f["hour_s"] = np.sin(2 * np.pi * d.index.hour / 24)
    f["hour_c"] = np.cos(2 * np.pi * d.index.hour / 24)
    f["dow"] = d.index.dayofweek
    ar = asian_range(d)
    f["asia_rng"] = ((ar["asia_hi"] - ar["asia_lo"]) / a).ffill()
    f["atr_pct"] = a / d["close"]
    f["bias"] = daily_trend(d)
    for m in ("ry_chg20", "dxy_chg20", "be_chg20", "vix_z", "DFII10"):
        f[m] = d[m] if m in d else np.nan
    return f


def barrier_labels(d: pd.DataFrame, sl_atr=1.0, tp_atr=2.0, horizon=24) -> tuple[np.ndarray, np.ndarray]:
    """1 if the target is hit before the stop within `horizon` bars, else 0. NaN near the end."""
    n = len(d)
    o, h, l = d["open"].values, d["high"].values, d["low"].values
    atr = d["atr"].values
    sp = DEFAULT_COSTS.spread_series(d)
    H = horizon
    idx = np.arange(n)[:, None] + 1 + np.arange(H)[None, :]  # bars i+1 .. i+H
    valid = idx[:, -1] < n
    idx = np.clip(idx, 0, n - 1)
    hh, ll = h[idx], l[idx]
    ent = np.r_[o[1:], np.nan]
    # long
    el = ent + np.r_[sp[1:], np.nan]
    tp_l, sl_l = el + tp_atr * atr, el - sl_atr * atr
    hit_tp = hh >= tp_l[:, None]
    hit_sl = ll <= sl_l[:, None]
    first = lambda m: np.where(m.any(1), m.argmax(1), H + 1)
    long_y = (first(hit_tp) < first(hit_sl)).astype(float)
    # short (exit at ask = bid + spread)
    tp_s, sl_s = ent - tp_atr * atr, ent + sl_atr * atr
    hit_tp = (ll + sp[idx]) <= tp_s[:, None]
    hit_sl = (hh + sp[idx]) >= sl_s[:, None]
    short_y = (first(hit_tp) < first(hit_sl)).astype(float)
    long_y[~valid], short_y[~valid] = np.nan, np.nan
    return long_y, short_y


class LGBMBarrier(Route):
    name = "ml_lgbm"
    family = "ml"
    thesis = ("Combine price, session and macro features non-linearly; let the model learn when a "
              "2:1 trade has better-than-base odds. Purged walk-forward keeps it honest.")
    params = {"train_bars": 24 * 260 * 3, "retrain_bars": 24 * 130, "embargo": 48, "edge": 0.06,
              "sl_atr": 1.0, "tp_atr": 2.0, "horizon": 24, "hours": (7, 20), "start": "2012-01-01"}

    def signals(self, d):
        import lightgbm as lgb

        s = self.empty(d)
        X = make_features(d)
        yl, ys = barrier_labels(d, self.p["sl_atr"], self.p["tp_atr"], self.p["horizon"])
        prob_l = pd.Series(np.nan, index=d.index)
        prob_s = pd.Series(np.nan, index=d.index)
        base_l = pd.Series(np.nan, index=d.index)
        base_s = pd.Series(np.nan, index=d.index)
        n = len(d)
        start = max(int(np.searchsorted(d.index, pd.Timestamp(self.p["start"], tz="UTC"))), self.p["train_bars"])
        tb, rb, emb = self.p["train_bars"], self.p["retrain_bars"], self.p["embargo"]
        params = dict(objective="binary", learning_rate=0.03, num_leaves=15, min_data_in_leaf=200,
                      feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=5.0, verbose=-1)
        Xv = X[FEATS].values
        for t0 in range(start, n, rb):
            tr = slice(max(0, t0 - tb), t0 - emb)
            te = slice(t0, min(n, t0 + rb))
            for y, prob, base in ((yl, prob_l, base_l), (ys, prob_s, base_s)):
                ytr = y[tr]
                m = ~np.isnan(ytr)
                if m.sum() < 1000:
                    continue
                mdl = lgb.train(params, lgb.Dataset(Xv[tr][m], ytr[m]), num_boost_round=200)
                prob.iloc[te] = mdl.predict(Xv[te])
                base.iloc[te] = ytr[m].mean()
        self.last_probs = pd.DataFrame({"p_long": prob_l, "p_short": prob_s, "base_l": base_l, "base_s": base_s})
        h = d.index.hour
        hours = (h >= self.p["hours"][0]) & (h < self.p["hours"][1])
        e = self.p["edge"]
        long_ = hours & (prob_l > base_l + e) & (prob_l >= prob_s)
        short = hours & (prob_s > base_s + e) & (prob_s > prob_l)
        s.loc[long_, "side"] = 1
        s.loc[short, "side"] = -1
        s["sl_dist"] = self.p["sl_atr"] * d["atr"]
        s["tp_dist"] = self.p["tp_atr"] * d["atr"]
        s["max_bars"] = self.p["horizon"]
        return s
