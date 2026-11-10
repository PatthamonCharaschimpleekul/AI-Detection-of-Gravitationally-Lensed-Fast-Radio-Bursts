# Update: independent reproduction and Stage 3 transfer check (val sources)

- **Date/time:** 2026-11-09 20:50
- **Plan:** [../plan/2026-11-09_1347_reproduction-and-stage3-transfer.md](../plan/2026-11-09_1347_reproduction-and-stage3-transfer.md)
- **Pipeline box:** `01_semi_synthetic_data/01_real_data`, `02_injection_labelling/01_injection`, `03_models_benchmark/track_B_pairs`
- **Matches plan?** 🟡 Reproduction ✅. Stage 3 headline ✅ for every method; b1 cross-correlation fails at S/N 10–25 (level shift); S/N ≥ 50 bin fails in point estimate; twin test flags model 6. Stage 4 done.

## What we did
- **Data reproduction (second machine):**
  - Re-downloaded and re-processed all 981 Catalog 2 repeater spectra with `stream_preprocess.py`, which runs `preprocess_catalog2.py` and `inject.build_cache()` unchanged and streams each file to stay within 13 GB of disk.
  - Two restarts:
    - Connection resets exhausted 6 download tries. Retries are now 20, with backoff capped at 120 s.
    - 10 DataLoader workers ran out of RAM. Now 4.
- **Frozen sets:** regenerated `val`, `val_bright` and `dev` folds 0–4 through `load_set` / `load_fold_set`, which assert the frozen hashes. The test sets were not touched.
- **Model 6:** trained seed 0, 20,000 steps, with the Stage 2 command (`outputs_local/run_m6_s0.log`).
  - Each worker draws pairs from (seed, worker id), so the training pair stream differs from the original run, which used 14 workers.
  - This run is therefore an independent replicate, not a bitwise rerun.
- **Stage 3:** ran `02_benchmark/transfer_check.py` as planned.
  - Added: the network's lensed-vs-unrelated log ratio (`|LvU`) is also saved, for the calibration identity check.
- **New check, `02_benchmark/eh0_check.py`:** E_U[r̂] on simulated unrelated pairs and on real cross-source pairs, with r̂ = exp(ℓ_lensed − ℓ_unrelated).

## Results
- **Hashes: 7/7 match** (`outputs_local/hashes.txt`).
  - Cache counts are identical to update 2026-11-05_1335: 950 eligible templates, 856 backgrounds, model scale b median 1.039.
- **Model 6 replicates (this machine, `run_stage4_seeds.sh` for seeds 1 and 2):** best `val_bright` recall **0.668 / 0.649 / 0.616** for seeds 0 / 1 / 2.
  - Seed 0 is inside the pre-registered 0.66–0.72, so the criterion passes.
  - Seeds 1 and 2 fall below that range. This machine's mean (0.644) sits about 0.05 below the original seeds (0.684–0.701).
  - Possible causes: GPU and torch build, the worker count (4 vs 14, which changes the pair stream), or chance. We report it rather than tune it away.
  - The gain over the GBM (0.285) is unaffected.
