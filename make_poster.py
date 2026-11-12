#!/usr/bin/env python3
"""N26MR flight-log poster for the Pimoroni Inky Impression 7.3" Spectra.

Renders an 800x480 vintage-style route map from a flight log,
restricted to the Spectra 6 palette, so what you see in a preview is
what the panel will show.

Data: flight legs and totals live in legs.json, airport coordinates
in airports.json, state outlines in us-states.json, all beside this
file.
"""
import json
import math
import os
import sys
from collections import Counter

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 800, 480
# Spectra 6 palette (as Pimoroni's inky library names them)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 128, 0)
BLUE = (0, 0, 180)
RED = (200, 0, 0)
YELLOW = (235, 190, 0)

_FONT_DIRS = ("/usr/share/fonts/truetype/dejavu",
              "/usr/share/fonts/truetype/liberation")
_FONT_FILES = {
    "serif_b": ("DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"),
    "serif": ("DejaVuSerif.ttf", "LiberationSerif-Regular.ttf"),
    "sans_b": ("DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"),
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
SERIF = _font("serif")
SANS_B = _font("sans_b")
SANS = _font("sans")





def arc_points(p1, p2, n=28):
    """Great-circle-ish arc between (lat, lon) pairs, as (lat, lon)."""
    la1, lo1 = math.radians(p1[0]), math.radians(p1[1])
    la2, lo2 = math.radians(p2[0]), math.radians(p2[1])
    def vec(la, lo):
        return (math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo),
                math.sin(la))
    v1, v2 = vec(la1, lo1), vec(la2, lo2)
    dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(v1, v2))))
    omega = math.acos(dot)
    if omega < 1e-6:
        return [p1, p2]
    pts = []
    for i in range(n + 1):
        t = i / n
        s = math.sin(omega)
        a = math.sin((1 - t) * omega) / s
        b = math.sin(t * omega) / s
        x = a * v1[0] + b * v2[0]
        y = a * v1[1] + b * v2[1]
        z = a * v1[2] + b * v2[2]
        pts.append((math.degrees(math.atan2(z, math.hypot(x, y))),
                    math.degrees(math.atan2(y, x))))
    return pts



def dashed_line(draw, pts, fill, width=1, dash=7, gap=5):
    """Draw a polyline as dashes (dash px on, gap px off)."""
    carry = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        seg = math.hypot(x2 - x1, y2 - y1)
        if seg == 0:
            continue
        ux, uy = (x2 - x1) / seg, (y2 - y1) / seg
        s = -carry
        while s < seg:
            on_end = min(s + dash, seg)
            if on_end > max(s, 0):
                draw.line([x1 + ux * max(s, 0), y1 + uy * max(s, 0),
                           x1 + ux * on_end, y1 + uy * on_end],
                          fill=fill, width=width)
            s += dash + gap
        carry = (seg + carry) % (dash + gap)


def spaced(draw, xy, text, font, fill, spacing=3):
    """Draw letter-spaced text centered at xy (center, top)."""
    widths = []
    total = 0
    for ch in text:
        w = draw.textlength(ch, font=font)
        widths.append(w)
        total += w + spacing
    total -= spacing
    x = xy[0] - total / 2
    y = xy[1]
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + spacing
    return total


