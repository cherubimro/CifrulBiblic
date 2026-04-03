#!/usr/bin/env python3
"""
Luna de Sânge — Eclipse lunare via NASA/JPL Horizons
=====================================================
Interogare directă NASA Horizons pentru pozițiile exacte ale Lunii
și Soarelui, apoi calcul precis al eclipselor lunare.

Utilizare:
    python blood_moon_horizons.py 33 33          # anul 33 d.Hr.
    python blood_moon_horizons.py 30 36          # anii 30-36 d.Hr.
    python blood_moon_horizons.py 2025 2025      # anul 2025
    python blood_moon_horizons.py 33 33 --serve  # dashboard web

Precizie: NASA JPL DE441 ephemeris (acuratețe sub 1 arcsecundă).

Surse:
  - NASA/JPL Horizons: ssd.jpl.nasa.gov/horizons/
  - Humphreys & Waddington (1983) Nature 306, 743-746
  - NASA GSFC Eclipse catalog: eclipse.gsfc.nasa.gov
"""

import sys
import time
import ssl
import math
import json
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import quote

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
API_BASE = "ssd.jpl.nasa.gov/api/horizons.api"
DEG = math.pi / 180
RAD = 180 / math.pi

JERUSALEM_LAT = 31.7683
JERUSALEM_LON = 35.2137

MOON_RADIUS_DEG = 0.259
EARTH_UMBRA_DEG = 0.72     # raza umbră — calibrată pe NASA GSFC (U.Radius variază 0.62-0.76°)
EARTH_PENUMBRA_DEG = 1.27   # raza penumbră — calibrată pe NASA GSFC (P.Radius variază 1.14-1.30°)

# ---------------------------------------------------------------------------
# HORIZONS API
# ---------------------------------------------------------------------------

def build_url(target, start, stop, step="1d", scheme="https"):
    """Construiește URL Horizons pentru un corp ceresc."""
    # Quantities: 1=RA/DEC, 20=observer range, 31=ecliptic lon/lat
    pairs = [
        ("format", "text"),
        ("COMMAND", f"'{target}'"),
        ("OBJ_DATA", "'NO'"),
        ("MAKE_EPHEM", "'YES'"),
        ("EPHEM_TYPE", "'OBSERVER'"),
        ("CENTER", "'500@399'"),          # geocentric
        ("START_TIME", f"'{start}'"),
        ("STOP_TIME", f"'{stop}'"),
        ("STEP_SIZE", f"'{step}'"),
        ("QUANTITIES", "'1,31'"),          # RA/DEC + ecliptic lon/lat
        ("CAL_FORMAT", "'CAL'"),
        ("ANG_FORMAT", "'DEG'"),
        ("CSV_FORMAT", "'YES'"),
        ("EXTRA_PREC", "'YES'"),
    ]
    qs = "&".join(f"{k}={v}" for k, v in pairs)
    # Encode spaces in URL
    qs = qs.replace(" ", "%20")
    return f"{scheme}://{API_BASE}?{qs}"


def fetch_url(url):
    """Fetch URL cu fallback HTTPS → HTTP."""
    for scheme_label, ctx_flag in [("HTTPS", None), ("HTTPS noverify", "_nv"), ("HTTP", None)]:
        actual_url = url
        if scheme_label == "HTTP":
            actual_url = url.replace("https://", "http://")
        ctx = None
        if ctx_flag == "_nv":
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        try:
            req = Request(actual_url, headers={"User-Agent": "blood_moon_horizons/1.0"})
            kwargs = {"timeout": 90}
            if ctx:
                kwargs["context"] = ctx
            with urlopen(req, **kwargs) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, OSError):
            continue
    raise ConnectionError("Nu mă pot conecta la JPL Horizons")


def parse_horizons_csv(raw):
    """Parsează răspunsul CSV Horizons. Returnează listă de dict-uri."""
    lines = raw.split("\n")
    soe = eoe = None
    for i, ln in enumerate(lines):
        if ln.strip() == "$$SOE":
            soe = i
        elif ln.strip() == "$$EOE":
            eoe = i
    if soe is None or eoe is None:
        return []

    rows = []
    for ln in lines[soe + 1:eoe]:
        ln = ln.strip()
        if not ln:
            continue
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) < 6:
            continue
        try:
            date_str = parts[0]
            ra = float(parts[3])
            dec = float(parts[4])
            ecl_lon = float(parts[5])
            ecl_lat = float(parts[6]) if len(parts) > 6 else 0.0
            rows.append({
                'date': date_str,
                'ra': ra, 'dec': dec,
                'ecl_lon': ecl_lon, 'ecl_lat': ecl_lat,
            })
        except (ValueError, IndexError):
            continue
    return rows


