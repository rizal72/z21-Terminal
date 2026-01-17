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
- **[docs/SPEED_TABLE_DB_MIGRATION.md](docs/SPEED_TABLE_DB_MIGRATION.md)** - Speed Table CV67-94 DB migration + config refactoring (2025-01-17)
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

## Python Virtual Environment & Deployment

**CRITICAL**: Always use venv for Python commands (Mac and PC).

- **Mac**: `source venv/bin/activate` before running Python
- **PC**: Managed automatically by Task Scheduler (`z21-restart`)

**For complete deployment workflow, rules, and troubleshooting**: See `~/.claude/skills/z21-deployment/SKILL.md`

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
- **Shell**: PowerShell 7.5.4 (SSH), PowerShell 5.1 (Task Scheduler)
- **Deployment**: See `~/.claude/skills/z21-deployment/SKILL.md` for:
  - Deployment decision tree (docs/backend/frontend)
  - PowerShell aliases (z21-deploy-dev, z21-restart, z21-log, etc.)
  - 8 CRITICAL rules (venv, CV test mode, git workflow, etc.)
  - Pre-deploy checklist

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

**Note**: Per changelog storico (2025-12-16 → 2025-01-16), vedi `docs/CHANGELOG_ARCHIVE.md`

---

### 2025-01-17 - 🗄️ **Speed Table DB Migration + Config Refactoring** (v1.0.0)

**Status**: ✅ **PRODUCTION COMPLETE** - JMRI independence achieved for speed table operations

**Implementation Time**: ~8 hours (14 commits total: design → code → test → deploy → bugfixes)

**Objective**: Eliminate JMRI dependency for daily speed table operations by migrating CV67-94 storage from JMRI roster XML to SQLite database.

**Architecture Changes**:

1. **Config Refactoring** - Unified locomotive metadata:
   ```json
   // OLD (scattered)
   {
     "locomotive_colors": {"1": "#FFFF00", "7": "#00FF00"},
     "cv_profiles": {"1": {"normal": {"cv3": 78, "cv4": 58}}}
   }

   // NEW (unified)
   {
     "locomotives": {
       "1": {
         "name": "Gr.675 017",
         "decoder": "LokSound V4.0",
         "color": "#FFFF00",
         "cv_profiles": {"normal": {"cv3": 78, "cv4": 58}},
         "notes": "Lead C10 Interno"
       }
     }
   }
   ```

2. **Database Migration** - CV67-94 in analytics.db:
   - Table: `locomotive_speed_table` (28 CV columns + undo snapshot)
   - Fields: `loco_address`, `cv67`-`cv94`, `previous_values` (JSON), `last_updated`, `source`
   - 1-level undo with swap mechanism (can undo the undo)
   - Audit trail: source tracking ('web_ui', 'jmri_import', 'undo', 'jmri_reimport')

3. **Data Flow**:
   - **Read**: DB primary → JMRI roster fallback (seamless migration)
   - **Write**: Decoder POM → DB update (instant visibility)
   - **Undo**: DB previous_values → Decoder POM (1-click restore)
   - **Re-import**: JMRI roster → DB (manual sync when needed)

**Backend Implementation**:

1. **`backend/services/config_helpers.py`** (NEW - 127 lines):
   - Backward compatible loaders for gradual migration
   - `get_locomotive_color(address)` - unified format with fallback
   - `get_locomotive_cv_profile(address, mode)` - cv3/cv4 retrieval
   - `get_locomotive_name(address)` - name from config
   - `get_all_locomotives()` - complete roster with fallback

2. **`backend/services/speed_table_helpers.py`** (MODIFIED - added 160 lines):
   - `read_cv_speed_table_from_db(loco_address)` - DB read (source of truth)
   - `update_cv_speed_table_in_db(loco_address, cv_values, source)` - DB write with undo snapshot
   - `undo_cv_speed_table(loco_address)` - Swap current ↔ previous values
   - All functions use `data/analytics.db` (PC production only)

3. **`backend/routers/speed_table.py`** (MODIFIED - added 164 lines):
   - **Modified GET** `/api/speed-table/{consist_id}` - Read DB first, JMRI fallback
   - **Modified POST** `/api/speed-table/write/{consist_id}` - Write POM + update DB
   - **NEW POST** `/api/speed-table/undo/{consist_id}` - Restore previous + write to decoder
   - **NEW POST** `/api/speed-table/reimport/{consist_id}` - Force sync from JMRI roster

4. **`backend/z21_manager.py`** + **`backend/video_feed.py`** (MODIFIED):
   - Updated to use `config_helpers` for locomotive data
   - Backward compatible with old config format

**Import Script**:

**`scripts/utils/import_speed_tables_from_jmri.py`** (NEW - 330 lines):
- Standalone script (no backend needed, works without GPU)
- Workflow:
  1. Load JMRI roster (reuses existing `Locomotive` class)
  2. Backup config.json (timestamped)
  3. Refactor config.json (merge scattered data → unified `locomotives`)
  4. Populate database (CV67-94 for all roster)
- Tested standalone on Mac (with DB copied from PC)
- Result: 7 locomotives imported successfully

**Frontend Implementation**:

**`web/src/components/charts/SpeedTableViewer.jsx`** (MAJOR CHANGES):

1. **Component-Level fetchSpeedTableData** (fixed scope bug):
   ```jsx
   const fetchSpeedTableData = async () => {
     // Moved from useEffect to component level
     // Now accessible from writeToDecoder, handleUndo, handleReimport
   };
   ```

2. **Undo Handler**:
   ```jsx
   const handleUndo = async () => {
     // POST /api/speed-table/undo/{consistId}
     // Restores previous_values from DB
     // Writes CVs to decoder via POM
     // Reloads UI (removes asterisks)
   };
   ```

3. **Re-import Handler**:
   ```jsx
   const handleReimport = async () => {
     // POST /api/speed-table/reimport/{consistId}
     // Reads CV67-94 from JMRI roster
     // Updates DB with JMRI values
     // Reloads UI (syncs with JMRI)
   };
   ```

