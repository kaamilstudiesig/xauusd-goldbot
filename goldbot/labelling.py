"""Labelling support: blind charts, the label store, and model features.

A chart shows ONLY what existed at the close of the signal candle: past H1 and 15m candles and the
lines exactly as the analyser drew them then. No future candles, no outcome, and (by default) no
calendar date, so memory of what gold did next can't leak into your decision.
"""
from __future__ import annotations

import io
import os
import sqlite3
from functools import lru_cache
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .analyser import ZoneAnalyser  # noqa: E402
from .data import PROC  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "journal" / "candidates.parquet"
LABELS_DB = Path(os.environ.get("GOLDBOT_LABELS_DB", ROOT / "journal" / "labels.db"))
M15 = pd.Timedelta(minutes=15)

# ---------- data ------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def bars15() -> pd.DataFrame:
    return pd.read_parquet(PROC / "xauusd_15m.parquet")[["open", "high", "low", "close"]]


@lru_cache(maxsize=1)
def candidates() -> pd.DataFrame:
    return pd.read_parquet(CANDIDATES).set_index("cid")


PUBLIC_COLS = ["side", "trigger", "tf", "kind", "level_side", "level", "structure", "candle", "session",
               "touches", "sl_dist", "close", "fvg_last3"]


def public_meta(cid: str, show_date: bool = False) -> dict:
    """What the labeller may see: the setup, never its outcome or period."""
    c = candidates().loc[cid]
    t = c["bar_time"]
    m = {k: (c[k].item() if hasattr(c[k], "item") else c[k]) for k in PUBLIC_COLS}
    m.update({"cid": cid, "when": t.strftime("%a %H:%M UTC") if not show_date else t.strftime("%Y-%m-%d %a %H:%M UTC")})
    m["entry_ref"] = round(float(c["close"]), 2)
    m["stop"] = round(float(c["close"] - c["side"] * c["sl_dist"]), 2)
    m["t2"] = round(float(c["close"] + 2 * c["side"] * c["sl_dist"]), 2)
    m["t3"] = round(float(c["close"] + 3 * c["side"] * c["sl_dist"]), 2)
    return m


# ---------- label store -----------------------------------------------------------------------


def db() -> sqlite3.Connection:
    con = sqlite3.connect(LABELS_DB)
    con.execute("""CREATE TABLE IF NOT EXISTS labels (
        cid TEXT PRIMARY KEY, decision TEXT, confidence INTEGER, note TEXT,
        labelled_at TEXT, seconds REAL, labeller TEXT)""")
    return con


def labels() -> pd.DataFrame:
    with db() as con:
        return pd.read_sql_query("SELECT * FROM labels", con)


def save_label(cid, decision, confidence, note="", seconds=None, labeller="trader"):
    assert decision in ("take", "skip", "opposite")
    with db() as con:
        con.execute("INSERT OR REPLACE INTO labels VALUES (?,?,?,?,?,?,?)",
                    (cid, decision, int(confidence), note, pd.Timestamp.now(tz="UTC").isoformat(), seconds, labeller))


def undo_last() -> str | None:
    with db() as con:
        r = con.execute("SELECT cid FROM labels ORDER BY labelled_at DESC LIMIT 1").fetchone()
        if r:
            con.execute("DELETE FROM labels WHERE cid=?", r)
        return r[0] if r else None


def next_cid(period: str | None = None) -> str | None:
    c = candidates()
    done = set(labels()["cid"])
    pool = c if not period else c[c["period"] == period]
    pool = pool[~pool.index.isin(done)].sort_values("order")
    return pool.index[0] if len(pool) else None


# ---------- blind chart -----------------------------------------------------------------------


def _candles(ax, w: pd.DataFrame, x0: int = 0, width: float = 3.2):
    x = np.arange(len(w)) + x0
    up = w["close"].values >= w["open"].values
    col = np.where(up, "#1f9e89", "#d1495b")
    ax.vlines(x, w["low"], w["high"], color=col, lw=0.8)
    ax.vlines(x, np.minimum(w["open"], w["close"]), np.maximum(w["open"], w["close"]), color=col, lw=width)
    return x


def _levels_at(t: pd.Timestamp):
    d = bars15()
    za = ZoneAnalyser(d.loc[t - pd.Timedelta(days=30): t])
    za.refresh_levels(t + M15)
    return za.levels


