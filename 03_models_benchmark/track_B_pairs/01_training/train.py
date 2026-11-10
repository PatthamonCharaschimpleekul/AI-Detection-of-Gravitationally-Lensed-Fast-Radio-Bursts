"""Stage 2: train one learned method on on-the-fly pairs, select on val_bright. Plan 2026-11-06_1223.

Usage (venv python, from this folder):
  python -I train.py --model 6 --seed 0 --steps N    # one run -> outputs/m6_s0/
  python -I train.py --model 6 --overfit             # self-check: memorise one batch
  python -I train.py --model 6 --shuffle --steps N   # self-check: shuffled labels must give AUC ~ 0.5
  python -I train.py --model 6 --fold K --scheme dev --steps 20000   # grouped fold K (plan 2026-11-08_0845) -> outputs/folds_dev/m6_f{K}/
  Stage 4 ablations (model 6): --no-align, --hardneg, --no-impostors; each adds its name to the output folder.
Test sets are never read here. Scheme 'all' trains on test-split sources, so it refuses to run before the benchmark-v1 tag (F8).
"""
import argparse, csv, sys, time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, IterableDataset, get_worker_info

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "02_benchmark"), str(HERE.parents[2] / "02_injection_labelling" / "01_injection")]
from inject import BRIGHT, KINDS, SNR_MIN, fold_pools, load_fold_set, load_pools, load_set, make_pair
from metrics import recall_at_fpr
from models import MODELS, lensed_score

BATCH, LR, WARMUP = 64, 1e-3, 1000  # warmup: without it the head ReLUs died in 4 of 12 runs (update 2026-11-06_2015)
COLLAPSED = np.log(4) - 0.01  # F6: mean loss over the last 1000 steps at or above this = collapsed run


HARDNEG_K = 4  # Stage 4: a hard repeat is the most template-similar of K candidate repeat pairs


def template_sim(c, ta, tb):
    """Correlation of two noise-free templates over the whole image (no noise, no nuisances)."""
    a, b = c["T"][ta].ravel(), c["T"][tb].ravel()
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


class Pairs(IterableDataset):
    """Endless batches from the train split; S/N floor mixed half and half, as for the GBM.
    Plan 2026-11-10_1300 options: merge (unrelated -> repeat target), bandpass (random smooth bandpass per member).
    Stage 4 options: kinds without impostors; half of the repeats replaced by the most similar of HARDNEG_K draws.
    With all options off, the rng draws are exactly those of the original loop."""

    def __init__(self, seed, fold=None, merge=False, bandpass=False, kinds=KINDS, hardneg=False):
        self.seed, self.fold = seed, fold  # fold = (scheme, k): train on the other folds' sources
        self.merge, self.bandpass = merge, bandpass  # plan 2026-11-10_1300: M (unrelated -> repeat target), P
        self.kinds, self.hardneg = kinds, hardneg  # Stage 4 ablations

    def __iter__(self):
        P = load_pools()["train"] if self.fold is None else fold_pools(load_pools(), *self.fold)[0]
        w = get_worker_info()
        rng = np.random.default_rng([self.seed, w.id if w else 0])
        while True:
            A, Bx, Y = [], [], []
            for _ in range(BATCH):
                kind = self.kinds[rng.integers(len(self.kinds))]
                floor = BRIGHT if rng.random() < 0.5 else SNR_MIN
                if self.hardneg and kind == "repeat" and rng.random() < 0.5:
                    cands = [make_pair(kind, rng, P, False, floor, self.bandpass) for _ in range(HARDNEG_K)]
                    xa, xb, _, _, y, _ = max(cands, key=lambda p: template_sim(P.c, p[5]["ti_a"], p[5]["ti_b"]))
                else:
                    xa, xb, _, _, y, _ = make_pair(kind, rng, P, False, floor, self.bandpass)
                y = 1 if self.merge and y == 2 else y
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
    ap.add_argument("--fold", type=int)
    ap.add_argument("--scheme", choices=("dev", "all"), default="dev")
    ap.add_argument("--merge-unrelated", action="store_true")  # plan 2026-11-10_1300, M
    ap.add_argument("--bandpass", action="store_true")  # plan 2026-11-10_1300, P
    ap.add_argument("--no-align", action="store_true", help="Stage 4: model 6 without the correlation alignment")
    ap.add_argument("--hardneg", action="store_true", help="Stage 4: hard-negative oversampling of repeats")
    ap.add_argument("--no-impostors", action="store_true", help="Stage 4: train without the impostor class")
    a = ap.parse_args()
    a.tag += "".join(f"_{k}" for k, v in (("noalign", a.no_align), ("hardneg", a.hardneg), ("noimp", a.no_impostors)) if v)
    if a.fold is not None:
        return train_fold(a)
    torch.manual_seed(a.seed)
    dev = "cuda"
    model, opt, sched, loader = setup(a.model, a.steps, 1000 + 10 * a.model + a.seed, None, 0 if a.overfit else a.workers,
                                      a.merge_unrelated, a.bandpass, align=not a.no_align,
                                      kinds=tuple(k for k in KINDS if not (a.no_impostors and k == "impostor")), hardneg=a.hardneg)
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


