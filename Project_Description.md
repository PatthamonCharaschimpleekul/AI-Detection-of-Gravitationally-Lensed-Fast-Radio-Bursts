# Project Description — AI Detection of Gravitationally Lensed Fast Radio Bursts

Detailed project plan for the research proposal of 31 Oct 2026.
Technical terms are defined in [Definitions_of_specific_terms.md](Definitions_of_specific_terms.md); this file explains *what* we will do, *why*, and *how we will know it worked*.

---

## 1. One-paragraph summary

Some fast radio bursts (FRBs), plausibly powered by magnetars, travel past a galaxy or a compact object on their way to Earth and are **gravitationally lensed**: the same burst arrives two or more times, separated by a time delay. Those delays measure the Hubble constant H₀ and the amount of compact dark matter. The obstacle is that **many FRBs repeat on their own**, so a "second burst" is ambiguous. We will simulate a realistic CHIME/FRB-like population, inject lensing at two scales, and train a model — built around a **weight-shared (Siamese) encoder** — to separate *lensed echoes* from *intrinsic repeats*, benchmarked honestly against cross-correlation and a physics likelihood test. The model's measured detection efficiency then feeds forecasts of H₀ precision and of what a non-detection says about compact dark matter.

---

## 2. Where the idea came from, and why it was reframed

### 2.1 The original wish
Use FRBs from magnetars to find "the edge of the universe" — how big the universe is.

### 2.2 Why that exact goal is not feasible
- **The "edge" is not an object we can detect.** The observable universe is bounded by the *particle horizon* (~46 billion light-years comoving radius), which is set by the age and expansion history of the universe, not by anything that emits signals. No source, FRB or otherwise, sits "at the edge".
- **FRBs are not seen that far.** Known FRBs reach redshift z ≈ 1 (a few candidates higher — verify current record before quoting). The cosmic microwave background, at z ≈ 1100, is already the farthest light we can see; FRBs are far closer.
- **Magnetar origin does not add distance information.** Knowing the engine is a magnetar tells us about the source physics, not about the size of the universe.

### 2.3 The feasible version of the same question
"How big is the universe?" in practice means **"how fast is it expanding?"** — the Hubble constant H₀, which sets the scale and age of the universe. FRBs *can* contribute to that:

| Original wish | Feasible proxy | How FRBs help |
|---|---|---|
| Size / edge of universe | Expansion rate H₀ | Lensing time delays (this project); DM–redshift relation (other work) |
| What the universe is made of | Fraction of dark matter in compact objects | Absence or presence of ms-scale lensing echoes |
| Use magnetar FRBs | Keep FRBs as the signal | Magnetars power at least some FRBs (SGR 1935+2154, 2020) |

An alternative closer to the original wish: the **DM–redshift (Macquart) relation** of FRBs with identified host galaxies (now in the hundreds) measures H₀ and the cosmic baryon content directly from existing data, without waiting for a lens. AI plays a smaller role there, which is why this project uses lensing instead.

So the project keeps all three ingredients of the original idea — neutron stars, bending of light, cosmic scale — in a form that can produce a real, publishable result within ~6 months.

---

## 3. Research questions

1. **Yield.** How many lensed FRBs should a CHIME/FRB-like survey detect per year, split by lens scale (galaxy vs compact object) and by repeater vs one-off?
2. **Discrimination.** Can a learned model built on a Siamese (weight-shared) encoder separate lensed pairs from intrinsic repeats better than cross-correlation, *under realistic propagation and instrumental effects*?
3. **Cosmology.** How precisely do N detected lensed FRBs measure H₀, and what does a null result imply for the compact-dark-matter fraction f_CO(M)?

> RQ2 is written so that "better than cross-correlation" is the test, not "Siamese wins". If a simpler method wins, that is a result too (see Sec. 6).

---

## 4. The physics that makes discrimination possible

A lensed echo is **the same emission event seen twice**. An intrinsic repeat is **a new event from the same source**. That difference shows up in several measurable places:

| Property | Lensed echo pair | Intrinsic repeat pair | Caveat |
|---|---|---|---|
| Intrinsic waveform (sub-burst structure, drift) | Identical up to noise | Different (bursts vary) | Only visible if the burst is resolved in time |
| Flux ratio | Set by lens magnification μ | Random | Repeaters can have similar fluences by chance |
| Time delay | Achromatic (same at all frequencies) | No fixed delay | Plasma lensing gives *chromatic* delays — an impostor |
| DM | Almost equal (small Δ from different paths through the lens galaxy) | Equal at first, may drift over months | Both pass through the same host |
| RM, scattering, scintillation | Slightly different (different sightlines) | Can drift with time | Simulation must include this |
| **Repeating lensed source** | Every burst has a copy at the same Δt with the same flux ratio | No such pattern | Strong, timing-only signal |

