# GPU Deployment Guide - z21-Terminal su PC Windows

## ✅ **STATUS: COMPLETED & OPERATIONAL** (2025-01-03)

**Sistema attualmente in produzione**:
- ✅ Backend running su PC Windows (porta 8000)
- ✅ YOLO tracking su GPU NVIDIA
- ✅ Tailscale Serve: https://hostname.tailXXXXXX.ts.net
- ✅ Frontend servito da FastAPI (production mode)
- ✅ CPU usage ridotto da 800% → ~100% (87% riduzione)
- ✅ Deployment script `z21-deploy` funzionante

---

**Obiettivo**: Spostare backend + YOLO tracking su PC Windows con GPU dedicata per ridurre CPU usage da 800% a ~100%.

**Vantaggi**:
- ✅ YOLO inference 3-5x più veloce (GPU vs CPU)
- ✅ CPU usage: 800% → 100% (~87% riduzione)
- ✅ Zero freeze video (GPU parallelizza tutto)
- ✅ Mac libero per frontend + altre task

**Timeline effettiva**: ~2-3 ore setup (COMPLETATO)

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

**✅ STATUS: COMPLETATO** (2025-01-06)
- SSH passwordless configurato (Mac + Termius)
- PasswordAuthentication disabilitata (solo chiavi SSH)
- Sicurezza ottimizzata (no attacchi brute force)

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

5. **Setup SSH passwordless (raccomandato)** ✅:

   **⚠️ IMPORTANTE: Location diversa per utenti Administrator**

   Se il tuo utente Windows è nel gruppo Administrators, il file authorized_keys è in:
   ```
   C:\ProgramData\ssh\administrators_authorized_keys
   ```

   Se è utente normale (non admin), il file è in:
   ```
   C:\Users\username\.ssh\authorized_keys
   ```

   **Setup per utenti Administrator** (questo setup):

   ```bash
   # 1. Dal Mac - mostra chiave pubblica
   cat ~/.ssh/id_rsa.pub
   # Copia output (inizia con "ssh-rsa ...")

   # 2. Copia su file temporaneo
   cat ~/.ssh/id_rsa.pub > /tmp/mac_key.txt

   # 3. Trasferisci su PC
   scp /tmp/mac_key.txt username@192.168.1.xxx:C:/Users/username/

   # 4. Sul PC (PowerShell come Amministratore) - aggiungi al file admin
   Get-Content C:/Users/username/mac_key.txt | Out-File -FilePath C:/ProgramData/ssh/administrators_authorized_keys -Append -Encoding utf8

   # 5. Fix permessi (CRITICO)
   icacls C:\ProgramData\ssh\administrators_authorized_keys /inheritance:r
   icacls C:\ProgramData\ssh\administrators_authorized_keys /grant BUILTIN\Administrators:F
   icacls C:\ProgramData\ssh\administrators_authorized_keys /grant "NT AUTHORITY\SYSTEM":F

   # 6. Verifica permessi
   icacls C:\ProgramData\ssh\administrators_authorized_keys
   # Output atteso:
   # BUILTIN\Administrators:(F)
   # NT AUTHORITY\SYSTEM:(F)
   ```

   **Setup per utenti normali** (alternativa):

   ```bash
   # Dal Mac - usa ssh-copy-id (funziona per utenti non-admin)
   ssh-copy-id username@192.168.1.xxx
   # Inserisci password Windows una sola volta

   # Oppure manualmente:
   # 1. Mostra chiave
   cat ~/.ssh/id_rsa.pub

   # 2. Sul PC (PowerShell)
   New-Item -Path $env:USERPROFILE\.ssh -ItemType Directory -Force
   Add-Content -Path $env:USERPROFILE\.ssh\authorized_keys -Value "INCOLLA_CHIAVE_PUBBLICA_QUI"

   # 3. Fix permessi
   icacls $env:USERPROFILE\.ssh\authorized_keys /inheritance:r
   icacls $env:USERPROFILE\.ssh\authorized_keys /grant:r "$env:USERNAME:(R)"
   ```

6. **Riavvia servizio SSH** (necessario per caricare authorized_keys):
   ```powershell
   # Sul PC (PowerShell come Amministratore)
   Restart-Service sshd
   ```

