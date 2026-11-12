#!/usr/bin/env python3
"""Show a plane's boot image (its photo) on the panel.

Run on the Pi:  python3 show_boot.py [--tail N26MR]

Looks for boot_<TAIL>.png (built from plane_<TAIL>.jpg on first
run); the original single-plane names boot.png / plane.jpg still
work for the first plane. If no photo exists it exits quietly —
the poster flow never depends on it.
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
    boot = _first(f"boot_{tail}.png", "boot.png")
    if boot is None:
        photo = _first(f"plane_{tail}.jpg", "plane.jpg")
        if photo is None:
            print(f"no photo for {tail}; skipping boot image")
            return
        import make_boot
        boot = os.path.join(HERE, f"boot_{tail}.png")
        make_boot.main(photo, boot, logbook.load_plane(tail, cfg))

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
