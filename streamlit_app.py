"""Root-level Streamlit entry point.

Running from the project root guarantees the ``audit_assistant`` package is
importable, and this is the file Streamlit Community Cloud looks for by default.

    streamlit run streamlit_app.py
"""

from audit_assistant.app.main import main

if __name__ == "__main__":
    main()
