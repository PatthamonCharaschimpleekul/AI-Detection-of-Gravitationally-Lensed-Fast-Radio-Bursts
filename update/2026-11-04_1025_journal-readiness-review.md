# Update: journal-readiness review of the plan

> **Superseded** by [2026-11-04_1112_single-paper-lensed-repeaters.md](2026-11-04_1112_single-paper-lensed-repeaters.md): the two-paper split below was replaced by a single paper on Tracks B + C. The review findings on transit selection, blind analysis, reproducibility and reference likelihood ratios still apply.

- **Date/time:** 2026-11-04 10:25
- **Plan:** none (review requested before starting work)
- **Pipeline box:** whole project (Project_Description.md, pipeline.mmd)
- **Matches plan?** 🟡 the plan changed: the project is now split into two papers

## What we did
- Reviewed Project_Description.md as a journal referee; checked claims against the full texts of Connor & Ravi 2022, Leung et al. 2022 and the CHIME baseband release on CANFAR.
- Applied all changes to Project_Description.md, pipeline.mmd and the 06_cosmology READMEs; made the Chang et al. year consistent (2025, MNRAS Letters 537, L61).

## Results
Major issues found and fixed:
1. **Transit selection:** CHIME sees a source only minutes per day, so the second image of a galaxy-lensed one-off is almost never recorded (P_FoV ≈ 0 for t_trans < Δt < 1 day, ~10⁻² beyond; Connor & Ravi 2022). Added P_FoV to the yield; Track B now targets lensed repeaters and all-sky monitors (BURSTT).
2. **Incoherent vs coherent:** a learned search on intensity cannot beat the CHIME coherent search where coherence holds. Track A now claims complementarity where scattering decoheres the signal (larger masses, longer lags; Leung et al. 2022).
3. **Scope:** split into Paper 1 (Track A, 6 months, PRD/MNRAS) and Paper 2 (Tracks B/C, MNRAS/RASTI); H₀ moved to the Paper 2 discussion.

Minor fixes: "fundamental limit" renamed to reference likelihood ratios (simplified + neural); Feldman–Cousins limit with DM–z marginalisation; blind-analysis protocol and reproducibility steps; baseband storage plan.

Data facts checked:
- Baseband release: DOI 10.11570/23.0029, ~2.3 GB per file, ~320 GB for 140 files (estimated from the first 35 listed). D: has ~250 GB free.

## Compared with the plan
The original single 6-month plan covering three tracks was not realistic for a journal paper; Paper 1 is now focused on Track A.

## Next
- Compute CHIME P_FoV per declination (open item, Sec. 12).
- Check overlap between Kader et al.'s 172 bursts and the 140 public ones.
- Start Paper 1 month 1: baseband download-and-reduce pipeline.
