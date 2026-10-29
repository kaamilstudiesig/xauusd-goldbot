BEGIN TRANSACTION;
CREATE TABLE allocation (ts TEXT, route TEXT, weight REAL, w_avg_r REAL, eff_n REAL, w_t REAL, status TEXT, run_id INTEGER);
INSERT INTO "allocation" VALUES('2026-10-29T20:06:03.444721+00:00','daily_trend',1.0,0.734,19.8,1.94,'active',1);
INSERT INTO "allocation" VALUES('2026-10-29T20:06:03.446847+00:00','daily_trend_long',0.0,0.951,14.2,1.8,'shadow',1);
INSERT INTO "allocation" VALUES('2026-10-29T20:06:03.449501+00:00','london_breakout',0.0,0.065,196.9,1.16,'shadow',1);
INSERT INTO "allocation" VALUES('2026-10-29T20:06:03.451540+00:00','trend_breakout',0.0,0.136,258.6,1.22,'shadow',1);
INSERT INTO "allocation" VALUES('2026-10-29T20:06:03.453353+00:00','mean_reversion',0.0,0.328,14.2,0.75,'shadow',1);
INSERT INTO "allocation" VALUES('2026-10-29T20:06:03.455226+00:00','london_breakout+macro',0.0,0.091,145.4,1.38,'shadow',1);
INSERT INTO "allocation" VALUES('2026-10-29T20:06:03.457195+00:00','trend_breakout+macro',0.0,0.15,203.6,1.17,'shadow',1);
INSERT INTO "allocation" VALUES('2026-10-29T20:06:03.458988+00:00','daily_trend+macro',0.0,0.495,20.4,1.37,'shadow',1);
INSERT INTO "allocation" VALUES('2026-10-29T20:06:03.460891+00:00','trend_pullback',0.0,-0.08,149.1,-0.71,'shadow',1);
INSERT INTO "allocation" VALUES('2026-10-29T20:06:03.461960+00:00','zone_v18',0.0,0.0,0.0,0.0,'shadow',1);
INSERT INTO "allocation" VALUES('2026-10-29T23:54:16.785837+00:00','daily_trend',1.0,0.734,19.8,1.94,'active',2);
INSERT INTO "allocation" VALUES('2026-10-29T23:54:16.787166+00:00','daily_trend_long',0.0,0.951,14.2,1.8,'shadow',2);
INSERT INTO "allocation" VALUES('2026-10-29T23:54:16.788380+00:00','london_breakout',0.0,0.065,196.9,1.16,'shadow',2);
INSERT INTO "allocation" VALUES('2026-10-29T23:54:16.789441+00:00','trend_breakout',0.0,0.136,258.6,1.22,'shadow',2);
INSERT INTO "allocation" VALUES('2026-10-29T23:54:16.790456+00:00','mean_reversion',0.0,0.328,14.2,0.75,'shadow',2);
INSERT INTO "allocation" VALUES('2026-10-29T23:54:16.791545+00:00','london_breakout+macro',0.0,0.091,145.4,1.38,'shadow',2);
INSERT INTO "allocation" VALUES('2026-10-29T23:54:16.792571+00:00','trend_breakout+macro',0.0,0.15,203.6,1.17,'shadow',2);
INSERT INTO "allocation" VALUES('2026-10-29T23:54:16.793504+00:00','daily_trend+macro',0.0,0.495,20.4,1.37,'shadow',2);
INSERT INTO "allocation" VALUES('2026-10-29T23:54:16.794460+00:00','trend_pullback',0.0,-0.08,149.1,-0.71,'shadow',2);
INSERT INTO "allocation" VALUES('2026-10-29T23:54:16.794991+00:00','zone_v18',0.0,0.0,0.0,0.0,'shadow',2);
CREATE TABLE discrepancies (ts TEXT, route TEXT, entry_time TEXT, field TEXT, frozen REAL, replay REAL);
CREATE TABLE equity (ts TEXT PRIMARY KEY, equity REAL, open_pnl REAL, closed_pnl REAL, run_id INTEGER);
INSERT INTO "equity" VALUES('2026-10-29 19:45:00+00:00',10000.0,0.0,0.0,1);
INSERT INTO "equity" VALUES('2026-10-29 23:30:00+00:00',10000.0,0.0,0.0,2);
CREATE TABLE notes (ts TEXT, author TEXT, route TEXT, text TEXT, tags TEXT);
CREATE TABLE runs (
  run_id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, last_bar TEXT, n_bars INTEGER,
  data_source TEXT, basis REAL, live_check TEXT, note TEXT);
INSERT INTO "runs" VALUES(1,'2026-10-29T20:06:02.877249+00:00','2026-10-29 19:45:00+00:00',66954,'twelvedata_spot (+27 bars)',0.0,'spot=4024.47 last_bar_close=4022.12','github-actions');
INSERT INTO "runs" VALUES(2,'2026-10-29T23:54:16.178124+00:00','2026-10-29 23:30:00+00:00',66965,'twelvedata_spot (+11 bars)',0.0,'spot=4008.66 last_bar_close=4011.77','github-actions');
CREATE TABLE signals (
  route TEXT, bar_time TEXT, side INTEGER, close REAL, sl_dist REAL, tp_dist REAL, run_id INTEGER,
  PRIMARY KEY (route, bar_time));
CREATE TABLE trades (
  route TEXT, entry_time TEXT, exit_time TEXT, side INTEGER, entry REAL, exit REAL, sl REAL, tp REAL,
  size REAL, pnl REAL, r REAL, reason TEXT, bars INTEGER, status TEXT, weight REAL,
  context TEXT, first_seen_run INTEGER, closed_run INTEGER,
  PRIMARY KEY (route, entry_time));
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('runs',2);
COMMIT;
