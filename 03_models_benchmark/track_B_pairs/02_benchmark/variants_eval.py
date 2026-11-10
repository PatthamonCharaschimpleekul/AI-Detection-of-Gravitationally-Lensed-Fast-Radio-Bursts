"""Evaluate the source-memorisation variants M, P, M+P of model 6 against the current model 6
(plan 2026-11-10_1300, decision rule fixed there). Development: val split only, no test file read.
Usage: python -I variants_eval.py      -> outputs/variants.txt
"""
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "01_training"), str(HERE.parents[2] / "02_injection_labelling" / "01_injection")]
from inject import BRIGHT, SNR_MIN, load_pools
import baselines as BL
import fitcheck as FC
import realburst as RB
import stage3_transfer as S3
from metrics import FPR, boot_recall, recall_at_fpr

OUT = HERE / "outputs"
TRN = HERE.parent / "01_training" / "outputs"
VARIANTS = {"current": "", "M": "_M", "P": "_P", "M+P": "_MP"}
if "--dry" in sys.argv:  # pipeline check before the runs exist: every variant points at the current model 6
    VARIANTS = {v: "" for v in VARIANTS}
RUNS = {v: [f"m6_s{s}{t}" for s in range(3)] for v, t in VARIANTS.items()}
ALL = list(dict.fromkeys(r for v in RUNS.values() for r in v))
out = []


def say(s=""):
    print(s, flush=True)
    out.append(s)


