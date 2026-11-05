# Impostors

**Purpose:** Plasma-lensed bursts (chromatic) and naturally multi-component bursts.

**Inputs:** Real templates.

**Outputs:** Impostor examples for training and controls.

Diagram box in [pipeline.mmd](/pipeline.mmd). Large files go in `data/` or `outputs/` inside this folder (gitignored).

**Status (2026-11-05):** implemented inside `02_injection_labelling/01_injection/inject.py` as the `impostor` pair kind (I1 shared envelope by envelope transfer, I2 shared scintillation). Plan: [plan 1925](/plan/2026-11-05_1925_impostor-pairs.md). Multi-component bursts and within-burst plasma echoes are out of scope for Track B (cross-file pairs).
