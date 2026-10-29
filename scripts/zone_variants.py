"""Every zone-analyser version tried in the refinement loop (see reports/iterations.md).
Names are vNN_<what changed>. Never edit a version after it has been run: add a new one."""
from __future__ import annotations

from dataclasses import replace

from goldbot.analyser import ZoneParams

B = ZoneParams()  # original defaults
MARU = ("bull_marubozu", "bear_marubozu")

ZV: dict[str, ZoneParams] = {
    # ---- v00: re-baseline the local session's variants on the Twelve Data feed ----
    "v00_breakout_smc": replace(B, mode="breakout", confirm="smc"),
    "v00_breakout_plain": replace(B, mode="breakout", confirm="none"),
    "v00_both_smc": replace(B, mode="both", confirm="smc"),
    "v00_rejection_candle": replace(B, mode="rejection", confirm="none"),
    "v00_retest": replace(B, triggers=("retest",)),
    "v00_sweep": replace(B, triggers=("sweep",)),
}

# ---- v01-v08: daily-trend filter (journal: with-trend signals +0.05..0.09R gross, against -0.05..-0.10R,
#      same sign in 2023 and 2024; Hurst/Ooi/Pedersen trend evidence) and cost-aware stops/targets ----
D20 = dict(bias="donchian", bias_days=20)
ZV.update({
    "v01_brk_smc_trend": replace(B, mode="breakout", confirm="smc", **D20),
    "v02_brk_plain_trend": replace(B, mode="breakout", confirm="none", **D20),
    "v03_brk_smc_trend_sma50": replace(B, mode="breakout", confirm="smc", bias="sma", bias_days=50),
    "v04_brk_smc_trend_rr3": replace(B, mode="breakout", confirm="smc", rr=3.0, **D20),
    "v05_brk_smc_trend_atr25": replace(B, mode="breakout", confirm="smc", stop_mode="atr", stop_atr=2.5, max_sl_atr=4.0, **D20),
    "v06_brk_smc_trend_swing": replace(B, mode="breakout", confirm="smc", stop_mode="swing", max_sl_atr=4.0, **D20),
    "v07_rej_candle_trend": replace(B, mode="rejection", confirm="none", **D20),
    "v08_all4_trend": replace(B, confirm="none", triggers=("breakout", "retest", "sweep", "rejection"), **D20),
})

# ---- v09-v15: exits and filters on top of v04 (breakout + SMC confirm + daily trend + 3R) ----
# journal: trades cut by the 20:45 flat rule averaged +0.67R (winners still running); H4 levels +0.175R vs 1h -0.01R
V04 = ZV["v04_brk_smc_trend_rr3"]
HOLD = dict(flat_hour=-1, max_bars=96)  # hold up to 24h, still flat into the weekend
ZV.update({
    "v09_v04_hold24h": replace(V04, **HOLD),
    "v10_v04_hold24h_swing": replace(V04, stop_mode="swing", max_sl_atr=4.0, **HOLD),
    "v11_v04_h4only": replace(V04, tfs=(("4h", 60),)),
    "v12_v04_shock3": replace(V04, shock_x=3.0, shock_bars=8),
    "v13_v04_be1": replace(V04, be_r=1.0),
    "v14_v04_hold24h_trail3": replace(V04, rr=6.0, trail_atr=3.0, **HOLD),
    "v15_v04_hold48h_rr4": replace(V04, rr=4.0, flat_hour=-1, max_bars=192),
})

# ---- v16-v22: around v09. journal (dev, both years): 07-09 UTC entries -0.17R, 12-15 UTC +0.34R; H4 +0.36R vs H1 +0.04R
V09 = ZV["v09_v04_hold24h"]
ZV.update({
    "v16_v09_no_london_open": replace(V09, session=(10, 18)),
    "v17_v09_ny_only": replace(V09, session=(12, 18)),
    "v18_v09_h4only": replace(V09, tfs=(("4h", 60),)),
    "v19_v09_plus_retest_sweep": replace(V09, triggers=("breakout", "retest", "sweep")),
    "v20_v09_plain": replace(V09, confirm="none"),
    "v21_v09_rr25": replace(V09, rr=2.5),
    "v22_v09_session10_20": replace(V09, session=(10, 20)),
})

# ---- v23-v28: neighbourhood of v16 (robustness, not selection: a real edge should not depend on one exact value)
V16 = ZV["v16_v09_no_london_open"]
ZV.update({
    "v23_v16_start9": replace(V16, session=(9, 18)),
    "v24_v16_start11": replace(V16, session=(11, 18)),
    "v25_v16_rr25": replace(V16, rr=2.5),
    "v26_v16_rr35": replace(V16, rr=3.5),
    "v27_v16_hold16h": replace(V16, max_bars=64),
    "v28_v16_hold32h": replace(V16, max_bars=128),
})

# ---- v29-v33: H4 levels only (v18 was the one version positive on DEV and VAL; v16 failed VAL: -0.25R,
#      June 2025 range, H1 S/R breakouts -0.63R while H4 stayed positive). Ways to get more H4 trades.
V18 = ZV["v18_v09_h4only"]
ZV.update({
    "v29_v18_no_london_open": replace(V18, session=(10, 18)),
    "v30_v18_lookback90": replace(V18, tfs=(("4h", 90),)),
    "v31_v18_plus_retest": replace(V18, triggers=("breakout", "retest")),
    "v32_v18_session7_20": replace(V18, session=(7, 20)),
    "v33_v18_buffer005": replace(V18, buffer_atr=0.05),
})

# ---- v34-v38: trend-STRENGTH gate (Kaufman efficiency ratio of the last 20 completed daily closes).
#      Motivation: v16 lost in the June 2025 range (VAL) and v18 lost Jun-Oct 2026 (HOLDOUT, looked at once)
#      while the daily Donchian bias stayed on. Tuned on DEV only.
ZV.update({
    "v34_v16_er20": replace(V16, er_min=0.20),
    "v35_v16_er30": replace(V16, er_min=0.30),
    "v36_v18_er20": replace(V18, er_min=0.20),
    "v37_v18_er30": replace(V18, er_min=0.30),
    "v38_v09_er25": replace(V09, er_min=0.25),
})
