import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from inject import load_pools, gen_set, member_stats
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import cross_val_score
P = load_pools()["train"]; c = P.c
sidx = {s: k for k, s in enumerate(np.unique(c["source"]))}
F, Y = [], []
for i, xa, xb, ma, mb, y, info in gen_set(P, 4000 * 3 // 2, 999, False):
    if y == 2: continue
    ea, eb = (info["ext_lo_a"], info["ext_hi_a"]), (info["ext_lo_b"], info["ext_hi_b"])
    if info["swapped"]: ea, eb = eb, ea
    sa, sb = member_stats(xa, ma, *ea), member_stats(xb, mb, *eb)
    ti = info["ti_b"] if info["swapped"] else info["ti_a"]
    ba, bb = (info["bi_b"], info["bi_a"]) if info["swapped"] else (info["bi_a"], info["bi_b"])
    F.append([(ma & mb).sum() / (ma | mb).sum(), np.log(sa["snr_box"] / max(sb["snr_box"], 1e-3)), sa["centre"] - sb["centre"],
              sidx[c["source"][c["bg_file"][ba]]], sidx[c["source"][c["bg_file"][bb]]], c["mjd_400"][c["bg_file"][ba]], c["mjd_400"][c["bg_file"][bb]],
              *c["par"][ti], c["snr_fitb"][ti], c["model_snr"][ti], np.log(info["snr_a"] / info["snr_b"])]); Y.append(y)
F, Y = np.array(F, float), np.array(Y)
G = {"mask_overlap": [0], "measured_snr_ratio": [1], "centre_offset": [2], "background_src_mjd": [3, 4, 5, 6], "template_params_one": list(range(7, 15)), "injected_snr_ratio": [15]}
gbm = HistGradientBoostingClassifier(random_state=0)
print("n", len(Y), "all", cross_val_score(gbm, F[:, :15], Y, cv=5, scoring="roc_auc").mean().round(3))
for g, ix in G.items():
    print(f"{g:22s} alone {cross_val_score(gbm, F[:, ix], Y, cv=5, scoring='roc_auc').mean():.3f}")
print("centre offset |d| median lensed/repeat", np.median(np.abs(F[Y == 0, 2])), np.median(np.abs(F[Y == 1, 2])))
