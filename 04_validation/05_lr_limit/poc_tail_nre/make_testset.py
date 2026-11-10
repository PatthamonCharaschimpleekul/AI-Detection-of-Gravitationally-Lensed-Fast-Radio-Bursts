"""G0: build the shared test set, compute exact LRs, and check they are correct.

H0 is stratified equally across rho, so rare high-rho pairs get enough samples;
metrics reweight each stratum back to the prior.

Usage: python make_testset.py [--n-per 300000] [--out outputs/testset]
"""
import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import torch

from sim import ExactLR, SimConfig, Simulator

ap = argparse.ArgumentParser()
ap.add_argument("--n-per", type=int, default=300_000)
ap.add_argument("--out", default="outputs/testset")
ap.add_argument("--chunk", type=int, default=20_000)
args = ap.parse_args()

out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
cfg = SimConfig()
sim = Simulator(cfg)
exact = ExactLR(cfg)
gen = torch.Generator(device="cuda").manual_seed(20261106)

n_rho = len(cfg.rhos)
strata = list(range(n_rho)) + [n_rho]  # last stratum is lensed
xs, per_rho, labels = [], [], []
t0 = time.time()
for s in strata:
    for start in range(0, args.n_per, args.chunk):
        n = min(args.chunk, args.n_per - start)
        if s == n_rho:
            x = sim.sample(n, lensed=True, generator=gen)
        else:
            x = sim.sample(n, rho_idx=torch.full((n,), s, device="cuda"), generator=gen)
        xs.append(x.cpu().numpy().astype(np.float32))
        per_rho.append(exact.log_per_rho(x).cpu().numpy())
        labels.append(np.full(n, s, dtype=np.int8))
    print(f"stratum {s}: {time.time() - t0:.0f}s", flush=True)

xs, per_rho, labels = np.concatenate(xs), np.concatenate(per_rho), np.concatenate(labels)
np.save(out / "x.npy", xs)
np.save(out / "per_rho.npy", per_rho)
np.save(out / "stratum.npy", labels)

# --- Correctness checks ------------------------------------------------------
lr = exact.log_r(torch.from_numpy(per_rho)).numpy()
np.save(out / "log_r.npy", lr)
p = np.array(cfg.p_rho)
is_h1 = labels == n_rho
w_h0 = np.where(is_h1, 0.0, p[np.minimum(labels, n_rho - 1)] / args.n_per)


def mean_se(v, w):
    """Weighted mean and its standard error for stratified samples."""
    m = (w * v).sum()
    return m, math.sqrt(((w * (v - m)) ** 2).sum())


report = {"n_per_stratum": args.n_per, "seconds": time.time() - t0}
m, se = mean_se(np.exp(lr), w_h0)
report["E_H0_r"] = [m, se]
inv = np.exp(-lr[is_h1])
report["E_H1_inv_r"] = [inv.mean(), inv.std() / math.sqrt(len(inv))]

# Per-rho identity: E[p(x|H1) / p(x|rho)] = 1 under rho.
report["E_rho_ratio"] = {}
for i, rho in enumerate(cfg.rhos):
    v = np.exp(per_rho[labels == i, -1] - per_rho[labels == i, i])
    report["E_rho_ratio"][str(rho)] = [v.mean(), v.std() / math.sqrt(len(v))]

# Empirical covariance of one component must match the closed-form covariance.
K = 400_000
xc = []
ia, ib, ta, tb, ri = 2, 3, 1, 2, 4
s_cfg = sim
with torch.no_grad():
    g_a, g_ind = sim.draw_g(K, gen), sim.draw_g(K, gen)
    rho = cfg.rhos[ri]
    g_b = rho * g_a + math.sqrt(1 - rho ** 2) * g_ind
    for g, a, t in ((g_a, ia, ta), (g_b, ib, tb)):
        y = sim.amps[a] * (sim.H[t] @ (sim.env * (1 + cfg.c * g))[:, :, None])[:, :, 0]
        xc.append(y + torch.randn(y.shape, device="cuda", generator=gen))
    X = torch.cat(xc, 1).double()
    comp = ri * exact.n_nuis + (ia * 5 + ib) * 16 + ta * 4 + tb
    prec = exact.P[comp]
    C = torch.cov(X.T)
    # For a correct precision, C @ prec = I up to sampling noise.
    report["cov_check_max_abs_err"] = (C @ prec - torch.eye(2 * cfg.T, device="cuda", dtype=torch.float64)).abs().max().item()

# Reliability of the exact LR: observed ratio of H1 to H0 mass in each r bin.
edges = np.arange(-6, 7)
rows = []
log10r = lr / math.log(10)
for lo, hi in zip(edges[:-1], edges[1:]):
    sel = (log10r >= lo) & (log10r < hi)
    h1 = (sel & is_h1).sum() / is_h1.sum()
    h0 = w_h0[sel].sum()
    n0 = int((sel & ~is_h1).sum())
    if h0 > 0 and h1 > 0 and n0 >= 20:
        rows.append([int(lo), int(hi), float(np.log10(h1 / h0)), n0])
report["reliability_exact_binlo_binhi_log10ratio_n0"] = rows

# Is there a usable tail?
tail = {}
for t in (1e1, 1e2, 1e3, 1e4, 1e5):
    sel = log10r >= math.log10(t)
    tail[f"{t:g}"] = {"recall": float((sel & is_h1).sum() / is_h1.sum()), "fpr": float(w_h0[sel].sum()),
                      "n0_raw": int((sel & ~is_h1).sum())}
report["tail_exact"] = tail


def to_py(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    raise TypeError(type(o))


(out / "g0_report.json").write_text(json.dumps(report, indent=1, default=to_py))
print(json.dumps(report, indent=1, default=to_py))
