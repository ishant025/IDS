import json
import os
import re
import sqlite3
import time
import threading
from collections import defaultdict, deque
from datetime import datetime
from flask import Flask, request, jsonify, Response, stream_with_context, render_template_string

app = Flask(__name__)

# ── Configuration ────────────────────────────────────────────────────────────
PORT = 5001
VALID_CREDENTIALS = {
    "admin": "secret123",
    "user": "password",
    "root": "toor",
}
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
LOG_FILE = os.path.join(LOG_DIR, "traffic.jsonl")

# ── Thread-safe state ─────────────────────────────────────────────────────────
log_lock = threading.Lock()
stats_lock = threading.Lock()

# Per-IP request timestamps (sliding window, last 10 s)
ip_requests: dict[str, deque] = defaultdict(deque)
ip_lock = threading.Lock()

# Track IPs currently doing high-rate flood (for DoS vs DDoS distinction)
_flooding_ips: dict[str, float] = {}   # ip → last_seen_timestamp
_flooding_lock = threading.Lock()
DDOS_UNIQUE_IP_THRESHOLD = 3           # 3+ simultaneous flooding IPs = DDoS

# Server stats
total_requests = 0
failed_logins = 0
blocked_ips: set[str] = set()

# SSE subscribers: list of queue.Queue instances
sse_subscribers: list = []
sse_lock = threading.Lock()

# ── Ensure log directory exists ───────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)

# ── Vulnerable SQLite DB (for demo) ──────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

def _init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS employees "
              "(id INTEGER PRIMARY KEY, name TEXT, department TEXT, salary INTEGER, email TEXT)")
    c.execute("DELETE FROM employees")
    c.executemany("INSERT INTO employees VALUES (?,?,?,?,?)", [
        (1, "Alice Johnson",  "Engineering",  120000, "alice@corp.local"),
        (2, "Bob Smith",      "HR",             85000, "bob@corp.local"),
        (3, "Carol White",   "Finance",        98000, "carol@corp.local"),
        (4, "Dave Brown",    "Engineering",   135000, "dave@corp.local"),
        (5, "Eve Davis",     "IT Security",   110000, "eve@corp.local"),
        (6, "Frank Miller",  "Management",    200000, "frank@corp.local"),
    ])
    conn.commit()
    conn.close()

_init_db()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_request_count(ip: str) -> int:
    """Return number of requests from *ip* in the last 10 seconds."""
    now = time.time()
    cutoff = now - 10.0
    with ip_lock:
        dq = ip_requests[ip]
        # Purge old entries
        while dq and dq[0] < cutoff:
            dq.popleft()
        dq.append(now)
        return len(dq)


# SQL Injection pattern detector
_SQLI_PATTERNS = re.compile(
    r"('\s*(or|and)\s*'?\d)|(\'\s*--)|(\'\s*;)|(\bor\b\s+\d+=\d+)"
    r"|(union\s+select)|(select\s+.*\s+from)|(drop\s+table)"
    r"|(insert\s+into)|(\bor\b\s+'[^']*'\s*=\s*')",
    re.IGNORECASE,
)

def _contains_sqli(text: str) -> bool:
    return bool(_SQLI_PATTERNS.search(text))

def _count_flooding_ips(src_ip: str, count: int) -> int:
    """Register src_ip as flooding (if count > 15) and return total unique flooding IPs."""
    now    = time.time()
    cutoff = now - 12.0   # consider IPs active for 12 s
    with _flooding_lock:
        if count > 15:
            _flooding_ips[src_ip] = now
        # Evict stale IPs
        stale = [ip for ip, ts in _flooding_ips.items() if ts < cutoff]
        for ip in stale:
            del _flooding_ips[ip]
        return len(_flooding_ips)


