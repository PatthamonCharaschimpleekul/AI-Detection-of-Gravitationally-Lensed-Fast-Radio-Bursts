# AI Detection of Gravitationally Lensed Fast Radio Bursts

Research project: using AI to detect gravitationally lensed fast radio bursts (FRBs).

- [Project_Description.md](Project_Description.md) — full project plan: motivation, research questions, pipeline, model design, evaluation, timeline
- [pipeline.mmd](pipeline.mmd) — Mermaid diagram of the agreed pipeline
- [Definitions_of_specific_terms.md](Definitions_of_specific_terms.md) — glossary with references

## Status

Update this table whenever an [update/](update/) file is written. ⬜ not started · 🟡 in progress · ✅ done

| Folder | Pipeline step | Status | Latest update |
|---|---|---|---|
| Plan | Project_Description.md, pipeline.mmd | ✅ single paper: Siamese for lensed repeaters (Tracks B + C) | [2026-11-04](update/2026-11-04_1112_single-paper-lensed-repeaters.md) |
| [literature_review](literature_review/) | Background and prior work | ✅ first pass | [2026-11-03](update/2026-11-03_1125_literature-and-data-check.md) |
| [01_semi_synthetic_data](01_semi_synthetic_data/) | Phase 1 · Semi-synthetic lensed repeaters | 🟡 Catalog 2 repeaters preprocessed: 981 × 256/1024 × 160 HDF5 + 20-chunk noise bank; repeater z table (`02_population`) and SIS lens + CHIME transit simulator (`03_lens_simulator`) built; per-image propagation (ΔDM, scattering, scintillation) and impostors implemented in `02_injection_labelling/01_injection/inject.py` (the `04_propagation` and `05_impostors` folders hold READMEs only). Waiting for the team's sign-off of the propagation model, the gate before the test split opens | [2026-11-05](update/2026-11-05_1051_catalog2-preprocessing.md), [2026-11-09 pop/lens/C](update/2026-11-09_1440_population-lens-trackC-forecast.md) |
| [02_injection_labelling](02_injection_labelling/) | Phase 2 · Injection & labelling | ✅ Track B sets v1.1: v1 (lensed/repeat/unrelated, template question closed) + impostor class (shared envelope / scintillation); probes pass, one small single-member S/N shift (AUC 0.50) documented. Thresholds from real negatives only | [2026-11-05](update/2026-11-05_1928_impostor-pairs.md) |
| [03_models_benchmark](03_models_benchmark/) | Phase 3–4 · Models & benchmark (Tracks B, C) | 🟡 Track B Stage 2 rerun (warmup) done on val: model 6 ahead of the feature GBM, +0.39 recall; model 7 reported as seed-unstable (1 of 3 seeds collapsed on a plateau, not a bug); audit found no bug; grouped folds agreed; rehearsal on dev sources: model 6 OOF +0.22 [+0.04, +0.38] over the GBM (development), one 2-burst source sets the fold-4 threshold; Stage 3 transfer (val): all methods pass after filling zero-padded real windows (model 6 had failed on them); real-burst lensed test passes (model 6 real/template recall 0.96); strong source memorisation found (seen vs unseen recall 0.89 vs 0.70), headline numbers use unseen sources only; training variants to reduce it (merge unrelated, random bandpass, both; 3 seeds each): none adopted, gain −0.006 to −0.036 with CIs including 0, all pass Stage 3 and the real-burst test (negative ablation); scattering check before the propagation sign-off: recall halves at a differential τ₆₀₀ of 1 ms and is 0.13× at 3 ms; training up to 10 ms (S) lifts that only to 0.24× and costs −0.04 on val_bright, not adopted (mostly a physical limit); test unopened. Second-machine reproduction: 7/7 frozen-set hashes match, model 6 replicates 0.668/0.649/0.616 (~0.05 below the originals); Stage 1 baselines, Stage 3 (12/12 pass with fill) and the real-burst test (ratio 0.97) reproduce. Stage 4 ablations (3 seeds): no-align −0.09, no impostors −0.17, hard negatives +0.05 (CI includes 0). Track C timing test built (`track_C_timing`) | [2026-11-11 scattering](update/2026-11-11_1630_wide-scattering-training.md), [2026-11-11 variants](update/2026-11-11_1110_source-memorisation-variants.md), [2026-11-10](update/2026-11-10_1130_real-burst-lensed-and-fit-check.md), [fold plan](plan/2026-11-08_0845_grouped-fold-addendum.md), [2026-11-09 repro/Stage 3/4](update/2026-11-09_2050_reproduction-and-stage3-transfer.md) |
| [04_validation](04_validation/) | Validation | 🟡 LR-limit POC (`05_lr_limit/poc_tail_nre`); Track C held-out false-alarm check: 1 in 166,000 scrambles | [2026-11-07](update/2026-11-07_0103_tail-nre-poc.md), [2026-11-09 pop/lens/C](update/2026-11-09_1440_population-lens-trackC-forecast.md) |
| [05_search](05_search/) | Search: Catalog 2 repeaters | ⬜ | — |
| [06_cosmology](06_cosmology/) | Forecasts (H₀ discussion only) | 🟡 lensed-repeater N_exp for Catalog 2: 5e-6–1e-4 (CHIME), ~50× for an all-sky monitor; transit alignment limits repeaters too (contradicts Sec. 4.1) | [2026-11-09 pop/lens/C](update/2026-11-09_1440_population-lens-trackC-forecast.md) |
| [07_deliverables](07_deliverables/) | Deliverables | 🟡 ICAIIC 2027 paper (`paper_icaiic/`, deadline 15 Nov): 6 pages, number audit against outputs done, grouped folds stated as a development rehearsal, figures fixed, no Type 3 fonts; waiting for the author list and submission. Combined MNRAS paper (`paper/`) after Stage 5 and the search ([plan 0740](plan/2026-11-11_0740_icaiic-and-combined-mnras.md)) | [2026-11-11 ICAIIC fixes](update/2026-11-11_0900_icaiic-rehearsal-wording.md), [2026-11-10 merge/repro/ICAIIC](update/2026-11-10_2045_merge-repro-icaiic-draft.md) |

## Workflow

1. Before starting a piece of work, write a plan in [plan/](plan/) — `YYYY-MM-DD_HHMM_<topic>.md`: what we will do and what we expect.
2. Do the work inside the matching pipeline folder. Large files go in `data/` or `outputs/` there (gitignored).
3. Afterwards, write an update in [update/](update/) with the same topic: what was done, results, whether it matched the plan.
4. Update the status table above.
