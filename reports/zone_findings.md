# Zone analyser findings

## Every variant: history vs blind October

                           trades                          win_rate                             avg_r                                pf                           total_r                 
period           2023-01..2025-07 Oct 2026 (blind) 2023-01..2025-07 Oct 2026 (blind) 2023-01..2025-07 Oct 2026 (blind) 2023-01..2025-07 Oct 2026 (blind) 2023-01..2025-07 Oct 2026 (blind)
variant                                                                                                                                                                                   
both_smc                    675.0             22.0             0.39             0.27           -0.089           -0.287             0.85             0.55            -59.8             -6.3
breakout_plain              617.0             19.0             0.39             0.32           -0.055           -0.120             0.91             0.81            -33.7             -2.3
breakout_smc                536.0             18.0             0.41             0.22           -0.025           -0.368             0.96             0.48            -13.3             -6.6
rejection_candle            923.0             39.0             0.33             0.31           -0.223           -0.204             0.68             0.68           -205.6             -7.9
rejection_smc               226.0              5.0             0.37             0.40           -0.175           -0.070             0.69             0.84            -39.6             -0.3
retest                      296.0             12.0             0.38             0.50           -0.087            0.077             0.86             1.15            -25.8              0.9
retest+sweep                503.0             17.0             0.36             0.41           -0.107           -0.069             0.83             0.88            -53.9             -1.2
sweep                       324.0             13.0             0.38             0.31           -0.074           -0.309             0.88             0.50            -24.1             -4.0

## History by year (groups with 15+ trades)

                       trades  win_rate  avg_r    pf  total_r
variant          year                                        
both_smc         2023   298.0      0.37 -0.165  0.73    -49.3
                 2024   290.0      0.40 -0.026  0.95     -7.5
                 2025    87.0      0.44 -0.035  0.94     -3.0
breakout_plain   2023   262.0      0.35 -0.160  0.75    -41.9
                 2024   272.0      0.41  0.021  1.04      5.6
                 2025    83.0      0.43  0.031  1.05      2.6
breakout_smc     2023   230.0      0.37 -0.141  0.77    -32.3
                 2024   234.0      0.43  0.072  1.13     16.7
                 2025    72.0      0.46  0.032  1.05      2.3
rejection_candle 2023   403.0      0.33 -0.243  0.65    -98.1
                 2024   404.0      0.33 -0.194  0.72    -78.2
                 2025   116.0      0.31 -0.253  0.63    -29.4
rejection_smc    2023    96.0      0.36 -0.209  0.63    -20.1
                 2024   101.0      0.39 -0.104  0.81    -10.5
                 2025    29.0      0.34 -0.311  0.47     -9.0
retest           2023   123.0      0.33 -0.232  0.65    -28.6
                 2024   134.0      0.41  0.021  1.03      2.8
                 2025    39.0      0.44 -0.000  1.00     -0.0
retest+sweep     2023   209.0      0.35 -0.153  0.76    -32.0
                 2024   230.0      0.37 -0.055  0.91    -12.8
                 2025    64.0      0.39 -0.143  0.77     -9.1
sweep            2023   136.0      0.40  0.008  1.01      1.1
                 2024   145.0      0.35 -0.138  0.78    -20.0
                 2025    43.0      0.40 -0.120  0.81     -5.2

## History by session (groups with 15+ trades)

                             trades  win_rate  avg_r    pf  total_r
variant          session                                           
both_smc         late_ny       33.0      0.45 -0.116  0.70     -3.8
                 london       274.0      0.36 -0.069  0.90    -19.0
                 ny_overlap   368.0      0.40 -0.101  0.81    -37.0
breakout_plain   late_ny       29.0      0.45 -0.270  0.45     -7.8
                 london       249.0      0.39  0.035  1.05      8.8
                 ny_overlap   339.0      0.39 -0.102  0.82    -34.6
breakout_smc     late_ny       28.0      0.50 -0.062  0.84     -1.7
                 london       202.0      0.40  0.063  1.10     12.7
                 ny_overlap   306.0      0.41 -0.079  0.86    -24.3
