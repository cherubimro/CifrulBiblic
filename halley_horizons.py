#!/usr/bin/env python3
"""
Comet 1P/Halley - JPL Horizons Ephemeris Query
===============================================
Queries NASA/JPL's Horizons REST API for the current position,
distance, brightness, and orbital data of Comet 1P/Halley.

Zero dependencies - uses only Python standard library.

Usage:
    python halley_horizons.py                          # today -> +30 days, 1-day steps
    python halley_horizons.py 2026-04-01 2026-05-01 7d
    python halley_horizons.py "2061-06-01" "2061-09-01" "1 d"   # next perihelion!
    python halley_horizons.py "1985-11-01" "1986-05-01" "7 d"   # 1986 apparition
    python halley_horizons.py --serve                            # web dashboard on http://localhost:8787

NOTE: JPL Horizons does NOT have ephemeris data for Comet Halley before
      Kepler-era observations (17th century). For the 66 AD or 12 BC
      apparitions, use halley_66ad.py (Yeomans & Kiang 1981 elements).

API docs: https://ssd-api.jpl.nasa.gov/doc/horizons.html
"""

import sys
import ssl
import textwrap
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

API_BASE = "ssd.jpl.nasa.gov/api/horizons.api"

HALLEY_COMMAND = "DES=1P;CAP;NOFRAG"

# Observer-table quantities:
#  1=RA/DEC  9=mag  19=helio range  20=obs range  23=elongation  24=phase  29=constellation
QUANTITIES = "1,9,19,20,23,24,29"

# ---------------------------------------------------------------------------
# URL BUILDER
# ---------------------------------------------------------------------------

def build_url(start, stop, step, scheme="https"):
    cmd = HALLEY_COMMAND.replace("=", "%3D").replace(";", "%3B")
    step_enc = step.replace(" ", "%20")
    pairs = [
        ("format",      "text"),
        ("COMMAND",      f"'{cmd}'"),
        ("OBJ_DATA",     "'YES'"),
        ("MAKE_EPHEM",   "'YES'"),
        ("EPHEM_TYPE",   "'OBSERVER'"),
        ("CENTER",       "'500@399'"),
        ("START_TIME",   f"'{start}'"),
        ("STOP_TIME",    f"'{stop}'"),
        ("STEP_SIZE",    f"'{step_enc}'"),
        ("QUANTITIES",   f"'{QUANTITIES}'"),
        ("CAL_FORMAT",   "'CAL'"),
        ("ANG_FORMAT",   "'DEG'"),
        ("CSV_FORMAT",   "'NO'"),
        ("EXTRA_PREC",   "'YES'"),
    ]
    qs = "&".join(f"{k}={v}" for k, v in pairs)
    return f"{scheme}://{API_BASE}?{qs}"

# ---------------------------------------------------------------------------
# FETCH — tries HTTPS → HTTPS (no verify) → HTTP
# ---------------------------------------------------------------------------

