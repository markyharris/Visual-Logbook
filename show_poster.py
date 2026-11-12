#!/usr/bin/env python3
"""Render a plane's flight-log poster and push it to the panel.

Run on the Pi:  python3 show_poster.py [--tail N26MR]

With no --tail, shows the plane set as the display plane in
config.json (the admin page sets it). A full Spectra refresh takes
~30 s; that is the panel, not a hang.
"""
import argparse
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def show(tail=None):
    import logbook
    import make_poster
    cfg = logbook.load_config()
    tail = tail or cfg["display_tail"]
    data = logbook.load_plane(tail, cfg)
    out = os.path.join(HERE, "poster_current.png")
    make_poster.main(out, data)

    from inky.auto import auto
    from PIL import Image
    inky = auto(ask_user=True, verbose=True)
    inky.set_image(Image.open(out))
    inky.show()
    print(f"poster for {tail} on the panel")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tail", default=None)
    show(ap.parse_args().tail)
