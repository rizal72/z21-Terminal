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

**Git add policy**: Sempre usare `git add .` (CLAUDE.md è gitignored)

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

**Note**: Per changelog storico (2025-12-16 → 2025-01-12), vedi `docs/CHANGELOG_ARCHIVE.md`

---

### 2025-01-14 - 🔍 **ROOT CAUSE ANALYSIS: Loco 7 Erratic Behavior**

**Investigation**: Analytics historical trend analysis su Consist 11 (30 sessioni, 2026-01-12 → 2026-01-14)

**Findings**:
- Loco 7 (Hornby TXS) comportamento **cronicamente instabile** fin dalla prima sessione tracked
- Average dT varia da -0.06s (BALANCED) a -1.23s (CRITICAL) senza pattern prevedibile
- Worst session: 2026-01-14 avg -1.23s, solo 51.6% SYNCED, range -3.52s to +1.09s (6.6s variabilità!)
- **NON esiste "cambio improvviso"**: problema esisteva già quando tracking iniziato

**Root Cause Identified**: 🎯 **Micro SMD capacitor (~0.5mm) staccato dalla PCB di loco 7**
- **Location**: Lato periferico PCB (opposto decoder), vicino bordo corto (coda/testa loco)
- **Function**: Smoothing/filtering capacitor per circuito alimentazione motore
- **Impact**: Senza filtro → alimentazione instabile, rumore elettrico, spikes non smorzati
- **Why not fixed**: Condensatore troppo piccolo per saldatura manuale, decoder sound troppo costoso per rischiare riparazione

**Workaround**: ✅ **Virtual Mode attivo e funzionante**
- Sistema compensa automaticamente comportamento erratico in real-time
- Analytics tracking valida efficacia compensazione
- Performance accettabile per operazioni quotidiane

**Documentation**: Dettagli completi → `docs/CONSIST_ROSTER.md` (sezione loco 7 - Known Hardware Issue)

**Tools Created**:
- `scripts/utils/analytics_report.py` - Session analysis con dT statistics
- `scripts/utils/c11_trend_analysis.py` - Historical trend C11 (30 sessions max)

**Key Insight**: Questo problema hardware è stata la motivazione principale per sviluppare sistema YOLO tracking + Virtual Mode con compensazione automatica velocità.

---

### 2025-01-14 - 📊 **REPORTS TAB MVP COMPLETATO**

**Status**: ✅ **v1.2 MILESTONE** - 3rd tab Analytics Dashboard implemented

**Obiettivo**: Sostituire CLI scripts (`analytics_report.py`, `c11_trend_analysis.py`) con web UI accessibile da tablet/smartphone per analisi session-by-session.

**Features Implemented**:

1. **Session History Table**:
   - Ultime 30 sessioni validate con colonne dinamiche (C10/C11 Avg Δt, Synced%)
   - Color-coded avg Δt: verde (<1.0s), ambra (1.0-1.5s), rosso (≥1.5s)
   - Consist filter: "All" mostra tutte sessioni con N/A per consist non girato, "C10"/"C11" filtra solo sessioni rilevanti
   - Clickable rows → Session Detail Modal

2. **Historical Trend Chart**:
   - LineChart con avg Δt over time (X-axis: date, Y-axis: seconds)
   - Reference lines: 0 (green), ±1.0 (amber), ±1.5 (red)
   - Dynamic lines per consist (color-coded)
   - Clickable points → Session Detail Modal
   - Custom tooltip mostra tutti consist non-null per data

3. **Session Detail Modal**:
   - Session metadata: ID, Date, Duration, Total Events
   - Per-consist breakdown: Total crossings, Avg Δt, Range, Trend, Status distribution (SYNCED/WARNING/CRITICAL)
   - Interpretation guide con bullet points
   - z-index 60 (sopra main Analytics modal)

**Backend API**:
- Endpoint: `GET /api/analytics/reports?limit=30&consist_filter=<id>`
- Helper: `format_duration_hms()` (HH:MM:SS formatting)
- Pre-aggregates statistics per session/consist (avg, min, max, status counts, synced%, trend)
- Returns consist IDs as strings in JSON (`"10"`, `"11"`)

**Critical Fixes**:
1. Fragment import (React.Fragment undefined)
2. Rules of Hooks (useMemo inside IIFE)
3. Exclude Overview charts da Reports tab
4. Helper functions null safety (`consistConfig || {}`)
5. TrackingConfig load race condition (spinner durante load)
6. Object.keys null safety (7 occorrenze con `|| {}`)
7. **Consist ID type mismatch**: Backend strings vs frontend numbers → `String(cid)` conversion necessaria
8. Session filtering by consist (`filteredReportsSessions` useMemo)
9. Custom tooltip per mostrare tutti consist per data

