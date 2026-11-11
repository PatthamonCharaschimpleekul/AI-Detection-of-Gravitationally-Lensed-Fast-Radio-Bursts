"""Stage 5 (plan 2026-11-08_0845 F5/F8): baselines 1-2 and the per-fold GBM on scheme 'all' held-out fold sets.

baselines.run_fold refuses scheme 'all' before Stage 5 by design. This wrapper repeats its body line for line for
scheme 'all' (same jobs, seeds, manifest assertion, GBM recipe and output file), without editing the team's file, and
only after the benchmark-v1 tag exists. Pools are capped at 8 processes for RAM; results do not depend on pool size.
Usage: python stage5_fold_baselines.py K      -> outputs/folds_all/gbm_fK.npz
"""
import csv
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import baselines as BL  # noqa: E402
from baselines import BRIGHT, FOLD_N, FOLD_SETS, MAN, METHODS, OUT, gbm_jobs, init, kind_of, run  # noqa: E402
from metrics import recall_at_fpr  # noqa: E402

SCHEME = "all"


def main(k):
    tag = subprocess.run(["git", "tag", "-l", "benchmark-v1"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    assert tag == "benchmark-v1", "scheme 'all' opens the test sources: only after the benchmark-v1 tag (plan 0845 F8)"
    from sklearn.ensemble import HistGradientBoostingClassifier
    with Pool(8, initializer=init, initargs=((SCHEME, k),)) as pool:
        tr = run(pool, gbm_jobs("tr", 500 + 2 * k))
        d = run(pool, [("ho", kind_of(i, True), [FOLD_SETS[SCHEME] + k, i], False, BRIGHT) for i in range(FOLD_N)])
    man = list(csv.DictReader(open(MAN / f"{SCHEME}_f{k}_bright.csv")))  # these jobs must be the frozen fold set
    assert [r["tmpl_a"] for r in man] == d["tmpl"].tolist() and np.allclose([float(r["snr_a"]) for r in man], d["snr_a"])
    gbm = HistGradientBoostingClassifier(random_state=0).fit(tr["f"], tr["y"] == 0)
    sc = {m: d["s"][:, i] for i, m in enumerate(METHODS)} | {"b3_gbm": gbm.predict_proba(d["f"])[:, 1]}
    (OUT / f"folds_{SCHEME}").mkdir(parents=True, exist_ok=True)
    np.savez(OUT / f"folds_{SCHEME}" / f"gbm_f{k}.npz", y=d["y"], src=d["src"], snr=d["snr"], imp=d["imp"], **sc)
    t = d["y"] != 2
    v, pos = sc["b3_gbm"][t], d["y"][t] == 0
    print(f"fold {k}: b3_gbm held-out recall {recall_at_fpr(v[pos], v[~pos]):.3f}", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]))
