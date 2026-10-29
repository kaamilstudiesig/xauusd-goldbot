# Zone analyser refinement log

**Outcome: target NOT met.** I tried 44 versions plus one journal-only idea. The best version that held up
on validation is `v18_v09_h4only`. On the 14 holdout months that traded it is positive after costs,
**PF 1.10, +0.069R per trade (50 trades)**, which is below the PF ≥ 1.2 target. It is not negative on
2023-01..2025-07 (+16.1R). The holdout is front-loaded: Aug-Dec 2025 made +16.0R, and 2026 lost -12.5R.

## Target and how it was judged
- Target (from the brief): PF ≥ 1.2 and avg R > 0 after costs on at least 3 recent held-out months, and not
  negative on 2023-01..2025-07.
- How I read it: I judged the **pooled** holdout (Aug 2025 - Oct 2026, every month that traded). Picking the
  3 best of 15 months would pass almost any version: v18 has 7 months with PF ≥ 1.2 even though it loses money
  over the last five months. Each month has only 1-7 v18 trades, so a single month's PF is noise.
- Split: DEV 2023-01..2024-12 (all tuning), VAL 2025-01..2025-07 (checked 3 times in total: v16, v18, v34),
  HOLD 2025-08..2026-10 (run once for the finalised version, with the original baseline as a reference;
  `reports/holdout_log.csv`).
- Engine: `scripts/blind_test.run_variant`, which feeds bars one at a time and fills on the next bar, stop
  first, with the unchanged cost model in `goldbot/costs.py`. Journal: `journal/blind.db`, tests
  `dev` / `val` / `hold` / `*_costx`. `tests/test_no_lookahead.py` passes for the default parameters and
  for every new knob.
- Caveat: Oct 2026 was already examined by the local session (the London fake-out lead), so it is not fully
  clean holdout data.

## Data (needed before any testing)
The cloud network blocks Hugging Face, Yahoo and FRED. I used the user's connected **Twelve Data** account
(free plan, 8 calls/min) to download XAU/USD 15m spot for 2022-10-24 to 2026-10-29: 33 calls and about 94.6k
bars, built into one consistent feed with `goldbot.data.build_15m()`. The timestamps come back in Sydney time,
which I verified against NFP spikes and the weekly open and close across several DST changes. I dropped the
weekend quotes and the flat filler bars in the 17:00 NY daily break. Details are in `docs/knowledge_base.md` §7.

## Versions (R after costs; PF on R)

