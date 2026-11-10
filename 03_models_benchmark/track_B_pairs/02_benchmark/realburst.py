"""Real-burst lensed test (plan 2026-11-10_0900, part A): do the methods rely on smooth fitburst templates?
Pseudo-lensed pairs = two copies of ONE real burst (cutout of its own window), injected like templates. Paired with
template copies and noise-only copies under identical draws. Recall at the operating threshold (val_bright).
Usage: python -I realburst.py      -> outputs/realburst.txt, outputs/realburst_scores.npz
"""
import sys
from multiprocessing import Pool
from pathlib import Path

import h5py
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "01_training"), str(HERE.parents[2] / "02_injection_labelling" / "01_injection")]
from inject import OFF_PAD, REAL, WIN, fill_window, load_pools, member
import baselines as BL
from metrics import FPR
from stage3_transfer import CKPTS, learned_scores, operating_negatives

OUT = HERE / "outputs"
NPAIR, MIN_SNR, KMAX, TAPER = 40, 50.0, 0.5, 3
SETTINGS = (25.0, 40.0)  # injected S/N; a burst enters a setting only if k = snr / its S/N <= KMAX
VERSIONS = ("real", "template", "noise")


def cutout(x, lo, hi):
    """x inside [lo - OFF_PAD, hi + OFF_PAD], zero outside, cosine-tapered over TAPER samples (no FFT ringing)."""
    a, b = max(lo - OFF_PAD, 0), min(hi + OFF_PAD + 1, WIN)
    w = np.zeros(WIN)
    w[a:b] = 1.0
    ramp = 0.5 - 0.5 * np.cos(np.pi * (np.arange(TAPER) + 0.5) / TAPER)
    w[a:a + TAPER] *= ramp
    w[b - TAPER:b] *= ramp[::-1]
    return x * w[None, :]


def load():
    pools = load_pools()
    c = pools["train"].c
    files = np.flatnonzero(c["eligible"] & (c["model_snr"] >= MIN_SNR) & np.isin(c["file_split"], ["val", "train"]))
    with h5py.File(REAL / "preproc" / "repeaters_256x160.h5") as f:
        X, TM = f["X"][files], f["time_mask"][files]
    own_bg = {int(fi): b for b, fi in enumerate(c["bg_file"])}
    cuts = {}
    for x, t, i in zip(X, TM, files):
        lo, hi = c["extent_lo"][i], c["extent_hi"][i]
        x, _ = fill_window(x, t, lo, hi)
        cuts[int(i)] = dict(real=cutout(x, lo, hi),
                            noise=cutout(c["bg_X"][own_bg[int(i)]], lo, hi) if int(i) in own_bg else None)
    return pools, c, files, cuts


def jobs_for(c, files):
    """(file, setting S/N, n, version) for every burst that reaches the setting with k <= KMAX."""
    out = []
    for i in files:
        for snr in SETTINGS:
            if snr / c["model_snr"][i] <= KMAX:
                out += [(int(i), snr, n, v) for n in range(NPAIR) for v in VERSIONS]
    return out


def make(job, pools, c, cuts):
    """Identical draws for all three versions of (file, snr, n): only the injected image differs."""
    i, snr, n, ver = job
    if ver == "noise" and cuts[i]["noise"] is None:
        return None
    P = pools[c["file_split"][i]]
    rng = np.random.default_rng([41, i, int(snr), n])
    ba, bb = rng.choice(P.bgs, 2, replace=False)
    while c["bg_file"][ba] == c["bg_file"][bb] or i in (c["bg_file"][ba], c["bg_file"][bb]):
        ba, bb = rng.choice(P.bgs, 2, replace=False)
    tau = float(np.exp(rng.uniform(np.log(0.01), 0.0))) if rng.random() < 0.5 else 0.0
    which = int(rng.integers(2))
    k = snr / c["model_snr"][i]
    kw = {} if ver == "template" else dict(S0=cuts[i][ver], amp=k)
    xa, ma, _ = member(c, i, ba, snr, rng, tau if which == 0 else 0.0, False, **kw)
    xb, mb, _ = member(c, i, bb, snr, rng, tau if which == 1 else 0.0, False, **kw)
    return xa, ma, xb, mb


def init_w():
    global G
    G = load()


def feats(job):
    pools, c, _, cuts = G
    r = make(job, pools, c, cuts)
    if r is None:
        return None
    return BL.score_pair(*r, c["freq_mhz"])


