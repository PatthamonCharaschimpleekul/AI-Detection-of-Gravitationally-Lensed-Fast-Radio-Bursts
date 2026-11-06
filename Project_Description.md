# Project Description — AI Detection of Gravitationally Lensed Fast Radio Bursts

Detailed project plan for the research proposal of 31 Oct 2026, revised 4 Nov 2026 to a single paper.
Technical terms are defined in [Definitions_of_specific_terms.md](Definitions_of_specific_terms.md); this file explains *what* we will do, *why*, and *how we will know it worked*.

**Working title:** *A Siamese network for identifying gravitationally lensed repeating fast radio bursts: benchmark, search of CHIME/FRB Catalog 2 repeaters, and forecasts for all-sky monitors.* Target journal: MNRAS.

---

## 1. One-paragraph summary

Some fast radio bursts (FRBs), plausibly powered by magnetars, pass a foreground galaxy on their way to Earth and are **gravitationally lensed**: every burst arrives two or more times, separated by a fixed delay of days to months. The obstacle is that **many FRBs repeat on their own**, so a second, similar burst from the same position is ambiguous. For a *repeating* source that is lensed, both images keep firing, so its burst list contains pairs that are copies of each other — same intrinsic shape, same delay, same flux ratio. We will build semi-synthetic lensed repeaters from real CHIME bursts, train a model built around a **weight-shared (Siamese) encoder** to tell lensed copies from intrinsic repeats, combine it with a timing test for a constant delay and flux ratio, benchmark both honestly against cross-correlation and physics baselines, search all public CHIME/FRB Catalog 2 repeaters, and forecast what all-sky monitors such as BURSTT will find.

---

## 2. Where the idea came from, and why it was reframed

### 2.1 The original wish
Use FRBs from magnetars to find "the edge of the universe" — how big the universe is.

### 2.2 Why that exact goal is not feasible
- **The "edge" is not an object we can detect.** The observable universe is bounded by the *particle horizon* (~46 billion light-years comoving radius), which is set by the age and expansion history of the universe, not by anything that emits signals. No source, FRB or otherwise, sits "at the edge".
- **FRBs are not seen that far.** Known FRBs reach redshift z ≈ 1 (a few candidates higher — verify current record before quoting). The cosmic microwave background, at z ≈ 1100, is already the farthest light we can see; FRBs are far closer.
- **Magnetar origin does not add distance information.** Knowing the engine is a magnetar tells us about the source physics, not about the size of the universe.

### 2.3 The feasible version of the same question
"How big is the universe?" in practice means **"how fast is it expanding?"** — the Hubble constant H₀, which sets the scale and age of the universe. Lensed repeating FRBs are one of the cleanest future routes to H₀ (Li et al. 2018; Wucknitz et al. 2021), but only once lensed repeaters can be *found*. This project builds and tests the finder.

| Original wish | Feasible proxy | How this project helps |
|---|---|---|
| Size / edge of universe | Expansion rate H₀ | Finds lensed repeaters, the systems needed for H₀ (H₀ itself is discussion only) |
| Bending of light | Galaxy-scale gravitational lensing | Lensed-copy identification is the core task |
| Use magnetar FRBs | Keep FRBs as the signal | Magnetars power at least some FRBs (SGR 1935+2154, 2020) |

An alternative closer to the original wish: the **DM–redshift (Macquart) relation** of FRBs with identified host galaxies measures H₀ directly from existing data. AI plays a smaller role there, which is why this project uses lensing instead.

---

## 3. Research questions

1. **Discrimination.** Can a model built on a Siamese (weight-shared) encoder separate lensed copies from intrinsic repeat bursts of the same source better than cross-correlation and physics- or feature-based baselines, *under realistic propagation and instrumental effects at CHIME resolution*?
2. **Search.** Combining pair scores with a timing test (constant delay and flux ratio), is any CHIME/FRB Catalog 2 repeater consistent with being gravitationally lensed? If none, what can be said given CHIME's exposure?
3. **Forecast.** How many lensed repeaters should CHIME-like transit surveys and coherent all-sky monitors (BURSTT-like) identify with this method?

