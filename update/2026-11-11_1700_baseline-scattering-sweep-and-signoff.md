# Update: baseline scattering sweep, and the 04_propagation sign-off (option A)

- **Date/time:** 2026-11-11 17:00
- **Request:** "sign off A และลองทำ sweep เพิ่ม", then "เริ่มเลย".
- **Code:**
  - `02_benchmark/tau_sweep_base.py` (new);
  - `baselines.work` takes an optional 7th job element, `tau_force`. Frozen jobs never set it.
- **Output:** `outputs/tau_sweep_base.txt` (gitignored).
- **Blinding:** val only. No test file was read and no tag was set.

## Baseline sweep
- **Pairs:** the same 2000 val lensed pairs per τ as `tau_sweep.py`.
- **Threshold:** each method's own `val_bright` operating threshold.
- **GBM:** refitted and asserted against the Stage 1 scores.

| τ₆₀₀ (ms) | Model 6 (mean, 3 seeds) | b1 xcorr | b2 physics fit | b3 GBM |
|---|---|---|---|---|
| 0 | 0.705 | 0.186 | 0.162 | 0.287 |
| 0.3 | 0.692 (0.98) | 0.176 (0.95) | 0.167 (1.03) | 0.282 (0.98) |
| 1 | 0.401 (0.57) | 0.108 (0.58) | 0.182 (1.12) | 0.204 (0.71) |
| 3 | 0.091 (0.13) | 0.035 (0.19) | **0.196 (1.21)** | 0.094 (0.33) |
| 10 | 0.009 (0.01) | 0.004 (0.02) | 0.074 (0.46) | 0.012 (0.04) |
| 30 | 0.003 (0.00) | 0.000 (0.00) | 0.025 (0.15) | 0.003 (0.01) |

## Reading, and a correction to update 1630
- **The shape-matching methods all lose recall the same way.** Model 6, cross-correlation and the feature GBM fall to 0.13–0.33× at 3 ms.
- **The physics fit does not.** It fits a scattering time, residual DM, lag and amplitude between the members, and its recall holds (it even rises) up to 3 ms.
- **The ranking flips:**
  - Model 6 still leads at τ₆₀₀ ≤ 1 ms: 0.40 against 0.18 at 1 ms.
  - Above about 2 ms the physics fit leads: 0.196 against 0.091 at 3 ms.
- **Correction.** Update 1630 called the limit "mostly physical". That is too strong. Strongly scattered copies are still identifiable by a model that represents scattering explicitly.
  - Model 6's loss is a limit of the model: it compares shapes, and widening its training range did not teach it the scattering transform.
  - A scattering-aware model (an explicit τ kernel in the alignment layer, or a hybrid with the physics fit) is a route for later. It needs its own plan.
- **What this changes for the paper's limitation statement:**
  - Model 6 covers differential τ₆₀₀ ≲ 1 ms (τ(1 GHz) ≲ 0.1 ms).
  - Beyond that, a physics fit retains some sensitivity.
  - Track C does not depend on burst shape.

## Sign-off (option A)
- **Ranges:** the 04_propagation nuisance ranges are signed off as they are, together with the stated limit above. The record is in [`01_semi_synthetic_data/04_propagation/README.md`](../01_semi_synthetic_data/04_propagation/README.md).
- **Frozen sets and methods:** unchanged.
- **Stage 5 gates now:**

  | Gate | Status |
  |---|---|
  | Sign-off | ✅ |
  | Methods frozen | ✅ (model 6 as in Stage 2; variants M, P, M+P and S not adopted) |
  | Tag `benchmark-v1` | ⬜ needs the user's go-ahead |
