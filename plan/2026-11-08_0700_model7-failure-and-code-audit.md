# Plan: why model 7 seed 1 does not train, and an audit of physics and program logic

Asked by the user 2026-11-08 after the Stage 2 rerun ([update](../update/2026-11-08_0640_phase3-stage2-rerun.md)).

1. **Model 7 seed 1.** Re-run the first 2000 steps of `m7_s1` and `m7_s2` (same seeds, same code) with instruments: loss, spread of the head input across pairs, attention entropy, gradient norm per block, active head units. Find where the signal is lost. Diagnosis only; no training setting changes without the user.
2. **Physics audit of `inject.py`:** dispersion constant and delay sign, residual-DM width, scattering law and kernel, scintillation statistics and channel width, S/N definition and re-normalisation, time resolution and frequency grid against the raw files, sigma units of the template.
3. **Logic audit:** pair construction per class (same draws for all classes, backgrounds never from the template's file, split disjointness), labels end to end, training loop, evaluation (member order, unrelated excluded), metric and bootstrap, baseline score alignment.
4. **Numeric checks** for anything suspicious, run on train/val only. Test sets stay closed; real same-source pairs stay blinded.
5. Report each item as OK, bug (with effect on results) or modelling limitation. Fixes that change frozen sets or results need the user's agreement.
