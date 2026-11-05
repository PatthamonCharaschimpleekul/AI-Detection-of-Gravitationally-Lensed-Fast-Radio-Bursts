"""Contrast (same vs different source), twin offset and twin Spearman per S/N bin, real vs v1 sim.
Pairs are real burst pairs; each is re-simulated from its own two templates at their measured
S/N on fresh backgrounds with full v1 nuisances. Bin = min(model_snr) of the pair."""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, h5py
from scipy.stats import spearmanr
from inject import load_pools, member, xcorr, REAL, SNR_MIN
c = load_pools()["train"].c
with h5py.File(REAL / "preproc" / "repeaters_256x160.h5") as f:
    Xr, FMr = f["X"][:], f["freq_mask"][:]
el = np.flatnonzero(c["eligible"]); src = c["source"]; S = sorted(set(src[el]))
rr = np.random.default_rng(51)
rows = []  # (same?, smin, real, sim)
for q in range(12000):
    if q % 2 == 0:
        v = el[src[el] == S[rr.integers(len(S))]]
        if len(v) < 2: continue
        i, j = rr.choice(v, 2, replace=False)
    else:
        i, j = rr.choice(el, 2, replace=False)
        if src[i] == src[j]: continue
    b1, b2 = rr.choice(np.flatnonzero(~np.isin(c["bg_file"], [i, j])), 2, replace=False)
    g = np.random.default_rng([80, q])
    si, sj = max(c["model_snr"][i], SNR_MIN), max(c["model_snr"][j], SNR_MIN)
    xi, mi, _ = member(c, i, b1, si, g, 0.0, False)
    xj, mj, _ = member(c, j, b2, sj, g, 0.0, False)
    # second independent sim of the same pair (other backgrounds, other draws): the noise ceiling
    b3, b4 = rr.choice(np.flatnonzero(~np.isin(c["bg_file"], [i, j, c["bg_file"][b1], c["bg_file"][b2]])), 2, replace=False)
    g2 = np.random.default_rng([81, q])
    yi, ni, _ = member(c, i, b3, si, g2, 0.0, False)
    yj, nj, _ = member(c, j, b4, sj, g2, 0.0, False)
    rows.append((src[i] == src[j], min(si, sj), xcorr(Xr[i], FMr[i] >= .25, Xr[j], FMr[j] >= .25), xcorr(xi, mi, xj, mj), xcorr(yi, ni, yj, nj)))
same, smin, real, sim, sim2 = (np.array(x) for x in zip(*rows))
bs = np.random.default_rng(0)
def ci(f, *arrs, n=1000):
    v = [f(*[a[ix] for a, ix in zip(arrs, [bs.integers(0, len(a), len(a)) for a in arrs])]) for _ in range(n)]
    return np.percentile(v, [2.5, 97.5])
print(f"{'min S/N':>9s} {'n same/diff':>11s} | {'real contrast':>22s} | {'sim contrast':>22s} | {'same-pair offset':>22s} | Spearman same: sim-real / sim-sim ceiling")
for lo, hi in ((10, 15), (15, 25), (25, 50), (50, 1e9)):
    b = (smin >= lo) & (smin < hi)
    rs, rd, ms, md = real[b & same], real[b & ~same], sim[b & same], sim[b & ~same]
    if len(rs) < 30 or len(rd) < 30:
        print(f"{lo:>4}-{hi if hi < 1e9 else 'inf':<4} {len(rs):5d}/{len(rd):<5d} too few"); continue
    con = lambda a, d: np.median(a) / np.median(d) - 1
    off = lambda a, r: np.median(a - r) / np.median(r)
    cr, cs = con(rs, rd), con(ms, md)
    o = off(ms, rs)
    lr, hr = ci(con, rs, rd); ls, hs = ci(con, ms, md)
    # offset CI must resample pairs jointly
    ov = [off(ms[ix], rs[ix]) for ix in bs.integers(0, len(rs), (1000, len(rs)))]
    print(f"{lo:>4}-{hi if hi < 1e9 else 'inf':<4} {len(rs):5d}/{len(rd):<5d} | {cr:+6.1%} [{lr:+6.1%},{hr:+6.1%}] | "
          f"{cs:+6.1%} [{ls:+6.1%},{hs:+6.1%}] | {o:+6.1%} [{np.percentile(ov, 2.5):+6.1%},{np.percentile(ov, 97.5):+6.1%}] | "
          f"{spearmanr(rs, ms).statistic:.2f} / {spearmanr(sim2[b & same], ms).statistic:.2f}")
