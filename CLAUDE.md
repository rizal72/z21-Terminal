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

## Changelog

**Note**: Per changelog storico (2025-12-16 → 2025-01-16), vedi `docs/CHANGELOG_ARCHIVE.md`

---

### 2025-01-19 - 📊 **ANALYTICS CONFIGURATION + CONFIG REORGANIZATION**

**Status**: ✅ **PRODUCTION READY** - Configurable chart optimization + organized config structure

**Analytics Configuration**:
- **New section**: `analytics.max_chart_events` (default 500)
- **Purpose**: Unified threshold for chart optimization
  - **Current view**: Shows last N events (no downsampling, full resolution)
  - **Overview view**: Downsamples to N events if total > N (LTTB + critical events)
- **Settings UI**: New Analytics tab (after Tracking, before Locomotives)
  - Input: number (100-2000, step 50)
  - Info: Performance vs history trade-off
  - Hot reload: No restart required (frontend-only parameter)
- **Backend**:
  - GET `/api/config/analytics` - Returns max_chart_events
  - POST `/api/settings/update` - Handles analytics section save
  - `routers/analytics.py` - Dynamic config load instead of hardcoded 500/1000

**Config.json Reorganization**:
- **Sections reordered** (matches Settings UI logical flow):
  1. debug (system - top)
  2. z21 (hardware)
  3. camera (hardware CV)
  4. video (output CV)
  5. consists (operations)
  6. gates (tracking zones)
  7. tracking + tracking_OBB + tracking_standard (YOLO + timing)
  8. **analytics** (NEW - chart optimization)
  9. locomotives (operations - bottom)
- **Locomotives sorted**: 1,2,4,5,6,7,8 (was random: 7,6,8,1,4,5,2)

**Import Script Fixes**:
- `import_single_locomotive.py`:
  - ✅ Fixed `analytics.db` → `data.db` (correct database path)
  - ✅ Added `testing` profile to `cv_profiles` (Test Mode support)
  - ✅ Dry-run shows speed table CV67-94 values
- Deleted obsolete scripts:
  - `import_speed_tables_from_jmri.py` (one-time migration)
  - `import_functions_from_jmri.py` (one-time migration)

**Commits**: `3ee3122`, `42d8705`, `3f08cd4`, `87956e1`, `aab532c`, `74dfc0c`, `1709534`

---

### 2025-01-18 - ✅ **TIMING_THRESHOLDS REFACTORING** (COMPLETED)

**Status**: ✅ **PRODUCTION READY** - Major nomenclature change for timing thresholds completed

**Motivation**: Current naming (`normal`, `warning`) semantically confusing - thresholds are UPPER limits but names suggest status

**Current Implementation** (pre-refactoring):
```json
{
  "timing_thresholds": {
    "normal": 1.0,    // Semantically confusing: max for SYNCED (not "normal")
    "warning": 1.5,   // Semantically confusing: max for WARNING (but >= 1.5 is CRITICAL!)
    "max_delta_t": 10.0  // OK - outlier filter
  }
}
```

**Logic**: `|Δt| < 1.0` → SYNCED, `1.0 ≤ |Δt| < 1.5` → WARNING, `|Δt| ≥ 1.5` → CRITICAL

**New Implementation** (post-refactoring):
```json
{
  "timing_thresholds": {
    "warning": 1.0,    // Clear: |Δt| >= 1.0 → WARNING
    "critical": 1.5,   // Clear: |Δt| >= 1.5 → CRITICAL
    "max_delta_t": 10.0  // Unchanged
  }
}
```

**Logic**: `|Δt| < 1.0` → SYNCED (implicit), `|Δt| ≥ 1.0` → WARNING, `|Δt| ≥ 1.5` → CRITICAL

**Changes**:
1. **Rename keys**: `normal` → `warning`, `warning` → `critical`
2. **Cleanup hardcoded values**: Replace `|| 1.0`, `|| 1.5`, `|| 2.0` with `DEFAULT_TIMING_THRESHOLDS` import
3. **Fail fast strategy**: Remove silent fallbacks, raise error if config corrupted
   - `DEFAULT_TIMING_THRESHOLDS` only in `main.py` for disaster recovery (config.json missing)
   - Elsewhere: fail fast if `timing_thresholds` missing or incomplete
4. **Fix obsolete values**: `2.0` hardcoded → `1.5` (current production value)

