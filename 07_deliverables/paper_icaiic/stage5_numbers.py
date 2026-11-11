"""Stage 5 macros for the ICAIIC paper (numbers_stage5.tex), read from the Stage 5 outputs only. Missing -> red \\pending{}.
  - primary: 80-source grouped folds, OOF scores (fold_scores.npz, gbm_fK.npz), metric and bootstrap exactly as folds_oof.py;
  - paired OOF differences of model 6 against models 4, 5, 7 (ablations, F7 secondary), same resamples;
  - fixed-split secondaries (stage5_fixed_split.txt) and transfer on held-out folds (folds_all/stage5_transfer.txt).
Usage: python stage5_numbers.py"""
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TB = ROOT / "03_models_benchmark" / "track_B_pairs"
OUT = TB / "02_benchmark" / "outputs"
FOLDS = TB / "01_training" / "outputs" / "folds_all"
sys.path.insert(0, str(TB / "02_benchmark"))
from metrics import boot_recall, recall_at_fpr  # noqa: E402

K = 5


def ci(x):
    lo, hi = np.percentile(x, [2.5, 97.5])
    return lo, hi


def fmt_d(m, lo, hi):
    return f"{m:+.3f} [{lo:+.3f}, {hi:+.3f}]".replace("-", "$-$")


