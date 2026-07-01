"""Upload + document-preview UI component.

Streamlit reruns the whole script on every interaction, so we deduplicate by a
content hash to avoid re-ingesting the same file repeatedly. Parsed documents
are cached in ``st.session_state['documents']`` for the session.
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
from audit_assistant.domain.models import ParsedDocument

log = get_logger(__name__)

_ACCEPTED = ["pdf", "xlsx", "xls", "csv", "docx", "txt", "png", "jpg", "jpeg"]


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render_uploader(container) -> None:
    """Render the sidebar uploader and ingest new files into the session."""
    ingested: dict[str, ParsedDocument] = st.session_state.setdefault("documents", {})
    hashes: set[str] = st.session_state.setdefault("doc_hashes", set())

    files = st.file_uploader(
        "Upload audit files",
        type=_ACCEPTED,
        accept_multiple_files=True,
        help="PDF, Excel, CSV, Word, images, and text. Max "
        f"{container.settings.max_upload_mb} MB each.",
    )

    for upload in files or []:
        data = upload.getvalue()
        digest = _digest(data)
        if digest in hashes:
            continue  # already ingested this exact file this session

        size_mb = len(data) / (1024 * 1024)
        with st.status(
            f"Processing **{upload.name}** ({size_mb:.1f} MB) — parsing and building "
            "the search index. Large reports can take up to a minute…",
            expanded=False,
        ) as status:
            try:
                doc = container.ingestion_service.ingest(filename=upload.name, data=data)
            except (FileValidationError, UnsupportedFileTypeError, ParsingError) as exc:
                status.update(label=f"❌ {upload.name}: {exc}", state="error")
                continue
            except Exception as exc:  # noqa: BLE001 - defensive: never crash the UI
                log.exception("Unexpected ingestion error for %s", upload.name)
                status.update(label=f"❌ {upload.name}: unexpected error ({exc}).", state="error")
                continue

            ingested[doc.document_id] = doc
            hashes.add(digest)
            container.audit_log.record("document_uploaded", f"{doc.filename} ({doc.page_count} pages)")
            chunks = doc.metadata.get("chunks", "?")
            status.update(
                label=f"✅ {doc.filename} — {doc.page_count} page(s), {chunks} chunks indexed",
                state="complete",
            )

    st.caption(f"{len(ingested)} document(s) in this session.")


def render_document_list() -> None:
    """Render an expandable preview of every ingested document."""
    documents: dict[str, ParsedDocument] = st.session_state.get("documents", {})
    if not documents:
        st.info("Upload documents from the sidebar to get started.")
        return

    st.subheader("📑 Ingested documents")
    for doc in documents.values():
        with st.expander(f"{doc.filename}  ·  {doc.file_type.value.upper()}  ·  {doc.page_count} page(s)"):
            if doc.metadata:
                st.caption(" | ".join(f"{k}: {v}" for k, v in doc.metadata.items()))
            for page in doc.pages:
                st.markdown(f"**Page {page.number}**")
                if page.text:
                    preview = page.text[:2000]
                    st.text(preview + ("…" if len(page.text) > 2000 else ""))
                for table in page.tables:
                    st.markdown(table.to_markdown())
