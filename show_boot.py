#!/usr/bin/env python3
"""Show the boot image (the aeroplane photo) on the panel.

Run at power-up (see visual-logbook-boot.service). Builds boot.png
from plane.jpg on first run via make_boot.py. If neither file is
present it exits quietly — the poster flow never depends on it.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    boot = os.path.join(HERE, "boot.png")
    if not os.path.exists(boot):
        photo = os.path.join(HERE, "plane.jpg")
        if not os.path.exists(photo):
            print("no boot image or source photo; skipping")
            return
        import make_boot
        make_boot.main(photo, boot)

    from inky.auto import auto
    from PIL import Image
    inky = auto(ask_user=True, verbose=True)
    inky.set_image(Image.open(boot))
    inky.show()
    print("boot image on the panel")


if __name__ == "__main__":
    main()
