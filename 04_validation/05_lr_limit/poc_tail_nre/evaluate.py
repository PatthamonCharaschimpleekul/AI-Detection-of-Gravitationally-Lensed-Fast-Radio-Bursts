"""Compare every trained run with the exact LR on the shared test set."""
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar

from sim import SimConfig

ap = argparse.ArgumentParser()
ap.add_argument("--test", default="outputs/testset")
ap.add_argument("--runs", default="outputs/runs")
ap.add_argument("--out", default="outputs/results.json")
args = ap.parse_args()

cfg = SimConfig()
n_rho = len(cfg.rhos)
test = Path(args.test)
strat = np.load(test / "stratum.npy")
exact = np.load(test / "log_r.npy").astype(np.float64)
per_rho = np.load(test / "per_rho.npy", mmap_mode="r")
is_h1 = strat == n_rho
n_per = int(is_h1.sum())
LN10 = math.log(10)


def h0_weights(p):
    p = np.asarray(p)
    w = np.zeros(len(strat))
    w[~is_h1] = p[strat[~is_h1]] / n_per
    return w


def bce(s, w0):
    """Balanced cross-entropy in nats, weighting H0 to the given prior."""
    l1 = np.logaddexp(0, -s[is_h1]).mean()
    l0 = (w0 * np.logaddexp(0, s)).sum()
    return 0.5 * (l1 + l0)


def metrics(s, ref, w0, thresholds=(1e2, 1e3, 1e4)):
    """Tail accuracy of log r estimate s against the exact ref (both natural log)."""
    out = {"excess_bce": bce(s, w0) - bce(ref, w0)}
    err = (s - ref) / LN10
    w = w0.copy()
    w[is_h1] = 1.0 / n_per  # A balanced mix of the two hypotheses.
    for lo in (0, 2, 3):
        sel = ref / LN10 >= lo
        tw = w[sel] / w[sel].sum()
        bias = (tw * err[sel]).sum()
        out[f"tail{lo}_bias_dex"] = bias
        out[f"tail{lo}_rmse_dex"] = math.sqrt((tw * err[sel] ** 2).sum())
    for t in thresholds:
        lt = math.log(t)
        key = f"{t:g}"
        out[f"fpr_{key}"] = w0[s >= lt].sum()
        out[f"fpr_exact_{key}"] = w0[ref >= lt].sum()
        out[f"recall_{key}"] = (s[is_h1] >= lt).mean()
        out[f"recall_exact_{key}"] = (ref[is_h1] >= lt).mean()
    # Ville/Markov identities that any true LR obeys, and that need only negatives.
    out["E_H0_rhat"] = (w0 * np.exp(np.clip(s, None, 50))).sum()
    return out


def temperature(cal):
    s, y = cal["s"], cal["y"]
    f = lambda T: (y * np.logaddexp(0, -s / T) + (1 - y) * np.logaddexp(0, s / T)).mean()
    return minimize_scalar(f, bounds=(0.2, 5.0), method="bounded").x


w0 = h0_weights(cfg.p_rho)
runs = defaultdict(list)
for d in sorted(Path(args.runs).iterdir()):
    if not (d / "meta.json").exists():
        continue
    meta = json.loads((d / "meta.json").read_text())
    s = np.load(d / "log_r.npy").astype(np.float64)
    m = metrics(s, exact, w0)
    m["seed"], m["seconds"], m["n_params"] = meta["seed"], meta["seconds"], meta["n_params"]
    T = temperature(np.load(d / "calib.npz"))
    m["temperature"] = T
    ts = metrics(s / T, exact, w0)
    m.update({f"ts_{k}": v for k, v in ts.items()})
    key = d.name.rsplit("_seed", 1)[0]
    runs[key].append(m)

summary = {}
for key, rows in runs.items():
    keys = [k for k in rows[0] if k != "seed"]
    summary[key] = {
        "n_seeds": len(rows),
        **{k: {"mean": float(np.mean([r[k] for r in rows])), "min": float(np.min([r[k] for r in rows])),
               "max": float(np.max([r[k] for r in rows]))} for k in keys},
    }

Path(args.out).write_text(json.dumps(summary, indent=1))
cols = ["excess_bce", "tail3_bias_dex", "tail3_rmse_dex", "fpr_1000", "recall_1000", "E_H0_rhat", "ts_tail3_rmse_dex", "ts_fpr_1000"]
print("exact: fpr_1000={:.2e} recall_1000={:.3f}".format(w0[exact >= math.log(1e3)].sum(), (exact[is_h1] >= math.log(1e3)).mean()))
print("run".ljust(36) + " ".join(c.rjust(18) for c in cols))
for key, s in sorted(summary.items()):
    print(key.ljust(36) + " ".join(f"{s[c]['mean']:.3g} [{s[c]['min']:.3g},{s[c]['max']:.3g}]".rjust(18) for c in cols))
