# GPU Deployment Guide - z21-Terminal su PC Windows

**Obiettivo**: Spostare backend + YOLO tracking su PC Windows con GPU dedicata per ridurre CPU usage da 800% a ~100%.

**Vantaggi**:
- ✅ YOLO inference 3-5x più veloce (GPU vs CPU)
- ✅ CPU usage: 800% → 100% (~87% riduzione)
- ✅ Zero freeze video (GPU parallelizza tutto)
- ✅ Mac libero per frontend + altre task

**Timeline**: ~2-3 ore setup iniziale

---

## 🖥️ Hardware Requirements

### PC Windows
- **GPU**: NVIDIA GTX 1050 Ti o superiore (6GB+ VRAM raccomandato)
- **RAM**: 8GB minimo, 16GB raccomandato
- **Storage**: 10GB free per Python + dependencies
- **Network**: Stesso network del Mac (WiFi/Ethernet) o Tailscale

### Verifica GPU NVIDIA

```powershell
# Apri Task Manager → Performance → GPU
# Oppure da terminale PowerShell:
nvidia-smi
```

Se vedi info GPU (nome, VRAM, driver version) → ✅ pronto per CUDA

---

## 📡 Step 1: Abilita SSH su Windows

### OpenSSH Server (Windows 10/11 built-in)

1. **Installa OpenSSH Server**:
   ```powershell
   # Apri PowerShell come Amministratore
   Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
   ```

2. **Avvia servizio SSH**:
   ```powershell
   Start-Service sshd
   Set-Service -Name sshd -StartupType 'Automatic'
   ```

3. **Configura firewall**:
   ```powershell
   # Regola automatica creata da OpenSSH, verifica:
   Get-NetFirewallRule -Name *ssh*
   ```

4. **Testa connessione dal Mac**:
   ```bash
   # Dal Mac:
   ssh username@192.168.1.xxx  # IP del PC Windows
   # Password: la tua password Windows
   ```

5. **Setup SSH passwordless (raccomandato)**:
   ```bash
   # Dal Mac - copia chiave pubblica su PC
   ssh-copy-id username@192.168.1.xxx
   # Inserisci password Windows una sola volta

   # Testa connessione passwordless
   ssh username@192.168.1.xxx
   # Deve entrare senza chiedere password ✅
   ```

   **Alternativa manuale** (se ssh-copy-id non funziona):
   ```bash
   # Dal Mac - mostra chiave pubblica
   cat ~/.ssh/id_rsa.pub
   # Copia output (inizia con "ssh-rsa ...")

   # Sul PC Windows (PowerShell come Amministratore)
   # Crea file authorized_keys
   New-Item -Path $env:USERPROFILE\.ssh -ItemType Directory -Force
   Add-Content -Path $env:USERPROFILE\.ssh\authorized_keys -Value "INCOLLA_CHIAVE_PUBBLICA_QUI"

   # Fix permessi (CRITICO per Windows)
   icacls $env:USERPROFILE\.ssh\authorized_keys /inheritance:r
   icacls $env:USERPROFILE\.ssh\authorized_keys /grant:r "$env:USERNAME:(R)"
   ```

   **Verifica finale**:
   ```bash
   # Dal Mac
   ssh username@192.168.1.xxx
   # Deve entrare senza password ✅
   ```

---

## 🌐 Step 2: Network Setup

### Opzione A: Stesso Network Locale (più semplice)

**Verifica che Mac e PC siano sulla stessa rete**:
```bash
# Dal Mac
ping 192.168.1.xxx  # IP del PC

# Dal PC (PowerShell)
ping 192.168.1.36   # IP del Mac (esempio)
```

**Pro**: Zero configurazione, veloce
**Contro**: Funziona solo a casa

### Opzione B: Tailscale con Serve (✅ raccomandato - già in uso sul Mac)

**Setup Tailscale** (5 minuti):
1. Installa su entrambi: https://tailscale.com/download
2. Login con stesso account
3. Dispositivi connessi automaticamente via VPN mesh

