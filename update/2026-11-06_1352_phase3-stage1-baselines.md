# Update: Phase 3 Stage 1, baselines 1–3 on val

- **Date/time:** 2026-11-06 13:52
- **Plan:** [../plan/2026-11-06_1223_phase3-trackB-benchmark.md](../plan/2026-11-06_1223_phase3-trackB-benchmark.md)
- **Pipeline box:** `03_models_benchmark/track_B_pairs/02_benchmark`
- **Matches plan?** 🟡 All three baselines ran on val only; the test sets stayed closed. The comparator for the primary test is now fixed. Two results differ from the plan's expectation (below), and a simulator bug was found and fixed.

## What we did
- [baselines.py](../03_models_benchmark/track_B_pairs/02_benchmark/baselines.py) and [metrics.py](../03_models_benchmark/track_B_pairs/02_benchmark/metrics.py) (primary metric and source bootstrap as fixed in the plan, with a self-check). Run: `venv/Scripts/python -I baselines.py`, ~2.5 min on 16 processes.
- Everything reads pixels only: the burst box comes from `find_box()`, not `ext_lo/hi`, and no fitburst parameter is used. Frozen pairs are regenerated and checked against the manifest row by row; the script refuses test sets.
- **1 Cross-correlation:** in the on-pulse boxes, ±24 lags, channels averaged by 1 / 4 / 16.
- **2 Physics statistic:** best fit of one burst to the other over τ (0–3 ms), ΔDM (±0.3 pc/cc), lag and amplitude, both directions, corrected for noise attenuation; same three channel blocks.
- **3 GBM:** 7 measured properties per member, as |difference| and mean. Trained on 60,000 train-split pairs (half with S/N floor 10, half with 25).
- **Self-checks pass:** scores do not depend on member order; an identical pair scores 1 in baseline 1.

## Results
`val_bright`, recall at 1% FPR, lensed vs repeat + impostor, source bootstrap 95% CI (n = 6000, 26 sources):

| method | recall | 95% CI | AUC |
|---|---|---|---|
| 1, 1 channel | 0.057 | 0.047–0.072 | 0.755 |
| 1, 4 channels | 0.096 | 0.074–0.120 | 0.803 |
| 1, 16 channels | 0.171 | 0.115–0.245 | 0.885 |
| 2, 1 channel | 0.091 | 0.054–0.149 | 0.840 |
| 2, 4 channels | 0.111 | 0.075–0.170 | 0.880 |
| 2, 16 channels | 0.164 | 0.119–0.235 | 0.931 |
| **3, GBM** | **0.263** | 0.167–0.404 | 0.928 |

- **Comparator fixed: `b3_gbm`** is the "best of 1–3" for the primary comparison. Differences on the same resamples: baseline 1 −0.097 [−0.195, −0.006], baseline 2 −0.105 [−0.229, −0.005].
- **Called lensed at the 1% FPR threshold, by negative type (best variants):** repeat 0.3%, unrelated 0.1–0.2%, I1 2.0–2.3%, I2 0–0.4%, I1+I2 2.8–2.9%.
- **b3 permutation importance (AUC drop):** |Δ centre frequency| 0.109, |Δ boxcar width| 0.058, |Δ width| 0.058, |Δ slope| 0.044, |Δ bandwidth| 0.020, mean width 0.015. These are burst-similarity features, so it is not winning on S/N or a shortcut.
- **`val` AUC by min S/N (b1 / b2 / b3):** 10–15: 0.788 / 0.795 / 0.830; 15–25: 0.822 / 0.862 / 0.871; 25–50: 0.902 / 0.926 / 0.946; > 50: 0.958 / 0.965 / 0.963.
- **GBM seed spread:** recall 0.264 ± 0.010 (SD, 8 seeds), far below the source CI, so the one-seed rule for baseline 3 stands.

## Compared with the plan
- **Bug found and fixed in `inject.py`.** Non-overlapping I1 template pairs made a member's signal exactly zero, giving NaN: 2 of 60,000 training pairs. No frozen set was affected: the manifests are unchanged, and their hashes were re-asserted. The transfer is now skipped for such pairs (they stay plain repeats), and `member()` asserts a finite scale. A re-scan shows 0 non-finite pairs in 60,000. The GBM's first-run 0.290 came from training data with those NaNs and is discarded.
- **Baseline 2 with 16 channels was added** after seeing that 16 helped baseline 1, so 2 has the same blocks as 1. Allowed by the plan (grids set on val).
- **Expected a matched-filter-like baseline to lead; a feature GBM leads instead.** Baseline 2 has the best-equal AUC (0.931) but not the best recall at 1% FPR.
- **Recall is low (0.16–0.26) although AUC is about 0.93.** At this FPR the false positives are nearly all I1 / I1+I2 impostors, which share the spectrum on purpose. The primary metric is therefore driven by that class, whose strength rests on a simulation choice (envelope transfer, 2/3 of impostors carrying I1). Results must always be reported split by negative type.

## Next
- Stage 2: smoke test with a DataLoader (pairs/s, GPU time), then fix the step budget in an update.
- These are val numbers for development only, not benchmark results.