7. **Verifica connessione passwordless**:
   ```bash
   # Dal Mac
   ssh username@192.168.1.xxx
   # Deve entrare senza chiedere password ✅
   ```

8. **Disabilita password authentication (raccomandato per sicurezza)** ✅:
   ```powershell
   # Sul PC (PowerShell come Amministratore)

   # 1. Modifica sshd_config
   (Get-Content C:/ProgramData/ssh/sshd_config) -replace '#PasswordAuthentication yes', 'PasswordAuthentication no' | Set-Content C:/ProgramData/ssh/sshd_config

   # 2. Verifica modifica
   Get-Content C:/ProgramData/ssh/sshd_config | Select-String "PasswordAuthentication"
   # Output: PasswordAuthentication no

   # 3. Riavvia servizio
   Restart-Service sshd

   # 4. Testa connessione con chiave
   # Dal Mac: ssh username@192.168.1.xxx
   # Deve funzionare senza password ✅
   ```

   **Vantaggi**:
   - ✅ Solo autenticazione chiavi SSH (no password)
   - ✅ Elimina attacchi brute force
   - ✅ Più sicuro (chiavi 2048+ bit)

   **Precauzione**: Backup chiavi private (Mac + mobile devices)

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

# IMPORTANTE: Servono DUE configurazioni per frontend + WebSocket

# 1. Porta 443 default (frontend - URL pulito senza porta)
tailscale serve --https=443 --bg http://localhost:8000

# 2. Porta 8000 (WebSocket - necessaria per connessioni WS)
tailscale serve --https=8000 --bg http://localhost:8000

# Verifica configurazione
tailscale serve status

# ⚠️ IMPORTANTE: I certificati HTTPS vengono generati AUTOMATICAMENTE da Tailscale Serve
# Non serve usare "tailscale cert" - il comando serve solo per server web personalizzati (nginx, Caddy, etc.)
# Tailscale Serve gestisce i certificati Let's Encrypt in automatico (validità: 90 giorni, rinnovo automatico)

# Output atteso:
# https://hostname.tailXXXXXX.ts.net (tailnet only)
# |-- / proxy http://localhost:8000
#
# https://hostname.tailXXXXXX.ts.net:8000 (tailnet only)
# |-- / proxy http://localhost:8000
```

**URL frontend accessibile**: `https://hostname.tailXXXXXX.ts.net` (senza porta!)
**URL WebSocket**: `wss://hostname.tailXXXXXX.ts.net:8000/ws` (con porta 8000)

**Configurazione persiste dopo reboot** ✅

**📝 Nota URL Tailscale**:
- **Mac**: `https://hostname.tailXXXXXX.ts.net` (frontend Vite porta 5173)
- **Mac Backend API**: `https://hostname.tailXXXXXX.ts.net:8000` (quando backend Mac è running)
- **PC Windows**: `https://hostname.tailXXXXXX.ts.net` (backend production - URL pulito senza porta!)
- **PC WebSocket**: `wss://hostname.tailXXXXXX.ts.net:8000/ws` (porta 8000 necessaria per WS)

**Pro**:
- Funziona ovunque (casa, remoto, rete diversa)
- HTTPS automatico con certificati Tailscale
- URL stabile con DNS automatico
- Zero configurazione firewall/router
- Mac/iPad accedono seamlessly
- **URL pulito senza porta** (443 → 8000 proxy automatico)

**Contro**:
- Overhead VPN minimo (~5-10ms latency)

### Differenza Mac vs PC (Importante!)

**Mac** (Development):
- Frontend Vite: porta 5173
- Backend FastAPI: porta 8000
- Due servizi separati → **NON serve** `tailscale serve` per Mac

**PC** (Production):
- Backend FastAPI (porta 8000) serve TUTTO (frontend + API + WebSocket)
- Frontend servito da `web/dist/` (production build)
- **Richiede** `tailscale serve` per esporre HTTPS

**Nota**: La sintassi corretta usa `=`:
```powershell
# ✅ CORRETTO
tailscale serve --https=443 --bg http://localhost:8000

# ❌ SBAGLIATO (senza =)
tailscale serve --bg --https 443 http://localhost:8000
```

### Reinstallazione Tailscale

Se reinstalli Tailscale o sostituisci il dispositivo, la configurazione `tailscale serve` viene persa.

