"""Linear-Gaussian burst-pair simulator with a closed-form marginal likelihood ratio.

Each pair is two 1-D time series of length T, one per burst:

    s_i = e * (1 + c * g_i)            intrinsic burst; g_i is a Gaussian process
    x_i = a_i * H_i * s_i + n_i        amplitude, scattering kernel, unit noise
    corr(g_A, g_B) = rho               rho = 1 for lensed pairs, rho < 1 for repeats

Given the discrete nuisances (a_A, a_B, tau_A, tau_B, rho) the pair is jointly
Gaussian, so each hypothesis is a finite Gaussian mixture and the exact LR is
computable. Amplitudes and scattering share one prior under both hypotheses, so
only waveform similarity separates them.
"""
from dataclasses import dataclass
from itertools import product

import torch


@dataclass(frozen=True)
class SimConfig:
    T: int = 64
    env_width: float = 8.0
    c: float = 0.8
    ell: float = 1.5
    jitter: float = 1e-4
    amps: tuple = (4.0, 6.0, 9.0, 14.0, 20.0)
    taus: tuple = (0.0, 1.0, 2.0, 4.0)
    rhos: tuple = (0.0, 0.3, 0.6, 0.8, 0.9, 0.95, 0.98)
    p_rho: tuple = (0.40, 0.25, 0.15, 0.10, 0.06, 0.03, 0.01)


def _build_operators(cfg, device, dtype):
    t = torch.arange(cfg.T, dtype=dtype, device=device)
    env = torch.exp(-0.5 * ((t - (cfg.T - 1) / 2) / cfg.env_width) ** 2)
    diff = t[None, :] - t[:, None]
    K = torch.exp(-0.5 * (diff / cfg.ell) ** 2) + cfg.jitter * torch.eye(cfg.T, dtype=dtype, device=device)
    Hs = []
    for tau in cfg.taus:
        if tau == 0:
            Hs.append(torch.eye(cfg.T, dtype=dtype, device=device))
            continue
        h = torch.exp(-t / tau)
        h = h / h.sum()
        H = torch.zeros(cfg.T, cfg.T, dtype=dtype, device=device)
        for lag in range(cfg.T):
            H += h[lag] * torch.diag(torch.ones(cfg.T - lag, dtype=dtype, device=device), -lag)
        Hs.append(H)
    return env, K, torch.stack(Hs)


class Simulator:
    """Draws pairs on the GPU. Shapes: x is (n, 2, T)."""

    def __init__(self, cfg=SimConfig(), device="cuda"):
        self.cfg, self.device = cfg, device
        self.env, K, self.H = _build_operators(cfg, device, torch.float32)
        self.L = torch.linalg.cholesky(K)
        self.amps = torch.tensor(cfg.amps, device=device, dtype=torch.float32)
        self.rhos = torch.tensor(cfg.rhos, device=device, dtype=torch.float32)
        self.p_rho = torch.tensor(cfg.p_rho, device=device, dtype=torch.float32)

    def draw_g(self, n, generator=None):
        z = torch.randn(n, self.cfg.T, device=self.device, generator=generator)
        return z @ self.L.T

    def sample(self, n, rho_idx=None, lensed=False, pool=None, generator=None):
        """Draw n pairs.

        lensed=True forces rho = 1. Otherwise rho_idx gives each pair's rho index.
        pool, if given, is a finite set of g templates used instead of fresh draws.
        """
        cfg, dev = self.cfg, self.device
        randint = lambda high: torch.randint(high, (n,), device=dev, generator=generator)
        ia, ib = randint(len(cfg.amps)), randint(len(cfg.amps))
        ta, tb = randint(len(cfg.taus)), randint(len(cfg.taus))
        if pool is None:
            g_a, g_ind = self.draw_g(n, generator), self.draw_g(n, generator)
        else:
            g_a, g_ind = pool[randint(len(pool))], pool[randint(len(pool))]
        if lensed:
            g_b = g_a
        else:
            rho = self.rhos[rho_idx][:, None]
            g_b = rho * g_a + torch.sqrt(1 - rho ** 2) * g_ind
        x = []
        for g, i_amp, i_tau in ((g_a, ia, ta), (g_b, ib, tb)):
            s = self.env * (1 + cfg.c * g)
            y = (self.H[i_tau] @ s[:, :, None])[:, :, 0]
            y = self.amps[i_amp][:, None] * y
            x.append(y + torch.randn_like(y) if generator is None else
                     y + torch.randn(y.shape, device=dev, generator=generator))
        return torch.stack(x, dim=1)


