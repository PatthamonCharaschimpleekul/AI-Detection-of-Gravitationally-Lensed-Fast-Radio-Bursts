"""Siamese encoder with feature-map fusion (Project_Description Sec. 6.3), in 1-D."""
import torch
from torch import nn
from torch.nn import functional as F


class ResBlock(nn.Module):
    def __init__(self, w, dilation):
        super().__init__()
        self.conv1 = nn.Conv1d(w, w, 3, padding=dilation, dilation=dilation)
        self.conv2 = nn.Conv1d(w, w, 3, padding=dilation, dilation=dilation)
        self.n1, self.n2 = nn.GroupNorm(8, w), nn.GroupNorm(8, w)

    def forward(self, x):
        y = self.conv1(F.gelu(self.n1(x)))
        y = self.conv2(F.gelu(self.n2(y)))
        return x + y


class SiameseRatio(nn.Module):
    """Outputs log r(x) = log p(x|lensed) / p(x|repeat), symmetric under A <-> B.

    With n_cond > 0 it takes a rho index and outputs log p(x|lensed) / p(x|rho).
    """

    def __init__(self, w=48, depth=4, head=256, n_cond=0):
        super().__init__()
        self.n_cond = n_cond
        self.input = nn.Conv1d(1, w, 5, padding=2)
        self.enc = nn.Sequential(*[ResBlock(w, 2 ** (i % 3)) for i in range(depth)])
        self.fuse_in = nn.Conv1d(3 * w, 2 * w, 1)
        self.fuse = nn.Sequential(*[ResBlock(2 * w, 2 ** (i % 4)) for i in range(depth)])
        # Fused map (mean + max) plus global per-channel energies and inner products.
        feat = 2 * 2 * w + 3 * w
        self.emb = nn.Embedding(n_cond, 32) if n_cond else None
        self.head = nn.Sequential(
            nn.Linear(feat + (32 if n_cond else 0), head), nn.GELU(),
            nn.Linear(head, head), nn.GELU(),
            nn.Linear(head, head), nn.GELU(),
            nn.Linear(head, 1),
        )

    def features(self, x):
        x = x / 10.0  # Amplitudes reach ~20 in units of the noise.
        fa = self.enc(self.input(x[:, :1]))
        fb = self.enc(self.input(x[:, 1:]))
        m = self.fuse(self.fuse_in(torch.cat([(fa - fb).abs(), fa * fb, fa + fb], 1)))
        return torch.cat([
            m.mean(-1), m.amax(-1),
            (fa * fb).mean(-1), ((fa - fb) ** 2).mean(-1), (fa ** 2 + fb ** 2).mean(-1),
        ], 1)

    def head_out(self, feat, rho_idx=None):
        if self.n_cond:
            feat = torch.cat([feat, self.emb(rho_idx)], 1)
        return self.head(feat)[:, 0]

    def forward(self, x, rho_idx=None):
        return self.head_out(self.features(x), rho_idx)

    @torch.no_grad()
    def log_r_marginal(self, x, log_p_rho):
        """Marginal log r for a conditional model: -logsumexp_rho(log p(rho) - f(x, rho))."""
        feat = self.features(x)
        fs = torch.stack([self.head_out(feat, torch.full((len(x),), i, device=x.device))
                          for i in range(self.n_cond)], 1)
        return -torch.logsumexp(log_p_rho.to(x.device) - fs, dim=1), fs
