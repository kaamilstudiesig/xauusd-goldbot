# XAU/USD knowledge base

What drives gold, what the research says about predicting it, and where each idea is used in this project.
Last updated 2026-10-29 (cloud session: 15m data source, zone-analyser research).

## 1. Price drivers (ranked by evidence)

| # | Driver | Direction | Horizon | Data in project | Notes |
|---|---|---|---|---|---|
| 1 | US real yields (10y TIPS) | rise → gold down | weeks-years | FRED `DFII10`, `ry_chg20` | Strongest long-run link (Erb & Harvey 2013). Broke down 2022-24 when central-bank buying overrode it: treat as regime-dependent. |
| 2 | US dollar (DXY) | USD up → gold down | days-months | yfinance `DX-Y.NYB`, `dxy_chg20` | Gold is priced in USD; foreign buyers' cost changes with the dollar. |
| 3 | Fed policy expectations | dovish → gold up | days-months | FRED `DFF` (effective fed funds) | Rate-path surprises (FOMC, CPI, NFP) cause the largest intraday moves. |
| 4 | Central-bank buying | steady bid | quarters-years | WGC Gold Demand Trends (quarterly, manual) | >1,000 t/yr in 2022-2024; main reason for the regime shift. |
| 5 | ETF flows | inflow → up | weeks-months | GLD/IAU holdings (not yet automated) | Western investor demand; reacts to real yields. |
| 6 | Risk-off / geopolitics | fear → up | hours-weeks | VIX `vix_z` | Short-lived spikes unless the shock changes rates or USD. |
| 7 | Inflation expectations | higher → up (mostly) | months | FRED `T10YIE` | Works through real yields. |
| 8 | Positioning (CFTC COT) | extreme long → reversal risk | weeks | not yet automated | Managed-money net length at multi-year extremes precedes pullbacks. |
| 9 | Physical demand (China/India) | supports dips | months | SGE premium, India imports (manual) | Price-sensitive: buyers step in on dips. |
| 10 | Oil shocks | ambiguous | weeks | - | High oil can lift inflation (gold up) or rates and USD (gold down). |

## 2. Intraday structure (where discretionary edge lives)

- **Sessions (UTC):** Asia 00-07 (thin liquidity, ranges), London 07-12 (first expansion), NY overlap 12-17 (largest volume, data releases at 12:30/13:30), late NY 17-21, **rollover 21-23 (spreads 3-5x, avoid)**.
- **Scheduled events:** NFP (1st Friday), CPI, FOMC (8/yr), PCE, jobless claims. Spreads widen 3-5x and stops slip.
- **LBMA fixes:** 10:30 and 15:00 London. Flows cluster around them.
- **Weekend gaps:** geopolitical news on weekends can gap the Sunday open.

## 3. What the evidence says about prediction

- **Direction is barely predictable.** Peer-reviewed out-of-sample work (Cabrera et al. 2022, J. Commodity Markets) finds ML rarely beats the historical mean for the gold risk premium.
- **Foundation models:** Kronos (AAAI 2026) shows forex IC of only 0.01-0.04 in its own appendix; an independent 25-market forex test (Chis, Aug 2026) found ~50% direction accuracy. A June 2026 benchmark (arXiv 2606.27100) concludes that TimesFM-2.5 / Moirai-2.0 / Chronos-2 are "useful priors", "not universal engines for alpha".
- **Trend following works on gold over long horizons.** Hurst, Ooi & Pedersen (2017), *A Century of Evidence on Trend-Following Investing*; Moskowitz, Ooi & Pedersen (2012), *Time Series Momentum*. Confirmed in this project: `daily_trend` is positive in all three test periods.
- **Volatility is predictable** (GARCH family; `arch` library), so use it for sizing and stops.
- **Costs decide intraday viability.** In this project every hourly route came out roughly break-even after a realistic spread, commission and slippage model.

## 4. Books (best ROI first)

