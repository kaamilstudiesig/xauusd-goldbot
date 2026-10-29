"""Zone analyser + triggers: the trader's process, automated and streamed bar by bar.

1. THRESHOLDS: every time an H1 bar completes, redraw wick/body lines (sloped channel and horizontal
   box) from recent completed H1 and H4 bars (goldbot.levels).
2. WATCH: on every completed 15m bar, check where price is relative to each threshold zone.
3. TRIGGERS
   BREAKOUT  a 15m candle CLOSES beyond the wick line (fresh cross, with buffer).
             confirm="smc": the closing candle must be a real body (>=50% of range) or print a BOS.
             Entry next 15m open; stop beyond the breakout candle / body line; target rr x risk.
   REJECTION price trades into the zone (reaches the body line) but no 15m close beyond the wick line;
             within `rev_window` bars a CHoCH/BOS forms against the approach.
             confirm="smc": also needs an FVG in the reversal direction within the last 3 bars.
             confirm="none": a rejection candle (hammer/shooting star/opposite marubozu) is enough.
             Stop beyond the extreme reached in the zone; target rr x risk.
4. Session filter (default 07:00-20:00 UTC), one signal per side per cooldown, flat by 20:45 UTC.

The analyser only ever reads bars up to the one it is processing. tests/test_no_lookahead.py checks that.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .levels import Boundary, boundaries
from .smc import Structure, candle_type, fvg_at, is_strong

M15 = pd.Timedelta(minutes=15)


def session_name(hour: int) -> str:
    if hour < 7 or hour >= 23:
        return "asia"
    if hour < 12:
        return "london"
    if hour < 17:
        return "ny_overlap"
    if hour < 21:
        return "late_ny"
    return "rollover"


def _ohlc_tf(d15: pd.DataFrame, rule: str) -> pd.DataFrame:
    x = d15.resample(rule, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    pc = x["close"].shift()
    tr = pd.concat([x["high"] - x["low"], (x["high"] - pc).abs(), (x["low"] - pc).abs()], axis=1).max(axis=1)
    x["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    x["close_time"] = x.index + pd.Timedelta(rule)
    return x


@dataclass
class ZoneParams:
    mode: str = "both"           # "both" | "breakout" | "rejection"
    confirm: str = "smc"         # "smc" | "none"
    rr: float = 2.0
    tfs: tuple = (("1h", 72), ("4h", 60))
    kinds: tuple = ("channel", "box", "sr1", "sr2")
    session: tuple = (7, 18)       # new entries 07:00-17:59 UTC (London + NY overlap)
    buffer_atr: float = 0.10
    rev_window: int = 16
    cooldown: int = 8
    min_sl_atr: float = 0.8
    max_sl_atr: float = 3.0
    max_bars: int = 32
    flat_hour: int = 20          # force exit on the 20:45 bar close
    triggers: tuple = ()         # explicit trigger set; empty = derived from `mode`
    retest_window: int = 12      # bars after a breakout in which a retest entry is allowed
    sweep_window: int = 4        # bars after a breakout in which a close back inside = fake-out
    # ---- refinements (defaults = original behaviour) ----
    bias: str = "none"           # "none" | "sma" (daily close vs SMA of completed days) | "donchian"
    bias_days: int = 50          # SMA / channel length in days for the daily bias
    bias_mode: str = "with"      # "with" = only trade with the daily bias; "against" = only against it
    min_touches: int = 0         # level must have >= this many touches
    skip_candles: tuple = ()     # trigger-bar candle types to skip (e.g. ("bull_marubozu", "bear_marubozu"))
    skip_hours: tuple = ()       # UTC entry hours to skip
    stop_mode: str = "candle"    # "candle" (breakout candle / body line) | "swing" (beyond last 15m swing) | "atr"
    stop_atr: float = 1.5        # stop distance for stop_mode="atr"
    shock_x: float = 0.0         # >0: skip entries for shock_bars after a 15m bar with range > shock_x * median range
    shock_bars: int = 8
    be_r: float = float("nan")   # move stop to entry once price has gone be_r * risk in favour (NaN = off)
    days_ok: tuple = (0, 1, 2, 3, 4)  # weekdays allowed for entries
    trail_atr: float = float("nan")    # trailing stop in 15m ATR at entry (NaN = off)
    weekend_flat: bool = True          # with flat_hour=-1: still close everything Friday 20:45 UTC
    er_days: int = 20                  # Kaufman efficiency ratio of completed daily closes (trend strength)
    er_min: float = 0.0                # >0: only enter when ER >= er_min (skip sideways regimes)


class ZoneAnalyser:
    def __init__(self, d15: pd.DataFrame, params: ZoneParams | None = None):
        self.p = params or ZoneParams()
        self.d = d15
        self.o, self.h, self.l, self.c = (d15[k].values for k in ("open", "high", "low", "close"))
        pc = np.r_[np.nan, self.c[:-1]]
        tr = np.nanmax(np.vstack([self.h - self.l, np.abs(self.h - pc), np.abs(self.l - pc)]), axis=0)
        self.atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().values  # causal
        self.t = d15.index
        self.tf = {name: _ohlc_tf(d15, name) for name, _ in self.p.tfs}
        self.struct = Structure(k=2)
        self.bias = self._daily_bias(self.p.bias, self.p.bias_days)
        self.bias_ctx = self._daily_bias("sma", 50)      # always journaled, even when not filtering
        self.bias_ctx20 = self._daily_bias("donchian", 20)
        self.er = self._daily_er(self.p.er_days)
        rng = pd.Series(self.h - self.l, index=d15.index)
        med = rng.rolling(200, min_periods=20).median().values  # causal (includes bar i)
        self.shock = (self.h - self.l) > (self.p.shock_x * med if self.p.shock_x > 0 else np.inf)
        self.last_shock = -10**9
        self.levels: list[Boundary] = []
        self.last_refresh = None
        self.touch: dict = {}       # key -> (start_i, extreme)
        self.last_fire: dict = {}
        self.prev_line: dict = {}
        self.signals: list = []
        self.pending: dict = {}     # key -> breakout awaiting retest / fake-out check
        modes = {"both": {"breakout", "rejection"}, "breakout": {"breakout"}, "rejection": {"rejection"}}
        self.trig = set(self.p.triggers) if self.p.triggers else modes[self.p.mode]

    def _daily_bias(self, kind: str, days: int) -> np.ndarray:
        """+1/-1/0 per 15m bar from COMPLETED UTC days only (day D uses closes up to D-1)."""
        if kind == "none":
            return np.zeros(len(self.d))
        day = self.d.index.normalize()
        dc = self.d["close"].groupby(day).last()
        if kind == "sma":
            b = np.sign(dc - dc.rolling(days).mean())
        elif kind == "donchian":  # +1 after a close above the N-day high until a close below the N-day low
            hi = self.d["high"].groupby(day).max().rolling(days).max().shift(1)
            lo = self.d["low"].groupby(day).min().rolling(days).min().shift(1)
            raw = pd.Series(np.where(dc > hi, 1.0, np.where(dc < lo, -1.0, np.nan)), index=dc.index)
            b = raw.ffill().fillna(0)
        else:
            raise ValueError(kind)
        b = b.shift(1).fillna(0)  # previous completed day
        return b.reindex(day).values

    def _daily_er(self, n: int) -> np.ndarray:
        """Efficiency ratio |C[D-1]-C[D-1-n]| / sum|dC| over the n completed days before day D (0..1)."""
        day = self.d.index.normalize()
        dc = self.d["close"].groupby(day).last()
        er = (dc - dc.shift(n)).abs() / dc.diff().abs().rolling(n).sum()
        return er.shift(1).reindex(day).fillna(0).values

    # ---- thresholds -------------------------------------------------------------------------
    def refresh_levels(self, tc: pd.Timestamp):
        lv = []
        for name, lookback in self.p.tfs:
            x = self.tf[name]
            n = int(np.searchsorted(x["close_time"].values, tc.to_datetime64(), side="right"))  # completed bars
            if n < 30:
                continue
            sub = x.iloc[max(0, n - lookback) : n]
            bars = {"o": sub["open"].values, "h": sub["high"].values, "l": sub["low"].values, "c": sub["close"].values}
            hours = pd.Timedelta(name).total_seconds() / 3600
            lv += [b for b in boundaries(bars, float(sub["atr"].iloc[-1]), name, hours, sub["close_time"].iloc[-1], lookback)
                   if b.kind in self.p.kinds and b.touches >= self.p.min_touches]
        self.levels = lv

    # ---- per bar ----------------------------------------------------------------------------
    def step(self, i: int):
        p = self.p
        t = self.t[i]
        tc = t + M15
        o, h, l, c, atr = self.o, self.h, self.l, self.c, self.atr[i]
        ev = self.struct.update(i, h, l, c)
        if self.shock[i]:
            self.last_shock = i
        hour_mark = tc.floor("1h")
        if self.last_refresh is None or hour_mark > self.last_refresh:
            self.refresh_levels(tc)
            self.last_refresh = hour_mark
        if i < 3 or not np.isfinite(atr):
            return
        in_session = (p.session[0] <= t.hour < p.session[1] and not (t.dayofweek == 4 and t.hour >= 18)
                      and t.hour not in p.skip_hours and t.dayofweek in p.days_ok
                      and i - self.last_shock >= p.shock_bars)
        fvg_recent = [fvg_at(j, h, l, 0.1 * atr) for j in range(i - 2, i + 1)]
        ctype = candle_type(o[i], h[i], l[i], c[i])
        buf = p.buffer_atr * atr
        self._pending_step(i, tc, buf, in_session, ev, fvg_recent, ctype)
        for b in self.levels:
            key = (b.tf, b.kind, b.side)
            wick, body = b.at(tc)
            prev_wick = self.prev_line.get(key, b.at(tc - M15)[0])
            self.prev_line[key] = wick
            up = b.side == "upper"
            s = 1 if up else -1                      # breakout direction
            beyond = (c[i] - wick) * s > buf
            was_inside = (c[i - 1] - prev_wick) * s <= buf
            if beyond and was_inside and key not in self.pending:
                self.pending[key] = {"i": i, "s": s, "b": b, "ext": h[i] if up else l[i]}
            # BREAKOUT
            if "breakout" in self.trig and in_session and beyond and was_inside:
                ok = True if p.confirm == "none" else (is_strong(o[i], h[i], l[i], c[i], s) or (ev is not None and ev[2] == s))
                if ok:
                    stop = self._stop(i, s, min(l[i], body - buf) if up else max(h[i], body + buf), buf)
                    self._emit(i, s, abs(c[i] - stop), "breakout", b, wick, body, ev, fvg_recent, ctype)
                self.touch.pop(key, None)
                continue
            if beyond and was_inside:
                self.touch.pop(key, None)
                continue
            # REJECTION: track touches of the zone
            reached = (h[i] >= body) if up else (l[i] <= body)
            if reached and not beyond:
                st, ext = self.touch.get(key, (i, h[i] if up else l[i]))
                self.touch[key] = (st, max(ext, h[i]) if up else min(ext, l[i]))
            if key in self.touch:
                st, ext = self.touch[key]
                if i - st > p.rev_window or beyond:
                    self.touch.pop(key, None)
                    continue
                if "rejection" in self.trig and in_session:
                    want = -s
                    shift = ev is not None and ev[2] == want
                    if p.confirm == "smc":
                        ok = shift and (want in fvg_recent)
                    else:
                        rej = ctype in (("shooting_star", "bear_marubozu") if up else ("hammer", "bull_marubozu"))
                        ok = shift or rej
                    if ok:
                        stop = self._stop(i, want, ext + buf if up else ext - buf, buf)
                        self._emit(i, want, abs(c[i] - stop), "rejection", b, wick, body, ev, fvg_recent, ctype)
                        self.touch.pop(key, None)

    def _pending_step(self, i, tc, buf, in_session, ev, fvg_recent, ctype):
        """Follow-up on recent breakouts: RETEST of the broken line, or SWEEP (fake-out) back inside."""
        p, o, h, l, c = self.p, self.o, self.h, self.l, self.c
        for key in list(self.pending):
            pd_ = self.pending[key]
            if i <= pd_["i"]:
                continue
            b, s, age = pd_["b"], pd_["s"], i - pd_["i"]
            up = s > 0
            wick, body = b.at(tc)
            pd_["ext"] = max(pd_["ext"], h[i]) if up else min(pd_["ext"], l[i])
            if (c[i] - wick) * s < -buf:  # closed back inside the wick line -> breakout failed
                if "sweep" in self.trig and in_session and age <= p.sweep_window:
                    stop = self._stop(i, -s, pd_["ext"] + s * buf, buf)
                    self._emit(i, -s, abs(c[i] - stop), "sweep", b, wick, body, ev, fvg_recent, ctype)
                del self.pending[key]
                continue
            if age > max(p.retest_window, p.sweep_window):
                del self.pending[key]
                continue
            if "retest" in self.trig and in_session and age <= p.retest_window:
                touched = (l[i] <= wick + buf) if up else (h[i] >= wick - buf)
                held = (c[i] - wick) * s > 0 and (c[i] - o[i]) * s > 0
                if touched and held:
                    stop = self._stop(i, s, min(l[i], body - buf) if up else max(h[i], body + buf), buf)
                    self._emit(i, s, abs(c[i] - stop), "retest", b, wick, body, ev, fvg_recent, ctype)
                    del self.pending[key]

    def _stop(self, i, side, default, buf):
        """Stop price for a trade in direction `side`. "swing": beyond the last confirmed 15m swing
        on the far side (falls back to `default` if that swing is on the wrong side of price)."""
        p = self.p
        if p.stop_mode == "candle":
            return default
        if p.stop_mode == "atr":
            return self.c[i] - side * p.stop_atr * self.atr[i]
        if p.stop_mode == "swing":
            sw = self.struct.last_sl if side > 0 else self.struct.last_sh
            if np.isfinite(sw) and (self.c[i] - sw) * side > 0:
                far = sw - side * buf
                return min(far, default) if side > 0 else max(far, default)
            return default
        raise ValueError(p.stop_mode)

    def _emit(self, i, side, sl_dist, trig, b: Boundary, wick, body, ev, fvg_recent, ctype):
        p = self.p
        atr = self.atr[i]
        if ctype in p.skip_candles or self.er[i] < p.er_min:
            return
        bias = self.bias[i]
        if p.bias != "none":
            if p.bias_mode == "with" and bias != side:
                return
            if p.bias_mode == "against" and bias != -side:
                return
        sl_dist = float(np.clip(sl_dist, p.min_sl_atr * atr, p.max_sl_atr * atr))
        key = (trig, b.side)
        if i - self.last_fire.get(key, -10**9) < p.cooldown:
            return
        self.last_fire[key] = i
        self.signals.append({
            "bar_time": self.t[i], "i": i, "side": side, "sl_dist": sl_dist, "tp_dist": p.rr * sl_dist,
            "trigger": trig, "level": b.describe(), "tf": b.tf, "kind": b.kind, "level_side": b.side,
            "wick": round(wick, 2), "body": round(body, 2), "close": round(float(self.c[i]), 2),
            "structure": f"{ev[1]} {'bull' if ev[2] > 0 else 'bear'} @ {ev[3]:.2f}" if ev else "",
            "fvg_last3": ",".join(str(x) for x in fvg_recent), "candle": ctype,
            "session": session_name(self.t[i].hour), "atr15": round(float(atr), 2),
            "er": round(float(self.er[i]), 3), "touches": b.touches, "bias": int(self.bias_ctx[i] * side), "dbias": int(self.bias_ctx20[i] * side),
            "hour": self.t[i].hour,
            "body_frac": round(abs(self.c[i] - self.o[i]) / max(self.h[i] - self.l[i], 1e-9), 2),
            "sl_atr": round(sl_dist / atr, 2),
        })

    # ---- run --------------------------------------------------------------------------------
    def run(self, start=None, end=None) -> pd.DataFrame:
        i0 = 0 if start is None else int(np.searchsorted(self.t, pd.Timestamp(start, tz="UTC")))
        i1 = len(self.t) if end is None else int(np.searchsorted(self.t, pd.Timestamp(end, tz="UTC")))
        # warm up structure on the bars before the test window (still causal)
        for i in range(max(0, i0 - 400), i1):
            if i < i0:
                self.struct.update(i, self.h, self.l, self.c)
                continue
            self.step(i)
        return pd.DataFrame(self.signals)

    def signal_frame(self, sig: pd.DataFrame) -> pd.DataFrame:
        """Convert emitted signals to the backtester's signal contract."""
        s = pd.DataFrame({"side": 0, "sl_dist": np.nan, "tp_dist": np.nan, "max_bars": float(self.p.max_bars),
                          "trail_atr": self.p.trail_atr, "force_exit": False, "be_r": self.p.be_r}, index=self.d.index)
        if len(sig):
            sig = sig.drop_duplicates("bar_time")  # one order per bar (first level that fired)
            s.loc[sig["bar_time"], ["side", "sl_dist", "tp_dist"]] = sig[["side", "sl_dist", "tp_dist"]].values
        idx = self.d.index
        s["force_exit"] = (idx.hour == self.p.flat_hour) & (idx.minute == 45)
        if self.p.weekend_flat:
            s["force_exit"] |= (idx.dayofweek == 4) & (idx.hour == 20) & (idx.minute == 45)
        return s
