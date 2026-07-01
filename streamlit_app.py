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


def _bridge_secrets_to_env() -> None:
    try:
        import streamlit as st

        for key, value in st.secrets.items():
            if isinstance(value, str):
                os.environ.setdefault(key, value)
    except Exception:  # noqa: BLE001 - no secrets file locally is fine
        pass


_bridge_secrets_to_env()

from audit_assistant.app.main import main  # noqa: E402

if __name__ == "__main__":
    main()
