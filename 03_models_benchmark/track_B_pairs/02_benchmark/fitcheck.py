"""Over/underfitting check (plan 2026-11-10_0900, part B).
1 learning curves from the Stage 2 logs; 2 seen-template set (train_bright_chk) vs val_bright: 4-class cross-entropy,
accuracy, AUC, recall at 1% FPR; 3 confusion matrices; 4 dev-fold model 6: a seen fold vs its held-out fold.
Usage: python -I fitcheck.py      -> outputs/fitcheck.txt
"""
import csv
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "01_training"), str(HERE.parents[2] / "02_injection_labelling" / "01_injection")]
from inject import BRIGHT, KINDS, gen_set, load_fold_set, load_pools, load_set
from metrics import recall_at_fpr
from stage3_transfer import CKPTS

TRN = HERE.parent / "01_training" / "outputs"
CHK_SEED, CHK_N = 211, 8000  # seen-template check set: train pool, floor 25, four kinds cycled
out = []


def say(s=""):
    print(s, flush=True)
    out.append(s)


def probs(net, A, B, bs=256):
    """4-class probabilities averaged over both member orders."""
    import torch
    net.eval()
    P = []
    with torch.no_grad():
        for i in range(0, len(A), bs):
            a = torch.from_numpy(A[i:i + bs]).half().cuda()
            b = torch.from_numpy(B[i:i + bs]).half().cuda()
            with torch.autocast("cuda", dtype=torch.bfloat16):
                p = (torch.softmax(net(a, b).float(), 1) + torch.softmax(net(b, a).float(), 1)) / 2
            P.append(p.cpu().numpy())
    return np.concatenate(P)


def metrics(p, y):
    from sklearn.metrics import roc_auc_score
    ce = float(-np.log(np.clip(p[np.arange(len(y)), y], 1e-7, 1)).mean())
    acc = float((p.argmax(1) == y).mean())
    t = y != 2
    s = np.log(np.clip(p[t, 0], 1e-7, 1)) - np.log(np.clip(1 - p[t, 0], 1e-7, 1))
    pos = y[t] == 0
    return ce, acc, roc_auc_score(pos, s), recall_at_fpr(s[pos], s[~pos])


def load_net(path, m):
    import torch
    from models import MODELS
    net = MODELS[m]().cuda()
    net.load_state_dict(torch.load(path, map_location="cuda"))
    return net


def seen_unseen_sets(pools):
    """(train_bright_chk: new pairs from seen train templates, val_bright: unseen sources), float16 to save RAM."""
    A, B, Y = [], [], []
    for _, xa, xb, ma, mb, y, _ in gen_set(pools["train"], CHK_N, CHK_SEED, False, True, BRIGHT):
        A.append(xa.astype(np.float16)); B.append(xb.astype(np.float16)); Y.append(y)
    VA, VB, _, _, VY = load_set("val_bright", pools)
    return (np.stack(A), np.stack(B), np.array(Y)), (VA.astype(np.float16), VB.astype(np.float16), VY)


def main():
    say("1. learning curves (val_bright recall every 1000 steps; training loss = running mean)")
    say(f"  {'run':7s} {'best@step':>12s} {'final':>6s} {'drop':>6s} {'slope last5/1k':>15s} {'loss 1k->20k':>14s}  reading")
    for m, s in CKPTS:
        r = list(csv.DictReader(open(TRN / f"m{m}_s{s}" / "log.csv")))
        v = np.array([float(x["val_recall"]) for x in r])
        L = np.array([float(x["loss"]) for x in r])
        b = int(v.argmax())
        slope = np.polyfit(np.arange(5), v[-5:], 1)[0]
        lslope = np.polyfit(np.arange(5), L[-5:], 1)[0]
        read = ("did not train" if v.max() < 0.05 else "still rising: underfit" if slope > 0.01 or lslope < -0.01
                else "peaked and fell: overfit" if v.max() - v[-1] > 0.05 else "plateau")
        say(f"  m{m}_s{s}  {v[b]:.3f}@{r[b]['step']:>6s} {v[-1]:6.3f} {v[b] - v[-1]:6.3f} {slope:+15.4f} {L[0]:6.3f}->{L[-1]:.3f}  {read}")

    pools = load_pools()
    (TA, TB, TY), (VA, VB, VY) = seen_unseen_sets(pools)
    say(f"\n2. seen templates (train_bright_chk: {CHK_N} new pairs from train templates, seed {CHK_SEED}) vs unseen (val_bright)")
    say(f"  {'run':7s} {'CE train/val':>14s} {'acc train/val':>14s} {'AUC train/val':>14s} {'recall train/val':>17s}  gaps CE / recall")
    conf = {}
    for m, s in CKPTS:
        net = load_net(TRN / f"m{m}_s{s}" / "best.pt", m)
        pt, pv = probs(net, TA, TB), probs(net, VA, VB)
        a, b = metrics(pt, TY), metrics(pv, VY)
        flag = "  TEMPLATE OVERFIT" if (b[0] - a[0] > 0.10 or a[3] - b[3] > 0.10) else ""
        say(f"  m{m}_s{s}  {a[0]:.3f}/{b[0]:.3f}  {a[1]:.3f}/{b[1]:.3f}  {a[2]:.3f}/{b[2]:.3f}  {a[3]:.3f}/{b[3]:.3f}"
            f"     {b[0] - a[0]:+.3f} / {a[3] - b[3]:+.3f}{flag}")
        if (m, s) == (6, 0):
            conf = {"train": (pt.argmax(1), TY), "val": (pv.argmax(1), VY)}
    say("\n3. model 6 seed 0, 4-class confusion (rows true, columns predicted: " + ", ".join(KINDS) + ")")
    for k, (pr, y) in conf.items():
        M = np.array([[((y == i) & (pr == j)).sum() for j in range(4)] for i in range(4)])
        say(f"  {k}:")
        for i in range(4):
            say(f"    {KINDS[i]:9s} " + " ".join(f"{x / M[i].sum():6.3f}" for x in M[i]))

    say("\n4. dev-fold model 6 (final checkpoints): a fold it trained on vs its held-out fold")
    del TA, TB, VA, VB
    half = lambda r: (r[0].astype(np.float16), r[1].astype(np.float16), r[2])
    sets = {}
    for k in range(5):
        j = (k + 1) % 5
        for q in (k, j):
            sets.setdefault(q, half(load_fold_set("dev", q, pools)))
        sets = {q: v for q, v in sets.items() if q in (k, j)}  # keep two sets in RAM
        net = load_net(TRN / "folds_dev" / f"m6_f{k}" / "final.pt", 6)
        a = metrics(probs(net, sets[j][0], sets[j][1]), sets[j][2])
        b = metrics(probs(net, sets[k][0], sets[k][1]), sets[k][2])
        say(f"  fold {k}: seen (dev_f{j}) CE {a[0]:.3f} recall {a[3]:.3f}  |  held-out CE {b[0]:.3f} recall {b[3]:.3f}  |  gaps {b[0] - a[0]:+.3f} / {a[3] - b[3]:+.3f}")
    (HERE / "outputs" / "fitcheck.txt").write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
