"""Calibration identity check on real negatives: E_U[r] = 1 for a true likelihood ratio r = p(x|lensed)/p(x|unrelated).

Reads outputs/stage3_generic_scores.npz (written by transfer_check.py). For each learned model, r_hat = exp(log-ratio
lensed vs unrelated), from balanced-class training. On simulated unrelated pairs the mean should be near 1 if the
network is calibrated; on real cross-source pairs (true unrelated pairs) a mean well above 1 means the model claims
more evidence on real negatives than its training supports, which would bias any posterior odds.

Real pairs share bursts, so uncertainty comes from a source bootstrap (pairs weighted by both sources' multiplicities,
as transfer_check.boot_fpr), and the betting e-process (Waudby-Smith & Ramdas 2024) is run on source-pair means,
treated as approximately independent units. Both are reported; the bootstrap is the primary interval.
Only true negatives are scored (blind protocol). Usage: python eh0_check.py
"""
import math
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent / "outputs"
LAMS = np.linspace(0.01, 0.99, 50)  # betting fractions, mixed uniformly
B, SEED, CLIP = 2000, 2026, 50.0


def e_value(r):
    """Mixture betting e-value against H0: E[r] <= 1, for r >= 0. Each factor 1 + lambda (r - 1) >= 1 - lambda > 0
    has expectation <= 1 under H0, so the product (and the uniform mixture over lambda) is an e-value."""
    lw = np.log1p(LAMS[None] * (np.asarray(r)[:, None] - 1)).sum(0)
    return float(np.exp(np.logaddexp.reduce(lw) - math.log(len(LAMS))))


def main():
    d = np.load(OUT / "stage3_generic_scores.npz", allow_pickle=True)
    sa, sb = d["src_a"].astype(str), d["src_b"].astype(str)
    names = sorted(set(sa) | set(sb))
    idx = {s: k for k, s in enumerate(names)}
    ia, ib = np.array([idx[s] for s in sa]), np.array([idx[s] for s in sb])
    rng = np.random.default_rng(SEED)
    lines = ["E_U[r_hat] on val-split pairs: simulated unrelated (reference) and real cross-source (true negatives)."]
    for key in [k for k in d.files if k.startswith("real|") and k.endswith("|LvU")]:
        m = key[len("real|"):]
        r_real = np.exp(np.clip(d[key], None, CLIP))
        r_sim = np.exp(np.clip(d[f"sim|{m}"], None, CLIP))
        boots = []
        for _ in range(B):
            cnt = np.bincount(rng.integers(len(names), size=len(names)), minlength=len(names))
            w = cnt[ia] * cnt[ib]
            if w.sum():
                boots.append((w * r_real).sum() / w.sum())
        lo, hi = np.quantile(boots, [0.025, 0.975])
        pairs = {}
        for a, b, r in zip(sa, sb, r_real):
            pairs.setdefault(tuple(sorted((a, b))), []).append(r)
        unit = np.array([np.mean(v) for v in pairs.values()])
        lines.append(f"{m}: sim mean {r_sim.mean():.3f} (n {len(r_sim)}) | real mean {r_real.mean():.3f} "
                     f"[{lo:.3f}, {hi:.3f}] (n {len(r_real)}, {len(names)} sources) | median log10 r real "
                     f"{np.median(np.log10(r_real)):+.2f}, sim {np.median(np.log10(r_sim)):+.2f} | "
                     f"betting e-value on {len(unit)} source-pair means {e_value(unit):.3g} (reject E<=1 at 5% if >= 20)")
    txt = "\n".join(lines)
    print(txt)
    (OUT / "eh0_val.txt").write_text(txt + "\n")


if __name__ == "__main__":
    main()
