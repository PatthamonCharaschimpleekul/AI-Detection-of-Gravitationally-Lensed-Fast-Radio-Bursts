"""Summarise CHIME/FRB Catalog 2 dynamic spectra: shape, resolution, window, usable channels.

Usage: python -I inspect_catalog2.py data/catalog2/dynamic_spectra   (a folder, or .h5 files)
Prints one line per file, then the ranges over all files.
"""
import sys
from pathlib import Path

import h5py
import numpy as np

rows = []
paths = [q for a in map(Path, sys.argv[1:]) for q in (sorted(a.glob("*.h5")) if a.is_dir() else [a])]
for path in paths:
    with h5py.File(path, "r") as f:
        t = f["index_map/times"][:]
        nu = f["index_map/freqs"][:]
        good = f["good_freq"][:]
        valid = f["flag"][:]
        rows.append((
            path.name.split("_")[0],
            f["data"].shape,
            np.median(np.diff(t)) * 1e3,
            (t[-1] - t[0]) * 1e3,
            nu.min(), nu.max(),
            good.mean(),
            valid[good].mean() if good.any() else 0.0,
            f.attrs["dm_incoherent"],
        ))

for name, shape, dt, win, lo, hi, g, v, dm in rows:
    print(f"{name}: {shape} dt={dt:.4f} ms window={win:.1f} ms nu={lo:.1f}-{hi:.1f} MHz "
          f"good_freq={g:.0%} valid_in_good={v:.0%} DM={dm:.1f}")

if rows:
    a = np.array([(r[2], r[3], r[6], r[7]) for r in rows])
    shapes = {r[1] for r in rows}
    print(f"\n{len(rows)} files | shapes {sorted(shapes)} | dt {a[:, 0].min():.4f}-{a[:, 0].max():.4f} ms | "
          f"window {a[:, 1].min():.0f}-{a[:, 1].max():.0f} ms | good_freq {a[:, 2].min():.0%}-{a[:, 2].max():.0%} "
          f"(median {np.median(a[:, 2]):.0%})")
