; ============================================================================
; AI Audit Assistant — Inno Setup installer definition
;
; Produces a small "online installer": it installs the app files + shortcuts,
; then runs packaging\install.ps1 which fetches Python deps, Ollama, and the
; AI models (large downloads happen at setup time, not inside this exe).
;
; Build:  ISCC.exe packaging\AuditAssistant.iss   (from the project root)
; Output: packaging\Output\AuditAssistant-Setup-<version>.exe
; ============================================================================

#define MyAppName "AI Audit Assistant"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "akaD1D"
#define MyAppURL "https://github.com/akaD1D/audit-assistant"

[Setup]
AppId={{6E1B2E5A-9C1D-4C61-A9D5-AUDITASSIST1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
; Per-user install: no admin rights needed, venv/data are writable.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\AuditAssistant
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=AuditAssistant-Setup-{#MyAppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "..\audit_assistant\*";               DestDir: "{app}\audit_assistant"; Flags: recursesubdirs ignoreversion; Excludes: "__pycache__\*"
Source: "..\scripts\*";                        DestDir: "{app}\scripts"; Flags: recursesubdirs ignoreversion; Excludes: "__pycache__\*"
Source: "..\knowledge_sources\standards\*";    DestDir: "{app}\knowledge_sources\standards"; Flags: recursesubdirs ignoreversion
Source: "..\assets\icon.ico";                  DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\.streamlit\config.toml";           DestDir: "{app}\.streamlit"; Flags: ignoreversion
Source: "..\streamlit_app.py";                 DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt";                 DestDir: "{app}"; Flags: ignoreversion
Source: "..\Launch Audit Assistant.bat";       DestDir: "{app}"; Flags: ignoreversion
Source: "install.ps1";                         DestDir: "{app}\packaging"; Flags: ignoreversion

[Icons]
Name: "{userdesktop}\{#MyAppName}";  Filename: "{app}\Launch Audit Assistant.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icon.ico"
Name: "{userprograms}\{#MyAppName}"; Filename: "{app}\Launch Audit Assistant.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icon.ico"

[Run]
; Post-install bootstrap: Python + deps + Ollama + models + KB seeding.
Filename: "powershell.exe"; \
    Parameters: "-ExecutionPolicy Bypass -NoProfile -File ""{app}\packaging\install.ps1"""; \
    Description: "Run first-time setup now (downloads Python packages and ~10 GB of AI models)"; \
    Flags: postinstall shellexec skipifsilent

[UninstallDelete]
; Remove everything setup created at runtime (venv, models cache, user data).
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\__pycache__"
