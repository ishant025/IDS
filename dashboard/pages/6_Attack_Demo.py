"""
Attack Demo Lab — Live attack demonstration using real CIC-IDS2017 samples.
Demonstrates BruteForce, DoS, DDoS, SQLi attacks with actual model predictions.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
import joblib, json, sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_sidebar import render_sidebar

st.set_page_config(
    page_title="Attack Demo Lab",
    page_icon=":material/security:",
    layout="wide",
)
render_sidebar()

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;500;600;700&display=swap');

    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #0d1117 60%, #0a0e27 100%);
        font-family: 'Inter', sans-serif;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border-right: 1px solid #21262d;
    }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    [data-testid="stHeader"] { background: transparent; }

    /* ── Page header ── */
    .demo-header {
        display: flex; align-items: center; gap: 16px;
        padding: 24px 0 20px 0;
        border-bottom: 1px solid #21262d;
        margin-bottom: 24px;
    }
    .demo-header-icon {
        width: 52px; height: 52px;
        background: linear-gradient(135deg, #8b5cf6, #6366f1);
        border-radius: 14px;
        display: flex; align-items: center; justify-content: center;
        font-size: 24px; flex-shrink: 0;
        box-shadow: 0 0 20px rgba(139,92,246,0.3);
    }
    .demo-header-title  { font-size: 1.7em; font-weight: 700; color: #e2e8f0; margin: 0; }
    .demo-header-sub    { font-size: 0.82em; color: #8b949e; margin: 0; margin-top: 3px; }

    /* ── Section label ── */
    .section-label {
        font-size: 0.70em; font-weight: 600; text-transform: uppercase;
        letter-spacing: 1.5px; color: #6b7280; margin: 20px 0 12px 0;
        display: flex; align-items: center; gap: 8px;
    }
    .section-label::after { content: ''; flex: 1; height: 1px; background: #21262d; }

    /* ── Status banner ── */
    .status-online {
        display: flex; align-items: center; gap: 10px;
        background: rgba(34,197,94,0.08);
        border: 1px solid rgba(34,197,94,0.25);
        border-radius: 10px; padding: 10px 16px;
        font-size: 0.82em; color: #4ade80;
        font-family: 'JetBrains Mono', monospace;
        margin-bottom: 20px;
    }
    .status-dot-green {
        width: 8px; height: 8px; border-radius: 50%;
        background: #22c55e; flex-shrink: 0;
        animation: pulse 1.4s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50%       { opacity: 0.35; transform: scale(0.75); }
    }

    /* ── Attack selector pills ── */
    .attack-selector-label {
        font-size: 0.78em; font-weight: 600; color: #8b949e;
        text-transform: uppercase; letter-spacing: 1px;
        margin-bottom: 10px;
    }

    /* ── Attack overview panel ── */
    .attack-overview {
        background: #0d1117; border: 1px solid #21262d;
        border-radius: 12px; padding: 22px 24px;
        margin-bottom: 20px; position: relative; overflow: hidden;
    }
    .attack-overview::before {
        content: ''; position: absolute;
        top: 0; left: 0; right: 0; height: 3px;
        border-radius: 12px 12px 0 0;
    }
    .ao-red::before    { background: linear-gradient(90deg, #ef4444, #f97316); }
    .ao-green::before  { background: linear-gradient(90deg, #22c55e, #10b981); }
    .ao-purple::before { background: linear-gradient(90deg, #8b5cf6, #6366f1); }
    .attack-name   { font-size: 1.3em; font-weight: 700; color: #e2e8f0; margin-bottom: 6px; }
    .attack-tagline { font-size: 0.85em; color: #94a3b8; margin-bottom: 12px; }
    .sev-badge {
        display: inline-block; font-size: 0.7em; font-weight: 700;
        font-family: 'JetBrains Mono', monospace; text-transform: uppercase;
        padding: 3px 10px; border-radius: 4px; letter-spacing: 0.5px;
    }
    .sev-none     { background: rgba(34,197,94,0.15);   color: #4ade80;  border: 1px solid rgba(34,197,94,0.3); }
    .sev-high     { background: rgba(249,115,22,0.15);  color: #fdba74;  border: 1px solid rgba(249,115,22,0.3); }
    .sev-critical { background: rgba(239,68,68,0.15);   color: #fca5a5;  border: 1px solid rgba(239,68,68,0.3); }

    /* ── Feature highlight table ── */
    .feat-table {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 10px; padding: 16px;
    }
    .feat-title {
        font-size: 0.72em; font-weight: 600; color: #6b7280;
        text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;
    }
    .feat-row {
        display: flex; align-items: flex-start; gap: 10px;
        padding: 6px 0; border-bottom: 1px solid #21262d;
    }
    .feat-row:last-child { border-bottom: none; }
    .feat-key {
        font-size: 0.75em; font-family: 'JetBrains Mono', monospace;
        color: #93c5fd; flex: 1; min-width: 0;
    }
    .feat-val { font-size: 0.75em; color: #d1d5db; flex: 1.4; text-align: right; }

    /* ── Story panel ── */
    .story-panel {
        background: #0d1117; border: 1px solid #21262d;
        border-radius: 12px; padding: 22px 24px;
        margin-bottom: 20px;
    }
    .story-panel-title {
        font-size: 0.72em; font-weight: 600; color: #6b7280;
        text-transform: uppercase; letter-spacing: 1px; margin-bottom: 14px;
    }

    /* ── SQLi live section ── */
    .sqli-panel {
        background: #0d1117; border: 1px solid rgba(168,85,247,0.3);
        border-radius: 12px; padding: 22px 24px; margin-bottom: 20px;
    }
    .sqli-title {
        font-size: 0.82em; font-weight: 700; color: #c4b5fd; margin-bottom: 14px;
    }
    .payload-row {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 6px; padding: 8px 12px; margin-bottom: 8px;
    }
    .payload-code {
        font-family: 'JetBrains Mono', monospace; font-size: 0.82em;
        color: #f87171; margin-bottom: 4px;
    }
    .payload-desc { font-size: 0.72em; color: #8b949e; }

    /* ── Verdict banner ── */
    .verdict-attack {
        background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.35);
        border-radius: 12px; padding: 20px 24px; margin-bottom: 16px;
        text-align: center;
    }
    .verdict-normal {
        background: rgba(34,197,94,0.08); border: 1px solid rgba(34,197,94,0.25);
        border-radius: 12px; padding: 20px 24px; margin-bottom: 16px;
        text-align: center;
    }
    .verdict-icon  { font-size: 2.2em; display: block; margin-bottom: 6px; }
    .verdict-label { font-size: 1.5em; font-weight: 700; }
    .verdict-sub   { font-size: 0.82em; color: #94a3b8; margin-top: 4px; }

    /* ── Model cards ── */
    .model-card {
        background: #0d1117; border: 1px solid #21262d;
        border-radius: 10px; padding: 16px;
    }
    .model-card-name { font-size: 0.82em; font-weight: 700; color: #94a3b8; margin-bottom: 8px; }
    .model-verdict-attack { color: #f87171; font-weight: 700; font-size: 1em; }
    .model-verdict-normal { color: #4ade80; font-weight: 700; font-size: 1em; }
    .prob-bar-wrap { height: 6px; background: #1e293b; border-radius: 3px; margin-top: 8px; overflow: hidden; }
    .prob-bar { height: 6px; border-radius: 3px; }

    /* ── History table ── */
    .history-section {
        background: #0d1117; border: 1px solid #21262d;
        border-radius: 12px; padding: 20px 22px; margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ── Paths ─────────────────────────────────────────────────────────────────────
MODELS_DIR    = Path(__file__).parent.parent.parent / "models"
PROCESSED_DIR = Path(__file__).parent.parent.parent / "data" / "processed"
SAMPLES_PATH  = PROCESSED_DIR / "demo_samples.json"

# ── Load models & config ──────────────────────────────────────────────────────
@st.cache_resource
def load_resources():
    models          = {}
    label_mapping   = {0: "Normal", 1: "Attack"}
    feature_columns = []

    prep_path = PROCESSED_DIR / "preprocessor.pkl"
    if prep_path.exists():
        prep            = joblib.load(str(prep_path))
        label_mapping   = prep.get("label_mapping", label_mapping)
        feature_columns = prep.get("feature_columns", [])

    p = MODELS_DIR / "xgboost.pkl"
    if p.exists():
        models["XGBoost"] = joblib.load(str(p))

    samples = {}
    if SAMPLES_PATH.exists():
        with open(SAMPLES_PATH) as f:
            samples = json.load(f)

    return models, label_mapping, feature_columns, samples

models, label_mapping, feature_columns, demo_samples = load_resources()

# ── Attack catalogue ──────────────────────────────────────────────────────────
ATTACKS = {
    "Normal Traffic": {
        "sample_key": "BENIGN",
        "color":      "green",
        "severity":   "None",
        "tagline":    "Legitimate web-browsing traffic — model should say Normal.",
        "story": """
