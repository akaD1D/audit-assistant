# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A local, single-user **AI Audit Assistant**: a Streamlit app that ingests documents (PDF/Excel/CSV/Word/images/TXT), answers audit questions grounded in them via RAG (with source + page citations and a confidence level), performs deterministic audit calculations, validates datasets, and exports reports. Default LLM is Google Gemini behind a provider-agnostic layer; embeddings are local and free.

## Commands

The interpreter is the project venv — always call it explicitly (Windows):

```bash
.venv/Scripts/python.exe -m pytest                       # full test suite
.venv/Scripts/python.exe -m pytest tests/test_calculations.py::test_materiality   # single test
.venv/Scripts/python.exe -m pytest -m "not slow"         # skip model-downloading e2e tests
.venv/Scripts/python.exe -m ruff check .                 # lint (config in pyproject.toml)
.venv/Scripts/python.exe -m mypy audit_assistant         # type check
```

Run the app (must run from the project root — see gotchas):

```powershell
.\run.ps1                                                # or:
.\.venv\Scripts\streamlit.exe run streamlit_app.py
```

Bulk knowledge-base tooling (stop the app first — Qdrant is single-process):

```bash
.venv/Scripts/python.exe scripts/download_sources.py     # download URLs in knowledge_sources/report_urls.txt
.venv/Scripts/python.exe scripts/ingest_folder.py "knowledge_sources/standards"   # index a folder (idempotent)
```

## Architecture (the big picture)

**Clean, layered, dependency arrows point inward.** `app` (Streamlit UI, thin) → `services` (business logic) → `domain` (dataclasses + `interfaces.py` ports) ← `infrastructure` (adapters implementing those ports). Services depend on the Protocol ports in `domain/interfaces.py`, never on concrete infrastructure — so providers/stores swap without touching business logic.

**`core/container.py` is the composition root.** `Container` builds and wires every service/adapter lazily via `cached_property`; `get_container()` returns the process-wide singleton. The UI resolves everything through the container — **when adding a service, wire it here**, not in the UI.

**Anti-hallucination is the central invariant, enforced two ways:**
1. **All audit maths are deterministic Python** in `audit/calculations/` (pure functions returning `CalculationResult` with step-by-step working). The LLM never computes numbers — it only routes/explains. `services/calculation_service.py` holds the catalog + history.
2. **Answers are RAG-grounded and must cite** `document + page + confidence`, enforced by the system prompt in `audit/prompts/system.py`. When retrieval is empty the model must say so, not invent.

**RAG pipeline:** `ingestion_service` (validate → parse → [images: vision-transcribe] → persist → index) → `services/chunking.py` (page-tagged, structure-aware) → local **fastembed** embeddings → **Qdrant** embedded store → `rag_service.retrieve` → `chat_service` assembles the grounded prompt → `LLMProvider`. Chat can scope to the current session's uploads or the entire persistent knowledge base.

**Provider abstraction:** `infrastructure/llm/` has adapters (Gemini default, plus OpenAI/Anthropic/Ollama) behind the `LLMProvider` port, selected by `factory.build_llm_provider` from `AUDIT_LLM_PROVIDER`. `FakeLLMProvider` is the deterministic test double.

**Persistence:** SQLite (`infrastructure/db.py` + repositories) holds document metadata, calculation history, and the audit log; Qdrant holds vectors; raw upload bytes go to disk. Everything lives under `data/` (gitignored) and the knowledge base persists across sessions.

**Config:** `core/config.py` uses pydantic-settings with the `AUDIT_` env prefix, loaded from `.env`. Access via `get_settings()` only.

## Non-obvious gotchas

- **Run from the project root.** pydantic-settings loads `.env` relative to the current working directory; running elsewhere means no API key.
- **Qdrant local mode is single-process.** The Streamlit app and the ingest scripts cannot open the storage simultaneously — stop one before running the other.
- **Streamlit sys.path:** Streamlit only adds the script's own dir to `sys.path`. Launch via `streamlit_app.py` (project root) or `app/main.py` (which has a path bootstrap) — not a bare module import.
- **Gemini model choice:** the configured key's `gemini-2.0-*` models return 429 (quota); use `gemini-2.5-flash` (the default). Free tier is ~20 req/min — `GeminiProvider.complete`/`complete_with_images` retry with backoff, but the **streaming path does not**.
- **Local embedding model** (fastembed `BAAI/bge-small-en-v1.5`) downloads on first use into `data/models`; HuggingFace symlinks are disabled for Windows compatibility.
- **Phases 0–2 need no API key** (parsing + retrieval are local). Only chat, report generation, and image transcription call Gemini — and image ingestion spends vision quota per image.

## Testing conventions

- Parser tests build **real** files in-memory (`tests/conftest.py` generates valid PDF/XLSX/DOCX/PNG bytes); LLM/retriever tests use `FakeLLMProvider` and small stubs.
- The `slow` marker denotes end-to-end tests that download the embedding model.
- `pyproject.toml` sets `pythonpath = ["."]` so tests import `audit_assistant` directly.
