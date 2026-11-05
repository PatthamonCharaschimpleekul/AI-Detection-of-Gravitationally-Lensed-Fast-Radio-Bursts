# Plan: download and inspect Catalog 2 repeater data

- **Date/time:** 2026-11-04 11:23
- **Pipeline box:** `01_semi_synthetic_data/01_real_data`

## What we will do
1. Download the Catalog 2 table (`chimefrbcat2.csv`) from CANFAR (DOI 10.11570/25.0066).
2. Select all bursts from repeating sources.
3. Download their total-intensity dynamic spectra (`<TNS>_stokesi_dynamic_spectrum.h5`) with a resumable script.
4. Download the exposure file (`chimefrbcat2_exposure.h5`).
5. Inspect formats: time/frequency resolution, window length, flagged channels, metadata; exposure structure.
6. Record results in the folder README and an update note.

## Expected result
- Table loads; ~4539 bursts, ~981 from ~83 repeaters.
- ~981 dynamic spectra downloaded, ~10 MB each (~10 GB); 0.983 ms resolution, 400–800 MHz.
- Exposure file readable; its sky/time structure understood well enough to plan the observation filter (Phase 1, step 4).

## Risks / open questions
- Some repeater bursts may lack dynamic spectra (Catalog 2 Table 2 lists missing data products).
- Catalog 2 dynamic spectra may differ in format from Catalog 1 waterfalls.
- The exposure file may give total exposure per sky position rather than time-resolved windows, which would limit burst-by-burst filtering.
