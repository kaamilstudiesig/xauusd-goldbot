# Paper trading report

Last run: 2026-11-27T11:59:55.207078+00:00 | last bar 2026-11-27 11:30:00+00:00 | basis 0.00 spot=3672.69 last_bar_close=3673.90
Equity: 9,963.47 (closed -36.53, open +0.00)

## Route status (backtest + paper, recency-weighted)
                route  weight  w_avg_r  eff_n     w_t       status
          daily_trend     1.0    0.324   11.0    0.73       active
     daily_trend_long     0.0    0.951   14.2    1.80       shadow
      london_breakout     0.0    0.120  127.1    1.70       shadow
       trend_breakout     0.0    0.348  168.8    2.24 flag_promote
       mean_reversion     0.0    0.328   14.2    0.75       shadow
london_breakout+macro     0.0    0.198   94.3    2.48 flag_promote
 trend_breakout+macro     0.0    0.348  133.1    1.93       shadow
    daily_trend+macro     0.0    0.446   12.5    1.10       shadow
       trend_pullback     0.0   -0.080  149.1   -0.71       shadow
             zone_v18     0.0    2.994    2.0 1335.24 flag_promote

## Closed trades by route
                                 trades  win_rate  avg_r  total_r      pnl
portfolio route                                                           
False     daily_trend+macro           1     1.000  0.276    0.276   13.787
          london_breakout             5     0.800  0.440    2.201  110.190
          london_breakout+macro       4     1.000  0.802    3.207  160.526
          trend_breakout              7     0.571  1.557   10.902  551.548
          trend_breakout+macro        6     0.500  1.407    8.443  423.428
          zone_v18                    2     1.000  2.994    5.988  301.626
True      daily_trend                 2     0.500 -0.365   -0.729  -36.532

## Open positions
               route  portfolio                entry_time  side    entry          sl  tp        pnl
trend_breakout+macro      False 2026-10-30 04:00:00+00:00    -1 3992.903 4022.321288 NaN 199.408273
   daily_trend+macro      False 2026-10-30 20:00:00+00:00    -1 3882.699 4043.289012 NaN   2.217137

Total closed trades: 27. Judge routes after 100+ trades, not after a month.