**Known Limitation**:
- **Multiple sessions same date**: Chart mostra 2 punti verticalmente allineati (es. C10 mattina, C11 sera) ma tooltip mostra solo UNA sessione (quella su cui hover)
- **Possibili soluzioni future**: Aggregate by date (backend), Custom tooltip con date-based lookup, Group sessions in chart data
- **Frequenza**: Bassa (raramente 2+ sessioni stesso giorno con consist diversi)

**Documentation**:
- `docs/REPORTS_TAB.md` - Documentazione completa implementazione (architecture, components, API, fixes, testing, future enhancements)

**Testing**: ✅ Manual testing completato su PC Windows + GPU (production environment)

**Commits**: `0f8c6f8` → `f55bc8f` (13 commits totali, 6 fix critici per crash/rendering)

**Next Steps** (future releases):
- v1.2.1: Multi-session same date tooltip fix
- v1.3: Speed setting tracking (HIGH PRIORITY)
- v1.3+: Sortable columns, pagination, CSV export, date range filter

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

---

Work in progress (2025-01-14):

### 2025-01-14 - 🎉 **SESSION BOUNDARY LINE BREAKS - RISOLTO!**

**Status**: ✅ **FEATURE COMPLETATA** dopo 10+ tentativi falliti

#### Il Problema
Linee continue nel grafico Δt Trends attraversavano pause/idle tra sessioni, rendendo difficile distinguere visivamente quando le locomotive erano ferme.

#### Tentativi Falliti (2025-01-13 → 2025-01-14)
1. **Segment-based con array separati** (commit `f3c40da`) - Recharts NON supporta `data` prop su Line
2. **Unified dataset + null boundaries** (commit `615f68e`) - Mini-segmenti ovunque
3. **Double-null strategy** (commit `f470b53`) - Recharts ignora double-null
4. **XAxis numeric + segments** (commit `8037997`) - 1000+ legend entries, illegibile
5. **Marker con undefined** (commit `250b863`) - Ignorati da Recharts
6. **Marker con NaN** (commit `863aa15`) - Stesso risultato
7. **connectNulls={false}** (commit `865387d`) - Spezza linee anche sui null naturali (altro consist)
8. **Plotly migration** (commits `28bed61`-`a9c0e2f`) - Bundle 8.5x più grande (5.5 MB), illegibile con dati sparsi

#### Soluzione Finale ✅ (commit `35ea274`)
**Segment-based rendering con dataKey separati** (NON array separati!)

**Approccio:**
```javascript
// 1. Rileva session boundaries, assegna segment numbers
const eventSegments = [0, 0, 0, 1, 1, 2, 2, 2, ...];

// 2. Build unified dataset con dataKey per ogni consist+segment
chartData = events.map(e => ({
  ...e,
  delta_t_c10_seg0: (consist === 10 && segment === 0) ? delta_t : null,
  delta_t_c10_seg1: (consist === 10 && segment === 1) ? delta_t : null,
  delta_t_c11_seg0: (consist === 11 && segment === 0) ? delta_t : null,
  delta_t_c11_seg1: (consist === 11 && segment === 1) ? delta_t : null,
  // ... etc
}));

// 3. Render Line separata per ogni segmento
<LineChart data={chartData}>  // <-- STESSO array per tutti!
  <Line dataKey="delta_t_c10_seg0" legendType={undefined} />
  <Line dataKey="delta_t_c10_seg1" legendType="none" />
  <Line dataKey="delta_t_c11_seg0" legendType={undefined} />
  <Line dataKey="delta_t_c11_seg1" legendType="none" />
</LineChart>
```

**Differenza Cruciale dal Tentativo #1:**
- ❌ **Prima**: Provato array `data` separati per ogni Line → non supportato
- ✅ **Ora**: **Singolo array condiviso, dataKey diversi** per ogni segmento → supportato!

**Legend Strategy**: `legendType="none"` sui segmenti >0 → ogni consist mostrato una sola volta

**Risultato:**
- ✅ Break visibili a ogni cambio sessione (idle periods)
- ✅ Funziona in Current E Overview modes
- ✅ Funziona con sampling LTTB (segmenti preservati)
- ✅ Legend pulita (no duplicati)
- ✅ Brush zoom/pan non influenzato
- ✅ Zero impatto performance

**Key Insight**: La "limitazione" di Recharts (array condiviso obbligatorio) è diventata la soluzione - il supporto multi-dataKey permette la segmentazione!

