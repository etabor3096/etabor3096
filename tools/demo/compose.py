"""Build the animated project cards (animated WebP, light and dark).

Each card is the usual project card drawn by build_assets.py, with four phone
screens left empty. This script fills the screens frame by frame:

  amphion   plays four recordings of the Amphion front-end demo (record.js)
  snapdose  animates a walkthrough over the real SnapDose screenshots. The app
            needs its Firebase backend to run, so this one is not a recording.

Usage, from the repo root:
  # Amphion demo running on localhost:5180 (Amphion repo, dev branch)
  node tools/demo/record.js tools/.demo/clips light
  node tools/demo/record.js tools/.demo/clips dark
  sh tools/fetch_screens.sh
  python tools/demo/compose.py --fonts <font dir> [--card amphion|snapdose] [--theme light|dark]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import build_assets as ba  # noqa: E402

WORK = ROOT / "tools" / ".demo"
SCALE = 2      # output pixels per CSS pixel, for sharp text on retina screens
FPS = 12
LENGTH = 12.0  # seconds per loop; record.js records exactly this long


def ease(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


# ---------------------------------------------------------------- amphion

class Clip:
    """One recording: frames with timestamps, cropped to the phone screen."""

    def __init__(self, folder, size):
        meta = json.loads((folder / "frames.json").read_text())
        b, s = meta["box"], meta["dpr"]
        self.crop = tuple(round(v * s) for v in (b["x"], b["y"], b["x"] + b["width"], b["y"] + b["height"]))
        self.frames = meta["frames"]
        self.folder = folder
        self.size = size
        self._cache = {}

    def __call__(self, t):
        i = 0
        for j, f in enumerate(self.frames):
            if f["t"] > t:
                break
            i = j
        if i not in self._cache:
            im = Image.open(self.folder / self.frames[i]["file"]).convert("RGB").crop(self.crop)
            self._cache = {i: im.resize(self.size, Image.LANCZOS)}
        return self._cache[i]


def amphion_screens(theme, c, sizes):
    return [Clip(WORK / "clips" / theme / name, size) for (name, _), size in zip(ba.AMPHION_CLIPS, sizes)]


# ---------------------------------------------------------------- snapdose

SHOTS = ROOT / "tools" / ".screens" / "snapdose"
PHASES = [(0, 3), (3, 6), (6, 9), (9, 12)]   # when each phone is in the spotlight
# Taps in screenshot coordinates (460 x 1000): (time, x, y)
TAPS = {
    "home": [(0.9, 372, 178), (2.2, 76, 935)],       # Refresh, then the Snap tab
    "results": [(3.65, 230, 862), (5.2, 340, 819)],  # shutter, then Confirm 46g
    "dose": [(7.0, 120, 411)],                       # Meal Dose
    "gallery": [(10.0, 120, 465)],                   # open Grilled salmon
}
SHUTTER = 3.9  # the photo is taken: flash, then the analysis results


def camera_view(results):
    """A viewfinder made from the meal photo on the results screen."""
    w, h = results.size
    im = Image.new("RGB", (w, h), (8, 8, 10))
    photo = results.crop((18, 200, 441, 520))
    pw = w
    ph = round(photo.height * pw / photo.width)
    photo = photo.resize((pw, ph), Image.LANCZOS)
    top = 430 - ph // 2
    im.paste(photo, (0, top))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1, L = 34, top - 22, w - 34, top + ph + 22, 34
    for (x, y, dx, dy) in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
        d.line((x, y, x + L * dx, y), fill="white", width=5)
        d.line((x, y, x, y + L * dy), fill="white", width=5)
    d.ellipse((230 - 38, 862 - 38, 230 + 38, 862 + 38), outline="white", width=6)
    d.ellipse((230 - 28, 862 - 28, 230 + 28, 862 + 28), fill="white")
    return im


class Walkthrough:
    """One phone's screen in the SnapDose walkthrough."""

    def __init__(self, index, name, size, theme):
        self.i, self.name, self.size = index, name, size
        self.shot = Image.open(SHOTS / f"{name}.png").convert("RGB")
        self.camera = camera_view(self.shot) if name == "results" else None
        self.dim = (13, 17, 23) if theme == "dark" else (246, 248, 250)

    def spotlight(self, t):
        a, b = PHASES[self.i]
        if self.i == 0 and t > 11.7:   # hand back to the first phone as the loop restarts
            return ease((t - 11.7) / 0.3)
        return ease((t - a) / 0.3) * (1 - ease((t - b + 0.3) / 0.3))

    def __call__(self, t):
        a, _ = PHASES[self.i]
        im = self.camera if (self.camera and a <= t < SHUTTER) else self.shot
        im = im.copy()
        w, h = im.size
        on = self.spotlight(t)
        if on > 0:  # slow push-in while in the spotlight
            z = 1 + 0.03 * ease((t - a) / 3)
            cw, ch = w / z, h / z
            im = im.crop((round((w - cw) / 2), round((h - ch) / 2), round((w + cw) / 2), round((h + ch) / 2))).resize((w, h), Image.LANCZOS)
        d = ImageDraw.Draw(im, "RGBA")
        for (tt, x, y) in TAPS[self.name]:
            k = (t - tt) / 0.55
            if 0 <= k < 1:
                r = 16 + 18 * ease(k)
                alpha = round(110 * (1 - k))
                d.ellipse((x - r, y - r, x + r, y + r), fill=(30, 30, 30, alpha // 2), outline=(30, 30, 30, alpha), width=3)
        if self.camera and SHUTTER <= t < SHUTTER + 0.4:
            im = Image.blend(im, Image.new("RGB", im.size, "white"), 1 - (t - SHUTTER) / 0.4)
        if on < 1:
            im = Image.blend(im, Image.new("RGB", im.size, self.dim), 0.55 * (1 - on))
        return im.resize(self.size, Image.LANCZOS)


def snapdose_screens(theme, c, sizes):
    return [Walkthrough(i, name, size, theme) for i, ((name, _, _), size) in enumerate(zip(ba.SNAPDOSE_SCREENS, sizes))]


# ---------------------------------------------------------------- shared

CARDS = {
    "amphion": (ba.amphion_frame, amphion_screens),
    "snapdose": (ba.snapdose_frame, snapdose_screens),
}


def rounded_mask(size, radius):
    big = Image.new("L", (size[0] * 4, size[1] * 4), 0)
    ImageDraw.Draw(big).rounded_rectangle((0, 0, big.width - 1, big.height - 1), radius * 4, fill=255)
    return big.resize(size, Image.LANCZOS)


def build(card, theme, c):
    frame_fn, screens_fn = CARDS[card]
    slots = []
    svg = frame_fn(c, slots)
    WORK.mkdir(parents=True, exist_ok=True)
    svg_path, png_path = WORK / f"{card}-frame-{theme}.svg", WORK / f"{card}-frame-{theme}.png"
    svg_path.write_text(svg)
    subprocess.run(["node", str(ROOT / "tools/demo/rasterize.js"), str(svg_path), str(png_path), str(SCALE)], check=True)
    background = Image.open(png_path).convert("RGBA")

    sizes = [(round(s["w"] * SCALE), round(s["h"] * SCALE)) for s in slots]
    screens = screens_fn(theme, c, sizes)
    placed = [(screen, (round(s["x"] * SCALE), round(s["y"] * SCALE)), rounded_mask(size, s["r"] * SCALE))
              for screen, s, size in zip(screens, slots, sizes)]

    frames = []
    for k in range(int(LENGTH * FPS)):
        t = k / FPS
        frame = background.copy()
        for screen, pos, mask in placed:
            frame.paste(screen(t), pos, mask)
        frames.append(frame)

    out = ba.OUT / "projects" / f"{card}-{theme}.webp"
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=round(1000 / FPS), loop=0,
                   quality=82, method=6, minimize_size=True, allow_mixed=True)
    print(f"{out.relative_to(ROOT)}: {len(frames)} frames, {out.stat().st_size / 1e6:.1f} MB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--card", choices=list(CARDS), action="append")
    ap.add_argument("--theme", choices=list(ba.PALETTES), action="append")
    ap.add_argument("--preview", type=float, nargs="*", help="write PNG frames at these times instead of the WebP")
    args = ap.parse_args()
    ba.load_fonts(args.fonts)
    for card in args.card or CARDS:
        for theme in args.theme or ba.PALETTES:
            if args.preview:
                preview(card, theme, ba.PALETTES[theme], args.preview)
            else:
                build(card, theme, ba.PALETTES[theme])


def preview(card, theme, c, times):
    """Quick check: a strip of single frames, without encoding the animation."""
    frame_fn, screens_fn = CARDS[card]
    slots = []
    frame_fn(c, slots)
    sizes = [(round(s["w"]), round(s["h"])) for s in slots]
    screens = screens_fn(theme, c, sizes)
    strip = Image.new("RGB", (sum(w for w, _ in sizes) + 10 * len(sizes), sizes[0][1] * len(times)), "gray")
    for row, t in enumerate(times):
        x = 0
        for screen, (w, h) in zip(screens, sizes):
            strip.paste(screen(t), (x, row * h))
            x += w + 10
    out = WORK / f"{card}-{theme}-preview.png"
    WORK.mkdir(parents=True, exist_ok=True)
    strip.save(out)
    print(out)


if __name__ == "__main__":
    main()
