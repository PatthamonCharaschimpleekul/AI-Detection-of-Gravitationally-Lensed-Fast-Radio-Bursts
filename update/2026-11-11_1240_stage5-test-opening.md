# Update: Stage 5, the one test opening (grouped folds over all 80 sources, fixed-split secondaries, transfer on held-out folds)

- **Date/time:** 2026-11-11 12:40
- **Plan:** [plan 2026-11-06_1223](../plan/2026-11-06_1223_phase3-trackB-benchmark.md) (Stage 5, "Fixed before results") and [addendum 2026-11-08_0845](../plan/2026-11-08_0845_grouped-fold-addendum.md) (F4–F8)
- **Pipeline box:** `03_models_benchmark/track_B_pairs`
- **Machine:** the second machine (RTX 5070 Ti 16 GB). Everything ran locally on branch `poc-lr-limit`; nothing was pushed, and the `benchmark-v1` tag is local only.
- **Matches plan?** 🟡 The pre-registered procedure was followed exactly, with **one protocol deviation, disclosed:** the test was opened on the user's instruction (2026-11-10 22:20) before `04_propagation` signed off the nuisance ranges (decision 5). Also, all methods are frozen at `benchmark-v1` = `ccbd35a`; the team's M/P variants (plan 1300) are therefore *not* part of this test.

## What we did
- **Tag:** `git tag -a benchmark-v1` at `ccbd35a` (local). It records the model 6 recipe of the Stage 2 rerun and the Stage 1 baselines. `train.py --scheme all` checks the tag.
- **Primary: grouped folds over all 80 pool sources** (scheme `all`, F1–F7), `run_stage5.sh`.
  - **Model 6, folds 0–4:** `train.py --model 6 --fold k --scheme all`. Settings exactly as in F4 (20,000 steps, final checkpoint, one seed per fold, training stream 2000 + 10·6 + k), with 4 data workers for RAM.
  - **GBM per fold:** `02_benchmark/stage5_fold_baselines.py k` repeats `baselines.run_fold` line for line for scheme `all`. The team's function refuses that scheme before Stage 5; its file is unchanged.
  - **OOF metric:** `02_benchmark/folds_oof.py --scheme all --models 6` (team code, unchanged).
  - Fold-set hashes were asserted by `load_fold_set` / the manifest check. No run collapsed (F6).
- **Secondary: fixed split** (`02_benchmark/stage5_fixed_split.py`). Run once on `test_bright`, `test` and `stress`.
  - Methods: baselines 1–2 (frozen grids), the Stage 1 GBM (refitted, asserted against the saved val_bright scores), and this machine's model 6 seeds 0–2. These checkpoints were selected on `val_bright` before the opening.
  - Pairs are regenerated in chunks and asserted against the manifest hashes.
  - The code was dry-run on `val` first. Its per-S/N numbers equal `paper_icaiic/snr_curve.txt`.
- **Secondary: Stage 3 transfer on each fold's held-out sources with its OOF models** (F8 last bullet; `02_benchmark/stage5_transfer_folds.py`).
  - Same rules as the team's `stage3_transfer.py`: `fill_window`, 5 twins per pair, threshold at the twins' 99th percentile, criterion ≤ 2%.
  - Each fold's GBM is refitted with the `run_fold` recipe and asserted against `gbm_fK.npz`.
  - **Compute cap (deviation, disclosed):** at most 4000 real pairs per fold, as a seeded random subset; 18,585 pairs in total.
- **Ablations:** models 4, 5, 7 per fold, finished 16:02 (see the addendum). The session that ran them ended during m4 f1, so the queue was resumed at 12:29 and m4 f1 was retrained from scratch with the same seed.

## Results
- **Primary (pre-registered): model 6 wins.** OOF recall at 1% FPR, lensed vs repeat + impostor, S/N ≥ 25, pooled threshold, source bootstrap (B = 2000, seed 2026, 80 sources). The sample is 10,000 lensed and 20,000 negatives.

  | | Recall [95%] |
  |---|---|
  | Model 6 | **0.436 [0.226, 0.675]** |
  | GBM (`b3_gbm`) | 0.211 [0.153, 0.293] |
  | **Model 6 − GBM** | **+0.226 [+0.067, +0.403]**, half-width 0.168, lower bound > 0 → **win** |

  - **Per-fold thresholds (secondary):** model 6 0.506 vs GBM 0.226.
  - **Per-fold recall, model 6:** 0.861 / 0.189 / 0.576 / 0.457 / 0.449. Fold 1 holds BIG source FRB 20220912A, and its CI is [0.05, 0.80].
  - **GBM per fold:** 0.287 / 0.160 / 0.253 / 0.166 / 0.264.
  - **Negatives above the pooled threshold:**

    | | I1 | I1+I2 | I2 | repeat |
    |---|---|---|---|---|
    | Model 6 | 96/3330 | 95/3247 | 2/3423 | 7/10000 |
    | GBM | 88 | 84 | 8 | 20 |

