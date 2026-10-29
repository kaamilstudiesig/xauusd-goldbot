"""Turning-point FEATURES must not change when later bars are deleted (labels are hindsight by design)."""
import sys, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from goldbot import labelling as L, turning_points as T

def test(cut="2026-02-17 14:30"):
    cut = pd.Timestamp(cut, tz="UTC")
    d = L.bars15().loc["2025-09-01":]
    full = T.bar_features(d)
    trunc = T.bar_features(d.loc[:cut])
    a, b = full.loc[:cut], trunc
    bad = (~np.isclose(a.fillna(-9e9).values, b.fillna(-9e9).values, atol=1e-9)).any(axis=0)
    assert not bad.any(), f"lookahead in: {list(a.columns[bad])}"
    print(f"turning-point features: {a.shape[1]} features x {len(a)} candles identical with and without later bars")

if __name__ == "__main__":
    test()
