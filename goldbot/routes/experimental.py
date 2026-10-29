"""Experimental routes: saved so they can be tested, but not run by default.

KronosForecast needs extra installs (torch + the Kronos repo) and a GPU or a lot of patience:
    uv pip install --python .venv/bin/python torch einops huggingface_hub safetensors
    git clone https://github.com/shiyu-coder/Kronos vendor/Kronos
Then run: .venv/bin/python scripts/research.py --routes kronos --since 2024-01-01
Independent tests on forex (Chis, Aug 2026) found ~50% directional accuracy, so treat it as a
feature to test, not a signal to trust.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .base import Route

VENDOR = Path(__file__).resolve().parents[2] / "vendor" / "Kronos"


class KronosForecast(Route):
    name = "kronos"
    family = "foundation_model"
    thesis = ("Kronos (AAAI 2026) is pre-trained on 12B candles. Use its zero-shot forecast of the "
              "next `pred_len` bars: trade when the forecast move exceeds `k_atr` x ATR.")
    params = {"model": "NeoQuasar/Kronos-small", "tokenizer": "NeoQuasar/Kronos-Tokenizer-base",
              "lookback": 400, "pred_len": 12, "k_atr": 1.0, "every": 4, "sl_atr": 1.5, "tp_atr": 2.0}

    def signals(self, d):
        if not VENDOR.exists():
            raise RuntimeError(f"Kronos not installed. See instructions at the top of {__file__}")
        sys.path.insert(0, str(VENDOR))
        from model import Kronos, KronosPredictor, KronosTokenizer  # type: ignore

        tok = KronosTokenizer.from_pretrained(self.p["tokenizer"])
        mdl = Kronos.from_pretrained(self.p["model"])
        pred = KronosPredictor(mdl, tok, max_context=512)
        s = self.empty(d)
        L, P = self.p["lookback"], self.p["pred_len"]
        cols = ["open", "high", "low", "close", "volume"]
        for i in range(L, len(d) - 1, self.p["every"]):
            x = d.iloc[i - L + 1 : i + 1]
            fut_ts = pd.Series(pd.date_range(x.index[-1] + pd.Timedelta(hours=1), periods=P, freq="h"))
            fc = pred.predict(df=x[cols].reset_index(drop=True), x_timestamp=pd.Series(x.index),
                              y_timestamp=fut_ts, pred_len=P, T=1.0, top_p=0.9, sample_count=1, verbose=False)
            move = fc["close"].iloc[-1] - x["close"].iloc[-1]
            if abs(move) > self.p["k_atr"] * d["atr"].iloc[i]:
                s.iloc[i, s.columns.get_loc("side")] = int(np.sign(move))
        s["sl_dist"] = self.p["sl_atr"] * d["atr"]
        s["tp_dist"] = self.p["tp_atr"] * d["atr"]
        s["max_bars"] = P
        return s
