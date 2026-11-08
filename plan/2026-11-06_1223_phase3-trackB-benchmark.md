# Plan: Phase 3–4, Track B pair benchmark (seven-method ladder)

- **Date/time:** 2026-11-06 12:23
- **Pipeline box:** `03_models_benchmark/track_B_pairs` (`01_training`, `02_benchmark`)
- **Follows:** [update 1928](../update/2026-11-05_1928_impostor-pairs.md), [decision record 1909](../update/2026-11-05_1909_template-closure-v1.md)
- **Status:** proposed. Decisions 1–6 need agreement before code. Metrics and comparison rules below are fixed before any Phase 3 result.

## Context
- **Data:** frozen sets v1.1 (val / test / stress, 4000 pairs each, four classes) and on-the-fly `make_pair()` for training. 34 / 26 / 20 pool sources in train / val / test; 755 / 89 / 103 templates.
- **Goal (RQ1):** does a Siamese encoder separate lensed copies from repeats and impostors better than cross-correlation, physics and feature baselines? "A simpler method wins" is a valid result (Project_Description Sec. 6.3).
- **Measured today:**
  - `make_pair` takes 4.0 ms per pair in one process, so on-the-fly training should not be data-bound with several workers (not yet measured with a DataLoader).
  - Installed torch is 2.13 **CPU-only**. The machine has an RTX 5070 Ti Laptop GPU (12 GB, driver CUDA 13.1) and 32 threads.
  - Test pairs at the headline S/N ≥ 25: **143 lensed, 390 negatives**, from 60 unique lensed templates and 20 sources (val: 141 / 397).

## Problems found while planning
1. **The transfer eval as written breaks the blind protocol.** The addendum to plan 1254 runs models on real repeat pairs. Sec. 7.1 item 7 says the pipeline and thresholds are fixed using simulations, off-pulse data and blind injections only, and that real repeaters are run only after the `unblind-v1` tag. Real same-source pairs are the search data.
   - **Already used, to be disclosed in the paper:** audit (d), (e) and `snr_bins.py` ran baseline-1 scores on real repeat pairs. Only medians and rank statistics were read. No pair was inspected as a candidate.
2. **The headline bin cannot measure the headline metric.** 390 negatives put a 1% FPR at about 4 pairs, and 0.1% cannot be measured at all.
3. **Baseline 1 is a straw man.** It correlates the whole 256 × 160 image, so about 40,000 noise pixels dominate the denominator. Its AUC even falls from 0.82 to 0.79 between S/N 25–50 and > 50. A learned model beating this proves nothing.
4. **The noise-ceiling result holds only for that score.** Update 1851 tested whole-image xcorr. Closing the template question on it does not cover the other six methods.
5. **Baseline 3 can cheat.** Its Sec. 6.3 features include fitburst parameters. Those are identical in a `lensed` pair by construction (probe-power AUC 1.000). Features must be measured from the injected pixels.
6. **Plain feature-map fusion cannot align the pair.** Each member is shifted up to ±10 samples, so the two can differ by up to 20 samples, and |g(A) − g(B)| compares unrelated positions.
7. **Scalar inputs do not exist for these pairs.** Sec. 6.3 lists ΔDM, ΔRM, flux ratio and time separation. The data are Stokes I (no RM), time separation is not simulated, and flux ratio was made uninformative on purpose (plan 1254, decision 3).
8. **The transfer criterion does not apply to learned scores.** "Shift beyond −6 to −10%" is a percentage of xcorr. It means nothing for a logit.
9. **Sec. 7 and the headline point in different directions.** Sec. 7 expects learned gains at low S/N. The locked headline is S/N ≥ 25. The headline stays locked; the primary comparison may well show no gain.

## Decisions (proposed)
1. **Blinding.** Before `unblind-v1`, transfer checks use **cross-source real pairs only**. These are true negatives by construction. No model scores real same-source pairs before the tag, except a blind aggregate: per-S/N-bin score histograms with the top 1% hidden and no pair identities. Time-scrambled lists belong to Track C. The addendum to plan 1254 is amended to match.
2. **Add bright sets (v1.2).** `val_bright` (8000 pairs) and `test_bright` (16,000 pairs), four classes, min S/N ≥ 25, built by redrawing (S/N_A, r) until both members pass. With the floor at 10 the loop never runs, so existing hashes stay valid (asserted). Template count stays small, so **all CIs bootstrap over sources**, never over pairs.
3. **Image-only inputs.** No scalar inputs in any model. Flux-ratio and timing consistency stay in Track C. Project_Description Sec. 6.3 is corrected.
4. **Stronger baseline 1, and a ceiling for every method.** Baseline 1 correlates only inside the on-pulse box, found from the pixels by the same function on simulated and real data (never from `ext_lo/hi`). The twin test is re-run for each method's score, on **cross-source** pairs (blinding-safe).
5. **The test sets stay closed until `04_propagation` signs off** the residual-DM and scattering ranges and the scintillation depth (all still placeholders). All development uses train and val. A range change means new set versions, which is cheap before the test is opened and expensive after.
6. **Scope.** Track B only.

   **Not in this plan:** Track C (needs `02_population`, `03_lens_simulator` and the observation filter), reference likelihood limits, the 1024-channel ablation (needs a new cache), Gaussian-noise and fully synthetic controls, and out-of-fold scoring for the search. The search must score each source with a model that never trained on it, so Phase 5 needs grouped-fold models.

