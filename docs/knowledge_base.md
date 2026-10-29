# XAU/USD knowledge base

What drives gold, what the research says about predicting it, and where each idea is used in this project.
Last updated 2026-10-30.

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
| Twelve Data | Spot cross-check (set `TWELVEDATA_API_KEY`) |
| LightGBM | `ml_lgbm` route (tested: no edge on H1) |
| Kronos (shiyu-coder/Kronos) | `kronos` experimental route |
| NautilusTrader / QuantConnect LEAN | Upgrade path when going live with a broker |
| Vibe-Trading (HKUDS) | Fast prototyping of new route ideas in plain English |
| QuantAgent / TradingAgents | Candidates for a news/chart "context" layer, not for execution |
| OANDA v20 practice API | Broker-grade paper fills on Linux (next step) |
