"""Upload + document management UI.

Uploads default to **session documents** (temporary, in-memory, never indexed
permanently). The user must explicitly choose "Add to Knowledge Base" to persist
a document. Processing is shown as staged progress.
"""

from __future__ import annotations

import hashlib

import streamlit as st

from audit_assistant.core.exceptions import (
    FileValidationError,
    ParsingError,
    UnsupportedFileTypeError,
)
from audit_assistant.core.logging import get_logger

log = get_logger(__name__)

_ACCEPTED = ["pdf", "xlsx", "xls", "csv", "docx", "txt", "png", "jpg", "jpeg"]
SESSION = "🗂️ This session only"
KB = "📚 Add to Knowledge Base"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _process_file(container, *, name: str, data: bytes, to_kb: bool) -> None:
    """Run the staged ingestion pipeline for one file into the chosen target."""
    ingestion = container.ingestion_service
    with st.status(f"Processing **{name}**…", expanded=True) as status:
        try:
            status.write("📤 Uploading…")
            file_type = ingestion.validate(filename=name, data=data)

            status.write("📄 Extracting text & tables…")
            document = ingestion.parse(filename=name, data=data, file_type=file_type)

            if ingestion.is_image(file_type):
                status.write("🔍 Reading image (OCR / vision)…")
                ingestion.transcribe_image(document, data)

            status.write("🧠 Creating embeddings…")
            chunks, embeddings = ingestion.embed(document)

            if to_kb:
                status.write("🗄️ Indexing into knowledge base…")
                ingestion.persist_to_kb(document, data, chunks, embeddings)
                container.audit_log.record("kb_add", f"{name} ({document.page_count}p)")
                target = "Knowledge Base"
            else:
                status.write("🗂️ Adding to this session…")
                st.session_state["session_index"].add(chunks, embeddings)
                st.session_state["session_docs"][document.document_id] = document
                container.audit_log.record("session_upload", name)
                target = "session"

            status.update(
                label=f"✅ {document.filename} → {target} — "
                f"{document.page_count} page(s), {len(chunks)} chunk(s)",
                state="complete",
            )
        except (FileValidationError, UnsupportedFileTypeError, ParsingError) as exc:
            status.update(label=f"❌ {name}: {exc}", state="error")
        except Exception as exc:  # noqa: BLE001 - never crash the UI
            log.exception("Ingestion failed for %s", name)
            status.update(label=f"❌ {name}: unexpected error ({exc})", state="error")


def render_uploader(container) -> None:
    processed: set[str] = st.session_state.setdefault("processed_hashes", set())

    destination = st.radio(
        "How would you like to use uploaded files?",
        [SESSION, KB],
        key="upload_destination",
        help="Session documents are temporary (this chat only). Knowledge Base "
        "documents are saved permanently and searchable in future sessions.",
    )
    to_kb = destination == KB

    files = st.file_uploader(
        "Upload files",
        type=_ACCEPTED,
        accept_multiple_files=True,
        help=f"PDF, Excel, CSV, Word, images, text. Max {container.settings.max_upload_mb} MB each.",
    )

    for upload in files or []:
        data = upload.getvalue()
        marker = f"{_digest(data)}:{destination}"
        if marker in processed:
            continue
        _process_file(container, name=upload.name, data=data, to_kb=to_kb)
        processed.add(marker)


def render_session_docs(container) -> None:
    docs = st.session_state.get("session_docs", {})
    st.caption(f"{len(docs)} temporary document(s) — cleared when you close the app.")
    for doc_id, doc in list(docs.items()):
        col1, col2 = st.columns([5, 1])
        col1.write(f"📄 {doc.filename}")
        if col2.button("🗑️", key=f"rm_sess_{doc_id}", help="Remove from session"):
            st.session_state["session_index"].remove_document(doc_id)
            docs.pop(doc_id, None)
            st.rerun()


def render_kb_summary(container) -> None:
    count = container.kb_service.count()
    st.caption(f"{count} document(s) saved permanently.")
    st.caption("Manage them in the **📚 Knowledge Base** tab.")


def render_recent_reports() -> None:
    reports = st.session_state.get("recent_reports", [])
    if not reports:
        st.caption("No reports generated yet.")
        return
    for r in reports[-5:][::-1]:
        st.write(f"📄 {r}")


def render_document_list() -> None:
    """Session document previews (for the Documents tab)."""
    documents = st.session_state.get("session_docs", {})
    if not documents:
        st.info("No session documents. Upload files from the sidebar to analyse them here.")
        return
    st.subheader("🗂️ Session documents")
    for doc in documents.values():
        with st.expander(f"{doc.filename} · {doc.file_type.value.upper()} · {doc.page_count} page(s)"):
            if doc.metadata:
                st.caption(" | ".join(f"{k}: {v}" for k, v in doc.metadata.items()))
            for page in doc.pages:
                if page.text:
                    st.text(page.text[:1500] + ("…" if len(page.text) > 1500 else ""))
                for table in page.tables:
                    st.markdown(table.to_markdown())
