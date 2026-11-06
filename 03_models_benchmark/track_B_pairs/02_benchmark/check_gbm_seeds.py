"""How much does baseline 3 move with the GBM seed? val_bright only."""
import numpy as np
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent))
from multiprocessing import Pool
from sklearn.ensemble import HistGradientBoostingClassifier
import baselines as b
from metrics import recall_at_fpr

if __name__ == "__main__":
    with Pool(16, initializer=b.init) as pool:
        tr = b.run(pool, [("train", b.KINDS[i % 4], [300 + (i >= b.N_TRAIN), i], False, 25.0 if i >= b.N_TRAIN else b.SNR_MIN)
                          for i in range(2 * b.N_TRAIN)])
        d = b.frozen(pool, "val_bright")
    t = d["y"] != 2
    pos = d["y"][t] == 0
    r = []
    for s in range(8):
        v = HistGradientBoostingClassifier(random_state=s).fit(tr["f"], tr["y"] == 0).predict_proba(d["f"][t])[:, 1]
        r.append(recall_at_fpr(v[pos], v[~pos]))
    print("b3 recall at 1% FPR over 8 GBM seeds:", np.round(r, 3), "mean %.3f sd %.3f" % (np.mean(r), np.std(r, ddof=1)))
