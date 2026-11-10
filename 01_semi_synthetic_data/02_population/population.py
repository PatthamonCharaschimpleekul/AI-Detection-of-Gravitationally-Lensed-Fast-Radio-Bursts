"""Per-repeater parameters and redshift samples from the CHIME/FRB Catalog 2 table.

z comes from the NE2001 DM excess through the Macquart relation:
  DM_exc = DM_halo + DM_cosmic(z) + DM_host / (1 + z)
  - DM_halo ~ U(25, 80) pc/cc (Milky Way halo; Prochaska & Zheng 2019 range)
  - DM_host ~ lognormal, median 68 pc/cc, sigma_ln 0.88 (Macquart et al. 2020 best fit)
  - DM_cosmic: Macquart et al. 2020 p(Delta), Delta = DM_cosmic / <DM_cosmic>(z), alpha = beta = 3, sigma = min(F z^-0.5, 2), F = 0.32
  - prior p(z) proportional to dV_c/dz / (1 + z) on 0.001 < z < 2 (constant comoving rate)
A source with a host-galaxy redshift uses it instead (HOST_Z; values to re-check against the papers before submission).
Cosmology: flat LCDM, H0 = 67.7, Omega_m = 0.31, Omega_b h^2 = 0.0224 (Planck 2018), f_IGM = 0.84, chi_e = 7/8.

Usage: python population.py   -> outputs/repeaters.csv, outputs/z_samples.npz
       python population.py --host-median 150   -> outputs/repeaters_host150.csv, z_samples_host150.npz (sensitivity)
"""
import csv
from pathlib import Path

import numpy as np
from scipy.integrate import cumulative_trapezoid
from scipy.optimize import brentq

HERE = Path(__file__).resolve().parent
TABLE = HERE.parent / "01_real_data" / "data" / "catalog2" / "chimefrbcat2.csv"
OUT = HERE / "outputs"
H0, OM, OBH2, F_IGM, CHI_E = 67.7, 0.31, 0.0224, 0.84, 7 / 8
C_KMS = 299792.458
N_SAMPLES = 2000
SEED = 20261109
# Host-galaxy redshifts of localized repeaters. Checked 2026-11-09 against the cited papers (abstract or table level).
HOST_Z = {
    "FRB20180916B": 0.0337,   # Marcote et al. 2020
    "FRB20201124A": 0.0979,   # Fong et al. 2021; Ravi et al. 2022
    "FRB20220912A": 0.0771,   # Ravi et al. 2023
    "FRB20190303A": 0.064,    # Michilli et al. 2023: merging pair at 0.06437 and 0.06386
    "FRB20180814A": 0.068,    # Michilli et al. 2023: 0.06835
    "FRB20181030A": 0.0039,   # Bhardwaj et al. 2021: NGC 3252, ~20 Mpc
    "FRB20200120E": 0.0008,   # M81 globular cluster, 3.6 Mpc (Bhardwaj et al. 2021; Kirsten et al. 2022)
}

ZG = np.geomspace(1e-3, 2.0, 600)


def E(z):
    return np.sqrt(OM * (1 + z) ** 3 + 1 - OM)


def comoving_mpc(z):
    zz = np.concatenate([[0.0], np.atleast_1d(z)])
    zf = np.linspace(0, zz.max(), 4000)
    dc = cumulative_trapezoid(1 / E(zf), zf, initial=0) * C_KMS / H0
    return np.interp(np.atleast_1d(z), zf, dc)


def dm_cosmic_mean(z):
    """<DM_cosmic>(z) in pc/cc for fully ionised H and He (chi_e) and f_IGM."""
    # 3 c H0 Omega_b f_IGM chi_e / (8 pi G m_p), with Omega_b = OBH2 / h^2
    G, MP, MPC, PC = 6.674e-11, 1.6726e-27, 3.0857e22, 3.0857e16
    h0 = H0 * 1e3 / MPC
    ob = OBH2 / (H0 / 100) ** 2
    pref = 3 * 2.998e8 * h0 * ob * F_IGM * CHI_E / (8 * np.pi * G * MP)  # electrons per m^2 per unit integral
    zf = np.linspace(0, max(np.max(z), 1e-3), 4000)
    integ = cumulative_trapezoid((1 + zf) / E(zf), zf, initial=0)
    return np.interp(z, zf, integ) * pref / (1e6 * PC)  # m^-2 -> cm^-3 pc


def p_delta_table(sig, alpha=3.0, beta=3.0):
    """Macquart et al. 2020 p(Delta) on a grid, with C0 set so <Delta> = 1."""
    d = np.linspace(1e-3, 15, 6000)

    def pdf(c0):
        lp = -beta * np.log(d) - (d ** -alpha - c0) ** 2 / (2 * alpha ** 2 * sig ** 2)
        p = np.exp(lp - lp.max())  # log space: the Gaussian factor underflows at extreme C0
        return p / np.trapezoid(p, d)

    grid = np.linspace(-30, 30, 241)
    mean = np.array([np.trapezoid(d * pdf(c), d) for c in grid]) - 1
    k = np.flatnonzero(np.diff(np.sign(mean)))[0]
    c0 = brentq(lambda c: np.trapezoid(d * pdf(c), d) - 1, grid[k], grid[k + 1])
    return d, pdf(c0)


