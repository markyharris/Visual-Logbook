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


def poster_data(data, cfg):
    """Plane data with draw_legs set when a poster window is on.

    Settings' poster_recent (0 = all) limits how many of the most
    recent flights the poster's MAP draws, so a growing log can't
    crowd the chart into unreadability. The full leg list stays
    untouched in data["legs"] — header stats keep describing the
    whole log, and the log itself is never trimmed.
    """
    try:
        n = int(cfg.get("poster_recent", 0) or 0)
    except (TypeError, ValueError):
        n = 0
    legs = data.get("legs", [])
    if n and len(legs) > n:
        ordered = [leg for _i, leg in sorted(
            enumerate(legs),
            key=lambda item: (str(item[1].get("date", "")), item[0]))]
        out = dict(data)
        out["draw_legs"] = ordered[-n:]
        return out
    return data


def show(tail=None):
    import logbook
    import make_poster
    cfg = logbook.load_config()
    tail = tail or cfg["display_tail"]
    data = poster_data(logbook.load_plane(tail, cfg), cfg)
    out = os.path.join(HERE, "poster_current.png")
    make_poster.main(out, data)

    from inky.auto import auto
    from PIL import Image
    inky = auto(ask_user=True, verbose=True)
    inky.set_image(Image.open(out))
    inky.show()
    state = logbook.load_state()
    state["showing_tail"] = tail
    logbook.save_state(state)
    print(f"poster for {tail} on the panel")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tail", default=None)
    show(ap.parse_args().tail)
