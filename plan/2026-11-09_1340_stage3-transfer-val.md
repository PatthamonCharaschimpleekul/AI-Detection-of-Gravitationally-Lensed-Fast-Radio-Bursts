# Plan: Stage 3 transfer checks on val-split real cross-source pairs

- **Date/time:** 2026-11-09 13:40
- **Pipeline box:** `03_models_benchmark/track_B_pairs/02_benchmark`
- **Follows:** [plan 1223](2026-11-06_1223_phase3-trackB-benchmark.md), Stage 3 and its correction "Transfer checks must not open the test split"
- **Blinding:** only real pairs from **two different val-split sources** are used. These are true negatives by construction. No real same-source pair is scored, and no test-split file is read.

## Question
Do the methods score real unrelated pairs the way they score simulated unrelated pairs? If real pairs score higher, a method is responding to something the fitburst templates lack, such as real burst structure or RFI. Its simulated recall would then not carry over to real data.

## What we will do
1. **Real pairs:**
   - Every pair (i, j) of eligible val-split burst files from different sources, with model S/N ≥ 10 for both bursts. There are 92 eligible files from 29 sources.
   - Inputs are the preprocessed real waterfalls (`repeaters_256x160.h5`, masked channels already zero), with the same channel mask (`freq_mask` ≥ 0.25) the baselines use.
2. **Simulated twins:**
   - For each real pair, 5 simulated unrelated pairs built from the **same two templates** at their own measured S/N.
   - Backgrounds are drawn from the val pool and never from file i or j. Nuisances follow `make_pair`: shift, residual DM, scintillation, and scattering on one member half the time.
   - The twins make the simulated reference match the real pairs in templates and S/N.
3. **Methods:**
   - Baselines `b1_blk16` and `b2_blk16`.
   - `b3_gbm`, refitted with the Stage 1 recipe. The refit is checked against the saved `val_bright` scores on the first 200 pairs.
   - The 12 Stage 2 checkpoints, models 4–7 × 3 seeds. They never trained on val sources.
   - Every score is averaged over both member orders.
4. **Criterion (plan 1223):**
   - The threshold is the 99th percentile of the twin scores in a bin. A method passes in that bin if the real cross-source FPR at that threshold is ≤ 2%.
   - Bins use the pair's min S/N: [10, 25) and ≥ 25. The headline bin is ≥ 25.
   - A 95% CI on the real FPR comes from a bootstrap over sources.
5. **Secondary:**
   - Real FPR at the threshold from `val_bright` `repeat` + `impostor`. This is the threshold the primary metric actually uses.
   - Split by channel-mask overlap, below or above the median.
   - **Twin test:** Spearman correlation between each real pair's score and its mean twin score, against the sim–sim ceiling (twin 1 vs twin 2).
6. Write `outputs/stage3_val.txt` and an update. The test-split version runs once, in Stage 5.

## Expected result
- About 4000 real pairs, of which about 800 are in the ≥ 25 bin.
- **If a method fails** (real FPR > 2%), it is reported, and no benchmark number for it is quoted until the cause is found. The likely causes are template smoothness and RFI.
- Models that rely on fine structure, such as model 6's correlation layer, are the most likely to fail. That is the point of the test.

## Risks / open questions
- **Small bright bin:** at about 800 pairs and 2%, about 16 pairs are expected above threshold, so the CI on FPR will be wide. Pass and fail are read from the point estimate, as written in plan 1223, with the CI reported.
- **Pairs are not independent:** each burst appears in many pairs. The bootstrap is therefore over sources, not over pairs.
- **The test is one-sided:** it checks the negatives only. Lensed real pairs do not exist, so recall transfer stays untestable.
