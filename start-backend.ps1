# z21-Terminal Backend Startup Script
# This script is launched by Task Scheduler to run backend detached from SSH sessions

# Fix encoding for console output (PS7 compatibility)
# Forces codepage 850 instead of UTF-8 to display correctly in Task Scheduler console
[Console]::OutputEncoding = [System.Text.Encoding]::GetEncoding(850)

# Disable ANSI colors on PS7+ (plain text for DOS console compatibility)
if ($PSVersionTable.PSVersion.Major -ge 7) {
    $PSStyle.OutputRendering = 'PlainText'
}

Set-Location C:\z21-Terminal\backend

# Rotate old log before starting
# Remove old backup if exists (to avoid "file already exists" error)
if (Test-Path C:\z21-Terminal\backend.log.old) {
    Remove-Item C:\z21-Terminal\backend.log.old -Force
}
# Rotate current log to .old
if (Test-Path C:\z21-Terminal\backend.log) {
    Rename-Item C:\z21-Terminal\backend.log backend.log.old
}

& ..\venv\Scripts\python.exe -u -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level warning 2>&1 | Tee-Object -FilePath C:\z21-Terminal\backend.log
