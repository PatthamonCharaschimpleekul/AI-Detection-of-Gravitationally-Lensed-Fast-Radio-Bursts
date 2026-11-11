"""Stage 5 secondaries on the fixed split (plan 2026-11-06_1223 "Fixed before results"; addendum 0845 F8, last bullets).

Runs once on the frozen test, test_bright and stress sets (test-split sources, never used in training here):
  - baselines 1-2 (frozen grids) and the Stage 1 GBM (refitted, checked against the saved val_bright scores);
  - model 6, this machine's three seeds (Stage 2 recipe, checkpoints selected on val_bright before the test opened).
Pairs are regenerated in chunks and checked against the manifest hashes, so nothing is stored at full size.
Reports, task lensed vs repeat + impostor: recall at 1% FPR with source-bootstrap CI and the paired difference
model 6 - GBM (pooled over seeds as in plan 1223), AUC, recall at 0.1% FPR, per-S/N bins (test), the frozen val_bright
threshold's recall and realised FPR, and negatives above threshold by type.
Usage: python stage5_fixed_split.py      -> outputs/stage5_fixed_split.txt, outputs/stage5_fixed_split.npz
"""
import csv
import hashlib
import json
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "01_training"), str(HERE.parents[2] / "02_injection_labelling" / "01_injection")]
import baselines as BL  # noqa: E402
from inject import MAN, SETS, SNR_MIN, VERSION, gen_set, kind_of, load_pools  # noqa: E402
from metrics import boot_recall, recall_at_fpr, source_resamples  # noqa: E402

OUT = HERE / "outputs"
TRAIN = HERE.parent / "01_training" / "outputs"
DRY = "--dry" in sys.argv  # code check on the val set only (no test pair is generated)
NAMES = ("val",) if DRY else ("test_bright", "test", "stress")
BINS = ((10, 15), (15, 25), (25, 50), (50, np.inf))


def learned_scores(name, pools):
    """Model 6 seeds 0-2 on a frozen set, generated in chunks; asserts the manifest hash."""
    import torch
    from models import MODELS
    from train import scores
    nets = []
    for s in range(3):
        net = MODELS[6]().to("cuda")
        net.load_state_dict(torch.load(TRAIN / f"m6_s{s}" / "best.pt", map_location="cuda"))
        nets.append(net)
    split, n, seed, wide, floor = SETS[name]
    h = hashlib.sha256()
    out, A, Bx = [[] for _ in nets], [], []

    def flush():
        a, b = torch.from_numpy(np.stack(A)).half(), torch.from_numpy(np.stack(Bx)).half()
        for k, net in enumerate(nets):
            out[k].append(scores(net, a, b, "cuda"))
        A.clear(); Bx.clear()

    for i, xa, xb, ma, mb, y, _ in gen_set(pools[split], n, seed, wide, floor > SNR_MIN, floor):
        h.update(xa.tobytes()); h.update(xb.tobytes())
        A.append(xa); Bx.append(xb)
        if len(A) == 512:
            flush()
    if A:
        flush()
    exp = json.loads((MAN / f"{name}.json").read_text())
    assert exp.get("version") == VERSION and h.hexdigest() == exp["sha256"], f"{name}: regenerated set differs from its manifest"
    return {f"m6_s{k}": np.concatenate(v).astype(float) for k, v in enumerate(out)}


def auc(pos, neg):
    from sklearn.metrics import roc_auc_score
    return roc_auc_score(np.r_[np.ones(len(pos)), np.zeros(len(neg))], np.r_[pos, neg])


