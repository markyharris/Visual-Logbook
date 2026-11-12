#!/usr/bin/env python3
"""Visual Logbook admin page (Pi, port 8080).

One stdlib-only web app: manage up to 6 planes, pick the one on
display, drive the panel (poster / photo), hold the FlightAware API
key, surface unknown airports and manual legs, and host the update
and rehome controls. LAN tool for the owner, like the fleet's other
admin pages — no login, don't expose it beyond the home network.

Run:  python3 admin.py            (visual-logbook-admin.service)
"""
import csv
import html
import io
import os
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import logbook  # noqa: E402

PORT = 8080


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


FAA_REGISTRY = ("https://registry.faa.gov/AircraftInquiry/Search/"
                "NNumberResult?nNumberTxt=")


def tail_html(tail):
    """The tail as a link to its FAA registration record.

    US N-numbers only — anything else (foreign registrations,
    military serials) stays plain text, since the FAA N-Number
    inquiry would have nothing for it.
    """
    t = str(tail).upper()
    if (len(t) > 1 and t.startswith("N")
            and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                    for c in t)):
        return (f"<a href='{FAA_REGISTRY}{t}' target='_blank' "
                f"rel='noopener'>{esc(t)}</a>")
    return esc(t)


def run_bg(*args):
    subprocess.Popen([sys.executable] + list(args), cwd=HERE,
                     stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)


def has_photo(cfg, tail):
    names = [f"plane_{tail}.jpg"]
    if cfg["planes"] and cfg["planes"][0]["tail"] == tail:
        names.append("plane.jpg")
    return any(os.path.exists(os.path.join(HERE, n)) for n in names)


def plane_stats(cfg, tail):
    data = logbook.load_plane(tail, cfg)
    legs = data.get("legs", [])
    last = max((l["date"] for l in legs), default="—")
    if isinstance(last, str) and last != "—":
        pass
    return data, len(legs), data.get("hours", 0), str(last)


