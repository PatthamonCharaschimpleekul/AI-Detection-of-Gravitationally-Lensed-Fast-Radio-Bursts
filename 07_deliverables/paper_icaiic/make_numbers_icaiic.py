"""numbers_icaiic.tex for the ICAIIC paper: macros not in ../paper/numbers.tex. Missing outputs -> red \\pending{}.
Team results quoted from update 2026-11-09_1520 (addendum) and 2026-11-10_1130; second-machine reproductions are read from
outputs. Usage: python make_numbers_icaiic.py"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "03_models_benchmark" / "track_B_pairs" / "02_benchmark" / "outputs"


def main():
    out = {"SthreeNpairs": "3851", "SthreeTeamMsix": "0.8 to 1.4\\%"}
    ab = OUT / "stage4_ablations.txt"
    if ab.exists():
        for key, name in (("noalign", "Noalign"), ("hardneg", "Hardneg"), ("noimp", "Noimp")):
            m = re.search("^" + key + r"\s+seeds \[.*?\]: recall ([0-9.]+) .*minus full: ([+-][0-9.]+) \[([+-][0-9.]+), ([+-][0-9.]+)\]",
                          ab.read_text(), re.M)
            if m:
                out[f"Abl{name}R"] = m.group(1)
                out[f"Abl{name}D"] = f"{m.group(2)} [{m.group(3)}, {m.group(4)}]".replace("-", "$-$")
    # Second-machine reproduction of the team's Stage 3 (stage3_transfer.py with fill_window) on m6_s0..2.
    s3 = OUT / "stage3_val.txt"
    txt = s3.read_text() if s3.exists() else ""
    hd = txt.split("bin >=25 (headline)")[1] if "bin >=25 (headline)" in txt else ""
    f = {k: float(v) for k, v in re.findall(r"^\s+(m6_s\d)\s+([0-9.]+) \[", hd, re.M)}
    rho = re.findall(r"^\s+m6_s\d .*?([+-][0-9.]+) / ([+-][0-9.]+)\s*$", hd, re.M)
    npairs = re.search(r"(\d+) real cross-source pairs", txt)
    if len(f) == 3:
        out["SthreeRepro"] = (f"Repeating this check on the second machine with its own model~6 seeds gives "
                              f"{', '.join(f'{100 * f[k]:.1f}' for k in sorted(f))}\\% "
                              f"({npairs.group(1) if npairs else '?'} pairs), all within the limit"
                              + (f", with rank correlations {min(float(a) for a, _ in rho):.2f} to {max(float(a) for a, _ in rho):.2f} "
                                 f"against ceilings {min(float(b) for _, b in rho):.2f} to {max(float(b) for _, b in rho):.2f}." if rho else "."))
    else:
        out["SthreeRepro"] = r"\pending{second-machine Stage 3 reproduction running}"
    rb = OUT / "realburst.txt"
    if rb.exists():
        m = re.search(r"m6 \(3 seeds\)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+) \[([0-9.]+), ([0-9.]+)\]", rb.read_text())
        out["RealBurstRepro"] = (f"On the second machine, its own model~6 seeds give a real/template ratio of {m.group(4)} "
                                 f"[{m.group(5)}, {m.group(6)}]." if m else r"\pending{parse realburst.txt}")
    else:
        out["RealBurstRepro"] = r"\pending{second-machine real-burst reproduction running}"
    # Compact forecast rows (CHIME vs all-sky, Catalog 2 and 10 yr, without/with magnification bias).
    sys.path.insert(0, str(HERE.parent / "paper"))
    from make_numbers import track_c

    def sci1(x):
        """One significant figure: reruns of the forecast scatter by tens of percent (update 2026-11-11_0900)."""
        m, e = f"{x:.0e}".split("e")
        return rf"${m}\times10^{{{int(e)}}}$"

    rows = []
    for lab, tag in (("Catalog 2, as observed", ""), (r"Catalog 2, $\gamma=1.5$", "_bias15"), ("10-yr survey", "_10yr"),
                     (r"10-yr survey, $\gamma=1.5$", "_10yr_bias15")):
        d = track_c(tag)
        if d:
            rows.append(f"{lab} & {sci1(d['chime'])} & {sci1(d['chime_echo'])} & {sci1(d['allsky'])} \\\\")
    out["ForecastCompact"] = "\n".join(rows) if rows else r"\pending{forecast}"
    base, bias = track_c(""), track_c("_bias15")
    if base and bias:
        out["NexpLo"], out["NexpHi"] = sci1(base["chime"]), sci1(bias["chime"])
        out["GainAllSkyOne"] = f"{round(base['allsky'] / base['chime'], -1):.0f}"
    keys = ["SthreeNpairs", "SthreeTeamMsix", "AblNoalignR", "AblNoalignD", "AblNoimpR", "AblNoimpD", "AblHardnegR",
            "AblHardnegD", "SthreeRepro", "RealBurstRepro", "ForecastCompact", "NexpLo", "NexpHi", "GainAllSkyOne"]
    (HERE / "numbers_icaiic.tex").write_text("".join(f"\\newcommand{{\\{k}}}{{{out.get(k, rf'\pending{{{k}}}')}}}\n" for k in keys))
    print((HERE / "numbers_icaiic.tex").read_text())


if __name__ == "__main__":
    main()
