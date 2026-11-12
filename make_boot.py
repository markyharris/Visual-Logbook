#!/usr/bin/env python3
"""Build a plane's boot image: its photo, Spectra-style.

Usage:  python3 make_boot.py [photo] [out.png] [--tail N26MR]

The photo is cropped to the panel's 5:3, given a slim black caption
band (tail number, aircraft type, home town from config.json), then
converted to the Inky Impression's six-colour Spectra palette with
Floyd-Steinberg dithering, so the PNG is what the panel will show.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 800, 480
BAND = 54

_FONT_DIRS = ("/usr/share/fonts/truetype/dejavu",
              "/usr/share/fonts/truetype/liberation")
_FONT_FILES = {
    "serif_b": ("DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"),
    "sans": ("DejaVuSans.ttf", "LiberationSans-Regular.ttf"),
}


def _font(style):
    """First installed file for a font style (DejaVu or Liberation).

    A bare Pi OS image may ship neither: install fonts-dejavu-core.
    """
    for name in _FONT_FILES[style]:
        for folder in _FONT_DIRS:
            path = os.path.join(folder, name)
            if os.path.exists(path):
                return path
    raise OSError(
        f"no {style} font found - run: sudo apt install fonts-dejavu-core")


SERIF_B = _font("serif_b")
SANS = _font("sans")

SPECTRA = [(0, 0, 0), (255, 255, 255), (0, 160, 0), (0, 0, 200),
           (210, 0, 0), (240, 200, 0)]


def to_spectra(img, saturation=1.3, contrast=1.08):
    img = img.convert("RGB")
    img = ImageEnhance.Color(img).enhance(saturation)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    pal = Image.new("P", (1, 1))
    flat = []
    for c in SPECTRA:
        flat.extend(c)
    flat.extend([0] * (768 - len(flat)))
    pal.putpalette(flat)
    return img.quantize(palette=pal,
                        dither=Image.FLOYDSTEINBERG).convert("RGB")


def main(photo, out, data=None):
    if data is None:
        import logbook
        cfg = logbook.load_config()
        data = logbook.load_plane(cfg["display_tail"], cfg)
    src = Image.open(photo)
    w, h = src.size
    cw = int(h * (W / H))
    x0 = max(0, min(w - cw, int(w * 0.03)))
    img = src.crop((x0, 0, x0 + cw, h)).resize((W, H), Image.LANCZOS)

    d = ImageDraw.Draw(img)
    d.rectangle([0, H - BAND, W, H], fill=(0, 0, 0))
    f1 = ImageFont.truetype(SERIF_B, 24)
    f2 = ImageFont.truetype(SANS, 11)
    d.text((36, H - BAND + 13), data["tail"], font=f1,
           fill=(255, 255, 255))
    home = (data.get("home_label") or "").upper()
    sub = data.get("aircraft", "").upper()
    if home:
        sub = f"{sub}  ·  {home}" if sub else home
    if sub:
        d.text((W - 36 - d.textlength(sub, font=f2), H - BAND + 21),
               sub, font=f2, fill=(255, 255, 255))

    to_spectra(img).save(out)
    print("wrote", out)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tail = None
    if "--tail" in sys.argv:
        tail = sys.argv[sys.argv.index("--tail") + 1]
    data = None
    if tail:
        import logbook
        cfg = logbook.load_config()
        data = logbook.load_plane(tail, cfg)
    photo = args[0] if args else os.path.join(HERE, "plane.jpg")
    out = args[1] if len(args) > 1 else os.path.join(HERE, "boot.png")
    main(photo, out, data)
