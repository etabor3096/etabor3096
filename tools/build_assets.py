"""Generate the SVG assets for the GitHub profile README.

Every piece of text is converted to outlines, so the art renders the same on
any machine no matter which fonts it has. Each asset is written twice, once
for GitHub's dark theme and once for its light theme.

Fonts (both SIL Open Font License, from github.com/google/fonts):
  Space Grotesk   ofl/spacegrotesk/SpaceGrotesk[wght].ttf
  JetBrains Mono  ofl/jetbrainsmono/JetBrainsMono[wght].ttf

Usage:
  pip install fonttools uharfbuzz pillow
  sh tools/fetch_screens.sh        # app screenshots, from the project repos
  python tools/build_assets.py --fonts <dir with the two .ttf files>
"""

import argparse
import base64
import math
from io import BytesIO
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"

PALETTES = {
    "dark": dict(
        page="#0d1117", card="#10151c", card2="#161c25", line="#272e39",
        text="#e6edf3", muted="#8b949e", faint="#353d49",
        acc="#f5a524", acc2="#4cc9a6", onacc="#1b1205", term="#090c10",
        termtext="#d6dde6",
    ),
    "light": dict(
        page="#ffffff", card="#f6f8fa", card2="#eceff3", line="#d6dce3",
        text="#1f2328", muted="#5b6570", faint="#c9d1d9",
        acc="#c46a00", acc2="#11806a", onacc="#ffffff", term="#161b22",
        termtext="#d6dde6",
    ),
}


