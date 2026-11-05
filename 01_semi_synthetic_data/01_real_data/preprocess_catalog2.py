"""Preprocess CHIME/FRB Catalog 2 repeater dynamic spectra into model-ready arrays.

Plan: plan/2026-11-04_1547_catalog2-preprocessing.md
Usage: python -I preprocess_catalog2.py [data_dir] [--limit N]
Writes data_dir/preproc/repeaters_256x160.h5 and repeaters_1024x160.h5 plus a PNG
gallery in ../outputs/preproc_gallery/ (both skipped under --limit).

Design facts (checked 2026-11-05, plan step 1): `data` is dedispersed at
attrs.dm_incoherent, which equals the fitburst DM for 980/981 bursts (worst 1.61
pc/cc = 0.03 ms sweep, sub-sample) -> no re-dedispersion. Burst extent comes from
attrs.pulse_emission_region where present (all but 8 files), else the band-summed
fitburst model, else the smoothed data peak. The 160-sample window is centred on
the extent midpoint, zero-padded where the file is short, with a time mask.
"""
import csv, json, sys
from pathlib import Path

import h5py
import numpy as np
from scipy.signal import medfilt

WIN = 160                 # time samples per burst (157 ms at native dt)
DT_FINE = 0.98304e-3      # s
OFF_PAD = 20              # samples either side of the extent excluded from off-pulse stats
CH_KHZ = 24.4140625       # native channel width, kHz
JUNK = ("", "nan", "-9999")
HERE = Path(__file__).parent

args = [a for a in sys.argv[1:] if not a.startswith("--")]
LIMIT = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
d = Path(args[0]) if args else HERE / "data" / "catalog2"


def num(s):
    if s is None or s in JUNK:
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


# ---- burst table; rows are fitburst components ----
comps = {}
for r in csv.DictReader(open(d / "chimefrbcat2.csv", newline="")):
    if r["repeater_name"] not in ("", "-9999"):
        comps.setdefault(r["tns_name"], []).append(r)
names = sorted(comps)
if LIMIT:
    names = names[:LIMIT]
print(f"{len(names)} repeater bursts to process")


def extent_of(f, g):
    """(lo, hi) inclusive burst columns in the file's own time grid.
    pulse_emission_region can hold several rows (one per sub-band): take their union."""
    if "pulse_emission_region" in f.attrs:
        pr = np.asarray(f.attrs["pulse_emission_region"], float).reshape(-1, 2)
        pr = pr[np.isfinite(pr).all(1) & (pr[:, 1] >= pr[:, 0])]
        if len(pr):
            return int(pr[:, 0].min()), int(pr[:, 1].max())
    if "model" in f:
        p = np.where(g[:, None], np.nan_to_num(f["model"][:], nan=0.0, posinf=0.0, neginf=0.0), 0).sum(0)
        on = p > 1e-3 * p.max()
        if on.any():
            return int(np.flatnonzero(on)[0]), int(np.flatnonzero(on)[-1])
    p = medfilt(np.where(g[:, None], np.nan_to_num(f["data"][:], nan=0.0, posinf=0.0, neginf=0.0), 0).sum(0), 9)
    k = int(p.argmax())
    return k, k


def scint_bandwidth(x, m, g, lo, hi):
    """Δν_d in kHz, same definition as check_freq_origin.py (where the plan's 24-220 kHz
    measurement came from): the on-pulse spectrum divided by its 1.56 MHz block envelope,
    ACF of the relative deviation over the emitting band only, normalised at lag 1 (the
    lag-0 spike is channel noise, white noise cancels at lag >= 1). Rough by design ->
    quality flag from S/N."""
    on = np.arange(max(lo, 0), min(hi + 1, m.shape[1]))
    if len(on) < 2:
        return np.nan
    S = np.where(m[:, on], x[:, on], 0.0).sum(1) / np.maximum(m[:, on].sum(1), 1)
    nch = np.maximum(g.reshape(-1, 64).sum(1), 1)
    blk = np.repeat(np.where(g, S, 0.0).reshape(-1, 64).sum(1) / nch, 64)
    ok = g & (blk > 0.3 * blk.max())
    if ok.sum() < 2000:
        return np.nan
    rel = np.where(ok, S / np.maximum(blk, 1e-9) - 1.0, 0.0)
    w = ok.astype(np.int64)
    acf = np.array([np.sum(rel[:-l or None] * rel[l:]) / max(np.sum(w[:-l or None] * w[l:]), 1) for l in range(0, 65)])
    if acf[1] <= 0:
        return np.nan
    acf = acf / acf[1]
    half = next((l for l in range(1, 65) if acf[l] < 0.5), 64)
    return float(half * CH_KHZ)