def page(msg=""):
    cfg = logbook.load_config()
    state = logbook.load_state()
    disp = cfg["display_tail"]
    out = ["<!doctype html><meta name=viewport "
           "content='width=device-width,initial-scale=1'>"
           "<link rel=icon type=image/jpeg href=/favicon.jpg>"
           "<title>Visual Logbook</title>"
           "<style>body{font-family:sans-serif;margin:16px;"
           "max-width:860px}table{border-collapse:collapse}"
           "td,th{border:1px solid #999;padding:4px 8px}"
           "input{margin:2px}fieldset{margin:12px 0}"
           ".msg{background:#efe;border:1px solid #9c9;"
           "padding:6px}</style>",
           "<h1><img src=/favicon.jpg alt='' "
           "style='height:30px;width:30px;vertical-align:-5px;"
           "border-radius:4px'> Visual Logbook — Admin</h1>"]
    if msg:
        out.append(f"<p class=msg>{esc(msg)}</p>")
    if state.get("update_available"):
        out.append("<p class=msg><b>Update available</b> — see the "
                   "Update section below.</p>")
    out.append(f"<p>On display: <b>{esc(disp)}</b> · "
               f"{len(cfg['planes'])} of {logbook.MAX_PLANES} planes · "
               f"<a href='/export'>Download all flights (CSV)</a></p>")

    # ---- planes table ---------------------------------------------
    out.append("<h2>Aircraft</h2><table><tr><th>Tail</th><th>Type</th>"
               "<th>Home</th><th>Flights</th><th>Hours</th>"
               "<th>Last flight</th><th>Last FA check</th>"
               "<th>Actions</th></tr>")
    for p in cfg["planes"]:
        tail = p["tail"]
        _d, n, hrs, last = plane_stats(cfg, tail)
        lf = state.get("last_fetch", {}).get(tail, {})
        lf_txt = esc(lf.get("when", "never"))
        if lf.get("note"):
            lf_txt += f" ({esc(lf['note'])})"
        star = " ★" if tail == disp else ""
        out.append(
            f"<tr><td><b>{tail_html(tail)}</b>{star}</td>"
            f"<td>{esc(p['type'])}</td><td>{esc(p['home'])}</td>"
            f"<td>{n}</td><td>{hrs:.1f}</td><td>{esc(last)}</td>"
            f"<td>{lf_txt}</td><td>"
            f"<form method=post action=/show style=display:inline>"
            f"<input type=hidden name=tail value='{esc(tail)}'>"
            f"<button name=what value=poster>Poster</button>"
            f"<button name=what value=photo>Photo</button></form> "
            f"<form method=get action=/flights "
            f"style=display:inline><input type=hidden name=tail "
            f"value='{esc(tail)}'><button>Flights</button></form> "
            f"<form method=post action=/set_display "
            f"style=display:inline><input type=hidden name=tail "
            f"value='{esc(tail)}'><button>Set display</button></form> "
            f"<form method=post action=/delete_plane "
            f"style=display:inline><input type=hidden name=tail "
            f"value='{esc(tail)}'><button>Delete</button></form><br>"
            f"{'Photo ✓' if has_photo(cfg, tail) else 'No photo'} "
            f"<form method=post action=/upload_photo "
            f"enctype=multipart/form-data style=display:inline>"
            f"<input type=hidden name=tail value='{esc(tail)}'>"
            f"<input type=file name=photo accept='image/*' required> "
            f"<button>Upload photo</button></form>"
            f"</td></tr>")
    out.append("</table>")

    # ---- add / edit plane ------------------------------------------
    out.append("<fieldset><legend>Add or edit a plane</legend>"
               "<form method=post action=/save_plane>"
               "Tail <input name=tail size=9 required> "
               "Type <input name=type size=16> "
               "Home <input name=home size=6 value=KFLG> "
               "Home label <input name=home_label size=18 "
               "value='Flagstaff, Arizona'><br>"
               "Hours so far <input name=hours size=6 value=0> "
               "<button>Save plane</button></form>"
               "<small>Saving an existing tail edits it. A new "
               "plane starts with an empty log (seed its hours "
               "above); its photo is plane_&lt;TAIL&gt;.jpg dropped "
               "in the project folder.</small></fieldset>")

    # ---- settings ----------------------------------------------------
    key_set = "set (leave blank to keep)" if cfg.get("fa_api_key") \
        else "not set"
    os_set = "set (leave blank to keep)" if cfg.get(
        "opensky_client_secret") else "not set"
    out.append("<fieldset><legend>Settings</legend>"
               "<form method=post action=/save_settings>"
               f"FlightAware AeroAPI key <input type=password "
               f"name=fa_api_key size=34 placeholder='{key_set}'> "
               f"Photo dwell (s) <input name=dwell_seconds size=4 "
               f"value={int(cfg.get('dwell_seconds', 30))}><br>"
               f"OpenSky client ID <input name=opensky_client_id "
               f"size=20 value='{esc(cfg.get('opensky_client_id', ''))}'> "
               f"secret <input type=password "
               f"name=opensky_client_secret size=20 "
               f"placeholder='{os_set}'> "
               f"<small>(free backup source)</small><br>"
               f"<label><input type=checkbox name=rotate value=yes "
               f"{'checked' if cfg.get('rotate') else ''}> "
               f"Rotate posters automatically</label> "
               f"every <input name=rotate_minutes size=3 "
               f"value={int(cfg.get('rotate_minutes', 10))}> minutes "
               "<button>Save settings</button></form>"
               "<form method=post action=/fetch_now>"
               "<button>Check flights now</button></form>"
               "</fieldset>")

    # ---- unknown airports + manual leg ------------------------------
    unknowns = {}
    for p in cfg["planes"]:
        data = logbook.load_plane(p["tail"], cfg)
        _f, unk = logbook.airports_for(data)
        for u in unk:
            unknowns.setdefault(u, []).append(p["tail"])
    out.append("<fieldset><legend>Unknown airports</legend>")
    if unknowns:
        for ident, tails in sorted(unknowns.items()):
            out.append(f"<form method=post action=/add_airport>"
                       f"<b>{esc(ident)}</b> (in {esc(', '.join(tails))}) "
                       f"<input type=hidden name=ident "
                       f"value='{esc(ident)}'>"
                       f"Lat <input name=lat size=9> "
                       f"Lon <input name=lon size=10> "
                       f"Name <input name=name size=18> "
                       f"<button>Add airport</button></form>")
    else:
        out.append("None — every airport in every log resolves.")
    out.append("</fieldset>")

    opts = "".join(f"<option>{esc(p['tail'])}</option>"
                   for p in cfg["planes"])
    out.append("<fieldset><legend>Add a flight by hand</legend>"
               "<form method=post action=/add_leg>"
               f"Plane <select name=tail>{opts}</select> "
               "Date <input name=date type=date required> "
               "From <input name=dep size=6 required> "
               "To <input name=arr size=6 required> "
               "NM <input name=nm size=5> "
               "Hours <input name=hours size=5> "
               "<button>Add flight</button></form>"
               "<small>NM blank = great-circle from the airport "
               "coordinates. Hours adds to the plane's total.</small>"
               "</fieldset>")

    # ---- update + rehome ---------------------------------------------
    lu = state.get("last_update_check") or "never"
    out.append("<fieldset><legend>Update</legend>"
               f"Last checked: {esc(lu)} · "
               f"Update available: "
               f"<b>{'yes' if state.get('update_available') else 'no'}"
               f"</b>"
               "<form method=post action=/update_check "
               "style=display:inline> <button>Check now</button>"
               "</form>"
               "<form method=post action=/update_now "
               "style=display:inline> <button>Update now</button>"
               "</form></fieldset>")
    out.append("<fieldset><legend>Rehome (Wi-Fi)</legend>"
               "If this frame moves to a new network or owner: "
               "forget the current Wi-Fi and reboot — Comitup will "
               "offer its setup access point for joining the new "
               "network from a phone.<br>"
               "<form method=post action=/rehome>"
               "<label><input type=checkbox name=sure value=yes> "
               "I understand — the frame will drop off this network"
               "</label> <button>Forget Wi-Fi and reboot</button>"
               "</form></fieldset>")
    out.append("</html>")
    return "".join(out)


