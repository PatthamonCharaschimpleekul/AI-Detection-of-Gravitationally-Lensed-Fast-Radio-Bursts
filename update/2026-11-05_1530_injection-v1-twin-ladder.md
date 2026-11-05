# Update: injection v1 (measured S/N) and the twin ladder

- **Date/time:** 2026-11-05 15:30
- **Plan:** [../plan/2026-11-05_1254_pair-injection.md](../plan/2026-11-05_1254_pair-injection.md); follows [update 2026-11-05_1335](2026-11-05_1335_pair-injection.md), checkpoint commit `496c048` (v0)
- **Pipeline box:** `02_injection_labelling/01_injection`
- **Matches plan?** 🟡 The amplitude fix is in, and the frozen sets are regenerated as **v1**. The twin ladder found the cause of the domain gap, and it is **not** the one we expected. It is a generic template deficit, not shared beam structure, so no beam fix was made.

## What we did
- **Amplitude bookkeeping (v1).**
  - The injected S/N, the S/N pool and the residual-DM scaling now all use `model_snr`: the matched-filter S/N of the fitburst model in the real data, already in the cache. Before, they used catalog `snr_fitb`.
  - Measured: `model_snr / snr_fitb` median **1.037** (IQR 1.006–1.072). So v0 members were ~3.7% fainter than the bursts they stand for.
  - The review's `snr_measured = b × ‖T/σ‖` is exactly `model_snr`: no new cache column was needed.
- **Version.** Manifests carry `version: "v1"` and `load_set()` refuses a manifest of another version. New hashes: val `54cc6d57`, test `c444efd5`, stress `337594c0` (v0 is in git at `496c048`).
- **Twin ladder in the audit.** The same 1000 real repeat pairs and the same fresh backgrounds are used for every variant, with identical nuisance draws (`member(..., off=...)` switches single nuisances off). Each is scored with baseline 1 at full resolution and on 16 × 25 MHz smoothed spectra.
- **Prototyped and rejected (not in the code):** a per-source spectral response estimated from the data, leave-pair-out, so it is not circular with the twin check.

## Results
| variant | full-res gap | 25 MHz gap |
|---|---|---|
| naked (template only, measured S/N) | −6.0% | −7.5% |
| + time shift | −5.9% | −7.9% |
| + residual DM | −6.0% | −7.3% |
| + scintillation | −8.4% | −9.3% |
| **full (v1)** | **−7.6%** | −9.3% |
| full, catalog S/N (v0) | −9.5% | −10.2% |

(Gap = median(sim − real) / median(real). Full v1 vs real: Wilcoxon p = 3e-12, Spearman 0.66.)

- **Uncertainty.** Over three fresh pair draws the full-v1 gap is −9.2 / −10.8 / −9.7%, with bootstrap 95% CIs within −13.4% … −7.0%. The **absolute** gap is therefore ±2 points. The ladder *steps* are paired (same pairs, backgrounds and draws), so they are much tighter than that.
- **Amplitude explains ~2 points** (v0 → v1), not the ~8 points estimated in the review. The xcorr denominator is dominated by noise, so it is not simply the product of amplitudes.
- **Most of the gap exists with no nuisance at all** (naked −6%), and it survives 25 MHz smoothing.
- **Leave-pair-out per-source spectral response does not close it:** −9.0% → −8.8% at full resolution, on the 683/1000 pairs where the source has a third burst.
- **The gap is generic, not source-specific.**
  - Naked-vs-real gap: same-source −3.4%, different-source −5.2%. A prototype over three seeds gave same −5.8 … −7.9% and different −4.7 … −8.5%.
  - **The same-vs-different contrast is preserved:** real +8.2%, naked +10.3% (prototype: real +7%, naked +8%).
  - A shared beam or source structure would make *same-source* real pairs pull away from simulation. They do not.
- **The cause is that the templates miss signal.** The fitburst model leaves unmodelled on-pulse signal energy of median **35%** of the model energy (IQR 17–69%), measured above the noise in the burst box. That missing part is positively correlated between any two aligned bursts (all pairs are centred on the extent midpoint), so real pairs of any kind score higher.
- **Scintillation is not innocent:** it adds ~2 points at full resolution. Its Gamma(N = 1.56 MHz / Δν_d) depth is an assumption, not a calibration.
- **v1 audit** (values that changed; others as in v0): probe (b) AUC **0.524 ± 0.013 → PASS**; centre-offset variant 0.564; (c) ≈ 0; baseline-1 AUC 0.65 / 0.76 / 0.82 / 0.87 by S/N bin.

## Compared with the review
- **Agreed and done:** checkpoint commit first; amplitude fix; twin ladder with smoothed scoring; v1 version bump; "do not tune nuisances until the twins match".
- **Not done, on the evidence:**
  - **Shared beam multiplier per pair.** The different-source check and the leave-pair-out response both say the gap is not source-shared. Adding a shared envelope would be tuning without a physical cause and would widen the same-source contrast, which simulation already slightly overstates.
- **Correction to the previous update.** It concluded that "lensed-vs-repeat is easier in simulation than in real data". The evidence no longer supports that. The gap is a global offset (all pair types, real higher), and the same-source contrast is reproduced. What remains is that the smooth templates understate real burst structure in every class.
- **Correction to an earlier number.** The v0 "−12%" was −0.002 / 0.016 with rounding; on the ladder's definition v0 is −9.5%.

## Next
- **Decision needed: template residual.**
  - The deficit is the "residual term" from the plan's risk list.
  - Option: add a smoothed, significance-thresholded data residual to each template. Shared within `lensed` pairs, it is the real physics of one burst.
  - It reintroduces the T1 shared-noise trap at a lower level, so it needs probe (c) re-run, and residual noise must be shared equally in `repeat` pairs or kept below the probe's sensitivity.
  - Alternative: keep v1 and report the generic −9 ± 2% offset as a limitation, with the contrast check as evidence that the lensed-vs-repeat contrast is preserved.
- Scintillation depth: calibrate against the measured fine-scale variance (`check_freq_structure.py`) instead of assuming Gamma(N).
- Benchmark numbers on v0 must not be quoted; v1 baseline-1 numbers are provisional until the decision above.
