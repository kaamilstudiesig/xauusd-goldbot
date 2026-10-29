# Route registry

Every idea is a "route": a self-contained module that can be backtested and paper traded. Results
below come from `scripts/research.py` (2008-2026 hourly XAU/USD, realistic costs, 0.5% risk per trade).
Rule parameters were fixed in advance, not optimised, so every period is effectively out-of-sample.

Costs modelled: spread $0.25 (London/NY), $0.40 (Asia), $1.20 (rollover), x3 on news-sized bars,
$0.07/oz commission, $0.05 entry and $0.20 stop slippage, overnight swap. Edit `goldbot/costs.py`
to match your broker.

## Status: ACTIVE (portfolio)

### daily_trend: daily channel breakout with trend filter
- **Idea:** close beyond the 20-day high/low in the direction of the 100-day mean, checked at 19:00 UTC; stop 2.5x daily ATR, trailing 3x daily ATR. Holds days to weeks.
- **Results (avg R / profit factor):** 2010-18 **+0.07R / 1.15**, 2019-22 **+0.21R / 1.45**, 2023-26 **+0.62R / 2.78**.
  Full: 136 trades, 43% wins, +0.21R avg, PF 1.5, max DD 4.3% at 0.5% risk.
- **Robustness:** 96-variant grid: 98% positive overall, 61% positive in all three periods (`reports/robustness_daily_trend.csv`).
- **Caveat:** about 8 trades a year. Expect 0-2 trades in a month of paper trading. Returns at 0.5% risk are small (~+1.7R/yr); this is a bias/regime layer, not a money printer.

## Status: SHADOW (paper traded, not in portfolio, gathering evidence)

| Route | Idea | 2010-18 | 2019-22 | 2023-26 | Verdict |
|---|---|---|---|---|---|
| daily_trend_long | daily_trend, longs only | +0.17R | +0.43R | +0.98R | Strong, but partly reflects gold's bull market (beta). Promote if you accept a long bias. |
| daily_trend+macro | daily_trend, only if real yields/DXY agree | +0.11R | +0.19R | +0.43R | Positive but weaker than unfiltered. The macro filter costs good trades. |
| london_breakout | First break of the Asian range 07-11 UTC, flat by 20:00 | -0.04R | -0.05R | +0.05R | Break-even after costs. Only works in the recent high-volatility regime. |
| london_breakout+macro | + macro filter | -0.03R | -0.08R | +0.05R | Same. |
| trend_breakout | 20-bar H1 breakout with EMA50/200 trend | -0.02R | -0.10R | +0.09R | Costs eat it. |
| trend_breakout+macro | + macro filter | -0.02R | -0.13R | +0.09R | Same. |
| mean_reversion | Bollinger 2.5σ + RSI in low ADX | -0.45R | -0.43R | +0.57R | Few trades; negative historically. |
| trend_pullback | Buy EMA50 pullbacks in uptrend | -0.17R | -0.26R | +0.02R | Negative. Candidate for removal. |

The shadow routes cost nothing to run. Every one of their trades is journaled with full context, so
you can see whether the 2023-26 improvement continues. The allocator flags `flag_promote` when a
route's recency-weighted t-stat exceeds 2.0 (paper trades count 3x).

## Status: TESTED, NOT RUN

### ml_lgbm: LightGBM + triple-barrier labels, purged walk-forward
- 6,508 trades, **-0.21R avg, PF 0.76** across all periods. Win rate 32% vs 33% break-even for 2:1.
- Conclusion: on H1 bars, 25 price/session/macro features carry no edge after costs.
- Worth retrying as **meta-labelling** (predict which `daily_trend`/`london_breakout` signals to take), once the journal has enough trades. Run with `scripts/research.py --routes ml_lgbm` (~4 min).

## Status: EXPERIMENTAL (saved, needs extra installs)

### kronos: Kronos foundation-model forecast
- See the install steps at the top of `goldbot/routes/experimental.py`. Run with `--routes kronos --since 2024-01-01`.
- Independent forex evidence is negative (~50% directional accuracy); test before trusting.

## Ideas queue (not yet built)
1. **Your own setups**: write your discretionary XAU/USD rules as a route. Highest expected value.
2. **Event filter**: no new intraday entries 30 min before/after NFP, CPI, FOMC (needs a calendar feed).
3. **COT positioning extreme filter** on daily_trend (CFTC weekly data).
4. **Volatility targeting** (Carver): size by forecast volatility (GARCH) instead of fixed 0.5% risk.
5. **QuantAgent / TradingAgents context layer**: daily written bias from charts and news, logged next to trades.
6. **Meta-labelling** with LightGBM on journaled trades.
