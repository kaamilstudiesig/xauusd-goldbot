# Blind test: hist_breakout_smc (2023-01-01 -> 2025-07-11)

Each 15m bar was revealed one at a time; orders were filled on later bars with realistic costs.

## Variants

     variant  signals  trades  trades_per_yr  win_rate  avg_r   pf  sharpe    cagr  max_dd  total_r
breakout_smc      593     536          212.8     0.409 -0.025 0.95   -0.26 -0.0304 -0.2022    -13.3

## breakout_smc: by trigger

          count  mean    sum
trigger                     
breakout    536 -0.02 -13.27

## breakout_smc: by session

            count  mean
session                
late_ny        28 -0.06
london        202  0.06
ny_overlap    306 -0.08
