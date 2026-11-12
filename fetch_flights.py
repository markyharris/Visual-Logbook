#!/usr/bin/env python3
"""Flight fetchers: append new flights to each plane's log.

Two sources, in order:

1. FlightAware AeroAPI (primary) — needs the owner's key in
   config.json (admin page → Settings). Last 14 days, completed
   flights only, dedupe by fa_flight_id, true off/on times.
2. OpenSky Network (free backup) — needs a free OpenSky account's
   API client ID + secret in config.json (admin page → Settings).
   OpenSky only serves historical flights to signed-in accounts,
   and its data lands a day behind, so this runs as a gap-filler:
   the last 4 days, flights whose estimated departure AND arrival
   airports are known (queried as complete UTC days, one day
   per request). Times are first-seen/last-seen on ADS-B,
   so hours are approximate. A flight either source already
   logged (same route, times within an hour) is never added
   twice — FlightAware's version wins because it runs first.

Both: append legs with great-circle NM from the airport data,
add airborne hours to the plane's total, and redraw the poster
if the displayed plane gained a flight. Run by
visual-logbook-fetch.timer (every 6 h), the admin page's fetch
button, or button D. Either source missing its credentials is
noted per plane and skipped — never fatal.
"""
import datetime
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import greatcircle  # noqa: E402
import logbook  # noqa: E402

API = "https://aeroapi.flightaware.com/aeroapi/flights/"
WINDOW_DAYS = 14

OS_API = "https://opensky-network.org/api/flights/aircraft"
OS_TOKEN_URL = ("https://auth.opensky-network.org/auth/realms/"
                "opensky-network/protocol/openid-connect/token")
OS_DAYS = 4            # complete UTC days back from yesterday


# ------------------------------------------------------------------
# FlightAware
# ------------------------------------------------------------------

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
            "off": off, "on": on,
        })
    return out


def fetch_fa(data, tail, key, now):
    """Append new FlightAware flights to data; return count."""
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
                "fa_id": fl["fa_id"], "time": fl["hours"],
                "off": fl["off"], "on": fl["on"]})
            data["hours"] = round(data.get("hours", 0)
                                  + fl["hours"], 1)
            known.add(fl["fa_id"])
            added += 1
        nxt = (payload.get("links") or {}).get("next")
        url = ("https://aeroapi.flightaware.com" + nxt) if nxt else None
    return added


# ------------------------------------------------------------------
# OpenSky
# ------------------------------------------------------------------

_B9 = "123456789"
_B10 = "0123456789"
_B34 = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789"  # no I / O, by design


def _enc_suffix(suf):
    if not suf:
        return 0
    r0 = _B34.find(suf[0])
    r1 = 0 if len(suf) == 1 else _B34.find(suf[1]) + 1
    if r0 < 24:                      # letter first: base 25
        return r0 * 25 + r1 + 1
    return r0 * 35 + r1 - 239        # digit first: base 35


def tail_to_icao24(tail):
    """US N-number → ICAO 24-bit hex (lowercase), or None.

    US addresses are assigned sequentially from A00001 = N1, so
    the hex is computed, not looked up. (Verified against the
    published vectors N1→a00001, N12345→a061d9, N456TS→a58a20,
    N86QU→abcdef, and N757AF→aa3410 in a live aircraft DB.)
    Non-US tails return None; set "icao24" on the plane in
    config.json to track those by OpenSky.
    """
    tail = (tail or "").strip().upper()
    if len(tail) < 2 or tail[0] != "N":
        return None
    d1 = _B9.find(tail[1])
    if d1 == -1:
        return None
    icao = 0xA00001 + d1 * 101711
    if len(tail) == 2:                       # N1
        return format(icao, "06x")
    d2 = _B10.find(tail[2])
    if d2 == -1:                             # N1A
        return format(icao + _enc_suffix(tail[2:4]), "06x")
    icao += d2 * 10111 + 601
    if len(tail) == 3:                       # N11
        return format(icao, "06x")
    d3 = _B10.find(tail[3])
    if d3 == -1:                             # N11A
        return format(icao + _enc_suffix(tail[3:5]), "06x")
    icao += d3 * 951 + 601                   # N111..
    return format(icao + _enc_suffix(tail[4:6]), "06x")


def _http_detail(stage, e):
    """An HTTPError with its response body attached — OpenSky's
    body says WHY (bad client, bad interval), which the bare
    status line hides."""
    try:
        body = e.read().decode("utf-8", "replace").strip()
    except Exception:
        body = ""
    return RuntimeError(f"{stage} HTTP {e.code}: {body[:140]}")


def os_token(cfg, cache):
    """OAuth2 client-credentials token for OpenSky, cached in
    the `cache` dict across planes; a failure is cached too so
    one bad credential set costs one error, not one per plane."""
    if "token" in cache:
        return cache["token"]
    if "error" in cache:
        raise cache["error"]
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": (cfg.get("opensky_client_id") or "").strip(),
        "client_secret": (cfg.get("opensky_client_secret")
                          or "").strip()}).encode()
    req = urllib.request.Request(OS_TOKEN_URL, data=body)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            cache["token"] = json.load(r)["access_token"]
    except urllib.error.HTTPError as e:
        cache["error"] = _http_detail("token", e)
        raise cache["error"]
    except Exception as e:
        cache["error"] = e
        raise
    return cache["token"]


def os_get(url, token):
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []          # OpenSky's "no flights in window"
        raise _http_detail("flights", e)