**Configura Tailscale Serve sul PC** (espone backend via HTTPS):

```powershell
# Sul PC Windows (dopo aver avviato backend sulla porta 8000)
tailscale serve --bg --https 8000 http://localhost:8000

# Verifica configurazione
tailscale serve status

# Output atteso:
# https://gaming-pc.tail9350d7.ts.net:8000 (tailnet only)
# |-- / proxy http://localhost:8000
```

**URL backend accessibile**: `https://gaming-pc.tail9350d7.ts.net:8000`

**Configurazione persiste dopo reboot** ✅

**📝 Nota URL Tailscale**:
- **Mac**: `https://mbp16diriccardo.tail9350d7.ts.net` (frontend Vite porta 5173)
- **Mac Backend API**: `https://mbp16diriccardo.tail9350d7.ts.net:8000` (quando backend Mac è running)
- **PC Windows**: `https://gaming-pc.tail9350d7.ts.net:8000` (backend production)

**Pro**:
- Funziona ovunque (casa, remoto, rete diversa)
- HTTPS automatico con certificati Tailscale
- URL stabile con DNS automatico
- Zero configurazione firewall/router
- Mac/iPad accedono seamlessly

**Contro**:
- Overhead VPN minimo (~5-10ms latency)

---

## 🐍 Step 3: Python + GPU Environment Setup

1. **Installa Python 3.11**:
   - Download: https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" durante install

2. **Installa CUDA Toolkit** (richiesto per PyTorch GPU):
   - Download: https://developer.nvidia.com/cuda-downloads
   - Versione: CUDA 11.8 o 12.1 (verifica compatibilità GPU)
   - Installa con opzioni default

3. **Verifica CUDA**:
   ```powershell
   nvcc --version  # Deve mostrare versione CUDA
   ```

4. **Installa cuDNN** (optional ma raccomandato):
   - Download: https://developer.nvidia.com/cudnn
   - Extract + copy files in CUDA directory

---

## 📦 Step 4: Clone Repository + Dependencies

### Dal PC Windows (PowerShell)

```powershell
# Clone repository
git clone git@github.com:rizal72/z21-Terminal.git
cd z21-Terminal

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt

# CRITICAL: Install PyTorch with GPU support
# Vedi: https://pytorch.org/get-started/locally/
# Esempio per CUDA 11.8:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Verifica PyTorch GPU

```python
# Python shell
import torch
print(torch.cuda.is_available())  # Deve essere True
print(torch.cuda.get_device_name(0))  # Nome GPU
```

Se `True` → ✅ GPU ready!

---

## 📹 Step 5: Camera RTSP Accessibility

**Verifica che PC possa accedere alla camera Tapo**:

```powershell
# Windows PowerShell
Test-NetConnection -ComputerName 192.168.1.4 -Port 554
```

Se "Connection successful" → ✅ Camera accessibile

**Se camera NON accessibile**:
- Verifica firewall PC
- Verifica che camera e PC siano stesso network/VLAN

---

## 🚀 Step 6: Run Backend su PC

### Setup Config Files

1. **Copy camera config**:
   ```powershell
   Copy-Item camera_config.json.example camera_config.json
   # Edit con username/password camera usando notepad
   notepad camera_config.json
   ```

2. **Copy gate config** (se non esiste):
   ```powershell
   # Copia dal Mac via SCP o crea nuovo
   ```

### Start Backend

```powershell
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000

# Oppure con auto-reload per development:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Note**:
- `--host 0.0.0.0` espone su tutte le interfacce (accessibile da Mac)
- Default `127.0.0.1` funziona SOLO locale

### Verifica Backend Running

```powershell
# Dal PC stesso (PowerShell)
Invoke-WebRequest -Uri http://localhost:8000/api/consists

# Dal Mac (per testare accessibilità remota)
curl http://PC_IP:8000/api/consists
# Deve restituire JSON con consists
```

