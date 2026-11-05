# Paper trading report

Last run: 2026-11-05T10:43:49.062847+00:00 | last bar 2026-11-05 10:15:00+00:00 | basis 0.00 spot=4127.46 last_bar_close=4124.44
Equity: 9,949.75 (closed -50.25, open +0.00)

## Route status (backtest + paper, recency-weighted)
                route  weight  w_avg_r  eff_n   w_t status
          daily_trend     1.0    0.336   12.1  0.71 active
     daily_trend_long     0.0    0.951   14.2  1.80 shadow
      london_breakout     0.0    0.056  156.3  0.87 shadow
       trend_breakout     0.0    0.191  235.5  1.62 shadow
       mean_reversion     0.0    0.328   14.2  0.75 shadow
london_breakout+macro     0.0    0.122  124.4  1.72 shadow
 trend_breakout+macro     0.0    0.150  203.6  1.17 shadow
    daily_trend+macro     0.0    0.495   20.4  1.37 shadow
       trend_pullback     0.0   -0.080  149.1 -0.71 shadow
             zone_v18     0.0    2.997    1.0  0.00 shadow

## Closed trades by route
                                 trades  win_rate  avg_r  total_r      pnl
portfolio route                                                           
False     london_breakout             2       0.5 -0.086   -0.173   -8.843
          london_breakout+macro       1       1.0  0.834    0.834   41.677
          trend_breakout              1       1.0  2.458    2.458  122.916
          zone_v18                    1       1.0  2.997    2.997  149.851
True      daily_trend                 1       0.0 -1.005   -1.005  -50.250

## Open positions
               route  portfolio                entry_time  side    entry          sl  tp        pnl
trend_breakout+macro      False 2026-10-30 04:00:00+00:00    -1 3992.903 4022.321288 NaN 199.408273
   daily_trend+macro      False 2026-10-30 20:00:00+00:00    -1 3882.699 4043.289012 NaN   2.217137
      trend_breakout      False 2026-11-05 04:00:00+00:00     1 4144.083 4105.571187 NaN -26.534932
trend_breakout+macro      False 2026-11-05 04:00:00+00:00     1 4144.083 4105.571187 NaN -26.212736

Total closed trades: 6. Judge routes after 100+ trades, not after a month.