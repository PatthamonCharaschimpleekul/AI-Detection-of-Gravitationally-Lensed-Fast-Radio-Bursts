# Plan: independent reproduction and Stage 3 transfer check (val sources)

- **Date/time:** 2026-11-09 13:47
- **Pipeline box:** `01_semi_synthetic_data/01_real_data`, `02_injection_labelling/01_injection`, `03_models_benchmark/track_B_pairs`
- **Follows:** [update 2026-11-08_1450](../update/2026-11-08_1450_grouped-fold-rehearsal.md); Stage 3 of [plan 2026-11-06_1223](2026-11-06_1223_phase3-trackB-benchmark.md)
- **Machine:** a second one (desktop RTX 5070 Ti 16 GB, torch 2.10+cu128, 13 GB free disk), not the one that produced the results so far.

## Why
The Track B result is development-only. The PDF summary lists what is missing before it can be claimed. The first item is the real cross-source transfer check, which is not yet run. A rerun on a second machine also tests the frozen sets and the training result.

## What we will do
1. **Reproduce the data.**
   - Run `preprocess_catalog2.py` and `inject.build_cache()` unchanged. A wrapper, `stream_preprocess.py`, downloads each raw file just before it is read and deletes it after, because the disk cannot hold the 13 GB.
   - Regenerate `val`, `val_bright` and the five `dev` fold sets with `load_set` / `load_fold_set`, which assert the frozen hashes.
   - The test sets are not regenerated or read.
2. **Reproduce model 6.**
   - Train model 6, seed 0, with the Stage 2 command (20,000 steps, warmup).
   - Compare its `val_bright` recall at 1% FPR with the original seeds (0.684–0.701).
3. **Stage 3 transfer check, development version** (`02_benchmark/transfer_check.py`).
   - **Real pairs:** all cross-source pairs among val-split templates. These are true negatives by construction, so the check is blinding-safe (decision 1).
   - **Simulated pairs:** `unrelated` val pairs, 12,000 at the S/N floor 10 plus 8,000 at floor 25, on streams 601/602, which no frozen set uses.
   - **Binning:** pair min S/N (10–25, 25–50, ≥ 50, and the headline ≥ 25), crossed with mask overlap split at the real median.
   - **Methods:** b1 and b2 variants, the GBM refitted with the baselines.py recipe, and model 6.
   - **Twin test:** each real pair is re-simulated twice from its own templates at measured S/N, with full v1 nuisances. Report Spearman real–twin against twin–twin per bin.

## Fixed before results
- **Reproduction passes if:**
  - all regenerated hashes match;
  - model 6 seed 0 lands within 0.66–0.72 recall on `val_bright`, the original seed range widened by ±0.02 for a different GPU and torch build.
  - A miss is reported, not tuned away.
- **Stage 3 criterion** (from plan 1223): in each bin, at the threshold giving 1% FPR on simulated `unrelated`, the real cross-source FPR must be ≤ 2%.
  - Headline = the S/N ≥ 25 bin.
  - A failure is reported and investigated before any benchmark number is quoted.
- **Twin test reading:** a real–twin Spearman more than 0.1 below the twin–twin ceiling in a bin with ≥ 100 real pairs counts as "uses something the templates lack".

## Expected result
- Hashes match, unless numpy or scipy versions change floating-point results; that would be worth knowing.
- Baselines pass, given the template-closure evidence for baseline 1. Model 6 is the open question: the upstream update 1909 warned that learned models may key on fitburst smoothness, and real bursts carry 35% more structure than templates. Real cross-source pairs may therefore look more alike to model 6 than simulated ones, which would push real FPR above 2%.

## Risks / open questions
- Only about 90 val bursts from 26 sources, so the S/N ≥ 25 cell may hold few real pairs and wide CIs.
- The mask-overlap split uses the real median, which is fixed from masks alone, before any score is seen.
- Another session may be running Stage 3 on the original machine. This work stays on branch `poc-lr-limit` until the team agrees.