## Fixed before results
- **Task:** `lensed` vs {`repeat`, `impostor`}; score = the method's lensed score, averaged over both member orders.
- **Primary metric:** recall at 1% FPR on `test_bright`, with a 95% CI from a source-level bootstrap.
- **Primary comparison (one):** model 6 vs the best of methods 1–3, where "best" is chosen on `val_bright`. Model 6 wins only if the paired recall difference has a 95% CI above 0. Otherwise the outcome is "physics matches" (Sec. 6.3 outcomes).
- **Secondary:** per-S/N-bin recall and AUC, recall at 0.1% FPR (with CI), `unrelated` included, impostor rejection by type (I1 / I2 / I1+I2), stress set, calibration, gain over baseline 1 vs S/N. Models 4, 5 and 7 are compared with 6 as ablations.
- **Sim FPRs rank methods only.** They are never quoted as false-alarm rates (real negatives only, plan 1254).

## What we will do
**Stage 0: setup**
1. Create a CUDA torch build in `venv/` (gitignored), leaving the system Python alone. Check that it runs on the 5070 Ti.
2. Add `snr_floor` to `make_pair` and write `val_bright` / `test_bright` manifests (v1.2). Assert the v1.1 hashes.
3. Amend plan 1254 and Project_Description (decisions 1 and 3).

**Stage 1: baselines on val** (`02_benchmark/baselines.py`, CPU)
1. **Cross-correlation:** on-pulse box, maximum over ±24 lags and over common channels.
2. **Physics statistic:** maximum over μ, lag, ΔDM and a scattering-τ grid of the fit of B to A ⊗ kernel, both directions, take the larger. Grids are set on val.
3. **GBM on measured features:** width, bandwidth, centre frequency, spectral slope, drift and residual DM, each from the pixels, as absolute differences between members plus each pair's order-invariant means. Trained on `make_pair` output.

**Stage 2: learned models on val** (`01_training/models.py`, `train.py`)
- Shared small CNN encoder, keeping time resolution ≤ 2 samples up to the fusion.
  - **4:** 2-channel CNN (A and B stacked).
  - **5:** classic Siamese (vector embedding + distance).
  - **6 (primary):** feature maps fused as |g(A) − g(B)| and g(A) · g(B), after a **correlation layer over ±24 lags** finds the alignment (problem 6). Symmetric in A and B.
  - **7:** cross-attention between patches of A and B.
- **Training:** 4-class cross-entropy, classes uniform, pairs on the fly, AdamW, mixed precision, same step budget for all models. 3 seeds per model. Checkpoint chosen by `val_bright` recall at 1% FPR.
- **Smoke test first:** measure pairs/s and GPU time on one model, then fix the step budget in an update before the full runs.
- **Self-checks:**
  - model 6 output unchanged when A and B swap (assert);
  - overfit one batch;
  - identical noise-free pair scores above any `repeat` in every baseline;
  - **shuffled-label run gives AUC ≈ 0.5** (catches a leak in the training loop).

**Stage 3: transfer checks** (after the first learned model, for every method)
- Real cross-source pairs from **test-split sources only**, by S/N bin and mask overlap, vs simulated `unrelated` pairs in the same bin.
- **Criterion (replaces the percentage rule):** at the threshold giving 1% FPR on simulated `unrelated` in that bin, the real cross-source FPR must be ≤ 2%. Failure is reported and investigated before any benchmark number is quoted.
- Cross-source twin test: Spearman sim–real vs sim–sim ceiling per bin. A score below its ceiling is using something the templates lack.

**Stage 4: ablations on val** (model 6 only)
- No correlation layer.
- Hard-negative oversampling in training (most similar repeats of a source), with the test distribution unchanged.
- Impostors removed from training.
- I1 limited to envelope overlap ≥ 0.3, only if a model is shown to exploit the non-overlap pairs.

**Stage 5: one test run**
- Requires decision 5 signed off, all methods frozen, git tag `benchmark-v1`.
- Run all seven methods once on `test`, `test_bright` and `stress`. Write the benchmark table.
- Any change after this is reported separately with its reason.

