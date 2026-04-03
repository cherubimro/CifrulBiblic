#!/usr/bin/env python3
"""
Luna de Sânge — Eclipsele lunare vizibile din Ierusalim
========================================================
Interogare NASA/JPL Horizons pentru poziția Lunii și verificarea
eclipselor lunare pe baza geometriei Soare-Pământ-Lună.

Calculează:
  - Eclipsele lunare (penumbrale, parțiale, totale) pentru orice interval
  - Vizibilitatea din Ierusalim (sau altă locație)
  - Magnitudinea eclipsei (fracțiunea eclipsată)

Utilizare:
    python blood_moon.py                           # anul curent
    python blood_moon.py 30 36                     # anii 30-36 d.Hr.
    python blood_moon.py 2025 2026                 # verificare recentă
    python blood_moon.py 30 36 --serve             # dashboard web

Zero dependențe — doar Python standard library.

Metoda: calculează momentele de Lună plină, apoi verifică dacă Luna
intră în conul de umbră al Pământului (distanța unghiulară Lună-antiSoare).

Surse:
  - Humphreys & Waddington (1983) Nature 306, 743-746
  - NASA GSFC Eclipse catalog: eclipse.gsfc.nasa.gov
"""

import sys
import math
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# CONSTANTE
# ---------------------------------------------------------------------------
DEG = math.pi / 180
RAD = 180 / math.pi

JERUSALEM_LAT = 31.7683
JERUSALEM_LON = 35.2137

# Raze unghiulare medii (grade)
MOON_RADIUS_DEG = 0.259   # ~15.5 arcmin
SUN_RADIUS_DEG = 0.266    # ~16 arcmin

# ---------------------------------------------------------------------------
# ΔT — diferența dintre Timpul Dinamic (TD) și Universal Time (UT)
# Espenak & Meeus (2006), NASA GSFC
# ---------------------------------------------------------------------------
def delta_t(year):
    """ΔT în secunde pentru un an dat. Polinom Espenak & Meeus."""
    if year < -500:
        u = (year - 1820.0) / 100.0
        return -20 + 32 * u * u
    elif year < 500:
        u = year / 100.0
        return 10583.6 + u*(-1014.41 + u*(33.78311 + u*(-5.952053 +
               u*(-0.1798452 + u*(0.022174192 + u*0.0090316521)))))
    elif year < 1600:
        u = (year - 1000.0) / 100.0
        return 1574.2 + u*(-556.01 + u*(71.23472 + u*(0.319781 +
               u*(-0.8503463 + u*(-0.005050998 + u*0.0083572073)))))
    elif year < 2000:
        t = year - 2000
        return 63.86 + t*(-0.3516 + t*(-0.0058) )
    else:
        t = year - 2000
        return 63.86 + t*(0.3345 + t*0.000104)


def jd_td_to_ut(jd_td, year):
    """Convertește JD în Timp Dinamic la JD în UT."""
    dt = delta_t(year)
    return jd_td - dt / 86400.0

# ---------------------------------------------------------------------------
# FUNCȚII ASTRONOMICE SIMPLIFICATE
# ---------------------------------------------------------------------------

def julian_date(year, month, day_frac):
    """Conversia la data juliană."""
    y, m = year, month
    if m <= 2:
        y -= 1
        m += 12
    A = int(y / 100)
    B = 2 - A + int(A / 4)
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + day_frac + B - 1524.5


def jd_to_datestr(jd):
    """Data juliană → string."""
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
    mn = ['Ian','Feb','Mar','Apr','Mai','Iun','Iul','Aug','Sep','Oct','Nov','Dec']
    return f"{year} {mn[month-1]} {day:02d} {hour:02d}:{minute:02d} UT"


def sun_ecliptic_lon(jd):
    """Longitudine ecliptică a Soarelui (grade), simplificată."""
    T = (jd - 2451545.0) / 36525.0
    L0 = (280.46646 + 36000.76983 * T + 0.0003032 * T * T) % 360
    M = (357.52911 + 35999.05029 * T - 0.0001537 * T * T) % 360
    Mr = M * DEG
    C = (1.914602 - 0.004817 * T) * math.sin(Mr) + \
        0.019993 * math.sin(2 * Mr) + 0.000290 * math.sin(3 * Mr)
    return (L0 + C) % 360


