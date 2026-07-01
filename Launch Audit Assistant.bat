@echo off
title AI Audit Assistant
echo ============================================
echo    AI Audit Assistant is starting...
echo    Your browser will open in a few seconds.
echo.
echo    Keep this window open while you work.
echo    Close it (or press Ctrl+C) to stop.
echo ============================================
echo.

REM Make sure the Ollama background server is running (safe if already up).
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe" (
    start "" "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"
)

REM Launch the app from its project folder.
cd /d "%~dp0"
".venv\Scripts\streamlit.exe" run "streamlit_app.py"

echo.
echo App stopped. You can close this window.
pause
