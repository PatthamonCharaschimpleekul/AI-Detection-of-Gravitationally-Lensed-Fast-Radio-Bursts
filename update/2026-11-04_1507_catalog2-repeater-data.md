# Update: download and inspect Catalog 2 repeater data

- **Date/time:** 2026-11-04 15:07
- **Plan:** [../plan/2026-11-04_1123_catalog2-repeater-data.md](../plan/2026-11-04_1123_catalog2-repeater-data.md)
- **Pipeline box:** `01_semi_synthetic_data/01_real_data`
- **Matches plan?** 🟡 mostly. All data are in; the format is less uniform than expected; the exposure file is integrated only, as the plan's risk list feared.

## What we did
- Downloaded the Catalog 2 table, the exposure file, and the dynamic spectra of all 981 repeater bursts from CANFAR (DOI 10.11570/25.0066). The script is [download_catalog2.py](../01_semi_synthetic_data/01_real_data/download_catalog2.py).
- Fixed the downloader twice:
  1. It now retries dropped connections with backoff, and uses 4 workers instead of 8.
  2. It now treats a file as complete only if h5py can open it. 48 files had been cut short but still had a valid HDF5 header; they were fetched again.
- Inspected every file with [inspect_catalog2.py](../01_semi_synthetic_data/01_real_data/inspect_catalog2.py), which now takes a folder. Read the exposure file structure and computed repeater statistics from the table.
- Wrote the format notes in [01_real_data/README.md](../01_semi_synthetic_data/01_real_data/README.md).

## Results
- **Table:** 4539 bursts. 981 are repeater bursts from 83 sources.
  - Bursts per source: median 3, maximum 373 (FRB 20220912A).
  - 78,701 within-source pairs (9,323 without FRB 20220912A).
  - 88 bursts have `excluded_flag=1`.
- **Dynamic spectra:** 981 of 981 downloaded, none missing, 13 GB.
  - 16384 channels over 400.2–800.2 MHz.
  - dt = 0.983 ms for 975 files; 1.966 or 3.932 ms for 6 files.
  - The window is 158 ms for 909 files and 38–799 ms for the rest.
  - `good_freq` 48–93% (median 72%).
- **Exposure:** HEALPix nside 4096, integrated `upper`/`lower` seconds per pixel, 2018-09-04 to 2023-09-15. Not time-resolved.

## Compared with the plan
- **Matched:** burst and source counts (4539 / 981 / 83). Every repeater burst has a dynamic spectrum, so the Table 2 risk did not occur. Resolution is 0.983 ms and the band is 400–800 MHz.
- **Differed:**
  - Size is 13 GB, not ~10 GB.
  - 6 files have coarser time resolution, and the window length varies. Preprocessing therefore needs a rebin and crop step to a fixed input size.
  - Usable channels (median 72%) are more than in Catalog 1 (44–71%).
- **Risk confirmed:** the exposure file gives total exposure only. Burst-by-burst observation filtering needs a reconstruction of transit windows from sidereal time, scaled to this exposure. That is an approximation to document.

## Next
- Phase 1, step 2: preprocessing. Choose one dt, rebin, crop around the peak, downsample frequency, keep the channel mask, and save a compact array set.
- Decide whether to keep `excluded_flag=1` bursts.
- Write the transit-window reconstruction for the observation filter and check it against the integrated exposure.