class ExactLR:
    """Exact per-hypothesis log densities by summing over every Gaussian component."""

    def __init__(self, cfg=SimConfig(), device="cuda", k_chunk=200):
        self.cfg, self.device, self.k_chunk = cfg, device, k_chunk
        dt = torch.float64
        env, K, H = _build_operators(cfg, device, dt)
        E = torch.diag(env)
        c2 = cfg.c ** 2
        Sg = c2 * E @ K @ E
        T = cfg.T
        # rho index len(rhos) means lensed, rho = 1.
        all_rhos = list(cfg.rhos) + [1.0]
        nuis = list(product(range(len(cfg.amps)), range(len(cfg.amps)),
                            range(len(cfg.taus)), range(len(cfg.taus))))
        self.n_nuis = len(nuis)
        self.n_rho = len(all_rhos)
        n_comp = self.n_nuis * self.n_rho
        P, b, cc, ld = [], [], [], []
        idx = torch.tensor(nuis, device=device)
        amps = torch.tensor(cfg.amps, device=device, dtype=dt)
        I = torch.eye(T, device=device, dtype=dt)
        for r in all_rhos:
            aa, ab = amps[idx[:, 0]], amps[idx[:, 1]]
            Ha, Hb = H[idx[:, 2]], H[idx[:, 3]]
            AA = (aa ** 2)[:, None, None] * (Ha @ Sg @ Ha.transpose(1, 2)) + I
            BB = (ab ** 2)[:, None, None] * (Hb @ Sg @ Hb.transpose(1, 2)) + I
            AB = (r * aa * ab)[:, None, None] * (Ha @ Sg @ Hb.transpose(1, 2))
            cov = torch.cat([torch.cat([AA, AB], 2), torch.cat([AB.transpose(1, 2), BB], 2)], 1)
            mean = torch.cat([aa[:, None] * (Ha @ env), ab[:, None] * (Hb @ env)], 1)
            chol = torch.linalg.cholesky(cov)
            prec = torch.cholesky_inverse(chol)
            bb = (prec @ mean[:, :, None])[:, :, 0]
            P.append(prec)
            b.append(bb)
            cc.append((mean * bb).sum(1))
            ld.append(2 * torch.log(torch.diagonal(chol, dim1=1, dim2=2)).sum(1))
        self.P = torch.cat(P)
        self.b = torch.cat(b)
        self.cc = torch.cat(cc)
        self.ld = torch.cat(ld)
        assert len(self.P) == n_comp

    @torch.no_grad()
    def log_per_rho(self, x):
        """Return (n, n_rho) log p(x | rho), marginal over the other nuisances."""
        X = x.reshape(len(x), -1).to(self.device, torch.float64)
        lp = torch.empty(len(self.P), len(X), device=self.device, dtype=torch.float64)
        for start in range(0, len(self.P), self.k_chunk):
            sel = slice(start, start + self.k_chunk)
            q = (X.T[None] * (self.P[sel] @ X.T)).sum(1)
            lin = self.b[sel] @ X.T
            lp[sel] = -0.5 * (q - 2 * lin + self.cc[sel][:, None] + self.ld[sel][:, None])
        log_n = torch.log(torch.tensor(float(self.n_nuis), dtype=torch.float64, device=self.device))
        out = torch.logsumexp(lp.reshape(self.n_rho, self.n_nuis, len(X)), dim=1) - log_n
        return out.T

    def log_r(self, per_rho, p_rho=None):
        """Marginal log LR given (n, n_rho) log densities, with the last column lensed."""
        p = torch.tensor(self.cfg.p_rho if p_rho is None else p_rho,
                         dtype=per_rho.dtype, device=per_rho.device)
        return per_rho[:, -1] - torch.logsumexp(per_rho[:, :-1] + torch.log(p), dim=1)
