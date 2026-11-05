import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, h5py
from inject import load_pools, member, xcorr, xcorr_smooth, REAL, SNR_MIN, WIN, NF
c = load_pools()["train"].c
with h5py.File(REAL / "preproc" / "repeaters_256x160.h5") as f:
    Xr, FMr = f["X"][:], f["freq_mask"][:]
BLK = 16
el = np.flatnonzero(c["eligible"])
# per-burst log ratio of on-pulse data spectrum to model spectrum (both in the file's sigma units), 16 x 25 MHz blocks
logR = np.full((len(c["tns"]), NF // BLK), np.nan)
for k in el:
    m = FMr[k] >= 0.25
    lo, hi = c["extent_lo"][k], c["extent_hi"][k] + 1
    Ts = c["T"][k] / np.maximum(c["sigma"][k], 1e-12)[:, None]
    sd = np.where(m, Xr[k][:, lo:hi].sum(1), 0).reshape(-1, BLK).sum(1)
    sm = np.where(m, Ts[:, lo:hi].sum(1), 0).reshape(-1, BLK).sum(1)
    b = sd.sum() / sm.sum()
    ok = sm > 0.1 * sm.max()
    logR[k, ok] = np.log(np.clip(sd[ok] / (b * sm[ok]), 0.05, 20))
def resp(src, excl):
    k = [t for t in el if c["source"][t] == src and t not in excl and np.isfinite(logR[t]).any()]
    if not k: return None
    e = np.nanmedian(logR[k], 0)
    return np.repeat(np.exp(np.nan_to_num(e, nan=0.0)), BLK)
def with_resp(c, idx, rp):
    """Apply a per-channel response to templates idx (member() no longer takes one)."""
    if rp is None:
        return c
    cr = dict(c); cr["T"] = c["T"].copy()
    for t in idx:
        cr["T"][t] = c["T"][t] * rp[:, None]
    return cr
byT = {s: el[c["source"][el] == s] for s in np.unique(c["source"][el])}
byT = {s: v for s, v in byT.items() if len(v) >= 2}
kT = sorted(byT); rr = np.random.default_rng(11)
out = {k: [] for k in ("real", "full", "full+resp", "naked+resp")}; has = []
for q in range(1000):
    i, j = rr.choice(byT[kT[rr.integers(len(kT))]], 2, replace=False)
    b1, b2 = rr.choice(np.flatnonzero(~np.isin(c["bg_file"], [i, j])), 2, replace=False)
    R = resp(c["source"][i], {i, j}); has.append(R is not None)
    out["real"].append((xcorr(Xr[i], FMr[i] >= .25, Xr[j], FMr[j] >= .25), xcorr_smooth(Xr[i], FMr[i] >= .25, Xr[j], FMr[j] >= .25)))
    for name, off, rp in (("full", (), None), ("full+resp", (), R), ("naked+resp", ("shift", "dm", "scint"), R)):
        g = np.random.default_rng([77, q])
        cr = with_resp(c, (i, j), rp)
        xi, mi, _ = member(cr, i, b1, max(c["model_snr"][i], SNR_MIN), g, 0.0, False, off)
        xj, mj, _ = member(cr, j, b2, max(c["model_snr"][j], SNR_MIN), g, 0.0, False, off)
        out[name].append((xcorr(xi, mi, xj, mj), xcorr_smooth(xi, mi, xj, mj)))
has = np.array(has); print("pairs with a leave-pair-out response:", has.sum(), "/ 1000")
ra = np.array(out["real"])
for k, v in out.items():
    v = np.array(v)
    for lab, sel in (("all", np.ones(1000, bool)), ("has resp", has)):
        g = [np.median(v[sel, d] - ra[sel, d]) / np.median(ra[sel, d]) for d in (0, 1)]
        print(f"{k:11s} {lab:9s} full-res gap {g[0]:+6.1%}  25MHz gap {g[1]:+6.1%}")
