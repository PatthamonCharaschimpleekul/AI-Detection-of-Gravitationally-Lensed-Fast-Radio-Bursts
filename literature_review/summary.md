# Literature summary: four plan-changing questions

Searched 2026-11-03. Based on abstracts and arXiv metadata of the papers in [README.md](README.md); full texts were read in detail on 2026-11-04 — see "Corrections after full-text check" at the bottom.

## Q1. Has an ML classifier for lensed vs intrinsic-repeat FRBs been published?

**No, not found.**
- FRB machine learning so far classifies **repeater vs non-repeater** sources (Kharel et al. 2026 on Catalog 2 dynamic spectra; Madheshwaran et al. 2025 on baseband; several feature-based studies). None addresses lensing.
- FRB lensing searches use **autocorrelation or cross-correlation**, not learned models (Kader et al. 2022; Chang et al. 2025; Krochek & Kovetz 2022).
- The closest precedent is in **gravitational waves**: lensed-pair identification with DenseNet/XGBoost (Goyal et al. 2021) and, in 2026, a **Siamese ResNet that fuses paired features by absolute difference and element-wise product** (Zhang et al. 2026). That is essentially our Track B design, applied to another messenger. It supports the Siamese choice, and their noted need for "detector-domain adaptation" matches our real-noise concern.
- The de Mello/Law (Caltech) Siamese FRB study listed in the glossary was **not found** by these searches; treat it as unverified.

**Effect on plan:** Track B novelty holds. Cite Zhang et al. 2026 and Goyal et al. 2021 as the method precedent.

## Q2. Current CHIME limits on compact dark matter?

- **Leung et al. 2022:** coherent lensing search of 172 bursts (114 sightlines) at 1.25 ns gives f ≲ 0.8 for masses ~10⁻³ M☉. Sensitive to sub-solar masses.
- **Krochek & Kovetz 2022:** tried to set a bound from the **public Catalog 1 intensity data** and **could not**: "instrumental noise and the provided ~1 ms time-resolution of the public data hinder this effort." They estimate a few times Catalog 1's size *at full instrument resolution* would test PBHs > 10 M☉.
- Sammons et al. 2020: ~130 FRBs with µs structure needed to beat the existing ~35% limit.

**Effect on plan (important):** Track A "priority 1: an f_CO limit from public Catalog 1 intensity data" will very likely fail; it has been tried. Options:
1. Use the **Catalog 1 baseband release (140 bursts, 2.56 µs)** for an incoherent µs-resolution search, covering roughly 0.1–100 M☉, a range between Leung's coherent (sub-solar) and Krochek's (≳10 M☉) targets. Needs checking against Kader et al. 2022, which used much of the same baseband data.
2. Use **Catalog 2 (4539 bursts)** if its public waterfalls have useful resolution; this is the "few times Catalog 1" Krochek & Kovetz asked for, but at ~1 ms it would still only reach higher masses.
3. Keep Track A as method development (injection–recovery, ε maps) and make the real-data limit secondary.

## Q3. Status of the Chang et al. candidate and FRB 20220529A?

- **FRB 20190308C** (Chang et al., arXiv 2406.19654, MNRAS Letters): 3.4σ lensed candidate from autocorrelation of multi-peak Catalog 1 bursts (42 of 536 have multiple peaks); lens mass estimated with the Chang–Refsdal model. No confirmation found. Krochek & Kovetz also flagged one double-burst candidate (~10 M☉) needing higher-resolution follow-up.
- **FRB 20220529A:** Pandhi et al. 2026 (3.2-year CHIME monitoring) favour a young expanding supernova remnant. No paper proposing a lensing interpretation was found, so the glossary's "lens interpretation from some groups" is **unverified**.

**Effect on plan:** FRB 20190308C stays as a control (Sec. 7.1). Glossary Sec. 5 needs correcting on FRB 20220529A.

## Q4. How does CHIME search for lensing echoes? (Track A baseline)

- **Coherent:** dechannelise baseband voltages to 1.25 ns, compute the time-lag autocorrelation of the electric field, and look for a significant peak (interference fringe). Scintillation produced a false candidate that had to be ruled out (Kader et al. 2022). Decoherence from scattering screens is modelled with a two-screen model (Leung et al. 2022).
- **Incoherent / intensity:** autocorrelation of the intensity time series with simulation-calibrated thresholds (Chang et al. 2025; Krochek & Kovetz 2022, who also set a per-burst flux-ratio threshold).

**Effect on plan:** Track A baselines are intensity autocorrelation (Krochek; Chang) and, if baseband is used, comparison with the coherent method's published sensitivity. Scintillation is a known impostor to add to Phase 1 impostors.

## Other findings worth noting

- **H₀ (Sec. 5.2):** Wucknitz et al. 2021 show that with coherent methods, combining time delays with their *time derivatives* can remove the lens-model uncertainty. Our statement that the lens model always dominates should be softened.
- **Lensed repeaters (Track C):** the fixed delay pattern is the accepted test (Li et al. 2018), but confirmation also requires matching radio and optical image positions.
- **Yields:** Ho et al. 2023 forecast ~24 lensed FRBs per year out of ~1700 for BURSTT-2048; Connor & Ravi 2022 cover rates from µs to years.

## Corrections after full-text check (2026-11-04)

A review against the full texts found errors in this summary; the corrected versions are now in Project_Description.md and the glossary:
- **Q2 option 1 was wrong:** 0.1–100 M☉ is *not* a mass gap. Kader et al. 2022 searched 10⁻⁴–10⁴ M☉ (lags from ns to 100 ms) on the same baseband data. The real gap is sensitivity (Leung et al. reach only f ≲ 0.8 near 10⁻³ M☉), and the public release has 140 bursts versus their 172.
- **Q2 option 2 needs a condition:** Krochek & Kovetz's "a few times Catalog 1" assumes full instrument time resolution, so a ~1 ms Catalog 2 does not meet it.
- **Q1:** Zhang et al. 2026 use exactly our fusion (|f₁ − f₂| + element-wise product); novelty must rest on the FRB domain, nuisances, benchmark and ε→limit chain.
- **Not supported by the texts, and not used:** a Connor & Ravi claim about EROS/HSC above 10² M☉ (that comparison is in Ho et al. 2023); FRB 20150422A as the first localized repeater (it is FRB 20121102A, per general knowledge; verify with Chatterjee et al. 2017).
- **Reinstated after verification (2026-11-04, Kader full text):** the recovery threshold "χ² ≳ 40 and εΓ ≳ 0.03" **is** in Kader et al. 2022 (Fig. 8 caption; mean relative-magnification error ~23%) — usable as the coherent-baseline reference for Track A. Kader's own count is 172 events / **103** independent sightlines (Sec. III.A); "114 sightlines" is Leung et al.'s figure.

## Proposed changes to Project_Description.md (applied 2026-11-04, with the corrections above)

1. Track A priority: replace "f_CO limit from public Catalog 1 data" with one of the options under Q2 (recommend option 1 + 3).
2. Add scintillation as an impostor (Phase 1 step 5, Sec. 7.1 controls).
3. Soften Sec. 5.2: cite Wucknitz et al. 2021 on removing lens-model uncertainty with delay derivatives.
4. Sec. 6/8: cite Zhang et al. 2026 and Goyal et al. 2021 as Siamese/pair precedents; drop the unverified de Mello reference.
5. Glossary: fix FRB 20220529A wording; the "Kalra et al. 2022" citation was a misattribution and has been corrected to Krochek & Kovetz 2022.
