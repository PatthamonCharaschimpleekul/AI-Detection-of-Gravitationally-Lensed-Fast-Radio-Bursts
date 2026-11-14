# Update: the order of the test opening and the sign-off, and how the ICAIIC paper reports it (merge of main into the Stage 5 draft)

- **Date/time:** 2026-11-13 10:30
- **Branch:** `icaiic-stage5-final`.
  - It is `icaiic-stage5-draft` (f7a5f12) with `origin/main` (ee355a4) merged in, plus the paper fixes below.
  - It contains `origin/main`, so merging it into main is a fast-forward.
- **Problem:** there were two conflicting ICAIIC versions.
  - **main (11-11 17:30):** development results only, with "the test split stays sealed under the pre-registered protocol".
  - **The Stage 5 draft:** the test results, with the deviation disclosed.
  - The `main` text is no longer true, because the second machine has opened the test. **Only the Stage 5 version can be submitted.**

## What happened, in order (all 2026-11-10/11)
| Time | Machine | Event | Effect on the test result |
|---|---|---|---|
| 11-10 22:20 | second | `benchmark-v1` tag (local) at `ccbd35a`; methods frozen; Stage 5 queue started (user's instruction) | the test is opened from here on |
| 11-11 11:31 | team | Variants M, P, M+P: none adopted (plan 1300 rule, val only) | none: model 6 unchanged |
| 11-11 12:40 | second | Stage 5 primary result: model 6 +0.226 [+0.067, +0.403] over the GBM | — |
| 11-11 13:40 | team | Scattering sweep (val): sign-off not given | — |
| 11-11 16:06 | second | Stage 5 results committed locally (merge `d7144c1`); not yet pushed | — |
| 11-11 16:25 | team | Wide-scattering variant S: not adopted (plan 1400 rule, fixed at 14:00, val only) | none: model 6 unchanged |
| 11-11 17:00 | team | 04_propagation sign-off, option A: ranges, frozen sets and methods unchanged | none |
| 11-11 17:30 | team | `main` paper still written as "test sealed" | superseded |
| 11-11 19:15 | second | Stage 5 results pushed to `poc-lr-limit` (first time on the shared repo) | the team can see the test result from here on |

## Why the pre-registered result still stands
- **No choice after the opening changed anything the test measures.**
  - The sign-off changed nothing. The ranges, frozen sets, methods, metric, bootstrap and fold rules are the same.
  - The only candidate method after the opening (S) was rejected by a rule fixed before its runs, on val only.
- **What the order costs.** The test was *run* before the sign-off, but its result reached the shared repo only afterwards (see the 18:30 correction below). The sign-off was a "keep everything" decision, so it could not have been tuned to the test either way.
- **What would break it** (not done, and not to be done):
  - changing ranges, methods or thresholds now and re-scoring the test;
  - choosing between test-scored variants.
  - Any new model (for example a scattering-aware one) on the test is post-hoc. It must be reported separately, next to this result.

## How the paper says it (the wording in `icaiic-stage5-final`)
- **Sec. VI "Pre-registered test"** (renamed from "blind test"):
  > The test sources were opened once, after all methods were frozen at a version tag. One deviation is disclosed: the test was opened before the nuisance ranges of the propagation model were formally signed off. The sign-off followed the test, so it was not blind to the result, but it used validation pairs only and kept the ranges, the frozen sets and all methods unchanged (a wide-scattering training variant was rejected by a rule fixed before its runs); the result therefore stands as the pre-registered comparison.
- **Limitations:** the order of events, plus the scattering limit, with the numbers from update 1700 and `04_propagation/README.md`:
  - recall 0.57× at τ₆₀₀ = 1 ms and 0.13× at 3 ms;
  - training to 10 ms does not recover it;
  - the physics fit holds to 3 ms.
- **Abstract and conclusion:** "pre-registered test ... run once", "within the simulated nuisance ranges". No unqualified "blind".

## Changes made today, on top of the merge
| Change | Before | After |
|---|---|---|
| Sec. VI heading | "Pre-registered blind test" | "Pre-registered test" |
| Splits paragraph | "sealed under a pre-registered blind protocol" | "sealed under the pre-registered protocol" |
| Transfer paragraph | "without breaking the blind protocol" | "without opening the search on same-source pairs" |
| Deviation sentence | — | adds that variant S was rejected by a rule fixed before its runs |

**Checked:**
- **Memorisation-variant numbers:** the draft's "−0.02 to +0.00" is the paired bootstrap mean from update 1110 (+0.003 / −0.020 / −0.001). `main`'s "−0.036 to −0.006" is the seed-mean difference. The draft's version is kept, because it matches "every interval includes zero".
- **Build:** 6 pages, 0 overfull boxes, no undefined references, no Type 3 fonts, no pending markers.

## Still open (team or user)
- **Push the `benchmark-v1` tag** (`ccbd35a`, local on the second machine). It needs the user's go-ahead.
- **Merge `icaiic-stage5-final` into main** (fast-forward), then submit through EDAS by 15 Nov. The author list is still withheld.

## Addendum 2026-11-13 11:00: full audit of the ICAIIC paper
Every number in the paper was traced to an output file or an update. Every figure was rendered and checked. All 24 references were checked, and four of them were confirmed on the web.

**Factual fixes:**
| Where | Before | After | Evidence |
|---|---|---|---|
| Sensitivity paragraph | "the untrained baselines move up or down" | All methods fall on the test sources, including cross-correlation and the physics fit, so the test sources are harder | Table I: 0.171 → 0.128 and 0.164 → 0.070 (`stage5_fixed_split.txt`) |
| Main result | "On validation every learned model beats the baselines" | "Every learned model that trained scores above the three baselines ... cross-attention's margin over the GBM includes zero" | Model 7 seed 1 collapsed (0.013); model 4 vs GBM on validation is +0.131 [−0.003, +0.266] (update 0640) |
| Main result | "at similar AUC" (0.982 vs 0.936) | "The AUCs differ far less" | — |
| Splits paragraph and Fig. 2 | "Sources are split 60/20/20" | "Whole sources ... 60/20/20 by burst count" | `inject.split_sources`: 26 validation and 20 test sources |
| Memorisation sentence | "repeat and unrelated pairs ... 32% vs 86%" | Model 6 seed 0, *repeat* pairs, 32% on unseen vs 86% on training sources | update 1130 confusion matrix |
| Host-DM sentence | "less than this scatter" | "about 20%, within this scatter" | HostSens −19%; the MC scatter SD is about 20% |
| Fig. 2, panel 4 | "Blind test" | "Pre-registered test, all 80 sources, run once" | — |

**Wording and style fixes:**
- **Abstract:** "within the simulated nuisance ranges" now qualifies the result rather than the baseline; "sealed" became "held-out".
- **Prior:** "of order 10⁻⁴ or less", consistent with the quoted τ = 1.5e-4 at z = 1.
- **Symbol τ:** τ is the score threshold, so the twin threshold is no longer called bare τ.
- **Cross-reference:** Section VII is now referenced where methods 1–3 are first named.
- **Fig. 5 caption:** "the approximation (4)".
- **Thousands separators:** 18,585, 20,000 and 78,701.
- **American spelling,** per the IEEE style manual. The title now reads "Recognize".

**References:** a separate `references_icaiic.bib` with IEEE journal abbreviations ("Phys. Rev. D", not "PhRvD"). The MNRAS draft keeps `../paper/references.bib`.
- Chang et al. 2024 is now cited as MNRAS Letters, with doi 10.1093/mnrasl/slae116.
- Ho et al. 2023 now prints its ApJ doi.
- The capitalisation of "Canadian" in the CHORD title is protected.

**Verified unchanged:**
- **Stage 5 macros:** regenerated; the only change is the pair count's separator.
- **Tables:** Table II matches `stage4_ablations.txt`, including the "every seed" claims. Table III matches `stage3_val.txt`, `realburst.txt` and updates 1520 and 1130.
- **Track C:** N_exp 5e-6 / 1e-4; 10-yr gain 1.4× and 1.8×; all-sky 50×.
- **Throughput:** 1149 pairs/s, from the session log.

**Build:** 6 pages, letter size, 0 overfull boxes, no undefined references, no BibTeX warnings, no Type 3 fonts, all fonts embedded.

**Open (user):**
- **Review mode:** the ICAIIC 2027 CFP and submission pages say nothing about blind review. If review is single-blind, the author block ("withheld for review") and the repository link must be filled in before upload.

## Addendum 2026-11-13 14:00: dash removal, plainer prose, final recheck
**Dashes:** no `--` or `---` is left in the paper text, the tables, the macros or the figures.
- **Ranges:** written as "400 to 800 MHz", "0.19 to 0.86", "1.5 to 3.4%".
  - The generators were updated to match: `stage5_numbers.py`, `make_numbers_icaiic.py`, `make_snr_curve.py` (tick labels) and `diagrams/make_diagrams.py` (Fig. 1, Fig. 2).
- **"methods 1–3":** replaced by the names of the three baselines.
- **Empty table cells:** left blank, and the captions say "Empty cells were not evaluated".
- **Table III:** the rank-correlation row is split into "Real-to-twin rank correlation" and "Twin-to-twin ceiling". This needs two new macros: `\SfiveTransferRhoReal` and `\SfiveTransferRhoCeil`.
- **Dashes kept on purpose:** "Abstract—" and "Index Terms—", citation ranges such as [3]–[5], page ranges in the references, and "——" for a repeated author in [21]. IEEEtran produces all of these as IEEE reference style.

**Prose:** every section was rewritten in plainer language.
- Shorter sentences, and fewer "X, not Y" constructions and colon-led explanations.
- The meaning and numbers are unchanged.
- A token diff against 5b44701 shows the same citations and refs. Its only number changes are:
  - "1–3", removed;
  - one "80", removed with a duplicate sentence (see the next list);
  - one 0.24, added.
- Two content corrections:
  - **Main result:** the sentence "every learned model scores above the three baselines over the 80 sources" was removed. Only the GBM was scored out-of-fold, and the ablations paragraph already gives the architecture-versus-GBM intervals.
  - **Limitations:** "Training to 10 ms does not recover it" became "Extending training to 10 ms raises the 3 ms value only to 0.24" (update 1630: ratio 0.13 → 0.24).

**Build:** 6 pages, 0 overfull boxes, no undefined references, no BibTeX warnings, no Type 3 fonts, all fonts embedded. Every page and figure was checked visually.

## Addendum 2026-11-13 15:00: final recheck
- **Remote:** fetched; nothing new on origin.
- **Macros:** the Stage 5 and ICAIIC macros regenerate to identical values.
- **Clean rebuild:** 6 pages, letter size, 0 overfull boxes, no undefined references, no BibTeX warnings, no Type 3 fonts, all fonts embedded, no `\pending`.
- **One underfull box** (badness 10000), in the Index Terms line. It is cosmetic and comes from IEEEtran's keyword justification.
- **Fixes:**
  - Fig. 3 was never cited in the text; it is now cited at the encoder.
  - The timing-test sentence is reworded.
  - "Quoted to one significant figure".
- **Figures:** all five are now cited in the text.

## Addendum 2026-11-13 17:00: full trace against code and outputs
Every hard-coded setting in the paper was traced to the code, the output files or the team updates. All of them match.
- **Data and injection:** `inject.py`
  - 256×160 spectra, 0.983 ms samples, 4000-pair sets, time shift ±10 samples.
  - I1 smoothing of 16 channels (25 MHz).
  - 60/20/20 split by burst count; S/N floors 10 and 25.
  - Default τ₆₀₀ cap of 1 ms ("the top of the training range").
- **Training:** `train.py` and `run_all.sh`: 20,000 steps, batch 64, AdamW with lr 1e-3 and weight decay 1e-4, 1000 warm-up steps, cosine decay.
- **Model 6:** `models.py`: asinh input, four 5×3 convolution blocks with GroupNorm, c = 64 at 16×80, MAXLAG 12, a learned β, two convolution blocks after fusion, mean+max pooling, and the correlation profile fed to the head.
- **Baselines:** `baselines.py`: ±24 lags, 16 channel blocks, 7 GBM features per member.
- **Stage 5 transfer:** all four methods pass; model 6 has 0.010 [0.005, 0.018] and ρ 0.91 / 0.90.
- **Claims from team updates:**
  - single-member probe AUC 0.519 ± 0.009 (update 1335);
  - hard negatives bias the likelihood ratio by about 1 dex (tail-NRE POC);
  - 12 trained models and 3 baselines;
  - lower transit above δ = 70°;
  - 4σ delay match with a 4 ms median timing error;
  - host DM 68 → 150 changes the yield by −19%.

**Fixes:**
- **Table II and the Ablations text:** "No alignment (correlation off)" became "No soft alignment". With `align=False` the correlation profile is still fed to the head; only the soft alignment is off.
- **Wording:**
  - "noting that…" was a dangling participle; it became "which its authors say…".
  - A doubled "and" in the deviation sentence became a semicolon.
  - "191 of 200 of model 6's" became "191 of 200 false positives of model 6".

**Build:** 6 pages, 0 overfull boxes, no undefined references, no BibTeX warnings, no Type 3 fonts, all fonts embedded. Every page was checked visually.

## Correction 2026-11-13 18:30: the test result reached the shared repo after the sign-off
Earlier versions of this note said that the Stage 5 results were pushed at 16:06 and that the sign-off was therefore not blind. That was wrong: 16:06 is the commit time of merge `d7144c1`, not its push time.

**Evidence:**
- **Push time** (`git reflog origin/poc-lr-limit` on the second machine): pushed at 2026-11-10 22:20 (`ccbd35a`, benchmark commit, no results), and next at 2026-11-11 19:15 (`d7144c1`, containing `104981f` and `a443a15`). There were no other pushes in between; the 19:15 push was a fast-forward.
- **Team's sign-off record:** commit `65acac9` (16:40) still says "This does not open the test split" and "test unopened, benchmark-v1 not tagged".
- **Team's paper on `main`:** commit `ee355a4` (16:48) still says "the test split stays sealed".
- **Rule for variant S:** fixed in plan 1400 (commit `1140f74`, 13:21), before any S run.

**Paper (Sec. VI), new wording:** "the test was run before the nuisance ranges of the propagation model were formally signed off. Its result reached the shared repository only after the sign-off, whose record still lists the test as unopened, …". The Limitations section now says "run" in place of "opened".

## Addendum 2026-11-14: authors, abstract length, final recheck
- **Review mode:** ICAIIC 2027 does not state double-blind review; the submission page, the CFP page and the CFP PDF all say nothing about it. Under the IEEE default this means single-blind, so author names are included.
- **Authors (IEEE template blocks):**
  1. Patthamon Charaschimpleekul (Harbin Engineering University)
  2. Watin Promfiy (KMITL, School of IT)
  3. Panita Thusaranon (KMITL, School of IT), corresponding author
- **Repository link:** replaces "withheld"; the repository is public (HTTP 200 without login). The link uses `xurl`, which removes 7 underfull lines in the Conclusion.
- **Abstract:** 292 → 250 words, the IEEE guideline. The test-set-only gain (+0.323) was dropped from the abstract; it remains in the text and in Table I.
- **Trims to fit 6 pages with the 3-column author block:**
  - a validation-numbers sentence (now said in the Table I caption);
  - the fold-variation sentence, shortened;
  - the checkpoint parenthetical in Sensitivity;
  - the Conclusion DOI, replaced by citation [20].
- **Fact diff against `1c1bccf`** (the last version fully traced to code): no result number changed, and all citations are kept.
- **Build:** 6 pages, letter size, 0 overfull boxes, 1 underfull box (the Index Terms line, from IEEEtran justification), no undefined references, no BibTeX warnings, no Type 3 fonts, all fonts embedded. Every page was checked visually.

## Addendum 2026-11-14 (later): title with U, observation model, no repository link
- **Title:** "259k Parameters to Recognize $U$: Siamese Alignment of Lensed Fast Radio Bursts" (2 lines). The 259k is checked against `models.py`: model 6 has 259,365 parameters.
- **Sec. III:** an observation model, $X=\mathcal{P}_\theta(U)+N$, where $U$ is the intrinsic burst (the template).
  - A lensed pair has $U_A=U_B$ with independent $\theta$; a repeat has $U_A\neq U_B$; an impostor is a repeat with a shared propagation imprint.
  - This matches the injection code.
  - The recall is now conditioned on $U_A=U_B$.
  - The unrelated-class symbol changed from $\textsc{u}$ to $\textsc{d}$, so it does not clash with $U$.
- **Repository:** the GitHub link was removed at the user's request. The Conclusion now says the code, manifests, hashes and plans are "available from the authors on request". `xurl` was removed. Sec. VI now says "the team's shared repository".
- **Trims to stay at 6 pages:** four sentences tightened (no content dropped), the memorization-variant clause shortened, and Fig. 5 width changed from 0.95 to 0.88 column.
- **Fact diff against `395e0d7`:** no result number changed, and all citations are kept.
- **Build:** 6 pages, 0 overfull boxes, no undefined references, no BibTeX warnings, no Type 3 fonts. Pages checked visually.

## Addendum 2026-11-14: final recheck after the title change
- **Remote:** fetched; nothing new.
- **Macros:** regenerate identically.
- **Clean rebuild:** 6 pages, letter size, 0 overfull boxes, 1 underfull box (the Index Terms line), no undefined references or multiply-defined labels, no BibTeX warnings, no Type 3 fonts, all fonts embedded, no `\pending`.
- **Abstract:** 250 words.
- **Fact diff against `1c1bccf`** (the last version fully traced to code): only intended changes, namely the title, the authors, the abstract, the trims, and the DOI replaced by citation [20]. No result number changed.
- **Observation model $X=\mathcal{P}_\theta(U)+N$:** checked against `inject.member` and `make_pair`. Each member has its own template, S/N, real background, shift, DM and scintillation, and one member is scattered. Impostors share an I1 gain or an I2 scintillation.
- **Fix:** "A pair (A,B) from one sky position is lensed…" became "A pair (A,B) of bursts is lensed…", because unrelated pairs come from two sources.

## Addendum 2026-11-14, visual recheck

- Eq. (3): number had dropped to its own line; now written with sigma_AB / sigma_BA (plus one clause defining sigma_AB), fits on one line. No change in meaning.
- Fig. 1: "new propagation imprint" ran past the panel (a) border (moved left); subscript "sid" touched the line below in panel (b) (rows re-spaced); the Δt label sat on its arrow (raised).
- Fig. 2: subscripts in panel 3 list touched the next line (line spacing 10 to 11-12 units).
- Fig. 4: legend "(16)" dropped (16-channel blocks are stated in the text); data and script keys unchanged.
- Rebuilt: 6 pages, letter, 0 overfull, no undefined refs, no Type 3 fonts. Fact diff vs d6ec69a: no number, macro or citation change.
