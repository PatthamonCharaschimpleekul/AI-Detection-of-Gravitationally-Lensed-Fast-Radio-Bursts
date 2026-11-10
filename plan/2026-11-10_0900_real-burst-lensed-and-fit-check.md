# Plan: real-burst lensed test, and over/underfitting check

- **Date/time:** 2026-11-10 09:00
- **Pipeline box:** `03_models_benchmark/track_B_pairs/02_benchmark`
- **Follows:** [update 1520 (Stage 3)](../update/2026-11-09_1520_stage3-transfer-val.md)
- **Status:** criteria below are fixed before any result.

## A. Do the models rely on smooth fitburst templates? (real-burst lensed test)
Stage 3 checked negatives only. Here the lensed class is built from **real bursts** instead of templates.

**Construction**
- **Bursts:** val-split eligible files with model S/N ≥ 50, so 15 bursts from 10 sources. Real windows go through `fill_window`.
- **Cutout:** the real window inside the burst's extent ± 20 samples (`OFF_PAD`), zero outside. This keeps the burst's own noise to the box.
- **Pseudo-lensed pair:** two copies of the cutout, each injected by `member()` on its own val background with independent nuisances (shift, residual DM, scattering on one member half the time, scintillation). The amplitude is a fixed k, so the injected S/N is k × the burst's S/N.
- **Template control:** exactly the same draws (backgrounds, nuisances), with the fitburst template injected at the same S/N instead of the cutout.
- **Noise-only control:** the same cutout box filled from the burst file's own off-pulse background (no burst) with the same k. Any score here comes from noise that both copies share.
- **Pairs:** 40 per burst and version, with rng([41, file, n]).
- **Two S/N settings:** 25 for every burst (k = 25 / S/N ≤ 0.5) and 40 for bursts with S/N ≥ 80.
- **Shared noise:** each copy carries the same real noise, a share of k²/(1 + k²) of its noise inside the box. At k ≤ 0.5 that is at most 20%. This biases the real version upward, which is why the noise-only control is there.

**Scoring and criterion (fixed now)**
- All Stage 2 checkpoints plus `b3_gbm` and `b2_blk16` are scored, averaged over both member orders.
- Recall is measured at the operating threshold: the 99th percentile of each method's `val_bright` repeat + impostor scores.
- **Pass for model 6 (3 seeds pooled, S/N 25):**
  1. real-version recall ≥ 0.8 × template-version recall;
  2. real-version recall > `b3_gbm` real-version recall;
  3. noise-only recall ≤ 0.05. Above that, shared noise alone can carry the score, and the test is reported as not interpretable.
- CIs come from a bootstrap over the 10 sources.
- **Secondary:** the same on train-split bursts (80 bursts with S/N ≥ 50). Template copies there were seen in training, so the train comparison leans toward the template version. That makes it conservative for this test.
- **Blinding:** each pair is two copies of **one** burst. No pair of two different bursts from one source is scored.

## B. Over/underfitting check (all Stage 2 checkpoints)
1. **Learning curves** from each `log.csv`: training loss and `val_bright` recall/AUC every 1000 steps.
   - **Underfitting signs:** validation recall still rising at step 20,000 (slope over the last 5 evaluations > 0.01 per 1000 steps), or training loss still falling clearly.
   - **Overfitting signs:** validation recall falling after its peak, with the final value more than 0.05 below the best.
2. **Generalisation gap:** a fresh bright set from **train** templates and train backgrounds (`train_bright_chk`, 8000 pairs, seed 211, floor 25, four kinds cycled). The pairs are new, but the templates were seen in training. Compare against `val_bright` (unseen sources):
   - 4-class cross-entropy, AUC and recall at 1% FPR.
   - Gap = train − val. A recall gap > 0.10 or a cross-entropy gap > 0.10 is called **template overfitting**.
3. **Capacity:** overfitting one batch already passes for all models. Underfitting is called if train and val cross-entropy are both high and close, and if the 4-class confusion shows errors beyond the pairs that cannot be separated (I2 vs repeat).
4. **Grouped folds (already run):** the held-out fold vs training folds for the 5 dev-fold model-6 runs, using the same set construction.

## Expected result
- A gives model 6 a real/template recall ratio with CI. If the ratio is clearly below 0.8, the simulated recall overstates real performance and the PoC claim must be weakened.
- B gives per-model curves and gaps. I expect a small template-overfitting gap, because there are only 755 training templates and the two BIG sources dominate them.

## Risks
- **15 val bursts from 10 sources** give a wide CI. The train-split secondary adds numbers but is biased in a known direction.
- **The cutout's box edge** gives a small step in noise level (variance 1 + k² inside). Both copies have it.
