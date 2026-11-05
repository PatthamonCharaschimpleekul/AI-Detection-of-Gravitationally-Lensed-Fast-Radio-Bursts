# Plan: build Track B training pairs by injection (lensed copy / intrinsic repeat / unrelated)

- **Date/time:** 2026-11-05 12:54
- **Pipeline box:** `02_injection_labelling/01_injection` (uses `01_semi_synthetic_data/04_propagation` nuisances, v0 ranges below)
- **Follows:** [update 2026-11-05_1051](../update/2026-11-05_1051_catalog2-preprocessing.md)
- **Status:** agreed 2026-11-05 with review changes (marked **[rev]**): common source pool (decision 5), S/N_B ≥ 10, probe (b) sample size and features, frozen sets as manifest + hash, S/N-scaled residual DM, Track B non-goal.

## Context
- Preprocessed data: `repeaters_256x160.h5` (981 × 256 × 160, σ-normalised per channel, masks, `norm/*`, metadata, 20-chunk noise bank).
- Track B asks "is burst j a lensed copy of burst i?". Training pairs need **no lens population and no exposure**: Δt (hours–months) puts the two images in different files, and the flux ratio is drawn directly. The lens population and observation filter are only needed by Track C and ε. **So Track B injection can start now**, before `02_population` / `03_lens_simulator`. Those get their own plan.
- Measured today (`repeaters_256x160.h5`, raw files):
  - Catalog S/N (`snr_fitb`): median 21.7, 90th percentile 51.9. Bursts with S/N ≥ 50 that are not coarse, clipped or sidelobe: **105 from 38 sources, only 16 sources with ≥ 2**.
  - The raw files' `model` dataset (fitburst) is noise-free, full resolution (16384 × N), parameters: amplitude, arrival time, width, DM, scattering timescale/index, spectral index/running.
  - Off-pulse samples per file (window minus extent ± 20): ≥ 60 in **856** files, ≥ 80 in 810.
  - Noise-bank pixels: lag-1 correlation 0.10 in time, 0.02 in frequency (close to white).

## The core problem: shortcuts
A model learns whatever separates the classes most easily. If positives and negatives are built differently, it learns the construction, not lensing. The two worst traps:

1. **Shared noise.** Copying image A's data into image B (B = r·A + noise) copies A's noise into B. Positives then have correlated noise and negatives do not. Restricting the copy to the on-pulse box does not fix it: with scale k = S/N_B / S/N_A, the shared fraction is k²/(1+k²). At k = 0.5 over a ~11 × 100-pixel box that is about a 6σ signal. Keeping k ≤ 0.2 makes injected S/N ≤ 0.2 × template S/N, so only the 105 brightest bursts work and they give mostly sub-threshold pairs.
2. **Shared fine structure.** Scintillation residual at 1.56 MHz is about √(49 kHz / 1.56 MHz) ≈ 18% per channel. A data template carries A's pattern into B, while real lensed images have independent patterns.

**Rule: every pair member, in every class, is built the same way: noise-free template + per-member nuisances + an independent real-noise background.**

## Decisions (proposed, to agree)
1. **Templates = fitburst models of real bursts (T2), for both classes.** Noise-free, so no shared noise and no baked-in scintillation. They keep each burst's real parameters (widths, components, drift, scattering, spectral shape), so intrinsic-repeat negatives keep source-specific variety. Eligible: has `model`, not `coarse_dt`, not `clipped`, not `sidelobe_flag` (count expected ~960).
   - **Realism arm (T1):** scaled real data in the on-pulse box, S/N_T ≥ 50, k ≤ 0.2. Used only in the stress-test set, and to measure the T2-vs-real gap.
   - Rejected: data templates as primary (traps 1 and 2); Gaussian-noise backgrounds (control only, per Project_Description Phase 2.1).
2. **Backgrounds = each file's own off-pulse samples, mirror-tiled to 160.** That gives ~850 real backgrounds, each with its real RFI and channel mask (instead of only 20 chunks). The background's `freq_mask` becomes the member's mask, so masks are independent of the template, as on different days. The 20 true chunks are the reference for checking the tiled ones.
3. **Flux ratio carries no Track B label.** Member A's S/N is drawn from the real `snr_fitb` distribution (≥ 10). Member B's S/N = r × S/N_A with r log-uniform in [0.05, 1], **in every class**, order randomised. Flux-ratio consistency across a source belongs to Track C.
   - **[rev] Both members must be detectable.** A real candidate pair always has two detected bursts, so r is drawn log-uniform in [max(0.05, 10 / S/N_A), 1], which gives S/N_B ≥ 10. This holds in every set; there is no faint-member augmentation in v0.
4. **Training pairs are made on the fly; val / test / stress sets are frozen** (fixed seeds plus a manifest CSV). One shared function `make_pair()` serves both, so training and test cannot drift apart.
   - **[rev] Frozen = manifest + per-pair seed + SHA-256 of the regenerated arrays**, not stored arrays: 3000 pairs × 2 × 256 × 160 float32 would be ~1 GB per set. Loading regenerates and checks the hash, so any code change that alters a frozen set fails loudly.
