"""
Overview — Visual project homepage with live stats
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_sidebar import render_sidebar

st.set_page_config(page_title="IDS — Overview", page_icon=":material/shield:", layout="wide")
render_sidebar()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE        = Path(__file__).parent.parent.parent
PROCESSED   = BASE / "data" / "processed"
MODELS_DIR  = BASE / "models"
FIGURES_DIR = BASE / "reports" / "figures"

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
    .page-header {
        display: flex; align-items: center; gap: 16px;
        padding: 28px 0 24px 0;
        border-bottom: 1px solid #21262d;
        margin-bottom: 28px;
    }
    .page-header-icon {
        width: 52px; height: 52px;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        border-radius: 14px;
        display: flex; align-items: center; justify-content: center;
        font-size: 26px; flex-shrink: 0;
        box-shadow: 0 0 20px rgba(99,102,241,0.3);
    }
    .page-header-title {
        font-size: 1.8em; font-weight: 700; color: #e2e8f0;
        line-height: 1.2; margin: 0;
    }
    .page-header-sub { font-size: 0.85em; color: #8b949e; margin: 0; margin-top: 2px; }

    /* ── Section titles ── */
    .section-title {
        font-size: 0.72em; font-weight: 600;
        text-transform: uppercase; letter-spacing: 1.5px;
        color: #6b7280; margin: 0 0 14px 0;
        display: flex; align-items: center; gap: 8px;
    }
    .section-title::after {
        content: ''; flex: 1; height: 1px; background: #21262d;
    }

    /* ── Stat cards ── */
    .stat-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        margin-bottom: 28px;
    }
    .stat-card {
        background: #0d1117;
        border: 1px solid #21262d;
        border-radius: 12px;
        padding: 20px 16px;
        position: relative;
        overflow: hidden;
        transition: border-color 0.2s;
    }
    .stat-card:hover { border-color: #30363d; }
    .stat-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 3px;
        border-radius: 12px 12px 0 0;
    }
    .stat-card-blue::before   { background: linear-gradient(90deg, #3b82f6, #06b6d4); }
    .stat-card-purple::before { background: linear-gradient(90deg, #8b5cf6, #6366f1); }
    .stat-card-green::before  { background: linear-gradient(90deg, #22c55e, #10b981); }
    .stat-card-orange::before { background: linear-gradient(90deg, #f97316, #eab308); }
    .stat-card-red::before    { background: linear-gradient(90deg, #ef4444, #f97316); }
    .stat-icon { font-size: 1.5em; margin-bottom: 8px; }
    .stat-value {
        font-size: 1.8em; font-weight: 700; color: #e2e8f0;
        font-family: 'JetBrains Mono', monospace;
        line-height: 1; margin-bottom: 4px;
    }
    .stat-label { font-size: 0.75em; color: #8b949e; font-weight: 500; }

    /* ── Attack cards ── */
    .attack-grid {
        display: grid; grid-template-columns: repeat(4, 1fr);
        gap: 14px; margin-bottom: 28px;
    }
    .attack-card {
        background: #0d1117;
        border: 1px solid #21262d;
        border-radius: 12px;
        padding: 20px;
        position: relative; overflow: hidden;
        transition: border-color 0.2s, transform 0.2s;
    }
    .attack-card:hover { border-color: #30363d; transform: translateY(-2px); }
    .attack-card-high::after, .attack-card-critical::after {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 3px;
        border-radius: 12px 12px 0 0;
    }
    .attack-card-high::after     { background: linear-gradient(90deg, #f97316, #eab308); }
    .attack-card-critical::after { background: linear-gradient(90deg, #ef4444, #f97316); }
    .attack-card-icon { font-size: 1.8em; margin-bottom: 10px; }
    .attack-card-name {
        font-size: 1em; font-weight: 700; color: #e2e8f0; margin-bottom: 6px;
    }
    .attack-card-desc { font-size: 0.78em; color: #8b949e; line-height: 1.5; margin-bottom: 12px; }
    .severity-badge {
        display: inline-block;
        font-size: 0.68em; font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        padding: 3px 10px; border-radius: 4px;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    .sev-high     { background: rgba(249,115,22,0.15); color: #fdba74; border: 1px solid rgba(249,115,22,0.3); }
    .sev-critical { background: rgba(239,68,68,0.15);  color: #fca5a5; border: 1px solid rgba(239,68,68,0.3); }

    /* ── Pipeline ── */
    .pipeline-container {
        background: #0d1117; border: 1px solid #21262d;
        border-radius: 12px; padding: 28px;
        margin-bottom: 28px;
    }
    .pipeline-row {
        display: flex; align-items: center; gap: 0;
        justify-content: space-between;
    }
    .pipeline-node {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 10px; padding: 14px 16px;
        text-align: center; flex: 1;
        transition: border-color 0.2s;
    }
    .pipeline-node:hover { border-color: #6366f1; }
    .pipeline-node-icon { font-size: 1.6em; display: block; margin-bottom: 6px; }
    .pipeline-node-label {
        font-size: 0.82em; font-weight: 600; color: #e2e8f0;
        display: block; margin-bottom: 2px;
    }
    .pipeline-node-sub {
        font-size: 0.68em; color: #6b7280;
        font-family: 'JetBrains Mono', monospace; display: block;
    }
    .pipeline-arrow { color: #6366f1; font-size: 1.3em; padding: 0 8px; flex-shrink: 0; }

    /* ── Performance table ── */
    .perf-container {
        background: #0d1117; border: 1px solid #21262d;
        border-radius: 12px; padding: 24px;
        margin-bottom: 28px;
    }

    /* ── Quick start ── */
    .qs-container {
        background: #0d1117; border: 1px solid #21262d;
        border-radius: 12px; padding: 24px;
    }
    .qs-step {
        display: flex; align-items: flex-start; gap: 14px;
        margin-bottom: 20px;
    }
    .qs-step-num {
        width: 28px; height: 28px; flex-shrink: 0;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.75em; font-weight: 700; color: white;
    }
    .qs-step-content { flex: 1; }
    .qs-step-title { font-size: 0.85em; font-weight: 600; color: #e2e8f0; margin-bottom: 6px; }
</style>
""", unsafe_allow_html=True)