def main(out_path, data=None):
    if data is None:
        import logbook
        cfg = logbook.load_config()
        data = logbook.load_plane(cfg["display_tail"], cfg)
    import datetime
    import logbook
    airports, _unknown = logbook.airports_for(data)
    home = data.get("home", "KFLG")
    legs = data["legs"]
    for leg in legs:
        if isinstance(leg["date"], str):
            leg["date"] = datetime.date.fromisoformat(leg["date"])
    timed = [l for l in legs if l["dep"] != l["arr"]]
    total_nm = sum(l["nm"] for l in legs)
    counts = Counter((min(l["dep"], l["arr"]), max(l["dep"], l["arr"]))
                     for l in timed)
    longest = max(timed, key=lambda l: l["nm"]) if timed else None
    first = min((l["date"] for l in legs), default=None)
    last = max((l["date"] for l in legs), default=None)

    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    # ---- frame: black edge, yellow pinstripe, red hairline --------
    # (same triple-frame scheme as the title page, make_title.py)
    d.rectangle([8, 8, W - 9, H - 9], outline=BLACK, width=3)
    d.rectangle([11, 11, W - 12, H - 12], fill=YELLOW)
    d.rectangle([15, 15, W - 16, H - 16], fill=WHITE)
    d.rectangle([15, 15, W - 16, H - 16], outline=RED, width=1)

    # ---- title block ----------------------------------------------
    f_title = ImageFont.truetype(SERIF_B, 46)
    f_sub = ImageFont.truetype(SANS_B, 15)
    f_small = ImageFont.truetype(SANS, 12)
    title = data["tail"]
    tw = d.textlength(title, font=f_title)
    d.text(((W - tw) / 2, 24), title, font=f_title, fill=BLUE)
    # rules flanking the title
    mid_y = 24 + 30
    d.line([60, mid_y, (W - tw) / 2 - 25, mid_y], fill=RED, width=2)
    d.line([(W + tw) / 2 + 25, mid_y, W - 60, mid_y], fill=RED, width=2)
    spaced(d, (W / 2, 82),
           f"{data['aircraft'].upper()}  ·  FLIGHT LOG  ·  "
           f"{last.year if last else ''}", f_sub, BLACK)

    # ---- map --------------------------------------------------------
    MX0, MY0, MX1, MY1 = 46, 118, 754, 396
    lats = [a["lat"] for a in airports.values()]
    lons = [a["lon"] for a in airports.values()]
    lat0, lat1 = min(lats) - 1.2, max(lats) + 1.2
    lon0, lon1 = min(lons) - 1.2, max(lons) + 1.2
    mid_lat = math.radians((lat0 + lat1) / 2)
    lon_span = (lon1 - lon0) * math.cos(mid_lat)
    lat_span = lat1 - lat0
    scale = min((MX1 - MX0) / lon_span, (MY1 - MY0) / lat_span)
    plot_w = lon_span * scale
    plot_h = lat_span * scale
    ox = MX0 + ((MX1 - MX0) - plot_w) / 2
    oy = MY0 + ((MY1 - MY0) - plot_h) / 2

    def xy(lat, lon):
        return (ox + (lon - lon0) * math.cos(mid_lat) * scale,
                oy + (lat1 - lat) * scale)

    # state outlines (dashed, chart style), clipped to the view
    states = json.load(open(os.path.join(HERE, "us-states.json")))
    for feat in states["features"]:
        geom = feat["geometry"]
        polys = (geom["coordinates"] if geom["type"] == "Polygon"
                 else [p for p in geom["coordinates"]])
        rings = []
        for poly in (geom["coordinates"] if geom["type"] == "Polygon"
                     else geom["coordinates"]):
            rings.extend(poly if geom["type"] == "MultiPolygon"
                         else [poly])
        for ring in rings:
            lons_r = [p[0] for p in ring]
            lats_r = [p[1] for p in ring]
            if (max(lons_r) < lon0 or min(lons_r) > lon1 or
                    max(lats_r) < lat0 or min(lats_r) > lat1):
                continue
            pts = [xy(p[1], p[0]) for p in ring]
            dashed_line(d, pts, GREEN)

    # state abbreviations, hand-placed in open country
    f_state = ImageFont.truetype(SANS_B, 11)
    state_labels = {
        "MN": (46.6, -95.2), "WI": (44.9, -91.4), "SD": (44.3, -100.3),
        "IA": (42.2, -93.6), "NE": (41.5, -99.9), "IL": (40.2, -89.3),
        "IN": (39.8, -86.2), "WY": (42.9, -107.7), "UT": (39.3, -112.7),
        "CO": (38.9, -105.6), "KS": (38.4, -98.5), "MO": (38.3, -92.6),
        "KY": (37.5, -86.6), "OK": (34.9, -96.4), "TN": (36.15, -85.7),
        "AR": (34.5, -92.4), "TX": (33.7, -100.5), "NM": (33.4, -106.6),
        "AZ": (33.5, -110.6),
    }
    for abbr, (la, lo) in state_labels.items():
        x, y = xy(la, lo)
        if not (MX0 + 8 <= x <= MX1 - 8 and MY0 + 8 <= y <= MY1 - 8):
            continue
        w = d.textlength(abbr, font=f_state)
        d.text((x - w / 2, y - 6), abbr, font=f_state, fill=BLUE)

    # legs as great-circle arcs, width grows with frequency
    for (a, b), n in sorted(counts.items()):
        if a not in airports or b not in airports:
            continue
        pts = [xy(lat, lon) for lat, lon in
               arc_points((airports[a]["lat"], airports[a]["lon"]),
                          (airports[b]["lat"], airports[b]["lon"]))]
        wdt = 2 if n == 1 else (3 if n == 2 else 4)
        d.line(pts, fill=RED, width=wdt, joint="curve")

    # compass rose, top-right of the map area, on a yellow disc
    cx, cy, r = MX1 - 30, MY0 + 30, 17
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=YELLOW)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=BLACK, width=1)
    d.polygon([(cx, cy - r + 3), (cx - 5, cy + 4), (cx + 5, cy + 4)],
              fill=RED)
    d.text((cx - 4, cy + 6), "N", font=f_small, fill=BLACK)

    # ---- airports ---------------------------------------------------
    f_lab = ImageFont.truetype(SANS_B, 12)
    # label side overrides: -1 = left of dot, 1 = right, and dy in px
    side = {"KJAC": (-1, -14), "46U": (-1, 4), "KPWK": (1, 2),
            "KRWN": (1, 2), "KDLH": (1, -4), "KFLG": (-1, -18),
            "KGEU": (-1, 6), "KINW": (1, 8), "M01": (1, 0),
            "KPVE": (1, -16), "KHRX": (-1, 2), "KDHT": (-1, 10),
            "KSAF": (1, 8), "KFYV": (-1, 5), "KBBG": (1, -13),
            "KBGD": (-1, -17), "KOJA": (1, 9)}
    for code, a in airports.items():
        x, y = xy(a["lat"], a["lon"])
        if code == home:
            d.ellipse([x - 8, y - 8, x + 8, y + 8], outline=RED, width=3)
            d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=RED)
        else:
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=WHITE)
            d.ellipse([x - 4, y - 4, x + 4, y + 4], outline=BLACK,
                      width=1)
            d.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=BLACK)
        s, dy = side.get(code, (1, -6))
        label = code if code != home else f"{home} · HOME"
        lw = d.textlength(label, font=f_lab)
        lx = x + 9 if s == 1 else x - 9 - lw
        d.text((lx, y + dy), label, font=f_lab,
               fill=RED if code == home else BLACK)

    # ---- footer stats ----------------------------------------------
    d.line([60, 412, W - 60, 412], fill=BLACK, width=1)
    f_stat = ImageFont.truetype(SANS_B, 17)
    stats = (f"{len(legs)} FLIGHTS  ·  {data['hours']:.1f} HOURS  ·  "
             f"{total_nm:,} NM  ·  {len(airports)} AIRPORTS")
    sw = d.textlength(stats, font=f_stat)
    d.text(((W - sw) / 2, 420), stats, font=f_stat, fill=BLUE)
    f_note = ImageFont.truetype(SANS, 12)
    if first and longest:
        note = (f"{first.strftime('%b %-d').upper()} – "
                f"{last.strftime('%b %-d, %Y').upper()}   ·   "
                f"LONGEST LEG: {longest['dep']} → {longest['arr']} · "
                f"{longest['nm']} NM")
    else:
        note = "NO FLIGHTS LOGGED YET"
    nw = d.textlength(note, font=f_note)
    d.text(((W - nw) / 2, 446), note, font=f_note, fill=RED)

    img.save(out_path)
    print("wrote", out_path)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         os.path.join(HERE, "poster_v1.png"))
