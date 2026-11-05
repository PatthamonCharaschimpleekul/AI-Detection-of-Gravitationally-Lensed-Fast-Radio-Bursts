"""v2 prerequisites (plan addendum 16:00): contrast CI, then residual shared-noise scan."""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, h5py
from scipy.ndimage import uniform_filter
from inject import load_pools, member, xcorr, REAL, SNR_MIN, R_MIN, WIN
pools = load_pools(); P = pools["train"]; c = P.c
with h5py.File(REAL / "preproc" / "repeaters_256x160.h5") as f:
    Xr, FMr, TMr = f["X"][:], f["freq_mask"][:], f["time_mask"][:]
el = np.flatnonzero(c["eligible"]); src = c["source"]
ALLN = ("shift", "dm", "scint")
# ---- 1. bootstrap CI of the same/different contrast, real vs naked ----
rr = np.random.default_rng(31)
S = sorted(set(src[el])); d = {"same": ([], []), "diff": ([], [])}
for q in range(4000):
    if q % 2 == 0:
        v = el[src[el] == S[rr.integers(len(S))]]
        if len(v) < 2: continue
        i, j = rr.choice(v, 2, replace=False); kind = "same"
    else:
        i, j = rr.choice(el, 2, replace=False)
        if src[i] == src[j]: continue
        kind = "diff"
    b1, b2 = rr.choice(np.flatnonzero(~np.isin(c["bg_file"], [i, j])), 2, replace=False)
    d[kind][0].append(xcorr(Xr[i], FMr[i] >= .25, Xr[j], FMr[j] >= .25))
    g = np.random.default_rng([79, q])
    xi, mi, _ = member(c, i, b1, max(c["model_snr"][i], SNR_MIN), g, 0.0, False, ALLN)
    xj, mj, _ = member(c, j, b2, max(c["model_snr"][j], SNR_MIN), g, 0.0, False, ALLN)
    d[kind][1].append(xcorr(xi, mi, xj, mj))
A = {k: (np.array(a), np.array(b)) for k, (a, b) in d.items()}
bs = np.random.default_rng(0)
out = {"real": [], "naked": [], "diff": []}
for _ in range(2000):
    s = bs.integers(0, len(A["same"][0]), len(A["same"][0])); t = bs.integers(0, len(A["diff"][0]), len(A["diff"][0]))
    cr = np.median(A["same"][0][s]) / np.median(A["diff"][0][t]) - 1
    cn = np.median(A["same"][1][s]) / np.median(A["diff"][1][t]) - 1
    out["real"].append(cr); out["naked"].append(cn); out["diff"].append(cn - cr)
for k, v in out.items():
    v = np.array(v); print(f"contrast {k:5s}: {np.median(v):+.1%}  95% CI {np.percentile(v, 2.5):+.1%} .. {np.percentile(v, 97.5):+.1%}")
print(f"  (n same {len(A['same'][0])}, diff {len(A['diff'][0])})")
# ---- 2. residual scan ----
rng = np.random.default_rng(41)
pool = P.snr_pool
rows = []
for nf in (4, 16, 32):
    for nt in (1, 3, 5):
        for th in (1.0, 2.0, 3.0):
            rec, exc, rho_p, z_m, kept_n = [], [], [], [], []
            for t in el:
                m = (FMr[t] >= .25)[:, None] & (TMr[t] > 0)[None, :]
                Ts = c["T"][t] / np.maximum(c["sigma"][t], 1e-12)[:, None]
                b = (Xr[t][m] * Ts[m]).sum() / (Ts[m] ** 2).sum()
                res = np.where(m, Xr[t] - b * Ts, 0.0)
                box = np.zeros_like(m); box[:, max(c["extent_lo"][t] - 10, 0):min(c["extent_hi"][t] + 11, WIN)] = True; box &= m
                w = uniform_filter(m.astype(float), (nf, nt), mode="constant") * nf * nt
                Sm = uniform_filter(res, (nf, nt), mode="constant") * nf * nt / np.maximum(w, 1)
                sig = 1 / np.sqrt(np.maximum(w, 1))
                kept = box & (np.abs(Sm) >= th * sig)
                exc.append((res[box] ** 2).sum() - box.sum())
                rec.append((Sm[kept] ** 2).sum() - (sig[kept] ** 2).sum())
                kept_n.append(kept.sum())
                if kept.sum() < 10:
                    rho_p.append(0.0); z_m.append(0.0); continue
                # noise-only proxy: smoothed independent real noise on the same kept cells
                bn, b1, b2 = rng.choice(len(c["bg_X"]), 3, replace=False)
                n = np.where(m, c["bg_X"][bn], 0.0)
                Rn = np.where(kept, uniform_filter(n, (nf, nt), mode="constant") * nf * nt / np.maximum(w, 1), 0.0)
                snr_a = rng.choice(pool); r = np.exp(rng.uniform(np.log(max(R_MIN, SNR_MIN / snr_a)), 0))
                ka = snr_a / c["model_snr"][t]; kb = r * ka
                m1 = ka * Rn + c["bg_X"][b1]; m2 = kb * Rn + c["bg_X"][b2]
                rho_p.append(np.corrcoef(m1[kept], m2[kept])[0, 1])
                s1 = uniform_filter(m1, (nf, nt), mode="constant"); s2 = uniform_filter(m2, (nf, nt), mode="constant")
                rs = np.corrcoef(s1[kept], s2[kept])[0, 1]
                z_m.append(rs * np.sqrt(kept.sum() / (nf * nt)))
            rec, exc = np.array(rec), np.array(exc)
            frac = np.median(rec / np.maximum(exc, 1e-9))
            rp, zm = np.median(rho_p), np.median(z_m)
            ok = rp <= 0.01 and zm <= 1.0
            rows.append((nf, nt, th, frac, np.median(kept_n), rp, zm, ok))
            print(f"nf={nf:2d} nt={nt} th={th:.0f}: recovered {frac:6.1%} of excess, kept {np.median(kept_n):6.0f} cells, "
                  f"pixel rho {rp:.4f}, matched z {zm:5.2f}  G-noise {'PASS' if ok else 'fail'}", flush=True)
p = [r for r in rows if r[-1]]
print("passing configs:", len(p), "best:", max(p, key=lambda r: r[3]) if p else None)
