# Blind test: hist_rejection_candle (2023-01-01 -> 2025-07-11)

Each 15m bar was revealed one at a time; orders were filled on later bars with realistic costs.

## Variants

         variant  signals  trades  trades_per_yr  win_rate  avg_r   pf  sharpe  cagr  max_dd  total_r
rejection_candle     1244     923          366.4     0.325 -0.223 0.68   -3.16 -0.34 -0.6708   -205.6

## rejection_candle: by trigger

           count  mean     sum
trigger                       
rejection    923 -0.22 -205.65

## rejection_candle: by session

            count  mean
session                
late_ny        55 -0.23
london        431 -0.28
ny_overlap    437 -0.17
