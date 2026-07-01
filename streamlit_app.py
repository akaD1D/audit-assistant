"""Root-level Streamlit entry point.

Running from the project root guarantees the ``audit_assistant`` package is
importable, and this is the file Streamlit Community Cloud looks for by default.

    streamlit run streamlit_app.py

On Streamlit Community Cloud, secrets are provided via ``st.secrets`` rather than
environment variables. We bridge them into ``os.environ`` here (before the config
singleton is built) so the ``AUDIT_``-prefixed pydantic settings pick them up.
Define secrets in the app dashboard, e.g.:

    AUDIT_GEMINI_API_KEY = "your-key"
    AUDIT_GEMINI_MODEL = "gemini-2.5-flash"
"""

from __future__ import annotations

import os
from pathlib import Path


def _bridge_secrets_to_env() -> None:
    # Only touch st.secrets if a secrets file actually exists. Accessing it when
    # absent emits a "No secrets found" message, which would run BEFORE
    # set_page_config() and break Streamlit's "first command" rule.
    candidates = [
        Path.home() / ".streamlit" / "secrets.toml",
        Path(".streamlit") / "secrets.toml",
    ]
    if not any(p.exists() for p in candidates):
        return
    try:
        import streamlit as st

        for key, value in st.secrets.items():
            if isinstance(value, str):
                os.environ.setdefault(key, value)
    except Exception:  # noqa: BLE001 - defensive: never block startup on secrets
        pass


_bridge_secrets_to_env()

from audit_assistant.app.main import main  # noqa: E402

if __name__ == "__main__":
    main()
