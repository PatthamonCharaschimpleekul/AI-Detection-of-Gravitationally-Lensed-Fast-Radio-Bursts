"""Is the sub-390 kHz structure scalloping (repeats every 16 channels, same in every burst) or scintillation
(random, a frequency ACF with a characteristic width)? On-pulse spectrum of the brightest bursts."""
import csv, sys
from pathlib import Path
import h5py, numpy as np
d = Path(sys.argv[1]); N = int(sys.argv[2])
rows = {}
for r in csv.DictReader(open(d / "chimefrbcat2.csv", newline="")):
    if r["repeater_name"] not in ("", "-9999"): rows.setdefault(r["tns_name"], r)
snr = lambda r: float(r["snr_fitb"]) if r["snr_fitb"] not in ("", "nan", "-9999") else 0
top = sorted(rows.values(), key=snr, reverse=True)[:N]
folds, out = [], []
for r in top:
    with h5py.File(d / "dynamic_spectra" / f"{r['tns_name']}_stokesi_dynamic_spectrum.h5", "r") as f:
        x = f["data"][:].astype(float); m = f["model"][:]; g = f["good_freq"][:].astype(bool)
    ts = np.nansum(np.where(g[:, None], m, 0), 0)
    if ts.max() <= 0: continue
    on = ts > 0.2 * ts.max()
    S = np.nanmean(x[:, on], 1); S[~g] = np.nan
    blk = np.repeat(np.nanmean(S.reshape(-1, 64), 1), 64)          # 1.56 MHz envelope
    ok = g & np.isfinite(S) & (blk > 0.3 * np.nanmax(blk))           # inside the burst's emitting band
    if ok.sum() < 2000: continue
    rel = np.where(ok, S / blk - 1, np.nan)
    folds.append([np.nanmean(rel[k::16]) for k in range(16)])
    z = np.nan_to_num(rel); w = ok.astype(float)
    num = np.array([np.sum(z[:-l or None] * z[l:]) for l in range(0, 65)])
    den = np.array([np.sum(w[:-l or None] * w[l:]) for l in range(0, 65)])
    acf = num / den; acf /= acf[1] if acf[1] > 0 else 1                # lag 0 holds the noise spike
    half = next((l for l in range(1, 65) if acf[l] < 0.5), 64)
    out.append((r["tns_name"], r["repeater_name"], snr(r), half, acf[1], np.nanstd(folds[-1]), np.nanstd(rel)))
F = np.array(folds)
print("mean on-pulse ripple folded mod 16 (fraction):", np.round(F.mean(0), 3))
print("ripple amplitude (std of fold) median:", f"{np.median([o[5] for o in out]):.3f}", "vs total fine scatter median:", f"{np.median([o[6] for o in out]):.3f}")
print("name, source, snr, ACF half-width (channels of 24.4 kHz):")
for o in out: print(f"  {o[0]} {o[1]} snr={o[2]:.0f} half={o[3]} ch = {o[3]*24.4:.0f} kHz")
h = np.array([o[3] for o in out]); print(f"median half-width {np.median(h):.0f} ch = {np.median(h)*24.4:.0f} kHz; {np.mean(h>=64):.0%} hit the 64-ch limit")
