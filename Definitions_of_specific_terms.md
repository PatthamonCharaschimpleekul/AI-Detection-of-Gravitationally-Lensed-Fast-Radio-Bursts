# Definitions of Specific Terms

Background glossary for the research proposal **"AI Detection of Gravitationally Lensed Fast Radio Bursts"** (31 Oct 2026).
Every term is defined plainly, then tied to *why it matters in this project*. References with links are at the end.

---

## 1. Radio transients and FRBs

**Fast Radio Burst (FRB)** — A flash of radio emission lasting ~1 millisecond, released with an isotropic-equivalent energy of up to ~10³⁹–10⁴¹ erg — roughly what the Sun emits in days, compressed into a millisecond. Dispersion measures (below) show the pulses travelled billions of light-years, so FRBs are extragalactic. Discovered in 2007 (the "Lorimer burst"); thousands now known. *Our project: FRBs are the signals we search for lens copies of.*

**Dispersion Measure (DM)** — The column density of free electrons between source and observer, ∫n dl, in pc cm⁻³. Radio pulses travel slower through plasma at low frequency, so a burst arrives later at low ν; measuring this sweep gives DM. DM is distance-like (higher DM ⇒ farther, on average) but noisy because it depends on both host and Milky Way electron content. *Our project: DM values must be de-depended — two lensed images of the same burst share the source but (in principle) have identical DM, whereas different bursts rarely match.*

**Dynamic spectrum** — A burst's "picture": intensity as a function of time × frequency. FRBs show downward-drifting stripes from dispersion. Machine-learning detectors (including ours) treat these as images.

**Repeater vs one-off** — Some FRB sources emit many bursts over years (repeaters, e.g. FRB 20180916B and FRB 20201124A); most known sources have only ever shown one burst ("one-offs"), and in CHIME/FRB catalogs only a few percent of detected events belong to repeaters. **The central ambiguity of this project: a "repeat" is either intrinsic (the source fired again) or a lens echo (the same fire, arriving twice).**

**Scattering** — Multipath propagation through electron-density turbulence smears a pulse in time, with an exponentially decaying low-frequency tail. It mimics millisecond-scale delays and modifies waveform shape between two observations of the same source — one of the reasons cross-correlation struggles (Sec. 4).

**Magnetar** — A neutron star with a surface magnetic field ~10¹⁴–10¹⁵ G (a trillion times stronger than any lab magnet). In 2020 a magnetar in our own Galaxy (SGR 1935+2154) produced a radio burst essentially indistinguishable from cosmological FRBs, proving magnetars can power at least some FRBs. Leading model: starquakes / magnetic reconnection events in magnetars.

---

## 2. Gravitational lensing

**Gravitational lensing** — General relativity: mass curves spacetime, so light from a background source is bent by foreground mass. Light acts as a probe of *all* mass (dark matter included), which is why lensing is our tool for dark-matter questions.

