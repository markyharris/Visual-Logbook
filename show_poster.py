#!/usr/bin/env python3
"""Render the flight-log poster and push it to the Inky Impression.

Run on the Pi:  python3 show_poster.py

Renders poster_current.png from legs.json / airports.json /
us-states.json (via make_poster.py), then displays it on the panel
with Pimoroni's inky library. A full Spectra refresh takes ~30 s;
that is the panel, not a hang.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    import make_poster
    out = os.path.join(HERE, "poster_current.png")
    make_poster.main(out)

    from inky.auto import auto
    from PIL import Image
    inky = auto(ask_user=True, verbose=True)
    inky.set_image(Image.open(out))
    inky.show()
    print("poster on the panel")


if __name__ == "__main__":
    main()
