"""Vector diagrams for the ICAIIC paper, written as HTML + inline SVG and printed to PDF with headless Chrome.

  fig_concept.html  -> fig_concept.pdf   (a) a lensed repeating FRB, (b) why a transit telescope rarely records both copies
  fig_workflow.html -> fig_workflow.pdf  data -> pair simulator -> Siamese correlation network -> validation -> deployment
  fig_arch.html     -> fig_arch.pdf      model 6 in detail

Burst images are drawn from data: real CHIME/FRB Catalog 2 dynamic spectra (preprocessed, validation-free bright bursts)
and catalogue templates from the injection cache; the dispersed sweep in the concept figure is computed from the cold-plasma
delay law. SVG units: 1 unit = 0.01 inch, so the page size in inches is width/100 x height/100.
Usage: python make_diagrams.py [--no-render]
"""
import re
import subprocess
import sys
from pathlib import Path

import h5py
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRE = ROOT / "01_semi_synthetic_data" / "01_real_data" / "data" / "catalog2" / "preproc" / "repeaters_256x160.h5"
CACHE = ROOT / "02_injection_labelling" / "01_injection" / "data" / "inject_cache_256.h5"
CHROME = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]
RNG = np.random.default_rng(20261110)
INK, INK2, MUTED, LINE = "#1d1d1b", "#55544f", "#8a8984", "#c9c8c2"
BLUE, BLUE_SOFT, ORANGE, ORANGE_SOFT, GREEN, GREEN_SOFT, GREY_SOFT = (
    "#2a78d6", "#e3eefb", "#eb6834", "#fdebe3", "#2f9e6e", "#e2f3ea", "#efeeea")
DEFS = f"""<defs>
<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" fill="{INK2}"/></marker>
<marker id="ahb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" fill="{BLUE}"/></marker>
<marker id="aho" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" fill="{ORANGE}"/></marker>
<radialGradient id="glow" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#ffd27a"/><stop offset="45%" stop-color="#f6a04d"/>
<stop offset="100%" stop-color="#f6a04d" stop-opacity="0"/></radialGradient>
<radialGradient id="lens" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#fff4d6"/><stop offset="35%" stop-color="#f3d9a4"/>
<stop offset="75%" stop-color="#d9b77a" stop-opacity="0.55"/><stop offset="100%" stop-color="#d9b77a" stop-opacity="0"/></radialGradient>
<radialGradient id="host" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#cfe0f7"/><stop offset="60%" stop-color="#9dbbe6" stop-opacity="0.6"/>
<stop offset="100%" stop-color="#9dbbe6" stop-opacity="0"/></radialGradient>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#f4f7fc"/><stop offset="100%" stop-color="#ffffff"/></linearGradient>
</defs>"""


# ----------------------------------------------------------------------------------------------------------------- helpers
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


SUB = re.compile(r"([A-Za-z\u03c1\u2113\u0303]+)_([A-Za-z\u2113]+)")


def text(x, y, s, cls="t", anchor="start", extra=""):
    """SVG text; fill="..." in extra becomes an inline style (so it beats the CSS class); a_b becomes a subscript."""
    extra = re.sub(r'fill="([^"]+)"', r'style="fill:\1"', extra)
    s = SUB.sub(lambda m: f'{m.group(1)}<tspan baseline-shift="sub" font-size="72%">{m.group(2)}</tspan>', s)
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}" {extra}>{s}</text>'


def rect(x, y, w, h, fill="#fff", stroke=LINE, sw=0.8, rx=3, extra=""):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'


def arrow(x1, y1, x2, y2, color="ink", dashed=False, sw=1.1):
    mk = {"ink": "ah", "blue": "ahb", "orange": "aho"}[color]
    col = {"ink": INK2, "blue": BLUE, "orange": ORANGE}[color]
    da = ' stroke-dasharray="3 2.2"' if dashed else ""
    return f'<path d="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}" stroke="{col}" stroke-width="{sw}" fill="none"{da} marker-end="url(#{mk})"/>'


def cmap(v, hi=(20, 33, 61)):
    """White -> deep navy, gamma 0.8 for contrast."""
    v = float(np.clip(v, 0, 1)) ** 0.8
    r, g, b = (int(round(255 + (h - 255) * v)) for h in hi)
    return f"#{r:02x}{g:02x}{b:02x}"


_clip = [0]


