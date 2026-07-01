"""Download public report PDFs listed in knowledge_sources/report_urls.txt.

Reads one URL per line (optionally ``url|filename.pdf``), downloads each into
knowledge_sources/reports/ with a browser-like User-Agent, and skips files that
already exist. Then run scripts/ingest_folder.py to index them.

Usage (from project root):
    .\\.venv\\Scripts\\python.exe scripts\\download_sources.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
URL_FILE = ROOT / "knowledge_sources" / "report_urls.txt"
DEST = ROOT / "knowledge_sources" / "reports"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _parse_lines(text: str) -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            url, name = line.split("|", 1)
            out.append((url.strip(), name.strip()))
        else:
            out.append((line, None))
    return out


def main() -> int:
    if not URL_FILE.exists():
        print(f"URL list not found: {URL_FILE}")
        return 1
    DEST.mkdir(parents=True, exist_ok=True)
    entries = _parse_lines(URL_FILE.read_text(encoding="utf-8"))
    if not entries:
        print("No URLs to download.")
        return 0

    ok = fail = skip = 0
    with httpx.Client(follow_redirects=True, timeout=420.0, headers=_HEADERS) as client:
        for i, (url, name) in enumerate(entries, start=1):
            filename = name or (url.split("/")[-1].split("?")[0] or f"file_{i}.pdf")
            target = DEST / filename
            if target.exists():
                print(f"[{i}/{len(entries)}] SKIP {filename} (already downloaded)")
                skip += 1
                continue
            try:
                resp = client.get(url)
                resp.raise_for_status()
                target.write_bytes(resp.content)
                print(f"[{i}/{len(entries)}] OK   {filename} ({len(resp.content) / 1e6:.1f} MB)")
                ok += 1
            except Exception as exc:  # noqa: BLE001
                print(f"[{i}/{len(entries)}] FAIL {url}: {exc}")
                fail += 1

    print(f"\nDone. {ok} downloaded, {skip} skipped, {fail} failed. Folder: {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
