# 2026-11-14 ICAIIC: submission version without author names

The team chose to submit without author names (advisor's usual practice; ICAIIC itself does not require blind review).

- `07_deliverables/paper_icaiic/main_anonymous.tex` -> `main_anonymous.pdf`: the submission file. It defines
  `\anonymoussubmission` and inputs `main.tex`, so the two versions can never drift apart.
- `main.tex` -> `main.pdf`: the same paper with the IEEE author blocks (Patthamon, Watin, Panita*), kept for camera-ready.
- Author block switch in `main.tex` (`\ifanonymous`); `balance` package added so the last-page columns are even in both versions.
- Checks on both PDFs: 6 pages, letter, 0 overfull, no undefined refs, no Type 3 fonts; the anonymous PDF contains no author
  name, affiliation, e-mail or repository link (text search) and no author field in the PDF metadata. All floats on the
  page of, or after, their first citation.
