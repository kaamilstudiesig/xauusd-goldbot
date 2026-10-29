# Blind test: hist_breakout_smc_wide (2023-01-01 -> 2025-07-11)

Each 15m bar was revealed one at a time; orders were filled on later bars with realistic costs.

## Variants

          variant  signals  trades  trades_per_yr  win_rate  avg_r   pf  sharpe    cagr  max_dd  total_r
breakout_smc_wide      593     523          207.6     0.421 -0.022 0.95   -0.24 -0.0259 -0.1756    -11.3

## breakout_smc_wide: by trigger

          count  mean    sum
trigger                     
breakout    523 -0.02 -11.27

## breakout_smc_wide: by session

            count  mean
session                
late_ny        27 -0.06
london        201  0.03
ny_overlap    295 -0.05
