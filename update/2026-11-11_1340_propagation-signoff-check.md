# Update: nuisance-range check before the 04_propagation sign-off. Scattering is the open item

- **Date/time:** 2026-11-11 13:40
- **Plan:** [plan 1300](../plan/2026-11-11_1300_propagation-signoff-check.md). The decision rule was fixed before the sweep.
- **Pipeline box:** `02_injection_labelling/01_injection` (`make_pair(tau_force=None)`) and `03_models_benchmark/track_B_pairs/02_benchmark/tau_sweep.py`. The output is `outputs/tau_sweep.txt` (gitignored).
- **Blinding:** val only. No test file was read and no tag was set. The `val_bright` hash is asserted with the new argument in place.
- **Matches plan?** 🟡 Yes. The rule's sweep criterion fails, and the literature criterion is not settled. **Not signed off.**

## Ranges in use (training, val, test; the stress set is wider)
| Nuisance | Range | Assessment |
|---|---|---|
| Time shift | uniform ±10 samples | Keep. A window offset, not physics. |
| Residual DM | normal(0, σ), σ = catalogue DM error × model S/N / injected S/N; median 0.13 pc cm⁻³ at S/N 25 | Keep. Each burst is dedispersed at its own DM, so the residual is measurement error. |
| Differential scattering | half of the pairs: one member gets τ₆₀₀ log-uniform 0.01–1 ms, scaling as ν⁻⁴ | **Open.** See below. |
| Scintillation | a fresh Gamma pattern per member at the source's bandwidth; median 32 scintles (about 18% per channel); 40% of templates use the default 49 kHz | Keep. Delays of days to months make the patterns independent. |
| Impostor mix | I1 / I2 / I1+I2 at 1:1:1 | Keep. A simulation choice, already stated in the Limitations. |

## Scattering sensitivity of model 6 (3 seeds, `val_bright` operating threshold)
**Frozen `val_bright`, lensed pairs by injected τ₆₀₀:**

| τ₆₀₀ bin | n | Mean recall |
|---|---|---|
| none | 1000 | 0.713 |
| 0.01–0.1 ms | 509 | 0.741 |
| 0.1–0.3 ms | 260 | 0.651 |
| 0.3–1 ms | 231 | 0.558 |

**Forced-τ sweep:** 2000 new val lensed pairs per value, floor 25, with only τ changing.

| τ₆₀₀ (ms) | τ at 1 GHz (ms, ν⁻⁴·⁴) | Recall s0 / s1 / s2 | Ratio to τ = 0 |
|---|---|---|---|
| 0 | 0 | 0.715 / 0.697 / 0.702 | 1.00 |
| 0.3 | 0.03 | 0.713 / 0.677 / 0.687 | 0.98 |
| 1 | 0.11 | 0.410 / 0.399 / 0.395 | 0.57 |
| 3 | 0.32 | 0.090 / 0.096 / 0.086 | **0.13** |
| 10 | 1.06 | 0.015 / 0.009 / 0.005 | 0.01 |
| 30 | 3.2 | 0.008 / 0.002 / 0.000 | 0.00 |

**Reading:**
- Model 6 recognises copies up to a differential τ₆₀₀ of about 0.3 ms.
- Recall halves at 1 ms, the top of the training range, and is near zero beyond 3 ms.
- The drop is consistent with a training range that ends at 1 ms. It is not yet known whether wider training recovers recall, or whether the copies are genuinely too different at 400–600 MHz: at 400 MHz, τ₆₀₀ = 3 ms is 15 ms.

## Literature (what sets the physical range)
- **Host and Milky Way scattering are common to both images.** The two paths are inseparable at the host and in the Galaxy, so this scattering is part of the template already. Only the **lens galaxy's ISM** makes the copies differ.
- **Intervening galaxies are usually weak scatterers:**
  - Lines of sight through intervening haloes show negligible scattering ([Ocker, Cordes & Chatterjee 2021](https://arxiv.org/abs/2101.04784v2)).
  - Halo models reach τ(1 GHz) ≳ 1 ms only for z_s ≳ 1.
  - Observed FRB scattering is mostly from the host ([Ocker et al. 2022](https://arxiv.org/pdf/2202.13458v2); [Apertif sample](https://arxiv.org/pdf/2406.00482)).
- **Lens-galaxy discs can scatter strongly.** A lens with a Milky-Way-like disc would give a range of scattering delays large enough to spoil delay measurements ([Wucknitz et al. 2021](https://arxiv.org/pdf/2004.11643)).
  - The lensing optical depth is dominated by massive early-type galaxies, which have little cold ISM, so typical differential scattering is small.
  - The tail, from images through a spiral disc, is not.
- **No paper gives a number.** None found gives a distribution of differential τ between galaxy-lensed FRB images. The literature criterion of the rule can therefore not be settled with a number.

## Against the decision rule (plan 1300)
| Criterion | Result |
|---|---|
| Typical differential τ₆₀₀ inside 0.01–1 ms (literature) | Plausible for early-type lenses (≲ 0.1 ms at 1 GHz ≈ ≲ 1 ms at 600 MHz), but **not quantified** |
| Recall at 3 ms ≥ 0.8 × recall at 0 | **0.13: fails** |

→ The rule says propose a change before the test opens. **The 04_propagation sign-off is not given.** The options are below.

## Options (team or user decision)
| Option | What changes | Frozen sets | Cost | Effect |
|---|---|---|---|---|
| A. Keep the ranges, sign off, report the sweep | nothing | unchanged | none | Benchmark valid for τ₆₀₀ ≤ 1 ms. The paper states that the detector loses lensed pairs with differential τ₆₀₀ ≳ 1 ms (τ(1 GHz) ≳ 0.1 ms), i.e. images through a scattering disc. |
| B. Widen training only (e.g. τ₆₀₀ to 10 ms, a training flag like P) | training recipe | unchanged | about 3 GPU-h for model 6 × 3 seeds, then the sweep again; if adopted, Stage 2/folds rehearsal reruns (about 1 day) | May extend coverage without touching the sets. Needs its own plan and rule. |
| C. Widen training and frozen sets | `make_pair` range, set version v1.5 | all regenerated | Stage 1–4 rerun (several days) | Benchmark covers the wide tail. Expensive before the test, much worse after it. |

## Not done
- The GBM and baselines are not in the sweep.
- No sweep over scintillation or residual DM. Their ranges follow from measurements, so the risk is low.
