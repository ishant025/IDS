"""
5_💻_Terminal.py — Live Attack Terminal

Key design:
  - @st.cache_resource for _T dict: persists across reruns, shared with bg thread
  - background thread writes to _T["output"] list
  - @st.fragment(run_every=0.5) reads _T and auto-refreshes terminal
  - Quick-launch buttons are outside the fragment (always clickable)
"""

import subprocess
import sys
import os
import threading
import streamlit as st
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_sidebar import render_sidebar

st.set_page_config(page_title="Attack Terminal · IDS", page_icon="💻", layout="wide")
render_sidebar()

PROJECT_DIR = Path(__file__).parent.parent.parent.resolve()
VENV_PYTHON = str(PROJECT_DIR / "venv" / "bin" / "python")


# ── Persistent state (survives Streamlit reruns) ───────────────────────────────
@st.cache_resource
def get_state():
    return {"output": [], "running": False, "process": None}

_T = get_state()


# ── Background attack runner ───────────────────────────────────────────────────
def _run_bg(cmd: list, cwd: str):
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONPATH": cwd}
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=cwd, env=env, text=True, bufsize=1,
        )
        _T["process"] = proc
        for line in iter(proc.stdout.readline, ""):
            if line:
                _T["output"].append(line)
        rc = proc.wait()
        _T["output"].append(f"\n[Process finished — exit code {rc}]\n")
    except Exception as e:
        _T["output"].append(f"\n[Error: {e}]\n")
    finally:
        _T["running"] = False
        _T["process"] = None


def launch(cmd: list, label: str):
    if _T["running"]:
        return
    _T["output"] = [f"$ python {label}\n"]
    _T["running"] = True
    _T["process"] = None
    threading.Thread(target=_run_bg, args=(cmd, str(PROJECT_DIR)), daemon=True).start()


def stop_attack():
    proc = _T.get("process")
    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    _T["output"].append("\n[⛔ Attack stopped by user]\n")
    _T["running"] = False
    _T["process"] = None


# ── Terminal renderer ──────────────────────────────────────────────────────────
def render_terminal():
    lines   = _T["output"]
    running = _T["running"]

    if not lines:
        body = (
            "<span style='color:#6e7681'>──────────────────────────────────</span>\n"
            "<span style='color:#3fb950;font-weight:700'>  🛡️  IDS Attack Terminal</span>\n"
            "<span style='color:#6e7681'>──────────────────────────────────</span>\n\n"
            "  Click an attack button below to start.\n"
            "  Output streams here in real time.\n"
        )
    else:
        body = ""
        for line in lines[-400:]:
            esc = (line.replace("&", "&amp;")
                       .replace("<", "&lt;")
                       .replace(">", "&gt;"))
            if line.startswith("$ "):
                body += (f'<span style="color:#58a6ff;font-weight:700">$</span>'
                         f' {esc[2:]}')
            elif any(k in line for k in ("SUCCESS","✅","[+]","success","Welcome")):
                body += f'<span style="color:#3fb950">{esc}</span>'
            elif any(k in line for k in ("FAIL","ERROR","stopped","⛔","[Error")):
                body += f'<span style="color:#ff7b72">{esc}</span>'
            elif any(k in line for k in ("Trying","[*]","Sending","Bot","Thread","Request")):
                body += f'<span style="color:#8b949e">{esc}</span>'
            elif any(k in line for k in ("finished","Exit","Complete","Attack","DDoS","DoS")):
                body += f'<span style="color:#d29922">{esc}</span>'
            else:
                body += esc

    cursor = '<span style="color:#3fb950">█</span>' if running else ""
    st.markdown(
        f'<div id="tw" style="background:#0d1117;border:1px solid #30363d;'
        f'border-radius:0 0 10px 10px;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:13px;line-height:1.6;padding:14px 16px;'
        f'min-height:360px;max-height:360px;overflow-y:auto;'
        f'color:#e6edf3;white-space:pre-wrap;word-break:break-all;">'
        f'{body}{cursor}</div>'
        f'<script>var e=document.getElementById("tw");if(e)e.scrollTop=e.scrollHeight;</script>',
        unsafe_allow_html=True,
    )


# ── Styles ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono&family=Inter:wght@400;600;700&display=swap');
.term-chrome{background:#161b22;border:1px solid #30363d;border-bottom:none;
  border-radius:10px 10px 0 0;padding:10px 16px;display:flex;align-items:center;gap:6px;}
