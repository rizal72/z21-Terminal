# z21-Terminal

Web-based DCC locomotive controller con tracking YOLO e compensazione automatica velocità.

**Progetto**: Plastico DCC - BiancAlice
**Data creazione**: 2025-12-16
**Repository**: https://github.com/rizal72/z21-Terminal (🔒 privato)

---

## 📋 Project Overview

Web-based locomotive controller featuring real-time computer vision tracking and automatic speed compensation via Z21 LAN protocol.

**Core Capabilities:**
- **Modern Web Dashboard**: Mobile-first PWA with multi-device sync, installable on tablets and smartphones for trackside operation
- **YOLO-Based Tracking**: Custom YOLOv8 model (93.1% mAP50) detects locomotives via IP camera, measures speed drift through configurable gate zones
- **Automatic Compensation**: Real-time Δt-based speed matching in Virtual Consist Mode, eliminating manual CV tuning
- **Consist Management**: Full CRUD operations via web UI - create, edit, delete consists without JMRI dependency
- **Adaptive Timing**: Supports both symmetric (oval) and asymmetric (figure-8) track geometries with single-direction gate timing

**Technical Highlights:**
- FastAPI backend with WebSocket streaming
- React + Vite frontend with Tailwind CSS
- Operations mode CV19 management (no programming track needed)
- Dynamic FPS tracking (30fps active, 1fps idle)
- Wake Lock API for uninterrupted mobile operation

**Architecture**: Originally built as JMRI extension, now increasingly independent with optional JMRI integration for initial roster import.

**Result**: Professional railway operations with smartphone convenience, combining traditional DCC control with modern web technologies and AI-powered automation.

---

## 📚 Documentazione Estesa

Per dettagli tecnici completi, vedi:
- **[docs/Z21_PROTOCOL.md](docs/Z21_PROTOCOL.md)** - Protocollo Z21 LAN (UDP) dettagliato
- **[docs/JMRI_INTEGRATION.md](docs/JMRI_INTEGRATION.md)** - Relazione con JMRI
- **[docs/CONSIST_ROSTER.md](docs/CONSIST_ROSTER.md)** - Consist 10/11 + Roster completo 7 locomotive
- **[docs/WEB_DASHBOARD.md](docs/WEB_DASHBOARD.md)** - Stack tecnologico, features, workflow development
- **[docs/COMPUTER_VISION.md](docs/COMPUTER_VISION.md)** - Sistema YOLO tracking, gate detection, Virtual Mode
- **[docs/CONSIST_MAPPING.md](docs/CONSIST_MAPPING.md)** - Logica Lead/Rear → Reference/Adjust (YOLO + Virtual Mode)
- **[docs/CONFIG_REFACTOR.md](docs/CONFIG_REFACTOR.md)** - Refactoring config.json structure (2025-01-03)
- **[docs/CHANGELOG_ARCHIVE.md](docs/CHANGELOG_ARCHIVE.md)** - Changelog 2025-12-16 → 2025-12-24

---

## Repository Git

**GitHub**: https://github.com/rizal72/z21-Terminal (🔒 privato)  
**Branch**: `develop` (lavoro), `main` (stabile)  
**Remote**: `git@github.com:rizal72/z21-Terminal.git` (SSH)

**Git Workflow**:
1. Lavoro quotidiano su `develop`
2. Merge `develop` → `main` quando pronto per release
3. **CRITICO**: Tornare sempre su `develop` dopo merge

**Git add policy**: Sempre usare `git add .`

---

## ⚠️ CRITICAL: Python Virtual Environment

**SEMPRE usare venv - Mac E PC - OGNI VOLTA che chiami python3**

Questa è una regola **NON NEGOZIABILE** per TUTTO il progetto, non solo per il refactor.

### Mac Development

**SEMPRE attivare venv prima di eseguire comandi Python**:

```bash
# Attivare venv (OBBLIGATORIO ogni volta)
source venv/bin/activate

# Poi eseguire comandi Python
python -m py_compile backend/routers/analytics.py
python scripts/utils/some_script.py
uvicorn main:app --reload
```

**Esempio - Syntax Check**:
```bash
source venv/bin/activate && python -m py_compile backend/routers/analytics.py backend/main.py
```

### PC Windows Production

**Il deployment production usa venv automaticamente** via Task Scheduler (configurato in `start-backend.ps1`).

**Per comandi manuali via SSH, attivare venv**:
```powershell
# Attivare venv (OBBLIGATORIO per comandi manuali)
.\venv\Scripts\Activate.ps1

# Poi eseguire comandi Python
python -m py_compile backend/main.py
python scripts/utils/some_script.py
```

**Nota**: Il comando `z21-restart` gestisce automaticamente venv activation via Task Scheduler.

### Perché È Importante

1. **Isolamento dipendenze**: PyTorch, ultralytics, FastAPI installati in venv, non system-wide
2. **Controllo versione Python**: Evita problemi da `brew upgrade python` su Mac
3. **Riproducibilità**: Stesso environment Mac (dev) e PC (production)
4. **Zero cognitive load**: Una volta attivato, tutti i comandi funzionano correttamente

### Cosa Succede Se Dimentichi

- ❌ **Import errors**: `ModuleNotFoundError: No module named 'fastapi'`
- ❌ **Versione Python sbagliata**: System Python 3.x invece di venv Python 3.11.x
- ❌ **Conflitti dipendenze**: Pacchetti system vs requirements progetto

**RICORDA**: Se vedi errori import Python, prima cosa da verificare: "Ho attivato venv?"

---

## Setup Hardware

**Control Station**:
- Roco Z21 Bianca (IP 192.168.1.111, porta UDP 21105)
- Serial 111466, Hardware 0x0203, Firmware 1.67

