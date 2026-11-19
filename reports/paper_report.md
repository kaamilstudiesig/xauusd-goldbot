# Paper trading report

Last run: 2026-11-19T02:46:39.070115+00:00 | last bar 2026-11-19 02:30:00+00:00 | basis 0.00 spot=3733.71 last_bar_close=3735.31
Equity: 9,941.40 (closed -50.25, open -8.35)

## Route status (backtest + paper, recency-weighted)
                route  weight  w_avg_r  eff_n     w_t       status
          daily_trend     1.0    0.336   12.1    0.71       active
     daily_trend_long     0.0    0.951   14.2    1.80       shadow
      london_breakout     0.0    0.120  127.1    1.70       shadow
       trend_breakout     0.0    0.184  183.1    1.38       shadow
       mean_reversion     0.0    0.328   14.2    0.75       shadow
london_breakout+macro     0.0    0.198   94.3    2.48 flag_promote
 trend_breakout+macro     0.0    0.146  146.3    0.97       shadow
    daily_trend+macro     0.0    0.495   20.4    1.37       shadow
       trend_pullback     0.0   -0.080  149.1   -0.71       shadow
             zone_v18     0.0    2.994    2.0 1335.24 flag_promote

## Closed trades by route
                                 trades  win_rate  avg_r  total_r      pnl
portfolio route                                                           
False     london_breakout             5      0.80  0.440    2.201  110.190
          london_breakout+macro       4      1.00  0.802    3.207  160.526
          trend_breakout              5      0.40  0.577    2.884  143.055
          trend_breakout+macro        4      0.25  0.106    0.426   19.895
          zone_v18                    2      1.00  2.994    5.988  301.626
True      daily_trend                 1      0.00 -1.005   -1.005  -50.250

## Open positions
               route  portfolio                entry_time  side    entry          sl  tp        pnl
trend_breakout+macro      False 2026-10-30 04:00:00+00:00    -1 3992.903 4022.321288 NaN 199.408273
   daily_trend+macro      False 2026-10-30 20:00:00+00:00    -1 3882.699 4043.289012 NaN   2.217137
      trend_breakout      False 2026-11-18 01:00:00+00:00    -1 3815.277 3848.639437 NaN  92.792555
trend_breakout+macro      False 2026-11-18 01:00:00+00:00    -1 3815.277 3848.639437 NaN  91.665838
         daily_trend       True 2026-11-18 20:00:00+00:00    -1 3723.386 3907.205534 NaN  -8.348136
   daily_trend+macro      False 2026-11-18 20:00:00+00:00    -1 3723.386 3907.205534 NaN  -8.390297

Total closed trades: 21. Judge routes after 100+ trades, not after a month.