def fmt(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


class Font:
    def __init__(self, path, wght):
        data = Path(path).read_bytes()
        self.hb_font = hb.Font(hb.Face(data))
        self.hb_font.set_variations({"wght": wght})
        tt = instantiateVariableFont(TTFont(path), {"wght": wght})
        self.glyphs = tt.getGlyphSet()
        self.order = tt.getGlyphOrder()
        self.upm = tt["head"].unitsPerEm

    def _shape(self, text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf, {"kern": True, "liga": False, "calt": False})
        return buf.glyph_infos, buf.glyph_positions

    def width(self, text, size, track=0.0):
        _, pos = self._shape(text)
        return sum(p.x_advance for p in pos) * size / self.upm + track * max(len(text) - 1, 0)

    def path(self, text, size, x, y, anchor="start", track=0.0):
        """Outline path for `text` with its baseline at y."""
        w = self.width(text, size, track)
        if anchor == "middle":
            x -= w / 2
        elif anchor == "end":
            x -= w
        s = size / self.upm
        pen = SVGPathPen(self.glyphs, ntos=fmt)
        infos, pos = self._shape(text)
        cx = x
        for info, p in zip(infos, pos):
            name = self.order[info.codepoint]
            t = TransformPen(pen, (s, 0, 0, -s, cx + p.x_offset * s, y - p.y_offset * s))
            self.glyphs[name].draw(t)
            cx += p.x_advance * s + track
        return pen.getCommands()


DISPLAY = MEDIUM = MONO = MONO_B = None


def load_fonts(font_dir):
    global DISPLAY, MEDIUM, MONO, MONO_B
    d = Path(font_dir)
    DISPLAY = Font(d / "SpaceGrotesk.ttf", 700)
    MEDIUM = Font(d / "SpaceGrotesk.ttf", 500)
    MONO = Font(d / "JetBrainsMono.ttf", 400)
    MONO_B = Font(d / "JetBrainsMono.ttf", 700)


def txt(font, text, size, x, y, fill, anchor="start", track=0.0, cls=None, extra=""):
    c = f' class="{cls}"' if cls else ""
    return f'<path{c} fill="{fill}" {extra} d="{font.path(text, size, x, y, anchor, track)}"/>'


def svg(w, h, label, body, style=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{label}">\n'
        f"<title>{label}</title>\n<style>{style}</style>\n{body}\n</svg>\n"
    )


REDUCED = "@media (prefers-reduced-motion:reduce){*{animation:none!important}.motion{display:none}}"


def write(name, theme, content):
    path = OUT / f"{name}-{theme}.svg"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


# ---------------------------------------------------------------- header

def header(c):
    W, H = 840, 222
    parts = []
    parts.append(txt(DISPLAY, "Elijah Tabor", 74, -3, 72, c["text"], track=-1.2))
    name_w = DISPLAY.width("Elijah Tabor", 74, -1.2)
    parts.append(f'<circle cx="{fmt(name_w + 12)}" cy="64" r="7" fill="{c["acc"]}"/>')
    parts.append(txt(MONO, "TUNING E STANDARD  ·  96 BPM  ·  4/4", 10.5, W, 18, c["muted"], "end", 0.6))

    top, gap, x0, x1 = 106, 14, 24, W - 2
    strings = "eBGDAE"
    for i, s in enumerate(strings):
        y = top + i * gap
        parts.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{c["faint"]}" stroke-width="1"/>')
        parts.append(txt(MONO, s, 10.5, 0, y + 3.8, c["muted"]))
    bars = [x0, 228, 432, 636]
    for bx in bars:
        parts.append(f'<line x1="{bx}" y1="{top}" x2="{bx}" y2="{top + 5 * gap}" stroke="{c["muted"]}" stroke-width="1.2"/>')
    parts.append(f'<line x1="{x1 - 6}" y1="{top}" x2="{x1 - 6}" y2="{top + 5 * gap}" stroke="{c["muted"]}" stroke-width="1.2"/>')
    parts.append(f'<line x1="{x1}" y1="{top}" x2="{x1}" y2="{top + 5 * gap}" stroke="{c["muted"]}" stroke-width="3"/>')

    # A fingerpicked progression: Em, C, G, D (string index 0 = high e).
    riff = [
        [(5, "0"), (3, "2"), (2, "0"), (1, "0"), (0, "0"), (1, "0"), (2, "0"), (3, "2")],
        [(4, "3"), (3, "2"), (2, "0"), (1, "1"), (0, "0"), (1, "1"), (2, "0"), (3, "2")],
        [(5, "3"), (3, "0"), (2, "0"), (1, "0"), (0, "3"), (1, "0"), (2, "0"), (3, "0")],
        [(4, "0"), (3, "0"), (2, "2"), (1, "3"), (0, "2"), (1, "3"), (2, "2"), (0, "5")],
    ]
    period, sweep = 9.0, 7.2
    span = (x1 - 6) - x0
    styles = []
    for b, notes in enumerate(riff):
        start = bars[b] if b < 3 else 636
        end = bars[b + 1] if b < 3 else x1 - 6
        step = (end - start) / 8
        for n, (si, fret) in enumerate(notes):
            x = start + step * (n + 0.5)
            y = top + si * gap
            delay = sweep * (x - x0) / span
            parts.append(f'<rect x="{fmt(x - 6)}" y="{y - 7}" width="12" height="14" fill="{c["page"]}"/>')
            parts.append(txt(MONO_B, fret, 11.5, x, y + 4.2, c["muted"], "middle",
                             cls="n", extra=f'style="animation-delay:{delay:.2f}s"'))
    styles.append(
        f".n{{animation:hit {period}s linear infinite}}"
        f"@keyframes hit{{0%{{fill:{c['acc']}}}6%{{fill:{c['acc']}}}14%,100%{{fill:{c['muted']}}}}}"
    )
    # Playhead
    pct = sweep / period * 100
    styles.append(
        f".ph{{animation:sweep {period}s linear infinite}}"
        f"@keyframes sweep{{0%{{transform:translateX(0);opacity:1}}{pct:.1f}%{{transform:translateX({span}px);opacity:1}}"
        f"{pct + 3:.1f}%,100%{{transform:translateX({span}px);opacity:0}}}}"
    )
    parts.append(
        f'<defs><linearGradient id="glow" x1="0" x2="1"><stop offset="0" stop-color="{c["acc"]}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{c["acc"]}" stop-opacity=".22"/></linearGradient></defs>'
        f'<g class="ph motion"><rect x="{x0 - 40}" y="{top - 10}" width="40" height="{5 * gap + 20}" fill="url(#glow)"/>'
        f'<line x1="{x0}" y1="{top - 10}" x2="{x0}" y2="{top + 5 * gap + 10}" stroke="{c["acc"]}" stroke-width="2"/></g>'
    )

    y = 210
    a = "›  now building  "
    b = "amphion"
    d = "  —  songs in, playable guitar tabs out"
    xa = 0
    parts.append(txt(MONO, a, 13, xa, y, c["muted"]))
    xb = xa + MONO.width(a, 13)
    parts.append(txt(MONO_B, b, 13, xb, y, c["acc"]))
    parts.append(txt(MONO, d, 13, xb + MONO_B.width(b, 13), y, c["muted"]))
    return svg(W, H, "Elijah Tabor. Now building Amphion: songs in, playable guitar tabs out.",
               "\n".join(parts), "".join(styles) + REDUCED)


# ---------------------------------------------------------------- headings

def heading(c, index, title):
    W, H = 840, 58
    parts = [txt(MONO_B, index, 13, 0, 37, c["acc"])]
    tx = 34
    parts.append(txt(MEDIUM, title, 31, tx, 39, c["text"], track=-0.3))
    end = tx + MEDIUM.width(title, 31, -0.3) + 20
    parts.append(f'<line x1="{fmt(end)}" y1="28" x2="826" y2="28" stroke="{c["line"]}" stroke-width="1"/>')
    for k in range(1, 4):
        tick = end + (826 - end) * k / 4
        parts.append(f'<line x1="{fmt(tick)}" y1="24" x2="{fmt(tick)}" y2="32" stroke="{c["line"]}" stroke-width="1"/>')
    parts.append(f'<circle cx="833" cy="28" r="4.5" fill="{c["acc"]}"/>')
    return svg(W, H, title, "\n".join(parts))


# ---------------------------------------------------------------- buttons

def button(c, label, primary=False, icon=None):
    size, track, padx, h = 11.5, 1.1, 16, 34
    tw = MONO_B.width(label, size, track)
    iw = 16 if icon else 0
    w = math.ceil(tw + iw + 2 * padx)
    fill = c["acc"] if primary else c["card"]
    stroke = c["acc"] if primary else c["line"]
    color = c["onacc"] if primary else c["text"]
    parts = [f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="7" fill="{fill}" stroke="{stroke}"/>']
    x = padx
    if icon == "play":
        parts.append(f'<path d="M{x} 11.5 L{x + 8} 17 L{x} 22.5Z" fill="{color}"/>')
        x += iw
    elif icon == "arrow":
        parts.append(f'<path d="M{x} 21 L{x + 7} 14 M{x + 2} 13.5 H{x + 7.5} V19" stroke="{color}" stroke-width="1.6" fill="none" stroke-linecap="round"/>')
        x += iw
    parts.append(txt(MONO_B, label, size, x, 21.3, color, track=track))
    return svg(w, h, label.title(), "\n".join(parts))


# ---------------------------------------------------------------- card chrome

def chrome(c, W, H, path, status, status_acc=True):
    col = c["acc"] if status_acc else c["muted"]
    sw = MONO_B.width(status, 10, 0.8)
    parts = [
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12" fill="{c["card"]}" stroke="{c["line"]}"/>',
        txt(MONO, path, 11, 18, 24, c["muted"]),
        f'<line x1="1" y1="38" x2="{W - 1}" y2="38" stroke="{c["line"]}"/>',
        f'<rect x="{fmt(W - 18 - sw - 26)}" y="10" width="{fmt(sw + 26)}" height="20" rx="10" fill="none" stroke="{col}" stroke-opacity=".55"/>',
        f'<circle cx="{fmt(W - 18 - sw - 14)}" cy="20" r="3" fill="{col}"/>',
        txt(MONO_B, status, 10, W - 26, 23.6, col, "end", 0.8),
    ]
    return parts


# ---------------------------------------------------------------- UI showcases

SCREENS = ROOT / "tools" / ".screens"  # filled by tools/fetch_screens.sh
_embedded = {}


def embed(name, width_px):
    """Downscale a screenshot and return it as a WebP data URI."""
    key = (name, width_px)
    if key not in _embedded:
        im = Image.open(SCREENS / name).convert("RGB")
        h = round(im.height * width_px / im.width)
        im = im.resize((width_px, h), Image.LANCZOS)
        buf = BytesIO()
        im.save(buf, "WEBP", quality=88, method=6)
        _embedded[key] = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
    return _embedded[key]


def showcase(c, slug, path, status, status_acc, screens, aspect, label, legend=None, slots=None):
    """A card of phone frames, each holding a real screenshot.

    screens: (file, caption, mine). `mine` gives the frame an amber bezel.
    A file of None leaves the screen empty for tools/demo/compose.py to fill
    with a recording; pass a list as `slots` to get each screen's rect back.
    """
    W, pad, gap, bezel = 840, 24, 20, 5
    n = len(screens)
    fw = (W - 2 * pad - (n - 1) * gap) / n      # frame width
    sw = fw - 2 * bezel                          # screen width
    sh = sw * aspect
    top = 60
    fh = sh + 2 * bezel
    cap_y = top + fh + 26
    H = round(cap_y + (40 if legend else 22))
    parts = chrome(c, W, H, path, status, status_acc)
    for i, (file, caption, mine) in enumerate(screens):
        fx = pad + i * (fw + gap)
        sx, sy = fx + bezel, top + bezel
        cid = f"{slug}{i}"
        edge = c["acc"] if mine else c["line"]
        parts.append(f'<rect x="{fmt(fx)}" y="{top}" width="{fmt(fw)}" height="{fmt(fh)}" rx="27" '
                     f'fill="{c["card2"]}" stroke="{edge}" stroke-width="1.5"/>')
        parts.append(f'<clipPath id="{cid}"><rect x="{fmt(sx)}" y="{sy}" width="{fmt(sw)}" height="{fmt(sh)}" rx="22"/></clipPath>')
        if file:
            parts.append(f'<image href="{embed(file, round(sw * 2))}" x="{fmt(sx)}" y="{sy}" width="{fmt(sw)}" '
                         f'height="{fmt(sh)}" preserveAspectRatio="xMidYMin slice" clip-path="url(#{cid})"/>')
        if slots is not None:
            slots.append(dict(x=sx, y=sy, w=sw, h=sh, r=22))
        cx = fx + fw / 2
        col = c["acc"] if mine else c["text"]
        parts.append(txt(MONO, caption, 11, cx, cap_y, col, "middle"))
    if legend:
        parts.append(f'<rect x="{pad}" y="{H - 23}" width="9" height="9" rx="2" fill="{c["acc"]}"/>')
        parts.append(txt(MONO, legend, 10.5, pad + 16, H - 14.5, c["muted"]))
    return svg(W, H, label, "\n".join(parts))


# The Amphion demo is one journey with one song, recorded step by step by
# tools/demo/record.js: (clip name, caption, seconds). The phones play in turn.
AMPHION_CLIPS = [
    ("record", "1  record a song", 8.0),
    ("ready", "2  tab ready → open it", 6.0),
    ("play", "3  play along in sync", 6.5),
    ("practice", "4  slow down + loop", 7.5),
]


def amphion_frame(c, slots):
    """The Amphion card with empty screens; compose.py plays the clips in them."""
    return showcase(
        c, "am", "amphion / live demo", "IN PROGRESS", True,
        [(None, cap, False) for _, cap, _ in AMPHION_CLIPS],
        844 / 390,
        "Amphion demo",
        slots=slots,
    )


# SnapDose needs its Firebase backend to run, so its card is a walkthrough
# animated from the real screenshots (tools/demo/compose.py), not a recording.
SNAPDOSE_SCREENS = [
    ("home", "live glucose", False),
    ("results", "snap → AI carb estimate", True),
    ("dose", "insulin dosing", False),
    ("gallery", "food gallery", True),
]


def snapdose_frame(c, slots):
    """The SnapDose card with empty screens; compose.py animates them."""
    return showcase(
        c, "sd", "snapdose / walkthrough", "SHIPPED · SPRING 2026", False,
        [(None, f"{i + 1}  {cap}", mine) for i, (_, cap, mine) in enumerate(SNAPDOSE_SCREENS)],
        1000 / 460,
        "SnapDose walkthrough",
        legend="screens I built",
        slots=slots,
    )


# ---------------------------------------------------------------- ember card

def ember(c):
    W, H = 840, 388
    parts = chrome(c, W, H, "ember / ingestion + cli", "IN PROGRESS · CAPSTONE 2026–27")
    styles = []

    # Terminal
    tx, ty, tw, th = 18, 54, 382, 316
    parts.append(f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="9" fill="{c["term"]}" stroke="{c["line"]}"/>')
    for k in range(3):
        parts.append(f'<circle cx="{tx + 16 + k * 13}" cy="{ty + 15}" r="4" fill="#3a414c"/>')
    parts.append(txt(MONO, "~/ember", 10, tx + tw - 14, ty + 19, "#6e7681", "end"))
    lines = [
        [("$ ", c["acc"], MONO_B), ("ember auth login", c["termtext"], MONO)],
        [("  opened the web app in your browser", "#7d8590", MONO)],
        [("  ok ", "#4cc9a6", MONO_B), ("signed in", c["termtext"], MONO)],
        [("$ ", c["acc"], MONO_B), ("ember auth status", c["termtext"], MONO)],
        [("  logged in · org ", "#7d8590", MONO), ("ember-development", c["termtext"], MONO)],
        [("$ ", c["acc"], MONO_B), ("ember status", c["termtext"], MONO)],
        [("  intake  ", "#7d8590", MONO), ("ok", "#4cc9a6", MONO_B), ("   enrich  ", "#7d8590", MONO),
         ("ok", "#4cc9a6", MONO_B), ("   mcp  ", "#7d8590", MONO), ("ok", "#4cc9a6", MONO_B)],
        [("  gitlab  ", "#7d8590", MONO), ("webhooks live · backfill done", c["termtext"], MONO)],
    ]
    ly = ty + 56
    n = len(lines)
    for i, segs in enumerate(lines):
        x = tx + 16
        group = []
        for s, col, f in segs:
            group.append(txt(f, s, 11.5, x, ly, col))
            x += f.width(s, 11.5)
        p = 4 + i * 8
        styles.append(f".l{i}{{animation:l{i} 12s steps(1) infinite}}"
                      f"@keyframes l{i}{{0%{{opacity:0}}{p}%{{opacity:1}}94%{{opacity:1}}97%,100%{{opacity:0}}}}")
        parts.append(f'<g class="l{i}">{"".join(group)}</g>')
        ly += 26
    cursor_y = ly
    parts.append(f'<g class="l{n}">' + txt(MONO_B, "$ ", 11.5, tx + 16, cursor_y, c["acc"]) +
                 f'<rect class="cur" x="{fmt(tx + 16 + MONO_B.width("$ ", 11.5))}" y="{cursor_y - 11}" width="7.5" height="14" fill="{c["termtext"]}"/></g>')
    p = 4 + n * 8
    styles.append(f".l{n}{{animation:l{n} 12s steps(1) infinite}}"
                  f"@keyframes l{n}{{0%{{opacity:0}}{p}%{{opacity:1}}94%{{opacity:1}}97%,100%{{opacity:0}}}}"
                  ".cur{animation:blink 1s steps(1) infinite}@keyframes blink{50%{opacity:0}}")

    # Pipeline diagram
    def node(x, y, w, h, label, mine=False, sub=None):
        stroke = c["acc"] if mine else c["line"]
        col = c["acc"] if mine else c["text"]
        out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{c["card2"]}" stroke="{stroke}"/>']
        if sub:
            out.append(txt(MONO, label, 11, x + w / 2, y + h / 2 - 2, col, "middle"))
            out.append(txt(MONO, sub, 9.5, x + w / 2, y + h / 2 + 11, c["muted"], "middle"))
        else:
            out.append(txt(MONO, label, 11, x + w / 2, y + h / 2 + 4, col, "middle"))
        return "".join(out)

    parts.append(txt(MONO, "SOURCES", 10, 426, 70, c["muted"], track=0.8))
    srcs = ["GitHub", "GitLab", "Jira", "Slack"]
    sy = [78, 106, 134, 162]
    for s, y in zip(srcs, sy):
        parts.append(node(426, y, 84, 24, s, mine=(s == "GitLab")))
    ix, iy = 556, 103
    for s, y in zip(srcs, sy):
        mine = s == "GitLab"
        d = f"M510 {y + 12} C533 {y + 12} 533 {iy + 17} {ix} {iy + 17}"
        pid = 'id="gl" ' if mine else ""
        parts.append(f'<path {pid}d="{d}" stroke="{c["acc"] if mine else c["faint"]}" stroke-width="{1.6 if mine else 1.1}" fill="none"/>')
    parts.append(node(ix, iy, 104, 34, "intake", sub="verify · store"))
    ex = 700
    parts.append(f'<path id="ie" d="M{ix + 104} {iy + 17} H{ex}" stroke="{c["faint"]}" stroke-width="1.1" fill="none"/>')
    parts.append(node(ex, iy, 120, 34, "enrich", sub="worker per source"))
    parts.append(f'<path d="M{ex + 60} {iy + 34} V204" stroke="{c["faint"]}" stroke-width="1.1" fill="none"/>')
    parts.append(node(ex, 204, 120, 38, "source_records", sub="+ pgvector"))
    parts.append(f'<path d="M{ex} 223 H{ix + 104}" stroke="{c["faint"]}" stroke-width="1.1" fill="none"/>')
    parts.append(node(ix, 206, 104, 34, "MCP server", sub="search"))
    parts.append(f'<path d="M{ix} 223 H510" stroke="{c["faint"]}" stroke-width="1.1" fill="none"/>')
    parts.append(node(426, 206, 84, 34, "agents", sub="Claude · Codex"))
    for k in range(3):
        parts.append(f'<circle class="motion" r="3.2" fill="{c["acc"]}"><animateMotion dur="2.4s" begin="{k * 0.8}s" '
                     f'repeatCount="indefinite"><mpath href="#gl"/></animateMotion></circle>')

    # The CLI + web app lane
    parts.append(f'<line x1="426" y1="264" x2="820" y2="264" stroke="{c["line"]}" stroke-dasharray="2 4"/>')
    parts.append(txt(MONO, "ACCESS", 10, 426, 284, c["muted"], track=0.8))
    parts.append(node(426, 294, 130, 38, "ember CLI", mine=True, sub="Rust"))
    parts.append(f'<path d="M556 313 H600 M594 308 L600 313 L594 318" stroke="{c["acc"]}" stroke-width="1.4" fill="none"/>')
    parts.append(node(600, 294, 220, 38, "web app", mine=True, sub="login · organizations · invites"))

    parts.append(f'<rect x="426" y="350" width="9" height="9" rx="2" fill="{c["acc"]}"/>')
    parts.append(txt(MONO, "the parts I built", 10.5, 442, 358.5, c["muted"]))
    return svg(W, H, "Ember: a terminal running ember auth login and ember status, next to the ingestion pipeline "
               "with the GitLab connector, the Rust CLI, and the web app's auth and organizations highlighted",
               "\n".join(parts), "".join(styles) + REDUCED)


# ---------------------------------------------------------------- footer

def footer(c):
    W, H = 840, 70
    parts = [f'<defs><linearGradient id="fade" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{W}" y2="0"><stop offset="0" stop-color="{c["faint"]}" stop-opacity="0"/>'
             f'<stop offset=".35" stop-color="{c["faint"]}"/></linearGradient></defs>']
    top, gap = 14, 8
    for i in range(6):
        y = top + i * gap
        parts.append(f'<line x1="0" y1="{y}" x2="{W - 2}" y2="{y}" stroke="url(#fade)"/>')
    parts.append(f'<line x1="{W - 9}" y1="{top}" x2="{W - 9}" y2="{top + 5 * gap}" stroke="{c["muted"]}" stroke-width="1.2"/>')
    parts.append(f'<line x1="{W - 2}" y1="{top}" x2="{W - 2}" y2="{top + 5 * gap}" stroke="{c["muted"]}" stroke-width="3.5"/>')
    for i in range(2):
        parts.append(f'<circle cx="{W - 18}" cy="{top + gap * (1.5 + i * 2)}" r="2.2" fill="{c["acc"]}"/>')
    parts.append(f'<rect x="{W - 186}" y="{top + 2 * gap - 9}" width="150" height="18" fill="{c["page"]}"/>')
    parts.append(txt(MONO_B, "THANKS FOR LISTENING", 10, W - 36, top + 2 * gap + 4, c["muted"], "end", 1.0))
    return svg(W, H, "Thanks for listening", "\n".join(parts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True)
    args = ap.parse_args()
    load_fonts(args.fonts)
    for theme, c in PALETTES.items():
        write("header", theme, header(c))
        write("projects/ember", theme, ember(c))
        write("footer", theme, footer(c))
        for slug, idx, title in [("now", "01", "Now building"), ("projects", "02", "Team projects"), ("toolbox", "03", "Toolbox")]:
            write(f"headings/{slug}", theme, heading(c, idx, title))
        for slug, label, primary, icon in [("amphion", "AMPHION", True, "play"), ("ember", "EMBER", False, "arrow"),
                                            ("snapdose", "SNAPDOSE", False, "arrow")]:
            write(f"buttons/{slug}", theme, button(c, label, primary, icon))


if __name__ == "__main__":
    main()
