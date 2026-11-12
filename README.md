# Visual Logbook

A flight log you can hang on the wall. Visual Logbook renders your
flying as a vintage-style route poster — every airport you've visited
as a dot, every route as a red arc over dashed state outlines — and
displays it on a Pimoroni Inky Impression 7.3" colour e-paper panel
driven by a Raspberry Pi.

Built for N26MR, a Cirrus SR22T based at Flagstaff (KFLG), but the
data files are plain JSON: any tail number, any log.

Run `python3 make_poster.py poster.png` to see the poster itself —
the N26MR sample shows the delivery wander home from Duluth, the
Jackson Hole trip, the Branson run, and the Flagstaff–Glendale
shuttle drawn thickest of all (flown six times).

## How it works

- `legs.json` — the flight log: one entry per flight (date, departure,
  arrival, nautical miles) plus the tail number, aircraft type and
  total hours for the footer.
- `airports.json` — coordinates for every airport in the log.
- `us-states.json` — simplified US state boundaries (public domain
  GeoJSON) for the chart backdrop.
- `make_poster.py` — renders the 800×480 poster with Pillow, using
  only the panel's six colours (black, white, red, yellow, blue,
  green), so the preview on a computer is what the panel shows.
  Routes flown more than once are drawn thicker.
- `show_poster.py` — renders and pushes the poster to the panel via
  Pimoroni's `inky` library. A full Spectra 6 refresh takes about
  30 seconds; the picture then stays with the power off.
- `make_boot.py` / `show_boot.py` — the boot picture: the aeroplane's
  own photo (drop it in as `plane.jpg`), cropped and converted to the
  six-colour palette with a caption band, shown at power-up before
  the poster. `visual-logbook-boot.service` runs it at boot.

## Quick start

See [HOWTO.md](HOWTO.md) for the full build. Short version:

```
git clone https://github.com/markyharris/Visual-Logbook.git
cd Visual-Logbook
python3 show_poster.py
```

(with a Pi set up per the HOWTO: SPI and I2C enabled, `inky` and
`pillow` installed.)

## Adding a flight

Append one line to the `legs` list in `legs.json`, update `hours`,
re-run `show_poster.py`. New airport? Add its coordinates to
`airports.json` (any airport directory gives lat/lon). The map
re-scales itself to fit.

## The multi-plane system

Up to six aircraft share the frame, each with its own log, photo
and poster:

- `admin.py` — a web admin page (port 8080) to manage the planes,
  choose the one on display, drive the panel, and hold the
  settings. `logbook.py` is the shared data layer; per-plane logs
  live in `legs_<TAIL>.json` beside a Pi-local `config.json`
  (neither is committed — the repo ships `legs.json` as plane #1's
  seed and `config.example.json` as the shape).
- `fetch_flights.py` — a flight poller (timer, every 6 h) with
  two sources: FlightAware AeroAPI (primary) and the OpenSky
  Network (free backup — fills recent gaps a day behind, and a
  flight either source already logged is never added twice). It
  appends completed flights, computes miles from a bundled US
  airport dataset (`us_airports.json`, from OurAirports), adds
  airborne hours, and redraws the displayed plane's poster when
  it gains a flight.
- `buttons.py` — the panel buttons (A/B previous/next plane,
  C photo, D fetch now); remote buttons wired in parallel to the
  same GPIO pins work identically.
- `updater.py` — git-based update check ("Update available" flag)
  and Update now, in the admin. `rehome.py` + Comitup handle
  moving the frame to a new Wi-Fi network or owner.
- `boot_sequence.py` — at power-up: the display plane's photo,
  a dwell (admin setting), then its poster.
- `rotate.py` — optional auto-rotation: cycle every plane's
  poster, minutes-per-poster set in the admin.