# ---------------------------------------------------------------------------
# CALCUL ECLIPSE
# ---------------------------------------------------------------------------

def angular_sep(lon1, lat1, lon2, lat2):
    """Separare unghiulară (grade)."""
    l1, b1, l2, b2 = lon1 * DEG, lat1 * DEG, lon2 * DEG, lat2 * DEG
    cos_d = math.sin(b1) * math.sin(b2) + math.cos(b1) * math.cos(b2) * math.cos(l1 - l2)
    return math.acos(max(-1, min(1, cos_d))) * RAD


def moon_alt_from_radec(ra, dec, jd, lat, lon):
    """Altitudinea din RA/Dec geocentrice (aproximare)."""
    T = (jd - 2451545.0) / 36525.0
    GMST = (280.46061837 + 360.98564736629 * (jd - 2451545.0)) % 360
    LST = (GMST + lon) % 360
    H = (LST - ra) % 360
    Hr, dr, lr = H * DEG, dec * DEG, lat * DEG
    sa = math.sin(dr) * math.sin(lr) + math.cos(dr) * math.cos(lr) * math.cos(Hr)
    return math.asin(max(-1, min(1, sa))) * RAD


def jd_to_horizons_date(jd):
    """JD → string format Horizons 'AD YYYY-Mon-DD HH:MM'."""
    z = int(jd + 0.5)
    A = z
    if z >= 2299161:
        alpha = int((z - 1867216.25) / 36524.25)
        A = z + 1 + alpha - int(alpha / 4)
    B = A + 1524
    C = int((B - 122.1) / 365.25)
    D = int(365.25 * C)
    E = int((B - D) / 30.6001)
    day = B - D - int(30.6001 * E)
    month = E - 1 if E < 14 else E - 13
    year = C - 4716 if month > 2 else C - 4715
    frac = (jd + 0.5) - int(jd + 0.5)
    hour = int(frac * 24)
    minute = int((frac * 24 - hour) * 60)
    mn = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    return f"AD {year:04d}-{mn[month-1]}-{day:02d} {hour:02d}:{minute:02d}"


def julian_date_approx(date_str):
    """Parsează data Horizons '2025-Mar-14 07:15' → JD aproximativ."""
    months = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
              'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
    try:
        parts = date_str.split()
        ymd = parts[0].split("-")
        year = int(ymd[0])
        month = months.get(ymd[1], 1)
        day = int(ymd[2])
        hm = parts[1].split(":") if len(parts) > 1 else ["12", "00"]
        frac = int(hm[0]) / 24.0 + int(hm[1]) / 1440.0
        y, m = year, month
        if m <= 2:
            y -= 1
            m += 12
        # Corecția gregoriană doar după 15 oct 1582
        B = 0
        if year > 1582 or (year == 1582 and month > 10) or (year == 1582 and month == 10 and day >= 15):
            A = int(y / 100)
            B = 2 - A + int(A / 4)
        return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + day + frac + B - 1524.5
    except:
        return 2451545.0



def jerusalem_local_time(date_str):
    """UT date string -> ora locala Ierusalim (UT + 2h21m)."""
    try:
        parts = date_str.split()
        hm = parts[-1].split(':')
        h = int(hm[0]) + 2
        m = int(hm[1]) + 21
        if m >= 60: h += 1; m -= 60
        if h >= 24: h -= 24
        return f'{h:02d}:{m:02d}'
    except:
        return '??:??'