def main():
    from sklearn.metrics import roc_auc_score
    out = {}
    g = [np.load(OUT / "folds_all" / f"gbm_f{k}.npz") for k in range(K)]
    y = np.concatenate([d["y"] for d in g])
    src = np.concatenate([d["src"] for d in g])
    keep = y != 2
    pos = (y == 0)[keep]
    S = {"gbm": np.concatenate([d["b3_gbm"] for d in g])[keep]}
    for m in (6, 5, 4, 7):
        f = [FOLDS / f"m{m}_f{k}" / "fold_scores.npz" for k in range(K)]
        if all(p.exists() for p in f):
            parts = [np.load(p) for p in f]
            assert all((p["y"] == d["y"]).all() for p, d in zip(parts, g))
            S[f"m{m}"] = np.concatenate([p["score"].astype(float) for p in parts])[keep]
            out[f"OofCollapsedM{m}"] = str(sum(bool(p["collapsed"]) for p in parts))
    src = src[keep]
    B = boot_recall(S, pos, src)
    word = {6: "Six", 5: "Five", 4: "Four", 7: "Seven"}
    for k, v in S.items():
        r = recall_at_fpr(v[pos], v[~pos])
        lo, hi = ci(B[k])
        name = "GBM" if k == "gbm" else word[int(k[1])]
        out[f"Oof{name}"] = f"{r:.3f} [{lo:.3f}, {hi:.3f}]"
        out[f"OofAuc{name}"] = f"{roc_auc_score(pos, v):.3f}"
    if "m6" in S:
        d = B["m6"] - B["gbm"]
        out["OofDiff"] = fmt_d(d.mean(), *ci(d))
        for m in (5, 4, 7):
            if f"m{m}" in S:
                d = B["m6"] - B[f"m{m}"]
                out[f"OofSixMinus{word[m]}"] = fmt_d(d.mean(), *ci(d))
                d = B[f"m{m}"] - B["gbm"]
                out[f"Oof{word[m]}MinusGBM"] = fmt_d(d.mean(), *ci(d))
        fp = (S["m6"] > np.quantile(S["m6"][~pos], 0.99)) & ~pos
        imp = np.concatenate([d["imp"] for d in g])[keep]
        yy = y[keep]
        env = int((fp & np.isin(imp, ["I1", "I1+I2"])).sum())
        out["OofFPenv"] = f"{env} of {int(fp.sum())}"
        out["OofFPrepeat"] = str(int((fp & (yy == 1)).sum()))
    txt = (OUT / "folds_all" / "oof_primary_m6.txt").read_text() if (OUT / "folds_all" / "oof_primary_m6.txt").exists() else ""
    m = re.search(r"per-fold thresholds, recall pooled\s+b3_gbm\s+([0-9.]+)\s+m6\s+([0-9.]+)", txt)
    if m:
        out["OofPerFoldGBM"], out["OofPerFoldSix"] = m.groups()
    for key, name in (("b3_gbm", "GBM"), ("m6", "Six")):
        f = re.search(rf"^\s+{key}\s+f0 .*$", txt.split("per-fold recall")[1], re.M) if "per-fold recall" in txt else None
        if f:
            vals = [float(v) for v in re.findall(r"f\d ([0-9.]+) \[", f.group(0))]
            out[f"OofFoldRange{name}"] = f"{min(vals):.2f}--{max(vals):.2f}"
    # fixed split
    fs = (OUT / "stage5_fixed_split.txt").read_text()
    for set_, key in (("test_bright", "Tb"), ("test", "Te"), ("stress", "St")):
        blk = fs.split(f"\n{set_}: ")[1].split("\n\n")[0]
        rec = dict(re.findall(r"^\s+(\S+)\s+([0-9.]+) \[", blk, re.M))
        aucs = dict(re.findall(r"^\s+(\S+)\s+[0-9.]+ \[[0-9., ]+\]\s+([0-9.]+)", blk, re.M))
        dm = re.search(r"model 6 \(3 seeds\) - b3_gbm: ([+-][0-9.]+) \[([+-][0-9.]+), ([+-][0-9.]+)\]", blk)
        out[f"{key}Six"] = " / ".join(rec[f"m6_s{s}"] for s in range(3))
        out[f"{key}GBM"] = rec["b3_gbm"]
        g3 = re.search(r"^\s+b3_gbm\s+([0-9.]+ \[[0-9.]+, [0-9.]+\])", blk, re.M)
        out[f"{key}GBMci"] = g3.group(1)
        out[f"{key}Xcorr"], out[f"{key}Phys"] = rec["b1_blk16"], rec["b2_blk16"]
        out[f"{key}Diff"] = fmt_d(*(float(x) for x in dm.groups()))
        out[f"{key}AucSix"] = f"{min(float(aucs[f'm6_s{s}']) for s in range(3)):.3f}--{max(float(aucs[f'm6_s{s}']) for s in range(3)):.3f}"
        out[f"{key}AucGBM"] = aucs["b3_gbm"]
    rr = re.search(r"test_bright: .*?\n(.*?)\n\n", fs, re.S).group(1)
    frz = {k: (a, b) for k, a, b in re.findall(r"^\s+(\S+)\s+[0-9.]+ \[.*?\]\s+[0-9.]+\s+[0-9.]+\s+([0-9.]+) / ([0-9.]+)", rr, re.M)}
    fr = [float(frz[f"m6_s{s}"][1]) for s in range(3)]
    out["TbFrozenFPRSix"] = f"{100 * min(fr):.1f}--{100 * max(fr):.1f}" + r"\%"
    out["TbFrozenFPRGBM"] = f"{100 * float(frz['b3_gbm'][1]):.1f}" + r"\%"
    # transfer on held-out folds
    tr = (OUT / "folds_all" / "stage5_transfer.txt").read_text()
    out["SfiveTransferPairs"] = re.search(r"(\d+) real cross-source pairs", tr).group(1)
    hd = tr.split("(headline)")[1]
    m6 = re.search(r"m6\s+([0-9.]+) \[([0-9.]+), ([0-9.]+)\].*?real~twin \+([0-9.]+) / ceiling \+([0-9.]+)", hd)
    out["SfiveTransferSix"] = f"{100 * float(m6.group(1)):.1f}\\% [{100 * float(m6.group(2)):.1f}, {100 * float(m6.group(3)):.1f}]"
    out["SfiveTransferRho"] = f"{m6.group(4)} / {m6.group(5)}"
    gb = re.search(r"b3_gbm\s+([0-9.]+)", hd)
    out["SfiveTransferGBM"] = f"{100 * float(gb.group(1)):.1f}" + r"\%"
    out["SfiveTransferAll"] = "PASS" if "FAIL" not in tr else "FAIL"
    keys = ["OofSix", "OofGBM", "OofDiff", "OofFive", "OofFour", "OofSeven", "OofAucSix", "OofAucGBM", "OofAucFive",
            "OofAucFour", "OofAucSeven", "OofSixMinusFive", "OofSixMinusFour", "OofSixMinusSeven", "OofFiveMinusGBM",
            "OofFourMinusGBM", "OofSevenMinusGBM", "OofCollapsedMSeven", "OofFPenv", "OofFPrepeat", "OofPerFoldGBM",
            "OofPerFoldSix", "OofFoldRangeSix", "OofFoldRangeGBM", "TbSix", "TbGBM", "TbGBMci", "TbXcorr", "TbPhys", "TbDiff", "TbAucSix", "TbAucGBM", "TeSix", "TeGBM", "TeDiff",
            "StSix", "StGBM", "StDiff", "TbFrozenFPRSix", "TbFrozenFPRGBM", "SfiveTransferPairs", "SfiveTransferSix",
            "SfiveTransferRho", "SfiveTransferGBM"]
    out["OofCollapsedMSeven"] = out.get("OofCollapsedM7", r"\pending{m7}")
    lines = [f"\\newcommand{{\\{k}}}{{{out.get(k, rf'\pending{{{k}}}')}}}" for k in keys]
    (HERE / "numbers_stage5.tex").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
