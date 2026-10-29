# goldbot: XAU/USD research and paper-trading workhouse

One market, done properly: data → realistic backtests → paper trading with a full journal →
recency-weighted re-scoring. **Simulation only: nothing here places real orders.**

## Runs by itself (GitHub Actions)
`.github/workflows/paper.yml` runs one paper-trading cycle every hour (Sun-Fri UTC) and commits the journal
(`journal/paper.sql`), the report (`reports/paper_report.md`) and new price bars (`data/live/`).
- Add the secret `TWELVEDATA_API_KEY` (repo Settings > Secrets and variables > Actions) for real spot bars;
  without it the runner uses GC=F futures minus the measured basis.
- Run it now: Actions tab > paper-trader > Run workflow.
- Locally, `git pull` and then `scripts/paper.py report`. Don't run `paper.py run` locally as well, or the two
  journals will diverge.

Heavy research on demand: open `colab/research.ipynb` in Google Colab (File > Open notebook > GitHub).

## Teach it your judgement (labeller)
```bash
.venv/bin/python scripts/labeller.py      # http://127.0.0.1:8765  - mark Take/Skip/Opposite on blind setups
.venv/bin/python scripts/train_meta.py    # your edge, imitation model, meta-label model -> reports/meta_report.md
```
See `docs/labeller.md`.

## Quick start
```bash
# refresh history + macro (run weekly)
.venv/bin/python -m goldbot.data
# backtest all routes, write reports/research_results.csv
.venv/bin/python scripts/research.py
# one paper-trading cycle (run hourly, a few minutes after the hour)
.venv/bin/python scripts/paper.py run
# see the paper journal
.venv/bin/python scripts/paper.py report
# add your own journal note
.venv/bin/python scripts/paper.py note "Skipped NY breakout, CPI in 10 min" --route london_breakout --tags news
```
Hourly schedule (crontab):
```
5 * * * 0-5 cd /home/kaamil/Desktop/projects/trade && .venv/bin/python scripts/paper.py run >> journal/cron.log 2>&1
```

## Layout
| Path | What |
|---|---|
| `goldbot/data.py` | Spot history (HF) + GC=F futures minus basis + FRED/yfinance macro, all in UTC |
| `goldbot/costs.py` | Gold spread/commission/slippage/swap model: **edit to match your broker** |
| `goldbot/backtest.py` | Conservative bar-by-bar engine (next-bar fills, stop-first, gaps) |
| `goldbot/routes/` | Strategy routes (`rules.py`, `ml.py`, `experimental.py`, `registry.py`) |
| `goldbot/paper.py` | Paper trader: replay with backtest rules, frozen journal, re-scoring |
| `goldbot/scoring.py` | Recency-weighted R, effective sample size, allocation |
| `config/paper.json` | Portfolio allocation, shadow routes, risk, half-life, paper weight |
| `journal/paper.db` | SQLite: runs, signals, trades (+context), equity, allocation, notes |
| `docs/knowledge_base.md` | Gold drivers, books, papers, tools |
| `docs/routes.md` | Every route, its results and its status |
| `reports/` | Research results, robustness grid, paper report |

## How "recent data counts more" works
`scoring.weighted_score` weights each trade by `0.5 ** (age_days / half_life)` (default 365 days),
and paper trades get an extra 3x weight. Each paper run re-scores every route. It flags
`flag_pause` for active routes whose evidence decays and `flag_promote` for shadow routes that earn
it. You approve changes by editing `config/paper.json`; nothing reallocates silently.

## Data caveats
- 15m bars (zone analyser) come from Twelve Data XAU/USD spot, 2022-10 -> today: `goldbot.data.build_15m()`, see
  docs/knowledge_base.md §7.
- Since Jul 2025 bars are GC=F futures minus a futures/spot basis anchored to weekly spot closes.
  The level matches spot to about $1-3. Set `TWELVEDATA_API_KEY` to log a live spot cross-check each run.
- yfinance is unofficial and can break. If it does, the next step is the OANDA v20 practice API.

## Rules before real money
1. At least 100 closed paper trades on the routes you'd trade (one month is not enough).
2. Paper results within the backtest's range (avg R, win rate, slippage).
3. Start live at 0.25% risk; scale only if live tracks paper.