def _try_fetch(url, context=None):
    """Single fetch attempt. Returns body text or raises."""
    req = Request(url, headers={"User-Agent": "halley_horizons.py/1.0"})
    kwargs = {"timeout": 60}
    if context is not None:
        kwargs["context"] = context
    with urlopen(req, **kwargs) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch(start, stop, step):
    """Try multiple transport strategies until one works."""

    strategies = [
        ("HTTPS",            build_url(start, stop, step, "https"),  None),
        ("HTTPS (no verify)", build_url(start, stop, step, "https"),  "_noverify"),
        ("HTTP",             build_url(start, stop, step, "http"),   None),
    ]

    errors = []

    for label, url, flag in strategies:
        ctx = None
        if flag == "_noverify":
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        try:
            text = _try_fetch(url, context=ctx)
            if label != "HTTPS":
                print(f"  Connected via: {label}")
            return text
        except (HTTPError, URLError, OSError) as exc:
            reason = str(getattr(exc, "reason", exc))
            errors.append(f"  {label}: {reason}")

    # All failed
    print("\n  ERROR: All connection methods failed:\n")
    for e in errors:
        print(e)
    print()
    print("  Make sure you have internet access.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# PARSER
# ---------------------------------------------------------------------------

def parse(raw):
    lines = raw.split("\n")

    soe = eoe = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s == "$$SOE":
            soe = i
        elif s == "$$EOE":
            eoe = i

    # Object / orbital data block: between 2nd and 4th star-lines
    obj_lines = []
    stars = 0
    for ln in lines:
        if ln.strip().startswith("*****"):
            stars += 1
            if stars >= 4:
                break
            continue
        if stars >= 2:
            obj_lines.append(ln)

    # Ephemeris header line (just before $$SOE)
    ephem_hdr = ""
    if soe is not None:
        for j in range(soe - 1, max(soe - 5, -1), -1):
            if "Date" in lines[j]:
                ephem_hdr = lines[j]
                break

    # Data rows
    data_rows = []
    if soe is not None and eoe is not None:
        data_rows = [ln for ln in lines[soe + 1 : eoe] if ln.strip()]

    # Target name
    target = ""
    for ln in lines:
        if "Target body name" in ln:
            target = ln.split(":", 1)[1].strip().split("{")[0].strip()
            break

    return {
        "target":    target,
        "obj_block": "\n".join(obj_lines),
        "ephem_hdr": ephem_hdr,
        "rows":      data_rows,
        "raw":       raw,
    }

# ---------------------------------------------------------------------------
# DISPLAY
# ---------------------------------------------------------------------------

SEP  = "=" * 72
THIN = "-" * 72
SEC  = lambda t: f"--- {t} " + "-" * max(0, 66 - len(t))

def display(info, start, stop, step):
    print()
    print(SEP)
    print("  COMET 1P/HALLEY  —  JPL Horizons Ephemeris")
    print(SEP)
    print(f"  Target   : {info['target'] or 'N/A'}")
    print(f"  Range    : {start}  ->  {stop}")
    print(f"  Step     : {step}")
    print(f"  Observer : Geocentric (Earth centre)")
    print(THIN)

    if info["obj_block"].strip():
        print()
        print(SEC("OBJECT & ORBITAL DATA"))
        for ln in info["obj_block"].split("\n"):
            print(f"  {ln}")

    print()
    print(SEC("EPHEMERIS"))
    if info["ephem_hdr"]:
        print(f"  {info['ephem_hdr'].strip()}")
        print()
    if info["rows"]:
        for row in info["rows"]:
            print(f"  {row}")
    else:
        print("  (no data rows returned — check date range)")
    print()

    print(SEC("COLUMN KEY"))
    print(textwrap.dedent("""\
      Date/Time ............ UTC calendar date
      R.A. / DEC ........... Right ascension & declination
      APmag ................ Apparent visual magnitude
      S-brt ................ Surface brightness (mag/arcsec^2)
      r / rdot ............. Heliocentric distance (AU) & velocity (km/s)
      delta / deldot ....... Observer distance (AU) & velocity (km/s)
      S-O-T ................ Sun-Observer-Target elongation angle
      S-T-O ................ Sun-Target-Observer phase angle
      Cnst ................. Constellation

      Negative deldot = target approaching.  Positive = receding.
    """))

    print(SEC("ACCESS METHODS"))
    print(textwrap.dedent("""\
      Web      https://ssd.jpl.nasa.gov/horizons/
      API      https://ssd.jpl.nasa.gov/api/horizons.api
      Telnet   telnet ssd.jpl.nasa.gov 6775  (needs stunnel)
               At prompt type:  NAME=Halley;CAP
      Email    horizons@ssd.jpl.nasa.gov  (subject: BATCH-LONG)
      Python   pip install astroquery
               >>> from astroquery.jplhorizons import Horizons
               >>> obj = Horizons(id='1P', id_type='designation',
               ...     location='500@399',
               ...     epochs={'start':'2026-03-28',
               ...             'stop':'2026-04-28', 'step':'1d'})
               >>> eph = obj.ephemerides(closest_apparition=True)
    """))
    print(SEP)
    print("  Data: NASA/JPL Horizons — Solar System Dynamics Group")
    print(SEP)
    print()

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
<title>☄ 1P/Halley — JPL Horizons</title>
<style>
:root{--bg:#06090f;--p:#0d1219;--pb:#1a2333;--t:#b8c7da;--dim:#506580;--br:#e2ecf5;--ac:#d4a84b;--ac2:#c75d5d;--m:monospace;--r:6px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--m);background:var(--bg);color:var(--t);min-height:100vh;line-height:1.55}
.w{max-width:1100px;margin:0 auto;padding:28px 16px 40px}
h1{text-align:center;font-size:1.6rem;color:var(--br);margin-bottom:6px}h1 span{color:var(--ac)}
.sub{text-align:center;font-size:.72rem;color:var(--dim);margin-bottom:20px}
.form-row{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-bottom:20px;align-items:end}
.form-row label{font-size:.65rem;color:var(--dim);text-transform:uppercase;letter-spacing:.05em;display:block;margin-bottom:3px}
.form-row input{background:var(--p);border:1px solid var(--pb);color:var(--br);padding:8px 12px;border-radius:var(--r);font-family:var(--m);font-size:.85rem;width:160px}
.form-row input:focus{outline:none;border-color:var(--ac)}
.form-row button{background:var(--ac);color:#000;border:none;padding:8px 20px;border-radius:var(--r);font-family:var(--m);font-weight:700;font-size:.85rem;cursor:pointer}
.form-row button:hover{background:#e0b85a}
.form-row button:disabled{opacity:.5;cursor:wait}
.warn{text-align:center;font-size:.7rem;color:var(--ac2);margin:-12px 0 16px;padding:8px;background:rgba(199,93,93,.1);border-radius:var(--r);display:none}
.card{background:var(--p);border:1px solid var(--pb);border-radius:var(--r);padding:14px 16px;margin-bottom:14px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:14px}
.stat{background:var(--p);border:1px solid var(--pb);border-radius:var(--r);padding:12px 14px}
.stat .label{font-size:.6rem;color:var(--dim);text-transform:uppercase}
.stat .val{font-size:1.2rem;color:var(--ac);font-weight:700;margin-top:2px}
.stat .detail{font-size:.65rem;color:var(--dim);margin-top:2px}
.scroll{overflow:auto;max-height:55vh;border:1px solid var(--pb);border-radius:var(--r)}
table{border-collapse:collapse;width:100%;font-size:.7rem}
thead th{padding:7px 5px;text-align:left;font-size:.6rem;font-weight:600;color:var(--ac);text-transform:uppercase;background:var(--p);border-bottom:1px solid var(--pb);position:sticky;top:0;white-space:nowrap}
tbody td{padding:4px 5px;border-bottom:1px solid #111921;white-space:nowrap}
tbody tr:nth-child(even){background:rgba(255,255,255,.015)}
tbody tr:hover{background:rgba(212,168,75,.08)}
#status{text-align:center;color:var(--dim);font-size:.8rem;margin:30px 0}
.obj{font-size:.68rem;color:var(--dim);white-space:pre-wrap;line-height:1.5;max-height:200px;overflow-y:auto}
.ft{text-align:center;margin-top:20px;font-size:.55rem;color:#2a3648}
.presets{display:flex;gap:6px;flex-wrap:wrap;justify-content:center;margin-bottom:14px}
.presets button{background:var(--pb);color:var(--t);border:1px solid #2a3648;padding:5px 10px;border-radius:var(--r);font-family:var(--m);font-size:.7rem;cursor:pointer}
.presets button:hover{border-color:var(--ac);color:var(--ac)}
</style>
</head>
<body>
<div class="w">
<h1>☄ Cometa <span>1P/Halley</span> — JPL Horizons</h1>
<div class="sub">Date în timp real de la NASA/JPL Solar System Dynamics</div>

<div class="presets">
  <button onclick="preset('2061-06-01','2061-10-01','7 d')">Următoarea apariție (~2061)</button>
  <button onclick="preset('1985-11-01','1986-05-01','7 d')">Apariția 1986</button>
  <button onclick="preset('2026-03-01','2026-04-01','1 d')">Azi (+30 zile)</button>
</div>

<div id="warn" class="warn">
  ⚠ JPL Horizons nu dispune de efemerida cometei Halley pentru date anterioare observațiilor lui Kepler (sec. XVII).<br>
  Pentru apariția din 66 d.Hr. sau 12 î.Hr., folosiți <b>halley_66ad.py</b> (Yeomans & Kiang 1981).
</div>

<div class="form-row">
  <div><label>Start</label><input id="start" value="2061-06-01"></div>
  <div><label>Stop</label><input id="stop" value="2061-10-01"></div>
  <div><label>Step</label><input id="step" value="7 d" style="width:80px"></div>
  <div><button id="btn" onclick="query()">Interogare JPL</button></div>
</div>

<div id="status"></div>
<div id="stats" class="stats" style="display:none"></div>
<div id="obj" class="card" style="display:none"></div>
<div id="tbl" style="display:none"></div>

<div class="ft">Sursa: NASA/JPL Solar System Dynamics — ssd.jpl.nasa.gov/horizons/</div>
</div>
<script>
function preset(a,b,c){document.getElementById('start').value=a;document.getElementById('stop').value=b;document.getElementById('step').value=c;query()}

function query(){
  const start=document.getElementById('start').value.trim();
  const stop=document.getElementById('stop').value.trim();
  const step=document.getElementById('step').value.trim();
  const btn=document.getElementById('btn');
  btn.disabled=true;btn.textContent='Se interogă…';
  document.getElementById('status').textContent='Se conectează la JPL Horizons…';
  document.getElementById('stats').style.display='none';
  document.getElementById('obj').style.display='none';
  document.getElementById('tbl').style.display='none';

  // Check for ancient dates
  const yr=parseInt(start);
  const warn=document.getElementById('warn');
  if(yr<1600){warn.style.display='block'}else{warn.style.display='none'}

  fetch('/query?start='+encodeURIComponent(start)+'&stop='+encodeURIComponent(stop)+'&step='+encodeURIComponent(step))
    .then(r=>r.json()).then(data=>{
      btn.disabled=false;btn.textContent='Interogare JPL';
      if(data.error){document.getElementById('status').innerHTML='<span style="color:#c75d5d">'+data.error+'</span>';return}
      document.getElementById('status').textContent='';
      renderData(data);
    }).catch(e=>{
      btn.disabled=false;btn.textContent='Interogare JPL';
      document.getElementById('status').innerHTML='<span style="color:#c75d5d">Eroare: '+e+'</span>';
    });
}

function renderData(data){
  // Stats
  document.getElementById('stats').style.display='grid';
  document.getElementById('stats').innerHTML=`
    <div class="stat"><div class="label">Țintă</div><div class="val">${data.target||'1P/Halley'}</div></div>
    <div class="stat"><div class="label">Interval</div><div class="val">${data.start}</div><div class="detail">→ ${data.stop}</div></div>
    <div class="stat"><div class="label">Rânduri date</div><div class="val">${data.rows.length}</div><div class="detail">pas: ${data.step}</div></div>
  `;
  // Object data
  if(data.obj_block){
    document.getElementById('obj').style.display='block';
    document.getElementById('obj').innerHTML='<div class="obj">'+data.obj_block.replace(/</g,'&lt;')+'</div>';
  }
  // Table
  if(data.rows.length>0){
    let h='<div class="scroll"><table><thead><tr><th>'+data.header.replace(/\s{2,}/g,'</th><th>')+'</th></tr></thead><tbody>';
    data.rows.forEach(r=>{h+='<tr><td>'+r.replace(/\s{2,}/g,'</td><td>')+'</td></tr>'});
    h+='</tbody></table></div>';
    document.getElementById('tbl').style.display='block';
    document.getElementById('tbl').innerHTML=h;
  }
}
</script>
</body>
</html>"""

class HorizonsHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): print(f"  {args[0]}")
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/' or parsed.path == '/index.html':
            self.send_response(200)
            self.send_header("Content-Type", "text/html;charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())
        elif parsed.path == '/query':
            qs = parse_qs(parsed.query)
            start = qs.get('start', [''])[0]
            stop = qs.get('stop', [''])[0]
            step = qs.get('step', ['1 d'])[0]
            try:
                raw = fetch(start, stop, step)
                info = parse(raw)
                result = json.dumps({
                    'target': info['target'],
                    'start': start, 'stop': stop, 'step': step,
                    'obj_block': info['obj_block'],
                    'header': info['ephem_hdr'],
                    'rows': info['rows'],
                })
            except Exception as e:
                result = json.dumps({'error': str(e)})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(result.encode())
        else:
            self.send_response(404); self.end_headers()

def serve_dashboard(port=8787):
    S = "=" * 70
    print(f"\n{S}")
    print(f"  1P/HALLEY — JPL Horizons Dashboard")
    print(f"{S}")
    print(f"  http://localhost:{port}")
    print(f"  Ctrl+C pentru oprire.\n{'-'*70}\n")
    srv = HTTPServer(("127.0.0.1", port), HorizonsHandler)
    try: webbrowser.open(f"http://localhost:{port}")
    except: pass
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\n  Oprit."); srv.server_close()

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    now = datetime.now(timezone.utc)
    default_start = now.strftime("%Y-%m-%d")
    default_stop  = (now + timedelta(days=30)).strftime("%Y-%m-%d")

    if "--serve" in sys.argv:
        idx = sys.argv.index("--serve")
        port = int(sys.argv[idx+1]) if len(sys.argv) > idx+1 else 8787
        serve_dashboard(port)
        return

    start = sys.argv[1] if len(sys.argv) > 1 else default_start
    stop  = sys.argv[2] if len(sys.argv) > 2 else default_stop
    step  = sys.argv[3] if len(sys.argv) > 3 else "1 d"

    # Normalise step: "7d" -> "7 d"
    if step and step[-1] in "dhm" and len(step) > 1 and step[-2].isdigit():
        step = step[:-1] + " " + step[-1]

    print(f"\n  Querying JPL Horizons for 1P/Halley …")
    print(f"  {start} -> {stop}, step {step}\n")

    raw = fetch(start, stop, step)

    if "$$SOE" not in raw:
        print("  WARNING: No ephemeris data markers found in response.")
        print("  Full response below:\n")
        print(raw)
        sys.exit(1)

    info = parse(raw)
    display(info, start, stop, step)


if __name__ == "__main__":
    main()