def setup(model_id, steps, stream, fold=None, workers=14, merge=False, bandpass=False, align=True, kinds=KINDS, hardneg=False):
    assert align or model_id == 6, "--no-align applies to model 6 only"
    model = (MODELS[model_id]() if align else MODELS[6](align=False)).to("cuda")
    opt = torch.optim.AdamW(model.parameters(), LR, weight_decay=1e-4)
    S = torch.optim.lr_scheduler
    sched = S.SequentialLR(opt, [S.LinearLR(opt, 1e-3, 1.0, WARMUP), S.CosineAnnealingLR(opt, steps - WARMUP)], [WARMUP])
    loader = DataLoader(Pairs(stream, fold, merge, bandpass, kinds, hardneg), batch_size=None, num_workers=workers, persistent_workers=workers > 0,
                        prefetch_factor=4 if workers else None, pin_memory=True)
    return model, opt, sched, loader


def train_fold(a):
    """F4-F6: Stage 2 settings, one seed per fold, final checkpoint (no selection), held-out fold set scored once."""
    if a.scheme == "all":
        import subprocess
        tag = subprocess.run(["git", "tag", "-l", "benchmark-v1"], capture_output=True, text=True, cwd=HERE).stdout.strip()
        assert tag == "benchmark-v1", "scheme 'all' opens the test sources: only after the benchmark-v1 tag (plan 2026-11-08_0845 F8)"
    A, Bx, Y, src = load_fold_set(a.scheme, a.fold)  # before the workers start: 2 x 1.2 GB float32 at the end ran out of RAM
    A, Bx = torch.from_numpy(A).half(), torch.from_numpy(Bx).half()
    stream = 2000 + 10 * a.model + a.fold
    torch.manual_seed(stream)
    dev = "cuda"
    model, opt, sched, loader = setup(a.model, a.steps, stream, (a.scheme, a.fold), a.workers, a.merge_unrelated, a.bandpass)
    it = iter(loader)
    out = HERE / "outputs" / f"folds_{a.scheme}" / (f"m{a.model}_f{a.fold}" + a.tag)
    out.mkdir(parents=True, exist_ok=True)
    fh = open(out / "log.csv", "w", newline="")
    log = csv.writer(fh)
    log.writerow(["step", "loss", "seconds"])
    t0, run, tail = time.time(), [], []
    for step in range(1, a.steps + 1):
        xa, xb, y = (t.to(dev, non_blocking=True) for t in next(it))
        with torch.autocast("cuda", dtype=torch.bfloat16):
            loss = torch.nn.functional.cross_entropy(model(xa, xb).float(), y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step(); sched.step()
        run.append(loss.item())
        if step > a.steps - 1000:
            tail.append(run[-1])
        if step % a.eval_every == 0 or step == a.steps:
            el = time.time() - t0
            log.writerow([step, np.mean(run), round(el)]); fh.flush()
            print(f"step {step} loss {np.mean(run):.4f}  {el:.0f}s  {step * BATCH / el:.0f} pairs/s", flush=True)
            run = []
    torch.save(model.state_dict(), out / "final.pt")
    collapsed = bool(np.mean(tail) >= COLLAPSED)
    v = scores(model, A, Bx, dev)
    assert np.isfinite(v).all(), "non-finite scores"
    np.savez(out / "fold_scores.npz", score=v, y=Y, src=src, collapsed=collapsed, tail_loss=np.mean(tail), seconds=time.time() - t0)
    k = Y != 2
    print(f"fold {a.fold}: tail loss {np.mean(tail):.4f} collapsed {collapsed}; held-out recall {recall_at_fpr(v[k][Y[k] == 0], v[k][Y[k] != 0]):.3f}")
    del it, loader


if __name__ == "__main__":
    main()