rejection_candle late_ny       55.0      0.33 -0.229  0.58    -12.6
                 london       431.0      0.28 -0.280  0.65   -120.6
                 ny_overlap   437.0      0.37 -0.166  0.72    -72.5
rejection_smc    london        96.0      0.32 -0.234  0.67    -22.4
                 ny_overlap   118.0      0.42 -0.135  0.71    -15.9
retest           late_ny       27.0      0.37 -0.201  0.52     -5.4
                 london       118.0      0.36 -0.085  0.88    -10.0
                 ny_overlap   151.0      0.39 -0.069  0.88    -10.4
retest+sweep     late_ny       27.0      0.33 -0.170  0.58     -4.6
                 london       189.0      0.34 -0.108  0.85    -20.4
                 ny_overlap   287.0      0.38 -0.101  0.83    -29.0
sweep            late_ny       15.0      0.47  0.082  1.19      1.2
                 london       106.0      0.33 -0.103  0.86    -10.9
                 ny_overlap   203.0      0.40 -0.071  0.87    -14.4

## History by tf (groups with 15+ trades)

                     trades  win_rate  avg_r    pf  total_r
variant          tf                                        
both_smc         1h   499.0      0.38 -0.100  0.83    -50.1
                 4h   176.0      0.43 -0.055  0.90     -9.8
breakout_plain   1h   455.0      0.37 -0.097  0.85    -44.3
                 4h   162.0      0.44  0.065  1.13     10.6
breakout_smc     1h   398.0      0.40 -0.029  0.95    -11.4
                 4h   138.0      0.43 -0.014  0.97     -1.9
rejection_candle 1h   613.0      0.33 -0.217  0.68   -132.8
                 4h   310.0      0.31 -0.235  0.66    -72.8
rejection_smc    1h   158.0      0.37 -0.183  0.66    -28.9
                 4h    68.0      0.38 -0.157  0.73    -10.7
retest           1h   209.0      0.36 -0.126  0.81    -26.3
                 4h    87.0      0.41  0.006  1.01      0.5
retest+sweep     1h   356.0      0.36 -0.118  0.82    -42.0
                 4h   147.0      0.37 -0.081  0.86    -11.9
sweep            1h   219.0      0.38 -0.080  0.87    -17.6
                 4h   105.0      0.37 -0.062  0.89     -6.5

## History by kind (groups with 15+ trades)

                                trades  win_rate  avg_r    pf  total_r
variant          kind                                                 
both_smc         box_lower        22.0      0.36 -0.305  0.57     -6.7
                 box_upper        32.0      0.38 -0.035  0.94     -1.1
                 channel_lower   297.0      0.41 -0.041  0.93    -12.2
                 channel_upper   324.0      0.37 -0.123  0.80    -39.8
breakout_plain   box_lower        22.0      0.27 -0.506  0.37    -11.1
                 box_upper        30.0      0.43  0.151  1.28      4.5
                 channel_lower   268.0      0.37 -0.115  0.82    -30.8
                 channel_upper   297.0      0.41  0.012  1.02      3.7
breakout_smc     box_lower        19.0      0.42 -0.186  0.72     -3.5
                 box_upper        29.0      0.38 -0.017  0.97     -0.5
                 channel_lower   230.0      0.42 -0.004  0.99     -0.9
                 channel_upper   258.0      0.40 -0.033  0.94     -8.4
rejection_candle box_lower        30.0      0.50  0.072  1.13      2.2
                 box_upper        28.0      0.39  0.059  1.10      1.7
                 channel_lower   439.0      0.32 -0.227  0.67    -99.9
                 channel_upper   426.0      0.31 -0.257  0.63   -109.6
rejection_smc    channel_lower   116.0      0.41 -0.118  0.77    -13.7
                 channel_upper   100.0      0.33 -0.233  0.62    -23.3
