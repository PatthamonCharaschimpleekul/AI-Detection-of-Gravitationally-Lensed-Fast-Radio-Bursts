# Update: impostor class for Track B (sets v1.1)

- **Date/time:** 2026-11-05 19:28
- **Plan:** [../plan/2026-11-05_1925_impostor-pairs.md](../plan/2026-11-05_1925_impostor-pairs.md) (see its "As built" section)
- **Pipeline box:** `01_semi_synthetic_data/05_impostors` → `02_injection_labelling/01_injection`
- **Matches plan?** 🟡 Mostly. The scope is as agreed (I1 + I2, cross-file only). I1 was rebuilt once after audit (a) caught a one-member cue. One audit KS test still fails formally, but the exploitable size is small (AUC ≤ 0.52).

## What we did
- **`make_pair("impostor")`:** two different templates of one source (same pool, sampling, S/N, backgrounds and nuisances as `repeat`), plus a shared imprint, uniformly one of I1 / I2 / I1+I2:
  - **I1:** envelope transfer. Member B takes member A's 25 MHz-smoothed spectral envelope.
  - **I2:** both members get the same scintillation gain pattern instead of independent ones.
- **Frozen sets v1.1:** val / test / stress grow to 4000 pairs. Pairs 0–2999 are exactly v1 (asserted against the v1 hashes for all three sets); 3000–3999 are impostors. New hashes: val `d9b6f8f6`, test `e9c120ea`, stress `1ac99f30`.
- **Audit extended** to four classes, plus the real control FRB 20201124A.
- [checks/impostor_member_cue.py](../02_injection_labelling/01_injection/checks/impostor_member_cue.py): the single-member cue test.
- **Docs:** [Project_Description.md](../Project_Description.md) Phase 1 step 5, the evaluation metric and the Sec. 7.1 controls are reworded to cross-file impostors. Multi-component bursts and within-burst echoes are out of Track B.

## Results
- **First build (parametric Gaussian I1, A 1–100):**
  - audit (a): impostor members' box S/N 9.58 vs repeat 10.04 (KS p = 0.000);
  - baseline 1 could not tell impostors from repeats (AUC 0.45–0.51). Rejected.
- **Final build (envelope transfer):**
  - **Probe (b):** lensed vs repeat AUC 0.505; impostor vs repeat (non-spectral features) **0.515 → PASS**.
  - **(c)** noise correlation ≈ 0 in all four classes.
  - **(a)** box S/N still differs: impostor 9.49 vs repeat 10.04 (KS p = 0.000), because transfer narrows B to the overlap of the two bands.
  - **Exploitable size of that cue:** a GBM on order-invariant single-member stats gives impostor vs repeat AUC **0.503** (I1 only 0.523, I2 0.471, I1+I2 0.517). Below the 0.55 gate used elsewhere; the KS test detects a real but small shift with 8000 members.
  - **Baseline 1 places impostors between repeat and lensed, as the plan expected:**

    | min S/N | lensed vs repeat | lensed vs impostor | impostor vs repeat |
    |---|---|---|---|
    | 10–15 | 0.642 | 0.594 | 0.545 |
    | 15–25 | 0.759 | 0.698 | 0.570 |
    | 25–50 | 0.821 | 0.711 | 0.623 |
    | > 50 | 0.788 | 0.751 | 0.550 |

  - **Band overlap:** of the 665 I1 impostors in test, 19% have envelope overlap < 0.3 (Bhattacharyya; median 0.62). For those, transfer cannot create emission where the template has none, so they act as near-repeats (gallery #3003).
- **Real control FRB 20201124A** (baseline-1 median, real pairs; reference, not a gate):
  - S/N 10–25: 0.0171 vs 0.0153 for other sources, i.e. its faint repeats are more alike than others' (+12%);
  - S/N ≥ 25: 0.0255 vs 0.0403 (less alike).
  - These are mixed signs and need no conclusion yet; they become a Phase 3 control for the learned models.
- **Gallery:** `outputs/gallery_impostor.png` shows shared bands in most pairs and the non-overlap failure in #3003.

## Compared with the plan
- **I1 design changed** from a parametric gain to envelope transfer (reason above; recorded in the plan's "As built"). This removes the placeholder A and w ranges the plan flagged as unchecked.
- **Audit (a) KS p > 0.01 fails for box S/N.** Kept, with the measured exploitable size (AUC ≤ 0.52) as the reason. A model reading single-member band shape gains almost nothing.
- I2 still uses the uncalibrated Gamma(N) scintillation depth (open since update 1530).
- I2 prevalence: 2/3 of impostors carry I2, versus the real short-gap rate per source. The prevalence-weighted rate is not computed yet (plan risk).

## Next
- **Phase 3 can start on v1.1** (`load_set`). Report lensed vs {repeat, impostor} separately, headline at S/N ≥ 25.
- Optional, only if a learned model exploits it: restrict I1 to template pairs with envelope overlap ≥ 0.3, and re-check probe (b) and the single-member cue.
- Prevalence weighting for I2 from the real burst-gap distribution per source.