**Commits**: `250b863` (markers undefined), `863aa15` (markers NaN), `865387d` (connectNulls test), `ed4cccb` (restore connectNulls), `35ea274` (✅ soluzione finale)

**Documentazione completa**: `docs/ANALYTICS.md` → "Failed Approaches #3" + "Working Solutions #4"

---

### 2025-01-14 - 📊 **BOX-SELECT ZOOM & Y-AXIS IMPROVEMENTS**

**Status**: ✅ **FEATURE COMPLETATA** - Interactive zoom, rotated labels, sticky legend

**Funzionalità implementate:**
- **Box-select zoom**: Trascina rettangolo in Overview mode, double-click reset
- **Y-axis fixes**: ReferenceLine visibility, decimali 2 cifre, padding 5%, label rotation 180°
- **Sticky legend**: Custom HTML in Current mode (non scorre), Recharts standard in Overview
- **Session breaks toggle**: Checkbox ⏸️ per attivare/disattivare segmenti (default OFF)

**Key challenges solved:**
- XAxis categorical non supporta domain → filtra data invece
- Performance mouseMove drag → throttle 50ms
- Label rotation + centering → accept default (good enough)

**Total commits**: 15
**Documentazione completa**: `docs/ANALYTICS.md` → "Changelog 2025-01-14"

---

Work in progress (2025-01-13):

### 2025-01-13 - 🏷️ **ANALYTICS WORKING TAG** (Rollback + Fix)

#### Context
Analytics panel was **already working** at commit `acfed1b` (2025-01-12 22:57).
Session filtering modifications attempted today broke the chart rendering.

#### Issues Found & Fixed

**Issue 1**: Chart disappeared after session filtering changes
- **Root cause**: Attempt to filter chart data by `session_id` made chart empty
- **Solution**: Reverted to `acfed1b` (original working version)
- Chart must show ALL events (no session filtering on chart data)

**Issue 2**: Gate crossings stats showed 0
- **Root cause**: SQL query searched for `event_type = 'gate_crossing'` but events are stored as `'delta_t'`
- **Solution**: Fixed SQL query in `backend/main.py` line 1718
- **Commit**: `418fc03`

**Issue 3**: "Detail" naming unclear
- **Solution**: Renamed "Detail" → "Current" throughout UI
- More intuitive: "Current session" vs "All sessions history"
- **Commit**: `418fc03`

#### Working State Restored
- **Tag created**: `analytics-working` (points to commit `418fc03`)
- **What works**:
  - ✅ Chart displays all 145 historical events correctly
  - ✅ Gate crossings stats show proper counts (C10/C11/All)
  - ✅ Current/Overview view toggle with arrow keys
  - ✅ Auto-refresh Current view when locos moving
- **Lesson**: Session filtering should ONLY affect stats cards, NEVER the chart data

**Commits**: `418fc03` (SQL fix + rename Detail→Current)
**Tag**: `analytics-working` (use `git show analytics-working` to see details)

---

### 2025-01-13 - 🎯 **DETERMINISTIC SESSION BOUNDARIES**

Implemented `navigator.sendBeacon('/api/close-session')` on page unload.
**Result**: Every page refresh = NEW session (100% deterministic, no timing dependencies).

**Details**: See `docs/ANALYTICS.md` → "Session Lifecycle - Investigation 2"
**Commit**: `f12cee5`

---

### 2025-01-13 - 📈 **ANALYTICS SUITE COMPLETATO - YOLO PERFORMANCE MONITORING**

**Status**: ✅ **MILESTONE COMPLETATO** (commit `5dd4ed3`) - 3/3 charts implementati

**Third Chart Implemented**: YOLO Performance Monitoring
- **FPS Line Chart** (time-series): Inference speed over time (50-130 FPS on TensorRT!)
- **Confidence Bar Chart** (snapshot): Per-locomotive detection quality (DCC addresses)

**Key Features**:
- **DCC address tracking**: Confidence keyed by DCC address (1, 5, 7, 8), NOT YOLO class
  - Ensures data consistency across model changes (OBB ↔ Standard)
- **5-second logging**: Reduces event volume (~720 events/hour vs 3600)
- **Session filtering rules**: Time-series charts NO filter, snapshot charts YES filter
- **Horizontal scroll**: FPS chart scrollable in Current view (like Δt chart)
- **Auto-scroll to right**: Always shows most recent data
- **Sticky header**: Tab buttons remain visible during scroll

**Production Results** (PC Windows + RTX 2060):
- FPS: 50-130 FPS (2-4x faster than 30 FPS target!)
- Confidence: Loco 1,7,8 = 60-75% (excellent), Loco 5 = 35% (below threshold)
- Charts: ✅ FPS scrollbar working, ✅ Confidence empty in Current (correct), ✅ Consist filtering functional