4. **UI Redesign** (after user feedback):
   - **Primary buttons** (left-aligned, prominent): Write, Export CSV
   - **Secondary buttons** (right-aligned, icon-only, semitransparent):
     - Undo: `fa-undo` icon, amber color, tooltip "Undo last change"
     - Re-import: `fa-sync` icon, slate color, tooltip "Re-import from JMRI"
   - Visual hierarchy clear: write/export = main actions, undo/reimport = utilities

5. **UI Refresh After Operations**:
   - Write → `fetchSpeedTableData()` (removes asterisks, syncs CV values)
   - Undo → `fetchSpeedTableData()` (shows restored values)
   - Re-import → `fetchSpeedTableData()` (shows JMRI synced values)

**Critical Bugs Fixed During Testing**:

1. **Gate Crossings Count Bug** (`backend/routers/analytics.py`):
   - **Problem**: Overview tab showed 500 events (downsampled) instead of real count (2000+)
   - **Fix**: Save `original_delta_t_count` before downsampling, return as `total_delta_t_events`
   - **Frontend**: Use `cumulativeData.total_delta_t_events` for accurate stats card

2. **Button Design Rejected** (`web/src/components/charts/SpeedTableViewer.jsx`):
   - **User Feedback**: "i due nuovi bottoni fanno cacare. Solo icona, meglio se rimpicciliti"
   - **Fix**: Changed to icon-only, smaller (`px-2 py-2`), right-aligned with `ml-auto`

3. **UI Not Refreshing After Write/Undo**:
   - **Problem**: CV values updated in DB but asterisks remained in UI
   - **Fix**: Added `await fetchSpeedTableData()` after successful operations

4. **fetchSpeedTableData Scope Error**:
   - **Problem**: Function defined inside `useEffect`, not accessible from handlers
   - **Error**: `Can't find variable: fetchSpeedTableData`
   - **Fix**: Moved function definition to component level (after state declarations)

5. **Import Script Attribute Error**:
   - **Problem**: `AttributeError: 'Locomotive' object has no attribute 'decoder'`
   - **Fix**: Changed `loco.decoder` → `loco.decoder_model` (correct attribute name)

**Testing Results**:

**Mac (Development)**:
- ✅ Import script executed successfully (standalone, no backend)
- ✅ 7 locomotives imported to config.json + DB
- ✅ Config.json refactored (unified locomotives section)
- ✅ DB populated with CV67-94 values from JMRI roster
- ✅ Syntax check: All backend files compiled without errors

**PC (Production)**:
- ✅ Full deployment via `z21-deploy-dev` (frontend build + backend restart)
- ✅ Speed Table GET: DB values displayed correctly
- ✅ CV Write: 28 CVs written + DB updated (asterisks removed after reload)
- ✅ Undo: Previous values restored to decoder + DB swapped
- ✅ Re-import: JMRI roster synced to DB (manual override)
- ✅ Gate Crossings: Accurate count displayed (not downsampled)
- ✅ Button layout: Primary prominent, secondary icon-only

**Deployment Strategy**:

1. **DB Location**: `backend/data/analytics.db` (PC only, not Mac)
2. **Config Migration**: Backward compatible loaders (old format fallback)
3. **Testing Workflow**:
   - Copy DB from PC to Mac (temporary for import script test)
   - Run import script on Mac (no GPU needed)
   - Copy modified DB back to PC
   - Deploy to PC production (full backend + frontend)

**Backward Compatibility**:

- Old config format (`locomotive_colors`, `cv_profiles`) still supported
- `config_helpers.py` checks new format first, falls back to old
- Gradual migration: can run with mixed old/new config
- No breaking changes for existing code

**Key Benefits Achieved**:

1. ✅ **JMRI Independence**: Speed table operations work without JMRI running
2. ✅ **Instant Visibility**: CV changes reflected immediately (no JMRI export/import)
3. ✅ **Undo Support**: 1-click restore of previous CV values
4. ✅ **Centralized Metadata**: All locomotive data in unified config section
5. ✅ **Audit Trail**: Source tracking + timestamps for all DB changes
6. ✅ **Manual Override**: Re-import button syncs from JMRI when needed
7. ✅ **Zero Breaking Changes**: Backward compatible with existing code

**Documentation**:

- ✅ **Design Doc**: `docs/SPEED_TABLE_DB_MIGRATION.md` (634 lines)
  - Complete architecture, schema, workflow, testing plan
- ✅ **Usage Instructions**: Import script, undo, re-import workflows

**Commits** (14 total):
- `08353ce` - Speed table DB migration implementation (core feature)
- `6b8116a` - Show non-validated sessions with badge (UI improvement)
- `7b89eab` - Remove session_validated blocking (frontend fix)
- `9729422` - Fix cumulative scaling bug (critical backend fix)
- `fc7b313` - Change adjustment ±2 to ±1 (conservative iterative)
- `7e3f6a0` - Summary cards redesign (removed Problematic, added Fixed)
- `880ab5a` - Step prominence in speed recommendations (UI tweak)
- `0dd9b98` - Revert horizontal format (user preference)
- `3602259` - Auto-select consist (UX improvement)
- `37a8966` - Fix auto-select logic (use reportsData)
- `77c5822` - Debug console logging (temporary)
- `0190c1a` - Use ONLY last session for auto-select (critical fix)
- `5118e21` - Remove debug console.log (cleanup)
- `[final]` - UI refresh + function scope fix (production ready)

**Files Modified** (11 total):
- `backend/services/config_helpers.py` (NEW)
- `backend/services/speed_table_helpers.py` (MODIFIED)
- `backend/routers/speed_table.py` (MODIFIED)
- `backend/routers/analytics.py` (MODIFIED - Gate Crossings fix)
- `backend/z21_manager.py` (MODIFIED - use config_helpers)
- `backend/video_feed.py` (MODIFIED - use config_helpers)
- `web/src/components/charts/SpeedTableViewer.jsx` (MAJOR CHANGES)
- `web/src/components/AnalyticsPanel.jsx` (MODIFIED - accurate count)
- `scripts/utils/import_speed_tables_from_jmri.py` (NEW)
- `config.json` (TRANSFORMED - unified structure)
- `docs/SPEED_TABLE_DB_MIGRATION.md` (NEW - design doc)

