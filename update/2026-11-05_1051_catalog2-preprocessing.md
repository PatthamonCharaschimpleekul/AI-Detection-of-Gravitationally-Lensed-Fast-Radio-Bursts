# Update: preprocess Catalog 2 repeater dynamic spectra

- **Date/time:** 2026-11-05 10:51
- **Plan:** [../plan/2026-11-04_1547_catalog2-preprocessing.md](../plan/2026-11-04_1547_catalog2-preprocessing.md)
- **Pipeline box:** `01_semi_synthetic_data/01_real_data`
- **Matches plan?** 🟡 mostly. All nine steps ran and every self-check passes. Three numbers differ: the noise bank is 20 stretches, not "a few hundred" (the plan's rule caps it at that — see Ruling); 6 bursts are `clipped`, not 1–3 (still under the plan's 1% line, so 160 samples stays); Δν_d measures on only 195/981 bursts (rough by design, quality flag stored).

## What we did
- Wrote [preprocess_catalog2.py](../01_semi_synthetic_data/01_real_data/preprocess_catalog2.py) (`python -I preprocess_catalog2.py data/catalog2`, ~20 min over all 981 files) and ran it end to end.
- **Step 1, dedispersion:** `dm_incoherent` equals the fitburst DM for 980/981 bursts; the worst outlier (1.61 pc/cc) is a 0.03 ms residual sweep, under one sample. **Ruling: no re-dedispersion.** `dm_used` = `dm_incoherent`, stored per burst.
- **Extent** comes from `pulse_emission_region`, which holds *several rows* (one per sub-band) in 186 files — we take the union of all rows (reading only the first would cut e.g. FRB20220714C to one sample). Fallback chain: band-summed fitburst model (>1e-3 of peak), then the smoothed data peak. Covers the 8 files with no `model` and the 7 with no `burst_parameters_json`.
- **Crop** to 160 samples centred on the extent midpoint; zero-pad + `time_mask` where the file is short (6094 padded samples total).
- **Frequency:** block means of 16 native channels (→1024) and 64 (→256), good channels only; `freq_mask` = good fraction; channels <25% good zeroed.
- **Normalise:** per output channel, off-pulse mean/std (extent ±20 excluded, ≥10 samples, else the catalog `statistics` std as fallback). The raw scale is recoverable: `norm/mean`, `norm/std` datasets store it per channel (added beyond the plan's list — Phase 2 flux-ratio work needs it, and it lets the binning assert run on reconstructed raws; see Compared below).
- **Noise bank** + **gallery** (59 PNGs: all >160-sample files, the 6 coarse, the 6 clipped, width-nan bursts, 30 random) + **asserts** per plan step 9, all passing.
- Δν_d uses the exact definition of `check_freq_origin.py` (where the plan's 73 kHz came from): ACF of the on-pulse spectrum's relative deviation from its 1.56 MHz envelope, over the emitting band, normalised at lag 1.

## Results
- `data/catalog2/preproc/repeaters_256x160.h5` (**167 MB**) and `repeaters_1024x160.h5` (**668 MB**).
- **981 bursts** × (256 or 1024) × 160, float32: 975 fine-dt + **6 `coarse_dt`**; **6 `clipped`**; flags `excluded_flag` 88, `sidelobe_flag` 4, `citizen_science_flag` 7 — all as the plan predicted.
- `X` on good cells: median |X| 0.65, std 1.03 (1024: 0.64/1.00); everything masked or padded is exactly 0; no NaNs anywhere. Noise bank std 0.98–1.01.
- **Noise bank: 20 chunks from 5 files** (`noise_bank/X` + `noise_bank/file_idx`).
- **Δν_d: median 49 kHz** over the **195/981** bursts where it measures (range 49–220 kHz); 81 bursts have no fitburst S/N or S/N<100, and the rest have too narrow an emitting band. `dnu_good` (= finite Δν_d and S/N ≥ 100) marks **23**.
- Asserts: shapes, finiteness, centre in window, unclipped extents inside the window, every fitburst arrival time inside its window (unclipped), binning conservation **0 cells > 8σ out of 23.5 M**.
- Gallery in [outputs/preproc_gallery/](../01_semi_synthetic_data/01_real_data/outputs/preproc_gallery/). By eye: every burst whole and centred; the only truncation is the 6 clipped ones, where exactly one edge sample of the emission region falls out.

## Compared with the plan
- **Matched:** 981/975/6 counts, all three CSV flags, window/crop/pad design, 256-primary + 1024-ablation files (~160/~640 MB predicted), per-channel off-pulse normalisation, Jy factor stored (`jy_per_unit`), gallery saved, minutes-to-tens-of-minutes runtime.
- **Differed:**
  - **Noise bank 20, not "a few hundred."** Ruling — the plan's own rule (a whole 160-sample stretch clear of the burst by 3 widths + 20 samples) cannot hold in a 162-sample file, and 909 files are 158 samples, so only the five 814-sample files contribute; FRB 20220912A's bursts (all 162) contribute none. This is a defect in the plan's expectation, not in the data. Phase 2 can stretch 20 real noise records into many with cyclic shifts, and can harvest more by allowing padded chunks or a clearance < 3 widths if needed.
  - **clipped = 6, not 1–3** (0.61%). Plan's risk rule: under 1% → keep 160 samples. Kept; each is flagged, worst overflow is 1 sample.
  - **Δν_d coverage 20%.** Plan flagged it as rough for faint bursts; the S/N quality flag was always the answer, but note only 33 bursts have S/N ≥ 100 at all.
  - **Binning assert redefined.** "mean-of-four X1024 == X256" is false by construction after per-channel σ-normalisation (σ₁₆ ≈ 2σ₆₄, so it holds for raws, not for X). Conservation is instead checked on raws reconstructed from `norm/mean`+`norm/std`: deviations > 8σ at 0 cells. The 8σ slack absorbs the unequal-valid-count difference at heavily masked channels; an ordering bug would deviate at every peak column and cannot pass.
  - **Centre = extent midpoint**, not "centre of the model's band-summed profile" (plan step 2 wording): the union of `pulse_emission_region` rows is the catalog's own statement of where the burst is, and it is what the crop is checked against.
  - Extra datasets vs the plan's list: `norm/mean`, `norm/std`, `meta/extent_lo/hi`, `meta/ncol/start` — all cheap, all needed by the asserts or Phase 2.

## Next
- Phase 2: build semi-synthetic pairs — inject one burst into another using the noise bank (20 real stretches + cyclic-shift variants), lens-copy pairs with Δν_d-independent scintillation, per the Siamese design.
- Train the 256-channel primary and the 1024-channel ablation; if 1024 wins materially, it is already on disk.
- Observation filter (transit-window reconstruction) is still open from the previous update; use `excluded_flag`/`citizen_science_flag` columns there, and leave Δν_d out of anything exposure-weighted (20% coverage).
