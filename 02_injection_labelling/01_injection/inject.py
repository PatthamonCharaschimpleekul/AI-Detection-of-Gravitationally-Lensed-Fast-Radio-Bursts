"""Track B pair injection: lensed copy / intrinsic repeat / unrelated pairs at 256 x 160.

Plan: plan/2026-11-05_1254_pair-injection.md
Usage: python -I inject.py            # build cache if missing, write frozen manifests, audit, gallery
       python -I inject.py --sets-only  # manifests only: skips the audit, which reads real same-source pairs
       python -I inject.py --rebuild  # rebuild the template/background cache from the raw files
Library (training): from inject import load_pools, make_pair, load_set

Rule: every member of every class = noise-free fitburst template (binned over ALL native
channels) x per-member nuisances + an independent real off-pulse background from another
file, whose channel mask and per-channel sigma the member inherits. All classes draw from
the same source pool (>= 2 eligible templates) with uniform source sampling, and both
members have injected S/N >= 10.
"""
import csv, hashlib, json, sys
from pathlib import Path

import h5py
import numpy as np

HERE = Path(__file__).resolve().parent
REAL = HERE.parents[1] / "01_semi_synthetic_data" / "01_real_data" / "data" / "catalog2"
CACHE = HERE / "data" / "inject_cache_256.h5"
MAN = HERE / "manifests"
OUT = HERE / "outputs"
WIN, NF, DT_MS, OFF_PAD = 160, 256, 0.98304, 20
SNR_MIN, R_MIN, OFF_MIN, DNU_DEFAULT, MODEL_SNR_MIN = 10.0, 0.05, 60, 49.0, 5.0
KDM = 4.148808e6  # dispersion constant, ms MHz^2 / (pc cm^-3)
BIG = ("FRB20220912A", "FRB20180916B")  # forced into train so they cannot dominate val/test
KINDS = ("lensed", "repeat", "unrelated", "impostor")
VERSION = "v1.3"  # v0 (496c048) catalog snr_fitb; v1 measured model S/N; v1.1 = v1 + 1000 impostor pairs; v1.2 adds bright sets;
# v1.3 drops near-empty backgrounds and stops dividing by a near-zero off-pulse sigma
BRIGHT = 25.0  # headline bin floor on pair min S/N (plan 2026-11-06_1223)
# name: (split, n_pairs, seed, wide nuisances, S/N floor); bright sets cycle all four kinds
SETS = {"val": ("val", 4000, 101, False, SNR_MIN), "test": ("test", 4000, 102, False, SNR_MIN),
        "stress": ("test", 4000, 103, True, SNR_MIN),
        "val_bright": ("val", 8000, 201, False, BRIGHT), "test_bright": ("test", 16000, 202, False, BRIGHT)}
FOLD_SEED, N_FOLDS = 2027, 5  # grouped folds, plan 2026-11-08_0845 (F1)
FOLD_SETS = {"dev": 411, "all": 401}  # fold-set seed = base + k; 8000 pairs each, floor BRIGHT, four kinds cycled (F3, F9)
FOLD_N = 8000
LEGACY = 3000  # pairs 0..2999 cycle lensed/repeat/unrelated; 3000.. are impostors
# I1 shared spectral envelope: a host plasma lens imposes one band shape on every burst while a caustic lasts
# (hours-days; Cordes et al. 2017, ApJ 842, 35). Implemented as envelope transfer: member B keeps its own
# time-frequency structure but takes member A's 25 MHz-smoothed spectral envelope, so each member's marginal
# stays a real burst spectrum (a parametric Gaussian gain made members narrower than real bursts: audit (a)).
I1_SMOOTH, I1_RMAX = 16, 10.0  # envelope smoothing (channels) and cap on the per-channel transfer ratio
PAR_NAMES = ("n_comp", "width_max_ms", "scat_ms", "dm_fitb", "spec_index0", "spec_running0")


def num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return np.nan


def extent_of(f, g):
    """Copied from 01_real_data/preprocess_catalog2.py so the template crop is identical."""
    from scipy.signal import medfilt
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