**Scenario:** A user opens a browser and visits `https://example.com`.

The browser establishes a short TCP connection to port 443, performs a TLS handshake,
downloads the page (~1.4 KB), and closes the connection cleanly with FIN/ACK.

**Traffic fingerprint:**
- Flow duration ≈ 150 ms
- ~35 packets/second, balanced in both directions
- Destination port 443 (HTTPS)
- Normal packet sizes (~400 B request, ~1 400 B response)

The model sees nothing unusual — all 70 features fall well within the distribution
it learned from normal traffic during training.
""",
        "features_highlight": {
            "Flow Duration":    "Short (~150 ms) ✅",
            "Fwd Packet Rate":  "~35 pkts/s ✅",
            "Bwd / Fwd ratio":  "~0.9 (balanced) ✅",
            "Destination Port": "443 (HTTPS) ✅",
            "TCP Flags":        "SYN + ACK + FIN ✅",
        },
    },
    "Brute Force — FTP": {
        "sample_key": "FTP-Patator",
        "color":      "red",
        "severity":   "High",
        "tagline":    "Automated password-guessing attack against an FTP server.",
        "story": """
**Scenario:** Attacker runs `patator ftp_login host=192.168.1.10 user=FILE0 password=FILE1`
using a wordlist of 10 000 common passwords.

