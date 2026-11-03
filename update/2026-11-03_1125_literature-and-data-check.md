# Update: literature review and CHIME data check

- **Date/time:** 2026-11-03 11:25
- **Plan:** [../plan/2026-11-03_1108_literature-and-data-check.md](../plan/2026-11-03_1108_literature-and-data-check.md)
- **Pipeline box:** `literature_review/` and `01_semi_synthetic_data/01_real_data`
- **Matches plan?** 🟡 partly. All steps done, but one result changes the plan (Track A on public data).

## What we did
- Web searches on the four questions; downloaded **19 arXiv papers** (83 MB) into `literature_review/papers/` (gitignored), indexed in [literature_review/README.md](../literature_review/README.md).
- Wrote [literature_review/summary.md](../literature_review/summary.md) with answers and proposed plan changes.
- Downloaded the Catalog 1 CSV and **7 waterfalls** (~400 MB) into `01_semi_synthetic_data/01_real_data/data/`; wrote [inspect_waterfalls.py](../01_semi_synthetic_data/01_real_data/inspect_waterfalls.py) and data notes in that folder's [README](../01_semi_synthetic_data/01_real_data/README.md).
- Corrected a misattributed citation ("Kalra et al. 2022" → Krochek & Kovetz 2022) in the glossary and Project_Description.md.

## Results
| Question | Answer |
|---|---|
| Q1 ML lensed-vs-repeat classifier published? | **No.** FRB ML covers repeater vs non-repeater only. Closest precedent: a 2026 Siamese ResNet for lensed gravitational-wave pairs (Zhang et al.), same fusion idea as our Track B |
| Q2 Current CHIME compact-DM limits | Leung et al. 2022: f ≲ 0.8 at ~10⁻³ M☉ (baseband, coherent). Krochek & Kovetz 2022: **no meaningful bound possible from public ~1 ms Catalog 1 data** |
| Q3 Candidates | FRB 20190308C (Chang et al.) unconfirmed 3.4σ candidate. FRB 20220529A: expanding supernova remnant favoured; no lensing paper found |
| Q4 CHIME echo search method | Coherent baseband autocorrelation at 1.25 ns; intensity autocorrelation with simulated thresholds. Scintillation caused a false candidate |

Data:
- Catalog 1 table: 600 rows (sub-bursts) for 536 bursts, 18 repeaters, as expected.
- Waterfalls: **dt = 0.983 ms**, 16384 channels × 24.4 kHz over 400–800 MHz, windows 18–130 ms, **29–56% channels RFI-flagged (NaN)**. `calibrated_wfall` time resolution unconfirmed.
- **Baseband Catalog 1: 140 bursts at 2.56 µs are public**, the realistic data for µs-scale Track A.

## Compared with the plan
- Expected 10–20 papers → 19. Expected ~1 ms resolution → confirmed.
- Expected "Track A at risk if ~1 ms" → **confirmed by prior work**: Krochek & Kovetz already tried and could not set a bound from these data. The Project_Description priority "Track A on real CHIME data → f_CO limit" needs changing.
- Track B novelty confirmed, now with a direct Siamese precedent from gravitational waves.

## Next
- Decide the Track A change (summary.md, Q2 options; recommended: baseband Catalog 1 for µs search + keep method development).
- Apply the other proposed doc changes (scintillation impostor, Wucknitz H₀ note, citations).
- Check download location and size of the baseband release and Catalog 2 waterfalls.
- Read in full: Krochek & Kovetz 2022, Kader et al. 2022, Chang et al. 2024, Zhang et al. 2026.
