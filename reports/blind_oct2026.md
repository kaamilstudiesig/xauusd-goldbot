# Blind test: oct2026 (2026-10-01 -> 2026-10-30)

Each 15m bar was revealed one at a time; orders were filled on later bars with realistic costs.

## Variants

         variant  signals  trades  trades_per_yr  win_rate  avg_r   pf  sharpe    cagr  max_dd  total_r
 sr_breakout_smc       15      14          182.6     0.214 -0.480 0.36   -4.93 -0.3564 -0.0404     -6.7
sr_rejection_smc        3       3           39.1     0.000 -0.805 0.00   -4.63 -0.1461 -0.0123     -2.4
       sr_retest        8       8          104.4     0.250 -0.164 0.75   -1.45 -0.0838 -0.0144     -1.3

## sr_rejection_smc: by trigger

           count  mean   sum
trigger                     
rejection      3  -0.8 -2.41

## sr_rejection_smc: by session

            count  mean
session                
late_ny         1 -0.01
london          1 -1.02
ny_overlap      1 -1.38

## sr_rejection_smc: every trade

               entry_time  side   trigger tf kind   entry      sl      tp    exit      reason     r            structure        candle    session
2026-10-01 17:45:00+00:00     1 rejection 1h  sr1 4186.67 4161.44 4237.14 4186.37 session_end -0.01 CHOCH bull @ 4185.17 shooting_star    late_ny
2026-10-16 14:00:00+00:00     1 rejection 1h  sr1 4193.47 4167.01 4246.40 4156.97    gap_stop -1.38 CHOCH bull @ 4189.77   bull_normal ny_overlap
2026-10-29 12:00:00+00:00    -1 rejection 1h  sr1 4016.75 4031.82 3986.61 4032.02        stop -1.02 CHOCH bear @ 4022.90 bear_marubozu     london