**User Feedback**: "stupendo pare funzioni tutto" 🎯

**Versioning**: Tagged as **v1.0.0** (JMRI independence milestone achieved)

---

### 2025-01-17 - 🎯 **Speed Table Viewer Phase 2: Direct CV Write** (v1.0.0 FINAL)

**Status**: ✅ **PRODUCTION READY** - Complete interactive CV editor with direct decoder programming

**Implementation Time**: ~6 hours (centralized CV write, API endpoint, UI refinements, testing)

**Objective**: Transform read-only Speed Table Viewer into full interactive editor with direct CV write via POM.

**Major Features**:

1. **Centralized CV Write Delay** (z21.py refactoring):
   - Moved `time.sleep(0.1)` into `write_cv_ops_mode()` method
   - Removed explicit sleeps from 4 call sites in `z21_manager.py`
   - DRY principle: centralized logic prevents decoder overload automatically
   - **Files**: `scripts/z21.py`, `backend/z21_manager.py`

2. **Direct CV Write Endpoint** (`POST /api/speed-table/write/{consist_id}`):
   - Writes all 28 CVs (CV67-94) via POM operations mode
   - Accepts `cv_values` dict from frontend (all 28 speed table values)
   - Returns: success status, failed CVs list, total time, loco address
   - Tested: 28 CVs written in ~2.8 seconds
   - **Files**: `backend/routers/speed_table.py` (lines 126-217)

3. **Dual-Button Workflow** (frontend):
   - **"Apply & Write to Decoder"**: Writes CVs + exports CSV backup
   - **"Export CSV Only"**: Exports current values without decoder write
   - Both buttons disabled when no modifications present
   - Visual feedback: success/error messages with timing
   - **Files**: `web/src/components/charts/SpeedTableViewer.jsx`

4. **Visual Feedback for Modifications**:
   - Blue border (`border-blue-400`) on modified CV bars
   - Blue asterisk next to CV value (e.g., "128*")
   - Priority: CRITICAL (red/amber) > modified (blue) > default (slate)
   - User sees EXACTLY which CVs were changed before writing
   - **Files**: `web/src/components/charts/SpeedTableViewer.jsx` (lines 260-280)

5. **Button Disable Logic**:
   - `hasModifications` check compares `cvValuesFloat` vs original `data.cv_values`
   - Write button disabled with tooltip: "No modifications to write"
   - Button always visible (user knows feature exists)
   - **Files**: `web/src/components/charts/SpeedTableViewer.jsx` (lines 53-57, 298)

6. **onBlur Fix** (prevent unwanted interpolation):
   - **Bug**: Clicking checkpoint without changing value still triggered interpolation
   - **Fix**: Compare old vs new value before calling `saveEdit()`
   - Only interpolate if value actually changed
   - **Files**: `web/src/components/charts/SpeedTableViewer.jsx` (lines 191-199)

7. **ESC Key Priority** (emergency stop):
   - Removed ESC handler from checkpoint editor
   - ESC now always bubbles to global emergency stop handler
   - Safety first: emergency stop > editor cancel
   - **Files**: `web/src/components/charts/SpeedTableViewer.jsx` (line removed from input)

8. **CSV Export Backup Suffix**:
   - No modifications: `speed_table_consist_11_loco_7_backup.csv`
   - With modifications: `speed_table_consist_11_loco_7.csv`
   - Clarifies purpose: backup = original roster values
   - **Files**: `web/src/components/charts/SpeedTableViewer.jsx` (lines 48-50)

**Critical Analytics Bug Fixed**:
- **Problem**: Overview mode showed 673 events instead of 500 (downsampling never applied)
- **Root Cause**: Parameter name mismatch - backend `max_points` (snake_case) vs frontend `maxPoints` (camelCase)
- **Fix**: Renamed all `max_points` → `maxPoints` in `backend/routers/analytics.py`
- **Result**: 673→500 delta_t (25% reduction), 1646→500 YOLO (70% reduction)
- **Log Visibility**: Moved verbose logs under `debug_enabled` flag, kept summary always visible
- **Files**: `backend/routers/analytics.py` (lines 48-131)

**Production Testing** (2025-01-17):
- ✅ CV86 written from 80 → 82 on loco 7 (Consist 11)
- ✅ Verified via Hornby Bluetooth app (decoder shows CV86 = 82)
- ✅ All 28 CVs written successfully in 2.81 seconds
- ✅ Visual feedback worked (blue borders, asterisks)
- ✅ Button disable logic correct (no modifications = disabled)
- ✅ Analytics downsampling: Overview chart readable (500 points, smooth curves)

**Key Technical Details**:
- CV write uses Z21 POM (Program On Main) - no programming track needed
- Float precision state preserved throughout editing workflow
- Checkpoint interpolation applied before write (smooth speed curves)
- Compatible with ESU (loco 1,2,5,6,8) and Hornby (loco 7) decoders

**Deployment**:
- ✅ Pushed to GitHub (develop branch)
- ✅ Deployed to PC production via `z21-deploy-dev`
- ✅ Frontend rebuilt (Vite 7.3.0)
- ✅ Backend restarted (Task Scheduler)

**Files Modified** (14 total):
- `scripts/z21.py` - Centralized CV write delay
- `backend/z21_manager.py` - Removed explicit sleeps (4 locations)
- `backend/routers/speed_table.py` - New CV write endpoint
- `backend/routers/analytics.py` - Fixed camelCase parameter bug
- `web/src/components/charts/SpeedTableViewer.jsx` - UI improvements
- `CLAUDE.md` - This changelog entry
- `docs/SPEED_TABLE_VIEWER.md` - Phase 2 documentation (to be updated)

**Versioning History**:
- Initially tagged v1.0.0 (prematurely - CV write not implemented)
- Changed to v0.9.5 (discovered CV write missing)
- Now v1.0.0 FINAL (CV write complete and tested)

**User Feedback**: "perfetto, valori scritti correttamente!" ✅

**Next Steps**: Evaluate "particolare" (user will specify)

---

### 2025-01-17 - 🎉 **v1.0.0 - Production Release**

**Status**: ✅ **PRODUCTION READY** - Complete locomotive control system with AI-powered speed optimization

