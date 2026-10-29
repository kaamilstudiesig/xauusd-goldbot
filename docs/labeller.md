# Teaching the system your judgement

The analyser finds every line break, retest, fake-out and rejection: 7,806 candidate setups from
2023 to today. Taken blindly they lose (about −0.12R each after costs). What you add as a trader is
the **filter**: which of these you'd actually take. The labeller captures that filter so it can be
measured and automated.

## 1. Label
```bash
.venv/bin/python scripts/labeller.py          # open http://127.0.0.1:8765
```
Each screen shows one setup at the close of its signal candle: H1 context on top, 15m below,
the lines exactly as the analyser drew them (the triggering line in orange), and the proposed stop and
2R/3R targets. **No future candles, no result, no calendar date** (dates hidden so memory can't leak in;
`--show-dates` turns them on).

| Key | Action |
|---|---|
| `T` / `S` / `O` | Take / Skip / Opposite (you'd trade it the other way, e.g. a fake-out) |
| `1` `2` `3` | Confidence low / medium / high. Saves and moves to the next setup |
| `N` | Write a note (why). Notes are compared to outcomes in the report |
| `Z` | Undo the last label |

Setups come in a fixed random order across all years and all trigger types, so a session can stop
and resume anywhere. Aim for **300-500 labels** (about 10-15 seconds each, so a few sessions).

Judge each one the way you would live: would you put this trade on, with this stop, right now?
Don't try to guess what the system wants.

The **Results** button shows how your takes did, but looking changes how you label. Use it only
after finishing a batch (it needs at least 30 labels).

## 2. Train
```bash
.venv/bin/python scripts/train_meta.py        # -> reports/meta_report.md
```
1. **Your edge:** do your takes beat the raw candidates? It gives a bootstrap interval, so you know
   whether the gap is real or luck. No ML involved.
2. **Imitation model** (100+ labels): learns your take/skip calls. AUC on setups it didn't train on
   shows how well it copies you (0.5 = coin flip, 0.7+ = it has your filter). It's then applied to the
   ~7,000 setups you never saw, and their outcomes show whether your filter, automated, makes money.
   It also lists what your decisions depend on most.
3. **Meta-label model:** the same idea trained on outcomes alone (2023-24), with the threshold chosen on
   2025 H1 and scored on Aug 2025-Oct 2026. Every look at those recent months is logged in
   `reports/meta_holdout_log.csv`.

## Reading the results
- Your takes clearly beat the baseline, and the imitation model reaches AUC 0.7+ with positive R on
  unseen setups: your discretion is the edge, so automate it and paper trade the imitation model.
- Your takes beat the baseline but the model can't copy you (AUC around 0.5): your edge uses
  something the features don't capture. Your notes show what to add as a feature.
- Your takes don't beat the baseline: this setup family isn't where your edge is. Label a
  different kind of setup, or rely on the routes that already work (daily_trend).

## Files
| File | What |
|---|---|
| `scripts/build_candidates.py` | builds `journal/candidates.parquet` (setups + hidden outcomes) |
| `goldbot/labelling.py` | blind chart renderer, label store, model features |
| `scripts/labeller.py`, `goldbot/web/labeller.html` | the labelling app |
| `journal/labels.db` | your labels (`GOLDBOT_LABELS_DB` overrides the path) |
| `scripts/train_meta.py` | the three analyses above |
