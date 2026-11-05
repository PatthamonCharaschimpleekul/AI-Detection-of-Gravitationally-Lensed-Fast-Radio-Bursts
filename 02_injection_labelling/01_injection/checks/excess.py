import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, h5py
from inject import load_pools, member, xcorr, REAL, SNR_MIN, WIN
c = load_pools()["train"].c
with h5py.File(REAL / "preproc" / "repeaters_256x160.h5") as f:
    Xr, FMr, TMr = f["X"][:], f["freq_mask"][:], f["time_mask"][:]
el = np.flatnonzero(c["eligible"])
fr = []
for k in el:
    m = (FMr[k] >= .25)[:, None] & (TMr[k] > 0)[None, :]
    lo, hi = max(c["extent_lo"][k], 0), min(c["extent_hi"][k] + 1, WIN)
    box = np.zeros_like(m); box[:, lo:hi] = True; box &= m
    # off-pulse box of equal size as noise reference
    Ts = c["T"][k] / np.maximum(c["sigma"][k], 1e-12)[:, None]
    b = (Xr[k][m] * Ts[m]).sum() / (Ts[m] ** 2).sum()
    res = Xr[k] - b * Ts
    ex = (res[box] ** 2).sum() - box.sum()  # unit-variance noise
    fr.append(ex / max(c["model_snr"][k] ** 2, 1e-9))
fr = np.array(fr)
print("unmodelled on-pulse signal energy / model energy: median %.3f, IQR %.3f..%.3f" % (np.median(fr), *np.percentile(fr, [25, 75])))
# bootstrap of the v1 'full' twin gap over pair resampling
byT = {s: el[c["source"][el] == s] for s in np.unique(c["source"][el])}
byT = {s: v for s, v in byT.items() if len(v) >= 2}
kT = sorted(byT)
for seed in (11, 12, 13):
    rr = np.random.default_rng(seed); R, S = [], []
    for q in range(1000):
        i, j = rr.choice(byT[kT[rr.integers(len(kT))]], 2, replace=False)
        b1, b2 = rr.choice(np.flatnonzero(~np.isin(c["bg_file"], [i, j])), 2, replace=False)
        R.append(xcorr(Xr[i], FMr[i] >= .25, Xr[j], FMr[j] >= .25))
        g = np.random.default_rng([77, q])
        xi, mi, _ = member(c, i, b1, max(c["model_snr"][i], SNR_MIN), g, 0.0, False)
        xj, mj, _ = member(c, j, b2, max(c["model_snr"][j], SNR_MIN), g, 0.0, False)
        S.append(xcorr(xi, mi, xj, mj))
    R, S = np.array(R), np.array(S); d = S - R
    bs = [np.median(d[ix]) / np.median(R[ix]) for ix in np.random.default_rng(0).integers(0, 1000, (500, 1000))]
    print(f"seed {seed}: full v1 gap {np.median(d) / np.median(R):+.1%}, bootstrap 95% CI {np.percentile(bs, 2.5):+.1%}..{np.percentile(bs, 97.5):+.1%}")
