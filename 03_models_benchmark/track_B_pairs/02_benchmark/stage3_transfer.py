"""Stage 3 transfer check on val-split real cross-source pairs (plan 2026-11-09_1340).
Real pairs from two DIFFERENT val sources only (true negatives; blinding-safe). Each real pair gets 5 simulated twins
from the same two templates at their measured S/N. Criterion: real FPR <= 2% at the twins' 99th-percentile score.
Usage: python -I stage3_transfer.py      -> outputs/stage3_val.txt, outputs/stage3_scores.npz
"""
import sys
from multiprocessing import Pool
from pathlib import Path

import h5py
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "01_training"), str(HERE.parents[2] / "02_injection_labelling" / "01_injection")]
from inject import BRIGHT, REAL, SNR_MIN, fill_window, load_pools, member
import baselines as BL
from metrics import FPR

OUT = HERE / "outputs"
NTWIN, LIMIT = 5, 0.02
BASE = ["b1_blk16", "b2_blk16"]  # best variant of each, chosen on val_bright in Stage 1
CKPTS = [(m, s) for m in (6, 5, 4, 7) for s in range(3)]


def load_real():
    pools = load_pools()
    c = pools["val"].c
    files = np.flatnonzero((c["file_split"] == "val") & c["eligible"] & (c["model_snr"] >= SNR_MIN))
    with h5py.File(REAL / "preproc" / "repeaters_256x160.h5") as f:
        X, FM, TM = f["X"][files], f["freq_mask"][files], f["time_mask"][files]
    # zero-padded short windows made model 6 fail (update 2026-11-09_1520): fill them like the backgrounds
    filled = [fill_window(x, t, c["extent_lo"][i], c["extent_hi"][i]) for x, t, i in zip(X, TM, files)]
    X = np.stack([y for y, _ in filled]).astype(np.float32)
    load_real.n_filled, load_real.n_short = sum(ok for _, ok in filled), int(((TM <= 0).mean(1) > 0).sum())
    return pools, c, files, dict(zip(files.tolist(), range(len(files)))), X, FM >= 0.25


def twin(c, i, j, rng, bgs):
    """One simulated unrelated pair from templates i and j at their measured S/N, nuisances as in make_pair."""
    ba, bb = rng.choice(bgs, 2, replace=False)
    while c["bg_file"][ba] == c["bg_file"][bb] or c["bg_file"][ba] in (i, j) or c["bg_file"][bb] in (i, j):
        ba, bb = rng.choice(bgs, 2, replace=False)
    tau = float(np.exp(rng.uniform(np.log(0.01), 0.0))) if rng.random() < 0.5 else 0.0
    which = int(rng.integers(2))
    xa, ma, _ = member(c, i, ba, max(c["model_snr"][i], SNR_MIN), rng, tau if which == 0 else 0.0, False)
    xb, mb, _ = member(c, j, bb, max(c["model_snr"][j], SNR_MIN), rng, tau if which == 1 else 0.0, False)
    return xa, ma, xb, mb


def twin_rng(i, j, t):
    return np.random.default_rng([31, int(i), int(j), t])


def init_w():
    global P, C, IDX, X, M
    P, C, _, IDX, X, M = load_real()


def feats(job):
    """job = (i, j, t): t = -1 real pair, else twin t. Returns the 6 baseline scores and the 14 GBM features."""
    i, j, t = job
    if t < 0:
        xa, ma, xb, mb = X[IDX[i]], M[IDX[i]], X[IDX[j]], M[IDX[j]]
    else:
        xa, ma, xb, mb = twin(C, i, j, twin_rng(i, j, t), P["val"].bgs)
    s, f = BL.score_pair(xa, ma, xb, mb, C["freq_mhz"])
    return s, f