def _classify_attack(count: int, sqli: bool = False,
                     path: str = "/", src_ip: str = "") -> str:
    """Classify attack type based on request count, path, and number of flooding IPs."""
    if sqli:
        return "sql_injection"
    # Login endpoint: repeated attempts regardless of rate = brute_force
    if path in ("/login", "/auth", "/signin") and count > 5:
        return "brute_force"
    # High-rate flood — check if it's multi-source (DDoS) or single-source (DoS)
    if count > 15:
        active_flooding = _count_flooding_ips(src_ip, count)
        if active_flooding >= DDOS_UNIQUE_IP_THRESHOLD:
            return "ddos"
        return "dos"
    if count > 5:
        return "brute_force"
    return "unknown"


def _write_log(entry: dict) -> None:
    """Append a JSON log entry and notify SSE subscribers."""
    line = json.dumps(entry)
    with log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    # Notify SSE listeners
    with sse_lock:
        for q in list(sse_subscribers):
            try:
                q.put_nowait(line)
            except Exception:
                pass


def _build_log_entry(
    *,
    username: str = "",
    success: bool = False,
    attack_type: str = "unknown",
    start_time: float,
    payload_size: int = 0,
    request_count: int = 1,
) -> dict:
    src_ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "127.0.0.1"
    src_ip = src_ip.split(",")[0].strip()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "src_ip": src_ip,
        "src_port": request.environ.get("REMOTE_PORT", 0),
        "dst_port": PORT,
        "method": request.method,
        "path": request.path,
        "username": username,
        "success": success,
        "attack_type": attack_type,
        "flow_duration_ms": round((time.time() - start_time) * 1000, 3),
        "payload_size": payload_size,
        "request_count_last_10s": request_count,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>CorpNet Secure Portal</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #0d1117;
      color: #c9d1d9;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 32px;
    }
    .brand-icon {
      width: 48px; height: 48px;
      background: linear-gradient(135deg, #238636, #1f6feb);
      border-radius: 12px;
      display: flex; align-items: center; justify-content: center;
      font-size: 24px;
    }
    .brand-name { font-size: 22px; font-weight: 700; color: #e6edf3; letter-spacing: 0.5px; }
    .brand-tagline { font-size: 11px; color: #8b949e; letter-spacing: 1.5px; text-transform: uppercase; }

    .card {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 16px;
      padding: 40px 44px;
      width: 100%;
      max-width: 420px;
      box-shadow: 0 16px 48px rgba(0,0,0,0.5);
    }

    h2 {
      font-size: 20px;
      font-weight: 600;
      color: #e6edf3;
      margin-bottom: 6px;
    }
    .subtitle {
      font-size: 13px;
      color: #8b949e;
      margin-bottom: 28px;
    }

    label {
      display: block;
      font-size: 13px;
      font-weight: 500;
      color: #8b949e;
      margin-bottom: 6px;
    }
    input[type="text"], input[type="password"] {
      width: 100%;
      padding: 10px 14px;
      background: #0d1117;
      border: 1px solid #30363d;
      border-radius: 8px;
      color: #e6edf3;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
      margin-bottom: 18px;
    }
    input[type="text"]:focus, input[type="password"]:focus {
      border-color: #1f6feb;
      box-shadow: 0 0 0 3px rgba(31,111,235,0.15);
    }

    .btn {
      width: 100%;
      padding: 11px;
      background: linear-gradient(180deg, #238636, #1a7f37);
      border: none;
      border-radius: 8px;
      color: #fff;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      letter-spacing: 0.3px;
      transition: opacity 0.2s;
      margin-top: 4px;
    }
    .btn:hover { opacity: 0.88; }

    .alert {
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 13px;
      margin-bottom: 20px;
    }
    .alert-error { background: rgba(218,54,51,0.15); border: 1px solid rgba(218,54,51,0.4); color: #f85149; }
    .alert-success { background: rgba(35,134,54,0.15); border: 1px solid rgba(35,134,54,0.4); color: #3fb950; }

    .divider { border-top: 1px solid #21262d; margin: 24px 0; }

    .footer-links {
      display: flex; justify-content: center; gap: 20px;
      font-size: 12px; color: #8b949e;
    }
    .footer-links a { color: #8b949e; text-decoration: none; }
    .footer-links a:hover { color: #c9d1d9; }

    .security-badge {
      display: flex; align-items: center; gap: 6px;
      font-size: 11px; color: #3fb950;
      margin-top: 20px; justify-content: center;
    }
    .security-badge::before { content: "🔒"; }

    .version-tag {
      position: fixed; bottom: 16px; right: 20px;
      font-size: 11px; color: #30363d;
    }
  </style>
</head>
<body>
  <div class="brand">
    <div class="brand-icon">🏢</div>
    <div>
      <div class="brand-name">CorpNet</div>
      <div class="brand-tagline">Secure Enterprise Portal</div>
    </div>
  </div>

  <div class="card">
    <h2>Sign in to your account</h2>
    <p class="subtitle">Use your corporate credentials to continue</p>

    {% if message %}
    <div class="alert {{ 'alert-success' if success else 'alert-error' }}">
      {{ message }}
    </div>
    {% endif %}

    <form method="POST" action="/login">
      <label for="username">Username</label>
      <input type="text" id="username" name="username"
             placeholder="your.name@corp.local" autocomplete="username" required />

      <label for="password">Password</label>
      <input type="password" id="password" name="password"
             placeholder="Enter your password" autocomplete="current-password" required />

      <button class="btn" type="submit">Sign In</button>
    </form>

    <div style="text-align:center; margin-top: 16px;">
      <a href="/search" style="color: #58a6ff; font-size: 12px; text-decoration: none;">
        &rarr; Employee Directory (Search)
      </a>
    </div>

    <div class="divider"></div>
    <div class="footer-links">
      <a href="#">Forgot password?</a>
      <a href="#">IT Support</a>
      <a href="#">Privacy Policy</a>
    </div>
    <div class="security-badge">Secured with TLS 1.3 · SOC 2 Compliant</div>
  </div>

  <div class="version-tag">CorpNet Portal v4.2.1 · Build 20240115</div>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    global total_requests
    t0 = time.time()
    src_ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "127.0.0.1"
    src_ip = src_ip.split(",")[0].strip()

    count = _get_request_count(src_ip)

    with stats_lock:
        total_requests += 1
        if count > 20:
            blocked_ips.add(src_ip)

    entry = _build_log_entry(
        attack_type=_classify_attack(count, path=request.path, src_ip=src_ip),
        start_time=t0,
        request_count=count,
    )
    _write_log(entry)
    return render_template_string(LOGIN_HTML, message=None, success=False), 200


@app.route("/login", methods=["GET", "POST"])
def login():
    global total_requests, failed_logins
    t0 = time.time()
    src_ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "127.0.0.1"
    src_ip = src_ip.split(",")[0].strip()

    if request.method == "GET":
        return render_template_string(LOGIN_HTML, message=None, success=False)

    # POST
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    payload_size = request.content_length or len(request.get_data())

    count = _get_request_count(src_ip)
    attack_type = _classify_attack(count, path=request.path, src_ip=src_ip)

    success = VALID_CREDENTIALS.get(username) == password

    with stats_lock:
        total_requests += 1
        if not success:
            failed_logins += 1
        if count > 20:
            blocked_ips.add(src_ip)

    entry = _build_log_entry(
        username=username,
        success=success,
        attack_type=attack_type,
        start_time=t0,
        payload_size=payload_size,
        request_count=count,
    )
    _write_log(entry)

    if success:
        message = f"Welcome back, {username}! You are now logged in."
    else:
        message = "Invalid username or password. Please try again."

    return render_template_string(
        LOGIN_HTML, message=message, success=success
    ), (200 if success else 401)


@app.route("/status", methods=["GET"])
def status():
    with stats_lock:
        return jsonify({
            "server": "CorpNet Secure Portal",
            "port": PORT,
            "total_requests": total_requests,
            "failed_logins": failed_logins,
            "blocked_ips": list(blocked_ips),
            "blocked_ip_count": len(blocked_ips),
            "log_file": os.path.abspath(LOG_FILE),
            "uptime_note": "Stats reset on server restart",
        })


@app.route("/logs/stream", methods=["GET"])
def logs_stream():
    """Server-Sent Events endpoint — streams new log lines in real time."""
    import queue

    q: queue.Queue = queue.Queue(maxsize=500)
    with sse_lock:
        sse_subscribers.append(q)

    def generate():
        try:
            yield "data: {\"event\": \"connected\", \"msg\": \"SSE stream started\"}\n\n"
            while True:
                try:
                    line = q.get(timeout=30)
                    yield f"data: {line}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            pass
        finally:
            with sse_lock:
                try:
                    sse_subscribers.remove(q)
                except ValueError:
                    pass

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Search page HTML (intentionally vulnerable to SQLi) ─────────────────────
SEARCH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>CorpNet &mdash; Employee Directory</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0d1117;
           color: #c9d1d9; min-height: 100vh; padding: 32px 20px 80px; }
    .container { max-width: 900px; margin: 0 auto; }

    /* Header */
    .header { display: flex; align-items: center; gap: 14px; margin-bottom: 20px; }
    .logo { width: 42px; height: 42px; background: linear-gradient(135deg,#1f6feb,#8957e5);
            border-radius: 10px; display: flex; align-items: center; justify-content: center;
            font-size: 20px; flex-shrink: 0; }
    h1 { font-size: 20px; font-weight: 700; color: #e6edf3; }
    .subtitle-small { font-size: 12px; color: #8b949e; }

    /* Nav */
    .nav { display: flex; gap: 20px; margin-bottom: 20px; border-bottom: 1px solid #21262d;
           padding-bottom: 12px; }
    .nav a { color: #8b949e; text-decoration: none; font-size: 13px; }
    .nav a:hover, .nav a.active { color: #58a6ff; }

    /* Stats bar */
    .stats-bar { display: flex; gap: 0; margin-bottom: 20px;
                 background: #161b22; border: 1px solid #30363d; border-radius: 10px;
                 overflow: hidden; }
    .stat-item { flex: 1; padding: 14px 18px; border-right: 1px solid #21262d; }
    .stat-item:last-child { border-right: none; }
    .stat-label { font-size: 10px; color: #8b949e; text-transform: uppercase;
                  letter-spacing: 0.8px; margin-bottom: 4px; }
    .stat-value { font-size: 18px; font-weight: 700; color: #e6edf3; }
    .stat-vuln { color: #f85149 !important; }

    /* SQLi tips */
    .sqli-tips { background: rgba(239,68,68,0.06); border: 1.5px solid rgba(239,68,68,0.45);
                 border-radius: 10px; padding: 18px 20px; margin-bottom: 20px; }
    .sqli-tips-title { font-size: 13px; font-weight: 700; color: #f85149; margin-bottom: 12px;
                       display: flex; align-items: center; gap: 8px; }
    .sqli-payload-row { display: flex; align-items: baseline; gap: 10px;
                        padding: 7px 0; border-bottom: 1px solid rgba(239,68,68,0.15); }
    .sqli-payload-row:last-child { border-bottom: none; }
    code { background: #0d1117; padding: 3px 8px; border-radius: 5px;
           font-size: 12px; color: #ffa657; font-family: 'Cascadia Code', 'Fira Code', monospace;
           white-space: nowrap; }
    .payload-effect { font-size: 11px; color: #8b949e; flex-shrink: 0; }

    /* Search box */
    .search-box { background: #161b22; border: 1px solid #30363d; border-radius: 12px;
                  padding: 22px 24px; margin-bottom: 20px; }
    .search-box h2 { font-size: 14px; font-weight: 600; color: #e6edf3; margin-bottom: 12px; }
    .hint { font-size: 11px; color: #8b949e; margin-bottom: 10px; }
    .input-row { display: flex; gap: 10px; }
    input[type=text] { flex: 1; padding: 9px 14px; background: #0d1117;
                       border: 1px solid #30363d; border-radius: 7px; color: #e6edf3;
                       font-size: 13px; outline: none; transition: border-color 0.2s; }
    input[type=text]:focus { border-color: #1f6feb; box-shadow: 0 0 0 3px rgba(31,111,235,0.12); }
    .btn { padding: 9px 22px; background: #1f6feb; border: none; border-radius: 7px;
           color: #fff; font-size: 13px; font-weight: 600; cursor: pointer;
           transition: background 0.15s; white-space: nowrap; }
    .btn:hover { background: #388bfd; }

    /* SQLi alert */
    .alert-sqli { background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.4);
                  border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;
                  color: #f85149; font-size: 13px; }

    /* Results table */
    .table-wrap { border-radius: 10px; overflow: hidden;
                  border: 1px solid #30363d; margin-bottom: 8px; }
    table { width: 100%; border-collapse: collapse; background: #161b22; }
    th { background: #21262d; padding: 10px 14px; text-align: left;
         font-size: 11px; color: #8b949e; font-weight: 600; text-transform: uppercase;
         letter-spacing: 0.6px; }
    td { padding: 10px 14px; font-size: 13px; border-bottom: 1px solid #21262d;
         transition: background 0.1s; }
    tr:last-child td { border-bottom: none; }
    tbody tr:hover td { background: #1c2128; }
    .col-salary { color: #f85149; font-weight: 600; }

    /* What-happened box */
    .sqli-explain { background: rgba(239,68,68,0.08); border: 1.5px solid rgba(239,68,68,0.5);
                    border-radius: 10px; padding: 20px 24px; margin-bottom: 20px; }
    .sqli-explain h3 { font-size: 15px; color: #f85149; margin-bottom: 10px; }
    .sqli-explain p { font-size: 13px; color: #c9d1d9; margin-bottom: 8px; line-height: 1.55; }
    .sqli-explain a { color: #58a6ff; font-size: 13px; font-weight: 600; text-decoration: none; }
    .sqli-explain a:hover { text-decoration: underline; }

    .no-results { color: #8b949e; font-size: 13px; padding: 24px; text-align: center; }
    .back-link { font-size: 12px; color: #58a6ff; text-decoration: none;
                 display: inline-block; margin-top: 16px; }

    /* Footer */
    .site-footer { position: fixed; bottom: 0; left: 0; right: 0;
                   background: #161b22; border-top: 1px solid #21262d;
                   padding: 10px 24px; font-size: 11px; color: #8b949e;
                   display: flex; align-items: center; justify-content: center; gap: 6px; }
    .site-footer a { color: #58a6ff; text-decoration: none; }
    .site-footer a:hover { text-decoration: underline; }
    .ids-dot { width: 7px; height: 7px; border-radius: 50%; background: #f85149;
               display: inline-block; animation: blink 1.4s infinite; }
    @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo">&#x1F3E2;</div>
      <div>
        <h1>CorpNet Secure Portal</h1>
        <div class="subtitle-small">Internal Employee Directory</div>
      </div>
    </div>

    <nav class="nav">
      <a href="/">Login</a>
      <a href="/search" class="active">Employee Search</a>
    </nav>

    <!-- Stats bar -->
    <div class="stats-bar">
      <div class="stat-item">
        <div class="stat-label">Total employees</div>
        <div class="stat-value">6</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Departments</div>
        <div class="stat-value">4</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Security status</div>
        <div class="stat-value stat-vuln">&#x26A0;&#xFE0F; VULNERABLE TO SQLi</div>
      </div>
    </div>

    <!-- SQLi tips -->
    <div class="sqli-tips">
      <div class="sqli-tips-title">&#x26A0; DEMO &mdash; This search is intentionally vulnerable to SQL Injection</div>
      <div class="sqli-payload-row">
        <code>' OR '1'='1</code>
        <span class="payload-effect">&rarr; Returns ALL employee records (auth bypass)</span>
      </div>
      <div class="sqli-payload-row">
        <code>' UNION SELECT id,name,department,salary,email FROM employees --</code>
        <span class="payload-effect">&rarr; Dumps salary data</span>
      </div>
      <div class="sqli-payload-row">
        <code>'; DROP TABLE employees; --</code>
        <span class="payload-effect">&rarr; Deletes all data (destructive!)</span>
      </div>
    </div>

    <!-- Search form -->
    <div class="search-box">
      <h2>Search employees by name</h2>
      <p class="hint">Enter a name to find employee records (e.g. &ldquo;Alice&rdquo;)</p>
      <form method="GET" action="/search">
        <div class="input-row">
          <input type="text" name="q" value="{{ query }}" placeholder="Search name..." autofocus />
          <button class="btn" type="submit">Search</button>
        </div>
      </form>
    </div>

    {% if sqli_detected %}
    <div class="alert-sqli">
      &#x26A0; SQL Injection payload detected in your query: <strong>{{ query }}</strong>
    </div>
    {% endif %}

    {% if results != None %}
      {% if results %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>ID</th><th>Name</th><th>Department</th><th>Salary</th><th>Email</th></tr>
          </thead>
          <tbody>
            {% for row in results %}
            <tr>
              <td>{{ row[0] }}</td>
              <td>{{ row[1] }}</td>
              <td>{{ row[2] }}</td>
              <td class="col-salary">{{ row[3] }}</td>
              <td>{{ row[4] }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      <p style="font-size:11px;color:#8b949e;margin-top:6px;">{{ results|length }} record(s) returned</p>
      {% else %}
      <div class="no-results">No employees found matching &ldquo;{{ query }}&rdquo;</div>
      {% endif %}
    {% endif %}

    {% if sqli_detected %}
    <div class="sqli-explain">
      <h3>&#x1F480; SQL Injection successful!</h3>
      <p>Your payload broke out of the SQL string and injected malicious commands.</p>
      <p>The IDS dashboard has logged this as an <strong>attack</strong> and your ML models have flagged it.</p>
      <a href="http://localhost:8502" target="_blank">&rarr; View IDS alert on dashboard</a>
    </div>
    {% endif %}

    <a href="/" class="back-link">&larr; Back to login</a>
  </div>

  <!-- Footer -->
  <div class="site-footer">
    <span class="ids-dot"></span>
    IDS Monitoring Active &middot; All requests logged &middot;
    <a href="http://localhost:8502" target="_blank">Go to dashboard &rarr;</a>
  </div>
</body>
</html>"""


@app.route("/search", methods=["GET"])
def search():
    global total_requests
    t0 = time.time()
    src_ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "127.0.0.1"
    src_ip = src_ip.split(",")[0].strip()
    count = _get_request_count(src_ip)

    query = request.args.get("q", "").strip()
    sqli  = _contains_sqli(query) if query else False
    attack_type = _classify_attack(count, sqli=sqli, path=request.path, src_ip=src_ip)

    with stats_lock:
        total_requests += 1

    payload_size = len(query.encode())

    entry = _build_log_entry(
        username=query[:50] if query else "",
        success=False,
        attack_type=attack_type,
        start_time=t0,
        payload_size=payload_size,
        request_count=count,
    )
    # Extra field for the dashboard
    entry["query"] = query[:200]
    entry["sqli_detected"] = sqli
    _write_log(entry)

    results = None
    if query:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            # INTENTIONALLY VULNERABLE — no parameterised query!
            sql = f"SELECT id, name, department, salary, email FROM employees WHERE name LIKE '%{query}%'"
            c.execute(sql)
            results = c.fetchall()
        except Exception as e:
            results = [("ERROR", str(e), "", "", "")]
        finally:
            conn.close()

    return render_template_string(
        SEARCH_HTML,
        query=query,
        results=results,
        sqli_detected=sqli,
    )


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[*] CorpNet target server starting on http://0.0.0.0:{PORT}")
    print(f"[*] Logging to: {os.path.abspath(LOG_FILE)}")
    print(f"[*] Valid credentials: admin:secret123 | user:password | root:toor")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