---

## 🌐 Step 7: Frontend Options

### Opzione A: Frontend su Mac (✅ raccomandato)

**Pro**: Zero modifiche, Mac gestisce UI solo

#### Se usi Tailscale (raccomandato):

```bash
# Sul Mac - il frontend si connette automaticamente al backend PC via Tailscale
cd web

# Edit .env (se non esiste, crealo)
echo "VITE_API_URL=https://gaming-pc.tail9350d7.ts.net:8000" > .env

# Oppure modifica vite.config.js per usare Tailscale URL:
export default defineConfig({
  server: {
    proxy: {
      '/api': 'https://gaming-pc.tail9350d7.ts.net:8000',
      '/ws': {
        target: 'wss://gaming-pc.tail9350d7.ts.net:8000',
        ws: true,
        changeOrigin: true
      }
    }
  }
})

# Start frontend
npm run dev

# Accesso: http://localhost:5173
```

**Nota**: Gli URL Tailscale sono già configurati con il nome del tuo PC: `gaming-pc.tail9350d7.ts.net`

#### Se usi IP locale (stesso network):

```bash
# Sul Mac
cd web

# Edit vite.config.js
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://192.168.1.xxx:8000',  // ← IP locale del PC
      '/ws': {
        target: 'ws://192.168.1.xxx:8000',
        ws: true
      }
    }
  }
})

# Start frontend
npm run dev
```

### Opzione B: Frontend su PC

```bash
# Sul PC
cd web
npm install
npm run dev -- --host 0.0.0.0

# Accedi da Mac/iPad
http://PC_IP:5173

# Oppure via Tailscale (se configurato anche frontend con serve):
tailscale serve --bg --https 5173 http://localhost:5173
# Accesso: https://gaming-pc.tail9350d7.ts.net
```

---

## 📊 Performance Attese

### Prima (Mac CPU solo)
- **CPU**: 800% (8 core al 100%)
- **YOLO FPS**: ~15-20 FPS
- **Freeze**: 30-50ms durante Δt calculation
- **Fan**: Rumoroso costante

### Dopo (PC GPU)
- **PC CPU**: ~100% (1-2 core)
- **PC GPU**: ~30-40% (YOLO parallelizzato)
- **YOLO FPS**: ~50-60 FPS (3x più veloce)
- **Freeze**: ~5-10ms (GPU non blocca)
- **Mac CPU**: ~10% (solo frontend React)

**Risparmio energetico**: ~70W Mac → ~150W PC (ma PC più performante)

---

## 🐛 Troubleshooting

### PyTorch non rileva GPU

**Problema**: `torch.cuda.is_available() = False`

**Soluzioni**:
1. Verifica driver NVIDIA:
   ```powershell
   nvidia-smi  # Deve funzionare
   ```

2. Reinstalla PyTorch con CUDA:
   ```powershell
   pip uninstall torch torchvision
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```

3. Verifica versione CUDA compatibile:
   ```python
   import torch
   print(torch.version.cuda)  # Deve matchare CUDA installata
   ```

### Backend non accessibile da Mac

**Problema**: `Connection refused` quando Mac cerca di connettersi

**Soluzioni**:
1. Verifica firewall PC:
   ```powershell
   # Windows - aggiungi regola
   New-NetFirewallRule -DisplayName "Python Backend" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
   ```

2. Verifica backend usa `--host 0.0.0.0`:
   ```powershell
   uvicorn main:app --host 0.0.0.0 --port 8000  # NOT 127.0.0.1
   ```

3. Test manuale:
   ```powershell
   # Dal PC stesso (PowerShell)
   Invoke-WebRequest -Uri http://localhost:8000/api/consists

   # Dal Mac
   curl http://PC_IP:8000/api/consists
   ```

### Camera RTSP non raggiungibile

**Problema**: PC non riesce a connettersi a camera

