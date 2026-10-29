"""Automatic threshold lines, drawn the way a discretionary gold trader draws them on H1/H4.

For each side (upper/lower) we draw two parallel lines:
  - the WICK line, through (approximately) all recent wick highs / wick lows
  - the BODY line, same slope, through the candle-body highs / lows (max/min of open, close)
The band between them is the threshold ZONE. A horizontal version of the same fit gives the
rectangle BOX (range top and bottom).

Fitting (in the style of the EXCAVO / WillyAlgoTrader channel scripts):
  1. confirmed pivots only (k bars on each side), so nothing repaints
  2. every pair of pivots defines a candidate line; score = pivots touching it within an ATR
     tolerance; reject lines that recent candles have closed through
  3. keep the best-scoring line with >= min_touch touches
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Boundary:
    side: str          # "upper" or "lower"
    kind: str          # "channel" or "box"
    tf: str            # "1h" / "4h"
    tf_hours: float
    slope: float       # $ per TF bar
    wick_end: float    # wick-line value at the close of the last completed TF bar
    body_end: float    # body-line value at the same point
    touches: int
    end_time: object   # close time of last completed TF bar (pd.Timestamp)
    span_bars: int

    def at(self, t_close) -> tuple[float, float]:
        """(wick, body) line values at time `t_close`, extrapolated along the slope."""
        dx = (t_close - self.end_time).total_seconds() / 3600 / self.tf_hours
        return self.wick_end + self.slope * dx, self.body_end + self.slope * dx

    def describe(self) -> str:
        return f"{self.tf} {self.kind} {self.side} wick {self.wick_end:.2f} body {self.body_end:.2f} slope {self.slope:+.2f}/bar touches {self.touches}"


def pivots(x: np.ndarray, k: int, high: bool) -> np.ndarray:
    """Indices of confirmed pivot highs/lows (needs k bars after, so the last k bars never qualify)."""
    n = len(x)
    out = []
    for i in range(k, n - k):
        w = x[i - k : i + k + 1]
        if (high and x[i] == w.max()) or (not high and x[i] == w.min()):
            out.append(i)
    return np.array(out, dtype=int)


def fit(o, h, l, c, atr: float, side: str, horizontal: bool, k: int = 3, tol_atr: float = 0.35,
        min_touch: int = 3, max_pierce: int = 1, max_pivots: int = 14):
    """Best wick line + parallel body line for one side. Returns (slope, wick_end, body_end, touches) or None."""
    n = len(c)
    upper = side == "upper"
    wick = h if upper else l
    body = np.maximum(o, c) if upper else np.minimum(o, c)
    piv = pivots(wick, k, high=upper)[-max_pivots:]
    if len(piv) < 2 or not np.isfinite(atr) or atr <= 0:
        return None
    tol = tol_atr * atr
    x = np.arange(n)
    best = None
    cands = [(a, a) for a in piv] if horizontal else [(a, b) for i, a in enumerate(piv) for b in piv[i + 1 :]]
    for a, b in cands:
        slope = 0.0 if horizontal else (wick[b] - wick[a]) / (b - a)
        if abs(slope) > 1.5 * atr:
            continue
        line = wick[a] + slope * (x - a)
        res = wick[piv] - line[piv]
        touch = piv[np.abs(res) <= tol]
        if len(touch) < min_touch:
            continue
        # closes through the line since the first touch (the line should have held price)
        seg = slice(int(touch.min()), n)
        pierce = np.sum(c[seg] > line[seg] + tol) if upper else np.sum(c[seg] < line[seg] - tol)
        if pierce > max_pierce:
            continue
        # wick line sits on the outermost touching wick; body line is parallel through the touching bodies
        wick_shift = (res[np.isin(piv, touch)].max() if upper else res[np.isin(piv, touch)].min())
        wline = line + wick_shift
        bres = body[touch] - wline[touch]
        bshift = np.median(bres)
        score = (len(touch), b, -abs(slope))
        if best is None or score > best[0]:
            best = (score, slope, wline[-1], wline[-1] + bshift, len(touch), n - a)
    if best is None:
        return None
    return best[1:]


def sr_levels(o, h, l, c, atr: float, k: int = 3, tol_atr: float = 0.35, min_touch: int = 3, per_side: int = 2):
    """Horizontal support/resistance from BOUNCE points: prices where the market turned (swing highs
    AND swing lows together, so a level that was resistance and later support counts both times).
    Returns [(side, wick, body, touches)], nearest levels first. Above price = resistance (upper)."""
    if not np.isfinite(atr) or atr <= 0:
        return []
    tol = tol_atr * atr
    ph, pl = pivots(h, k, True), pivots(l, k, False)
    pts = np.r_[h[ph], l[pl]]
    if len(pts) < min_touch:
        return []
    counts = np.array([(np.abs(pts - p) <= tol).sum() for p in pts])
    order = np.argsort(-counts, kind="stable")
    chosen = []
    for j in order:
        if counts[j] < min_touch:
            break
        cluster = pts[np.abs(pts - pts[j]) <= tol]
        centre = cluster.mean()
        if all(abs(centre - x[0]) > 1.0 * atr for x in chosen):
            chosen.append((centre, cluster))
    last = c[-1]
    out = []
    for side, sel in (("upper", [x for x in chosen if x[0] > last]), ("lower", [x for x in chosen if x[0] < last])):
        sel = sorted(sel, key=lambda x: abs(x[0] - last))[:per_side]
        for centre, cl in sel:
            # zone: outer edge = most extreme turn (wick line), inner edge = typical turn (body line)
            wick = cl.max() if side == "upper" else cl.min()
            body = np.median(cl)
            if abs(wick - body) < 0.2 * atr:
                body = wick - 0.2 * atr if side == "upper" else wick + 0.2 * atr
            out.append((side, float(wick), float(body), len(cl)))
    return out


def boundaries(bars, atr: float, tf: str, tf_hours: float, end_time, lookback: int) -> list[Boundary]:
    """Sloped channel lines, the horizontal box, and horizontal support/resistance (bounce) levels
    from the last `lookback` completed bars. `bars` = dict of numpy arrays o, h, l, c."""
    o, h, l, c = (bars[k][-lookback:] for k in ("o", "h", "l", "c"))
    out = []
    ranks = {"upper": 0, "lower": 0}
    for side, w, b, t in sr_levels(o, h, l, c, atr):
        ranks[side] += 1
        out.append(Boundary(side, f"sr{ranks[side]}", tf, tf_hours, 0.0, w, b, t, end_time, len(c)))
    for kind, horiz in (("channel", False), ("box", True)):
        for side in ("upper", "lower"):
            r = fit(o, h, l, c, atr, side, horiz)
            if r:
                slope, w, b, t, span = r
                out.append(Boundary(side, kind, tf, tf_hours, slope, w, b, t, end_time, span))
    # a channel needs both sides roughly parallel; a box needs both sides and a sane height
    for kind in ("channel", "box"):
        sides = [x for x in out if x.kind == kind]
        if len(sides) == 2:
            up, lo = sorted(sides, key=lambda x: x.side != "upper")
            height = up.wick_end - lo.wick_end
            if height <= 0 or height > 12 * atr:
                out = [x for x in out if x.kind != kind]
    return out
