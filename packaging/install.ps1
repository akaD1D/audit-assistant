# ============================================================================
# AI Audit Assistant — first-run setup (executed by the installer)
#
# Installs everything the app needs on a fresh Windows PC:
#   1. Python 3.12 (via winget, user scope) if missing
#   2. A private virtual environment + Python dependencies
#   3. Ollama (local AI runtime) if missing
#   4. The AI models (qwen2.5:7b text + minicpm-v vision, ~10 GB total)
#   5. Seeds the Knowledge Base with the bundled audit standards
#
# Safe to re-run: every step detects what is already installed and skips it.
# Usage:  powershell -ExecutionPolicy Bypass -File install.ps1 [-SkipModels]
# ============================================================================
param(
    [switch]$SkipModels,
    [switch]$NoPrompt   # unattended mode (testing/CI): no final keypress
)

$ErrorActionPreference = "Stop"
$App = Split-Path -Parent $PSScriptRoot   # {app} dir = parent of packaging\

function Step($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "    OK: $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "    NOTE: $msg" -ForegroundColor Yellow }

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   AI Audit Assistant - Setup"                 -ForegroundColor Cyan
Write-Host "   This may take 10-30 minutes on first run"   -ForegroundColor Cyan
Write-Host "   (Python packages + ~10 GB of AI models)"    -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# --- 1. Python 3.12 ---------------------------------------------------------
Step "Checking Python 3.12"
$Python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
if (-not (Test-Path $Python)) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd -and ((& $cmd.Source --version) -match "3\.1[2-9]")) { $Python = $cmd.Source }
}
if (Test-Path $Python) {
    Ok "Found $Python"
} else {
    Step "Installing Python 3.12 (this is a one-time download)"
    winget install -e --id Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements
    $Python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    if (-not (Test-Path $Python)) { throw "Python install failed. Install Python 3.12 from python.org and re-run this setup." }
    Ok "Python installed"
}

# --- 2. Virtual environment + dependencies ----------------------------------
Step "Creating the app's Python environment"
$Venv = Join-Path $App ".venv"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $VenvPy)) { & $Python -m venv $Venv }
Ok "Environment ready"

Step "Installing Python packages (a few minutes on first run)"
& $VenvPy -m pip install --upgrade pip --quiet
& $VenvPy -m pip install -r (Join-Path $App "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Package installation failed. Check your internet connection and re-run." }
Ok "Packages installed"

# --- 3. Default configuration ------------------------------------------------
Step "Writing default configuration"
$EnvFile = Join-Path $App ".env"
if (-not (Test-Path $EnvFile)) {
@"
# AI Audit Assistant - local configuration (offline mode via Ollama)
AUDIT_LLM_PROVIDER=ollama
AUDIT_OLLAMA_MODEL=qwen2.5:7b
AUDIT_OLLAMA_VISION_MODEL=minicpm-v
AUDIT_OLLAMA_BASE_URL=http://localhost:11434
AUDIT_EMBEDDING_BACKEND=local
"@ | Out-File -FilePath $EnvFile -Encoding ascii
    Ok "Created .env (offline Ollama mode)"
} else { Ok ".env already exists - keeping your settings" }

# --- 4. Ollama (local AI runtime) --------------------------------------------
Step "Checking Ollama (runs the AI on your PC)"
$Ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
if (-not (Test-Path $Ollama)) {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { $Ollama = $cmd.Source }
}
if (Test-Path $Ollama) {
    Ok "Found Ollama"
} else {
    Step "Installing Ollama"
    winget install -e --id Ollama.Ollama --accept-source-agreements --accept-package-agreements
    $Ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    if (-not (Test-Path $Ollama)) { Warn "Ollama install could not be verified. Install it from ollama.com, then re-run this setup." }
    else { Ok "Ollama installed" }
}

# --- 5. AI models (the big download) -----------------------------------------
if (-not $SkipModels -and (Test-Path $Ollama)) {
    Step "Downloading AI models (~10 GB total - please be patient)"
    Write-Host "    Text model  : qwen2.5:7b (~4.7 GB)"
    & $Ollama pull qwen2.5:7b
    Write-Host "    Vision model: minicpm-v (~5.5 GB, reads invoices/receipts)"
    & $Ollama pull minicpm-v
    Ok "Models ready"
} elseif ($SkipModels) {
    Warn "Skipped model downloads (-SkipModels)."
}

# --- 6. Seed the Knowledge Base with audit standards --------------------------
Step "Loading audit standards into the Knowledge Base (IFRS/IAS/ISA/COSO/SOX)"
$Standards = Join-Path $App "knowledge_sources\standards"
if (Test-Path $Standards) {
    Push-Location $App
    try {
        & $VenvPy (Join-Path $App "scripts\ingest_folder.py") $Standards
        Ok "Standards loaded"
    } catch {
        Warn "Could not pre-load standards ($_). The app will still work; you can add them later."
    } finally { Pop-Location }
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "   Setup complete!"                            -ForegroundColor Green
Write-Host "   Double-click 'AI Audit Assistant' on your"  -ForegroundColor Green
Write-Host "   desktop to start the app."                  -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
if (-not $NoPrompt) { Read-Host "Press Enter to close this window" }
