"""Scattering sweep for the baselines (b1_blk16, b2_blk16, b3_gbm): the same pairs as tau_sweep.py (seed [61, i], val,
floor 25, tau600 forced on one member), each at its own val_bright operating threshold. Val only.
Usage: python -I tau_sweep_base.py      -> outputs/tau_sweep_base.txt
"""
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "01_training"), str(HERE.parents[2] / "02_injection_labelling" / "01_injection")]
from inject import BRIGHT
import baselines as BL
import stage3_transfer as S3
from metrics import FPR
from tau_sweep import N, TAUS


def main():
    thr = {k: np.quantile(v, 1 - FPR) for k, v in S3.operating_negatives([]).items()}
    out = [f"baseline sweep: {N} val lensed pairs per value (same pairs as tau_sweep.py), recall at the val_bright operating threshold"]
    with Pool(16, initializer=BL.init) as pool:
        gbm = BL.fit_gbm(pool)
        base = None
        for t in TAUS:
            d = BL.run(pool, [("val", "lensed", [61, i], False, BRIGHT, False, t) for i in range(N)])
            sc = {k: d["s"][:, BL.METHODS.index(k)] for k in S3.BASE} | {"b3_gbm": gbm.predict_proba(d["f"])[:, 1]}
            rec = {k: (v > thr[k]).mean() for k, v in sc.items()}
            base = rec if base is None else base
            out.append(f"  tau600 {t:5.1f} ms  " + "  ".join(f"{k} {rec[k]:.3f} ({rec[k] / max(base[k], 1e-9):.2f})" for k in rec))
            print(out[-1], flush=True)
    (HERE / "outputs" / "tau_sweep_base.txt").write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
