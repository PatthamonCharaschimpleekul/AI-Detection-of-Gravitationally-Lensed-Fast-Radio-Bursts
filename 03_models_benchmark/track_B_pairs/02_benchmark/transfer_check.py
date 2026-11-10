"""Stage 3 transfer check, development version: val-split sources only (plan 2026-11-06_1223, Stage 3 as corrected).

Real cross-source pairs are true negatives by construction, so scoring them does not break the blind protocol.
For each method and bin of (pair min S/N, mask overlap):
  1. threshold = 99th percentile of the method's scores on simulated `unrelated` val pairs in that bin;
  2. real FPR = share of real val cross-source pairs above it. Criterion: real FPR <= 2%.
Twin test: each real pair is re-simulated twice from its own two templates at their measured S/N
(fresh backgrounds, full v1 nuisances, as checks/snr_bins.py). Spearman(real, twin) far below
Spearman(twin, twin2) means the score uses something the templates lack.

Usage (from this folder): python transfer_check.py --model 6:../01_training/outputs/m6_s0/best.pt [--model ...]
Writes outputs/stage3_val.txt and outputs/stage3_val_scores.npz. Never reads test-split sources.
"""
import argparse, sys
from multiprocessing import Pool
from pathlib import Path

import h5py
import numpy as np
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "01_training"), str(HERE.parents[2] / "02_injection_labelling" / "01_injection")]
from inject import REAL, SNR_MIN, make_pair, member
import baselines
from baselines import METHODS, gbm_jobs, score_pair

OUT = HERE / "outputs"
SNR_BINS = ((10, 25), (25, 50), (50, np.inf))
FPR_SIM, FPR_MAX = 0.01, 0.02
B_BOOT, BOOT_SEED = 2000, 2026
SIM_SEED, TWIN_SEED = 601, 611  # new streams, not used by any frozen set


def overlap(ma, mb):
    return float((ma & mb).sum() / max((ma | mb).sum(), 1))


# ---------------- workers: build pairs and score the baselines ----------------
def init():
    global P, XR, FMR
    baselines.init()  # baselines.work needs its pools in each worker
    P = baselines.POOLS["val"]
    with h5py.File(REAL / "preproc" / "repeaters_256x160.h5") as f:
        XR, FMR = f["X"][:], f["freq_mask"][:] >= 0.25


def sim_job(job):
    """Simulated unrelated val pair, as make_pair builds it."""
    seed, floor = job
    xa, xb, ma, mb, _, info = make_pair("unrelated", np.random.default_rng(seed), P, False, floor)
    s, f = score_pair(xa, ma, xb, mb, P.c["freq_mhz"])
    return xa, xb, ma, mb, s, f, min(info["snr_a"], info["snr_b"]), overlap(ma, mb), info["src_a"], info["src_b"]


def real_job(job):
    i, j = job
    s, f = score_pair(XR[i], FMR[i], XR[j], FMR[j], P.c["freq_mhz"])
    return s, f


def twin_job(job):
    """One re-simulation of real pair (i, j): its two templates at measured S/N on fresh val backgrounds."""
    q, i, j, stream = job
    c = P.c
    rng = np.random.default_rng([stream, q])
    used = {i, j}
    out = []
    for t in (i, j):
        while True:
            b = int(rng.choice(P.bgs))
            if c["bg_file"][b] not in used:
                break
        used.add(c["bg_file"][b])
        x, m, _ = member(c, t, b, max(c["model_snr"][t], SNR_MIN), rng, 0.0, False)
        out += [x, m]
    xa, ma, xb, mb = out
    s, f = score_pair(xa, ma, xb, mb, c["freq_mhz"])
    return xa, xb, ma, mb, s, f


# ---------------- learned models ----------------
def load_models(specs):
    import torch
    from models import MODELS
    ms = {}
    for spec in specs:
        k, path = spec.split(":", 1)
        m = MODELS[int(k)]().to("cuda")
        m.load_state_dict(torch.load(path, map_location="cuda"))
        m.eval()
        ms[f"m{k}:{Path(path).parent.name}"] = m
    return ms


