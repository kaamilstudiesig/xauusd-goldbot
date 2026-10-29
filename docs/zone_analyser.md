# Zone analyser: your discretionary process, automated

## How your process maps to the code

| Your step | Code | File |
|---|---|---|
| Look at recent H1 / H4 charts | Rebuilt every time an H1 bar completes, from the last 72 H1 and 60 H4 **completed** bars | `analyser.refresh_levels` |
| Draw a line through ~all wick highs | Best line through pairs of confirmed swing highs, scored by how many wicks touch it (within 0.35 ATR); lines that candles have closed through are rejected | `levels.fit` |
| Parallel line through candle (body) highs | Same slope, shifted to the median body high of the touching candles: the zone is between the two | `levels.fit` |
| Same for wick lows / body lows | `side="lower"` | `levels.fit` |
| Rectangle box | Same fit with slope forced to 0 (horizontal top and bottom) | `levels.boundaries` |
| Threshold reached → watch the market | Each completed 15m bar is checked against every zone | `analyser.step` |
| FVG, BOS, CHoCH | Streaming swing structure (confirmed fractals), FVG = 3-candle imbalance | `smc.py` |
| Candle types | marubozu (displacement), hammer, shooting star, doji, normal | `smc.candle_type` |
| "Only after one 15m candle closes beyond" | Breakout requires a 15m **close** beyond the wick line + 0.1 ATR buffer | `analyser.step` |
| Current open market | Session filter (default 07:00-18:00 UTC entries), flat by 20:45 UTC | `ZoneParams.session` |

## Triggers (each one a testable variant)

| Trigger | Rule | Stop | Target |
|---|---|---|---|
| `breakout` | Fresh 15m close beyond the wick line (+ real body or BOS when `confirm="smc"`) | below breakout candle / body line | 2R |
| `retest` | After a breakout, price comes back to the broken wick line within 12 bars and a 15m candle closes back in the breakout direction | below the retest candle / body line | 2R |
| `sweep` | Breakout candle closes beyond, then within 4 bars a 15m close comes back inside the wick line (fake-out / liquidity grab) → trade the other way | beyond the sweep extreme | 2R |
| `rejection` | Price reaches the body line, no close beyond; then CHoCH/BOS against the move (+ FVG when `confirm="smc"`, or a rejection candle when `confirm="none"`) | beyond the zone extreme | 2R |

Stops are clipped to 0.8-3.0 x 15m ATR. Costs as in `goldbot/costs.py`.

## Blind testing
`scripts/blind_test.py` feeds bars one at a time. The analyser decides on the close of bar *t* using
only bars <= *t*; the order is filled at the open of *t+1* by the backtest engine.
`tests/test_no_lookahead.py` proves it: the decisions are identical when all future bars are deleted.

Each trade is journaled in `journal/blind.db` (`blind_trades`, `blind_signals`) with the line it
used, the trigger, the structure event, FVGs, the candle type and the session. Charts showing the
lines exactly as the analyser saw them at entry are in `reports/charts/<test>/`.

```bash
.venv/bin/python scripts/blind_test.py --name oct2026 --start 2026-10-01 --end 2026-10-30
scripts/run_hist.sh      # all variants, 2023-01 -> 2025-07, in parallel
```

## Refinement knobs (ZoneParams; defaults = original behaviour)
| Param | Meaning |
|---|---|
| `bias`, `bias_days`, `bias_mode` | daily trend filter from completed UTC days: `"donchian"` (20-day channel state) or `"sma"` |
| `er_min`, `er_days` | trend-strength gate: Kaufman efficiency ratio of daily closes |
| `stop_mode` | `"candle"` (original), `"swing"` (beyond last confirmed 15m swing), `"atr"` |
| `flat_hour=-1`, `max_bars`, `weekend_flat` | hold past the session (time stop in 15m bars), still flat into the weekend |
| `be_r`, `trail_atr` | breakeven / trailing stop (backtester `be_r`, `trail_atr`) |
| `min_touches`, `skip_candles`, `skip_hours`, `days_ok`, `shock_x`/`shock_bars` | entry filters |

## Refinement loop
```bash
.venv/bin/python scripts/signal_pool.py                         # DEV signals scored one by one (gross vs net)
.venv/bin/python scripts/zone_research.py v18_v09_h4only         # DEV + VAL, journaled to journal/blind.db
.venv/bin/python scripts/zone_research.py v18_v09_h4only --holdout [--cost-scale]   # once per final version
.venv/bin/python scripts/zone_findings.py --final v18_v09_h4only
```
Versions live in `scripts/zone_variants.py`. Every run is in `reports/iterations.csv`, and holdout runs are also
in `reports/holdout_log.csv`.

## Results
See `reports/iterations.md` (every version, the conclusion) and `reports/zone_findings.md` (journal breakdowns).
