"""Galaxy lensing of repeaters (SIS) and the CHIME observation filter.

Lenses: singular isothermal spheres with the Choi, Park & Vogeley (2007) velocity-dispersion function
(phi* = 8.0e-3 h^3 Mpc^-3, sigma* = 161 km/s, alpha = 2.32, beta = 2.67), constant comoving density.
  theta_E = 4 pi (sigma/c)^2 D_ls/D_s;  images at theta_E (1 +- y) for y < 1
  delay   dt = 2 y theta_E^2 (1 + z_l) D_l D_s / (c D_ls)   (outer, brighter image first)
  |mu+-|  = 1/y +- 1, flux ratio r = (1 - y)/(1 + y) (trailing / leading)
  tau(z_s) = int dz_l int dsigma phi(sigma) pi theta_E^2 D_c(z_l)^2 dD_c/dz_l
Source-plane position y is uniform in area, p(y) = 2y; no magnification bias (conservative for tau).

Observation (checked on the 981 real bursts, update 2026-11-09): CHIME sees a source within
|HA| cos(dec) < 1.1 deg of upper transit (99% of real bursts), and of lower transit for dec > 70 deg.
A copy is observed if it falls in a transit window, inside the survey dates, on a day CHIME was observing
(probability p_on from the catalog exposure), and its S/N stays at or above the detection floor.

Usage: python lens.py  (self-checks and a tau table -> outputs/tau.csv)
"""
from pathlib import Path

import numpy as np
from scipy.integrate import cumulative_trapezoid
from scipy.special import gamma as G

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
H0, OM = 67.7, 0.31
h = H0 / 100
C_KMS = 299792.458
MPC_S = 3.0857e19 / C_KMS  # light travel time across 1 Mpc, in s
PHI_STAR, SIG_STAR, ALPHA, BETA = 8.0e-3 * h ** 3, 161.0, 2.32, 2.67
SURVEY = (58365.0, 60202.0)  # 2018-09-04 to 2023-09-15, the Catalog 2 exposure period
SID_DAY = 0.99726957  # solar days
CHIME_LON = -119.6237  # deg
HALF_WIDTH_DEG = 1.1  # on-sky EW half-width of the transit window
SNR_DET = 10.0

_zf = np.linspace(0, 6, 6001)
_dc = cumulative_trapezoid(1 / np.sqrt(OM * (1 + _zf) ** 3 + 1 - OM), _zf, initial=0) * C_KMS / H0


def dcom(z):
    return np.interp(z, _zf, _dc)


def ang_dists(zl, zs):
    """D_l, D_s, D_ls (angular diameter, Mpc), flat universe."""
    dl, ds = dcom(zl), dcom(zs)
    return dl / (1 + zl), ds / (1 + zs), (ds - dl) / (1 + zs)


_sg = np.linspace(20, 600, 600)
_phi = PHI_STAR * (_sg / SIG_STAR) ** ALPHA * np.exp(-(_sg / SIG_STAR) ** BETA) * BETA / G(ALPHA / BETA) / _sg
_s4 = np.trapezoid(_phi * _sg ** 4, _sg)  # int phi sigma^4 dsigma


def tau_dz(zl, zs):
    """d tau / d z_l for a source at zs."""
    dl, ds, dls = ang_dists(zl, zs)
    te2_per_s4 = (4 * np.pi / C_KMS ** 2) ** 2 * (dls / ds) ** 2  # theta_E^2 / sigma^4
    ddc = C_KMS / H0 / np.sqrt(OM * (1 + zl) ** 3 + 1 - OM)
    return np.pi * te2_per_s4 * _s4 * dcom(zl) ** 2 * ddc


def tau(zs, n=400):
    zl = np.linspace(1e-4, zs, n, endpoint=False)
    return np.trapezoid(tau_dz(zl, zs), zl)


_X = np.linspace(1e-4, 1, 400, endpoint=False)  # z_l / z_s
_ZS_GRID = np.geomspace(5e-4, 2.5, 120)
_XCDF = np.array([np.cumsum(w) / np.sum(w) for w in (tau_dz(_X * z, z) for z in _ZS_GRID)])


