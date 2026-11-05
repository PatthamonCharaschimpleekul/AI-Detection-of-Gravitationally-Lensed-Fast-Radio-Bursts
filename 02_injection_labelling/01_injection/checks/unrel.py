import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, h5py
from inject import load_pools, member, xcorr, REAL, SNR_MIN
c = load_pools()["train"].c
with h5py.File(REAL / "preproc" / "repeaters_256x160.h5") as f:
    Xr, FMr = f["X"][:], f["freq_mask"][:]
el = np.flatnonzero(c["eligible"])
src = c["source"]; S = sorted(set(src[el]))
for kind in ("same source", "different source"):
    out = []
    for seed in (21, 22, 23):
        rr = np.random.default_rng(seed); R, M = [], []
        for q in range(1000):
            if kind == "same source":
                s = S[rr.integers(len(S))]; v = el[src[el] == s]
                if len(v) < 2: continue
                i, j = rr.choice(v, 2, replace=False)
            else:
                i, j = rr.choice(el, 2, replace=False)
                if src[i] == src[j]: continue
            b1, b2 = rr.choice(np.flatnonzero(~np.isin(c["bg_file"], [i, j])), 2, replace=False)
            R.append(xcorr(Xr[i], FMr[i] >= .25, Xr[j], FMr[j] >= .25))
            g = np.random.default_rng([78, q])
            xi, mi, _ = member(c, i, b1, max(c["model_snr"][i], SNR_MIN), g, 0.0, False, ("shift", "dm", "scint"))
            xj, mj, _ = member(c, j, b2, max(c["model_snr"][j], SNR_MIN), g, 0.0, False, ("shift", "dm", "scint"))
            M.append(xcorr(xi, mi, xj, mj))
        R, M = np.array(R), np.array(M)
        out.append((np.median(M - R) / np.median(R), np.median(R), np.median(M), len(R)))
    o = np.array(out)
    print(f"{kind:16s} naked-vs-real gap over 3 seeds: {', '.join(f'{x:+.1%}' for x in o[:, 0])}  (real median {o[:,1].mean():.4f}, naked {o[:,2].mean():.4f}, n/seed ~{int(o[:,3].mean())})")