def block_bins(x, m, g, b, off_cols, fb_std, cols_list):
    """Average every b native channels into one output channel, then normalise each output
    channel per its off-pulse mean/std. Returns (n_sets, n_freq, WIN) float32, freq_mask.
    Padding columns stay 0; blocks <25% good are 0; channels with <10 off-pulse samples
    fall back to fb_std (catalog whole-timeseries std; data is already mean-subtracted)."""
    ncol = x.shape[1]
    sm = m.reshape(-1, b, ncol)
    vb = np.where(m, x, 0.0).reshape(-1, b, ncol).sum(1) / np.maximum(sm.sum(1), 1)
    valid = sm.any(1)
    vo = vb[:, off_cols]
    vvo = valid[:, off_cols]
    cnt = np.maximum(vvo.sum(1), 1)
    omean = np.where(vvo, vo, 0.0).sum(1) / cnt
    ostd = np.sqrt(np.clip((np.where(vvo, vo, 0.0) ** 2).sum(1) / cnt - omean**2, 1e-12, None))
    fb_mean, fb_s = 0.0, fb_std.reshape(-1, b).mean(1)
    enough = (cnt >= 10) & (ostd > 0)
    omean = np.where(enough, omean, fb_mean)
    ostd = np.where(enough, ostd, np.where(fb_s > 0, fb_s, 1.0))
    out = np.zeros((len(cols_list), vb.shape[0], WIN), np.float64)
    for i, cols in enumerate(cols_list):
        sel = (cols >= 0) & (cols < ncol)
        v = np.zeros((vb.shape[0], WIN))
        v[:, sel] = vb[:, cols[sel]]
        out[i][:, sel] = (v[:, sel] - omean[:, None]) / ostd[:, None]
    mask = g.reshape(-1, b).mean(1)
    out[:, mask < 0.25] = 0.0
    return out.astype(np.float32), mask.astype(np.float32), omean.astype(np.float32), ostd.astype(np.float32)


xs, fmasks, tmasks, noise, noise_src, meta_rows = {256: [], 1024: []}, {256: [], 1024: []}, [], {256: [], 1024: []}, [], []
nrm = {256: [], 1024: []}  # per-channel off-pulse mean/std used for normalisation (Phase 2 needs these)

