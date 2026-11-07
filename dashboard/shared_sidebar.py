"""
Shared sidebar + global CSS — import this in every page.
"""

import time
from pathlib import Path
import streamlit as st

_LOG_FILE = Path(__file__).parent.parent / "logs" / "traffic.jsonl"


def _system_status() -> tuple[str, str, bool]:
    if _LOG_FILE.exists():
        age = time.time() - _LOG_FILE.stat().st_mtime
        if age < 30:
            return "LIVE", "live", True
    return "IDLE", "idle", False


def inject_global_css():
    st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;500;600;700&display=swap');

    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #0d1117 60%, #0a0e27 100%);
        font-family: 'Inter', sans-serif;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%) !important;
        border-right: 1px solid #21262d;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stHeader"] { background: transparent; }

    /* ── Hide "app" label above nav ── */
    [data-testid="stSidebarNav"]::before { display: none !important; }
    [data-testid="stSidebarNavSeparator"] { display: none !important; }

    /* ── Nav link styling ── */
    [data-testid="stSidebarNav"] a {
        display: flex; align-items: center; gap: 10px;
        padding: 9px 14px; border-radius: 8px; margin: 2px 4px;
        font-size: 0.875em; font-weight: 500; color: #8b949e !important;
        text-decoration: none; transition: background 0.15s, color 0.15s;
        border: 1px solid transparent;
    }
    [data-testid="stSidebarNav"] a:hover {
        background: rgba(99,102,241,0.10); color: #c4b5fd !important;
        border-color: rgba(99,102,241,0.2);
    }
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background: rgba(99,102,241,0.15); color: #a5b4fc !important;
        border-color: rgba(99,102,241,0.3); font-weight: 600;
    }
    [data-testid="stSidebarNav"] ul { padding: 4px 0 !important; }
    [data-testid="stSidebarNav"] li { margin: 0 !important; }

    /* ── Sidebar elements ── */
    .sb-brand {
        display: flex; align-items: center; gap: 12px;
        padding: 6px 0 12px 0;
    }
    .sb-brand-icon {
        width: 40px; height: 40px; flex-shrink: 0;
        background: linear-gradient(135deg, #1e1b4b, #312e81);
        border: 1px solid rgba(99,102,241,0.4);
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 0 12px rgba(99,102,241,0.25);
    }
    .sb-brand-name {
        font-size: 1.05em; font-weight: 700; color: #e2e8f0;
        letter-spacing: 0.3px;
    }
    .sb-brand-sub { font-size: 0.68em; color: #6b7280; margin-top: 1px; }

    .status-pill {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 5px 12px; border-radius: 20px;
        font-size: 0.8em; font-weight: 600; font-family: 'JetBrains Mono', monospace;
    }
    .status-live { background: rgba(34,197,94,0.15);   color: #4ade80; border: 1px solid rgba(34,197,94,0.3); }
    .status-idle { background: rgba(107,114,128,0.15); color: #9ca3af; border: 1px solid rgba(107,114,128,0.3); }
    .status-dot  { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
    .dot-live    { background: #22c55e; animation: sb-pulse 1.4s ease-in-out infinite; }
    .dot-idle    { background: #6b7280; }
    @keyframes sb-pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50%       { opacity: 0.4; transform: scale(0.8); }
    }

    .attack-badge-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
    .attack-badge {
        font-size: 0.68em; font-weight: 600;
        font-family: 'JetBrains Mono', monospace; padding: 3px 8px; border-radius: 4px;
    }
    .ab-red    { background: rgba(239,68,68,0.15);   color: #fca5a5; border: 1px solid rgba(239,68,68,0.3); }
    .ab-orange { background: rgba(249,115,22,0.15);  color: #fdba74; border: 1px solid rgba(249,115,22,0.3); }
    .ab-red2   { background: rgba(239,68,68,0.15);   color: #fca5a5; border: 1px solid rgba(239,68,68,0.3); }
    .ab-gray   { background: rgba(107,114,128,0.12); color: #9ca3af; border: 1px solid rgba(107,114,128,0.25); }

    /* ── Home page: hero banner ── */
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        border: 1px solid #312e81; border-radius: 16px;
        padding: 48px 40px; text-align: center;
        position: relative; overflow: hidden; margin-bottom: 32px;
    }
    .hero-banner::before {
        content: ''; position: absolute; top: -50%; left: -50%;
        width: 200%; height: 200%;
        background: radial-gradient(ellipse at center, rgba(99,102,241,0.08) 0%, transparent 60%);
        pointer-events: none;
    }
    .hero-title { font-size: 2.6em; font-weight: 700; color: #e2e8f0; letter-spacing: -0.5px; margin: 0 0 10px 0; }
    .hero-title span {
        background: linear-gradient(90deg, #818cf8, #38bdf8, #34d399);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    }
    .hero-sub  { color: #94a3b8; font-size: 1.05em; margin: 0 0 28px 0; }
    .hero-tags { display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; }
    .hero-tag  {
        background: rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.35);
        color: #a5b4fc; padding: 4px 14px; border-radius: 20px;
        font-size: 0.78em; font-weight: 500; font-family: 'JetBrains Mono', monospace;
    }

    /* ── Home page: nav cards ── */
    .nav-card {
        background: #0d1117; border: 1px solid #21262d; border-radius: 12px;
        padding: 24px 20px; transition: border-color 0.2s, transform 0.2s;
        height: 100%; position: relative; overflow: hidden;
    }
    .nav-card::after {
        content: ''; position: absolute; top: 0; left: 0; right: 0;
        height: 3px; border-radius: 12px 12px 0 0;
    }
    .nav-card-live::after     { background: linear-gradient(90deg, #ef4444, #f97316); }
    .nav-card-demo::after     { background: linear-gradient(90deg, #8b5cf6, #6366f1); }
    .nav-card-overview::after { background: linear-gradient(90deg, #3b82f6, #06b6d4); }
    .nav-card:hover { border-color: #30363d; transform: translateY(-2px); }
    .nav-card-icon  { font-size: 2em; margin-bottom: 12px; }
    .nav-card-title { font-size: 1.1em; font-weight: 700; color: #e2e8f0; margin-bottom: 6px; }
    .nav-card-desc  { color: #8b949e; font-size: 0.88em; line-height: 1.5; }
    .nav-card-badge {
        display: inline-block; margin-top: 12px;
        font-size: 0.72em; font-weight: 600; font-family: 'JetBrains Mono', monospace;
        padding: 2px 10px; border-radius: 20px;
    }
    .badge-live { background: rgba(239,68,68,0.15);  color: #fca5a5; border: 1px solid rgba(239,68,68,0.3); }
    .badge-demo { background: rgba(139,92,246,0.15); color: #c4b5fd; border: 1px solid rgba(139,92,246,0.3); }
    .badge-info { background: rgba(59,130,246,0.15); color: #93c5fd; border: 1px solid rgba(59,130,246,0.3); }

    /* ── Home page: flow diagram ── */
    .flow-section {
        background: #0d1117; border: 1px solid #21262d;
        border-radius: 12px; padding: 24px 28px;
    }
    .flow-title {
        font-size: 0.8em; font-weight: 600; text-transform: uppercase;
        letter-spacing: 1px; color: #6b7280; margin-bottom: 16px;
    }
    .flow-steps { display: flex; align-items: center; flex-wrap: wrap; }
    .flow-step  {
        background: #161b22; border: 1px solid #30363d; border-radius: 8px;
        padding: 10px 16px; text-align: center; flex: 1; min-width: 120px;
    }
    .flow-step-icon  { font-size: 1.4em; display: block; margin-bottom: 4px; }
    .flow-step-label { font-size: 0.78em; font-weight: 600; color: #e2e8f0; display: block; }
    .flow-step-sub   { font-size: 0.68em; color: #8b949e; display: block; font-family: 'JetBrains Mono', monospace; }
    .flow-arrow { color: #30363d; font-size: 1.2em; padding: 0 6px; flex-shrink: 0; }
</style>
""", unsafe_allow_html=True)


def render_sidebar():
    """Call this at the top of every page to get a consistent sidebar."""
    inject_global_css()

    with st.sidebar:
        # ── Brand header (top) ────────────────────────────────────────────
        st.markdown("""
        <div class="sb-brand">
            <div class="sb-brand-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2L3 7V12C3 16.55 6.84 20.74 12 22C17.16 20.74 21 16.55 21 12V7L12 2Z"
                          fill="url(#sg)" stroke="rgba(255,255,255,0.15)" stroke-width="0.5"/>
                    <path d="M9 12L11 14L15 10" stroke="white" stroke-width="2"
                          stroke-linecap="round" stroke-linejoin="round"/>
                    <defs>
                        <linearGradient id="sg" x1="3" y1="2" x2="21" y2="22" gradientUnits="userSpaceOnUse">
                            <stop offset="0%" stop-color="#6366f1"/>
                            <stop offset="100%" stop-color="#8b5cf6"/>
                        </linearGradient>
                    </defs>
                </svg>
            </div>
            <div>
                <div class="sb-brand-name">ShieldAI</div>
                <div class="sb-brand-sub">Intrusion Detection System</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # ── System status ─────────────────────────────────────────────────
        status_label, status_cls, is_live = _system_status()
        dot_cls = "dot-live" if is_live else "dot-idle"
        st.markdown("**System Status**")
        st.markdown(f"""
        <div class="status-pill status-{status_cls}">
            <span class="status-dot {dot_cls}"></span>
            {status_label}
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # ── Attack type legend ────────────────────────────────────────────
        st.markdown("**Attack Types**")
        st.markdown("""
        <div class="attack-badge-row">
            <span class="attack-badge ab-red">SQL Injection</span>
            <span class="attack-badge ab-orange">Brute Force</span>
            <span class="attack-badge ab-red2">DoS</span>
            <span class="attack-badge ab-red2">DDoS</span>
            <span class="attack-badge ab-gray">Unknown</span>
        </div>
        <p style="font-size:0.72em; color:#6b7280; margin-top:8px;">
            Classified by ML models in real time.
        </p>
        """, unsafe_allow_html=True)

        st.divider()
        st.markdown(
            '<p style="font-size:0.72em; color:#6b7280;">Dataset: CIC-IDS2017 · Model: XGBoost</p>',
            unsafe_allow_html=True,
        )