- **Stage 3** (`02_benchmark/outputs/stage3_val.txt`):
  - **Sample:** 3750 real cross-source pairs from 89 val bursts (26 sources), against 20,000 simulated unrelated pairs.
  - **Headline S/N ≥ 25 (793 real pairs), real FPR at the simulated 1% threshold:** every method passes.

    | Method | Real FPR [95% source bootstrap] | Twin Spearman real–sim / sim–sim |
    |---|---|---|
    | b1 xcorr (blk1 / 4 / 16) | 0.9% / 0.9% / 0.5% | 0.95 / 0.95 … 0.96 / 0.95 |
    | b2 physics fit (blk1 / 4 / 16) | 0.3% / 0.4% / 0.4% | 0.92–0.95 / 0.93–0.94 |
    | b3 GBM | 1.3% [0.2, 2.8] | 0.83 / 0.83 |
    | Model 6 | 1.4% [0.1, 4.0] | **0.76 / 0.87** |

  - **S/N 10–25 (2794 real pairs):**
    - Model 6: 0.5% real FPR, below the simulated 1%, so simulated thresholds are conservative there. GBM 1.2%, physics fit 0.6–1.0%.
    - **Cross-correlation (b1) fails: 6.2% / 3.8% / 2.4%** for blk1 / 4 / 16, with every CI above 1.3% and blk1/4 entirely above 2%. Its twin rank correlation is at the ceiling (0.77–0.85).
    - So this is a **level shift, not a rank problem**. The cause is composition, not the simulator: see the twin decomposition below. (A first guess, the template energy deficit, was tested and rejected for b1.)
    - The physics fit (amplitude μ fitted), the GBM and model 6 are not affected.
    - Generic-simulation thresholds for b1 are therefore unsafe at low S/N. A search must set them from real negatives, or from S/N-matched simulation.
  - **S/N ≥ 50 (85 real pairs): fails in point estimate** for b1 blk1 and blk4, the GBM (3.5%) and model 6 (2.4%), with CIs up to 12%.
    - **Investigation:** the false positives are the same pairs for every failing method. FRB 20220428C's two bursts (S/N 106 and 137) paired with bright bursts of FRB 20210219C and FRB 20220207A, plus one more pair for the GBM.
    - The physics fit (b2) rejects all of them.
    - So this comes from one source's bright, simple bursts and is not specific to the learned model. With 85 pairs, 2 hits cannot separate 1% from 2%.
  - **Twin test: model 6 is flagged.**
    - Real–twin Spearman is more than 0.1 below the ceiling in the S/N 25–50 bin (0.74 vs 0.87) and in the headline bin (0.76 vs 0.87). S/N 10–25 is borderline (0.70 vs 0.79).
    - No baseline is flagged.
    - So model 6 responds to structure the templates lack, as update 1909 warned.
    - The gap is mostly scatter, not a shift. At S/N ≥ 25 real pairs score slightly *higher* than their twins (median log-odds −11.2 vs −11.8; real > twin for 57% of pairs), yet the real FPR in the tail stays within 2%. For the GBM and b1 the shares are 43–51%.
- **Calibration identity** (`02_benchmark/outputs/eh0_val.txt`):
  - **Simulated unrelated:** mean r̂ 1.94 (bootstrap 1.42–2.61). Model 6's LR over-claims by about 2× on its own simulation, driven by the tail: the top 10 pairs carry 43–69% of the sum.
  - **Real cross-source:** mean r̂ 1.10 [0.20, 2.55] (source bootstrap). This is consistent with 1 and with the simulated value, so there is no extra over-claiming on real negatives.
  - **Betting e-process:** e = 0.009 on 325 source-pair means. It has little power for heavy-tailed r̂, so the bootstrap is the primary result.

- **Stage 4 ablations** (`02_benchmark/ablation_compare.py`, `outputs/stage4_ablations.txt`).
  - Model 6, seeds 0–2, on `val_bright`.
  - Seed-mean recall and the seed-mean paired difference from the full model, both on the same source resamples.
  - The full model's seed mean is 0.644.

  | Ablation | Recall (mean) | Difference [95%] | Per seed |
  |---|---|---|---|
  | No alignment (correlation layer off) | 0.557 | −0.087 [−0.186, −0.025] | −0.093, −0.097, −0.072 |
  | Hard-negative repeats (best of 4 by template similarity) | 0.698 | +0.053 [−0.011, +0.082] | +0.046, +0.040, +0.074 |
  | No impostors in training | 0.474 | −0.170 [−0.254, −0.052] | −0.198, −0.169, −0.145 |

  - **Alignment and the impostor class are both needed:** each costs recall in every seed.
  - **Hard negatives:** a small gain in every seed, but the interval still includes zero.
  - **We do not adopt hard negatives without an LR correction:** the POC showed they bias a learned LR low by about 1 dex. Importance-weighting them is a cheap follow-up.