def sample_lens(zs, n, rng):
    """n lens draws for a source at zs (scalar, or one z_s per draw): delay (days), flux ratio
    r = trailing/leading, z_l, sigma (km/s), y. z_l / z_s comes from the nearest of 120 tabulated z_s."""
    zs = np.broadcast_to(np.asarray(zs, float), (n,))
    k = np.clip(np.searchsorted(_ZS_GRID, zs), 0, len(_ZS_GRID) - 1)
    u = rng.uniform(size=n)
    zl = zs * np.array([np.interp(u[q], _XCDF[k[q]], _X) for q in range(n)])
    ws = np.cumsum(_phi * _sg ** 4)
    sig = np.interp(rng.uniform(size=n), ws / ws[-1], _sg)  # cross-section weights sigma^4
    y = np.sqrt(rng.uniform(size=n))
    dl, ds, dls = ang_dists(zl, zs)
    te = 4 * np.pi * (sig / C_KMS) ** 2 * dls / ds
    dt_s = 2 * y * te ** 2 * (1 + zl) * dl * ds / dls * MPC_S
    return dict(dt_days=dt_s / 86400, r=(1 - y) / (1 + y), zl=zl, sigma=sig, y=y)


def hour_angle(mjd, ra):
    """Hour angle at CHIME, hours in [-12, 12)."""
    gmst = (18.697374558 + 24.06570982441908 * (mjd - 51544.5)) % 24
    return ((gmst + CHIME_LON / 15 - ra / 15 + 12) % 24) - 12


def in_window(mjd, ra, dec):
    """True where CHIME's formed beams cover the source: upper transit, or lower transit for dec > 70 deg."""
    ha = hour_angle(mjd, ra)
    cosd = np.cos(np.radians(dec))
    up = np.abs(ha) * 15 * cosd < HALF_WIDTH_DEG
    low = (dec > 70) & ((12 - np.abs(ha)) * 15 * cosd < HALF_WIDTH_DEG)
    return up | low


def window_hours(dec):
    """Daily hours in the upper and lower transit windows."""
    w = 2 * HALF_WIDTH_DEG / (15 * np.cos(np.radians(dec)))
    return np.minimum(w, 24), np.where(dec > 70, np.minimum(w, 24), 0.0)


def p_on(exp_up_h, dec):
    """Share of survey days CHIME observed in the upper window, from the catalog exposure (capped at 1)."""
    w_up, _ = window_hours(dec)
    return float(np.clip(exp_up_h / ((SURVEY[1] - SURVEY[0]) * w_up), 0, 1))


def observe(t, snr, ra, dec, pon, rng):
    """Which copies at times t (MJD) with S/N snr are detected."""
    ok = (t >= SURVEY[0]) & (t <= SURVEY[1]) & in_window(t, ra, dec) & (snr >= SNR_DET)
    return ok & (rng.uniform(size=len(t)) < pon)


def main():
    OUT.mkdir(exist_ok=True)
    rng = np.random.default_rng(1)
    # Self-check 1: delay formula against the Fermat potential, theta^2/2 - theta_E |theta| - beta theta, on a grid.
    zl, zs, sig, y = 0.3, 1.0, 200.0, 0.4
    dl, ds, dls = ang_dists(zl, zs)
    te = 4 * np.pi * (sig / C_KMS) ** 2 * dls / ds
    phi = lambda th: th ** 2 / 2 - te * abs(th) - y * te * th
    dt_fermat = (phi(-te * (1 - y)) - phi(te * (1 + y))) * (1 + zl) * dl * ds / dls * MPC_S / 86400
    d = sample_lens(zs, 1, np.random.default_rng(0))
    dt_formula = 2 * y * te ** 2 * (1 + zl) * dl * ds / dls * MPC_S / 86400
    assert abs(dt_fermat / dt_formula - 1) < 1e-9, (dt_fermat, dt_formula)
    print(f"check: SIS sigma=200 km/s, z_l=0.3, z_s=1, y=0.4 -> theta_E {np.degrees(te) * 3600:.2f} arcsec, delay {dt_formula:.1f} days")
    # Self-check 2: tau(z_s) of an SIS population grows ~ D_c^3 at low z.
    t1, t2 = tau(0.05), tau(0.1)
    print(f"check: tau(0.1)/tau(0.05) = {t2 / t1:.2f}, D_c ratio cubed {(dcom(0.1) / dcom(0.05)) ** 3:.2f}")
    rows = [(z, tau(z)) for z in (0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 1.5, 2.0)]
    np.savetxt(OUT / "tau.csv", rows, delimiter=",", header="z_s,tau", comments="", fmt="%.4g")
    print("tau(z_s):", ", ".join(f"{z:g}: {t:.2e}" for z, t in rows))
    for zs in (0.1, 0.3, 1.0):
        s = sample_lens(zs, 200000, rng)
        print(f"z_s={zs}: delay days median {np.median(s['dt_days']):.2f}, 5-95% "
              f"[{np.percentile(s['dt_days'], 5):.3f}, {np.percentile(s['dt_days'], 95):.1f}]; r median {np.median(s['r']):.2f}")


if __name__ == "__main__":
    main()
