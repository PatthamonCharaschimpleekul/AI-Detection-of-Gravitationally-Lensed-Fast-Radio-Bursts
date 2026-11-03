"""Print structure, resolution and shape of CHIME/FRB Catalog 1 waterfall files.

Usage: python -I inspect_waterfalls.py data/waterfalls/*.h5
"""
import sys

import h5py


def show(name, obj):
    if isinstance(obj, h5py.Dataset):
        print(f"  {name}: shape={obj.shape} dtype={obj.dtype}")
    for k, v in obj.attrs.items():
        print(f"    @{k} = {v}")


import numpy as np

verbose = "-v" in sys.argv
for path in [a for a in sys.argv[1:] if a != "-v"]:
    with h5py.File(path, "r") as f:
        if verbose:
            print(path)
            f.visititems(show)
        g = f["frb"]
        t, nu = g["plot_time"][:], g["plot_freq"][:]
        wf, cal = g["wfall"][:], g["calibrated_wfall"][:]
        print(
            f"{g.attrs['tns_name'].decode()}: DM={g.attrs['dm']:.1f}"
            f" | wfall {wf.shape} dt={np.median(np.diff(t)) * 1e3:.4f} ms window={(t[-1] - t[0]) * 1e3:.1f} ms"
            f" | nu {nu.min():.2f}-{nu.max():.2f} MHz dnu={abs(np.median(np.diff(nu))) * 1e3:.2f} kHz"
            f" | NaN chans {np.isnan(wf).all(axis=1).mean():.0%}"
            f" | calibrated {cal.shape} extent={np.round(g['extent'][:], 3)}"
        )
