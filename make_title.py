#!/usr/bin/env python3
"""Build a plane's title page: the card shown before its poster
when the plane has no photo.

Usage:  python3 make_title.py [out.png] [--tail N35MH]

A flat vintage-poster card in the Spectra palette — tail number
large in blue serif, aircraft type and home base under a red rule —
rendered with the same fonts and palette conversion as the boot
photo (make_boot), so the two intro pages feel like a set.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 800, 480

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 200)
RED = (210, 0, 0)


def _fit(draw, text, path, size, max_w):
    """Largest font at or below `size` that keeps text within max_w."""
    while size > 12:
        f = ImageFont.truetype(path, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return ImageFont.truetype(path, size)


def main(out, data=None):
    if data is None:
        import logbook
        cfg = logbook.load_config()
        data = logbook.load_plane(cfg["display_tail"], cfg)
    from make_boot import SERIF_B, SANS, to_spectra

    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    # double frame, poster style
    d.rectangle([18, 18, W - 18, H - 18], outline=BLACK, width=3)
    d.rectangle([28, 28, W - 28, H - 28], outline=RED, width=2)

    f_head = ImageFont.truetype(SANS, 19)
    d.text((W // 2, 84), "V I S U A L   L O G B O O K", font=f_head,
           fill=BLUE, anchor="mm")

    tail = (data.get("tail") or "").upper()
    f_tail = _fit(d, tail, SERIF_B, 150, 640)
    d.text((W // 2, 208), tail, font=f_tail, fill=BLUE, anchor="mm")

    d.rectangle([W // 2 - 110, 282, W // 2 + 110, 286], fill=RED)

    y = 330
    aircraft = (data.get("aircraft") or "").upper()
    if aircraft:
        f_type = _fit(d, aircraft, SERIF_B, 44, 640)
        d.text((W // 2, y), aircraft, font=f_type, fill=BLACK,
               anchor="mm")
        y += 44

    home = (data.get("home") or "").upper()
    label = (data.get("home_label") or "").upper()
    sub = f"{home}  ·  {label}" if home and label else home or label
    if sub:
        f_sub = _fit(d, sub, SANS, 20, 640)
        d.text((W // 2, y), sub, font=f_sub, fill=BLACK, anchor="mm")

    legs = data.get("legs") or []
    hours = data.get("hours") or 0
    if legs or hours:
        stats = f"{len(legs)} FLIGHTS  ·  {hours:.1f} HOURS"
        f_stats = ImageFont.truetype(SANS, 16)
        d.text((W // 2, H - 62), stats, font=f_stats, fill=BLUE,
               anchor="mm")

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
    out = args[0] if args else os.path.join(HERE, "title.png")
    main(out, data)
