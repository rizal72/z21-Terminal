# z21-Terminal PC PowerShell profile functions
# SINGLE SOURCE OF TRUTH - git-tracked, deployable with git pull.
# The user profile (Documents\PowerShell\Microsoft.PowerShell_profile.ps1)
# only dot-sources this file. To recover on a fresh PC: clone the repo,
# restore the profile dot-source line, reopen PowerShell.

# Git autocompletion (posh-git)
Import-Module posh-git

# Interactive mode - see logs in real-time, Ctrl+C to stop (no Y/N prompt)
function z21-backend {
    Set-Location C:\z21-Terminal\backend
    & ..\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level warning --reload
}

# View backend logs in real-time (Ctrl+C to stop)
function z21-log {
    Get-Content C:\z21-Terminal\backend.log -Wait -Tail 200
}

# Background mode - Task Scheduler (survives SSH close, truly detached)
function z21-start {
    # Check if task already exists and is running
    $task = Get-ScheduledTask -TaskName "z21-backend" -ErrorAction SilentlyContinue
    if ($task -and $task.State -eq 'Running') {
        Write-Host "Backend already running" -ForegroundColor Yellow
        return
    }

    # Register task if not exists
    if (-not $task) {
        $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\z21-Terminal\start-backend.ps1"
        $principal = New-ScheduledTaskPrincipal -UserId (whoami) -LogonType Interactive -RunLevel Highest
        Register-ScheduledTask -TaskName "z21-backend" -Action $action -Principal $principal -Force | Out-Null
    }

    # Start task
    Start-ScheduledTask -TaskName "z21-backend"
    Start-Sleep -Milliseconds 500  # Wait for task to start

    Write-Host "Backend started via Task Scheduler (survives SSH close)" -ForegroundColor Green
    Write-Host "Log file: C:\z21-Terminal\backend.log"
    Write-Host "View logs: z21-log"
    Write-Host "Stop: z21-stop"
}

# Restart backend - stop and restart via Task Scheduler
function z21-restart {
    Write-Host "Restarting backend..." -ForegroundColor Yellow
    z21-stop
    Start-Sleep -Seconds 1
    z21-start
}

# Stop backend - stops Task Scheduler task and kills Python processes
function z21-stop {
    Write-Host ""
    Write-Host "=== Stopping z21-Terminal Backend ===" -ForegroundColor Yellow
    Write-Host ""

    # Stop scheduled task if running
    $task = Get-ScheduledTask -TaskName "z21-backend" -ErrorAction SilentlyContinue
    if ($task -and $task.State -eq 'Running') {
        Stop-ScheduledTask -TaskName "z21-backend"
        Write-Host "Scheduled task stopped" -ForegroundColor Green
        Start-Sleep -Milliseconds 500
    }

    # Kill any remaining Python processes (cleanup)
    $processes = Get-Process python -ErrorAction SilentlyContinue
    if ($processes) {
        Stop-Process -Name python -Force
        Write-Host "Backend processes cleaned up" -ForegroundColor Green
        Start-Sleep -Seconds 1
    } else {
        Write-Host "No Python processes found" -ForegroundColor Yellow
    }
    Write-Host ""
}

# === z21-Terminal Deployment (Common Helper) ===
function Deploy-Z21Terminal {
    param(
        [string]$Branch
    )

    Write-Host ""
    $branchDisplay = if ($Branch -eq "main") { "Production" } else { "Development" }
    Write-Host "=== z21-Terminal $branchDisplay Deployment ($Branch) ===" -ForegroundColor Cyan
    Write-Host ""

    Set-Location C:\z21-Terminal

    Write-Host "[1/4] Switching to $Branch branch..." -ForegroundColor Yellow
    git checkout $Branch
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Could not switch to $Branch branch!" -ForegroundColor Red
        return
    }

    Write-Host "[2/4] Resetting to origin/$Branch..." -ForegroundColor Yellow
    git fetch origin
    git reset --hard origin/$Branch
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Git sync failed!" -ForegroundColor Red
        return
    }
    Write-Host "Synced to origin/$Branch (config.json reset, config.local.json preserved)" -ForegroundColor Green

    Write-Host ""
    Write-Host "[3/4] Building frontend..." -ForegroundColor Yellow
    Set-Location web
    npm install
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Frontend build failed!" -ForegroundColor Red
        return
    }
    Set-Location C:\z21-Terminal

    Write-Host ""
    Write-Host "[4/4] Restarting backend..." -ForegroundColor Yellow
    z21-restart

    Write-Host ""
    Write-Host "=== $branchDisplay Deployment Complete! ===" -ForegroundColor Green
    Write-Host "Branch: $Branch | Config: config.json + config.local.json override" -ForegroundColor Gray
    Write-Host ""
}

# Production deployment (main branch)
function z21-deploy {
    Deploy-Z21Terminal -Branch "main"
}

# Development deployment (develop branch)
function z21-deploy-dev {
    Deploy-Z21Terminal -Branch "develop"
}

# Frontend dev server
function z21-frontend {
    Set-Location C:\z21-Terminal\web
    npm run dev -- --host
}

# Git check for updates
function git-check {
    Write-Host "Fetching updates..." -ForegroundColor Cyan
    git fetch
    $behind = git rev-list HEAD..origin/main --count
    if ($behind -gt 0) {
        Write-Host "Branch is $behind commits behind origin/main" -ForegroundColor Yellow
        git log HEAD..origin/main --oneline
    } else {
        Write-Host "Branch is up to date" -ForegroundColor Green
    }
}

# Backend status check
function z21-status {
    $task = Get-ScheduledTask -TaskName "z21-backend" -ErrorAction SilentlyContinue
    if ($task) {
        $state = $task.State
        if ($state -eq 'Running') {
            Write-Host "[OK] Backend ATTIVO (Task Scheduler: $state)" -ForegroundColor Green
            $pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
            if ($pythonProcesses) {
                $pythonProcesses | Select-Object Id, ProcessName, StartTime
            }
        } else {
            Write-Host "[X] Backend NON ATTIVO (Task State: $state)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[X] Backend task not registered (run z21-start to create)" -ForegroundColor Red
    }
}
