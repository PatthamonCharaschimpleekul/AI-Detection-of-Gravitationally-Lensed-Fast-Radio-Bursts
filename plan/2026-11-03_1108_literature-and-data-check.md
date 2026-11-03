# Plan: literature review and CHIME data check

- **Date/time:** 2026-11-03 11:08
- **Pipeline box:** `literature_review/` (new) and `01_semi_synthetic_data/01_real_data`

## What we will do
1. Search the web for papers that answer four plan-changing questions:
   - Q1: Has an ML classifier for lensed vs intrinsic-repeat FRBs been published?
   - Q2: What are the current CHIME limits on compact dark matter (f_CO / f_PBH)?
   - Q3: Status of the Chang et al. 2025 lensed candidate and of FRB 20220529A.
   - Q4: How does CHIME search for lensing echoes (autocorrelation, baseband)? → Track A baseline.
2. Download the key papers (arXiv PDFs) into `literature_review/papers/` and list them in `literature_review/README.md`.
3. Write `literature_review/summary.md`: 2–3 lines per question with sources, and whether the plan must change.
4. Find which CHIME/FRB data products are public; download the Catalog 1 table and 5–10 waterfalls into `01_semi_synthetic_data/01_real_data/data/`.
5. Inspect them: time and frequency resolution, number of channels, file format and size, what metadata is included.

## Expected result
- 10–20 papers downloaded and indexed.
- Clear yes/no answers to Q1–Q4; a list of any changes needed to Project_Description.md.
- Catalog 1 table loaded (expect 536 bursts, 62 from 18 repeaters).
- Waterfall resolution known. Expectation: ~1 ms time resolution, 16k channels over 400–800 MHz (possibly downsampled in the public release). If coarser than ~1 ms, Track A is at risk.

## Risks / open questions
- Some papers may be paywalled; use arXiv versions.
- Public waterfalls may be large or downsampled.
- PDFs are kept out of git (licences vary); only the index and summary are committed.