**Implementation Approach** (REUSABLE for future charts):
1. **Backend tracking**: Performance stats in `yolo_tracker.py` with deque histories
2. **Event logging**: 5-second interval in `tracking_daemon.py` (reduce volume)
3. **API update**: Add `session_id` to query for filtering support
4. **Frontend charts**:
   - Time-series: NO session filtering, horizontal scroll, auto-scroll right
   - Snapshot: YES session filtering (Current/Overview semantics)
5. **Refs for scroll**: One ref per scrollable chart, shared auto-scroll effect

**Session Filtering Rules** (CRITICAL):
| Chart Type | Session Filter | Rationale |
|-----------|---------------|-----------|
| Δt Trends (time-series) | ❌ NO | Historical trends valuable |
| FPS (time-series) | ❌ NO | Performance trends over time |
| Confidence (snapshot) | ✅ YES | Current vs Overview semantics |
| Stats Cards | ✅ YES | Session-specific metrics |

**Commits**:
- `4bce745` - YOLO Performance Monitoring implementation
- `4457541` - Sticky header
- `01df6af` - FPS chart horizontal scroll
- `d2630a3` - Remove session filtering from FPS
- `5dd4ed3` - Confidence chart session filtering logic

**Documentation**:
- `docs/ANALYTICS.md` - Complete implementation approach (REUSABLE PATTERN)
- Section "YOLO Performance Monitoring" with step-by-step guide

**✅ ANALYTICS SUITE COMPLETE** - All 3 charts from original plan implemented:
1. ✅ Session Statistics Dashboard (cards)
2. ✅ Δt Trends Visualization (line chart)
3. ✅ YOLO Performance Monitoring (FPS + confidence charts)

---

### 2025-01-13 - 📊 **TAIL VS SAMPLING STRATEGY + CONDITIONAL DEBUG LOGGING**

**Status**: ✅ **IMPLEMENTED** (commit `2480eaf`)

**Problem**: Need smart data strategy for large datasets (>1000 events):
- Initial uniform sampling was too aggressive (sampled ALL data including recent)
- User wanted full resolution for recent data, sampling only for historical overview

**Solution: Tail vs Sampling** (mutually exclusive parameters):

**Current View** (`?tail=1000`):
- Returns **last N events** at full resolution (no sampling)
- Keeps recent data intact (important for active operations)
- Example: 1523 events → returns last 1000 (events 524-1523)

**Overview View** (`?maxPoints=500`):
- **Uniform sampling** across entire history
- Optimizes performance for historical trends
- Example: 1523 events → samples to 500 (every 3rd event)

**Conditional Debug Logging**:
- Log ONLY when `config.json` → `"debug": {"enabled": true}`
- Log ONLY if reduction is **significant**: >10% **OR** >100 events absolute
- Prevents spam for minimal reductions (501→500 = silent)

**Log Examples**:
```
❌ 501->500 (1 event, 0.2%) - No log (not significant)
❌ 550->500 (50 events, 9.1%) - No log (<10%)
✅ 600->500 (100 events, 16.7%) - [DEBUG] Sampling applied (maxPoints=500) | dT: 600->500 | YOLO: 600->500
✅ 1000->500 (500 events, 50%) - [DEBUG] Sampling applied (maxPoints=500) | dT: 1000->500 | YOLO: 1000->500
```

**Key Benefits**:
- ✅ Current view: Full resolution recent data (no detail loss)
- ✅ Overview view: Performance optimized (sampling entire history)
- ✅ Silent by default (no log spam unless debug enabled + significant)
- ✅ Universal: Works for ALL event types (Δt, YOLO, future charts)
- ✅ Transparent: Frontend unchanged (receives array of events)

**Files Modified**:
- `backend/main.py`: Tail vs sampling logic + conditional debug log
- `web/src/components/AnalyticsPanel.jsx`: View-specific API calls
- `docs/ANALYTICS.md`: Updated STEP 1 with tail/sampling strategy

**Commit**: `2480eaf`

---

### 2025-01-13 - 📊 **ANALYTICS SESSION-FILTERED CARDS COMPLETATO**

**Status**: ✅ **MILESTONE VERIFIED** (commit `33345ba`) - Tested with real locomotive movement

**Implemented:**
- **Current view**: Cards filtrate per sessione corrente (Duration, Gate Crossings, Critical Events)
- **Overview view**: Cards mostrano dati storici totali
- **Consist filters**: All/C10/C11 funzionano per Card 2 e Card 3
- **Banner warning**: "Session not validated" quando validated=0
- **Chart**: Sempre tutti i dati (non filtrato per sessione) ✅
- **Legend**: Visibile solo con filtro "All" (evita chart shift verticale)

