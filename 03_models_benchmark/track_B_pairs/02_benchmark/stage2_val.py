"""Stage 2 val comparison on val_bright: learned models vs b3_gbm, and the grouped-fold trigger. Plan 2026-11-06_1223.
Development numbers only; checkpoints were selected on this same set, so learned recalls are slightly optimistic.
Reads val_bright only. Output: outputs/stage2_val.txt
"""
import csv
from pathlib import Path

import numpy as np

from metrics import boot_recall, recall_at_fpr

HERE = Path(__file__).resolve().parent
TRAIN = HERE.parent / "01_training" / "outputs"
out = []


def say(s=""):
    print(s, flush=True)
    out.append(s)


d = np.load(HERE / "outputs" / "scores_val_bright.npz")
keep = d["y"] != 2  # primary task: lensed vs repeat + impostor
pos, src, snr, imp, y = (d["y"] == 0)[keep], d["src"][keep], d["snr"][keep], d["imp"][keep], d["y"][keep]
S = {"b3_gbm": d["b3_gbm"][keep]}
for m in (6, 5, 4, 7):
    for s in range(3):
        r = TRAIN / f"m{m}_s{s}"
        v = np.load(r / "val_bright_scores.npy")
        rows = list(csv.DictReader(open(r / "log.csv")))
        logged = max(float(x["val_recall"]) for x in rows)
        assert len(v) == keep.sum() and abs(recall_at_fpr(v[pos], v[~pos]) - logged) < 1e-9, r  # pair order matches
        S[f"m{m}_s{s}"] = v.astype(float)

say(f"val_bright, lensed vs repeat+impostor: {pos.sum()} pos, {(~pos).sum()} neg, {len(np.unique(src))} sources")
B = boot_recall(S, pos, src)
say(f"resamples used {len(B['b3_gbm'])}")
say("\nmethod    recall  [95% source bootstrap]  AUC")
from sklearn.metrics import roc_auc_score
for k, v in S.items():
    say(f"{k:9s} {recall_at_fpr(v[pos], v[~pos]):.3f}  [{np.percentile(B[k], 2.5):.3f}, {np.percentile(B[k], 97.5):.3f}]  {roc_auc_score(pos, v):.3f}")


def diff(m, ref="b3_gbm", seeds=range(3)):
    x = np.concatenate([B[f"m{m}_s{s}"] - (B[ref] if ref == "b3_gbm" else B[f"{ref}_s{s}"]) for s in seeds])
    return x.mean(), *np.percentile(x, [2.5, 97.5])


say("\npaired difference vs b3_gbm, pooled over seeds")
for m in (6, 5, 4, 7):
    a, lo, hi = diff(m)
    say(f"model {m}: {a:+.3f} [{lo:+.3f}, {hi:+.3f}]")
a, lo, hi = diff(6)
hw = (hi - lo) / 2
secs = [float(list(csv.DictReader(open(TRAIN / f"m6_s{s}" / "log.csv")))[-1]["seconds"]) for s in range(3)]
gpu_h = 5 * max(secs) / 3600
say(f"\ngrouped-fold trigger: half-width {hw:.3f} (> 0.10: {hw > 0.10}); 5 x slowest model-6 run = {gpu_h:.1f} GPU-h (<= 24: {gpu_h <= 24})")
say(f"TRIGGERED: {hw > 0.10 and gpu_h <= 24}")

say("\nmodel 6 vs model 5, seed-paired")
x = np.concatenate([B[f"m6_s{s}"] - B[f"m5_s{s}"] for s in range(3)])
say(f"{x.mean():+.3f} [{np.percentile(x, 2.5):+.3f}, {np.percentile(x, 97.5):+.3f}]")

say("\nrecall by S/N bin (threshold from all negatives)")
edges = [25, 40, 80, np.inf]
for k in ("b3_gbm", "m5_s0", "m6_s0", "m6_s1", "m6_s2"):
    v = S[k]
    t = np.quantile(v[~pos], 0.99)
    say(f"{k:9s} " + "  ".join(f"[{a:g},{b:g}) {(v[pos & (snr >= a) & (snr < b)] > t).mean():.3f} n={(pos & (snr >= a) & (snr < b)).sum()}" for a, b in zip(edges, edges[1:])))

say("\nnegatives above the 1% threshold, by type")
ty = np.where(y == 1, "repeat", np.char.add("imp:", imp))
for k in ("b3_gbm", "m6_s0", "m6_s1", "m6_s2"):
    v = S[k]
    fp = (v > np.quantile(v[~pos], 0.99)) & ~pos
    say(f"{k:9s} " + "  ".join(f"{t} {(fp & (ty == t)).sum()}/{(~pos & (ty == t)).sum()}" for t in np.unique(ty[~pos])))

(HERE / "outputs" / "stage2_val.txt").write_text("\n".join(out) + "\n")
