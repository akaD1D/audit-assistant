"""App-render smoke test using Streamlit's AppTest.

Executes the real app script end-to-end (all tabs render) and asserts no
exception is raised. Catches render-time errors like nested expanders, missing
session_state keys, and bad widget wiring — the class of bug that service-level
unit tests miss.

Runs against an isolated temp data dir so it never touches the real knowledge
base or fights the single-process Qdrant lock of a running app.
"""

from __future__ import annotations

import pytest

pytest.importorskip("streamlit.testing.v1")


def test_app_renders_without_exception(tmp_path, monkeypatch) -> None:
    from streamlit.testing.v1 import AppTest

    # Isolate storage so we don't lock/pollute the real data dir.
    monkeypatch.setenv("AUDIT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUDIT_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("AUDIT_DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("AUDIT_VECTOR_DIR", str(tmp_path / "qdrant"))
    monkeypatch.setenv("AUDIT_LLM_PROVIDER", "ollama")  # no key/network needed to render

    # Reset the cached settings + container singletons so the app rebuilds
    # against the isolated dirs.
    from audit_assistant.core import container as container_mod
    from audit_assistant.core.config import get_settings

    get_settings.cache_clear()
    container_mod._container = None
    try:
        at = AppTest.from_file("streamlit_app.py", default_timeout=120)
        at.run()
        assert not at.exception, f"App raised on initial render: {at.exception}"
    finally:
        get_settings.cache_clear()
        container_mod._container = None
