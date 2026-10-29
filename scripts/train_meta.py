"""Learn from your labels and from outcomes. Writes reports/meta_report.md.

Three questions, answered separately:
  1. YOUR EDGE    Do the setups you mark "take" beat the raw candidates after costs? (no ML needed)
  2. IMITATION    Can a model reproduce your take/skip calls from the setup's features? If so, apply it
                  to the thousands of setups you never labelled and measure their outcomes.
  3. META-LABEL   Without your labels: can a model trained on DEV outcomes pick better setups?
                  Threshold chosen on VAL, scored once on HOLD (each HOLD look is logged).

  .venv/bin/python scripts/train_meta.py
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import lightgbm as lgb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from goldbot import labelling as L  # noqa: E402

MODELS = ROOT / "journal" / "models"
REPORT = ROOT / "reports" / "meta_report.md"
HOLD_LOG = ROOT / "reports" / "meta_holdout_log.csv"
PARAMS = dict(objective="binary", learning_rate=0.03, num_leaves=7, min_data_in_leaf=40, feature_fraction=0.7,
              bagging_fraction=0.8, bagging_freq=1, lambda_l2=10.0, verbose=-1, seed=7)


def summarise(g: pd.DataFrame, name: str) -> dict:
    return {"group": name, "n": len(g), "win_3R": round((g.r3 > 0).mean(), 3) if len(g) else np.nan,
            "avg_r3": round(g.r3.mean(), 3) if len(g) else np.nan, "avg_r2": round(g.r2.mean(), 3) if len(g) else np.nan,
            "total_r3": round(g.r3.sum(), 1) if len(g) else np.nan}


def boot_diff(a: np.ndarray, b: np.ndarray, n=4000, seed=7) -> tuple[float, float]:
    """90% bootstrap interval for mean(a) - mean(b)."""
    rng = np.random.default_rng(seed)
    d = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(n)]
    return float(np.percentile(d, 5)), float(np.percentile(d, 95))


def time_folds(times: pd.Series, k=5, embargo_days=2):
    """Contiguous time blocks; training excludes a small embargo around each test block."""
    order = np.argsort(times.values)
    blocks = np.array_split(order, k)
    for b in blocks:
        t0, t1 = times.iloc[b].min(), times.iloc[b].max()
        emb = pd.Timedelta(days=embargo_days)
        tr = np.where((times < t0 - emb) | (times > t1 + emb))[0]
        yield tr, b


def your_edge(c, lab, out):
    j = lab.join(c, on="cid")
    out += ["## 1. Your edge (no model)", ""]
    rows = [summarise(c[c.period.isin(j.period.unique())], "baseline: all candidates")]
    for d in ("take", "skip", "opposite"):
        rows.append(summarise(j[j.decision == d], f"you: {d}"))
    for conf in (3, 2, 1):
        rows.append(summarise(j[(j.decision == "take") & (j.confidence == conf)], f"  take, confidence {conf}"))
    for p in ("dev", "val", "hold"):
        rows.append(summarise(j[(j.decision == "take") & (j.period == p)], f"  take, {p} months"))
    out += [pd.DataFrame(rows).to_string(index=False), ""]
    takes, others = j[j.decision == "take"].r3.values, j[j.decision != "take"].r3.values
    if len(takes) >= 20 and len(others) >= 20:
        lo, hi = boot_diff(takes, others)
        verdict = "a real edge so far" if lo > 0 else "not yet distinguishable from luck"
        out += [f"Take minus not-take, avg 3R: {takes.mean() - others.mean():+.3f}R (90% interval {lo:+.3f} to {hi:+.3f}): {verdict}.", ""]
    notes = j[j.note.fillna("").str.len() > 0][["cid", "decision", "confidence", "note", "r3"]]
    if len(notes):
        out += ["Your notes vs outcome (last 15):", "", notes.tail(15).round(2).to_string(index=False), ""]


def imitation(c, lab, X, out):
    out += ["## 2. Imitation model (learns your take/skip calls)", ""]
    j = lab.set_index("cid")
    y = (j["decision"] == "take").astype(int)
    Xl = X.loc[y.index]
    times = c.loc[y.index, "bar_time"]
    oof = pd.Series(np.nan, index=y.index)
    for tr, te in time_folds(times.reset_index(drop=True)):
        if y.iloc[tr].nunique() < 2:
            continue
        m = lgb.train({**PARAMS, "min_data_in_leaf": 10}, lgb.Dataset(Xl.iloc[tr], y.iloc[tr]), 150)
        oof.iloc[te] = m.predict(Xl.iloc[te])
    ok = oof.notna()
    auc = roc_auc_score(y[ok], oof[ok]) if ok.sum() > 20 and y[ok].nunique() == 2 else np.nan
    out += [f"How well the model predicts YOUR decision on setups it didn't train on: AUC {auc:.2f} "
            "(0.5 = coin flip, 0.7+ = it has learned your filter).", ""]
    model = lgb.train({**PARAMS, "min_data_in_leaf": 10}, lgb.Dataset(Xl, y), 150)
    MODELS.mkdir(parents=True, exist_ok=True)
    model.save_model(str(MODELS / "imitation.txt"))
    # apply to setups you never labelled, at your own take rate
    unl = c[~c.index.isin(y.index)]
    p = pd.Series(model.predict(X.loc[unl.index]), index=unl.index)
    thr = p.quantile(1 - y.mean())
    rows = []
    for per in ("dev", "val", "hold"):
        u = unl[unl.period == per]
        rows += [summarise(u, f"{per}: all unlabelled"), summarise(u[p.loc[u.index] >= thr], f"{per}: model-as-you takes")]
    out += ["Your filter, automated, on setups you never saw:", "", pd.DataFrame(rows).to_string(index=False), ""]
    imp = pd.Series(model.feature_importance("gain"), index=X.columns).sort_values(ascending=False)
    out += ["What your decisions depend on most (model's view):", "", (imp / imp.sum()).head(10).round(3).to_string(), ""]


def meta_label(c, X, out, log_holdout: bool):
    out += ["## 3. Meta-label model (learns from outcomes, ignores your labels)", ""]
    y = (c["r3"] > 0).astype(int)
    dev, val, hold = (c.period == "dev"), (c.period == "val"), (c.period == "hold")
    model = lgb.train(PARAMS, lgb.Dataset(X[dev], y[dev]), 200)
    model.save_model(str(MODELS / "meta.txt"))
    pv = pd.Series(model.predict(X[val]), index=c.index[val])
    best = None
    for q in (0.5, 0.6, 0.7, 0.8, 0.9):
        thr = pv.quantile(q)
        g = c[val][pv >= thr]
        if len(g) >= 30 and (best is None or g.r3.mean() > best[1]):
            best = (thr, g.r3.mean(), q)
    if best is None:
        out += ["Not enough VAL trades to choose a threshold.", ""]
        return
    thr, _, q = best
    rows = [summarise(c[dev], "dev: all"), summarise(c[val], "val: all"),
            summarise(c[val][pv >= thr], f"val: model top {1 - q:.0%} (threshold chosen here)")]
    ph = pd.Series(model.predict(X[hold]), index=c.index[hold])
    rows += [summarise(c[hold], "hold: all"), summarise(c[hold][ph >= thr], f"hold: model top picks")]
    out += [pd.DataFrame(rows).to_string(index=False), ""]
    if log_holdout:
        g = c[hold][ph >= thr]
        row = pd.DataFrame([{"ts": pd.Timestamp.now(tz="UTC").isoformat(), "n": len(g), "avg_r3": g.r3.mean(),
                             "quantile": q, "threshold": thr, "note": ""}])
        row.to_csv(HOLD_LOG, mode="a", header=not HOLD_LOG.exists(), index=False)
        n_looks = len(pd.read_csv(HOLD_LOG))
        out += [f"HOLD has now been looked at {n_looks} time(s) (`{HOLD_LOG.name}`). Every extra look makes it less of a true test.", ""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-labels", type=int, default=100)
    ap.add_argument("--no-holdout-log", action="store_true", help="for tests: don't record a HOLD look")
    a = ap.parse_args()
    c = L.candidates()
    X = L.features(c.reset_index()).set_index(c.index)
    lab = L.labels()
    out = ["# Meta-labelling report", "", f"Candidates: {len(c)} | your labels: {len(lab)}", ""]
    if len(lab) >= 30:
        your_edge(c, lab, out)
    else:
        out += [f"(Sections 1-2 need labels: {len(lab)} so far.)", ""]
    if len(lab) >= a.min_labels:
        imitation(c, lab, X, out)
    meta_label(c, X, out, log_holdout=not a.no_holdout_log)
    REPORT.write_text("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
