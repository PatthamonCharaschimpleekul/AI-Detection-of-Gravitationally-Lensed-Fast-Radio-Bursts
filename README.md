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
| [01_semi_synthetic_data](01_semi_synthetic_data/) | Phase 1 · Semi-synthetic lensed repeaters | 🟡 Catalog 2 repeaters preprocessed: 981 × 256/1024 × 160 HDF5 + 20-chunk noise bank; lens population, propagation, impostors next | [2026-11-05](update/2026-11-05_1051_catalog2-preprocessing.md) |
| [02_injection_labelling](02_injection_labelling/) | Phase 2 · Injection & labelling | ✅ Track B sets v1.1: v1 (lensed/repeat/unrelated, template question closed) + impostor class (shared envelope / scintillation); probes pass, one small single-member S/N shift (AUC 0.50) documented. Thresholds from real negatives only | [2026-11-05](update/2026-11-05_1928_impostor-pairs.md) |
| [03_models_benchmark](03_models_benchmark/) | Phase 3–4 · Models & benchmark (Tracks B, C) | 🟡 Track B Stage 1 done on val: comparator for the primary test is the feature GBM; learned models next | [2026-11-06](update/2026-11-06_1352_phase3-stage1-baselines.md) |
| [04_validation](04_validation/) | Validation | ⬜ | — |
| [05_search](05_search/) | Search: Catalog 2 repeaters | ⬜ | — |
| [06_cosmology](06_cosmology/) | Forecasts (H₀ discussion only) | ⬜ | — |
| [07_deliverables](07_deliverables/) | Deliverables | ⬜ | — |

## Workflow

1. Before starting a piece of work, write a plan in [plan/](plan/) — `YYYY-MM-DD_HHMM_<topic>.md`: what we will do and what we expect.
2. Do the work inside the matching pipeline folder. Large files go in `data/` or `outputs/` there (gitignored).
3. Afterwards, write an update in [update/](update/) with the same topic: what was done, results, whether it matched the plan.
4. Update the status table above.