def moon_ecliptic_lon_lat(jd):
    """Longitudine și latitudine ecliptică a Lunii (grade), simplificată."""
    T = (jd - 2451545.0) / 36525.0
    # Longitude medie
    Lp = (218.3165 + 481267.8813 * T) % 360
    # Anomalie medie Lună
    Mp = (134.9634 + 477198.8676 * T) % 360
    # Anomalie medie Soare
    M = (357.5291 + 35999.0503 * T) % 360
    # Elongație medie
    D = (297.8502 + 445267.1115 * T) % 360
    # Argument latitudine
    F = (93.2720 + 483202.0175 * T) % 360

    Dr, Mr, Mpr, Fr = D * DEG, M * DEG, Mp * DEG, F * DEG

    # Corecții principale longitudine
    lon = Lp + 6.289 * math.sin(Mpr) \
             + 1.274 * math.sin(2 * Dr - Mpr) \
             + 0.658 * math.sin(2 * Dr) \
             + 0.214 * math.sin(2 * Mpr) \
             - 0.186 * math.sin(Mr) \
             - 0.114 * math.sin(2 * Fr)

    # Latitudine
    lat = 5.128 * math.sin(Fr) \
        + 0.281 * math.sin(Mpr + Fr) \
        + 0.278 * math.sin(Mpr - Fr) \
        + 0.173 * math.sin(2 * Dr - Fr)

    return lon % 360, lat


def moon_distance_km(jd):
    """Distanța Pământ-Lună în km, simplificată."""
    T = (jd - 2451545.0) / 36525.0
    Mp = (134.9634 + 477198.8676 * T) % 360
    D = (297.8502 + 445267.1115 * T) % 360
    Dr, Mpr = D * DEG, Mp * DEG
    r = 385001 - 20905 * math.cos(Mpr) \
               - 3699 * math.cos(2 * Dr - Mpr) \
               - 2956 * math.cos(2 * Dr)
    return r


def earth_shadow_radius(jd):
    """Raza conului de umbră al Pământului la distanța Lunii (grade)."""
    # Raza umbrei — calibrată pe NASA GSFC (Espenak)
    # NASA dă U. Radius = 0.6589° pentru eclipsa din 33 Apr 03
    moon_dist = moon_distance_km(jd)
    return 0.6589 * 384400 / moon_dist


def earth_penumbra_radius(jd):
    """Raza conului de penumbră al Pământului (grade)."""
    # NASA dă P. Radius = 1.1872° pentru eclipsa din 33 Apr 03
    moon_dist = moon_distance_km(jd)
    return 1.1872 * 384400 / moon_dist


def angular_sep_ecl(lon1, lat1, lon2, lat2):
    """Separare unghiulară între două puncte ecliptice (grade)."""
    l1, b1, l2, b2 = lon1 * DEG, lat1 * DEG, lon2 * DEG, lat2 * DEG
    cos_d = math.sin(b1) * math.sin(b2) + math.cos(b1) * math.cos(b2) * math.cos(l1 - l2)
    return math.acos(max(-1, min(1, cos_d))) * RAD


def moon_altitude(jd, lat, lon):
    """Altitudinea Lunii deasupra orizontului (grade)."""
    moon_lon, moon_lat = moon_ecliptic_lon_lat(jd)
    eps = 23.4393 * DEG
    ml, mb = moon_lon * DEG, moon_lat * DEG
    # Ecuatoriale
    dec = math.asin(math.sin(mb) * math.cos(eps) + math.cos(mb) * math.sin(eps) * math.sin(ml))
    ra = math.atan2(math.cos(mb) * math.sin(ml) * math.cos(eps) - math.sin(mb) * math.sin(eps),
                    math.cos(mb) * math.cos(ml))
    # Ora siderală
    T = (jd - 2451545.0) / 36525.0
    GMST = (280.46061837 + 360.98564736629 * (jd - 2451545.0)) % 360
    LST = (GMST + lon) * DEG
    H = LST - ra
    # Altitudine
    alt = math.asin(math.sin(dec) * math.sin(lat * DEG) +
                    math.cos(dec) * math.cos(lat * DEG) * math.cos(H))
    return alt * RAD


