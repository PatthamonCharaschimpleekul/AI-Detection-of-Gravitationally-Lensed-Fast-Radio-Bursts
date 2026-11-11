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

## Addendum 2026-11-11 10:40: fonts, figures and the last page (user: "Fix all 6")
**Fonts**
- Every font in the PDF is embedded.
- The two matplotlib figures used Type 3 fonts (DejaVu Sans), which IEEE PDF checks often reject.
- `make_snr_curve.py` and `paper/make_figures.py` now write Type 42 fonts in Times New Roman, the paper's face.

**Fig. 4 (S/N curve)**
- Redrawn from the committed `snr_curve.txt` with the new `--from-txt` mode. The values are the same, and no GPU or checkpoints are needed.

**Fig. 5 (transit): not regenerated on this machine**
- **Why not:** it needs `track_C_timing/outputs/track_c_sources.csv`, which exists only on the second machine.
- **Rerun here:** `population.py` and `timing.py` with defaults, and again with `--scrambles 2000`. Neither reproduces the paper's run.

  | Run | Median p_align | CHIME N_exp, timing | All-sky N_exp, timing | Σ τ |
  |---|---|---|---|---|
  | Defaults | 1.87% | 3.7e-6 | 2.5e-4 | 2.81e-3 |
  | `--scrambles 2000` | — | 6.4e-6 | 3.0e-4 | 2.89e-3 |
  | Paper | 1.8% | 5.3e-6 | 2.6e-4 | 2.9e-3 |

- **Reading:** the forecast carries Monte Carlo scatter of tens of percent between runs. Quoting it to two significant figures overstates its precision.
- **To do (second machine):** run `python make_figures.py` from its own outputs. The script fix is in.
- **Local files:** the rerun outputs here are gitignored and are not used by the paper.

**Diagrams (`diagrams/make_diagrams.py`, `common.css`, rendered with Edge headless)**
- **Fig. 1a timeline:** the copy of the first burst fell on the fifth burst and was hidden, so the Δt arrow pointed at a blue tick. Burst times are now 38, 60, 82, 115, 145, so all five copies are visible and the arrow ends on an orange copy.
- **Fig. 1a copy 2:** the fainter amplitude was cancelled by a normalisation, so copy 2 looked identical to copy 1. It is now fainter (0.7) and has a ν⁻⁴ scattering tail. The 800/MHz/400 labels moved left of the tile.
- **Fig. 3:** the "MLP" label moved above the nodes, so the profile arrow no longer hits it.
- **Small text:** `.tx` went from 8 to 9 units (5.8 pt → 6.5 pt) and `.ts` from 9 to 9.5. Labels that then overflowed were shortened:
  - "Catalog 2, 400–800 MHz"
  - "shared imprint"
  - "shared encoder, 2-sample resolution"
  - "soft alignment over ±24 samples"
  - "4-class head → score s(A, B)"
  - "vs per-pair twins"
  - "data, sets, training"
  - "ρ(ℓ), lags ±24 samples"

**Last page**
- `\IEEEtriggeratref{15}` balances the two reference columns.

**Build**
- 6 pages, no overfull boxes.
- The only Type 3 fonts left are in Fig. 5.
