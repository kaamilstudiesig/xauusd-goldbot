"""Setup labeller: a small local web app.

  .venv/bin/python scripts/labeller.py            # then open http://127.0.0.1:8765
  .venv/bin/python scripts/labeller.py --period hold --show-dates

Each screen is one candidate setup at the close of its signal candle: no future candles, no
outcome, no calendar date (unless --show-dates). Mark Take / Skip / Opposite and a confidence.
Labels go to journal/labels.db. Then run scripts/train_meta.py.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from goldbot import labelling as L  # noqa: E402

HTML = (ROOT / "goldbot" / "web" / "labeller.html").read_bytes()
ARGS = argparse.Namespace(period=None, show_dates=False, goal=400)


@lru_cache(maxsize=64)
def chart(cid: str) -> bytes:
    return L.render(cid, show_date=ARGS.show_dates)


def stats() -> dict:
    lab = L.labels()
    if len(lab) < 30:
        return {"message": f"Label at least 30 setups first ({len(lab)} so far)."}
    c = L.candidates()
    j = lab.join(c[["r2", "r3", "period"]], on="cid")

    def row(name, g):
        return {"group": name, "n": int(len(g)), "win3": f"{(g.r3 > 0).mean():.0%}",
                "r3": f"{g.r3.mean():+.3f}", "r2": f"{g.r2.mean():+.3f}"}

    base = c[c.period.isin(j.period.unique())]
    rows = [row("Baseline (all candidates)", base)]
    for d in ("take", "skip", "opposite"):
        g = j[j.decision == d]
        if len(g):
            rows.append(row(f"Your {d}", g))
    for conf in (3, 2, 1):
        g = j[(j.decision == "take") & (j.confidence == conf)]
        if len(g):
            rows.append(row(f"  take, confidence {conf}", g))
    note = ("'Opposite' rows show the setup's own direction: negative there means you were right to fade it. "
            "Differences under ~0.15R on fewer than 100 trades are mostly noise.")
    return {"rows": rows, "note": note}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, default=lambda o: o.item() if hasattr(o, "item") else str(o)).encode())

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path == "/":
                return self._send(200, HTML, "text/html; charset=utf-8")
            if u.path == "/api/progress":
                n = len(L.labels())
                c = L.candidates()
                pool = c if not ARGS.period else c[c.period == ARGS.period]
                return self._json({"labelled": n, "remaining": int(len(pool) - n), "goal": ARGS.goal})
            if u.path == "/api/next":
                n = int(q.get("n", ["1"])[0])
                c = L.candidates()
                done = set(L.labels()["cid"])
                pool = c if not ARGS.period else c[c.period == ARGS.period]
                ids = pool[~pool.index.isin(done)].sort_values("order").index[:n]
                return self._json({"items": [L.public_meta(i, ARGS.show_dates) for i in ids]})
            if u.path.startswith("/api/candidate/"):
                return self._json(L.public_meta(u.path.rsplit("/", 1)[1], ARGS.show_dates))
            if u.path.startswith("/chart/") and u.path.endswith(".png"):
                return self._send(200, chart(u.path[7:-4]), "image/png")
            if u.path == "/api/stats":
                return self._json(stats())
            return self._json({"error": "not found"}, 404)
        except KeyError:
            return self._json({"error": "unknown candidate"}, 404)

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}") if n else {}
        if u.path == "/api/label":
            L.save_label(body["cid"], body["decision"], body["confidence"], body.get("note", ""), body.get("seconds"))
            return self._json({"ok": True})
        if u.path == "/api/undo":
            return self._json({"cid": L.undo_last()})
        return self._json({"error": "not found"}, 404)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--period", choices=["dev", "val", "hold"], help="only show candidates from one period")
    ap.add_argument("--show-dates", action="store_true", help="show calendar dates (off by default to avoid memory bias)")
    ap.add_argument("--goal", type=int, default=400)
    a = ap.parse_args()
    ARGS.period, ARGS.show_dates, ARGS.goal = a.period, a.show_dates, a.goal
    L.candidates(), L.bars15()  # warm caches
    print(f"Labeller on http://127.0.0.1:{a.port}  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()


if __name__ == "__main__":
    main()