def main():
    # ---- 1. val_bright recall, paired differences (P-GBM fitted here as the fair comparator for P) ----
    vb = np.load(OUT / "scores_val_bright.npz")
    keep = vb["y"] != 2
    pos, src = (vb["y"] == 0)[keep], vb["src"][keep]
    with Pool(16, initializer=BL.init) as pool:
        pg = BL.fit_gbm(pool, bandpass=True)
        f = BL.frozen(pool, "val_bright")["f"]
    S = {r: np.load(TRN / r / "val_bright_scores.npy").astype(float) for r in ALL}
    S["b3_gbm"], S["p_gbm"] = vb["b3_gbm"][keep], pg.predict_proba(f)[:, 1][keep]
    B = boot_recall(S, pos, src)
    pt = {k: recall_at_fpr(v[pos], v[~pos]) for k, v in S.items()}
    gbm = max(("b3_gbm", "p_gbm"), key=pt.get)
    say(f"1. val_bright recall at 1% FPR (lensed vs repeat+impostor); GBM comparator = {gbm} "
        f"(b3 {pt['b3_gbm']:.3f}, bandpass-trained {pt['p_gbm']:.3f})")
    pooled = {}
    for v, rs in RUNS.items():
        pooled[v] = np.mean([pt[r] for r in rs])
        line = f"  {v:8s} seeds " + " / ".join(f"{pt[r]:.3f}" for r in rs) + f"  mean {pooled[v]:.3f}"
        dg = np.concatenate([B[r] - B[gbm] for r in rs])
        line += f"   vs GBM {dg.mean():+.3f} [{np.percentile(dg, 2.5):+.3f}, {np.percentile(dg, 97.5):+.3f}]"
        if v != "current":
            dc = np.concatenate([B[r] - B[c] for r, c in zip(rs, RUNS["current"])])
            line += f"   vs current {dc.mean():+.3f} [{np.percentile(dc, 2.5):+.3f}, {np.percentile(dc, 97.5):+.3f}]"
        say(line)

    # ---- 2. memorisation gap ----
    pools = load_pools()
    (TA, TB, TY), (VA, VB, VY) = FC.seen_unseen_sets(pools)
    say("\n2. seen (train_bright_chk) vs unseen (val_bright): recall, CE, and val repeat->unrelated rate")
    gap = {}
    for v, rs in RUNS.items():
        g = []
        for r in rs:
            net = FC.load_net(TRN / r / "best.pt", 6)
            pv = FC.probs(net, VA, VB)
            a, b = FC.metrics(FC.probs(net, TA, TB), TY), FC.metrics(pv, VY)
            ru = (pv.argmax(1)[VY == 1] == 2).mean()
            g.append(a[3] - b[3])
            say(f"  {r:10s} recall {a[3]:.3f}/{b[3]:.3f} gap {a[3] - b[3]:+.3f}   CE {a[0]:.3f}/{b[0]:.3f}   repeat->unrelated {ru:.3f}")
        gap[v] = np.mean(g)
    del TA, TB, VA, VB

    # ---- 3. Stage 3 transfer, headline bin, per seed ----
    _, c, files, IDX, X, M = S3.load_real()
    srcs = c["source"]
    pairs = np.array([(i, j) for a, i in enumerate(files) for j in files[a + 1:] if srcs[i] != srcs[j]])
    snr = np.minimum(c["model_snr"][pairs[:, 0]], c["model_snr"][pairs[:, 1]])
    sel = np.flatnonzero(snr >= BRIGHT)
    pairs = pairs[sel]
    sv = pools["val"]
    real = S3.learned_scores(lambda ks: (X[[IDX[pairs[k, 0]] for k in ks]], X[[IDX[pairs[k, 1]] for k in ks]]), len(pairs), ALL)

    def twin_get(ks):
        A, Bb = [], []
        for k in ks:
            p, t = divmod(k, S3.NTWIN)
            xa, _, xb, _ = S3.twin(c, pairs[p, 0], pairs[p, 1], S3.twin_rng(pairs[p, 0], pairs[p, 1], t), sv.bgs)
            A.append(xa); Bb.append(xb)
        return np.stack(A), np.stack(Bb)
    tw = S3.learned_scores(twin_get, len(pairs) * S3.NTWIN, ALL)
    say(f"\n3. Stage 3 headline bin ({len(pairs)} real cross-source val pairs, filled windows): real FPR at the twins' 99th pct (limit {S3.LIMIT:.0%})")
    s3ok = {}
    for v, rs in RUNS.items():
        f_ = [(real[r] > np.quantile(tw[r], 1 - FPR)).mean() for r in rs]
        s3ok[v] = all(x <= S3.LIMIT for x in f_)
        say(f"  {v:8s} " + " / ".join(f"{x:.3f}" for x in f_) + f"  {'pass' if s3ok[v] else 'FAIL'}")

    # ---- 4. real-burst lensed test, val bursts, S/N 25 ----
    rpools, rc, rfiles, cuts = RB.load()
    jobs = [j for j in RB.jobs_for(rc, rfiles) if rc["file_split"][j[0]] == "val" and j[1] == 25.0
            and (j[3] != "noise" or cuts[j[0]]["noise"] is not None)]
    ver = np.array([j[3] for j in jobs])

    def get(ks):
        A, Bb = [], []
        for q in ks:
            xa, _, xb, _ = RB.make(jobs[q], rpools, rc, cuts)
            A.append(xa); Bb.append(xb)
        return np.stack(A), np.stack(Bb)
    rb = S3.learned_scores(get, len(jobs), ALL)
    thr = {r: np.quantile(v, 1 - FPR) for r, v in S3.operating_negatives(ALL).items()}
    say(f"\n4. real-burst lensed test (val bursts, S/N 25, {len(jobs) // 3} pairs per version): recall real / template / noise, ratio")
    ratio = {}
    for v, rs in RUNS.items():
        h = {w: np.mean([(rb[r][ver == w] > thr[r]).mean() for r in rs]) for w in RB.VERSIONS}
        ratio[v] = h["real"] / max(h["template"], 1e-9)
        say(f"  {v:8s} {h['real']:.3f} / {h['template']:.3f} / {h['noise']:.3f}   ratio {ratio[v]:.2f}")

    # ---- decision (plan 2026-11-10_1300) ----
    say("\ndecision rule: (a) pooled gain >= +0.03 over current, (b) seen-unseen gap below current's, (c) Stage 3 pass, (d) ratio >= 0.8")
    ok = []
    for v in ("M", "P", "M+P"):
        cr = [pooled[v] - pooled["current"] >= 0.03, gap[v] < gap["current"], s3ok[v], ratio[v] >= 0.8]
        say(f"  {v:4s} gain {pooled[v] - pooled['current']:+.3f}  gap {gap[v]:+.3f} (current {gap['current']:+.3f})  "
            f"stage3 {s3ok[v]}  ratio {ratio[v]:.2f}  ->  {'ELIGIBLE' if all(cr) else 'no'} {cr}")
        if all(cr):
            ok.append(v)
    say(f"ADOPT: {max(ok, key=pooled.get) if ok else 'none (current model 6 stays; report as negative ablation)'}")
    (OUT / ("variants_dry.txt" if "--dry" in sys.argv else "variants.txt")).write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
