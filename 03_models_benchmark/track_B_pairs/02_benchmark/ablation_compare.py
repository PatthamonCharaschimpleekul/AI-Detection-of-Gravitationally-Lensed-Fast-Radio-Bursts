"""Stage 4 ablations on val_bright: recall at 1% FPR (lensed vs repeat + impostor) for each ablation and its paired
difference from the full model of the same seed, with the shared source bootstrap of metrics.py.
With several seeds, the seed-mean difference is bootstrapped on the same source resamples for every run.
Checkpoints were selected on this set, so all recalls are slightly optimistic, equally.
Reads the val_bright manifest (labels, sources) and saved scores only. Output: outputs/stage4_ablations.txt
Usage: python ablation_compare.py [--seeds 0 1 2]
"""
import argparse
import csv
from pathlib import Path

import numpy as np

from metrics import boot_recall, recall_at_fpr

HERE = Path(__file__).resolve().parent
TRAIN = HERE.parent / "01_training" / "outputs"
MAN = HERE.parents[2] / "02_injection_labelling" / "01_injection" / "manifests" / "val_bright.csv"
TAGS = ("", "_noalign", "_hardneg", "_noimp")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="*", default=[0, 1, 2])
    a = ap.parse_args()
    rows = list(csv.DictReader(open(MAN)))
    y = np.array([int(r["label"]) for r in rows])
    keep = y != 2
    src = np.array([r["src_a"] for r in rows])[keep]
    imp = np.array([r["imp_type"] for r in rows])[keep]
    pos = y[keep] == 0
    S = {}
    for s in a.seeds:
        for t in TAGS:
            f = TRAIN / f"m6_s{s}{t}" / "val_bright_scores.npy"
            if f.exists():
                S[(s, t)] = np.load(f).astype(float)
                assert len(S[(s, t)]) == keep.sum(), f
    B = boot_recall({f"{s}{t}": v for (s, t), v in S.items()}, pos, src)
    rec = {k: recall_at_fpr(v[pos], v[~pos]) for k, v in S.items()}
    out = [f"val_bright, lensed vs repeat+impostor: {pos.sum()} pos, {(~pos).sum()} neg, {len(np.unique(src))} sources"]
    for (s, t), v in S.items():
        th = np.quantile(v[~pos], 0.99)
        fp = (~pos) & (v > th)
        kinds = ", ".join(f"{k or 'repeat'}:{int((fp & (imp == k)).sum())}" for k in sorted(set(imp[~pos])))
        out.append(f"m6_s{s}{t:9s} recall {rec[(s, t)]:.3f}  FP by type {kinds}")
    out.append("\nseed-mean recall and paired difference from the full model (same seeds, same resamples)")
    for t in TAGS:
        seeds = [s for s in a.seeds if (s, t) in S and (s, "") in S]
        if not seeds:
            continue
        m = np.mean([rec[(s, t)] for s in seeds])
        mb = np.mean([B[f"{s}{t}"] for s in seeds], 0)
        lo, hi = np.quantile(mb, [0.025, 0.975])
        line = f"{'full' if not t else t[1:]:8s} seeds {seeds}: recall {m:.3f} [{lo:.3f}, {hi:.3f}]"
        if t:
            d = np.mean([B[f"{s}{t}"] - B[f"{s}"] for s in seeds], 0)
            dm = np.mean([rec[(s, t)] - rec[(s, "")] for s in seeds])
            line += f"  minus full: {dm:+.3f} [{np.quantile(d, 0.025):+.3f}, {np.quantile(d, 0.975):+.3f}]"
            line += "  per seed " + " ".join(f"{rec[(s, t)] - rec[(s, '')]:+.3f}" for s in seeds)
        out.append(line)
    txt = "\n".join(out)
    print(txt)
    (HERE / "outputs" / "stage4_ablations.txt").write_text(txt + "\n")


if __name__ == "__main__":
    main()