# ── Cached loaders ────────────────────────────────────────────────────────────
@st.cache_data
def load_arrays():
    try:
        X_train = np.load(str(PROCESSED / "X_train.npy"))
        X_test  = np.load(str(PROCESSED / "X_test.npy"))
        return X_train, X_test
    except Exception:
        return None, None

@st.cache_resource
def count_models():
    return len(list(MODELS_DIR.glob("*.pkl")))

@st.cache_data
def load_perf():
    csv_path = FIGURES_DIR / "model_comparison.csv"
    if csv_path.exists():
        df = pd.read_csv(str(csv_path))
        if "Model" in df.columns:
            df = df[df["Model"].str.contains("xgboost", case=False, na=False)]
        return df if not df.empty else None
    return None

# ── Data ──────────────────────────────────────────────────────────────────────
X_train, X_test = load_arrays()
n_models        = count_models()
perf_df         = load_perf()

train_count = f"{len(X_train):,}" if X_train is not None else "—"
test_count  = f"{len(X_test):,}"  if X_test  is not None else "—"

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <div class="page-header-icon">🛡️</div>
    <div>
        <div class="page-header-title">Intrusion Detection System</div>
        <div class="page-header-sub">AI-powered real-time network security · CIC-IDS2017 · XGBoost</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Stat cards ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">System Stats</div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="stat-grid">
    <div class="stat-card stat-card-blue">
        <div class="stat-icon">📚</div>
        <div class="stat-value">{train_count}</div>
        <div class="stat-label">Training Samples</div>
    </div>
    <div class="stat-card stat-card-purple">
        <div class="stat-icon">🧪</div>
        <div class="stat-value">{test_count}</div>
        <div class="stat-label">Test Samples</div>
    </div>
    <div class="stat-card stat-card-green">
        <div class="stat-icon">🔢</div>
        <div class="stat-value">70</div>
        <div class="stat-label">Features</div>
    </div>
    <div class="stat-card stat-card-orange">
        <div class="stat-icon">🤖</div>
        <div class="stat-value">{n_models}</div>
        <div class="stat-label">Models Trained</div>
    </div>
    <div class="stat-card stat-card-red">
        <div class="stat-icon">🎯</div>
        <div class="stat-value">4</div>
        <div class="stat-label">Attack Types</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Attack types ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Attack Types Detected</div>', unsafe_allow_html=True)
