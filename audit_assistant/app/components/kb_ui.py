"""Knowledge Base management page: view, search, filter, rename, replace,
re-index, and delete permanently-saved documents (with confirmation)."""

from __future__ import annotations

import streamlit as st

from audit_assistant.core.logging import get_logger

log = get_logger(__name__)

_ACCEPTED = ["pdf", "xlsx", "xls", "csv", "docx", "txt", "png", "jpg", "jpeg"]
_TYPE_ICON = {
    "pdf": "📕", "xlsx": "📊", "xls": "📊", "csv": "📈",
    "docx": "📘", "txt": "📄", "png": "🖼️", "jpg": "🖼️", "jpeg": "🖼️",
}


def _fmt_size(n: int | None) -> str:
    if not n:
        return "—"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _fmt_date(iso: str) -> str:
    return iso.replace("T", " ")[:16] if iso else "—"


@st.dialog("Rename document")
def _rename_dialog(container, doc: dict) -> None:
    new_name = st.text_input("New name", value=doc["filename"])
    if st.button("Save", type="primary"):
        container.kb_service.rename(doc["document_id"], new_name)
        st.rerun()


@st.dialog("Delete document")
def _delete_dialog(container, doc: dict) -> None:
    st.warning(
        f"Permanently delete **{doc['filename']}**?\n\n"
        "This removes the document, its embeddings, and its stored file. "
        "This cannot be undone."
    )
    c1, c2 = st.columns(2)
    if c1.button("🗑️ Delete", type="primary", use_container_width=True):
        container.kb_service.delete(doc["document_id"])
        container.audit_log.record("kb_delete", doc["filename"])
        st.rerun()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()


@st.dialog("Replace document")
def _replace_dialog(container, doc: dict) -> None:
    st.caption(f"Upload a new version of **{doc['filename']}** — the old embeddings "
               "are removed and the document keeps its identity.")
    new_file = st.file_uploader("New version", type=_ACCEPTED, key=f"replace_{doc['document_id']}")
    if new_file and st.button("Replace", type="primary"):
        with st.spinner("Replacing and re-indexing…"):
            container.kb_service.replace(
                doc["document_id"], filename=new_file.name, data=new_file.getvalue()
            )
            container.audit_log.record("kb_replace", new_file.name)
        st.rerun()


def render_knowledge_base(container) -> None:
    st.subheader("📚 Knowledge Base")
    st.caption("Permanently saved documents — searchable in every session.")

    docs = container.kb_service.list()
    if not docs:
        st.info("No documents saved yet. Upload a file from the sidebar and choose "
                "**Add to Knowledge Base**.")
        return

    col1, col2 = st.columns([2, 1])
    query = col1.text_input("🔎 Search by name", placeholder="e.g. IFRS, invoice, SABIC…")
    all_types = sorted({d["file_type"] for d in docs})
    selected = col2.multiselect("Filter by type", all_types, default=all_types)

    filtered = [
        d for d in docs
        if query.lower() in d["filename"].lower() and d["file_type"] in selected
    ]
    st.caption(f"Showing {len(filtered)} of {len(docs)} document(s).")

    for doc in filtered:
        icon = _TYPE_ICON.get(doc["file_type"], "📄")
        status = "✅ Indexed" if doc.get("chunks") else "⚠️ Not indexed"
        header = (
            f"{icon}  {doc['filename']}  ·  {doc['file_type'].upper()}  ·  "
            f"{_fmt_size(doc['size_bytes'])}  ·  {status}"
        )
        with st.expander(header):
            meta_cols = st.columns(4)
            meta_cols[0].metric("Pages", doc["pages"])
            meta_cols[1].metric("Chunks", doc.get("chunks") or 0)
            meta_cols[2].metric("Size", _fmt_size(doc["size_bytes"]))
            meta_cols[3].metric("Added", _fmt_date(doc["created_at"]))

            if doc.get("metadata"):
                extra = {k: v for k, v in doc["metadata"].items() if k != "chunks"}
                if extra:
                    st.caption("Metadata: " + " · ".join(f"{k}: {v}" for k, v in extra.items()))

            b1, b2, b3, b4 = st.columns(4)
            if b1.button("✏️ Rename", key=f"rn_{doc['document_id']}", use_container_width=True):
                _rename_dialog(container, doc)
            if b2.button("🔄 Replace", key=f"rp_{doc['document_id']}", use_container_width=True):
                _replace_dialog(container, doc)
            if b3.button("♻️ Re-index", key=f"ri_{doc['document_id']}", use_container_width=True):
                with st.spinner("Re-indexing…"):
                    n = container.kb_service.reindex(doc["document_id"])
                st.success(f"Re-indexed into {n} chunk(s).")
            if b4.button("🗑️ Delete", key=f"dl_{doc['document_id']}", use_container_width=True):
                _delete_dialog(container, doc)