def main():
    import sys
    host_med = float(sys.argv[sys.argv.index("--host-median") + 1]) if "--host-median" in sys.argv else 68.0
    tag = "" if host_med == 68.0 else f"_host{host_med:g}"
    OUT.mkdir(exist_ok=True)
    rows = [r for r in csv.DictReader(open(TABLE, newline="")) if r["repeater_name"] not in ("", "-9999")]
    num = lambda s: float(s) if s not in ("", "nan", "-9999") else np.nan
    bursts = {}
    for r in rows:  # one entry per burst; sub-burst rows share the burst's time and DM
        b = bursts.setdefault(r["tns_name"], dict(src=r["repeater_name"], ra=num(r["ra"]), dec=num(r["dec"]),
                                                  dm=num(r["dm_fitb"]), dm_exc=num(r["dm_exc_ne2001"]),
                                                  mjd_400=num(r["mjd_400"]), mjd_inf=num(r["mjd_inf"]),
                                                  mjd_inf_err=num(r["mjd_inf_err"]), snr=num(r["snr_fitb"]),
                                                  bonsai_snr=num(r["bonsai_snr"]), fluence=num(r["fluence"]),
                                                  excluded=r["excluded_flag"] == "1"))
        b["snr"] = float(np.fmax(b["snr"], num(r["snr_fitb"])))
    by_src = {}
    for name, b in bursts.items():
        by_src.setdefault(b["src"], []).append((name, b))

    # p(DM_exc | z) by Monte Carlo over halo and host, on the z grid.
    rng = np.random.default_rng(SEED)
    n_mc = 4000
    halo = rng.uniform(25, 80, n_mc)
    host = np.exp(np.log(host_med) + 0.88 * rng.normal(size=n_mc))
    mean_c = dm_cosmic_mean(ZG)
    # sigma is capped at 2 (z < 0.026), where DM_cosmic < 25 pc/cc and the host term dominates anyway
    tables = [p_delta_table(min(0.32 / np.sqrt(z), 2.0)) for z in ZG]
    dv = comoving_mpc(ZG) ** 2 / E(ZG)
    prior = dv / (1 + ZG) * np.gradient(ZG)
    prior /= prior.sum()

    out_rows, zs = [], {}
    for src, items in sorted(by_src.items()):
        dm_exc = float(np.nanmedian([b["dm_exc"] for _, b in items]))
        if src in HOST_Z:
            z = np.full(N_SAMPLES, HOST_Z[src])
            zmed, zlo, zhi, how = HOST_Z[src], HOST_Z[src], HOST_Z[src], "host"
        else:
            like = np.zeros(len(ZG))
            for k, z in enumerate(ZG):
                dc = dm_exc - halo - host / (1 + z)  # implied DM_cosmic per MC draw
                d, p = tables[k]
                like[k] = np.mean(np.interp(dc / mean_c[k], d, p, left=0, right=0) / mean_c[k])
            post = prior * like
            post /= post.sum()
            cdf = np.cumsum(post)
            z = np.interp(rng.uniform(size=N_SAMPLES), cdf, ZG)
            zmed, zlo, zhi = (float(np.interp(q, cdf, ZG)) for q in (0.5, 0.16, 0.84))
            how = "dm"
        zs[src] = z
        t = np.sort([b["mjd_inf"] for _, b in items])
        out_rows.append(dict(source=src, n_bursts=len(items), n_excluded=sum(b["excluded"] for _, b in items),
                             ra=items[0][1]["ra"], dec=items[0][1]["dec"], dm_exc_ne2001=round(dm_exc, 1),
                             z_median=round(zmed, 4), z_lo=round(zlo, 4), z_hi=round(zhi, 4), z_from=how,
                             first_mjd=round(t[0], 4), last_mjd=round(t[-1], 4), span_days=round(t[-1] - t[0], 1),
                             median_snr=round(float(np.nanmedian([b["snr"] for _, b in items])), 1)))
    with open(OUT / f"repeaters{tag}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(out_rows)
    np.savez(OUT / f"z_samples{tag}.npz", **zs)
    if tag:  # sensitivity run: burst lists are unchanged
        print(f"host median {host_med:g}: z median of medians {np.median([r['z_median'] for r in out_rows]):.3f}")
        return
    # Burst lists for the lens simulator and Track C: one row per burst.
    with open(OUT / "bursts.csv", "w", newline="") as f:
        cols = ["tns", "src", "mjd_400", "mjd_inf", "mjd_inf_err", "snr", "bonsai_snr", "fluence", "dm", "excluded"]
        w = csv.writer(f)
        w.writerow(cols)
        for name, b in sorted(bursts.items(), key=lambda kv: kv[1]["mjd_inf"]):
            w.writerow([name] + [b[k] for k in cols[1:]])
    zm = np.array([r["z_median"] for r in out_rows])
    print(f"{len(out_rows)} repeaters, {len(bursts)} bursts; host z for {sum(r['z_from'] == 'host' for r in out_rows)}; "
          f"z median of medians {np.median(zm):.3f}, range {zm.min():.4f}-{zm.max():.3f}")
    # Check: <DM_cosmic>(z=1) should be about 900-1000 pc/cc for these parameters (Macquart et al. 2020 Fig. 2).
    print(f"<DM_cosmic>(0.1, 0.5, 1.0) = {dm_cosmic_mean(np.array([0.1, 0.5, 1.0])).round(0)} pc/cc")


if __name__ == "__main__":
    main()
