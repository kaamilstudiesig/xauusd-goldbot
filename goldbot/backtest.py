"""Bar-by-bar backtester for one-position-at-a-time routes on XAU/USD hourly bid bars.

Signal contract (a DataFrame aligned to the bars, produced by a route):
  side      +1 long / -1 short / 0 none, decided at the bar CLOSE -> filled at the NEXT bar open
  sl_dist   stop distance in $ from entry (required when side != 0)
  tp_dist   target distance in $ (NaN = no target)
  max_bars  time stop in bars (NaN = none)
  trail_atr optional ATR multiple for a trailing stop, fixed in $ at entry (NaN = none)
  force_exit optional bool: close any open position at this bar's close

Fill rules (conservative):
  - prices are bid; longs buy at ask (bid + spread), shorts cover at ask
  - entry slippage on market entries, extra slippage on stop fills
  - if a bar touches both stop and target, the stop is assumed first
  - gaps through the stop fill at the open
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .costs import DEFAULT_COSTS, CostModel


@dataclass
class BTConfig:
    equity0: float = 10_000.0
    risk_pct: float = 0.005        # risk per trade as a fraction of equity
    max_leverage: float = 20.0
    costs: CostModel = field(default_factory=lambda: DEFAULT_COSTS)


def run(df: pd.DataFrame, sig: pd.DataFrame, cfg: BTConfig | None = None, route: str = "") -> tuple[pd.DataFrame, pd.Series]:
    cfg = cfg or BTConfig()
    c = cfg.costs
    o, h, l, cl = (df[k].values for k in ("open", "high", "low", "close"))
    atr = df["atr"].values if "atr" in df else np.full(len(df), np.nan)
    spread = c.spread_series(df)
    side = sig["side"].fillna(0).values.astype(int)
    sl_d = sig["sl_dist"].values
    tp_d = sig["tp_dist"].values if "tp_dist" in sig else np.full(len(df), np.nan)
    mb = sig["max_bars"].values if "max_bars" in sig else np.full(len(df), np.nan)
    tr = sig["trail_atr"].values if "trail_atr" in sig else np.full(len(df), np.nan)
    fx = sig["force_exit"].fillna(False).values.astype(bool) if "force_exit" in sig else np.zeros(len(df), bool)
    idx = df.index
    days = idx.normalize().values

    eq = cfg.equity0
    eq_curve = np.empty(len(df))
    trades = []
    pos = 0
    entry = sl = tp = size = 0.0
    ei = 0
    max_b = np.nan
    trail = np.nan
    risk_usd = 0.0

    def close_pos(j, px, reason):
        nonlocal eq, pos
        pnl = (px - entry) * size * pos - c.commission_rt * size
        nights = int((days[j] - days[ei]) / np.timedelta64(1, "D"))
        if nights > 0:
            rate = c.swap_long_annual if pos > 0 else c.swap_short_annual
            pnl -= entry * size * rate * nights / 365
        eq += pnl
        trades.append((route, idx[ei], idx[j], pos, entry, px, sl0, tp, size, pnl, pnl / risk_usd if risk_usd else 0.0, reason, j - ei))
        pos = 0

    sl0 = 0.0
    for i in range(len(df)):
        # 1) manage open position on bar i
        if pos != 0 and i > ei:
            sp = spread[i]
            if pos > 0:
                if o[i] <= sl:
                    close_pos(i, o[i] - c.slippage_stop, "gap_stop")
                elif l[i] <= sl:
                    close_pos(i, sl - c.slippage_stop, "stop")
                elif not np.isnan(tp) and h[i] >= tp:
                    close_pos(i, tp, "target")
            else:
                if o[i] + sp >= sl:
                    close_pos(i, o[i] + sp + c.slippage_stop, "gap_stop")
                elif h[i] + sp >= sl:
                    close_pos(i, sl + c.slippage_stop, "stop")
                elif not np.isnan(tp) and l[i] + sp <= tp:
                    close_pos(i, tp, "target")
            if pos != 0:
                if fx[i] or (not np.isnan(max_b) and i - ei >= max_b):
                    px = cl[i] if pos > 0 else cl[i] + sp
                    close_pos(i, px, "time" if not fx[i] else "session_end")
                elif not np.isnan(trail):
                    if pos > 0:
                        sl = max(sl, cl[i] - trail)
                    else:
                        sl = min(sl, cl[i] + sp + trail)
        # 2) new entry from signal at bar i close -> fill at bar i+1 open
        if pos == 0 and side[i] != 0 and i + 1 < len(df) and not np.isnan(sl_d[i]) and sl_d[i] > 0:
            j = i + 1
            s = side[i]
            px = o[j] + spread[j] + c.slippage_entry if s > 0 else o[j] - c.slippage_entry
            risk_usd = eq * cfg.risk_pct
            size = min(risk_usd / sl_d[i], eq * cfg.max_leverage / px)
            risk_usd = size * sl_d[i]
            pos, entry, ei = s, px, j
            sl = px - s * sl_d[i]
            sl0 = sl
            tp = px + s * tp_d[i] if not np.isnan(tp_d[i]) else np.nan
            max_b, trail = mb[i], tr[i] * atr[i]
        eq_curve[i] = eq + ((cl[i] - entry) * size * pos if pos != 0 and i >= ei else 0.0)

    if pos != 0:
        close_pos(len(df) - 1, cl[-1], "end")
    cols = ["route", "entry_time", "exit_time", "side", "entry", "exit", "sl", "tp", "size", "pnl", "r", "reason", "bars"]
    return pd.DataFrame(trades, columns=cols), pd.Series(eq_curve, index=idx, name="equity")


def metrics(trades: pd.DataFrame, equity: pd.Series) -> dict:
    if len(trades) == 0:
        return {"trades": 0}
    r = trades["r"]
    wins = trades["pnl"] > 0
    gp, gl = trades.loc[wins, "pnl"].sum(), -trades.loc[~wins, "pnl"].sum()
    daily = equity.resample("D").last().dropna()
    dr = daily.pct_change().dropna()
    years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1e-9)
    dd = (equity / equity.cummax() - 1).min()
    return {
        "trades": int(len(trades)),
        "trades_per_yr": round(len(trades) / years, 1),
        "win_rate": round(wins.mean(), 3),
        "avg_r": round(r.mean(), 3),
        "pf": round(gp / gl, 2) if gl > 0 else np.inf,
        "sharpe": round(dr.mean() / dr.std() * np.sqrt(252), 2) if dr.std() > 0 else 0.0,
        "cagr": round((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1, 4),
        "max_dd": round(dd, 4),
        "total_r": round(r.sum(), 1),
    }