def build_cache():
    """Templates (binned fitburst models) and mirror-tiled off-pulse backgrounds -> CACHE."""
    with h5py.File(REAL / "preproc" / "repeaters_256x160.h5") as f:
        X, FM, TM, NS = f["X"][:], f["freq_mask"][:], f["time_mask"][:], f["norm/std"][:]
        meta = {k: f["meta/" + k][:] for k in f["meta"]}
    tns = meta["tns"].astype(str)
    dmerr = {}
    for r in csv.DictReader(open(REAL / "chimefrbcat2.csv", newline="")):
        v = num(r["dm_fitb_err"])
        if np.isfinite(v) and v > 0 and r["tns_name"] not in dmerr:
            dmerr[r["tns_name"]] = v
    n = len(tns)
    T = np.zeros((n, NF, WIN), np.float32)
    has_model = np.zeros(n, bool)
    par = np.full((n, len(PAR_NAMES)), np.nan)
    freq = None
    for i, t in enumerate(tns):
        if meta["coarse_dt"][i]:
            continue  # coarse files sit on another time grid; never templates or backgrounds
        with h5py.File(REAL / "dynamic_spectra" / f"{t}_stokesi_dynamic_spectrum.h5") as f:
            fr = f["index_map/freqs"][:].reshape(NF, -1).mean(1)
            assert freq is None or np.allclose(fr, freq)
            freq = fr
            if "burst_parameters_json" in f.attrs:
                bp = json.loads(f.attrs["burst_parameters_json"])
                par[i] = [len(bp["arrival_time"]), 1e3 * np.nanmax(bp["burst_width"]),
                          1e3 * bp["scattering_timescale"][0], bp["dm"][0],
                          bp["spectral_index"][0], bp["spectral_running"][0]]
            if "model" not in f:
                continue
            g = f["good_freq"][:].astype(bool)
            lo, hi = extent_of(f, g)
            start = (lo + hi + 1) // 2 - WIN // 2
            assert lo - start == meta["extent_lo"][i], (t, lo - start, meta["extent_lo"][i])
            m = np.nan_to_num(f["model"][:], nan=0.0, posinf=0.0, neginf=0.0)
        mb = m.reshape(NF, -1, m.shape[1]).mean(1)  # all channels: the template's own mask must not leak
        cols = np.arange(start, start + WIN)
        ok = (cols >= 0) & (cols < mb.shape[1])
        T[i][:, ok] = mb[:, cols[ok]]
        has_model[i] = np.abs(T[i]).sum() > 0
        if (i + 1) % 100 == 0:
            print(f"  cache {i + 1}/{n}", flush=True)

    # model-vs-data check in each file's own sigma units: s = matched-filter S/N of the model in
    # the data, b = best-fit scale (b ~ 1 means model and data share units)
    good = (FM >= 0.25)[:, :, None] & (TM[:, None, :] > 0)
    Ts = np.where(good, T / np.maximum(NS, 1e-12)[:, :, None], 0.0)
    tt = (Ts ** 2).sum((1, 2))
    xt = (np.where(good, X, 0.0) * Ts).sum((1, 2))
    model_snr = np.where(tt > 0, xt / np.sqrt(np.maximum(tt, 1e-30)), np.nan)
    model_b = np.where(tt > 0, xt / np.maximum(tt, 1e-30), np.nan)

    snr = meta["snr_fitb"].astype(float)
    eligible = (has_model & (meta["coarse_dt"] == 0) & (meta["clipped"] == 0) & (meta["sidelobe_flag"] == 0)
                & (model_snr >= MODEL_SNR_MIN) & (snr > 0) & np.array([t in dmerr for t in tns]))

    # backgrounds: off-pulse columns (real samples, outside extent +- OFF_PAD), left+right
    # segments joined, mirror-tiled to WIN. Inherit the file's freq_mask and norm/std.
    bg_X, bg_idx = [], []
    for i in range(n):
        if meta["coarse_dt"][i]:
            continue
        c = np.arange(WIN)
        off = c[(TM[i] > 0) & ((c < meta["extent_lo"][i] - OFF_PAD) | (c > meta["extent_hi"][i] + OFF_PAD))]
        if len(off) < OFF_MIN:
            continue
        seq = np.concatenate([off, off[::-1]])
        seq = np.tile(seq, WIN // len(seq) + 1)[:WIN]
        bg_X.append(X[i][:, seq])
        bg_idx.append(i)
    bg_idx = np.array(bg_idx)

    src = meta["source"].astype(str)
    dnu_src = {}
    for s in np.unique(src):
        v = meta["dnu_d_khz"][(src == s) & (meta["dnu_good"] == 1)]
        dnu_src[s] = float(np.median(v)) if len(v) else DNU_DEFAULT
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(CACHE, "w") as f:
        f["T"] = T
        f["eligible"] = eligible
        f["model_snr"] = model_snr
        f["model_b"] = model_b
        f["par"] = par
        f["dm_err"] = np.array([dmerr.get(t, np.nan) for t in tns])
        f["dnu_khz"] = np.array([dnu_src[s] for s in src])
        f["freq_mhz"] = freq
        f["bg/X"] = np.stack(bg_X)
        f["bg/file_idx"] = bg_idx
        f["fm"] = FM
        f["sigma"] = NS
        for k in ("tns", "source", "snr_fitb", "mjd_400", "coarse_dt", "extent_lo", "extent_hi"):
            f["meta/" + k] = meta[k]
    print(f"cache: {eligible.sum()} eligible templates (has model {has_model.sum()}, model S/N<{MODEL_SNR_MIN:g}: "
          f"{(has_model & (model_snr < MODEL_SNR_MIN)).sum()}), {len(bg_idx)} backgrounds; "
          f"model scale b median {np.nanmedian(model_b[eligible]):.3f}")


class Pools:
    """Everything make_pair needs for one split, or for an explicit set of source names (grouped folds)."""

    def __init__(self, c, split):
        self.c, self.split = c, split
        inn = c["file_split"] == split if isinstance(split, str) else np.isin(c["source"], sorted(split))
        self.tmpl = {}
        for s in np.unique(c["source"][inn & c["eligible"]]):
            t = np.flatnonzero((c["source"] == s) & c["eligible"])
            if len(t) >= 2:  # decision 5: one pool for every class
                self.tmpl[s] = t
        self.sources = np.array(sorted(self.tmpl))
        self.bgs = np.flatnonzero(inn[c["bg_file"]] & c["bg_ok"])  # rows of bg/X
        # v1: matched-filter S/N of the model in the real data (catalog snr_fitb is ~3.7% lower,
        # which made v0 members systematically fainter than the bursts they stand for)
        snr = c["model_snr"][np.isfinite(c["model_snr"])]
        self.snr_pool = snr[snr >= SNR_MIN]  # catalog-wide S/N distribution, same for all splits


def split_sources(source, seed=7):
    """Sources -> train/val/test, 60/20/20 by burst count; BIG forced into train."""
    names, counts = np.unique(source, return_counts=True)
    rng = np.random.default_rng(seed)
    order = [k for k in rng.permutation(len(names)) if names[k] not in BIG]
    target = {"train": 0.6, "val": 0.2, "test": 0.2}
    got = {"train": 0, "val": 0, "test": 0}
    out = {n: "train" for n in BIG}
    for k in order:
        tot = sum(got.values()) + counts[k]
        sp = max(target, key=lambda s: target[s] * tot - got[s])
        out[names[k]] = sp
        got[sp] += counts[k]
    return out


def load_pools():
    c = {}
    with h5py.File(CACHE) as f:
        for k in ("T", "eligible", "model_snr", "par", "dm_err", "dnu_khz", "freq_mhz", "fm", "sigma"):
            c[k] = f[k][:]
        c["bg_X"], c["bg_file"] = f["bg/X"][:], f["bg/file_idx"][:]
        for k in f["meta"]:
            c[k] = f["meta/" + k][:]
    c["source"] = c["source"].astype(str)
    c["tns"] = c["tns"].astype(str)
    sp = split_sources(c["source"])
    c["file_split"] = np.array([sp[s] for s in c["source"]])
    # two files have almost no valid off-pulse data, so their "noise" is zeros
    c["bg_ok"] = np.array([np.median(x[c["fm"][f] >= 0.25].std(1)) > 0.5 for x, f in zip(c["bg_X"], c["bg_file"])])
    return {s: Pools(c, s) for s in ("train", "val", "test")}


def assign_folds(sources, seed=FOLD_SEED, k=N_FOLDS):
    """F1: BIG in folds 0 and 1, the other sources permuted and dealt round-robin starting at fold 2."""
    out = {b: i for i, b in enumerate(BIG) if b in sources}
    rest = sorted(s for s in sources if s not in BIG)
    for j, s in enumerate(np.random.default_rng(seed).permutation(rest)):
        out[str(s)] = (len(BIG) + j) % k
    return out


def fold_sources(pools, scheme):
    """Pool sources a fold scheme covers: 'dev' = train + val only (rehearsal, F9), 'all' = every pool source."""
    return [str(s) for sp in (("train", "val") if scheme == "dev" else ("train", "val", "test")) for s in pools[sp].sources]


def fold_pools(pools, scheme, k):
    """(training pool, held-out pool) for fold k: templates and backgrounds never cross the fold boundary (F2)."""
    f = assign_folds(fold_sources(pools, scheme))
    c = pools["train"].c
    return Pools(c, {s for s, j in f.items() if j != k}), Pools(c, {s for s, j in f.items() if j == k})


def fold_set(pools, scheme, k):
    _, H = fold_pools(pools, scheme, k)
    return gen_set(H, FOLD_N, FOLD_SETS[scheme] + k, False, True, BRIGHT)


def load_fold_set(scheme, k, pools=None):
    """Regenerate fold set k and check it against folds_v1.json. Returns arrays, labels and source of each pair."""
    pools = pools or load_pools()
    man = json.loads((MAN / "folds_v1.json").read_text())
    assert man["assign"][scheme] == assign_folds(fold_sources(pools, scheme)), "fold assignment changed"
    h, XA, XB, Y, S = hashlib.sha256(), [], [], [], []
    for i, xa, xb, ma, mb, y, info in fold_set(pools, scheme, k):
        h.update(xa.tobytes()); h.update(xb.tobytes())
        XA.append(xa); XB.append(xb); Y.append(y); S.append(info["src_a"])
    assert h.hexdigest() == man["sha256"][f"{scheme}_f{k}"], f"{scheme} fold {k}: regenerated set differs from folds_v1.json"
    return np.stack(XA), np.stack(XB), np.array(Y), np.array(S)


def freeze_folds(pools):
    """Write folds_v1.json (assignments + set hashes) and one manifest csv per fold set. Builds pairs, scores nothing (F8)."""
    man = dict(seed=FOLD_SEED, n_folds=N_FOLDS, n_pairs=FOLD_N, set_seeds=FOLD_SETS, version=VERSION, assign={}, sha256={}, counts={})
    c = pools["train"].c
    for scheme in FOLD_SETS:
        f = assign_folds(fold_sources(pools, scheme))
        man["assign"][scheme] = f
        for k in range(N_FOLDS):
            T, H = fold_pools(pools, scheme, k)
            assert not set(T.sources) & set(H.sources) and len(T.sources) + len(H.sources) == len(f)
            assert not set(c["source"][c["bg_file"][T.bgs]]) & set(H.sources)  # no background crosses the boundary
            assert not set(c["source"][c["bg_file"][H.bgs]]) & set(T.sources)
            h, rows = hashlib.sha256(), []
            for i, xa, xb, ma, mb, y, info in fold_set(pools, scheme, k):
                assert info["src_a"] in H.tmpl and info["src_b"] in H.tmpl and min(info["snr_a"], info["snr_b"]) >= BRIGHT - 1e-9
                h.update(xa.tobytes()); h.update(xb.tobytes())
                rows.append(dict(i=i, label=y, **info))
            name = f"{scheme}_f{k}"
            man["sha256"][name] = h.hexdigest()
            man["counts"][name] = dict(held_sources=len(H.sources), held_templates=int(sum(map(len, H.tmpl.values()))),
                                       train_sources=len(T.sources), train_templates=int(sum(map(len, T.tmpl.values()))),
                                       held_bgs=len(H.bgs), train_bgs=len(T.bgs))
            with open(MAN / f"{name}_bright.csv", "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
            print(name, man["counts"][name], h.hexdigest()[:12], flush=True)
    (MAN / "folds_v1.json").write_text(json.dumps(man, indent=1))


def fshift(a, d):
    """Shift each row of a (nf, WIN) right by d samples (scalar or per-row), zero-padded, no wrap."""
    n = 2 * WIN
    F = np.fft.rfft(a, n, axis=1)
    k = np.fft.rfftfreq(n)
    F *= np.exp(-2j * np.pi * k[None, :] * np.atleast_1d(d)[:, None])
    return np.fft.irfft(F, n, axis=1)[:, :WIN]


def member(c, ti, bi, snr, rng, tau600, wide, off=(), gain_shared=None, scint_shared=None):
    """One pair member: template ti on background row bi at injected matched-filter S/N snr.
    off: nuisances to switch off ("shift", "dm", "scint") for the twin ladder; draws still happen
    so the remaining nuisances get identical values. gain_shared / scint_shared: impostor imprints
    shared by both members (I1 plasma-lens gain, I2 scintillation pattern) instead of independent ones."""
    f = c["freq_mhz"]
    fi = c["bg_file"][bi]
    mask = c["fm"][fi] >= 0.25
    sig = c["sigma"][fi]
    med = np.median(sig[mask])
    sig = np.clip(sig, med / 3, med * 3)  # nearly-masked channels must not blow up the template
    S = c["T"][ti] / sig[:, None]  # physical template in the BACKGROUND file's sigma units
    shift = rng.uniform(-1, 1) * (20 if wide else 10)
    sdm = c["dm_err"][ti] * c["model_snr"][ti] / snr * (3 if wide else 1)
    ddm = rng.normal(0, sdm)
    shift, ddm = (0.0 if "shift" in off else shift), (0.0 if "dm" in off else ddm)
    S = fshift(S, shift + KDM * ddm * (f ** -2.0 - 600.0 ** -2.0) / DT_MS)
    if tau600 > 0:
        t = np.arange(WIN) * DT_MS
        tau = tau600 * (f / 600.0) ** -4.0
        ker = np.exp(-t[None, :] / tau[:, None])
        ker /= ker.sum(1, keepdims=True)
        S = np.fft.irfft(np.fft.rfft(S, 2 * WIN, axis=1) * np.fft.rfft(ker, 2 * WIN, axis=1), 2 * WIN, axis=1)[:, :WIN]
    nsc = max(1.0, 1562.5 / c["dnu_khz"][ti])
    gain = rng.gamma(nsc, 1.0 / nsc, NF)  # fresh scintillation pattern, the source's bandwidth
    if scint_shared is not None:
        gain = scint_shared.copy()
    if "scint" in off:
        gain = np.ones(NF)
    # bands that do not overlap leave nothing to transfer: the pair then stays a plain repeat
    if gain_shared is not None and ((S * gain_shared[:, None])[mask] ** 2).sum() > 0:
        gain = gain * gain_shared
    if wide:  # stress only: smooth beam/bandpass multiplier
        x = (f - f[0]) / (f[-1] - f[0])
        gain *= np.clip(1 + 0.3 * sum(rng.normal() * np.cos(2 * np.pi * k * x + rng.uniform(0, 2 * np.pi))
                                      for k in (1, 2, 3)) / np.sqrt(3), 0.05, None)
    S *= gain[:, None]
    S[~mask] = 0.0
    a = snr / np.sqrt((S ** 2).sum())
    assert np.isfinite(a), f"empty template {ti} on background {bi}"
    out = a * S + c["bg_X"][bi]
    # re-normalise per channel exactly like preprocessing: off-pulse = outside the injected extent +- OFF_PAD
    prof = S.sum(0)
    on = np.flatnonzero(np.abs(prof) > 1e-3 * np.abs(prof).max())
    cols = np.arange(WIN)
    off = (cols < on[0] - OFF_PAD) | (cols > on[-1] + OFF_PAD)
    if off.sum() >= 10:
        mu, sd = out[:, off].mean(1), out[:, off].std(1)
        out = np.where(mask[:, None], (out - mu[:, None]) / np.where(sd > 0.2, sd, 1.0)[:, None], 0.0)  # off-pulse is unit-variance: sd << 1 means flagged zeros
    out[~mask] = 0.0
    assert np.abs(out).max() < 1e4, f"runaway pixel: template {ti}, background {bi}"
    info = dict(shift=shift, ddm=ddm, tau600=tau600, ext_lo=int(on[0]), ext_hi=int(on[-1]))
    return out.astype(np.float32), mask, info


def envelope_transfer(Ta, Tb):
    """Per-channel ratio that gives template Tb the smoothed spectral envelope of Ta (both raw units)."""
    from scipy.ndimage import uniform_filter1d
    ea = uniform_filter1d(np.clip(Ta.sum(1), 0, None), I1_SMOOTH)
    eb = uniform_filter1d(np.clip(Tb.sum(1), 0, None), I1_SMOOTH)
    ea, eb = ea / ea.max(), eb / eb.max()
    return np.clip(ea / np.maximum(eb, 1e-3), 0.0, I1_RMAX)


def make_pair(kind, rng, P, wide=False, snr_floor=SNR_MIN):
    """Returns xa, xb (NF, WIN) float32, mask_a, mask_b, label (0 lensed, 1 repeat, 2 unrelated, 3 impostor), info.
    impostor = two different templates of one source sharing I1 (plasma-lens gain), I2 (scintillation) or both."""
    c = P.c
    s = P.sources[rng.integers(len(P.sources))]
    if kind == "lensed":
        ta = tb = rng.choice(P.tmpl[s])
        s2 = s
    elif kind in ("repeat", "impostor"):
        ta, tb = rng.choice(P.tmpl[s], 2, replace=False)
        s2 = s
    else:
        others = P.sources[P.sources != s]
        s2 = others[rng.integers(len(others))]
        ta, tb = rng.choice(P.tmpl[s]), rng.choice(P.tmpl[s2])
    imp = dict(imp_type="")
    gsh = ssh = None
    if kind == "impostor":  # extra draws only in this branch, so the other kinds' streams are unchanged
        t = ("I1", "I2", "I1+I2")[int(rng.integers(3))]
        imp["imp_type"] = t
        if "I1" in t:
            gsh = envelope_transfer(c["T"][ta], c["T"][tb])  # applied to member B only
        if "I2" in t:
            nsc = max(1.0, 1562.5 / c["dnu_khz"][ta])
            ssh = rng.gamma(nsc, 1.0 / nsc, NF)
    snr_a = float(rng.choice(P.snr_pool))
    r = float(np.exp(rng.uniform(np.log(max(R_MIN, SNR_MIN / snr_a)), 0.0)))  # S/N_b >= SNR_MIN
    while r * snr_a < snr_floor or snr_a < snr_floor:  # bright sets: redraw, so (S/N_a, r) stays the truncated joint
        snr_a = float(rng.choice(P.snr_pool))
        r = float(np.exp(rng.uniform(np.log(max(R_MIN, SNR_MIN / snr_a)), 0.0)))
    snr_b = r * snr_a
    ba, bb = rng.choice(P.bgs, 2, replace=False)
    while c["bg_file"][bb] == c["bg_file"][ba] or c["bg_file"][bb] in (ta, tb) or c["bg_file"][ba] in (ta, tb):
        ba, bb = rng.choice(P.bgs, 2, replace=False)  # backgrounds never from the template's own file
    hi = 3.0 if wide else 1.0
    tau = float(np.exp(rng.uniform(np.log(0.01), np.log(hi)))) if rng.random() < 0.5 else 0.0
    which = int(rng.integers(2))
    xa, ma, ia = member(c, ta, ba, snr_a, rng, tau if which == 0 else 0.0, wide, scint_shared=ssh)
    xb, mb, ib = member(c, tb, bb, snr_b, rng, tau if which == 1 else 0.0, wide, gain_shared=gsh, scint_shared=ssh)
    swap = bool(rng.random() < 0.5)
    info = dict(kind=kind, src_a=s, src_b=s2, tmpl_a=c["tns"][ta], tmpl_b=c["tns"][tb], ti_a=int(ta), ti_b=int(tb),
                bg_a=c["tns"][c["bg_file"][ba]], bg_b=c["tns"][c["bg_file"][bb]], bi_a=int(ba), bi_b=int(bb),
                snr_a=snr_a, snr_b=snr_b, scat_member=which if tau > 0 else -1, tau600=tau, **imp,
                **{k + "_a": v for k, v in ia.items() if k != "tau600"}, **{k + "_b": v for k, v in ib.items() if k != "tau600"})
    if swap:  # random order; info keeps the pre-swap labels plus the flag
        xa, xb, ma, mb = xb, xa, mb, ma
    info["swapped"] = swap
    return xa, xb, ma, mb, KINDS.index(kind), info


def kind_of(i, cycle4=False):
    """Frozen sets: i < LEGACY cycles the three v1 kinds, later i are impostors.
    cycle4: all four kinds in turn (audit sets)."""
    if cycle4:
        return KINDS[i % 4]
    return KINDS[i % 3] if i < LEGACY else "impostor"


def gen_set(P, n, seed, wide, cycle4=False, snr_floor=SNR_MIN):
    """Deterministic: pair i uses rng([seed, i]) and kind kind_of(i)."""
    for i in range(n):
        yield (i,) + make_pair(kind_of(i, cycle4), np.random.default_rng([seed, i]), P, wide, snr_floor)


def load_set(name, pools=None):
    """Regenerate a frozen set and check it against its manifest hash. Returns arrays + labels."""
    pools = pools or load_pools()
    split, n, seed, wide, floor = SETS[name]
    exp = json.loads((MAN / f"{name}.json").read_text())
    assert exp.get("version") == VERSION, f"{name}: manifest is {exp.get('version', 'v0')}, code is {VERSION}"
    h = hashlib.sha256()
    XA, XB, MA, MB, Y = [], [], [], [], []
    for i, xa, xb, ma, mb, y, _ in gen_set(pools[split], n, seed, wide, floor > SNR_MIN, floor):
        h.update(xa.tobytes()); h.update(xb.tobytes())
        XA.append(xa); XB.append(xb); MA.append(ma); MB.append(mb); Y.append(y)
    assert h.hexdigest() == exp["sha256"], f"{name}: regenerated set differs from its manifest (code or inputs changed)"
    return np.stack(XA), np.stack(XB), np.stack(MA), np.stack(MB), np.array(Y)


# ---------------- audit helpers ----------------
def member_stats(x, m, lo, hi):
    cols = np.arange(WIN)
    off = (cols < lo - OFF_PAD) | (cols > hi + OFF_PAD)
    band = x[m].mean(0)
    sm = np.convolve(band, np.ones(3) / 3, "same")
    bs = max((np.convolve(band, np.ones(w), "same") / np.sqrt(w)).max() for w in (1, 2, 4, 8, 16)) * np.sqrt(m.sum())
    return dict(off_std=float(x[m][:, off].std()) if off.any() else np.nan, mask_frac=float(m.mean()),
                snr_box=float(bs), centre=int(sm.argmax()))


def xcorr(a, ma, b, mb, maxlag=20):
    """Baseline 1: max normalised cross-correlation over +-maxlag samples, common channels."""
    m = ma & mb
    A, B = a[m], b[m]
    n = 2 * WIN
    cc = np.fft.irfft((np.fft.rfft(A, n, axis=1) * np.conj(np.fft.rfft(B, n, axis=1))).sum(0), n)
    cc = np.concatenate([cc[-maxlag:], cc[:maxlag + 1]])
    return float(cc.max() / np.sqrt((A ** 2).sum() * (B ** 2).sum() + 1e-30))


def xcorr_smooth(a, ma, b, mb, blk=16, maxlag=20):
    """Baseline 1 on spectra block-averaged over blk channels (mask-weighted): envelope scale only."""
    def sm(x, m):
        w = m.reshape(-1, blk).sum(1)
        return (np.where(m[:, None], x, 0).reshape(-1, blk, WIN).sum(1) / np.maximum(w, 1)[:, None]), w >= blk // 4
    A, va = sm(a, ma)
    B, vb = sm(b, mb)
    return xcorr(A, va, B, vb, maxlag)


def main():
    if "--rebuild" in sys.argv or not CACHE.exists():
        build_cache()
    # self-check of the shift primitive: integer and DM shifts move a delta where expected
    d = np.zeros((2, WIN)); d[:, 50] = 1
    assert np.allclose(fshift(d, 7)[:, 57], 1, atol=1e-9) and np.allclose(fshift(d, np.array([0.0, 3.0]))[1, 53], 1, atol=1e-9)

    pools = load_pools()
    c = pools["train"].c
    if "--folds" in sys.argv:  # plan 2026-11-08_0845
        f = assign_folds(fold_sources(pools, "all"))
        assert sorted(np.bincount(list(f.values()))) == [16] * 5 and [f[b] for b in BIG] == [0, 1]
        assert sorted(np.bincount(list(assign_folds(fold_sources(pools, "dev")).values()))) == [12] * 5
        freeze_folds(pools)
        load_fold_set("dev", 4, pools)  # regeneration reproduces the hash
        print("load_fold_set('dev', 4) regenerates identical arrays")
        return
    print("split  sources(pool)  templates  backgrounds")
    for s, P in pools.items():
        print(f"{s:6s} {len(P.sources):5d} {sum(len(v) for v in P.tmpl.values()):10d} {len(P.bgs):11d}")
    # split-disjointness: templates and backgrounds only from their own split's files
    for s, P in pools.items():
        assert all((c["file_split"][t] == s).all() for t in P.tmpl.values())
        assert (c["file_split"][c["bg_file"][P.bgs]] == s).all()
    assert not (set(pools["train"].sources) & set(pools["test"].sources))

    # ---- frozen sets: manifest + hash ----
    MAN.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    keep = {}
    for name, (split, n, seed, wide, floor) in SETS.items():
        h = hashlib.sha256()
        rows = []
        for i, xa, xb, ma, mb, y, info in gen_set(pools[split], n, seed, wide, floor > SNR_MIN, floor):
            assert xa.shape == xb.shape == (NF, WIN) and np.isfinite(xa).all() and np.isfinite(xb).all()
            assert not xa[~ma].any() and not xb[~mb].any(), "masked channels must be zero"
            assert min(info["snr_a"], info["snr_b"]) >= floor - 1e-9
            h.update(xa.tobytes()); h.update(xb.tobytes())
            rows.append(dict(i=i, seed=f"{seed}:{i}", label=y, **info))
            if name == "test" and (i < 30 or LEGACY <= i < LEGACY + 10):
                keep[i] = (xa, xb, ma, mb, info)
        with open(MAN / f"{name}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        srcshare = max(np.unique([r["src_a"] for r in rows], return_counts=True)[1]) / n
        (MAN / f"{name}.json").write_text(json.dumps(dict(split=split, n=n, seed=seed, wide=wide, snr_floor=floor, version=VERSION, sha256=h.hexdigest(),
                                                          max_source_share=round(float(srcshare), 3)), indent=1))
        print(f"frozen {name}: {n} pairs from {split}, max source share {srcshare:.1%}, sha256 {h.hexdigest()[:12]}")
    load_set("test", pools)  # regeneration reproduces the hash
    print("load_set('test') regenerates identical arrays")
    if "--sets-only" in sys.argv:  # the audit below reads real same-source pairs: blinded until unblind-v1 (plan 2026-11-06_1223)
        return

    # ---- leak audit on a separate train-split set (2000 pairs per class) ----
    P = pools["train"]
    sidx = {s: k for k, s in enumerate(np.unique(c["source"]))}  # stable categorical code
    rows = []
    for i, xa, xb, ma, mb, y, info in gen_set(P, 8000, 999, False, cycle4=True):
        ea, eb = (info["ext_lo_a"], info["ext_hi_a"]), (info["ext_lo_b"], info["ext_hi_b"])
        if info["swapped"]:
            ea, eb = eb, ea
        sa = member_stats(xa, ma, *ea)
        sb = member_stats(xb, mb, *eb)
        both = ma & mb
        lo = min(info["ext_lo_a"], info["ext_lo_b"]) - OFF_PAD
        hi = max(info["ext_hi_a"], info["ext_hi_b"]) + OFF_PAD
        cols = np.arange(WIN)
        off = (cols < lo) | (cols > hi)
        nc = np.corrcoef(xa[both][:, off].ravel(), xb[both][:, off].ravel())[0, 1] if off.sum() > 5 and both.any() else np.nan
        ti_first = info["ti_b"] if info["swapped"] else info["ti_a"]
        bi_a, bi_b = (info["bi_b"], info["bi_a"]) if info["swapped"] else (info["bi_a"], info["bi_b"])
        rows.append(dict(y=y, sa=sa, sb=sb, noise_corr=nc, xc=xcorr(xa, ma, xb, mb),
                         snr_min=min(info["snr_a"], info["snr_b"]),
                         centre_off=sa["centre"] - sb["centre"],
                         # off_std is exactly 1 after re-normalisation, so not a feature; the centre
                         # offset measures profile similarity (lensing information), reported separately
                         f=[(ma & mb).sum() / max((ma | mb).sum(), 1), np.log(sa["snr_box"] / max(sb["snr_box"], 1e-3)),
                            sidx[c["source"][c["bg_file"][bi_a]]], sidx[c["source"][c["bg_file"][bi_b]]],
                            c["mjd_400"][c["bg_file"][bi_a]], c["mjd_400"][c["bg_file"][bi_b]],
                            *c["par"][ti_first], c["snr_fitb"][ti_first], c["model_snr"][ti_first]],
                         par_both=[*c["par"][info["ti_a"]], *c["par"][info["ti_b"]]]))
    from scipy.stats import ks_2samp
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import cross_val_score
    rep = []
    # plan step 3, revised: the 20 genuine chunks come from 5 long-window files whose noise is
    # time-correlated (lag-1 0.05-0.16) unlike the 158-sample files (~0), so they are not a fair
    # reference. Paired check instead: each tiled background vs one contiguous off-pulse run of its own file.
    with h5py.File(REAL / "preproc" / "repeaters_256x160.h5") as f:
        TMr0 = f["time_mask"][:]
    Xr0 = None
    with h5py.File(REAL / "preproc" / "repeaters_256x160.h5") as f:
        Xr0 = f["X"][:]
    lt, lr_, lft, lfr = [], [], [], []
    for b_, fi in enumerate(c["bg_file"]):
        m = c["fm"][fi] >= 0.25
        cols = np.arange(WIN)
        off = cols[(TMr0[fi] > 0) & ((cols < c["extent_lo"][fi] - OFF_PAD) | (cols > c["extent_hi"][fi] + OFF_PAD))]
        brk = np.flatnonzero(np.diff(off) > 1)
        run = off[:brk[0] + 1] if len(brk) and brk[0] + 1 >= len(off) - brk[0] - 1 else (off[brk[0] + 1:] if len(brk) else off)
        if len(run) < 20:
            continue
        v, t = Xr0[fi][m][:, run], c["bg_X"][b_][m]
        lr_.append(np.corrcoef(v[:, :-1].ravel(), v[:, 1:].ravel())[0, 1]); lt.append(np.corrcoef(t[:, :-1].ravel(), t[:, 1:].ravel())[0, 1])
        lfr.append(np.corrcoef(v[:-1].ravel(), v[1:].ravel())[0, 1]); lft.append(np.corrcoef(t[:-1].ravel(), t[1:].ravel())[0, 1])
    lt, lr_, lft, lfr = map(np.array, (lt, lr_, lft, lfr))
    rep.append(f"(0) backgrounds vs their own file's contiguous off-pulse (n={len(lt)}): lag-1 time median {np.median(lt):+.3f} vs "
               f"{np.median(lr_):+.3f}, median |diff| {np.median(np.abs(lt - lr_)):.3f}; lag-1 freq {np.median(lft):+.3f} vs "
               f"{np.median(lfr):+.3f}, median |diff| {np.median(np.abs(lft - lfr)):.3f}")
    Y = np.array([r["y"] for r in rows])
    rep.append("(a) per-member stats, KS p-values (members A and B pooled):")
    for k in ("off_std", "mask_frac", "snr_box", "centre"):
        v = {y: np.array([r[s][k] for r in rows if r["y"] == y for s in ("sa", "sb")]) for y in range(4)}
        p01, p02, p31 = ks_2samp(v[0], v[1]).pvalue, ks_2samp(v[0], v[2]).pvalue, ks_2samp(v[3], v[1]).pvalue
        med = "/".join(f"{np.nanmedian(v[y]):.3f}" for y in range(4))
        rep.append(f"    {k:9s} lensed-vs-repeat p={p01:.3f}  lensed-vs-unrelated p={p02:.3f}  "
                   f"impostor-vs-repeat p={p31:.3f}  medians {med}")
    lr = Y < 2
    F = np.array([r["f"] for r in rows], float)[lr]
    gbm = HistGradientBoostingClassifier(random_state=0)
    auc = cross_val_score(gbm, F, Y[lr], cv=5, scoring="roc_auc")
    Fb = np.array([r["par_both"] for r in rows], float)[lr]
    auc_both = cross_val_score(gbm, Fb, Y[lr], cv=5, scoring="roc_auc")
    rep.append(f"(b) shortcut probe, lensed vs repeat, n={lr.sum()}: AUC {auc.mean():.3f} +- {auc.std():.3f}  "
               f"[gate <= 0.55: {'PASS' if auc.mean() <= 0.55 else 'FAIL'}]")
    Fc = np.column_stack([F, np.array([r["centre_off"] for r in rows], float)[lr]])
    auc_c = cross_val_score(gbm, Fc, Y[lr], cv=5, scoring="roc_auc")
    rep.append(f"    with centre offset added (a profile-similarity measurement, i.e. lensing information): AUC {auc_c.mean():.3f}")
    ir = (Y == 1) | (Y == 3)
    Fi = np.array([r["f"] for r in rows], float)[ir]
    auc_i = cross_val_score(gbm, Fi, Y[ir], cv=5, scoring="roc_auc")
    rep.append(f"    impostor vs repeat, same non-spectral features, n={ir.sum()}: AUC {auc_i.mean():.3f} +- {auc_i.std():.3f}  "
               f"[gate <= 0.55: {'PASS' if auc_i.mean() <= 0.55 else 'FAIL'}]")
    rep.append(f"    probe-power check, fitburst params of BOTH members: AUC {auc_both.mean():.3f} (expected ~1: equality is the lensing signal)")
    nc = {y: np.array([r["noise_corr"] for r in rows if r["y"] == y]) for y in range(4)}
    rep.append("(c) off-pulse noise correlation between members (T2): " +
               "  ".join(f"{KINDS[y]} {np.nanmean(nc[y]):+.4f} (sd {np.nanstd(nc[y]):.4f})" for y in range(4)))
    # T1 trap demo: scaled real data in the on-pulse box shares the template's noise
    with h5py.File(REAL / "preproc" / "repeaters_256x160.h5") as f:
        Xr, FMr, TMr = f["X"][:], f["freq_mask"][:], f["time_mask"][:]
    bright = np.flatnonzero(c["eligible"] & (c["snr_fitb"] >= 50))
    rng = np.random.default_rng(5)
    for k in (0.1, 0.2, 0.5):
        zs, cs = [], []
        for ti in bright:
            m = (FMr[ti] >= 0.25)
            lo, hi = c["extent_lo"][ti] - 2, c["extent_hi"][ti] + 3
            box = np.zeros((NF, WIN), bool); box[m, max(lo, 0):min(hi, WIN)] = True
            Ts = np.where(m[:, None], c["T"][ti] / np.maximum(c["sigma"][ti], 1e-12)[:, None], 0)
            b = (Xr[ti][box] * Ts[box]).sum() / max((Ts[box] ** 2).sum(), 1e-30)
            b1, b2 = rng.choice(len(c["bg_X"]), 2, replace=False)
            r1 = k * (Xr[ti] - b * Ts) + c["bg_X"][b1]
            r2 = k * (Xr[ti] - b * Ts) + c["bg_X"][b2]
            msk = box & (c["fm"][c["bg_file"][b1]] >= 0.25)[:, None] & (c["fm"][c["bg_file"][b2]] >= 0.25)[:, None]
            if msk.sum() < 20:
                continue
            cc = np.corrcoef(r1[msk], r2[msk])[0, 1]
            cs.append(cc); zs.append(cc * np.sqrt(msk.sum()))
        rep.append(f"    T1 at k={k}: residual corr {np.mean(cs):.3f} (k^2/(1+k^2) = {k*k/(1+k*k):.3f}), "
                   f"median z {np.median(zs):.1f} over {len(cs)} bright templates")
    # (d) baseline 1 on constructed vs real as-observed repeat pairs
    xc = {y: np.array([r["xc"] for r in rows if r["y"] == y]) for y in range(4)}
    real_src = c["source"]
    ok = (c["coarse_dt"] == 0) & (c["snr_fitb"] >= SNR_MIN)
    rr = np.random.default_rng(11)
    real = []
    byS = {s: np.flatnonzero(ok & (real_src == s)) for s in np.unique(real_src)}
    byS = {s: v for s, v in byS.items() if len(v) >= 2}
    keys = sorted(byS)
    for _ in range(2000):  # uniform over sources, like the constructed pairs
        v = byS[keys[rr.integers(len(keys))]]
        i, j = rr.choice(v, 2, replace=False)
        real.append(xcorr(Xr[i], FMr[i] >= 0.25, Xr[j], FMr[j] >= 0.25))
    real = np.array(real)
    # twin ladder: each real repeat pair (i, j) re-simulated from its own two templates on the SAME
    # fresh backgrounds and the SAME nuisance draws in every variant -> each step isolates one cause.
    # Scored at full resolution and on 16 x 25 MHz smoothed spectra (envelope/beam scale only).
    el = np.flatnonzero(c["eligible"])
    byT = {s: el[c["source"][el] == s] for s in np.unique(c["source"][el])}
    byT = {s: v for s, v in byT.items() if len(v) >= 2}
    kT = sorted(byT)
    ALLN = ("shift", "dm", "scint")
    variants = {"naked": dict(off=ALLN), "+shift": dict(off=("dm", "scint")), "+dm": dict(off=("shift", "scint")),
                "+scint": dict(off=("shift", "dm")), "full (v1)": dict(off=()), "full, catalog S/N (v0)": dict(off=(), cat=True)}
    lad = {k: ([], []) for k in ("real", *variants)}
    for q in range(1000):
        i, j = rr.choice(byT[kT[rr.integers(len(kT))]], 2, replace=False)
        b1, b2 = rr.choice(np.flatnonzero(~np.isin(c["bg_file"], [i, j])), 2, replace=False)
        mi_, mj_ = FMr[i] >= 0.25, FMr[j] >= 0.25
        lad["real"][0].append(xcorr(Xr[i], mi_, Xr[j], mj_)); lad["real"][1].append(xcorr_smooth(Xr[i], mi_, Xr[j], mj_))
        for name, v in variants.items():
            snr_i, snr_j = ((c["snr_fitb"][i], c["snr_fitb"][j]) if v.get("cat") else (c["model_snr"][i], c["model_snr"][j]))
            g = np.random.default_rng([77, q])
            xi, mi, _ = member(c, i, b1, max(snr_i, SNR_MIN), g, 0.0, False, v["off"])
            xj, mj, _ = member(c, j, b2, max(snr_j, SNR_MIN), g, 0.0, False, v["off"])
            lad[name][0].append(xcorr(xi, mi, xj, mj)); lad[name][1].append(xcorr_smooth(xi, mi, xj, mj))
    lad = {k: (np.array(a), np.array(b)) for k, (a, b) in lad.items()}
    from scipy.stats import wilcoxon
    twin_lines = ["    twin ladder (n=1000 real repeat pairs; gap = median(sim - real) / median(real)):",
                  f"      {'variant':24s} {'full-res median':>15s} {'gap':>7s}   {'25 MHz median':>13s} {'gap':>7s}"]
    for k, (a, b) in lad.items():
        ra, rb = lad["real"]
        ga = np.median(a - ra) / np.median(ra) if k != "real" else 0.0
        gb = np.median(b - rb) / np.median(rb) if k != "real" else 0.0
        twin_lines.append(f"      {k:24s} {np.median(a):15.4f} {ga:+7.1%}   {np.median(b):13.4f} {gb:+7.1%}")
    a, ra = lad["full (v1)"][0], lad["real"][0]
    twin_lines.append(f"      full (v1) vs real: Wilcoxon p={wilcoxon(a, ra).pvalue:.2e}, "
                      f"Spearman r={np.corrcoef(np.argsort(np.argsort(ra)), np.argsort(np.argsort(a)))[0, 1]:.2f}")
    # is the gap source-specific (shared beam/structure) or a generic template deficit? Same check
    # on different-source pairs: naked templates vs real, and the same-vs-different contrast.
    cnt = {}
    for kind in ("same", "diff"):
        R_, M_ = [], []
        for q in range(1000):
            if kind == "same":
                i, j = rr.choice(byT[kT[rr.integers(len(kT))]], 2, replace=False)
            else:
                i, j = rr.choice(el, 2, replace=False)
                if c["source"][i] == c["source"][j]:
                    continue
            b1, b2 = rr.choice(np.flatnonzero(~np.isin(c["bg_file"], [i, j])), 2, replace=False)
            R_.append(xcorr(Xr[i], FMr[i] >= 0.25, Xr[j], FMr[j] >= 0.25))
            g = np.random.default_rng([78, q])
            xi, mi, _ = member(c, i, b1, max(c["model_snr"][i], SNR_MIN), g, 0.0, False, ALLN)
            xj, mj, _ = member(c, j, b2, max(c["model_snr"][j], SNR_MIN), g, 0.0, False, ALLN)
            M_.append(xcorr(xi, mi, xj, mj))
        cnt[kind] = (np.median(R_), np.median(M_))
    twin_lines.append(f"      naked-vs-real gap, same-source {cnt['same'][1] / cnt['same'][0] - 1:+.1%}, different-source "
                      f"{cnt['diff'][1] / cnt['diff'][0] - 1:+.1%}; same/different contrast real "
                      f"{cnt['same'][0] / cnt['diff'][0] - 1:+.1%}, naked {cnt['same'][1] / cnt['diff'][1] - 1:+.1%}")
    twin_line = "\n".join(twin_lines)
    rep.append(f"(d) baseline-1 xcorr medians: constructed lensed {np.median(xc[0]):.3f}, repeat {np.median(xc[1]):.3f}, "
               f"unrelated {np.median(xc[2]):.3f}, impostor {np.median(xc[3]):.3f}; REAL repeat pairs {np.median(real):.3f} (n=2000); "
               f"KS constructed-vs-real repeat p={ks_2samp(xc[1], real).pvalue:.2e}")
    smin = np.array([r["snr_min"] for r in rows])
    XC = np.array([r["xc"] for r in rows])
    for a_, b_ in ((10, 15), (15, 25), (25, 50), (50, 1e9)):
        sb_ = (smin >= a_) & (smin < b_)
        auc_txt = []
        for pos, neg, nm in ((0, 1, "lensed vs repeat"), (0, 3, "lensed vs impostor"), (3, 1, "impostor vs repeat")):
            s = sb_ & ((Y == pos) | (Y == neg))
            if s.sum() > 50 and len(set(Y[s])) == 2:
                auc_txt.append(f"{nm} {roc_auc_score(Y[s] == pos, XC[s]):.3f}")
        rep.append(f"    baseline-1 AUC, min S/N {a_}-{b_ if b_ < 1e9 else 'inf'}: " + ", ".join(auc_txt) + f" (n={sb_.sum()})")
    rep.append(twin_line)
    # (e) real control (plan 1925): FRB 20201124A, the proposed plasma-lensing repeater; reference, not a gate
    ctl = "FRB20201124A"
    msnr = np.where(np.isfinite(c["model_snr"]), c["model_snr"], c["snr_fitb"])
    rc = np.random.default_rng(13)
    others = [k for k in keys if k != ctl]
    sc = {}
    for nm in ("20201124A", "other sources"):
        vals = []
        for _ in range(3000):
            v = byS[ctl] if nm == "20201124A" else byS[others[rc.integers(len(others))]]
            i, j = rc.choice(v, 2, replace=False)
            vals.append((min(msnr[i], msnr[j]), xcorr(Xr[i], FMr[i] >= 0.25, Xr[j], FMr[j] >= 0.25)))
        sc[nm] = np.array(vals)
    rep.append("(e) real control FRB 20201124A: baseline-1 median xcorr of its real repeat pairs vs other sources' (by min S/N)")
    for a_, b_ in ((10, 25), (25, 1e9)):
        cells = []
        for nm, v in sc.items():
            s = (v[:, 0] >= a_) & (v[:, 0] < b_)
            cells.append(f"{nm} {np.median(v[s, 1]):.4f} (n={s.sum()})" if s.sum() >= 10 else f"{nm} n={s.sum()}")
        rep.append(f"    S/N {a_}-{b_ if b_ < 1e9 else 'inf'}: " + "; ".join(cells))
    txt = "\n".join(rep)
    print(txt)
    (OUT / "audit.txt").write_text(txt + "\n")

    # ---- gallery: 10 test pairs per class ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for y, kind in enumerate(KINDS):
        idx = [i for i in sorted(keep) if kind_of(i) == kind][:10]
        fig, ax = plt.subplots(len(idx), 2, figsize=(7, 1.6 * len(idx)))
        for r, i in enumerate(idx):
            xa, xb, ma, mb, info = keep[i]
            for col, x in enumerate((xa, xb)):
                ax[r, col].imshow(x, aspect="auto", origin="lower", vmin=-2, vmax=4, cmap="viridis")
                ax[r, col].set_xticks([]); ax[r, col].set_yticks([])
            ax[r, 0].set_ylabel(f"#{i}", fontsize=7)
            ax[r, 1].set_title(f"{info['tmpl_a']} | {info['tmpl_b']}  S/N {info['snr_a']:.0f}/{info['snr_b']:.0f}", fontsize=6)
        fig.suptitle(f"test pairs: {kind}")
        fig.tight_layout()
        fig.savefig(OUT / f"gallery_{kind}.png", dpi=110)
        plt.close(fig)
    print(f"gallery: {OUT}/gallery_*.png")


if __name__ == "__main__":
    main()