retest           box_lower        17.0      0.24 -0.516  0.34     -8.8
                 box_upper        23.0      0.43  0.209  1.37      4.8
                 channel_lower   112.0      0.35 -0.234  0.62    -26.2
                 channel_upper   144.0      0.41  0.030  1.05      4.4
retest+sweep     box_lower        25.0      0.28 -0.231  0.64     -5.8
                 box_upper        39.0      0.44  0.185  1.33      7.2
                 channel_lower   200.0      0.34 -0.195  0.70    -38.9
                 channel_upper   239.0      0.38 -0.069  0.89    -16.4
sweep            box_lower        15.0      0.40  0.256  1.48      3.8
                 box_upper        23.0      0.43  0.226  1.48      5.2
                 channel_lower   136.0      0.38 -0.149  0.76    -20.3
                 channel_upper   150.0      0.37 -0.086  0.86    -12.8

## History by candle (groups with 15+ trades)

                                trades  win_rate  avg_r    pf  total_r
variant          candle                                               
both_smc         bear_marubozu   186.0      0.40 -0.065  0.89    -12.0
                 bear_normal     125.0      0.36 -0.159  0.75    -19.8
                 bull_marubozu   198.0      0.35 -0.170  0.72    -33.6
                 bull_normal     150.0      0.44  0.025  1.05      3.7
breakout_plain   bear_marubozu   142.0      0.40 -0.050  0.92     -7.1
                 bear_normal     125.0      0.34 -0.223  0.67    -27.9
                 bull_marubozu   161.0      0.35 -0.181  0.71    -29.2
                 bull_normal     148.0      0.48  0.206  1.39     30.5
                 doji             17.0      0.24 -0.481  0.43     -8.2
breakout_smc     bear_marubozu   153.0      0.42  0.002  1.00      0.3
                 bear_normal      93.0      0.41 -0.082  0.86     -7.6
                 bull_marubozu   174.0      0.36 -0.162  0.74    -28.2
                 bull_normal     112.0      0.46  0.155  1.28     17.3
rejection_candle bear_marubozu   298.0      0.31 -0.256  0.63    -76.2
                 bear_normal      49.0      0.39 -0.020  0.96     -1.0
                 bull_marubozu   297.0      0.35 -0.154  0.76    -45.6
                 bull_normal      58.0      0.34 -0.298  0.56    -17.3
                 hammer          112.0      0.29 -0.320  0.60    -35.8
                 shooting_star   107.0      0.32 -0.288  0.64    -30.8
rejection_smc    bear_marubozu    55.0      0.35 -0.150  0.74     -8.2
                 bear_normal      45.0      0.29 -0.323  0.49    -14.5
                 bull_marubozu    56.0      0.34 -0.188  0.66    -10.5
                 bull_normal      56.0      0.48 -0.077  0.84     -4.3
retest           bear_marubozu    18.0      0.28 -0.191  0.69     -3.4
                 bear_normal      71.0      0.39 -0.170  0.72    -12.1
                 bull_marubozu    22.0      0.27 -0.175  0.74     -3.8
                 bull_normal      93.0      0.41  0.048  1.08      4.5
                 doji             61.0      0.36 -0.166  0.74    -10.1
                 hammer           18.0      0.56  0.392  1.83      7.1
retest+sweep     bear_marubozu    71.0      0.42  0.165  1.33     11.7
                 bear_normal     132.0      0.36 -0.214  0.66    -28.3
                 bull_marubozu    67.0      0.31 -0.227  0.65    -15.2
                 bull_normal     147.0      0.39  0.006  1.01      0.8
                 doji             53.0      0.34 -0.175  0.74     -9.3
                 hammer           17.0      0.41 -0.028  0.96     -0.5
                 shooting_star    16.0      0.12 -0.825  0.08    -13.2
sweep            bear_marubozu    70.0      0.40  0.076  1.14      5.3
                 bear_normal      99.0      0.37 -0.129  0.79    -12.8
                 bull_marubozu    67.0      0.34 -0.262  0.58    -17.5
                 bull_normal      77.0      0.43  0.092  1.16      7.1