**Milestone**: First production release with full feature set:
- ✅ Dual consist control (C10, C11) with real-time WebSocket sync
- ✅ YOLO-based computer vision tracking (4 locomotives, OBB model, TensorRT GPU acceleration)
- ✅ Automatic speed compensation via Virtual Consist Mode
- ✅ Interactive Speed Table Viewer with direct CV write to decoder (POM)
- ✅ JMRI-compatible checkpoint interpolation with float precision
- ✅ Cumulative intelligent CV recommendations with auto-clear on fix
- ✅ Session tracking with running session display (green badge in Reports)
- ✅ Analytics dashboard with intelligent downsampling (LTTB algorithm)
- ✅ Mobile-first PWA design with Tailscale HTTPS access

**What's New in v1.0.0**:
- **Speed Table Viewer Phase 2** complete:
  - Interactive editing with checkpoint-based interpolation
  - Direct CV write to decoder via Z21 POM (28 CVs in ~2.8s)
  - Dual-button workflow (Apply & Write vs Export Only)
  - Visual feedback for modifications (blue borders, asterisks)
  - Float precision state (prevents rounding loss)
- **Analytics Downsampling Fix**: Fixed critical bug (673→500 events in Overview mode)
- **Running Sessions**: Visible in Reports tab with green border + "RUNNING" badge
- **Deployment Workflow**: Skill created for Mac → PC automation
- **Documentation**: Consolidated (CLAUDE.md, skills, comprehensive guides)

**Technical Stack**:
- Backend: FastAPI + WebSocket + SQLite + YOLO v8 nano OBB + TensorRT
- Frontend: React 18.3 + Vite 6.0 + Tailwind CSS
- Hardware: Roco Z21 Bianca, Tapo IP camera 720P, PC Windows 11 + GPU

**Production Deployment**: PC Windows (gaming-pc) via z21-deploy-dev

**Production Testing**: CV write verified on loco 7 (CV86: 80→82, confirmed via Hornby app)

**Next Phase**: v1.1.0+ (optional enhancements - system is feature-complete)

---

### 2025-01-17 - 🐛 **Fix: Running Sessions in Reports Tab**

**Status**: ✅ **FIXED AND DEPLOYED**

**Bug**: Running sessions (end_time = NULL) were excluded from Reports list due to SQL filter.

**Impact**: Current active session invisible in Reports tab despite UI supporting green badge.

**Fix**:
- Removed `AND end_time IS NOT NULL` filter in `get_reports_data()` query
- Calculate duration using `time.time()` if `end_time` is NULL (shows elapsed time)
- Added missing `import time` for time module

**Result**: Running sessions now visible in Reports with:
- Green border (`border-green-500/50`)
- Green background (`bg-green-900/10`)
- "RUNNING" badge (green)
- Real-time duration updates on refresh

**Commit**: `54d7e7d` - fix(reports): include running sessions in Reports tab

**Deployed**: Backend restarted on PC production

---

### 2025-01-17 - ⚙️ **Speed Table Viewer: Phase 2 Interactive Editing** (Complete)

**Status**: ✅ **DEPLOYED TO PRODUCTION** - JMRI-compatible checkpoint-based editing with float precision

**Objective**: Transform read-only speed table into fully interactive editor with automatic smoothing via checkpoint interpolation.

**Implementation Time**: ~2 hours (9 tasks)

**Features Implemented**:

1. **Float Precision State** (`cvValuesFloat`):
   - Stores CV values as floats internally (e.g., 146.333...)
   - Rounds only on display (UI shows integers)
   - Rounds only on export (JMRI CSV compatibility)
   - Prevents gradual adjustment propagation loss
   - Example: Adjust CV86 by -1, four times → adjacent CVs smoothly update (no "stuck" values)

2. **Checkpoint System**:
   - Default 10 checkpoints at operational speeds: `[3, 6, 9, 12, 15, 17, 20, 23, 26, 28]` (10%-100%)
   - Checkboxes under all 28 bars (user can customize)
   - Minimum 2 checkpoints enforced (interpolation requires bounds)
   - Toggle on/off with visual feedback

3. **Linear Interpolation**:
   - Auto-recalculates non-checkpoint steps when checkpoint modified
   - Formula: `value = valueA + (valueB - valueA) * (stepX - stepA) / (stepB - stepA)`
   - Interpolates both zones: prev→modified, modified→next
   - Pure float math (no rounding until display/export)

4. **Interactive Editing**:
   - Click checkpoint value (blue bold) → numeric input appears
   - Click checkpoint bar → same input
   - Type new value (0-255), Enter to save, Escape to cancel
   - Keyboard navigation, auto-focus, validation
   - Non-checkpoints: gray text, read-only (auto-interpolated)

5. **Recommendations Approval Workflow**:
   - Checkbox per recommendation (default all checked)
   - Select All / Deselect All buttons
   - "Apply N Selected" button (disabled if 0 selected)
   - Visual feedback: unchecked recommendations opacity 50%
   - Apply → calls `applyInterpolation()` for each selected CV
   - Selection clears after apply

6. **CSV Export Updated**:
   - Phase 1: Exported original + suggested recommendations
   - Phase 2: Exports current `cvValuesFloat` (includes all user edits + applied recommendations)
   - JMRI-compatible format unchanged (CV,value)

**UI/UX Enhancements**:
- Checkpoint values: **blue bold, cursor pointer** (click to edit)
- Non-checkpoint values: gray (auto-interpolated, read-only)
- Percent labels: shown only on checkpoints
- Tooltips: "Click to edit" vs "Auto-interpolated"
- Smooth Tailwind transitions on all changes

**Technical Details**:
- State: `cvValuesFloat` (CV67-94 as floats), `checkpoints` (Set), `editingStep`, `selectedRecommendations` (Set)
- Functions: `interpolate()`, `applyInterpolation()`, `startEditing()`, `saveEdit()`, `toggleCheckpoint()`, `toggleRecommendation()`
- Safety: CV range validation (0-255), minimum 2 checkpoints
- Real-time: interpolation on every checkpoint modification

**Commit**: `db1196a` - feat(speed-table): implement Phase 2 interactive editing (+295 lines, -57 lines)