**Strong lensing** — When the alignment is close enough (within the lens's Einstein radius, typically ~0.4–2″ for a galaxy-mass lens), the source appears as **two or more distinct images** (or arcs/rings). The classic examples are Einstein crosses and lensed quasars like HE 0435−1223. *Our FRB case: a foreground galaxy splits one burst into 2–4 "echoes".*

**Time delay** — The arrival-time difference between images, from two effects: (1) geometric path length differences and (2) Shapiro delay (light climbing out of the lens potential well). For **galaxy-mass lenses the delays are days to months**; for **stellar-mass or lighter compact objects, µs–ms**. Crucially, Δt is a property of the *lens and cosmometry*, not of the source — it is **achromatic** (the same at all frequencies) and does not reshape the pulse.

**Lens echo** — A multiply-imaged arrival of one physical event. Detecting a lens echo in an FRB means finding two bursts whose intrinsic waveform is the same to within noise, separated by an achromatic delay.

**Magnification (µ)** — Each image is brightened/faded by the lens (flux ratio set by the mass model, not the source). So two echoes have *different fluences* but *identical morphology* — another discriminator against intrinsically identical repeats? (careful: an intrinsic repeater could also produce similar fluences; see Sec. 6.)

**Microlensing / compact-object lensing** — Lensing by individual stars or compact dark clumps along the line of sight. Delays are sub-ms to ms, so it shows up as microsecond/millisecond "echoes" — the BURSTT-style frontier. Non-detections of such echoes constrain how much dark matter can be in compact form (Sec. 3).

**Plasma lensing** — Refraction by dense free-electron clumps (in the host, or circum-magnetar plasma). It also repeats/brightens bursts (observed in FRB 20201124A), but is **chromatic** (delay and brightening vary strongly with frequency), unlike gravity. *Our classifier must not confuse plasma lensing with gravitational lensing — the frequency-dependence is the tell.*

**Einstein radius (θ_E)** — Angular scale of a lens, θ_E ∝ √(M/D). Sets the alignment tolerance and roughly the image separation.

**Optical depth to strong lensing (τ)** — The probability that a random background source is multiply imaged by intervening galaxies, ≈ 10⁻³–10⁻² for galaxy lenses at FRB redshifts. The entire expected-yield calculation of this project is τ × (number of FRBs).

---

## 3. Cosmology

**Hubble constant (H₀)** — The present expansion rate of the universe (km s⁻¹ Mpc⁻¹). Measuring it precisely is the "final word" problem of cosmology.

**Hubble tension** — Early-universe inference (Planck CMB + ΛCDM): H₀ = 67.4 ± 0.5. Late-universe measurements — distance ladder (SH0ES ≈ 73) and **lensed-quasar time-delay cosmography** (H0LiCOW: 73.3 (+1.7/−1.8), 2.4%) — disagree with it at ~4–5σ. This is the puzzle our lensed-FRB H₀ measurement addresses.

**Time-delay cosmography** — Measure Δt between lensed images + model the lens mass ⇒ infer the time-delay distance DΔt ⇒ H₀ in one step, no cosmic distance ladder. Proven with ~40 quasars (H0LiCOW/TDCOSMO, 2.4%); FRBs add *precision* bursts because pulse waveforms allow far cleaner alignment of images than fuzzy quasar light curves (Li et al. 2018 projected ~1% H₀ from ~10 lensed repeaters with SKA-era data; our proposal asks what N lensed FRBs buy today).

**Dark matter** — Non-luminous mass (~85% of matter) inferred from galaxy rotation, lensing, CMB, structure formation. Its particle nature is unknown.

**Compact dark matter / primordial black holes (PBHs)** — One candidate: dark matter made of black holes (or other compact objects) formed in the early universe, spanning many masses. Microlensing/echo searches with FRBs directly constrain the PBH fraction f_PBH: Kalra et al. (2022) used the *absence* of sub-ms repeats in CHIME Catalog 1; Ho et al. (2023) forecasted constraints for future surveys (BURSTT). **Our null-result question:** if we find no ms-echoes, what does that rule out?

**Redshift (z)** — Cosmological stretch of light; z = 1 means the universe was half its current size when the light left.

---

## 4. Machine learning

**Siamese neural network** — Two inputs (here: two bursts' dynamic spectra) pass through **identical, weight-shared** encoders g(·) that map each to a vector (embedding); the network is trained so that paired lens echoes embed *close together* and unrelated bursts *far apart* (contrastive / triplet loss). It outputs a learned similarity score rather than a hand-picked one.

**Embedding / metric learning** — A low-dimensional learned representation where distances mean physical similarity.

**Contrastive loss** — Pulls same-pair embeddings together, pushes different-pair ones apart up to a margin; the standard training objective for a Siamese net.

**Cross-correlation (our baseline)** — Slide one waveform against another, integrating the product; optimal for *identical* signals differing only by shift + stationary additive noise. Weaknesses that a learned metric can beat: differing DMs (before/during dedispersion), scattering tails, scintillation, sub-sample delays, magnification-modified shapes. Prior art: auto-correlation searches of FRB data for echoes (e.g., high-time-resolution CHIME searches); a Caltech undergraduate study (de Mello, mentor C. Law) and an AAS abstract already tested Siamese-style pair comparison on simulated lensed FRBs — so the idea has *some* pedigree but **no mature peer-reviewed benchmark ⇒ our novelty space**.

**CNN (convolutional neural network)** — The usual encoder inside a Siamese net for image-like inputs (dynamic spectra).

**Precision / recall / ROC / false-alarm rate (FAR)** — With lensed pairs intrinsically rare (τ ~ 10⁻³), even 1% FAR drowns the few dozen real pairs. So: report FAR (e.g. at fixed recall) and precision at expected base rate, not accuracy. Class-imbalance handling (balanced loss, hard-negative mining) is mandatory.

**Simulation / data augmentation** — Because confirmed lensed FRBs are (currently) absent, training labels must be synthetic: simulate an FRB population matching CHIME/FRB Catalog 1 statistics (rate, DM, energy, spectral shape), inject lensing (pairs with delays µs→months, magnifications), re-add realistic noise/dispersion/scattering. The science then hinges on how honest the simulation is — every mismatch is a bias in Q1–Q3.

---

## 5. Instruments and data

**CHIME** — Canadian Hydrogen Intensity Mapping Experiment: a drifting-scope radio telescope (400–800 MHz) whose FRB backend detects roughly one FRB per day. Its public catalogs are the backbone of this project.

**CHIME/FRB Catalog 1** — 536 bursts (Jul 2018 – Jul 2019), of which **62 bursts from 18 repeaters**; fully public, includes DMs and basic burst properties. Our simulation target. (A 2nd catalog, 4539 bursts incl. 83 repeaters, appeared in 2026 — worth recalibrating to it if available at run time.)

**Westerbork (WSRT) and host-galaxy follow-up** — High-sensitivity arrays used to localize and monitor repeaters.

**Case study — FRB 20220529A**: the first repeating FRB localized to a host (z ≈ 0.9, spiral galaxy; CHIME-led work, 2025). Its burst regularities attracted a **gravitational-lens interpretation** from some groups, while a 2026 CHIME+Westerbork monitoring result (steadily declining DM, depolarization) favours an **expanding-nebula environment** instead. *Unresolved → this is precisely the discrimination our model automates.*

---

## 6. Scientific backing for the three research questions

**Q1 — How many lensed FRBs should a CHIME-like survey detect per year?**
Building blocks: galaxy strong-lensing optical depth τ ≈ 0.3–1% of high-z sources; CHIME detects ~500–1000 FRBs/yr; a fraction are at z ≳ 0.5 where τ peaks; repeater echoes boost event counts by (µ₁+µ₂)… Estimates in the literature: a handful of strongly lensed FRBs per year at most for current all-sky instruments (Connor et al. 2023 worked out rates across delay scales µs–yr; Ho et al. 2023 computed τ for each Catalog-1 FRB; Li et al. 2018 projected ~10 lensed *repeaters* over a decade+ with SKA). Chang et al. (2025) already report **one lensed candidate found hiding in CHIME Catalog 1** — the per-year scale of the answer is therefore plausibly ~1–5 for galaxy lenses, with dedicated high-time-resolution analyses adding the ms-scale compact-object population. *Our answer refines that with the repeater-echo term and a realistic detection pipeline.*

**Q2 — Can a Siamese network beat cross-correlation?**
Support for trying: cross-correlation's failure modes are documented (different DMs/scattering between echoes; plasma-lensing impostors). Siamese/contrastive pair models dominate other "same-object, changed-presentation" tasks (image retrieval, face verification, lensed-quasar pair mining). Direct precedent for FRB pairs is thin (Caltech de Mello/Law study; AAS-235 abstract) ⇒ well-motivated, low-crowding methodological niche. The honest test: identical simulated truth sets, metrics = recall at fixed FAR on (a) echo vs intrinsic-repeat discrimination and (b) lensed vs plasma-lensed discrimination.

**Q3 — Cosmology yield and the meaning of a null result?**
With ~N lensed FRBs (delay + host DM + (future) lens imaging): H₀ precision scales ~1/√N; Li et al. 2018 argued ~1% is reachable with ~10 well-modelled systems; even 5% would be an independent late-universe datapoint bearing directly on the Hubble tension (H0LiCOW 73.3 vs Planck 67.4). A **null result** is also publishable physics: absence of ms-µs echoes in a sample of K FRBs constrains the compact-dark-matter fraction f_PBH(M) (precedent: Kalra et al. 2022 on Catalog 1; Ho et al. 2023 forecasts) and caps τ, testing small-scale structure predictions.

---

## 7. Pitfalls the reader should keep in mind

1. **Echo ≠ identical-looking bursts.** Intrinsic repeaters can look similar by chance; lensed images differ in magnification and (slightly) scattering geometry. The discriminator is *jointly* achromatic fixed delay + waveform identity beyond noise + plausible DM equality — hence a learned metric over raw pairs.
2. **Plasma lensing is chromatic; gravity is not.**
3. **Simulation realism sets everything.** Bias in the assumed FRB population or lens model propagates straight into Q1–Q3.
4. **Base rates are tiny** (τ ~ 10⁻³): false-alarm control, not raw accuracy, is the headline number.
5. **One published lensed candidate (Chang et al. 2025) and one contested repeater (FRB 20220529A)** mean the field is live — good timing, but verify current status before writing any proposal text (see Sec. 5).

---

## References

- The First CHIME/FRB Fast Radio Burst Catalog — [arXiv:2106.04352](https://arxiv.org/abs/2106.04352)
- Updating the first CHIME/FRB catalog — [arXiv:2311.00111](https://arxiv.org/abs/2311.00111); CHIME/FRB second catalog: [IOP](https://iopscience.iop.org/article/10.3847/1538-4365/ae3828), one-off vs repeater subpopulations: [arXiv:2610.18710](https://arxiv.org/html/2610.18710v1)
- CHIME/FRB open data: [chime-frb.ca](https://chime-frb.ca/)
- Li et al. 2018, Strongly lensed repeating FRBs as precision cosmological probes — [arXiv:1708.06357](https://arxiv.org/abs/1708.06357), [Nat. Commun.](https://www.nature.com/articles/s41467-018-06303-0)
- Connor et al. 2023, Stellar prospects for FRB gravitational lensing — [arXiv:2206.14310](https://arxiv.org/html/2206.14310v1)
- Ho et al. 2023, Future constraints on dark matter with lensed FRBs (BURSTT) — [arXiv:2304.04990](https://arxiv.org/html/2304.04990v1), [ApJ](https://iopscience.iop.org/article/10.3847/1538-4357/accb9e)
- Kalra et al. 2022, Constraining PBH dark matter with CHIME — [ADS](https://ui.adsabs.harvard.edu/abs/2022PhRvD.105j3528K)
- Chang et al. 2025, A lensed FRB candidate in the first CHIME/FRB Catalogue — [MNRAS-L](https://academic.oup.com/mnrasl/article/537/1/L61/7922865)
- Pastor-Marazuela et al. 2025, FRBs & the radio perspective on multi-messenger lensing (review) — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11982924/)
- Wong et al. 2020 (H0LiCOW XIII), 2.4% H₀ from lensed quasars — [MNRAS](https://academic.oup.com/mnras/article/498/1/1420/5849454); TDCOSMO XXIII (2026) — [A&A](https://www.aanda.org/articles/aa/full_html/2026/02/aa56411-25/aa56411-25.html)
- Pandhi et al. 2026, A steadily declining DM for FRB 20220529A (expanding nebula) — [arXiv:2602.22309](https://arxiv.org/abs/2602.22309), [ApJ-L](https://iopscience.iop.org/article/10.3847/2041-8213/ae52f8)
- de Mello (Caltech SFP/CURJ), Siamese networks for FRB pair similarity — [CURJ](https://curj.caltech.edu/2021-06-26/are-all-fast-radio-bursts-the-same/)
- Sky at Night explainer on FRB lensing — [link](https://www.skyatnightmagazine.com/space-science/fast-radio-bursts-gravitational-lensing)

*Status: glossary compiled 1 Nov 2026 from the sources above. Verify claims marked "proposed/contested" against the live literature before quoting in the proposal.*