for i, tns in enumerate(names):
    rows = comps[tns]
    with h5py.File(d / "dynamic_spectra" / f"{tns}_stokesi_dynamic_spectrum.h5") as f:
        x = f["data"][:]
        g = f["good_freq"][:].astype(bool)
        m = g[:, None] & f["flag"][:]
        t = f["index_map/times"][:]
        dt = float(np.median(np.diff(t)))
        ncol = x.shape[1]
        lo, hi = extent_of(f, g)
        e = hi - lo + 1
        mid = (lo + hi + 1) // 2
        start = mid - WIN // 2
        ar = np.arange(ncol)
        off_cols = ar[(ar < lo - OFF_PAD) | (ar > hi + OFF_PAD)]
        # fallback normalisation: catalog whole-timeseries stats; data units are (raw-mean)/mean
        if "statistics/mean" in f:
            mu = f["statistics/mean"][:]
            fb_std = np.where(mu > 0, np.sqrt(np.clip(f["statistics/central_moment_2"][:], 1e-30, None)) / np.maximum(mu, 1e-30), 1.0)
        else:
            fb_std = np.ones(16384)
        # noise chunks: whole 160-sample stretches clear of the burst band (extent +- 3*extent
        # - OFF_PAD, which is >= 3 widths from any component), fully off-pulse, >=50% valid;
        # fine-dt files only (coarse dt would put chunks on a different time grid than the input)
        colsets = [np.arange(start, start + WIN)]
        if dt < 1.5 * DT_FINE:
            ban_lo, ban_hi = lo - 3 * e - OFF_PAD, hi + 3 * e + OFF_PAD
            for st in range(0, ncol - WIN + 1, WIN):
                if (st + WIN <= ban_lo or st >= ban_hi) and m[:, st:st + WIN].mean() >= 0.5:
                    colsets.append(np.arange(st, st + WIN))
        bp = json.loads(f.attrs["burst_parameters_json"]) if "burst_parameters_json" in f.attrs else {}
        jy = float(np.median(f["calibration/flux_conversion_factor"][:][g])) if "calibration/flux_conversion_factor" in f else np.nan
        dm = float(f.attrs["dm_incoherent"])
    meta = dict(
        tns=tns, source=rows[0]["repeater_name"], mjd=num(rows[0]["mjd_400"]), dt_ms=dt * 1e3, ncol=ncol,
        start=int(start), centre=mid - start, ext_lo=lo - start, ext_hi=hi - start, dm=dm, jy=jy,
        snr=(lambda v: max(v) if v else np.nan)([s for s in (num(r["snr_fitb"]) for r in rows) if not np.isnan(s)]),
        dnu=scint_bandwidth(x, m, g, lo, hi),
        excluded=int(rows[0]["excluded_flag"]), sidelobe=int(rows[0]["sidelobe_flag"]),
        citizen=int(rows[0]["citizen_science_flag"]),
        coarse=int(dt > 1.5 * DT_FINE), clipped=int(e > WIN),
        rel_arrival=np.array(bp.get("arrival_time", []), float),
    )
    if len(meta["rel_arrival"]) and dt:
        meta["rel_arrival"] = (meta["rel_arrival"] - t[0]) / dt - start  # window-relative columns
    meta_rows.append(meta)
    tmasks.append(((np.arange(start, start + WIN) >= 0) & (np.arange(start, start + WIN) < ncol)).astype(np.uint8))
    for res in (1024, 256):
        v, fm, omean, ostd = block_bins(x, m, g, 16384 // res, off_cols, fb_std, colsets)
        xs[res].append(v[0])
        fmasks[res].append(fm)
        nrm[res].append(np.stack([omean, ostd]))
        for j in range(1, len(colsets)):
            noise[res].append(v[j])
            if res == 256:  # one source index per chunk, not one per (chunk, resolution)
                noise_src.append(i)
    if (i + 1) % 100 == 0:
        print(f"  {i + 1}/{len(names)}", flush=True)

X = {k: np.stack(v) for k, v in xs.items()}
FM = {k: np.stack(v) for k, v in fmasks.items()}
TM = np.stack(tmasks)
NB = {k: np.stack(v) if len(v) else np.zeros((0, k, WIN), np.float32) for k, v in noise.items()}
NS = np.array(noise_src, dtype=np.int32)
assert len(NS) == len(noise[256]) == len(noise[1024]), (len(NS), len(noise[256]), len(noise[1024]))
print(f"bursts {len(names)} | noise chunks {len(NS)} | coarse_dt {sum(o['coarse'] for o in meta_rows)} | clipped {sum(o['clipped'] for o in meta_rows)}")

# ---- asserts (plan step 9) ----
dnu = np.array([o["dnu"] for o in meta_rows])
assert np.all(np.isnan(dnu) | ((dnu >= CH_KHZ) & (dnu <= 64 * CH_KHZ))), f"bad dnu: {dnu[~np.isnan(dnu) & ((dnu < CH_KHZ) | (dnu > 64 * CH_KHZ))]}"
print(f"dnu_d kHz: median {np.nanmedian(dnu):.0f}, measured on {np.isfinite(dnu).sum()}/{len(dnu)} bursts")
for res in (256, 1024):
    assert X[res].shape == (len(names), res, WIN), X[res].shape
    assert np.isfinite(X[res]).all() and np.isfinite(FM[res]).all() and np.isfinite(NB[res]).all()
for o in meta_rows:
    assert 0 <= o["centre"] <= WIN - 1
    if not o["clipped"]:
        assert 0 <= o["ext_lo"] <= o["ext_hi"] <= WIN - 1, o["tns"]
        if len(o["rel_arrival"]):
            assert np.all((o["rel_arrival"] > -1.5) & (o["rel_arrival"] < WIN - 0.5)), f"components outside window: {o['tns']}"
# binning conserves the mean: each X256 channel == mean of its four X1024 channels
# binning conserves the mean: undo the per-channel normalisation (raw = X*std + mean, stored in
# norm/*) and require mean-of-four-1024-raws ≈ 256-raw within the per-channel noise scale
NR = {k: np.stack(v) for k, v in nrm.items()}
raw = {k: X[k] * NR[k][:, 1, :, None] + NR[k][:, 0, :, None] for k in (256, 1024)}
ok = (FM[256] >= 0.25) & np.all(FM[1024].reshape(len(names), 256, 4) >= 0.25, axis=2)
dev = np.abs(raw[1024].reshape(len(names), 256, 4, WIN).mean(2) - raw[256])
# heavily masked columns legitimately differ a little (mean of four sub-block means vs pooled
# mean with unequal valid counts), so tolerate sparse 8-sigma outliers but demand that an
# ordering bug — which would deviate at every peak column — cannot pass:
bad = (dev > 8 * NR[256][:, 1, :, None]) & ok[..., None]
frac = bad.sum() / max(ok.sum() * WIN, 1)
assert frac < 1e-4, f"{bad.sum()} cells fail binning conservation ({frac:.2%}), worst {dev[bad].max():.2e}"
print(f"asserts pass; binning conserved: {bad.sum()} cells > 8 sigma ({frac:.2e} of {ok.sum() * WIN})")

if LIMIT:
    print("--limit: skipping save/gallery")
    sys.exit(0)

# ---- save ----
pre = d / "preproc"
pre.mkdir(exist_ok=True)
scols = {
    "tns": np.array([o["tns"] for o in meta_rows], dtype="S32"),
    "source": np.array([o["source"] for o in meta_rows], dtype="S32"),
    "mjd_400": [o["mjd"] for o in meta_rows], "dt_ms": [o["dt_ms"] for o in meta_rows],
    "centre": [o["centre"] for o in meta_rows], "extent_lo": [o["ext_lo"] for o in meta_rows],
    "extent_hi": [o["ext_hi"] for o in meta_rows], "dm_used": [o["dm"] for o in meta_rows],
    "jy_per_unit": [o["jy"] for o in meta_rows], "dnu_d_khz": [o["dnu"] for o in meta_rows],
    "dnu_good": [int(o["snr"] >= 100 and np.isfinite(o["dnu"])) for o in meta_rows],
    "snr_fitb": [o["snr"] if np.isfinite(o["snr"]) else -9999 for o in meta_rows],
    "excluded_flag": [o["excluded"] for o in meta_rows], "sidelobe_flag": [o["sidelobe"] for o in meta_rows],
    "citizen_science_flag": [o["citizen"] for o in meta_rows], "coarse_dt": [o["coarse"] for o in meta_rows],
    "clipped": [o["clipped"] for o in meta_rows],
}
for res in (256, 1024):
    p = pre / f"repeaters_{res}x{WIN}.h5"
    with h5py.File(p, "w") as f:
        f["X"] = X[res]
        f["freq_mask"] = FM[res]
        f["time_mask"] = TM
        f["norm/mean"] = NR[res][:, 0]
        f["norm/std"] = NR[res][:, 1]
        f["noise_bank/X"] = NB[res]
        f["noise_bank/file_idx"] = NS
        for k, v in scols.items():
            f["meta/" + k] = np.asarray(v)
    print("wrote", p, f"{p.stat().st_size / 1e6:.0f} MB")

# ---- gallery (plan step 7): long-window, width-nan, coarse, clipped, + 30 random ----
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import random
gal = HERE / "outputs" / "preproc_gallery"
gal.mkdir(parents=True, exist_ok=True)
sel = {i for i, o in enumerate(meta_rows) if o["ncol"] > WIN + 2 or o["coarse"] or o["clipped"]}
sel |= {i for i, o in enumerate(meta_rows) if all(str(num(r["width_fitb"])) in ("nan", "None") for r in comps[o["tns"]])}
sel |= set(random.Random(42).sample(sorted(set(range(len(names))) - sel), 30))
for i in sorted(sel):
    o = meta_rows[i]
    with h5py.File(d / "dynamic_spectra" / f"{o['tns']}_stokesi_dynamic_spectrum.h5") as f:
        gg = f["good_freq"][:].astype(bool)
        mm = gg[:, None] & f["flag"][:]
        band = np.where(mm, f["data"][:], 0).sum(0) / np.maximum(mm.sum(0), 1)
    fig, ax = plt.subplots(2, 1, figsize=(8, 5))
    ax[0].plot(band, lw=0.8)
    ax[0].axvspan(o["start"] + o["ext_lo"], o["start"] + o["ext_hi"], alpha=0.2, color="r")
    ax[0].axvline(o["start"], color="g"); ax[0].axvline(o["start"] + WIN, color="g")
    ax[0].set_title(f"{o['tns']} native dt={o['dt_ms']:.3f} ms, n={o['ncol']}; red=extent, green=crop")
    ax[1].plot(X[256][i].mean(0), lw=0.8)
    ax[1].set_title("after crop+normalise: band-mean of X256")
    fig.tight_layout()
    fig.savefig(gal / f"{i:03d}_{o['tns']}.png")
    plt.close(fig)
print(f"gallery: {len(sel)} PNGs in {gal}")