**Deployment**:
- Deployed to PC production (z21-deploy-dev)
- Frontend rebuilt (Vite 7.3.0, 3.88s)
- Backend restarted (Task Scheduler)

**Skill Update**: Added "Complete Workflow (Mac → PC)" section to `z21-deployment` skill:
- Step 4 reminder: **MUST deploy to PC after push**
- Clarified: Mac = development, PC = production environment

**Testing**: Ready for user validation in production environment.

**Next Phase**: Phase 2B (future) - Direct POM write via Z21 (optional, alternative to CSV export).

---

### 2025-01-17 - 🧹 **CLAUDE.md Cleanup + Deployment Skill Creation**

**Status**: ✅ **COMPLETED** - Documentation consolidation and skill-based workflow enforcement

**Objective**: Eliminate duplication between CLAUDE.md and new deployment skill, enforce correct workflow usage

**Trigger**: I manually executed deployment commands instead of using PowerShell aliases. User corrected: "ma non hai eseguito l'alias!!! Hai fatto tutto a mano"

**Implementation**:

1. **Created Deployment Skill** (`~/.claude/skills/z21-deployment/SKILL.md` - 314 lines):
   - Deployment decision tree (docs/backend/frontend → correct command)
   - PowerShell aliases (z21-deploy-dev, z21-deploy, z21-restart, z21-stop, z21-log)
   - 8 CRITICAL rules (venv, CV test mode, git workflow, frontend rebuild, secrets, SSH protocol, encoding, README language)
   - Pre-deploy checklist (7 items)
   - Config files behavior (config.json vs config.local.json)
   - PC info (SSH, paths, shell, logs)

2. **Consolidated Skill** (404 → 314 lines, 22% reduction):
   - Removed CRITICAL Rule #9 (PowerShell Aliases) - redundant with dedicated section
   - Removed CRITICAL Rule #10 (SSH Username) - evident from examples
   - Removed Common Scenarios - redundant with Decision Tree
   - Removed Quick Reference Table - redundant with PowerShell Aliases

3. **Simplified CLAUDE.md** (~73 lines removed):
   - Python Virtual Environment section: 56 lines → 8 lines
   - Production Deployment section: 35 lines → 10 lines
   - Replaced with references to `~/.claude/skills/z21-deployment/SKILL.md`

**Benefits**:
- ✅ Single source of truth (skill file)
- ✅ Auto-triggered on deployment requests
- ✅ Prevents manual command execution
- ✅ CLAUDE.md cleaner, more maintainable
- ✅ Zero duplication

**User Feedback During Creation**:
- "dove possibile userei comandi one line"
- "SSH gaming-pc da solo ti da errore, serve sempre l'username"
- "ci sono altri aliases su PC che potrsti usare in altri scenari, uno su tutti z21-log"
- "recentemente abbiamo deciso di mettere su git anche claude ed altri files md, per cui quella parte la devi togliere"
- "hai fatto un check per vedere se alcune regole sono duplicate?"

**Files Created**:
- `~/.claude/skills/z21-deployment/SKILL.md` - Complete deployment workflow

**Files Modified**:
- `/Users/riccardosallusti/Documents/_PROGETTI/z21-Terminal/CLAUDE.md` - Simplified deployment sections

---

### 2025-01-17 - 🔄 **SPEED TABLE VIEWER: Cumulative Intelligent Recommendations** (v0.9.0)

**Status**: ✅ **MILESTONE ACHIEVED** - Iterative testing workflow with intelligent "fixed" detection

**Objective**: Transform single-session recommendations into cumulative historical analysis that persists across sessions but auto-clears when speeds are proven OK.

**Implementation Time**: ~6-8 hours (14 commits with multiple iterations on auto-select logic)

**Major Changes**:

1. **Cumulative Historical Data** (Backend):
   - `get_critical_events_by_speed()` now aggregates ALL sessions (removed `session_id` parameter)
   - Cumulative CRITICAL/WARNING counts provide complete problem picture
   - Commit: `08353ce`

2. **Intelligent "Fixed" Detection** (Backend):
   - Speed considered fixed if last tested session has ≥3 Δt events AND <20% CRITICAL rate
   - Fixed speeds excluded from recommendations (problem resolved)
   - Enables iterative workflow: adjust CV → retest → recommendation auto-disappears
   - Commit: `08353ce`

3. **Fixed ±1 CV Adjustment** (Backend - CRITICAL FIX):
   - **Bug**: Cumulative scaling caused massive adjustments (CV86 80→48 = -32!)
   - **User Insight**: "CV misconfiguration error is CONSTANT regardless of CRITICAL count"
   - **Fix**: Changed from `(critical_count // 5) * 2` to fixed `adjustment_magnitude = 1`
   - **Reasoning**: More CRITICALs = more confirmation, NOT bigger CV error
   - **Result**: Conservative iterative approach (adjust -1, retest, repeat)
   - Commits: `9729422`, `fc7b313`

4. **Non-Validated Session Display** (Frontend):
   - Show UI even when session not validated (was blocking entire UI)
   - Added amber badge "WAITING FOR FIRST ΔT" when session exists but no events yet
   - Backend returns latest session regardless of validation state
   - Commits: `6b8116a`, `7b89eab`

5. **Summary Cards Redesign** (Frontend):
   - **Removed**: "Problematic Speeds" card (redundant with Recommendations)
   - **Added**: "Fixed Speeds" card (positive feedback, green theme)
   - **Result**: Card 2 = actionable (what to do), Card 3 = success feedback (what you fixed)
   - Commit: `7e3f6a0`

6. **Step Prominence** (Frontend):
   - "Step 20 (CV86)" format with Step in white font-semibold
   - CV index secondary in gray parentheses
   - Horizontal layout preserved (user preference)
   - Commits: `880ab5a`, `0dd9b98`

7. **Auto-Select Consist** (Frontend - Multiple Iterations):
   - **Goal**: Avoid extra click when opening Speed Tuning tab
   - **Challenge**: Race conditions + wrong data source (cumulativeData has ALL history)
   - **Final Solution**: Use ONLY `reportsData.sessions[0].consists` (last validated session)
   - **Result**: Auto-selects whichever consist(s) ran most recently
   - Commits: `3602259`, `37a8966`, `77c5822` (debug), `0190c1a` (fix), `5118e21` (cleanup)

