# Plan addendum: grouped folds become the Track B primary

- **Date/time:** 2026-11-08 08:45
- **Pipeline box:** `03_models_benchmark/track_B_pairs` (`01_training`, `02_benchmark`); fold sets in `02_injection_labelling/01_injection`
- **Amends:** [plan 1223](2026-11-06_1223_phase3-trackB-benchmark.md), section "Grouped folds: decided by numbers, on val only"
- **Trigger record:** [update 0640](../update/2026-11-08_0640_phase3-stage2-rerun.md). Half-width 0.158 > 0.10, and 5 model-6 runs take 5.2 GPU-h ≤ 24, so the trigger is met.
- **Status:** agreed 2026-11-08 (user: "Approve, start"). Rehearsal (F9) in progress.

## What changes
- **Primary metric:** recall at 1% FPR on out-of-fold (OOF) scores from 5 source-grouped folds over all 80 pool sources. This replaces recall on `test_bright`.
- **Primary comparison:** unchanged in form. Model 6 against `b3_gbm`, which is already chosen on `val_bright` as the best of methods 1–3. Model 6 wins only if the paired difference has a 95% CI lower bound above 0.
- **Everything else in plan 1223 stays:** blinding, Stage 3 transfer criterion, Stage 4 ablations on val, disclosure list.

## Facts this rests on (measured 2026-11-08)
- **Pool:** 34 train, 26 val and 20 test sources, 80 in total. They hold 755, 89 and 103 templates, 947 in total. The two BIG sources hold 361 and 112 templates; both are currently forced into train.
- **Run time on the RTX 5070 Ti, 20,000 steps:** model 6 takes 3716–3752 s. Models 4, 5 and 7 take 667–977 s each.
- **Best vs final checkpoint on `val_bright`, 9 runs that trained:** the final checkpoint at step 20,000 is 0.004–0.072 recall below the selected best, with median 0.018. For model 6 the gap is 0.018, 0.015 and 0.025.

## Decisions (proposed)

**F1. Fold assignment.**
- Fixed rule, rng seed 2027:
  1. Put the two BIG sources first, in folds 0 and 1.
  2. Permute the other 78 sources at random.
  3. Deal them round-robin, starting at fold 2, so every fold gets 16 sources.
- Balancing by source count matches the metric, because pairs are drawn uniformly over sources and the bootstrap resamples sources.
- Template counts will be unequal: the folds holding a BIG source keep fewer training templates. The per-fold source and template counts are reported. Nothing is rebalanced afterwards.
- The assignment is written to `manifests/folds_v1.json` with a sha256 and asserted on every load.
- BIG are held out like any other source. Phase 5 needs every source scored by a model that never trained on it.

**F2. Pools per fold.**
- The training pool for fold k holds the templates and backgrounds from the files of the 64 sources outside fold k.
- The held-out pool holds the templates and backgrounds from fold k's 16 sources. Unrelated partners are drawn from fold k as well.
- This reuses `Pools` with a source list in place of a split name. `make_pair` and `member` are unchanged.
- The same assertions as `inject.py` apply: no template or background crosses the fold boundary.

**F3. Fold sets, frozen.**
- `fold{k}_bright` for k = 0–4, each with 8000 pairs. Floor S/N ≥ 25, four kinds cycled, set seeds 401–405.
- That gives 40,000 OOF pairs in total; `val_bright` has 8000 pairs from 26 sources.
- Version v1.4 adds these sets. The existing hashes are unchanged (asserted).
- Seeds checked against the ones in use: 77–81, 101–103, 201–202, 300–301 and 555 for sets and checks, and 1040–1072 for training streams.

**F4. Training per fold.**
- Settings are exactly those of the Stage 2 rerun: batch 64, AdamW 1e-3, 1000-step warmup then cosine, bf16, 20,000 steps, the current `models.py` including model 7's head LayerNorm.
- One seed per fold, as agreed in plan 1223. Training stream seed is 2000 + 10·model + k.

**F5. Checkpoint: final step, no selection.**
- There is no clean validation set inside a fold. Carving one from the training sources would cost sources and add a rule.
- The final-vs-best gap measured above is small, and using the final step removes the selection optimism already disclosed for val.
- The GBM is refitted per fold. It uses the same recipe (30,000 pairs per floor, 10 and 25, random_state 0) on the fold's training pool, with pair seeds [500 + 2k + floor index, i].
- Baselines 1 and 2 have no training. Their grids stay frozen as set on val.

