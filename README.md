# AI Detection of Gravitationally Lensed Fast Radio Bursts

Research project: using AI to detect gravitationally lensed fast radio bursts (FRBs).

- [Project_Description.md](Project_Description.md) — full project plan: motivation, research questions, pipeline, model design, evaluation, timeline
- [pipeline.mmd](pipeline.mmd) — Mermaid diagram of the agreed pipeline
- [Definitions_of_specific_terms.md](Definitions_of_specific_terms.md) — glossary with references

## Status

Update this table whenever an [update/](update/) file is written. ⬜ not started · 🟡 in progress · ✅ done

| Folder | Pipeline step | Status | Latest update |
|---|---|---|---|
| [01_semi_synthetic_data](01_semi_synthetic_data/) | Phase 1 · Semi-synthetic data | ⬜ | — |
| [02_injection_labelling](02_injection_labelling/) | Phase 2 · Injection & labelling | ⬜ | — |
| [03_models_benchmark](03_models_benchmark/) | Phase 3–4 · Models & benchmark (Tracks A, B, C) | ⬜ | — |
| [04_validation](04_validation/) | Validation | ⬜ | — |
| [05_search](05_search/) | Search real CHIME data | ⬜ | — |
| [06_cosmology](06_cosmology/) | Phase 5 · Cosmology | ⬜ | — |
| [07_deliverables](07_deliverables/) | Deliverables | ⬜ | — |

## Workflow

1. Before starting a piece of work, write a plan in [plan/](plan/) — `YYYY-MM-DD_HHMM_<topic>.md`: what we will do and what we expect.
2. Do the work inside the matching pipeline folder. Large files go in `data/` or `outputs/` there (gitignored).
3. Afterwards, write an update in [update/](update/) with the same topic: what was done, results, whether it matched the plan.
4. Update the status table above.
