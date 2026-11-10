"""Does the template energy deficit explain the Stage 3 twin gaps? (development diagnostic, val sources only)

Per burst: deficit = 1 - s^2 / E_on, where s is the template's matched-filter S/N in the data (inject.build_cache) and
E_on = sum over good on-pulse cells of (x^2 - 1), the data's on-pulse signal energy in noise units.
Per real cross-source pair (true negatives, as in transfer_check.py): pair deficit = mean of its two members.
Tests, per method, in the S/N bins of Stage 3:
  - level: Spearman(pair deficit, real score - twin score). Positive = real pairs score higher than their twins
    the more energy the templates miss (the b1 level shift).
  - scatter: Spearman(pair deficit, |rank(real) - rank(twin)|). Positive = the twin gap grows with the deficit.
Reads outputs/stage3_generic_scores.npz and rebuilds the pair list exactly as transfer_check.py does.
"""
import sys
from pathlib import Path

import h5py
import numpy as np
from scipy.stats import rankdata, spearmanr

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "01_training"), str(HERE.parents[2] / "02_injection_labelling" / "01_injection")]
from inject import CACHE, REAL  # noqa: E402
import baselines  # noqa: E402

OUT = HERE / "outputs"


def deficits():
    with h5py.File(REAL / "preproc" / "repeaters_256x160.h5") as f:
        X, FM, TM = f["X"][:], f["freq_mask"][:], f["time_mask"][:]
        lo, hi = f["meta/extent_lo"][:], f["meta/extent_hi"][:]
    with h5py.File(CACHE) as f:
        s = f["model_snr"][:]
    cols = np.arange(X.shape[2])
    box = (cols[None] >= lo[:, None]) & (cols[None] <= hi[:, None]) & (TM > 0)
    good = (FM >= 0.25)[:, :, None] & box[:, None, :]
    e_on = (np.where(good, X.astype(float) ** 2 - 1.0, 0.0)).sum((1, 2))
    return 1.0 - s ** 2 / np.where(e_on > 0, e_on, np.nan)


def main():
    d = deficits()
    baselines.init()
    P = baselines.POOLS["val"]
    c = P.c
    R = np.sort(np.concatenate(list(P.tmpl.values())))
    pairs = np.array([(int(i), int(j)) for k, i in enumerate(R) for j in R[k + 1:] if c["source"][i] != c["source"][j]])
    z = np.load(OUT / "stage3_generic_scores.npz", allow_pickle=True)
    assert len(pairs) == len(z["r_smin"]) and (c["source"][pairs[:, 0]] == z["src_a"]).all(), "pair order differs"
    print(f"burst deficit over {np.isfinite(d[R]).sum()} val templates: median {np.nanmedian(d[R]):.2f} "
          f"(IQR {np.nanpercentile(d[R], 25):.2f}-{np.nanpercentile(d[R], 75):.2f}); all eligible {np.nanmedian(d[c['eligible']]):.2f}")
    pd = d[pairs].mean(1)
    lines = []
    methods = [m[len("real|"):] for m in z.files if m.startswith("real|") and not m.endswith("|LvU")]
    for lo, hi, lab in ((10, 25, "S/N 10-25"), (25, np.inf, "S/N >= 25")):
        sel = (z["r_smin"] >= lo) & (z["r_smin"] < hi) & np.isfinite(pd)
        for m in methods:
            r, t = z[f"real|{m}"][sel], z[f"twin1|{m}"][sel]
            lev = spearmanr(pd[sel], r - t).statistic
            sc = spearmanr(pd[sel], np.abs(rankdata(r) - rankdata(t))).statistic
            lines.append(f"{lab:10s} {m:14s} n {sel.sum():5d}  level rho {lev:+.3f}  scatter rho {sc:+.3f}")
    txt = "\n".join(lines)
    print(txt)
    (OUT / "deficit_twin.txt").write_text(txt + "\n")


if __name__ == "__main__":
    main()