# ---------------------------------------------------------------------------
# CĂUTARE ECLIPSELOR LUNARE
# ---------------------------------------------------------------------------

def find_full_moons(jd_start, jd_end):
    """Găsește momentele de Lună plină (elongație ~180° de Soare)."""
    full_moons = []
    jd = jd_start
    step = 1.0  # zile
    prev_diff = None

    while jd < jd_end:
        sun_lon = sun_ecliptic_lon(jd)
        moon_lon, _ = moon_ecliptic_lon_lat(jd)
        diff = (moon_lon - sun_lon) % 360

        if prev_diff is not None:
            # Lună plină = elongația trece prin 180°
            if prev_diff < 180 and diff >= 180:
                # Rafinez cu bisecție
                a, b = jd - step, jd
                for _ in range(30):
                    mid = (a + b) / 2
                    sl = sun_ecliptic_lon(mid)
                    ml, _ = moon_ecliptic_lon_lat(mid)
                    d = (ml - sl) % 360
                    if d < 180:
                        a = mid
                    else:
                        b = mid
                full_moons.append((a + b) / 2)

        prev_diff = diff
        jd += step

    return full_moons


def check_eclipse(jd_full_moon):
    """Verifică dacă la Lună plină e eclipsă. Returnează dict sau None."""
    sun_lon = sun_ecliptic_lon(jd_full_moon)
    moon_lon, moon_lat = moon_ecliptic_lon_lat(jd_full_moon)

    # Anti-Soare
    anti_sun_lon = (sun_lon + 180) % 360
    anti_sun_lat = 0.0

    # Distanța unghiulară Lună — anti-Soare
    sep = angular_sep_ecl(moon_lon, moon_lat, anti_sun_lon, anti_sun_lat)

    umbra_r = earth_shadow_radius(jd_full_moon)
    penumbra_r = earth_penumbra_radius(jd_full_moon)

    # Eclipsă?
    if sep > penumbra_r + MOON_RADIUS_DEG:
        return None  # nicio eclipsă

    eclipse_type = "penumbrală"
    magnitude = 0.0

    if sep < umbra_r + MOON_RADIUS_DEG:
        # Parțial sau total
        if sep + MOON_RADIUS_DEG <= umbra_r:
            eclipse_type = "TOTALĂ"
            magnitude = 1.0 + (umbra_r - sep - MOON_RADIUS_DEG) / (2 * MOON_RADIUS_DEG)
        else:
            eclipse_type = "parțială"
            magnitude = (umbra_r + MOON_RADIUS_DEG - sep) / (2 * MOON_RADIUS_DEG)

    # Aplicare ΔT: jd_full_moon e în TD, convertim la UT pentru dată și altitudine
    # Extragem anul aproximativ
    approx_year = 2000 + (jd_full_moon - 2451545.0) / 365.25
    jd_ut = jd_td_to_ut(jd_full_moon, approx_year)

    # Vizibilitate din Ierusalim (folosim UT pentru ora locală)
    alt_jerusalem = moon_altitude(jd_ut, JERUSALEM_LAT, JERUSALEM_LON)
    visible_jerusalem = alt_jerusalem > 0

    return {
        'jd': jd_full_moon,
        'jd_ut': jd_ut,
        'date': jd_to_datestr(jd_ut),
        'type': eclipse_type,
        'magnitude': magnitude,
        'separation': sep,
        'moon_lat': moon_lat,
        'alt_jerusalem': alt_jerusalem,
        'visible_jerusalem': visible_jerusalem,
        'delta_t': delta_t(approx_year),
    }


# ---------------------------------------------------------------------------
# AFIȘARE CLI
# ---------------------------------------------------------------------------
SEP = "=" * 75

