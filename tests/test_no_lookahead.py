"""The analyser must make identical decisions whether or not future bars exist in memory."""
import sys, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from goldbot.analyser import ZoneAnalyser, ZoneParams
from goldbot.data import PROC

# the refinement knobs (daily bias, swing stops, shock filter, touches, candle filter) must be causal too
REFINED = ZoneParams(mode="breakout", bias="sma", bias_days=50, stop_mode="swing", shock_x=3.0, er_min=0.15,
                     min_touches=3, skip_candles=("bull_marubozu", "bear_marubozu"), triggers=("breakout", "retest", "sweep"))


def check(params, start, cut, end, load_from):
    d = pd.read_parquet(PROC / "xauusd_15m.parquet").loc[load_from:end]
    cut = pd.Timestamp(cut, tz="UTC")
    full = ZoneAnalyser(d, params).run(start, end)
    trunc = ZoneAnalyser(d.loc[:cut - pd.Timedelta(minutes=15)], params).run(start, end)
    a = full[full.bar_time < cut].reset_index(drop=True)
    b = trunc.reset_index(drop=True)
    cols = [c for c in ["bar_time", "side", "trigger", "sl_dist", "level", "bias", "dbias", "er"] if c in a]
    assert len(a) == len(b), f"signal count differs: full={len(a)} truncated={len(b)}"
    assert a[cols].equals(b[cols]), "decisions differ -> lookahead!"
    return len(a), cut


def test(start="2026-10-01", cut="2026-10-15 13:00", end="2026-10-30"):
    n, c = check(ZoneParams(), start, cut, end, "2026-09-05")
    print(f"no lookahead (default): {n} signals before {c} identical with and without future data")


def test_refined(start="2026-09-01", cut="2026-10-15 13:00", end="2026-10-30"):
    n, c = check(REFINED, start, cut, end, "2026-05-01")
    assert n > 0
    print(f"no lookahead (refined): {n} signals before {c} identical with and without future data")


if __name__ == "__main__":
    test()
    test_refined()