def model_scores(ms, XA, XB, bs=128):
    """Lensed log-odds averaged over both member orders, exactly as train.scores."""
    import torch
    from models import lensed_score
    out = {}
    A, B = torch.from_numpy(np.asarray(XA)).half(), torch.from_numpy(np.asarray(XB)).half()
    with torch.no_grad():
        for name, m in ms.items():
            v, u = [], []
            for k in range(0, len(A), bs):
                a, b = A[k:k + bs].cuda(), B[k:k + bs].cuda()
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    lab, lba = m(a, b).float(), m(b, a).float()
                s = lensed_score(lab) + lensed_score(lba)
                v.append(s.float().cpu() / 2)
                # log ratio lensed vs unrelated (classes are balanced in training, so this estimates log p(x|L)/p(x|U))
                u.append(((lab[:, 0] - lab[:, 2]) + (lba[:, 0] - lba[:, 2])).float().cpu() / 2)
            out[name] = torch.cat(v).numpy()
            out[name + "|LvU"] = torch.cat(u).numpy()
    return out


def run_scored(pool, fn, jobs, ms, has_pixels, chunk=1024):
    """Map fn over jobs in chunks; score learned models on the pixels, then drop them to save memory."""
    keep = {"s": [], "f": [], "rest": []}
    learned = {}
    for c0 in range(0, len(jobs), chunk):
        r = pool.map(fn, jobs[c0:c0 + chunk], chunksize=16)
        if has_pixels:
            sc = model_scores(ms, [x[0] for x in r], [x[1] for x in r])
            for k, v in sc.items():
                learned.setdefault(k, []).append(v)
            keep["s"] += [x[4] for x in r]
            keep["f"] += [x[5] for x in r]
            keep["rest"] += [x[6:] for x in r]
        else:
            keep["s"] += [x[0] for x in r]
            keep["f"] += [x[1] for x in r]
        print(f"  {fn.__name__}: {min(c0 + chunk, len(jobs))}/{len(jobs)}", flush=True)
    return np.array(keep["s"]), np.array(keep["f"]), keep["rest"], {k: np.concatenate(v) for k, v in learned.items()} if learned else {}


