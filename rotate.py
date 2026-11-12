#!/usr/bin/env python3
"""Poster rotation: cycle the panel through every plane's poster.

Runs as visual-logbook-rotate.service. Behaviour (all set in the
admin page's Settings):
  rotate          on/off
  rotate_minutes  how long each poster stays up (default 10)

Every configured plane takes part, even one with no logged
flights yet — it has a poster (seeded hours) and a photo, and
excluding it left a two-plane frame cycling a single poster
(fixed Nov 12, 2026). The cycle resumes from whatever poster is
currently up (state.showing_tail, kept by show_poster), so a
manual Show or a button press doesn't fight the rotation — it
just becomes the rotation's new starting point.
Config is re-read every few seconds, so admin changes land without
a restart.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import logbook  # noqa: E402
import show_boot  # noqa: E402
import show_poster  # noqa: E402

TICK = 10  # seconds between config checks


def rotation_tails(cfg):
    return [p["tail"] for p in cfg["planes"]]


def next_tail(cfg, current):
    tails = rotation_tails(cfg)
    if not tails:
        return None
    if current in tails:
        return tails[(tails.index(current) + 1) % len(tails)]
    return tails[0]


def show_plane(cfg, tail):
    """A plane's turn: its intro first (photo, or a title page if
    it has no photo), held for the dwell, then its poster for the
    rest of the slot."""
    dwell = int(cfg.get("dwell_seconds", 30))
    if dwell > 0:
        show_boot.show(tail)          # photo, or a title page if none
        time.sleep(dwell)
    show_poster.show(tail)


def main():
    shown_at = 0.0
    current = logbook.load_state().get("showing_tail")
    while True:
        cfg = logbook.load_config()
        if cfg.get("rotate"):
            state = logbook.load_state()
            external = state.get("showing_tail")
            if external and external != current:
                current = external  # someone else drove the panel
            interval = max(1, int(cfg.get("rotate_minutes", 10))) * 60
            now = time.time()
            if now - shown_at >= interval:
                nxt = next_tail(cfg, current)
                if nxt:
                    try:
                        show_plane(cfg, nxt)
                        current = nxt
                    except Exception as e:
                        print("rotate show failed:", e, flush=True)
                    shown_at = time.time()
        time.sleep(TICK)


if __name__ == "__main__":
    main()
