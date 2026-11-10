# Update: repeater population, SIS lens simulator, Track C timing test and first forecasts

- **Date/time:** 2026-11-09 14:40
- **Plan:** Phase 1 steps 1, 2 and 4 and Phase 5.1 of Project_Description. No separate plan file; this update records the design choices.
- **Pipeline box:** `01_semi_synthetic_data/02_population`, `03_lens_simulator`, `03_models_benchmark/track_C_timing`, `06_cosmology/01_forecast`
- **Matches plan?** 🟡 Built and self-checked. The transit result **contradicts Sec. 4.1** (see below).

## What we did
- **`02_population/population.py`:** per-repeater table, burst lists, and redshift samples.
  - Host-galaxy z for 7 localised repeaters, checked against the cited papers on 2026-11-09.
  - Otherwise z from the NE2001 DM excess through the Macquart relation, with a halo term (25–80 pc/cc), a lognormal host term (median 68, σ_ln 0.88), and the Macquart p(Δ) with F = 0.32.
  - Check: ⟨DM_cosmic⟩(z = 1) = 911 pc/cc.
- **`03_lens_simulator/lens.py`:**
  - **Lens model:** SIS lenses with the Choi et al. 2007 velocity-dispersion function. Delay, flux ratio and optical depth are computed in closed form, and the delay formula is checked against the Fermat potential.
  - **CHIME observation filter:** a transit window of |HA| cos δ < 1.1°, plus a lower transit for δ > 70°; survey dates; observing days p_on, taken from catalogue `exp_up`; and S/N ≥ 10.
  - **Window measured on real data:** 94% of real bursts lie within 0.25 h of transit, and 99% within 1.08° on sky.
- **`track_C_timing/timing.py`:**
  - **Statistic:** k_max, the largest set of disjoint burst pairs sharing one delay within 4σ of the infinite-frequency timing errors (median 4 ms), with S/N ratios agreeing within a factor 2.
  - **Background:** time-scrambled lists, with each burst moved by whole sidereal days, which keeps hour angle, S/N and transit selection. Per-source threshold at a false-alarm probability of 1e-3.
  - **Efficiency:** from lensed injections into scrambled lists, conditioned exactly on window alignment.
  - **Blinding:** unscrambled real lists are never scored.

## Results
- **Optical depth:** τ(z_s) for the SIS population is 3.1e-7 at z = 0.1, 7.1e-6 at 0.3, 2.8e-5 at 0.5 and 1.5e-4 at 1.0. This is without magnification bias.
  - Summed over the 83 repeaters: 2.9e-3.
  - The sum is dominated by a few high-DM sources with no host z, whose DM-inferred z of ~1.5 may be biased high by large host DM.
- **Delays:** median 5 d at z = 0.1, 14 d at 0.3, 39 d at 1.0. 90% of delays fall between 0.5 d and 200 d.
- **Timing background:** k_max ≥ 2 never occurs by chance in 2000 scrambles for most sources. The exceptions, and the threshold k each gets:

  | Source | Bursts | P(k_max ≥ 2) in scrambles | Threshold k |
  |---|---|---|---|
  | FRB 20220912A | 373 | 1.0 | 4 |
  | FRB 20180916B | 113 | 0.054 | 3 |
  | FRB 20201124A | 34 | 0.013 | 3 |
  | FRB 20190303A | 35 | 0.001 | 2 |
  | FRB 20190208A | 18 | 0.0005 | 2 |

- **Transit geometry: the main finding.**
  - **Why copies are rarely recorded:**
    - Every recorded burst arrives within minutes of transit. Its copy therefore arrives at the same hour-angle offset, 24 h × frac(Δt / T_sid), for every burst of the source.
    - So copies are recorded for all bursts or for none. They are recorded only if Δt is within minutes of a whole number of sidereal days, or of half a day for lower transits at δ > 70°.
  - **Size of the effect:** the share of lens delays that align is p_align = 1.8% at the median over sources. It ranges from 0.6% to 100%, where 100% is near the pole.
  - **Consistency check:** the simulated values follow twice the transit-window width per sidereal day (`07_deliverables/paper/fig_transit.pdf`).
  - **Conclusion:** a repeater gives many pairs *once aligned*, but the chance of alignment is the same ~θ_EW/2π as for one-off FRBs.