**Soluzioni**:
1. Verifica routing:
   ```powershell
   tracert 192.168.1.4  # Windows PowerShell
   ```

2. Prova VLC per testare stream:
   ```
   Media → Open Network Stream
   rtsp://user:pass@192.168.1.4:554/stream2
   ```

3. Se PC su WiFi diverso/VLAN:
   - Sposta PC su stesso network del Mac
   - O configura router per permettere routing tra VLAN

---

## ⚙️ Setup Production Deploy Script

**Due opzioni disponibili**:
- **Opzione A**: PowerShell Functions (funzionano SOLO in PowerShell)
- **Opzione B**: Batch Files (funzionano in cmd.exe E PowerShell) ← **raccomandato per chi è abituato a cmd.exe**

### Opzione A: PowerShell Profile Functions

```powershell
# Apri PowerShell profile
notepad $PROFILE
# Se file non esiste: New-Item -Path $PROFILE -ItemType File -Force

# Aggiungi queste funzioni:

# Start backend (manual mode)
function z21-backend {
    Set-Location "C:\path\to\z21-Terminal\backend"
    .\venv\Scripts\Activate.ps1
    uvicorn main:app --host 0.0.0.0 --port 8000
}

# Start backend with auto-reload (development)
function z21-backend-reload {
    Set-Location "C:\path\to\z21-Terminal\backend"
    .\venv\Scripts\Activate.ps1
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
}

# Production deployment (pull + build + restart)
function z21-deploy {
    $ProjectRoot = "C:\path\to\z21-Terminal"
    Set-Location $ProjectRoot

    Write-Host "`n🚀 z21-Terminal Production Deployment" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    # Pull latest code from main branch
    Write-Host "📥 Pulling latest code from main..." -ForegroundColor Yellow
    git pull origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Git pull failed!" -ForegroundColor Red
        return
    }

    # Build frontend
    Write-Host "`n📦 Building frontend production bundle..." -ForegroundColor Yellow
    Set-Location "$ProjectRoot\web"

    # Install/update npm dependencies if package.json changed
    $packageChanged = git diff HEAD@{1} HEAD --name-only | Select-String "package.json"
    if ($packageChanged) {
        Write-Host "   📦 package.json changed, running npm install..." -ForegroundColor Yellow
        npm install
    }

    # Build production bundle (creates dist/ folder)
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Frontend build failed!" -ForegroundColor Red
        return
    }

    # Update backend dependencies
    Write-Host "`n🐍 Updating backend dependencies..." -ForegroundColor Yellow
    Set-Location "$ProjectRoot\backend"
    ..\venv\Scripts\Activate.ps1
    pip install -r requirements.txt --quiet

    # Kill existing backend process
    Write-Host "`n🔄 Stopping existing backend..." -ForegroundColor Yellow
    Get-Process | Where-Object {$_.ProcessName -eq "python" -and $_.Path -like "*z21-Terminal*"} | Stop-Process -Force
    Start-Sleep -Seconds 2

    # Start backend (production mode - serves dist/)
    Write-Host "`n✅ Starting backend in production mode..." -ForegroundColor Green
    Set-Location "$ProjectRoot\backend"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectRoot\backend'; ..\venv\Scripts\Activate.ps1; uvicorn main:app --host 0.0.0.0 --port 8000"

    Write-Host "`n✅ Deployment complete!" -ForegroundColor Green
    Write-Host "   Backend + Frontend: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "   Tailscale URL: https://gaming-pc.tail9350d7.ts.net:8000" -ForegroundColor Cyan
}

