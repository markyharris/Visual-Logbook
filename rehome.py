#!/usr/bin/env python3
"""Rehome: forget every saved Wi-Fi connection and reboot.

With no known network at boot, Comitup raises its setup access
point so the frame can join a new network from a phone — the
fleet's standard rehoming flow. Invoked from the admin page.

SAFETY: without Comitup this would strand the frame (no known
network, no setup AP, no way back in short of a keyboard or an
Ethernet cable) — which is exactly what nearly happened on
Nov 12, 2026, when the first frame turned out never to have
had Comitup installed. So: refuse to run unless Comitup is
present AND enabled. The admin handler checks the same thing
before dispatching here.
"""
import os
import shutil
import subprocess
import sys


def comitup_ready():
    found = (shutil.which("comitup")
             or os.path.exists("/usr/sbin/comitup")
             or os.path.exists(
                 "/usr/lib/systemd/system/comitup.service")
             or os.path.exists(
                 "/lib/systemd/system/comitup.service")
             or os.path.exists(
                 "/etc/systemd/system/comitup.service"))
    if not found:
        return False
    try:
        r = subprocess.run(["systemctl", "is-enabled", "comitup"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() == "enabled"
    except Exception:
        return False


def main():
    if not comitup_ready():
        print("refusing to rehome: Comitup is not installed and "
              "enabled on this frame — forgetting the Wi-Fi "
              "would strand it")
        return 1
    out = subprocess.run(
        ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
        capture_output=True, text=True).stdout
    for line in out.splitlines():
        name, _, typ = line.rpartition(":")
        if "wireless" in typ:
            subprocess.run(["sudo", "-n", "nmcli", "connection",
                            "delete", name])
            print("forgot Wi-Fi:", name)
    subprocess.run(["sudo", "-n", "reboot"])


if __name__ == "__main__":
    sys.exit(main())
