"""Paper-trading entry point.

  .venv/bin/python scripts/paper.py run            # one cycle: refresh data, update trades, journal
  .venv/bin/python scripts/paper.py report         # print the current paper report
  .venv/bin/python scripts/paper.py note "text" --route daily_trend --tags "fomc,discipline"

Run it hourly (e.g. cron at minute 5) so each completed H1 bar is processed.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goldbot import paper  # noqa: E402
from goldbot.journal import add_note  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "report", "note"])
    ap.add_argument("text", nargs="?", default="")
    ap.add_argument("--route", default="")
    ap.add_argument("--tags", default="")
    a = ap.parse_args()
    if a.cmd == "run":
        s = paper.run_once(note=a.text)
        print(json.dumps(s, indent=2, default=str))
        (ROOT / "reports" / "paper_report.md").write_text(paper.report())
    elif a.cmd == "report":
        print(paper.report())
    else:
        add_note(a.text, a.route, a.tags)
        print("note saved")


if __name__ == "__main__":
    main()
