# Literature review

- [summary.md](summary.md): answers to the four plan-changing questions, and what they mean for the project.
- `papers/`: downloaded arXiv PDFs. They are kept out of git because licences vary; re-download from the arXiv links below.

## Index (downloaded 2026-11-03)

| File (`papers/…pdf`) | Paper | arXiv | Why it matters |
|---|---|---|---|
| **Lensing searches and compact dark matter** | | | |
| Munoz2016_FRB_lensing_compact_DM | Muñoz et al. 2016, *Lensing of FRBs as a probe of compact dark matter* | [1605.00008](https://arxiv.org/abs/1605.00008) | Founding paper: echo method, optical depth formulas |
| Sammons2020_compact_DM_FRB_microstructure | Sammons et al. 2020 (ApJ 900, 122), *First constraints on compact DM from FRB microstructure* | [2002.12533](https://arxiv.org/abs/2002.12533) | ~130 FRBs at µs resolution needed to beat existing limits |
| Krochek2021_PBH_CHIME_cat1 | Krochek & Kovetz 2022 (PRD), *Constraining PBH DM with CHIME FRBs* | [2112.03721](https://arxiv.org/abs/2112.03721) | **Tried Track A on public Catalog 1 data; ~1 ms resolution too coarse for a meaningful bound** |
| Kader2022_CHIME_baseband_lens_search | Kader et al. 2022, *High-time-resolution search … lens interferometry with CHIME/FRB* | [2204.06014](https://arxiv.org/abs/2204.06014) | Coherent autocorrelation search, 172 bursts at 1.25 ns; Track A baseline |
| Leung2022_PBH_CHIME_lens_interferometry | Leung et al. 2022 (PRD 106, 043017), *Constraining PBHs using FRB lens interferometry* | [2204.06001](https://arxiv.org/abs/2204.06001) | Current CHIME limit: f ≲ 0.8 at ~10⁻³ M☉ |
| Chang2024_lensed_candidate_CHIME_cat1 | Chang et al. 2025 (MNRAS Letters 537, L61), *A lensed FRB candidate in the first CHIME/FRB Catalogue* | [2406.19654](https://arxiv.org/abs/2406.19654) | FRB 20190308C, 3.4σ, autocorrelation on Catalog 1; a control for our pipeline |
| Connor2022_stellar_prospects_FRB_lensing | Connor & Ravi 2022, *Stellar prospects for FRB gravitational lensing* | [2206.14310](https://arxiv.org/abs/2206.14310) | Rates across delays µs–years; input to RQ1 |
| Ho2023_future_DM_constraints_lensed_FRB | Ho et al. 2023, *Future constraints on DM with lensed FRBs (BURSTT)* | [2304.04990](https://arxiv.org/abs/2304.04990) | ~24 lensed / 1700 FRBs per year forecast for BURSTT |
| **Cosmology with lensed repeaters** | | | |
| Li2018_lensed_repeaters_precision_probes | Li et al. 2018 (Nat. Commun.), *Strongly lensed repeating FRBs as precision probes* | [1708.06357](https://arxiv.org/abs/1708.06357) | H₀ from lensed repeaters; fixed delay pattern = Track C |
| Wucknitz2020_cosmology_lensed_repeaters | Wucknitz et al. 2021 (A&A 645, A44), *Cosmology with gravitationally lensed repeating FRBs* | [2004.11643](https://arxiv.org/abs/2004.11643) | Delay + its time derivative can remove lens-model uncertainty; affects Sec. 5.2 |
| **Data** | | | |
| CHIME2021_Catalog1 | CHIME/FRB 2021, *The First CHIME/FRB Catalog* | [2106.04352](https://arxiv.org/abs/2106.04352) | Our population and data source |
| CHIME2023_Catalog1_baseband_update | CHIME/FRB 2024 (ApJ 969, 145), *Updating Catalog 1 with baseband data* | [2311.00111](https://arxiv.org/abs/2311.00111) | **140 bursts public at 2.56 µs** |
| Sand2024_Catalog1_baseband_morphology | Sand et al. 2024, *Morphology of 137 FRBs down to µs timescales* | [2408.13215](https://arxiv.org/abs/2408.13215) | Burst substructure at µs; impostor source for Track A |
| CHIME2026_Catalog2 | CHIME/FRB 2026 (ApJS), *The Second CHIME/FRB Catalog* | [2601.09399](https://arxiv.org/abs/2601.09399) | 4539 bursts, 981 from 83 repeaters |
| Pandhi2026_FRB20220529A_declining_DM | Pandhi et al. 2026, *Declining DM for FRB 20220529A* | [2602.22309](https://arxiv.org/abs/2602.22309) | Favours an expanding supernova remnant over lensing |
| **Machine learning** | | | |
| Kharel2025_DL_repeater_vs_nonrepeater_morphology | Kharel et al. 2026 (ApJ 998, 1), *Repeating vs nonrepeating FRBs: deep learning on morphology* | [2509.06208](https://arxiv.org/abs/2509.06208) | ConvNeXt on Catalog 2 dynamic spectra; closest FRB-image ML precedent |
| Madheshwaran2025_ML_baseband_classification | Madheshwaran et al. 2025, *ML classification of CHIME baseband FRBs* | [2512.08308](https://arxiv.org/abs/2512.08308) | Repeater candidates from baseband features |
| Goyal2021_ML_lensed_GW_pairs | Goyal et al. 2021 (PRD 104, 124057), *Rapid identification of strongly lensed GW events with ML* | [2106.12466](https://arxiv.org/abs/2106.12466) | Lensed-pair ML in gravitational waves (DenseNet + XGBoost) |
| Zhang2026_pairwise_DL_lensed_GW | Zhang et al. 2026, *Time-domain deep learning for pairwise identification of lensed GW candidates* | [2605.29510](https://arxiv.org/abs/2605.29510) | **Siamese ResNet with \|difference\| and product fusion for lensed pairs**; direct design precedent for Track B |

Journal references are from the arXiv metadata where available; check the journal versions before citing.
