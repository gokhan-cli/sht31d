import os
import re
import subprocess
import json
import threading
import urllib.parse
import urllib.request
import time as _time
from dotenv import load_dotenv
from flask import Flask, Response, render_template_string

load_dotenv()

app = Flask(__name__)

# --- WhatsApp Bildirim Ayarları (CallMeBot) ---
WA_ENABLED     = True
WA_PHONE       = os.getenv("WA_PHONE")        # .env'den oku
WA_APIKEY      = os.getenv("WA_APIKEY")       # .env'den oku
TEMP_THRESHOLD = 23.0

if not WA_PHONE:
    raise ValueError("KRİTİK HATA: WA_PHONE .env dosyasında bulunamadı!")
if not WA_APIKEY:
    raise ValueError("KRİTİK HATA: WA_APIKEY .env dosyasında bulunamadı!")
_alert_sent      = False
_last_temp       = None
_last_alert_time = 0

ALERT_INTERVAL = 600

def send_whatsapp_alert(temp):
    try:
        msg     = f"⚠️ RPi3 Sıcaklık Uyarısı: {temp:.2f} °C (eşik: {TEMP_THRESHOLD} °C)"
        encoded = urllib.parse.quote(msg)
        url     = (f"https://api.callmebot.com/whatsapp.php"
                   f"?phone={WA_PHONE}&text={encoded}&apikey={WA_APIKEY}")
        urllib.request.urlopen(url, timeout=10)
        print(f"[WHATSAPP] Mesaj gönderildi: {temp:.2f} °C")
    except Exception as e:
        print(f"[WHATSAPP] Hata: {e}")

def check_temp_alert(temp_str):
    global _alert_sent, _last_temp, _last_alert_time
    try:
        temp = float(temp_str)
        _last_temp = temp
        now = _time.time()
        if temp >= TEMP_THRESHOLD:
            if not _alert_sent or (now - _last_alert_time) >= ALERT_INTERVAL:
                _alert_sent      = True
                _last_alert_time = now
                if WA_ENABLED:
                    threading.Thread(target=send_whatsapp_alert, args=(temp,), daemon=True).start()
        elif temp < TEMP_THRESHOLD:
            _alert_sent = False
    except Exception:
        pass

PATTERN = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
    r".*?Temp:\s*([\d.]+)"
    r".*?Hum:\s*([\d.]+)"
    r".*?HI:\s*([\d.]+)"
    r".*?CPU:\s*([\d.]+)"
    r".*?HS:\s*([\d.]+)"
)
HEATER_ON  = re.compile(r"Is\u0131t\u0131c\u0131 A\u00c7IK")
HEATER_OFF = re.compile(r"Is\u0131t\u0131c\u0131 KAPALI")

HTML = r"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Sıcaklık ve Nem Takibi</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
  <style>