def boot_fpr(flag, sa, sb, names):
    """Source bootstrap of a pair-level rate: resample sources, weight each pair by both sources' multiplicities."""
    idx = {s: k for k, s in enumerate(names)}
    ia, ib = np.array([idx[s] for s in sa]), np.array([idx[s] for s in sb])
    rng = np.random.default_rng(BOOT_SEED)
    out = []
    for _ in range(B_BOOT):
        cnt = np.bincount(rng.integers(len(names), size=len(names)), minlength=len(names))
        w = cnt[ia] * cnt[ib]
        if w.sum():
            out.append((w * flag).sum() / w.sum())
    return np.percentile(out, [2.5, 97.5])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", default=[], help="id:checkpoint, e.g. 6:../01_training/outputs/m6_s0/best.pt")
    ap.add_argument("--n-sim", type=int, default=12000, help="simulated unrelated pairs at the S/N floor 10")
    ap.add_argument("--n-sim-bright", type=int, default=8000, help="extra simulated unrelated pairs at floor 25")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    from sklearn.ensemble import HistGradientBoostingClassifier
    OUT.mkdir(exist_ok=True)
    ms = load_models(a.model)
    init()
    c = P.c
    with h5py.File(REAL / "preproc" / "repeaters_256x160.h5") as f:
        assert (f["meta/tns"][:].astype(str) == c["tns"]).all(), "preproc and cache rows differ"
    assert P.split == "val"

    # Real val bursts = the val templates; all cross-source pairs among them.
    R = np.sort(np.concatenate(list(P.tmpl.values())))
    assert (c["file_split"][R] == "val").all()
    pairs = [(int(i), int(j)) for k, i in enumerate(R) for j in R[k + 1:] if c["source"][i] != c["source"][j]]
    pi, pj = np.array(pairs).T
    r_smin = np.minimum(c["model_snr"][pi], c["model_snr"][pj])
    r_ov = np.array([overlap(FMR[i], FMR[j]) for i, j in pairs])
    ov_cut = float(np.median(r_ov))  # fixed from masks only, before any score is seen
    print(f"{len(R)} real val bursts from {len(P.sources)} sources -> {len(pairs)} cross-source pairs; "
          f"mask-overlap split at the real median {ov_cut:.3f}", flush=True)

    with Pool(a.workers, initializer=init) as pool:
        print("GBM training pairs (train split, recipe of baselines.py)", flush=True)
        tr = baselines.run(pool, gbm_jobs("train", 300))
        gbm = HistGradientBoostingClassifier(random_state=0).fit(tr["f"], tr["y"] == 0)
        jobs = [([SIM_SEED, i], SNR_MIN) for i in range(a.n_sim)] + [([SIM_SEED + 1, i], 25.0) for i in range(a.n_sim_bright)]
        s_s, s_f, rest, s_l = run_scored(pool, sim_job, jobs, ms, True)
        r_s, r_f, _, _ = run_scored(pool, real_job, pairs, {}, False)
        t1 = run_scored(pool, twin_job, [(q, i, j, TWIN_SEED) for q, (i, j) in enumerate(pairs)], ms, True)
        t2 = run_scored(pool, twin_job, [(q, i, j, TWIN_SEED + 1) for q, (i, j) in enumerate(pairs)], ms, True)
    r_l = model_scores(ms, XR[pi], XR[pj]) if ms else {}
    s_smin, s_ov = np.array([x[0] for x in rest]), np.array([x[1] for x in rest])

    def table(s, f, learned):
        return {m: s[:, k] for k, m in enumerate(METHODS)} | {"b3_gbm": gbm.predict_proba(f)[:, 1]} | learned

    S, Rs = table(s_s, s_f, s_l), table(r_s, r_f, r_l)
    T1, T2 = table(t1[0], t1[1], t1[3]), table(t2[0], t2[1], t2[3])
    src_a, src_b = c["source"][pi], c["source"][pj]
    names = P.sources

    cells = [(f"S/N {lo}-{hi if hi < np.inf else 'inf'}", (lo, hi), None) for lo, hi in SNR_BINS]
    cells += [("S/N >= 25 (headline)", (25, np.inf), None)]
    cells += [(f"S/N {lo}-{hi if hi < np.inf else 'inf'}, overlap {'<' if lo_ov else '>='} {ov_cut:.2f}", (lo, hi), lo_ov)
              for lo, hi in SNR_BINS for lo_ov in (True, False)]
    rep = [f"Stage 3 transfer check on val-split sources (development). {len(pairs)} real cross-source pairs, "
           f"{len(s_smin)} simulated unrelated. Criterion: real FPR <= {FPR_MAX:.0%} at the sim {FPR_SIM:.0%} threshold.",
           "real FPR CI: source bootstrap (pairs weighted by both sources' multiplicities). '-' = fewer than 100 sim or 30 real pairs."]
    verdict = {}
    for m in S:
        rep.append(f"\n{m}")
        for label, (lo, hi), lo_ov in cells:
            sel_s = (s_smin >= lo) & (s_smin < hi)
            sel_r = (r_smin >= lo) & (r_smin < hi)
            if lo_ov is not None:
                sel_s &= (s_ov < ov_cut) == lo_ov
                sel_r &= (r_ov < ov_cut) == lo_ov
            if sel_s.sum() < 100 or sel_r.sum() < 30:
                rep.append(f"  {label:42s} n_sim {sel_s.sum():5d} n_real {sel_r.sum():5d}  -")
                continue
            th = np.quantile(S[m][sel_s], 1 - FPR_SIM)
            flag = Rs[m][sel_r] > th
            lo_ci, hi_ci = boot_fpr(flag, src_a[sel_r], src_b[sel_r], names)
            ok = flag.mean() <= FPR_MAX
            if lo_ov is None and label.startswith("S/N >= 25"):
                verdict[m] = ok
            rho_rt = spearmanr(Rs[m][sel_r], T1[m][sel_r]).statistic
            rho_tt = spearmanr(T2[m][sel_r], T1[m][sel_r]).statistic
            rep.append(f"  {label:42s} n_sim {sel_s.sum():5d} n_real {sel_r.sum():5d}  real FPR {flag.mean():.3f} "
                       f"[{lo_ci:.3f}, {hi_ci:.3f}] {'PASS' if ok else 'FAIL'}  twin Spearman real-sim {rho_rt:.2f} / sim-sim {rho_tt:.2f}")
    rep.append("\nheadline (S/N >= 25) verdicts: " + ", ".join(f"{m} {'PASS' if v else 'FAIL'}" for m, v in verdict.items()))
    txt = "\n".join(rep)
    print(txt)
    (OUT / "stage3_val.txt").write_text(txt + "\n")
    np.savez(OUT / "stage3_val_scores.npz", r_smin=r_smin, r_ov=r_ov, src_a=src_a, src_b=src_b, s_smin=s_smin, s_ov=s_ov,
             **{f"real|{k}": v for k, v in Rs.items()}, **{f"sim|{k}": v for k, v in S.items()},
             **{f"twin1|{k}": v for k, v in T1.items()}, **{f"twin2|{k}": v for k, v in T2.items()})


if __name__ == "__main__":
    main()
