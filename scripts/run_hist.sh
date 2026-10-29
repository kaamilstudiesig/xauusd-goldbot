#!/usr/bin/env bash
# Run each zone-analyser variant over 2023-01 -> 2025-07 in parallel (4 at a time).
cd "$(dirname "$0")/.."
VARS="both_smc breakout_smc breakout_plain rejection_smc rejection_candle retest sweep retest+sweep"
printf "%s\n" $VARS | xargs -P 4 -I{} sh -c '.venv/bin/python scripts/blind_test.py --name "hist_{}" --start 2023-01-01 --end 2025-07-11 --no-charts --variants "{}" --chart-variant "{}" > "reports/tmp/hist_{}.log" 2>&1'
echo done
