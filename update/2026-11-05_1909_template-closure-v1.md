# Decision record: template question closed with v1; Phase 3 may start

- **Date/time:** 2026-11-05 19:09
- **Plan:** [../plan/2026-11-05_1254_pair-injection.md](../plan/2026-11-05_1254_pair-injection.md) (addendum "template question closed; Phase 3 requirements")
- **Evidence:** [update 1640](2026-11-05_1640_v2-residual-gates.md) (v2 one-shot fails G-twin) and [update 1851](2026-11-05_1851_snr-binned-domain-check.md) (per-S/N-bin domain check with noise ceiling)
- **Pipeline box:** `02_injection_labelling/01_injection`

## Decision
**Templates stay v1:** fitburst models at measured S/N, with frozen sets val `54cc6d57`, test `c444efd5`, stress `337594c0`. No new template will be built.

## Why
1. **Ranking: no template can do better.** Spearman sim–real equals the sim–sim noise ceiling in every S/N bin (0.39/0.40, 0.58/0.59, 0.91/0.91, 0.92/0.88).
2. **What remains is a constant ~8% similarity scale** (−6 to −10%, no S/N trend), and real-negative calibration absorbs it. It rivals the contrast only at S/N < 25, where the real contrast is itself ≈ 0.
3. **The pre-registered escape hatch was used once and failed** (v2 G-twin −11.4%). This was reproduced bit-for-bit at 18:57, confirming that the 18:35 run was complete and not cut by the network drop at ~14:12, which came after the v1 run had finished. Reopening it without new evidence would be a tuning loop.
4. **Corrections to the review on record:**
   - "Offset ≈ 3× contrast" was a pooled-median artefact; per bin, the offset is 6–50× smaller than the contrast at S/N ≥ 25.
   - "Spearman 0.66 breaks the rank claim" was wrong; 0.66 is a mixture of bins, and the scatter is noise.
5. **Still standing:** the `lensed` class has no real counterpart to check. The direction argument says v1 *understates* lensed-vs-repeat separation (conservative): the missing energy is fully shared within one burst's two images and only partly shared between different bursts.

## Consequences
- **Simulation is used only** for training, ranking metrics, ablations and ε. Absolute thresholds come from real negatives only: time-scrambled lists and cross-source pairs, stratified by S/N bin and mask overlap.
- **Headline bin is pre-specified:** min S/N ≥ 25. Lower bins are secondary.
- **Required Phase 3 step:** a real-negative transfer eval of the first learned model, which doubles as the Track C calibration set.
- **The training hold is lifted.**
- **The paper reports** the twin ladder, the noise ceiling and the per-bin offset as the quantified domain-gap limitation.
