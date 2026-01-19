# z21-Terminal

Web-based DCC locomotive controller con tracking YOLO e compensazione automatica velocità.

**Progetto**: Plastico DCC - BiancAlice
**Data creazione**: 2025-12-16
**Repository**: https://github.com/rizal72/z21-Terminal (🔒 privato)

---

## ⚠️⚠️⚠️ ALWAYS READ z21-deployment SKILL BEFORE DOING ANYTHING ⚠️⚠️⚠️

**Location**: `~/.claude/skills/z21-deployment/SKILL.md`

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
  - 7 CRITICAL rules (venv, git workflow, frontend rebuild, secrets, SSH, encoding, README)
  - Pre-deploy checklist (6 items)
- **Task Scheduler Backend**:
  - Script: `start-backend.ps1` (root directory, versionated)
  - Task name: "z21-backend" (registered automatically by PowerShell profile)
  - Features: Log rotation, PS7 encoding compatibility, detached execution
  - Called by: `z21-start`, `z21-restart` aliases via Task Scheduler
  - Log file: `C:\z21-Terminal\backend.log` (rotated to .old on each start)

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

### Function Editor (Settings UI)

**Status**: ✅ **FULLY IMPLEMENTED** (2025-01-19)

**Features**:
- **Edit labels F0-F28**: Inline editing with 20 char max length
- **Toggle lockable flag**: Direct checkbox manipulation
- **Add functions**: Filtered dropdown (F0-F28, showing only available numbers)
- **Delete functions**: Trash icon with confirmation dialog
- **Smart change detection**: Deep comparison for unsaved changes warning
- **Hot reload**: No backend restart required (roster reload only)

**UI Pattern**: Accordion-based progressive disclosure
- Collapsible locomotive cards (7 locomotives)
- Expand to show function list with inline editor
- Click-to-edit label + checkbox for lockable
- Add function: inline form with filtered dropdown + input field
- Delete function: trash icon → confirmation → automatic array sort

**Validation**:
- **Frontend**: Empty label check, max 20 chars, immediate feedback
- **Backend**: Full validation (empty, length, function number 0-28, lockable boolean)
- **Function numbers**: F0-F28 allowed, gaps permitted (F0,F1,F3,F4 valid)
- **Automatic sort**: Array always sorted by function number after add/delete

**Technical Details**:
- **Files modified**:
  - `web/src/components/SettingsModal.jsx` - Accordion UI, inline editor, add/delete logic
  - `backend/routers/config.py` - `validate_locomotive_functions()` helper, max 20 chars
- **State management**: `settings` vs `initialSettings` for deep comparison (JSON.stringify)
- **Unsaved changes**: Warning only on real changes, not just modal open/close
- **Hot reload**: POST /api/settings/update → POST /api/reload-roster → immediate effect

**User Experience**:
- Zero cognitive load: edit directly where you see the values
- No modal complexity: accordion keeps context visible
- Smart warnings: only when truly necessary (deep comparison)
- Immediate feedback: validation errors shown inline
- No restart: changes live immediately after save

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

### 2025-01-19 - 🎨 **LOCOMOTIVE FUNCTION EDITOR (Settings UI)**

**Status**: ✅ **FULLY IMPLEMENTED** - Full CRUD operations for locomotive functions F0-F28

**Implementation Phases**:

**Phase 1: Edit Labels & Lockable** (commit `0261156`)
- Accordion-based UI with progressive disclosure (7 locomotives)
- Inline editing: function labels (max 20 chars) + lockable checkboxes
- Frontend + backend validation (empty check, max length)
- Hot reload via roster reload (no backend restart)
- Settings UI info banner updated

**Phase 2: Add & Delete Functions** (commit `1a88ec0`)
- **Add function**: Filtered dropdown (F0-F28, only available numbers) + inline form
- **Delete function**: Trash icon + confirmation dialog
- **Max length**: Reduced from 50 to 20 chars (better UI fit)
- **Function gaps**: Allowed (F0,F1,F3,F4 valid - skip F2 OK)
- **Automatic sort**: Array sorted by function number after add/delete

