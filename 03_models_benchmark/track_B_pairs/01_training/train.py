"""Stage 2: train one learned method on on-the-fly pairs, select on val_bright. Plan 2026-11-06_1223.

Usage (venv python, from this folder):
  python -I train.py --model 6 --seed 0 --steps N    # one run -> outputs/m6_s0/
  python -I train.py --model 6 --overfit             # self-check: memorise one batch
  python -I train.py --model 6 --shuffle --steps N   # self-check: shuffled labels must give AUC ~ 0.5
Test sets are never read here.
"""
import argparse, csv, sys, time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, IterableDataset, get_worker_info

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "02_benchmark"), str(HERE.parents[2] / "02_injection_labelling" / "01_injection")]
from inject import BRIGHT, KINDS, SNR_MIN, load_pools, load_set, make_pair
from metrics import recall_at_fpr
from models import MODELS, lensed_score

BATCH, LR, WARMUP = 64, 1e-3, 1000  # warmup: without it the head ReLUs died in 4 of 12 runs (update 2026-11-06_2015)


class Pairs(IterableDataset):
    """Endless batches from the train split; S/N floor mixed half and half, as for the GBM."""

    def __init__(self, seed):
        self.seed = seed

    def __iter__(self):
        P = load_pools()["train"]
        w = get_worker_info()
        rng = np.random.default_rng([self.seed, w.id if w else 0])
        while True:
            A, Bx, Y = [], [], []
            for _ in range(BATCH):
                xa, xb, _, _, y, _ = make_pair(KINDS[rng.integers(4)], rng, P, False, BRIGHT if rng.random() < 0.5 else SNR_MIN)
                A.append(xa); Bx.append(xb); Y.append(y)
            yield torch.from_numpy(np.stack(A)).half(), torch.from_numpy(np.stack(Bx)).half(), torch.tensor(Y)


@torch.no_grad()
def scores(model, A, Bx, dev, bs=128):
    """Lensed log-odds averaged over both member orders."""
    model.eval()
    out = []
    for i in range(0, len(A), bs):
        a, b = A[i:i + bs].to(dev), Bx[i:i + bs].to(dev)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            s = lensed_score(model(a, b).float()) + lensed_score(model(b, a).float())
        out.append(s.float().cpu() / 2)
    model.train()
    return torch.cat(out).numpy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=int, required=True, choices=sorted(MODELS))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--eval-every", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--overfit", action="store_true")
    ap.add_argument("--shuffle", action="store_true")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    torch.manual_seed(a.seed)
    dev = "cuda"
    model = MODELS[a.model]().to(dev)
    opt = torch.optim.AdamW(model.parameters(), LR, weight_decay=1e-4)
    S = torch.optim.lr_scheduler
    sched = S.SequentialLR(opt, [S.LinearLR(opt, 1e-3, 1.0, WARMUP), S.CosineAnnealingLR(opt, a.steps - WARMUP)], [WARMUP])
    loader = DataLoader(Pairs(1000 + 10 * a.model + a.seed), batch_size=None, num_workers=0 if a.overfit else a.workers,
                        persistent_workers=not a.overfit, prefetch_factor=None if a.overfit else 4, pin_memory=True)
    it = iter(loader)

    if a.overfit:
        xa, xb, y = (t.to(dev) for t in next(it))
        for s in range(1500):
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss = torch.nn.functional.cross_entropy(model(xa, xb).float(), y)
            opt.zero_grad(); loss.backward(); opt.step()
        acc = (model(xa, xb).argmax(1) == y).float().mean().item()
        print(f"overfit one batch, model {a.model}: loss {loss.item():.4f}, accuracy {acc:.3f}")
        assert acc > 0.95
        return

    A, Bx, _, _, Y = load_set("val_bright")
    keep = Y != 2  # primary task: lensed vs repeat + impostor
    A, Bx = torch.from_numpy(A[keep]).half(), torch.from_numpy(Bx[keep]).half()
    pos = Y[keep] == 0
    out = HERE / "outputs" / (f"m{a.model}_s{a.seed}" + a.tag)
    out.mkdir(parents=True, exist_ok=True)
    log = csv.writer(open(out / "log.csv", "w", newline=""))
    log.writerow(["step", "loss", "val_recall", "val_auc", "seconds"])
    best, t0, run = -1.0, time.time(), []
    for step in range(1, a.steps + 1):
        xa, xb, y = next(it)
        xa, xb, y = xa.to(dev, non_blocking=True), xb.to(dev, non_blocking=True), y.to(dev, non_blocking=True)
        if a.shuffle:
            y = y[torch.randperm(len(y), device=dev)]
        with torch.autocast("cuda", dtype=torch.bfloat16):
            loss = torch.nn.functional.cross_entropy(model(xa, xb).float(), y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step(); sched.step()
        run.append(loss.item())
        if step % a.eval_every == 0 or step == a.steps:
            from sklearn.metrics import roc_auc_score
            v = scores(model, A, Bx, dev)
            assert np.isfinite(v).all(), "non-finite scores"
            r, auc = recall_at_fpr(v[pos], v[~pos]), roc_auc_score(pos, v)
            el = time.time() - t0
            log.writerow([step, np.mean(run), r, auc, round(el)])
            print(f"step {step} loss {np.mean(run):.4f} val recall {r:.3f} auc {auc:.3f}  {el:.0f}s  {step * BATCH / el:.0f} pairs/s", flush=True)
            run = []
            if r > best:
                best = r
                torch.save(model.state_dict(), out / "best.pt")
                np.save(out / "val_bright_scores.npy", v)
    print(f"best val recall {best:.3f}")
    # workers hold endless iterators: leave without waiting on them
    del it, loader


if __name__ == "__main__":
    main()
