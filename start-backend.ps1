# z21-Terminal Backend Startup Script
# This script is launched by Task Scheduler to run backend detached from SSH sessions

Set-Location C:\z21-Terminal\backend

# Rotate old log before starting
if (Test-Path C:\z21-Terminal\backend.log) {
    Rename-Item C:\z21-Terminal\backend.log backend.log.old -Force
}

& ..\venv\Scripts\python.exe -u -m uvicorn main:app --host 0.0.0.0 --port 8000 2>&1 | Tee-Object -FilePath C:\z21-Terminal\backend.log
