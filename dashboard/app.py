"""
IDS — Intrusion Detection System Dashboard
Main entry point for the Streamlit multi-page application.
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from shared_sidebar import render_sidebar

st.set_page_config(
    page_title="IDS — Intrusion Detection System",
    page_icon=":material/shield:",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar()

# ── Hero banner ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
    <div class="hero-title">🛡️ <span>Intrusion Detection System</span></div>
    <div class="hero-sub">AI-powered real-time network security · CIC-IDS2017 · XGBoost</div>
    <div class="hero-tags">
        <span class="hero-tag">XGBoost</span>
        <span class="hero-tag">CIC-IDS2017</span>
        <span class="hero-tag">Real-time Detection</span>
        <span class="hero-tag">4 Attack Types</span>
        <span class="hero-tag">70 Features</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Navigation cards ──────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3, gap="medium")

with col1:
    st.markdown("""
    <div class="nav-card nav-card-live">
        <div class="nav-card-icon">📡</div>
        <div class="nav-card-title">Live Monitor</div>
        <div class="nav-card-desc">Watch attacks get detected in real time. Live alert feed, ML predictions, threat level indicators.</div>
        <span class="nav-card-badge badge-live">REAL-TIME</span>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="nav-card nav-card-demo">
        <div class="nav-card-icon">🎯</div>
        <div class="nav-card-title">Attack Demo Lab</div>
        <div class="nav-card-desc">Step-by-step attack walkthroughs using real CIC-IDS2017 samples with live model predictions.</div>
        <span class="nav-card-badge badge-demo">INTERACTIVE</span>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="nav-card nav-card-overview">
        <div class="nav-card-icon">📊</div>
        <div class="nav-card-title">Overview</div>
        <div class="nav-card-desc">Project architecture, model performance metrics, dataset stats and quick-start guide.</div>
        <span class="nav-card-badge badge-info">DOCS</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Demo flow ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="flow-section">
    <div class="flow-title">Demo Flow</div>
    <div class="flow-steps">
        <div class="flow-step">
            <span class="flow-step-icon">🖥️</span>
            <span class="flow-step-label">Start Server</span>
            <span class="flow-step-sub">localhost:5001</span>
        </div>
        <span class="flow-arrow">→</span>
        <div class="flow-step">
            <span class="flow-step-icon">⚡</span>
            <span class="flow-step-label">Run Attack</span>
            <span class="flow-step-sub">bruteforce / dos / sqli</span>
        </div>
        <span class="flow-arrow">→</span>
        <div class="flow-step">
            <span class="flow-step-icon">📝</span>
            <span class="flow-step-label">Logs Written</span>
            <span class="flow-step-sub">traffic.jsonl</span>
        </div>
        <span class="flow-arrow">→</span>
        <div class="flow-step">
            <span class="flow-step-icon">🤖</span>
            <span class="flow-step-label">ML Predicts</span>
            <span class="flow-step-sub">XGBoost</span>
        </div>
        <span class="flow-arrow">→</span>
        <div class="flow-step">
            <span class="flow-step-icon">🚨</span>
            <span class="flow-step-label">Live Alert</span>
            <span class="flow-step-sub">dashboard</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
