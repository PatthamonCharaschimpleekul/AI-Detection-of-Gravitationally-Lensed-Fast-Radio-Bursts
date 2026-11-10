"""Can real repeat pairs, with no labels and no simulator, reveal a wrong LR?

A true LR obeys E_H0[r] = 1 for any repeat population. So on known repeat pairs, a mean r_hat
above 1 shows the score is anti-conservative for that population. This asks how many
independent pairs that takes, using a test valid without knowing the score's distribution:
the betting e-process W_n = prod(1 + lam (r_i - 1)), with lam mixed over a grid, is a
nonnegative martingale when E[r] <= 1, so rejecting at W_n >= 1/alpha has level alpha.

Also checks temperature-scaled `naive`, whose tail RMSE looks best, for overclaiming.
"""
import json
import math
from pathlib import Path

import numpy as np

from sim import SimConfig

cfg = SimConfig()
n_rho = len(cfg.rhos)
strat = np.load("outputs/testset/stratum.npy")
idx = [np.where(strat == i)[0] for i in range(n_rho)]
is_h1 = strat == n_rho
n_per = int(is_h1.sum())
LN10 = math.log(10)
LAMS = np.array([0.01, 0.03, 0.1, 0.3, 0.9])
PRIORS = {"nominal": np.array(cfg.p_rho), "uniform": np.full(n_rho, 1 / n_rho),
          "hard": np.array([0, 0, 0, .1, .2, .3, .4])}
# Mild misspecification: a fraction eps of the population is uniform over rho.
for eps in (0.05, 0.1, 0.25, 0.5):
    PRIORS[f"mix{eps:g}"] = (1 - eps) * PRIORS["nominal"] + eps * PRIORS["uniform"]
NS = (83, 300, 1000, 5000, 20000)
TRIALS = 400


def draw(s, p, n, rng):
    """n pairs from a repeat population with prior p over rho, as r_hat values."""
    counts = rng.multinomial(n, p)
    return np.concatenate([np.exp(np.clip(s[rng.choice(idx[i], c)], None, 50)) for i, c in enumerate(counts)])


def rejects(r, alpha=0.05):
    log_wealth = np.log1p(LAMS[None] * (r[:, None] - 1)).sum(0)
    return np.logaddexp.reduce(log_wealth) - math.log(len(LAMS)) >= math.log(1 / alpha)


def power(s, p, n, rng):
    return float(np.mean([rejects(draw(s, p, n, rng)) for _ in range(TRIALS)]))


rng = np.random.default_rng(20261107)
res = {"exact": {}, "models": {}}
exact = np.load("outputs/testset/log_r.npy").astype(np.float64)
print("rejection rate of 'E_H0[r_hat] <= 1' at level 0.05, by number of independent repeat pairs")
print("score / population".ljust(40) + "".join(str(n).rjust(8) for n in NS) + "   E[r_hat]")
targets = [("exact", exact)]
for name in ("plain_w48_s30000_seed0", "plain_w48_s60000_seed0", "iw_w48_s30000_seed0", "naive_w48_s30000_seed0"):
    targets.append((name, np.load(f"outputs/runs/{name}/log_r.npy").astype(np.float64)))
for name, s in targets:
    for pname, p in PRIORS.items():
        row = {n: power(s, p, n, rng) for n in NS}
        mean = sum(p[i] * np.exp(np.clip(s[idx[i]], None, 50)).mean() for i in range(n_rho))
        res["models"][f"{name}|{pname}"] = {"power": row, "E_r": float(mean)}
        print(f"{name} / {pname}".ljust(40) + "".join(f"{row[n]:8.2f}" for n in NS) + f"{mean:10.2f}")

# Temperature-scaled naive: does its lower RMSE come with honest scores?
w0 = np.zeros(len(strat))
p0 = np.array(cfg.p_rho)
w0[~is_h1] = p0[strat[~is_h1]] / n_per
print("\ntemperature-scaled naive: claim vs observed log10 ratio, and E_H0")
res["ts_naive"] = {}
for seed in (0, 1, 2):
    d = Path(f"outputs/runs/naive_w48_s30000_seed{seed}")
    s = np.load(d / "log_r.npy").astype(np.float64)
    cal = np.load(d / "calib.npz")
    from scipy.optimize import minimize_scalar
    f = lambda T: (cal["y"] * np.logaddexp(0, -cal["s"] / T) + (1 - cal["y"]) * np.logaddexp(0, cal["s"] / T)).mean()
    T = minimize_scalar(f, bounds=(0.2, 5.0), method="bounded").x
    ts = s / T
    rows = []
    for lo, hi in ((1, 2), (2, 3), (3, 4), (4, 6)):
        sel = (ts / LN10 >= lo) & (ts / LN10 < hi)
        n1, h0 = (sel & is_h1).sum(), w0[sel].sum()
        if n1 and h0:
            rows.append([lo, hi, float(ts[sel & is_h1].mean() / LN10), float(np.log10(n1 / n_per / h0))])
    e = float((w0 * np.exp(np.clip(ts, None, 50))).sum())
    res["ts_naive"][seed] = {"T": T, "bins_lo_hi_h1claim_observed": rows, "E_H0": e}
    print(f"seed{seed} T={T:.3f} E_H0={e:.2f} " + " | ".join(f"[{a},{b}) {c:.2f} vs {o:.2f}" for a, b, c, o in rows))

Path("outputs/diagnostic_power.json").write_text(json.dumps(res, indent=1))
