#!/usr/bin/env python3
"""Panel power actions for the admin page's Power section.

  python3 power.py blank     clear the panel to white; the frame
                             stays on (rotation, if enabled, will
                             redraw at the next plane's turn)
  python3 power.py reboot    reboot the Pi (the boot sequence
                             redraws photo + poster)
  python3 power.py shutdown  clear the panel FIRST, then power
                             off — an e-paper panel would
                             otherwise hold its last image forever

Reboot / poweroff run through the passwordless sudoers entries
(/usr/bin/reboot, /usr/bin/poweroff — see HOWTO section 7).
Blanking needs no sudo: it just drives the panel.
"""
import subprocess
import sys


def blank_panel():
    from inky.auto import auto
    from PIL import Image
    inky = auto(ask_user=True, verbose=True)
    w, h = inky.resolution
    inky.set_image(Image.new("RGB", (w, h), (255, 255, 255)))
    inky.show()
    print("panel blanked")


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "blank":
        blank_panel()
    elif action == "reboot":
        subprocess.run(["sudo", "-n", "/usr/bin/reboot"])
    elif action == "shutdown":
        blank_panel()
        subprocess.run(["sudo", "-n", "/usr/bin/poweroff"])
    else:
        print("usage: power.py blank|reboot|shutdown")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
