#!/usr/bin/env python3
"""Rehome: forget every saved Wi-Fi connection and reboot.

With no known network at boot, Comitup (installed per the HOWTO)
raises its setup access point so the frame can join a new network
from a phone — the fleet's standard rehoming flow. Invoked only
from the admin page, behind its confirm checkbox.
"""
import subprocess


def main():
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
    main()