- **Expected lensed repeaters in the Catalog 2 sample:**

  | Scenario | Σ τ | N_exp, timing detection | N_exp, ≥ 1 recorded copy |
  |---|---|---|---|
  | CHIME as observed | 2.9e-3 | 5.3e-6 | 3.2e-5 |
  | All-sky monitor, same sources | 2.9e-3 | 2.6e-4 | 6.3e-4 |
  | CHIME, magnification bias γ = 1.5 | 1.8e-2 | 1.2e-4 | 4.9e-4 |
  | All-sky, γ = 1.5 | 1.8e-2 | 6.2e-3 | 9.3e-3 |

  | CHIME-like, 10 yr | 2.8e-3 | 7.4e-6 | 4.9e-5 |
  | All-sky, 10 yr | 2.8e-3 | 3.7e-4 | 6.8e-4 |
  | CHIME-like, 10 yr, γ = 1.5 | 1.8e-2 | 2.2e-4 | 6.3e-4 |
  | All-sky, 10 yr, γ = 1.5 | 1.8e-2 | 7.4e-3 | 9.6e-3 |

  - **A longer transit survey barely helps:** 10 years instead of 5.1 raises CHIME N_exp by only 1.4–1.8×, because the alignment requirement stays. An all-sky monitor gains ~50×. For CHIME-like surveys the limit is sky coverage, not time on sky.
- **Held-out false-alarm check (`track_C_timing/far_check.py`, `outputs/far_check.csv`):**
  - Method: thresholds set from 2000 scrambles on one random stream, then exceedances counted in 2000 fresh scrambles per source on an independent stream.
  - Result: 1 exceedance in 166,000 (FRB 20190417A, 1/2000). The per-source rate is 6e-6 (95% upper 2.9e-5, against the nominal 1e-3), and at most 0.002 false sources are expected in a search of all 83 repeaters.
  - The test is conservative because k is an integer.

## Compared with the plan
- **Sec. 4.1 and update 2026-11-04_1112 should be corrected.** They say lensed repeaters "escape most of" the transit problem. The alignment requirement says they do not; repeaters only give more pairs once aligned. This strengthens the motivation for the all-sky-monitor forecast, Phase 5.1 (c).
  - **Why the old argument fails.** "Every transit catches bursts from both images" is true, but those are *different* bursts.
    - A pair needs the *same* burst in both images.
    - The copy of a burst recorded at transit arrives at a fixed hour-angle offset.
    - Image-2 bursts seen at transit therefore have image-1 counterparts that arrived off transit, unless the delay is aligned.
  - **Proposed replacement text for Sec. 4.1** (for the team to accept or edit):
    > A lensed repeater does not escape this. Every transit records bursts from both images, but rarely the same burst twice: the copy of a burst recorded at transit arrives Δt later at hour angle 24 h × frac(Δt/T_sid), the same offset for every burst of the source. Copies are recorded only if Δt lies within minutes of a whole number of sidereal days, for a share p_align ≈ 2 × (window width)/T_sid of lenses (median 1.8% for the Catalog 2 repeaters). Once aligned, a repeater gives many copy pairs, so a source-level timing test is very sensitive; the rate of aligned lenses, not the number of bursts, sets the yield (update 2026-11-09_1440).
- **N_exp ≪ 1 for Catalog 2,** as Sec. 5.1 already expected. A null search result is the expected outcome.

## Assumptions to review
- **Lens model:** SIS only, with no external shear. An SIE would add 4-image systems.
- **Which image is recorded:** the recorded list is treated as the brighter, leading image, so the copies are the fainter trailing image.
- **S/N of copies:** copy S/N = S/N × r × lognormal(0, 0.3).
- **Detection floor:** S/N ≥ 10, against a catalogue bonsai floor of about 8.5. This choice is conservative.
- **Magnification bias:** shown only as a variant. Its slope for CHIME repeaters is not measured.
- **Observing days:** p_on comes from the integrated exposure, which assumes downtime is spread evenly over the survey.

## Next
- **Single-copy channel:** done in the paper draft. N(≥ 1 recorded copy) = 3.2e-5, which is about 1.5e-5 at model 6's development recall.
- **Sec. 4.1:** the team decides on the replacement text above.
