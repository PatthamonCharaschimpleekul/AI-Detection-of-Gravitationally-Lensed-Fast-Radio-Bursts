"""Primary metric and source bootstrap, fixed in plan 2026-11-06_1223 ("Agreed 2026-11-06")."""
import numpy as np

FPR, B_BOOT, BOOT_SEED = 0.01, 2000, 2026


def recall_at_fpr(pos, neg, fpr=FPR):
    """ROC point: threshold = (1 - fpr) quantile of negatives, recall = share of positives strictly above it."""
    return float((pos > np.quantile(neg, 1 - fpr)).mean())


def source_resamples(src, B=B_BOOT, seed=BOOT_SEED):
    """B resamples of sources with replacement, as index arrays. One list shared by all methods and seeds."""
    names = np.unique(src)
    rows = {s: np.flatnonzero(src == s) for s in names}
    rng = np.random.default_rng(seed)
    for _ in range(B):
        yield np.concatenate([rows[s] for s in rng.choice(names, len(names))])


def boot_recall(scores, pos, src):
    """scores: {method: array over pairs}; pos: bool lensed; pairs of other kinds must be filtered out first.
    Returns {method: B recalls}, all on the same resamples, thresholds recomputed inside each resample."""
    out = {k: [] for k in scores}
    for ix in source_resamples(src):
        p = pos[ix]
        if p.all() or not p.any():
            continue
        for k, v in scores.items():
            out[k].append(recall_at_fpr(v[ix][p], v[ix][~p]))
    return {k: np.array(v) for k, v in out.items()}


if __name__ == "__main__":  # self-check on separable and shuffled scores
    r = np.random.default_rng(0)
    y = np.arange(4000) % 2 == 0
    assert recall_at_fpr(np.ones(100), np.zeros(1000)) == 1.0
    s = r.normal(size=4000)
    assert abs(recall_at_fpr(s[y], s[~y]) - FPR) < 0.01
    src = np.array([f"s{i // 2 % 10}" for i in range(4000)])  # every source holds both classes
    b = boot_recall({"perfect": y * 1.0 + r.normal(0, 1e-3, 4000), "noise": s}, y, src)
    assert b["perfect"].min() == 1.0 and abs(np.median(b["noise"]) - FPR) < 0.01 and len(b["noise"]) == B_BOOT
    print("metrics self-check OK")
