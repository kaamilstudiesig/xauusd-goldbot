"""Meta-label v2: filter the analyser's setups with free quant data and forecasting-model features.

Rules (fixed before looking at any result):
  - train every feature set on DEV (2023-2024) outcomes: target = the setup reached 3R before its stop
  - on VAL (Jan-Jul 2025) pick, per set, the top-quantile threshold with the best average R (>= 30 trades)
  - the set with the best VAL average R is the ONLY one run on HOLD (Aug 2025 -> Oct 2026), once, logged
Success target: profit factor >= 1.2 and average R > 0 after costs on HOLD, also with overlapping
setups removed (one position at a time).

  .venv/bin/python scripts/train_meta_v2.py               # writes reports/meta_v2_report.md
  .venv/bin/python scripts/train_meta_v2.py --no-hold     # DEV/VAL only, no HOLD look
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from goldbot import labelling as L, quant_features as Q  # noqa: E402

REPORT = ROOT / "reports" / "meta_v2_report.md"
LOG = ROOT / "reports" / "meta_v2_holdout_log.csv"
MODELS = ROOT / "journal" / "models"
PARAMS = dict(objective="binary", learning_rate=0.03, num_leaves=7, min_data_in_leaf=60, feature_fraction=0.7,
              bagging_fraction=0.8, bagging_freq=1, lambda_l2=10.0, verbose=-1, seed=7)
ROUNDS = 250
QUANTILES = (0.5, 0.6, 0.7, 0.8, 0.9)


def pf(r: pd.Series) -> float:
    loss = -r[r < 0].sum()
    return float(r[r > 0].sum() / loss) if loss > 0 else np.nan


def non_overlap(g: pd.DataFrame, gap_hours: float = 4.0) -> pd.DataFrame:
    """One position at a time (approx.): skip picks within `gap_hours` of the last accepted one."""
    keep, last = [], None
    for i, t in zip(g.index, g["bar_time"]):
        if last is None or t - last >= pd.Timedelta(hours=gap_hours):
            keep.append(i)
            last = t
    return g.loc[keep]


def stats(g: pd.DataFrame, name: str) -> dict:
    return {"group": name, "n": len(g), "win_3R": round((g.r3 > 0).mean(), 3) if len(g) else np.nan,
            "avg_r3": round(g.r3.mean(), 3) if len(g) else np.nan, "pf": round(pf(g.r3), 2) if len(g) else np.nan,
            "total_r3": round(g.r3.sum(), 1) if len(g) else np.nan}


def boot_ci(r: np.ndarray, n=4000, seed=7) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    m = [rng.choice(r, len(r)).mean() for _ in range(n)]
    return float(np.percentile(m, 5)), float(np.percentile(m, 95))


def feature_sets(c: pd.DataFrame) -> dict[str, pd.DataFrame]:
    base = L.features(c.reset_index()).set_index(c.index)
    q = Q.build(c.reset_index(), L.bars15()).set_index(c.index)
    macro = q[[k for k in q if k.startswith("m_")]]
    cot = q[[k for k in q if k.startswith("cot_")]]
    intr = q[[k for k in q if k.startswith("i_")]]
    sets = {"base": base, "base+macro": base.join(macro), "base+cot": base.join(cot),
            "base+intraday": base.join(intr)}
    extra = [base, macro, cot, intr]
    for fc in sorted((ROOT / "journal").glob("forecast_*.parquet")):
        f = pd.read_parquet(fc).reindex(c.index)
        name = fc.stem.replace("forecast_", "")
        if f.notna().mean().min() > 0.99:
            sets[f"base+{name}"] = base.join(f.add_prefix(f"{name}_"))
            extra.append(f.add_prefix(f"{name}_"))
    sets["all"] = pd.concat(extra, axis=1)
    return sets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-hold", action="store_true")
    a = ap.parse_args()
    c = L.candidates().sort_values("bar_time")
    y = (c["r3"] > 0).astype(int)
    dev, val, hold = (c.period == "dev"), (c.period == "val"), (c.period == "hold")
    sets = feature_sets(c)
    out = ["# Meta-label v2: quant + forecast features", "",
           f"Setups: {len(c)} (DEV {dev.sum()}, VAL {val.sum()}, HOLD {hold.sum()}). Target: reached 3R before the stop.", "",
           "## VAL (Jan-Jul 2025): each feature set trained on DEV only", ""]
    rows, best = [], None
    base_val = stats(c[val], "all VAL setups")
    for name, X in sets.items():
        m = lgb.train(PARAMS, lgb.Dataset(X[dev], y[dev]), ROUNDS)
        pv = pd.Series(m.predict(X[val]), index=c.index[val])
        cand = None
        for q in QUANTILES:
            thr = pv.quantile(q)
            g = c[val][pv >= thr]
            if len(g) >= 30 and (cand is None or g.r3.mean() > cand[2]):
                cand = (q, thr, g.r3.mean(), g)
        if cand is None:
            continue
        q, thr, _, g = cand
        rows.append({"features": name, "n_features": X.shape[1], "top": f"{1 - q:.0%}", **{k: v for k, v in stats(g, "").items() if k != "group"},
                     "pf_no_overlap": round(pf(non_overlap(g).r3), 2)})
        if best is None or g.r3.mean() > best[3]:
            best = (name, m, thr, g.r3.mean(), q)
    tab = pd.DataFrame(rows).sort_values("avg_r3", ascending=False)
    out += [f"Baseline, all VAL setups: n {base_val['n']}, avg {base_val['avg_r3']:+.3f}R, PF {base_val['pf']}", "",
            tab.to_string(index=False), "",
            f"Chosen on VAL (rule: best avg R): **{best[0]}**, top {1 - best[4]:.0%} of setups by model score.", ""]
    name, model, thr = best[0], best[1], best[2]
    MODELS.mkdir(parents=True, exist_ok=True)
    model.save_model(str(MODELS / "meta_v2.txt"))
    imp = pd.Series(model.feature_importance("gain"), index=sets[name].columns).sort_values(ascending=False)
    out += ["Top features of the chosen model:", "", (imp / imp.sum()).head(12).round(3).to_string(), ""]

    if not a.no_hold:
        ph = pd.Series(model.predict(sets[name][hold]), index=c.index[hold])
        g = c[hold][ph >= thr]
        no = non_overlap(g)
        lo, hi = boot_ci(no.r3.values) if len(no) > 10 else (np.nan, np.nan)
        out += ["## HOLD (Aug 2025 -> Oct 2026): run once for the chosen set", "",
                pd.DataFrame([stats(c[hold], "all HOLD setups"), stats(g, "model picks"),
                              stats(no, "model picks, one at a time")]).to_string(index=False), "",
                f"One-at-a-time avg R 90% bootstrap interval: {lo:+.3f} to {hi:+.3f}.", ""]
        mon = no.groupby(no.bar_time.dt.strftime("%Y-%m")).r3.agg(["size", "mean", "sum"]).round(2)
        out += ["By month (one at a time):", "", mon.to_string(), ""]
        ok = pf(no.r3) >= 1.2 and no.r3.mean() > 0
        out += [f"**Target (PF >= 1.2 and avg R > 0, one at a time): {'MET' if ok else 'NOT MET'}** "
                f"(PF {pf(no.r3):.2f}, avg {no.r3.mean():+.3f}R, {len(no)} trades).", ""]
        row = pd.DataFrame([{"ts": pd.Timestamp.now(tz="UTC").isoformat(), "features": name, "quantile": best[4],
                             "n": len(no), "avg_r3": no.r3.mean(), "pf": pf(no.r3), "met": ok}])
        row.to_csv(LOG, mode="a", header=not LOG.exists(), index=False)
        out += [f"HOLD looks so far: {len(pd.read_csv(LOG))} (`{LOG.name}`).", ""]
    REPORT.write_text("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