**What happens step by step:**
1. Patator opens a TCP connection to **port 21** (FTP)
2. Server: `220 FTP Server Ready`
3. Attacker sends: `USER admin`
4. Server: `331 Password required`
5. Attacker sends: `PASS <guess>`
6. Server: `530 Login incorrect` → connection closed
7. **Repeat 10 000 times** — ~180 attempts per minute

After 840 attempts, credential `admin : ftp123` is found → full FTP access obtained.

**Why the model catches it:**
Each micro-flow has identical structure (same byte count, same port, same duration).
The extreme **connection rate to port 21** from one source IP, combined with uniform
packet lengths, is a textbook brute-force signature in the CIC-IDS2017 dataset.
""",
        "features_highlight": {
            "Destination Port": "21 (FTP) 🔴",
            "Connections/min":  "~180 (automated) 🔴",
            "Flow Duration":    "~1–3 s each",
            "Fwd Bytes":        "~300 B (USER+PASS payload)",
            "Bwd Bytes":        "~300 B (530 error reply)",
        },
    },
    "Brute Force — SSH": {
        "sample_key": "SSH-Patator",
        "color":      "red",
        "severity":   "High",
        "tagline":    "Automated credential stuffing attack against SSH (port 22).",
        "story": """
**Scenario:** Attacker runs `hydra -l root -P rockyou.txt ssh://192.168.1.10`

**What happens step by step:**
1. Hydra opens a TCP connection to **port 22** (SSH)
2. SSH key exchange takes place (~3 packets)
3. Attacker sends authentication request with `root` + `<guessed password>`
4. Server replies: `Permission denied` → connection closed
5. **Repeat 450 times per minute** — fully automated, no human delay

After 2 300 attempts, `root : password123` succeeds → root shell obtained.