.tdot{width:12px;height:12px;border-radius:50%;display:inline-block;}
.dr{background:#ff5f57;}.dy{background:#febc2e;}.dg{background:#28c840;}
.tlbl{font-family:'Inter',sans-serif;font-size:12px;color:#8b949e;margin-left:8px;font-weight:600;}
.slive{color:#3fb950;font-size:11px;margin-left:auto;font-weight:700;}
.sidle{color:#6e7681;font-size:11px;margin-left:auto;}
.info-card{background:#0d1117;border:1px solid #30363d;border-radius:10px;
  padding:14px 16px;margin-bottom:10px;font-family:'Inter',sans-serif;}
.ic-title{font-size:13px;font-weight:700;color:#e6edf3;margin-bottom:5px;}
.ic-cmd{font-family:'JetBrains Mono',monospace;font-size:11px;color:#3fb950;
  background:#161b22;padding:4px 8px;border-radius:4px;display:block;
  word-break:break-all;margin-bottom:5px;}
.ic-desc{font-size:11px;color:#8b949e;}
.tip-box{background:#0d1117;border:1px solid #30363d;border-left:3px solid #3fb950;
  border-radius:8px;padding:14px 16px;margin-top:12px;
  font-family:'Inter',sans-serif;font-size:12px;color:#8b949e;}
.tip-box strong{color:#e6edf3;}
</style>
""", unsafe_allow_html=True)

# ── Attack definitions ─────────────────────────────────────────────────────────
ATTACKS = [
    ("⚡ BruteForce", [VENV_PYTHON, "attack_scripts/bruteforce.py", "--stop-on-success"],
     "attack_scripts/bruteforce.py --stop-on-success", "Tries common passwords on /login."),
    ("💣 DoS",        [VENV_PYTHON, "attack_scripts/dos_attack.py", "--rate", "80"],
     "attack_scripts/dos_attack.py --rate 80",         "HTTP flood from single IP at 80 req/s."),
    ("🌊 DDoS",       [VENV_PYTHON, "attack_scripts/ddos_attack.py", "--threads", "10"],
     "attack_scripts/ddos_attack.py --threads 10",     "Coordinated flood from 10 bot IPs."),
    ("💉 SQL Inject", [VENV_PYTHON, "attack_scripts/sqli_attack.py"],
     "attack_scripts/sqli_attack.py",                  "SQL injection payloads on /search."),
]

# ── Page layout ────────────────────────────────────────────────────────────────
st.markdown("## 💻 Live Attack Terminal")
st.caption("Run attacks and watch output stream live. Switch to 🔴 Live Monitor to see detections.")
st.markdown("<br>", unsafe_allow_html=True)

col_term, col_info = st.columns([3, 1], gap="large")

with col_term:
    running = _T["running"]

    st.markdown(f"""
    <div class="term-chrome">
      <span class="tdot dr"></span><span class="tdot dy"></span><span class="tdot dg"></span>
      <span class="tlbl">zsh · venv activated · Anomaly/</span>
      {"<span class='slive'>● RUNNING</span>" if running else "<span class='sidle'>● Idle</span>"}
    </div>""", unsafe_allow_html=True)

    # ── Auto-refreshing terminal (fragment runs every 0.5s) ────────────────────
    @st.fragment(run_every=0.5)
    def terminal_fragment():
        render_terminal()
        if _T["running"]:
            if st.button("⛔ Stop Attack", type="primary"):
                stop_attack()
                st.rerun(scope="fragment")

    terminal_fragment()

    # ── Attack buttons (outside fragment — always immediately clickable) ────────
    st.markdown("**⚡ Quick Launch:**")
    btn_cols = st.columns(len(ATTACKS) + 1)

    for i, (lbl, cmd, disp, _desc) in enumerate(ATTACKS):
        with btn_cols[i]:
            if st.button(lbl, use_container_width=True, disabled=running,
                         type="primary" if i == 0 else "secondary",
                         key=f"atk_{i}"):
                launch(cmd, disp)
                st.rerun()

    with btn_cols[-1]:
        if st.button("🗑️ Clear", use_container_width=True,
                     disabled=running, key="clear_btn"):
            _T["output"] = []
            st.rerun()

    # ── Custom command input ───────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    with st.form("custom_cmd", clear_on_submit=True):
        cc1, cc2 = st.columns([5, 1])
        with cc1:
            custom = st.text_input(
                "Custom command",
                placeholder="python attack_scripts/bruteforce.py --stop-on-success",
                label_visibility="collapsed",
                disabled=running,
            )
        with cc2:
            go = st.form_submit_button("▶ Run", use_container_width=True, disabled=running)

    if go and custom.strip():
        parts = custom.strip().split()
        if parts[0] in ("python", "python3"):
            parts[0] = VENV_PYTHON
        launch(parts, custom.strip())
        st.rerun()

# ── Info column ────────────────────────────────────────────────────────────────
with col_info:
    st.markdown("#### 🎯 Attack Reference")
    for lbl, _cmd, disp, desc in ATTACKS:
        st.markdown(f"""
        <div class="info-card">
          <div class="ic-title">{lbl}</div>
          <code class="ic-cmd">python {disp}</code>
          <div class="ic-desc">{desc}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div class="tip-box">
      💡 <strong>Demo Flow:</strong><br><br>
      1. Click an attack button<br>
      2. Switch to <strong>🔴 Live Monitor</strong><br>
      3. Watch live alerts!<br><br>
      <strong>⛔ Stop</strong> ends any<br>running attack instantly.
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**🔗 Quick Links**")
    st.markdown("- [🌐 Target Site](http://localhost:5001)")
    st.markdown("- [🔑 /login](http://localhost:5001/login)")
    st.markdown("- [🔍 /search](http://localhost:5001/search)")
