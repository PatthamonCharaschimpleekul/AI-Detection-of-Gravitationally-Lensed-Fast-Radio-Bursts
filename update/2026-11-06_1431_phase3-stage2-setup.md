# Update: Phase 3 Stage 2 setup (sets v1.3, smoke test, step budget fixed)

- **Date/time:** 2026-11-06 14:31
- **Plan:** [../plan/2026-11-06_1223_phase3-trackB-benchmark.md](../plan/2026-11-06_1223_phase3-trackB-benchmark.md)
- **Pipeline box:** `03_models_benchmark/track_B_pairs/01_training`, `02_injection_labelling/01_injection`
- **Matches plan?** 🟡 Models, self-checks and smoke test are done and the step budget is fixed here before the full runs, as the plan requires. A second simulator bug forced new frozen sets (v1.3). Test sets remain unscored.

## What we did
- [models.py](../03_models_benchmark/track_B_pairs/01_training/models.py): methods 4–7 on one small encoder (72k–259k parameters). [train.py](../03_models_benchmark/track_B_pairs/01_training/train.py): on-the-fly pairs (S/N floor mixed half 10, half 25, as for the GBM), 4-class cross-entropy, AdamW 1e-3 with cosine decay, batch 64, bf16, gradient clip 1, checkpoint chosen by `val_bright` recall at 1% FPR.
- **Step budget, fixed before full runs: 20,000 steps for all models, 3 seeds each**, evaluated every 1000 steps ([run_all.sh](../03_models_benchmark/track_B_pairs/01_training/run_all.sh)).
  - Measured steady state: model 6 about 305 pairs/s (GPU-bound; 8 vs 14 workers made no difference), model 4 about 1300, model 7 about 950. Model 5 not timed.
  - Estimate: about 70 min per model-6 run, about 6.5 hours in total.

## Bug: runaway pixels, sets v1.3
- **Found by** the overfit self-check of model 4: its loss was NaN, because a pixel overflowed float16.
- **Two causes:**
  - Backgrounds `FRB20201125B` and `FRB20210712B` have almost no valid off-pulse data (152–244 unmasked channels with zero variance). Both are in the train split; 0.26% of training members hit them, with pixels up to 5e10. They are now excluded.
  - The per-channel re-normalisation divided by a near-zero off-pulse σ in channels whose off-pulse columns were flagged zeros. It now leaves channels with σ < 0.2 unscaled.
- **`member()` now asserts** |pixel| < 1e4. After the fix, the maximum pixel is 131 in `val_bright`, 156 in `test_bright`, 170 in a 12,000-pair train sample.
- **Effect on frozen sets (old vs new code, pair by pair):** val 0.05%, val_bright 0.05%, test 2.3%, stress 2.6%, test_bright 2.4% of pairs changed, in about 0.2–0.6% of those pairs' pixels. Most test changes come from one background (`FRB20230604C`). Nobody has scored the test sets, so nothing is lost.
- **v1.3 hashes:** val `c02f8a28`, test `98c50b41`, stress `ae9fa9b4`, val_bright `7fc8915b`, test_bright `8c1bb4b4`. The v1 / v1.1 hash asserts are removed, because those sets no longer exist as such. The earlier claim "pairs 0–2999 equal v1" no longer holds exactly.
- **Earlier results:** template-closure numbers (updates 1530–1909) were on the old pixels. They used train-split audit pairs with the 0.26% contamination, and `snr_bins.py` used pools containing the two bad backgrounds. Not re-run: that audit reads real same-source pairs, which are now blinded. Expected effect is small, but it is not measured.

## Results
- **Baselines re-run on v1.3:** b1 and b2 unchanged to 3 digits (0.171, 0.164). **b3_gbm 0.285 [0.180, 0.401]**, AUC 0.925; this replaces the 0.263 in update 1352, whose GBM trained on the contaminated pairs. Comparator stays `b3_gbm`.
- **Self-checks pass:** symmetry of models 5, 6, 7 (assert), correlation layer finds a planted lag, all four models memorise one batch (accuracy 1.000).
- **Shuffled-label control, model 6, 900 steps:** AUC 0.523 then 0.518, loss 1.387 ≈ ln 4. Close to chance, as required, but slightly above 0.5 on 6000 pairs; it is a short run, not a proof of zero leak.
- **Smoke runs (not results):** at 900 steps, model 6 reached recall 0.445, AUC 0.974 on `val_bright`, already above every baseline. Models 4 and 7 are still near chance at 900 steps (AUC 0.64, 0.50).

## Compared with the plan
- The fast rise of model 6 was not expected. It may be real, since the two members share a noise-free template. It may also be exactly what the plan warned about, keying on fitburst smoothness, which real bursts lack. Stage 3 is the test.

## Next
- Full runs, then the val comparison, the grouped-fold trigger and Stage 3.
