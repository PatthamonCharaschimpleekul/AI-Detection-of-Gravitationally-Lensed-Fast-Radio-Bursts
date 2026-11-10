"""Held-out check of the Track C false-alarm rate (04_validation/03_false_alarm).

For each source, set k_thr from N calibration scrambles exactly as timing.py does, then count exceedances
k_max >= k_thr in N fresh scrambles drawn from an independent stream. Reports the realised per-source rate and the
expected number of false sources over the whole sample. Only time-scrambled lists are scored (blind protocol).

Usage: python far_check.py [--scrambles 2000] [--far 1e-3]
"""
import argparse
import csv

import numpy as np

from timing import OUT, SEED, k_max, load_sources, scramble


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scrambles", type=int, default=2000)
    ap.add_argument("--far", type=float, default=1e-3)
    a = ap.parse_args()
    cal, test = np.random.default_rng(SEED + 1), np.random.default_rng(SEED + 2)
    rows = []
    for name, src in load_sources().items():
        bg = np.array([k_max(scramble(src, cal), src["err"], src["snr"]) for _ in range(a.scrambles)])
        k_thr = next(k for k in range(2, 50) if (bg >= k).mean() <= a.far)
        ho = np.array([k_max(scramble(src, test), src["err"], src["snr"]) for _ in range(a.scrambles)])
        rows.append(dict(source=name, n_bursts=src["n"], k_thr=k_thr, cal_exceed=int((bg >= k_thr).sum()),
                         test_exceed=int((ho >= k_thr).sum()), test_p_k2=round(float((ho >= 2).mean()), 4)))
        print(rows[-1], flush=True)
    with open(OUT / "far_check.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    hits = np.array([r["test_exceed"] for r in rows])
    n_src, total = len(rows), hits.sum()
    rate = total / (n_src * a.scrambles)
    # one-sided 95% Poisson upper bound on the pooled count (Garwood), via chi-square quantile
    from scipy.stats import chi2
    up = chi2.ppf(0.95, 2 * (total + 1)) / 2 / (n_src * a.scrambles)
    print(f"held-out exceedances {total} in {n_src} x {a.scrambles} scrambles: rate {rate:.2e} "
          f"(95% upper {up:.2e}; nominal {a.far:.0e}); expected false sources per search {n_src * rate:.3f} "
          f"(95% upper {n_src * up:.3f}); worst source {rows[int(hits.argmax())]['source']} {hits.max()}/{a.scrambles}")


if __name__ == "__main__":
    main()