**Files to modify** (12 total):
- **Config**: `config.json` (1)
- **Backend**: `main.py`, `dependencies.py`, `config_manager.py`, `routers/config.py`, `z21_manager.py`, `ws_tracking.py`, `yolo_tracker.py`, `tracking_daemon.py`, `log_colors.py` (9)
- **Frontend**: `SettingsModal.jsx`, `DeltaTStatsPanel.jsx`, `DeltaTChart.jsx` (3)

**Testing plan**:
1. Backend compile check (all .py files)
2. Frontend build (npm run build)
3. PC deployment (z21-deploy-dev)
4. Functional test: tracking daemon + analytics + speed compensation
5. Verify logs show correct thresholds

**Risk**: High impact refactoring (touches core tracking logic + analytics). Checkpoint commit done before starting.

---

### 2025-01-18 - ⚙️ **Settings UI Complete + Consist Manager Enhancements**

**Status**: ✅ **COMPLETE** - Unified settings management + gate assignment feature

**Major Features**:

**1. Settings UI - Complete Implementation** (Phases 1-3):

**Phase 1 - Backend Migration**:
- Created `scripts/utils/migrate_config_unified.py` (one-time migration script)
- Extracted Z21 settings from hardcoded values → `config.z21` section
- Merged camera_config.json → `config.camera` section
- Credentials split: `config.json` (versionated) + `config.local.json` (gitignored, auto-merged)
- Updated backend loaders: `main.py`, `z21_manager.py`, `video_feed.py`, `rtsp_handler.py`

**Phase 2 - Backend API Endpoints**:
- `POST /api/settings/update` - Rewritten for unified config structure
- `POST /api/settings/yolo-preset/load` - Load tracking_OBB/tracking_standard profiles
- `POST /api/settings/z21/test` - Test Z21 connection (host/port validation)
- `POST /api/settings/camera/test` - Test RTSP stream (IP/port/credentials validation)
- Restart detection matrix: backend/video_feed/tracker/none (hot reload)

**Phase 3 - Frontend 7 Tabs**:
- System: debug.enabled toggle
- Z21 Network: host, port + test button
- Camera: IP, port, stream, username, password + test button
- Video Feed: FPS slider (hot reload, no restart)
- YOLO Model: confidence, IoU, OBB toggle + preset buttons (OBB/Standard)
- Tracking: active/idle FPS, timing thresholds (normal/warning/max_delta_t)
- Locomotives: read-only display (name, decoder, functions count)

**Config Structure** (post-migration):
```json
{
  "z21": {"host": "192.168.1.111", "port": 21105},
  "camera": {"ip": "...", "port": 554, "stream": "stream2", "username": "", "password": ""},
  "video": {"fps": 30},
  "tracking": {"fps": {...}, "timing_thresholds": {...}, "yolo_*": ...}
}
```

**2. Consist Manager - Gate Assignment Feature**:

**Frontend** (`ConsistForm.jsx`):
- Added `gate_assignment` to formData state
- Created `handleGateAssignmentChange()` handler for dropdown logic
- New UI section: "Gate Tracking Mode (Advanced)" with two dropdowns:
  - Reference loco monitored by: [All gates / Gate 3 / Gate 4 / ...]
  - Adjust loco monitored by: [All gates / Gate 3 / Gate 4 / ...]
- Mode indicator: automatic detection (symmetric green / asymmetric amber)
- Logic: both="All gates" → `gate_assignment: null`, specific gates → `{reference: X, adjust: Y}`

**Backend** (`routers/config.py`, `services/broadcast.py`):
- `POST /api/consists`: Read `gate_assignment` from request
- `PUT /api/consists/{address}`: Update `gate_assignment`
- `build_consist_response()`: Include `gate_assignment` in consist data

**Examples**:
- Consist 10 (figure-8): `{"reference": 3, "adjust": 4}` = asymmetric, directional
- Consist 11 (oval): `null` = symmetric, bidirectional

**3. Bug Fixes**:
- Locomotive decoder field: Changed from `decoder_model` to `decoder` (correct field name)
- Settings modal width: `max-w-4xl` → `max-w-6xl` (match Analytics panel, remove scrollbar)
- Gate assignment not loaded: Added `gate_assignment` to `ConsistManagerModal` handleEdit
- Gate assignment not saved: Added `gate_assignment` to `ConsistForm` onSubmit payload
- Emoticons removal: Replaced emoji in `config.json` notes with ASCII text (encoding compliance)

**Commits** (30 total today):

