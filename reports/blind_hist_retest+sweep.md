# Blind test: hist_retest+sweep (2023-01-01 -> 2025-07-11)

Each 15m bar was revealed one at a time; orders were filled on later bars with realistic costs.

## Variants

     variant  signals  trades  trades_per_yr  win_rate  avg_r   pf  sharpe    cagr  max_dd  total_r
retest+sweep      642     503          199.7     0.364 -0.107 0.82   -1.08 -0.1051  -0.259    -53.9

## retest+sweep: by trigger

         count  mean    sum
trigger                    
retest     251 -0.11 -28.46
sweep      252 -0.10 -25.45

## retest+sweep: by session

            count  mean
session                
late_ny        27 -0.17
london        189 -0.11
ny_overlap    287 -0.10
