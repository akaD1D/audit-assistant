# Convenience launcher for Windows PowerShell.
# Usage:  .\run.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
& "$root\.venv\Scripts\streamlit.exe" run "$root\streamlit_app.py"
