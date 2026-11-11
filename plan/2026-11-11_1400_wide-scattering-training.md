# Plan: widen the scattering range in training only (option B of update 1340)

- **Date/time:** 2026-11-11 14:00
- **Pipeline box:** `03_models_benchmark/track_B_pairs/01_training`; `02_injection_labelling/01_injection` (a training-only argument)
- **Follows:** [update 1340](../update/2026-11-11_1340_propagation-signoff-check.md). Model 6's recall falls to 0.57× at a differential τ₆₀₀ of 1 ms and to 0.13× at 3 ms. Training covers only 0.01–1 ms.
- **Status:** agreed 2026-11-11 (user: "B: widen training"). The rule below is fixed before any result.

## What changes
- **`make_pair`:** gets `tau_hi=None`. When it is set, the differential τ₆₀₀ is drawn log-uniform over [0.01, tau_hi] ms instead of [0.01, 1] ms.
  - The draw count is unchanged and it is still applied to half of the pairs.
  - With the default `None`, frozen sets are unchanged, which is asserted on the `val_bright` hash.
- **`train.py --wide-scat`:** sets `tau_hi = 10` ms for the training stream. Outputs carry the tag `_S`.
- **Frozen sets, baselines and the metric:** unchanged.

## Runs
- Model 6, seeds 0–2, Stage 2 settings: 20,000 steps, best checkpoint on `val_bright`. About 3 GPU-h.
- Afterwards:
  - `variants_eval.py`, with variant S added;
  - `tau_sweep.py --runs m6_s0_S,m6_s1_S,m6_s2_S`, with the same pairs as the current model's sweep.

## Decision rule (fixed now)
**Adopt S** (it becomes model 6 and 04_propagation is signed off with the current frozen sets) if all four hold:
1. **Non-inferior on `val_bright`:** pooled recall at least current − 0.03. The frozen sets only go up to 1 ms, so a small loss there is acceptable.
2. **Sweep:** recall at τ₆₀₀ = 3 ms ≥ 0.8 × S's own recall at τ = 0 (the sign-off criterion of plan 1300).
3. **Stage 3** passes for all 3 seeds.
4. **Real-burst ratio** ≥ 0.8.

**Otherwise:**
- **S improves the 3 ms recall but misses 0.8:** report both curves, and the user chooses between option A (sign off, state the limit) and a wider S.
- **S does not improve:** the loss is physical (copies too different at 400–600 MHz). Take option A and state the limit in the paper.

## Risks
- **Scattering stays uncovered by the benchmark.** The frozen sets top out at 1 ms, so the benefit of S shows only in the diagnostic sweep. If S is adopted, the paper reports the sweep as the scattering coverage.
- **If S is adopted:** plan 0845 F4 changes recipe. The dev-fold rehearsal reruns (about 5 GPU-h) before `benchmark-v1`.
