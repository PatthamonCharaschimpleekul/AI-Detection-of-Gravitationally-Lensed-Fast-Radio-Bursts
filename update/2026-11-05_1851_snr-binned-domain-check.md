# Update: domain check per S/N bin. The template offset is a constant ~8% scale, and per-pair scatter is pure noise

- **Date/time:** 2026-11-05 18:51
- **Plan:** [../plan/2026-11-05_1254_pair-injection.md](../plan/2026-11-05_1254_pair-injection.md) (new addendum: permanent Track C calibration on real negatives; hold on training)
- **Follows:** [update 1640](2026-11-05_1640_v2-residual-gates.md)
- **Pipeline box:** `02_injection_labelling/01_injection`
- **Matches plan?** — a diagnostic, not a plan step. It changes how severe the v1 limitation is.

## What we did
- [checks/snr_bins.py](../02_injection_labelling/01_injection/checks/snr_bins.py) samples ~12,000 real burst pairs, half same-source and half different-source.
- Each pair is re-simulated **twice** from its own two templates at their measured S/N, with full v1 nuisances, each time on different fresh backgrounds.
- All three versions (real, sim, second sim) are scored with baseline 1. Bin = min model S/N of the pair. CIs: 1000 bootstraps.
- The second simulation gives the **noise ceiling**: the best sim-vs-real agreement a perfect template could reach, since real and simulated pairs never share a noise realisation.
- Source of the "+3%" in update 1640: it is the **real** same-vs-different contrast (bootstrap of real pairs, +2.9%), not a simulated one.

## Results
| min S/N | n same / diff | real contrast | sim contrast | same-pair offset (sim vs real) | Spearman sim–real / sim–sim ceiling |
|---|---|---|---|---|---|
| 10–15 | 1478 / 1210 | +2.4% [−0.9, +4.8] | +1.7% [−0.7, +4.8] | −7.0% [−9.1, −5.7] | 0.39 / 0.40 |
| 15–25 | 3199 / 2903 | +5.7% [+2.6, +10.2] | +7.6% [+5.2, +10.0] | −8.6% [−10.1, −7.2] | 0.58 / 0.59 |
| 25–50 | 907 / 809 | +63.8% [+47.4, +84.4] | +54.4% [+40.4, +69.9] | −10.0% [−11.9, −8.3] | 0.91 / 0.91 |
| > 50 | 204 / 74 | +278% [+165, +579] | +289% [+135, +633] | −5.7% [−9.8, −3.0] | 0.92 / 0.88 |

(An earlier run of the same script without the ceiling, on another seed, gave the same pattern. Its 10–15 sim contrast was +5.5%; the two agree within their CIs.)

1. **The contrast is strongly S/N-dependent.** It is a few % at S/N < 25 and +60% to +280% above 25. The "+3%" headline was the pooled median, dominated by faint pairs.
2. **The template offset is a near-constant multiplicative scale**, −6 to −10% in every bin, with no S/N trend. At S/N ≥ 25 it is **6–50× smaller than the contrast**. At S/N < 25 it is comparable to the contrast, but there the **real** contrast is itself only a few % (baseline 1 barely separates same- from different-source faint pairs in real data either).
3. **Simulation reproduces the contrast in every bin** (CIs overlap everywhere).
4. **Per-pair scatter is noise, not template.** Spearman sim–real equals the sim–sim ceiling in every bin. The pooled 0.66 from update 1530 is a mixture of the bins and is fully explained by independent noise. A perfect template could not do better.

## Compared with the review
- **Review point 1 (offset ≈ 3× contrast): true for the pooled median, false where the contrast is large.** By bin, the offset only rivals the contrast where the real contrast is also near zero.
- **Review point 2 (Spearman 0.66 breaks the rank claim): refuted.** The scatter sits at the noise ceiling, so the template adds no rank noise. Its only effect on baseline-1 scores is the constant ~8% scale, which does not change ranks within one domain.
- **Review point 3 (the `lensed` class cannot be checked): stands.** There is no real lensed pair. The likely direction can be argued but not measured:
  - The missing ~35% energy is fully shared by the two images of one burst, but only partly correlated between different bursts (the ~8% offset).
  - So real lensed pairs should gain *more* similarity than real repeats.
  - On this argument, v1 understates lensed-vs-repeat separation (conservative), not overstates it.
- **Review step 3 (build v2 per the hatch): not done, and I disagree with doing it.** The hatch config was built and run once under the locked gates in update 1640: G-noise selected 32 ch × 5 samples, θ = 1, and G-twin failed (−11.4%). Running it again with the same gates is the tuning loop the failure path forbids. Option (c), synthetic shared wings, is not needed on this evidence: what it would fix is a constant scale that real-data calibration already absorbs, and it adds knobs.
- **Accepted as permanent design (written into the plan):**
  - Track C and every threshold are calibrated on real-data negatives only, stratified by S/N bin and mask overlap.
  - Training and benchmark numbers stay on hold until the template question is closed.

## Next
- **Decision for the user:** close the template question with v1 (limitation = constant ~8% similarity scale, contrast reproduced in every S/N bin, per-pair agreement at the noise ceiling, real-data threshold calibration). Or name what a new template must achieve that v1 does not, as a new pre-registered gate.
- Once closed: lift the hold and start Phase 3 baselines on v1 (`load_set()`).
- Report benchmark results per S/N bin, since the task is very different above and below S/N ≈ 25.