Where the distortion between echoes comes from:
- **Gravity does not distort the burst.** Gravitational lensing is achromatic and leaves the waveform shape unchanged; it only shifts arrival time and scales brightness.
- **Plasma does.** Each image takes a different path through the lens galaxy's gas, so it picks up slightly different scattering, scintillation, DM and RM.
- **Dispersion is a small effect.** Each burst is dedispersed at its own DM, and ΔDM between images is tiny. Scattering and scintillation are the distortions that matter.

Key consequences for the design:
- **Do not simulate perfect copies.** If lensed images are exact scaled copies, any model reaches ~100% on simulation and fails on real data. Propagation differences must be in the training data.
- **The hard negatives are similar-looking repeats** from the same source in the same activity window, not random unrelated bursts.
- **Timing alone is powerful for lensed repeaters** (last row) and needs no deep learning.

---

## 5. Pipeline

The work splits into three tracks because the lens scales lead to different data problems:

- **Track A — compact-object lensing (µs–ms delays).** Both images fall inside *one* dynamic spectrum. Task: "does this single burst contain an echo?"
- **Track B — galaxy lensing (days–months delays).** Images are *separate detections*. Task: "is burst B a lensed copy of burst A?" ← the Siamese model lives here.
- **Track C — timing of lensed repeaters.** Task: "do this source's arrival times show a constant delay with a constant flux ratio?"

**Priorities.** Lensing is rare, so the project is ordered by what can produce a real result now:
1. **Track A on real CHIME data → an actual f_CO(M) limit.** A concrete, publishable physics result within this project, even with zero detections.
2. **Track B (Siamese) on semi-synthetic data.** Methodology and readiness for next-generation surveys (CHIME Outriggers, CHORD, DSA-2000, SKA), which will detect many more FRBs.
3. **H₀ as a forecast only** (Sec. 5.2 explains why).

### Phase 1 — Semi-synthetic data: real bursts, simulated lensing
**Goal:** use real data everywhere it exists, and simulate only what has never been observed — the lensing itself.

No confirmed lensed FRB exists yet (only the Chang et al. 2025 candidate), so lensed positives cannot come from a dataset. Everything else can:

