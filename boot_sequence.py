#!/usr/bin/env python3
"""Boot sequence: the display plane's photo, a dwell, then its poster.

Run by visual-logbook-boot.service. The dwell (seconds the photo
stays up, complete) is dwell_seconds in config.json — set it on the
admin page.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import logbook  # noqa: E402
import show_boot  # noqa: E402
import show_poster  # noqa: E402


def main():
    cfg = logbook.load_config()
    show_boot.show(cfg["display_tail"])
    dwell = int(cfg.get("dwell_seconds", 30))
    if dwell:
        time.sleep(dwell)
    show_poster.show(cfg["display_tail"])


if __name__ == "__main__":
    main()
