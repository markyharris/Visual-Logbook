#!/usr/bin/env python3
"""FlightAware fetcher: append new flights to each plane's log.

Run by visual-logbook-fetch.timer (every 6 h), the admin page's
"Check FlightAware now" button, or button D. Needs the owner's
AeroAPI key in config.json (admin page → Settings); without one it
notes that and does nothing.

For every plane: pull the last 14 days of flights, keep completed
ones we haven't logged (dedupe by fa_flight_id), append legs with
great-circle NM from the airport data, add airborne hours
(actual_off → actual_on) to the plane's total, and redraw the
poster if that plane is on display and gained a flight.
"""
import datetime
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import greatcircle  # noqa: E402
import logbook  # noqa: E402

API = "https://aeroapi.flightaware.com/aeroapi/flights/"
WINDOW_DAYS = 14


def api_get(url, key):
    req = urllib.request.Request(url, headers={"x-apikey": key})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def parse_flights(payload):
    """Completed flights from an AeroAPI /flights payload."""
    out = []
    for fl in payload.get("flights", []):
        if fl.get("cancelled") or not fl.get("actual_on"):
            continue
        origin = fl.get("origin") or {}
        dest = fl.get("destination") or {}
        dep = origin.get("code_icao") or origin.get("code")
        arr = dest.get("code_icao") or dest.get("code")
        off, on = fl.get("actual_off"), fl.get("actual_on")
        if not (dep and arr and off and on):
            continue
        t_off = datetime.datetime.fromisoformat(
            off.replace("Z", "+00:00"))
        t_on = datetime.datetime.fromisoformat(
            on.replace("Z", "+00:00"))
        out.append({
            "fa_id": fl.get("fa_flight_id"),
            "date": t_off.date().isoformat(),
            "dep": dep.upper(), "arr": arr.upper(),
            "hours": round((t_on - t_off).total_seconds() / 3600, 1),
        })
    return out


def leg_nm(dep, arr):
    a, b = logbook.resolve_airport(dep), logbook.resolve_airport(arr)
    if a and b:
        return round(greatcircle.nm(a, b))
    return 0


def fetch_plane(cfg, tail, key, now):
    data = logbook.load_plane(tail, cfg)
    known = {l.get("fa_id") for l in data["legs"]}
    end = now
    start = now - datetime.timedelta(days=WINDOW_DAYS)
    q = urllib.parse.urlencode({
        "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": end.strftime("%Y-%m-%dT%H:%M:%SZ")})
    url = f"{API}{urllib.parse.quote(tail)}?{q}"
    added = 0
    while url:
        payload = api_get(url, key)
        for fl in parse_flights(payload):
            if fl["fa_id"] in known:
                continue
            data["legs"].append({
                "date": fl["date"], "dep": fl["dep"],
                "arr": fl["arr"], "nm": leg_nm(fl["dep"], fl["arr"]),
                "fa_id": fl["fa_id"]})
            data["hours"] = round(data.get("hours", 0)
                                  + fl["hours"], 1)
            known.add(fl["fa_id"])
            added += 1
        nxt = (payload.get("links") or {}).get("next")
        url = ("https://aeroapi.flightaware.com" + nxt) if nxt else None
    # repair NM on older auto legs whose airports have since resolved
    for leg in data["legs"]:
        if leg.get("nm", 0) == 0 and leg["dep"] != leg["arr"]:
            leg["nm"] = leg_nm(leg["dep"], leg["arr"])
    data["legs"].sort(key=lambda l: l["date"])
    logbook.save_plane(data)
    return added


def main():
    cfg = logbook.load_config()
    state = logbook.load_state()
    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = now.astimezone().strftime("%Y-%m-%d %H:%M")
    key = (cfg.get("fa_api_key") or "").strip()
    if not key:
        for p in cfg["planes"]:
            state["last_fetch"][p["tail"]] = {
                "when": stamp, "note": "no API key set"}
        logbook.save_state(state)
        print("no FlightAware API key in config; skipping")
        return
    display_changed = False
    for p in cfg["planes"]:
        tail = p["tail"]
        try:
            added = fetch_plane(cfg, tail, key, now)
            note = f"+{added} flight(s)" if added else "no new"
            if added and tail == cfg["display_tail"]:
                display_changed = True
        except Exception as e:
            note = f"error: {e}"
            added = 0
        state["last_fetch"][tail] = {"when": stamp, "note": note}
        print(tail, note)
    logbook.save_state(state)
    if display_changed:
        subprocess.Popen([sys.executable,
                          os.path.join(HERE, "show_poster.py")],
                         cwd=HERE)


if __name__ == "__main__":
    main()
