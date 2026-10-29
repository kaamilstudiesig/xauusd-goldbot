"""Forecasting-model features for every candidate setup.

For each setup, a pre-trained time-series model sees the last 512 15m closes (up to and including the
signal candle) and forecasts the next `horizon` bars. We keep its view relative to the trade:
  fc_ret_dir   median forecast move to the horizon, in 15m ATRs, + = in the trade's direction
  fc_width     10%-90% forecast range at the horizon, in ATRs (expected volatility)
  fc_skew_dir  upside room minus downside room, in ATRs, + = favours the trade

Backends
  chronos  amazon/chronos-bolt-small (48M params): runs on a normal CPU, ~10-20 min for all setups
  timesfm  google/timesfm-2.5-200m-pytorch: bigger; run it on Colab with a GPU

  .venv/bin/python scripts/forecast_features.py --backend chronos      # -> journal/forecast_chronos.parquet
Note: these models were pre-trained on public data that may include gold up to their release date, so
their features on DEV months may look better than they are. HOLD months (Aug 2025+) are cleaner.
"""
from __future__ import annotations

import argparse
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from goldbot import labelling as L  # noqa: E402


class ChronosBackend:
    def __init__(self, device="cpu"):
        import torch
        from chronos import BaseChronosPipeline

        self.torch = torch
        self.p = BaseChronosPipeline.from_pretrained("amazon/chronos-bolt-small", device_map=device, torch_dtype=torch.float32)

    def quantiles(self, ctx: np.ndarray, horizon: int) -> np.ndarray:
        """ctx (batch, length) -> (batch, 3) quantiles 10/50/90 at the horizon."""
        q, _ = self.p.predict_quantiles(self.torch.tensor(ctx, dtype=self.torch.float32),
                                        prediction_length=horizon, quantile_levels=[0.1, 0.5, 0.9])
        return q[:, -1, :].cpu().numpy()


class TimesFMBackend:
    def __init__(self, device="cuda"):
        import timesfm

        self.m = timesfm.TimesFM_2p5_200M_torch.from_pretrained("google/timesfm-2.5-200m-pytorch")
        self.m.compile(timesfm.ForecastConfig(max_context=1024, max_horizon=256, normalize_inputs=True,
                                              use_continuous_quantile_head=True, fix_quantile_crossing=True))

    def quantiles(self, ctx: np.ndarray, horizon: int) -> np.ndarray:
        _, q = self.m.forecast(horizon=horizon, inputs=list(ctx))
        q = np.asarray(q)[:, -1, :]          # mean, q10 ... q90
        return np.stack([q[:, 1], q[:, 5], q[:, 9]], axis=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["chronos", "timesfm"], default="chronos")
    ap.add_argument("--device", default=None)
    ap.add_argument("--context", type=int, default=512)
    ap.add_argument("--horizon", type=int, default=16)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--limit", type=int, default=0, help="only the first N setups (for a quick test)")
    a = ap.parse_args()
    out = ROOT / "journal" / f"forecast_{a.backend}.parquet"
    c = L.candidates().sort_values("bar_time")
    if a.limit:
        c = c.iloc[: a.limit]
    close = L.bars15()["close"]
    pos = close.index.get_indexer(pd.DatetimeIndex(c["bar_time"]))
    assert (pos >= 0).all(), "candidate bar missing from 15m data"
    vals = close.values.astype(np.float32)
    dev = a.device or ("cuda" if a.backend == "timesfm" else "cpu")
    model = ChronosBackend(dev) if a.backend == "chronos" else TimesFMBackend(dev)
    rows, t0 = [], time.time()
    for k in range(0, len(c), a.batch):
        p = pos[k: k + a.batch]
        ctx = np.stack([vals[max(0, i - a.context + 1): i + 1] if i + 1 >= a.context else
                        np.r_[np.full(a.context - i - 1, vals[0]), vals[: i + 1]] for i in p])
        rows.append(model.quantiles(ctx, a.horizon))
        if k // a.batch % 20 == 0:
            print(f"{k + len(p)}/{len(c)}  {time.time() - t0:.0f}s", flush=True)
    q = np.vstack(rows)
    side, atr, px = c["side"].values, c["atr15"].values, c["close"].values
    f = pd.DataFrame({
        "fc_ret_dir": (q[:, 1] - px) / atr * side,
        "fc_width": (q[:, 2] - q[:, 0]) / atr,
        "fc_skew_dir": ((q[:, 2] - px) - (px - q[:, 0])) / atr * side,
    }, index=c.index)
    f.to_parquet(out)
    print(f"{len(f)} setups -> {out} ({time.time() - t0:.0f}s)")
    print(f.describe().round(3))


if __name__ == "__main__":
    main()
