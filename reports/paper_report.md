# Paper trading report

Last run: 2026-11-03T03:02:45.885970+00:00 | last bar 2026-11-03 02:45:00+00:00 | basis 0.00 spot=3944.62 last_bar_close=3950.59
Equity: 9,978.71 (closed +0.00, open -21.29)

## Route status (backtest + paper, recency-weighted)
                route  weight  w_avg_r  eff_n           w_t       status
          daily_trend     1.0    0.734   19.8  1.940000e+00       active
     daily_trend_long     0.0    0.951   14.2  1.800000e+00       shadow
      london_breakout     0.0    0.090  173.0  1.500000e+00       shadow
       trend_breakout     0.0    0.191  235.5  1.620000e+00       shadow
       mean_reversion     0.0    0.328   14.2  7.500000e-01       shadow
london_breakout+macro     0.0    0.122  124.4  1.720000e+00       shadow
 trend_breakout+macro     0.0    0.150  203.6  1.170000e+00       shadow
    daily_trend+macro     0.0    0.495   20.4  1.370000e+00       shadow
       trend_pullback     0.0   -0.080  149.1 -7.100000e-01       shadow
             zone_v18     0.0    2.997    1.0  6.748705e+15 flag_promote

## Closed trades by route
                                 trades  win_rate  avg_r  total_r      pnl
portfolio route                                                           
False     london_breakout             1       1.0  0.834    0.834   41.677
          london_breakout+macro       1       1.0  0.834    0.834   41.677
          trend_breakout              1       1.0  2.458    2.458  122.916
          zone_v18                    1       1.0  2.997    2.997  149.851

## Open positions
               route  portfolio                entry_time  side    entry          sl  tp        pnl
trend_breakout+macro      False 2026-10-30 04:00:00+00:00    -1 3992.903 4022.321288 NaN 199.408273
         daily_trend       True 2026-10-30 20:00:00+00:00    -1 3882.699 4043.289012 NaN -21.293822
   daily_trend+macro      False 2026-10-30 20:00:00+00:00    -1 3882.699 4043.289012 NaN   2.217137

Total closed trades: 4. Judge routes after 100+ trades, not after a month.