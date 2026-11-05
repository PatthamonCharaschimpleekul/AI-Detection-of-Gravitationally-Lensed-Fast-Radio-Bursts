"""How much does a single member (no pair comparison) reveal impostor vs repeat? GBM on order-invariant
per-member stats (box S/N, mask fraction, centre) of both members, 5-fold CV, train split."""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import cross_val_score
from inject import load_pools, make_pair, member_stats
P = load_pools()["train"]
F, Y, T = [], [], []
for q in range(4000):
    kind = ("repeat", "impostor")[q % 2]
    xa, xb, ma, mb, y, info = make_pair(kind, np.random.default_rng([555, q]), P)
    ea, eb = (info["ext_lo_a"], info["ext_hi_a"]), (info["ext_lo_b"], info["ext_hi_b"])
    if info["swapped"]:
        ea, eb = eb, ea
    sa, sb = member_stats(xa, ma, *ea), member_stats(xb, mb, *eb)
    v = sorted([(sa["snr_box"], sa["mask_frac"], sa["centre"]), (sb["snr_box"], sb["mask_frac"], sb["centre"])])
    F.append([*v[0], *v[1]]); Y.append(y == 3); T.append(info["imp_type"])
F, Y, T = np.array(F), np.array(Y), np.array(T)
gbm = HistGradientBoostingClassifier(random_state=0)
print("single-member stats, impostor vs repeat: AUC %.3f" % cross_val_score(gbm, F, Y, cv=5, scoring="roc_auc").mean())
for t in ("I1", "I2", "I1+I2"):
    s = ~Y | (T == t)
    print(f"  only {t:6s} impostors vs repeat: AUC {cross_val_score(gbm, F[s], Y[s], cv=5, scoring='roc_auc').mean():.3f} (n={s.sum()})")
