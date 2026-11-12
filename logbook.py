#!/usr/bin/env python3
"""Shared data layer for Visual Logbook (multi-plane).

Files (all beside this module):
  legs.json            seed log shipped with the repo (plane #1)
  config.json          Pi-local settings: planes list (max 6), the
                       plane on display, FlightAware key, dwell time
  legs_<TAIL>.json     each plane's live log (Pi-local, never in git)
  state.json           Pi-local runtime state (fetches, update flag)
  airports.json        hand-checked coordinates (win over the dataset)
  custom_airports.json coordinates added from the admin page
  us_airports.json     bundled US airport dataset (OurAirports)

Nothing here talks to the panel or the network; the other programs
(admin, fetcher, show_*) build on these helpers.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_PLANES = 6

CONFIG = os.path.join(HERE, "config.json")
STATE = os.path.join(HERE, "state.json")
SEED = os.path.join(HERE, "legs.json")
CUSTOM_AIRPORTS = os.path.join(HERE, "custom_airports.json")


def _read(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)


def legs_path(tail):
    return os.path.join(HERE, f"legs_{tail}.json")


def ensure_config():
    """Create config.json (and plane #1's live log) from the seed."""
    cfg = _read(CONFIG)
    if cfg:
        return cfg
    seed = _read(SEED, {"tail": "N26MR", "aircraft": "Cirrus SR22T",
                        "hours": 0, "legs": []})
    tail = seed["tail"]
    cfg = {
        "fa_api_key": "",
        "display_tail": tail,
        "dwell_seconds": 30,
        "planes": [{
            "tail": tail,
            "type": seed.get("aircraft", ""),
            "home": "KFLG",
            "home_label": "Flagstaff, Arizona",
        }],
    }
    _write(CONFIG, cfg)
    if not os.path.exists(legs_path(tail)):
        _write(legs_path(tail), seed)
    return cfg


def load_config():
    return ensure_config()


def save_config(cfg):
    _write(CONFIG, cfg)


def load_state():
    return _read(STATE, {"last_fetch": {}, "update_available": False,
                         "last_update_check": None})


def save_state(state):
    _write(STATE, state)


def plane_cfg(cfg, tail):
    for p in cfg["planes"]:
        if p["tail"] == tail:
            return p
    return None


def load_plane(tail, cfg=None):
    """A plane's logbook data: {tail, aircraft, hours, legs, home,
    home_label}. Falls back to the seed file for plane #1."""
    cfg = cfg or load_config()
    data = _read(legs_path(tail))
    if data is None:
        seed = _read(SEED)
        if seed and seed.get("tail") == tail:
            data = seed
        else:
            pc = plane_cfg(cfg, tail) or {}
            data = {"tail": tail, "aircraft": pc.get("type", ""),
                    "hours": 0, "legs": []}
    pc = plane_cfg(cfg, tail) or {}
    data["home"] = pc.get("home", "KFLG")
    data["home_label"] = pc.get("home_label", "")
    if pc.get("type"):
        data["aircraft"] = pc["type"]
    return data


def save_plane(data):
    _write(legs_path(data["tail"]), {
        "tail": data["tail"],
        "aircraft": data.get("aircraft", ""),
        "hours": data.get("hours", 0),
        "legs": data.get("legs", []),
    })


# ---- airports -------------------------------------------------------

_us_cache = None
_curated_cache = None


def resolve_airport(ident):
    """Coordinates for an ident: admin-added first, then the
    hand-checked seed list, then the bundled US dataset.
    Returns {"lat", "lon", "name"} or None."""
    global _us_cache, _curated_cache
    ident = (ident or "").strip().upper()
    if not ident:
        return None
    custom = _read(CUSTOM_AIRPORTS, {})
    if ident in custom:
        c = custom[ident]
        return {"lat": c["lat"], "lon": c["lon"],
                "name": c.get("name", ident)}
    if _curated_cache is None:
        _curated_cache = _read(os.path.join(HERE, "airports.json"), {})
    if ident in _curated_cache:
        c = _curated_cache[ident]
        return {"lat": c["lat"], "lon": c["lon"],
                "name": c.get("name", ident)}
    if _us_cache is None:
        _us_cache = _read(os.path.join(HERE, "us_airports.json"), {})
    if ident in _us_cache:
        lat, lon, name = _us_cache[ident]
        return {"lat": lat, "lon": lon, "name": name}
    return None


def add_custom_airport(ident, lat, lon, name=""):
    custom = _read(CUSTOM_AIRPORTS, {})
    custom[ident.strip().upper()] = {"lat": float(lat),
                                     "lon": float(lon),
                                     "name": name or ident}
    _write(CUSTOM_AIRPORTS, custom)


def airports_for(data):
    """({ident: airport}, [unknown idents]) for a plane's legs + home."""
    idents = {data.get("home", "KFLG")}
    for leg in data.get("legs", []):
        idents.add(leg["dep"])
        idents.add(leg["arr"])
    found, unknown = {}, []
    for ident in sorted(idents):
        ap = resolve_airport(ident)
        if ap:
            found[ident] = ap
        else:
            unknown.append(ident)
    return found, unknown
