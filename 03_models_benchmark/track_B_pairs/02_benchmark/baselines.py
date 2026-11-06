"""Stage 1: baselines 1-3 of the Track B ladder, on the val sets only.

Plan: plan/2026-11-06_1223_phase3-trackB-benchmark.md
Usage: python -I baselines.py        (venv python; writes outputs/stage1_val.txt and outputs/scores_<set>.npz)

Everything here reads pixels only: no ext_lo/hi, no fitburst parameters, so the same functions run on
real pairs. Test sets are refused until Stage 5.
"""
import csv, sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[2] / "02_injection_labelling" / "01_injection")]
from inject import DT_MS, KDM, KINDS, MAN, NF, SETS, SNR_MIN, WIN, kind_of, load_pools, make_pair, xcorr, xcorr_smooth
from metrics import FPR, boot_recall, recall_at_fpr

OUT = HERE / "outputs"
PAD, MAXLAG = 6, 24
TAUS, DDMS = (0.0, 0.1, 0.3, 1.0, 3.0), (0.0, 0.1, -0.1, 0.3, -0.3)  # ms at 600 MHz; pc/cc, symmetric on purpose
B1_BLK, B2_BLK = (1, 4, 16), (1, 4, 16)
N_TRAIN = 30000  # GBM pairs per S/N floor
METHODS = [f"b1_blk{b}" for b in B1_BLK] + [f"b2_blk{b}" for b in B2_BLK]
FEATS = ("snr", "boxcar_w", "width", "nu_c", "bandwidth", "slope", "dm_slope")
FEAT_NAMES = [f"|d {k}|" for k in FEATS] + [f"mean {k}" for k in FEATS]


