"""Separate miscalibration from power loss, and test re-marginalising over a new prior.

Self-calibration: within a bin of r_hat, does the observed H1/H0 density ratio equal r_hat?
A score can be far from the exact r and still be a valid LR of itself.
Power: recall at a fixed false-positive rate, which ignores the score's scale.
"""
import json
import math
from pathlib import Path

import numpy as np

from sim import SimConfig

cfg = SimConfig()
n_rho = len(cfg.rhos)
strat = np.load("outputs/testset/stratum.npy")
exact = np.load("outputs/testset/log_r.npy").astype(np.float64)
per_rho = np.load("outputs/testset/per_rho.npy")
is_h1 = strat == n_rho
n_per = int(is_h1.sum())
LN10 = math.log(10)


def w0_for(p):
    w = np.zeros(len(strat))
    w[~is_h1] = np.asarray(p)[strat[~is_h1]] / n_per
    return w


def exact_for(p):
    return per_rho[:, -1] - np.logaddexp.reduce(per_rho[:, :-1] + np.log(p), axis=1)


def recall_at_fpr(s, w0, fpr):
    order = np.argsort(-s[~is_h1])
    cum = np.cumsum(w0[~is_h1][order])
    k = np.searchsorted(cum, fpr)
    if k >= len(order):
        return float("nan")
    return float((s[is_h1] >= s[~is_h1][order][k]).mean())


def reliability(s, w0, edges=(1, 2, 3, 4)):
    """Bins of log10 r_hat: mean claim vs observed log10 ratio, with a Poisson error."""
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (s / LN10 >= lo) & (s / LN10 < hi)
        h1_n = (sel & is_h1).sum()
        h0 = w0[sel].sum()
        w2 = (w0[sel] ** 2).sum()
        if h1_n < 5 or h0 == 0:
            rows.append((lo, hi, None, None, None))
            continue
        obs = math.log10((h1_n / n_per) / h0)
        err = math.sqrt(1 / h1_n + w2 / h0 ** 2) / LN10
        # Claim: the H1-weighted mean of log10 r_hat within the bin.
        rows.append((lo, hi, float((s[sel & is_h1] / LN10).mean()), obs, err))
    return rows


w0 = w0_for(cfg.p_rho)
res = {}
fprs = (1e-2, 1e-3, 1e-4, 3.55e-5, 1e-5)
print("recall at fixed FPR".ljust(30) + " ".join(f"{f:>9.2e}" for f in fprs))
print("exact".ljust(30) + " ".join(f"{recall_at_fpr(exact, w0, f):9.4f}" for f in fprs))
runs = sorted(d for d in Path("outputs/runs").iterdir() if (d / "meta.json").exists())
for d in runs:
    s = np.load(d / "log_r.npy").astype(np.float64)
    print(d.name.ljust(30) + " ".join(f"{recall_at_fpr(s, w0, f):9.4f}" for f in fprs))
    res[d.name] = {"recall_at_fpr": {f"{f:g}": recall_at_fpr(s, w0, f) for f in fprs}, "reliability": reliability(s, w0)}
print("\nself-calibration: bin of log10 r_hat -> mean claim vs observed log10 ratio +- err")
for name, r in res.items():
    print(name, " | ".join(
        f"[{lo},{hi}) n/a" if c is None else f"[{lo},{hi}) {c:.2f} vs {o:.2f}+-{e:.2f}" for lo, hi, c, o, e in r["reliability"]))
print("exact", " | ".join(
    f"[{lo},{hi}) n/a" if c is None else f"[{lo},{hi}) {c:.2f} vs {o:.2f}+-{e:.2f}" for lo, hi, c, o, e in reliability(exact, w0)))

# Prior amortisation: `cond` can be re-marginalised to a new prior with no retraining.
alts = {"uniform": np.full(n_rho, 1 / n_rho), "hard": np.array([.1, .1, .1, .2, .2, .2, .1])}
print("\nnew prior, no retraining: bias/rmse (dex) at exact r>=1e3, FPR and recall at r_hat>=1e3")
for pname, p in alts.items():
    ex, w = exact_for(p), w0_for(p)
    wmix = w.copy()
    wmix[is_h1] = 1 / n_per
    sel = ex / LN10 >= 3
    tw = wmix[sel] / wmix[sel].sum()
    print(f"{pname}: exact fpr={w[ex >= math.log(1e3)].sum():.2e} recall={(ex[is_h1] >= math.log(1e3)).mean():.4f}")
    cands = {}
    for d in runs:
        s = np.load(d / "log_r.npy").astype(np.float64)
        cands[d.name + " (unchanged)"] = s
        if (d / "f_rho.npy").exists():
            f = np.load(d / "f_rho.npy").astype(np.float64)
            cands[d.name + " (re-marginalised)"] = -np.logaddexp.reduce(np.log(p) - f, axis=1)
    for name, s in cands.items():
        err = (s - ex) / LN10
        print(f"  {name:48s} bias={(tw * err[sel]).sum():+.3f} rmse={math.sqrt((tw * err[sel] ** 2).sum()):.3f}"
              f" fpr={w[s >= math.log(1e3)].sum():.2e} recall={(s[is_h1] >= math.log(1e3)).mean():.4f}"
              f" E_H0={(w * np.exp(np.clip(s, None, 50))).sum():.3f}")
Path("outputs/tail_analysis.json").write_text(json.dumps(res, indent=1))
