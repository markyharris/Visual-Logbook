#!/usr/bin/env python3
"""Panel buttons (and any remote buttons wired in parallel).

A (GPIO 5)  previous plane's poster     C (GPIO 16) display plane's photo
B (GPIO 6)  next plane's poster         D (GPIO 24) FlightAware check + redraw

Buttons are momentary switches to ground with pull-ups — the same
lines the Inky Impression's built-in buttons use, so frame-mounted
remote buttons wired to the same GPIO pins work identically.
Runs as visual-logbook-buttons.service.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import logbook  # noqa: E402

try:
    from gpiozero import Button
except ImportError:
    sys.exit("gpiozero not installed: "
             "sudo apt install python3-gpiozero")

PIN_A, PIN_B, PIN_C, PIN_D = 5, 6, 16, 24


def run(*args):
    subprocess.Popen([sys.executable] + [os.path.join(HERE, a)
                                         if a.endswith(".py") else a
                                         for a in args],
                     cwd=HERE)


def cycle(step):
    cfg = logbook.load_config()
    tails = [p["tail"] for p in cfg["planes"]]
    if not tails:
        return
    i = tails.index(cfg["display_tail"]) if cfg["display_tail"] \
        in tails else 0
    cfg["display_tail"] = tails[(i + step) % len(tails)]
    logbook.save_config(cfg)
    run("show_poster.py")


def main():
    Button(PIN_A, pull_up=True, bounce_time=0.3).when_pressed = \
        lambda: cycle(-1)
    Button(PIN_B, pull_up=True, bounce_time=0.3).when_pressed = \
        lambda: cycle(+1)
    Button(PIN_C, pull_up=True, bounce_time=0.3).when_pressed = \
        lambda: run("show_boot.py")
    Button(PIN_D, pull_up=True, bounce_time=0.3).when_pressed = \
        lambda: run("fetch_flights.py")
    print("buttons live: A/B prev/next plane, C photo, D fetch")
    from signal import pause
    pause()


if __name__ == "__main__":
    main()
