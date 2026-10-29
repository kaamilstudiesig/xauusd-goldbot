"""Quant features at a candidate must not change when later price bars are removed."""
import sys, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from goldbot import labelling as L, quant_features as Q

def test(cut="2026-03-10 13:00"):
    cut = pd.Timestamp(cut, tz="UTC")
    c = L.candidates().reset_index()
    c = c[(c.bar_time < cut) & (c.bar_time >= cut - pd.Timedelta(days=40))]
    d = L.bars15()
    full = Q.build(c, d)
    trunc = Q.build(c, d.loc[:cut - pd.Timedelta(minutes=15)])
    diff = (full - trunc).abs().max().max()
    assert np.allclose(full.fillna(-9e9), trunc.fillna(-9e9), atol=1e-9), (full - trunc).abs().max().sort_values().tail()
    print(f"quant features: {len(c)} candidates identical with and without later bars (max diff {diff:.2e})")

if __name__ == "__main__":
    test()
