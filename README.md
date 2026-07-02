# 🧾 AI Audit Assistant

![Python](https://img.shields.io/badge/python-3.12-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B)
![Tests](https://img.shields.io/badge/tests-78%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

A document-aware AI assistant for auditing work. Upload PDFs, Excel/CSV, Word,
images, and text; ask questions answered **from your documents** with citations
and a confidence level; run **deterministic audit calculations**; validate
datasets; and export professional reports.

> Built to **never invent numbers** — all audit math runs in plain Python, and
> every answer is grounded in retrieved document context (RAG).

## Status

Built in phases. Complete so far:

- ✅ **Phase 0** — bootstrap, scaffold, core config/logging/DI, tests
- ✅ **Phase 1** — document parsing (PDF/Excel/CSV/Word/TXT/image), secure
  upload validation, SQLite persistence, upload UI
- ✅ **Phase 2** — RAG core: structure-aware chunking, local ONNX embeddings
  (fastembed), Qdrant vector store, retrieval + **keyless semantic search UI**
- ✅ **Phase 3** — provider-agnostic LLM layer (Gemini default; OpenAI/Anthropic/
  Ollama swappable) + grounded chat with **citations & confidence** (verified live)
- ✅ **Phase 4** — image understanding: vision-LLM transcription of invoices/
  receipts/statements (amounts, dates, parties, missing-field detection) with
  Tesseract OCR fallback; image content flows into RAG (verified live)
- ✅ **Phase 5** — deterministic audit calculations engine: 28 calculations
  (materiality, MUS/attribute sampling, ratios, variance/trend/CAGR, Benford's
  Law, VAT, aging, reconciliation, risk model, inventory FIFO/WAC, payroll) with
  step-by-step working + a keyless calculator UI and saved history
- ✅ **Phase 6** — Excel workbook profiling (multi-sheet, dtypes, missing,
  duplicates, outliers, formula cells, cross-sheet compare) + dataset quality
  validator (score/grade, imbalance, leakage, bias, preprocessing & feature-eng
  suggestions, AI-training verdict)
- ✅ **Phase 7** — cross-document search: semantic + keyword + numeric value
  filter (e.g. "amount > 100,000") + LLM-powered document comparison
- ✅ **Phase 8** — report generation (executive/audit/risk/findings/observations)
  grounded in documents, exportable to **PDF, Word, and Excel** (verified live)
- ✅ **Phase 9** — hardening: persistent activity/audit log + viewer, deployment
  guide, and documented multi-user upgrade path

**All 9 phases complete · 76 tests passing.** Numbers come from Python, never the
LLM. See `../.claude/plans/*.md` for the full roadmap.

## Tech stack (lean, local, free to run)

| Concern      | Choice                                             |
|--------------|----------------------------------------------------|
| UI           | Streamlit                                          |
| RAG store    | Qdrant (local/embedded — no server, no Docker)     |
| Embeddings   | `fastembed` ONNX (local, **no API key**, no torch) |
| Chat LLM     | Google Gemini (free tier) — provider-swappable     |
| Metadata DB  | SQLite                                             |
| Parsing      | PyMuPDF, pdfplumber, python-docx, openpyxl, pandas |

Only the **chat** step needs a provider key; parsing + retrieval run offline.

## 📦 Install on Windows (easiest — no coding needed)

Download the installer and run it — the app sets itself up and runs **100%
offline and free** on your PC (no accounts, no API keys, no quotas).

**Steps:**

1. Go to **[Releases](https://github.com/akaD1D/audit-assistant/releases)** and
   download `AuditAssistant-Setup-x.x.x.exe`.
2. Double-click it.
   - If Windows shows a blue **"Windows protected your PC"** screen, click
     **More info → Run anyway** (the installer is new/unsigned — this is normal).
3. Click through the wizard and keep **"Run first-time setup now"** ticked on
   the last page.
4. A setup window opens and installs everything automatically:
   - Python 3.12 (if you don't have it)
   - The app's Python packages
   - **Ollama** — the engine that runs the AI locally on your PC
   - The AI models (**~10 GB download** — text + invoice-reading vision model)
   - Pre-loads the Knowledge Base with IFRS/IAS/ISA/COSO/SOX reference summaries
5. When it says **Setup complete**, double-click **AI Audit Assistant** on your
   desktop. Your browser opens with the app. Done. 🎉

**Requirements:** Windows 10/11 · 16 GB RAM recommended · ~15 GB free disk ·
internet needed **only during setup** (afterwards it runs fully offline).

> 💡 Prefer the cloud AI instead of local? After installing, edit the `.env`
> file in `%LOCALAPPDATA%\AuditAssistant` and set `AUDIT_LLM_PROVIDER=gemini`
> plus your free Gemini API key.

## Setup (developers)

```powershell
# 1. Create the virtual environment (Python 3.12)
python -m venv .venv

# 2. Install dependencies
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 3. (Optional now, required for chat) configure a provider
copy .env.example .env
#   then paste a free Gemini key from https://aistudio.google.com/app/apikey

# 4. Run the app
.\run.ps1
#   or: .\.venv\Scripts\streamlit.exe run audit_assistant\app\main.py
```

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Knowledge base (standards + company reports)

The assistant answers from a **persistent knowledge base** — every ingested
document stays searchable across sessions. In the Chat tab, choose **"Entire
knowledge base"** to query everything, or **"Only this session's uploads"** to
scope to what you just added.

Bulk-load documents (idempotent — safe to re-run):

```powershell
# 1. Download public report PDFs listed in knowledge_sources/report_urls.txt
.\.venv\Scripts\python.exe scripts\download_sources.py

# 2. Index a whole folder (recursively) into the knowledge base
.\.venv\Scripts\python.exe scripts\ingest_folder.py "knowledge_sources\reports"
.\.venv\Scripts\python.exe scripts\ingest_folder.py "knowledge_sources\standards"
```

A starter set is included under `knowledge_sources/`: public **IFRS/IAS/ISA/COSO/
SOX** summaries (freely licensed) and public **Saudi company reports** (SABIC,
STC, Al Rajhi). Add your own PDFs to a folder and run `ingest_folder.py` to grow it.

> ⚠️ **Copyright:** the full official IFRS/IAS/ISA texts are copyrighted — load
> only copies you are licensed to use. The included summaries are public/CC-licensed.
>
> ⚠️ **Stop the app before bulk-ingesting.** Qdrant's local storage is
> single-process — the Streamlit app and `ingest_folder.py` cannot access it at
> the same time. Close the app (Ctrl+C), run the ingest, then start the app again.

## Deploy & share (free)

Publish to **Streamlit Community Cloud** so others just open a URL:

1. Push this repo to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io), create an app pointing at
   `streamlit_app.py`.
3. In the app's **Secrets**, add your Gemini key:
   ```toml
   AUDIT_GEMINI_API_KEY = "your-key"
   AUDIT_GEMINI_MODEL = "gemini-2.5-flash"
   ```
   (Streamlit exposes secrets as env vars, which the `AUDIT_`-prefixed settings pick up.)

## Upgrade path (multi-user / production)

The layered architecture keeps this a config/adapter change, not a rewrite:

| Lean (now)                 | Production upgrade                              |
|----------------------------|------------------------------------------------|
| SQLite                     | PostgreSQL (swap `Database` + repositories)     |
| Qdrant embedded            | Qdrant/Qdrant Cloud server (swap client URL)    |
| Streamlit, single user     | FastAPI backend + React/Next.js frontend        |
| No auth                    | JWT auth + role-based permissions               |
| Local disk storage         | Encrypted object storage + antivirus scan hook  |

Services depend on `domain/interfaces.py` ports, so each row above is a new
adapter behind the same interface.

## Project layout

```
audit_assistant/
  app/             Streamlit UI (thin)
  core/            config, logging, exceptions, DI container
  domain/          entities + interfaces (ports)
  services/        business logic
  infrastructure/  parsers, embeddings, vector store, LLM, repositories
  audit/           deterministic calculations + prompt guardrails
  reports/         PDF / Word / Excel export
tests/             pytest suite
```