**Key User Insights Captured**:
- "se adjust continua a sommarsi solo su un CV, resta problema smoothing" → Phase 2 requirement documented
- "io manualmente vado sempre di + o - 2 al massimo" → informed ±1 conservative approach
- "la visualizzazione tutta orizzontale di prima mi piaceva!" → UI preference preserved

**Testing Results**:
- ✅ Cumulative recommendations aggregate historical data correctly
- ✅ Fixed detection works (speed 70% cleared after good session)
- ✅ Non-validated sessions show UI with amber badge
- ✅ Auto-select picks correct consist from last session
- ✅ ±1 adjustment prevents massive CV changes

**Documentation Updated**:
- `docs/SPEED_TABLE_VIEWER.md` - Added "🆕 2025-01-17 Updates" section
- Workflow example showing 3-session iterative testing
- Phase 2 smoothing requirement documented

**Commits**: 14 total (`08353ce` → `5118e21`)

**Files Modified**:
- `backend/services/analytics_db.py` - Cumulative queries + fixed detection
- `backend/services/speed_table_helpers.py` - Fixed ±1 adjustment
- `backend/routers/speed_table.py` - Latest session (any state)
- `web/src/components/charts/SpeedTableViewer.jsx` - UI improvements
- `web/src/components/AnalyticsPanel.jsx` - Auto-select consist logic
- `docs/SPEED_TABLE_VIEWER.md` - Feature documentation
- `CLAUDE.md` - This changelog entry

**Versioning Decision**: Tagged as **v0.9.0** (not v1.4)
- Current: Feature-complete Phase 1 (Speed Table Viewer read-only)
- Future v1.0.0: Phase 2 Auto CV Adjust with smoothing (automation completa)
- Reasoning: 0.x = "stable but evolving", 1.0 = production-ready auto-tuning

---

### 2025-01-16 - 📊 **SPEED TABLE VIEWER: Phase 1 Complete** (Read-Only CV Analysis)

**Status**: ✅ **PRODUCTION READY** - Visual JMRI-style speed table with CV recommendations

**Feature**: 28-bar visualization of CV67-94 with automatic CV adjustment recommendations based on real-time consist performance data.

**Implementation**:
- **Time**: ~8 hours (complete feature + critical bug fixes)
- **Commits**: 14 commits (`078b215` → `1d1d752`)
- **Documentation**: `docs/SPEED_TABLE_VIEWER.md` (complete technical spec)

**Backend** (3 files: 2 new, 1 modified):
- ✅ `routers/speed_table.py` - API endpoint `/api/speed-table/{consist_id}`
- ✅ `services/speed_table_helpers.py` - CV calculation logic (reuses existing Locomotive class)
- ✅ `services/analytics_db.py` - Query CRITICAL events + mean Δt per speed

**Frontend** (1 new component):
- ✅ `SpeedTableViewer.jsx` - 28 vertical bars + recommendations table + CSV export

**Features Implemented**:
- ✅ 28 vertical bars displaying current CV values from JMRI roster XML
- ✅ Color-coded highlighting (gray/amber/red) based on CRITICAL event counts
- ✅ Speed percentage labels (10%, 20%, ..., 100%) aligned to JMRI steps
- ✅ CV adjustment recommendations with direction based on mean Δt sign
- ✅ CSV export for manual JMRI DecoderPro import
- ✅ Real-time session tracking (session ID displayed in Current view + Reports tab)
- ✅ Running session highlighted in Reports list (green border + "RUNNING" badge)

**Critical Bugs Fixed**:
1. **Emoji in backend logs** → ASCII-only `[ERROR]` prefix (commit `5d64b74`)
2. **macOS metadata files** → Skip `._*.xml` files (commit `5d64b74`)
3. **CV recommendation direction** → Use mean Δt sign (negative → decrease CV, positive → increase CV) - CRITICAL fix (commit `91f7ce6`)
4. **Step percentage alignment** → Use `Math.floor()` instead of `Math.round()` (commit `eb7c844`)

**Algorithm Highlights**:
- **Speed to JMRI step**: `step = floor(dcc_speed / 4.5) + 1` (28 steps, 0-126 DCC speeds)
- **CV adjustment magnitude**: `(critical_count // 5) * 2` (conservative, user-validated)
- **Direction logic**: `delta_t < 0` → adjust faster → decrease CV | `delta_t > 0` → adjust slower → increase CV

**Session Tracking Integration**:
- Session ID visible in Current view (inside duration card)
- Running sessions highlighted in Reports tab (before end_time)
- Speed Table uses current/last validated session for recommendations

**User Feedback**: "Stuoendo, un lavoro fantastico" 🎯

**Phase 2 Roadmap** (not implemented):
- Interactive CV editing (keyboard arrows, drag-to-adjust)
- CV smoothing (±3 adjacent steps interpolation)
- Auto-apply to decoder (direct POM writes)
- Speed table validation (monotonicity checks)

**References**:
- Full documentation: `docs/SPEED_TABLE_VIEWER.md`
- API spec, algorithms, testing notes, known limitations

---

### 2025-01-17 - 🔄 **Speed Table Viewer: Cumulative Intelligent Recommendations**

**Status**: ✅ **IMPLEMENTED**

**Objective**: Replace single-session recommendations with cumulative historical data + intelligent "fixed" detection

**User Request**: "Raccomandazioni dovrebbero essere incrementali - se risolvo speed 70%, raccomandazione sparisce, ma speed 100% non testata deve restare"

**Implementation**:

1. **Cumulative Historical Data**:
   - `get_critical_events_by_speed()` - Removed `session_id` parameter, aggregates ALL sessions
   - CRITICAL/WARNING counts from full history
   - Mean Δt calculated across all historical events (more accurate direction)

2. **Intelligent "Fixed" Detection**:
   - For each speed with CRITICAL, check last session that tested it
   - **Fixed criteria**: >= 3 Δt events AND < 20% CRITICAL rate (max 1/5 events)
   - Fixed speeds excluded from recommendations (proven OK)
   - Query iterates: find last session per speed → count events → calculate rate

