# Real data sources

**Purpose:** Download and organise CHIME/FRB Catalog 1–2 waterfalls and tables, repeater bursts (CHIME, FAST, Blinkverse) and off-pulse noise/RFI.

**Inputs:** chime-frb.ca, FAST and Blinkverse archives.

**Outputs:** Local copies in data/, plus a short note on versions and resolution.

Diagram box in [pipeline.mmd](/pipeline.mmd). Large files go in `data/` or `outputs/` inside this folder (gitignored).

## Data notes (checked 2026-11-03)

### Sources
| Product | Where | Notes |
|---|---|---|
| Catalog 1 table (v210806.vFINAL) | [CSV](https://assets.chime-frb.ca/catalogs/catalog1/releases/210806.vFINAL/data/catalog1.210806.vFINAL.csv) (also JSON, FITS) | 600 rows = sub-burst components of 536 bursts; 18 repeaters; 42 rows flagged `excluded_flag=1` |
| Catalog 1 waterfalls | [CANFAR DOI 10.11570/21.0007](https://www.canfar.net/storage/list/AstroDataCitationDOI/CISTI.CANFAR/21.0007/data/waterfalls/data) | One HDF5 per burst, `<TNS name>_waterfall.h5`, 30–116 MB each |
| Catalog 1 baseband (140 bursts) | CHIME/FRB 2024, arXiv 2311.00111 | 2.56 µs, 1024 channels, HDF5; download location not yet checked |
| Catalog 2 (4539 bursts) | arXiv 2601.09399 | Public data products not yet checked |
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
- ~1 ms resolution confirms the limit noted by Krochek & Kovetz 2022: compact-lens echoes need Δt ≳ a few ms, i.e. lens masses ≳ tens of M☉ (Δt ≈ 40 µs × M/M☉ × (1+z_l) at y ≈ 1), and windows of tens of ms cap Δt at the high end.
- Galaxy-lens pairs (Track B) are separate files, so the short window is fine there.
- For µs-scale Track A work, the baseband release is the data to get next.

Run the check: `python -I inspect_waterfalls.py data/waterfalls/*.h5` (add `-v` for the full HDF5 tree).
