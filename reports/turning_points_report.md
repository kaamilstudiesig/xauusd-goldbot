# Turning points: why gold turns, and can it be predicted?

4418 real turns (swing >= 3 ATR afterwards) on 15m XAU/USD, 2022-11 -> 2026-10. 9.8% of candles are 'near a turn' (within 1 ATR, the turn forming in the window -2..+4 candles).

## 1. Why: conditions at real turns vs ordinary candles

Lift = how many times more common the condition is at a real turn than at a random candle. Most of these are only visible AT the turn candle (a sweep, a wick), so they explain turns, they don't forecast them.

### Swing highs

     condition  at_turns  all_candles  lift  median_swing_after_atr
     shock_bar     0.065        0.008  8.52                     5.7
  stretched_bb     0.223        0.061  3.63                     5.3
   rsi_extreme     0.206        0.061  3.38                     5.0
rejection_wick     0.358        0.158  2.27                     5.2
   news_window     0.164        0.087  1.89                     5.1
    swept_asia     0.465        0.380  1.22                     5.1
swept_prev_day     0.498        0.425  1.17                     5.1
   cot_crowded     0.183        0.191  0.96                     5.2
 near_round_25     0.171        0.183  0.94                     5.0

### Swing lows

     condition  at_turns  all_candles  lift  median_swing_after_atr
     shock_bar     0.061        0.008  7.92                     5.4
  stretched_bb     0.273        0.055  5.00                     5.1
   rsi_extreme     0.191        0.043  4.50                     5.2
rejection_wick     0.382        0.165  2.31                     5.0
   news_window     0.162        0.087  1.86                     5.3
    swept_asia     0.435        0.327  1.33                     5.0
swept_prev_day     0.424        0.363  1.17                     5.0
 near_round_25     0.198        0.183  1.09                     5.0
   cot_crowded     0.020        0.023  0.87                     6.5

### By session

                 turns  median_swing_atr
session    type                         
asia       high    632               5.2
           low     623               5.3
late_ny    high    161               4.6
           low     200               4.8
london     high    499               5.4
           low     501               5.3
ny_overlap high    784               5.1
           low     792               5.1
rollover   high    133               5.1
           low      93               5.3

asia          0.348
london        0.218
ny_overlap    0.217
late_ny       0.172
rollover      0.045

## 2. Can turns be predicted from what's known at the candle?

AUC: 0.5 = coin flip, 0.6 = weak but real, 0.7+ = useful.

                              target  base_rate_val  AUC_val
                              y_turn          0.103    0.777
                                y_up          0.044    0.921
                                y_dn          0.059    0.867
direction (given a turn): up vs down          0.428    0.998

Careful: these AUCs are inflated. 'Near a turn' mostly means 'near the recent high/low', which is visible in real time, but most such candles are NOT turns. The question that matters is the next one.

### The real question: at a fresh extreme, turn or continue?

                 question period  candles  turn_rate   AUC
at a 4h high: turns down?    val     1384      0.185 0.562
   at a 4h low: turns up?    val      783      0.223 0.573

What predicts THAT a turn is near (timing model):

dist_hi16        0.194
dist_lo16        0.151
bb_pos           0.066
range_atr        0.052
rsi              0.049
r4               0.046
i_range_today    0.037
hour             0.033
r16              0.030
dist_lo96        0.024
dist_hi96        0.018
i_rv_ratio       0.016

## 3. Trading the predictions (after costs, one position at a time)

Long when the up-turn score is in its top quantile (short likewise), 07-18 UTC, stop beyond the last 4 candles, target 2R, max 8h, flat 20:45 UTC. Quantile chosen on VAL.

VAL (Jan-Jul 2025):

 quantile  trades   win  avg_r   pf  total_r
     0.95     467 0.330 -0.195 0.77    -91.1
     0.97     249 0.345 -0.159 0.81    -39.7
     0.98     134 0.381 -0.041 0.95     -5.6
     0.99      53 0.264 -0.373 0.58    -19.8

## Verdict
- Turns cluster at visible extremes (stretched Bollinger bands, RSI extremes, rejection wicks, news shocks), so a model
  finds "near a turn" easily (inflated AUC 0.78-0.92).
- The question that matters, at a fresh 4h extreme will price turn or continue, is barely predictable: AUC 0.56-0.57.
- Trading it loses at every threshold on VAL (-0.04R to -0.37R after costs). HOLD was deliberately NOT run: the idea
  failed validation, so spending a look at the newest months would only use them up.
- Useful output: the WHY tables above (which conditions accompany real turns), and `journal/turning_points.parquet`
  (every turn since Nov 2022 with its conditions) for your own study.