1. **Robert Carver, *Systematic Trading* (2015) and *Advanced Futures Trading Strategies* (2023):** position sizing, volatility targeting, combining trend rules. The blueprint for `daily_trend` and the allocation layer.
2. **Marcos López de Prado, *Advances in Financial Machine Learning* (2018):** triple-barrier labels, purged walk-forward, meta-labelling, deflated Sharpe. Used in `ml_lgbm`.
3. **Ernest Chan, *Algorithmic Trading* (2013) and *Quantitative Trading* (2nd ed. 2021):** mean reversion vs momentum, practical backtesting pitfalls.
4. **Andreas Clenow, *Following the Trend* (2013):** diversified trend following, realistic expectations.
5. **Van Tharp, *Trade Your Way to Financial Freedom*:** R-multiples and expectancy (the journal reports everything in R).
6. **Kathy Lien, *Day Trading and Swing Trading the Currency Market*:** session behaviour and news trading.
7. **World Gold Council, *Gold Demand Trends* (quarterly) and the *Gold Return Attribution Model (GRAM)*:** the official driver decomposition.

## 5. Papers

- Erb & Harvey (2013), *The Golden Dilemma*, Financial Analysts Journal: real yields, inflation hedge myths.
- Baur & Lucey (2010), *Is Gold a Hedge or a Safe Haven?*: safe-haven behaviour is short-lived (~15 trading days).
- Hurst, Ooi & Pedersen (2017): trend following across a century.
- Moskowitz, Ooi & Pedersen (2012), *Time Series Momentum*, JFE.
- Shi et al. (2025/AAAI 2026), *Kronos: A Foundation Model for the Language of Financial Markets*, arXiv 2508.02739.
- Y-Research-SBU (2025), *QuantAgent*, arXiv 2509.09995: multi-agent VLM chart reading.
- Noguer i Alonso & Franklin (2026), *Pretrained Time-Series Foundation Models for Financial Return Forecasting*, arXiv 2606.27100.
- Bailey & López de Prado (2014), *The Deflated Sharpe Ratio*: correcting for many backtests.

## 6. Open-source tools (and how they fit)

| Tool | Use here |
|---|---|
| Hugging Face `ZombitX64/xauusd-gold-price-historical-data-2004-2025` | Spot history 2004-2025 (in use) |
| yfinance `GC=F`, `DX-Y.NYB`, `^VIX`, `^TNX` | Recent bars + macro (in use) |
| FRED | Real yields, breakevens, fed funds (in use) |
| Twelve Data | XAU/USD 15m spot 2022-10 -> today (in use, see §7); spot cross-check (`TWELVEDATA_API_KEY`) |
| LightGBM | `ml_lgbm` route (tested: no edge on H1) |
| Kronos (shiyu-coder/Kronos) | `kronos` experimental route |
| NautilusTrader / QuantConnect LEAN | Upgrade path when going live with a broker |
| Vibe-Trading (HKUDS) | Fast prototyping of new route ideas in plain English |
| QuantAgent / TradingAgents | Candidates for a news/chart "context" layer, not for execution |
| OANDA v20 practice API | Broker-grade paper fills on Linux (next step) |

## 7. 15m data source (filled the Aug 2025 -> Aug 2026 gap)

**Twelve Data `time_series`, symbol `XAU/USD`, interval `15min`**, used through the user's connected Twelve Data
account (free Basic plan: 8 calls/min, 800/day, 5000 bars per call; earliest 15m bar 2020-01-24).
Thirty-three 56-day windows cover **2022-10-24 -> 2026-10-29 (94.6k bars)**. The raw responses are in
`data/raw/td15/td_<first>_<last>.csv` and are built by `goldbot.data.build_15m()` into
`data/processed/xauusd_15m.parquet`. This replaces the HF-2022 + GC=F-minus-basis stitch with one spot feed.
To refresh: fetch the newest window (any API key or the MCP connector), save it into `data/raw/td15/`, then
run `build_15m()`.

