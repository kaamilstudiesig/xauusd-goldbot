"""Recency-weighted scoring: recent trades count more than old ones (half-life in days).
Paper-trade results can be given an extra weight multiplier so live-ish evidence dominates."""
from __future__ import annotations

import numpy as np
import pandas as pd


def recency_weights(times: pd.Series, half_life_days: float = 365.0, now: pd.Timestamp | None = None) -> np.ndarray:
    now = now or pd.Timestamp.now(tz="UTC")
    age = (now - pd.to_datetime(times, utc=True)).dt.total_seconds() / 86400
    return 0.5 ** (age.values / half_life_days)


def weighted_score(trades: pd.DataFrame, half_life_days: float = 365.0, paper_mult: float = 3.0) -> dict:
    """Weighted mean R, effective sample size and a weighted t-stat."""
    if len(trades) == 0:
        return {"w_avg_r": 0.0, "eff_n": 0.0, "w_t": 0.0}
    w = recency_weights(trades["exit_time"], half_life_days)
    if "source" in trades:
        w = w * np.where(trades["source"].values == "paper", paper_mult, 1.0)
    r = trades["r"].values
    mu = np.sum(w * r) / w.sum()
    var = np.sum(w * (r - mu) ** 2) / w.sum()
    eff_n = w.sum() ** 2 / np.sum(w ** 2)
    t = mu / np.sqrt(var / eff_n) if var > 0 else 0.0
    return {"w_avg_r": round(float(mu), 3), "eff_n": round(float(eff_n), 1), "w_t": round(float(t), 2)}


def allocate(scores: dict[str, dict], min_t: float = 1.5, min_eff_n: float = 30, cap: float = 0.5) -> dict[str, float]:
    """Risk share per route: positive, statistically supported routes only, proportional to t-stat."""
    raw = {k: v["w_t"] for k, v in scores.items() if v["w_t"] >= min_t and v["eff_n"] >= min_eff_n and v["w_avg_r"] > 0}
    if not raw:
        return {}
    tot = sum(raw.values())
    w = {k: min(cap, v / tot) for k, v in raw.items()}
    tot = sum(w.values())
    return {k: round(v / tot, 3) for k, v in w.items()}
