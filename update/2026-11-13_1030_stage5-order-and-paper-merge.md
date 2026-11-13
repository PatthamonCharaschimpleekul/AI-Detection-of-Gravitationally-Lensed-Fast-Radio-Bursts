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
| 11-11 16:06 | second | Stage 5 results pushed to `poc-lr-limit` | the team can see the test result from here on |
| 11-11 16:25 | team | Wide-scattering variant S: not adopted (plan 1400 rule, fixed at 14:00, val only) | none: model 6 unchanged |
| 11-11 17:00 | team | 04_propagation sign-off, option A: ranges, frozen sets and methods unchanged | none |
| 11-11 17:30 | team | `main` paper still written as "test sealed" | superseded |

## Why the pre-registered result still stands
- **No choice after the opening changed anything the test measures.**
  - The sign-off changed nothing. The ranges, frozen sets, methods, metric, bootstrap and fold rules are the same.
  - The only candidate method after the opening (S) was rejected by a rule fixed before its runs, on val only.
- **What the order costs.** The sign-off was *not blind* to the result. The paper says so in one sentence. Because it was a "keep everything" decision, it could not have been tuned to the test.
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
