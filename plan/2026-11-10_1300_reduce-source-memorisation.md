# Plan addendum: reduce source memorisation in model 6

- **Date/time:** 2026-11-10 13:00
- **Pipeline box:** `03_models_benchmark/track_B_pairs/01_training`; `02_injection_labelling/01_injection` (training-only option)
- **Follows:** [update 1130](../update/2026-11-10_1130_real-burst-lensed-and-fit-check.md)
- **Amends:** [plan 1223](2026-11-06_1223_phase3-trackB-benchmark.md) (Stage 2 training) and [plan 0845](2026-11-08_0845_grouped-fold-addendum.md) F4 (the training settings the folds freeze)
- **Status:** agreed 2026-11-10 (user: "Approve, start"). The decision rule below is fixed before any result.

## Why
- Model 6 learns which **source** a burst comes from. On seen sources it tells repeat from unrelated almost perfectly (0.86 correct), but on unseen sources half of the repeats are called unrelated.
- Recall is 0.89 on seen sources and 0.70 on unseen ones. Cross-entropy is 0.45 against 1.17.
- The lensed decision itself barely depends on this (0.985 vs 0.951 correct). Even so, capacity spent on source identity is capacity not spent on "same burst or not", and the impostor rows are where unseen-source errors pile up.

## Interventions (training only; frozen sets, baselines' sets and the metric do not change)
**M: merge the unrelated label into repeat in the loss.**
- Unrelated pairs stay in training as negatives, but their target becomes `repeat`.
- The model is then no longer rewarded for telling "two bursts of one source" from "bursts of two sources". That distinction can only be learned on seen sources, by remembering source identity, and the primary task does not need it.
- The model keeps 4 outputs; logit 2 is never a target. `lensed_score` (lensed against the other three) is unchanged.
- Code: one `--merge-unrelated` flag in `train.py`.

**P: a random smooth bandpass per member during training.**
- This is the existing `wide` gain multiplier: amplitude 0.3, cosine terms k = 1, 2, 3, applied to the signal before the noise is added.
- It is used without the other `wide` changes (larger shift, DM and scattering ranges).
- It hides a source's typical spectral envelope.
- **It is physically reasonable:** two lensed images arrive at different times, so the burst sits at a different place in the CHIME beam and sees a different bandpass.
- Code: a `bandpass` argument in `member` and `make_pair`, default off.
  - Frozen sets never set it, so every set hash is unchanged (asserted on `val_bright`).
  - With it on, the training stream draws extra rng values. That is allowed, because training pairs are not frozen.

**Not in this plan:**
- More templates for the lensed class from non-repeating Catalog 2 bursts. That needs a new download and cache, so it is a plan of its own if M and P are not enough.
- Weight decay or early stopping. The curves already plateau, so these are unlikely to help.

## Runs
- Model 6 only, with the Stage 2 settings: 20,000 steps, warmup, batch 64, best checkpoint chosen on `val_bright`.
- Seeds 0–2, so each variant is directly comparable with the current model 6.

| Variant | Runs | GPU-h |
|---|---|---|
| M | 3 | about 3.1 |
| P | 3 | about 3.1 |
| M + P | 3 | about 3.1 |
| **total** | 9 | **about 9.4** (overnight) |

- **GBM fairness:** P is a data change, so `b3_gbm` is also refitted on bandpass-augmented training pairs (P-GBM). The comparator is whichever GBM is better on `val_bright`. M does not apply to the GBM, which is already binary lensed vs rest.
- **GPU check:** the runner waits for a free GPU before each run and has a 2 h timeout per run, as in `run_folds.sh`.

## What is measured, for each variant against the current model 6 (same seeds)
1. **Primary (development):** `val_bright` recall at 1% FPR, paired difference with seeds pooled, source bootstrap. Computed against the current model 6 and against `b3_gbm`.
2. **Memorisation gap:** recall and cross-entropy on `train_bright_chk` (seen templates, no bandpass) against `val_bright`, plus the 4-class confusion. This reuses `fitcheck.py`.
3. **Does not break:**
   - Stage 3 transfer: real FPR ≤ 2% per seed, headline bin.
   - Real-burst lensed test: real/template ratio ≥ 0.8.
   - Both rerun with the existing scripts.

## Decision rule (fixed now)
Adopt the variant with the highest pooled `val_bright` recall among those that meet **all** of:
- (a) pooled recall gain over the current model 6 ≥ +0.03;
- (b) recall gap (seen − unseen) smaller than the current model 6's (0.19 mean);
- (c) Stage 3 passes for all 3 seeds;
- (d) real-burst ratio ≥ 0.8.

If no variant meets all four, model 6 stays as it is, and this is reported as a negative ablation.

Model 4, 5 and 7 are not retrained. They are ablations of the architecture, not of the training recipe.

## If a variant is adopted
- It becomes "model 6" for Stage 5. Plan 0845 F4 is updated to the new recipe before `benchmark-v1`.
- The dev-fold rehearsal (F9) is rerun with it, about 5 GPU-h, to confirm the fold code path.
- **Disclosure:** the recipe was chosen on `val_bright`, whose sources are also part of the 80-source Stage 5 folds. This is mild selection bias, the same kind as choosing the GBM comparator on val. It is stated in the paper.

## Expected result
- I expect M to shrink the repeat-vs-unrelated gap a lot, but I am unsure it moves lensed recall, since the lensed row was already 0.95.
- I expect P to help most on impostors (I1 shares an envelope) and on sources with distinctive bandpasses.
- **A null result is plausible:** the source memorisation may not cost the primary task much.

## Risks
- **Seed noise:** about 0.01–0.02 recall between seeds, which is why (a) asks for +0.03 and not just above 0.
- **P could hurt lensed recall** if real lensed pairs share a bandpass, for example when they are close in time. Real lensed delays for galaxy lenses are days to months, so a shared bandpass is unlikely. For short delays it would matter, and that is a Track C (timing) question.
- **Selection on val_bright** (see disclosure above).