def tile(x, y, w, h, img, mask=None, border=LINE, bw=0.8, rx=2.0):
    """A dynamic spectrum as a grid of cells; img rows run from high frequency (top) to low; values in [0, 1]."""
    _clip[0] += 1
    cid = f"c{_clip[0]}"
    nr, nc = img.shape
    dw, dh = w / nc, h / nr
    out = [f'<clipPath id="{cid}"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}"/></clipPath>',
           f'<g clip-path="url(#{cid})">']
    for i in range(nr):
        if mask is not None and mask[i]:
            out.append(f'<rect x="{x:.2f}" y="{y + i * dh:.2f}" width="{w:.2f}" height="{dh + 0.05:.2f}" fill="#f3f2ee"/>')
            continue
        for j in range(nc):
            out.append(f'<rect x="{x + j * dw:.2f}" y="{y + i * dh:.2f}" width="{dw + 0.05:.2f}" height="{dh + 0.05:.2f}" fill="{cmap(img[i, j])}"/>')
    out.append("</g>")
    out.append(rect(x, y, w, h, fill="none", stroke=border, sw=bw, rx=rx))
    return "\n".join(out)


def norm(img, lo=None, hi=None):
    a = np.arcsinh(img)
    lo = np.nanpercentile(a, 30) if lo is None else lo
    hi = np.nanpercentile(a, 99.7) if hi is None else hi
    return np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1)


def block(img, fr, tr):
    nf, nt = img.shape[0] // fr, img.shape[1] // tr
    return img[:nf * fr, :nt * tr].reshape(nf, fr, nt, tr).mean((1, 3))


