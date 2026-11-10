# Update: real-burst lensed test, and over/underfitting check

- **Date/time:** 2026-11-10 11:30
- **Plan:** [plan 0900](../plan/2026-11-10_0900_real-burst-lensed-and-fit-check.md). Criteria were fixed before the runs.
- **Code (in `03_models_benchmark/track_B_pairs/02_benchmark`):** `realburst.py`, `fitcheck.py`; results in `outputs/realburst.txt` and `outputs/fitcheck.txt` (gitignored).
- **Supporting changes:**
  - `inject.member()` takes optional `S0, amp` to inject a given image at a fixed amplitude, with the same rng draws. With the defaults, behaviour is unchanged.
  - `baselines.fit_gbm` and `stage3_transfer.operating_negatives` are shared helpers. `stage3_transfer.py` now uses them.
- **Blinding:** every real-burst pair is two copies of **one** burst. No test file was read.

## A. Real-burst lensed test: PASS
**Setup**
- **Bursts:** 15 val bursts with model S/N ≥ 50, from 10 sources.
- **Pseudo-lensed pairs:** two copies of the real burst's cutout (extent ± 20 samples, tapered), each with independent nuisances on its own val background.
- **Controls, same draws:** template copies, and noise-only copies made from the burst file's own off-pulse noise.
- **Threshold:** the operating threshold from `val_bright`.

**Val bursts, injected S/N 25 (k median 0.17, shared noise ≤ 3%)**

| Method | real | template | noise-only | real / template [95% source CI] |
|---|---|---|---|---|
| **model 6 (3 seeds)** | **0.663** | 0.691 | 0.000 | **0.96 [0.89, 1.06]** |
| model 5 (s0 / s1 / s2) | 0.35 / 0.34 / 0.31 | 0.42 / 0.47 / 0.42 | 0.000 | 0.84 / **0.72** / **0.74** |
| model 4 | 0.28–0.34 | 0.32–0.35 | 0.01–0.11 | 0.81–0.98 |
| model 7 (s0, s2) | 0.37, 0.54 | 0.38, 0.58 | 0.000 | 0.97, 0.93 |
| b3_gbm | 0.178 | 0.192 | 0.022 | 0.93 [0.65, 1.36] |
| b2_blk16 | 0.235 | 0.437 | **0.360** | not interpretable |

- **Criterion (model 6):**
  - real ≥ 0.8 × template: 0.663 ≥ 0.553, yes.
  - real > GBM real: 0.663 > 0.178, yes.
  - noise-only ≤ 0.05: 0.000, yes.
  - **PASS.**
- **S/N 40 (13 val bursts):** model 6 ratio 0.99 [0.91, 1.13].
- **Train-split bursts (80; biased toward the template version):** model 6 ratio 1.01–1.02.
- **Reading:**
  - Model 6 identifies two copies of a real burst, with its fine structure and real noise, about as well as two copies of a smooth template. **It does not rely on template smoothness.**
  - **Shared noise does not drive model 6:** the noise-only copies score 0.
- **Model 5 relies on smoothness:** its ratio falls to 0.72–0.84 at S/N 25, and two seeds have a CI below 0.9. This is a second argument for the correlation layer, beside the val result.
- **Baseline 2 reacts to the shared noise** (noise-only recall 0.36). Its normalisation by noise attenuation rewards noise-only boxes, so it cannot be judged by this test. That is not a problem in the benchmark, where noise is independent.

## B. Over/underfitting check
**1. Learning curves:** they plateau. There is no sign of overfitting over training steps.
- **Model 6:** best at 17,000–19,000 steps; final is 0.015–0.025 below best; slope over the last 5 evaluations is about 0. Training loss falls from 1.03 to 0.51 and flattens.
- **m4_s0:** falls 0.072 after its peak at 10,000 steps, which is overfitting over steps. The other two m4 seeds plateau.
- **m7_s2:** still rising slightly (+0.011 per 1000 steps), so mildly underfit. **m7_s1:** did not train (known).

**2. Seen templates vs unseen sources:** there is a large gap, **source and template memorisation**.

| Run | CE train / val | accuracy train / val | AUC train / val | recall train / val |
|---|---|---|---|---|
| model 6 (3 seeds) | 0.45 / 1.17–1.24 | 0.81 / 0.61 | 0.996 / 0.986 | 0.89 / 0.68–0.70 |
| model 5 | 0.54–0.56 / 1.07–1.13 | 0.78 / 0.60 | 0.992 / 0.976 | 0.78–0.80 / 0.50–0.56 |
| model 4 | 0.76–0.80 / 0.89–0.91 | 0.65–0.67 / 0.58–0.61 | 0.975 / 0.959 | 0.43–0.48 / 0.40–0.41 |
| model 7 (s0, s2) | 0.54–0.57 / 0.96 | 0.77 / 0.62 | 0.992 / 0.976 | 0.74–0.78 / 0.47–0.58 |

- Every trained run crosses the planned flag (gap > 0.10).
- Model 4 is the smallest model and has the smallest gap, but also the weakest fit on both sets. That is closer to underfitting by capacity.

**3. Where the gap comes from: the confusion matrix for model 6 seed 0**

| True class | Predicted correctly, train | Predicted correctly, val | Main confusion on val |
|---|---|---|---|
| lensed | 0.985 | 0.951 | impostor 0.046 |
| repeat | 0.857 | **0.316** | **unrelated 0.506** |
| unrelated | 0.833 | 0.729 | repeat 0.181 |
| impostor | 0.580 | 0.468 | unrelated 0.314 |

- On seen sources, the model separates repeat from unrelated well. It has learned **which source** a burst comes from, such as its spectral envelope or beam pattern.
- On unseen sources that knowledge is gone, and half of the repeats are called unrelated.
- **The lensed class barely changes (0.985 vs 0.951).** The lensed decision rests on "same burst", not on source identity.
- **Dev folds, held-out vs seen:** the same pattern. CE gap +0.6 to +1.3; recall gap +0.14 to +0.78, largest in fold 4, the fold with the 2-burst source.

## What this means
- **The reported numbers are not contaminated.** Every primary number (`val_bright`, grouped-fold OOF, Stage 3, test) uses sources the model never trained on. The gap shows what the model memorises, not an optimistic headline.
- **Seen-source scores must never be used.** Repeat pairs from seen sources get very different scores from unseen ones. This confirms the grouped-fold design for the Phase 5 search: each source is scored by a model that never trained on it.
- **There is room to improve.** Recall on seen sources is 0.89 against 0.70 on unseen. Reducing source memorisation could raise unseen recall. Candidates, not done and needing a plan addendum because they change frozen training:
  1. **Drop the repeat-vs-unrelated distinction from the loss** (merge or down-weight "unrelated"). Telling repeat from unrelated on seen sources rewards learning source identity, and the primary task does not need it.
  2. **A random smooth bandpass per member during training.** The `wide` stress multiplier already exists. It hides the source's spectral envelope.
  3. **More templates for the lensed class from non-repeating Catalog 2 bursts.** A lensed pair needs only one burst, so this would multiply template diversity.
  4. **Stronger weight decay or early stopping.** These are unlikely to help, because the curves already plateau.
- **Underfitting:** not a concern for model 6; its curves plateau and it fits the seen data well. Model 4 is capacity-limited, as expected from its design. m7_s2 could gain from more steps.