CSV_FIELDS = ["Date", "Tail", "Type", "From", "To", "NM",
              "FlightTime", "OffUTC", "OnUTC", "Source"]


def flights_csv(cfg, tails):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CSV_FIELDS)
    for tail in tails:
        data = logbook.load_plane(tail, cfg)
        for leg in data.get("legs", []):
            w.writerow([
                leg.get("date", ""), tail, data.get("aircraft", ""),
                leg.get("dep", ""), leg.get("arr", ""),
                leg.get("nm", ""), leg.get("time", ""),
                leg.get("off", ""), leg.get("on", ""),
                "manual" if str(leg.get("fa_id", "")).startswith(
                    "manual") else (
                    "OpenSky" if str(leg.get("fa_id", "")).startswith(
                        "opensky-") else (
                        "FlightAware" if leg.get("fa_id")
                        else "log"))])
    return buf.getvalue()


def flights_page(cfg, tail):
    data = logbook.load_plane(tail, cfg)
    rows = []
    t_nm = t_time = 0.0
    for leg in data.get("legs", []):
        t_nm += leg.get("nm", 0) or 0
        t_time += leg.get("time", 0) or 0
        rows.append(
            f"<tr><td>{esc(leg.get('date', ''))}</td>"
            f"<td>{esc(leg.get('dep', ''))}</td>"
            f"<td>{esc(leg.get('arr', ''))}</td>"
            f"<td>{esc(leg.get('nm', ''))}</td>"
            f"<td>{esc(leg.get('time', ''))}</td>"
            f"<td>{esc(leg.get('off', ''))}</td>"
            f"<td>{esc(leg.get('on', ''))}</td></tr>")
    return ("<!doctype html><meta name=viewport "
            "content='width=device-width,initial-scale=1'>"
            f"<title>{esc(tail)} flights</title>"
            "<style>body{font-family:sans-serif;margin:16px}"
            "table{border-collapse:collapse}td,th{border:1px solid "
            "#999;padding:4px 8px}</style>"
            f"<h1>{tail_html(tail)} — {esc(data.get('aircraft', ''))}</h1>"
            f"<p>{len(rows)} flights · {t_nm:,.0f} NM · "
            f"{t_time:.1f} h timed flights "
            f"(plane total {data.get('hours', 0):.1f} h)</p>"
            f"<p><a href='/export?tail={esc(tail)}'>"
            "Download CSV</a> · <a href='/'>Back to admin</a></p>"
            "<table><tr><th>Date</th><th>From</th><th>To</th>"
            "<th>NM</th><th>Time (h)</th><th>Off (UTC)</th>"
            "<th>On (UTC)</th></tr>" + "".join(rows) + "</table>")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, code=200):
        b = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _multipart(self):
        """{field: (filename, bytes or text)} from a multipart body."""
        ctype = self.headers.get("Content-Type", "")
        m = re.search(r"boundary=([^;]+)", ctype)
        if not m:
            return {}
        boundary = ("--" + m.group(1).strip().strip('"')).encode()
        n = int(self.headers.get("Content-Length", 0))
        if n > 16 * 1024 * 1024:
            raise ValueError("upload too large (16 MB max)")
        body = self.rfile.read(n)
        fields = {}
        for part in body.split(boundary):
            if b"\r\n\r\n" not in part:
                continue
            head, content = part.split(b"\r\n\r\n", 1)
            if content.endswith(b"\r\n"):
                content = content[:-2]
            dm = re.search(rb'name="([^"]+)"', head)
            if not dm:
                continue
            name = dm.group(1).decode()
            fm = re.search(rb'filename="([^"]*)"', head)
            if fm:
                fields[name] = (fm.group(1).decode(), content)
            else:
                fields[name] = (None, content.decode(errors="replace"))
        return fields

    def _form(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n).decode() if n else ""
        return {k: v[0] for k, v in parse_qs(raw).items()}

    def _upload_photo(self):
        cfg = logbook.load_config()
        try:
            fields = self._multipart()
            tail = fields.get("tail", (None, ""))[1].strip().upper()
            filename, content = fields.get("photo", (None, b""))
            if logbook.plane_cfg(cfg, tail) is None:
                raise ValueError("unknown plane")
            if not filename or not content:
                raise ValueError("no file chosen")
            from PIL import Image
            img = Image.open(io.BytesIO(content))
            img.convert("RGB").save(
                os.path.join(HERE, f"plane_{tail}.jpg"), quality=92)
            stale = os.path.join(HERE, f"boot_{tail}.png")
            if os.path.exists(stale):
                os.remove(stale)
            if cfg["planes"] and cfg["planes"][0]["tail"] == tail:
                old = os.path.join(HERE, "boot.png")
                if os.path.exists(old):
                    os.remove(old)
            run_bg("make_boot.py", f"plane_{tail}.jpg",
                   f"boot_{tail}.png", "--tail", tail)
            msg = (f"Photo saved for {tail} — its boot image is "
                   f"rebuilding; the Photo button shows it.")
        except Exception as e:
            msg = f"Upload error: {e}"
        self._send(page(msg))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/export", "/flights"):
            cfg = logbook.load_config()
            q = {k: v[0] for k, v in
                 parse_qs(parsed.query).items()}
            if path == "/flights":
                self._send(flights_page(
                    cfg, q.get("tail", cfg["display_tail"])))
                return
            tail = q.get("tail")
            tails = [tail] if tail else [p["tail"]
                                          for p in cfg["planes"]]
            body = flights_csv(cfg, tails).encode()
            name = f"visual-logbook-{tail or 'all'}.csv"
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Disposition",
                             f"attachment; filename={name}")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path in ("/favicon.jpg", "/favicon.ico", "/favicon.png"):
            try:
                import favicon_data
                b = favicon_data.ICON_JPG
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(b)))
                self.send_header("Cache-Control", "max-age=86400")
                self.end_headers()
                self.wfile.write(b)
            except Exception:
                self.send_response(404)
                self.end_headers()
            return
        self._send(page())

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/upload_photo":
            self._upload_photo()
            return
        f = self._form()
        cfg = logbook.load_config()
        msg = ""
        try:
            if path == "/show":
                tail = f["tail"]
                run_bg("show_poster.py" if f.get("what") != "photo"
                       else "show_boot.py", "--tail", tail)
                msg = f"Showing {f.get('what', 'poster')} for {tail} — give the panel ~30 s."
            elif path == "/set_display":
                cfg["display_tail"] = f["tail"]
                logbook.save_config(cfg)
                msg = f"{f['tail']} is now the display plane."
            elif path == "/save_plane":
                tail = f["tail"].strip().upper()
                pc = logbook.plane_cfg(cfg, tail)
                entry = {"tail": tail, "type": f.get("type", ""),
                         "home": f.get("home", "KFLG").strip().upper(),
                         "home_label": f.get("home_label", "")}
                if pc:
                    pc.update(entry)
                    msg = f"{tail} updated."
                else:
                    if len(cfg["planes"]) >= logbook.MAX_PLANES:
                        msg = "Plane limit reached (6)."
                    else:
                        cfg["planes"].append(entry)
                        data = logbook.load_plane(tail, cfg)
                        data["hours"] = float(f.get("hours") or 0)
                        logbook.save_plane(data)
                        msg = f"{tail} added."
                logbook.save_config(cfg)
            elif path == "/delete_plane":
                tail = f["tail"]
                cfg["planes"] = [p for p in cfg["planes"]
                                 if p["tail"] != tail]
                if cfg["display_tail"] == tail and cfg["planes"]:
                    cfg["display_tail"] = cfg["planes"][0]["tail"]
                logbook.save_config(cfg)
                msg = f"{tail} removed (its log file stays on disk)."
            elif path == "/save_settings":
                if f.get("fa_api_key"):
                    cfg["fa_api_key"] = f["fa_api_key"].strip()
                cfg["opensky_client_id"] = (
                    f.get("opensky_client_id") or "").strip()
                if f.get("opensky_client_secret"):
                    cfg["opensky_client_secret"] = f[
                        "opensky_client_secret"].strip()
                cfg["dwell_seconds"] = max(
                    0, int(f.get("dwell_seconds") or 30))
                cfg["rotate"] = f.get("rotate") == "yes"
                cfg["rotate_minutes"] = max(
                    1, int(f.get("rotate_minutes") or 10))
                logbook.save_config(cfg)
                msg = "Settings saved."
            elif path == "/fetch_now":
                run_bg("fetch_flights.py")
                msg = "Flight check started (FlightAware + OpenSky)."
            elif path == "/add_airport":
                logbook.add_custom_airport(f["ident"], f["lat"],
                                           f["lon"], f.get("name", ""))
                msg = f"{f['ident']} added — redraw a poster to use it."
            elif path == "/add_leg":
                tail = f["tail"]
                data = logbook.load_plane(tail, cfg)
                dep = f["dep"].strip().upper()
                arr = f["arr"].strip().upper()
                nm = f.get("nm", "").strip()
                if not nm:
                    a, b = logbook.resolve_airport(dep), \
                        logbook.resolve_airport(arr)
                    if a and b:
                        import greatcircle
                        nm = round(greatcircle.nm(a, b))
                    else:
                        nm = 0
                leg = {
                    "date": f["date"], "dep": dep, "arr": arr,
                    "nm": int(nm), "fa_id": f"manual-{f['date']}-{dep}-{arr}"}
                if f.get("hours"):
                    leg["time"] = float(f["hours"])
                data["legs"].append(leg)
                if f.get("hours"):
                    data["hours"] = round(
                        float(data.get("hours", 0)) +
                        float(f["hours"]), 1)
                data["legs"].sort(key=lambda l: l["date"])
                logbook.save_plane(data)
                msg = f"Flight added to {tail}."
            elif path == "/update_check":
                run_bg("updater.py", "check")
                msg = "Update check started — refresh in a few seconds."
            elif path == "/update_now":
                run_bg("updater.py", "apply")
                msg = "Updating — services restart; panel redraws after."
            elif path == "/rehome":
                if f.get("sure") == "yes":
                    run_bg("rehome.py")
                    msg = "Wi-Fi forgotten; rebooting into setup mode."
                else:
                    msg = "Tick the understand box first."
            else:
                msg = "Unknown action."
        except Exception as e:  # keep the page alive on bad input
            msg = f"Error: {e}"
        self._send(page(msg))


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
