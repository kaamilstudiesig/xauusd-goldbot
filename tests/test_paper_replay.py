"""Replay paper trading from an earlier start into a temp journal; check trades are recorded once
and a second run changes nothing (idempotent, closed trades frozen)."""
import json, sys, tempfile, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from goldbot import journal, paper

def test_replay(start="2026-09-01"):
    tmp = Path(tempfile.mkdtemp())
    journal.DB = tmp / "test.db"
    cfg = paper.load_cfg(); cfg["paper_start"] = start
    paper.load_cfg = lambda: cfg
    s1 = paper.run_once("test 1")
    t1 = journal.read("SELECT route, entry_time, status, pnl, r FROM trades ORDER BY route, entry_time")
    s2 = paper.run_once("test 2")
    t2 = journal.read("SELECT route, entry_time, status, pnl, r FROM trades ORDER BY route, entry_time")
    assert len(t1) == len(t2), "second run must not add duplicate trades"
    assert (t1.pnl.round(6) == t2.pnl.round(6)).all()
    print(f"trades journaled: {len(t1)} | portfolio equity {s1['equity']} | discrepancies:",
          len(journal.read("SELECT * FROM discrepancies")))
    print(t1.groupby(["route", "status"]).agg(n=("r", "size"), avg_r=("r", "mean")).round(2).to_string())
    print(paper.report())

if __name__ == "__main__":
    test_replay()
