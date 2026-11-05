# Plan: preprocess Catalog 2 repeater dynamic spectra into model-ready arrays

- **Date/time:** 2026-11-04 15:47
- **Pipeline box:** `01_semi_synthetic_data/01_real_data`
- **Follows:** [update 2026-11-04_1507](../update/2026-11-04_1507_catalog2-repeater-data.md)

## Context
- 981 repeater bursts are on disk, but they do not have the same size:
  - **Time resolution:** dt = 0.983 ms for 975 files; 1.966 or 3.932 ms for 6.
  - **Window:** 158 ms for 909 files, 38–799 ms for the rest.
  - **Channel masks** differ per burst (`good_freq` 48–93%).
- Every file holds **one burst event**: widths are ~0.3–20 ms, and some bursts have up to 7 sub-bursts a few ms apart. Galaxy-lens images arrive hours to months apart, so the two images of a lens are always in **different files**. Cropping a file therefore cannot split a lensed pair.

## Decisions (agreed 2026-11-04)
1. **Time resolution: keep the native 0.983 ms. Never upsample.**
   - **Training and simulation:** leave out the 6 coarse files (0.6% of bursts). Their sources keep other bursts.
   - **Real search:** keep all 981. When a pair mixes resolutions, average the finer burst over 2 or 4 samples to match the coarser one. The coarse file is not changed. The finer one is binned exactly the way CHIME binned the coarse one.
2. **Window: crop, do not split.**
   - Cut a fixed window of **160 samples (157 ms)** centred on the burst, chosen so that every sub-burst stays inside it.
   - Shorter files are padded with zeros, plus a time mask that marks which samples are padding.
   - Off-pulse stretches of the long files are saved separately as a **real-noise bank** for injection (Phase 2).
3. **`excluded_flag=1` bursts (88 of 981 repeater bursts): keep them in the arrays with a flag column.**
   - **Meaning.** Catalog 2 (arXiv:2601.09399, Appendix A) defines it as "events that should be excluded from parameter inference due to non-nominal telescope operation". §II.1 names two groups: 13 commissioning-period events, where exposure is unknown before 2018-09-04, and 121 events on days with RMS noise >10% above the median, which are removed from the exposure. The table has 369 flagged bursts. The text does not explain the other 235.
   - **Repeaters.** 1 flagged burst is from commissioning and 87 are later. 46 belong to FRB 20220912A.
   - **Why it matters.** The flag does not mean the burst is bad. It means the burst falls outside the exposure, so it is outside the selection function.
   - **Use them** as burst templates and in pair scores; the morphology is real.
   - **Leave them out** wherever exposure enters: the observation filter, ε from injection–recovery, the Track C source likelihood, and the forecasts. Their days count as unexposed there, matching the exposure file.
   - **Cost.** 6 sources fall below 2 unflagged bursts. Those sources still enter the pair-level search.
   - **Related flags, also stored.** `sidelobe_flag` (4 repeater bursts) have no flux or localization, so no flux ratio. `citizen_science_flag` (7) have a different selection, so they are left out of statistics.

## What we will do
1. **Check dedispersion.** Confirm which DM each `data` array is dedispersed to (`dm_incoherent` vs the fitburst DM in `burst_parameters_json` / `dm_fitb`). Compare residual sweep on a few bright bursts. If they differ, re-dedisperse to `dm_fitb` so pairs are compared at their best DM.
2. **Find the burst centre.**
   - **Default:** use the fitburst model (`model` dataset). Take the centre of the model's band-summed profile, and require that all components fall inside the window.
   - **Fallback (no model, or width = nan):** take the peak of the smoothed, band-summed time series over good channels.