> RQ1 is written so that "better than cross-correlation" is the test, not "Siamese wins". If a simpler method wins, that is a result too (see Sec. 6).

**Out of scope:** compact-object (µs–ms) lensing and dark-matter limits, which the CHIME collaboration already addresses with baseband data (Kader et al. 2022; Leung et al. 2022); one-off FRBs lensed by galaxies (see Sec. 4.1); measuring H₀ (discussion only, Sec. 5.2).

---

## 4. The physics that makes discrimination possible

A lensed echo is **the same emission event seen twice**. An intrinsic repeat is **a new event from the same source**. That difference shows up in several measurable places:

| Property | Lensed copy pair | Intrinsic repeat pair | Caveat |
|---|---|---|---|
| Intrinsic waveform (sub-burst structure, drift, spectral shape) | Identical up to noise | Different (bursts vary) | Repeater bursts are often several ms wide and narrow-band, so structure is partly resolved at ~1 ms |
| Flux ratio | Set by lens magnification μ, **the same for every pair** | Random | Repeaters can have similar fluences by chance |
| Time delay | Achromatic, **the same for every pair** | No fixed delay | Plasma lensing gives *chromatic* delays — an impostor |
| DM | Almost equal (small Δ from different paths through the lens galaxy) | Equal at first, may drift over months (e.g. FRB 20220529A) | Both pass through the same host |
| RM, scattering, scintillation | Slightly different (different sightlines) | Can drift with time | Simulation must include this |

Where the distortion between copies comes from:
- **Gravity does not distort the burst.** Gravitational lensing is achromatic and leaves the waveform shape unchanged; it only shifts arrival time and scales brightness.
- **Plasma does.** Each image takes a different path through the lens galaxy's gas, so it picks up slightly different scattering, scintillation, DM and RM.
- **Dispersion is a small effect.** Each burst is dedispersed at its own DM, and ΔDM between images is tiny.

Key consequences for the design:
- **Do not simulate perfect copies.** Exact scaled copies make any model look perfect on simulation and fail on real data. Propagation differences must be in the training data.
- **The hard negatives are similar-looking repeats** from the same source in the same activity window, not random unrelated bursts.
- **Morphology and timing are complementary.** Each pair is weak evidence on its own; many pairs sharing one delay and one flux ratio are strong evidence.

### 4.1 Why repeaters, not one-offs: the transit problem

A transit telescope sees each source only while it crosses the beam (minutes per day). A second image arriving later than that but within a day is never seen; for delays longer than a day the chance it lands in the beam is roughly the beam's east–west width over 2π, ~10⁻². Connor & Ravi 2022 conclude that CHIME *"will not see strong lensing by foreground galaxies"* from one-off pairs.

A lensed **repeater** escapes most of this: both image streams keep firing, so every transit can catch bursts from both, and over years of exposure some bursts *and their copies* are both recorded. The number of recorded copy pairs depends on the source's burst rate, the delay and CHIME's exposure history, all of which the simulation models (Phase 1, step 4).

---

## 5. Pipeline

Two complementary parts, combined at the source level:

- **Track B — pair morphology.** Task: "is burst j a lensed copy of burst i of the same source?" ← the Siamese model lives here.
- **Track C — source timing.** Task: "does this source's burst list contain many pairs with one shared delay and one shared flux ratio?"

### Phase 1 — Semi-synthetic lensed repeaters: real bursts, simulated lensing
**Goal:** use real data everywhere it exists, and simulate only what has never been observed — the lensing itself.

No confirmed lensed FRB exists yet (only the unconfirmed FRB 20190308C candidate, Chang et al. 2025), so lensed positives cannot come from a dataset. Everything else can:

