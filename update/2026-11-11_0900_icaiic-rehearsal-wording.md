# Update: ICAIIC draft, grouped-fold wording and number audit against Track B outputs

- **Date/time:** 2026-11-11 09:00
- **Plan:** [plan 0740](../plan/2026-11-11_0740_icaiic-and-combined-mnras.md), steps A2, A4 and A5
- **Pipeline box:** `07_deliverables/paper_icaiic`
- **Matches plan?** ✅ for A2, A4 and A5. A3, the variant sentence, waits for `variants.txt`.

## Changes in `main.tex` (user approved edits 1–7)
1. **Abstract:** "source-grouped cross-validation" becomes "source-grouped cross-validation rehearsal on the 60 development sources".
2. **Validation, grouped folds:** states that this is the rehearsal on 60 development sources, with test sources excluded and one model-6 seed per fold. The 80-source folds follow the test sign-off.
3. **Table I caption:** the fixed split uses the validation sources; the grouped folds are out-of-fold over the 60 development sources.
4. **Main result:** now says "grouped-fold rehearsal", and adds that per-fold recall is 0.12–0.73, with the lowest fold set by one 2-burst source.
5. **Table II caption:** adds "on the second machine". Its full model is 0.644, which differs from Table I's 0.68–0.70.
6. **Limitations:** adds that the grouped-fold numbers are a rehearsal.
7. **Real-data paragraph:** "15 trained models and baselines" becomes "12 trained models and 3 baselines".

## Number audit (A4)
**Checked against our outputs:**

| Item | Source file |
|---|---|
| Stage 3 headline | `stage3_val.txt` |
| Rank correlations | `stage3_val.txt` |
| Real-burst ratios | `realburst.txt` |
| Fixed-split recalls | `stage2_val.txt` |
| OOF and its difference | `folds_dev/oof.txt` |
| Confusion figures | `fitcheck.txt` |

**Corrected:**
- **GBM AUC 0.928 → 0.925.** The 0.928 came from the superseded GBM of update 1352, which was trained on contaminated pairs.
- **Model 6 AUC 0.986 → 0.987.** The mean of 0.987, 0.988 and 0.985 is 0.987. The text range now reads 0.976–0.987.

**Not changed:** model 7's AUC of 0.976 is the mean of its two trained seeds, and the collapsed seed is marked by footnote a.

**Not audited:** the survey-geometry and forecast numbers. These come from the other contributor's outputs.

## Build (A5)
- `latexmk -pdf`: 6 pages, no errors, no overfull boxes.
- Font embedding was not checked on this machine, because `pdffonts` is not installed.
