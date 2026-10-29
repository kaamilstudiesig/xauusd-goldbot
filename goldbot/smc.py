"""Streaming market-structure tools on 15m bars: swings, BOS, CHoCH, FVG, candle types.

Definitions follow the common ICT/SMC conventions (as implemented in joshyattridge/smart-money-concepts),
but computed incrementally so a value at bar i only uses bars <= i:
  swing high/low  fractal pivot with k bars each side, CONFIRMED k bars later
  BOS             close beyond the last swing in the direction of the current structure
  CHoCH           close beyond the last swing AGAINST the current structure (first sign of a shift)
  FVG             3-candle imbalance: bullish if low[i] > high[i-2]; bearish if high[i] < low[i-2]
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Structure:
    k: int = 2
    trend: int = 0                  # +1 bullish, -1 bearish, 0 unknown
    last_sh: float = np.nan         # last confirmed swing high
    last_sl: float = np.nan
    sh_used: bool = True            # each swing can only be broken once
    sl_used: bool = True
    events: list = field(default_factory=list)  # (i, "BOS"/"CHOCH", +1/-1, level)

    def update(self, i: int, h: np.ndarray, l: np.ndarray, c: np.ndarray):
        """Process bar i. Returns the structure event on this bar, or None."""
        k = self.k
        j = i - k  # the bar that can now be confirmed as a pivot
        if j >= k:
            if h[j] == h[j - k : j + k + 1].max():
                self.last_sh, self.sh_used = h[j], False
            if l[j] == l[j - k : j + k + 1].min():
                self.last_sl, self.sl_used = l[j], False
        ev = None
        if not self.sh_used and c[i] > self.last_sh:
            ev = (i, "BOS" if self.trend >= 0 else "CHOCH", +1, self.last_sh)
            self.trend, self.sh_used = 1, True
        elif not self.sl_used and c[i] < self.last_sl:
            ev = (i, "BOS" if self.trend <= 0 else "CHOCH", -1, self.last_sl)
            self.trend, self.sl_used = -1, True
        if ev:
            self.events.append(ev)
        return ev


def fvg_at(i: int, h: np.ndarray, l: np.ndarray, min_size: float) -> int:
    """+1 bullish FVG completed at bar i, -1 bearish, 0 none."""
    if i < 2:
        return 0
    if l[i] - h[i - 2] > min_size:
        return 1
    if l[i - 2] - h[i] > min_size:
        return -1
    return 0


def candle_type(o: float, h: float, l: float, c: float) -> str:
    rng = h - l
    if rng <= 0:
        return "doji"
    body = abs(c - o)
    up_w = h - max(o, c)
    lo_w = min(o, c) - l
    d = "bull" if c > o else "bear"
    if body / rng >= 0.7:
        return f"{d}_marubozu"          # strong displacement candle
    if body / rng <= 0.15:
        return "doji"
    if up_w >= 2 * body and up_w > lo_w * 2:
        return "shooting_star"          # rejection from above
    if lo_w >= 2 * body and lo_w > up_w * 2:
        return "hammer"                 # rejection from below
    return f"{d}_normal"


def is_strong(o, h, l, c, direction: int, min_body=0.5) -> bool:
    """Close in the direction with a real body (not a wick poke)."""
    rng = h - l
    return rng > 0 and (c - o) * direction > 0 and abs(c - o) / rng >= min_body
