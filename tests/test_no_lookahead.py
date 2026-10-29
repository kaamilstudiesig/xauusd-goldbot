"""The analyser must make identical decisions whether or not future bars exist in memory."""
import sys, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from goldbot.analyser import ZoneAnalyser, ZoneParams
from goldbot.data import PROC

def test(start="2026-10-01", cut="2026-10-15 13:00", end="2026-10-30"):
    d = pd.read_parquet(PROC / "xauusd_15m.parquet").loc["2026-09-05":end]
    cut = pd.Timestamp(cut, tz="UTC")
    full = ZoneAnalyser(d, ZoneParams()).run(start, end)
    trunc = ZoneAnalyser(d.loc[:cut - pd.Timedelta(minutes=15)], ZoneParams()).run(start, end)
    a = full[full.bar_time < cut].reset_index(drop=True)
    b = trunc.reset_index(drop=True)
    cols = ["bar_time", "side", "trigger", "sl_dist", "level"]
    assert len(a) == len(b), f"signal count differs: full={len(a)} truncated={len(b)}"
    assert a[cols].equals(b[cols]), "decisions differ -> lookahead!"
    print(f"no lookahead: {len(a)} signals before {cut} identical with and without future data")

if __name__ == "__main__":
    test()
