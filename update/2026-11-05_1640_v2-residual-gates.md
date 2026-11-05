# Update: v2 (template + smoothed residual) fails its pre-registered gate → ship v1

- **Date/time:** 2026-11-05 16:40
- **Plan:** [addendum 16:00 in ../plan/2026-11-05_1254_pair-injection.md](../plan/2026-11-05_1254_pair-injection.md), gates written before any v2 measurement
- **Pipeline box:** `02_injection_labelling/01_injection`
- **Matches plan?** ✅ The one-shot ran as pre-registered. G-noise selected one config, G-twin failed, and the failure path applies: **v1 stays the shipped set**. No tuning loop.

## What we did
Scripts are in [checks/](../02_injection_labelling/01_injection/checks/), run with `python -I checks/<name>.py` from `01_injection/`:
- `v2_prereq.py`: bootstrap CI of the same/different contrast, then the residual scan over n_f ∈ {4, 16, 32} channels × n_t ∈ {1, 3, 5} samples × θ ∈ {1, 2, 3}.
  - Measured per config: recovered residual energy, plus shared noise in the burst box at the k that the S/N pool actually produces.
  - Shared noise was measured on a noise-only proxy: the same kept cells filled with smoothed independent real noise.
- `v2_gtwin.py`: G-twin for the selected config, 3 seeds × 1000 real repeat pairs, with bootstrap CIs.
- The earlier diagnostics (`probe_groups.py`, `excess.py`, `unrel.py`, `resp_proto.py`) are kept there too, so every number in updates 1335/1530 is reproducible. `resp_proto.py` was adapted to the current `member()` signature (the response now multiplies the templates instead of the gain; same arithmetic) and has not been re-run since.

## Results
- **Same/different contrast, with a fresh, larger sample** (1933 same, 1623 different; 2000 bootstraps):

  | | contrast | 95% CI |
  |---|---|---|
  | real | +2.9% | −0.1 … +8.2% |
  | naked | +2.5% | +0.1 … +5.5% |
  | naked − real | −0.5% | −5.2 … +2.9% |

  The earlier +8.2 / +10.3% (update 1530) were single draws; the true contrast is a few percent. Simulation reproduces it within errors.
- **Residual scan.** 6 of 27 configs pass G-noise, all at 32 channels or 16 × 5 with θ = 3.
  - **Pixel-scale ρ is the binding constraint, not the matched detector.** At small kernels ρ = 0.04–0.19, while the matched z can be < 1 because few kernel-sized cells are kept.
  - The best passing config, **32 ch × 5 samples, θ = 1**, recovers only **~10%** of the unmodelled energy (pixel ρ 0.008, matched z 0.46).
  - Configs that recover most of it (4 ch × 3 samples, θ = 1: ~90%) have pixel ρ 0.06 and z 1.6: the T1 trap again.
  - Caveat: recovered fractions > 100% at small kernels show that thresholding biases the noise correction upward there. The ranking is still clear.
- **G-twin, selected config** (pooled, n = 3000):

  | variant | gap | 95% CI |
  |---|---|---|
  | v2, full nuisances | −11.4% | −12.9 … −9.9% |
  | v2, scintillation off (upper bound on similarity) | −9.4% | −11.2 … −8.2% |
  | v2 naked | −8.4% | −9.7 … −6.8% |
  | v1 naked (reference) | −8.1% | −9.6 … −6.2% |

  **FAIL** (gate |gap| ≤ 2 points). The residual that is safe to share changes the gap by +0.3 points (within noise). Even with scintillation off, the gap is −9.4%, so calibrating scintillation depth cannot rescue v2. Scintillation calibration was therefore not done.

## Compared with the plan / review
- **Pre-registration held.** Gates, selection rule and failure path were written down before measuring, then executed once.
- **My objection to the pixel-scale gate was wrong in this regime.** I argued it would pass too easily because smoothing lowers shared and independent noise alike. In fact pixel ρ was the stricter of the two gates here. Keeping both gates was still right: neither alone rules out every config.
- **The review's arithmetic still holds, and is stronger with the corrected contrast.** Pooled full-v1 gap ≈ −9 to −11% against a same/different contrast of ≈ +3%, so sim same-source ≈ 0.90 × 1.03 U ≈ **0.93 U**, below real unrelated pairs (U). The template deficit is about 3× the class contrast under baseline 1.
- **The cause is fixed and quantified:** the fitburst model misses a median 35% of on-pulse signal energy. The only safe way to give that energy back (shared within `lensed` pairs) leaks shared noise unless it is smoothed so hard that ~90% of it is lost again.

## Limitation to report (v1)
Templates are fitburst models, which miss ~26% of real on-pulse signal power (35% of model energy).
- **Effect:** simulated pairs of every kind score ~9–11% lower in baseline-1 similarity than real pairs (twin test, CI ±1.5 points), an offset ~3× the same/different-source contrast. Simulation reproduces the contrast itself within errors (difference −0.5%, CI −5.2 … +2.9%).
- **Ranking metrics (AUC) on simulation are usable. Absolute score thresholds calibrated on simulation are not transferable to real pairs:** they would over-call similarity, and hence `lensed`, on real data. Track C must calibrate on real-data backgrounds (time-scrambled lists, cross-source pairs), not on simulated scores.
- A data-residual template cannot be shared safely between lensed images; the noise-leak scan quantifies this.

## Next
- **Discuss with the advisor.** Ask whether the limitation plus the real-data calibration for Track C is acceptable, or whether a different template source is wanted (e.g. a better burst model, or high-S/N data templates restricted to the stress set).
- Meanwhile v1 is usable for Phase 3 ranking benchmarks. Thresholds for the search come only from real-data backgrounds (already the plan for the false-alarm rate, Sec. 7).
- Nothing in v1 changed today: the frozen hashes stay val `54cc6d57`, test `c444efd5`, stress `337594c0`.