**Phase 3: Smart Change Detection** (commit `5de4baf`)
- Deep comparison (`JSON.stringify`) for unsaved changes warning
- Warning only on real changes (not just modal open/close)
- Prevents accidental data loss from premature close

**Technical Details**:
- **Files modified**:
  - `web/src/components/SettingsModal.jsx` - Accordion UI, inline editor, state management
  - `backend/routers/config.py` - `validate_locomotive_functions()` helper
- **Validation**: Frontend (immediate feedback) + Backend (security)
- **Hot reload**: POST /api/settings/update → POST /api/reload-roster
- **State management**: `settings` vs `initialSettings` for change detection

**User Experience**:
- Zero cognitive load: edit where you see values
- No modal complexity: accordion keeps context visible
- Smart warnings: only when necessary
- Immediate feedback: inline validation errors
- No restart: changes live immediately

**Commits**: `0261156`, `1a88ec0`, `5de4baf`

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

**Config.json Reorganization**:
- Sections reordered (matches Settings UI logical flow)
- Locomotives sorted by ID (1,2,4,5,6,7,8)
- Analytics section added after tracking

**Import Script Fixes**:
- `import_single_locomotive.py`: Fixed analytics.db → data.db, added testing profile
- Deleted obsolete migration scripts

**Commits**: `3ee3122`, `42d8705`, `3f08cd4`, `87956e1`, `aab532c`, `74dfc0c`, `1709534`

---

### 2025-01-18 - ✅ **TIMING_THRESHOLDS REFACTORING**

**Status**: ✅ **COMPLETED** - Renamed `normal` → `warning`, `warning` → `critical`

**Changes**:
- Config keys: `timing_thresholds.warning = 1.0`, `timing_thresholds.critical = 1.5`
- Logic: `|Δt| < 1.0` → SYNCED, `≥ 1.0` → WARNING, `≥ 1.5` → CRITICAL
- Backend: Removed hardcoded fallbacks, fail-fast strategy
- Frontend: Settings UI updated (yellow WARNING, red CRITICAL), slider thumbs reduced
- Analytics: DRY metrics (memoized gate crossings count)

**Files modified**: 15 (config, 9 backend, 3 frontend, 2 scripts)

---

### 2025-01-17 - 🎉 **JMRI INDEPENDENCE ACHIEVED** (v1.0.0)

**Status**: ✅ **MILESTONE COMPLETE** - z21-Terminal fully autonomous for daily operations

**Achievement**: JMRI now **optional** - only needed for `import_single_locomotive.py` script when adding new locomotives

**What Changed**:
1. **Function Labels F0-F28** → `config.json` (was: JMRI roster XML)
2. **Locomotive Roster** → `config.json` (backend loads all 7 locomotives)
3. **Speed Tables CV67-94** → `data.db` (editable via web UI)
4. **CV19 Consist Management** → Automatic (Virtual/DCC Mode toggle)
5. **Consist CRUD** → Web UI (create, edit, delete)

**The Ultimate Test**: Renamed `roster/` → `roster.backup/` on PC → backend still works! 🎉

**Documentation**: See `docs/SPEED_TABLE_DB_MIGRATION.md`, `docs/JMRI_INTEGRATION.md` for complete implementation details

**Commits**: 17+ commits, key: `f64da28`, `5192495`, `5d77537`

---

### 2025-01-16 and Earlier

**Entries moved to archive**: See `docs/CHANGELOG_ARCHIVE.md` for:
- 2025-01-16: Speed Table Viewer Phase 1 (Read-Only CV Analysis)
- 2025-01-15: Speed Table Direct CV Write Phase 2
- 2025-01-13 to 2025-12-16: Complete development history