| Ingredient | Source |
|---|---|
| Burst templates and repeater burst lists | CHIME/FRB Catalog 2 dynamic spectra (0.983 ms, 400–800 MHz) and table: 981 bursts from 83 repeaters ([DOI 10.11570/25.0066](https://doi.org/10.11570/25.0066)) |
| **Intrinsic-repeat negatives** | The real Catalog 2 repeater burst lists; larger samples (FAST bursts of FRB 20121102A, Blinkverse) only for training augmentation |
| Noise and RFI | Real off-pulse regions of the same dynamic spectra |
| Exposure (when CHIME was watching each position) | Catalog 2 exposure file (`chimefrbcat2_exposure.h5`, 206 MB) |
| **Lensed positives** | Simulated: each burst of a real repeater copied with delay Δt, flux ratio μ_B/μ_A and independent propagation effects, injected onto real noise |

Steps:
1. **Lens population.** Singular isothermal sphere / SIE galaxy lenses with optical depth τ(z_s); output image count, delays Δt (hours–months) and magnifications. Source redshift from DM (Macquart relation + host and Milky Way contributions, with scatter).
2. **Lensed repeater construction.** Take a real repeater's burst list as image A. Image B = every burst of A delayed by Δt and scaled by the flux ratio. The observed source is the union of both streams.
3. **Per-image propagation differences:** ΔDM, ΔRM, different scattering time and scintillation pattern.
4. **Observation.** Keep only bursts (from either image) that arrive while CHIME's exposure covers the position *and* pass the detection threshold after magnification. This applies the transit selection of Sec. 4.1 burst by burst.
5. **Impostors (cross-file pairs only; [plan 2026-11-05_1925](plan/2026-11-05_1925_impostor-pairs.md)).** An impostor is a pair of *different* bursts from one source that share a propagation imprint, so they look like one burst seen twice:
   - **I1:** a shared spectral envelope, as from a host plasma-lens caustic lasting hours to days;
   - **I2:** a shared diffractive-scintillation pattern, for repeats closer than the scintillation time.

   Plasma-lensing echoes within one burst, multi-component bursts and the µs-scale scintillation candidates of Kader et al. 2022 are within-file effects. They are outside Track B, which compares bursts hours to months apart.
6. Fully synthetic bursts (parametric pulse models) only as a control set, to check that results do not depend on the particular real templates.

Caution: FAST data are at ~1.25 GHz, CHIME at 400–800 MHz. FAST bursts are rescaled to the CHIME band and resolution and used only for augmentation; every headline result is on CHIME data.

### Phase 2 — Injection and labelling
**Goal:** model-ready data with honest labels.

1. Inject lensed copies into dynamic spectra at CHIME resolution on **real off-pulse data and RFI**; Gaussian noise only as a control.
2. Labels:
   - pairs: `lensed copy` / `intrinsic repeat` / `unrelated` (different sources) / `impostor`
   - sources: `lensed repeater` / `unlensed repeater`
3. **Split by source, not by pair**, into train / validation / test, so no source appears in more than one split.
4. Keep a separate "realism stress test" set with nuisance parameters wider than in training.

### Phase 3 — Model design
See Sec. 6. Summary:
- Pair level: **Siamese encoder with feature-map fusion** (primary), a cross-attention variant, plus a classic Siamese and a 2-channel CNN as ablations; trained with physics-based augmentation and hard negatives.
- Source level: a timing likelihood test for a shared delay and flux ratio, weighted by the pair scores.

### Phase 4 — Training, validation, benchmarking
**Goal:** show whether learning helps, and by how much.

Methods compared on identical test sets (Sec. 6.3). Metrics in Sec. 7. The outputs that matter downstream are the **source-level detection efficiency ε(Δt, μ, burst rate, exposure)** and the **false-alarm rate per repeater**.

### Phase 5 — Search and forecasts

#### 5.1 Expected yield (RQ3)

$$
N_{\text{exp}} = \sum_k \int \frac{d\tau_k}{d\Delta t}\,\varepsilon_k(\Delta t)\,d\Delta t
$$

summed over repeaters k, where dτ_k/dΔt is the probability that repeater k is lensed with delay Δt and ε_k is the source-level detection efficiency from Phase 4. ε_k already includes the exposure selection (Phase 1, step 4). For one-off bursts the equivalent selection is Connor & Ravi 2022, Eq. 7:

$$
P_{\text{FoV}}(\Delta t) =
\begin{cases}
1 & \Delta t < t_{\text{trans}} \\
0 & t_{\text{trans}} < \Delta t < 1\ \text{day} \\
\theta_{\text{EW}} / 2\pi & \Delta t > 1\ \text{day}
\end{cases}
$$

The forecast is computed for (a) CHIME as observed (Catalog 2 exposure), (b) a CHIME-like survey run longer, and (c) a coherent all-sky monitor (BURSTT-like, P_FoV ≈ 1 up to the survey length).

With τ ~ 10⁻³ and 83 repeaters, N_exp for Catalog 2 is expected to be ≪ 1. A null search result is therefore **expected**, and the paper presents it as a demonstration and a check of the false-alarm rate, not as a strong constraint.

#### 5.2 H₀ (discussion only)
The delay between images i and j is

$$
\Delta t_{ij} = \frac{D_{\Delta t}}{c}\,\Delta\phi_{ij},
\qquad
D_{\Delta t} = (1+z_l)\frac{D_l D_s}{D_{ls}} \;\propto\; \frac{1}{H_0}
$$

where Δφ_ij comes from the lens mass model. FRB delays are measured almost perfectly, so the lens model (~5–10% per system today, plus the mass-sheet degeneracy) dominates; Li et al. 2018 still budget ~0.8% for mass modelling and ~2% for line-of-sight structure even with HST imaging. Coherent timing of a lensed repeater over years can remove the lens-model uncertainty using the delay's time derivative (Wucknitz et al. 2021), at the cost of ns–µs timing and sub-mas astrometry. Measuring H₀ also needs image positions, lens imaging and redshifts, all outside this project; the paper states how many lensed repeaters a BURSTT-like survey would supply.

---

## 6. Model design and the Siamese question

### 6.1 What a classic Siamese network does
Two inputs pass through **the same encoder (shared weights)**, each is compressed to a vector (embedding), and a distance between the two vectors decides "same or different". Trained with contrastive or triplet loss.

### 6.2 Is it the right tool here? Honest assessment

**What fits:**
- Weight sharing is exactly right: both bursts should be processed by the same feature extractor, and the answer should not depend on which burst is called A or B.
- Learned similarity can absorb nuisance effects (scattering, scintillation, RFI) that break cross-correlation.

**What does not fit:**
- **Late fusion loses information.** Classic Siamese compares the two bursts only after each is squashed to a vector. "Is B a scaled copy of A?" depends on point-by-point time–frequency detail that is gone by then.
- **Cross-correlation is close to optimal in the ideal case.** If B = μ·A + Gaussian noise, a matched filter is the best possible test. A learned model can only win through realistic nuisances.
- **Limited structure in the data.** At ~1 ms resolution some bursts are barely resolved, so there is less internal structure for a deep network to exploit.

### 6.3 Decision: keep the Siamese encoder, fix the fusion

**Primary model: Siamese encoder with feature-map fusion.**
- Shared-weight CNN encoder g(·) applied to burst A and burst B.
- Combine the **intermediate feature maps**: |g(A) − g(B)|, g(A)·g(B), and optionally a cross-correlation layer between them.
- A small classification head outputs P(lensed copy), P(intrinsic repeat), P(unrelated).
- Image-only input, no scalars: data are Stokes I (no RM), time separation is not simulated, and flux ratio is uninformative in Track B by design. Flux-ratio and timing consistency belong to Track C ([plan 2026-11-06_1223](plan/2026-11-06_1223_phase3-trackB-benchmark.md)).
- Loss: cross-entropy (class-weighted for the rare `lensed copy` class), optionally plus a contrastive term on the embeddings.

**Prior art and what is new.** The same fusion — a shared encoder with |f₁ − f₂| and element-wise product — was used for lensed gravitational-wave pairs by Zhang et al. 2026, and Goyal et al. 2021 screened lensed GW pairs with DenseNet/XGBoost. The novelty here is therefore **not** the fusion design but:
- the FRB domain and lensed *repeaters*;
- per-image propagation nuisances (scattering, scintillation, ΔDM, ΔRM) built into training;
- exposure-aware construction of lensed repeaters from real CHIME data;
- combining pair morphology with source timing;
- the benchmark ladder against physics baselines, and a search of real data.

The literature search of 2026-11-03 (abstract level) found no ML lensed-pair classifier for FRBs.

**Tolerance to propagation effects comes from the data, not from a special loss.** Lensed positive pairs are built with **physics-based augmentation**: each image independently gets its own scattering time, scintillation pattern, small ΔDM and ΔRM, and RFI, so the model learns which differences are "same burst, different path".

**Hard negatives drive training.** Intrinsic repeats from the same source in the same activity window, chosen to look as similar as possible, are oversampled.

**Benchmark ladder** — all methods on the same test set; the simplest method that works is the recommendation:

| # | Method | Role |
|---|---|---|
| 1 | Cross-correlation / matched filter | Traditional baseline |
| 2 | Physics likelihood ratio: fit B = μ·A ⊗ scattering kernel vs "independent burst" | Strongest non-ML baseline |
| 3 | Gradient-boosted trees on features (ΔDM, ΔRM, width, drift rate, spectral index, bandwidth, flux ratio) | Interpretable baseline |
| 4 | 2-channel CNN (A and B stacked, early fusion) | Ablation: no weight sharing |
| 5 | Classic Siamese (vector embedding + distance) | Ablation: late fusion |
| 6 | **Siamese encoder + feature-map fusion** | Primary model |
| 7 | Siamese encoder + cross-attention: time–frequency patches of A attend to patches of B | Alternative fusion |

**Source-level combination (Track C).** For each repeater and each trial delay Δt, collect pairs (i, j) with t_j − t_i ≈ Δt. Score the hypothesis "lensed with delay Δt and flux ratio r" by a likelihood that uses (a) how many pairs line up at that Δt given the exposure, (b) the consistency of their flux ratios with one r, and (c) each pair's morphology score from the pair model. The background distribution comes from time-scrambled burst lists of the same source. Every pair-level method in the ladder can feed this step, so the benchmark is also reported at source level. A set Transformer over a source's bursts is an optional comparison, kept only if it beats the likelihood.

**Why not a long time-series Transformer over the days–months gap:** nothing is recorded between bursts — CHIME stores only a short window around each trigger. The separation is a scalar input; attention is used *within* a pair (model 7).

**Reference limit.** With random nuisances the exact likelihood ratio cannot be computed, so we report how close each method gets to two approximations: the likelihood ratio under a simplified model with nuisances fixed or analytically marginalised, and a neural likelihood-ratio estimate (simulation-based inference) trained on the full simulator. Neither is a true optimum, and the paper says so.

**Base rate (Bayes prior).** A model score is not the probability of lensing. With τ ~ 10⁻³, even a strong classifier gives a low posterior. Candidates are reported as posterior odds = likelihood ratio × prior odds from τ.

**Final decisions combine evidence, not one model.** A candidate also needs: consistency with one Δt and one flux ratio across pairs (Track C); continued monitoring; and, eventually, imaging of a foreground lens galaxy.

**Deployment as a cascade.** Cross-correlation / likelihood ratio (1–2) runs first on every pair; only ambiguous pairs go to the learned model. Goyal et al. 2021 used ML the same way for lensed GW pairs: seconds per pair, versus hours to days for a full Bayesian comparison.

Possible outcomes and what each means:
- **6 or 7 beats 1–5:** the Siamese design is justified; the comparison with 5 shows why fusion matters.
- **2 or 3 matches 6:** physics already captures the signal at CHIME resolution; the paper is a systematic benchmark plus a search and forecast. Still publishable.
- **Everything fails on the stress-test set:** the simulation is too optimistic or CHIME resolution is too coarse — the forecast becomes "current data are not enough; this is what is needed", which is also a result.

---

## 7. Evaluation

Lensed events are rare (τ ~ 10⁻³), so accuracy is meaningless — a model that always says "not lensed" is 99.9% accurate.

Report instead, at both pair and source level:
- **ROC and precision–recall curves**, and **recall at very low false-positive rate**.
- **Expected false lensing claims per repeater and per survey-year** at the chosen threshold — the headline number.
- **Detection efficiency ε(Δt, μ, burst rate, exposure)** as a function, not a single number; Sec. 5.1 needs it.
- **Gain over cross-correlation as a function of S/N.** We expect little or no gain at high S/N; the case for the learned model rests on the low-S/N and strongly scattered regime.
- **Distance to the reference limit** (Sec. 6.3).
- **Calibration** of predicted probabilities (reliability diagram).
- **Robustness:** stress-test set with wider nuisances; Gaussian vs real noise backgrounds.
- **Impostor rejection:** how often impostor pairs (shared plasma-lens envelope or shared scintillation, Phase 1 step 5) are called lensed copies.

### 7.1 Validating the search: "no lens" vs "we missed it"

A non-detection only means something if we can show the pipeline would have found a lensed repeater that was there. Checks:

1. **Injection–recovery.** Turn real Catalog 2 repeaters into lensed ones (Phase 1, steps 2–4) with known Δt and flux ratio, run the full pipeline, and measure ε. This ε is the one in Sec. 5.1.
2. **Blind injections.** A script (or a teammate) converts an unknown number of real repeaters into lensed ones and seals the answer key; we search, then unseal.
3. **False-alarm rate from real data.** Time-scrambled burst lists and cross-source pairs give the real background.
4. **Controls.** Must flag or explain: the FRB 20190308C candidate (Chang et al. 2025). Must reject: real repeat pairs of the plasma-lensing candidate FRB 20201124A, and impostor pairs. (Multi-component bursts cannot form a cross-file pair, so they are not a Track B control.) Baselines and learned models must agree; disagreements are investigated before any conclusion.
5. **Expected count before searching.** Compute N_exp for Catalog 2 first (Sec. 5.1), so the reader knows a null was expected.
6. **Injection realism.** Too-clean injections inflate ε, so injections span several distortion levels and results are reported as a range.
7. **Blind analysis protocol.** Pipeline, thresholds and priors are fixed using simulations, off-pulse data and blind injections only. That version is tagged in git (e.g. `unblind-v1`) and only then run on the real Catalog 2 repeaters. Any change after unblinding is reported separately with its reason. Before the tag, real data enter only as cross-source pairs (true negatives by construction) and as blind same-source histograms with the top 1% hidden. Earlier uses of real same-source pair statistics during template validation are disclosed in the paper (list in [plan 2026-11-06_1223](plan/2026-11-06_1223_phase3-trackB-benchmark.md)).
8. **Reproducibility.** Data versions are recorded (Catalog 2 DOI 10.11570/25.0066), random seeds are fixed and logged, and code plus derived data products are released with a Zenodo DOI at submission.

| Injections recovered? | Real detection? | Meaning |
|---|---|---|
| Yes (high ε) | No | No lensed repeaters in that range (expected, Sec. 5.1) |
| No (low ε) | No | Pipeline or data not sensitive → no conclusion |
| Yes | Yes | Candidate → compare with false-alarm rate, follow up |
| No | Yes | Suspicious, likely artefact → investigate |

---

## 8. Risks and mitigations

| Risk | Effect | Mitigation |
|---|---|---|
| Simulation too clean | Model learns shortcuts, fails on real data | Semi-synthetic data (real bursts, real repeats, real noise, real exposure), per-image propagation differences, stress-test set |
| Telescope domain mismatch (FAST vs CHIME) | Model learns telescope, not physics | FAST used only for augmentation, rescaled to CHIME; headline results CHIME-only. Related: Zhang et al. 2026 report accuracy falling from ~96% to ~84% between detector noise models (different noise levels, not a clean shift test) |
| Data leakage | Over-optimistic scores | Split by source |
| Class imbalance | Misleading metrics | FPR-based metrics and false claims per repeater |
| Similar-looking intrinsic repeats | High false-positive rate | Hard-negative mining, timing consistency (Track C), Bayes prior from τ |
| Lensed and repeat pairs indistinguishable at ~1 ms | Morphology alone fails | Measure reference limits first; rely more on timing; report what higher resolution would add |
| Few recorded copy pairs per source because of transit exposure | Low ε for low-rate repeaters | Model exposure explicitly; report ε versus burst rate; forecast for all-sky monitors |
| Expected yield in Catalog 2 ≪ 1 | "No result" | Stated before the search (Sec. 7.1, step 5); the paper's value is the method, the validated search and the forecast |
| Model beaten by baselines | "AI not needed" | Framed as a benchmark in RQ1; still publishable |
| Prior work already did this | Lower novelty | Same fusion exists for lensed GW pairs (Zhang et al. 2026): claim novelty on FRB lensed repeaters, nuisances, exposure, timing combination and real search; re-check for an FRB ML lensed-pair classifier before submission |

---

## 9. Timeline (~6 months)

| Month | Work | Milestone |
|---|---|---|
| 1 | Literature check (done); download Catalog 2 repeater dynamic spectra (~10 MB each, ~10 GB), table and exposure; data inspection | Repeater dataset and exposure loaded and documented |
| 2 | Lens population; lensed-repeater constructor with exposure; propagation effects; impostors; injection | Datasets frozen and versioned; N_exp for Catalog 2 computed |
| 3 | Baselines 1–3 at pair level; timing likelihood (Track C) | First pair- and source-level ε on simulation |
| 4 | Siamese models (6, 7, 5) and 2-channel CNN (4); ablations; reference likelihood ratios | Benchmark table |
| 5 | Injection–recovery on real repeaters; false-alarm rate; blind injections; freeze, tag and unblind | Search result on 83 repeaters |
| 6 | Forecasts (CHIME as observed, longer CHIME-like, BURSTT-like); write-up; code and data release | Paper submitted (MNRAS) |

---

## 10. Tools, data and compute

- **Language and ML:** Python, PyTorch, scikit-learn / LightGBM for the feature baseline.
- **Scientific stack:** numpy, scipy, h5py, astropy; `frb`-style utilities for DM–z if useful.
- **Data:**
  - CHIME/FRB Catalog 2 ([DOI 10.11570/25.0066](https://doi.org/10.11570/25.0066)): table, total-intensity dynamic spectra (`<TNS>_stokesi_dynamic_spectrum.h5`, ~10 MB each; 0.983 ms, 400–800 MHz), exposure (`chimefrbcat2_exposure.h5`, 206 MB).
  - CHIME/FRB Catalog 1 waterfalls (already inspected; see `01_semi_synthetic_data/01_real_data/README.md`) as a cross-check of format.
  - FAST repeater bursts and the Blinkverse database for training augmentation only.
- **Compute:** machine A for simulation (CPU-heavy), machine B for training (GPU). Storage need is small (~10–20 GB).

---

## 11. Deliverables

1. Paper: Siamese benchmark (seven methods, pair and source level, ablations, gain vs S/N, distance to reference limits); validated search of 83 Catalog 2 repeaters; forecasts for CHIME-like and BURSTT-like surveys; H₀ in the discussion.
2. Open-source code: lensed-repeater constructor with exposure, baselines, models, evaluation scripts.
3. Derived data products (ε maps, search scores) with a Zenodo DOI.

---

## 12. Open items to verify before starting

- Current highest-redshift FRB (for Sec. 2.2).
- Re-check before submission that no ML lensed-pair classifier for FRBs has been published (the 2026-11-03 search found none, at abstract level).
- Catalog 2 dynamic spectrum format: resolution, window length, flagged channels, whether repeater bursts are all included.
- Catalog 2 exposure file format, and CHIME's east–west beam width and transit time per declination.
- Follow-up status of the FRB 20190308C candidate (Chang et al. 2025).
- Availability and format of FAST repeater bursts and the Blinkverse database.
