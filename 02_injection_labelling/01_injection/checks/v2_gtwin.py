"""G-twin for the one pre-registered v2 config (32 ch x 5 samples, theta=1): twin gap of T+R_s vs real."""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, h5py
from scipy.ndimage import uniform_filter
from inject import load_pools, member, xcorr, REAL, SNR_MIN, WIN
P = load_pools()["train"]; c = P.c
with h5py.File(REAL / "preproc" / "repeaters_256x160.h5") as f:
    Xr, FMr, TMr = f["X"][:], f["freq_mask"][:], f["time_mask"][:]
el = np.flatnonzero(c["eligible"]); src = c["source"]
NF_, NT_, TH = 32, 5, 1.0
T2 = c["T"].copy()
for t in el:
    m = (FMr[t] >= .25)[:, None] & (TMr[t] > 0)[None, :]
    Ts = c["T"][t] / np.maximum(c["sigma"][t], 1e-12)[:, None]
    b = (Xr[t][m] * Ts[m]).sum() / (Ts[m] ** 2).sum()
    res = np.where(m, Xr[t] - b * Ts, 0.0)
    box = np.zeros_like(m); box[:, max(c["extent_lo"][t] - 10, 0):min(c["extent_hi"][t] + 11, WIN)] = True; box &= m
    w = uniform_filter(m.astype(float), (NF_, NT_), mode="constant") * NF_ * NT_
    Sm = uniform_filter(res, (NF_, NT_), mode="constant") * NF_ * NT_ / np.maximum(w, 1)
    kept = box & (np.abs(Sm) >= TH / np.sqrt(np.maximum(w, 1)))
    T2[t] = c["T"][t] + np.where(kept, Sm, 0.0) * c["sigma"][t][:, None] / b  # back to raw model units
c2 = dict(c); c2["T"] = T2
byT = {s: el[src[el] == s] for s in np.unique(src[el])}; byT = {s: v for s, v in byT.items() if len(v) >= 2}; kT = sorted(byT)
for label, off in (("v2 full nuisances", ()), ("v2 scint off (upper bound)", ("scint",)), ("v2 naked", ("shift", "dm", "scint")), ("v1 naked (reference)", "v1")):
    R, M = [], []
    for seed in (11, 12, 13):
        rr = np.random.default_rng(seed)
        for q in range(1000):
            i, j = rr.choice(byT[kT[rr.integers(len(kT))]], 2, replace=False)
            b1, b2 = rr.choice(np.flatnonzero(~np.isin(c["bg_file"], [i, j])), 2, replace=False)
            R.append(xcorr(Xr[i], FMr[i] >= .25, Xr[j], FMr[j] >= .25))
            g = np.random.default_rng([77, seed, q])
            cc, o = (c, ("shift", "dm", "scint")) if off == "v1" else (c2, off)
            xi, mi, _ = member(cc, i, b1, max(c["model_snr"][i], SNR_MIN), g, 0.0, False, o)
            xj, mj, _ = member(cc, j, b2, max(c["model_snr"][j], SNR_MIN), g, 0.0, False, o)
            M.append(xcorr(xi, mi, xj, mj))
    R, M = np.array(R), np.array(M)
    gap = np.median(M - R) / np.median(R)
    bs = [np.median((M - R)[ix]) / np.median(R[ix]) for ix in np.random.default_rng(0).integers(0, len(R), (500, len(R)))]
    print(f"{label:28s} gap {gap:+.1%}  95% CI {np.percentile(bs, 2.5):+.1%}..{np.percentile(bs, 97.5):+.1%}  "
          f"G-twin(|gap|<=2pt) {'PASS' if abs(gap) <= 0.02 else 'fail'}", flush=True)
