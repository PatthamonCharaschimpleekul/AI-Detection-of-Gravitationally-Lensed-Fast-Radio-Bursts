# Update: downscale to a single paper on lensed repeaters (Tracks B + C)

- **Date/time:** 2026-11-04 11:12
- **Plan:** none (scope decision)
- **Pipeline box:** whole project (Project_Description.md, pipeline.mmd, folder READMEs)
- **Matches plan?** 🟡 the plan changed: one paper instead of two

## What we did
- Chose Tracks B + C over Track A for a single paper. Reasons: it uses the Siamese model (the project's core idea); data are light (~10 GB, already-familiar format); the field has no FRB ML lensed-pair classifier; lensed repeaters avoid most of the transit problem; Catalog 2 gives a real search sample. Track A would compete with the CHIME collaboration's coherent search on fewer bursts and needs ~320 GB of baseband processing.
- Rewrote Project_Description.md and pipeline.mmd for the single paper; working title: *A Siamese network for identifying gravitationally lensed repeating FRBs: benchmark, search of CHIME/FRB Catalog 2 repeaters, and forecasts for all-sky monitors* (target MNRAS).
- Removed `03_models_benchmark/track_A_compact` and `06_cosmology/02_fco_limit`; renamed `06_cosmology/01_yield` → `01_forecast` and `03_h0_forecast` → `02_h0_discussion`; rewrote affected folder READMEs.
- The two-paper revision of earlier today was never committed; it is replaced by this one. Its review fixes that still apply are kept (P_FoV, blind analysis, reproducibility, reference likelihood ratios, Bayes prior).

## Results
- Catalog 2 data products are public: [DOI 10.11570/25.0066](https://doi.org/10.11570/25.0066), folders `table`, `dynamic_spectra` (`<TNS>_stokesi_dynamic_spectrum.h5`, ~10 MB each, 0.983 ms), `exposure` (`chimefrbcat2_exposure.h5`, 206 MB), `localizations`.
- 981 repeater bursts × ~10 MB ≈ 10 GB, well within free disk space.

## Compared with the plan
Out of scope now: compact-object lensing, f_CO limits, one-off lensed pairs, H₀ beyond a discussion paragraph.

## Next
- Plan and run month 1: download Catalog 2 repeater dynamic spectra, table and exposure; inspect format against Catalog 1.