def main():
    tag = subprocess.run(["git", "tag", "-l", "benchmark-v1"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    assert tag == "benchmark-v1", "the test split opens only after the benchmark-v1 tag (plan 1223 Stage 5)"
    BL.init()
    data = {}
    with Pool(8, initializer=BL.init) as pool:
        gbm = BL.fit_gbm(pool)  # Stage 1 GBM, asserted against outputs/scores_val_bright.npz
        for name in NAMES:
            split, n, seed, wide, floor = SETS[name]
            d = BL.run(pool, [(split, kind_of(i, floor > SNR_MIN), [seed, i], wide, floor) for i in range(n)])
            man = list(csv.DictReader(open(MAN / f"{name}.csv")))
            assert [r["tmpl_a"] for r in man] == d["tmpl"].tolist() and np.allclose([float(r["snr_a"]) for r in man], d["snr_a"])
            d["sc"] = {m: d["s"][:, i] for i, m in enumerate(BL.METHODS)} | {"b3_gbm": gbm.predict_proba(d["f"])[:, 1]}
            data[name] = d
            print(f"{name}: baselines scored ({n} pairs)", flush=True)
    pools = load_pools()
    for name in NAMES:
        data[name]["sc"] |= learned_scores(name, pools)
        print(f"{name}: model 6 scored", flush=True)

    # frozen thresholds from val_bright (repeat + impostor, 99th percentile), fixed before the test opened
    vb = np.load(OUT / "scores_val_bright.npz")
    tv = vb["y"] != 2
    thr = {"b3_gbm": np.quantile(vb["b3_gbm"][tv & (vb["y"] != 0)], 0.99),
           "b1_blk16": np.quantile(vb["b1_blk16"][tv & (vb["y"] != 0)], 0.99),
           "b2_blk16": np.quantile(vb["b2_blk16"][tv & (vb["y"] != 0)], 0.99)}
    for s in range(3):
        v = np.load(TRAIN / f"m6_s{s}" / "val_bright_scores.npy")
        thr[f"m6_s{s}"] = np.quantile(v[vb["y"][tv] != 0], 0.99)

    rep, save = [], {}
    show = ["b1_blk16", "b2_blk16", "b3_gbm", "m6_s0", "m6_s1", "m6_s2"]
    for name in NAMES:
        d = data[name]
        t = d["y"] != 2
        pos, src, snr = d["y"][t] == 0, d["src"][t], d["snr"][t]
        S = {k: d["sc"][k][t] for k in show}
        B = boot_recall(S, pos, src)
        rep.append(f"\n{name}: {pos.sum()} lensed, {(~pos).sum()} repeat+impostor, {len(np.unique(src))} sources")
        rep.append(f"  {'method':9s} {'recall@1%':>9s} {'95% CI':>15s} {'AUC':>6s} {'rec@0.1%':>8s}   frozen val thr: recall / realised FPR")
        for k, v in S.items():
            lo, hi = np.percentile(B[k], [2.5, 97.5])
            rep.append(f"  {k:9s} {recall_at_fpr(v[pos], v[~pos]):9.3f} [{lo:.3f}, {hi:.3f}] {auc(v[pos], v[~pos]):6.3f} "
                       f"{recall_at_fpr(v[pos], v[~pos], 0.001):8.3f}   {(v[pos] > thr[k]).mean():.3f} / {(v[~pos] > thr[k]).mean():.4f}")
        d6 = np.concatenate([B[f"m6_s{s}"] - B["b3_gbm"] for s in range(3)])  # pooled 3B values (plan 1223)
        pt = np.mean([recall_at_fpr(S[f"m6_s{s}"][pos], S[f"m6_s{s}"][~pos]) for s in range(3)]) - recall_at_fpr(S["b3_gbm"][pos], S["b3_gbm"][~pos])
        lo, hi = np.percentile(d6, [2.5, 97.5])
        rep.append(f"  model 6 (3 seeds) - b3_gbm: {pt:+.3f} [{lo:+.3f}, {hi:+.3f}]  {'win (lower bound > 0)' if lo > 0 else 'no win'}")
        if name in ("test", "val"):
            rep.append("  per-S/N recall at 1% FPR (bin-wise threshold): " + "  ".join(f"[{a},{b})" for a, b in BINS))
            for k, v in S.items():
                cells = []
                for a, b in BINS:
                    q = (snr >= a) & (snr < b)
                    cells.append(f"{recall_at_fpr(v[q & pos], v[q & ~pos]):.3f}")
                rep.append(f"    {k:9s} " + "  ".join(cells) + f"   (lensed per bin: {' / '.join(str(int(((snr >= a) & (snr < b) & pos).sum())) for a, b in BINS)})")
        imp = d["imp"][t]
        ty = np.where(d["y"][t] == 1, "repeat", np.char.add("imp:", imp.astype(str)))
        for k in ("b3_gbm", "m6_s0"):
            v = S[k]
            fp = (v > np.quantile(v[~pos], 0.99)) & ~pos
            rep.append(f"  negatives above the 1% threshold, {k}: " + "  ".join(f"{u} {(fp & (ty == u)).sum()}/{(~pos & (ty == u)).sum()}" for u in np.unique(ty[~pos])))
        for k, v in S.items():
            save[f"{name}|{k}"] = v
        save[f"{name}|y"], save[f"{name}|src"], save[f"{name}|snr"] = d["y"][t], src, snr
    txt = "Stage 5 secondaries on the fixed split (opened at benchmark-v1; one run)\n" + "\n".join(rep)
    print(txt)
    (OUT / "stage5_fixed_split.txt").write_text(txt + "\n")
    np.savez(OUT / "stage5_fixed_split.npz", **save)


if __name__ == "__main__":
    main()