**Known Issue (da fixare in futuro):**
- C10 filter scrolla a destra (area vuota) perché eventi C10 sono all'inizio timeline
- Soluzione futura: calcolare posizione ultimo evento C10 e scrollare lì esattamente
- Per ora: utente scrolla manualmente a sinistra per vedere C10

**Real-World Test** (2025-01-13 evening):
- ✅ Session validation working (banner disappears after first Δt)
- ✅ Current view cards update correctly (Gate Crossings, Critical Events)
- ✅ Overview view shows historical data
- ✅ Consist filters (All/C10/C11) working
- ✅ Chart always visible, shows all events
- ✅ Deterministic sessions (page refresh = new session)

**Commits**: `fc38298`, `c5d28ef`, `cc5bcaf`, `0e10eb8`, `d6af031`, `89cc116`, `33345ba`
**Tag**: `analytics-working` (✅ verified at `33345ba`)

---

### 2025-01-13 - 🚂 **LOCOMOTIVE OPERATING TIME TRACKING**

**Status**: ✅ **IMPLEMENTED** - Hybrid approach (Events + Stats tables)

#### Implementation

**Database Schema** (`analytics_logger.py`):
- Added `locomotive_stats` table (address, total_operating_seconds, total_sessions, last_active_time)
- Method `log_loco_operating_time()` for dual-write (events + stats)

**Backend Tracking** (`backend/main.py`):
- Global `loco_start_times` dictionary (address → timestamp)
- Movement start: `speed > 0` and not in dict → save timestamp
- Movement stop: `speed == 0` and in dict → calculate duration, log event
- Real-time tracking for individual locomotives (addresses 1, 5, 7, 8)

**Migration** (`scripts/utils/migrate_operating_time.py`):
- One-time backfill from existing sessions (46 events)
- Assumption: Consist locos operated together (same duration)
- Mapping: C10→[1,5], C11→[7,8]
- Result: Loco 1/5: 22.66h, Loco 7/8: 73.22h

**API Endpoint**:
- `GET /api/analytics/locomotive-stats` - Aggregated stats per locomotive
- Endpoint `/api/analytics/cumulative` enhanced with `loco_operating_time` events

**Frontend Chart** (`AnalyticsPanel.jsx`):
- Bar chart with colored bars (LOCO_COLORS)
- **Visibility**: ONLY in Overview (cumulative historic data)
- Hidden in Current view (events logged only at movement stop)

**Rationale**: Operating Time = cumulative aging/maintenance metric, not session metric

**Commits**: `b7c4114`, `2e6bea9`, `a061d49`, `ff40c8b` (migration), `4641995` (session filtering), `db60bf6`, `6133ca4`, `d791f20`, `b547636` (endpoint fixes), `5642b8c` (always show chart), `c79c83c` (tooltip fix), `84c048d` (overview only)

---

### 2025-01-13 - 🗂️ **DATA DIRECTORY REFACTORING**

**Motivation**: Prevent path errors when adding new analytics endpoints

**Change**: Moved `data/` → `backend/data/`
- **Before**: `Path(__file__).parent.parent / "data" / "analytics.db"` (2 levels up)
- **After**: `Path(__file__).parent / "data" / "analytics.db"` (1 level up)

**Files Modified**:
- `backend/main.py`: 3 endpoints (session, cumulative, locomotive-stats)
- `backend/tracking_daemon.py`: 1 path reference
- `.gitignore`: `data/*.db` → `backend/data/*.db`
- `docs/ANALYTICS.md`: Updated path reference

**Benefits**:
- ✅ Simpler paths (one `.parent` less)
- ✅ Logically correct (data belongs to backend)
- ✅ Prevents future path errors

**Commit**: `aa1d172`

---

### 2025-01-13 - ♻️ **ANALYTICSPANEL REFACTORING**

**Motivation**: Eliminate code duplication (~80 lines, 4+ duplications each)

**Constants Extracted**:
```javascript
// Tooltip styles (4 duplications → 1 constant)
const TOOLTIP_STYLES = {
  contentStyle: { backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' },
  labelStyle: { color: '#e2e8f0' },
  itemStyle: { color: '#e2e8f0' }
};

// Chart axis styles (4 duplications → 1 constant)
const CHART_AXIS_STYLES = {
  grid: { strokeDasharray: '3 3', stroke: '#374151' },
  axis: { stroke: '#9CA3AF' }
};

// Consist addresses (2 duplications → 1 constant)
const CONSIST_ADDRESSES = {
  10: [1, 5],
  11: [7, 8]
};

// Consist colors (2 duplications → 1 constant)
const CONSIST_COLORS = {
  all: 'text-white',
  10: 'text-fuchsia-400',
  11: 'text-blue-400'
};
```

