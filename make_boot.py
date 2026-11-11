#!/usr/bin/env python3
"""Build the boot image: the aeroplane's photo, Spectra-style.

Usage:  python3 make_boot.py [photo] [out.png]

Defaults: reads plane.jpg, writes boot.png. The photo is cropped to
the panel's 5:3, given a slim black caption band (tail number from
legs.json, aircraft type, home town), then converted to the Inky
Impression's six-colour Spectra palette with Floyd-Steinberg
dithering, so the PNG is exactly what the panel will show.
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 800, 480
BAND = 54
HOME_LABEL = "FLAGSTAFF, ARIZONA"
SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

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


def main(photo, out):
    data = json.load(open(os.path.join(HERE, "legs.json")))
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
    sub = f"{data['aircraft'].upper()}  ·  {HOME_LABEL}"
    d.text((W - 36 - d.textlength(sub, font=f2), H - BAND + 21),
           sub, font=f2, fill=(255, 255, 255))

    to_spectra(img).save(out)
    print("wrote", out)


if __name__ == "__main__":
    photo = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        HERE, "plane.jpg")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        HERE, "boot.png")
    main(photo, out)
