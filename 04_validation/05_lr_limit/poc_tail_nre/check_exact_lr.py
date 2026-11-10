"""G0 follow-up: is E_H1[1/r] != 1 a code bug or a heavy-tail sampling effect?

Same code, but with low amplitudes so the hypotheses overlap and the identities
E_q[p/q] = 1 have low variance. Reports effective sample size (ESS) for each identity,
and a scale-free covariance check on whitened samples.
"""
import math

import torch

from sim import ExactLR, SimConfig, Simulator


def check(cfg, n=200_000, label=""):
    sim, exact = Simulator(cfg), ExactLR(cfg)
    gen = torch.Generator(device="cuda").manual_seed(5)
    print(f"--- {label} amps={cfg.amps}")
    def ident(logw, name):
        w = torch.exp(logw)
        m, se = w.mean().item(), (w.std() / math.sqrt(len(w))).item()
        ess = (w.sum() ** 2 / (w ** 2).sum()).item()
        print(f"{name:26s} mean={m:.4f} se={se:.4f} z={(m - 1) / se if se else 0:+.2f} ESS={ess:.0f} of {len(w)}")
    for i, rho in enumerate(cfg.rhos):
        ps = []
        for _ in range(n // 20_000):
            x = sim.sample(20_000, rho_idx=torch.full((20_000,), i, device="cuda"), generator=gen)
            ps.append(exact.log_per_rho(x))
        p = torch.cat(ps)
        ident(p[:, -1] - p[:, i], f"E_rho={rho}[p1/p_rho]")
    ps = []
    for _ in range(n // 20_000):
        ps.append(exact.log_per_rho(sim.sample(20_000, lensed=True, generator=gen)))
    p = torch.cat(ps)
    ident(-exact.log_r(p), "E_H1[1/r]")
    return sim, exact, gen


low = SimConfig(amps=(1.0, 1.5, 2.0, 2.5, 3.0))
check(low, label="low amplitude")
sim, exact, gen = check(SimConfig(), label="main config")

# Whitened covariance: for correct Sigma, Cov(L^-1 (x - m)) = I up to sampling noise.
cfg = SimConfig()
worst = 0
K = 500_000
for ia, ib, ta, tb, ri in [(2, 3, 1, 2, 4), (4, 4, 3, 0, 6), (0, 1, 0, 0, 0), (4, 0, 2, 2, 5)]:
    rho = cfg.rhos[ri]
    g_a, g_ind = sim.draw_g(K, gen), sim.draw_g(K, gen)
    g_b = rho * g_a + math.sqrt(1 - rho ** 2) * g_ind
    xs = []
    for g, a, t in ((g_a, ia, ta), (g_b, ib, tb)):
        y = sim.amps[a] * (sim.H[t] @ (sim.env * (1 + cfg.c * g))[:, :, None])[:, :, 0]
        xs.append(y + torch.randn(y.shape, device="cuda", generator=gen))
    X = torch.cat(xs, 1).double()
    comp = ri * exact.n_nuis + (ia * 5 + ib) * 16 + ta * 4 + tb
    P = exact.P[comp]
    mean = torch.linalg.solve(P, exact.b[comp])
    L = torch.linalg.cholesky(P)  # P = L L^T, so L^T whitens x - m.
    Z = (X - mean) @ L
    C = torch.cov(Z.T)
    err = (C - torch.eye(C.shape[0], device="cuda", dtype=torch.float64)).abs().max().item()
    merr = Z.mean(0).abs().max().item()
    # Max of ~128^2/2 entries with se ~ 1/sqrt(K) (sqrt(2)/sqrt(K) on the diagonal).
    print(f"comp ({ia},{ib},{ta},{tb},rho={rho}): whitened cov max err={err:.5f} mean err={merr:.5f} (1/sqrt(K)={1 / math.sqrt(K):.5f})")

# E_q[p/q] has finite variance only if 2*P_p - P_q is positive definite (same means here,
# up to the shared rho-free mean). Check both directions for the lensed vs rho identities.
print("--- finite-variance condition: min eigenvalue of 2*P_target - P_proposal, one component")
for label, c in (("low", SimConfig(amps=(1.0, 1.5, 2.0, 2.5, 3.0))), ("main", SimConfig())):
    ex = ExactLR(c)
    comp0 = (2 * 5 + 2) * 16 + 1 * 4 + 1  # Mid amplitudes, tau = 1 on both images.
    P1 = ex.P[(ex.n_rho - 1) * ex.n_nuis + comp0]
    for ri, rho in enumerate(c.rhos):
        Pr = ex.P[ri * ex.n_nuis + comp0]
        fwd = torch.linalg.eigvalsh(2 * P1 - Pr).min().item()  # E_rho[p1/p_rho]
        rev = torch.linalg.eigvalsh(2 * Pr - P1).min().item()  # E_H1[p_rho/p1]
        print(f"{label} rho={rho}: E_rho[p1/p_rho] {fwd:+.3e} ({'finite' if fwd > 0 else 'INFINITE'})"
              f" | E_H1[p_rho/p1] {rev:+.3e} ({'finite' if rev > 0 else 'INFINITE'})")
