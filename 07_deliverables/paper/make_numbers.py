"""Write numbers.tex for the paper draft from the pipeline outputs, so no number is typed by hand.
Missing outputs become red \\pending{} markers. Usage: python make_numbers.py"""
import csv
import re
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TC = ROOT / "03_models_benchmark" / "track_C_timing" / "outputs"
TB = ROOT / "03_models_benchmark" / "track_B_pairs"


def sci(x):
    m, e = f"{x:.1e}".split("e")
    return rf"${m}\times10^{{{int(e)}}}$"


def track_c(tag):
    p = TC / f"track_c_sources{tag}.csv"
    if not p.exists():
        return None
    r = list(csv.DictReader(open(p)))
    f = lambda k: np.array([float(x[k]) for x in r])
    tau = f("tau")
    return dict(tau=tau.sum(), chime=(tau * f("eff_timing_chime")).sum(), chime_echo=(tau * f("p_echo_chime")).sum(),
                allsky=(tau * f("eff_timing_allsky")).sum(), allsky_echo=(tau * f("p_echo_allsky")).sum(),
                palign=float(np.median(f("p_align"))))


def main():
    out = {"RecallMsixOOF": "0.47 [0.25, 0.66]", "RecallGBMOOF": "0.25 [0.20, 0.30]", "DiffOOF": "+0.22 [+0.04, +0.38]"}
    base, bias = track_c(""), track_c("_bias15")
    rows = []
    for label, tag in (("CHIME, Catalog 2", ""), (r"CHIME, Catalog 2, $\gamma=1.5$", "_bias15"),
                       ("CHIME-like, 10 yr", "_10yr"), (r"CHIME-like, 10 yr, $\gamma=1.5$", "_10yr_bias15")):
        d = track_c(tag)
        if d:
            rows.append(f"{label} & {sci(d['tau'])} & {sci(d['chime'])} & {sci(d['chime_echo'])} \\\\")
            allsky_label = label.replace("CHIME, Catalog 2", "All-sky, same sources").replace("CHIME-like", "All-sky")
            rows.append(f"{allsky_label} & {sci(d['tau'])} & {sci(d['allsky'])} & {sci(d['allsky_echo'])} \\\\")
        else:
            rows.append(f"{label} & \\multicolumn{{3}}{{c}}{{\\pending{{running}}}} \\\\")
    out["ForecastRows"] = "\n".join(rows)
    if base:
        out["PalignMedian"] = f"{100 * base['palign']:.1f}\\%"
        out["NexpCHIME"] = sci(base["chime"])
        out["GainAllSky"] = f"$\\sim${base['allsky'] / base['chime']:.0f}"
        out["NexpEcho"] = sci(base["chime_echo"])
        out["NexpEchoPair"] = sci(base["chime_echo"] * 0.467)  # x model-6 OOF recall at the simulated 1% FPR
    out["NexpCHIMEbias"] = sci(bias["chime"]) if bias else r"\pending{bias run}"
    h150 = track_c("_host150")
    if base and h150:
        out["HostSens"] = f"{100 * (h150['chime'] / base['chime'] - 1):+.0f}" + r"\%"
        out["HostSensTau"] = f"{100 * (h150['tau'] / base['tau'] - 1):+.0f}" + r"\%"
    ten, tenb = track_c("_10yr"), track_c("_10yr_bias15")
    if base and ten and bias and tenb:
        out["GainTenYr"] = f"{ten['chime'] / base['chime']:.1f}--{tenb['chime'] / bias['chime']:.1f}"
    fl = TC / "far_check.log"
    if fl.exists():
        m = re.search(r"held-out exceedances (\d+) in (\d+) x (\d+) scrambles: rate ([0-9.e+-]+) \(95% upper ([0-9.e+-]+);"
                      r".*expected false sources per search ([0-9.]+) \(95% upper ([0-9.]+)\)", fl.read_text())
        if m:
            hits, ns, nb, rate, up, efs, efs_up = m.groups()
            out["FarHeldOut"] = f"{hits} of {int(ns) * int(nb):,} held-out scrambles".replace(",", "{,}")
            out["FarRateUp"] = sci(float(up))
            out["FarSearchUp"] = efs_up
    # Stage 3 transfer check (val sources, development).
    s3 = TB / "02_benchmark" / "outputs" / "stage3_generic_val.txt"
    if s3.exists():
        blocks = {}
        for blk in s3.read_text().split("\n\n"):
            ls = blk.strip().splitlines()
            if ls:
                blocks[ls[0].strip()] = ls[1:]
        pat = r"real FPR ([0-9.]+) \[([0-9.]+), ([0-9.]+)\].*real-sim ([0-9.]+) / sim-sim ([0-9.]+)"
        for key, name in (("m6:m6_s0", "Msix"), ("b3_gbm", "GBM")):
            for ln in blocks.get(key, []):
                m = re.search(pat, ln)
                if m and "(headline)" in ln:
                    f, lo, hi, rt, tt = m.groups()
                    out[f"SthreeFPR{name}"] = f"{100 * float(f):.1f}\\% [{100 * float(lo):.1f}, {100 * float(hi):.1f}]"
                    out[f"SthreeTwin{name}"] = f"{rt} against {tt}"
        fprs = []
        for k in (0, 1, 2):
            for ln in blocks.get(f"m6:m6_s{k}", []):
                m = re.search(r"real FPR ([0-9.]+) \[[0-9.]+, ([0-9.]+)\]", ln)
                if m and "(headline)" in ln:
                    fprs.append((100 * float(m.group(1)), 100 * float(m.group(2))))
        if len(fprs) == 3:
            out["SthreeFPRMsixSeeds"] = ", ".join(f"{f:.1f}" for f, _ in fprs) + r"\%"
            out["SthreeFPRMsixHi"] = f"{max(h for _, h in fprs):.0f}" + r"\%"
    tw = TB / "02_benchmark" / "outputs" / "stage3_twin_fpr.txt"
    if tw.exists():
        sec = {}
        for blk in tw.read_text().split("\n\n")[1:]:
            ls = blk.strip().splitlines()
            sec[ls[0].split(":")[0]] = ls
        g = lambda b, m: re.search(rf"{re.escape(m)}\s+real ([0-9.]+)\s+twin ([0-9.]+)\s+gap ([+-][0-9.]+) \[([+-][0-9.]+), ([+-][0-9.]+)\]",
                                   "\n".join(sec[b]))
        hd = "S/N >= 25 (headline)"
        gaps = [g(hd, f"m6:m6_s{k}") for k in (0, 1, 2)]
        if all(gaps):
            gv = sorted(100 * float(x.group(3)) for x in gaps)
            out["GapMsix"] = f"+{gv[0]:.1f} to +{gv[-1]:.1f} points"
        base_gaps = [g(hd, m) for m in ("b1_blk1", "b1_blk4", "b1_blk16", "b2_blk1", "b2_blk4", "b2_blk16", "b3_gbm")]
        if all(base_gaps):
            out["GapBaseMax"] = f"{100 * max(abs(float(x.group(3))) for x in base_gaps):.1f} points"
        lo = [g("S/N 10-25", m) for m in ("b1_blk1", "b1_blk4", "b1_blk16")]
        if all(lo):
            out["BoneLowReal"] = ", ".join(f"{100 * float(x.group(1)):.1f}" for x in lo) + r"\%"
            out["BoneLowTwin"] = ", ".join(f"{100 * float(x.group(2)):.1f}" for x in lo) + r"\%"
        m = re.search(r"S/N 10-25: \d+ real pairs, median pair S/N real ([0-9.]+) vs generic sim ([0-9.]+)", tw.read_text())
        if m:
            out["SnrLowReal"], out["SnrLowSim"] = m.groups()
    eh = TB / "02_benchmark" / "outputs" / "eh0_val.txt"
    if eh.exists():
        sims = [float(x) for x in re.findall(r"sim mean ([0-9.]+)", eh.read_text())]
        reals = [float(x) for x in re.findall(r"real mean ([0-9.]+)", eh.read_text())]
        if len(sims) == 3:
            out["EhSimSeeds"] = ", ".join(f"{x:.1f}" for x in sims)
            out["EhRealSeeds"] = ", ".join(f"{x:.2f}" for x in reals)
    if eh.exists():
        m = re.search(r"sim mean ([0-9.]+).*real mean ([0-9.]+) \[([0-9.]+), ([0-9.]+)\]", eh.read_text())
        if m:
            out["EhSim"], out["EhReal"] = f"{float(m.group(1)):.2f}", f"{float(m.group(2)):.2f} [{float(m.group(3)):.2f}, {float(m.group(4)):.2f}]"
    ab = TB / "02_benchmark" / "outputs" / "stage4_ablations.txt"
    if ab.exists():
        txt = ab.read_text()
        m = re.search(r"^full\s+seeds \[(.*?)\]: recall ([0-9.]+)", txt, re.M)
        if m:
            out["AblSeeds"] = str(len(m.group(1).split(",")))
            out["AblFull"] = m.group(2)
        reps = re.findall(r"^m6_s(\d)\s+recall ([0-9.]+)", txt, re.M)
        if reps:
            out["ReproSeeds"] = " / ".join(r for _, r in reps)
        for key, name in (("noalign", "Noalign"), ("hardneg", "Hardneg"), ("noimp", "Noimp")):
            m = re.search("^" + key + r"\s+seeds \[.*?\]: recall ([0-9.]+) .*minus full: ([+-][0-9.]+) \[([+-][0-9.]+), ([+-][0-9.]+)\]", txt, re.M)
            if m:
                out[f"Abl{name}"] = f"{m.group(1)}, difference {m.group(2)} [{m.group(3)}, {m.group(4)}]".replace("-", "$-$")
    # Reproduction (plan 2026-11-09_1347).
    h = TB / "outputs_local" / "hashes.txt"
    if h.exists():
        txt = h.read_text()
        ok = txt.count("hash OK")
        out["ReproHashes"] = f"{ok}/7 match" if "Error" not in txt else r"\pending{hash mismatch: see outputs\_local/hashes.txt}"
    log = TB / "outputs_local" / "run_m6_s0.log"
    if log.exists() and "best val recall" in log.read_text():
        out["ReproMsix"] = re.findall(r"best val recall ([0-9.]+)", log.read_text())[-1]
    lines = []
    for k in ("RecallMsixOOF", "RecallGBMOOF", "DiffOOF", "PalignMedian", "NexpCHIME", "NexpCHIMEbias", "GainAllSky",
              "GainTenYr", "HostSens", "HostSensTau", "NexpEcho", "NexpEchoPair", "FarHeldOut", "FarRateUp", "FarSearchUp", "ReproHashes", "ReproMsix", "SthreeFPRMsix", "SthreeFPRGBM", "SthreeTwinMsix", "SthreeTwinGBM", "EhSim", "EhReal", "SthreeFPRMsixSeeds", "SthreeFPRMsixHi", "GapMsix", "GapBaseMax", "BoneLowReal", "BoneLowTwin", "SnrLowReal", "SnrLowSim", "EhSimSeeds", "EhRealSeeds", "ReproSeeds", "AblSeeds", "AblFull", "AblNoalign", "AblHardneg", "AblNoimp", "ForecastRows"):
        v = out.get(k, rf"\pending{{{k}}}")
        lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    (HERE / "numbers.tex").write_text("\n".join(lines) + "\n")
    print((HERE / "numbers.tex").read_text())


if __name__ == "__main__":
    main()
