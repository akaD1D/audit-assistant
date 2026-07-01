"""Bulk-ingest a folder of documents into the persistent knowledge base.

Recursively finds every supported file under a folder and ingests it (parse ->
chunk -> embed -> persist to Qdrant + SQLite). Ingested documents stay searchable
across sessions, forming the assistant's knowledge base (e.g. IFRS/IAS/ISA texts
you are licensed to use, plus public Saudi company reports).

Usage (from the project root):
    .\\.venv\\Scripts\\python.exe scripts\\ingest_folder.py "C:\\path\\to\\reports"

Notes:
    - PDFs/Word/Excel/CSV/TXT are embedded locally (free, no API calls).
    - Images call the vision model (uses Gemini quota) — keep those separate if
      you want a purely offline/free bulk load.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the project root importable when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit_assistant.core.container import get_container  # noqa: E402
from audit_assistant.infrastructure.parsers.base import supported_extensions  # noqa: E402
from audit_assistant.services.bulk_ingest import discover_files  # noqa: E402


def main(folder_arg: str) -> int:
    folder = Path(folder_arg)
    if not folder.is_dir():
        print(f"Not a folder: {folder}")
        return 1

    container = get_container()
    extensions = {f".{e}" for e in supported_extensions()}
    files = discover_files(folder, extensions)
    if not files:
        print(f"No supported documents found under {folder}.")
        print(f"Supported extensions: {', '.join(sorted(extensions))}")
        return 0

    already = container.document_repository.existing_filenames()
    print(f"Found {len(files)} document(s). Ingesting into the knowledge base…\n")
    ok = fail = skip = 0
    for i, path in enumerate(files, start=1):
        if path.name in already:
            print(f"[{i}/{len(files)}] SKIP {path.name} (already in knowledge base)")
            skip += 1
            continue
        try:
            data = path.read_bytes()
            doc = container.ingestion_service.ingest(filename=path.name, data=data)
            container.audit_log.record("kb_ingest", path.name)
            print(f"[{i}/{len(files)}] OK   {path.name} — {doc.page_count} page(s)")
            ok += 1
        except Exception as exc:  # noqa: BLE001 - keep going on individual failures
            print(f"[{i}/{len(files)}] FAIL {path.name}: {exc}")
            fail += 1

    total = container.document_repository.count()
    print(
        f"\nDone. {ok} ingested, {skip} skipped, {fail} failed. "
        f"Knowledge base now holds {total} document(s)."
    )
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('Usage: python scripts/ingest_folder.py "C:\\path\\to\\folder"')
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