def find_box(x, m):
    """Burst time window from pixels: best boxcar on the band mean, padded. Same function for sim and real."""
    band = x[m].mean(0) * np.sqrt(m.sum())
    best, c, W = -np.inf, WIN // 2, 1
    for w in (1, 2, 4, 8, 16, 32):
        s = np.convolve(band, np.ones(w), "same") / np.sqrt(w)
        if s.max() > best:
            best, c, W = s.max(), int(s.argmax()), w
    return max(c - W // 2 - PAD, 0), min(c + W - W // 2 + PAD, WIN), float(best), W


def boxed(x, box):
    y = np.zeros_like(x)
    y[:, box[0]:box[1]] = x[:, box[0]:box[1]]
    return y


def b1(xa, ma, xb, mb, ba, bb, blk):
    """Cross-correlation inside the on-pulse boxes, best lag, on common channels (blk-channel averaged)."""
    A, Bx = boxed(xa, ba), boxed(xb, bb)
    return xcorr(A, ma, Bx, mb, MAXLAG) if blk == 1 else xcorr_smooth(A, ma, Bx, mb, blk, MAXLAG)


def b2(xa, ma, xb, mb, ba, bb, freq, blk):
    """Physics statistic: best fit of one burst to the other through a scattering kernel, residual DM, lag and
    free amplitude, both directions. Correlation is divided by the noise attenuation of each box, so the
    score does not simply rise with S/N."""
    c = ma & mb
    if blk > 1:  # blocks of channels with enough common valid channels
        w = c.reshape(-1, blk).sum(1)
        keep = w >= blk // 4
        red = lambda x: (np.where(c[:, None], x, 0).reshape(-1, blk, WIN).sum(1) / np.maximum(w, 1)[:, None])[keep]
        A, Bx, f = red(boxed(xa, ba)), red(boxed(xb, bb)), freq.reshape(-1, blk).mean(1)[keep]
        nvar = (1.0 / np.maximum(w, 1))[keep]  # noise variance per block
    else:
        A, Bx, f, nvar = boxed(xa, ba)[c], boxed(xb, bb)[c], freq[c], np.ones(c.sum())
    n = 2 * WIN
    k = np.fft.rfftfreq(n)
    t = np.arange(WIN) * DT_MS
    delay = {d: np.exp(-2j * np.pi * k[None, :] * (KDM * d * (f ** -2.0 - 600.0 ** -2.0) / DT_MS)[:, None]) for d in DDMS}
    FA, FB = np.fft.rfft(A, n, axis=1), np.fft.rfft(Bx, n, axis=1)
    ea, eb = (A ** 2).sum(), (Bx ** 2).sum()
    na, nb = nvar.sum() * (ba[1] - ba[0]), nvar.sum() * (bb[1] - bb[0])
    atten = np.sqrt(max(1 - na / max(ea, 1e-9), 0.02) * max(1 - nb / max(eb, 1e-9), 0.02))
    best = -np.inf
    for F1, F2, e2 in ((FA, FB, eb), (FB, FA, ea)):
        for tau in TAUS:
            if tau > 0:
                ker = np.exp(-t[None, :] / (tau * (f / 600.0) ** -4.0)[:, None])
                G = F1 * np.fft.rfft(ker / ker.sum(1, keepdims=True), n, axis=1)
            else:
                G = F1
            e1 = (np.fft.irfft(G, n, axis=1) ** 2).sum()
            C = G * np.conj(F2)
            for d in DDMS:
                cc = np.fft.irfft((C * delay[d]).sum(0), n)
                best = max(best, max(cc[:MAXLAG + 1].max(), cc[-MAXLAG:].max()) / np.sqrt(e1 * e2 + 1e-30))
    return float(best / atten)


def member_feats(x, m, box, freq):
    """Seven measured burst properties: S/N, boxcar width, profile width, centre frequency, bandwidth,
    spectral slope, residual-DM slope (time centroid against nu^-2 over four sub-bands)."""
    lo, hi, snr, W = box
    sp = np.where(m, x[:, lo:hi].sum(1), 0.0)
    sm = np.clip(np.convolve(sp, np.ones(16) / 16, "same"), 0, None) + 1e-9
    nu = (sm * freq).sum() / sm.sum()
    bw = np.sqrt((sm * (freq - nu) ** 2).sum() / sm.sum())
    slope = np.polyfit((freq[m] - 600) / 200, sm[m], 1)[0] / sm[m].mean()
    tt = np.arange(lo, hi)
    p = np.clip(x[m, lo:hi].mean(0), 0, None) + 1e-9
    tc = (p * tt).sum() / p.sum()
    wid = np.sqrt((p * (tt - tc) ** 2).sum() / p.sum())
    cen, inv = [], []
    for q in np.array_split(np.flatnonzero(m), 4):
        pq = np.clip(x[q, lo:hi].mean(0), 0, None) + 1e-9
        cen.append((pq * tt).sum() / pq.sum())
        inv.append(freq[q].mean() ** -2.0 * 1e6)
    return [snr, W, wid, nu, bw, slope, np.polyfit(inv, cen, 1)[0]]


def score_pair(xa, ma, xb, mb, freq):
    ba, bb = find_box(xa, ma), find_box(xb, mb)
    s = [b1(xa, ma, xb, mb, ba, bb, b) for b in B1_BLK] + [b2(xa, ma, xb, mb, ba, bb, freq, b) for b in B2_BLK]
    fa, fb = np.array(member_feats(xa, ma, ba, freq)), np.array(member_feats(xb, mb, bb, freq))
    return s, np.concatenate([np.abs(fa - fb), (fa + fb) / 2])


def init():
    global POOLS
    POOLS = load_pools()


def work(job):
    """job = (split, kind, seed list, wide, floor); exactly the call gen_set makes for a frozen pair."""
    split, kind, seed, wide, floor = job
    P = POOLS[split]
    xa, xb, ma, mb, y, info = make_pair(kind, np.random.default_rng(seed), P, wide, floor)
    s, f = score_pair(xa, ma, xb, mb, P.c["freq_mhz"])
    return s, f, y, info["src_a"], min(info["snr_a"], info["snr_b"]), info["imp_type"], info["tmpl_a"], info["snr_a"]


def run(pool, jobs):
    r = pool.map(work, jobs, chunksize=50)
    return dict(s=np.array([x[0] for x in r]), f=np.array([x[1] for x in r]), y=np.array([x[2] for x in r]),
                src=np.array([x[3] for x in r]), snr=np.array([x[4] for x in r]), imp=np.array([x[5] for x in r]),
                tmpl=np.array([x[6] for x in r]), snr_a=np.array([x[7] for x in r]))


def frozen(pool, name):
    assert "test" not in name and name != "stress", "test sets stay closed until Stage 5"
    split, n, seed, wide, floor = SETS[name]
    d = run(pool, [(split, kind_of(i, floor > SNR_MIN), [seed, i], wide, floor) for i in range(n)])
    man = list(csv.DictReader(open(MAN / f"{name}.csv")))  # these jobs must be the manifest's pairs
    assert [r["tmpl_a"] for r in man] == d["tmpl"].tolist()
    assert np.allclose([float(r["snr_a"]) for r in man], d["snr_a"])
    return d


def main():
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score
    OUT.mkdir(exist_ok=True)
    init()
    P = POOLS["val"]
    freq = P.c["freq_mhz"]
    # self-checks: order invariance, and an identical pair must score at the top
    xa, xb, ma, mb, _, _ = make_pair("repeat", np.random.default_rng(1), P, False, 25.0)
    s1, f1 = score_pair(xa, ma, xb, mb, freq)
    s2, f2 = score_pair(xb, mb, xa, ma, freq)
    assert np.allclose(s1, s2) and np.allclose(f1, f2), "scores depend on member order"
    same, same_f = score_pair(xa, ma, xa, ma, freq)
    assert abs(same[0] - 1) < 1e-6 and not same_f[:7].any()

    with Pool(16, initializer=init) as pool:
        tr = run(pool, [("train", KINDS[i % 4], [300 + (i >= N_TRAIN), i], False, 25.0 if i >= N_TRAIN else SNR_MIN)
                        for i in range(2 * N_TRAIN)])
        data = {n: frozen(pool, n) for n in ("val", "val_bright")}
    gbm = HistGradientBoostingClassifier(random_state=0).fit(tr["f"], tr["y"] == 0)
    names = METHODS + ["b3_gbm"]
    rep = []
    for n, d in data.items():
        d["sc"] = {k: d["s"][:, i] for i, k in enumerate(METHODS)} | {"b3_gbm": gbm.predict_proba(d["f"])[:, 1]}
        np.savez(OUT / f"scores_{n}.npz", y=d["y"], src=d["src"], snr=d["snr"], imp=d["imp"], **d["sc"])
    d = data["val_bright"]
    t = d["y"] != 2  # task: lensed vs repeat + impostor
    pos, src = d["y"][t] == 0, d["src"][t]
    boot = boot_recall({k: v[t] for k, v in d["sc"].items()}, pos, src)
    rep.append(f"val_bright primary: recall at {FPR:.0%} FPR, lensed vs repeat+impostor, source bootstrap 95% CI (n={t.sum()})")
    point = {}
    for k in names:
        v = d["sc"][k][t]
        point[k] = recall_at_fpr(v[pos], v[~pos])
        lo, hi = np.percentile(boot[k], [2.5, 97.5])
        rep.append(f"  {k:9s} {point[k]:.3f} [{lo:.3f}, {hi:.3f}]   AUC {roc_auc_score(pos, v):.3f}")
    best = {f: max((k for k in names if k.startswith(f)), key=point.get) for f in ("b1", "b2", "b3")}
    win = max(best.values(), key=point.get)
    rep.append(f"best variant per method: {best}; best of 1-3 for the primary comparison: {win}")
    rep.append(f"recall difference of each method vs {win}, same resamples:")
    for k in best.values():
        dd = boot[k] - boot[win]
        rep.append(f"  {k:9s} {dd.mean():+.3f} [{np.percentile(dd, 2.5):+.3f}, {np.percentile(dd, 97.5):+.3f}]")
    rep.append(f"share called lensed at the 1% FPR threshold (val_bright), by negative type:")
    for k in best.values():
        v = d["sc"][k]
        th = np.quantile(v[t][~pos], 1 - FPR)
        cells = [f"repeat {(v[d['y'] == 1] > th).mean():.3f}", f"unrelated {(v[d['y'] == 2] > th).mean():.3f}"]
        cells += [f"{i} {(v[d['imp'] == i] > th).mean():.3f}" for i in ("I1", "I2", "I1+I2")]
        rep.append(f"  {k:9s} " + "  ".join(cells))
    from sklearn.inspection import permutation_importance
    pi = permutation_importance(gbm, d["f"][t], pos, scoring="roc_auc", n_repeats=5, random_state=0)
    order = np.argsort(-pi.importances_mean)[:6]
    rep.append("b3 permutation importance (AUC drop, val_bright): " +
               ", ".join(f"{FEAT_NAMES[i]} {pi.importances_mean[i]:.3f}" for i in order))
    d = data["val"]
    rep.append("val AUC lensed vs repeat+impostor by min S/N:")
    for lo, hi in ((10, 15), (15, 25), (25, 50), (50, 1e9)):
        s = (d["snr"] >= lo) & (d["snr"] < hi) & (d["y"] != 2)
        rep.append(f"  {lo}-{hi if hi < 1e9 else 'inf'} (n={s.sum()}): " +
                   "  ".join(f"{k} {roc_auc_score(d['y'][s] == 0, d['sc'][k][s]):.3f}" for k in best.values()))
    txt = "\n".join(rep)
    print(txt)
    (OUT / "stage1_val.txt").write_text(txt + "\n")


if __name__ == "__main__":
    main()