def find_eclipses_horizons(year_start, year_end):
    """Interogă Horizons pentru Lună și Soare, găsește eclipsele.
    Faza 1: scanare la 6h pentru detectarea lunilor pline.
    Faza 2: re-interogare la 10 min pe ±12h în jurul fiecărei luni pline,
            pentru precizie maximă la magnitudine și timp.
    """
    start = f"AD {year_start}-Jan-01" if year_start > 0 else f"{year_start}-Jan-01"
    stop = f"AD {year_end}-Dec-31" if year_end > 0 else f"{year_end}-Dec-31"

    # ── Faza 1: scanare grosieră la 6h ──
    step = "6h"
    print(f"  Faza 1: scanare grosieră ({start} → {stop}, pas 6h) …")
    print(f"    Interogare Horizons: Luna …")
    url_moon = build_url("301", start, stop, step)
    raw_moon = fetch_url(url_moon)
    time.sleep(2)
    moon_data = parse_horizons_csv(raw_moon)
    print(f"    Luna: {len(moon_data)} puncte")

    print(f"    Interogare Horizons: Soarele …")
    url_sun = build_url("10", start, stop, step)
    raw_sun = fetch_url(url_sun)
    time.sleep(2)
    sun_data = parse_horizons_csv(raw_sun)
    print(f"    Soarele: {len(sun_data)} puncte")

    if len(moon_data) != len(sun_data):
        n = min(len(moon_data), len(sun_data))
        moon_data = moon_data[:n]
        sun_data = sun_data[:n]

    # Găsim momentele de lună plină, filtrate pe latitudine ecliptică
    full_moon_dates = []
    prev_elong = None
    n = min(len(moon_data), len(sun_data))
    for i in range(n):
        elong = (moon_data[i]['ecl_lon'] - sun_data[i]['ecl_lon']) % 360
        if prev_elong is not None and prev_elong < 180 and elong >= 180:
            lat = moon_data[i]['ecl_lat']
            if abs(lat) <= 1.6:  # doar candidatele cu eclipsă posibilă
                full_moon_dates.append(moon_data[i]['date'])
        prev_elong = elong

    print(f"    Luni pline detectate: {len(full_moon_dates)}")

    # ── Faza 2: re-interogare fină (10 min) pentru fiecare lună plină ──
    eclipses = []
    for fm_idx, fm_date in enumerate(full_moon_dates):
        # Construim fereastra ±12h din data lunii pline
        jd_fm = julian_date_approx(fm_date)
        # Start = -12h, Stop = +12h
        jd_start = jd_fm - 0.5
        jd_stop = jd_fm + 0.5

        # Convertim JD înapoi la date string pentru Horizons
        fm_start_str = jd_to_horizons_date(jd_start)
        fm_stop_str = jd_to_horizons_date(jd_stop)

        url_m = build_url("301", fm_start_str, fm_stop_str, "10m")
        url_s = build_url("10", fm_start_str, fm_stop_str, "10m")

        try:
            raw_m = fetch_url(url_m)
            raw_s = fetch_url(url_s)
        except:
            continue

        md = parse_horizons_csv(raw_m)
        sd = parse_horizons_csv(raw_s)
        if not md or not sd:
            continue
        n = min(len(md), len(sd))

        # Găsim separarea minimă Lună — anti-Soare
        best_sep = 999
        best_idx = 0
        for k in range(n):
            anti_lon = (sd[k]['ecl_lon'] + 180) % 360
            sep = angular_sep(md[k]['ecl_lon'], md[k]['ecl_lat'], anti_lon, 0.0)
            if sep < best_sep:
                best_sep = sep
                best_idx = k

        sep = best_sep
        bm = md[best_idx]
        bs = sd[best_idx]

        eclipse_type = None
        magnitude = 0.0

        if sep < EARTH_PENUMBRA_DEG + MOON_RADIUS_DEG:
            eclipse_type = "penumbrală"
            if sep < EARTH_UMBRA_DEG + MOON_RADIUS_DEG:
                if sep + MOON_RADIUS_DEG <= EARTH_UMBRA_DEG:
                    eclipse_type = "TOTALĂ"
                    magnitude = 1.0 + (EARTH_UMBRA_DEG - sep - MOON_RADIUS_DEG) / (2 * MOON_RADIUS_DEG)
                else:
                    eclipse_type = "parțială"
                    magnitude = (EARTH_UMBRA_DEG + MOON_RADIUS_DEG - sep) / (2 * MOON_RADIUS_DEG)

        if eclipse_type:
            jd = julian_date_approx(bm['date'])
            alt = moon_alt_from_radec(bm['ra'], bm['dec'], jd,
                                      JERUSALEM_LAT, JERUSALEM_LON)
            eclipses.append({
                'date': bm['date'],
                'type': eclipse_type,
                'magnitude': magnitude,
                'moon_lat': bm['ecl_lat'],
                'alt_jerusalem': alt,
                'visible_jerusalem': alt > 0,
                'separation': sep,
                })

        prev_elong = elong

    return eclipses