**Database Refactoring** (Phase 0-2):
- `22b24c8` - refactor: centralize DB access - analytics_db → data_db (Phase 0)
- `d404c50` - refactor: rename database file analytics.db → data.db (Phase 1)
- `0923003` - refactor: rename cv_profile_mode → test_mode (systematic rename)
- `710a5c1` - feat(db): migrate operational state to database (Phase 2)
- `24a40e3` - fix: replace all Unicode emojis with ASCII in migration script
- `46156d8` - fix: add missing DataDB import in main.py
- `e8ea15a` - fix: migration script Unicode error on Windows
- `7d71995` - fix: update all remaining analytics.db → data.db references
- `473b864` - feat: add merge script for analytics.db → data.db
- `dd0eb91` - fix: correct merge script schema (event_type + data JSON)
- `735787c` - docs: update DB_REFACTORING.md with Phase 0-2 completion log

**Speed Correlation Chart Fixes**:
- `4ba4169` - fix: restore speed percentage labels on X-axis
- `285dd31` - fix: move CustomTick outside component and pass as reference
- `734c075` - fix: remove overlapping 'DCC Speed' label from X-axis

**Settings UI** (Phase 1-3):
- `0620ef7` - docs: add comprehensive Settings UI design document
- `19402d2` - refactor: remove Reload Roster button, add Settings button
- `e4395dc` - feat: add Settings modal component (Phase 3 - Part 1)
- `e131a9f` - feat: add config API endpoints (Phase 3 - Part 2)
- `2c4b022` - feat: Phase 1 - Backend migration to unified config structure
- `2c74aae` - feat: Phase 2 - Backend API expansion
- `0c880d2` - feat: Phase 3 - Frontend Settings UI (7 tabs)
- `1d64ed7` - fix: use correct decoder field name (decoder not decoder_model)
- `9afd825` - fix: increase Settings modal width to max-w-6xl

**Consist Manager - Gate Assignment**:
- `1acd7a6` - feat: gate_assignment UI implementation
- `734d0b1` - fix: load gate_assignment from config (broadcast.py)
- `8fc154a` - fix: pass gate_assignment to edit form
- `a61ad55` - fix: pass gate_assignment on submit

**Cleanup**:
- `0392b58` - refactor: remove emoticons from config.json notes

**Documentation**:
- `bfa1957` - docs: document timing_thresholds refactoring plan
- `f9f0764` - docs: complete changelog for 2025-01-18

**Files Modified** (15 total):
- **Migration**: `migrate_config_unified.py` (NEW)
- **Backend**: `main.py`, `z21_manager.py`, `video_feed.py`, `rtsp_handler.py`, `routers/config.py`, `services/broadcast.py` (6)
- **Frontend**: `SettingsModal.jsx`, `ConsistForm.jsx`, `ConsistManagerModal.jsx` (3)
- **Config**: `config.json`, `config.local.json` (2)

**Testing**: ✅ Complete deployment and functional testing on PC production environment

**User Feedback**: "stupendo pare funzioni tutto" (Settings UI save), gate_assignment load/save verified working

---

### 2025-01-17 - 🎉 **JMRI INDEPENDENCE ACHIEVED** (v1.0.0)

**Status**: ✅ **MILESTONE COMPLETE** - z21-Terminal is now fully autonomous for daily operations

**Implementation**: 17+ commits spanning function labels migration, broadcast fixes, and config-based locomotive loading

**Achievement**: **JMRI now optional** - only needed for import script when adding new locomotives to the roster

**Liberation Day**: Complete self-sufficiency for daily railway operations without external dependencies

**What Changed**:

1. **Function Labels F0-F28** → `config.json` (was: JMRI roster XML only):
   ```json
   {
     "locomotives": {
       "1": {
         "functions": [
           {"number": 0, "label": "light", "lockable": true},
           {"number": 1, "label": "sound", "lockable": true},
           ...
         ]
       }
     }
   }
   ```
   - New script: `import_functions_from_jmri.py` (one-time migration)
   - Backend reads config first, JMRI roster fallback
   - Web dashboard displays function labels from config

2. **Locomotive Roster** → `config.json` (was: JMRI roster XML required):
   - `load_all_locomotives_from_config()` in roster_loader.py
   - Backend loads all 7 locomotives from config (address, name, decoder, color, cv_profiles, functions)
   - Dropdown list shows consists + individual locomotives ✅
   - **Tested**: Renamed `roster/` → `roster.backup/` on PC → backend still works! 🎉