**Helper Functions Extracted**:
```javascript
// Event filtering (3+ duplications → 1 function)
const filterEventsBySession = (events, viewMode, currentSession) => ...

// Address filtering (2 duplications → 1 function)
const getAddressFilter = (consistFilter) => ...

// Consist color (2 duplications → 1 function)
const getConsistColor = (consist, defaultColor) => ...
```

**Confidence Chart Refactored**:
- Eliminated ~30 lines of duplication (data + Cell mapping)
- Used helpers for session filtering, address filtering
- Cleaner, more maintainable code

**Result**:
- Code reduction: ~50 lines
- Build size: 658.74 kB → 658.26 kB
- All charts use shared constants/helpers

**Commit**: `e610f70`

---

### 2025-01-13 - 🔧 **Z21 HEALTH CHECK GRACE PERIOD**

**Problem**: False positive disconnects from single packet loss
- Check every 5s, single failure → immediate OFFLINE
- UDP packet loss → spurious disconnects

**Solution**: Require 2 consecutive failures before marking offline

**Implementation**:
- Global `z21_consecutive_failures` counter
- Success → reset counter to 0, mark ONLINE
- Failure → increment counter
  - If counter == 1 → log warning "(1/2) grace period"
  - If counter >= 2 → mark OFFLINE
- Detection time: 10s (2 × 5s checks)

**Benefits**:
- ✅ Eliminates false positives from occasional packet loss
- ✅ Maintains 5s check interval (responsive)
- ✅ Clear logging ("1/2 grace period")

**Commit**: `5428a81`

---

### 2025-01-13 - ♻️ **ANALYTICS REFACTORING & CLEANUP**

#### Revert All Idle/Break Line Experiments (commit `a406909`)
**Problem**: Multiple failed attempts to show line breaks during idle periods:
- Double-null strategy: Failed when consists move independently
- Dashed lines approach: Wrong logic (marked events as idle instead of gaps)
- Null points with connectNulls=false: Circular iteration, already tried before

**Solution**: Hard reset to commit `3512f8d` (config-driven refactoring working), removed ALL experimental code (88 lines deleted).

**Result**: Clean codebase with original behavior (continuous lines with `connectNulls={true}`)

---

### 2025-01-13 - 🔧 **ANALYTICS UX IMPROVEMENTS**

#### Operating Time Chart Filtering (commit `1e44b33`)
- **Problem**: Operating Time chart didn't respond to consist filters (All/C10/C11)
- **Solution**: Applied `getAddressFilter()` to filter locomotives by consist
- **Result**: All/C10/C11 filtering works across ALL 4 charts consistently

#### Sticky Header Filters (commit `a7d88c7`)
- **Problem**: Consist filters (All/C10/C11) only visible above first chart, disappeared when scrolling
- **Solution**: Moved filters to sticky header (Row 2, below Current/Overview tabs)
- **Features**: Always visible, controls all charts simultaneously, "Filter:" label added
- **Result**: Better UX, no need to scroll up to change filters

#### Chart Remount Fix (commit `e3eaa18`)
- **Problem**: Changing filters All/C11→C10 showed wrong scrollbar position (chart appeared empty, manual scroll needed to correct)
- **Root cause**: React not remounting chart wrapper when filter changed
- **Solution**: Added `key={consistFilter}` to scrollable wrappers (Δt and FPS charts)
- **Result**: Chart width, scrollbar, and scroll position recalculate correctly on filter change

#### Click Outside to Close (commit `d1642d4`)
- **Feature**: Click on backdrop overlay closes Analytics panel
- **Implementation**: `onClick={handleClose}` on backdrop + `stopPropagation` on panel content
- **Result**: Standard modal UX pattern

#### X-Axis Improvements for Overview Mode (commit `945b9e8`)
- **Problem**: In Overview mode with hundreds of events, timestamp labels on X-axis were compressed and illegible
- **Solution**: Conditional X-axis dataKey:
  - **Current mode**: `dataKey="time"` (readable timestamps with few events)
  - **Overview mode**: `dataKey="index"` (event numbers: 1, 50, 100...) + label "Event #" / "Sample #"
- **Applied to**: Δt Trends chart ("Event #") and FPS chart ("Sample #")
- **Result**: Clear, readable X-axis in Overview even with 500+ events

