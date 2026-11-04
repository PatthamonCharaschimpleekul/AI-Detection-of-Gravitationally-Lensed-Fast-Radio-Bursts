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
| **Catalog 2 (4539 bursts; 981 from 83 repeaters)** — main dataset | [CANFAR DOI 10.11570/25.0066](https://www.canfar.net/storage/list/AstroDataCitationDOI/CISTI.CANFAR/25.0066/data) | Folders `table`, `dynamic_spectra/data` (`<TNS>_stokesi_dynamic_spectrum.h5`, ~10 MB each; 0.983 ms, 400–800 MHz), `exposure` (`chimefrbcat2_exposure.h5`, 206 MB), `localizations`. Checked 2026-11-04; format not yet inspected |
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
- Next: download the Catalog 2 repeater dynamic spectra and exposure, and check that their format matches Catalog 1.

Run the check: `python -I inspect_waterfalls.py data/waterfalls/*.h5` (add `-v` for the full HDF5 tree).