def main():
    pools, c, files, cuts = load()
    jobs = jobs_for(c, files)
    ok = [cuts[j[0]]["noise"] is not None or j[3] != "noise" for j in jobs]
    jobs = [j for j, o in zip(jobs, ok) if o]
    J = np.array([(j[0], int(j[1]), j[2]) for j in jobs])
    ver = np.array([j[3] for j in jobs])
    split = c["file_split"][J[:, 0]]
    src = c["source"][J[:, 0]]
    print(f"{len(files)} bright bursts (val {np.isin(files, np.flatnonzero(c['file_split'] == 'val')).sum()}), {len(jobs)} pairs", flush=True)

    with Pool(16, initializer=init_w) as pool:
        r = pool.map(feats, jobs, chunksize=20)
    with Pool(16, initializer=BL.init) as pool:
        gbm = BL.fit_gbm(pool)
    S = np.array([x[0] for x in r])
    F = np.array([x[1] for x in r])
    sc = {"b2_blk16": S[:, BL.METHODS.index("b2_blk16")], "b3_gbm": gbm.predict_proba(F)[:, 1]}

    def get(ks):
        A, B = [], []
        for q in ks:
            xa, _, xb, _ = make(jobs[q], pools, c, cuts)
            A.append(xa); B.append(xb)
        return np.stack(A), np.stack(B)
    sc |= learned_scores(get, len(jobs))
    np.savez(OUT / "realburst_scores.npz", J=J, ver=ver, split=split, src=src, **sc)

    thr = {k: np.quantile(v, 1 - FPR) for k, v in operating_negatives().items()}
    rep = []
    say = lambda s="": (print(s, flush=True), rep.append(s))
    hit = {k: sc[k] > thr[k] for k in sc}
    hit["m6 (3 seeds)"] = np.mean([hit[f"m6_s{s}"] for s in range(3)], 0)
    order = ["m6 (3 seeds)"] + [f"m{m}_s{s}" for m, s in CKPTS] + ["b3_gbm", "b2_blk16"]
    rng = np.random.default_rng(2026)
    for sp in ("val", "train"):
        for snr in SETTINGS:
            base = (split == sp) & (J[:, 1] == snr)
            if not base.any():
                continue
            names = np.unique(src[base])
            nb = len(np.unique(J[base, 0]))
            say(f"\n{sp} bursts, injected S/N {snr:g}: {nb} bursts, {len(names)} sources, {NPAIR} pairs per burst and version"
                f"; k = {np.median(snr / c['model_snr'][np.unique(J[base, 0])]):.2f} median")
            say(f"  {'method':13s} {'real':>6s} {'template':>9s} {'noise':>6s}   real/template [95% source CI]")
            boots = [rng.choice(names, len(names)) for _ in range(2000)]
            for k in order:
                rv = {v: hit[k][base & (ver == v)] for v in VERSIONS}
                sv = {v: src[base & (ver == v)] for v in VERSIONS}

                def ratio(ns):
                    a = np.concatenate([rv["real"][sv["real"] == s_] for s_ in ns])
                    b = np.concatenate([rv["template"][sv["template"] == s_] for s_ in ns])
                    return a.mean() / max(b.mean(), 1e-9)
                bs = [ratio(b) for b in boots]
                say(f"  {k:13s} {rv['real'].mean():6.3f} {rv['template'].mean():9.3f} {rv['noise'].mean():6.3f}   "
                    f"{ratio(names):.2f} [{np.percentile(bs, 2.5):.2f}, {np.percentile(bs, 97.5):.2f}]")
            if sp == "val" and snr == 25.0:
                m6 = {v: hit["m6 (3 seeds)"][base & (ver == v)].mean() for v in VERSIONS}
                g = hit["b3_gbm"][base & (ver == "real")].mean()
                crit = [m6["real"] >= 0.8 * m6["template"], m6["real"] > g, m6["noise"] <= 0.05]
                say(f"  CRITERION (plan): real >= 0.8 x template {crit[0]}; real > b3_gbm real ({g:.3f}) {crit[1]}; "
                    f"noise-only <= 0.05 {crit[2]}  ->  {'PASS' if all(crit) else 'FAIL'}")
    (OUT / "realburst.txt").write_text("\n".join(rep) + "\n")


if __name__ == "__main__":
    main()