## Expected result
- The stronger baseline 1 and baseline 2 do much better at S/N ≥ 25 than the old xcorr (AUC 0.79–0.82).
- **"2 or 3 matches 6" at S/N ≥ 25 is a likely outcome.** At high S/N a matched filter is near optimal, and any learned gain should sit at lower S/N (a secondary result).
- Model 6 beats 5 on impostors and misaligned pairs, if fusion matters.
- Baselines cannot separate I2 impostors much better than repeats at 1.56 MHz resolution.

## Risks / open questions
- **Few sources.** 20 test sources give wide CIs, and the primary comparison may be inconclusive. Grouped folds over all sources would help, at about five times the training cost. Decide after the smoke test.
- **Template memorisation.** 755 templates, with two sources holding 63% of them (361 + 112). Watch the train-vs-val gap. Sampling is uniform over sources, so most of the two big sources' templates are rarely seen.
- **Smooth templates.** Learned models may key on fitburst smoothness. The transfer checks are there to catch this, and they use cross-source pairs, which do not test the `lensed` class. That class stays unverifiable on real data.
- **Blinded histograms** are still a look at real same-source data. If decision 1 should be stricter, drop them.
- **`04_propagation` may land late** and hold back the test run. Development can continue meanwhile.

## Agreed 2026-11-06: decisions 1–6 accepted, plus these rules (fixed before any Phase 3 code or result)
**Threshold provenance (primary metric).** The sim FPR is a ranking statistic, so the primary is a ROC point: in each bootstrap resample, for each method and seed, the threshold is the 99th percentile of that resample's `repeat` + `impostor` scores, and recall is the share of `lensed` scores strictly above it. Thresholds are therefore recomputed inside the resample, so the CI includes threshold uncertainty, and every method sits at exactly the same FPR. **Secondary:** the threshold frozen on `val_bright` at `benchmark-v1`, reporting recall *and* realised test FPR. No sim threshold is ever used in the search.

**Paired difference and seeds.**
- Checkpoint is selected per seed on `val_bright`.
- B = 2000 resamples of test sources with replacement, one fixed list (seed 2026) shared by all methods and seeds. Pairing means both methods' recalls are computed on the same resample.
- For model 6 seed s and resample b: d(b, s) = recall₆(b, s) − recall_best(b). Point estimate = mean of d. CI = 2.5–97.5 percentiles of the pooled 3B values, which keeps seed spread in the interval.
- Baselines 1 and 2 are deterministic; baseline 3 uses one fixed seed.
- Model 6 wins only if the lower CI bound is above 0.

**Transfer checks must not open the test split (correction to Stage 3).** During development, Stage 3 uses real cross-source pairs from **val-split** sources and simulated `unrelated` from val. The test-split version runs once in Stage 5.

**Grouped folds: decided by numbers, on val only.** After Stage 2, compute the 95% CI half-width of the primary difference on `val_bright`.
- **Trigger:** half-width > 0.10 recall **and** 5 × (measured time of one model-6 run) ≤ 24 GPU-hours.
- **If triggered:** before the test is opened, the primary changes to out-of-fold scores from 5 source-grouped folds over all pool sources, with settings frozen and one seed per fold. This needs its own plan addendum and bright sets per fold, and it replaces `test_bright`. Those models are also the out-of-fold models Phase 5 needs.
- **If not triggered:** the fixed split stays primary, and folds wait for Phase 5.
- The decision is written in an update before `benchmark-v1`. It is never revisited after the test is opened.

**GPU gate (Stage 0).** Pass = `torch.cuda.get_device_capability()` is (12, 0), `sm_120` is in `torch.cuda.get_arch_list()`, and one real conv + backward step in mixed precision runs with finite loss.
- **Fallback, pre-agreed:** try one other official CUDA wheel. If that also fails, train on CPU with encoder channels halved and a step budget set so one run takes ≤ 6 hours. All models then use the same reduced setup, keep 3 seeds, and the change is recorded in an update.

**Disclosure list for the paper: every use of real same-source pairs before `unblind-v1`.** Only medians, rank statistics and bootstrap summaries were read; no pair was inspected as a candidate.
- `inject.py` audit: (d) real repeat pairs, the twin ladder, the same/different contrast, and (e) the FRB 20201124A control (update 1928).
- `checks/`: `resp_proto.py`, `excess.py`, `unrel.py`, `v2_prereq.py`, `v2_gtwin.py`, `snr_bins.py`.

## Addendum 2026-11-08: grouped folds
Trigger met (update 0640). The fold design is in [plan 0845](2026-11-08_0845_grouped-fold-addendum.md), status proposed.