| Version | What changed (vs parent) | Why | DEV n / avgR / PF | VAL | HOLD |
|---|---|---|---|---|---|
| v00_breakout_smc | baseline (local session) | re-baseline on new feed | 586 / -0.076 / 0.88 | -0.030 / 0.95 | **313 / -0.048 / 0.92** (reference) |
| v00_breakout_plain | baseline | | 673 / -0.118 / 0.82 | -0.044 / 0.93 | |
| v00_both_smc | baseline | | 714 / -0.081 / 0.87 | -0.068 / 0.89 | |
| v00_rejection_candle | baseline | | 923 / -0.136 / 0.80 | -0.214 / 0.68 | |
| v00_retest | baseline | | 337 / -0.156 / 0.78 | +0.070 / 1.14 | |
| v00_sweep | baseline | | 357 / -0.061 / 0.90 | +0.033 / 1.06 | |
| — signal pool (DEV) | every signal scored alone, gross vs net | find where the edge and the costs are | gross ≈ 0 for every trigger; **costs 0.13-0.19R/trade** | | |
| v01_brk_smc_trend | + daily 20-day Donchian trend filter | pool: with-trend +0.05..0.09R gross, against -0.05..-0.10R, same sign in 2023 and 2024 | 291 / -0.030 / 0.95 | | |
| v02_brk_plain_trend | v01 without the SMC confirm | | 343 / -0.108 / 0.84 | | |
| v03_brk_smc_trend_sma50 | trend = close vs 50-day SMA | alternative trend definition | 299 / -0.046 / 0.93 | | |
| v04_brk_smc_trend_rr3 | v01 + 3R target | with-trend winners run further | 283 / +0.022 / 1.03 | | |
| v05_brk_smc_trend_atr25 | v01 + 2.5 ATR stop | wider stop means costs are a smaller share of R | 281 / +0.013 / 1.02 | | |
| v06_brk_smc_trend_swing | v01 + stop beyond last 15m swing | structure stop (user lead) | 270 / +0.012 / 1.02 | | |
| v07_rej_candle_trend | rejection + trend | buy support in an uptrend | 628 / -0.114 / 0.83 | | |
| v08_all4_trend | all 4 triggers + trend | | 869 / -0.120 / 0.82 | | |
| **v09_v04_hold24h** | v04, hold up to 24h, flat into the weekend | journal: trades cut at 20:45 averaged +0.67R | 272 / **+0.096 / 1.13** | | |
| v10_v04_hold24h_swing | v09 + swing stop | | 229 / +0.084 / 1.14 | | |
| v11_v04_h4only | v04, H4 levels only | journal: H4 +0.175R vs H1 -0.01R | 92 / +0.040 / 1.07 | | |
| v12_v04_shock3 | v04 + no entries for 2h after a >3x-range bar | event/news proxy | 165 / +0.091 / 1.13 (2023 < 0) | | |
| v13_v04_be1 | v04 + breakeven at +1R | user idea | 290 / -0.039 / 0.93 | | |
| v14_v04_hold24h_trail3 | v09 + 3 ATR trail, 6R cap | let trends run | 274 / +0.007 / 1.01 | | |
| v15_v04_hold48h_rr4 | hold 48h, 4R | | 251 / +0.008 / 1.01 | | |
| v16_v09_no_london_open | v09, entries 10-18 UTC | journal: 07-09 UTC -0.17R in both years (user's London fake-out lead) | 222 / **+0.145 / 1.20** | **58 / -0.254 / 0.68 ✗** | |
| v17_v09_ny_only | v09, entries 12-18 UTC | | 187 / +0.106 / 1.15 | | |
| v18_v09_h4only | v09, H4 levels only | user lead + journal | 88 / **+0.149 / 1.23** | **21 / +0.144 / 1.22 ✓** | **50 / +0.069 / 1.10** (costs×price: +0.048 / 1.07) |
| v19_v09_plus_retest_sweep | v09 + retest and sweep triggers | more trades | 430 / +0.009 / 1.01 | | |
| v20_v09_plain | v09 without the SMC confirm | | 317 / +0.007 / 1.01 | | |
| v21_v09_rr25 | v09 with 2.5R | | 276 / +0.091 / 1.13 | | |
| v22_v09_session10_20 | entries 10-20 UTC | | 243 / +0.098 / 1.13 | | |
| v23-v28 | v16 neighbours: start 9/11, rr 2.5/3.5, hold 16h/32h | robustness check | all +0.107..+0.140, PF 1.15-1.19, both years > 0 | | |
| v29_v18_no_london_open | H4 + entries 10-18 | | 77 / +0.171 / 1.27 | | |
| v30_v18_lookback90 | H4 lines from 90 bars | more H4 trades | 131 / +0.067 / 1.10 | | |
| v31_v18_plus_retest | H4 + retest trigger | more H4 trades | 102 / +0.137 / 1.21 | | |
| v32_v18_session7_20 | H4, entries 07-20 | | 92 / +0.138 / 1.21 | | |
| v33_v18_buffer005 | H4, 0.05 ATR buffer | | 90 / +0.131 / 1.20 | | |
| v34_v16_er20 | v16 + 20-day efficiency ratio ≥ 0.20 | skip sideways regimes (v16 lost in the June 2025 range; v18 lost Jun-Oct 2026) | 106 / **+0.193 / 1.28** | **25 / -0.094 / 0.88 ✗** | |
| v35_v16_er30 | ER ≥ 0.30 | | 67 / +0.246 / 1.36 (too few) | | |
| v36_v18_er20 | H4 + ER ≥ 0.20 | | 36 / +0.117 / 1.17 (2024 < 0) | | |
| v37_v18_er30 | H4 + ER ≥ 0.30 | | 24 / +0.444 / 1.78 (too few) | | |
| v38_v09_er25 | v09 + ER ≥ 0.25 | | 110 / +0.092 / 1.13 | | |
| — round numbers (pool) | breakout candle crosses a $10/$25/$50 level | Osler (2000, 2003): stop-loss clusters beyond round numbers | sign flips between 2023 and 2024: rejected | | |

Count: **44 versions** run through the backtester (6 baselines + v01..v38) plus 2 journal-only studies
(signal pool and round numbers). That is 3 validation looks and 1 holdout look for selection (+1 reference and
+1 cost-stress run of the same version).

## What the journal says (DEV, consistent in 2023 and 2024)
1. **Costs, not signals, are the first problem.** Scored on their own, signals are close to zero gross
   (breakout -0.01R, sweep +0.055R, rejection +0.03R), and costs take 0.13-0.19R per trade because 15m stops
   average only a few dollars.
2. **Trade with the daily trend.** With-trend breakouts are +0.09R gross and against-trend ones are -0.10R,
   with the same sign in both years. This is the only filter that was strong in both years.
3. **Let winners run past the session.** The 20:45 forced exit was cutting winners: holding up to 24h moved
   avg R from +0.02 to +0.10. Breakeven stops and trailing stops both made results worse.
4. **H4 levels beat H1 levels**, and they were the only version that held up on VAL: H1 S/R breakouts lost
   -0.63R in the June 2025 range.
5. **London-open entries (07-09 UTC) lose** on DEV. Removing them looked good on DEV but failed VAL.
6. SMC confirm (body ≥ 50% or BOS) matters: removing it took avg R back to about 0 (v20, v02).
7. Did not help: retest or sweep triggers, rejection trades, the shock (news) filter, breakeven, trailing,
   longer holds, round numbers, and the efficiency-ratio gate (which overfit: good on DEV, failed VAL).

## Why the target is not met
- **Too few trades.** The version that generalises (H4 levels) fires about 3 times a month. Monthly PF is noise
  and the pooled holdout (50 trades) has a wide error band: PF 1.10 is consistent with anything from clearly
  negative to clearly profitable: a bootstrap of the 50 trades gives a 90% band of PF 0.61-1.82 and
  avg R -0.31..+0.45.
- **Regime decay in 2026.** Holdout Aug-Dec 2025 (a strong, orderly uptrend) made +1.0R per trade. 2026
  (sharp two-way swings: +$400 weeks, the March sell-off from 5171 to 4491) made -0.37R per trade. The daily
  trend filter stays "on" through these whipsaws.
- **Shorts.** Shorts were weaker than longs in every split (holdout shorts -0.31R). I did not make the version
  long-only: that would be a bet on the 2023-26 gold bull market, not a property of the zone process.
- **The H1/15m process sits too close to the cost line.** Every H1 version that looked good on DEV failed VAL.

## Final parameters (best validated version, `v18_v09_h4only`)
```python
ZoneParams(mode="breakout", confirm="smc", rr=3.0, tfs=(("4h", 60),), kinds=("channel", "box", "sr1", "sr2"),
           session=(7, 18), buffer_atr=0.10, cooldown=8, min_sl_atr=0.8, max_sl_atr=3.0,
           max_bars=96, flat_hour=-1, weekend_flat=True,
           bias="donchian", bias_days=20, bias_mode="with")   # everything else default
```

## Suggested next steps (not done here)
1. **Paper-trade v18 in shadow** alongside `daily_trend` to collect forward trades. At about 3 a month it needs
   roughly 2 years to reach 100 trades, so judge it together with `daily_trend`, not on its own.
2. A real economic calendar (FOMC/CPI/NFP) instead of the range-shock proxy. Holdout gap-stops cost about 1.7R
   each.
3. Better broker data: the 2026 Twelve Data feed has 5-decimal composite prices and filler bars. OANDA practice
   or Dukascopy tick data would allow a fill-quality check.
