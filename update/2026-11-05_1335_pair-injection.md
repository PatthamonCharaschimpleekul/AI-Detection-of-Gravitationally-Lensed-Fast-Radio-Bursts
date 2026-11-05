# Update: Track B pair injection v0 (lensed copy / intrinsic repeat / unrelated)

- **Date/time:** 2026-11-05 13:35
- **Plan:** [../plan/2026-11-05_1254_pair-injection.md](../plan/2026-11-05_1254_pair-injection.md) (with the review changes marked [rev])
- **Pipeline box:** `02_injection_labelling/01_injection`
- **Matches plan?** 🟡 mostly. Every step ran, the leak audit passes, and the frozen sets regenerate bit-identically. Two checks had to be redefined after the first run; both are reported with their first-run numbers below. The domain check shows a real gap, in the direction that makes the benchmark **optimistic**.

## What we did
- Wrote [inject.py](../02_injection_labelling/01_injection/inject.py): cache build, `make_pair()`, splits, frozen sets, audit and gallery. Run with `python -I inject.py`; it takes ~15 min the first time (reading the models), then a few minutes.
- **Templates:** the fitburst `model` of each file, binned to 256 channels over **all** native channels (so the template file's mask cannot leak), with the same crop as preprocessing (asserted against `meta/extent_lo` for every file).
- **Backgrounds:** off-pulse columns of each file, mirror-tiled to 160 samples. Each background brings its file's `freq_mask` and per-channel σ, and the template is divided by the *background's* σ, so no day-specific spectral imprint is shared between members.
- **Nuisances per member:**
  - time offset ±10 samples;
  - residual DM with σ = `dm_fitb_err` × `snr_fitb` / S/N_inj → median |ΔDM| 0.052 pc/cc, i.e. a 1-sample sweep across the band (90th percentile 7.8);
  - extra scattering on one member in 50% of pairs;
  - fresh scintillation gains using the source's Δν_d.
- **Stress set:** 3× DM σ, ±20 samples, τ up to 3 ms, and a smooth beam multiplier.
- **Review fixes are in:**
  - one source pool (≥ 2 eligible templates) with uniform source sampling for all classes;
  - S/N_B ≥ 10 (asserted on every frozen pair);
  - probe (b) on n = 4000;
  - frozen sets = manifest + SHA-256;
  - S/N-scaled residual DM.

## Results
- **Cache:** **950 eligible templates**. 968 files have a model; 9 fail the model-S/N-in-data ≥ 5 cut. **856 backgrounds.** Model scale vs data b median **1.039**, so model and data share units (plan step 2 settled).
- **Split by source** (seed 7, the two big sources in train):

  | split | pool sources | templates | backgrounds |
  |---|---|---|---|
  | train | 34 | 755 | 684 |
  | val | 26 | 89 | 89 |
  | test | 20 | 103 | 83 |

  Split-disjointness is asserted for templates and backgrounds. Max single-source share in a frozen set is 4.6–5.9% (rule: ≤ 20%).
- **Frozen sets:** val / test / stress, 3000 pairs each (1:1:1), in [manifests/](../02_injection_labelling/01_injection/manifests/) (~0.8 MB CSV each). `load_set("test")` regenerates identical arrays. The hashes did not change across the three runs today, in which only the audit changed.
- **Leak audit** ([audit.txt](../02_injection_labelling/01_injection/outputs/audit.txt)):
  - **(0) Backgrounds vs their own file's contiguous off-pulse run** (n = 856): lag-1 time correlation +0.006 vs −0.000 (median |diff| 0.008); frequency +0.001 vs +0.001. Tiling preserves the noise.
  - **(a)** Per-member KS p: mask fraction 0.67 / 0.78, S/N 0.63 / 0.10, centre 0.017 / 0.99. Centre at 0.017 is one of 8 tests, so it is not significant after correction. Off-pulse std is exactly 1 by construction.
  - **(b) Shortcut probe: AUC 0.519 ± 0.009 → PASS.** The probe-power check with both members' fitburst parameters gives AUC 1.000. That confirms the probe can see a leak, and that "both members' parameters" encode the lensing answer itself (equality), which is why the probe uses one member only.
  - **(c)** T2 off-pulse noise correlation between members: +0.0001 / −0.0000 / −0.0003 (sd 0.010). Zero, as designed. The T1 trap is confirmed on 105 bright templates: residual correlation 0.019 / 0.060 / 0.272 at k = 0.1 / 0.2 / 0.5 (median z = 1.1 / 3.5 / **17.6**). That is above k²/(1+k²) because model mismatch is shared too.
  - **(d) Baseline 1** (max normalised cross-correlation, ±20 lags): lensed vs repeat AUC **0.65 / 0.74 / 0.82 / 0.88** for min S/N 10–15 / 15–25 / 25–50 / > 50. It is not ≈ 1 at low S/N, so the injection is not trivially clean.
- **Gallery:** `outputs/gallery_{lensed,repeat,unrelated}.png`. By eye: bursts whole, backgrounds independent with real RFI rows and masks, and the mirror symmetry of the tiling is visible in some backgrounds (expected, symmetric across classes).

## Compared with the plan
- **Probe (b) redefined after the first run.** First run: **AUC 0.564 ± 0.014 → FAIL**. A group ablation traced it to the *centre offset* (alone 0.534; all other groups 0.48–0.50). The centre offset measures how alike the two profiles are, which is lensing information, not a construction artefact. So it was wrongly listed as "no lensing information". It was removed from the gate and is still reported (0.554 with it). Off-pulse-std ratio was also dropped (it is ≡ 1). This is a post-hoc change to a gate and is stated as such.
- **Background check (step 3) redefined.** Against the 20 genuine chunks, every KS test failed (lag-1 time 0.006 vs 0.091). The cause is the reference, not the tiling: the chunks all come from 5 long-window files whose noise is time-correlated (raw lag-1 0.05–0.16), while the 158-sample files have ~0. Tiled backgrounds from those same 5 files keep 0.07–0.16. The check now compares each background with its own file. **New fact:** the long-window files have different noise statistics from the 158-sample majority. Worth knowing for anything that uses them as a noise reference.
- **Domain check (d), expected vs found.** The plan expected T2 repeats to look *more* alike than real repeats (model smoother). The opposite came out:
  - Unpaired: real repeat pairs median xcorr 0.016, constructed repeats 0.014, constructed **lensed** 0.017. So real same-source repeats are about as alike as our lensed copies.
  - **Paired twins** (each real repeat pair re-simulated from its own two templates at catalog S/N, n = 1000): sim − real median **−0.002** (~12%), Wilcoxon p = 1e-26, Spearman 0.63.
  - **Meaning:** v0 makes repeats look less alike than reality, so lensed-vs-repeat is **easier in simulation than in real data**, and benchmark numbers on this set would be optimistic.
  - Likely causes, untested: real same-source bursts share a sky position and so a beam/bandpass response; the independent scintillation gains (~18% per channel) decorrelate more than real repeats; catalog S/N ≠ matched-filter S/N.
- T1 appears only in probe (c), as planned for v0. The stress set has no T1 pairs.
- One small discrepancy found: the preprocessing update lists `meta/ncol` and `meta/start` as saved, but the h5 does not contain them. inject.py recomputes the crop start from `pulse_emission_region` and asserts it matches `extent_lo`.

## Next
- **Close the realism gap before any benchmark number is taken.** Run the paired-twin check with one nuisance switched off at a time (scintillation, residual DM, time offset) and with a shared per-source spectral response, to see which one drives the −0.002. Then bump the set version.
- `04_propagation`: literature ranges for residual DM and scattering, and a shared screen (shared τ) for same-source pairs.
- `05_impostors`: plasma lensing, diffractive scintillation, multi-component bursts → the `impostor` class.
- Then Phase 3: baselines 1–3 and the Siamese models on `load_set()`.