#### Consist Names Shortened (commit `16b1f1f`)
- **Problem**: Consist names too long for chart legends: "Consist 10 - Tracciato Interno (Figura 8)"
- **Solution**: Abbreviated in `config.json`:
  - C10: "Consist 10 - Tracciato Interno (Figura 8)" → "C10 Interno"
  - C11: "Consist 11 - Tracciato Esterno (Ovale)" → "C11 Esterno"
- **Used in**: Chart legends, Config Manager, API responses
- **Benefits**: Cleaner UI, field still configurable (user can change anytime)

#### Min Threshold Line Styling (commit `10fee70`)
- **Change**: Confidence chart "Min Threshold (50%)" line changed from red to white
- **Reason**: Better visibility and consistency with other reference lines

---

### 2025-01-13 - 🚀 **LTTB DOWNSAMPLING WITH CRITICAL EVENT PRESERVATION** (commit `683d263`)

#### Motivation
Analytics reaching >500 events → uniform sampling loses important peaks/valleys and critical anomalies.

#### Implementation

**Added Functions** (`backend/main.py`):

1. **`lttb_downsample()`** - Generic LTTB (Largest Triangle Three Buckets) algorithm
   - Selects points forming largest triangles (preserves visual shape)
   - Much better than uniform sampling for peaks/valleys
   - ~40 lines pure Python (no dependencies)

2. **`smart_downsample_delta_t()`** - Intelligent Δt downsampling
   - **ALWAYS includes ALL critical events** (|Δt| ≥ 1.5s, both positive and negative)
   - Applies LTTB to remaining normal events to reach target (e.g., 500 points)
   - Critical events NEVER lost regardless of sampling

**Updated Endpoint** (`/api/analytics/cumulative`):
- **Δt events**: `smart_downsample_delta_t()` (critical preserved + LTTB on rest)
- **YOLO FPS**: `lttb_downsample()` (shape preservation)

**Performance**:
- Runtime downsampling (always fresh, no stale cache)
- With <1000 events: <20ms overhead (negligible)
- With 5000 events: ~50-100ms (still acceptable)

**Event Volume Example** (90 min session):
- YOLO frames processed: 162,000 frames (30 FPS × 5400s)
- Events logged to DB: 1,080 (every 5s)
- Displayed in Overview (LTTB): 500 points
- Reduction: 324:1 (frames→display), 2.16:1 (DB→display)

**Benefits**:
- ✅ Critical anomalies (|Δt| ≥ 1.5s) ALWAYS visible in Overview
- ✅ Chart shape preserved much better than uniform sampling
- ✅ Ready for >500 events (weeks/months of data)
- ✅ Frontend unchanged (transparent backend optimization)

**Tag**: `analytics-working` updated to include LTTB optimization

---

### 2025-01-13 - 📚 **README UPDATE & ANALYTICS DOCUMENTATION**

**README.md updated** (commit `207d411`):
- Added **Analytics Dashboard** section with complete feature list
- Updated **Project Structure** (added `backend/data/` for SQLite analytics)
- Fixed **GPU model** (GTX 1050 Ti → RTX 2060)
- Added **TensorRT acceleration** details (2-5x faster inference)
- Updated **YOLO model specs** (OBB mAP50 91.7%, oriented bboxes)
- Added **Z21 health** 2-failure grace period
- Replaced INSTALL.md reference with **Quick Start** guide

**Tag updated**: `analytics-working` moved to commit `c4c536d`

---

### 2025-01-13 - ♻️ **ANALYTICSPANEL REFACTORING PHASE 2**

**Completato DRY cleanup** (commit `28882ef`):
- **Card 2/3 color logic**: Use `getConsistColorClass()` helper (eliminated 8 lines ternary duplication)
- **All chart axes**: `XAxis`/`YAxis` use `{...CHART_AXIS_STYLES.axis}` (full consistency)
- **Fix missing CartesianGrid**: Confidence chart now uses shared constant

**Results**:
- Build size: 658.22 kB (stable)
- Code eliminated: ~15 lines (Phase 1+2 total: ~65 lines)
- DRY compliance: 100% - zero duplication

---

### 2025-01-13 - 🔄 **DYNAMIC CHART LINE BREAKS (CONFIG-DRIVEN)**

#### Implementation (commit `c4c536d`)

**Backend** (`/api/config/tracking`):
- New endpoint returns `idle_timeout_seconds` from `config.json`

**Frontend** (`AnalyticsPanel.jsx`):
- Fetch tracking config on mount (idle_timeout_seconds)
- Add `breakLineOnIdle()` helper: inserts null points when gap > idle_timeout
- Apply to Δt Trends chart (breaks line when consist stops)

