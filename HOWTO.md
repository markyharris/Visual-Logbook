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

4. Free the SPI chip-select pin. The inky library drives chip
   select in software, so the kernel's SPI driver must not claim
   GPIO8 — without this step the run stops with "some pins we need
   are in use! Chip Select … claimed by spi0 CS0" (Pimoroni's own
   troubleshooting note):

   ```
   echo "dtoverlay=spi0-0cs" | sudo tee -a /boot/firmware/config.txt
   sudo reboot
   ```

## 2. Install the software

```
sudo apt update
sudo apt install -y git python3-pip python3-pil fonts-dejavu-core
pip3 install --break-system-packages inky
git clone https://github.com/markyharris/Visual-Logbook.git
cd Visual-Logbook
```

## 3. First run

```
python3 show_poster.py
```

(On a fresh clone this also creates `config.json` and the first
plane's live log from the seed `legs.json` — see §7.)

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

## 5. The boot picture

Drop a photo of the aeroplane in the project folder as `plane.jpg`
(per plane: `plane_<TAIL>.jpg`), then:

```
python3 show_boot.py
```

builds the boot image (cropped to 5:3, caption band with the tail
number, converted to the panel's six colours) and puts it on the
panel. To have it greet you at every power-up, install the boot
service (§7): it shows the display plane's photo, waits the dwell
time from the admin settings, then settles on the poster. E-paper
holds its last image, so the photo is also simply what the frame
shows whenever it's off.

## 6. Keeping it current (manual, for now)

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

## 7. The multi-plane system (admin, FlightAware, buttons)

Up to 6 planes, each with its own log, photo and poster, managed
from a web admin page. Install the services once:

```
sudo apt install -y python3-gpiozero
sudo cp visual-logbook-admin.service visual-logbook-buttons.service \
        visual-logbook-fetch.service visual-logbook-fetch.timer \
        visual-logbook-boot.service visual-logbook-rotate.service \
        /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now visual-logbook-admin \
    visual-logbook-buttons visual-logbook-boot \
    visual-logbook-rotate
sudo systemctl enable --now visual-logbook-fetch.timer
```

The updater and the rehome button restart things without a
password prompt; grant exactly those commands:

```
echo "vislog ALL=(root) NOPASSWD: /usr/bin/systemctl restart visual-logbook-admin.service visual-logbook-buttons.service visual-logbook-boot.service visual-logbook-rotate.service, /usr/bin/nmcli connection delete *, /usr/bin/reboot" | sudo tee /etc/sudoers.d/visual-logbook
```

(adjust the user name if yours differs).

- **Admin page**: http://<pi>:8080 — add/edit planes, choose the
  one on display, show a poster or photo now, add flights by hand,
  fix unknown airports, set the photo dwell. Each plane's photo is
  uploaded right in its table row (any image; it's stored as
  `plane_<TAIL>.jpg` and its boot image rebuilds automatically) —
  or drop the file into the project folder yourself.
- **FlightAware**: get an AeroAPI key (flightaware.com → AeroAPI),
  paste it into Settings. The fetch timer then checks every 6
  hours: completed flights are appended with great-circle miles,
  airborne hours are added to the plane's total, and the poster
  redraws itself if that plane is on display. Airports not in the
  bundled US dataset appear under "Unknown airports" in the admin;
  give their coordinates once and they're never asked again.
- **OpenSky (free backup)**: create a free account at
  opensky-network.org, then create an API client in your account
  settings — that gives a client ID and a client secret. Paste
  both into Settings, under the FlightAware key. With those set,
  every fetch also asks OpenSky for the last 4 days: it's
  community ADS-B, a day behind FlightAware, and it only logs a
  flight when it can estimate both airports — low VFR hops with
  thin receiver coverage are often missed, and the times are
  first-seen/last-seen rather than true off/on, so the hours are
  approximate (the CSV Source column says "OpenSky" for these).
  A flight FlightAware already logged is never duplicated. The
  ICAO hex OpenSky keys on is computed from the N-number
  automatically; a non-US plane can set `"icao24": "…"` on its
  entry in config.json instead.
- **Flight data out**: every plane's row has a **Flights** link —
  its full history with dates, routes, miles and (for fetched
  flights) off/on times and per-flight hours — plus a CSV
  download; the header has "Download all flights (CSV)". The CSV
  (Date, Tail, Type, From, To, NM, FlightTime, OffUTC, OnUTC,
  Source) drops straight into a spreadsheet or a logbook import.
  Fetched flights carry their times; hand-added flights carry a
  time if you entered hours; the seed log's flights predate
  per-flight times, so their time cells are blank while the
  plane's Hobbs total still shows on the poster.
- **Rotation**: in Settings, tick "Rotate posters automatically"
  and set the minutes per poster — the panel cycles every plane
  that has flights (visual-logbook-rotate.service). Each plane's
  turn opens with its photo, held for the photo dwell, then its
  poster — the boot sequence, per plane. Manual shows and button
  presses don't fight it; the cycle resumes from whatever is up.
- **Buttons**: A/B = previous/next plane, C = photo, D = check
  flights now. The panel's built-in buttons and any remote
  buttons wired in parallel to GPIO 5 / 6 / 16 / 24 (to ground)
  are the same thing to the software.
- **Updates**: the admin's Update section checks GitHub daily-use
  style — Check now compares the clone against the repo; Update
  now pulls and restarts. `config.json`, the per-plane logs,
  photos and state are gitignored, so updates never touch them.
- **Rehome**: install Comitup (the fleet's standard Pi rehoming —
  see livesectional-lite's WIFI-PROVISIONING notes), then the
  admin's Rehome button can forget the current Wi-Fi and reboot
  into Comitup's phone-friendly setup access point.