## Added 2026-11-10: three seeds, twin decomposition, deficit test
- **Stage 3 with model 6 seeds 0, 1, 2** (`outputs/stage3_val.txt`; the seed-0-only run is kept as `stage3_val_s0only.txt`, and its baselines are identical).
  - Headline real FPR: **1.4%, 1.9%, 1.6%**. All pass, with intervals up to 5%.
  - Twin Spearman: 0.75–0.76 against a ceiling of 0.85–0.87 in every seed. The twin flag holds for all seeds.
- **Twin decomposition (`02_benchmark/twin_fpr.py`, `outputs/stage3_twin_fpr.txt`).**
  - At the generic-simulation threshold, the twin FPR (mean of 2 draws) measures the composition effect. Real − twin measures the transfer gap.
  - **Baselines:** the transfer gap is consistent with zero in every bin; in the headline bin it is at most 0.5 points.
  - **b1 at S/N 10–25 is pure composition:**
    - FPR real 6.2 / 3.8 / 2.4%, twin 5.6 / 4.0 / 2.5%.
    - Real pairs in that bin are brighter (median S/N 16.9 vs 13.5 for generic sim), and b1 grows with S/N inside the bin.
  - **Model 6 is the only method with a real gap:** +0.6 to +1.2 points in the headline bin across seeds. Intervals touch zero, e.g. seed 1 +1.2 [+0.0, +4.1]. At S/N 10–25 its gap is about 0.
- **Template-deficit test (`02_benchmark/deficit_twin.py`, `outputs/deficit_twin.txt`).**
  - Per burst, deficit = 1 − s²/E_on, with s the template matched-filter S/N in the data and E_on the on-pulse signal energy.
    - Median 0.18 on val templates and 0.23 on all eligible templates.
    - This measure is smaller than the 35% residual-energy figure of update 1909, so it is not the same statistic.
  - At S/N ≥ 25, the pair deficit vs model 6 real − twin score gives Spearman **+0.16 to +0.23** over seeds; for every baseline it is ≤ +0.05.
  - The pair deficit vs rank discrepancy gives +0.13 to +0.24.
  - So model 6's gap is tied to template incompleteness. b1's is not: its ρ is negative.
- **E_U[r̂], three seeds:**
  - Simulated means are 1.94, 1.73, 7.33. The seed-2 value is unstable because of the heavy tail.
  - Real means are 1.10, 1.86, 1.53, all consistent with 1 within a factor of 2.
- **Host-DM sensitivity of the forecast (`population.py --host-median 150`, `timing.py --zfile z_samples_host150.npz --tag _host150`):**
  - Median host DM 68 → 150 pc/cc gives Σ τ −13% and CHIME timing N_exp −19% (4.3e-6 vs 5.3e-6).
  - The forecast is not sensitive to this assumption.
- **Suggestion for the Stage 3 protocol:** report the twin-matched gap alongside the raw rate. The raw rate confounds transfer with composition: b1 "fails" while transferring perfectly, and model 6 "passes" while having the only real gap.

## Compared with the plan
- **Expected result:** the plan expected model 6 might fail Stage 3 because real pairs look *more* alike.
  - **At S/N ≥ 25:** that tendency is present but small. Real pairs score slightly above their twins, and the real FPR is 1.4% against the simulated 1%, inside the 2% limit.
  - **At S/N 10–25:** the real tail is lighter (0.5%).
  - **Twin gap:** real, but so far it costs ranking fidelity, not false-positive control. Thresholds for a search must still come from real negatives.
- **The S/N ≥ 50 failure is reported, as the plan requires.** The headline bin passes, and the failure has a single-source explanation shared by the baselines. The decision whether benchmark numbers may be quoted is for the team; we recommend quoting them with this caveat.

## Next
- If the team shares the original machine's seed checkpoints, run Stage 3 on them too, and check whether the ~0.05 replicate offset comes from the worker count (rerun with 14 workers when RAM allows).
- Run Stage 3 on the other two seeds' checkpoints from the original machine, if the team shares them.
- Test-split evaluation and the search need team sign-off (Stage 5).