def find_eclipses_horizons_sse(year_start, year_end, send_event):
    """Versiune cu SSE — trimite progresul pas cu pas."""
    start = f"AD {year_start}-Jan-01" if year_start > 0 else f"{year_start}-Jan-01"
    stop = f"AD {year_end}-Dec-31" if year_end > 0 else f"{year_end}-Dec-31"
    step = "6h"

    send_event("progress", {"msg": f"Faza 1: interogare Luna ({start} \u2192 {stop}) \u2026"})
    url_moon = build_url("301", start, stop, step)
    raw_moon = fetch_url(url_moon)
    time.sleep(2)
    moon_data = parse_horizons_csv(raw_moon)
    send_event("progress", {"msg": f"Luna: {len(moon_data)} puncte. Interogare Soarele \u2026"})

    url_sun = build_url("10", start, stop, step)
    raw_sun = fetch_url(url_sun)
    time.sleep(2)
    sun_data = parse_horizons_csv(raw_sun)
    send_event("progress", {"msg": f"Soarele: {len(sun_data)} puncte. Detectare luni pline \u2026"})

    n = min(len(moon_data), len(sun_data))
    moon_data = moon_data[:n]
    sun_data = sun_data[:n]

    full_moon_candidates = []
    prev_elong = None
    for i in range(n):
        elong = (moon_data[i]['ecl_lon'] - sun_data[i]['ecl_lon']) % 360
        if prev_elong is not None and prev_elong < 180 and elong >= 180:
            # Filtrare rapidă: latitudinea ecliptică prea mare = imposibil eclipsă
            # Penumbra + raza Lunii ≈ 1.53° — dacă |lat| > 1.6°, skip
            lat = moon_data[i]['ecl_lat']
            if abs(lat) <= 1.6:
                full_moon_candidates.append(moon_data[i]['date'])
        prev_elong = elong

    send_event("progress", {"msg": f"Faza 2: {len(full_moon_candidates)} candidate din luni pline (filtrate). Verificare la 10 min \u2026"})

    eclipses = []
    for fm_idx, fm_date in enumerate(full_moon_candidates):
        send_event("progress", {"msg": f"Candidat {fm_idx+1}/{len(full_moon_candidates)}: {fm_date} \u2026"})
        jd_fm = julian_date_approx(fm_date)
        fm_start_str = jd_to_horizons_date(jd_fm - 0.5)
        fm_stop_str = jd_to_horizons_date(jd_fm + 0.5)
        try:
            url_m = build_url("301", fm_start_str, fm_stop_str, "10m")
            url_s = build_url("10", fm_start_str, fm_stop_str, "10m")
            raw_m = fetch_url(url_m)
            time.sleep(2)
            raw_s = fetch_url(url_s)
            time.sleep(2)
        except:
            continue
        md = parse_horizons_csv(raw_m)
        sd = parse_horizons_csv(raw_s)
        if not md or not sd:
            continue
        nn = min(len(md), len(sd))
        best_sep = 999
        best_idx = 0
        for k in range(nn):
            anti_lon = (sd[k]['ecl_lon'] + 180) % 360
            sep = angular_sep(md[k]['ecl_lon'], md[k]['ecl_lat'], anti_lon, 0.0)
            if sep < best_sep:
                best_sep = sep
                best_idx = k
        sep = best_sep
        bm = md[best_idx]
        eclipse_type = None
        magnitude = 0.0
        if sep < EARTH_PENUMBRA_DEG + MOON_RADIUS_DEG:
            eclipse_type = "penumbral\u0103"
            if sep < EARTH_UMBRA_DEG + MOON_RADIUS_DEG:
                if sep + MOON_RADIUS_DEG <= EARTH_UMBRA_DEG:
                    eclipse_type = "TOTAL\u0102"
                    magnitude = 1.0 + (EARTH_UMBRA_DEG - sep - MOON_RADIUS_DEG) / (2 * MOON_RADIUS_DEG)
                else:
                    eclipse_type = "par\u021bial\u0103"
                    magnitude = (EARTH_UMBRA_DEG + MOON_RADIUS_DEG - sep) / (2 * MOON_RADIUS_DEG)
        if eclipse_type:
            jd = julian_date_approx(bm['date'])
            alt = moon_alt_from_radec(bm['ra'], bm['dec'], jd, JERUSALEM_LAT, JERUSALEM_LON)
            eclipses.append({
                'date': bm['date'], 'type': eclipse_type, 'magnitude': magnitude,
                'moon_lat': bm['ecl_lat'], 'alt_jerusalem': alt,
                'visible_jerusalem': alt > 0, 'separation': sep,
            })
            send_event("found", {"date": bm['date'], "type": eclipse_type, "mag": round(magnitude, 3)})

    send_event("progress", {"msg": f"Complet: {len(eclipses)} eclips\u0103(e) g\u0103site."})
    return eclipses


