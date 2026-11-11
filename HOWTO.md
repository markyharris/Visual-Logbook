# Visual Logbook — HOWTO

Build and run the flight-log poster on a Raspberry Pi with a Pimoroni
Inky Impression 7.3" (Spectra 6) colour e-paper display.

## Parts

- Pimoroni Inky Impression 7.3" (Spectra 6, 800×480) — PIM773
- Raspberry Pi with a 40-pin GPIO header (Pi 5 / 4 / 3 / Zero 2 W all
  work; the poster renders in a second or two on any of them)
- microSD card, Pi power supply
- A frame or stand of your choosing (the panel is the picture)

## 1. Prepare the Pi

1. Flash Raspberry Pi OS (Bookworm or later) with Raspberry Pi
   Imager. Set your Wi-Fi, hostname and SSH in the imager's settings
   if you want headless access.
2. Seat the Pi on the Inky Impression's GPIO header (or the panel on
   the Pi — the two boards stack), connect power, boot.
3. Enable the interfaces the panel needs:

   ```
   sudo raspi-config
   ```

   Interface Options → SPI → Yes, and I2C → Yes. Reboot.

## 2. Install the software

```
sudo apt update
sudo apt install -y git python3-pip python3-pil
pip3 install --break-system-packages inky
git clone https://github.com/markyharris/Visual-Logbook.git
cd Visual-Logbook
```

## 3. First run

```
python3 show_poster.py
```

The poster renders, then the panel refreshes — Spectra 6 takes
about 30 seconds and cycles through its colours while it works.
That is normal. The finished poster then stays on the panel even
with the power unplugged (e-paper holds its image).

To preview on any computer instead (no panel needed):

```
python3 make_poster.py poster.png
```

## 4. Your own log

- `legs.json` holds the flying. Each leg is
  `{"date": "2026-07-15", "dep": "KDLH", "arr": "KPWK", "nm": 338}`.
  Set `tail`, `aircraft` and `hours` at the top of the file.
- Every airport in the log needs an entry in `airports.json`:
  `{"lat": 46.8421, "lon": -92.1936, "name": "Duluth Intl, MN"}`.
  Lat/lon for any field is on its AirNav or SkyVector page.
- Airports you've only flown locally at (departure = arrival) draw
  as a dot with no line, which is honest — they were still flights,
  and they count in the footer.
- Re-run `python3 show_poster.py` after any edit. The map re-fits
  itself to the airports in the log.

## 5. Keeping it current (manual, for now)

After a flight, add the leg to `legs.json`, bump `hours`, and re-run.
Automatic FlightAware updates are on the roadmap.

## Notes and gotchas

- Colours are drawn from the panel's own six-colour palette, so
  there is no dithering guesswork: the PNG preview is faithful.
- Route line width encodes frequency: 2 px flown once, 3 px twice,
  4 px three or more. The home airport (KFLG) gets a red ring.
- State outlines are dashed, chart-style, and clipped to the map
  area, which is fitted to your airports — fly somewhere new and the
  map politely makes room.
