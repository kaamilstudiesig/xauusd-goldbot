# Paper trading report

Last run: 2026-11-18T02:50:09.001771+00:00 | last bar 2026-11-18 02:30:00+00:00 | basis 0.00 spot=3796.65 last_bar_close=3800.18
Equity: 9,949.75 (closed -50.25, open +0.00)

## Route status (backtest + paper, recency-weighted)
                route  weight  w_avg_r  eff_n     w_t       status
          daily_trend     1.0    0.336   12.1    0.71       active
     daily_trend_long     0.0    0.951   14.2    1.80       shadow
      london_breakout     0.0    0.096  134.5    1.40       shadow
       trend_breakout     0.0    0.184  183.1    1.38       shadow
       mean_reversion     0.0    0.328   14.2    0.75       shadow
london_breakout+macro     0.0    0.169  101.1    2.19 flag_promote
 trend_breakout+macro     0.0    0.146  146.3    0.97       shadow
    daily_trend+macro     0.0    0.495   20.4    1.37       shadow
       trend_pullback     0.0   -0.080  149.1   -0.71       shadow
             zone_v18     0.0    2.994    2.0 1335.24 flag_promote

## Closed trades by route
                                 trades  win_rate  avg_r  total_r      pnl
portfolio route                                                           
False     london_breakout             4      0.75  0.321    1.282   63.974
          london_breakout+macro       3      1.00  0.763    2.289  114.426
          trend_breakout              5      0.40  0.577    2.884  143.055
          trend_breakout+macro        4      0.25  0.106    0.426   19.895
          zone_v18                    2      1.00  2.994    5.988  301.626
True      daily_trend                 1      0.00 -1.005   -1.005  -50.250

## Open positions
               route  portfolio                entry_time  side    entry          sl  tp        pnl
trend_breakout+macro      False 2026-10-30 04:00:00+00:00    -1 3992.903 4022.321288 NaN 199.408273
   daily_trend+macro      False 2026-10-30 20:00:00+00:00    -1 3882.699 4043.289012 NaN   2.217137
      trend_breakout      False 2026-11-18 01:00:00+00:00    -1 3815.277 3848.639437 NaN   9.382249
trend_breakout+macro      False 2026-11-18 01:00:00+00:00    -1 3815.277 3848.639437 NaN   9.268326

Total closed trades: 19. Judge routes after 100+ trades, not after a month.