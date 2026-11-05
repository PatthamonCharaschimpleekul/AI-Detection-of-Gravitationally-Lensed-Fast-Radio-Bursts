"""How much real spectral structure sits below each channel width? Uses the brightest repeater bursts.
For block size b (native channels): fine-scale variance = var(spectrum - block-mean), on-pulse minus a same-length
off-pulse stretch (noise), as a fraction of the total signal variance in the spectrum."""
import csv, sys
from pathlib import Path
import h5py, numpy as np

d = Path(sys.argv[1]); N = int(sys.argv[2])
rows = {}
for r in csv.DictReader(open(d / "chimefrbcat2.csv", newline="")):
    if r["repeater_name"] not in ("", "-9999"):
        rows.setdefault(r["tns_name"], r)
snr = lambda r: float(r["snr_fitb"]) if r["snr_fitb"] not in ("", "nan", "-9999") else 0
top = sorted(rows.values(), key=snr, reverse=True)[:N]
B = [16, 64, 256, 1024]

def fine_var(s, b):
    blk = np.nanmean(s.reshape(-1, b), 1)
    return np.nanvar(s - np.repeat(blk, b))

res, ripple = [], []
for r in top:
    with h5py.File(d / "dynamic_spectra" / f"{r['tns_name']}_stokesi_dynamic_spectrum.h5", "r") as f:
        x = f["data"][:].astype(float); m = f["model"][:]; g = f["good_freq"][:].astype(bool)
    x[~g] = np.nan
    ts = np.nansum(np.where(g[:, None], m, 0), 0)
    if ts.max() <= 0: continue
    on = ts > 0.2 * ts.max(); n_on = on.sum()
    idx = np.flatnonzero(on)
    off_start = 0 if idx[0] > 2 * n_on else (idx[-1] + n_on if idx[-1] + 2 * n_on < x.shape[1] else None)
    if off_start is None: continue
    S = np.nanmean(x[:, on], 1); Nn = np.nanmean(x[:, off_start:off_start + n_on], 1)
    tot = np.nanvar(S) - np.nanvar(Nn)
    if tot <= 0: continue
    res.append([(fine_var(S, b) - fine_var(Nn, b)) / tot for b in B])
    sd = np.nanstd(x[:, ~on], 1); fold = np.array([np.nanmedian(sd[k::16]) for k in range(16)])
    ripple.append(fold / np.nanmedian(fold))
res = np.array(res)
print(f"{len(res)} bright bursts (snr_fitb {snr(top[-1]):.0f}-{snr(top[0]):.0f})")
for b, col in zip(B, res.T):
    print(f"structure finer than {b:5d} ch ({b*0.0244:6.2f} MHz, {16384//b:5d} channels kept): "
          f"median {np.median(col):6.1%}  [16-84%: {np.percentile(col,16):6.1%} .. {np.percentile(col,84):6.1%}]")
rp = np.median(ripple, 0)
print("off-pulse std folded mod 16 channels (1.0 = median):", np.round(rp, 3))