Quirks found and handled (all checked, not assumed):
- **Timestamps are in Australia/Sydney time (AEST/AEDT)**, not UTC. Evidence: the weekly open lands on
  Sun 18:00 New York and the last bar on Fri 16:45 NY across US and Australian DST changes, and NFP spikes
  sit at 12:30/13:30 UTC once converted. `TD_TZ` in `goldbot/data.py`.
- **Weekend quotes** from mid-2025 (whole Saturdays, flat weekend filler in 2026) and **flat filler bars in the
  17:00-18:00 NY daily break** in 2026: removed by `trading_week_mask`.
- Friday closes match the weekly spot file to within about $1 in 2026 and a few dollars in late 2025.
- In winter weeks of 2022-2024 the feed stops about 1.5h before the real Friday close. The analyser never
  trades then (no entries after 18:00 UTC on Fridays).
- 2026 prices carry 5 decimals (composite feed). Treat 2026 fills as approximate.
- Not usable from this cloud environment (blocked by its network policy): Hugging Face, Yahoo Finance (yfinance),
  FRED, Kaggle. With network access, `build_15m()` still merges HF and GC=F proxy bars where Twelve Data has
  no bar.

## 8. Research on intraday S/R, SMC and gold (zone-analyser refinement, Oct 2026)

| Source | Claim | Tested here? | Result |
|---|---|---|---|
| Osler (2000), *Support for Resistance: Technical Analysis and Intraday Exchange Rates*, FRBNY EPR; Osler (2003), *Currency Orders and Exchange Rate Dynamics*, J. Finance ([NY Fed SR125](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf), [SR150](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.pdf)) | Take-profits cluster at round numbers (reversals); stop-losses cluster just beyond them (breaks accelerate) | Yes: breakouts crossing $10/$25/$50 levels | No consistent effect on gold DEV (sign flips between years) |
| Chang & Osler (1999) / FMG DP 142, *When support/resistance levels are broken, can profits be made?* ([FMG](https://www.fmg.ac.uk/publications/discussion-papers/when-supportresistance-levels-are-broken-can-profits-be-made)) | S/R breaks profitable after costs in FX | Yes (the breakout trigger) | Not on its own: about 0 gross. Positive only with the daily trend, 3R and a 24h hold |
| Batten, Lucey, McGroarty, Peat, Urquhart (2018), *Does intraday technical trading have predictive power in precious metal markets?*, JIFMIM ([IDEAS](https://ideas.repec.org/a/eee/intfin/v52y2018icp102-113.html)) | 5-min gold rules: standard parameters have no predictive power; some do after searching a parameter universe, gross of costs | Method lesson | Same pattern here: many DEV winners, few survive VAL. Hence the strict split and the logged count of versions |
| Sullivan, Timmermann & White (1999); Bailey & López de Prado (2014) | Data snooping and deflated Sharpe | Method | 44 versions tried, all logged in `reports/iterations.md` |
| Gao, Han, Li & Zhou (2018), *Market intraday momentum*, JFE; commodity intraday momentum (Hull repository) | First half-hour predicts last half-hour; stronger on news days | Indirectly (session splits) | NY-session entries strongest on DEV; London-open entries weakest |
| Hurst, Ooi & Pedersen (2017); Moskowitz, Ooi & Pedersen (2012) | Time-series momentum | Yes: 20-day Donchian daily bias | The only filter positive in both DEV years |
| Kaufman, *Trading Systems and Methods* (efficiency ratio) | Trend strength separates trend from range | Yes (v34-v38) | Helped on DEV, failed VAL: overfit |
| [joshyattridge/smart-money-concepts](https://github.com/joshyattridge/smart-money-concepts) (Python; FVG, swings, BOS/CHoCH, order blocks, liquidity) | Indicator definitions only, no backtests | Definitions mirrored in `goldbot/smc.py` (streaming, causal) | n/a |
| TradingView / MQL5 SMC scripts for XAUUSD | Claimed edges, mostly unvalidated or commercial | No | No reproducible open-source XAUUSD SMC backtest found |