# ---------------------------------------------------------------------------
# AFIȘARE CLI
# ---------------------------------------------------------------------------
SEP = "=" * 80

def display_cli(eclipses, y1, y2):
    print(f"\n{SEP}")
    print(f"  LUNA DE SÂNGE — Eclipse lunare {y1}–{y2} d.Hr.")
    print(f"  Sursa: NASA/JPL Horizons (DE441) — Vizibilitate din Ierusalim")
    print(SEP)

    if not eclipses:
        print("\n  Nicio eclipsă lunară găsită.\n")
        return

    print(f"\n  {'Data (UT)':<26} {'Tip':<12} {'Magnit.':>7} {'Lat.Luna':>9} {'Alt.Ier.':>8} {'Viz.':>5}")
    print(f"  {'-'*26} {'-'*10} {'-'*12} {'-'*7} {'-'*9} {'-'*8} {'-'*5}")

    for e in eclipses:
        viz = "DA" if e['visible_jerusalem'] else ("răsare eclipsată" if e['alt_jerusalem'] > -45 and e['magnitude'] > 0.3 else "nu")
        note = ""
        if e['type'] == "TOTALĂ":
            note = " ◄ LUNA DE SÂNGE"
        elif e['type'] == "parțială" and e['magnitude'] > 0.4:
            note = " ◄ roșiatică"
        # Ora locală Ierusalim ≈ UT + 2h21m (longitudine 35.21°)
        local_h = ''
        try:
            parts = e['date'].split()
            hm = parts[-1].split(':')
            h = int(hm[0]) + 2
            m = int(hm[1]) + 21
            if m >= 60: h += 1; m -= 60
            if h >= 24: h -= 24
            local_h = f'{h:02d}:{m:02d}'
        except: local_h = '??:??'
        print(f"  {e['date']:<26} {local_h:>10} {e['type']:<12} {e['magnitude']:7.3f} "
              f"{e['moon_lat']:9.2f}° {e['alt_jerusalem']:8.1f}° {viz}{note}")

    tot = len(eclipses)
    totl = len([e for e in eclipses if e['type'] == "TOTALĂ"])
    part = len([e for e in eclipses if e['type'] == "parțială"])
    vis = len([e for e in eclipses if e['visible_jerusalem']])
    print(f"\n  Rezumat: {tot} eclipsă(e) — {totl} totală(e), {part} parțială(e), {vis} vizibilă(e) din Ierusalim.")

    # Evidențiază 33 Apr
    for e in eclipses:
        if "0033-Apr" in e['date'] or "33-Apr" in e['date']:
            print(f"\n  ★ ECLIPSA RĂSTIGNIRII: {e['date']}")
            print(f"    Tip: {e['type']}, magnitudine umbrală: {e['magnitude']:.3f}")
            print(f"    NASA GSFC (Espenak): magnitudine 0.5764, max 14:47:51 UT")
            print(f"    Vizibilă din Ierusalim: luna a răsărit deja eclipsată (~18:20 local)")
            print(f"    → Fapte 2:20: «soarele se va schimba în întuneric și luna în sânge»")
            print(f"    → Humphreys & Waddington (1983) Nature 306, 743–746")

    print(f"\n{SEP}")
    print(f"  Sursa: NASA/JPL Horizons — ssd.jpl.nasa.gov/horizons/")
    print(f"  Referință: NASA GSFC Eclipse catalog — eclipse.gsfc.nasa.gov")
    print(f"{SEP}\n")


# ---------------------------------------------------------------------------
# WEB DASHBOARD
# ---------------------------------------------------------------------------
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse as url_parse, parse_qs as qs_parse

