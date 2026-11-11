# Update: source-memorisation variants M, P, M+P of model 6: none adopted (negative ablation)

- **Date/time:** 2026-11-11 11:10
- **Plan:** [plan 1300](../plan/2026-11-10_1300_reduce-source-memorisation.md). The decision rule was fixed before the runs.
- **Pipeline box:** `03_models_benchmark/track_B_pairs`
- **Code:** `01_training/run_variants.sh` and `02_benchmark/variants_eval.py`. Outputs are in `02_benchmark/outputs/variants.txt` (gitignored).
- **Matches plan?** ✅ All 9 runs finished (exit 0) and the evaluation ran unchanged. Decision: **ADOPT none**. The current model 6 stays.

## Runs
- **Variants:**
  - **M:** the unrelated label is merged into repeat.
  - **P:** a random smooth bandpass is applied per member.
  - **M+P:** both.
- **Each variant:** seeds 0–2, Stage 2 settings, about 57 min per run.
- **Gap in the schedule:** P seed 2 did not start between 23:20 and 07:12. The free-GPU wait or machine sleep is the likely cause; it is not investigated. No run failed.
- **Merge during the runs:** M+P used `train.py` after the `poc-lr-limit` merge. Its pair stream is bit-identical (checked in plan 0740, A1).

## Results (val_bright, unseen sources, 95% source bootstrap)
| Variant | Recall s0 / s1 / s2 | Mean | Paired vs current | Seen − unseen gap | Stage 3 headline FPR | Real-burst ratio |
|---|---|---|---|---|---|---|
| current | 0.701 / 0.698 / 0.684 | 0.694 | — | +0.197 | 0.011 / 0.014 / 0.008 | 0.96 |
| M | 0.681 / 0.702 / 0.657 | 0.680 | +0.003 [−0.070, +0.096] | +0.200 | 0.011 / 0.010 / 0.011 | 0.94 |
| P | 0.640 / 0.689 / 0.645 | 0.658 | −0.020 [−0.122, +0.096] | +0.196 | 0.011 / 0.008 / 0.011 | 0.96 |
| M+P | 0.675 / 0.708 / 0.680 | 0.688 | −0.001 [−0.086, +0.096] | +0.175 | 0.009 / 0.015 / 0.011 | 0.97 |

**Decision rule** (all four criteria needed):

| Variant | (a) gain ≥ +0.03 | (b) gap below current | (c) Stage 3 passes | (d) ratio ≥ 0.8 | Outcome |
|---|---|---|---|---|---|
| M | −0.014, fails | fails | passes | passes | not eligible |
| P | −0.036, fails | passes | passes | passes | not eligible |
| M+P | −0.006, fails | passes | passes | passes | not eligible |

No variant meets (a), so none is adopted.

## Reading
- **No recall gain.** Removing the repeat-vs-unrelated target, hiding the spectral envelope, or both leaves lensed recall on unseen sources unchanged or slightly lower. Every paired interval includes zero.
- This supports update 1130: the source memorisation does not cost the primary task. The lensed decision rests on "same burst", not on source identity.
- **The memorisation gap barely moves:**
  - M+P narrows it from 0.197 to 0.175. Two of three seeds are lower, and the change is within seed noise.
  - The seen-source advantage in *lensed* recall is not driven by the repeat/unrelated distinction.
- **P changes what is memorised, not lensed recall:**
  - Val repeat→unrelated confusion falls from 0.47–0.51 to 0.31–0.38.
  - Val cross-entropy falls from 1.17–1.24 to 0.89–1.03.
  - Lensed recall drops by 0.036.
  - The real-burst test shows the same drop in absolute recall: real 0.533 against 0.663. The ratio stays 0.96.
- **M's cross-entropy of about 4.3 is expected.** Logit 2 is never a target, so true-unrelated pairs get a large loss. M's repeat→unrelated of 0.000 follows from the same design.
- **All variants pass Stage 3 and the real-burst test.** The pipeline is robust to these recipe changes.
- **Bandpass-trained GBM:** 0.264, below b3's 0.285. The comparator stays `b3_gbm`.

## Consequences
- **No change to model 6:**
  - Plan 0845 F4 is unchanged.
  - The dev-fold rehearsal is not rerun.
  - ICAIIC Table I stays.
- **For the paper:** one sentence on this as a negative ablation (training-recipe changes aimed at source memorisation). It applies to the original machine's seeds.
- **Open:** the remaining route to more template diversity is lensed templates from non-repeating Catalog 2 bursts. It needs its own plan, and is not urgent given this result.