**Riconfigurazione** (da eseguire dopo reinstallazione):
```powershell
# 1. Reset configurazione precedente
tailscale serve reset

# 2. Riconfigura con sintassi corretta
tailscale serve --https=443 --bg http://localhost:8000
tailscale serve --https=8000 --bg http://localhost:8000

# 3. Verifica
tailscale serve status
```

⚠️ **NOTA IMPORTANTE**: Non usare `tailscale cert` per generare certificati manualmente!
- `tailscale cert` serve SOLO per server web personalizzati (nginx, Caddy, Apache)
- `tailscale serve` gestisce i certificati AUTOMATICAMENTE (Let's Encrypt, validità 90 giorni)
- Il comando `tailscale cert` genererà file `.crt` e `.key` nella directory corrente, ma questi NON vengono usati da `tailscale serve`

### Opzione C: LAN Access Diretto (senza Tailscale) ✅

**Setup**: Richiede apertura porta firewall Windows (one-time setup)

```powershell
# Sul PC Windows (PowerShell come Amministratore)
New-NetFirewallRule -DisplayName "z21-Terminal Backend" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

**URL frontend accessibile (LAN locale)**: `http://192.168.1.3:8000` (porta esplicita richiesta)
**URL alternativo**: `http://hostname.local:8000` (se hostname risolve)

**Pro**:
- Zero overhead (no VPN tunnel)
- Più veloce (connessione LAN diretta)
- No dipendenze Tailscale
- Funziona anche se Tailscale spento

**Contro**:
- Funziona SOLO sulla rete locale (a casa)
- HTTP non criptato (no HTTPS)
- Porta esplicita :8000 richiesta (browser non assume default 80/443)

**Quando usarlo**:
- Development locale rapido
- Troubleshooting Tailscale
- Massime performance (no VPN overhead)

**📝 Confronto URL**:
| Modalità | URL Frontend | Porta | Protocollo | Funziona Remoto? |
|----------|--------------|-------|------------|------------------|
| **Tailscale** | `https://hostname.tailXXXXXX.ts.net` | Implicita (443 → 8000) | HTTPS | ✅ Sì |
| **LAN diretta** | `http://192.168.1.3:8000` | Esplicita (:8000) | HTTP | ❌ No (solo locale) |

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
pip install -r backend\requirements.txt
pip install -r scripts\requirements.txt
pip install -r requirements-gpu.txt  # PyTorch GPU with CUDA 11.8
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

## 📋 Step 5: Copy Configuration Files from Mac to PC

**IMPORTANTE**: Il PC Windows necessita di alcuni file di configurazione e stato che non sono committati su git (gitignored per sicurezza/privacy).

### File da Copiare (TUTTI necessari)

| File | Percorso Mac | Percorso PC | Descrizione |
|------|--------------|-------------|-------------|
| **camera_config.json** | `~/Documents/projects/z21-Terminal/` | `C:\z21-Terminal\` | Credenziali camera RTSP |
| **JMRI Roster** | `~/Library/Preferences/JMRI/.../roster/` | `C:\Users\<username>\Library\Preferences\JMRI\.../roster\` | Roster locomotive e consist |

**Note**: `consist_state.json` è deprecato (migrato in `config.json` che è tracciato da git)

### Comandi di Copia

**Dal Mac** (esegui questi comandi):

```bash
# 1. Camera config (credenziali RTSP)
scp ~/Documents/projects/z21-Terminal/camera_config.json user@192.168.1.3:C:/z21-Terminal/

# 2. JMRI Roster (locomotive configuration)
# 2a. Crea tar del roster
cd ~/Library/Preferences/JMRI/La_mia_Ferrovia_in_JMRI.jmri
tar czf /tmp/roster.tar.gz roster/

# 2b. Copia tar su PC
scp /tmp/roster.tar.gz user@192.168.1.3:C:/Users/<username>/

# 2c. Estrai su PC (esegui su PC via SSH)
ssh user@192.168.1.3 'mkdir -p "C:\Users\<username>\Library\Preferences\JMRI\La_mia_Ferrovia_in_JMRI.jmri" && cd "C:\Users\<username>\Library\Preferences\JMRI\La_mia_Ferrovia_in_JMRI.jmri" && tar xzf C:\Users\<username>\roster.tar.gz'
```

### Verifica File Copiati

**Sul PC** (PowerShell):

```powershell
# Verifica tutti i file necessari esistono
Test-Path C:\z21-Terminal\camera_config.json
Test-Path "C:\Users\<username>\Library\Preferences\JMRI\La_mia_Ferrovia_in_JMRI.jmri\roster\consist\consist.xml"

# Output atteso: True per entrambi
```

**Note**: Lo stato Virtual Mode (virtual_mode, auto_compensation_enabled) è ora salvato in `config.json` che è tracciato da git, quindi viene copiato automaticamente con `git pull`.

---

## 📹 Step 6: Camera RTSP Accessibility

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

## 🚀 Step 7: Run Backend su PC

### Start Backend

**IMPORTANTE**: Prima verifica che tutti i file di Step 5 siano stati copiati!

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

## 🌐 Step 8: Frontend Options

### Opzione A: Frontend su Mac (✅ raccomandato)

**Pro**: Zero modifiche, Mac gestisce UI solo

#### Se usi Tailscale (raccomandato):

```bash
# Sul Mac - il frontend si connette automaticamente al backend PC via Tailscale
cd web

# Edit .env (se non esiste, crealo)
echo "VITE_API_URL=https://hostname.tailXXXXXX.ts.net:8000" > .env

# Oppure modifica vite.config.js per usare Tailscale URL:
export default defineConfig({
  server: {
    proxy: {
      '/api': 'https://hostname.tailXXXXXX.ts.net:8000',
      '/ws': {
        target: 'wss://hostname.tailXXXXXX.ts.net:8000',
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

**Nota**: Gli URL Tailscale sono già configurati con il nome del tuo PC: `hostname.tailXXXXXX.ts.net`

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
tailscale serve --https=5173 --bg http://localhost:5173
# Accesso: https://hostname.tailXXXXXX.ts.net
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
   pip install -r requirements-gpu.txt
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

## ⚙️ Setup PowerShell Aliases

**✅ STATUS: IMPLEMENTATO** (2025-01-07)

Tutti i comandi sono implementati come **funzioni PowerShell** nel `$PROFILE`. Niente file .bat, tutto gestito tramite PowerShell.

### Setup PowerShell Profile

Il file `$PROFILE` contiene le funzioni z21 e viene caricato automaticamente ad ogni avvio di PowerShell.

**Location**: `C:\Users\<username>\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`

**Contenuto completo**:

```powershell
# z21-Terminal aliases (PowerShell functions)

# Interactive mode - see logs in real-time, Ctrl+C to stop (no Y/N prompt)
# Auto-reload enabled for local development
function z21-backend {
    Set-Location C:\z21-Terminal\backend
    & ..\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
}

# Background mode - Task Scheduler (survives SSH close, truly detached)
# Uses start-backend.ps1 script launched by Windows Task Scheduler
function z21-start {
    # Check if task already exists and is running
    $task = Get-ScheduledTask -TaskName "z21-backend" -ErrorAction SilentlyContinue
    if ($task -and $task.State -eq 'Running') {
        Write-Host "Backend already running" -ForegroundColor Yellow
        return
    }

    # Register task if not exists (auto-create on first run)
    if (-not $task) {
        $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\z21-Terminal\start-backend.ps1"
        $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest
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

# Check backend status (via Task Scheduler)
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

# View backend logs in real-time (tail -f equivalent)
function z21-log {
    Get-Content C:\z21-Terminal\backend.log -Wait -Tail 50
}

# Production deployment - git pull + stop backend + build frontend + auto-start backend
function z21-deploy {
    Write-Host ""
    Write-Host "=== z21-Terminal Production Deployment ===" -ForegroundColor Cyan
    Write-Host ""

    Set-Location C:\z21-Terminal

    # Step 1: Git checkout main + pull
    Write-Host "[1/4] Switching to main and pulling latest code..." -ForegroundColor Yellow
    git checkout main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Could not switch to main branch!" -ForegroundColor Red
        return
    }
    git pull origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Git pull failed!" -ForegroundColor Red
        return
    }

    # Step 2: Stop backend
    Write-Host ""
    Write-Host "[2/4] Stopping backend..." -ForegroundColor Yellow
    $processes = Get-Process python -ErrorAction SilentlyContinue
    if ($processes) {
        Stop-Process -Name python -Force
        Write-Host "Backend stopped" -ForegroundColor Green
    } else {
        Write-Host "No backend running" -ForegroundColor Yellow
    }

    # Step 3: Build frontend
    Write-Host ""
    Write-Host "[3/4] Building frontend..." -ForegroundColor Yellow
    Set-Location web
    npm install
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Frontend build failed!" -ForegroundColor Red
        return
    }

    # Step 4: Start backend in background
    Write-Host ""
    Write-Host "[4/4] Starting backend..." -ForegroundColor Yellow
    Set-Location C:\z21-Terminal
    z21-start

    # Info
    Write-Host ""
    Write-Host "=== Deployment Complete! ===" -ForegroundColor Green
    Write-Host "Backend running in background" -ForegroundColor Green
    Write-Host ""
}

# Frontend dev server
function z21-frontend {
    Set-Location C:\z21-Terminal\web
    npm run dev -- --host
}
```

### Ricaricare Profile

Dopo modifiche al `$PROFILE`, ricarica senza riavviare PowerShell:

```powershell
. $PROFILE
```

### Comandi Disponibili

| Comando | Modalità | Descrizione | Usa quando |
|---------|----------|-------------|------------|
| **`z21-backend`** | Interactive | Log real-time, Ctrl+C per fermare (no prompt Y/N) | Debug locale, vuoi vedere log |
| **`z21-start`** | Background | Task Scheduler (truly detached, survives SSH close) | Production via SSH dal Mac |
| **`z21-stop`** | - | Stops Task Scheduler task + kills Python processes | Fermare backend |
| **`z21-status`** | - | Check backend status (via Task Scheduler state) | Verificare se backend è running |
| **`z21-log`** | Interactive | Tail -f backend.log (real-time) | Vedere log in tempo reale |
| **`z21-restart`** | Background | Stop + restart via Task Scheduler | Backend già running, vuoi restart |
| **`z21-deploy`** | Deployment | Git pull + stop + build frontend + auto-start backend | Full deployment (tutto automatico) |
| **`z21-frontend`** | Interactive | Vite dev server (porta 5173) | Development frontend |

### Caratteristiche Chiave

**✅ No "Terminate batch job (Y/N)?" prompt**:
- Funzioni PowerShell eseguono direttamente Python (no .bat wrapper)
- Ctrl+C ferma uvicorn immediatamente

**✅ Background mode truly detached** (2025-01-09):
- `z21-start` usa **Windows Task Scheduler** invece di `Start-Process`
- Task "z21-backend" creato automaticamente al primo avvio
- Backend **veramente detached**: sopravvive a SSH close, logout, reboot (se configurato)
- Script `start-backend.ps1` eseguito dal Task Scheduler
- Log salvati in `C:\z21-Terminal\backend.log`

**✅ TAB completion intelligente**:
- Digita `z21-` e premi TAB per ciclare tra comandi
- Ordine: backend, frontend, reload, start, stop

**✅ Auto-reload su sviluppo locale** (2025-01-09):
- Flag `--reload` attivo SOLO su `z21-backend` (interactive mode)
- `z21-start` (background production) NO `--reload` per stabilità logging
- Motivo: `--reload` + `Tee-Object` causano interruzioni log file
- Production workflow: `git pull` → `z21-restart` (1 comando, stabile)

---

## 🔄 Update Workflow

### Backend-Only Changes (modifiche file `.py`)

**Production via SSH** (configurazione stabile):

```powershell
# Dal Mac via SSH
ssh user@hostname
cd C:\z21-Terminal
git pull
z21-restart  # Riavvia backend (~2s)
```

**Perché z21-restart è necessario:**
- `z21-start` (background) non usa `--reload` per stabilità logging
- `--reload` + `Tee-Object` causano interruzioni nel file di log
- `z21-restart` è veloce (1 comando) e garantisce log stabili

**Dev locale su PC:**
```powershell
z21-backend  # Interactive mode con --reload attivo
# Modifiche .py → auto-reload automatico
```

### Full Deployment (backend + frontend)

```powershell
# Usa z21-deploy per rebuild completo
z21-deploy
```

**Quando usare `z21-deploy`:**
- ✅ Modifiche frontend (`web/` directory)
- ✅ Modifiche dipendenze (`requirements*.txt`)
- ✅ Modifiche config critici (struttura `config.json`)

**Quando basta `git pull + z21-restart`:**
- ✅ Modifiche solo backend (`.py` files)

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
npm run build
cd ..

# First start
z21-start
```

#### Avvio Backend in Production

**Prima volta o dopo riavvio PC**:
```powershell
# Avvia backend in background (hidden window, persiste dopo SSH close)
z21-start

# Output:
# Backend started in background (hidden window)
# Log file: C:\z21-Terminal\backend.log
# View logs: z21-log
# Stop: z21-stop
```

#### Aggiornamenti Code

**Opzione A - Solo backend modificato**:
```powershell
# Pull + restart backend (veloce, no frontend build)
cd C:\z21-Terminal
git pull origin main
z21-restart

# z21-restart fa: z21-stop → wait 1s → z21-start
```

**Opzione B - Frontend modificato (o full deployment)**:
```powershell
# Full deployment: pull + stop + build frontend + auto-start
z21-deploy

# Output:
# [1/4] Switching to main and pulling latest code...
# [2/4] Stopping backend...
# [3/4] Building frontend...
# [4/4] Starting backend...
# === Deployment Complete! ===
# Backend running in background
```

#### View Logs

**Check log in tempo reale**:
```powershell
# Con alias z21-log (last 50 lines, follow mode)
z21-log

# Oppure via SSH dal Mac
ssh user@hostname "z21-log"

# O comando manuale
Get-Content C:\z21-Terminal\backend.log -Wait -Tail 50
```

**Accesso Production**:
- Locale: http://localhost:8000
- Tailscale: https://hostname.tailXXXXXX.ts.net
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

# PC pull e reload via SSH dal Mac
```

**Accesso Development**:
- Frontend: http://localhost:5173 (Vite HMR)
- Backend API: http://localhost:8000

### Stop Backend

**Check status prima**:
```powershell
# Verifica se backend è running
z21-status

# Output se attivo:
# [OK] Backend ATTIVO (2 processo/i Python)
#   Id ProcessName StartTime
#   -- ----------- ---------
# 1234 python      1/8/2026 8:30:00 PM
# 5678 python      1/8/2026 8:30:00 PM
```

**Stop backend**:
```powershell
# PC locale
z21-stop

# Output:
# === Stopping z21-Terminal Backend ===
# Backend stopped successfully

# Da remoto via SSH dal Mac
ssh user@hostname "z21-stop"
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
       │                          3. Pull + Reload
       │                          ◄─────────┤
       │                     git pull && z21-restart
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
   z21-deploy # Pull + build + auto-start (tutto automatico)
   # Verifica: http://localhost:8000
   z21-stop   # Ferma backend
   ```
3. **Autostart backend** su PC Windows con Task Scheduler:
   - Apri Task Scheduler
   - Create Task: "z21-Terminal Backend"
   - Trigger: At startup
   - Action: Start PowerShell script con comando: `powershell -Command "& {z21-start}"`
4. **Monitoring tools** (GPU usage, temperature):
   - Task Manager → Performance → GPU
   - MSI Afterburner (opzionale)
5. **Backup config** (camera_config.json):
   - Questo file NON è in git (contiene credenziali)
   - Copia manualmente da Mac a PC la prima volta
   - Backup periodico raccomandato
   - **Note**: `consist_state.json` deprecato (migrato in `config.json` tracciato da git)

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
- Accesso: http://localhost:8000 o https://hostname.tailXXXXXX.ts.net
- CPU usage: ~100% (GPU offload)
- Comandi:
  - `z21-start` - Avvia backend in background
  - `z21-stop` - Ferma backend + cleanup porta
  - `z21-status` - Check se backend è running
  - `z21-log` - View logs real-time
  - `z21-restart` - Restart backend
  - `z21-deploy` - Full deployment (git pull + build frontend)

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

**Ultimo aggiornamento**: 2025-01-07
**Status**: ✅ **DEPLOYED & OPERATIONAL** (sistema in produzione su PC Windows)
- Backend + YOLO tracking running su GPU NVIDIA
- Tailscale Serve: https://hostname.tailXXXXXX.ts.net
- Production mode attivo (frontend servito da FastAPI)
- PowerShell aliases attivi: z21-start, z21-stop, z21-status, z21-log, z21-restart, z21-deploy, z21-backend, z21-frontend
- Background mode persiste dopo SSH close (no Y/N prompt su Ctrl+C)
