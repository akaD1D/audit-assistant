"""UI theme: professional styling for a ChatGPT/Copilot-like feel.

Injects scoped CSS (works in Streamlit's light and dark modes by using
translucent tones and the accent colour) and renders a branded header.
Keeping this in one module lets the rest of the UI stay logic-only.
"""

from __future__ import annotations

import streamlit as st

ACCENT = "#2563EB"       # trustworthy blue
ACCENT_DARK = "#1E40AF"

_CSS = f"""
<style>
/* ---- layout & typography -------------------------------------------------*/
.block-container {{ padding-top: 2.2rem; max-width: 1150px; }}
html, body, [class*="css"] {{
    font-family: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
}}
h1, h2, h3 {{ font-weight: 700; letter-spacing: -0.01em; }}

/* ---- branded header ------------------------------------------------------*/
.aa-header {{
    background: linear-gradient(120deg, {ACCENT} 0%, {ACCENT_DARK} 100%);
    color: #fff; border-radius: 16px; padding: 1.1rem 1.4rem; margin-bottom: 1.1rem;
    box-shadow: 0 6px 20px rgba(37,99,235,0.25);
    display: flex; align-items: center; gap: 0.9rem;
}}
.aa-header .aa-logo {{ font-size: 2rem; line-height: 1; }}
.aa-header h1 {{ color: #fff; font-size: 1.5rem; margin: 0; }}
.aa-header p {{ color: rgba(255,255,255,0.85); margin: 0.15rem 0 0; font-size: 0.9rem; }}
.aa-badges {{ margin-left: auto; display: flex; gap: 0.5rem; flex-wrap: wrap; }}
.aa-badge {{
    background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.25);
    color: #fff; padding: 0.25rem 0.7rem; border-radius: 999px; font-size: 0.78rem;
    white-space: nowrap;
}}

/* ---- tabs as pills -------------------------------------------------------*/
[data-testid="stTabs"] button[role="tab"] {{
    border-radius: 10px; padding: 0.35rem 0.9rem; font-weight: 600;
}}
[data-testid="stTabs"] button[aria-selected="true"] {{
    background: rgba(37,99,235,0.12); color: {ACCENT};
}}

/* ---- chat bubbles --------------------------------------------------------*/
[data-testid="stChatMessage"] {{
    border-radius: 14px; padding: 0.4rem 0.2rem; margin-bottom: 0.3rem;
}}

/* ---- buttons -------------------------------------------------------------*/
.stButton > button, .stDownloadButton > button {{
    border-radius: 10px; font-weight: 600; border: 1px solid rgba(37,99,235,0.35);
    transition: all 0.15s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
    border-color: {ACCENT}; color: {ACCENT}; transform: translateY(-1px);
}}

/* ---- inputs --------------------------------------------------------------*/
[data-testid="stChatInput"] textarea, .stTextInput input, .stNumberInput input {{
    border-radius: 10px !important;
}}

/* ---- expanders & cards ---------------------------------------------------*/
[data-testid="stExpander"] {{ border-radius: 12px; border: 1px solid rgba(128,128,128,0.2); }}
[data-testid="stMetric"] {{
    background: rgba(37,99,235,0.06); border: 1px solid rgba(37,99,235,0.15);
    border-radius: 12px; padding: 0.6rem 0.9rem;
}}

/* ---- sidebar -------------------------------------------------------------*/
[data-testid="stSidebar"] {{ border-right: 1px solid rgba(128,128,128,0.15); }}
[data-testid="stSidebar"] h2 {{ font-size: 1.05rem; }}

/* ---- confidence chips (rendered via markdown colour) ---------------------*/
</style>
"""


def apply_theme() -> None:
    """Inject the global CSS. Call once, early in the page."""
    st.markdown(_CSS, unsafe_allow_html=True)


def render_header(*, kb_count: int, provider: str, llm_ready: bool) -> None:
    """Render the branded gradient header with status chips."""
    status = "🟢 AI ready" if llm_ready else "🟡 add key for chat"
    st.markdown(
        f"""
        <div class="aa-header">
            <div class="aa-logo">🧾</div>
            <div>
                <h1>AI Audit Assistant</h1>
                <p>Grounded answers with citations · deterministic audit calculations · report export</p>
            </div>
            <div class="aa-badges">
                <span class="aa-badge">📚 {kb_count} docs</span>
                <span class="aa-badge">🤖 {provider}</span>
                <span class="aa-badge">{status}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
