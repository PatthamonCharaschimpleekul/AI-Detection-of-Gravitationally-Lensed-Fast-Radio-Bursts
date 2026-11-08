# Update: why model 7 seed 1 does not train; physics and logic audit

- **Date/time:** 2026-11-08 08:00
- **Plan:** [../plan/2026-11-08_0700_model7-failure-and-code-audit.md](../plan/2026-11-08_0700_model7-failure-and-code-audit.md)
- **Pipeline box:** `02_injection_labelling/01_injection`, `03_models_benchmark/track_B_pairs`
- **Matches plan?** ✅ Diagnosis and audit done, on train/val only. No code, set or result changed. Test sets stay closed.

## Model 7 seed 1: representation collapse on a plateau, not a code bug
Re-ran the first 2500 steps of `m7_s1` and `m7_s2` with the same seeds and code, plus instruments (scratch script, not kept). The failure reproduces: seed 1 ends at loss 1.386, seed 2 at 0.977.

| Step | Seed 1: token spread / active head units / encoder gradient | Seed 2: same |
|---|---|---|
| 1 | 0.61 / 76 / 0.84 | 0.61 / 91 / 0.85 |
| 500 | 0.28 / 26 / 0.09 | 0.55 / 30 / 0.10 |
| 1000 | 0.20 / 6 / 0.016 | 0.92 / 17 / 0.05 |
| 2000 | 0.18 / 1 / 0.002 | 0.85 / 55 / 2.2 |

- **Starting point, both seeds:** attention is uniform (entropy 1.000 of maximum). Each token of burst A is compared with the plain average of burst B's 320 tokens, where the burst fills only a few. That comparison carries almost no pair information, so the loss sits at ln 4 at first.
- **Seed 1:** the tokens within an image become alike (spread 0.61 → 0.18), the encoder gradient falls about 400-fold, and the head units die (76 → 1). Attention never leaves uniform. The model settles on predicting the class prior. Most of this happens during warmup, at low learning rate.
- **Seed 2:** token spread grows instead (0.61 → 0.9). Attention starts to focus near step 1800 (entropy 0.94), and the loss then drops.
- **Conclusion:** model 7 has no comparison path that works from the start, so whether it escapes the plateau depends on the seed. Model 6 does not have this problem: its correlation layer compares the two bursts without parameters from step 1.
- **Code is not at fault:** symmetry self-check, one-batch memorisation (accuracy 1.000), and seed 2 learning normally.
- **Possible fixes, none applied:** LayerNorm on tokens before attention (standard pre-norm transformer), a learned attention temperature, or reporting model 7 as seed-unstable.

## Physics audit (`inject.py`)
| Item | Check | Result |
|---|---|---|
| Dispersion constant | 4.148808e6 ms MHz² (pc cm⁻³)⁻¹ = 4.1488 ms GHz² | OK |
| Delay sign and size | +1 pc cm⁻³ moves a spike +15 samples at 401 MHz, −5 at 799 MHz (analytic +14.5, −5.1; textbook 14.4 ms from 400 to 600 MHz) | OK |
| Residual DM width | σ = catalog DM error × (template S/N / injected S/N). In `val_bright`: median 0.015 pc cm⁻³, smear 0.2 samples at 400 MHz, 0.1% over 10 samples | OK, small |
| Scattering | τ ∝ ν⁻⁴, one-sided exponential, unit-sum kernel, linear convolution with zero padding | OK. Uses index 4, not 4.4: a simplification |
| Time and frequency grid | 0.98304 ms native; 256 channels of 1.5625 MHz, 400.98–799.41 MHz, ascending | OK |
| Scintillation | Gamma(n, 1/n) per channel, n = channel width / Δν_d: mean 1.000, variance 1/n (checked) | OK. Δν_d 49–220 kHz, always below the channel width, so independent channels are valid. Most sources use the 49 kHz default |
| S/N | matched filter over unmasked channels in background σ units, then the same per-channel renormalisation as preprocessing | OK |

**One modelling question, not a bug:** `member()` divides the template by the background file's per-channel σ, not by its own file's σ. This reshapes each member's spectrum by σ_template/σ_background, which varies by about 20% from channel to channel (median sd 0.20; 90th percentile 0.25). That is similar in size to the scintillation (sd 0.18).
- If raw units are uncalibrated gains, the template's own σ would be the physical choice. If they are calibrated, the current choice is right.
- Either way it is independent per member and the same for every class. It makes all pairs less alike and cannot inflate lensed scores.
- The twin test against real pairs already includes it.
- Changing it needs new frozen sets and new runs. It belongs with the `04_propagation` sign-off.

## Logic audit
- **Construction rules, all 8000 `val_bright` pairs:** 0 violations. Rules checked: label equals kind; same source unless unrelated; same template only for lensed; two different backgrounds, neither from a template's own file; all sources in val; impostor type only for impostors; both S/N ≥ 25.
- **Nuisances do not differ by class (no leak):** median S/N A 48–50 and B 33 for every class; scattered share 49–52%; scattering τ median 0.09–0.10 ms; shift and residual DM equal; swapped share 50–51%.
- **Labels end to end:** baseline score file labels and sources equal the manifest. Learned score files reproduce their logged recall (asserted in `stage2_val.py`), so pair order matches.
- **Training:** train split only, uniform classes, per-worker RNG streams distinct, test never read.
- **Evaluation and metric:** checks passed for both member orders averaged, unrelated excluded from the primary, lensed log-odds formula, correlation-layer lag sign, threshold at the 99th percentile of negatives with strict >, and all 2000 source resamples used.
- **Known limitation (already disclosed):** checkpoints are chosen on `val_bright`, so val recalls are slightly optimistic.

## Decision (2026-11-08): model 7 reported as seed-unstable
- No architecture change, no rerun. All three seeds stay in the record as they are (0.471, 0.013, 0.579).
- The paper reports model 7 as unstable across seeds: 1 of 3 collapsed on the chance plateau, with the diagnosis above.
- Model 7 is not used as a comparator and gets no paired-difference claim. The primary comparison stays model 6 vs `b3_gbm`.
- The same rule carries into the grouped folds: model 7 runs with its frozen code, and every collapsed fold-seed is counted and reported, not replaced.

## Next
- The σ question (decide at the `04_propagation` sign-off). Then the grouped-fold addendum.