:root {
  --bg:    #f2f2f2;
  --surf:  #ffffff;
  --surf2: #f7f7f7;

  --brd:   #cfcfcf;
  --brd2:  #a8a8a8;

  --c1: #000000;
  --c2: #222222;
  --c3: #444444;
  --c4: #666666;
  --c5: #111111;

  --lbl:  #707070;
  --val:  #000000;
  --unit: #5f5f5f;
  --dim:  #8a8a8a;
  --txt:  #1f1f1f;

  --mono: 'JetBrains Mono', monospace;
  --head: 'Outfit', sans-serif;
}
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background: var(--bg);
      color: var(--txt);
      font-family: var(--mono);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* ── HEADER ── */
    header {
      padding: 1rem 1.4rem;
      border-bottom: 1px solid #cfcfcf;
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: var(--surf);
      position: sticky;
      top: 0;
      z-index: 10;
    }
    .brand {
      font-family: var(--head);
      font-size: 1.05rem;
      font-weight: 800;
      letter-spacing: .04em;
      color: #000;
    }
    .brand span { color: var(--c1); }

    .conn {
      display: flex;
      align-items: center;
      gap: .5rem;
    }
    .status-dot {
      width: 8px; height: 8px;
      border-radius: 50%;
      background: #000;
      box-shadow: none;
      animation: none;
    }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:.25} }
    .status-label {
      font-size: .65rem;
      letter-spacing: .18em;
      color: var(--lbl);
      font-family: var(--head);
      font-weight: 600;
    }

    /* ── GRID ── */
    .cards {
      display: grid;
      /* Mobile: 2 columns; desktop: 5 columns */
      grid-template-columns: repeat(2, 1fr);
      gap: 1px;
      background: var(--brd);
      border: 1px solid var(--brd);
      border-radius: 10px;
      overflow: hidden;
      margin: 1.2rem 1rem 0;
    }

    /* Isıtıcı kartı mobilde tam genişlik */
    .card:last-child {
      grid-column: 1 / -1;
    }

    @media (min-width: 640px) {
      .cards {
        grid-template-columns: repeat(5, 1fr);
        margin: 1.6rem 1.6rem 0;
      }
      .card:last-child {
        grid-column: auto;
      }
    }

    /* ── CARD ── */
    .card {
      background: var(--surf);
      padding: 1.2rem 1.1rem 1rem;
      display: flex;
      flex-direction: column;
      gap: .4rem;
      position: relative;
      overflow: hidden;
    }
    .card:hover { background: var(--surf); }

    /* label */
    .card-label {
      font-family: var(--head);
      font-size: .6rem;
      font-weight: 600;
      letter-spacing: .18em;
      text-transform: uppercase;
      color: var(--lbl);
      margin-bottom: .1rem;
    }

    /* value — high contrast white-ish with colour glow */
    .card-value {
      font-size: 2.2rem;
      line-height: 1;
      font-weight: 700;
      color: #000;
      text-shadow: none;
      letter-spacing: -.02em;
    }

    /* unit */
    .card-unit {
      font-size: .72rem;
      color: var(--color);
      opacity: .7;
      margin-top: .05rem;
      font-weight: 600;
    }

    /* progress bar */
    .card-bar {
      height: 6px;
      border-radius: 2px;
      background: var(--brd2);
      margin-top: .6rem;
      overflow: hidden;
    }
    .card-bar-fill {
      height: 100%;
      border-radius: 2px;
      background: var(--color);
      width: 0%;
      transition: width .4s linear;
      box-shadow: none;
    }

    /* ── HEATER CARD ── */
    .heater-row {
      display: flex;
      align-items: center;
      gap: .8rem;
      margin-top: .4rem;
    }
    .heater-icon {
      font-size: 1.6rem;
      line-height: 1;
    }
    .heater-badge {
      font-family: var(--head);
      font-size: .75rem;
      font-weight: 700;
      letter-spacing: .14em;
      padding: .3rem .8rem;
      border-radius: 6px;
      border: 1.5px solid var(--color);
      color: var(--val);
      background: #efefef;
      transition: all .3s;
    }

    /* ── TIMESTAMP ── */
    .timestamp {
      text-align: center;
      font-size: .65rem;
      letter-spacing: .12em;
      color: var(--dim);
      padding: .8rem 1rem;
      font-family: var(--head);
    }

    /* ── LOG ── */
    .log-wrap {
      margin: .8rem 1rem 1.5rem;
      background: var(--surf);
      border: 1px solid var(--brd);
      border-radius: 10px;
      overflow: hidden;
    }
    @media (min-width: 640px) {
      .log-wrap { margin: 1rem 1.6rem 2rem; }
    }
    .log-header {
      font-family: var(--head);
      font-size: .58rem;
      font-weight: 600;
      letter-spacing: .22em;
      text-transform: uppercase;
      color: var(--lbl);
      padding: .6rem 1rem;
      border-bottom: 1px solid var(--brd);
      background: #f4f4f4;
    }
    .log-body {
      padding: .6rem .9rem;
      max-height: 140px;
      overflow-y: auto;
      font-size: .68rem;
      line-height: 1.75;
      color: var(--dim);
    }
    .log-body div { border-bottom: 1px solid #e5e5e5; padding: .08rem 0; }
    .log-body div:last-child { color: var(--txt); }
    .log-body::-webkit-scrollbar { width: 3px; }
    .log-body::-webkit-scrollbar-thumb { background: var(--brd2); border-radius: 2px; }

    /* ── ANIMATIONS ── */
    @keyframes flash { 0%{opacity:.25} 60%{opacity:1} 100%{opacity:1} }
    .flash { animation: flash .5s ease; }

    @keyframes pulseGlow {
      0%,100% { box-shadow: 0 0 8px var(--c5); }
      50%      { box-shadow: 0 0 22px var(--c5); }
    }
    .heater-active { animation: pulseGlow 1.2s infinite; }

    .flash {
      animation: none !important;
    }

    .heater-active {
      animation: none !important;
    }

    .status-dot {
      animation: none !important;
    }

    * {
      scroll-behavior: auto;
    }
  </style>
</head>
<body>

<header>
  <div class="brand">Sistem <span>Odası</span></div>
  <div class="conn">
    <span class="status-dot" id="dot"></span>
    <span class="status-label" id="conn-label">BAĞLANIYOR</span>
  </div>
</header>

<div class="cards">

  <div class="card" style="--color:var(--c1)">
    <div class="card-label">Sıcaklık</div>
    <div class="card-value" id="v-temp">—</div>
    <div class="card-unit">°C</div>
    <div class="card-bar"><div class="card-bar-fill" id="b-temp"></div></div>
  </div>

  <div class="card" style="--color:var(--c2)">
    <div class="card-label">Bağıl Nem</div>
    <div class="card-value" id="v-hum">—</div>
    <div class="card-unit">%</div>
    <div class="card-bar"><div class="card-bar-fill" id="b-hum"></div></div>
  </div>

  <div class="card" style="--color:var(--c3)">
    <div class="card-label">Hissedilen</div>
    <div class="card-value" id="v-hi">—</div>
    <div class="card-unit">°C &nbsp;HI</div>
    <div class="card-bar"><div class="card-bar-fill" id="b-hi"></div></div>
  </div>

  <div class="card" style="--color:var(--c4)">
    <div class="card-label">CPU Sıcaklığı</div>
    <div class="card-value" id="v-cpu">—</div>
    <div class="card-unit">°C</div>
    <div class="card-bar"><div class="card-bar-fill" id="b-cpu"></div></div>
  </div>

  <div class="card" id="heater-card" style="--color:var(--c5)">
    <div class="card-label">Isıtıcı</div>
    <div class="heater-row">
      <span class="heater-icon" id="v-hs">○</span>
      <span class="heater-badge" id="hs-badge">—</span>
    </div>
  </div>

</div>

<div class="timestamp" id="ts">—</div>

<div class="log-wrap">
  <div class="log-header">▸ Ham Log Akışı</div>
  <div class="log-body" id="log"></div>
</div>

<script>
const maxVal = { temp: 50, hum: 100, hi: 50, cpu: 85 };

function set(id, val) {
  const el = document.getElementById('v-' + id);
  el.textContent = parseFloat(val).toFixed(2);
  el.classList.remove('flash');
  void el.offsetWidth;
  el.classList.add('flash');
  const bar = document.getElementById('b-' + id);
  if (bar) bar.style.width = Math.min(100, (parseFloat(val) / maxVal[id]) * 100) + '%';
}

function setHeater(val) {
  const on    = parseFloat(val) >= 1;
  const badge = document.getElementById('hs-badge');
  const icon  = document.getElementById('v-hs');
  const card  = document.getElementById('heater-card');
  badge.textContent = on ? 'AÇIK' : 'KAPALI';
  icon.textContent  = on ? '●' : '○';
  icon.style.color  = on ? 'var(--c5)' : 'var(--lbl)';
  icon.style.textShadow = on ? '0 0 16px var(--c5)' : 'none';
  card.classList.toggle('heater-active', on);
}

function addLog(line, heaterEvent) {
  const log = document.getElementById('log');
  const d   = document.createElement('div');
  d.textContent = line;
  if (heaterEvent === 'on')  { d.style.color = 'var(--c5)'; d.style.fontWeight = '700'; }
  if (heaterEvent === 'off') { d.style.color = 'var(--c2)'; }
  log.appendChild(d);
  while (log.children.length > 30) log.removeChild(log.firstChild);
  log.scrollTop = log.scrollHeight;
}

const src = new EventSource('/stream');

src.onopen = () => {
  document.getElementById('conn-label').textContent = 'CANLI';
  document.getElementById('dot').style.cssText = 'background:var(--c2);box-shadow:0 0 8px var(--c2)';
};
src.onerror = () => {
  document.getElementById('conn-label').textContent = 'KESİLDİ';
  document.getElementById('dot').style.cssText = 'background:var(--c5);box-shadow:0 0 8px var(--c5)';
};

src.onmessage = (e) => {
  const d = JSON.parse(e.data);
  if (!d || Object.keys(d).length === 0) return; // keep-alive

  if (d.heater_event === 'on' || d.heater_event === 'off') {
    triggerHeaterFlash(d.heater_event);
    addLog(d.raw, d.heater_event);
    return;
  }

  set('temp', d.temp);
  set('hum',  d.hum);
  set('hi',   d.hi);
  set('cpu',  d.cpu);
  setHeater(d.hs);
  document.getElementById('ts').textContent = '⏱ ' + d.time;
  addLog(d.raw, null);
};

function triggerHeaterFlash(state) {
  const color = state === 'on' ? 'var(--c5)' : 'var(--c2)';
  const card  = document.getElementById('heater-card');
  card.style.outline    = '1px solid ' + (state === 'on' ? '#111111' : '#e7e7e7');
  card.style.boxShadow  = '0 0 10px ' + (state === 'on' ? '#11111166' : '#e7e7e766');
  setTimeout(() => { card.style.outline = ''; card.style.boxShadow = ''; }, 1800);
  setHeater(state === 'on' ? 1 : 0);
}

let toastTimer;
function showToast(msg, color) {
  let t = document.getElementById('toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'toast';
    t.style.cssText = [
      'position:fixed', 'bottom:1.4rem', 'right:1.2rem',
      'padding:.55rem 1.1rem', 'border-radius:8px',
      "font-family:'Outfit',sans-serif", 'font-size:.82rem',
      'font-weight:600', 'border:1.5px solid',
      'z-index:999', 'transition:opacity .4s',
      'pointer-events:none', 'letter-spacing:.06em'
    ].join(';');
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.background  = color + '22';
  t.style.borderColor = color;
  t.style.color       = '#000';
  t.style.opacity     = '1';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.style.opacity = '0', 3200);
}
</script>
</body>
</html>"""


# --- Merkezi journalctl okuyucu ---
import queue

_subscribers = []
_subs_lock   = threading.Lock()
_last_event  = None


def _reader_thread():
    """Tek bir journalctl process — tüm SSE bağlantılarına dağıtır."""
    global _last_event
    proc = subprocess.Popen(
        ["journalctl", "-u", "influxdb.service", "-f", "-n", "1",
         "--no-pager", "--output=cat"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    for line in proc.stdout:
        line = line.strip()
        payload = None
        m = PATTERN.search(line)
        if m:
            check_temp_alert(m.group(2))
            payload = {
                "time": m.group(1),
                "temp": m.group(2),
                "hum":  m.group(3),
                "hi":   m.group(4),
                "cpu":  m.group(5),
                "hs":   m.group(6),
                "raw":  line,
                "heater_event": None,
            }
        elif HEATER_ON.search(line):
            payload = {"heater_event": "on",  "raw": line}
        elif HEATER_OFF.search(line):
            payload = {"heater_event": "off", "raw": line}

        if payload:
            msg = f"data: {json.dumps(payload)}\n\n"
            _last_event = msg
            with _subs_lock:
                for q in _subscribers:
                    try:
                        q.put_nowait(msg)
                    except Exception:
                        pass


threading.Thread(target=_reader_thread, daemon=True).start()


@app.route("/stream")
def stream():
    q = queue.Queue(maxsize=50)
    if _last_event:
        q.put(_last_event)
    with _subs_lock:
        _subscribers.append(q)

    def event_stream():
        try:
            while True:
                try:
                    msg = q.get(timeout=25)
                    yield msg
                except queue.Empty:
                    yield "data: {}\n\n"  # keep-alive
        finally:
            with _subs_lock:
                try:
                    _subscribers.remove(q)
                except ValueError:
                    pass

    return Response(event_stream(), mimetype="text/event-stream",
                    headers={"X-Accel-Buffering": "no",
                             "Cache-Control": "no-cache"})


@app.route("/")
def index():
    return render_template_string(HTML)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
