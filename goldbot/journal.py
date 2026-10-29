"""SQLite journal: every run, signal, trade, equity point and manual note is recorded.
Closed trades are frozen (never rewritten), so the record stays accurate even if data is revised."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parents[1] / "journal" / "paper.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  run_id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, last_bar TEXT, n_bars INTEGER,
  data_source TEXT, basis REAL, live_check TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS trades (
  route TEXT, entry_time TEXT, exit_time TEXT, side INTEGER, entry REAL, exit REAL, sl REAL, tp REAL,
  size REAL, pnl REAL, r REAL, reason TEXT, bars INTEGER, status TEXT, weight REAL,
  context TEXT, first_seen_run INTEGER, closed_run INTEGER,
  PRIMARY KEY (route, entry_time));
CREATE TABLE IF NOT EXISTS signals (
  route TEXT, bar_time TEXT, side INTEGER, close REAL, sl_dist REAL, tp_dist REAL, run_id INTEGER,
  PRIMARY KEY (route, bar_time));
CREATE TABLE IF NOT EXISTS equity (ts TEXT PRIMARY KEY, equity REAL, open_pnl REAL, closed_pnl REAL, run_id INTEGER);
CREATE TABLE IF NOT EXISTS allocation (ts TEXT, route TEXT, weight REAL, w_avg_r REAL, eff_n REAL, w_t REAL, status TEXT, run_id INTEGER);
CREATE TABLE IF NOT EXISTS notes (ts TEXT, author TEXT, route TEXT, text TEXT, tags TEXT);
CREATE TABLE IF NOT EXISTS discrepancies (ts TEXT, route TEXT, entry_time TEXT, field TEXT, frozen REAL, replay REAL);
"""


def connect() -> sqlite3.Connection:
    DB.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    return con


def read(sql: str, params=()) -> pd.DataFrame:
    with connect() as con:
        return pd.read_sql_query(sql, con, params=params)


def add_note(text: str, route: str = "", tags: str = "", author: str = "trader") -> None:
    with connect() as con:
        con.execute("INSERT INTO notes VALUES (?,?,?,?,?)", (pd.Timestamp.now(tz="UTC").isoformat(), author, route, text, tags))


def dumps(d: dict) -> str:
    return json.dumps({k: (None if pd.isna(v) else (round(float(v), 5) if isinstance(v, (int, float)) else str(v))) for k, v in d.items()})


# ---- text snapshot (for git) ------------------------------------------------------------------
# The scheduled runner commits journal/paper.sql (plain SQL, diff-friendly) instead of the binary
# .db, so hourly commits stay tiny. The .db is rebuilt from it when missing.
SQL = DB.with_suffix(".sql")


def export_sql() -> None:
    with connect() as con:
        SQL.write_text("\n".join(con.iterdump()) + "\n")


def restore_sql() -> bool:
    if DB.exists() or not SQL.exists():
        return False
    con = sqlite3.connect(DB)
    con.executescript(SQL.read_text())
    con.close()
    return True