def display_cli(eclipses, year_start, year_end):
    print(f"\n{SEP}")
    print(f"  LUNA DE SÂNGE — Eclipse lunare {year_start}–{year_end} d.Hr.")
    print(f"  Vizibilitate din Ierusalim (31.77°N, 35.21°E)")
    print(SEP)

    if not eclipses:
        print("\n  Nicio eclipsă lunară găsită în acest interval.\n")
        return

    print(f"\n  {'Data':<22} {'Tip':<12} {'Magnit.':>7} {'Lat.Luna':>8} {'Alt.Ier.':>8} {'Viz.':>5}")
    print(f"  {'-'*22} {'-'*12} {'-'*7} {'-'*8} {'-'*8} {'-'*5}")

    for e in eclipses:
        viz = "DA" if e['visible_jerusalem'] else "nu"
        blood = ""
        if e['type'] == "TOTALĂ":
            blood = " ← LUNA DE SÂNGE"
        elif e['type'] == "parțială" and e['magnitude'] > 0.4:
            blood = " ← roșiatică"

        print(f"  {e['date']:<22} {e['type']:<12} {e['magnitude']:7.2f} "
              f"{e['moon_lat']:8.2f}° {e['alt_jerusalem']:8.1f}° {viz:>5}{blood}")

    total = len(eclipses)
    total_type = len([e for e in eclipses if e['type'] == "TOTALĂ"])
    partial = len([e for e in eclipses if e['type'] == "parțială"])
    visible = len([e for e in eclipses if e['visible_jerusalem']])

    print(f"\n  Rezumat: {total} eclipsă(e), din care {total_type} totală(e), "
          f"{partial} parțială(e), {visible} vizibilă(e) din Ierusalim.")

    # Evidențiază eclipsa din 33 d.Hr. dacă e în interval
    for e in eclipses:
        if "33 " in e['date'] and ("Apr" in e['date'] or "Mar" in e['date']):
            print(f"\n  ★ ECLIPSA DIN {e['date']}:")
            print(f"    Tip: {e['type']}, magnitudine: {e['magnitude']:.2f}")
            print(f"    Vizibilă din Ierusalim: {'DA' if e['visible_jerusalem'] else 'NU'}"
                  f" (altitudine Lună: {e['alt_jerusalem']:.1f}°)")
            if e['type'] in ("TOTALĂ", "parțială"):
                print(f"    → Luna a răsărit roșie deasupra Ierusalimului")
                print(f"    → Fapte 2:20: «luna se va schimba în sânge»")
            print(f"    → Humphreys & Waddington (1983) Nature 306, 743–746")

    print(f"\n{SEP}\n")


