# Meta-label v2: quant + forecast features

Setups: 7806 (DEV 4271, VAL 1116, HOLD 2419). Target: reached 3R before the stop.

## VAL (Jan-Jul 2025): each feature set trained on DEV only

Baseline, all VAL setups: n 1116, avg -0.074R, PF 0.9

     features  n_features top   n  win_3R  avg_r3   pf  total_r3  pf_no_overlap
   base+macro          33 10% 112   0.393   0.224 1.38      25.0           1.14
base+intraday          33 10% 112   0.321   0.143 1.22      16.0           0.98
 base+chronos          24 10% 112   0.304   0.048 1.07       5.4           1.18
     base+cot          29 30% 335   0.316   0.030 1.04      10.1           1.19
          all          56 10% 112   0.295   0.007 1.01       0.8           1.35
         base          21 10% 112   0.295  -0.046 0.94      -5.1           0.84

Chosen on VAL (rule: best avg R): **base+macro**, top 10% of setups by model score.

Top features of the chosen model:

m_dxy_chg20_dir    0.082
m_be_chg20         0.074
m_vix_z            0.069
atr15              0.068
sl_atr             0.063
m_dxy_chg5         0.062
m_ry_chg20_dir     0.059
m_dxy_chg5_dir     0.056
m_dxy_chg20        0.050
m_ry_chg5_dir      0.048
er                 0.045
m_vix              0.043

## HOLD (Aug 2025 -> Oct 2026): run once for the chosen set

                     group    n  win_3R  avg_r3   pf  total_r3
           all HOLD setups 2419   0.260  -0.099 0.87    -240.5
               model picks  241   0.303  -0.059 0.92     -14.1
model picks, one at a time  126   0.325   0.035 1.05       4.4

One-at-a-time avg R 90% bootstrap interval: -0.208 to +0.293.

By month (one at a time):

          size  mean    sum
bar_time                   
2025-08      9 -0.10  -0.94
2025-09      3 -0.44  -1.31
2025-10      4  0.52   2.09
2025-11     16  0.71  11.35
2025-12      8  0.45   3.60
2026-01      4  0.89   3.54
2026-02      6  0.07   0.43
2026-03      5 -0.21  -1.06
2026-04     12 -0.35  -4.15
2026-05     10  0.11   1.12
2026-06      7  0.46   3.23
2026-07      7 -0.17  -1.21
2026-08     11 -0.12  -1.34
2026-09     12 -0.66  -7.88
2026-10     12 -0.26  -3.12

**Target (PF >= 1.2 and avg R > 0, one at a time): NOT MET** (PF 1.05, avg +0.035R, 126 trades).

HOLD looks so far: 1 (`meta_v2_holdout_log.csv`).