**F6. Collapse rule (any model, any fold).**
- A run is called collapsed if its mean training loss over the last 1000 steps is ≥ 1.376, within 0.01 of ln 4.
- A collapsed run is counted and reported. It is never rerun or replaced, and its scores go into the metric as they are.
- This applies to model 6 too. Model 6 has not collapsed in any of its 3 runs.

**F7. Metric and paired difference on OOF scores.**
- Every fold-set pair is scored by its fold's model, averaging both member orders.
- The bootstrap uses B = 2000 resamples of the 80 sources with replacement, from one fixed list with seed 2026, shared by all methods.
- In each resample the threshold is the 99th percentile of the resample's pooled repeat + impostor scores across folds, and recall is the share of lensed scores strictly above it.
  - A pooled threshold penalises score-scale differences between fold models. That is the honest number for one system that scores every source.
- d(b) = recall₆(b) − recall_gbm(b). The point estimate is the mean of d, and the CI is the 2.5–97.5 percentiles of the 2000 values.
- **Secondary:**
  - recall with a separate threshold per fold, pooled over folds;
  - per-fold recall with source-bootstrap CIs, to show spread between folds;
  - impostor rejection by type;
  - models 4, 5 and 7 against 6 as ablations, with model 7's collapsed folds marked.

**F8. Timing and blinding.**
- Training on folds puts the 20 test-split sources into training data. Running the folds is therefore the test opening, and it happens in Stage 5 only, after:
  - `04_propagation` signs off the nuisance ranges;
  - all methods are frozen;
  - the `benchmark-v1` tag.
- **Allowed now:**
  - the fold code;
  - `folds_v1.json`;
  - the fold-set manifests and hashes, which build pairs but score nothing;
  - the rehearsal in F9.
- At Stage 5, the fixed-split models (Stage 2 checkpoints) are also run once on `test`, `test_bright` and `stress`. These are secondary: per-S/N bins, the frozen-threshold recall with realised FPR, and the stress set. Those models never saw test sources, so these numbers stay valid.
- At Stage 5 the Stage 3 transfer check runs on each fold's held-out sources with OOF models, in place of the test split.

**F9. Rehearsal on development sources only.**
- Five folds over the 60 train + val sources, 12 per fold, with the same rules F1–F7 and set seeds 411–415.
- Model 6 and the GBM only. No test-split source is read.
- **Purpose:** prove the fold code end to end, measure real per-fold time, and see how wide the OOF CI is.
- **Cost:** about 5 × 1.04 h for model 6, plus the GBM on CPU, so about 5.5 GPU-h.
- The result is reported as development. It may lead to bug fixes, each logged in an update. It may not change F1–F7 settings.

## What we will do (after agreement)
1. Add the fold assignment and fold-aware `Pools` to `inject.py`. Freeze `folds_v1.json` and the rehearsal and fold-set manifests (v1.4). Assert the old hashes.
2. Add `--fold k` to `train.py` and `baselines.py`: training pool from the other folds, final checkpoint, collapse flag in the log.
3. Write `02_benchmark/folds_oof.py`: OOF scoring, the F7 bootstrap and the secondaries. Test it on the rehearsal.
4. Run the rehearsal (F9). Write an update.
5. Stop. The real fold runs wait for Stage 5 gates (F8).

## Expected result
- `folds_v1.json` with 5 × 16 sources, and fold-set hashes recorded.
- Rehearsal: 5 model-6 runs of about 1 h each, none collapsed, with an OOF CI half-width printed. I expect it narrower than 0.158 because it uses 60 sources instead of 26, but I have not checked this.
- Stage 5 cost for all four learned models: 5 × (1.04 + 0.22 + 0.26 + 0.25) ≈ 8.9 GPU-h, plus the GBM on CPU.

## Risks / open questions
- **One seed per fold** mixes seed spread and fold spread. Model 7 may collapse in some folds, and model 6 could in principle too. F6 counts them rather than hiding them.
- **Pooled threshold across five models** may cost recall if fold models' logit scales differ. The per-fold threshold secondary shows how much.
- **BIG folds** train on about half the templates of the others. Uniform sampling over sources limits the effect, but per-fold recall should be read with that in mind.
- **Sources outside the 80-source pool** (fewer than 2 templates) are not covered by any fold. Phase 5 needs a rule for them, such as the mean of all five fold models. That is not decided here.
- **The final checkpoint** is slightly weaker than the selected best on val (median 0.018). The comparison stays fair because every model, including the GBM, gets no selection.
