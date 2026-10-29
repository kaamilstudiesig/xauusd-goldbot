# Blind test: hist_rejection_smc (2023-01-01 -> 2025-07-11)

Each 15m bar was revealed one at a time; orders were filled on later bars with realistic costs.

## Variants

      variant  signals  trades  trades_per_yr  win_rate  avg_r   pf  sharpe    cagr  max_dd  total_r
rejection_smc      245     226           89.7     0.372 -0.175 0.68   -1.38 -0.0768 -0.1947    -39.6

## rejection_smc: by trigger

           count  mean    sum
trigger                      
rejection    226 -0.18 -39.62

## rejection_smc: by session

            count  mean
session                
late_ny        12 -0.10
london         96 -0.23
ny_overlap    118 -0.14