# Salva e ricarica profile
. $PROFILE
```

### Sostituisci Path

**IMPORTANTE**: Cambia `C:\path\to\z21-Terminal` con il path reale del tuo PC.

**Pro**:
- ✅ Sintassi moderna e potente
- ✅ Output colorato e formattato
- ✅ Gestione errori avanzata

**Contro**:
- ❌ Funziona SOLO in PowerShell (non in cmd.exe)
- ❌ Più lento da avviare
- ❌ Richiede apprendimento PowerShell syntax

**Usage**:
```powershell
# Solo da PowerShell
z21-backend
z21-deploy
```

---

### Opzione B: Batch Files nel PATH (raccomandato per cmd.exe)

**Setup**:

1. **Crea directory scripts**:
   ```cmd
   mkdir C:\Scripts
   ```

2. **Crea file `C:\Scripts\z21-backend.bat`**:
   ```batch
   @echo off
   cd /d C:\z21-Terminal\backend
   call venv\Scripts\activate.bat
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. **Crea file `C:\Scripts\z21-backend-reload.bat`**:
   ```batch
   @echo off
   cd /d C:\z21-Terminal\backend
   call venv\Scripts\activate.bat
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Crea file `C:\Scripts\z21-deploy.bat`**:
   ```batch
   @echo off
   cd /d C:\z21-Terminal
   echo.
   echo === z21-Terminal Production Deployment ===
   echo.

   echo [1/4] Pulling latest code from main...
   git pull origin main
   if errorlevel 1 (
       echo ERROR: Git pull failed!
       pause
       exit /b 1
   )

   echo.
   echo [2/4] Building frontend...
   cd web
   call npm install
   call npm run build
   if errorlevel 1 (
       echo ERROR: Frontend build failed!
       pause
       exit /b 1
   )

   echo.
   echo [3/4] Updating backend dependencies...
   cd ..\backend
   call ..\venv\Scripts\activate.bat
   pip install -r requirements.txt --quiet

   echo.
   echo [4/4] Restarting backend...
   taskkill /F /IM python.exe 2>nul
   timeout /t 2 >nul

   echo.
   echo Starting backend in new window...
   start "z21-Backend" cmd /k "cd /d C:\z21-Terminal\backend && call venv\Scripts\activate.bat && uvicorn main:app --host 0.0.0.0 --port 8000"

   echo.
   echo === Deployment Complete! ===
   echo Backend + Frontend: http://localhost:8000
   echo Tailscale URL: https://gaming-pc.tail9350d7.ts.net:8000
   echo.
   pause
   ```

5. **Aggiungi `C:\Scripts` al PATH**:
   ```
   1. Win + X → System
   2. Advanced system settings
   3. Environment Variables
   4. System variables → Path → Edit
   5. New → C:\Scripts
   6. OK tutto
   7. Riavvia cmd.exe/PowerShell
   ```

**Pro**:
- ✅ Funziona da cmd.exe E PowerShell
- ✅ Sintassi familiare (batch DOS)
- ✅ Veloce da avviare
- ✅ Facile da modificare (notepad)

**Contro**:
- ❌ Output meno formattato (no colori)
- ❌ Gestione errori più semplice

**Usage**:
```cmd
:: Funziona da cmd.exe
z21-backend
z21-deploy

:: Funziona anche da PowerShell
z21-backend
z21-deploy
```

---

### Confronto Opzioni

| Feature | PowerShell Functions | Batch Files |
|---------|---------------------|-------------|
| Funziona in cmd.exe | ❌ | ✅ |
| Funziona in PowerShell | ✅ | ✅ |
| Output colorato | ✅ | ❌ |
| Sintassi familiare DOS | ❌ | ✅ |
| Velocità startup | Media | Veloce |
| Facile da modificare | Media | ✅ |

**Raccomandazione**: Se sei abituato a cmd.exe → **Opzione B (Batch Files)**

---

## 📋 Development vs Production Setup

### Architettura Ibrida

Il backend FastAPI supporta **automaticamente** due modalità:

#### Development Mode (Mac)

```bash
# Mac - nessun dist/ folder
cd z21-Terminal
z21  # Backend porta 8000 + Vite dev server porta 5173
```

**Comportamento**:
- `web/dist/` **NON esiste** (gitignored)
- Backend FastAPI: API only (porta 8000)
- Frontend Vite: Hot Module Replacement (porta 5173)
- CORS aperto per localhost:5173 → localhost:8000

**Console output**:
```
⚠️  Development mode: Frontend dist not found
   Expected: /path/to/z21-Terminal/web/dist
   Use Vite dev server: cd web && npm run dev
   Access dashboard at: http://localhost:5173
