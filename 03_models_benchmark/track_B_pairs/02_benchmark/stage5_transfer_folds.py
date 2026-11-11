"""Stage 5 transfer check on each fold's held-out sources with its out-of-fold models (plan 2026-11-08_0845 F8, last bullet).

Same rules as stage3_transfer.py (team): real cross-source pairs between held-out sources only (true negatives),
real windows filled with fill_window, NTWIN = 5 twins per pair from the same two templates at their measured S/N
(backgrounds from the fold's held-out pool), criterion real FPR <= 2% at the twins' 99th percentile per min-S/N bin.
Each pair is scored by its own fold's models: model 6 final checkpoint (folds_all/m6_fK/final.pt), baselines 1-2
(frozen grids) and the fold GBM (refitted with the run_fold recipe and checked against the saved gbm_fK.npz scores).
Thresholds are set per fold from that fold's twins, hits are pooled over folds, and the CI is a source bootstrap over all
held-out sources. Compute cap (deviation, disclosed): at most MAXPAIRS real pairs per fold, a seeded random subset.
Usage: python stage5_transfer_folds.py      -> outputs/folds_all/stage5_transfer.txt
"""
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import h5py
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "01_training"), str(HERE.parents[2] / "02_injection_labelling" / "01_injection")]
import baselines as BL  # noqa: E402
from inject import BRIGHT, FOLD_SETS, REAL, SNR_MIN, fill_window, fold_pools, kind_of, load_pools  # noqa: E402
from metrics import FPR  # noqa: E402
from stage3_transfer import NTWIN, LIMIT, twin, twin_rng  # noqa: E402

OUT = HERE / "outputs" / "folds_all"
TR = HERE.parent / "01_training" / "outputs" / "folds_all"
K, MAXPAIRS, SEED = 5, 4000, 2026
BASE = ["b1_blk16", "b2_blk16"]


def load_fold_real(k):
    pools = load_pools()
    ho = fold_pools(pools, "all", k)[1]
    c = ho.c
    srcs = set(map(str, ho.sources))
    files = np.flatnonzero(np.isin(c["source"], list(srcs)) & c["eligible"] & (c["model_snr"] >= SNR_MIN))
    with h5py.File(REAL / "preproc" / "repeaters_256x160.h5") as f:
        X, FM, TM = f["X"][files], f["freq_mask"][files], f["time_mask"][files]
    filled = [fill_window(x, t, c["extent_lo"][i], c["extent_hi"][i]) for x, t, i in zip(X, TM, files)]
    X = np.stack([y for y, _ in filled]).astype(np.float32)
    return ho, c, files, dict(zip(files.tolist(), range(len(files)))), X, FM >= 0.25


def init_w(k):
    global HO, C, IDX, X, M
    HO, C, _, IDX, X, M = load_fold_real(k)


def feats(job):
    i, j, t = job
    if t < 0:
        xa, ma, xb, mb = X[IDX[i]], M[IDX[i]], X[IDX[j]], M[IDX[j]]
    else:
        xa, ma, xb, mb = twin(C, i, j, twin_rng(i, j, t), HO.bgs)
    return BL.score_pair(xa, ma, xb, mb, C["freq_mhz"])


