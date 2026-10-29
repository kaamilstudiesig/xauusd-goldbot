# Blind test: oct2026_wide (2026-10-01 -> 2026-10-30)

Each 15m bar was revealed one at a time; orders were filled on later bars with realistic costs.

## Variants

          variant  signals  trades  trades_per_yr  win_rate  avg_r   pf  sharpe    cagr  max_dd  total_r
breakout_smc_wide       19      18          234.8     0.222 -0.344 0.46    -4.2 -0.3343  -0.043     -6.2

## breakout_smc_wide: by trigger

          count  mean   sum
trigger                    
breakout     18 -0.34 -6.19

## breakout_smc_wide: by session

            count  mean
session                
late_ny         3 -0.40
london          9 -0.68
ny_overlap      6  0.19

## breakout_smc_wide: every trade

               entry_time  side  trigger tf    kind   entry      sl      tp    exit      reason     r            structure        candle    session
2026-10-02 07:15:00+00:00     1 breakout 1h channel 4198.76 4183.53 4229.21 4183.33        stop -1.02                        bull_normal     london
2026-10-02 11:15:00+00:00     1 breakout 4h channel 4198.66 4166.99 4262.01 4166.79        stop -1.01                      bull_marubozu     london
2026-10-02 15:45:00+00:00    -1 breakout 1h     box 4144.01 4172.94 4086.15 4143.31 session_end  0.02                        bear_normal ny_overlap
2026-10-05 08:15:00+00:00     1 breakout 4h channel 4176.69 4142.90 4244.27 4142.70        stop -1.01                      bull_marubozu     london
2026-10-06 08:30:00+00:00     1 breakout 1h channel 4152.93 4138.55 4181.69 4181.69      target  2.00   BOS bull @ 4149.83 bull_marubozu     london
2026-10-07 12:30:00+00:00    -1 breakout 1h channel 4084.82 4118.84 4016.79 4119.04        stop -1.01   BOS bear @ 4113.87 bear_marubozu ny_overlap
2026-10-14 09:30:00+00:00    -1 breakout 1h     box 4148.67 4162.53 4120.96 4162.73        stop -1.02                        bear_normal     london
2026-10-14 12:45:00+00:00    -1 breakout 1h channel 4099.67 4144.52 4009.98 4112.17 session_end -0.28 CHOCH bear @ 4143.72 bear_marubozu ny_overlap
2026-10-16 07:15:00+00:00     1 breakout 1h channel 4193.27 4176.54 4226.74 4176.34        stop -1.02                      bull_marubozu     london
2026-10-16 17:15:00+00:00    -1 breakout 1h channel 4165.92 4185.15 4127.46 4168.52 session_end -0.14                      bear_marubozu    late_ny
2026-10-20 14:30:00+00:00     1 breakout 1h channel 4164.35 4138.88 4215.27 4138.68        stop -1.01                      bull_marubozu ny_overlap
2026-10-21 07:30:00+00:00     1 breakout 1h channel 4134.59 4120.81 4162.15 4120.61        stop -1.02                      bull_marubozu     london
2026-10-21 10:45:00+00:00     1 breakout 1h channel 4138.49 4124.82 4165.83 4124.62        stop -1.02 CHOCH bull @ 4135.69 bull_marubozu     london
2026-10-22 12:00:00+00:00    -1 breakout 1h channel 4066.79 4084.63 4031.10 4084.83        stop -1.02                        bear_normal     london
2026-10-22 14:00:00+00:00    -1 breakout 1h channel 4063.69 4085.78 4019.49 4032.29 session_end  1.42   BOS bear @ 4064.84 shooting_star ny_overlap
2026-10-26 17:15:00+00:00     1 breakout 1h channel 4030.24 4016.23 4058.27 4016.03        stop -1.02 CHOCH bull @ 4025.24   bull_normal    late_ny
2026-10-27 13:45:00+00:00     1 breakout 1h channel 4031.63 4016.35 4062.18 4062.18      target  2.00                        bull_normal ny_overlap
2026-10-29 18:00:00+00:00    -1 breakout 1h channel 4004.45 4020.99 3971.37 4005.00         end -0.04   BOS bear @ 4007.50 bear_marubozu    late_ny
