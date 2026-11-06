# Injection

**Purpose:** Inject lensed copies onto real off-pulse noise at CHIME band and resolution (400–800 MHz).

**Inputs:** Templates, noise, lens and propagation parameters.

**Outputs:** Dynamic spectra.

Diagram box in [pipeline.mmd](/pipeline.mmd). Large files go in `data/` or `outputs/` inside this folder (gitignored).

## Track B pair injection (v0, 2026-11-05)

Run: `python -I inject.py` (first run builds `data/inject_cache_256.h5` from the raw files, ~15 min; `--rebuild` forces it). Plan: [plan](/plan/2026-11-05_1254_pair-injection.md). Results: [v0 update](/update/2026-11-05_1335_pair-injection.md), [v1 update](/update/2026-11-05_1530_injection-v1-twin-ladder.md). Current sets: **v1.2** (v1 + 1000 impostor pairs + `val_bright` / `test_bright`; use `--sets-only`, the full audit reads real same-source pairs; [impostor update](/update/2026-11-05_1928_impostor-pairs.md)).

- **Training:** `from inject import load_pools, make_pair`; `make_pair(kind, rng, pools["train"])` with kind `lensed` / `repeat` / `unrelated` / `impostor` returns two 256 × 160 members, their masks, a label and a nuisance record.
- **Frozen sets:** `load_set("val" | "test" | "stress")` regenerates the arrays from [manifests/](manifests/) and fails if the SHA-256 no longer matches. Any change to `make_pair`, the cache or the split means a new set version.
- `outputs/audit.txt` holds the leak audit; `outputs/gallery_*.png` shows 10 test pairs per class.