3. **Speed Tables CV67-94** → `analytics.db` (was: JMRI roster XML):
   - Editable via web UI (Speed Table Viewer)
   - Undo/Re-import functionality
   - See detailed changelog sections below for implementation

4. **CV19 Consist Management** → Automatic (was: JMRI required):
   - Virtual Mode / DCC Mode toggle in web UI
   - Operations mode CV write (no programming track needed)
   - State persisted in config.json

5. **Consist CRUD** → Web UI (was: JMRI required):
   - Create, edit, delete consists via web dashboard
   - Consist configuration in config.json

**The Ultimate Test** 🎯:

```bash
# PC Windows - Rename JMRI roster directory
Rename-Item 'roster' -NewName 'roster.backup'

# Restart backend
z21-restart

# Result:
[INIT] Loading all locomotives from config.json...
[INIT] Loaded 7 locomotives
[INIT] Initialized locomotive 1 (in consist 10)
[INIT] Initialized locomotive 2
[INIT] Initialized locomotive 4
[INIT] Initialized locomotive 5 (in consist 10)
[INIT] Initialized locomotive 6
[INIT] Initialized locomotive 7 (in consist 11)
[INIT] Initialized locomotive 8 (in consist 11)
```

✅ **Backend runs perfectly without JMRI roster!**
✅ **Web dashboard shows all 9 entries** (2 consists + 7 locomotives)
✅ **Function clicks work** (no more `[WARN] Address X not found`)
✅ **JMRI now optional** - only needed for import scripts when adding new locomotives

**Key Commits**:
- `f64da28` - Function labels migration to config.json
- `5192495` - Fix broadcast.py typo (_locomotive_dict → _locomotive_data)
- `5d77537` - Load locomotives from config.json (JMRI fallback)
- Plus all Speed Table DB Migration commits (see detailed section below)

**Import Scripts**:
- `scripts/utils/import_speed_tables_from_jmri.py` - Speed tables + config refactoring
- `scripts/utils/import_functions_from_jmri.py` - Function labels F0-F28 migration

**Documentation Updated**:
- ✅ `docs/LOCOMOTIVE_SYNC_MAC_PC.md` (Mac/PC workflow for adding new locos)
- ✅ `docs/JMRI_INTEGRATION.md` (updated independence status)
- ✅ `docs/Z21_PROTOCOL.md`, `docs/CONSIST_ROSTER.md` (comprehensive specs)

**User Quote**: "Questa è la vera release 1.0.0" 🎉

**For detailed implementation notes** (Speed Table DB Migration, Interactive Editing, etc.), see sections below.

---

**Detailed Implementation Sections** (Speed Table Feature Development):

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

**Objective**: Transform read-only Speed Table Viewer into full interactive editor with direct CV write via POM.

**Major Features**:
- Centralized CV write delay (z21.py refactoring - DRY principle)
- Direct CV write endpoint `POST /api/speed-table/write/{consist_id}` - 28 CVs in ~2.8s
- Dual-button workflow: "Apply & Write to Decoder" vs "Export CSV Only"
- Visual feedback: blue border + asterisk on modified CVs
- Button disable logic when no modifications present
- onBlur fix: prevent unwanted interpolation on click without change
- ESC key priority for emergency stop (safety first)
- CSV export backup suffix clarifies original vs modified
- Analytics downsampling bug fixed (parameter name mismatch)

**Production Testing**: ✅ All 28 CVs written successfully in ~2.8s, verified via Hornby Bluetooth app

**User Feedback**: "perfetto, valori scritti correttamente!" ✅

---

### 2025-01-16 - 📊 **SPEED TABLE VIEWER: Phase 1 Complete** (Read-Only CV Analysis)

**Status**: ✅ **PRODUCTION READY** - Visual JMRI-style speed table with CV recommendations

**Features**:
- 28 vertical bars displaying CV67-94 values from JMRI roster XML
- Color-coded highlighting (gray/amber/red) based on CRITICAL event counts
- Speed percentage labels (10%-100%) aligned to JMRI steps
- CV adjustment recommendations with direction based on mean Δt sign
- CSV export for manual JMRI DecoderPro import
- Real-time session tracking + running session highlight

**Algorithm**: `step = floor(dcc_speed / 4.5) + 1` | Direction: `delta_t < 0` → decrease CV, `delta_t > 0` → increase CV

**User Feedback**: "Stupendo, un lavoro fantastico" 🎯

**Documentation**: `docs/SPEED_TABLE_VIEWER.md` (complete technical spec)

---

