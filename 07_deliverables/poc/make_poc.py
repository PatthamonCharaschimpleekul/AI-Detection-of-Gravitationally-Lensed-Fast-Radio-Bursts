"""Two-page proof-of-concept summary for Track B (development results, 2026-11-08).
Numbers are copied from 03_models_benchmark/track_B_pairs/02_benchmark/outputs/stage2_val.txt and
outputs/folds_dev/oof.txt (both gitignored), as reported in update/2026-11-08_0640 and _1450.
Usage: venv/Scripts/python -I 07_deliverables/poc/make_poc.py  ->  07_deliverables/poc/trackB_poc_2026-11-08.pdf
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = Path(__file__).resolve().parent
FONTS = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DV", str(FONTS / "DejaVuSans.ttf")))  # full Unicode: ≥, −, ν
pdfmetrics.registerFont(TTFont("DVB", str(FONTS / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DV", boldItalic="DVB")

# paired recall difference vs b3_gbm at 1% FPR: (label, mean, lo, hi)
DIFFS = [("Model 6, fixed split (val_bright, 3 seeds)", 0.394, 0.226, 0.542),
         ("Model 6, grouped folds (60 sources, OOF)", 0.220, 0.035, 0.381),
         ("Model 5, fixed split", 0.244, 0.024, 0.436),
         ("Model 4, fixed split", 0.131, -0.003, 0.266),
         ("Model 7, fixed split (1 of 3 seeds collapsed)", 0.065, -0.352, 0.389)]


def figure(path):
    fig, ax = plt.subplots(figsize=(6.6, 2.4), dpi=200)
    y = list(range(len(DIFFS)))[::-1]
    for yi, (lab, m, lo, hi) in zip(y, DIFFS):
        c = "#1f5aa6" if lab.startswith("Model 6") else "#8a8a8a"
        ax.errorbar(m, yi, xerr=[[m - lo], [hi - m]], fmt="o", color=c, capsize=3, lw=1.6, ms=5)
    ax.axvline(0, color="#c0392b", lw=1, ls="--")
    ax.set_yticks(y, [d[0] for d in DIFFS], fontsize=8)
    ax.set_xlabel("Recall difference vs feature GBM at 1% FPR (95% source-bootstrap CI)", fontsize=8)
    ax.tick_params(axis="x", labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    ss = getSampleStyleSheet()
    body = ParagraphStyle("b", parent=ss["Normal"], fontName="DV", fontSize=9.2, leading=12.4, spaceAfter=4)
    h = ParagraphStyle("h", parent=body, fontName="DVB", fontSize=11, spaceBefore=8, spaceAfter=3, textColor=colors.HexColor("#1f3a5f"))
    title = ParagraphStyle("t", parent=body, fontName="DVB", fontSize=15, leading=19, spaceAfter=2)
    sub = ParagraphStyle("s", parent=body, fontSize=8.6, textColor=colors.HexColor("#555555"))
    small = ParagraphStyle("sm", parent=body, fontSize=8, leading=10.5, textColor=colors.HexColor("#444444"))
    bl = lambda items: [Paragraph(f"• {t}", ParagraphStyle("li", parent=body, leftIndent=10, firstLineIndent=-8)) for t in items]

    def table(rows, widths):
        t = Table(rows, colWidths=widths)
        t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "DV", 8.4), ("FONT", (0, 0), (-1, 0), "DVB", 8.4),
                               ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef6")),
                               ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#1f3a5f")),
                               ("LINEBELOW", (0, -1), (-1, -1), 0.4, colors.grey),
                               ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                               ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
        return t

    fig = HERE / "_poc_fig.png"
    figure(fig)
    s = [Paragraph("Proof of concept: identifying gravitationally lensed repeating FRBs from pair morphology", title),
         Paragraph("Track B (Siamese pair classifier), CHIME/FRB Catalog 2 · status 8 November 2026 · "
                   "<b>development results on semi-synthetic data; the test sets are still closed</b>", sub),
         Paragraph("Question", h),
         Paragraph("Can a neural network tell two lensed images of the same burst apart from two different bursts of the same "
                   "repeating source, and from impostor pairs that share propagation effects, better than cross-correlation, "
                   "a physics matched-filter statistic and a gradient-boosted model on measured burst features?", body),
         Paragraph("Data and setup", h),
         *bl(["<b>Pairs:</b> semi-synthetic, built from CHIME/FRB Catalog 2 fitburst templates injected into real off-pulse "
              "backgrounds (256 channels, 400–800 MHz, 0.98 ms). Each member gets independent nuisances: time shift, "
              "residual DM, scattering (τ ∝ ν<super>−4</super>) and scintillation.",
              "<b>Classes:</b> lensed (same template), repeat (two templates of one source), impostor (two templates sharing a "
              "plasma-lens gain I1, scintillation I2, or both) and unrelated (different sources).",
              "<b>Task and metric:</b> lensed vs repeat + impostor at pair S/N ≥ 25. Primary metric: recall at 1% false-positive "
              "rate, with 95% CIs from a bootstrap over sources (B = 2000). All rules were fixed before any learned result.",
              "<b>Models:</b> image-only inputs. Model 6 = shared CNN encoder + correlation layer over ±24 lags + symmetric "
              "fusion. Models 4, 5 and 7 (2-channel CNN, classic Siamese, cross-attention) are ablations. Comparator: the best "
              "of the three baselines on validation, which is the feature GBM.",
              "<b>Evaluation:</b> (a) fixed split, val_bright: 26 validation sources, 8000 pairs, 3 seeds per model; "
              "(b) rehearsal of the pre-registered grouped-fold design: 5 source-grouped folds over 60 development sources, "
              "out-of-fold (OOF) scores, final checkpoint, no selection."]),
         Paragraph("Results", h),
         Image(str(fig), width=16.5 * cm, height=6.0 * cm),
         Paragraph("Figure 1. Paired recall difference against the feature GBM. The dashed line is no difference.", small),
         Spacer(1, 4),
         table([["Method", "Fixed split recall (seeds)", "Grouped-fold OOF recall [95% CI]"],
                ["Feature GBM (best baseline)", "0.285 [0.180, 0.401]", "0.246 [0.199, 0.297]"],
                ["Model 6 (correlation layer)", "0.701 / 0.698 / 0.684", "0.467 [0.253, 0.662]"],
                ["Model 5 (classic Siamese)", "0.500 / 0.559 / 0.541", "not run"],
                ["Model 4 (2-channel CNN)", "0.423 / 0.409 / 0.407", "not run"],
                ["Model 7 (cross-attention)", "0.471 / 0.013 / 0.579", "not run"],
                ["Model 6 − GBM", "+0.394 [+0.226, +0.542]", "+0.220 [+0.035, +0.381]"]],
               [5.2 * cm, 5.0 * cm, 6.0 * cm]),
         Paragraph("Table 1. Recall at 1% FPR, lensed vs repeat + impostor, S/N ≥ 25. Fixed-split checkpoints were selected on "
                   "the same set, so those values are slightly optimistic; the OOF values use no selection.", small),
         Paragraph("Main findings", h),
         *bl(["<b>Model 6 beats the best baseline in both evaluations</b>; the lower CI bound is above zero each time. "
              "Its gain holds across S/N bins (val_bright recall 0.67–0.77 vs 0.23–0.52 for the GBM).",
              "<b>Explicit alignment matters:</b> the ranking is 6 > 5 > 4 in every seed. Model 6 vs 5 is +0.15 [−0.02, +0.35], "
              "so that step alone is not yet significant.",
              "<b>Hard negatives are impostors with a shared plasma-lens gain (I1, I1+I2)</b>, for every method. "
              "Shared scintillation alone (I2) and ordinary repeats are rarely confused.",
              "<b>A few sources set the threshold.</b> In one rehearsal fold, a source with only two bursts supplied about half "
              "of the false positives above the 1% threshold, and that fold's recall fell to 0.12. Results vary strongly between "
              "sources, which is why the CIs are wide (half-width 0.16–0.17).",
              "<b>Model 7 is seed-unstable:</b> one of three seeds collapsed on the chance plateau (diagnosed: representation "
              "collapse with uniform attention, not a code bug). It is reported as such and not used as a comparator."]),
         Paragraph("Checks already done", h),
         *bl(["Physics audit: dispersion constant and delay sign, residual-DM size, scattering kernel, time/frequency grid, "
              "scintillation statistics and S/N definition all verified.",
              "Logic audit: 0 construction-rule violations in 8000 pairs; nuisances (S/N, scattering, shift, member order) "
              "equal across classes, so there is no class leak; labels match end to end.",
              "Model self-checks: member-swap invariance, one-batch overfit, shuffled labels give AUC ≈ 0.5.",
              "Blinding: no model has scored real same-source pairs; the test split has not been opened."]),
         Paragraph("What this does not show yet", h),
         *bl(["<b>Transfer to real data (most important).</b> The models could exploit the smoothness of fitburst templates. "
              "The planned check uses real cross-source pairs: real FPR must be ≤ 2% at the simulated 1% threshold.",
              "<b>Final nuisance ranges.</b> Residual DM, scattering and scintillation depth are placeholders until the "
              "propagation module signs them off. One open modelling choice: template normalisation by the background's noise.",
              "<b>Held-out performance.</b> All numbers are from development sources that also guided design choices.",
              "<b>Real false-alarm rates.</b> Simulated FPRs only rank methods. The lensed class cannot be verified on real data."]),
         Paragraph("Next steps to a claimable result", h),
         Paragraph("1. Transfer checks on validation-split real cross-source pairs. 2. Sign-off of the nuisance ranges. "
                   "3. Freeze all methods, tag benchmark-v1, and run the pre-registered 5-fold grouped evaluation over all "
                   "80 sources once (about 9 GPU-hours). The claim stands only if the lower CI bound of model 6 − GBM is above zero.", body),
         Paragraph("<b>Bottom line:</b> in simulation, a Siamese network with an explicit correlation layer separates lensed "
                   "image pairs from repeats and impostors clearly better than physics and feature baselines. Whether this "
                   "survives real data is the next test.", body)]
    out = HERE / "trackB_poc_2026-11-08.pdf"
    SimpleDocTemplate(str(out), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                      title="Track B proof of concept", author="Track B, AI detection of lensed FRBs").build(s)
    fig.unlink()
    print(out)


if __name__ == "__main__":
    main()
