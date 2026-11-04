# Lens simulator and lensed-repeater constructor

**Purpose:** Galaxy lenses (SIS/SIE, Δt hours–months, magnifications); turn a real repeater into a lensed one (image B = image A delayed by Δt, scaled by the flux ratio); keep only bursts inside CHIME exposure and above threshold.

**Inputs:** Repeater burst lists, population parameters, Catalog 2 exposure.

**Outputs:** Lensed repeater burst lists with labels.

Diagram box in [pipeline.mmd](/pipeline.mmd). Large files go in `data/` or `outputs/` inside this folder (gitignored).