3. **Fixed ±1 CV Adjustment** (critical bug fix):
   - **OLD (WRONG)**: `adjustment = (critical_count // 5) * 2` → 83 CRITICAL = -32! 😱
   - **NEW (CORRECT)**: `adjustment = 1` (fixed)
   - **User insight**: CV misconfiguration error is CONSTANT regardless of count
     - 10 CRITICAL = CV too high by ~1
     - 100 CRITICAL = STILL too high by ~1 (same config!)
     - More CRITICALs = more confirmation, NOT bigger error
   - Iterative workflow: adjust -1, retest, still problematic? -1 again

4. **Non-Validated Session Display**:
   - Added `get_latest_session()` method (returns any session, validated or not)
   - Router always shows session_id (even if not validated)
   - Frontend badge **"WAITING FOR FIRST ΔT"** (amber) when `session_validated = false`
   - Historical recommendations always visible (independent from session state)
   - Fixed frontend blocking condition (`if (!data || !session_validated)` → `if (!data)`)

**Workflow Example** (C11 - Tracciato Esterno):
```
Session 1: 70% + 100% tested
  Speed 70%: 12 events, 8 CRITICAL → CV82 -1
  Speed 100%: 8 events, 7 CRITICAL → CV94 -1

Session 2: ONLY 70% tested (validate fix)
  Speed 70%: 6 events, 0 CRITICAL (0% rate) → FIXED! Recommendation disappears ✅
  Speed 100%: NOT tested → CV94 -1 PERSISTS ⚠️

Session 3: ONLY 100% tested
  Speed 100%: 6 events, 1 CRITICAL (16.7% rate) → FIXED! Recommendation disappears ✅
```

**Phase 2 Smoothing Requirement** (documented):
- User insight: "Se adjust continua a sommarsi solo su un CV, resta problema smoothing"
- Auto-adjust MUST smooth adjacent CVs to preserve speed curve
- Algorithm: CV target ±1, CV±1 adjacent ±0.5 (rounded)
- Without smoothing: step/jump in curve → inconsistent loco behavior

**Commits**:
- `08353ce` - Implement cumulative intelligent recommendations
- `6b8116a` - Show non-validated sessions with badge
- `7b89eab` - Remove session_validated blocking condition (frontend fix)
- `9729422` - Fix cumulative scaling bug (±2 became -32 with 83 CRITICAL!)
- `fc7b313` - Change adjustment from ±2 to ±1 (iterative conservative)

**Files Modified**:
- `backend/services/analytics_db.py` - get_critical_events_by_speed(), get_latest_session()
- `backend/services/speed_table_helpers.py` - calculate_cv_recommendations()
- `backend/routers/speed_table.py` - use cumulative data + latest session
- `web/src/components/charts/SpeedTableViewer.jsx` - badge + blocking fix
- `docs/SPEED_TABLE_VIEWER.md` - comprehensive update section

**Benefits**:
- ✅ Zero cognitive load (system remembers all problems)
- ✅ Iterative testing (adjust → retest → auto-clear if OK)
- ✅ Conservative (±1 prevents overshooting)
- ✅ Phase 2 ready (smoothing algorithm documented)

---

### 2025-01-17 - 📄 **CSV Export JMRI-Compatible + Phase 2 Design Documentation**

**Status**: ✅ **COMPLETED**

**Objective**: Finalize Phase 1 CSV export for seamless JMRI DecoderPro import workflow + comprehensive Phase 2 design documentation

**Implementation Time**: ~3-4 hours (research JMRI import, refactor CSV export, write extensive Phase 2 docs)

---

#### Part 1: CSV Export JMRI-Compatible

**Research**: JMRI DecoderPro CSV import capabilities
- ✅ Confirmed: JMRI supports CSV import via File → Import → CSV
- ✅ Format required: Simple 2-column `CV,value` (no extra metadata)
- ⚠️ Historical bug: Quoted headers caused import failures (fixed in JMRI 5.x+)

**Changes**:
```javascript
// OLD (multi-column, not importable):
'JMRI Step,CV Index,Current Value,Suggested Value,Delta,Critical Count,Warning Count,Notes\n'
'20,86,128,126,-2,12,5,"Needs adjustment"\n'

// NEW (JMRI-ready):
'CV,value\n'
'86,126\n'
```

**Logic Update**:
- If CV has recommendation → use **suggested value** (optimized)
- If CV is OK → use **current value** (no change)
- Result: CSV contains speed table ready to apply directly

**UI Changes**:
- Button label: "Export CSV" → **"Export for JMRI"**
- Filename suffix: `_JMRI.csv` (clarifies purpose)
- Tooltip: Added JMRI menu path "(File → Import → CSV)"

**User Workflow** (zero friction):
1. Click "Export for JMRI" in Speed Table Viewer
2. Download `speed_table_consist_11_loco_7_JMRI.csv`
3. JMRI DecoderPro → File → Import → CSV → Select file
4. Write to decoder (ops mode or programming track)

**Commits**:
- Frontend: `web/src/components/charts/SpeedTableViewer.jsx` (lines 48-77, 237-241, 293)

---

#### Part 2: Phase 2 Design Documentation (Comprehensive)

**Documented in**: `docs/SPEED_TABLE_VIEWER.md` (new section ~400 lines)

**Topics Covered**:

1. **JMRI Checkpoint System** (How It Works)
   - Checkbox-based fixed points (user controls which steps)
   - Automatic linear interpolation between checkpoints
   - Edit behavior (modify checkpoint → all intermediate steps recalculate)
   - Mathematical formula with examples

2. **Checkpoint Strategy: Operational Speed Percentages**
   - **Key Insight**: Checkpoints should match controller usage (10%, 20%, ..., 100%)
   - **Default checkpoints**: Steps `[3, 6, 9, 12, 15, 17, 20, 23, 26, 28]`
   - **Rationale**: Users never command intermediate steps directly (only used by decoder during acceleration)
   - Mapping table: Percentage → DCC Speed → JMRI Step → CV Index