**Result**:
- Chart shows traces ONLY when locomotives moving (no false lines across gaps)
- Coerenza with backend: same `idle_timeout_seconds` (default 10s, configurable)
- User changes `config.json` → backend restart → frontend reflects new threshold

---

### 2025-01-13 - 🐛 **IDLE LINE BREAKS FIX (ALL FILTER)**

#### Problem (commit `a9ab5d6`)
Initial implementation broke lines only in single-consist filters (C10/C11), not in "All" view.

**Root cause**: Used simple filtering → null points had only single consist null (delta_t_c10=null, delta_t_c11=value).

#### Solution: Double-Null Strategy
- **Filter 'All'**: Apply `breakLineOnIdle()` separately to C10 and C11, then merge chronologically
- Creates **double-null idle points** (both delta_t_c10 AND delta_t_c11 = null)
- `connectNulls={true}` connects through **single nulls** (other consist) but NOT **double nulls** (idle)

**Result**: Idle breaks visible in All/C10/C11 filters

**Known limitation discovered later**: In "All" filter, idle breaks don't work when consists move independently (C10 idle, C11 moving → C11 events between C10 idle points have single null, not double null). Solution planned: dashed lines for idle periods (see next section).

---

### 2025-01-13 - 🎛️ **CONFIG-DRIVEN REFACTORING (DYNAMIC CONSIST SUPPORT)**

#### Motivation
Analytics hardcoded consist IDs 10/11 everywhere → adding/renaming consists required code changes.

#### Implementation (commit `658d636`)

**Backend** (`/api/config/tracking` extended):
- Return consist definitions from `config.json`:
  - `consist_id` → `{name, lead_address, rear_address, addresses: [...]}`

**Frontend** (`AnalyticsPanel.jsx`):
- **Removed hardcoded constants**:
  - `CONSIST_ADDRESSES = {10: [1,5], 11: [7,8]}`
  - `CONSIST_COLORS = {10: 'text-fuchsia-400', 11: 'text-blue-400'}`
- **Added dynamic color palettes** (cyclic, up to 6 consists):
  - `CONSIST_COLOR_PALETTE` (stroke colors)
  - `CONSIST_COLOR_CLASSES` (text colors)
  - `CONSIST_BG_CLASSES` (button backgrounds)
- **Helper functions**:
  - `getConsistStrokeColor()` - Chart line colors (cyclic)
  - `getConsistColorClass()` - Text colors for UI (cyclic)
  - `getConsistBgClass()` - Button backgrounds (cyclic)
  - `getAddressFilter()` - Locomotive addresses per consist (dynamic)
- **Dynamic rendering**:
  - Filter buttons: `Object.keys(consistConfig).map(...)` (not hardcoded 10/11)
  - Chart Line components: `map()` over consist IDs, `dataKey: delta_t_c${id}`
  - Card labels: `C${consistFilter}` (not ternary C10/C11)
- **breakLineOnIdle() refactored**:
  - Generates dynamic `delta_t_cXX` fields for all consists
  - All filter: loops all consist IDs (not hardcoded 10/11)

**Result**:
- Support for **N consists** (2, 3, 5, etc.) from `config.json`
- Add/remove/rename consists: **zero code changes** needed
- Cyclic color assignment (up to 6 consists, then repeats)
- Build size: 659.47 kB (+0.39 kB, acceptable)

**Fix** (commit `3512f8d`):
- Added missing `config = load_config()` call in `get_tracking_config()` endpoint
- Initial deploy had `NameError: name 'config' is not defined`

---

### 2025-01-13 - 🚧 **IDLE VISUALIZATION IMPROVEMENT (IN PROGRESS)**

#### Current Limitation
"All" filter shows continuous lines even during idle periods when consists move independently (e.g., C10 idle for 11 hours while C11 running).

**Root cause**: Double-null strategy doesn't work when one consist moves while other is idle → moving consist events have single null (delta_t_c10=null, delta_t_c11=value), not double null.

#### Planned Solution: Dashed Lines for Idle Periods
**Approach**: Render **dual Line components** per consist:
1. **Active line**: Solid stroke when consist moving
2. **Idle line**: Dashed stroke (`strokeDasharray`) during idle periods

**Implementation steps** (estimated 1-2 hours):
1. Mark events post-idle with flag (e.g., `idle_period_c10: true`)
2. Render 2 Lines per consist: one for active data, one for idle data
3. Idle line: same color but `strokeDasharray="5 5"` (dashed pattern)

**Benefit**: Visual distinction between movement and idle in "All" filter, without breaking existing data processing.

**Status**: Ready to implement (user approved Opzione B - dashed lines)