- **Secondary, fixed split on the 20 test-split sources** (model 6 = this machine's seeds, about 0.05 below the original seeds on val):

  | Set | GBM recall@1% | Model 6 (s0 / s1 / s2) | Model 6 − GBM [95%] | AUC GBM / model 6 | recall@0.1% GBM / model 6 |
  |---|---|---|---|---|---|
  | `test_bright` (S/N ≥ 25) | 0.226 | 0.596 / 0.459 / 0.594 | **+0.323 [+0.115, +0.543]** | 0.934 / 0.976–0.985 | 0.040 / 0.18–0.22 |
  | `test` (S/N ≥ 10) | 0.152 | 0.317 / 0.290 / 0.292 | +0.148 [+0.029, +0.411] | 0.872 / 0.958–0.963 | — |
  | `stress` | 0.068 | 0.154–0.183 | +0.104 [+0.019, +0.228] | — | — |

  - **`test` per S/N** (lensed per bin 537 / 320 / 118 / 25):
    - model 6: [10, 15) 0.21–0.24; [15, 25) 0.29–0.43; [25, 50) 0.31–0.46; [50, ∞) 0.76–0.84;
    - GBM: 0.09 / 0.14 / 0.14 / 0.44.
  - **Frozen `val_bright` threshold on `test_bright`:** realised FPR is 1.5–3.4% for model 6 and 1.5% for the GBM, against a target of 1%. Recall is 0.69–0.74 vs 0.30. The threshold does not transfer exactly between source sets, so search thresholds must come from real negatives, as planned.
- **Secondary, transfer on held-out fold sources (OOF models, 80 sources, 18,585 real cross-source pairs): all pass.**

  | S/N bin | Real pairs | Model 6 | GBM | b1 / b2 |
  |---|---|---|---|---|
  | ≥ 25 | 3472 | 0.010 [0.005, 0.018] | 0.009 | 0.009 / 0.007 |
  | 10–25 | 15,113 | 0.010 [0.007, 0.014] | 0.010 | 0.010 / 0.006 |

  - **Real~twin Spearman, model 6:** 0.91 against a ceiling of 0.90 (S/N ≥ 25), and 0.86 against 0.81 (S/N 10–25). It is at or above the ceiling for every method.

## Compared with the plan
- **Primary: met.**
  - **Shrinkage:** the development rehearsal over 60 sources gave +0.220 [+0.035, +0.381]; the all-source result +0.226 [+0.067, +0.403] agrees and has a lower bound further from zero.
  - **Prediction:** plan 1223 expected "2 or 3 matches 6 at S/N ≥ 25" as a likely outcome. That did not happen.
- **Impostor confusion persists:** I1 / I1+I2 remain almost all of model 6's false positives, as on val.
- **Deviations (both disclosed):** the test was opened before the `04_propagation` sign-off, and the fold transfer check scores a seeded subset. A change of nuisance ranges by `04_propagation` would now require a new set version and a separately reported rerun.

## Next
- `unblind-v1` (Phase 5 search on real same-source pairs) is a separate, later team decision. It is not done here.

## Addendum 2026-11-11 16:30: models 4 and 7 on the folds; the team's scattering sweep
**Ablations by fold (F7 secondary).** Same OOF scores, metric and source bootstrap as the primary. No fold collapsed for model 7 (0 of 5).

| Model | OOF recall [95%] | AUC | Model 6 minus it | It minus GBM |
|---|---|---|---|---|
| 6 (ours) | 0.436 [0.226, 0.675] | 0.982 | — | +0.226 [+0.067, +0.403] |
| 5 classic Siamese | 0.368 | 0.976 | +0.068 [−0.013, +0.154] | +0.158 [+0.031, +0.286] |
| 4 two-channel CNN | 0.299 [0.218, 0.474] | 0.967 | +0.124 [−0.027, +0.287] | +0.102 [+0.024, +0.213] |
| 7 cross-attention | 0.264 [0.156, 0.411] | 0.969 | +0.172 [+0.058, +0.307] | +0.054 [−0.011, +0.138] |

- **Ranking holds; not every gap is resolved.** Model 6 is first, but only its lead over model 7 excludes zero.
- **Paper sentence corrected.** "Every learned model still beats the GBM" is false for model 7 on the folds: its interval includes zero. The paper now says this, both in the main result and in the ablation paragraph.

**Team update 1340 (fetched 16:20): the scattering sweep, and the 04_propagation sign-off not given.**
- Model 6's recall is 0.98× at a differential τ₆₀₀ of 0.3 ms, 0.57× at 1 ms and 0.13× at 3 ms.
- The paper's Limitations now state this, with the Wucknitz et al. (2021) lens-disc case. The paper is still 6 pages.
- **Interaction with this test opening (team decision needed):**
  - The team's plan 1400 (option B, `--wide-scat` training) would replace model 6 if adopted, and it expected to rerun the rehearsal *before* `benchmark-v1`.
  - This machine has already opened the test with the current model 6, at a local tag only.
  - If S is adopted, its test numbers are no longer blind, because the test has been seen. They must be reported as a separate, post-hoc run next to this one, and this run stays the pre-registered result for the current model 6.
  - Nothing here has been pushed. The team's main branch and tags are untouched.