def render(cid: str, show_date: bool = False) -> bytes:
    c = candidates().loc[cid]
    t = c["bar_time"]
    d = bars15()
    hist = d.loc[:t]                                     # nothing after the signal candle
    w15 = hist.iloc[-112:]
    h1 = hist.loc[t - pd.Timedelta(days=8):].resample("1h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    h1 = h1[h1.index + pd.Timedelta(hours=1) <= t + M15]  # completed H1 bars only
    levels = _levels_at(t)
    side = int(c["side"])
    pad_r = 14
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(13, 8.2), gridspec_kw={"height_ratios": [1, 1.25]})
    fig.patch.set_facecolor("white")
    for ax, w, step, title in ((a1, h1, pd.Timedelta(hours=1), "H1 context"), (a2, w15, M15, "15m (signal candle = last)")):
        x = _candles(ax, w, width=2.6 if ax is a1 else 3.2)
        xr = np.arange(len(w) + pad_r)
        # draw lines in candle units through their value at the signal time (like a chart that skips weekends)
        j_sig = len(w) - 1
        for b in levels:
            trig = b.tf == c["tf"] and b.kind == c["kind"] and b.side == c["level_side"]
            col = "#e9a03b" if trig else ("#3d5a80" if b.kind == "channel" else "#7b6d8d" if b.kind == "box" else "#5c8d89")
            w0, b0 = b.at(t + M15)
            per_bar = b.slope * (step / pd.Timedelta(hours=b.tf_hours))
            wv = w0 + per_bar * (xr - j_sig)
            bv = b0 + per_bar * (xr - j_sig)
            ax.plot(xr, wv, color=col, lw=2.2 if trig else 1.0, alpha=0.95 if trig else 0.55,
                    label=f"{b.tf} {b.kind} {b.side}{'  <- trigger' if trig else ''}")
            ax.plot(xr, bv, color=col, lw=1.0 if trig else 0.7, ls="--", alpha=0.8 if trig else 0.4)
        lo, hi = w["low"].min(), w["high"].max()
        if ax is a2:
            j = len(w) - 1
            ax.annotate("", xy=(j, c["close"]), xytext=(j + 4, c["close"]),
                        arrowprops=dict(arrowstyle="->", color="black", lw=1.4))
            stop = c["close"] - side * c["sl_dist"]
            t3 = c["close"] + 3 * side * c["sl_dist"]
            t2 = c["close"] + 2 * side * c["sl_dist"]
            ax.hlines(stop, j + 1, j + pad_r, color="#d1495b", lw=1.3, ls=":")
            ax.hlines([t2, t3], j + 1, j + pad_r, color="#1f9e89", lw=1.0, ls=":")
            ax.text(j + pad_r, stop, " stop", va="center", fontsize=7, color="#d1495b")
            ax.text(j + pad_r, t2, " 2R", va="center", fontsize=7, color="#1f9e89")
            ax.text(j + pad_r, t3, " 3R", va="center", fontsize=7, color="#1f9e89")
            lo, hi = min(lo, stop, t2, t3), max(hi, stop, t2, t3)
        pad = (hi - lo) * 0.08
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_xlim(-1, len(w) + pad_r + 2)
        k = max(1, len(w) // 8)
        fmt = "%m-%d %H:%M" if show_date else "%a %H:%M"
        ax.set_xticks(x[::k])
        ax.set_xticklabels([ts.strftime(fmt) for ts in w.index[::k]], fontsize=7)
        ax.tick_params(axis="y", labelsize=7)
        ax.grid(alpha=0.15)
        ax.set_title(title, fontsize=8, loc="left")
    a1.legend(fontsize=6.5, loc="upper left", ncol=3, framealpha=0.8)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    return buf.getvalue()


# ---------- features for models ---------------------------------------------------------------

CAT = ["trigger", "tf", "kind", "level_side", "candle", "session", "struct_type"]
NUM = ["side", "touches", "er", "bias", "dbias", "hour", "body_frac", "sl_atr", "atr15", "zone_atr", "dist_atr",
       "struct_aligned", "fvg_aligned", "dow"]


def features(c: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame(index=c.index)
    for k in ("side", "touches", "er", "bias", "dbias", "hour", "body_frac", "sl_atr", "atr15"):
        f[k] = c[k].astype(float)
    f["zone_atr"] = (c["wick"] - c["body"]).abs() / c["atr15"]
    f["dist_atr"] = (c["close"] - c["wick"]) * np.where(c["level_side"] == "upper", 1, -1) / c["atr15"]
    st = c["structure"].fillna("")
    f["struct_type"] = st.str.split().str[0].fillna("none").replace("", "none")
    f["struct_aligned"] = np.where(st.str.contains("bull"), 1, np.where(st.str.contains("bear"), -1, 0)) * c["side"]
    fv = c["fvg_last3"].fillna("0,0,0").str.split(",").apply(lambda x: sum(int(v) for v in x))
    f["fvg_aligned"] = fv * c["side"]
    f["dow"] = pd.to_datetime(c["bar_time"], utc=True).dt.dayofweek
    for k in ("trigger", "tf", "kind", "level_side", "candle", "session"):
        f[k] = c[k].astype(str)
    for k in CAT:
        f[k] = f[k].astype("category")
    return f
