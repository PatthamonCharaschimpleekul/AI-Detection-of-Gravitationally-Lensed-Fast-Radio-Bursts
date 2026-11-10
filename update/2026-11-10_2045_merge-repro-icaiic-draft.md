# Update: merge onto main, second-machine reproduction of Stage 3 and the real-burst test, ICAIIC paper draft

- **Date/time:** 2026-11-10 20:45
- **Plan:** follows [update 2026-11-09_2050](2026-11-09_2050_reproduction-and-stage3-transfer.md) (see its correction section), team updates [2026-11-09_1520](2026-11-09_1520_stage3-transfer-val.md) and [2026-11-10_1130](2026-11-10_1130_real-burst-lensed-and-fit-check.md)
- **Pipeline box:** `03_models_benchmark/track_B_pairs/02_benchmark`, `07_deliverables/paper_icaiic`
- **Matches plan?** ✅ The reproductions agree with the team's results. One earlier claim of ours is withdrawn (below).

## What we did
- **Rebased branch `poc-lr-limit` onto `origin/main` (7380a66).**
  - **`train.py` conflict:** resolved to keep both sets of flags: the team's `--merge-unrelated` / `--bandpass` and our `--no-align` / `--hardneg` / `--no-impostors`.
  - **Check:** with every option off, and with `merge + bandpass` on, the merged `Pairs` stream is bit-identical to `origin/main` (first two batches compared).
  - **`setup()`:** keeps the team's positional order (`merge`, `bandpass` after `workers`), so `train_fold` is unchanged.
- **Second-machine reproduction of the team's checks** on this machine's model 6 seeds, through `02_benchmark/repro_upstream_m6.py`.
  - The team's code runs unchanged. Only two things differ: the checkpoint list is narrowed to `m6_s0..2`, because models 4, 5 and 7 were not retrained here, and process pools are capped at 8 for RAM.
  - **Stage 1 baselines (`baselines.py`):**
    - b1 and b2 recalls are identical to update 2026-11-06_1352, e.g. b1_blk16 0.171 [0.115, 0.245] and b2_blk16 0.164 [0.119, 0.235].
    - The GBM gives 0.280 [0.173, 0.413].
  - **Stage 3 (`stage3_transfer.py`, with `fill_window`):**
    - Same sample: 90 files, 29 sources, 3851 pairs (876 in the headline bin). 26 of 27 short windows were filled.
    - **12 of 12 verdicts pass.**
    - Headline real FPR: model 6 seeds 0/1/2 give 0.015 / 0.013 / 0.010; b1_blk16 0.007, b2_blk16 0.006, GBM 0.010.
    - Model 6's real~twin Spearman is 0.91–0.92, against ceilings of 0.87–0.89.
  - **Real-burst lensed test (`realburst.py`): PASS.**
    - At S/N 25, model 6 (3 seeds) gives real 0.604, template 0.624, noise-only 0.000. The ratio is **0.97 [0.91, 1.08]**, against 0.96 on the team's machine.
    - At S/N 40 the ratio is 1.04. On train bursts it is 0.98–1.01.
- **Correction:** our earlier claim that model 6 has a real sim-to-real gap tied to template deficit is withdrawn. It came from scoring unfilled windows; details are in update 2026-11-09_2050. The MNRAS draft text has been corrected. Its Stage 3 figure still shows the generic-threshold check and should be replaced if that draft is used.
- **ICAIIC 2027 paper draft:** `07_deliverables/paper_icaiic/` (IEEEtran conference, A4).
  - **Venue:** deadline 15 Nov 2026, maximum 6 pages. The draft is currently 5 pages.
  - **Framing for an AI audience:** pairwise verification without real positives; the Siamese correlation network; a validation protocol with real negatives, per-pair twins, a real-burst proxy and reproduction; and the survey-geometry limit.
  - **New figures:**
    - example pairs of the four classes from `val_bright` (`make_examples.py`);
    - recall vs pair S/N on `val` (`make_snr_curve.py`). Model 6 gets 0.41 at S/N 10–15 against GBM 0.12, and 0.76 against 0.53 at 25–50;
    - an architecture diagram (TikZ).
  - **Numbers:** generated from outputs by `../paper/make_numbers.py` and `make_numbers_icaiic.py`. Team results are quoted from their updates; second-machine reproductions are read from outputs.
  - **Added references, metadata checked:** Bromley 1993, Koch 2015, FlowNet 2015, Tobin 2017, Chen 2022. CHIME/FRB capitalisation in the bib is fixed.

## Still needed before submission (team decisions)
- **Authors and consent:** the paper uses the team's benchmark, Stage 3 and real-burst results, so the team must agree to the submission and its author list. Names are withheld in the draft.
- **Test split (Stage 5):** needs the team's sign-off. The paper is written to stand on development results, and a red marker holds the place for the test result.
- **Dual submission:** ICAIIC forbids it, so the MNRAS version must wait until the ICAIIC decision (15 Dec) and then be substantially extended.
- **Model 6 variants M and P (team plan 1300):** if adopted before the deadline, Table I and the ablations should use the final recipe.