**Computer Vision**:
- Tapo IP camera (rtsp://192.168.1.4:554/stream2 - 720P)

**Production Deployment (PC Windows)**:
- Username: `riccardo@gaming-pc` (SSH access from Mac)
- **Path**: `C:\z21-Terminal` (⚠️ CRITICAL - root C:, NOT Documents!)
- OS: Windows 11
- Python: venv isolato con PyTorch GPU + CUDA 11.8
- **Shell Configuration** (hybrid setup):
  - **SSH**: PowerShell 7.5.4 (default via Registry `HKLM:\SOFTWARE\OpenSSH\DefaultShell`)
    - Better command syntax, fewer retry attempts for SSH operations
    - Profile master: `~\Documents\PowerShell\Microsoft.PowerShell_profile.ps1` (PS7)
    - Profile PS5.1: symlink → PS7 master (compatibilità legacy)
  - **Task Scheduler** (z21-backend): PowerShell 5.1 (`powershell.exe`)
    - Console window displays colors perfectly (Windows-1252 encoding)
    - PS7 shows garbled ANSI codes in Task Scheduler console (UTF-8 encoding mismatch)
    - `start-backend.ps1` has PS7 encoding fix (inactive with PS5.1, ready if needed)
  - Git autocompletion: posh-git installato su entrambi PS7 e PS5.1
- **Deployment aliases** (PowerShell):
  - `z21-deploy` - Production deploy from `main` branch
  - `z21-deploy-dev` - Development deploy from `develop` branch
  - Both use shared `Deploy-Z21Terminal` helper function (DRY)
- **Deploy workflow**:
  1. Switch to branch (main/develop)
  2. `git reset --hard origin/<branch>` (clean config.json, preserve config.local.json)
  3. Build frontend (`npm install` + `npm run build`)
  4. Restart backend (`z21-restart`)
- **⚠️ IMPORTANTE**:
  - `config.json` viene sovrascritto ad ogni deploy (`git reset --hard`)
  - `config.local.json` è **gitignored** → NON toccato da deploy (usa per override locali)
  - **CV Test Mode**: Premere T per tornare a NORMAL prima di chiudere/deployare
  - Altrimenti: disallineamento tra CV fisici (test) e config (normal)

**Software**:
- JMRI (roster/consist management)
- Python 3 (backend z21.py library)

Per dettagli protocollo Z21: vedi `docs/Z21_PROTOCOL.md`

---

## Relazione con JMRI

**z21-Terminal è un'estensione di JMRI, non un sostituto.**

- Legge roster e consist da file XML JMRI
- NON richiede JMRI in esecuzione (solo i file XML)
- Coesistenza possibile: entrambi comunicano con Z21 via UDP

**Workflow**:
1. **Setup** (JMRI DecoderPro): configura decoder, roster, consist
2. **Operations** (z21-Terminal): controllo quotidiano, automazioni Python 3
3. **Maintenance** (JMRI): modifiche CV, aggiornamenti

Per dettagli completi: vedi `docs/JMRI_INTEGRATION.md`

---

## Consist Configuration & Locomotive Roster

**2 Consist configurati** (DAC software-based):
- **Consist 10** (Tracciato Interno): Gr.675 017 (1) + D645 014 (5)
- **Consist 11** (Tracciato Esterno): E656 239 (7) + E444 056 (8)

**6 Locomotive operative** (ESU LokPilot/LokSound, Hornby TXS)

**Per dettagli completi**: vedi [docs/CONSIST_ROSTER.md](docs/CONSIST_ROSTER.md)
- Specifiche tecniche complete (decoder, CV, speed control)
- Tabella riepilogo roster
- Note decoder compatibility (CV read/write operations mode)

---

## Tool e Script

### Script Implementati

1. **read_cv_from_roster.py** - Legge CV da roster XML JMRI
2. **read_consists.py** - Visualizza configurazione consist
3. **z21.py** - Libreria completa protocollo Z21 LAN (UDP)
4. **z21_controller.py** - Controller interattivo CLI

**Metodi z21.py**:
- `get_status()`, `get_loco_info()`
- `set_loco_speed()`, `set_loco_function()`
- `write_cv_ops_mode()`, `read_cv_on_main()`
- `track_power_on/off()`, `emergency_stop_all()`

**Features Controller CLI**:
- Velocità (w/s, 0-9, \), direzione (d), emergency stop (TAB)
- Funzioni F0-F28 con Shift+A-Z hotkeys
- Polling periodico Z21 (500ms) per sync power/funzioni

Per dettagli Z21 protocol: vedi `docs/Z21_PROTOCOL.md`

---
## Web Dashboard

**Status**: ✅ **MVP COMPLETATO** (2025-12-24)
**URL locale**: http://localhost:5173
**URL Tailscale**:
- **Mac (development)**: https://mbp16diriccardo.tail9350d7.ts.net
- **PC (production)**: https://gaming-pc.tail9350d7.ts.net

### Quick Start (macOS)
```bash
z21           # Avvia backend + frontend in tab iTerm2 separate
z21-backend   # Backend FastAPI (porta 8000)
z21-frontend  # Frontend Vite (porta 5173)
```

**Venv Auto-Activation**: Gli alias in `~/.bash_aliases` attivano automaticamente `venv/` se esiste, altrimenti usano system Python. Zero cognitive load, protezione da `brew upgrade python`.

**⚠️ IMPORTANT - Frontend Changes**: Modifiche a `web/src/*` richiedono **SEMPRE rebuild** o restart dev server:
- **Development** (Mac): Restart Vite dev server (Ctrl+C + `z21-frontend`)
- **Production** (PC): `z21-deploy-dev` (pull + build + restart)
- **Backend** ha hot-reload automatico, **frontend NO** (Vite HMR non sempre affidabile per useEffect/hooks)

**Stack**: React 18.3 + Vite 6.0 + Tailwind CSS + FastAPI + WebSocket
**Features**: Dual consist control, real-time sync, Gate Editor (drag/drop/rotate/resize), mobile-first responsive design

**Per dettagli completi**: vedi [docs/WEB_DASHBOARD.md](docs/WEB_DASHBOARD.md)
- Stack tecnologico completo (frontend + backend)
- Development workflow (Vite HMR, quando riavviare)
- Features implementate (controllo locomotive, UI/UX, real-time sync)
- Fix importanti risolti (Tailwind v4, function state sync, Safari bugs)
- Mobile optimizations (Wake Lock, responsive layout)
- Alias bash con venv auto-activation

---
---
## Computer Vision Tracking System

**Status**: ✅ **PHASE 4 COMPLETATA** - Gate Timing Detection integrato in Web Dashboard  
**Approccio**: YOLO custom training + timing-based gate crossing detection

### Obiettivo
- **Monitoraggio posizioni real-time** delle locomotive sul tracciato
- **Speed matching automatico** tramite co-presence timing Δt tra lead/rear
- **Auto-calibrazione consist** via CV adjustment (Mode 2) o Virtual Mode (Mode 3)

### Stack Implementato
- **YOLO v8 nano** - Object detection custom trained (4 locomotive, mAP50 = 80.7%)
- **Gate timing detection** - 2 gate rettangolari condivisi per Consist 11 (cross-validation)
- **Tracking daemon** - Headless YOLO inference + WebSocket broadcast
- **Video feed MJPEG** - RTSP stream con overlay gate + Δt stats panel
- **Frontend integration** - React component con Δt panel real-time

### Features Live
- ✅ YOLO detection tutte e 4 locomotive (confidence 0.60-0.92)
- ✅ Dual-gate co-presence timing (Gate 1: 100x100px, Gate 2: 60x60px)
- ✅ Cross-gate Δt calculation con fresh timestamp logic
- ✅ WebSocket sync multi-device (daemon → backend → frontend)
- ✅ Soglie timing: |Δt| < 1.0s SYNCED, 1.0-2.0s WARNING, >2.0s CRITICAL
- ✅ Debug mode flag in config.json per console logging intelligente

**Per dettagli completi**: vedi [docs/COMPUTER_VISION.md](docs/COMPUTER_VISION.md)
- YOLO training workflow completo (dataset, annotazione, training Colab)
- Gate timing detection strategy (timing-based vs distance-based)
- Reference Loco Strategy (CRITICO per Auto CV Adjust)
- Phase 4 implementation details (daemon, video feed, frontend)
- Virtual Consist Mode (Phase 4B) - CV19 management automatico
- Roadmap fasi successive (Auto CV Adjust, Software Sync)

### Production Testing Results (2025-01-10 → 2025-01-11)

**✅ TESTING COMPLETATO** - 3 configurazioni testate approfonditamente su PC Windows + GPU

**Test 1: OBB Model** (`yolo_obb: true`, `yolo_iou: 0.85`)
- ✅ **Overlap handling**: Perfetto - entrambe le loco visibili quando si passano vicino
- ✅ **Bbox orientation**: Poligoni ruotati seguono angolo locomotiva
- ❌ **Distant detection**: Loco 7 confidence <0.4 quando lontana da camera
  - Richiesto `yolo_confidence: 0.1` per detectare loco 7 distante
  - Side effect: False positives (carrozze misclassificate, doppio bbox stessa loco)

**Test 2: Standard Model** (`yolo_obb: false`, `yolo_iou: 0.85`)
- ✅ **Distant detection**: Loco 7 confidence 0.4+ anche quando lontana
- ✅ **Detection consistente**: Tutte le loco detectate su tutto il tracciato
- ⚠️ **Overlap handling**: NMS sopprime ancora una loco quando si passano vicino (IoU 0.85 insufficiente)

**Test 3: Standard Model + High IoU** (temporaneamente scelto 2025-01-10)
```json
{
  "yolo_confidence": 0.2,
  "yolo_iou": 0.95,
  "yolo_obb": false
}
```
- ✅ **Distant detection**: Perfetto (tutte le loco, tutte le distanze)
- ✅ **Overlap handling**: Entrambe le loco visibili quando si passano vicino (NMS solo se overlap >95%)
- ✅ **False positives**: Minimali (confidence 0.2 sufficiente)
- ⚠️ **Trade-off**: Doppio bbox occasionale su overlap estremo

**Test 4: OBB Model + Tuned Params** ✅ **VINCITORE FINALE** (2025-01-11)
```json
{
  "yolo_confidence": 0.3,  // Più alto per ridurre false positives
  "yolo_iou": 0.6,         // Più basso OK perché bbox ruotati = meno overlap
  "yolo_obb": true         // OBB model attivo
}
```
- ✅ **Overlap handling**: Perfetto (bbox ruotati non sovrapposti)
- ✅ **Distant detection**: Confidence 0.3 bilancia detection vs false positives
- ✅ **Bbox precision**: Poligoni ruotati seguono orientamento reale locomotive
- ✅ **IoU ottimizzato**: 0.6 sufficiente (OBB riduce overlap geometricamente)

**Decisione Finale: OBB Model Wins** (dopo ulteriori test)
- **Perché OBB vince**: Tuning parametri risolve problema distant detection
  - Confidence 0.3 (vs 0.1 test iniziale): elimina false positives mantenendo detection
  - IoU 0.6: ottimale per bbox ruotati (overlap geometrico ridotto)
  - Bbox orientation: rappresentazione più accurata della geometria reale
- **Perché Standard non basta**: Overlap handling imperfetto anche con IoU 0.95
  - Doppi bbox su overlap estremo (raro ma fastidioso)

#### TensorRT Optimization & Critical Fix (2025-01-11)

**Motivazione**: Ridurre bbox lag da 2-3s a <0.5s tramite GPU acceleration

**Implementation**: Export modello a TensorRT .engine format (FP16 half-precision)
- Script: `scripts/utils/export_tensorrt.py` (auto-detect standard vs OBB)
- Priority fallback: `.engine` → `.onnx` → `.pt`
- Auto-detection in `yolo_tracker.py` (zero config changes needed)

**Critical Bug Found & Fixed**:
- **Problem**: ONNX/TensorRT zero detection (bbox invisibili, no console output)
- **Root cause**: ONNX/TensorRT export NON preserva task metadata
  - YOLO assumeva `task='detect'` invece di `task='obb'`
  - OBB model trattato come standard detection → output format incompatibile
- **Solution**: Explicitly specify `task='obb'` when loading OBB models
  ```python
  if yolo_obb:
      self.model = YOLO(model_path, task='obb')  # Fix per ONNX/TensorRT OBB
  else:
      self.model = YOLO(model_path)              # Standard detection
  ```
- **Commits**: `1012ccb` (ONNX fallback), `2d17969` (task='obb' fix)

**Test Results**:
- ✅ **ONNX fallback**: 1.5-2x faster than PyTorch (intermediate speed)
- ✅ **TensorRT OBB**: 2-5x faster (6-15ms/frame vs 30ms PyTorch)
- ✅ **Detection perfect**: All 4 locos detected with rotated bboxes
- ✅ **Bbox lag eliminated**: <0.5s (was 2-3s)
- ✅ **Gate timing accurate**: Real-time Δt calculation
- ✅ **Fallback compatible**: Works with both standard and OBB models

**Model Files**:
- `best_obb.pt`: 6.6 MB (PyTorch OBB - backup)
- `best_obb.onnx`: 11.9 MB (ONNX OBB - intermediate speed)
- `best_obb.engine`: 13.7 MB (TensorRT OBB - maximum speed)

**Key Insight**: ONNX/TensorRT export strips model metadata → explicit task specification REQUIRED for OBB models

**Documentation**: See `docs/TENSORRT_OPTIMIZATION.md` for complete export workflow

---

**Key Insights** (Test 4 OBB):
- OBB richiede tuning diverso da Standard: confidence più alto, IoU più basso
- Geometry matters: bbox ruotati riducono overlap → IoU threshold più basso funziona meglio
- False positives risolvibili: confidence 0.3 sweet spot per OBB (0.2 troppo basso)
- Production testing iterativo essenziale: primi test OBB avevano parametri subottimali

**✅ Production Verification** (2025-01-11):
- ✅ YOLO OBB detection: Bbox ruotati funzionanti in video feed
- ✅ Gate passes: Detection affidabile su entrambi i gate
- ✅ Distant detection: Confidence 0.3 ottimale (nessun false positive)
- ✅ Overlap handling: Perfetto (zero doppi bbox)
- ✅ WebSocket stats: Badge interattivo funzionante (uptime, messages, reconnects)
- ✅ Test badge: UI migliorata ("Test" fisso con colori verde/amber)

### Future Tasks

#### ⏳ **Expand YOLO Tracking: 4 → 6 Locomotive Classes**

**Obiettivo**: Aggiungere loco 2 (E656 182) e loco 6 (D445 1140) al tracking YOLO

**Workflow Incrementale** (non serve rifare annotation esistenti):

1. **Setup Plastico** (solo nuove loco):
   - Rimuovere fisicamente: Loco 1, 5, 7, 8 (già nel dataset v6)
   - Tenere solo: Loco 2 + Loco 6 (nuove classi)

2. **Cattura Video** (~10 min):
   - Camera Tapo RTSP 720P
   - Far girare entrambe (consist temporaneo o separate)
   - Variare: distanze, angoli, velocità, illuminazione
   - Durata: 5-10 minuti → ~100-150 frame/loco

3. **Frame Extraction** (script esistente):
   - `scripts/utils/1_extract_frames.py`
   - Output: 200-300 frame totali

4. **Upload Roboflow** (versioning automatico):
   - Progetto "BiancAlice" esistente → upload nuovi frame
   - Roboflow crea VERSION 7 automaticamente
   - Dataset finale = v6 (4 classi) + v7 (2 classi) = 6 classi

5. **Annotation** (~1-2 ore):
   - Smart Select solo per 2 nuove classi:
     - `2_E656_182` (nuovo)
     - `6_D445_1140` (nuovo)
   - Classi esistenti NON toccate (già annotate)

6. **Training Google Colab** (~5-10 min):
   - `scripts/utils/3_train_yolo_colab.py` (auto-fetch v7)
   - Output: `best.pt` con 6 classi

7. **Code Update** (class mapping):
   ```python
   # yolo_tracker.py - DCC_TO_YOLO_CLASS
   # PRIMA (4 classi):
   {1: 0, 5: 1, 7: 2, 8: 3}

   # DOPO (6 classi - ordine alfabetico Roboflow):
   {1: 0, 2: 1, 5: 2, 6: 3, 7: 4, 8: 5}
   ```

8. **Export TensorRT** (su PC, ~2 min):
   - `python scripts\utils\export_tensorrt.py`
   - Output: `best_obb.engine` aggiornato (6 classi)

**Stima Tempo Totale**: ~2-3 ore (quasi tutto annotation manuale)

**Vantaggi**:
- ✅ Non rifare annotation esistenti (Roboflow merge automatico)
- ✅ Meno lavoro (~200 nuovi frame vs 600+ totali)
- ✅ Transfer learning (YOLO mantiene detection esistenti)
- ✅ Versioning (rollback a v6 se serve)

---

#### ⏳ **IR Night Vision Detection Test**

Test YOLO con Tapo camera in modalità notturna

**Contesto**: Test precedente (vecchio modello YOLO standard, su Mac) fallito

**Da verificare con setup attuale**:
- Modello YOLOv8n OBB (mAP50 91.7%, confidence 0.3, TensorRT GPU)
- PC Windows con GPU (inference più veloce)
- Stream RTSP stability con IR attivo + locomotive in movimento

**Expected issue**: OpenCV stream decode instability in IR mode

**Possibili soluzioni se fallisce**:
- Provare stream1 (1080p) invece di stream2 (720p)
- Forzare codec H.264 (Tapo potrebbe switchare ad H.265 in IR)
- Disabilitare IR automatico se LED sempre disponibili

**Test quando**: Plastico acceso, locomotive in movimento, luci spente

---
## Note Operative

### Speed Matching
- Gestito manualmente dall'utente tramite JMRI e speed tables CV
- Le coppie nei consist sono sincronizzate per viaggiare insieme
- Il controller non gestisce calibrazione, solo controllo

### CV Operations
- **Lettura CV da roster JMRI**: ✅ Implementata (via file XML)
- **Lettura CV diretta (POM Read - Operations Mode)**: ✅ **IMPLEMENTATA E FUNZIONANTE**
  - **Comando XpressNet**: `E6 30 [addr] [E4|cv_msb] [cv_lsb] [0x00] [xor]` (verify con value=0)
  - **Risposta**: `64 14 [addr_msb] [addr_lsb] [VALUE] [xor]` - valore reale nel byte 5
  - **⚠️ DECODER COMPATIBILITY**:
    - **ESU LokPilot/LokSound** (loco 1, 2, 5, 6, 8): ✅ **FUNZIONA** (primo tentativo, stabile)
    - **Hornby TXS** (loco 7): ❌ **NON SUPPORTA** CV read in ops mode
      - Alternativa: App Hornby Bluetooth
  - **Implementazione**: `read_cv_on_main()` in z21.py con retry automatico (3 tentativi, 2s delay)
- **Scrittura CV diretta (POM Write - Operations Mode)**: ✅ **IMPLEMENTATA E FUNZIONANTE**
  - **Comando XpressNet**: `E6 30 [addr] [EC|cv_msb] [cv_lsb] [value] [xor]`
  - **Z21 comportamento**: NON invia ACK per successo, solo errori `0x61`
  - **Timeout**: 500ms per rilevare errori, silenzio = successo
  - **Testato**: CV4 cambiato da 14→20→14 con successo (loco 2 - ESU)
  - **DECODER COMPATIBILITY**:
    - **ESU, Hornby, tutti i decoder in uso**: ✅ **FUNZIONA** (conferma utente - uso quotidiano)
  - **Implementazione**: `write_cv_ops_mode()` in z21.py
  - **Critical per CV Tracking**: Mode 2 (Auto CV Adjust) è **CONFERMATO FATTIBILE** ✅
- **Programming track**: ⏳ Da implementare (opzionale, per decoder non-ESU)
  - Richiede sconnettere plastico e mettere solo loco su binario
  - Comando XpressNet diverso da POM
- **Nota decoder utilizzati nel roster**:
  - **Loco 1, 2, 5, 6, 8**: ESU LokPilot 5 / LokSound V4.0 ✅ (read + write OK)
  - **Loco 7**: Hornby TXS ⚠️ (read NO, write OK, read via BT app)

### DecoderPro Usage
- **Tool principale**: DecoderPro (parte di JMRI)
- Usato per configurazione decoder e CV programming
- Programming track per lettura/scrittura CV
- Operations mode per scrittura CV on-the-fly (dove supportato)

---

---

## Note Operative

### CV Operations

**CV WRITE (Operations Mode)** - ✅ IMPLEMENTATO:
- Comando XpressNet: `E6 30 [addr] [EC|cv_msb] [cv_lsb] [value] [xor]`
- Z21 NON invia ACK per successo (silenzio = OK)
- Funziona su decoder: ESU ✅, Hornby ✅

**CV READ (Operations Mode)** - ✅ IMPLEMENTATO:
- Comando XpressNet: `E6 30 [addr] [E4|cv_msb] [cv_lsb] [0x00] [xor]`
- Funziona SOLO su decoder ESU, NON su Hornby TXS
- Z21 White: no CV read standard (solo verify trick)

**Mode 2 Auto CV Adjust**: ✅ CONFERMATO FATTIBILE

Per dettagli completi: vedi `docs/Z21_PROTOCOL.md`

---

## ⛔ KNOWN ISSUES / FAILED EXPERIMENTS

**🚫 NON RIPROVARE QUESTI APPROCCI - GIÀ TESTATI E FALLITI**

### 1. ⛔ Start-Process per Finestre Detached (Windows)
**Tentato**: 2025-01-09 + 2025-01-11
**Problema**: `Start-Process pwsh.exe -WindowStyle Hidden/Normal` NON crea processi veramente detached
- Processo resta legato alla sessione SSH
- Chiudi SSH → processo termina
- Riapri SSH → backend morto
- La finestra non appare o si chiude immediatamente

**Soluzione funzionante**: ✅ **Windows Task Scheduler**
- `Register-ScheduledTask` + `Start-ScheduledTask`
- Processo veramente detached dal sistema operativo
- Sopravvive a: SSH close, logout, reboot
- Usato attualmente in `z21-start` function

**Riferimenti**: CHANGELOG_ARCHIVE.md riga 299-335

---

### 2. ⛔ Motion Detection Puro per Locomotive Tracking
**Tentato**: 2025-12-29 (Phase 3 sospesa)
**Problema**: Background subtraction MOG2 NON sufficiente per tracking affidabile
- Troppo sensibile a: illuminazione, ombre, elementi statici del plastico
- Impossibile distinguere lead da rear locomotive senza ML
- Bounding box include loco + carrozze → centro ≠ posizione reale locomotiva
- Tracciato ovale = direzioni multiple → pattern analysis troppo complesso

**Approcci falliti**:
- Motion detection con pattern analysis (tetti, pantografi, scoring)
- Calcolo vettore direzione per estremità bounding box
- Ottimizzazioni background subtractor (varThreshold, learningRate, morphology)
- Versione minimalista (solo area filtering)

**Soluzione funzionante**: ✅ **YOLO Custom Training**
- YOLOv8 nano trained su 4 locomotive specifiche
- Dataset Roboflow con annotazioni manuali
- mAP50 = 93.1% (standard) / 91.7% (OBB)
- Detection robusta a tutte le distanze e angoli

**Riferimenti**: CHANGELOG_ARCHIVE.md riga 1364-1497

---

### 3. ⛔ PowerShell 7 Task Scheduler con Colori ANSI
**Tentato**: 2025-01-11
**Problema**: PS7 encoding UTF-8 vs console Task Scheduler codepage 850/1252
- **PlainText mode** (`$PSStyle.OutputRendering = 'PlainText'`): Funziona ma solo B/N, niente colori
- **Ansi mode** (`$PSStyle.OutputRendering = 'Ansi'`): Mostra codici ANSI grezzi `[97m[INIT][0m` invece dei colori
- La console Task Scheduler non interpreta ANSI codes correttamente

**Soluzione funzionante**: ✅ **Hybrid Configuration**
- **SSH**: PowerShell 7 (migliore sintassi, comandi riescono al primo tentativo)
- **Task Scheduler**: PowerShell 5.1 (colori perfetti, encoding Windows-1252 nativo)
- `start-backend.ps1` ha fix encoding PS7 (inattivo con PS5.1, pronto se serve)

**Riferimenti**: CLAUDE.md 2025-01-11 changelog

---

### 4. ⛔ Idle Line Breaks Visualization in Δt Chart (Recharts Limitation)
**Tentato**: 2025-01-13 (5 approcci diversi, tutti falliti)
**Problema**: Recharts non supporta line breaks visuali basate su gap temporali in dataset con null naturali
- Ogni evento ha UN solo consist (gate crossing = single consist per timestamp)
- Dataset naturalmente ha: `{delta_t_c10: value, delta_t_c11: null}` OR viceversa
- Recharts `connectNulls` prop gestisce SOLO null consecutivi, non gap temporali

**Approcci falliti** (tutti revertati via git reset --hard):

1. **Segment-based + separate data arrays** (commit `f3c40da`)
   - Multiple Line components, ognuno con proprio data array
   - Problema: Tutti i segmenti sovrapposti a sinistra del chart (no timeline corretta)
   - Legend duplicata (7+ voci per consist invece di 2)

2. **Unified dataset + null boundaries** (commit `615f68e`)
   - Dataset unificato con null points inseriti ai gap boundaries
   - connectNulls={false} per rompere linee
   - Problema: Solo mini-segmenti 2-3 punti (rompe su OGNI null, inclusi naturali)

3. **Selective null boundaries** (commit `63e508e`)
   - Null SOLO per consist con gap, non tutti i consist
   - Problema: Stesso del #2 (ogni null naturale rompe la linea)

4. **Double-null strategy + connectNulls=true** (commit `f470b53`)
   - connectNulls={true} per connettere null singoli (naturali)
   - Null doppi (tutti i consist) ai gap boundaries
   - Problema: Recharts IGNORA completamente double-null points → nessun line break

5. **Segment-based + XAxis numerico** (commit `8037997`)
   - XAxis type="number" con timestamp domain
   - Multiple Line components con data separati
   - Problema DISASTROSO:
     - Punti allineati verticalmente (scale compressione)
     - Legend con 1000+ voci ("delta" ripetuto)
     - Overview chart illeggibile (legend riempie schermo)
     - Nessuna linea (rarissimi casi)

**Root Cause** (Recharts design limitation):
- Recharts non ha concetto di "gap temporale" tra punti
- `connectNulls` gestisce solo presenza/assenza valori, non timing
- XAxis numerico con data separati non condivide domain correttamente
- Multiple Line con data props generano legend entries duplicate

**Decisione**: ✅ **FEATURE ABBANDONATA**
- Hard reset a commit `19d227e` (ultima versione stabile)
- 5 commit revertati completamente
- Analytics Dashboard funziona perfettamente SENZA idle line breaks
- Linee continue = accettabile (user può vedere gap negli stats cards)

**Alternative considerate MA non perseguite**:
- Custom SVG paths (troppo complesso, reinventare Recharts)
- Switch a libreria diversa (Plotly, Victory) → breaking change enorme
- Dashed lines durante idle → già provato in passato, stesso problema

**Riferimenti**: Git commits f3c40da → 8037997 (tutti revertati)

---


**💡 REGOLA GENERALE**: Se un approccio è nell'archive come "FALLITO" o "SOSPESO", NON riprovarlo senza una ragione tecnica specifica nuova (es. nuova versione software, hardware diverso).

---

## Changelog

**Note**: Per changelog storico (2025-12-16 → 2025-01-15), vedi `docs/CHANGELOG_ARCHIVE.md`

---

### 2026-01-15 - 🎉 **SPEED TABLE AUTO-TUNING: Phase 1 MVP COMPLETATA**

**Status**: ✅ **PHASE 1 COMPLETE** - Speed correlation analytics live in production

**Implementation Summary**:
- **Time**: ~3 hours (stima: 8-12h) - ottimizzato grazie a modular architecture
- **Commits**: 5 commits (ba8d9e4 → f8669c7)
- **Deploy**: PC Windows production via `z21-deploy-dev`
- **Testing**: ✅ Live con dati reali (C10: 52 eventi, C11: 300 eventi a speed 70)

**Backend** (3 files modified):
- ✅ `ws_control.py`: Speed event logging in `handle_set_speed()` (logga solo se speed cambia)
- ✅ `analytics_db.py`: `get_speed_correlation()` con "Next N Events" strategy (default N=10)
- ✅ `routers/analytics.py`: Endpoint `/api/analytics/speed-correlation?consist_id=X`

**Frontend** (4 files: 3 modified, 1 new):
- ✅ `analyticsConstants.js`: `SPEED_STATUS_COLORS` (no hardcoded thresholds!)
- ✅ `analyticsHelpers.js`: 3 helper functions (reference lines, bucket color, recommendations)
- ✅ `SpeedCorrelationChart.jsx`: NEW scatter chart component con error bars + reference lines
- ✅ `AnalyticsPanel.jsx`: 4th tab "Speed Tuning" integrato (187 lines added)

**Features Implemented**:
- ✅ Speed vs Δt scatter chart con error bars (std dev)
- ✅ Dynamic reference lines da config thresholds (SYNCED/WARNING/ACTION)
- ✅ Color-coded points by dominant status (green/amber/red)
- ✅ Summary cards (speed changes, samples, buckets)
- ✅ CV tuning recommendations (text only - Phase 1, manual JMRI adjustment)
- ✅ Consist filter enforcement (must select C10 or C11, not "All")
- ✅ Auto-reload on consist filter change

**Database Migrations** (2 scripts, one-time execution):
1. **Migration 1** (`migrate_add_speed.py`): Aggiunto `speed: 70` a 352 eventi delta_t storici
   - Backup: `analytics.db.backup_20260115_151846.backup`
2. **Migration 2** (`add_historical_speed_events.py`): Creati 2 eventi `speed_setting` (0→70)
   - C10: 52 eventi delta_t utilizzabili
   - C11: 300 eventi delta_t utilizzabili
   - Backup: `analytics.db.backup_20260115_163137.backup`

**Production Results** (2026-01-15 16:30):
- **Consist 10**: Speed 70 → Mean Δt +1.07s (±0.60s) - 50% SYNCED, 30% CRITICAL
- **Consist 11**: Speed 70 → Mean Δt -0.80s (±1.15s) - 60% SYNCED, 30% CRITICAL
- **Status**: Entrambi sotto soglia action (1.5s) → "All speeds well synchronized!" ✅

**Critical Fixes Applied**:
- ✅ Exclude speed-tuning from Current/Overview charts rendering (efa54ba)
- ✅ Correct terminology: "Reference/Adjust loco" instead of "Lead/Rear" (f8669c7)
- ✅ Fix recommendation logic: Δt > 0 = adjust slower (not faster)

**Architecture Notes**:
- **No hardcoded thresholds**: Tutti i threshold da `config.json` (dynamic)
- **Modular design**: Chart component riutilizzabile, helpers DRY
- **"Next N Events" strategy**: Adattivo a track length (C10: 55s vs C11: 15s lap)
- **Phase 1 scope**: TEXT recommendations only (manual CV adjustment via JMRI)

**Next: Phase 2 Enhancement** (discussed, not implemented):
- Read CV speed table values from JMRI roster (CV67-94)
- JMRI-style step numbering (1-28 instead of CV67-94)
- Specific recommendations: "Step 16 (CV82): 128 → 135 (+7)" instead of generic text
- Before/after preview with exact CV values

**References**:
- Design: `docs/SPEED_TABLE_TUNING.md`
- Plan: `~/.claude/plans/glimmering-sleeping-starfish.md`

---

### 2026-01-15 - 🐛 **SPEED TUNING: 8 Critical Bugs Fixed After Phase 1 Deployment**

**Status**: ✅ **ALL BUGS FIXED** - Speed Tuning fully functional, v1.4 tag created

**Context**: After Phase 1 MVP deployment, extensive testing revealed 8 critical bugs preventing Speed Tuning from working correctly. This debugging session (~6 hours) identified and fixed all issues.

**Critical Bugs Discovered and Fixed**:

1. **🔴 WebSocket Crash - Missing `await` Keyword** (MOST CRITICAL)
   - **Error**: speed_setting events logged to console but NEVER reached database (0 events in DB)
   - **Cause**: `analytics_logger.log_event()` is async but called without `await` in `ws_control.py:184`
   - **Evidence**: 17 delta_t events at speed 126 existed (daemon logging worked), but 0 speed_setting events
   - **Fix**: Added `await` before `analytics_logger.log_event()` call
   - **File**: `backend/websocket_handlers/ws_control.py:184`
   - **Commit**: `9f50436`

2. **🔴 analytics_logger Not Accessible from ws_control.py**
   - **Error**: `AttributeError: 'TrackingManager' object has no attribute 'analytics_logger'`
   - **Cause**: analytics_logger lives in tracking_daemon, not tracking_manager
   - **User symptom**: "le loco partono solo la prima volta e poi non è più possibile fermarle"
   - **Fix**: Added analytics_logger to dependencies.py global state pattern
     - tracking_daemon sets it on startup via `dependencies.set_analytics_logger()`
     - ws_control.py gets it via `dependencies.get_analytics_logger()`
   - **Files**: `backend/dependencies.py`, `backend/tracking_daemon.py`, `backend/websocket_handlers/ws_control.py`
   - **Commits**: `cdf5f9c`, `d4c8c60`

3. **🟡 Circular Import - dependencies.py**
   - **Error**: `ImportError: cannot import name 'TrackingManager' from partially initialized module`
   - **Cause**: Import chain: main.py → tracking_manager → tracking_daemon → dependencies → tracking_manager
   - **Fix**: Used `TYPE_CHECKING` pattern in dependencies.py to avoid runtime circular import
     ```python
     from typing import TYPE_CHECKING
     if TYPE_CHECKING:
         from z21_manager import Z21Manager
         from tracking_manager import TrackingManager
     ```
   - **File**: `backend/dependencies.py`
   - **Commit**: `d4c8c60`

4. **🟡 Speed Field Missing in delta_t Events**
   - **Error**: delta_t events had no speed field → correlation algorithm couldn't work
   - **Evidence**: Recent events showed `speed: None` or missing speed field
   - **Fix**: Added `'speed': self.consist_speeds.get(consist_id, 0)` to delta_t event data
   - **File**: `backend/tracking_daemon.py:204`
   - **Commit**: `8d97f24`

5. **🟡 Gate Editor Path Wrong**
   - **Error**: `[Errno 2] No such file or directory: 'C:\\z21-Terminal\\backend\\config.json'`
   - **Cause**: Gate editor tried to save to backend/config.json instead of root
   - **Fix**: Changed to use `get_config_path()` instead of hardcoded path calculation
   - **File**: `backend/routers/config.py:347`
   - **Commit**: `5e04b62`

6. **🟡 Config Paths Not Centralized**
   - **User feedback**: "ci sono altri mille posti in cui qualcosa salva il config, ti prego di controllare tutti"
   - **Fix**: Systematic search and replace all config.json access with `get_config_path()`
   - **Files**: `backend/routers/config.py`, `backend/z21_manager.py`, `backend/video_feed.py`
   - **Commits**: `5e04b62`, `aaa8db5`

7. **🟡 Error Messages Not Visible in Logs**
   - **User feedback**: "ma perchè non ho visto l'errore nel log, perchè non era rosso?"
   - **Cause**: FastAPI/Starlette WebSocket handler uses print() instead of log()
   - **Fix**: Created `ColoredOutput` wrapper class to intercept sys.stdout.write() and add colored [ERROR]/[WARN] prefix
   - **File**: `backend/log_colors.py:69-112`
   - **Commit**: `0502e73`

8. **🟢 Orange Color for [SPEED] Log Prefix**
   - **User request**: "possiamo dare un colore anche agli eventi speed? Orange"
   - **Fix**: Added `'\033[38;5;208m'` (orange) to [SPEED] prefix in log_colors.py
   - **File**: `backend/log_colors.py:26`
   - **Commit**: `0a4e3cd`

**Database Migrations** (Historical Data Correction):

1. **Speed 70 → 88 Correction** (`fix_speed_70_to_88.py`):
   - **Context**: User meant 70% of 126 = 88 DCC speed, not literal 70
   - **User feedback**: "quando ti ho detto che i 333 eventi erano a speed 70, volevo dire 70% non 70, quindi speed 88!!!!!"
   - **Results**:
     - 352 delta_t events updated: speed 70 → 88
     - 2 speed_setting events updated: speed_new 70 → 88
   - **Backup**: `analytics.db.backup_20260115_181523.backup`

**Architecture Improvements**:
- ✅ **Global state pattern** in dependencies.py for analytics_logger access
- ✅ **TYPE_CHECKING guard** prevents circular imports
- ✅ **Centralized config path** via get_config_path() across all files
- ✅ **Auto-prefix error wrapper** for better log visibility

**Production Deployment**:
- ✅ All fixes deployed to PC Windows via `z21-deploy-dev`
- ✅ Speed Tuning chart now shows data correctly
- ✅ Speed_setting events logging to database (verified with test session)
- ✅ Orange [SPEED] log prefix visible in console
- ✅ Config.json synced from Mac to PC (gate modifications preserved)

**Final Status**:
- **Tag**: `v1.4` (moved from initial Phase 1 commit)
- **Commits**: `cdf5f9c` → `9f50436` (8 commits)
- **Testing**: ✅ Full verification on PC Windows production
- **User confirmation**: All features working correctly

**Time Investment**: ~6 hours debugging + testing
**Key Insight**: async/await bugs are silent killers - function appears to work (logs print) but never executes (no DB writes)

---

### 2025-01-15 - 🎨 **FRONTEND REFACTORING COMPLETATO** (Analytics Dashboard)

**Status**: ✅ **MILESTONE ACHIEVED** - Modular chart components, merged to develop

**Objective**: Reduce AnalyticsPanel.jsx from 1684 lines (monolithic) to modular architecture with extracted chart components + helpers + constants

**Final Results**:
- **AnalyticsPanel.jsx**: 1684 → 1151 lines (-31.6% reduction, -533 lines)
- **Total modular code**: 909 lines across 8 new files
- **Architecture**: 5 Chart Components + 1 Helpers Module + 1 Constants Module + 1 Plan Document
- **Chart compatibility**: 100% - all Current/Overview/Reports view differences preserved
- **Testing**: All features verified on PC Windows production (all charts, session filtering, consist filtering, click interactions)

**Files Created** (8 total):
1. `web/src/components/charts/DeltaTChart.jsx` (282 lines) - Δt Trends with session breaks + box-select zoom
2. `web/src/components/charts/FPSChart.jsx` (162 lines) - Inference FPS with average badge
3. `web/src/components/charts/ConfidenceChart.jsx` (138 lines) - Detection confidence per locomotive
4. `web/src/components/charts/OperatingTimeChart.jsx` (94 lines) - Total operating time (Overview only)
5. `web/src/components/charts/HistoricalTrendChart.jsx` (178 lines) - Session-by-session trend (Reports tab)
6. `web/src/utils/analyticsHelpers.js` (86 lines) - 7 pure utility functions
7. `web/src/constants/analyticsConstants.js` (31 lines) - Shared constants + styles
8. `docs/FRONTEND_REFACTOR_PLAN.md` (1535 lines) - Complete refactoring documentation

**Critical Features Preserved**:
- **DeltaTChart**: 8 Current/Overview differences (XAxis dataKey, scroll, width, dots, stroke, zoom, duplicate Y-axis, auto-scroll)
- **FPSChart**: 5 Current/Overview differences + FPS avg badge (idle filtering)
- **ConfidenceChart**: Snapshot (Current) vs Aggregated (Overview) logic
- **HistoricalTrendChart**: Custom tooltip showing ALL consists + clickable points for Session Detail Modal

**Bugs Fixed During Refactoring**:
1. **ConfidenceChart Overview mode**: Now aggregates all historical events (loco 5 missing fix)
2. **FPSChart dots alignment**: Dots only in Current mode (aligned with DeltaTChart behavior)
3. **DRY improvements**: Eliminated duplicate data prep logic in ConfidenceChart

**Time Investment**: ~6-8 hours across 4 phases
**Commits**: 17 commits (Phase 0 → Phase 4)
**Branch**: `refactor-frontend` → merged to `develop`

**Benefits**:
- ✅ Single Responsibility: Each chart component ~90-280 lines (manageable)
- ✅ Reusability: Charts can be used independently
- ✅ Testability: Isolated components easier to test
- ✅ Maintainability: Future chart additions follow established pattern
- ✅ DRY: Shared constants/helpers eliminate duplication
- ✅ Scalability: Adding SpeedCorrelationChart (v1.4) now straightforward

**Deployment**: Tested on PC Windows production after each phase (same workflow as backend refactoring)

**Git Workflow**:
- Merged: `refactor-frontend` → `develop` (--no-ff, preserve history)
- Tagged: `frontend-refactor-complete`
- Branch deleted: Local and remote cleaned up

**Production Deployment**: ✅ **VERIFIED** (2025-01-15)
- Deployed via `z21-deploy-dev` on PC Windows
- All 5 chart components working perfectly
- No regressions, all features functional
- User confirmed: "la perfezione!" 🎯

---

### 2025-01-15 - 🎉 **BACKEND REFACTORING COMPLETATO** (Phase 4)

**Status**: ✅ **MILESTONE ACHIEVED** - Modular architecture complete, merged to develop

**Objective**: Reduce main.py from 2340 lines (monolithic) to modular architecture with routers + services + WebSocket handlers

**Final Results**:
- **main.py**: 2340 → 742 lines (-68.3% reduction, -1598 lines)
- **Total modular code**: 3162 lines across 11 new files
- **Architecture**: Routers (4) + Services (4) + WebSocket Handlers (2) + Dependencies system
- **Endpoint compatibility**: 100% - all 27 endpoints functional, zero breaking changes
- **Testing**: All features verified on PC Windows production (locomotive control, tracking, YOLO, analytics, gate editor)

**Files Created** (11 total):
1. `backend/dependencies.py` (230 lines) - Global state dependency injection
2. `backend/routers/analytics.py` (226 lines) - 6 analytics endpoints
3. `backend/routers/config.py` (378 lines) - 7 config/consist/gate endpoints
4. `backend/routers/roster.py` (110 lines) - 3 roster endpoints
5. `backend/routers/status.py` (125 lines) - 2 status/telemetry endpoints
6. `backend/services/analytics_db.py` (435 lines) - SQLite analytics queries
7. `backend/services/broadcast.py` (237 lines) - WebSocket broadcast utilities
8. `backend/services/config_manager.py` (172 lines) - Configuration access helpers
9. `backend/services/downsampling.py` (149 lines) - LTTB + smart Δt downsampling
10. `backend/websocket_handlers/ws_control.py` (394 lines) - Real-time locomotive control (10 message types)
11. `backend/websocket_handlers/ws_tracking.py` (192 lines) - YOLO tracking daemon handler (3 message types)

**Critical Bugs Fixed During Refactoring**:
1. **Namespace Collision**: Renamed `websockets/` → `websocket_handlers/` (uvicorn conflict)
2. **WebSocket Crash**: Fixed `get_full_roster()` import from `routers.roster`
3. **Tracking Broken**: Synced `tracking_daemon_ws` with `dependencies.set_tracking_daemon_ws()`
4. **Video Panels Missing**: Updated `get_tracked_consist_ids()` to use `gate_ids` field (config schema change)
5. **YOLO Bbox Gone**: Changed video feed callback to use `dependencies.get_yolo_detections()`
6. **Dead Code**: Removed unused globals `tracking_daemon_ws` and `yolo_detections` (final cleanup)

**Architecture Achieved**:
```
backend/
├── main.py (742 lines - minimal delegation, FastAPI app)
├── dependencies.py (global state injection)
├── routers/
│   ├── analytics.py (6 endpoints)
│   ├── config.py (7 endpoints)
│   ├── roster.py (3 endpoints)
│   └── status.py (2 endpoints)
├── services/
│   ├── analytics_db.py (SQLite queries)
│   ├── broadcast.py (WebSocket utilities)
│   ├── config_manager.py (config helpers)
│   └── downsampling.py (LTTB + smart sampling)
└── websocket_handlers/
    ├── ws_control.py (10 control messages)
    └── ws_tracking.py (3 tracking messages)
```

**Benefits for Future Development**:
- ✅ **Maintainability**: Single responsibility per file (~150-400 lines each)
- ✅ **Testability**: Each router/service can be tested independently
- ✅ **Scalability**: New features (Speed Table Auto-Tuning v1.3) require zero main.py changes
- ✅ **Collaboration**: Multiple developers can work on different routers without conflicts
- ✅ **Debugging**: Clear separation of concerns, easier to locate bugs

**Time Investment**: ~10-12 hours total (4 phases, incremental testing after each)
**Rollback Safety**: Git tag created after each phase (rollback ready if needed)

**Commits**: `10d0bfd` → `0502e73` (14 commits across 4 phases)

**Documentation Updated**:
- `backend/README.md` - Project structure section
- `docs/REFACTOR_PLAN.md` - Complete implementation guide
- `CLAUDE.md` - This changelog entry

**Next Steps** (v1.3 Speed Table Auto-Tuning):
- Add `routers/speed_tuning.py` (clean separation)
- Extend `AnalyticsDB` with speed correlation queries
- Add CV write operations in `services/cv_manager.py`

---

### 2025-01-15 - ♻️ **BACKEND REFACTORING: Phase 2.2 Completato + Venv Documentation**

**Status**: ✅ **Config Router Extracted** - 7 endpoints migrated to `backend/routers/config.py`

**Phase 2.2 Implementation**:

1. **Config Router Created** (`backend/routers/config.py`, 378 lines):
   - GET `/api/consists` - List all consists with state and gates
   - POST `/api/consists` - Create new consist with CV19 write (Virtual/DCC mode)
   - PUT `/api/consists/{address}` - Update consist (mode switching, gate assignments)
   - DELETE `/api/consists/{address}` - Delete consist (writes CV19=0 if DCC mode)
   - GET `/api/config/tracking` - Get tracking configuration (idle_timeout, thresholds, consists)
   - GET `/api/gates` - Get current gate configuration
   - POST `/api/save-gates` - Save gate configuration from web editor

2. **Key Features**:
   - **CV19 Operations**: Automatic CV write for Virtual Mode (CV19=0) vs DCC Mode (CV19=consist_address)
   - **Global State Management**: Uses dependency injection via `dependencies.get_consist_data()`, `dependencies.get_z21_manager()`
   - **Broadcast Integration**: Updates global state and broadcasts to all connected clients after CRUD operations
   - **Backup Creation**: Gate editor creates `config.json.backup` before saving

3. **Testing Results** (PC Windows production):
   - ✅ GET `/api/consists` → 2 consists, 4 gates
   - ✅ GET `/api/gates` → 4 gates
   - ✅ GET `/api/config/tracking` → idle_timeout 10s, 2 consists

**Refactoring Progress**:
- **main.py**: 2340 → 1227 lines (-1113 lines, **-47.5%** reduction)
- **Routers extracted**: analytics.py (228 lines), config.py (378 lines)
- **Total endpoints migrated**: 13/27 (48%)

**Critical Documentation Added**:
- **Plan file updated** with **"⚠️ CRITICAL: Development Environment Requirements"** section
- **Emphasizes**: ALWAYS use venv on both Mac AND PC, every time calling python3
- **Includes**: Practical examples for Mac (`source venv/bin/activate`) and PC (`.\venv\Scripts\Activate.ps1`)
- **Explains**: Why it matters (dependency isolation, version control, reproducibility)
- **Warns**: What happens if forgotten (ModuleNotFoundError, wrong Python version, conflicts)

**Files Modified**:
- `backend/routers/config.py` (NEW - 378 lines)
- `backend/main.py` (removed 7 config endpoints, -334 lines)
- `~/.claude/plans/glimmering-sleeping-starfish.md` (venv requirements section added)

**Next Steps**: Phase 2.3 - Extract locomotives router (8 endpoints)

**Commits**: `cbd1e60` - Phase 2.2: Extract config router + Plan file venv documentation

---


## 📋 TODO / Future Enhancements

### Header UI Consistency (2025-01-14)

**Task**: Uniformare i 3 bottoni sinistra allo stile di Analytics (icona + label)

**SINISTRA - ACTIONS (da aggiornare):**
```
[🔄] → [🔄 Reload]     + tooltip: "Reload roster from JMRI XML files"
[➕] → [➕ Add]         + tooltip: "Add controller panel"
[⚙️] → [⚙️ Consists]   + tooltip: "Manage consists"
[📊 Analytics]         (unchanged)
```

**DESTRA - STATES + BADGES (unchanged):**
```
[🧪 Test] [🛑 STOP] [⚡ON] [📶WS] [🔌Z21]
```

**DECISIONE COLORI (da valutare):**

**Opzione A**: Analytics → grigio/bianco (uniformare tutto)
- Tutti e 4 i bottoni identici (grigio/bianco, hover ambra)
- Coerenza visiva totale

**Opzione B**: 3 bottoni → colori personalizzati (differenziare)
- Analytics resta blu (già OK)
- Reload: ? colore da decidere
- Add: ? colore da decidere
- Consists: ? colore da decidere
- Differenziazione visiva per tipo azione

**Layout finale:**
```
[Logo] [🔄 Reload] [➕ Add] [⚙️ Consists] [📊 Analytics] ............ [🧪 Test] [🛑 STOP] [⚡ON] [📶WS] [🔌Z21]
        └──────────────── ACTIONS ────────────┘                       └────── UNCHANGED ─────┘
```

**Files**: `web/src/App.jsx`


**Note**: Per dettagli completi implementation Analytics (2025-01-13/14), vedi `docs/CHANGELOG_ARCHIVE.md`

---
