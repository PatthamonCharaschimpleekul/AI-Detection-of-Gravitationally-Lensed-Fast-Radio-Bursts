# Update: Phase 3 Stage 2 rerun with warmup (fold trigger met again)

- **Date/time:** 2026-11-08 06:40
- **Plan:** [../plan/2026-11-06_1223_phase3-trackB-benchmark.md](../plan/2026-11-06_1223_phase3-trackB-benchmark.md), note [../plan/2026-11-07_0000_stage2-warmup-rerun.md](../plan/2026-11-07_0000_stage2-warmup-rerun.md)
- **Pipeline box:** `03_models_benchmark/track_B_pairs/01_training`, `02_benchmark`
- **Matches plan?** 🟡 All 12 runs done with warmup (all models) and LayerNorm (model 7). One run crashed and was rerun; one model-7 seed still did not train. Fold trigger met. Test sets remain unscored.

## What we did
- Reran all 12 runs, 16:35 on 2026-11-07 to 06:32 on 2026-11-08. First-run outputs are kept in `01_training/outputs/nowarmup/` (with their `stage2_val.txt`).
- **Crash:** `m5_s2` stopped near step 10,000 with `CUDA error: out of memory` at about 20:30. The process then hung, and the queue stood still until 21:29, when it was stopped by hand. Throughput had dropped from about 1200 to 900 pairs/s from step 5000, so something else was likely using the machine. Cause not found. The run was redone from scratch with the same command; the crashed log is kept as `run_m5_s2_crashed.log`.
- **Known weakness:** a crash inside `train.py` can leave the process hanging. Not fixed.

## Results (`val_bright`, development numbers; checkpoints chosen on this set)

| Method | Recall by seed | AUC | Difference vs `b3_gbm`, seeds pooled | First run (no warmup) |
|---|---|---|---|---|
| `b3_gbm` | 0.285 [0.180, 0.401] | 0.925 | n/a | same |
| Model 6 | 0.701, 0.698, 0.684 | 0.985–0.988 | **+0.394 [+0.226, +0.542]** | +0.365 [+0.216, +0.504] |
| Model 5 | 0.500, 0.559, 0.541 | 0.976–0.977 | +0.244 [+0.024, +0.436] | +0.237 [+0.034, +0.402] |
| Model 4 | 0.423, 0.409, 0.407 | 0.957–0.960 | +0.131 [−0.003, +0.266] | one dead seed |
| Model 7 | 0.471, **0.013**, 0.579 | 0.972, **0.494**, 0.979 | not meaningful (one dead seed) | all seeds dead |

- Model 6 minus model 5, seed-paired: +0.150 [−0.015, +0.349]. Still not shown.
- Model 6 per S/N bin: about 0.67–0.70 at 25–80, 0.73–0.77 above 80 (`b3_gbm`: 0.23, 0.37, 0.52).
- False positives at the 1% threshold are still mostly I1 and I1+I2 impostors (about 36–38 of 40), for model 6 and `b3_gbm` alike.
- **`m7_s1` did not train:** loss 1.386 for all 20,000 steps. In the 4000-step test the same seed started learning near step 3000. No further fix is agreed; model 7 is reported as failing to train in 1 of 3 seeds.

## Grouped-fold trigger
- Half-width **0.158** (> 0.10); 5 × slowest model-6 run **5.2 GPU-h** (≤ 24). **Triggered**, as in the first run.
- By the agreed rule, the primary becomes 5 source-grouped out-of-fold scores before the test is opened. Needs a plan addendum and bright sets per fold.

## Disclosure
- Warmup and the model-7 LayerNorm were added after seeing val results of the first run. Both runs are reported.

## Next
- Plan addendum for grouped folds, then Stage 3 transfer checks. Not started.