def page(name, w, h, body, title):
    css = (HERE / "common.css").read_text()
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>
<style>@page {{ size: {w / 100:.2f}in {h / 100:.2f}in; margin: 0; }} {css}</style></head>
<body><svg xmlns="http://www.w3.org/2000/svg" width="{w / 100:.2f}in" height="{h / 100:.2f}in" viewBox="0 0 {w} {h}">
{DEFS}
{body}
</svg></body></html>"""
    (HERE / f"{name}.html").write_text(html, encoding="utf-8")


# ----------------------------------------------------------------------------------------------------------------- data
def real_tiles():
    """Bright real bursts (dedispersed), cropped around the emission and block-averaged to 32 x 40 cells."""
    out = []
    with h5py.File(PRE) as f:
        snr = np.nan_to_num(f["meta/snr_fitb"][:])
        lo, hi = f["meta/extent_lo"][:], f["meta/extent_hi"][:]
        for i in np.argsort(-snr)[:40]:
            x = f["X"][i].astype(float)
            fm = f["freq_mask"][i] >= 0.25
            if fm.mean() < 0.6:
                continue
            c = int((lo[i] + hi[i]) // 2)
            a = max(0, min(160 - 80, c - 40))
            x = np.where(fm[:, None], x, np.nan)[:, a:a + 80]
            img = block(np.nan_to_num(x), 8, 2)[::-1]
            m = block(fm[:, None].astype(float), 8, 1)[::-1, 0] < 0.5
            out.append((norm(img), m))
            if len(out) == 6:
                break
    return out


def templates():
    with h5py.File(CACHE) as f:
        T, src, ok = f["T"][:], f["meta/source"][:].astype(str), f["eligible"][:]
    return T, src, ok


def pair_images(T, src, ok):
    """Schematic members of the four classes, built like the injection: template(s) + fresh noise + masks."""
    s0 = "FRB20180916B"
    idx = np.flatnonzero((src == s0) & ok)
    big = idx[np.argsort(-np.abs(T[idx]).reshape(len(idx), -1).max(1))]
    other = np.flatnonzero((src != s0) & ok)
    oth = other[np.argsort(-np.abs(T[other]).reshape(len(other), -1).max(1))][3]

    def crop(t, shift=0):
        prof = np.abs(t).sum(0)
        c = int(np.argmax(prof))
        a = max(0, min(160 - 80, c - 40 + shift))
        return t[:, a:a + 80]

    def member(t, shift=0, env=None, seed=0):
        r = np.random.default_rng(seed)
        x = crop(t, shift) / (np.abs(t).max() + 1e-9) * 3.0
        if env is not None:
            x = x * env[:, None]
        scint = 1 + 0.35 * np.repeat(r.normal(size=32), 8)[:, None]
        x = x * scint + r.normal(0, 0.55, x.shape)
        m = np.zeros(256, bool)
        for k in r.choice(256, 6, replace=False):
            m[k:k + r.integers(3, 10)] = True
        img = block(np.where(m[:, None], 0, x), 8, 2)[::-1]
        return norm(img, lo=0.0, hi=np.percentile(np.arcsinh(img), 99.5)), block(m[:, None].astype(float), 8, 1)[::-1, 0] > 0.5

    a, b, c = big[0], big[1], big[2]
    sm = np.convolve(np.abs(T[a]).sum(1), np.ones(16) / 16, "same")
    env = sm / sm.max()
    return {"lensed": (member(T[a], 0, seed=1), member(T[a], 3, seed=2)),
            "repeat": (member(T[a], 0, seed=3), member(T[b], 0, seed=4)),
            "impostor": (member(T[a], 0, seed=5), member(T[c], 0, env=np.clip(env * 1.6, 0, 1), seed=6)),
            "unrelated": (member(T[a], 0, seed=7), member(T[oth], 0, seed=8))}


def dispersed(seed, dm_shape=1.0, scint=0.0, width=1.6, amp=1.0, scat=0.0, nf=36, nt=56, t0=10):
    """Cold-plasma sweep, t(nu) ~ nu^-2, drawn on noise; rows from 800 MHz (top) to 400 MHz.
    scat: scattering time at 400 MHz in samples, tau ~ nu^-4 (one-sided exponential tail)."""
    r = np.random.default_rng(seed)
    nu = np.linspace(0.8, 0.4, nf)
    delay = (nu ** -2 - 0.8 ** -2) / (0.4 ** -2 - 0.8 ** -2) * (nt - 2 * t0) * dm_shape
    t = np.arange(nt)
    gain = 1 + scint * r.normal(size=nf)
    img = np.exp(-0.5 * ((t[None] - t0 - delay[:, None]) / width) ** 2)
    if scat:
        for i, tau in enumerate(scat * (0.4 / nu) ** 4):
            k = np.exp(-np.arange(nt) / tau)
            img[i] = np.convolve(img[i], k / k.sum())[:nt]  # flux kept, so the peak drops as the tail grows
    img = amp * img * np.clip(gain, 0.2, None)[:, None]
    img += r.normal(0, 0.16, img.shape)
    return np.clip(img / 1.05, 0, 1)  # same noise scale for every copy, so a fainter copy looks fainter


# ----------------------------------------------------------------------------------------------------------------- figures
def fig_concept():
    W, H = 716, 214
    b = []
    # panel (a): lensing geometry
    b.append(rect(4, 4, 452, 206, fill="url(#sky)", stroke=LINE, rx=6))
    b.append(text(14, 20, "(a)", "tag") + text(34, 20, "A galaxy-lensed repeating FRB: every burst arrives twice", "th"))
    sx, sy, lx, ly, ox, oy = 46, 98, 196, 98, 356, 98
    b.append(f'<ellipse cx="{sx}" cy="{sy}" rx="30" ry="18" fill="url(#host)"/>')
    b.append(f'<circle cx="{sx}" cy="{sy}" r="11" fill="url(#glow)"/>')
    for k in range(8):
        ang = k * np.pi / 4
        b.append(f'<line x1="{sx + 3 * np.cos(ang):.1f}" y1="{sy + 3 * np.sin(ang):.1f}" x2="{sx + 7.5 * np.cos(ang):.1f}" '
                 f'y2="{sy + 7.5 * np.sin(ang):.1f}" stroke="{ORANGE}" stroke-width="1"/>')
    b.append(f'<circle cx="{sx}" cy="{sy}" r="2.4" fill="{ORANGE}"/>')
    b.append(text(sx, 134, "repeating FRB", "ts", "middle") + text(sx, 144, "source", "ts", "middle"))
    b.append(f'<ellipse cx="{lx}" cy="{ly}" rx="34" ry="22" fill="url(#lens)"/>')
    b.append(f'<ellipse cx="{lx}" cy="{ly}" rx="9" ry="6" fill="#f7e2b5" stroke="#d2ad6c" stroke-width="0.6"/>')
    b.append(text(lx + 38, ly + 3, "lens galaxy", "ts"))
    # paths: image 1 (short) above, image 2 (long) below
    b.append(f'<path d="M{sx + 8},{sy - 3} Q{lx},{ly - 62} {ox - 26},{oy - 6}" stroke="{BLUE}" stroke-width="1.4" fill="none" marker-end="url(#ahb)"/>')
    b.append(f'<path d="M{sx + 8},{sy + 3} Q{lx},{ly + 70} {ox - 26},{oy + 6}" stroke="{ORANGE}" stroke-width="1.4" fill="none" stroke-dasharray="4 2.4" marker-end="url(#aho)"/>')
    b.append(text(lx, 52, "image 1", "ts", "middle", f'fill="{BLUE}"'))
    b.append(text(lx, 158, "image 2: longer path, arrives Δt later, fainter", "ts", "middle", f'fill="{ORANGE}"'))
    # telescope (cylinder reflector)
    b.append(f'<path d="M{ox - 18},{oy - 10} Q{ox},{oy + 14} {ox + 18},{oy - 10}" fill="#eef1f5" stroke="{INK2}" stroke-width="1.1"/>')
    b.append(f'<line x1="{ox}" y1="{oy - 10}" x2="{ox}" y2="{oy + 2}" stroke="{INK2}" stroke-width="0.8"/>')
    b.append(f'<line x1="{ox - 22}" y1="{oy + 10}" x2="{ox + 22}" y2="{oy + 10}" stroke="{INK2}" stroke-width="1"/>')
    b.append(text(ox, oy + 24, "CHIME", "ts", "middle"))
    # two dispersed copies of one burst at the observer
    c1 = dispersed(11, scint=0.25)
    c2 = dispersed(12, scint=0.45, amp=0.7, scat=2.5)
    b.append(tile(386, 34, 56, 44, c1, border=BLUE, bw=1.1))
    b.append(tile(386, 114, 56, 44, c2, border=ORANGE, bw=1.1))
    b.append(text(414, 30, "copy 1", "tx", "middle") + text(414, 170, "copy 2: same burst,", "tx", "middle"))
    b.append(text(414, 179, "new propagation imprint", "tx", "middle"))
    b.append(text(382, 40, "800", "tx", "end") + text(382, 78, "400", "tx", "end") + text(382, 59, "MHz", "tx", "end"))
    # burst timeline: every burst repeats after the same delay
    ty = 196
    b.append(f'<line x1="22" y1="{ty}" x2="440" y2="{ty}" stroke="{INK2}" stroke-width="0.9" marker-end="url(#ah)"/>')
    b.append(text(436, ty + 11, "time", "tx", "end"))
    t1 = [38, 60, 82, 115, 145]  # no burst may sit on another burst's copy (t + dt)
    dt = 132
    for t in t1:
        b.append(f'<line x1="{t}" y1="{ty - 9}" x2="{t}" y2="{ty}" stroke="{BLUE}" stroke-width="2"/>')
        b.append(f'<line x1="{t + dt}" y1="{ty - 6}" x2="{t + dt}" y2="{ty}" stroke="{ORANGE}" stroke-width="2"/>')
    b.append(f'<path d="M{t1[0]},{ty - 13} L{t1[0] + dt},{ty - 13}" stroke="{INK2}" stroke-width="0.8" marker-start="url(#ah)" marker-end="url(#ah)"/>')
    b.append(text(t1[0] + dt / 2, ty - 16, "Δt (days–months), identical for every burst", "tx", "middle"))
    # panel (b): transit alignment
    X0 = 464
    b.append(rect(X0, 4, 248, 206, fill="#ffffff", stroke=LINE, rx=6))
    b.append(text(X0 + 10, 20, "(b)", "tag") + text(X0 + 30, 20, "A transit telescope sees each source", "th"))
    b.append(text(X0 + 30, 33, "for minutes per sidereal day", "th"))
    ax0, ax1 = X0 + 16, X0 + 236
    days = 4
    per = (ax1 - ax0) / days
    win = 6.0

    def row(y, label, sub, frac, ok):
        out = [text(ax0, y - 31, label, "tb"), text(ax0, y - 21, sub, "tx")]
        out.append(f'<line x1="{ax0}" y1="{y}" x2="{ax1}" y2="{y}" stroke="{INK2}" stroke-width="0.8"/>')
        for d in range(days):
            cx = ax0 + per * (d + 0.5)
            out.append(f'<rect x="{cx - win:.1f}" y="{y - 14}" width="{2 * win:.1f}" height="20" fill="{ORANGE_SOFT}" stroke="none"/>')
            out.append(f'<line x1="{ax0 + per * d:.1f}" y1="{y - 2}" x2="{ax0 + per * d:.1f}" y2="{y + 2}" stroke="{MUTED}" stroke-width="0.6"/>')
        for d in (0, 1):
            cx = ax0 + per * (d + 0.5) + (1.5 if d else -1.5)
            out.append(f'<line x1="{cx:.1f}" y1="{y - 11}" x2="{cx:.1f}" y2="{y}" stroke="{BLUE}" stroke-width="2"/>')
            cc = cx + per * (2 + frac)
            col = ORANGE if ok else MUTED
            out.append(f'<line x1="{cc:.1f}" y1="{y - 8}" x2="{cc:.1f}" y2="{y}" stroke="{col}" stroke-width="2"' + ("" if ok else ' stroke-dasharray="2 1.5"') + '/>')
            out.append(f'<path d="M{cx:.1f},{y + 6} Q{(cx + cc) / 2:.1f},{y + 18} {cc:.1f},{y + 6}" stroke="{col}" stroke-width="0.7" fill="none" marker-end="url(#{"aho" if ok else "ah"})"/>')
        mark = "✓ copies recorded" if ok else "✗ copies missed"
        out.append(text(ax1, y - 31, mark, "ts", "end", f'fill="{GREEN if ok else ORANGE}"'))
        return out

    b += row(94, "Δt ≠ n·T_sid", "copies arrive between transits", 0.37, False)
    b += row(150, "Δt ≈ n·T_sid (within minutes)", "copies arrive inside the window", 0.0, True)
    for d in range(days):
        b.append(text(ax0 + per * (d + 0.5), 168, f"day {d + 1}", "tx", "middle"))
    b.append(rect(ax0, 173, ax1 - ax0, 34, fill=GREY_SOFT, stroke="none", rx=4))
    b.append(text((ax0 + ax1) / 2, 186, "p_align ≈ 2 × window / T_sid ≈ 2% of lenses", "t", "middle"))
    b.append(text((ax0 + ax1) / 2, 201, "the same for all bursts of a source: all copies or none", "tx", "middle"))
    b.append(rect(ax0 + 2, 40, 9, 7, fill=ORANGE_SOFT, stroke="none", rx=1) + text(ax0 + 14, 46, "transit window", "tx"))
    b.append(f'<line x1="{ax0 + 80}" y1="{47}" x2="{ax0 + 80}" y2="{40}" stroke="{BLUE}" stroke-width="2"/>' + text(ax0 + 84, 46, "recorded burst", "tx"))
    b.append(f'<line x1="{ax0 + 150}" y1="{47}" x2="{ax0 + 150}" y2="{40}" stroke="{ORANGE}" stroke-width="2"/>' + text(ax0 + 154, 46, "its copy", "tx"))
    page("fig_concept", W, H, "\n".join(b), "Lensed FRB concept")


def fig_workflow(reals, pairs):
    W, H = 716, 236
    b = []
    cols = [(4, 146, "1", "Real CHIME data"), (162, 178, "2", "Pair simulator"), (352, 156, "3", "Siamese correlation net"),
            (520, 192, "4", "Validation, no real positives")]
    for x, w, n, title in cols:
        b.append(rect(x, 4, w, 176, fill="#fbfaf7", stroke=LINE, rx=6))
        b.append(f'<circle cx="{x + 14}" cy="17" r="8" fill="{INK}"/>' + text(x + 14, 20.5, n, "tx", "middle", 'fill="#fff" font-weight="bold"'))
        b.append(text(x + 27, 21, title, "th"))
    for x0, x1 in ((150, 162), (340, 352), (508, 520)):
        b.append(arrow(x0 + 1, 92, x1 - 1, 92, sw=1.4))
    # 1: real bursts
    for k, (img, m) in enumerate(reals[:3]):
        b.append(tile(18 + k * 9, 34 + k * 9, 70, 56, img, mask=m, border="#9a998f"))
    b.append(tile(104, 34, 40, 32, reals[3][0], mask=reals[3][1], border="#9a998f"))
    b.append(tile(104, 72, 40, 32, reals[4][0], mask=reals[4][1], border="#9a998f"))
    b.append(text(14, 122, "981 bursts · 83 repeaters", "t"))
    b.append(text(14, 134, "Catalog 2, 400–800 MHz", "ts"))
    b.append(text(14, 150, "→ 950 noise-free templates", "ts"))
    b.append(text(14, 161, "→ 856 real noise backgrounds", "ts"))
    b.append(text(14, 172, "bursts split 60/20/20, by source", "tx"))
    # 2: four classes
    names = [("lensed", "same burst twice", BLUE), ("repeat", "two bursts, one source", INK2),
             ("impostor", "shared imprint", ORANGE), ("unrelated", "two sources", MUTED)]
    for k, (nm, sub, col) in enumerate(names):
        gx, gy = 170 + (k % 2) * 86, 32 + (k // 2) * 66
        (ia, ma), (ib, mb) = pairs[nm]
        b.append(tile(gx, gy + 12, 38, 30, ia, mask=ma, border=col, bw=1.1 if nm in ("lensed", "impostor") else 0.8))
        b.append(tile(gx + 42, gy + 12, 38, 30, ib, mask=mb, border=col, bw=1.1 if nm in ("lensed", "impostor") else 0.8))
        b.append(text(gx, gy + 8, nm, "tb", extra=f'fill="{col}"'))
        b.append(text(gx, gy + 52, sub, "tx"))
    b.append(text(170, 165, "+ nuisances per member: time shift, ΔDM,", "tx"))
    b.append(text(170, 174, "scattering, scintillation; frozen, hashed sets", "tx"))
    # 3: network sketch
    y0 = 40
    b.append(tile(364, y0, 30, 24, pairs["lensed"][0][0], border=BLUE))
    b.append(tile(364, y0 + 32, 30, 24, pairs["lensed"][1][0], border=BLUE))
    b.append(f'<path d="M408,{y0 + 2} L436,{y0 + 8} L436,{y0 + 18} L408,{y0 + 24} z" fill="{GREY_SOFT}" stroke="#9a998f" stroke-width="0.8"/>')
    b.append(f'<path d="M408,{y0 + 34} L436,{y0 + 40} L436,{y0 + 50} L408,{y0 + 56} z" fill="{GREY_SOFT}" stroke="#9a998f" stroke-width="0.8"/>')
    b.append(text(414, y0 + 31, "g", "tx it", "middle"))
    b.append(rect(436, y0 + 10, 44, 36, fill=ORANGE_SOFT, stroke="#e3a88b", rx=3))
    xs = np.linspace(440, 476, 25)
    prof = np.exp(-0.5 * ((xs - 462) / 3.5) ** 2) * 0.9 + 0.08 * np.random.default_rng(3).normal(size=25)
    pts = " ".join(f"{x:.1f},{y0 + 42 - 26 * p:.1f}" for x, p in zip(xs, prof))
    b.append(f'<polyline points="{pts}" fill="none" stroke="{ORANGE}" stroke-width="1"/>')
    b.append(text(458, y0 + 6, "align ρ(ℓ)", "tx", "middle"))
    b.append(arrow(429, y0 + 13, 435, y0 + 22) + arrow(429, y0 + 45, 435, y0 + 36))
    b.append(f'<circle cx="494" cy="{y0 + 28}" r="10" fill="{GREEN_SOFT}" stroke="{GREEN}" stroke-width="0.9"/>')
    b.append(text(494, y0 + 31, "fuse", "tx", "middle"))
    b.append(arrow(481, y0 + 28, 484, y0 + 28))
    b.append(text(364, y0 + 74, "1. shared encoder, 2-sample resolution", "tx"))
    b.append(text(364, y0 + 84, "2. soft alignment over ±24 samples", "tx"))
    b.append(text(364, y0 + 94, "3. fuse |g_A − g_B| and g_A ⊙ g_B", "tx"))
    b.append(text(364, y0 + 104, "4. 4-class head → score s(A, B)", "tx"))
    b.append(rect(364, 152, 136, 20, fill=BLUE_SOFT, stroke="none", rx=4))
    b.append(text(432, 165, "259k parameters", "t", "middle", f'fill="{BLUE}"'))
    # 4: validation rows
    rows = [("Pre-registered test", "all 80 sources, run once", "+0.23 recall"),
            ("Real cross-source pairs", "vs per-pair twins", "FPR \u2248 1%"),
            ("Real-burst copies", "vs template copies", "ratio 0.97"),
            ("Second-machine rerun", "data, sets, training", "7/7 hashes")]
    for k, (a, s_, badge) in enumerate(rows):
        y = 34 + k * 36
        b.append(rect(528, y, 176, 30, fill="#ffffff", stroke=LINE, rx=4))
        b.append(f'<circle cx="539" cy="{y + 15}" r="4.5" fill="{GREEN}"/>' + text(539, y + 18, "\u2713", "tx", "middle", 'fill="#fff"'))
        b.append(text(548, y + 13, a, "tx", extra=f'fill="{INK}"') + text(548, y + 24, s_, "tx"))
        b.append(rect(646, y + 9, 54, 13, fill=GREEN_SOFT, stroke="none", rx=3))
        b.append(text(673, y + 18.5, badge, "tx", "middle", f'fill="{GREEN}" font-weight="bold"'))
    # deployment strip
    b.append(rect(4, 188, 708, 44, fill=GREY_SOFT, stroke="none", rx=6))
    b.append(f'<circle cx="18" cy="210" r="8" fill="{INK}"/>' + text(18, 213.5, "5", "tx", "middle", 'fill="#fff" font-weight="bold"'))
    b.append(text(32, 205, "Deployment: where can the detector work?", "th"))
    b.append(text(32, 220, "Timing test on burst lists (false alarms checked on 166,000 scrambles) and survey-geometry simulation "
                           "→ copies are recorded for only ~2% of lenses at a transit telescope;", "ts"))
    b.append(text(32, 230, "an all-sky monitor watching the same sources would find ~50× more lensed repeaters.", "ts"))
    page("fig_workflow", W, H, "\n".join(b), "Workflow")


def fig_arch(pairs):
    W, H = 716, 178
    b = []
    (ia, ma), (ib, mb) = pairs["lensed"]
    b.append(tile(8, 22, 54, 42, ia, mask=ma, border=BLUE, bw=1.1) + text(35, 16, "burst A", "ts", "middle"))
    b.append(tile(8, 104, 54, 42, ib, mask=mb, border=BLUE, bw=1.1) + text(35, 158, "burst B", "ts", "middle"))
    b.append(text(8, 170, "256 × 160 (freq × time)", "tx"))
    # encoder trapezoids
    for y in (22, 104):
        b.append(f'<path d="M74,{y} L132,{y + 9} L132,{y + 33} L74,{y + 42} z" fill="{GREY_SOFT}" stroke="#9a998f" stroke-width="0.9"/>')
        b.append(text(103, y + 19, "asinh +", "tx", "middle") + text(103, y + 29, "4 conv blocks", "tx", "middle"))
        b.append(arrow(63, y + 21, 73, y + 21))
    b.append(f'<path d="M103,66 L103,102" stroke="{MUTED}" stroke-width="0.9" stroke-dasharray="2 2"/>')
    b.append(text(107, 87, "shared g", "tx"))
    # feature-map stacks
    def stack(x, y, col):
        out = []
        for k in range(4):
            out.append(rect(x + k * 3, y + k * 2.5, 30, 20, fill=col, stroke="#9a998f", sw=0.6, rx=1.5))
        return "".join(out)
    b.append(stack(142, 30, "#eef3fb") + text(162, 24, "g_A", "ts it", "middle"))
    b.append(stack(142, 112, "#eef3fb") + text(162, 152, "g_B", "ts it", "middle"))
    b.append(text(162, 168, "64 × 16 × 80", "tx", "middle"))
    b.append(arrow(133, 43, 141, 43) + arrow(133, 125, 141, 125))
    # correlation layer with a computed profile
    cx0 = 196
    b.append(rect(cx0, 52, 104, 74, fill=ORANGE_SOFT, stroke="#e3a88b", rx=4))
    b.append(text(cx0 + 52, 64, "correlation layer", "tb", "middle"))
    ta = ia.mean(0)
    tb = ib.mean(0)
    lags = np.arange(-12, 13)
    rho = np.array([np.corrcoef(ta, np.roll(tb, -l))[0, 1] for l in lags])
    rho = (rho - rho.min()) / (rho.max() - rho.min() + 1e-9)
    px = np.linspace(cx0 + 10, cx0 + 94, len(lags))
    pts = " ".join(f"{x:.1f},{112 - 34 * r:.1f}" for x, r in zip(px, rho))
    b.append(f'<line x1="{cx0 + 10}" y1="112" x2="{cx0 + 94}" y2="112" stroke="{MUTED}" stroke-width="0.6"/>')
    b.append(f'<polyline points="{pts}" fill="none" stroke="{ORANGE}" stroke-width="1.3"/>')
    k = int(np.argmax(rho))
    b.append(f'<circle cx="{px[k]:.1f}" cy="{112 - 34 * rho[k]:.1f}" r="2" fill="{ORANGE}"/>')
    b.append(text(cx0 + 52, 122, "ρ(ℓ), lags ±24 samples", "tx", "middle"))
    b.append(arrow(176, 44, cx0 - 1, 70) + arrow(176, 126, cx0 - 1, 108))
    # softmax weights + soft alignment
    sx0 = 316
    b.append(rect(sx0, 52, 92, 74, fill="#ffffff", stroke=LINE, rx=4))
    b.append(text(sx0 + 46, 64, "soft alignment", "tb", "middle"))
    w = np.exp(10 * (rho - 1))
    w /= w.sum()
    bx = np.linspace(sx0 + 10, sx0 + 82, len(lags))
    for x, v in zip(bx, w):
        b.append(f'<rect x="{x - 1.2:.1f}" y="{100 - 30 * v / w.max():.1f}" width="2.4" height="{30 * v / w.max():.1f}" fill="{ORANGE}"/>')
    b.append(f'<line x1="{sx0 + 8}" y1="100" x2="{sx0 + 84}" y2="100" stroke="{MUTED}" stroke-width="0.6"/>')
    b.append(text(sx0 + 46, 111, "w_ℓ ∝ exp(β ρ(ℓ))", "tx", "middle") + text(sx0 + 46, 121, "g̃_B = Σ w_ℓ g_B(ℓ)", "tx", "middle"))
    b.append(arrow(301, 89, sx0 - 1, 89))
    # fusion
    fx = 432
    b.append(f'<circle cx="{fx}" cy="70" r="11" fill="{GREEN_SOFT}" stroke="{GREEN}" stroke-width="1"/>' + text(fx, 73.5, "|−|", "t", "middle"))
    b.append(f'<circle cx="{fx}" cy="108" r="11" fill="{GREEN_SOFT}" stroke="{GREEN}" stroke-width="1"/>' + text(fx, 112, "⊙", "t", "middle"))
    b.append(arrow(409, 82, fx - 11, 72) + arrow(409, 96, fx - 11, 106))
    b.append(text(fx - 4, 47, "fusion", "tb", "end"))
    b.append(f'<path d="M176,40 C 300,10 400,14 {fx},58" stroke="{MUTED}" stroke-width="0.8" fill="none" stroke-dasharray="2 2" marker-end="url(#ah)"/>')
    b.append(text(300, 20, "g_A", "tx it", "middle"))
    # head
    hx = 460
    b.append(stack(hx, 76, GREEN_SOFT))
    b.append(arrow(fx + 11, 70, hx - 1, 84) + arrow(fx + 11, 108, hx - 1, 92))
    b.append(text(hx + 15, 70, "128 ch.", "tx", "middle"))
    b.append(rect(510, 66, 56, 46, fill="#ffffff", stroke=LINE, rx=4))
    b.append(text(538, 82, "2 conv", "tx", "middle") + text(538, 92, "mean + max", "tx", "middle") + text(538, 102, "pool", "tx", "middle"))
    b.append(arrow(495, 89, 509, 89))
    # correlation profile skip
    b.append(f'<path d="M248,127 C 260,165 520,170 596,116" stroke="{ORANGE}" stroke-width="0.9" fill="none" stroke-dasharray="3 2" marker-end="url(#aho)"/>')
    b.append(text(420, 165, "correlation profile ρ also feeds the head", "tx", "middle", f'fill="{ORANGE}"'))
    # MLP
    mx = 580
    for i, n in enumerate((4, 5, 4)):
        for j in range(n):
            yy = 89 + (j - (n - 1) / 2) * 10
            b.append(f'<circle cx="{mx + i * 16}" cy="{yy:.1f}" r="3" fill="#ffffff" stroke="{INK2}" stroke-width="0.8"/>')
    b.append(arrow(567, 89, mx - 5, 89))
    b.append(text(mx + 16, 61, "MLP", "tx", "middle"))  # above the nodes: the profile arrow enters from below
    # outputs
    ox0 = 628
    labs = [("lensed", 0.82, BLUE), ("repeat", 0.08, INK2), ("unrelated", 0.04, MUTED), ("impostor", 0.06, ORANGE)]
    for i, (lab, p, col) in enumerate(labs):
        y = 62 + i * 15
        b.append(rect(ox0, y, 62 * p + 1, 9, fill=col, stroke="none", rx=1.5))
        b.append(text(ox0 + 64 * p + 4, y + 8, lab, "tx"))
    b.append(arrow(mx + 36, 89, ox0 - 2, 89))
    b.append(text(ox0, 54, "4 logits", "tb"))
    b.append(text(ox0, 132, "score = log-odds of", "tx") + text(ox0, 141, "lensed vs. the rest;", "tx"))
    b.append(text(ox0, 150, "both orders averaged", "tx"))
    page("fig_arch", W, H, "\n".join(b), "Model 6 architecture")


def render(name):
    exe = next(p for p in CHROME if Path(p).exists())
    src = (HERE / f"{name}.html").as_uri()
    out = HERE.parent / f"{name}.pdf"
    subprocess.run([exe, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--no-margins",
                    f"--print-to-pdf={out}", src], check=True, capture_output=True, timeout=120)
    return out


def main():
    reals = real_tiles()
    T, src, ok = templates()
    pairs = pair_images(T, src, ok)
    fig_concept()
    fig_workflow(reals, pairs)
    fig_arch(pairs)
    if "--no-render" not in sys.argv:
        for n in ("fig_concept", "fig_workflow", "fig_arch"):
            print("wrote", render(n))


if __name__ == "__main__":
    main()
