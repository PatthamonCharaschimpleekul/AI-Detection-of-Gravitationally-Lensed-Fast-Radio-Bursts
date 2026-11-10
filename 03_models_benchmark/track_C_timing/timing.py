"""Track C: source-level timing test for a shared lensing delay, its background, efficiency and N_exp.

Statistic. A galaxy lens repeats every burst after one delay dt, fixed to far better than the catalog's
arrival-time errors (median 4 ms at infinite frequency). Pairs (i, j) of a burst list whose delays agree within
TOL_SIGMA combined errors and whose S/N ratios agree within a factor exp(R_TOL) form a delay cluster.
k_max = size of the largest cluster of disjoint pairs. An unlensed repeater rarely has k_max >= 2.

Blinding. The statistic is only ever computed on time-scrambled real lists (each burst moved by a whole number
of sidereal days, which keeps its hour angle, S/N and the transit selection) and on lensed injections into
them. The unscrambled real lists are the search data; this module never scores them (Sec. 7.1 item 7).

Lensed injection into a scrambled list: every burst gets a trailing copy at t + dt with S/N x r x g, where
g ~ lognormal(0, 0.3) stands for beam position and scintillation, and t is perturbed by the two bursts' timing errors.
The copy is kept if lens.observe() detects it. (dt, r) are drawn from the SIS population at the source's z.

Variants: --gamma g adds magnification bias for integral counts N(>S) ~ S^-g: a lens with leading-image
magnification mu+ = 1 + 1/y is weighted by mu+^g, which raises tau by E[mu+^g] and favours small y (r near 1).
--years L stretches the survey to L years: each list is resampled to n L / L_cat bursts on random sidereal days.

Usage: python timing.py [--scrambles 1000] [--injections 400] [--far 1e-3] [--gamma 0] [--years 0] [--tag ""]
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "01_semi_synthetic_data" / "03_lens_simulator"))
import lens  # noqa: E402

POP = ROOT / "01_semi_synthetic_data" / "02_population" / "outputs"
TABLE = ROOT / "01_semi_synthetic_data" / "01_real_data" / "data" / "catalog2" / "chimefrbcat2.csv"
OUT = HERE / "outputs"
TOL_SIGMA, R_TOL, G_SCATTER = 4.0, 0.7, 0.3
SEED = 20261109


def k_max(t, err, snr):
    """Largest cluster of disjoint burst pairs sharing one delay (and one S/N ratio)."""
    n = len(t)
    if n < 4:
        return 1 if n >= 2 else 0
    i, j = np.triu_indices(n, 1)
    d = t[j] - t[i]
    s = np.sqrt(err[i] ** 2 + err[j] ** 2)
    lr = np.log(snr[j] / snr[i])
    o = np.argsort(d)
    d, s, lr, i, j = d[o], s[o], lr[o], i[o], j[o]
    wmax = TOL_SIGMA * np.sqrt(2) * s.max()
    hi = np.searchsorted(d, d + wmax, side="right")
    best = 1
    for a in np.flatnonzero(hi - np.arange(len(d)) > 1):  # pairs with a neighbour inside the widest window
        b = np.arange(a + 1, hi[a])
        ok = (d[b] - d[a] < TOL_SIGMA * np.sqrt(s[a] ** 2 + s[b] ** 2)) & (np.abs(lr[b] - lr[a]) < R_TOL)
        ok &= (i[b] != i[a]) & (i[b] != j[a]) & (j[b] != i[a]) & (j[b] != j[a])
        if ok.any():
            # greedy disjoint set among a's matches (lower bound on the cluster size, exact for 2)
            used, k = {i[a], j[a]}, 1
            for q in b[ok]:
                if i[q] not in used and j[q] not in used:
                    used |= {i[q], j[q]}
                    k += 1
            best = max(best, k)
    return best


def scramble(src, rng):
    """Move each burst by a random whole number of sidereal days inside the survey (keeps HA and S/N)."""
    t = src["t"]
    lo = np.ceil((lens.SURVEY[0] - t) / lens.SID_DAY)
    hi = np.floor((lens.SURVEY[1] - t) / lens.SID_DAY)
    k = rng.integers(lo, hi + 1)
    return t + k * lens.SID_DAY


def inject(t, src, dt, r, rng, all_sky=False):
    """Scrambled list t plus the detected trailing copies for delay dt (days) and flux ratio r."""
    err, snr = src["err"], src["snr"]
    tc = t + dt + rng.normal(0, np.sqrt(2) * err)
    sc = snr * r * np.exp(G_SCATTER * rng.normal(size=len(t)))
    if all_sky:
        det = (sc >= lens.SNR_DET) & (tc <= lens.SURVEY[1])
    else:
        det = lens.observe(tc, sc, src["ra"], src["dec"], src["pon"], rng)
    return np.concatenate([t, tc[det]]), np.concatenate([err, err[det]]), np.concatenate([snr, sc[det]]), int(det.sum())


def stretch(src, years, rng):
    """Resample a burst list onto a longer survey: same bursts (S/N, errors, hour angles), proportionally more of them."""
    base = (lens.SURVEY[1] - lens.SURVEY[0]) / 365.25
    n = int(round(len(src["t"]) * years / base))
    k = rng.integers(len(src["t"]), size=n)
    return dict(src, t=src["t"][k], err=src["err"][k], snr=src["snr"][k], n=n)


def load_sources(zfile="z_samples.npz"):
    zs = np.load(POP / zfile)
    exp_up = {}
    for r in csv.DictReader(open(TABLE, newline="")):
        if r["repeater_name"] not in ("", "-9999") and r["exp_up"] not in ("", "nan"):
            exp_up.setdefault(r["repeater_name"], float(r["exp_up"]))
    srcs = {}
    for b in csv.DictReader(open(POP / "bursts.csv", newline="")):
        srcs.setdefault(b["src"], []).append(b)
    meta = {r["source"]: r for r in csv.DictReader(open(POP / "repeaters.csv", newline=""))}
    out = {}
    for s, bs in sorted(srcs.items()):
        f = lambda k: np.array([float(b[k]) for b in bs])
        snr = np.where(np.isfinite(f("bonsai_snr")), f("bonsai_snr"), f("snr"))
        ra, dec = float(meta[s]["ra"]), float(meta[s]["dec"])
        out[s] = dict(t=f("mjd_inf"), err=np.maximum(f("mjd_inf_err"), 1e-9), snr=snr, ra=ra, dec=dec,
                      pon=lens.p_on(exp_up.get(s, 0.0), dec), z=zs[s], n=len(bs))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scrambles", type=int, default=1000)
    ap.add_argument("--injections", type=int, default=400)
    ap.add_argument("--far", type=float, default=1e-3, help="false-alarm probability per source")
    ap.add_argument("--gamma", type=float, default=0.0, help="magnification-bias slope; 0 = none")
    ap.add_argument("--years", type=float, default=0.0, help="survey length in years; 0 = Catalog 2 as observed")
    ap.add_argument("--tag", default="")
    ap.add_argument("--zfile", default="z_samples.npz", help="redshift samples from 02_population (sensitivity runs)")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    rng = np.random.default_rng(SEED)
    # Self-checks: an exact repeat of four bursts gives k = 4; a scramble keeps hour angles.
    t0 = np.array([58500.1, 58501.3, 58507.9, 58530.2])
    tt = np.concatenate([t0, t0 + 12.345])
    assert k_max(tt, np.full(8, 1e-8), np.r_[np.full(4, 20.0), np.full(4, 10.0)]) == 4
    srcs = load_sources(a.zfile)
    if a.years:
        srcs = {k: stretch(v, a.years, rng) for k, v in srcs.items()}
        lens.SURVEY = (lens.SURVEY[0], lens.SURVEY[0] + 365.25 * a.years)
    s0 = next(iter(srcs.values()))
    assert np.allclose(lens.hour_angle(scramble(s0, rng), s0["ra"]), lens.hour_angle(s0["t"], s0["ra"]), atol=1e-3)

    rows = []
    for name, src in srcs.items():
        bg = np.array([k_max(scramble(src, rng), src["err"], src["snr"]) for _ in range(a.scrambles)])
        # threshold: smallest k with background P(k_max >= k) <= far; with few scrambles, 2 needs zero hits
        k_thr = next(k for k in range(2, 50) if (bg >= k).mean() <= a.far)
        res = {}
        # Delays from the source's lens population. Under CHIME's transit, a delay shows copies only if it brings
        # them back into a transit window, so sample that geometry exactly: f = share of the source's bursts
        # whose copy lands in a window. eff = P(f > 0) x eff | f > 0, the second from injections drawn from
        # the f > 0 delays (importance sampling; all-sky needs no conditioning).
        pool = lens.sample_lens(rng.choice(src["z"], 20000), 20000, rng)
        bias = 1.0
        if a.gamma:
            w = (1 + 1 / pool["y"]) ** a.gamma
            bias = float(w.mean())
            k = rng.choice(len(w), len(w), p=w / w.sum())
            pool = {key: v[k] for key, v in pool.items()}
        tt = src["t"][None, :] + pool["dt_days"][:, None]
        f_in = lens.in_window(tt, src["ra"], src["dec"]).mean(1)
        p_align = float((f_in > 0).mean())
        for mode in ("chime", "all_sky"):
            cand = np.flatnonzero(f_in > 0) if mode == "chime" else np.arange(len(f_in))
            if len(cand) == 0:
                res[mode] = (0.0, 0.0, 0.0)
                continue
            det, echoes = [], []
            for q in rng.choice(cand, a.injections):
                t = scramble(src, rng)
                # the scramble moves bursts by whole sidereal days, so window alignment of the delay is unchanged
                tl, el, sl, ne = inject(t, src, float(pool["dt_days"][q]), float(pool["r"][q]), rng, mode == "all_sky")
                echoes.append(ne)
                det.append(k_max(tl, el, sl) >= k_thr)
            w = p_align if mode == "chime" else 1.0
            res[mode] = (w * np.mean(det), w * np.mean(np.array(echoes) >= 1), w * np.mean(echoes))
        tau = bias * float(np.mean([lens.tau(z) for z in rng.choice(src["z"], 50)]))
        rows.append(dict(source=name, n_bursts=src["n"], p_on=round(src["pon"], 3), p_align=round(p_align, 4), z_median=round(float(np.median(src["z"])), 3),
                         tau=f"{tau:.3e}", bg_p_k2=round(float((bg >= 2).mean()), 4), k_thr=k_thr,
                         eff_timing_chime=round(res["chime"][0], 4), p_echo_chime=round(res["chime"][1], 4),
                         mean_echoes_chime=round(res["chime"][2], 3),
                         eff_timing_allsky=round(res["all_sky"][0], 4), p_echo_allsky=round(res["all_sky"][1], 4)))
        print(f"{name}: n={src['n']} p_on={src['pon']:.2f} bg P(k>=2)={rows[-1]['bg_p_k2']} k_thr={k_thr} "
              f"p_align {p_align:.3f} eff chime {res['chime'][0]:.4f} (echo {res['chime'][1]:.3f}) all-sky {res['all_sky'][0]:.3f} tau {tau:.2e}", flush=True)
    with open(OUT / f"track_c_sources{a.tag}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    tau = np.array([float(r["tau"]) for r in rows])
    for mode in ("chime", "allsky"):
        e = np.array([r[f"eff_timing_{mode}"] for r in rows])
        pe = np.array([r[f"p_echo_{mode}"] for r in rows])
        print(f"{mode}: N_exp (timing, k_max >= k_thr) = {np.sum(tau * e):.2e}; "
              f"expected lensed repeaters with >= 1 detected echo = {np.sum(tau * pe):.2e}; sum tau = {tau.sum():.2e}")


if __name__ == "__main__":
    main()
