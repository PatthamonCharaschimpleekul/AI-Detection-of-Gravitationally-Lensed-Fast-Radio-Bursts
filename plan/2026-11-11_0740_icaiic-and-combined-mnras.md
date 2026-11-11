# Plan: ICAIIC 2027 submission now, one combined MNRAS paper later

- **Date/time:** 2026-11-11 07:40
- **Pipeline box:** `07_deliverables/paper_icaiic`, `07_deliverables/paper` (from branch `poc-lr-limit`); later `05_search`, `06_cosmology`
- **Decision (user, 2026-11-11):** submit the short AI paper to ICAIIC 2027 (deadline 15 Nov), then write one combined MNRAS paper with Track B (ours) and the population, lens, Track C and forecast work from `poc-lr-limit`.
- **Status:** step A1 done 2026-11-11 (user: "merge เลย"): fast-forward to ccbd35a; training pair stream bit-identical to 7380a66 with flags off and with merge + bandpass (2 batches). Rest waits for approval.

## Scope split
| Part | Owner so far | Goes into |
|---|---|---|
| Data, injection, impostors, frozen sets, models 4–7, baselines, grouped folds, Stage 3, real-burst test, fit check, variants M/P | us (main) | ICAIIC + MNRAS |
| Lens population, SIS + transit simulator, transit alignment, forecasts | poc-lr-limit | ICAIIC (short) + MNRAS |
| Track C timing test, held-out false alarm | poc-lr-limit | MNRAS only |
| Second-machine reproduction, Stage 4 ablations | poc-lr-limit | ICAIIC + MNRAS |
| Tail-NRE POC, E_H0 identity | poc-lr-limit | MNRAS appendix |

## A. ICAIIC, by 14 Nov
1. **Merge `poc-lr-limit` into main.** It is rebased on 7380a66, so this is a fast-forward. Check that `train.py` with every flag off still gives the frozen hashes, then push.
2. **Wording fixes in `paper_icaiic/main.tex`:**
   - The grouped-fold OOF (0.47, +0.22 over GBM) is the **rehearsal** on the 60 development sources (test sources excluded). Say so in the abstract, Sec. Validation and Table I. The 80-source folds come after `benchmark-v1`.
   - Name the 2-burst source that drives fold 4 only if space allows.
3. **Variant result (run ends about 11:30 today):**
   - ADOPT none → one sentence: training-time bandpass and label merging did not raise recall (negative ablation). Table I unchanged.
   - A variant adopted → rerun the dev-fold rehearsal with it (about 5 GPU-h), then update Table I, the ablations and the abstract.
4. **Number audit** against our outputs (`stage3_val.txt`, `realburst.txt`, `fitcheck.txt`, `folds_oof`) and the second machine's.
5. **Build:** `latexmk -pdf`, 6 pages max, fonts embedded, no overfull boxes.
6. **Submission:** you submit on EDAS and decide the author list. I do not submit.

## B. Combined MNRAS paper, after ICAIIC (decision 15 Dec)
**Outline:**
1. Intro.
2. Data: Catalog 2, 981 spectra.
3. Lens population and observation model, including transit alignment. This sets what the search can expect.
4. Semi-synthetic pairs and impostors.
5. Methods: Track B models and baselines; Track C timing; validation without positives (Stage 3 twins, real-burst proxy, E_H0).
6. Benchmark results: 80-source grouped folds, ablations, memorisation, Stage 3, reproduction, timing false alarm.
7. **Search of the Catalog 2 repeaters (Stage 5).** A null result is expected, and the forecast says why.
8. Forecasts: CHIME against an all-sky monitor, magnification bias.
9. Discussion.
10. Appendix: tail-NRE POC.

**Work still needed:**
- Sign-off of `04_propagation` and `benchmark-v1`.
- 80-source folds, with `baselines.py` scheme `all` gated like `train.py`.
- Unblinding and the search (`05_search`) for Track B and Track C.
- Correct Sec. 4.1 of Project_Description (transit alignment).
- In `paper/numbers.tex`, replace the retracted Stage 3 numbers (unfilled windows: 1.4%, twin 0.76 against 0.87) and the Stage 3 figure.

**Overlap with ICAIIC:**
- The MNRAS paper cites the ICAIIC paper.
- It adds the search, Track C, the full forecast and the appendix.
- Before submitting, check MNRAS's policy on prior conference papers and the IEEE copyright on reused figures.

## Expected result
- ICAIIC PDF of 6 pages, every number traceable, rehearsal stated as rehearsal, ready on main by 14 Nov.
- An MNRAS outline in `07_deliverables/paper/` matching section B, written after Stage 5.

## Risks / open questions
- Deadline: a variant adoption costs about 5 GPU-h plus rewriting, which still fits before 15 Nov.
- The second machine's model 6 is about 0.05 below ours. The paper reports both, with no tuning.
- The ICAIIC paper reports development numbers only. A reviewer may ask for the test result, which stays sealed until sign-off.
- Authors and consent are yours to settle with the other contributor.