3. **Crop or pad to 160 samples.** Write a time mask (1 = real data, 0 = padding). Flag any burst whose model extends past the window (expected: FRB20211115D, scattering 0.35 s).
4. **Downsample frequency.** Primary: **256 channels** (64 native, 1.56 MHz). Also save **1024 channels** (16 native = one CHIME coarse channel, 390 kHz) for a benchmark ablation.
   - Any re-dedispersion (step 1) is done at native resolution first.
   - Average only good channels. Store the good fraction per new channel as a frequency mask, and zero channels that are less than 25% good.
   - **Block sizes must be multiples of 16.** Each 390 kHz coarse channel is split into 16, and its edge channels sit ~20% low (measured below). Averaging whole coarse channels cancels this ripple exactly.
   - **Measured on the 28–34 brightest repeater bursts (snr_fitb 92–419),** 2026-11-04, with `check_freq_structure.py` and `check_freq_origin.py` (`python -I <script> data/catalog2 40`). Signal variance finer than a given width, as a share of all spectral signal variance, median:

     | Finer than | Share of signal variance |
     |---|---|
     | 390 kHz | 14% |
     | 1.56 MHz | 20% |
     | 6.25 MHz | 25% |
     | 25 MHz | 30% |

     The fine part is mostly scintillation-like: frequency ACF half-width 24–220 kHz, median 73 kHz. The 16-channel ripple accounts for only a small share (fold amplitude 0.11 vs fine scatter 0.71).
   - **Why 256 is acceptable for the main task.** Scintillation changes within hours, and lens images are ~arcsec apart, so the two images of a lens never share a scintillation pattern. Its statistics (bandwidth) are the same for lensed copies and for intrinsic repeats of the same source. So it carries no lensed-vs-repeat signal. The burst's own spectral shape (tens of MHz, drift) survives at 1.56 MHz.
   - **Keep the information anyway, cheaply.** Store each burst's scintillation bandwidth Δν_d, measured from the native-resolution ACF, as a scalar in the metadata table. It may help against unrelated-source and impostor pairs.
   - The 1024-channel ablation tests whether the 390 kHz–1.56 MHz band matters.
5. **Normalise.** Per channel, subtract the off-pulse mean and divide by the off-pulse standard deviation. Store the calibration factor to Jy (`calibration/*`) separately; the flux-ratio input needs it.
6. **Build the noise bank.** From files longer than 160 samples, take 160-sample stretches that stay at least 3 burst widths from any component. Process them in the same way (steps 4–5).
7. **Visual check.** Save a PNG gallery to `outputs/preproc_gallery/`:
   - all 26 long-window bursts;
   - all bursts with width = nan;
   - the 6 coarse bursts;
   - 30 random others.

   Before and after cropping, check by eye that no sub-burst is cut off.
8. **Save** two HDF5 files, `data/catalog2/preproc/repeaters_256x160.h5` (~160 MB) and `repeaters_1024x160.h5` (~640 MB). Each holds:
   - `X` (981 × n_freq × 160, float32), `freq_mask`, `time_mask`;
   - a metadata table: TNS name, source, `mjd_400`, native dt, centre index, DM used, Jy factor, Δν_d and its quality flag, `excluded_flag`, `sidelobe_flag`, `citizen_science_flag`, `coarse_dt`, `clipped`;
   - `noise_bank`.
9. **Self-check (asserts in the script):**
   - array shapes;
   - binning conserves the mean;
   - every fitburst component lies inside its window, unless the burst is flagged `clipped`;
   - for 0.983 ms files, no NaN outside masked regions.

Script: `01_semi_synthetic_data/01_real_data/preprocess_catalog2.py`, run with `python -I`.

## Expected result
- 981 bursts in one file: 975 marked training-eligible, 6 marked `coarse_dt`. At most a handful (~1–3) flagged `clipped`.
- A noise bank of a few hundred 160-sample stretches. Most will come from the 26 long files and from FRB 20220912A.
- The gallery shows every burst whole and centred.
- Run time is minutes, dominated by reading 13 GB.

## Risks / open questions
- **Dedispersion:** if `data` is dedispersed at the incoherent (detection) DM, residual sweep would differ between bursts and look like a "not the same burst" signal. Step 1 must settle this first.
- **256 channels drops ~20% of spectral signal variance,** mostly scintillation (measured above). If the 1024-channel ablation does better, switch the primary input to 1024 (~640 MB instead of ~160 MB).
- **Δν_d from the ACF is a rough estimate.** It is noisy for faint bursts. Store an S/N-based quality flag with it.
- **The fallback centre** may lock on RFI for faint bursts with no fitburst model. The gallery check covers these.
- **160 samples** may be too short for the most scattered bursts. If more than ~1% are clipped, use 256 samples instead.
- **`excluded_flag`:** the text explains only 134 of the 369 flagged bursts. Ask CHIME/FRB, or check the catalog's release notes, before the search unblinding.