5. **[rev] One source pool and one source distribution for every class.** All classes draw only from sources with ≥ 2 eligible templates, with sources sampled uniformly (`unrelated`: two distinct sources, each uniform). Otherwise single-template sources would appear only as `lensed` (they cannot make a `repeat`), and the model could learn their morphology as a lensed fingerprint. Deployment matches: a real candidate pair always comes from a source with ≥ 2 bursts.
6. **Templates are binned over all native channels** (the fitburst model is defined everywhere). Using the template file's own channel mask would put the same mask imprint into both members of a `lensed` pair; that would be a leak. The mask comes only from the background.

**Non-goal [rev]:** delays shorter than the 157 ms window (wave-optics or asteroid/stellar-mass lenses, both images in one file) are outside Track B; ~1 ms data cannot resolve them anyway (Krochek & Kovetz 2022).

## What we will do
1. **Split by source first** (prerequisite from `03_split`). Assign the 83 sources to train / val / test (60 / 20 / 20 by eligible-template count, seeded). FRB 20220912A and FRB 20180916B go to train, so they do not dominate the test set. Templates **and backgrounds** are used only inside their split.
2. **Templates.** Bin each eligible `model` to 256 channels with the same block means as `preprocess_catalog2.py` (import its functions). Crop with the same centre and window. Check the model's units against the data (band-summed on-pulse model vs data, per burst); use it only up to a scale, since S/N is set in step 5.
3. **Backgrounds.** For files with ≥ 60 off-pulse samples, mirror-tile the off-pulse columns to 160 and keep the file's `freq_mask`. Check against the 20 genuine chunks: per-pixel histogram, per-channel std, lag-1 time/frequency correlation (KS p > 0.01). If the tiling seams show up, raise the minimum to 80 samples.
4. **Per-member nuisances (v0 ranges, refined later by `04_propagation`).** All are applied independently to each member, in every class:
   - **Residual DM.** Each real file is dedispersed to its own fitted DM, so a lensing ΔDM is mostly removed. What remains is the fit error: Gaussian with σ = the template's `dm_fitb_err` × `snr_fitb` / S/N_injected **[rev]** (a burst injected fainter than it was observed has a worse DM fit), applied as a per-channel sub-sample shift (Fourier).
   - **Extra scattering.** Exponential kernel, τ(600 MHz) log-uniform in [0.01, 1] ms (∝ ν⁻⁴), on a random member, 50% of pairs. Note for `04_propagation`: a shared screen would give same-source pairs a shared τ and `unrelated` pairs independent ones. That is more physical, and since it is symmetric it does not leak.
   - **Scintillation.** A fresh multiplicative gain per channel: the mean of N = 1.56 MHz / Δν_d exponential scintles. Use the source's Δν_d where `dnu_good`, else 49 kHz.
   - **Time offset.** Uniform ±10 samples, plus a sub-sample shift.
   - **Beam/bandpass:** none in v0 training. A smooth random spectral multiplier goes into the stress-test set. Open: use the CHIME beam model if it is available.
5. **Inject.** member = a × template ⊗ nuisances + background, where a is set so the matched-filter S/N over unmasked channels equals the drawn S/N. Zero masked channels, then re-run the same per-channel off-pulse normalisation as preprocessing.
6. **Pair classes** (`make_pair(kind, rng)`):
   - `lensed`: the same template for both members;
   - `repeat`: two different templates from the same source;
   - `unrelated`: templates from different sources.
   - `impostor` stays a placeholder until `05_impostors`.

   Frozen sets: classes 1:1:1, with no source above 20% of a set's pairs. Pair counts are set after the leak audit (start with test = 3000 pairs).
7. **Leak audit: a gate before any model is trained.**
   - (a) Per-member stats (off-pulse std, mask fraction, measured S/N, centre) have the same distribution in every class (KS p > 0.01).
   - (b) Shortcut probe: a GBM on features that carry no lensing information reaches **AUC ≤ 0.55** for lensed vs repeat. **[rev]** Measured on ≥ 2000 pairs per class (fixed seed, separate from the frozen sets), 5-fold cross-validated. Features:
     - mask overlap, S/N ratio, noise-std ratio, centre offset;
     - background source index and MJD (not the 850-level file ID);
     - fitburst parameters of **one** member (random order).

     Parameters of both members are deliberately excluded. In a `lensed` pair they are identical by construction, so their equality *is* the lensing signal and would give AUC ≈ 1 trivially. One member's parameters still catch any morphology or source asymmetry between classes.
   - (c) Shared-noise probe: the correlation of off-pulse residuals between members is consistent with 0 in all classes (T2), and is measured as a function of k for T1.
   - (d) Domain check: baseline 1 (cross-correlation) scores on constructed `repeat` pairs vs real as-observed repeat pairs of the same sources. A clear gap means T2 is too clean; widen the nuisances and report the gap.
