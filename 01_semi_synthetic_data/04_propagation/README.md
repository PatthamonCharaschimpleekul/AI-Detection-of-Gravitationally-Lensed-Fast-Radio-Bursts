# Per-image propagation

**Purpose:** Independent ΔDM, ΔRM, scattering and scintillation for each lensed image.

**Inputs:** Lens outputs.

**Outputs:** Distortion parameters per image.

Diagram box in [pipeline.mmd](/pipeline.mmd). Large files go in `data/` or `outputs/` inside this folder (gitignored).

**Implementation:** `02_injection_labelling/01_injection/inject.py` (`member`, `make_pair`). There is no separate code in this folder.

## Sign-off of the nuisance ranges (Stage 5 gate, plan 1223 decision 5)
- **Signed off:** 2026-11-11 by the user (option A of [update 1340](../../update/2026-11-11_1340_propagation-signoff-check.md), user: "sign off A").
- **Ranges:** these are the ranges of the frozen sets v1.3–v1.4. They are unchanged by this sign-off.
- **This does not open the test split.** The `benchmark-v1` tag and Stage 5 need a separate go-ahead.

| Nuisance (per member) | Range | Evidence |
|---|---|---|
| Time shift | uniform ±10 samples (stress ±20) | window offset |
| Residual DM | normal(0, σ), σ = catalogue DM error × model S/N / injected S/N (stress ×3) | each burst is dedispersed at its own DM, so the residual is measurement error |
| Differential scattering | half of the pairs: one member, τ₆₀₀ log-uniform 0.01–1 ms, ∝ ν⁻⁴ (stress to 3 ms) | host and Milky Way scattering are common to both images (they are in the template); only the lens galaxy's ISM differs, and it is small for the early-type lenses that dominate the optical depth (update 1340) |
| Scintillation | fresh Gamma pattern at the source's bandwidth, default 49 kHz where unmeasured | delays of days to months give independent patterns |
| Impostors | I1 / I2 / I1+I2 at 1:1:1 | simulation choice, stated in the paper |

**Stated limit (must appear in the paper):** recall falls with differential scattering. Lensed-pair recall relative to τ = 0, on val with the same pairs for every method:

| τ₆₀₀ | Model 6 | Physics fit (b2) | Cross-correlation (b1) | GBM |
|---|---|---|---|---|
| 1 ms | 0.57× | 1.12× | 0.58× | 0.71× |
| 3 ms | 0.13× | 1.21× | 0.19× | 0.33× |
| 10 ms | 0.01× | 0.46× | 0.02× | 0.04× |

- **Model 6:** training to 10 ms does not fix its loss ([update 1630](../../update/2026-11-11_1630_wide-scattering-training.md)).
- **The physics fit keeps its (low) recall up to 3 ms** because it fits τ explicitly. The loss is therefore partly a limit of shape-matching models, not purely physical ([update 1700](../../update/2026-11-11_1700_baseline-scattering-sweep-and-signoff.md)).