st.markdown("""
<div class="attack-grid">
    <div class="attack-card attack-card-high">
        <div class="attack-card-icon">🔐</div>
        <div class="attack-card-name">BruteForce</div>
        <div class="attack-card-desc">Credential guessing via port 21/22 (FTP/SSH) — repeated automated login attempts until access is gained.</div>
        <span class="severity-badge sev-high">High</span>
    </div>
    <div class="attack-card attack-card-high">
        <div class="attack-card-icon">⚡</div>
        <div class="attack-card-name">DoS</div>
        <div class="attack-card-desc">HTTP flood from a single source — exhausts server threads and CPU, causing service degradation.</div>
        <span class="severity-badge sev-high">High</span>
    </div>
    <div class="attack-card attack-card-critical">
        <div class="attack-card-icon">💥</div>
        <div class="attack-card-name">DDoS</div>
        <div class="attack-card-desc">Multi-bot coordinated flood — amplifies traffic beyond network capacity, rendering the server unreachable.</div>
        <span class="severity-badge sev-critical">Critical</span>
    </div>
    <div class="attack-card attack-card-critical">
        <div class="attack-card-icon">💉</div>
        <div class="attack-card-name">SQL Injection</div>
        <div class="attack-card-desc">Malicious SQL via web form inputs — bypasses authentication and exfiltrates or corrupts the database.</div>
        <span class="severity-badge sev-critical">Critical</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── ML Pipeline ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">ML Pipeline</div>', unsafe_allow_html=True)
st.markdown("""
<div class="pipeline-container">
    <div class="pipeline-row">
        <div class="pipeline-node">
            <span class="pipeline-node-icon">📦</span>
            <span class="pipeline-node-label">CIC-IDS2017</span>
            <span class="pipeline-node-sub">2.8M records · 8 CSVs</span>
        </div>
        <span class="pipeline-arrow">→</span>
        <div class="pipeline-node">
            <span class="pipeline-node-icon">🧹</span>
            <span class="pipeline-node-label">Preprocessing</span>
            <span class="pipeline-node-sub">Clean · Encode · Scale</span>
        </div>
        <span class="pipeline-arrow">→</span>
        <div class="pipeline-node">
            <span class="pipeline-node-icon">✂️</span>
            <span class="pipeline-node-label">Split</span>
            <span class="pipeline-node-sub">Train / Val / Test</span>
        </div>
        <span class="pipeline-arrow">→</span>
        <div class="pipeline-node">
            <span class="pipeline-node-icon">🤖</span>
            <span class="pipeline-node-label">XGBoost</span>
            <span class="pipeline-node-sub">200 trees · depth 8</span>
        </div>
        <span class="pipeline-arrow">→</span>
        <div class="pipeline-node">
            <span class="pipeline-node-icon">📊</span>
            <span class="pipeline-node-label">Evaluate</span>
            <span class="pipeline-node-sub">F1 · ROC-AUC · CM</span>
        </div>
        <span class="pipeline-arrow">→</span>
        <div class="pipeline-node">
            <span class="pipeline-node-icon">📡</span>
            <span class="pipeline-node-label">Live IDS</span>
            <span class="pipeline-node-sub">Real-time alerts</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Model performance ─────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Model Performance — XGBoost</div>', unsafe_allow_html=True)

with st.container(border=True):
    if perf_df is not None:
        # Style the dataframe
        numeric_cols = perf_df.select_dtypes(include=[float, int]).columns.tolist()

        def highlight_high(val):
            try:
                v = float(val)
                if v >= 0.99:
                    return "color: #4ade80; font-weight: 600;"
                elif v >= 0.95:
                    return "color: #86efac;"
                elif v < 0.80:
                    return "color: #fca5a5;"
            except (ValueError, TypeError):
                pass
            return "color: #e2e8f0;"

        styled = perf_df.style.map(highlight_high, subset=numeric_cols)
        st.dataframe(styled, hide_index=True, width="stretch")

        # Show figures if available
        fig_cols = st.columns(3)
        fig_files = [
            (FIGURES_DIR / "confusion_matrices.png", "Confusion Matrix"),
            (FIGURES_DIR / "roc_curves.png",         "ROC Curves"),
            (FIGURES_DIR / "metrics_comparison.png", "Metrics Comparison"),
        ]
        for col, (fig_path, caption) in zip(fig_cols, fig_files):
            if fig_path.exists():
                with col:
                    st.image(str(fig_path), caption=caption, width="stretch")
    else:
        st.info(
            "Model performance will appear after running: `python run_pipeline.py`",
            icon=":material/info:",
        )

# ── Quick start ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Quick Start</div>', unsafe_allow_html=True)

with st.expander("Show setup & commands", expanded=False):
    col_a, col_b = st.columns(2, gap="large")

    with col_a:
        st.markdown("**1 — Start the target server**")
        st.code("python target_server/app.py", language="bash")
        st.caption("Runs CorpNet on http://localhost:5001")

        st.markdown("**2 — Launch the dashboard**")
        st.code("streamlit run dashboard/app.py", language="bash")
        st.caption("Opens on http://localhost:8502")

    with col_b:
        st.markdown("**3 — Run attack scripts**")
        st.code(
            "# BruteForce\npython attack_scripts/bruteforce.py\n\n"
            "# DoS flood\npython attack_scripts/dos_attack.py --rate 100\n\n"
            "# DDoS simulation\npython attack_scripts/ddos_attack.py --threads 10\n\n"
            "# SQL Injection\npython attack_scripts/sqli_attack.py",
            language="bash",
        )

    st.markdown("**4 — (Optional) Retrain from scratch**")
    st.code("python run_pipeline.py", language="bash")
    st.caption("Loads CIC-IDS2017, preprocesses, trains XGBoost, evaluates, saves model.")