**Why the model catches it:**
SSH auth flows are slightly larger than FTP (SSH handshake overhead ≈ 900 B).
The model flags: destination port 22, high connection frequency,
very **uniform inter-arrival time** (bots don't pause like humans do),
and repeated incomplete handshake patterns from a single source IP.
""",
        "features_highlight": {
            "Destination Port":  "22 (SSH) 🔴",
            "Connections/min":   "~450 (automated) 🔴",
            "Inter-flow time":   "Very uniform (bot, not human) 🔴",
            "Fwd Packet Length": "~900 B (SSH handshake overhead)",
            "TCP Flags":         "SYN repeated, no FIN 🔴",
        },
    },
    "DoS — HTTP Flood (Hulk)": {
        "sample_key": "DoS Hulk",
        "color":      "red",
        "severity":   "Critical",
        "tagline":    "Single-machine HTTP flood that exhausts the web server in seconds.",
        "story": """
**Scenario:** Attacker runs the **HULK** tool targeting `http://victim.local:80`

**What happens step by step:**
1. HULK generates a **unique URL per request** (e.g. `/?id=a3f9b2`) to bypass caching
2. Sends **15 400 HTTP GET requests per second** from one machine
3. Each request has a randomised `User-Agent` and `Referer` header
4. Server threads all blocked waiting for responses → CPU hits 100% in 8 s
5. Legitimate users start getting `503 Service Unavailable`

**Why the model catches it:**
Extreme **forward packet rate** (>3 standard deviations above the mean).
The fwd/bwd packet ratio is heavily skewed — almost **no responses** come back
because the server is overwhelmed. Flow duration is abnormally long for port-80.
These three features together strongly push the classifier into the Attack region.
""",
        "features_highlight": {
            "Flow Duration":    "~98 s (extreme for HTTP) 🔴",
            "Fwd Packet Rate":  "15 400 pkts/s 🔴",
            "Bwd / Fwd ratio":  "~0.01 (server overwhelmed) 🔴",
            "Destination Port": "80 (HTTP) 🔴",
            "Flow Bytes/s":     ">2.5 MB/s 🔴",
        },
    },
    "SQL Injection": {
        "sample_key": "SQL Injection",
        "color":      "red",
        "severity":   "Critical",
        "tagline":    "Injects malicious SQL into a web form to bypass auth and dump the database.",
        "try_live":   True,
        "live_url":   "http://localhost:5001/search",
        "live_cmd":   "python attack_scripts/sqli_attack.py",
        "payloads": [
            ("' OR '1'='1",                                               "Basic auth bypass — always-true condition"),
            ("' OR '1'='1' --",                                           "Bypass + comment out rest of query"),
            ("' UNION SELECT id,name,department,salary,email FROM employees --", "Dump entire employees table"),
            ("'; DROP TABLE employees; --",                               "Destructive — delete all data"),
        ],
        "story": """
**Scenario:** Attacker opens `http://localhost:5001/search` — CorpNet's Employee Directory.

The search box takes a name and runs this SQL query behind the scenes:
```sql
SELECT * FROM employees WHERE name LIKE '%<your input>%'
```
Because the developer **did not sanitise the input**, an attacker can break out of the
string and inject their own SQL commands.

**Step-by-step attack:**
1. Attacker types `' OR '1'='1` in the search box
2. The SQL becomes: `SELECT * FROM employees WHERE name LIKE '%' OR '1'='1%'`
3. Since `'1'='1'` is **always true**, every row matches
4. All 6 employee records are returned — including salaries and emails!
5. Next payload: `' UNION SELECT ...` dumps the entire table structure

**Why the model catches it:**
SQL injection payloads make the HTTP request **payload larger and byte-pattern anomalous**
compared to a normal name search. Features like `Fwd Packet Length Max` and
`Bwd Packet Length` deviate significantly from benign web traffic.
""",
        "features_highlight": {
            "Fwd Packet Length": "High & variable (long SQLi payload) 🔴",
            "Bwd Packet Length": "Very large (full DB dump response) 🔴",
            "Destination Port":  "5001 / 80 (web server)",
            "Payload pattern":   "SQL keywords: OR, UNION, SELECT 🔴",
            "Flow asymmetry":    "Large response vs small request 🔴",
        },
    },
    "DDoS — UDP / LOIT Flood": {
        "sample_key": "DDoS",
        "color":      "red",
        "severity":   "Critical",
        "tagline":    "Distributed flood from hundreds of bots — saturates the network link.",
        "story": """
**Scenario:** Attacker activates a **200-node botnet** targeting `192.168.1.1:80`

**What happens step by step:**
1. Command sent to all bots: `START_FLOOD 192.168.1.1 80`
2. Each bot sends maximum-size packets continuously (TCP/UDP mix)
3. Total inbound traffic: **~4.8 Gbps** — far beyond the victim's link capacity
4. Victim's network interface card drops packets → entire server becomes unreachable
5. Attack sustained for 90 seconds — takedown complete

**Why the model catches it:**
Unlike DoS (single source), DDoS shows **many source IPs** sending coordinated traffic.
Each individual flow looks semi-normal, but the **aggregate pattern** —
zero backward packets (fire-and-forget), very high flow bytes/s,
and large total forward bytes — matches the DDoS cluster in the training data.
""",
        "features_highlight": {
            "Bwd Packets":      "~0 (no server replies) 🔴",
            "Flow Bytes/s":     "Extremely high 🔴",
            "Total Fwd Bytes":  "Very large 🔴",
            "Source IPs":       "200 unique bots 🔴",
            "Destination Port": "80 (HTTP target)",
        },
    },
}

_SEV_CLASS = {"None": "sev-none", "High": "sev-high", "Critical": "sev-critical"}
_OV_CLASS  = {"None": "ao-green", "High": "ao-red", "Critical": "ao-red"}


# ── Prediction helpers ────────────────────────────────────────────────────────
def predict_sample(feature_vector: list) -> dict:
    X = np.array(feature_vector).reshape(1, -1)
    results = {}
    for name, model in models.items():
        pred = int(model.predict(X)[0])
        try:
            proba       = model.predict_proba(X)[0]
            attack_prob = float(proba[1]) if len(proba) > 1 else float(pred)
            confidence  = float(max(proba))
        except Exception:
            attack_prob = float(pred)
            confidence  = 1.0
        results[name] = {
            "prediction":  pred,
            "label":       label_mapping.get(pred, "Attack" if pred == 1 else "Normal"),
            "attack_prob": attack_prob,
            "confidence":  confidence,
        }
    return results

def feature_bar_chart(vector: list):
    feat_names = feature_columns if feature_columns else [f"F{i}" for i in range(len(vector))]
    vals = np.array(vector[:len(feat_names)])
    fig  = go.Figure(go.Bar(
        x=feat_names, y=vals,
        marker=dict(
            color=vals, colorscale="RdBu_r", cmin=-4, cmax=4,
            showscale=True,
            colorbar=dict(
                title=dict(text="Scaled value", font=dict(color="#8b949e")),
                thickness=12,
                tickfont=dict(color="#8b949e"),
            ),
        ),
    ))
    fig.update_layout(
        xaxis=dict(
            tickangle=45,
            tickfont=dict(size=8, color="#8b949e"),
            title=dict(text="Feature", font=dict(color="#8b949e")),
        ),
        yaxis=dict(
            title=dict(text="Scaled value", font=dict(color="#8b949e")),
            tickfont=dict(color="#8b949e"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,17,23,0.8)",
        height=300,
        margin=dict(l=10, r=10, t=10, b=130),
    )
    return fig

def confidence_bars(results: dict):
    names  = list(results.keys())
    probs  = [results[n]["attack_prob"] for n in names]
    colors = ["#ef4444" if p >= 0.5 else "#22c55e" for p in probs]
    labels = [f"{p:.1%}  {'ATTACK' if p >= 0.5 else 'Normal'}" for p in probs]
    fig = go.Figure(go.Bar(
        y=names, x=probs, orientation="h",
        marker_color=colors,
        text=labels, textposition="outside",
        textfont=dict(color="#e2e8f0"),
        cliponaxis=False,
    ))
    fig.add_vline(x=0.5, line_dash="dash", line_color="rgba(255,255,255,0.25)",
                  annotation_text="decision boundary",
                  annotation_font_color="#8b949e",
                  annotation_position="top right")
    fig.update_layout(
        xaxis=dict(
            range=[0, 1.25],
            tickformat=".0%",
            title=dict(text="Attack probability →", font=dict(color="#8b949e")),
            tickfont=dict(color="#8b949e"),
        ),
        yaxis=dict(
            title=dict(text=""),
            tickfont=dict(color="#e2e8f0"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,17,23,0.8)",
        height=55 * len(results) + 80,
        margin=dict(l=10, r=110, t=20, b=30),
        showlegend=False,
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# PAGE LAYOUT
# ══════════════════════════════════════════════════════════════════════════════

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="demo-header">
    <div class="demo-header-icon">🎯</div>
    <div>
        <div class="demo-header-title">Attack Demo Lab</div>
        <div class="demo-header-sub">Real samples from CIC-IDS2017 · Select an attack · Watch the model detect it live</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Guard: models & samples ───────────────────────────────────────────────────
if not models:
    st.error("No trained models found. Run `python run_pipeline.py` first.", icon=":material/error:")
    st.stop()

if not demo_samples:
    st.error("Demo samples not found. Run the pipeline to generate `demo_samples.json`.", icon=":material/error:")
    st.stop()

# ── Online status ─────────────────────────────────────────────────────────────
model_list = ", ".join(models.keys())
st.markdown(f"""
<div class="status-online">
    <span class="status-dot-green"></span>
    Models online: {model_list} &nbsp;·&nbsp; Dataset: CIC-IDS2017 &nbsp;·&nbsp; Samples: real traffic
</div>
""", unsafe_allow_html=True)

# ── Step 1: Attack selector ───────────────────────────────────────────────────
st.markdown('<div class="section-label">Step 1 — Choose an Attack</div>', unsafe_allow_html=True)

attack_names = list(ATTACKS.keys())
selected = st.pills(
    "attack_selector",
    attack_names,
    default=attack_names[0],
    label_visibility="collapsed",
)

attack      = ATTACKS[selected]
sample_pool = demo_samples.get(attack["sample_key"], [])
sev         = attack["severity"]
sev_cls     = _SEV_CLASS.get(sev, "sev-high")
ov_cls      = _OV_CLASS.get(sev, "ao-red")

# ── Step 2: Attack overview ───────────────────────────────────────────────────
st.markdown('<div class="section-label">Step 2 — Attack Overview</div>', unsafe_allow_html=True)

col_overview, col_features = st.columns([3, 2], gap="medium")

with col_overview:
    st.markdown(f"""
    <div class="attack-overview {ov_cls}">
        <div class="attack-name">{selected}</div>
        <div class="attack-tagline">{attack['tagline']}</div>
        <span class="sev-badge {sev_cls}">Severity: {sev}</span>
    </div>
    """, unsafe_allow_html=True)

    # Story — use native st.markdown for the body (supports code blocks etc.)
    st.markdown(
        '<div class="story-panel-title" style="font-size:0.72em;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">What is the attacker doing?</div>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown(attack["story"])

with col_features:
    feat_rows_html = ""
    for feat, val in attack["features_highlight"].items():
        feat_rows_html += f"""
        <div class="feat-row">
            <span class="feat-key">{feat}</span>
            <span class="feat-val">{val}</span>
        </div>
        """
    st.markdown(
        f"""
        <div class="feat-table">
            <div class="feat-title">Traffic characteristics flagged by model</div>
            {feat_rows_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── SQLi live section ──────────────────────────────────────────────────────────
if attack.get("try_live"):
    st.markdown('<div class="section-label">Step 3 — Try it Live (SQL Injection)</div>', unsafe_allow_html=True)

    with st.container(border=True):
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("**Option A — Manual in browser**")
            st.link_button(
                ":material/open_in_new: Open Employee Search page",
                attack["live_url"],
                type="primary",
            )
            st.caption("Copy-paste these payloads into the search box:")
            for payload, desc in attack["payloads"]:
                st.code(payload, language=None)
                st.caption(f"↳ {desc}")
        with c2:
            st.markdown("**Option B — Automated script**")
            st.code(attack["live_cmd"], language="bash")
            st.caption("Fires all 12 SQLi payloads and prints results. Watch Live Monitor for alerts!")
            st.info(
                "Make sure target server is running: `python target_server/app.py`",
                icon=":material/info:",
            )

    sim_step_label = "Step 4 — Simulate & Detect"
else:
    sim_step_label = "Step 3 — Simulate the Attack"

# ── Simulation ────────────────────────────────────────────────────────────────
st.markdown(f'<div class="section-label">{sim_step_label}</div>', unsafe_allow_html=True)

if not sample_pool:
    st.warning(f"No samples loaded for `{attack['sample_key']}` — check demo_samples.json.", icon=":material/warning:")
    st.stop()

col_btn, col_info = st.columns([1, 3], gap="medium")
with col_btn:
    simulate = st.button(
        ":material/play_arrow: Run Simulation",
        type="primary",
        width="stretch",
    )
with col_info:
    st.caption(
        f"Each click picks a **real packet** from {len(sample_pool):,} verified "
        f"`{attack['sample_key']}` samples in CIC-IDS2017 "
        f"and runs it through {len(models)} trained model(s)."
    )

# ── Session history ────────────────────────────────────────────────────────────
history_key = f"history_{selected}"
if history_key not in st.session_state:
    st.session_state[history_key] = []

if simulate:
    idx     = np.random.randint(0, len(sample_pool))
    vector  = sample_pool[idx]
    results = predict_sample(vector)
    attack_votes = sum(1 for r in results.values() if r["prediction"] == 1)
    verdict      = "Attack" if attack_votes >= len(results) / 2 else "Normal"
    st.session_state[history_key].insert(0, {
        "sample_idx":   idx,
        "vector":       vector,
        "results":      results,
        "verdict":      verdict,
        "attack_votes": attack_votes,
        "total_models": len(results),
    })
    st.session_state[history_key] = st.session_state[history_key][:10]

# ── Latest result ─────────────────────────────────────────────────────────────
if st.session_state[history_key]:
    latest       = st.session_state[history_key][0]
    results      = latest["results"]
    verdict      = latest["verdict"]
    attack_votes = latest["attack_votes"]
    total_models = latest["total_models"]
    is_attack    = verdict == "Attack"

    # Verdict banner
    if is_attack:
        st.markdown(f"""
        <div class="verdict-attack">
            <span class="verdict-icon">🚨</span>
            <span class="verdict-label" style="color:#f87171;">ATTACK DETECTED</span>
            <div class="verdict-sub">Sample #{latest['sample_idx']} · {attack_votes}/{total_models} models flagged</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="verdict-normal">
            <span class="verdict-icon">✅</span>
            <span class="verdict-label" style="color:#4ade80;">NORMAL TRAFFIC</span>
            <div class="verdict-sub">Sample #{latest['sample_idx']} · {attack_votes}/{total_models} models flagged</div>
        </div>
        """, unsafe_allow_html=True)

    # Confidence bars chart
    st.markdown("**Model Confidence Breakdown**")
    st.plotly_chart(confidence_bars(results), width="stretch")

    # Per-model cards
    model_cols = st.columns(len(results))
    for col, (mname, res) in zip(model_cols, results.items()):
        is_atk    = res["prediction"] == 1
        bar_color = "#ef4444" if is_atk else "#22c55e"
        verdict_cls = "model-verdict-attack" if is_atk else "model-verdict-normal"
        verdict_txt = res["label"]
        icon = "🔴" if is_atk else "🟢"
        prob_pct = int(res["attack_prob"] * 100)
        with col:
            st.markdown(f"""
            <div class="model-card">
                <div class="model-card-name">{mname}</div>
                <div class="{verdict_cls}">{icon} {verdict_txt}</div>
                <div style="font-size:0.72em; color:#8b949e; margin-top:4px; font-family:'JetBrains Mono',monospace;">
                    attack prob: {res['attack_prob']:.1%}
                </div>
                <div class="prob-bar-wrap">
                    <div class="prob-bar" style="width:{prob_pct}%; background:{bar_color};"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Feature vector heatmap
    with st.expander(":material/bar_chart: Raw feature vector (70 scaled values)", expanded=False):
        st.caption("Red bars = high anomaly values that pushed the model toward Attack. Blue = below normal mean.")
        st.plotly_chart(feature_bar_chart(latest["vector"]), width="stretch")

    # History table
    if len(st.session_state[history_key]) > 1:
        st.markdown('<div class="section-label" style="margin-top:20px;">Session History</div>', unsafe_allow_html=True)
        hist_rows = []
        for h in st.session_state[history_key]:
            row = {
                "Sample #": h["sample_idx"],
                "Verdict":  h["verdict"],
                "Votes":    f"{h['attack_votes']}/{h['total_models']}",
            }
            for mname, res in h["results"].items():
                row[mname] = f"{res['attack_prob']:.1%}"
            hist_rows.append(row)

        hist_df = pd.DataFrame(hist_rows)

        def color_verdict(val):
            return "color: #f87171; font-weight:bold" if val == "Attack" else "color: #4ade80;"

        st.dataframe(
            hist_df.style.map(color_verdict, subset=["Verdict"]),
            hide_index=True,
            width="stretch",
        )
        if st.button(":material/delete: Clear history"):
            st.session_state[history_key] = []
            st.rerun()

else:
    st.info(
        "Click **Run Simulation** to pick a real packet from the dataset and see the model predict it.",
        icon=":material/info:",
    )

# ── Comparison table ──────────────────────────────────────────────────────────
st.divider()
with st.expander(":material/compare: Compare all attacks — what makes each unique?", expanded=False):
    compare_data = []
    for att_name, att_info in ATTACKS.items():
        feats = att_info["features_highlight"]
        compare_data.append({
            "Attack":        att_name,
            "Severity":      att_info["severity"],
            "Key feature":   list(feats.keys())[0],
            "Anomaly":       list(feats.values())[0],
            "Dataset label": att_info["sample_key"],
        })
    st.dataframe(pd.DataFrame(compare_data), hide_index=True, width="stretch")