def learned_scores(getter, n_items):
    """Scores of all 12 Stage 2 checkpoints on items 0..n_items-1; getter(k) -> (xa, xb) for a chunk of indices."""
    import torch
    from models import MODELS
    from train import scores
    TR = HERE.parent / "01_training" / "outputs"
    nets = {}
    for m, s in CKPTS:
        net = MODELS[m]().to("cuda")
        net.load_state_dict(torch.load(TR / f"m{m}_s{s}" / "best.pt", map_location="cuda"))
        nets[f"m{m}_s{s}"] = net
    out = {k: [] for k in nets}
    for lo in range(0, n_items, 1000):
        A, B = getter(range(lo, min(lo + 1000, n_items)))
        A, B = torch.from_numpy(A).half(), torch.from_numpy(B).half()
        for k, net in nets.items():
            out[k].append(scores(net, A, B, "cuda"))
        print(f"  learned scores {min(lo + 1000, n_items)}/{n_items}", flush=True)
    return {k: np.concatenate(v).astype(float) for k, v in out.items()}


def operating_negatives():
    """val_bright repeat + impostor scores per method: their 99th percentile is the primary metric's threshold."""
    vb = np.load(OUT / "scores_val_bright.npz")
    keep = vb["y"] != 2
    neg = vb["y"][keep] != 0
    out = {k: vb[k][keep][neg] for k in BASE + ["b3_gbm"]}
    for m, s in CKPTS:
        out[f"m{m}_s{s}"] = np.load(HERE.parent / "01_training" / "outputs" / f"m{m}_s{s}" / "val_bright_scores.npy")[neg]
    return out


