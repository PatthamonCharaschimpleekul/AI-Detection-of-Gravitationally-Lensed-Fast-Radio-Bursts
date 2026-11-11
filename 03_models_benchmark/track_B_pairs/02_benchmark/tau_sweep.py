"""Scattering sensitivity of model 6 before the 04_propagation sign-off (plan 2026-11-11_1300). Val only, no test file read.
1 frozen val_bright: lensed recall by injected tau600 bin (threshold = usual val_bright operating threshold).
2 sweep: new val lensed pairs, floor 25, tau600 forced on one member to 0 ... 30 ms; every other draw identical per i.
Usage: python -I tau_sweep.py      -> outputs/tau_sweep.txt
"""
import csv
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "01_training"), str(HERE.parents[2] / "02_injection_labelling" / "01_injection")]
from inject import BRIGHT, MAN, load_pools, load_set, make_pair
import stage3_transfer as S3
from metrics import FPR

RUNS = sys.argv[sys.argv.index("--runs") + 1].split(",") if "--runs" in sys.argv else [f"m6_s{s}" for s in range(3)]
TAUS = [0.0, 0.3, 1.0, 3.0, 10.0, 30.0]
N = 2000
out = []


def say(s=""):
    print(s, flush=True)
    out.append(s)


def main():
    thr = {r: np.quantile(v, 1 - FPR) for r, v in S3.operating_negatives(RUNS).items()}
    # ---- 1. frozen val_bright by tau bin ----
    vb = np.load(HERE / "outputs" / "scores_val_bright.npz")
    man = list(csv.DictReader(open(MAN / "val_bright.csv")))
    assert [int(m["label"]) for m in man] == list(vb["y"]), "manifest and score order differ"
    keep = vb["y"] != 2
    tau = np.array([float(m["tau600"]) for m in man])[keep]
    lens = vb["y"][keep] == 0
    say("1. frozen val_bright, lensed recall at the operating threshold by injected tau600 (ms, one member); model 6 seeds 0/1/2")
    for lo, hi in ((0, 0), (0.01, 0.1), (0.1, 0.3), (0.3, 1.0)):
        sel = lens & ((tau == 0) if hi == 0 else (tau >= lo) & (tau < hi))
        rec = [(np.load(HERE.parent / "01_training" / "outputs" / r / "val_bright_scores.npy")[sel[: len(sel)]] > thr[r]).mean()
               for r in RUNS]
        name = "none" if hi == 0 else f"[{lo}, {hi})"
        say(f"  tau {name:12s} n={sel.sum():4d}  recall " + " / ".join(f"{x:.3f}" for x in rec) + f"  mean {np.mean(rec):.3f}")

    # ---- 2. forced-tau sweep on val lensed pairs ----
    P = load_pools()["val"]
    load_set("val_bright")  # asserts the frozen hash with the new tau_force argument in place (default None)

    def getter(t):
        def g(ks):
            A, B = [], []
            for i in ks:
                xa, xb, *_ = make_pair("lensed", np.random.default_rng([61, i]), P, False, BRIGHT, tau_force=t)
                A.append(xa); B.append(xb)
            return np.stack(A), np.stack(B)
        return g

    say(f"\n2. sweep: {N} new val lensed pairs per value, floor S/N {BRIGHT:.0f}, tau600 forced on one member, same draws otherwise")
    base = None
    for t in TAUS:
        sc = S3.learned_scores(getter(t), N, RUNS)
        rec = np.array([(sc[r] > thr[r]).mean() for r in RUNS])
        base = rec if base is None else base
        say(f"  tau600 {t:5.1f} ms (1 GHz {t * 0.6 ** 4.4:6.3f} ms)  recall " + " / ".join(f"{x:.3f}" for x in rec)
            + f"  mean {rec.mean():.3f}  ratio to tau 0: {(rec / base).mean():.2f}")
    (HERE / "outputs" / ("tau_sweep_" + RUNS[0].split("_", 2)[-1] + ".txt" if "--runs" in sys.argv else "tau_sweep.txt")).write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