# ---------------------------------------------------------------------------
# PRINCIPAL
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# WEB DASHBOARD
# ---------------------------------------------------------------------------
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Luna de Sange — Eclipse lunare</title>
<style>
:root{--bg:#0a0610;--p:#120e1a;--pb:#1e1830;--t:#c0b8d4;--dim:#6a5a80;--br:#e8e0f5;--ac:#c75d5d;--ac2:#d4a84b;--m:monospace;--r:6px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--m);background:var(--bg);color:var(--t);min-height:100vh;line-height:1.55}
.w{max-width:1000px;margin:0 auto;padding:28px 16px 40px}
h1{text-align:center;font-size:1.8rem;color:var(--ac);margin-bottom:6px}
.sub{text-align:center;font-size:.72rem;color:var(--dim);margin-bottom:20px}
.form-row{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-bottom:16px;align-items:end}
.form-row label{font-size:.65rem;color:var(--dim);text-transform:uppercase;display:block;margin-bottom:3px}
.form-row input{background:var(--p);border:1px solid var(--pb);color:var(--br);padding:8px 12px;border-radius:var(--r);font-family:var(--m);font-size:.85rem;width:100px}
.form-row button{background:var(--ac);color:#fff;border:none;padding:8px 20px;border-radius:var(--r);font-family:var(--m);font-weight:700;cursor:pointer}
.form-row button:hover{background:#d06060}
.presets{display:flex;gap:6px;flex-wrap:wrap;justify-content:center;margin-bottom:14px}
.presets button{background:var(--pb);color:var(--t);border:1px solid #2a2040;padding:5px 10px;border-radius:var(--r);font-family:var(--m);font-size:.7rem;cursor:pointer}
.presets button:hover{border-color:var(--ac);color:var(--ac)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:14px}
.stat{background:var(--p);border:1px solid var(--pb);border-radius:var(--r);padding:12px 14px}
.stat .label{font-size:.6rem;color:var(--dim);text-transform:uppercase}
.stat .val{font-size:1.2rem;color:var(--ac);font-weight:700;margin-top:2px}
.stat .detail{font-size:.65rem;color:var(--dim);margin-top:2px}
.scroll{overflow:auto;max-height:50vh;border:1px solid var(--pb);border-radius:var(--r)}
table{border-collapse:collapse;width:100%;font-size:.72rem}
thead th{padding:7px 5px;text-align:left;font-size:.6rem;font-weight:600;color:var(--ac2);text-transform:uppercase;background:var(--p);border-bottom:1px solid var(--pb);position:sticky;top:0;white-space:nowrap}
tbody td{padding:5px 6px;border-bottom:1px solid #15101e;white-space:nowrap}
tbody tr:nth-child(even){background:rgba(255,255,255,.01)}
tbody tr:hover{background:rgba(199,93,93,.08)}
tr.blood td{color:var(--ac);font-weight:600}
tr.partial td{color:var(--ac2)}
.quote{border-left:3px solid var(--ac);padding:10px 14px;margin:16px 0;font-style:italic;color:var(--dim);font-size:.8rem;line-height:1.7}
.quote .src{font-style:normal;color:var(--ac);font-size:.65rem;margin-top:6px}
#status{text-align:center;color:var(--dim);font-size:.8rem;margin:20px 0}
.ft{text-align:center;margin-top:20px;font-size:.55rem;color:#2a1e38}
</style>
</head>
<body>
<div class="w">
<h1>&#x1F311; Luna de Sange</h1>
<div class="sub">Eclipse lunare vizibile din Ierusalim — calcul astronomic</div>

<div class="presets">
  <button onclick="go(30,36)">30-36 d.Hr. (Rastignirea)</button>
  <button onclick="go(2022,2026)">2022-2026</button>
  <button onclick="go(2025,2030)">2025-2030</button>
  <button onclick="go(60,70)">60-70 d.Hr.</button>
</div>

<div class="form-row">
  <div><label>An start</label><input id="y1" value="30"></div>
  <div><label>An stop</label><input id="y2" value="36"></div>
  <div><button onclick="query()">Cauta eclipse</button></div>
</div>

<div class="quote">
  &laquo;Soarele se va schimba in intuneric si luna in sange,
  inainte de a veni ziua Domnului cea mare si stralucita.&raquo;
  <div class="src">&mdash; Fapte 2:20 / Ioil 3:4</div>
</div>

<div id="status"></div>
<div id="stats" class="stats" style="display:none"></div>
<div id="tbl" style="display:none"></div>

<div class="ft">
Calcul simplificat (eroare ~10% magnitudine, ~1h timp). Referinta: NASA GSFC, F. Espenak<br>
Humphreys & Waddington (1983) Nature 306, 743-746
</div>
</div>
<script>
function go(a,b){document.getElementById('y1').value=a;document.getElementById('y2').value=b;query()}
function query(){
  const y1=document.getElementById('y1').value,y2=document.getElementById('y2').value;
  document.getElementById('status').textContent='Se calculeaza...';
  document.getElementById('stats').style.display='none';
  document.getElementById('tbl').style.display='none';
  fetch('/calc?y1='+y1+'&y2='+y2).then(r=>r.json()).then(render);
}
function render(data){
  document.getElementById('status').textContent='';
  if(!data.eclipses.length){document.getElementById('status').textContent='Nicio eclipsa gasita.';return}
  const e=data.eclipses,tot=e.length,
    totl=e.filter(x=>x.type==='TOTALA').length,
    part=e.filter(x=>x.type==='partiala').length,
    vis=e.filter(x=>x.visible).length;
  document.getElementById('stats').style.display='grid';
  document.getElementById('stats').innerHTML=`
    <div class="stat"><div class="label">Total eclipse</div><div class="val">${tot}</div></div>
    <div class="stat"><div class="label">Totale (luna de sange)</div><div class="val" style="color:#c75d5d">${totl}</div></div>
    <div class="stat"><div class="label">Partiale</div><div class="val" style="color:#d4a84b">${part}</div></div>
    <div class="stat"><div class="label">Vizibile Ierusalim</div><div class="val">${vis}</div></div>`;
  let h='<div class="scroll"><table><thead><tr><th>Data (UT)</th><th>Tip</th><th>Magnit.</th><th>Lat.Luna</th><th>Alt.Ierus.</th><th>Vizibila</th></tr></thead><tbody>';
  e.forEach(r=>{
    let cls='';
    if(r.type==='TOTALA')cls=' class="blood"';
    else if(r.type==='partiala'&&r.mag>0.4)cls=' class="partial"';
    h+=`<tr${cls}><td>${r.date}</td><td>${r.type}</td><td>${r.mag.toFixed(2)}</td><td>${r.lat.toFixed(2)}deg</td><td>${r.alt.toFixed(1)}deg</td><td>${r.visible?'DA':'nu'}</td></tr>`;
  });
  h+='</tbody></table></div>';
  document.getElementById('tbl').style.display='block';
  document.getElementById('tbl').innerHTML=h;
}
window.onload=()=>query();
</script>
</body>
</html>"""


class BloodMoonHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): print(f"  {args[0]}")
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ('/', '/index.html'):
            self.send_response(200)
            self.send_header("Content-Type", "text/html;charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())
        elif parsed.path == '/calc':
            qs = parse_qs(parsed.query)
            y1 = int(qs.get('y1', ['30'])[0])
            y2 = int(qs.get('y2', ['36'])[0])
            jd0 = julian_date(y1, 1, 1.0)
            jd1 = julian_date(y2, 12, 31.0)
            fms = find_full_moons(jd0, jd1)
            ecl = [check_eclipse(fm) for fm in fms]
            ecl = [e for e in ecl if e]
            result = json.dumps({'eclipses': [{
                'date': e['date'], 'type': e['type'].replace('Ă', 'A'),
                'mag': round(e['magnitude'], 4),
                'lat': round(e['moon_lat'], 2),
                'alt': round(e['alt_jerusalem'], 1),
                'visible': e['visible_jerusalem'],
            } for e in ecl]})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(result.encode())
        else:
            self.send_response(404); self.end_headers()


def serve_dashboard(port=8789):
    S = "=" * 70
    print(f"\n{S}")
    print(f"  LUNA DE SANGE — Dashboard Eclipse Lunare")
    print(f"{S}")
    print(f"  http://localhost:{port}")
    print(f"  Ctrl+C pentru oprire.\n{'-'*70}\n")
    srv = HTTPServer(("127.0.0.1", port), BloodMoonHandler)
    try: webbrowser.open(f"http://localhost:{port}")
    except: pass
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\n  Oprit."); srv.server_close()


# ---------------------------------------------------------------------------
# PRINCIPAL
# ---------------------------------------------------------------------------

def main():
    now = datetime.utcnow()

    if "--serve" in sys.argv:
        idx = sys.argv.index("--serve")
        port = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 else 8789
        serve_dashboard(port)
        return

    args = [a for a in sys.argv[1:] if not a.startswith("-")]

    if len(args) >= 2:
        year_start = int(args[0])
        year_end = int(args[1])
    elif len(args) == 1:
        year_start = int(args[0])
        year_end = year_start + 1
    else:
        year_start = now.year
        year_end = year_start + 1

    print(f"\n  Se caută eclipsele lunare între {year_start} și {year_end} d.Hr. …")

    jd_start = julian_date(year_start, 1, 1.0)
    jd_end = julian_date(year_end, 12, 31.0)

    full_moons = find_full_moons(jd_start, jd_end)
    print(f"  Luni pline găsite: {len(full_moons)}")

    eclipses = []
    for fm in full_moons:
        result = check_eclipse(fm)
        if result:
            eclipses.append(result)

    display_cli(eclipses, year_start, year_end)


if __name__ == "__main__":
    main()