def main():
    from scipy.stats import spearmanr
    pools, c, files, IDX, X, M = load_real()
    src = c["source"]
    pairs = np.array([(i, j) for a, i in enumerate(files) for j in files[a + 1:] if src[i] != src[j]])
    npr = len(pairs)
    snr = np.minimum(c["model_snr"][pairs[:, 0]], c["model_snr"][pairs[:, 1]])
    sa, sb = src[pairs[:, 0]], src[pairs[:, 1]]
    overlap = np.array([(M[IDX[i]] & M[IDX[j]]).mean() for i, j in pairs])
    print(f"real windows with missing columns {load_real.n_short}, filled {load_real.n_filled}", flush=True)
    print(f"{len(files)} val files, {len(set(src[files]))} sources, {npr} real cross-source pairs, {(snr >= BRIGHT).sum()} with min S/N >= {BRIGHT:g}", flush=True)

    # ---- baselines and GBM features (CPU) ----
    jobs = [(i, j, -1) for i, j in pairs] + [(i, j, t) for i, j in pairs for t in range(NTWIN)]
    with Pool(16, initializer=init_w) as pool:
        r = pool.map(feats, jobs, chunksize=40)
    S = np.array([x[0] for x in r]); F = np.array([x[1] for x in r])
    with Pool(16, initializer=BL.init) as pool:
        gbm = BL.fit_gbm(pool)
    allsc = {k: S[:, BL.METHODS.index(k)] for k in BASE} | {"b3_gbm": gbm.predict_proba(F)[:, 1]}
    R = {k: v[:npr] for k, v in allsc.items()}
    T = {k: v[npr:].reshape(npr, NTWIN) for k, v in allsc.items()}

    # ---- learned models (GPU); twins regenerated with the same seeds as the CPU path ----
    sv = pools["val"]
    real_get = lambda ks: (X[[IDX[pairs[k, 0]] for k in ks]], X[[IDX[pairs[k, 1]] for k in ks]])

    def twin_get(ks):
        A, B = [], []
        for k in ks:
            p, t = divmod(k, NTWIN)
            xa, _, xb, _ = twin(c, pairs[p, 0], pairs[p, 1], twin_rng(pairs[p, 0], pairs[p, 1], t), sv.bgs)
            A.append(xa); B.append(xb)
        return np.stack(A), np.stack(B)
    lr = learned_scores(real_get, npr)
    lt = learned_scores(twin_get, npr * NTWIN)
    for k in lr:
        R[k], T[k] = lr[k], lt[k].reshape(npr, NTWIN)
    np.savez(OUT / "stage3_scores.npz", pairs=pairs, snr=snr, overlap=overlap, **{f"real_{k}": v for k, v in R.items()},
             **{f"twin_{k}": v for k, v in T.items()})

    # ---- report ----
    rep = []
    say = lambda s="": (print(s, flush=True), rep.append(s))
    names = np.unique(np.concatenate([sa, sb]))
    rng = np.random.default_rng(2026)
    boots = [np.bincount(rng.integers(len(names), size=len(names)), minlength=len(names)) for _ in range(2000)]
    ia, ib = np.searchsorted(names, sa), np.searchsorted(names, sb)

    def fpr_ci(hit, sel):
        """Source bootstrap: a pair counts w[a] * w[b] times in a resample of sources."""
        v = []
        for w in boots:
            wt = (w[ia] * w[ib])[sel]
            if wt.sum() > 0:
                v.append((wt * hit).sum() / wt.sum())
        return np.percentile(v, [2.5, 97.5])

    vneg = operating_negatives()

    bins = {"[10,25)": (snr >= SNR_MIN) & (snr < BRIGHT), ">=25 (headline)": snr >= BRIGHT}
    say(f"real windows with missing columns: {load_real.n_short}, filled with mirrored off-pulse noise: {load_real.n_filled}")
    say(f"Stage 3, val split: {len(files)} files, {len(names)} sources, {npr} real cross-source pairs, {NTWIN} twins each")
    say(f"criterion: real FPR <= {LIMIT:.0%} at the twins' {1 - FPR:.0%} quantile, per min-S/N bin; CI = source bootstrap (threshold fixed)")
    for b, sel in bins.items():
        say(f"\nbin {b}: {sel.sum()} real pairs, {sel.sum() * NTWIN} twins")
        say(f"  {'method':9s} {'real FPR':>9s} {'95% CI':>15s}  verdict   twin FPR at val_bright thr / real   Spearman real~twin / ceiling")
        for k in R:
            thr = np.quantile(T[k][sel].ravel(), 1 - FPR)
            hit = R[k][sel] > thr
            lo, hi = fpr_ci(hit, sel)
            tv = np.quantile(vneg[k], 1 - FPR)
            rho = spearmanr(R[k][sel], T[k][sel].mean(1)).statistic
            ceil = spearmanr(T[k][sel][:, 0], T[k][sel][:, 1]).statistic
            say(f"  {k:9s} {hit.mean():9.3f} [{lo:.3f}, {hi:.3f}]  {'PASS' if hit.mean() <= LIMIT else 'FAIL'}      "
                f"{(T[k][sel] > tv).mean():.3f} / {(R[k][sel] > tv).mean():.3f}                    {rho:+.2f} / {ceil:+.2f}")
    sel = bins[">=25 (headline)"]
    med = np.median(overlap[sel])
    say(f"\nheadline bin split by channel-mask overlap (median {med:.2f}): real FPR at the twin threshold, low / high overlap")
    for k in R:
        thr = np.quantile(T[k][sel].ravel(), 1 - FPR)
        lo_, hi_ = sel & (overlap <= med), sel & (overlap > med)
        say(f"  {k:9s} {(R[k][lo_] > thr).mean():.3f} (n={lo_.sum()}) / {(R[k][hi_] > thr).mean():.3f} (n={hi_.sum()})")
    say("\nheadline bin: real pairs above the twin threshold, by source (top 5, model 6 seed 0 and b3_gbm)")
    for k in ("m6_s0", "b3_gbm"):
        thr = np.quantile(T[k][sel].ravel(), 1 - FPR)
        hit = sel & (R[k] > thr)
        cnt = {}
        for a, b in zip(sa[hit], sb[hit]):
            for s_ in (a, b):
                cnt[s_] = cnt.get(s_, 0) + 1
        say(f"  {k:9s} {hit.sum()} pairs: " + ", ".join(f"{s_} {n}" for s_, n in sorted(cnt.items(), key=lambda x: -x[1])[:5]))
    (OUT / "stage3_val.txt").write_text("\n".join(rep) + "\n")


if __name__ == "__main__":
    main()
