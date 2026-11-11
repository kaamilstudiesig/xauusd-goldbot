# Paper trading report

Last run: 2026-11-11T01:11:49.848504+00:00 | last bar 2026-11-11 00:45:00+00:00 | basis 0.00 spot=4031.28 last_bar_close=4032.99
Equity: 9,949.75 (closed -50.25, open +0.00)

## Route status (backtest + paper, recency-weighted)
                route  weight  w_avg_r  eff_n           w_t       status
          daily_trend     1.0    0.336   12.1  7.100000e-01       active
     daily_trend_long     0.0    0.951   14.2  1.800000e+00       shadow
      london_breakout     0.0    0.075  143.8  1.130000e+00       shadow
       trend_breakout     0.0    0.147  203.7  1.180000e+00       shadow
       mean_reversion     0.0    0.328   14.2  7.500000e-01       shadow
london_breakout+macro     0.0    0.144  110.5  1.940000e+00       shadow
 trend_breakout+macro     0.0    0.097  167.0  7.000000e-01       shadow
    daily_trend+macro     0.0    0.495   20.4  1.370000e+00       shadow
       trend_pullback     0.0   -0.080  149.1 -7.100000e-01       shadow
             zone_v18     0.0    2.997    1.0  6.748705e+15 flag_promote

## Closed trades by route
                                 trades  win_rate  avg_r  total_r      pnl
portfolio route                                                           
False     london_breakout             3     0.667  0.169    0.507   25.125
          london_breakout+macro       2     1.000  0.757    1.513   75.675
          trend_breakout              3     0.333  0.300    0.899   44.110
          trend_breakout+macro        2     0.000 -0.780   -1.560  -77.849
          zone_v18                    1     1.000  2.997    2.997  149.851
True      daily_trend                 1     0.000 -1.005   -1.005  -50.250

## Open positions
               route  portfolio                entry_time  side    entry          sl  tp        pnl
trend_breakout+macro      False 2026-10-30 04:00:00+00:00    -1 3992.903 4022.321288 NaN 199.408273
   daily_trend+macro      False 2026-10-30 20:00:00+00:00    -1 3882.699 4043.289012 NaN   2.217137

Total closed trades: 12. Judge routes after 100+ trades, not after a month.