# Plan note: Stage 2 rerun with learning-rate warmup

Addendum to [2026-11-06_1223_phase3-trackB-benchmark.md](2026-11-06_1223_phase3-trackB-benchmark.md). Agreed by the user after update 2026-11-06_2015.

- **Why:** 4 of 12 runs never trained (dead first ReLU of the head). The plan had no rule for this.
- **Change:** linear warmup over the first 1000 of 20,000 steps, then cosine as before. Nothing else changes: models, seeds, budget, data, selection.
- **Test first:** the four dead runs (`m7` seeds 0, 1, 2 and `m4_s1`), 4000 steps each. Pass = loss below ln 4 and AUC well above 0.5 in all four.
- **If it passes:** rerun all 12 under the same setting. The first runs move to `01_training/outputs/nowarmup/` and stay available.
- **If it fails:** stop and report; no other fix is agreed.
- **Disclosure:** this change was made after seeing val results. Both sets of val numbers are reported. Test sets stay closed.

## Addendum: LayerNorm for model 7 (agreed by the user 2026-11-07)
Warmup failed for model 7. Add LayerNorm before its head only, keep warmup. Test 3 seeds × 4000 steps, same pass rule. If it passes, rerun all 12. If it fails, drop model 7 and rerun models 4, 5, 6, reporting that model 7 did not train under this setup.