```

#### Production Mode (PC Windows)

```powershell
# PC Windows - dist/ folder esiste
cd z21-Terminal
z21-deploy  # Pull + Build + Restart
```

**Comportamento**:
- `web/dist/` **esiste** (generato da `npm run build` su PC)
- Backend FastAPI: API + static files (porta 8000)
- Frontend: Minified production bundle servito da FastAPI
- Tutto accessibile da porta 8000 unica

**Console output**:
```
✅ Production mode: Serving frontend from /path/to/z21-Terminal/web/dist
   Access dashboard at: http://localhost:8000
```

### File Structure

```
z21-Terminal/
├── backend/
│   └── main.py              # Conditional serving logic
├── web/
│   ├── dist/                # ❌ gitignored (PC only)
│   ├── src/                 # ✅ in git
│   ├── package.json         # ✅ in git
│   └── vite.config.js       # ✅ in git
└── .gitignore               # dist/ excluded
```

### Conditional Serving Logic

**In `backend/main.py`** (già implementato):

```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# ... dopo tutte le route API ...

frontend_dist = Path(__file__).parent.parent / "web" / "dist"
if frontend_dist.exists() and frontend_dist.is_dir():
    # Production mode
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    print("✅ Production mode: Serving frontend from dist/")
else:
    # Development mode
    print("⚠️  Development mode: Use Vite dev server")
```

**Vantaggi**:
- ✅ Zero configurazione diversa tra dev/prod
- ✅ Detection automatico modalità
- ✅ Mac workflow invariato (Vite HMR)
- ✅ PC serve tutto da porta 8000
- ✅ dist/ mai su git (no conflitti)

---

## 🔄 Workflow Quotidiano

### Workflow Production (PC Windows)

#### Prima configurazione

```powershell
# Clone repository
git clone git@github.com:rizal72/z21-Terminal.git
cd z21-Terminal

# Checkout main branch (production)
git checkout main

# Setup Python environment
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt

# Setup Node.js environment
cd web
npm install
cd ..

# First deployment
z21-deploy
```

#### Aggiornamenti successivi

```powershell
# Quando Mac ha pushato nuove feature su main
z21-deploy  # Pull + Build + Restart

# Output:
# 🚀 z21-Terminal Production Deployment
# ========================================
# 📥 Pulling latest code from main...
# 📦 Building frontend production bundle...
# 🐍 Updating backend dependencies...
# 🔄 Stopping existing backend...
# ✅ Starting backend in production mode...
# ✅ Deployment complete!
#    Backend + Frontend: http://localhost:8000
#    Tailscale URL: https://gaming-pc.tail9350d7.ts.net:8000
```

**Accesso Production**:
- Locale: http://localhost:8000
- Tailscale: https://gaming-pc.tail9350d7.ts.net:8000
- Tutto servito da porta 8000 (backend + frontend)

### Workflow Development (Mac)

```bash
# Lavora su develop branch
git checkout develop

# Sviluppo normale
z21  # Backend porta 8000 + Vite porta 5173

# Commit e push
git add .
git commit -m "feat: ..."
git push origin develop

# Quando pronto per production
git checkout main
git merge develop
git push origin main

# PC fa pull automatico con z21-deploy
```

**Accesso Development**:
- Frontend: http://localhost:5173 (Vite HMR)
- Backend API: http://localhost:8000

### Stop Backend

**PC**:
```powershell
# Trova processo Python
Get-Process | Where-Object {$_.ProcessName -eq "python"}

# Killalo
Stop-Process -Name python -Force

# Oppure Ctrl+C nel terminal backend
```

---

## 🌿 Git Branch Strategy

### Setup Branches

```bash
# Mac - Development
git checkout develop  # Default branch per sviluppo