def parse_opensky(payload, icao24):
    """Usable flights from an OpenSky /flights/aircraft payload:
    both airports estimated, sane duration. Times are epoch
    seconds (firstSeen / lastSeen on the ADS-B network)."""
    out = []
    for fl in payload or []:
        dep = fl.get("estDepartureAirport")
        arr = fl.get("estArrivalAirport")
        first, last = fl.get("firstSeen"), fl.get("lastSeen")
        if not (dep and arr and first and last):
            continue
        hours = (last - first) / 3600
        if hours < 0.08 or hours > 30:
            continue
        t_off = datetime.datetime.fromtimestamp(
            first, datetime.timezone.utc)
        out.append({
            "fa_id": f"opensky-{icao24}-{first}",
            "date": t_off.date().isoformat(),
            "dep": dep.upper(), "arr": arr.upper(),
            "hours": round(hours, 1),
            "off": t_off.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "on": datetime.datetime.fromtimestamp(
                last, datetime.timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"),
        })
    return out


def _leg_time(leg):
    off = leg.get("off")
    if not off:
        return None
    try:
        return datetime.datetime.fromisoformat(
            off.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def same_flight(leg, cand):
    """True if an already-logged leg is the candidate's flight:
    same route and either off-times within an hour, or the
    logged leg has no time (seed log) and the dates match."""
    if leg.get("dep") != cand["dep"] or leg.get("arr") != cand["arr"]:
        return False
    t_leg, t_cand = _leg_time(leg), _leg_time(cand)
    if t_leg is not None and t_cand is not None:
        return abs(t_leg - t_cand) <= 3600
    if t_leg is None:
        return leg.get("date") == cand["date"]
    return False


def fetch_opensky(data, plane, cfg, cache, now):
    """Append new OpenSky flights to data; return count."""
    icao24 = ((plane.get("icao24") or "").strip().lower()
              or tail_to_icao24(plane["tail"]))
    if not icao24:
        raise ValueError(f"no ICAO hex for {plane['tail']}")
    token = os_token(cfg, cache)
    known = {l.get("fa_id") for l in data["legs"]}
    added = 0
    # Complete UTC days only, in 1-day requests: OpenSky's batch
    # holds nothing for today yet, and its stated cap is a 2-day
    # interval — exactly-2-day requests drew HTTP 400 in the
    # field (Nov 12, 2026), so stay well inside it.
    today0 = int(datetime.datetime(
        now.year, now.month, now.day,
        tzinfo=datetime.timezone.utc).timestamp())
    for back in range(OS_DAYS):
        end = today0 - back * 86400
        begin = end - 86400
        q = urllib.parse.urlencode(
            {"icao24": icao24, "begin": begin, "end": end})
        for fl in parse_opensky(os_get(f"{OS_API}?{q}", token),
                                icao24):
            if fl["fa_id"] in known:
                continue
            if any(same_flight(l, fl) for l in data["legs"]):
                continue
            data["legs"].append({
                "date": fl["date"], "dep": fl["dep"],
                "arr": fl["arr"], "nm": leg_nm(fl["dep"], fl["arr"]),
                "fa_id": fl["fa_id"], "time": fl["hours"],
                "off": fl["off"], "on": fl["on"]})
            data["hours"] = round(data.get("hours", 0)
                                  + fl["hours"], 1)
            known.add(fl["fa_id"])
            added += 1
    return added


# ------------------------------------------------------------------
# Shared
# ------------------------------------------------------------------

def leg_nm(dep, arr):
    a, b = logbook.resolve_airport(dep), logbook.resolve_airport(arr)
    if a and b:
        return round(greatcircle.nm(a, b))
    return 0


def fetch_plane(cfg, plane, fa_key, os_cache, now):
    """Run both sources for one plane. Returns (added, note)."""
    tail = plane["tail"]
    data = logbook.load_plane(tail, cfg)
    added = 0
    parts = []
    if fa_key:
        try:
            n = fetch_fa(data, tail, fa_key, now)
            added += n
            parts.append(f"FlightAware +{n}" if n
                         else "FlightAware no new")
        except Exception as e:
            parts.append(f"FlightAware error: {e}")
    else:
        parts.append("FlightAware: no key set")
    if (cfg.get("opensky_client_id") or "").strip() and \
            (cfg.get("opensky_client_secret") or "").strip():
        try:
            n = fetch_opensky(data, plane, cfg, os_cache, now)
            added += n
            parts.append(f"OpenSky +{n}" if n else "OpenSky no new")
        except Exception as e:
            parts.append(f"OpenSky error: {e}")
    else:
        parts.append("OpenSky: no account set")
    # repair NM on older auto legs whose airports have since resolved
    for leg in data["legs"]:
        if leg.get("nm", 0) == 0 and leg["dep"] != leg["arr"]:
            leg["nm"] = leg_nm(leg["dep"], leg["arr"])
    data["legs"].sort(key=lambda l: (l["date"], _leg_time(l) or 0))
    logbook.save_plane(data)
    return added, "; ".join(parts)


def main():
    cfg = logbook.load_config()
    state = logbook.load_state()
    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = now.astimezone().strftime("%Y-%m-%d %H:%M")
    fa_key = (cfg.get("fa_api_key") or "").strip()
    os_cache = {}
    display_changed = False
    for plane in cfg["planes"]:
        tail = plane["tail"]
        try:
            added, note = fetch_plane(cfg, plane, fa_key,
                                      os_cache, now)
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
