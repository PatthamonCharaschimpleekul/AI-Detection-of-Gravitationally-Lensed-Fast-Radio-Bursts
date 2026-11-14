"""Fig. 5 of the ICAIIC paper: the MNRAS figure (../paper/make_figures.py, fig_transit) with the dashed line labelled as
Eq. (4) and headroom above p_align = 1 so no point touches the frame. Same inputs, same computation.
Usage: python make_transit_icaiic.py -> fig_transit.pdf here (found before ../paper/ through \\graphicspath)."""
import importlib.util
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("mnras_figs", HERE.parent / "paper" / "make_figures.py")
mf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mf)  # sets the shared rcParams (serif, Type 42 fonts, recessive axes)

tc, rep = mf.rows(mf.TC / "track_c_sources.csv"), {r["source"]: r for r in mf.rows(mf.POP / "repeaters.csv")}
assert tc, "track_c_sources.csv missing"
dec = np.array([float(rep[r["source"]]["dec"]) for r in tc])
p = np.array([float(r["p_align"]) for r in tc])
fig, ax = plt.subplots(figsize=(3.3, 2.4))
d = np.linspace(-10, 89, 300)
w = np.minimum(2 * 1.1 / (15 * np.cos(np.radians(d))), 24) / 23.934  # one window, share of a sidereal day
ax.plot(d, np.minimum(2 * w * np.where(d > 70, 2, 1), 1), color=mf.INK2, lw=1.2, ls="--",
        label=r"Eq. (4): $2W(\delta)/T_{\rm sid}$")
ax.scatter(dec, p, s=14, color=mf.BLUE, edgecolor="white", linewidth=0.6, zorder=3, label=f"{len(p)} repeaters (simulated)")
ax.set_yscale("log")
lo = min(p.min(), 1e-2)
ax.set_ylim(lo / 1.6, 1.6)
ax.set_xlabel("Declination (deg)")
ax.set_ylabel(r"$p_{\rm align}$ (share of lenses)")
ax.legend(frameon=False, loc="upper left", fontsize=7)
fig.tight_layout()
fig.savefig(HERE / "fig_transit.pdf")
print("wrote", HERE / "fig_transit.pdf", len(p), "sources")