# PC - Production
git checkout main  # Branch stabile per production
```

### Workflow Completo

```
┌──────────────┐                 ┌──────────────┐
│     Mac      │                 │  PC Windows  │
│  (develop)   │                 │    (main)    │
└──────────────┘                 └──────────────┘
       │                                │
       │ 1. Develop features            │
       ├─────────────►                  │
       │ git add/commit/push            │
       │                                │
       │ 2. Ready for prod              │
       ├─────────────►                  │
       │ git checkout main              │
       │ git merge develop              │
       │ git push origin main           │
       │                                │
       │                          3. Deploy
       │                          ◄─────────┤
       │                          z21-deploy
       │                                │
       │                          4. Running
       │                          ◄─────────┤
       │                       Production on GPU
```

**Vantaggi**:
- ✅ Mac: sperimenta liberamente su develop
- ✅ PC: sempre stabile su main
- ✅ Zero rischio deploy code non testato
- ✅ Rollback facile: git checkout main && git pull

---

## 🎯 Next Steps

Dopo setup funzionante:

1. **Alias PowerShell** per start rapido (già implementato sopra ✅)
2. **Test production deployment**:
   ```powershell
   z21-deploy  # Prima volta
   # Verifica: http://localhost:8000
   ```
3. **Autostart backend** su PC Windows con Task Scheduler:
   - Apri Task Scheduler
   - Create Task: "z21-Terminal Backend"
   - Trigger: At startup
   - Action: Start PowerShell script con `z21-backend`
4. **Monitoring tools** (GPU usage, temperature):
   - Task Manager → Performance → GPU
   - MSI Afterburner (opzionale)
5. **Backup config** (gate_config.json, camera_config.json):
   - Questi file NON sono in git
   - Copia manualmente da Mac a PC la prima volta
   - Backup periodico raccomandato

---

## 📝 Note Finali

### Quando conviene GPU deployment

**✅ Setup raccomandato se**:
- Hai PC Windows con GPU NVIDIA disponibile
- Mac troppo lento (800% CPU) / fan rumoroso
- Vuoi YOLO più veloce (tracking più preciso)
- Vuoi production setup separato da development

**❌ Rimani su Mac se**:
- Non hai GPU NVIDIA (solo Intel/AMD)
- PC Windows non sempre acceso
- Setup troppo complesso per uso occasionale
- Sviluppo solo/testing

### Riepilogo Setup Finale

**Mac** (Development):
- Branch: `develop`
- Mode: Development (Vite HMR)
- Accesso: http://localhost:5173
- CPU usage: 800% (accettabile per dev)

**PC Windows** (Production):
- Branch: `main`
- Mode: Production (dist/ servito da FastAPI)
- Accesso: http://localhost:8000 o https://gaming-pc.tail9350d7.ts.net:8000
- CPU usage: ~100% (GPU offload)
- Deployment: `z21-deploy` (un comando)

**Git Sync**:
- Codice: sincronizzato automaticamente via git
- Config files (camera, gate): copia manuale prima volta
- Frontend build: generato su PC (mai su git)

### Alternative

- **Cloud GPU** (Google Colab, AWS) - più complesso, costo mensile
- **Raspberry Pi 5 + Coral TPU** - basso consumo ma meno potente
- **Mac M1/M2 con Metal acceleration** - da testare PyTorch MPS

---

## 📚 Riferimenti

- **Tailscale Serve**: https://tailscale.com/kb/1242/tailscale-serve
- **PyTorch GPU**: https://pytorch.org/get-started/locally/
- **FastAPI StaticFiles**: https://fastapi.tiangolo.com/tutorial/static-files/
- **Vite Production Build**: https://vitejs.dev/guide/build.html

---

**Ultimo aggiornamento**: 2025-01-02
**Status**: ✅ **Implementato** (conditional serving + deploy script ready)
