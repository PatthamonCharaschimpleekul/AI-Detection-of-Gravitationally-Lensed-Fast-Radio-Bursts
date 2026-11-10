"""G4: can pairs be told apart by injection artefacts alone, with no burst physics?

Compares real same-source repeat pairs against simulated "lensed" pairs built two ways:
  naive     B = mu * (whole waterfall of A, noise included) + other burst's off-pulse noise
  reinject  B = mu * (fitburst model of A, no noise) + other burst's off-pulse noise

Two statistics use no signal: off-pulse noise correlation and the RFI-mask overlap.
A third asks whether the re-injection fix creates its own shortcut: a real burst keeps
structure the fitburst model misses, while a re-injected one has only noise left on-pulse.
AUC is the chance that a simulated pair scores above a real pair; 0.5 means no shortcut.

Usage: python -I shortcut_check.py <waterfall dir> [out.json]
"""
import glob
import itertools
import json
import os
import sys

import h5py
import numpy as np

SEED = 20261106
MUS = (0.3, 0.5, 1.0)


def load(path):
    with h5py.File(path, "r") as f:
        g = f["frb"]
        wf = g["wfall"][:].astype(np.float64)
        model = g["model_wfall"][:].astype(np.float64)
        name = g.attrs["tns_name"]
    name = name.decode() if isinstance(name, bytes) else str(name)
    mask = np.isnan(wf).all(axis=1)
    ts = np.nansum(wf, axis=0)
    peak = int(np.argmax(ts))
    prof = np.nansum(model, axis=0)
    on = prof > 0.01 * prof.max() if prof.max() > 0 else np.zeros(wf.shape[1], bool)
    on[max(0, peak - 2):peak + 3] = True
    off = ~on
    if off.sum() < 4:
        return None
    # Whiten each channel with its off-pulse statistics.
    mu = np.nanmean(wf[:, off], axis=1, keepdims=True)
    sd = np.nanstd(wf[:, off], axis=1, keepdims=True)
    sd[~(sd > 0)] = np.nan
    white, tmpl = (wf - mu) / sd, model / sd
    good = np.isfinite(white).all(axis=1)
    off_band = white[good][:, off].mean(axis=0)
    res_band = (white[good][:, on] - tmpl[good][:, on]).mean(axis=0)
    off_ms = float((off_band ** 2).mean())
    return {"name": name, "wf": white, "model": tmpl, "off": np.where(off)[0], "mask": mask,
            "on_n": int(on.sum()), "off_band": off_band, "off_ms": off_ms,
            "res_excess": float((res_band ** 2).mean() / off_ms)}


def off_noise(b, n, rng):
    """Draw n off-pulse time samples of burst b, as (channels, n)."""
    return b["wf"][:, rng.choice(b["off"], n, replace=True)]


def noise_corr(a_off, b_off):
    """Pearson correlation over matching off-pulse pixels flagged in neither burst."""
    n = min(a_off.shape[1], b_off.shape[1])
    u, v = a_off[:, :n].ravel(), b_off[:, :n].ravel()
    ok = np.isfinite(u) & np.isfinite(v)
    return float(np.corrcoef(u[ok], v[ok])[0, 1]), int(ok.sum())


def jaccard(m1, m2):
    return float((m1 & m2).sum() / (m1 | m2).sum())


def auc(sim, real):
    sim, real = np.asarray(sim), np.asarray(real)
    return float(((sim[:, None] > real[None]).mean() + 0.5 * (sim[:, None] == real[None]).mean()))


def main():
    wdir = sys.argv[1]
    bursts = [b for b in (load(p) for p in sorted(glob.glob(os.path.join(wdir, "*_waterfall.h5")))) if b]
    rep_map = json.load(open(os.path.join(wdir, "_sources.json")))
    by_src = {}
    for b in bursts:
        by_src.setdefault(rep_map[b["name"]], []).append(b)
    print({k: len(v) for k, v in by_src.items()}, flush=True)
    rng = np.random.default_rng(SEED)
    real_c, real_j = [], []
    sims = {m: {"c": [], "j": []} for m in ("naive", "reinject")}
    for src, group in by_src.items():
        for a, b in itertools.combinations(group, 2):
            real_c.append(abs(noise_corr(a["wf"][:, a["off"]], b["wf"][:, b["off"]])[0]))
            real_j.append(jaccard(a["mask"], b["mask"]))
            for mu in MUS:
                # Noise and mask for B come from b, a burst from another day.
                n = len(a["off"])
                nb = off_noise(b, n, rng)
                a_off = a["wf"][:, a["off"]]
                naive = mu * a_off + nb
                sims["naive"]["c"].append(abs(noise_corr(a_off, naive)[0]))
                # The template has no noise, so B's off-pulse is only b's noise.
                template = np.nan_to_num(a["model"])[:, a["off"]]
                reinj = mu * template + nb
                sims["reinject"]["c"].append(abs(noise_corr(a_off, reinj)[0]))
                # A naive copy keeps A's RFI mask in B, on top of b's.
                sims["naive"]["j"].append(jaccard(a["mask"], a["mask"] | b["mask"]))
                # Re-injection with a fresh mask from b matches real pairs by construction.
                sims["reinject"]["j"].append(jaccard(a["mask"], b["mask"]))
    # On-pulse residual power over off-pulse power, band-averaged. Re-injected bursts have
    # only noise on-pulse, so draw that from the off-pulse samples of another burst.
    real_res = [b["res_excess"] for b in bursts]
    reinj_res = []
    for b in bursts:
        for other in bursts:
            if other is not b:
                draw = rng.choice(other["off_band"], b["on_n"], replace=True)
                reinj_res.append(float((draw ** 2).mean() / other["off_ms"]))
    res = {
        "n_bursts": len(bursts),
        "on_pulse_residual": {
            "real_median": float(np.median(real_res)), "real_p90": float(np.percentile(real_res, 90)),
            "reinject_median": float(np.median(reinj_res)), "reinject_p90": float(np.percentile(reinj_res, 90)),
            "auc_real_above_reinject": auc(real_res, reinj_res),
        }, "n_real_pairs": len(real_c),
        "real_noise_corr_median": float(np.median(real_c)), "real_noise_corr_max": float(np.max(real_c)),
        "real_mask_jaccard_median": float(np.median(real_j)),
    }
    for m, v in sims.items():
        res[m] = {
            "noise_corr_median": float(np.median(v["c"])), "noise_corr_min": float(np.min(v["c"])),
            "auc_noise_corr": auc(v["c"], real_c),
            "mask_jaccard_median": float(np.median(v["j"])), "auc_mask_jaccard": auc(v["j"], real_j),
        }
    print(json.dumps(res, indent=1))
    if len(sys.argv) > 2:
        json.dump(res, open(sys.argv[2], "w"), indent=1)


main()
