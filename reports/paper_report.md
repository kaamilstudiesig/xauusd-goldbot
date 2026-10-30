# Paper trading report

Last run: 2026-10-30T12:41:19.816055+00:00 | last bar 2026-10-30 12:15:00+00:00 | basis 0.00 spot=3962.12 last_bar_close=3965.07
Equity: 10,000.00 (closed +0.00, open +0.00)

## Route status (backtest + paper, recency-weighted)
                route  weight  w_avg_r  eff_n   w_t status
          daily_trend     1.0    0.734   19.8  1.94 active
     daily_trend_long     0.0    0.951   14.2  1.80 shadow
      london_breakout     0.0    0.065  196.9  1.16 shadow
       trend_breakout     0.0    0.136  258.6  1.22 shadow
       mean_reversion     0.0    0.328   14.2  0.75 shadow
london_breakout+macro     0.0    0.091  145.4  1.38 shadow
 trend_breakout+macro     0.0    0.150  203.6  1.17 shadow
    daily_trend+macro     0.0    0.495   20.4  1.37 shadow
       trend_pullback     0.0   -0.080  149.1 -0.71 shadow
             zone_v18     0.0    0.000    0.0  0.00 shadow

## Open positions
                route  portfolio                entry_time  side    entry          sl          tp       pnl
       trend_breakout      False 2026-10-30 04:00:00+00:00    -1 3992.903 4022.321288         NaN 44.329568
 trend_breakout+macro      False 2026-10-30 04:00:00+00:00    -1 3992.903 4022.321288         NaN 44.329568
      london_breakout      False 2026-10-30 08:00:00+00:00    -1 3971.454 4016.843896 3933.550000  5.103559
london_breakout+macro      False 2026-10-30 08:00:00+00:00    -1 3971.454 4016.843896 3933.550000  5.103559
             zone_v18      False 2026-10-30 10:15:00+00:00    -1 3983.480 4007.026932 3912.839204 38.932885

Total closed trades: 0. Judge routes after 100+ trades, not after a month.