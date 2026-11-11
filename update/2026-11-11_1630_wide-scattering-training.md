# Update: wide-scattering training (option B): not adopted. The scattering limit is mostly physical

- **Date/time:** 2026-11-11 16:30
- **Plan:** [plan 1400](../plan/2026-11-11_1400_wide-scattering-training.md). The rule was fixed before the runs.
- **Code:** `01_training/run_wide_scat.sh`, `train.py --wide-scat` (training τ₆₀₀ log-uniform 0.01–10 ms, half of the pairs), `tau_sweep.py --runs`, and `variants_eval.py` with variant S.
- **Outputs:** `02_benchmark/outputs/tau_sweep_S.txt` and `variants.txt` (gitignored).
- **Matches plan?** ✅ The 3 runs exit 0, and the sweep and evaluation ran unchanged. Decision: **not adopted.** The current model 6 stays.

## Results (S = wide-scattering training, against the current model 6; 3 seeds each)
| Check | Current | S |
|---|---|---|
| `val_bright` recall (s0 / s1 / s2) | 0.701 / 0.698 / 0.684, mean 0.694 | 0.598 / 0.697 / 0.677, mean 0.657 |
| Paired difference vs current [95%] | — | −0.022 [−0.134, +0.081]; pooled mean −0.037 |
| Sweep recall at τ₆₀₀ = 0 / 0.3 / 1 / 3 / 10 / 30 ms | 0.705 / 0.692 / 0.401 / 0.091 / 0.009 / 0.003 | 0.666 / 0.667 / 0.434 / 0.158 / 0.052 / 0.004 |
| Ratio at 3 ms (to its own τ = 0) | 0.13 | **0.24** |
| Stage 3 headline FPR | 0.011 / 0.014 / 0.008, pass | 0.010 / 0.009 / 0.010, pass |
| Real-burst ratio | 0.96 | 0.99 |
| Seen − unseen recall gap | +0.197 | +0.166 to +0.274 |

## Against the rule
| Criterion | Result |
|---|---|
| 1. Non-inferior on `val_bright` (≥ current − 0.03) | −0.037: **fails** (seed 0 is low, 0.598) |
| 2. Recall at 3 ms ≥ 0.8 × at 0 | 0.24: **fails** |
| 3. Stage 3 | passes |
| 4. Real-burst ratio ≥ 0.8 | 0.99: passes |

The rule's branch is: "S improves the 3 ms recall but misses 0.8 → report both curves; the user chooses between A and a wider S."

## Reading
- **Ten times more scattering in training barely moves the curve.** Recall at 3 ms goes from 0.09 to 0.16, at 1 ms from 0.40 to 0.43, and at 10 ms from 0.01 to 0.05. About 18% of S's training pairs had τ₆₀₀ > 1 ms.
- **The limit is mostly physical, not a coverage gap.**
  - At τ₆₀₀ = 3 ms the scattered copy has τ ≈ 15 ms at 400 MHz.
  - Its fine structure is smeared, so it no longer looks like the same burst more than a different burst of the same source does.
  - A wider training range trades recall at small τ (−0.04) for a small gain at large τ.
- **A wider S is unlikely to reach 0.8 at 3 ms.** Pushing further is not recommended.

## What this means for the sign-off
- **Option A (keep the ranges and state the limit) is the remaining route.**
  - The detector, like any burst-identity method, verifies copies only when the differential scattering is small: τ₆₀₀ ≲ 0.3 ms at full recall, half recall at about 1 ms (τ(1 GHz) ≈ 0.1 ms).
  - This matches lens galaxies with little cold ISM (massive early types, which dominate the lensing optical depth).
  - It excludes images seen through a scattering disc, which a timing test (Track C) can still catch, since it does not compare burst shapes.
- **This needs an explicit sign-off from the user.** The plan-1300 criterion (≥ 0.8 at 3 ms) is not met by any option, so signing off means accepting the stated limit.

## Not done
- The GBM and baselines are not in the sweep.
- The S checkpoints are kept in `outputs/m6_s*_S` (gitignored) but are not used further.
