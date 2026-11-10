"""Train one neural ratio estimator and score the shared test set.

Methods, all with balanced lensed/repeat batches and the same sample budget:
  plain  negatives from the rho prior
  naive  negatives uniform over rho, no correction (hard-negative oversampling)
  iw     negatives uniform over rho, loss weighted by p(rho)/q(rho)
  cond   negatives uniform over rho, network conditioned on rho, then marginalised

Usage: python train.py --method iw --seed 0 [--finite 4539] [--steps 30000] [--width 48]
"""
import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from model import SiameseRatio
from sim import SimConfig, Simulator

ap = argparse.ArgumentParser()
ap.add_argument("--method", required=True, choices=["plain", "naive", "iw", "cond"])
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--finite", type=int, default=0, help="template pool size; 0 = unlimited simulation")
ap.add_argument("--steps", type=int, default=30_000)
ap.add_argument("--batch", type=int, default=2048)
ap.add_argument("--width", type=int, default=48)
ap.add_argument("--depth", type=int, default=4)
ap.add_argument("--lr", type=float, default=2e-3)
ap.add_argument("--test", default="outputs/testset")
ap.add_argument("--tag", default="")
ap.add_argument("--runsdir", default="outputs/runs")
args = ap.parse_args()

name = f"{args.method}_w{args.width}_s{args.steps}" + (f"_finite{args.finite}" if args.finite else "") + args.tag + f"_seed{args.seed}"
out = Path(args.runsdir) / name
out.mkdir(parents=True, exist_ok=True)
torch.manual_seed(args.seed + 1000)
dev = "cuda"
cfg = SimConfig()
sim = Simulator(cfg, dev)
n_rho = len(cfg.rhos)
p = sim.p_rho
q = torch.full_like(p, 1.0 / n_rho)
use_q = args.method != "plain"
is_cond = args.method == "cond"
# Fixed seed: every finite-pool run sees the same templates, separate from the test set.
pool = None
if args.finite:
    pool = sim.draw_g(args.finite, torch.Generator(device=dev).manual_seed(777))

model = SiameseRatio(w=args.width, depth=args.depth, n_cond=n_rho if is_cond else 0).to(dev)
n_params = sum(x.numel() for x in model.parameters())
opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
sched = torch.optim.lr_scheduler.OneCycleLR(opt, args.lr, total_steps=args.steps, pct_start=0.05)


def batch():
    n = args.batch // 2
    x1 = sim.sample(n, lensed=True, pool=pool)
    idx = torch.multinomial(q if use_q else p, n, replacement=True)
    x0 = sim.sample(n, rho_idx=idx, pool=pool)
    x = torch.cat([x1, x0])
    y = torch.cat([torch.ones(n, device=dev), torch.zeros(n, device=dev)])
    w = torch.ones(2 * n, device=dev)
    if args.method == "iw":
        w[n:] = (p / q)[idx]
    # A positive has no rho of its own, so give it a random condition.
    cond = torch.cat([torch.multinomial(q, n, replacement=True), idx]) if is_cond else None
    return x, y, w, cond


t0 = time.time()
hist = []
model.train()
for step in range(args.steps):
    x, y, w, cond = batch()
    loss = F.binary_cross_entropy_with_logits(model(x, cond), y, weight=w)
    opt.zero_grad(set_to_none=True)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
    opt.step()
    sched.step()
    if step % 2000 == 0 or step == args.steps - 1:
        hist.append([step, loss.item(), time.time() - t0])
        print(f"{name} {step} loss={loss.item():.4f} t={time.time() - t0:.0f}s", flush=True)

torch.save(model.state_dict(), out / "model.pt")

# --- Score the shared test set ------------------------------------------------
model.eval()
X = np.load(Path(args.test) / "x.npy", mmap_mode="r")
scores, per_rho = [], []
log_p = torch.log(p)
with torch.no_grad():
    for start in range(0, len(X), 16384):
        xb = torch.from_numpy(np.array(X[start:start + 16384])).to(dev)
        if is_cond:
            lr, fs = model.log_r_marginal(xb, log_p)
            per_rho.append(fs.cpu().numpy())
        else:
            lr = model(xb)
        scores.append(lr.cpu().numpy())
np.save(out / "log_r.npy", np.concatenate(scores))
if is_cond:
    np.save(out / "f_rho.npy", np.concatenate(per_rho))

# Held-out calibration scores for temperature scaling, from fresh simulation.
scores_cal, labels_cal, n_cal = [], [], 200_000
with torch.no_grad():
    for _ in range(n_cal // 20_000):
        x1 = sim.sample(10_000, lensed=True)
        x0 = sim.sample(10_000, rho_idx=torch.multinomial(p, 10_000, replacement=True))
        xb = torch.cat([x1, x0])
        lr = model.log_r_marginal(xb, log_p)[0] if is_cond else model(xb)
        scores_cal.append(lr.cpu().numpy())
        labels_cal.append(np.r_[np.ones(10_000), np.zeros(10_000)])
np.savez(out / "calib.npz", s=np.concatenate(scores_cal), y=np.concatenate(labels_cal))
(out / "meta.json").write_text(json.dumps({**vars(args), "name": name, "n_params": n_params, "history": hist,
                                           "seconds": time.time() - t0}, indent=1))
print(f"done {name} params={n_params} t={time.time() - t0:.0f}s", flush=True)