DASHBOARD = r"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Luna de Sange — NASA JPL Horizons</title>
<style>
:root{--bg:#0a0610;--p:#120e1a;--pb:#1e1830;--t:#c0b8d4;--dim:#6a5a80;--br:#e8e0f5;--ac:#c75d5d;--ac2:#d4a84b;--m:monospace;--r:6px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--m);background:var(--bg);color:var(--t);min-height:100vh;line-height:1.55}
.w{max-width:1050px;margin:0 auto;padding:28px 16px 40px}
h1{text-align:center;font-size:1.8rem;color:var(--ac);margin-bottom:4px}
.sub{text-align:center;font-size:.72rem;color:var(--dim);margin-bottom:18px}
.form-row{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-bottom:14px;align-items:end}
.form-row label{font-size:.65rem;color:var(--dim);text-transform:uppercase;display:block;margin-bottom:3px}
.form-row input{background:var(--p);border:1px solid var(--pb);color:var(--br);padding:8px 12px;border-radius:var(--r);font-family:var(--m);font-size:.85rem;width:100px}
.form-row input:focus{outline:none;border-color:var(--ac)}
.form-row button{background:var(--ac);color:#fff;border:none;padding:8px 20px;border-radius:var(--r);font-family:var(--m);font-weight:700;cursor:pointer}
.form-row button:hover{background:#d06060}
.form-row button:disabled{opacity:.5;cursor:wait}
.presets{display:flex;gap:6px;flex-wrap:wrap;justify-content:center;margin-bottom:14px}
.presets button{background:var(--pb);color:var(--t);border:1px solid #2a2040;padding:6px 12px;border-radius:var(--r);font-family:var(--m);font-size:.72rem;cursor:pointer}
.presets button:hover{border-color:var(--ac);color:var(--ac)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:14px}
.stat{background:var(--p);border:1px solid var(--pb);border-radius:var(--r);padding:12px 14px}
.stat .label{font-size:.6rem;color:var(--dim);text-transform:uppercase}
.stat .val{font-size:1.2rem;color:var(--ac);font-weight:700;margin-top:2px}
.stat .detail{font-size:.65rem;color:var(--dim);margin-top:2px}
.scroll{overflow:auto;max-height:50vh;border:1px solid var(--pb);border-radius:var(--r);margin-bottom:14px}
table{border-collapse:collapse;width:100%;font-size:.72rem}
thead th{padding:7px 5px;text-align:left;font-size:.6rem;font-weight:600;color:var(--ac2);text-transform:uppercase;background:var(--p);border-bottom:1px solid var(--pb);position:sticky;top:0;white-space:nowrap}
tbody td{padding:5px 6px;border-bottom:1px solid #15101e;white-space:nowrap}
tbody tr:nth-child(even){background:rgba(255,255,255,.01)}
tbody tr:hover{background:rgba(199,93,93,.08)}
tr.blood td{color:var(--ac);font-weight:700}
tr.partial td{color:var(--ac2)}
.quote{border-left:3px solid var(--ac);padding:10px 14px;margin:16px 0;font-style:italic;color:var(--dim);font-size:.78rem;line-height:1.7}
.quote .src{font-style:normal;color:var(--ac);font-size:.65rem;margin-top:6px}
.highlight{margin:16px 0;padding:14px 16px;border-left:3px solid var(--ac);background:rgba(199,93,93,.06);border-radius:0 6px 6px 0;font-size:.78rem}
#status{text-align:center;color:var(--dim);font-size:.8rem;margin:20px 0}
.ft{text-align:center;margin-top:20px;font-size:.55rem;color:#2a1e38}
</style>
</head>
<body>
<div class="w">
<h1>&#x1F311; Luna de S&#xE2;nge</h1>
<div class="sub">Eclipse lunare via NASA/JPL Horizons (DE441) &#x2014; vizibilitate din Ierusalim</div>

<div class="presets">
  <button onclick="go(30,36)">30&#x2013;36 d.Hr. (R&#x103;stignirea)</button>
  <button onclick="go(33,33)">Anul 33 d.Hr.</button>
  <button onclick="go(2025,2025)">2025</button>
  <button onclick="go(2025,2030)">2025&#x2013;2030</button>
  <button onclick="go(60,70)">60&#x2013;70 d.Hr.</button>
</div>

<div class="form-row">
  <div><label>An start</label><input id="y1" value="33"></div>
  <div><label>An stop</label><input id="y2" value="33"></div>
  <div><button id="btn" onclick="query()">Interogare NASA JPL</button></div>
</div>

<div class="quote">
  &#xAB;Soarele se va schimba &#xEE;n &#xEE;ntuneric &#x219;i luna &#xEE;n s&#xE2;nge,
  &#xEE;nainte de a veni ziua Domnului cea mare &#x219;i str&#x103;lucit&#x103;.&#xBB;
  <div class="src">&#x2014; Fapte 2:20 / Ioil 3:4</div>
</div>

<div id="status"></div>
<div id="stats" class="stats" style="display:none"></div>
<div id="highlight" style="display:none"></div>
<div id="tbl" style="display:none"></div>

<div class="ft">
Sursa: NASA/JPL Horizons DE441 &#x2014; ssd.jpl.nasa.gov/horizons/<br>
Referin&#x21B;&#x103;: Humphreys &amp; Waddington (1983) Nature 306, 743&#x2013;746 &#xB7;
NASA GSFC Eclipse catalog (F. Espenak)
</div>
</div>
<script>
function go(a,b){document.getElementById('y1').value=a;document.getElementById('y2').value=b;query()}

function query(){
  const y1=document.getElementById('y1').value.trim();
  const y2=document.getElementById('y2').value.trim();
  const btn=document.getElementById('btn');
  btn.disabled=true;btn.textContent='Se interogheaz\u0103 NASA\u2026';
  document.getElementById('status').innerHTML='<span style="color:var(--ac2)">Se conecteaz\u0103 la JPL Horizons\u2026 (Faza 1: scanare, Faza 2: precizie)</span>';
  document.getElementById('stats').style.display='none';
  document.getElementById('tbl').style.display='none';
  document.getElementById('highlight').style.display='none';

  const es=new EventSource('/calc?y1='+y1+'&y2='+y2);
  es.addEventListener('progress',function(e){
    const d=JSON.parse(e.data);
    document.getElementById('status').innerHTML='<span style="color:var(--ac2)">'+d.msg+'</span>';
  });
  es.addEventListener('found',function(e){
    const d=JSON.parse(e.data);
    const st=document.getElementById('status');
    st.innerHTML+='<br><span style="color:var(--ac)">★ '+d.date+' — '+d.type+' (mag '+d.mag+')</span>';
  });
  es.addEventListener('result',function(e){
    es.close();
    btn.disabled=false;btn.textContent='Interogare NASA JPL';
    document.getElementById('status').textContent='';
    const data=JSON.parse(e.data);
    render(data);
  });
  es.addEventListener('error',function(e){
    es.close();
    btn.disabled=false;btn.textContent='Interogare NASA JPL';
    try{const d=JSON.parse(e.data);document.getElementById('status').innerHTML='<span style="color:var(--ac)">'+d.error+'</span>';}
    catch(x){document.getElementById('status').innerHTML='<span style="color:var(--ac)">Conexiune pierdută</span>';}
  });
}

function render(data){
  const e=data.eclipses;
  if(!e.length){document.getElementById('status').textContent='Nicio eclips\u0103 lunar\u0103 g\u0103sit\u0103.';return}
  const tot=e.length,
    totl=e.filter(x=>x.type==='TOTAL\u0102').length,
    part=e.filter(x=>x.type==='par\u021Bial\u0103').length,
    vis=e.filter(x=>x.visible).length;

  document.getElementById('stats').style.display='grid';
  document.getElementById('stats').innerHTML=
    '<div class="stat"><div class="label">Eclipse g\u0103site</div><div class="val">'+tot+'</div></div>'+
    '<div class="stat"><div class="label">Totale (luna de s\u00E2nge)</div><div class="val" style="color:#c75d5d">'+totl+'</div></div>'+
    '<div class="stat"><div class="label">Par\u021Biale</div><div class="val" style="color:#d4a84b">'+part+'</div></div>'+
    '<div class="stat"><div class="label">Vizibile Ierusalim</div><div class="val">'+vis+'</div></div>';

  let h='<div class="scroll"><table><thead><tr><th>Data (UT)</th><th>Ora Ierusalim</th><th>Tip</th><th>Magnit. umbral\u0103</th><th>Lat. Luna</th><th>Alt. Ierusalim</th><th>Vizibil\u0103</th></tr></thead><tbody>';
  e.forEach(r=>{
    let cls='';
    if(r.type==='TOTAL\u0102')cls=' class="blood"';
    else if(r.type==='par\u021Bial\u0103'&&r.mag>0.4)cls=' class="partial"';
    const note=r.type==='TOTAL\u0102'?' \u25C0 LUNA DE S\u00CENGE':(r.mag>0.4?' \u25C0 ro\u0219iatic\u0103':'');
    h+='<tr'+cls+'><td>'+r.date+'</td><td>'+(r.local_time||'')+'</td><td>'+r.type+'</td><td>'+r.mag.toFixed(3)+'</td><td>'+r.lat.toFixed(2)+'\u00B0</td><td>'+r.alt.toFixed(1)+'\u00B0</td><td>'+(r.viz_label||'nu')+note+'</td></tr>';
  });
  h+='</tbody></table></div>';
  document.getElementById('tbl').style.display='block';
  document.getElementById('tbl').innerHTML=h;

  // Highlight eclipsa din 33 Apr
  const apr33=e.find(x=>x.date.includes('0033-Apr'));
  if(apr33){
    document.getElementById('highlight').style.display='block';
    document.getElementById('highlight').innerHTML=
      '<div class="highlight">'+
      '<b style="color:var(--br)">\u2605 Eclipsa R\u0103stignirii: '+apr33.date+'</b><br><br>'+
      'Tip: <b>'+apr33.type+'</b>, magnitudine umbral\u0103 calculat\u0103: <b>'+apr33.mag.toFixed(3)+'</b><br>'+
      'NASA GSFC (F. Espenak): magnitudine <b>0.5764</b>, max <b>14:47:51 UT</b> (<a href="https://eclipse.gsfc.nasa.gov/LEhistory/LEplot/LE0033Apr03P.pdf" target="_blank" style="color:var(--ac2)">PDF NASA</a>)<br>'+'Humphreys &amp; Waddington (1983) <a href="https://www.nature.com/articles/306743a0" target="_blank" style="color:var(--ac2)"><i>Nature</i> 306, 743–746</a><br>'+
      'Luna a r\u0103s\u0103rit deasupra Ierusalimului deja eclipsat\u0103, ro\u0219iatic\u0103 (~18:20 local)<br>'+
      '<i>\u00ABSoarele se va schimba \u00EEn \u00EEntuneric \u0219i luna \u00EEn s\u00E2nge\u00BB (Fapte 2:20)</i>'+
      '</div>';
  }
}
</script>
</body>
</html>"""


class BloodMoonHorizonsHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): print(f"  {args[0]}")
    def do_GET(self):
        parsed = url_parse(self.path)
        if parsed.path in ('/', '/index.html'):
            self.send_response(200)
            self.send_header("Content-Type", "text/html;charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD.encode())
        elif parsed.path == '/calc':
            qs = qs_parse(parsed.query)
            y1 = int(qs.get('y1', ['33'])[0])
            y2 = int(qs.get('y2', ['33'])[0])
            # SSE — trimitem progresul pas cu pas
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            def send_event(evt, data_dict):
                msg = f"event: {evt}\ndata: {json.dumps(data_dict)}\n\n"
                try: self.wfile.write(msg.encode()); self.wfile.flush()
                except: pass
            try:
                ecl = find_eclipses_horizons_sse(y1, y2, send_event)
                send_event("result", {'eclipses': [{
                    'date': e['date'], 'type': e['type'],
                    'mag': round(e['magnitude'], 4),
                    'lat': round(e['moon_lat'], 2),
                    'alt': round(e['alt_jerusalem'], 1),
                    'visible': e['visible_jerusalem'],
                    'viz_label': 'DA' if e['visible_jerusalem'] else ('răsare eclipsată' if e['alt_jerusalem'] > -45 and e['magnitude'] > 0.3 else 'nu'),
                    'local_time': jerusalem_local_time(e['date']),
                } for e in ecl]})
            except Exception as ex:
                send_event("error", {'error': str(ex)})
        else:
            self.send_response(404); self.end_headers()


def serve_dashboard(port=8789):
    S = "=" * 70
    print(f"\n{S}")
    print(f"  LUNA DE SÂNGE — NASA JPL Horizons Dashboard")
    print(f"{S}")
    print(f"  http://localhost:{port}")
    print(f"  Ctrl+C pentru oprire.\n{'-'*70}\n")
    srv = HTTPServer(("127.0.0.1", port), BloodMoonHorizonsHandler)
    try: webbrowser.open(f"http://localhost:{port}")
    except: pass
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\n  Oprit."); srv.server_close()


# ---------------------------------------------------------------------------
# PRINCIPAL
# ---------------------------------------------------------------------------

def main():
    if "--serve" in sys.argv:
        idx = sys.argv.index("--serve")
        port = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 else 8789
        serve_dashboard(port)
        return

    args = [a for a in sys.argv[1:] if not a.startswith("-")]

    if len(args) >= 2:
        y1, y2 = int(args[0]), int(args[1])
    elif len(args) == 1:
        y1 = int(args[0])
        y2 = y1
    else:
        from datetime import datetime
        y1 = y2 = datetime.utcnow().year

    eclipses = find_eclipses_horizons(y1, y2)
    display_cli(eclipses, y1, y2)


if __name__ == "__main__":
    main()
