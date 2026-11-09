# Update: Stage 3 transfer check on val-split real cross-source pairs

- **Date/time:** 2026-11-09 15:20
- **Plan:** [plan 1340](../plan/2026-11-09_1340_stage3-transfer-val.md)
- **Code:** `03_models_benchmark/track_B_pairs/02_benchmark/stage3_transfer.py`. Output is in `outputs/stage3_val.txt` and `outputs/stage3_scores.npz` (gitignored).
- **Blinding:** only cross-source pairs from val-split files were used. No same-source real pair was scored, and no test-split file was read.

## Setup
- **Real pairs:** 90 val files (model S/N ≥ 10) from 29 sources give 3851 real cross-source pairs. Of these, 876 are in the headline bin (min S/N ≥ 25).
- **Twins:** 5 simulated twins per pair, built from the same two templates at their measured S/N.
- **GBM refit:** reproduces the Stage 1 `val_bright` scores (asserted on 200 pairs).
- **Criterion (fixed in plan 1223):** in each bin, real FPR ≤ 2% at the twins' 99th percentile. In the headline bin that means at most 17 of 876 pairs above threshold.

## Result
- **Bin [10, 25):** every method passes, with real FPR 0.1–1.4%.
- **Headline bin (≥ 25):**

| Method | Real FPR [95% source bootstrap] | Verdict | Spearman real~twin / sim ceiling |
|---|---|---|---|
| b1_blk16 | 0.007 [0.000, 0.023] | pass | 0.97 / 0.95 |
| b2_blk16 | 0.006 [0.000, 0.023] | pass | 0.97 / 0.95 |
| b3_gbm | 0.009 [0.000, 0.022] | pass | 0.88 / 0.83 |
| model 6, seeds 0 / 1 / 2 | 0.015 / **0.022** / 0.013 | pass / **FAIL** / pass | 0.85–0.88 / 0.88–0.91 |
| model 5, 3 seeds | 0.010–0.013 | pass | 0.93–0.95 / 0.93–0.94 |
| model 4, 3 seeds | 0.007–0.014 | pass | 0.83–0.86 / 0.77–0.81 |
| model 7, 3 seeds | 0.005–0.015 | pass | 0.85–0.91 / 0.74–0.91 |

- **Model 6 seed 1 fails by 2 pairs** (19 against a limit of 17). Model 6 has the highest real FPR of any method in all three seeds.
- **Ranking transfers.** Spearman correlation between each real pair's score and its twins' mean is at or near the sim–sim ceiling for every method. Simulated pairs reproduce how the methods rank real unrelated pairs.
- **At the operating threshold** (from `val_bright` repeat + impostor), real FPR is 0.000–0.007 for every method. That threshold sits far above the unrelated-pair scores, so the primary metric is not affected.

## Investigation: model 6 reacts to zero-padded real windows
- **15% of all real files are short-window files:** more than 5% of the 160-sample window has no data and is zero (`time_mask` = 0). Of the val files in this check, 4% are short-window.
- **Training never shows such windows.** Simulated members sit on mirror-tiled backgrounds that fill the whole window.
- **Model 6's false positives come from them:**

| Pairs in headline bin | b3_gbm | m6 s0 | m6 s1 | m6 s2 | m5 s0 | m4 s0 | m7 s0 |
|---|---|---|---|---|---|---|---|
| no short member (753) | 0.008 | 0.009 | 0.012 | 0.008 | 0.012 | 0.016 | 0.011 |
| one short member (120) | 0.017 | **0.042** | **0.075** | **0.042** | 0.008 | 0.000 | 0.017 |

- **Without short-window members, every method passes,** and model 6 drops to 0.8–1.2%.
- **The hits recur across seeds:** 7 of model 6's pairs above threshold are shared by all three seeds. The most frequent burst is FRB20211120C (file 508), which has data only in columns about 47–108.
- **Reading:** this is a format mismatch between real and simulated inputs, not physics. Model 6's correlation layer sees two windows with the same blank-edge pattern as alike.
- **Why it matters for Phase 5:** the same effect would raise lensed scores for real same-source pairs from short-window files. That is a false-candidate risk, beyond this check.

## Options (decision needed)
1. **Fill missing columns in real windows** with mirror-tiled off-pulse noise from the same file. This is the method the backgrounds were built with. It changes real-data preparation only: frozen sets, training and Stage 2 results are untouched. Then rerun Stage 3. **Recommended:** cheapest, and consistent with the simulation.
2. **Train with real time-mask patterns** applied to simulated members. This needs new training runs for every model.
3. **Exclude short-window files** from transfer checks and the search. This loses 15% of real bursts.

## Next
- A decision on the options above. Then rerun Stage 3, still on val only.
