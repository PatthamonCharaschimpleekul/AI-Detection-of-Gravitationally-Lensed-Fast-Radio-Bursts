# Plan: impostor pairs for Track B (cross-file pairs only)

- **Date/time:** 2026-11-05 19:25
- **Pipeline box:** `01_semi_synthetic_data/05_impostors` → class `impostor` in `02_injection_labelling/01_injection`
- **Follows:** [update 1909](../update/2026-11-05_1909_template-closure-v1.md)
- **Status:** proposed; decisions 1–3 need agreement before code.

## Context: the listed impostors were written for a broader project
Project_Description (Phase 1 step 5, Sec. 7 controls) lists three impostors: plasma-lensed bursts, diffractive scintillation, and naturally multi-component bursts. Two of them are **within-file** phenomena:
- **Plasma-lensing echoes** arrive µs–s apart, inside one 157 ms window or a few seconds away.
- **Multi-component bursts** are sub-bursts ms apart in one file.
- The scintillation false candidates of Kader et al. 2022 were echo candidates in baseband, i.e. µs-scale and within one burst.

Track B compares bursts in **different files**, hours to months apart (galaxy lenses). Within-file echoes are excluded by the Track B non-goal (plan 1254). So an impostor for Track B must be **a pair of different bursts that looks like one burst seen twice.**

## Decisions (proposed)
1. **Impostor = an intrinsic-repeat pair (two different templates, same source) that shares a propagation imprint gravity would also leave identical.** Two physical mechanisms:
   - **I1, shared plasma-lens magnification.** A plasma lens in the host (proposed for FRB 20201124A's band-limited brightening) multiplies every burst passing through it by the same chromatic gain G(ν) while it persists. Two repeats then share a narrow-band spectral envelope, which mimics the "same spectrum" signature of a lensed copy.
     - Model: G(ν) = 1 + A·exp(−(ν−ν₀)² / 2w²), applied to both members.
     - Ranges: ν₀ uniform over 400–800 MHz; w log-uniform 10–100 MHz; A log-uniform 1–10. These are placeholder ranges. **To check against the literature** (Cordes et al. 2017; FRB 20201124A papers) before freezing.
   - **I2, shared scintillation.** Repeats closer in time than the scintillation timescale (minutes to hours at CHIME) share one diffractive pattern. Model: the same per-channel scintillation gain on both members, instead of independent gains.
   - I1+I2 can combine.
   - Gravity is achromatic: real lensed images have *independent* plasma imprints, which is what v1 already simulates. So the discriminating physics is "same burst" (morphology), not "same spectrum".
2. **Out of scope, written into Project_Description:**
   - **Multi-component bursts** and **plasma-lensing echoes within one burst** are Track B non-goals; they cannot form a cross-file pair.
   - The Sec. 7 control "must reject multi-component bursts" is reworded to cross-file pairs.
   - **Hard negatives** (the most similar real repeats) stay a Phase 3 training choice (mining/oversampling), not a fourth class.
3. **Labels and use.** `impostor` is a fourth pair label, but Track B stays binary for scoring: `lensed` vs everything else.
   - Frozen sets get impostors added as **v1.1**: val/test/stress grow from 3000 to 4000 pairs (1:1:1:1). The existing 3000 pairs keep their index and seed (new pairs are appended, kinds cycle `i % 4` only for i ≥ 3000), so v1 subsets stay reproducible.
   - **Real control:** FRB 20201124A's real repeat pairs (34 bursts in Catalog 2) must not score as `lensed`. It is the Project_Description control; it is in the test split only if the split put it there, so it is checked separately on real data.

## What we will do
1. `make_pair("impostor", …)`: same source pool and source sampling as the other classes; two different templates. Draw I1 with p = 0.5 and I2 with p = 0.5 (at least one), and apply them as **shared** multipliers before per-member nuisances. Everything else (S/N, r, backgrounds, shift, DM, scattering) is exactly as in `repeat`.
2. **Leak audit** extended to impostor vs lensed and impostor vs repeat:
   - probe (b) with the same feature set, gate AUC ≤ 0.55 for impostor vs repeat on non-spectral features;
   - (a) per-member KS;
   - (c) noise correlation ≈ 0.
   - Expected and wanted: baseline 1 scores impostors *between* repeat and lensed (they share spectra, not morphology).
3. **Real control:** baseline 1 on FRB 20201124A real pairs vs other sources' real repeat pairs, per S/N bin. This is a reference, not a gate.
4. Version bump to v1.1; manifests and hashes; the v1 subsets regenerate identically (asserted).

## Expected result
- Impostor baseline-1 median between repeat and lensed. If it equals lensed, the impostor is too strong for a morphology-blind score: that is the intended hard case, and it is reported.
- Probe (b) for impostor vs repeat ≈ 0.5 on non-spectral features.
- v1 hashes unchanged for indices < 3000.

## Risks / open questions
- I1 ranges are placeholders until checked against the literature. A wrong A or w makes the class trivially easy or impossible.
- I2 assumes the current Gamma(N) scintillation depth, which is not calibrated (update 1530).
- **Selection:** in real data, short-gap repeats are common only for very active sources (FRB 20220912A, FRB 20201124A). I2's prevalence in the test set should follow the real gap distribution per source, not 50%. v1.1 uses 50% for the benchmark and reports the prevalence-weighted rate separately.

## As built (2026-11-05, after agreement) — changes from the proposal
- **Literature check (I1):** Cordes et al. 2017 (ApJ 842, 35) give caustic boosts up to ~100 that last hours to days and appear as narrow spectral peaks. No CHIME-band width was found; Chen et al. 2024 (arXiv:2401.18036) model FRB 20201124A with a 1-D Gaussian lens.
- **I1 changed from a parametric Gaussian gain to envelope transfer.**
  - **Why:** the first build (Gaussian, A 1–100, w 10–100 MHz) failed audit (a). Impostor members' box S/N fell to 9.58 vs 10.04 for repeats (KS p = 0.000), because the gain made single members narrower than real bursts. That is a one-member cue a model could learn as "narrow-band → not lensed", which is harmful because most CHIME repeaters are band-limited.
  - **Now:** member B keeps its own time–frequency structure but takes member A's 25 MHz-smoothed envelope (ratio capped at 10). So each member's spectrum stays a real burst spectrum, and there are no A or w knobs.
- **Counts:** pairs 3000–3999 are **all** impostors (1000), giving 1000 per class. The v1 pairs 0–2999 are asserted to reproduce the v1 hashes.
