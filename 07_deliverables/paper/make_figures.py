"""Figures for the paper draft, from pipeline outputs. Usage: python make_figures.py -> fig_*.pdf
Palette: reference categorical slots 1-2 (blue, orange), recessive grey axes and text."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TC = ROOT / "03_models_benchmark" / "track_C_timing" / "outputs"
POP = ROOT / "01_semi_synthetic_data" / "02_population" / "outputs"
BLUE, ORANGE, INK, INK2, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.size": 8, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                     # Type 42 (TrueType) fonts and the paper's serif face: IEEE PDF checks reject Type 3 fonts
                     "pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "serif",
                     "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"], "mathtext.fontset": "stix"})


def rows(path):
    return list(csv.DictReader(open(path))) if path.exists() else []


def fig_transit():
    tc, rep = rows(TC / "track_c_sources.csv"), {r["source"]: r for r in rows(POP / "repeaters.csv")}
    if not tc:
        return
    dec = np.array([float(rep[r["source"]]["dec"]) for r in tc])
    p = np.array([float(r["p_align"]) for r in tc])
    fig, ax = plt.subplots(figsize=(3.3, 2.4))
    d = np.linspace(-10, 89, 300)
    w = np.minimum(2 * 1.1 / (15 * np.cos(np.radians(d))), 24) / 23.934  # one window, share of a sidereal day
    ax.plot(d, np.minimum(2 * w * np.where(d > 70, 2, 1), 1), color=INK2, lw=1.2, ls="--", label="two windows' width / day")
    ax.scatter(dec, p, s=14, color=BLUE, edgecolor="white", linewidth=0.6, zorder=3, label="83 repeaters (simulated)")
    ax.set_yscale("log")
    ax.set_xlabel("Declination (deg)")
    ax.set_ylabel(r"$p_{\rm align}$ (share of lenses)")
    ax.legend(frameon=False, loc="upper left", fontsize=7)
    fig.tight_layout()
    fig.savefig(HERE / "fig_transit.pdf")


def fig_trackb():
    items = [("Model 6, fixed split", 0.394, 0.226, 0.542), ("Model 6, grouped folds", 0.220, 0.035, 0.381),
             ("Model 5, fixed split", 0.244, 0.024, 0.436), ("Model 4, fixed split", 0.131, -0.003, 0.266)]
    fig, ax = plt.subplots(figsize=(3.4, 1.9))
    y = np.arange(len(items))[::-1]
    for yi, (lab, m, lo, hi) in zip(y, items):
        ax.plot([lo, hi], [yi, yi], color=BLUE, lw=2, solid_capstyle="round")
        ax.scatter([m], [yi], s=28, color=BLUE, edgecolor="white", linewidth=1.2, zorder=3)
        ax.text(hi + 0.02, yi, f"{m:+.2f}", va="center", color=INK, fontsize=7)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(y, [i[0] for i in items])
    ax.set_xlabel("Recall gain over the GBM")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(-0.1, 0.72)
    fig.tight_layout()
    fig.savefig(HERE / "fig_trackb.pdf")


def fig_forecast():
    labels, chime, sky = [], [], []
    for lab, tag in (("Cat. 2", ""), ("Cat. 2, bias", "_bias15"), ("10 yr", "_10yr"), ("10 yr, bias", "_10yr_bias15")):
        r = rows(TC / f"track_c_sources{tag}.csv")
        if not r:
            continue
        tau = np.array([float(x["tau"]) for x in r])
        labels.append(lab)
        chime.append((tau * np.array([float(x["eff_timing_chime"]) for x in r])).sum())
        sky.append((tau * np.array([float(x["eff_timing_allsky"]) for x in r])).sum())
    if not labels:
        return
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(3.3, 2.2))
    ax.bar(x - 0.19, chime, 0.36, color=BLUE, label="CHIME transit", edgecolor="white", linewidth=1)
    ax.bar(x + 0.19, sky, 0.36, color=ORANGE, label="All-sky monitor", edgecolor="white", linewidth=1)
    ax.set_yscale("log")
    ax.set_xticks(x, labels)
    ax.set_ylabel(r"$N_{\rm exp}$ (timing detection)")
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(HERE / "fig_forecast.pdf")


def fig_stage3():
    import re
    p = ROOT / "03_models_benchmark" / "track_B_pairs" / "02_benchmark" / "outputs" / "stage3_val.txt"
    if not p.exists():
        return
    blocks = {}
    for blk in p.read_text().split("\n\n"):
        ls = blk.strip().splitlines()
        if ls:
            blocks[ls[0].strip()] = ls[1:]
    methods = [("b1_blk4", "Cross-corr."), ("b2_blk4", "Physics fit"), ("b3_gbm", "GBM"), ("m6:m6_s0", "Model 6")]
    bins = [("S/N 10-25 ", "10-25"), ("S/N 25-50 ", "25-50"), ("S/N 50-inf ", r"$\geq$50"), ("(headline)", r"$\geq$25 (main)")]
    fig, ax = plt.subplots(figsize=(3.4, 2.9))
    shades = ["#b9b8b3", "#85847f", INK, BLUE]
    for k, (key, lab) in enumerate(methods):
        for j, (tag, _) in enumerate(bins):
            ln = next((l for l in blocks.get(key, []) if tag in l and "overlap" not in l), None)
            m = re.search(r"real FPR ([0-9.]+) \[([0-9.]+), ([0-9.]+)\]", ln or "")
            if not m:
                continue
            f, lo, hi = (100 * float(v) for v in m.groups())
            y = j + (k - 1.5) * 0.18
            ax.plot([lo, hi], [y, y], color=shades[k], lw=1.6, solid_capstyle="round")
            ax.scatter([f], [y], s=18, color=shades[k], edgecolor="white", linewidth=0.8, zorder=3,
                       label=lab if j == 0 else None)
    ax.axvline(2, color=ORANGE, lw=1, ls="--")
    ax.text(2.25, -0.62, "2% limit", color=INK2, fontsize=7, va="center")
    ax.set_yticks(range(len(bins)), [b[1] for b in bins])
    ax.set_ylim(3.45, -0.8)
    ax.set_xlabel("Real FPR at simulated 1% threshold (%)")
    ax.set_ylabel("Pair min S/N")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(-0.3, 13)
    ax.legend(frameon=False, fontsize=6.5, ncol=2, loc="lower center", bbox_to_anchor=(0.4, 1.03),
              handletextpad=0.2, columnspacing=0.8)
    fig.tight_layout()
    fig.savefig(HERE / "fig_stage3.pdf")


if __name__ == "__main__":
    fig_stage3()
    fig_transit()
    fig_trackb()
    fig_forecast()
    print("figures:", sorted(p.name for p in HERE.glob("fig_*.pdf")))
