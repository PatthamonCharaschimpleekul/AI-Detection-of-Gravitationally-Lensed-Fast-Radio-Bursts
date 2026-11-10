"""Separate sim-to-real transfer from sample composition in the Stage 3 check (development, val sources).

Stage 3 compares real cross-source pairs with *generic* simulated unrelated pairs, whose S/N and template mix differ
from the real pairs'. The twins re-simulate each real pair from its own two templates at its own S/N, so at the same
threshold:
  real FPR - twin FPR   = transfer gap (what the simulator misses),
  twin FPR - 1%         = composition effect (which pairs, at which S/N).
Twin FPR is the mean over the two twin draws. Interval on the transfer gap: source bootstrap (pairs weighted by both
sources' multiplicities, as transfer_check.boot_fpr). Reads outputs/stage3_generic_scores.npz. Output: outputs/stage3_twin_fpr.txt
"""
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent / "outputs"
BINS = ((10, 25, "S/N 10-25"), (25, 50, "S/N 25-50"), (50, np.inf, "S/N >= 50"), (25, np.inf, "S/N >= 25 (headline)"))
B, SEED = 2000, 2026


def main():
    z = np.load(OUT / "stage3_generic_scores.npz", allow_pickle=True)
    r, s = z["r_smin"], z["s_smin"]
    sa, sb = z["src_a"].astype(str), z["src_b"].astype(str)
    names = sorted(set(sa) | set(sb))
    idx = {n: k for k, n in enumerate(names)}
    ia, ib = np.array([idx[x] for x in sa]), np.array([idx[x] for x in sb])
    rng = np.random.default_rng(SEED)
    W = []
    for _ in range(B):
        cnt = np.bincount(rng.integers(len(names), size=len(names)), minlength=len(names))
        W.append(cnt[ia] * cnt[ib])
    W = np.array(W, float)
    methods = [k[len("real|"):] for k in z.files if k.startswith("real|") and not k.endswith("|LvU")]
    lines = ["FPR at the threshold giving 1% on generic simulated unrelated pairs: real, twin (mean of 2 draws), and the",
             "transfer gap real - twin [95% source bootstrap]. Composition effect = twin - 1%."]
    for lo, hi, lab in BINS:
        ss, sr = (s >= lo) & (s < hi), (r >= lo) & (r < hi)
        lines.append(f"\n{lab}: {sr.sum()} real pairs, median pair S/N real {np.median(r[sr]):.1f} vs generic sim {np.median(s[ss]):.1f}")
        for m in methods:
            th = np.quantile(z[f"sim|{m}"][ss], 0.99)
            fr = (z[f"real|{m}"] > th) & sr
            ft = (((z[f"twin1|{m}"] > th).astype(float) + (z[f"twin2|{m}"] > th)) / 2) * sr
            w = W[:, sr]
            ok = w.sum(1) > 0
            gap = ((w * (fr[sr] - ft[sr])).sum(1)[ok] / w.sum(1)[ok])
            g_lo, g_hi = np.quantile(gap, [0.025, 0.975])
            lines.append(f"  {m:14s} real {fr[sr].mean():.3f}  twin {ft[sr].mean():.3f}  gap {fr[sr].mean() - ft[sr].mean():+.3f} "
                         f"[{g_lo:+.3f}, {g_hi:+.3f}]")
    txt = "\n".join(lines)
    print(txt)
    (OUT / "stage3_twin_fpr.txt").write_text(txt + "\n")


if __name__ == "__main__":
    main()
