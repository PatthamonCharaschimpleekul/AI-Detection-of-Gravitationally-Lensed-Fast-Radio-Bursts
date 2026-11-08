"""Grouped-fold primary (plan 2026-11-08_0845, F7): out-of-fold recall at 1% FPR, model 6 vs b3_gbm.
Usage: python -I folds_oof.py [--scheme dev] [--models 6]     -> outputs/folds_<scheme>/oof.txt
Reads only the held-out fold-set scores written by train.py --fold and baselines.py --fold.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I drops the script folder from the path
from metrics import FPR, boot_recall, recall_at_fpr

HERE = Path(__file__).resolve().parent
a = sys.argv
SCHEME = a[a.index("--scheme") + 1] if "--scheme" in a else "dev"
MODELS = [int(m) for m in a[a.index("--models") + 1].split(",")] if "--models" in a else [6]
OUT = HERE / "outputs" / f"folds_{SCHEME}"
TRAIN = HERE.parent / "01_training" / "outputs" / f"folds_{SCHEME}"
K = 5
out = []


def say(s=""):
    print(s, flush=True)
    out.append(s)


def per_fold_threshold_recall(v, pos, fold):
    """Secondary: each fold model gets its own 99th-percentile threshold; recall pooled over all lensed pairs."""
    hit = np.zeros(len(v), bool)
    for k in np.unique(fold):
        f = fold == k
        hit[f] = v[f] > np.quantile(v[f & ~pos], 1 - FPR)
    return float(hit[pos].mean())


# self-check: identical score scales -> both thresholds agree; one fold shifted up -> pooled loses recall, per-fold does not
r = np.random.default_rng(0)
_p, _f = np.arange(20000) % 2 == 0, np.arange(20000) // 2 % 4
_v = np.where(_p, 2.5, 0.0) + r.normal(size=20000)
assert abs(per_fold_threshold_recall(_v, _p, _f) - recall_at_fpr(_v[_p], _v[~_p])) < 0.02
_w = _v + 3.0 * (_f == 0)
assert per_fold_threshold_recall(_w, _p, _f) > recall_at_fpr(_w[_p], _w[~_p]) + 0.05

g = [np.load(OUT / f"gbm_f{k}.npz") for k in range(K)]
y = np.concatenate([d["y"] for d in g])
src = np.concatenate([d["src"] for d in g])
imp = np.concatenate([d["imp"] for d in g])
fold = np.concatenate([np.full(len(d["y"]), k) for k, d in enumerate(g)])
assert all(not set(g[i]["src"]) & set(g[j]["src"]) for i in range(K) for j in range(i + 1, K)), "a source sits in two folds"
S, collapsed, secs = {"b3_gbm": np.concatenate([d["b3_gbm"] for d in g])}, {}, {}
for m in MODELS:
    parts = []
    for k in range(K):
        d = np.load(TRAIN / f"m{m}_f{k}" / "fold_scores.npz")
        assert (d["y"] == g[k]["y"]).all() and (d["src"] == g[k]["src"]).all(), f"m{m} fold {k}: pair order differs from the GBM file"
        parts.append(d["score"].astype(float))
        collapsed[(m, k)], secs[(m, k)] = bool(d["collapsed"]), float(d["seconds"])
    S[f"m{m}"] = np.concatenate(parts)

keep = y != 2  # primary task: lensed vs repeat + impostor
pos, src, imp, y, fold = (y == 0)[keep], src[keep], imp[keep], y[keep], fold[keep]
S = {k: v[keep] for k, v in S.items()}
say(f"scheme {SCHEME}: {K} folds, {len(np.unique(src))} sources, {pos.sum()} lensed, {(~pos).sum()} negatives (OOF, pooled)")
for (m, k), c in collapsed.items():
    say(f"  m{m} fold {k}: {secs[(m, k)] / 3600:.2f} h{'  COLLAPSED (F6)' if c else ''}")

B = boot_recall(S, pos, src)
say(f"\nprimary: recall at {FPR:.0%} FPR, pooled threshold, source bootstrap ({len(B['b3_gbm'])} resamples)")
for k, v in S.items():
    say(f"  {k:7s} {recall_at_fpr(v[pos], v[~pos]):.3f} [{np.percentile(B[k], 2.5):.3f}, {np.percentile(B[k], 97.5):.3f}]")
for m in MODELS:
    dd = B[f"m{m}"] - B["b3_gbm"]
    lo, hi = np.percentile(dd, [2.5, 97.5])
    say(f"  m{m} - b3_gbm: {dd.mean():+.3f} [{lo:+.3f}, {hi:+.3f}]  half-width {(hi - lo) / 2:.3f}  "
        f"{'win (lower bound > 0)' if lo > 0 else 'no win'}")

say("\nsecondary: per-fold thresholds, recall pooled")
for k, v in S.items():
    say(f"  {k:7s} {per_fold_threshold_recall(v, pos, fold):.3f}")

say("\nsecondary: per-fold recall [source bootstrap within the fold]")
for k, v in S.items():
    cells = []
    for f in range(K):
        q = fold == f
        b = boot_recall({k: v[q]}, pos[q], src[q])[k]
        cells.append(f"f{f} {recall_at_fpr(v[q & pos], v[q & ~pos]):.3f} [{np.percentile(b, 2.5):.2f},{np.percentile(b, 97.5):.2f}]")
    say(f"  {k:7s} " + "  ".join(cells))

say("\nnegatives above the pooled 1% threshold, by type")
ty = np.where(y == 1, "repeat", np.char.add("imp:", imp.astype(str)))
for k, v in S.items():
    fp = (v > np.quantile(v[~pos], 1 - FPR)) & ~pos
    say(f"  {k:7s} " + "  ".join(f"{t} {(fp & (ty == t)).sum()}/{(~pos & (ty == t)).sum()}" for t in np.unique(ty[~pos])))

(OUT / "oof.txt").write_text("\n".join(out) + "\n")
