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

## Roadmap

- Automatic updates: watch FlightAware for the tail number and add
  new flights by itself.
- The panel's four side buttons page between posters (a second
  aircraft, a statistics page).
- Wi-Fi rehoming and update checks, matching the rest of the fleet's
  house rules.