8. **Save** template and background caches to `02_injection_labelling/01_injection/data/`, and frozen-set manifests (CSV: per-pair seed, label, template / background IDs, every nuisance value, plus the set's SHA-256) to `outputs/`. Write a gallery of 10 pairs per class.
   - v0 scope: T1 appears only in probe (c). Adding T1 pairs to the stress set is deferred: they need ≥ 2 bright templates per source on both classes (only 16 sources qualify).
   - Mirror tiling leaves a periodicity at lag ≈ 2 × the off-pulse length that the lag-1 check cannot see. It is symmetric across classes, so it does not leak; it matters only when interpreting the stress test.

Script: `02_injection_labelling/01_injection/inject.py` (library with `make_pair()` plus a CLI that writes the frozen sets and runs the audit), run with `python -I`, plus asserts: shapes, no NaN, masks applied, split-disjoint templates and backgrounds, manifest regenerates identical arrays from the seed.

## Expected result
- ~960 templates, ~850 backgrounds, split by source. Backgrounds are statistically indistinguishable from the 20 genuine chunks.
- Leak audit passes: probe AUC ≈ 0.50–0.55, shared-noise correlation ≈ 0 for T2.
- Baseline 1 separates `lensed` from `repeat` almost perfectly at high S/N and degrades towards S/N 10. **If it stays at AUC ≈ 1 down to S/N 10, the injection is too clean, not the task solved:** widen the nuisances before the benchmark.
- Domain check: real repeat pairs score a little higher (less similar) under baseline 1 than T2 repeats, because the fitburst model smooths structure. The size of that gap goes in the paper.

## Risks / open questions
- **T2 is smoother than real bursts.** The fitburst model drops irregular sub-structure. That could make lensed copies easier to recognise than in reality, or hide the very detail the Siamese model would use. T1 and the domain check measure this. If the gap is large, add a smoothed, significance-thresholded data residual to the model (and re-check probe c).
- **Bad fitburst fits** (multi-component, RFI) give wrong templates. The gallery plus a model-vs-data residual χ² cut cover this.
- **Mirror tiling** may leave periodic RFI patterns. Check 3 and the 80-sample fallback cover this.
- **Residual-DM and scattering ranges** are placeholders until `04_propagation` sets them from the literature. Frozen sets get a version tag, and a range change means a new version.
- **Split balance.** Putting the two big sources in train leaves val/test with 81 small sources (median 3 bursts). Some test sources have < 2 eligible templates, so they give `lensed` and `unrelated` pairs but no `repeat` pairs.
- **No beam model in v0 training.** If the stress test shows a large drop from the beam multiplier, it moves into training.

## Addendum 2026-11-05 16:00 — v2 (template + smoothed residual): pre-registered gates, written before any v2 measurement
- **Trigger:** the risk-list escape hatch above ("if the gap is large, add a smoothed, significance-thresholded data residual"). Trigger evidence: [update 1530](../update/2026-11-05_1530_injection-v1-twin-ladder.md) — v1 twin gap −9 ± 2%, generic template deficit (35% unmodelled signal energy), not beam.
- **Why v1 + limitation may not be enough:** at the medians, sim same-source pairs (≈ 0.91 × 1.082 U ≈ 0.985 U) score *below* real unrelated pairs (U). The offset is as large as the class contrast, so a threshold calibrated on sim would over-call `lensed` on real data. Ranking AUC survives; calibrated thresholds (Track C) do not.
- **v2 template:** T + R_s. R_s = the burst's own data residual (X − b·T) in σ units, mask-weighted 2-D boxcar (n_f channels × n_t samples), zeroed on flagged channels, kept only in cells with |R_s| ≥ θ × its noise σ, back in raw units.
- **Prerequisites (measured before any v2 build):**
  1. bootstrap 95% CI of the same/different contrast (real vs naked);
  2. a scan over (n_f, n_t, θ) of recovered residual energy and in-box shared noise.
- **Gates (locked now, one shot):**
  - **G-noise (shared noise in the burst box, `lensed` pairs, at the k = S/N_inj / model_snr that the S/N pool actually produces).** Pixel-scale median ρ ≤ 0.01 **and** a matched detector median z ≤ 1.0. The matched detector smooths both members with the same kernel and correlates over the kept cells, with z = ρ × √(n_kept / n_kernel). Both are measured on a noise-only proxy: the same kept-cell mask filled with smoothed independent real noise, so only the shared noise is counted. The pixel-scale ρ alone is not enough: smoothing lowers shared and independent noise equally, so a detector smoothing at the kernel scale sees ρ ≈ k² / (1 + k²) again.
  - **Config selection rule:** among (n_f, n_t, θ) passing G-noise, take the one recovering the most residual energy. If none passes, **v2 is not built.**
  - **G-twin:** full-v2 twin gap |median| ≤ 2 points, pooled over 3 seeds × 1000 pairs.
  - **G-audit:** probe (b) AUC ≤ 0.55; probe (c) unchanged.
  - Scintillation depth is calibrated against the real fine-scale spectral variance before any v2 freeze.
- "Equal shared noise in `repeat` pairs" cannot be executed: `repeat` members never share R_s. The only branch is "below probe sensitivity" (G-noise).
- **Failure path:** any gate fails → ship v1 and report the quantified limitation (the arithmetic above) → discuss with the advisor. No tuning loop.