| Ingredient | Source |
|---|---|
| Burst templates | CHIME/FRB Catalog 1 (and Catalog 2) waterfall data, [chime-frb.ca](https://chime-frb.ca/) |
| **Intrinsic-repeat negatives** | Real bursts from CHIME repeaters, plus large repeater samples (e.g. FAST bursts of FRB 20121102A, the Blinkverse repeater database) |
| Noise and RFI | Real off-pulse regions of the same waterfalls |
| Population statistics (rate, DM, fluence, width, scattering, repeater fraction) | CHIME catalog tables |
| **Lensed positives** | Simulated: a real burst copied with lens delay Δt, magnification μ and independent propagation effects, injected onto real noise |

The hardest negatives (real repeats that look alike) are therefore real, and the only simulated physics is lensing, which is well understood.

Steps:
1. Population statistics from **CHIME/FRB Catalog 1** (recalibrate to Catalog 2 if available), used for rates and for sampling lens geometry.
2. Redshift assignment from DM (Macquart relation + host and Milky Way contributions, with scatter).
3. Lensing:
   - **Galaxy scale:** singular isothermal sphere / SIE lens population with optical depth τ(z); output image count, Δt (days–months), magnifications.
   - **Compact scale:** point-mass lenses of mass M with fraction f_CO; output Δt (µs–ms), flux ratio.
4. Per-image propagation differences: ΔDM, ΔRM, different scattering time and scintillation pattern.
5. Impostors: plasma-lensed bursts (chromatic delays and magnification).
6. Fully synthetic bursts (parametric pulse models) only as a control set, to check that results do not depend on the particular real templates.

Caution: FAST data are at ~1.25 GHz, CHIME at 400–800 MHz. Bursts from other telescopes are rescaled to the CHIME band and resolution, and every result is also reported on CHIME-only data.

### Phase 2 — Signal injection and labelling
**Goal:** model-ready data with honest labels.

1. Inject lensed copies into dynamic spectra at CHIME resolution (400–800 MHz) on **real off-pulse data and RFI**; Gaussian noise only as a control.
2. Labels:
   - Track A: `echo` / `no echo` / `plasma impostor`
   - Track B pairs: `lensed` / `intrinsic repeat` / `unrelated`
3. **Split by source, not by pair**, into train / validation / test, so no source appears in more than one split.
4. Keep a separate "realism stress test" set with nuisance parameters wider than in training.

### Phase 3 — Model design
See Sec. 6 for the full reasoning. Summary:
- Track A: single-input CNN.
- Track B: **Siamese encoder with feature-map fusion** (primary), a cross-attention variant, plus a classic Siamese and a 2-channel CNN as ablations; trained with physics-based augmentation and hard negatives.
- Track C: a likelihood test on arrival times; no neural network.

### Phase 4 — Training, validation, benchmarking
**Goal:** show whether learning helps, and by how much.

Methods compared on identical test sets (Sec. 6.3). Metrics in Sec. 7. The output that matters downstream is the **detection efficiency ε(Δt, μ, S/N)** and the **false-alarm rate per survey-year**.

### Phase 5 — Cosmological forecasts
#### 5.1 Yield (RQ1)
Expected detections per year:

$$
N_{\text{exp}} = \sum_i \tau_i\,\varepsilon_i
$$

summed over the simulated population, where τ_i is the probability that burst i is lensed (optical depth) and ε_i is the detection efficiency measured in Phase 4.

#### 5.2 H₀ from galaxy-lens time delays (RQ3)
The delay between images i and j is

$$
\Delta t_{ij} = \frac{D_{\Delta t}}{c}\,\Delta\phi_{ij},
\qquad
D_{\Delta t} = (1+z_l)\frac{D_l D_s}{D_{ls}} \;\propto\; \frac{1}{H_0}
$$

- D_l, D_s, D_ls: angular diameter distances to the lens, to the source, and from lens to source; all scale as 1/H₀.
- Δφ_ij: Fermat-potential difference, from the **lens mass model**.

Simplest example, a singular isothermal sphere (SIS) lens:

$$
\Delta t = \frac{(1+z_l)}{2c}\frac{D_l D_s}{D_{ls}}\left(\theta_A^2 - \theta_B^2\right)
$$

So H₀ ∝ Δφ / Δt, with

$$
\frac{\delta H_0}{H_0} \approx \sqrt{\left(\frac{\delta \Delta t}{\Delta t}\right)^2 + \left(\frac{\delta \Delta\phi}{\Delta\phi}\right)^2}
$$

An FRB gives Δt to ~ms over days (δΔt/Δt ~ 10⁻⁸), so the first term vanishes and the lens model (~5–10% per system for lensed quasars today, plus the mass-sheet degeneracy) dominates. For N systems, σ(H₀)/H₀ ≈ (per-system lens-model error)/√N.

**What Δt alone cannot do:** measuring H₀ also needs arcsecond image positions (VLBI or CHIME Outriggers), imaging of the lens galaxy for the mass model, and redshifts z_l and z_s. These are outside this project, so the H₀ part is a forecast: how large N must be, and which follow-up is needed.

#### 5.3 Compact dark matter from a null result (RQ3)
For a point-mass lens of mass M at redshift z_l, with y the source offset in units of the Einstein radius:

$$
\Delta t = \frac{4GM(1+z_l)}{c^3}\left[\frac{y\sqrt{y^2+4}}{2} + \ln\frac{\sqrt{y^2+4}+y}{\sqrt{y^2+4}-y}\right]
$$

$$
R_{\text{flux}} = \frac{y^2+2+y\sqrt{y^2+4}}{y^2+2-y\sqrt{y^2+4}}
$$

Since 4GM/c³ ≈ 20 µs × (M/M☉), a ~30 M☉ lens gives Δt ≈ 0.6 ms — the Track A window.

The lensing optical depth of each burst scales with f_CO, the fraction of dark matter in compact objects:

$$
N_{\text{exp}}(f_{CO}, M) = \sum_i \tau_i(f_{CO}, M)\,\varepsilon_i
$$

If Track A finds **no** echoes, Poisson statistics give P(0) = e^(−N_exp), so at 95% confidence

$$
N_{\text{exp}} < 3 \;\Rightarrow\; f_{CO}(M) < \frac{3}{\sum_i \tau_i(f_{CO}{=}1, M)\,\varepsilon_i}
$$

The mass range is bounded below by time resolution (Δt must be resolvable) and above by the data window length and the largest detectable flux ratio. Compare the resulting limit with existing CHIME limits (Krochek & Kovetz 2022; Leung et al. 2022).

---

## 6. Model design and the Siamese question

### 6.1 What a classic Siamese network does
Two inputs pass through **the same encoder (shared weights)**, each is compressed to a vector (embedding), and a distance between the two vectors decides "same or different". Trained with contrastive or triplet loss.

### 6.2 Is it the right tool here? Honest assessment

**What fits:**
- Weight sharing is exactly right: both bursts should be processed by the same feature extractor, and the answer should not depend on which burst is called A or B.
- Learned similarity can absorb nuisance effects (scattering, scintillation, RFI) that break cross-correlation.

**What does not fit:**
- **Late fusion loses information.** Classic Siamese compares the two bursts only after each is squashed to a vector. The question "is B a scaled, shifted copy of A?" depends on point-by-point time–frequency detail that is gone by then.
- **Its main practical advantage is not needed.** Siamese embeddings make searching millions of pairs cheap. But galaxy-lensed images are separated by arcseconds, below CHIME's arcminute localization, so candidate pairs are only bursts from the *same* apparent source — few pairs, no search problem.
- **Cross-correlation is close to optimal in the ideal case.** If B = μ·A(t − Δt) + Gaussian noise, a matched filter is the best possible test. A learned model can only win through realistic nuisances.
- **Limited structure in the data.** At ~1 ms resolution many CHIME bursts are barely resolved, so there is less internal structure for a deep network to exploit.
- **Not used for Track A.** With both images in one spectrum there is no pair to feed a Siamese network.

### 6.3 Decision: keep the Siamese encoder, fix the fusion

**Primary model (Track B): Siamese encoder with feature-map fusion.**
- Shared-weight CNN encoder g(·) applied to burst A and burst B (Siamese).
- Instead of collapsing to vectors first, combine the **intermediate feature maps**: |g(A) − g(B)|, g(A)·g(B), and optionally a cross-correlation layer between them.
- A small classification head outputs P(lensed), P(repeat), P(unrelated).
- Extra scalar inputs: ΔDM, ΔRM, flux ratio, time separation.
- Loss: cross-entropy (class-weighted for the rare `lensed` class), optionally plus a contrastive term on the embeddings.

This keeps what is good about Siamese networks (shared weights, symmetry, learned similarity) and removes the late-fusion weakness.

**Tolerance to propagation effects comes from the data, not from a special loss.** A model only learns to ignore the distortions it sees in training, so lensed positive pairs are built with **physics-based augmentation**: each image independently gets its own scattering time, scintillation pattern, small ΔDM and ΔRM, and RFI. The model then learns which differences are "same burst, different path" (the idea behind SimCLR-style augmentation, with physically motivated transforms). The margin in any contrastive term sets how much difference is allowed, and it can be tuned.

**Hard negatives drive training.** Intrinsic repeats from the same source in the same activity window, chosen to look as similar as possible, are oversampled. Random unrelated bursts are easy and teach little.

**Benchmark ladder** — all methods on the same test set; the simplest method that works is the recommendation:

| # | Method | Role |
|---|---|---|
| 1 | Cross-correlation / matched filter | Traditional baseline |
| 2 | Physics likelihood ratio: fit B = μ·shift(A) ⊗ scattering kernel vs "independent burst" | Strongest non-ML baseline |
| 3 | Gradient-boosted trees on features (ΔDM, ΔRM, width, drift rate, spectral index, polarization angle, flux ratio) | Interpretable baseline |
| 4 | 2-channel CNN (A and B stacked, early fusion) | Ablation: no weight sharing |
| 5 | Classic Siamese (vector embedding + distance) | Ablation: late fusion |
| 6 | **Siamese encoder + feature-map fusion** | Primary model |
| 7 | Siamese encoder + cross-attention: time–frequency patches of A attend to patches of B | Alternative fusion; robust to small shifts and warps, needs more training data (simulation makes that cheap) |

**Why not a long time-series Transformer over the days–months gap:** nothing is recorded between the two bursts — CHIME stores only a short window around each trigger, and a month of raw data at ms resolution would be ~10⁹–10¹⁰ samples per channel, almost all noise. The separation between the bursts is a single number and goes into the model as a scalar input. Attention is used *within* the pair (model 7), not across the gap.

**Fundamental limit.** If a burst is unresolved at ~1 ms, a lensed pair and a similar-looking repeat can be genuinely indistinguishable in these data, and no model can fix that. We estimate the best achievable performance with the exact likelihood ratio on simulation (where the true generating process is known) and report how close each method gets to it.

**Base rate (Bayes prior).** A model score is not the probability of lensing. With τ ~ 10⁻³, even a strong classifier gives a low posterior. Before calling any pair "lensed" we convert scores into posterior odds = likelihood ratio × prior odds from τ.

**Final decisions combine evidence, not one model.** Beyond the waveform:
- A lensed one-off gives exactly two bursts and then silence, while a repeater keeps firing, so continued monitoring separates them.
- Optical/IR imaging of the host can reveal a foreground lens galaxy.
- A lensed repeater shows the constant-delay pattern of Track C.

**Deployment as a cascade.** Cross-correlation / likelihood ratio (1–2) runs first on every candidate pair: fast, explainable, and expected to be enough at high S/N. Only ambiguous pairs (low S/N or strongly distorted) go to the learned model. This keeps results explainable where possible and spends compute only where learning can help.

Possible outcomes and what each means:
- **6 or 7 beats 1–5:** the Siamese design is justified; the comparison with 5 shows why fusion matters.
- **2 or 3 matches 6:** physics already captures the signal; the paper is a systematic benchmark plus a forecast. Still publishable.
- **Everything fails on the stress-test set:** the simulation is too optimistic or CHIME resolution is too coarse — the forecast becomes "current instruments are not enough", which is also a result.

**Track A model:** single-input CNN on the dynamic spectrum, compared against auto-correlation (and published CHIME baseband methods where applicable).

**Track C:** likelihood test for a constant delay Δt with constant flux ratio in a source's arrival-time list. Optional comparison: a set Transformer that takes every burst of one source as a token (burst embedding + arrival time + fluence) and flags pairs with a shared Δt and flux ratio — kept only if it beats the likelihood test.

---

## 7. Evaluation

Lensed events are rare (τ ~ 10⁻³), so accuracy is meaningless — a model that always says "not lensed" is 99.9% accurate.

Report instead:
- **ROC and precision–recall curves**, and **recall at very low false-positive rate**.
- **Expected false lensing claims per survey-year** at the chosen threshold — the headline number.
- **Detection efficiency ε(Δt, μ, S/N)** as a function, not a single number; Phase 5 needs it.
- **Gain over cross-correlation as a function of S/N.** We expect little or no gain at high S/N; the case for the learned model rests on the low-S/N and strongly scattered regime.
- **Distance to the fundamental limit:** each method's performance relative to the exact likelihood ratio on simulation.
- **Calibration** of predicted probabilities (reliability diagram).
- **Robustness:** performance on the stress-test set with wider nuisances and on Gaussian-vs-real noise backgrounds.
- **Impostor rejection:** how often plasma-lensed bursts are called gravitationally lensed.

Sanity check on real data (no labels): run the final model on CHIME Catalog 1 repeaters and the published lensed candidate (Chang et al. 2025) and report scores — as a consistency check, not as a detection claim.

### 7.1 Validating a null result: "no lens" vs "we missed it"

A non-detection only means something if we can show the pipeline would have found a lens that was there. Checks:

1. **Injection–recovery.** Inject fake echoes with known Δt, μ, S/N into the *same real CHIME data* we search, run the full pipeline, and measure ε(Δt, μ, S/N). This ε is the one in the f_CO limit (Sec. 5.3), so where the pipeline is weak, the limit is automatically weak.
2. **Blind injections.** A script (or a teammate) injects an unknown number of fakes and seals the answer key; we search, then unseal. This stops thresholds being tuned toward the answer.
3. **False-alarm rate from real data.** Pairs known not to be lensed (bursts from different sources, or time-shifted pairings, like LIGO time slides) give the real background.
4. **Controls.** Must flag or explain: the Chang et al. 2025 candidate. Must reject: plasma-lensed FRB 20201124A and naturally multi-component bursts. Baselines and learned models must agree; disagreements are investigated before any conclusion.
5. **Expected count before searching.** Compute N_exp at f_CO = 1 first. If N_exp ≪ 1, a non-detection says nothing; if N_exp ≫ 3, it is a real constraint.
6. **Injection realism.** Too-clean injections inflate ε and make the limit falsely tight, so injections span several distortion levels and the limit is reported as a range.

| Injections recovered? | Real detection? | Meaning |
|---|---|---|
| Yes (high ε) | No | No lenses in that range → f_CO limit |
| No (low ε) | No | Pipeline or data not sensitive → no conclusion |
| Yes | Yes | Candidate → compare with false-alarm rate, follow up |
| No | Yes | Suspicious, likely artefact → investigate |

---

## 8. Risks and mitigations

| Risk | Effect | Mitigation |
|---|---|---|
| Simulation too clean | Model learns shortcuts, fails on real data | Semi-synthetic data (real bursts, real repeats, real noise), per-image propagation differences, stress-test set |
| Telescope domain mismatch (FAST 1.25 GHz vs CHIME 400–800 MHz) | Model learns telescope, not physics | Rescale to CHIME band and resolution; report CHIME-only results too |
| Data leakage | Over-optimistic scores | Split by source |
| Class imbalance | Misleading metrics | Report FPR-based metrics and false claims per year |
| Similar-looking intrinsic repeats | High false-positive rate | Hard-negative mining, Bayes prior from τ, multi-evidence final decision |
| Lensed and repeat pairs fundamentally indistinguishable at CHIME resolution | No method can succeed on morphology alone | Measure the likelihood-ratio limit first; lean on timing (Track C) and follow-up evidence |
| Deep model costly and hard to explain | Results hard to trust | Cascade: statistical methods first, learned model only for ambiguous pairs |
| Model beaten by baselines | "AI not needed" | Framed as benchmark in RQ2; still publishable |
| Prior work already did this | Lower novelty | Literature check before Phase 3 (de Mello/Law Siamese study, AAS abstract, CHIME lensing searches) |
| Lens-model error dominates H₀ | Forecast looks weak | State it explicitly; that limitation is itself useful guidance |
| CHIME time resolution too coarse | Little morphology to learn | Test at several resolutions; note what baseband data would add |

---

## 9. Timeline (~6 months)

| Month | Work | Milestone |
|---|---|---|
| 1 | Literature check; read CHIME Catalog 1 data; population simulator | Simulated population matches catalog distributions |
| 2 | Lensing + propagation effects + injection; Track A dataset | Track A data ready; baselines 1–2 running |
| 3 | Track A CNN; Track B pair dataset; baselines 1–3 on Track B | First Track A result |
| 4 | Siamese models (6, 7, 5) and 2-channel CNN (4); ablations; likelihood-ratio limit | Benchmark table for Track B |
| 5 | Stress tests; Track C timing test; ε(Δt, μ, S/N) | Efficiency maps |
| 6 | Phase 5 forecasts; write-up; release code | Paper draft + open-source pipeline |

The first end-to-end result is Track A with its baseline (end of month 3), so there is a complete, if small, result early.

---

## 10. Tools, data and compute

- **Language and ML:** Python, PyTorch, scikit-learn / LightGBM for the feature baseline.
- **Scientific stack:** numpy, scipy, astropy; `frb`-style utilities for DM–z if useful.
- **Data:** CHIME/FRB Catalog 1 (and Catalog 2 if available) from [chime-frb.ca](https://chime-frb.ca/) — catalog tables and the public waterfall data (verify which products are public and at what resolution). Repeater burst samples from FAST (FRB 20121102A) and the Blinkverse database for intrinsic-repeat negatives. Kaggle has pulsar datasets (e.g. HTRU2) but nothing with lensed FRB labels.
- **Compute:** machine A for simulation (CPU-heavy), machine B for training (GPU).

---

## 11. Deliverables

1. **Open-source pipeline:** population simulator, lensing injector, baselines, models, evaluation scripts.
2. **Benchmark table:** seven methods on identical test sets, with ablations, gain vs S/N, and distance to the likelihood-ratio limit.
3. **Efficiency maps** ε(Δt, μ, S/N) for both lens scales.
4. **Forecast paper:** expected yield, H₀ precision vs N, f_CO limits from a null result — publishable even if the answer is "current instruments are not enough".

---

## 12. Open items to verify before starting

- Current highest-redshift FRB (for Sec. 2.2).
- Whether an ML lensed-vs-repeat classifier has been published since the de Mello/Law study.
- Exact public CHIME data products and their time/frequency resolution.
- Status of the Chang et al. 2025 lensed candidate and of FRB 20220529A.
- Latest CHIME limits on compact dark matter to compare the null-result forecast against.
- Availability and format of FAST repeater bursts and the Blinkverse database.
- Current localization precision of CHIME Outriggers (relevant to Sec. 5.2).
