"""Recall at 1% FPR (lensed vs repeat + impostor) by pair minimum S/N on the frozen val set (validation sources).
Baselines from the team's Stage 1 scores (outputs/scores_val.npz, rerun on this machine); model 6 = this machine's three
seeds, scored here. Usage: python make_snr_curve.py -> fig_snr.pdf, snr_curve.txt"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TB = ROOT / "03_models_benchmark" / "track_B_pairs"
sys.path[:0] = [str(TB / "01_training"), str(TB / "02_benchmark"), str(ROOT / "02_injection_labelling" / "01_injection")]
from inject import load_set  # noqa: E402
from metrics import recall_at_fpr  # noqa: E402
from models import MODELS  # noqa: E402
from train import scores  # noqa: E402

BINS = [(10, 15), (15, 25), (25, 50), (50, np.inf)]
BLUE, INK, INK2, GRID = "#2a78d6", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.size": 8})


def main():
    d = np.load(TB / "02_benchmark" / "outputs" / "scores_val.npz")
    A, Bx, _, _, Y = load_set("val")
    assert (Y == d["y"]).all(), "pair order differs from the Stage 1 scores"
    smin = d["snr"].min(1) if d["snr"].ndim == 2 else d["snr"]
    keep = Y != 2
    S = {"Cross-corr. (16)": d["b1_blk16"], "Physics fit (16)": d["b2_blk16"], "Feature GBM": d["b3_gbm"]}
    At, Bt = torch.from_numpy(A).half(), torch.from_numpy(Bx).half()
    m6 = []
    for s in range(3):
        net = MODELS[6]().to("cuda")
        net.load_state_dict(torch.load(TB / "01_training" / "outputs" / f"m6_s{s}" / "best.pt", map_location="cuda"))
        m6.append(scores(net, At, Bt, "cuda"))
    lines, curves = [], {}
    for name, v in list(S.items()) + [(f"Model 6 s{s}", m6[s]) for s in range(3)]:
        r = []
        for lo, hi in BINS:
            sel = keep & (smin >= lo) & (smin < hi)
            pos = Y[sel] == 0
            r.append(recall_at_fpr(v[sel][pos], v[sel][~pos]))
        curves[name] = r
        if name.startswith("Cross"):
            lines.append("pairs per bin (pos/neg): " + "  ".join(
                f"{int(((Y == 0) & keep & (smin >= lo) & (smin < hi)).sum())}/{int(((Y != 0) & keep & (smin >= lo) & (smin < hi)).sum())}"
                for lo, hi in BINS))
        lines.append(f"{name:18s} " + "  ".join(f"{x:.3f}" for x in r))
    txt = "bins " + " ".join(f"[{lo},{hi})" for lo, hi in BINS) + "\n" + "\n".join(lines)
    print(txt)
    (HERE / "snr_curve.txt").write_text(txt + "\n")
    x = np.arange(len(BINS))
    fig, ax = plt.subplots(figsize=(3.4, 2.5))
    greys = ["#b9b8b3", "#85847f", INK]
    for (name, v), c in zip(S.items(), greys):
        ax.plot(x, curves[name], "-o", color=c, lw=1.6, ms=4, mec="white", mew=0.8, label=name)
    m = np.array([curves[f"Model 6 s{s}"] for s in range(3)])
    ax.fill_between(x, m.min(0), m.max(0), color=BLUE, alpha=0.18, lw=0)
    ax.plot(x, m.mean(0), "-o", color=BLUE, lw=2, ms=4.5, mec="white", mew=0.8, label="Model 6 (3 seeds)")
    ax.set_xticks(x, ["10–15", "15–25", "25–50", "≥50"])
    ax.set_xlabel("Pair minimum S/N")
    ax.set_ylabel("Recall at 1% FPR")
    ax.set_ylim(0, 1)
    for k in ("top", "right"):
        ax.spines[k].set_visible(False)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK2, labelsize=7)
    ax.legend(frameon=False, fontsize=6.5, ncol=2, loc="lower center", bbox_to_anchor=(0.5, 1.0), columnspacing=1.0)
    fig.tight_layout()
    fig.savefig(HERE / "fig_snr.pdf")


if __name__ == "__main__":
    main()
