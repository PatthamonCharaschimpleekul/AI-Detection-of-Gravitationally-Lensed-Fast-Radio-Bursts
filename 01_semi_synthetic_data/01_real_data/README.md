# Real data sources

**Purpose:** Download and organise CHIME/FRB Catalog 2 repeater dynamic spectra, table and exposure (and Catalog 1 waterfalls as a format cross-check), plus FAST/Blinkverse repeater bursts for augmentation.

**Inputs:** CANFAR (Catalog 2 DOI 10.11570/25.0066; Catalog 1 DOI 10.11570/21.0007), FAST and Blinkverse archives.

**Outputs:** Local copies in data/, plus a short note on versions and resolution.

Diagram box in [pipeline.mmd](/pipeline.mmd). Large files go in `data/` or `outputs/` inside this folder (gitignored).

## Data notes (checked 2026-11-03)

### Sources
| Product | Where | Notes |
|---|---|---|
| Catalog 1 table (v210806.vFINAL) | [CSV](https://assets.chime-frb.ca/catalogs/catalog1/releases/210806.vFINAL/data/catalog1.210806.vFINAL.csv) (also JSON, FITS) | 600 rows = sub-burst components of 536 bursts; 18 repeaters; 42 rows flagged `excluded_flag=1` |
| Catalog 1 waterfalls | [CANFAR DOI 10.11570/21.0007](https://www.canfar.net/storage/list/AstroDataCitationDOI/CISTI.CANFAR/21.0007/data/waterfalls/data) | One HDF5 per burst, `<TNS name>_waterfall.h5`, 30–116 MB each |
| **Catalog 2 (4539 bursts; 981 from 83 repeaters)** — main dataset | [CANFAR DOI 10.11570/25.0066](https://www.canfar.net/storage/list/AstroDataCitationDOI/CISTI.CANFAR/25.0066/data) | Folders `table`, `dynamic_spectra/data` (`<TNS>_stokesi_dynamic_spectrum.h5`, ~10 MB each; 0.983 ms, 400–800 MHz), `exposure` (`chimefrbcat2_exposure.h5`, 206 MB), `localizations`. Repeater spectra, table and exposure downloaded and inspected 2026-11-04 (see below) |
| Catalog 1 baseband (140 bursts) | [CANFAR DOI 10.11570/23.0029](https://doi.org/10.11570/23.0029) | 2.56 µs, ~2.3 GB per file. Not used since the switch to a single lensed-repeater paper |
| Blinkverse | blinkverse.alkaidos.cn | Multi-telescope database with FAST dynamic spectra (~5600 bursts, mostly FRB 20121102A and 20201124A); not yet accessed |

### Downloaded samples (`data/`)
- `catalog1/catalog1.210806.vFINAL.csv`
- `waterfalls/`: FRB20180725A, FRB20180727A, FRB20180729A (one-offs); FRB20180814A, FRB20180916B, FRB20181019A (repeater bursts; the last two are from the same source, FRB 20180916B); FRB20190308C (Chang et al. lensed candidate).

### Waterfall format (from [inspect_waterfalls.py](inspect_waterfalls.py))
- Group `frb`, attributes `tns_name`, `dm`, `scatterfit`, calibration source and date.
- `wfall`: 16384 channels × N time samples, **dt = 0.98304 ms**, dedispersed at the catalog DM. Window 18–130 ms (19–133 samples).
- Frequency 400.2–800.2 MHz, **24.41 kHz channels**.
- **29–56% of channels are NaN** (RFI-flagged); must be handled before use.
- Also `model_wfall`, `model_ts`, `model_spec` (fitburst model), `ts`, `spec`, `plot_time`, `plot_freq`, `extent`.
- `calibrated_wfall`: 16384 × 192–768 samples; its time axis is not stored and the format docs could not be reached, so its resolution is **unconfirmed**. Do not use until checked.

### What this means
- Galaxy-lens copies of repeater bursts are separate files, so the short window is fine for pair comparison.
- ~1 ms resolution limits how much burst structure a pair model can see; repeater bursts are often several ms wide, which helps.
- ~1 ms data cannot support compact-lens (µs–ms) work, which is out of scope (Krochek & Kovetz 2022).
Run the check: `python -I inspect_waterfalls.py data/waterfalls/*.h5` (add `-v` for the full HDF5 tree).

## Catalog 2 repeaters (downloaded and checked 2026-11-04)

Download: `python -I download_catalog2.py` (resumable, ~13 GB). Inspect: `python -I inspect_catalog2.py data/catalog2/dynamic_spectra`.

### Files in `data/catalog2/`
- `chimefrbcat2.csv`: 5045 rows (sub-burst components) for 4539 bursts. Repeaters: 1282 rows, **981 bursts from 83 sources**.
- `dynamic_spectra/`: all 981 repeater bursts, `<TNS>_stokesi_dynamic_spectrum.h5`, 13 GB total. None are missing.
- `chimefrbcat2_exposure.h5`: 216 MB.
- `missing_dynamic_spectra.txt`: empty.

### Repeater sample
- Bursts per source: median 3, minimum 2, maximum 373 (FRB 20220912A). Next largest: FRB 20180916B (113), FRB 20190303A (35), FRB 20201124A (34), FRB 20180814A (20).
- There are 78,701 within-source burst pairs. Without FRB 20220912A there are 9,323. FRB 20220912A spans 368 days; FRB 20180916B spans 1748 days.
- 88 bursts have `excluded_flag=1`. Decide before the search whether to keep them.
- Arrival-time columns: `mjd_400`, `mjd_inf` (with `_err`).

### Dynamic-spectrum format
- Datasets:
  - `data`: 16384 freq × N time, float32, mean-normalised;
  - `flag`;
  - `good_freq`;
  - `model` (fitburst);
  - `calibration/*` (to Jy);
  - `statistics/*`;
  - `index_map/times`, `index_map/times_unix` and `index_map/freqs`.
- Attributes include `dm_incoherent`, `burst_parameters_json` and `event_id`.
- Frequency is 400.2–800.2 MHz in 16384 channels (24.41 kHz), the same as Catalog 1.
- **Time resolution is not uniform.** 975 files have dt = 0.983 ms, 3 have 1.966 ms and 3 have 3.932 ms (FRB20180917A, FRB20210215C, FRB20220602D, FRB20230503B, FRB20230511C, FRB20230601E).
- **Window length is not uniform.** 909 files have 162 samples (158 ms); the rest range from 38 to 799 ms.
- **Usable channels (`good_freq`):** 48–93%, median 72%. Within good channels, 98–100% of samples are valid.

### What this means
- The model input needs a fixed size. Pick one dt, rebin the 6 coarse files or the rest to match, and crop or pad the window around the burst peak. Frequency must be downsampled (16384 channels is far more than needed).
- Masking differs per burst, so augmentation and the model must handle a per-burst channel mask. Use `good_freq` directly.
- **The exposure file is integrated, not time-resolved.** It has HEALPix `upper` and `lower` arrays (201,326,592 pixels = nside 4096) with total seconds on sky per pixel, `t_res` = 12, covering 2018-09-04 to 2023-09-15. It cannot say whether CHIME was observing at a given moment. The Phase 1 observation filter must rebuild daily transit windows from RA and sidereal time, scaled to the integrated exposure. This approximation must be stated in the paper.
- Download caution: CANFAR sometimes ends a transfer early without an error. 48 of the first 981 files were truncated but had a valid HDF5 header. `download_catalog2.py` now counts a file as complete only if h5py opens it.

## Preprocessing (done 2026-11-05)

Run: `python -I preprocess_catalog2.py data/catalog2` (~20 min). Plan and results: [plan](/plan/2026-11-04_1547_catalog2-preprocessing.md), [update](/update/2026-11-05_1051_catalog2-preprocessing.md).

- Output: `data/catalog2/preproc/repeaters_256x160.h5` (primary) and `repeaters_1024x160.h5` (ablation). Each holds `X` (981 × n_freq × 160, off-pulse σ-normalised), `freq_mask`, `time_mask`, `norm/mean`, `norm/std`, a metadata table (flags, DM used, Jy factor, Δν_d) and `noise_bank` (20 real 160-sample chunks).
- Gallery: `outputs/preproc_gallery/` (59 PNGs).
