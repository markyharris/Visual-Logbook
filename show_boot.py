#!/usr/bin/env python3
"""Show a plane's intro image on the panel: its photo if it has
one, otherwise a generated title page (tail number card).

Run on the Pi:  python3 show_boot.py [--tail N26MR]

Looks for boot_<TAIL>.png (built from plane_<TAIL>.jpg on first
run); the original single-plane names boot.png / plane.jpg still
work for the first plane. A plane with no photo gets a title page
from make_title (title_<TAIL>.png, rebuilt each show so edits to
the plane's type or home base land immediately).
"""
import argparse
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def _first(*names):
    for n in names:
        p = os.path.join(HERE, n)
        if os.path.exists(p):
            return p
    return None


def show(tail=None):
    import logbook
    cfg = logbook.load_config()
    tail = tail or cfg["display_tail"]
    first = cfg["planes"][0]["tail"] if cfg["planes"] else None
    legacy = ["boot.png"] if tail == first else []
    boot = _first(f"boot_{tail}.png", *legacy)
    if boot is None:
        legacy = ["plane.jpg"] if tail == first else []
        photo = _first(f"plane_{tail}.jpg", *legacy)
        data = logbook.load_plane(tail, cfg)
        if photo is None:
            import make_title
            boot = os.path.join(HERE, f"title_{tail}.png")
            make_title.main(boot, data)
        else:
            import make_boot
            boot = os.path.join(HERE, f"boot_{tail}.png")
            make_boot.main(photo, boot, data)

    from inky.auto import auto
    from PIL import Image
    inky = auto(ask_user=True, verbose=True)
    inky.set_image(Image.open(boot))
    inky.show()
    print(f"boot image for {tail} on the panel")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tail", default=None)
    show(ap.parse_args().tail)
