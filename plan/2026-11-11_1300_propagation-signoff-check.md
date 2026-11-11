# Plan: check the nuisance ranges before the 04_propagation sign-off (Stage 5 gate)

- **Date/time:** 2026-11-11 13:00
- **Pipeline box:** `01_semi_synthetic_data/04_propagation`, `02_injection_labelling/01_injection`, `03_models_benchmark/track_B_pairs/02_benchmark`
- **Request (user, 2026-11-11):** "ทำ test sign off เผื่อไว้" (prepare the test sign-off). This plan prepares it. It does **not** open the test split. The tag `benchmark-v1` and the fold runs wait for an explicit go-ahead.

## Why
- Plan 1223 decision 5 and plan 0845 F8 keep the test split closed until `04_propagation` signs off three ranges: residual DM, scattering and scintillation depth.
- Of these, differential scattering between the two lensed images (log-uniform 0.01–1 ms at 600 MHz, in half of the pairs) has never been checked against physics or against the model's sensitivity.

## What we will do (val only, no test file read)
1. **Sensitivity on the frozen `val_bright`:** model 6 recall (3 seeds) for lensed pairs, split by injected τ₆₀₀ bin: none, 0.01–0.1, 0.1–0.3 and 0.3–1 ms. The threshold is the usual one, set on all negatives.
2. **Scattering sweep beyond the training range:**
   - **Pairs:** new val lensed pairs, 2000 per value, floor S/N 25, with τ₆₀₀ forced to 0, 0.3, 1, 3, 10 and 30 ms on one member.
   - **Paired draws:** every other draw is identical across τ values (seed `[61, i]`), so only τ changes.
   - **Scoring:** recall at the `val_bright` operating threshold.
   - **Code:** `make_pair` gets an optional `tau_force`. With the default `None` the rng draws are unchanged, which is asserted on the `val_bright` hash.
   - **Not frozen:** this is a diagnostic set.
3. **Literature check:** the expected differential scattering of two galaxy-lensed images at 600 MHz, from the lens galaxy's ISM and the host. Sources are cited.
4. **Sign-off record:** a proposed sign-off in `01_semi_synthetic_data/04_propagation/README.md` that lists:
   - every range;
   - the evidence for it;
   - the decision: keep, or widen before the test opens.

   It stays marked "proposed" until the user confirms.

## Decision rule (fixed now)
- **Keep 0.01–1 ms** if both of these hold:
  - the literature's typical differential τ₆₀₀ for galaxy lenses lies within it, so a wider tail is not the typical case;
  - **or** the sweep shows that recall at 3 ms is at least 0.8 × the recall at τ = 0.
- **Otherwise, propose widening** the training and test range before the test opens. This means new set versions and retraining, and it gets a plan of its own.
- **Either way:** the τ sweep is reported in the paper as a sensitivity curve.

## Expected result
A table of recall against τ, a short literature summary, and a proposed sign-off text. No tag and no test access.

## Risks
- **Literature:** values for differential scattering through lens galaxies are scarce and model dependent. A range, not a number, is the likely outcome.
- **Sweep coverage:** the sweep covers only lensed pairs. Scattering on negatives is part of the frozen sets and is not changed here.
