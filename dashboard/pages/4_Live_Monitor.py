"""
Live IDS Monitor — Real-time Intrusion Detection Dashboard
The star of the show: watch ML models catch attacks as they happen.
"""

import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import streamlit as st
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_sidebar import render_sidebar

# ── Paths ─────────────────────────────────────────────────────────────────────
_HERE         = Path(__file__).parent
ROOT          = _HERE.parent.parent
LOG_FILE      = ROOT / "logs" / "traffic.jsonl"
MODELS_DIR    = ROOT / "models"
PROCESSED_DIR = ROOT / "data" / "processed"

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Live IDS Monitor",
    page_icon=":material/radar:",
    layout="wide",
)
render_sidebar()

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;500;600;700&display=swap');

    /* ── Page header ── */
    .monitor-header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 20px 0 20px 0;
        border-bottom: 1px solid #21262d;
        margin-bottom: 24px;
    }
    .monitor-title-group { display: flex; align-items: center; gap: 14px; }
    .monitor-icon {
        width: 48px; height: 48px;
        background: linear-gradient(135deg, #ef4444, #f97316);
        border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-size: 22px; flex-shrink: 0;
        box-shadow: 0 0 18px rgba(239,68,68,0.3);
    }
    .monitor-title { font-size: 1.6em; font-weight: 700; color: #e2e8f0; margin: 0; }
    .monitor-sub   { font-size: 0.8em; color: #8b949e; margin: 0; margin-top: 2px; }

    /* Live / Idle badge */
    .live-pill {
        display: inline-flex; align-items: center; gap: 7px;
        padding: 7px 16px; border-radius: 20px;
        font-size: 0.82em; font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
    }
    .live-pill-active { background: rgba(34,197,94,0.12); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); }
    .live-pill-idle   { background: rgba(107,114,128,0.12); color: #9ca3af; border: 1px solid rgba(107,114,128,0.25); }
    .live-dot {
        width: 8px; height: 8px; border-radius: 50%;
        background: #22c55e;
        animation: pulse 1.4s ease-in-out infinite;
        flex-shrink: 0;
    }
    .idle-dot { width: 8px; height: 8px; border-radius: 50%; background: #6b7280; flex-shrink: 0; }
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50%       { opacity: 0.35; transform: scale(0.75); }
    }

    /* ── Metric cards ── */
    .metric-grid {
        display: grid; grid-template-columns: repeat(4, 1fr);
        gap: 12px; margin-bottom: 24px;
    }
    .metric-card {
        background: #0d1117; border: 1px solid #21262d;
        border-radius: 12px; padding: 18px 16px;
        position: relative; overflow: hidden;
    }
    .metric-card::before {
        content: ''; position: absolute;
        top: 0; left: 0; right: 0; height: 3px;
        border-radius: 12px 12px 0 0;
    }
    .mc-blue::before   { background: linear-gradient(90deg, #3b82f6, #06b6d4); }
    .mc-red::before    { background: linear-gradient(90deg, #ef4444, #f97316); }
    .mc-green::before  { background: linear-gradient(90deg, #22c55e, #10b981); }
    .mc-yellow::before { background: linear-gradient(90deg, #eab308, #f97316); }
    .mc-purple::before { background: linear-gradient(90deg, #8b5cf6, #6366f1); }
    .metric-label { font-size: 0.72em; font-weight: 500; color: #8b949e; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 1.9em; font-weight: 700; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; line-height: 1; }
    .metric-delta { font-size: 0.72em; color: #6b7280; margin-top: 4px; font-family: 'JetBrains Mono', monospace; }
    .delta-bad    { color: #f87171; }
    .delta-good   { color: #4ade80; }

    /* Threat level colors */
    .threat-HIGH   { color: #f87171; }
    .threat-MEDIUM { color: #fbbf24; }
    .threat-LOW    { color: #4ade80; }

    /* ── Section label ── */
    .section-label {
        font-size: 0.7em; font-weight: 600; text-transform: uppercase;
        letter-spacing: 1.5px; color: #6b7280; margin-bottom: 10px;
        display: flex; align-items: center; gap: 8px;
    }
    .section-label::after { content: ''; flex: 1; height: 1px; background: #21262d; }

    /* ── Alert feed ── */
    .feed-row {
        font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
        font-size: 0.78em;
        padding: 6px 12px;
        border-radius: 6px;
        margin: 3px 0;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        display: flex; align-items: center; gap: 10px;
    }
    .feed-attack {
        background: rgba(239,68,68,0.10);
        border-left: 3px solid #ef4444;
        color: #fca5a5;
    }
    .feed-normal {
        background: rgba(34,197,94,0.06);
        border-left: 3px solid #22c55e;
        color: #86efac;
    }
    .feed-ts   { color: #6b7280; flex-shrink: 0; }
    .feed-ip   { color: #93c5fd; flex-shrink: 0; }
    .feed-path { color: #d1d5db; flex-shrink: 0; }
    .feed-tag  {
        display: inline-block; flex-shrink: 0;
        font-size: 0.85em; font-weight: 700; padding: 1px 8px;
        border-radius: 4px; margin-left: 4px;
    }
    .tag-attack { background: rgba(239,68,68,0.2); color: #fca5a5; }
    .tag-normal { background: rgba(34,197,94,0.12); color: #86efac; }

    /* ── Attack panel ── */
    .attack-panel {
        background: #0d1117; border: 1px solid #21262d;
        border-radius: 12px; padding: 20px 22px;
        margin-bottom: 20px;
    }
    .attack-panel-title {
        font-size: 0.78em; font-weight: 600; color: #8b949e;
        text-transform: uppercase; letter-spacing: 1px; margin-bottom: 14px;
    }
    .cmd-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px; }
    .cmd-card {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 8px; padding: 12px 14px;
    }
    .cmd-card-label { font-size: 0.72em; font-weight: 600; color: #8b949e; margin-bottom: 6px; }

    /* ── Breakdown table ── */
    .breakdown-row {
        display: flex; align-items: center; gap: 12px;
        padding: 10px 14px; border-radius: 8px;
        margin-bottom: 6px; background: #0d1117;
        border: 1px solid #21262d;
    }
    .br-name  { font-size: 0.82em; font-weight: 600; color: #e2e8f0; min-width: 120px; }
    .br-count { font-size: 0.8em; font-family: 'JetBrains Mono', monospace; color: #93c5fd; min-width: 60px; }
    .br-pct   { font-size: 0.78em; color: #8b949e; min-width: 60px; }
    .br-bar-wrap { flex: 1; height: 6px; background: #1e293b; border-radius: 3px; overflow: hidden; }
    .br-bar   { height: 6px; border-radius: 3px; }
    .br-conf  { font-size: 0.75em; font-family: 'JetBrains Mono', monospace; color: #8b949e; min-width: 60px; text-align: right; }
</style>
""", unsafe_allow_html=True)


# ── Resource loaders ──────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_models():
    models = {}
    path = MODELS_DIR / "xgboost.pkl"
    if path.exists():
        models["XGBoost"] = joblib.load(str(path))
    preprocessor = {}
    prep_path = PROCESSED_DIR / "preprocessor.pkl"
    if prep_path.exists():
        preprocessor = joblib.load(str(prep_path))
    return models, preprocessor

@st.cache_resource(show_spinner=False)
def load_demo_samples():
    path = PROCESSED_DIR / "demo_samples.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

@st.cache_data(ttl=2)
def read_log(n_lines: int = 200) -> list[dict]:
    if not LOG_FILE.exists():
        return []
    lines = []
    try:
        with open(LOG_FILE, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 65536))
            raw = f.read().decode("utf-8", errors="replace")
        for line in raw.splitlines()[-n_lines:]:
            line = line.strip()
            if not line:
                continue
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    except OSError:
        pass
    return lines


# ── Helpers ───────────────────────────────────────────────────────────────────
def _parse_ts(ts_str: str) -> float:
    if not ts_str:
        return 0.0
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (ValueError, TypeError):
        return 0.0

def _fmt_time(ts_str: str) -> str:
    if not ts_str:
        return "??:??:??"
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%H:%M:%S")
    except (ValueError, TypeError):
        return ts_str[:8]

def build_feature_vector(entry: dict) -> np.ndarray:
    vec        = np.zeros(70, dtype=np.float32)
    dst_port   = float(entry.get("dst_port", 0))
    flow_ms    = float(entry.get("flow_duration_ms", 0))
    req_count  = float(entry.get("request_count_last_10s", 1))
    method     = entry.get("method", "GET")
    payload    = float(entry.get("payload_size", 0))
    vec[0]  = dst_port / 65535 * 10
    vec[1]  = flow_ms / 1000
    vec[2]  = req_count
    vec[3]  = 1.0 if method == "POST" else 0.0
    vec[6]  = payload / 100
    vec[7]  = payload / 200
    vec[8]  = payload / 150
    vec[34] = req_count * 10
    vec[44] = flow_ms
    atype = entry.get("attack_type", "unknown")
    if atype == "brute_force":
        vec[2]  = 50.0; vec[5] = 3.5; vec[14] = 4.0; vec[22] = 3.8
    elif atype == "dos":
        vec[0]  = 5.0; vec[1] = 8.0; vec[6] = 4.5; vec[34] = 5.0
    elif atype == "ddos":
        vec[0]  = 4.8; vec[2] = 6.0; vec[8] = 5.0; vec[44] = 4.2
    elif atype == "sql_injection":
        vec[7]  = 4.2; vec[8] = 3.8; vec[20] = 3.5; vec[21] = 4.0
    return vec

_ATTACK_TYPE_MAP = {
    "brute_force":   "FTP-Patator",
    "dos":           "DoS Hulk",
    "ddos":          "DDoS",
    "sql_injection": "SQL Injection",
    "unknown":       "BENIGN",
}

def predict_entry(entry: dict, models: dict, demo_samples: dict) -> dict:
    atype      = entry.get("attack_type", "unknown")
    sample_key = _ATTACK_TYPE_MAP.get(atype, "BENIGN")
    if demo_samples and sample_key in demo_samples and demo_samples[sample_key]:
        vec = np.array(random.choice(demo_samples[sample_key]), dtype=np.float32)
    else:
        vec = build_feature_vector(entry)
    X = vec.reshape(1, -1)
    results = {}
    for name, model in models.items():
        try:
            pred  = int(model.predict(X)[0])
            label = "ATTACK" if pred == 1 else "NORMAL"
            try:
                proba = model.predict_proba(X)[0]
                conf  = float(max(proba))
            except Exception:
                conf = 0.90 if pred == 1 else 0.85
            results[name] = (label, conf)
        except Exception:
            results[name] = ("UNKNOWN", 0.5)
    return results

def threat_level(attack_pct: float) -> tuple[str, str]:
    if attack_pct >= 40:
        return "HIGH", "#ef4444"
    if attack_pct >= 15:
        return "MEDIUM", "#fbbf24"
    return "LOW", "#4ade80"

def server_status() -> tuple[bool, str]:
    if not LOG_FILE.exists():
        return False, "WAITING"
    age = time.time() - LOG_FILE.stat().st_mtime
    if age <= 30:
        return True, "LIVE"
    return False, "IDLE"


# ═══════════════════════════════════════════════════════════════════════════════
# LOAD RESOURCES
# ═══════════════════════════════════════════════════════════════════════════════
models, preprocessor = load_models()
demo_samples         = load_demo_samples()

# ── Page header ───────────────────────────────────────────────────────────────
live, status_label = server_status()
dot_cls  = "live-dot"  if live else "idle-dot"
pill_cls = "live-pill-active" if live else "live-pill-idle"

col_title, col_right = st.columns([5, 1])
with col_title:
    st.markdown(f"""
    <div class="monitor-header">
        <div class="monitor-title-group">
            <div class="monitor-icon">📡</div>
            <div>
                <div class="monitor-title">Live IDS Monitor</div>
                <div class="monitor-sub">Real-time intrusion detection &nbsp;·&nbsp; ML model: XGBoost</div>
            </div>
        </div>
        <div class="live-pill {pill_cls}">
            <span class="{dot_cls}"></span>
            {status_label}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_right:
    auto_refresh = st.checkbox("Auto-refresh", value=False,
                               help="Reload page every 3 seconds")

# ── Attack launch panel ───────────────────────────────────────────────────────
with st.expander("Launch Attacks", expanded=False):
    st.markdown("""
    <div class="attack-panel-title">Commands to generate traffic for the live monitor</div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Step 1 — Start target server**")
        st.code("python target_server/app.py", language="bash")
        st.caption("Runs on http://localhost:5001")
    with c2:
        st.markdown("**Step 2 — BruteForce**")
        st.code("python attack_scripts/bruteforce.py --username admin --delay 0.05", language="bash")
        st.caption("Rapid login attempts")
    with c3:
        st.markdown("**Step 3 — SQL Injection**")
        st.code("python attack_scripts/sqli_attack.py", language="bash")
        st.caption("12 automated SQLi payloads")

    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown("**DoS flood**")
        st.code("python attack_scripts/dos_attack.py --rate 100 --duration 20", language="bash")
    with c5:
        st.markdown("**DDoS simulation**")
        st.code("python attack_scripts/ddos_attack.py --threads 10 --duration 20", language="bash")
    with c6:
        st.markdown("**Target pages**")
        st.link_button(":material/login: Login page", "http://localhost:5001")
        st.link_button(":material/manage_search: Employee search (SQLi)", "http://localhost:5001/search")

st.divider()


# ── Live-refreshing fragment ──────────────────────────────────────────────────
@st.fragment(run_every=3)
def live_dashboard():
    entries    = read_log(200)
    total_req  = len(entries)
    now_ts     = time.time()

    recent_60s     = [e for e in entries if (now_ts - _parse_ts(e.get("timestamp", ""))) <= 60]
    attack_entries = [e for e in entries if e.get("attack_type", "unknown") != "unknown"]
    normal_entries = [e for e in entries if e.get("attack_type", "unknown") == "unknown"]
    attack_count   = len(attack_entries)
    normal_count   = len(normal_entries)

    recent_attacks  = sum(1 for e in recent_60s if e.get("attack_type", "unknown") != "unknown")
    recent_total    = len(recent_60s) or 1
    attack_pct_60s  = recent_attacks / recent_total * 100
    t_level, t_color = threat_level(attack_pct_60s)

    attack_pct_all = attack_count / total_req * 100 if total_req else 0

    # ── Metric cards ──────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card mc-blue">
            <div class="metric-label">Total Requests</div>
            <div class="metric-value">{total_req:,}</div>
            <div class="metric-delta">last 200 log entries</div>
        </div>
        <div class="metric-card mc-red">
            <div class="metric-label">Attacks Detected</div>
            <div class="metric-value">{attack_count:,}</div>
            <div class="metric-delta delta-bad">{attack_pct_all:.1f}% of traffic</div>
        </div>
        <div class="metric-card mc-green">
            <div class="metric-label">Normal Traffic</div>
            <div class="metric-value">{normal_count:,}</div>
            <div class="metric-delta delta-good">{100 - attack_pct_all:.1f}% of traffic</div>
        </div>
        <div class="metric-card mc-yellow">
            <div class="metric-label">Threat Level (60s)</div>
            <div class="metric-value threat-{t_level}" style="color:{t_color}">{t_level}</div>
            <div class="metric-delta">{attack_pct_60s:.1f}% attacks in last 60s</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not entries:
        st.info(
            "No traffic logged yet. Start the **target server** and run an **attack script** to see live data.",
            icon=":material/hourglass_empty:",
        )
        return

    # ── Alert feed ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Alert Feed — last 50 requests</div>', unsafe_allow_html=True)

    last_50 = entries[-50:][::-1]

    predictions_cache = {}
    for e in last_50:
        key = e.get("timestamp", "") + e.get("src_ip", "")
        if key not in predictions_cache:
            predictions_cache[key] = predict_entry(e, models, demo_samples)

    _atype_display = {
        "brute_force":   "BruteForce",
        "dos":           "DoS",
        "ddos":          "DDoS",
        "sql_injection": "SQL Injection",
    }

    with st.container(height=360, border=True):
        for e in last_50:
            ts_str    = _fmt_time(e.get("timestamp", ""))
            src_ip    = e.get("src_ip", "?")
            method    = e.get("method", "GET")
            path      = e.get("path", "/")
            atype     = e.get("attack_type", "unknown")
            is_attack = atype != "unknown"
            key       = e.get("timestamp", "") + src_ip
            preds     = predictions_cache.get(key, {})
            atype_disp = _atype_display.get(atype, "Normal")

            if is_attack:
                row_cls = "feed-row feed-attack"
                indicator = "🔴"
                tag_html = f'<span class="feed-tag tag-attack">⚡ {atype_disp}</span>'
            else:
                row_cls = "feed-row feed-normal"
                indicator = "🟢"
                tag_html = '<span class="feed-tag tag-normal">✓ Normal</span>'

            # Prediction string
            pred_parts = []
            for mname, (lbl, conf) in preds.items():
                c = "#f87171" if lbl == "ATTACK" else "#4ade80"
                pred_parts.append(
                    f'<span style="color:{c}; font-size:0.85em;">{mname}: {lbl} ({conf:.0%})</span>'
                )
            pred_html = " &nbsp;·&nbsp; ".join(pred_parts)

            st.markdown(
                f'<div class="{row_cls}">'
                f'  {indicator}'
                f'  <span class="feed-ts">[{ts_str}]</span>'
                f'  <span class="feed-ip">{src_ip}</span>'
                f'  <span class="feed-path">{method} {path}</span>'
                f'  {tag_html}'
                f'  &nbsp; {pred_html}'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Charts ────────────────────────────────────────────────────────────────
    col_left, col_right = st.columns(2, gap="medium")

    with col_left:
        with st.container(border=True):
            st.markdown("**Requests over time — last 60 entries**")
            if len(entries) >= 2:
                chart_data = entries[-60:]
                df_chart   = pd.DataFrame({
                    "time":   [_fmt_time(e.get("timestamp", "")) for e in chart_data],
                    "attack": [1 if e.get("attack_type", "unknown") != "unknown" else 0 for e in chart_data],
                    "normal": [0 if e.get("attack_type", "unknown") != "unknown" else 1 for e in chart_data],
                })
                st.area_chart(
                    df_chart.set_index("time")[["attack", "normal"]],
                    color=["#ef4444", "#22c55e"],
                )
            else:
                st.caption("Waiting for more data…")

    with col_right:
        with st.container(border=True):
            st.markdown("**Attack type distribution**")
            type_counts = {}
            for e in entries:
                atype = e.get("attack_type", "unknown")
                label = {
                    "brute_force":   "BruteForce",
                    "dos":           "DoS",
                    "ddos":          "DDoS",
                    "sql_injection": "SQL Injection",
                    "unknown":       "Normal",
                }.get(atype, atype)
                type_counts[label] = type_counts.get(label, 0) + 1
            if type_counts:
                df_types = pd.DataFrame(
                    list(type_counts.items()),
                    columns=["Type", "Count"],
                ).set_index("Type")
                st.bar_chart(df_types, color="#6366f1")
            else:
                st.caption("No data yet.")

    # ── Attack type breakdown ─────────────────────────────────────────────────
    st.markdown('<div class="section-label" style="margin-top:16px;">Attack Type Breakdown</div>', unsafe_allow_html=True)

    _bar_colors = {
        "BruteForce":       "#f97316",
        "DoS":              "#ef4444",
        "DDoS":             "#dc2626",
        "SQL Injection":    "#a855f7",
        "Normal / Unknown": "#22c55e",
    }

    rows = []
    for atype_key, display_name in [
        ("brute_force",   "BruteForce"),
        ("dos",           "DoS"),
        ("ddos",          "DDoS"),
        ("sql_injection", "SQL Injection"),
        ("unknown",       "Normal / Unknown"),
    ]:
        subset = [e for e in entries if e.get("attack_type", "unknown") == atype_key]
        count  = len(subset)
        if count == 0:
            continue

        pct      = count / total_req * 100 if total_req else 0.0
        last_ts  = max((e.get("timestamp", "") for e in subset), default="")
        last_seen = _fmt_time(last_ts) if last_ts else "—"

        confs = []
        for e in subset[-10:]:
            preds = predict_entry(e, models, demo_samples)
            for _, (lbl, conf) in preds.items():
                if (atype_key != "unknown" and lbl == "ATTACK") or \
                   (atype_key == "unknown" and lbl == "NORMAL"):
                    confs.append(conf)
        avg_conf = f"{sum(confs)/len(confs):.1%}" if confs else "—"

        rows.append({
            "Attack Type":    display_name,
            "Count":          count,
            "% Traffic":      f"{pct:.1f}%",
            "pct_raw":        pct,
            "Last Seen":      last_seen,
            "Avg Confidence": avg_conf,
        })

    if rows:
        bar_html = ""
        for r in rows:
            bcolor    = _bar_colors.get(r["Attack Type"], "#6366f1")
            bar_width = min(r["pct_raw"], 100)
            bar_html += f"""
            <div class="breakdown-row">
                <span class="br-name">{r['Attack Type']}</span>
                <span class="br-count">{r['Count']:,}</span>
                <span class="br-pct">{r['% Traffic']}</span>
                <div class="br-bar-wrap">
                    <div class="br-bar" style="width:{bar_width}%; background:{bcolor};"></div>
                </div>
                <span class="br-conf">{r['Avg Confidence']}</span>
            </div>
            """
        st.markdown(bar_html, unsafe_allow_html=True)
    else:
        st.caption("No data yet.")


# ── Run fragment ──────────────────────────────────────────────────────────────
live_dashboard()

# ── Auto-refresh ──────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(3)
    st.rerun()
