"""Second-machine reproduction of the team's Stage 3 (stage3_transfer.py, with fill_window) and real-burst lensed test
(realburst.py), restricted to the model 6 checkpoints trained on this machine (m6_s0..2). The team's code is used
unchanged; only its checkpoint list is narrowed, because models 4, 5 and 7 were not retrained here.
Also reruns the team's Stage 1 baselines (baselines.py) first if outputs/scores_val_bright.npz is missing, because
Stage 3 asserts its GBM refit against it. Worker pools are capped at 8 processes (RAM on this machine); results do not
depend on the pool size.
Usage: python repro_upstream_m6.py [baselines|stage3|realburst|both]"""
import multiprocessing
import sys
from pathlib import Path

import baselines
import stage3_transfer

POOL = 8


def capped_pool(n=None, *a, **k):
    return multiprocessing.Pool(min(n or POOL, POOL), *a, **k)


for mod in (baselines, stage3_transfer):
    if hasattr(mod, "Pool"):
        mod.Pool = capped_pool

stage3_transfer.CKPTS = [(6, s) for s in range(3)]

if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "both"
    if what == "baselines" or not (Path(baselines.OUT) / "scores_val_bright.npz").exists():
        baselines.main()
    if what in ("stage3", "both"):
        stage3_transfer.main()
    if what in ("realburst", "both"):
        import realburst
        if hasattr(realburst, "Pool"):
            realburst.Pool = capped_pool
        realburst.CKPTS = stage3_transfer.CKPTS
        realburst.main()
