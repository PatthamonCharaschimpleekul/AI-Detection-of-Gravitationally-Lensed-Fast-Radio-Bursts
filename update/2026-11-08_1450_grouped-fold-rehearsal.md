# Update: grouped-fold code and rehearsal (F9)

- **Date/time:** 2026-11-08 14:50
- **Plan:** [plan 0845](../plan/2026-11-08_0845_grouped-fold-addendum.md), agreed 2026-11-08
- **Pipeline box:** `02_injection_labelling/01_injection`, `03_models_benchmark/track_B_pairs`
- **Status:** rehearsal done on the 60 dev sources (train + val). No test-split source was read or scored. The real fold run waits for the Stage 5 gates (F8).

## Code (commit aaa6f45 plus fixes in this commit)
- **`inject.py`:**
  - `assign_folds` implements F1.
  - `Pools` now also accepts a set of source names.
  - `fold_pools` implements F2. `load_fold_set` regenerates a fold set and checks its hash.
  - `inject.py --folds` freezes `manifests/folds_v1.json` and writes one csv per fold set.
- **`train.py --fold K --scheme dev|all`:** Stage 2 settings, stream seed 2000 + 10·model + k, final checkpoint, F6 collapse flag. Writes `fold_scores.npz`. Scheme `all` refuses to run without the `benchmark-v1` tag.
- **`baselines.py --fold K`:** the GBM is refitted on the other folds with pair seeds [500 + 2k + floor index, i]. Baselines 1 and 2 use the frozen grids. The held-out pairs are checked against the fold manifest.
- **`02_benchmark/folds_oof.py`:**
  - F7 primary: pooled threshold, source bootstrap with B = 2000 and seed 2026, paired difference.
  - Secondaries: per-fold thresholds, per-fold recall, false positives by type.
  - Self-check of the per-fold threshold function.
- **`01_training/run_folds.sh`:** skips finished folds, waits for a free GPU before each run, and applies a 2 h timeout per run.
- **Deviation from the plan:** VERSION stays v1.3 rather than v1.4. `make_pair` is unchanged, and bumping VERSION would force every existing manifest to be rewritten. The fold sets carry their own hashes in `folds_v1.json`. The `val` and `val_bright` hashes were re-checked and still reproduce.

## Fold sets frozen
| Fold | dev: held-out sources / templates | dev: training templates | all: held-out sources / templates |
|---|---|---|---|
| 0 | 12 / 441 (FRB20220912A) | 403 | 16 / 439 |
| 1 | 12 / 188 (FRB20180916B) | 656 | 16 / 196 |
| 2 | 12 / 69 | 775 | 16 / 118 |
| 3 | 12 / 71 | 773 | 16 / 78 |
| 4 | 12 / 75 | 769 | 16 / 116 |

Backgrounds come only from pool sources' files, so 3 of 771 dev backgrounds are unused.

## Incidents
- **Smoke test, out of RAM:** the held-out set was built after the 12 data workers had started. Fixed by loading it before training.
- **Fold 1, CUDA out of memory at step about 1000 (10:31):** Ollama (`deepseek-r1:14b`) had loaded onto the GPU and held 9.4 GB of 12 GB. Throughput had fallen from 350 to 135 pairs/s before the crash, the same pattern as the m5_s2 crash on 2026-11-07, which was probably the same cause.
  - The hung process was killed and fold 1 rerun from scratch. Its loss at step 1000 was identical (1.0257), as expected from fixed seeds.
  - The OOM log is kept as `run_m6_f1_oom.log`.
  - The runner now waits for under 2.5 GB of GPU memory in use before each fold. It cannot stop Ollama loading in the middle of a run.
- **`folds_oof.py` first run:** it failed on the import path under `-I`, then on a bug in its own self-check data, where two of the toy folds held only positives. Both were fixed. The metric code was unchanged.

## Rehearsal results (development; `outputs/folds_dev/oof.txt`)
- **Model 6 runs:** 0.95–0.97 h each. None collapsed: tail loss 0.46–0.50, far from the F6 threshold of 1.376.
- **GBM:** about 2.5 min per fold on CPU.

**Primary (F7), 60 sources, 10,000 lensed and 20,000 negatives:**

| Method | OOF recall at 1% FPR [95% source bootstrap] |
|---|---|
| model 6 | 0.467 [0.253, 0.662] |
| b3_gbm | 0.246 [0.199, 0.297] |
| **difference** | **+0.220 [+0.035, +0.381]**, half-width 0.173 |

- In the rehearsal the lower bound is above 0, so model 6 would win. This is a development number only.
- **The half-width did not narrow.** At 0.173 it is wider than the 0.158 from `val_bright`. The plan expected it to be narrower; that expectation was wrong. The spread between folds is what widens it.
- **Per-fold thresholds instead of one pooled threshold:** model 6 0.488, GBM 0.251. So differences in score scale between fold models cost only about 0.02.

**Per fold, recall [source bootstrap inside the fold]:**

| Fold | model 6 | b3_gbm |
|---|---|---|
| 0 | 0.662 [0.41, 0.99] | 0.220 |
| 1 | 0.728 [0.60, 0.95] | 0.335 |
| 2 | 0.570 [0.26, 0.82] | 0.191 |
| 3 | 0.355 [0.15, 0.85] | 0.237 |
| 4 | **0.123** [0.04, 0.83] | 0.274 |

**Why fold 4 is low: one source sets the threshold.**
- FRB20210504D has only 2 templates. Every one of its repeat and impostor pairs therefore uses the same two bursts.
- Model 6 scores those pairs high: 32 of the roughly 63 negatives above fold 4's 1% threshold come from this one source. The threshold rises, and 9 of the 12 sources drop to lensed recall of 0.06 or less.
- FRB20210305A plays the same role in fold 3 (23 negatives above threshold).
- The GBM is spread more evenly across sources: 18 false positives from FRB20210504D in fold 4.
- **Reading:** this is not a code fault. Two different bursts from a 2-burst source can look alike to model 6, and at 1% FPR a handful of such sources decides the threshold. It is a real property of the method that the paper should show, for example as per-source false-positive counts.
- These are dev sources, so looking at them per source does not touch the test.

**False positives at the pooled threshold:**

| Type | model 6 | b3_gbm |
|---|---|---|
| I1 | 94 / 3238 | 83 / 3238 |
| I1+I2 | 101 / 3292 | 88 / 3292 |
| I2 | 3 / 3470 | 7 / 3470 |
| repeat | 2 / 10000 | 22 / 10000 |

Model 6's false positives are almost all I1 impostors, the same as on `val_bright`.

## What this means for Stage 5
- The fold code works end to end: 5 trainings, 5 GBM fits, and the OOF report.
- **Stage 5 cost estimate for 4 learned models:** 5 × (0.96 + 0.22 + 0.26 + 0.25) ≈ 8.5 GPU-h.
- Per F9, nothing in F1–F7 changes because of these numbers.
- **Expect a wide OOF CI at Stage 5 as well,** because source-level heterogeneity dominates. 80 sources will help somewhat. I have not estimated by how much.

## Next
- **Still open:** the σ question and the `04_propagation` sign-off.
- Stage 3 transfer checks on val-split cross-source real pairs.
- Before Stage 5, `baselines.py` needs the same tag check for scheme `all` as `train.py`. It currently refuses outright.
