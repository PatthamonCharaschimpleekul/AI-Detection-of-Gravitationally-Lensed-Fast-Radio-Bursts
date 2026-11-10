"""Example pairs of the four classes from the frozen val_bright set (validation sources only), for the ICAIIC paper.
Usage: python make_examples.py -> fig_examples.pdf"""
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "02_injection_labelling" / "01_injection"))
from inject import load_set  # noqa: E402

MAN = ROOT / "02_injection_labelling" / "01_injection" / "manifests" / "val_bright.csv"
INK2 = "#52514e"


def main():
    rows = list(csv.DictReader(open(MAN)))
    XA, XB, MA, MB, Y = load_set("val_bright")
    smin = np.array([min(float(r["snr_a"]), float(r["snr_b"])) for r in rows])
    imp = np.array([r["imp_type"] for r in rows])
    picks = []
    for lab, name, extra in ((0, "lensed", None), (1, "repeat", None), (3, "impostor (I1)", "I1"), (2, "unrelated", None)):
        ok = (Y == lab) & (smin >= 40) & (smin <= 80)
        if extra:
            ok &= imp == extra
        picks.append((name, int(np.flatnonzero(ok)[0])))
    fig, axes = plt.subplots(2, 4, figsize=(7.0, 2.9), sharex=True, sharey=True)
    for c, (name, i) in enumerate(picks):
        for r, (X, M) in enumerate(((XA, MA), (XB, MB))):
            img = np.where(M[i][:, None] if M[i].ndim == 1 else M[i], X[i], np.nan)
            ax = axes[r, c]
            ax.imshow(np.arcsinh(img), aspect="auto", origin="lower", cmap="Greys", vmin=-1, vmax=np.nanpercentile(np.arcsinh(X[i]), 99.8),
                      extent=(0, 160 * 0.983, 400, 800), interpolation="nearest")
            ax.tick_params(colors=INK2, labelsize=6, length=2)
            if r == 0:
                ax.set_title(f"{name}\nmin S/N {smin[i]:.0f}", fontsize=7)
        axes[0, 0].set_ylabel("A: freq. (MHz)", fontsize=6.5)
        axes[1, 0].set_ylabel("B: freq. (MHz)", fontsize=6.5)
    for ax in axes[1]:
        ax.set_xlabel("time (ms)", fontsize=6.5)
    fig.tight_layout(pad=0.3, w_pad=0.4, h_pad=0.4)
    fig.savefig(HERE / "fig_examples.pdf", dpi=300)
    print("pairs:", picks)


if __name__ == "__main__":
    main()
