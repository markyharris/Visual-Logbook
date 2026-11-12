#!/usr/bin/env python3
"""Update check / apply for Visual Logbook (git-based, like the
other Pi projects in the fleet).

  python3 updater.py check   fetch origin; flag state.update_available
  python3 updater.py apply   pull --ff-only, restart services, redraw

Code updates never touch Pi-local data: config.json, legs_*.json,
state.json, photos and boot images are all gitignored, so a pull
can't overwrite the owner's logs or settings.
"""
import datetime
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import logbook  # noqa: E402

SERVICES = ["visual-logbook-admin.service",
            "visual-logbook-buttons.service",
            "visual-logbook-boot.service"]


def git(*args):
    return subprocess.run(["git", "-C", HERE] + list(args),
                          capture_output=True, text=True, timeout=120)


def check():
    state = logbook.load_state()
    state["last_update_check"] = datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M")
    r = git("fetch", "origin", "main")
    if r.returncode != 0:
        state["update_available"] = False
        state["update_note"] = "fetch failed (offline?)"
    else:
        head = git("rev-parse", "HEAD").stdout.strip()
        remote = git("rev-parse", "origin/main").stdout.strip()
        state["update_available"] = bool(remote) and head != remote
        state["update_note"] = "update waiting" if \
            state["update_available"] else "up to date"
    logbook.save_state(state)
    print(state["update_note"])


def apply():
    r = git("pull", "--ff-only")
    state = logbook.load_state()
    if r.returncode != 0:
        state["update_note"] = f"pull failed: {r.stderr.strip()[:120]}"
        logbook.save_state(state)
        print(state["update_note"])
        return
    state["update_available"] = False
    state["update_note"] = "updated just now"
    logbook.save_state(state)
    subprocess.run(["sudo", "-n", "systemctl", "restart"] + SERVICES,
                   capture_output=True)
    subprocess.Popen([sys.executable,
                      os.path.join(HERE, "show_poster.py")], cwd=HERE)
    print("updated")


if __name__ == "__main__":
    (apply if len(sys.argv) > 1 and sys.argv[1] == "apply"
     else check)()