3. **The Rounding Problem** (Critical Design Decision)
   - **Issue**: Integer-only math prevents gradual adjustments from propagating
   - **Example**: Adjusting step 20 by -1 requires -3 to -4 iterations before adjacent steps change
   - **Solution**: Float precision internally, round only on display/export
   - **Benefits**: Mathematically accurate, gradual propagation works correctly, JMRI-compatible

4. **Implementation Plan** (Detailed)
   - UI changes: Checkpoint checkboxes, interactive editing, real-time preview
   - Data structure: Float precision state (`cvValuesFloat`)
   - Interpolation algorithm: Linear between checkpoints (code examples)
   - Edge cases: First/last checkpoint handling
   - Backend changes: Minimal (endpoint already complete)

5. **Features Roadmap**
   - Core (required): Checkpoint editing, float precision, interactive adjustment
   - Optional: Auto-apply to decoder, validation, undo/redo, preset curves

6. **Timeline Estimate**: 12-16 hours total effort

**Code Examples**: Complete JavaScript/JSX snippets for all major functions

**Benefits**:
- ✅ Zero ambiguity for future implementation
- ✅ Captures JMRI workflow understanding
- ✅ Documents float precision rationale (critical decision)
- ✅ Ready for Phase 2 kickoff (no rework needed)

---

**Files Modified**:
- `web/src/components/charts/SpeedTableViewer.jsx` - CSV export refactor
- `docs/SPEED_TABLE_VIEWER.md` - Phase 2 section (~400 lines added)
- `CLAUDE.md` - This changelog entry

**Key Insight Captured** (from user):
> "I checkpoint attivi di default devono sempre essere quelli corrispondenti alle speed percentuali 10 20 30 40 etc, perchè muovendo le loco sempre usando gli step percentuali, che è come facciamo sempre noi, andiamo ad interpolare solo i valori intermedi"

**Result**: Phase 1 finalized (JMRI-ready export), Phase 2 fully designed and documented. Ready to implement when user validates Phase 1 in production.

---

### 2025-01-17 - 🎯 **Phase 2 User Approval Workflow Design**

**Status**: ✅ **DOCUMENTED**

**Objective**: Define semi-automatic CV adjustment workflow with user approval

**User Request**:
> "Io preferisco il 2 ma mi piacerebbe che la preview fosse cmq in realtime sulle barre e poi approve finale, la uno è troppo granulare, non è rocket science"

**Approach Finalized**: Checkboxes + Real-Time Preview + Final Approval

---

#### Design Decisions

**What User Wanted**:
- ✅ Batch approval (not per-CV granular)
- ✅ Real-time preview on bars (visual feedback immediate)
- ✅ Single final approval (not rocket science)

**How It Works**:

1. **Recommendations List** (with checkboxes)
   - Default: All recommendations checked (opt-out model)
   - User unchecks recommendations they don't want to apply
   - Select All / Deselect All buttons

2. **Real-Time Preview** (on speed table bars)
   - Checked recommendation → Bar changes color immediately (blue → orange)
   - Checkpoint bars: Solid orange (direct modification)
   - Interpolated bars: Light orange (auto-calculated)
   - Unchecked → Bar reverts to blue (no change)
   - Tooltip: "Current: 128 → New: 127 (float: 126.67)"

3. **Impact Summary**
   - "2 checkpoints + 8 interpolated = 10 CVs will change"
   - User sees EXACTLY what will be modified before approval

4. **Final Approval Button**
   - "Apply 2 Selected Changes"
   - Disabled if no checkboxes selected
   - Opens confirmation dialog with summary

5. **Confirmation Dialog**
   - Summary: "2 checkpoint values, 8 interpolated, Total: 10 CVs"
   - Choose method: Export to JMRI CSV OR Write via POM (Z21)
   - Cancel button always available

**Benefits**:
- ✅ Not too granular (single approval, not per-CV)
- ✅ Visual feedback (bars change in real-time)
- ✅ Safe (confirmation dialog before write)
- ✅ Flexible (user can select/deselect)
- ✅ Simple ("not rocket science")
- ✅ WYSIWYG (bars show exact effect)

**Implementation Details**: Full code examples in `docs/SPEED_TABLE_VIEWER.md` (~200 lines added)
- State management (selected recommendations, projected CV values)
- Checkbox handlers (toggle, select all, deselect all)
- Real-time preview calculation (useEffect on selection change)
- Bar rendering with color coding (checkpoint vs interpolated)
- Apply button handler (confirmation dialog + export/write)

**Safety Features**:
- Visual validation (color-coded bars)
- Tooltip precision (shows float values)
- Confirmation dialog (summary before write)
- Optional warnings (monotonicity, large jumps, range check)
- Undo capability (reset to original values)

**User Experience Flow**: 5 steps documented
1. View recommendations (all checked by default)
2. Adjust selections (uncheck unwanted, bars update real-time)
3. Review visual preview (hover for exact values)
4. Click "Apply Selected Changes" (confirmation dialog)
5. Choose method (Export CSV or POM write)

**Files Modified**:
- `docs/SPEED_TABLE_VIEWER.md` - User Approval Workflow section (~200 lines)
- `CLAUDE.md` - This changelog entry

**Key Insight Captured**: Batch approval with real-time preview strikes optimal balance between safety and usability. Per-CV approval is overkill for simple CV adjustments.

**Recommendation Persistence Clarified**:
- Recommendations are **persistent** (calculated on-the-fly from cumulative historical data)
- Cancel button does NOT consume recommendations (they remain until resolved)
- Two resolution paths:
  1. Manual: User applies changes via JMRI/POM
  2. Automatic: New test session shows speed FIXED (< 20% CRITICAL rate)
- Iterative workflow: Apply -1 → test → if still problematic, apply -1 again
- Database: No changes on Cancel, recommendations recalculated from same historical events

**Files Modified**:
- `docs/SPEED_TABLE_VIEWER.md` - Recommendation Persistence section (~80 lines)
- `CLAUDE.md` - This clarification

---

## 📋 TODO / Future Enhancements

**Note**: Nessun TODO attivo. Vedi sezioni precedenti per roadmap features (Speed Table Phase 2, YOLO expansion, etc.)

---