def fold_gbm(k):
    """run_fold's GBM for fold k, refitted; checked on the first 200 pairs of the frozen fold set."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    with Pool(8, initializer=BL.init, initargs=(("all", k),)) as pool:
        tr = BL.run(pool, BL.gbm_jobs("tr", 500 + 2 * k))
        chk = BL.run(pool, [("ho", kind_of(i, True), [FOLD_SETS["all"] + k, i], False, BRIGHT) for i in range(200)])
    gbm = HistGradientBoostingClassifier(random_state=0).fit(tr["f"], tr["y"] == 0)
    assert np.allclose(gbm.predict_proba(chk["f"])[:, 1], np.load(OUT / f"gbm_f{k}.npz")["b3_gbm"][:200]), f"fold {k} GBM refit differs"
    return gbm


def main():
    import torch
    from scipy.stats import spearmanr
    from models import MODELS
    from train import scores
    tag = subprocess.run(["git", "tag", "-l", "benchmark-v1"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    assert tag == "benchmark-v1"
    rng = np.random.default_rng(SEED)
    allR, allT, meta = {}, {}, []
    for k in range(K):
        ho, c, files, IDX, Xr, Mr = load_fold_real(k)
        src = c["source"]
        pairs = np.array([(i, j) for a, i in enumerate(files) for j in files[a + 1:] if src[i] != src[j]])
        n_all = len(pairs)
        if n_all > MAXPAIRS:
            pairs = pairs[np.sort(rng.choice(n_all, MAXPAIRS, replace=False))]
        npr = len(pairs)
        print(f"fold {k}: {len(files)} held-out files, {len(set(src[files]))} sources, {n_all} cross-source pairs, scoring {npr}", flush=True)
        jobs = [(i, j, -1) for i, j in pairs] + [(i, j, t) for i, j in pairs for t in range(NTWIN)]
        with Pool(8, initializer=init_w, initargs=(k,)) as pool:
            r = pool.map(feats, jobs, chunksize=40)
        S, F = np.array([x[0] for x in r]), np.array([x[1] for x in r])
        gbm = fold_gbm(k)
        sc = {b: S[:, BL.METHODS.index(b)] for b in BASE} | {"b3_gbm": gbm.predict_proba(F)[:, 1]}
        net = MODELS[6]().to("cuda")
        net.load_state_dict(torch.load(TR / f"m6_f{k}" / "final.pt", map_location="cuda"))
        real, tw = [], []
        for lo in range(0, npr, 500):
            ks = range(lo, min(lo + 500, npr))
            A = torch.from_numpy(Xr[[IDX[pairs[q, 0]] for q in ks]]).half()
            B = torch.from_numpy(Xr[[IDX[pairs[q, 1]] for q in ks]]).half()
            real.append(scores(net, A, B, "cuda"))
            ta, tb = [], []
            for q in ks:
                for t in range(NTWIN):
                    xa, _, xb, _ = twin(c, pairs[q, 0], pairs[q, 1], twin_rng(pairs[q, 0], pairs[q, 1], t), ho.bgs)
                    ta.append(xa); tb.append(xb)
            tw.append(scores(net, torch.from_numpy(np.stack(ta)).half(), torch.from_numpy(np.stack(tb)).half(), "cuda"))
        m6r, m6t = np.concatenate(real).astype(float), np.concatenate(tw).astype(float)
        snr = np.minimum(c["model_snr"][pairs[:, 0]], c["model_snr"][pairs[:, 1]])
        for name, v, w in [(b, sc[b][:npr], sc[b][npr:]) for b in sc] + [("m6", m6r, m6t)]:
            allR.setdefault(name, []).append(v)
            allT.setdefault(name, []).append(w.reshape(npr, NTWIN))
        meta.append((np.full(npr, k), snr, src[pairs[:, 0]], src[pairs[:, 1]]))
    fold = np.concatenate([m[0] for m in meta]); snr = np.concatenate([m[1] for m in meta])
    sa = np.concatenate([m[2] for m in meta]).astype(str); sb = np.concatenate([m[3] for m in meta]).astype(str)
    R = {k: np.concatenate(v) for k, v in allR.items()}
    T = {k: np.concatenate(v) for k, v in allT.items()}
    names = np.unique(np.concatenate([sa, sb]))
    ia, ib = np.searchsorted(names, sa), np.searchsorted(names, sb)
    br = np.random.default_rng(2026)
    boots = [np.bincount(br.integers(len(names), size=len(names)), minlength=len(names)) for _ in range(2000)]
    rep = [f"Stage 5 transfer on held-out fold sources (scheme all): {len(R['m6'])} real cross-source pairs "
           f"(<= {MAXPAIRS} per fold, seeded subset), {NTWIN} twins each, {len(names)} sources",
           f"criterion: real FPR <= {LIMIT:.0%} at the twins' {1 - FPR:.0%} quantile, threshold per fold, hits pooled; CI = source bootstrap"]
    for lab, sel in (("[10,25)", (snr >= SNR_MIN) & (snr < BRIGHT)), (">=25 (headline)", snr >= BRIGHT)):
        rep.append(f"\nbin {lab}: {sel.sum()} real pairs")
        for m in ["b1_blk16", "b2_blk16", "b3_gbm", "m6"]:
            hit = np.zeros(len(snr), bool)
            for k in range(K):
                q = sel & (fold == k)
                if q.any():
                    thr = np.quantile(T[m][q].ravel(), 1 - FPR)
                    hit[q] = R[m][q] > thr
            vals = []
            for w in boots:
                wt = (w[ia] * w[ib])[sel]
                if wt.sum() > 0:
                    vals.append((wt * hit[sel]).sum() / wt.sum())
            lo, hi = np.percentile(vals, [2.5, 97.5])
            rho = spearmanr(R[m][sel], T[m][sel].mean(1)).statistic
            ceil = spearmanr(T[m][sel][:, 0], T[m][sel][:, 1]).statistic
            f = hit[sel].mean()
            rep.append(f"  {m:9s} {f:.3f} [{lo:.3f}, {hi:.3f}]  {'PASS' if f <= LIMIT else 'FAIL'}   Spearman real~twin {rho:+.2f} / ceiling {ceil:+.2f}")
    txt = "\n".join(rep)
    print(txt)
    (OUT / "stage5_transfer.txt").write_text(txt + "\n")


if __name__ == "__main__":
    main()
