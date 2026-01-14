# Changelog Archive (2025-12-16 → 2025-01-12)

Archived changelog entries and failed experiments documentation.

For recent changes, see main CLAUDE.md file.

---

## Changelog 2025-01-12

### 2025-01-12 - 🔌 **Z21 OFFLINE HANDLING FIX**

#### Problem
- When Z21 went offline (startup or runtime disconnect), UI showed track power ON
- Dangerous state desync: Emergency stop button disabled, power badge green
- Backend had correct state but initial_state broadcast sent stale power state

#### Solution: Dual Fix (Frontend + Backend)

**Fix 1: Frontend Immediate Fallback** (`0d12c64` - 2025-01-11 23:46)
- **Location**: `web/src/App.jsx`
- **Trigger**: Runtime Z21 disconnect (health check detects offline)
- **Action**: WebSocket `z21_status` listener forces `trackPower = false` immediately
- **Result**: Instant visual feedback (power badge OFF, emergency stop button disabled, power OFF sound)

**Fix 2: Backend Startup State** (`d7e960d` - 2025-01-12 00:09)
- **Location**: `backend/main.py`
- **Trigger**: App startup with Z21 unreachable
- **Action**:
  - Force `last_track_power_state = False` when Z21 connection fails
  - Force `consist_state[address]['power'] = False` for all consists
  - Update log: `"Z21 connection: OFFLINE (track power: OFF)"`
- **Result**: initial_state broadcast correct → page reload shows OFF state

#### Result
- ✅ UI always synchronized with Z21 connection state
- ✅ Safe behavior: track power OFF when Z21 unreachable
- ✅ Works both at startup and runtime disconnect
- **Commits**: `0d12c64`, `d7e960d`

---

### 2025-01-12 - ⚙️ **CONFIGURABLE IDLE TIMEOUT & ANALYTICS PLANNING**

#### Configurable Idle Timeout (`e563f1c`)

**Problem**: `IDLE_COOLDOWN_SECONDS` was hardcoded and used but never defined in tracking_daemon.py

**Solution**: Made idle timeout configurable via `config.json`
- **Config parameter**: `tracking.idle_timeout_seconds` (default: 10)
- **Shared usage**:
  - YOLO tracking: Switch to idle mode (1 FPS) after timeout
  - Analytics: Session end detection (no gate crossings after timeout)
- **Files modified**:
  - `config.json`: Added `idle_timeout_seconds: 10` with documentation note
  - `backend/tracking_daemon.py`: Load from config, replace all hardcoded references

**Benefits**:
- ✅ Single source of truth for idle detection
- ✅ Configurable without code changes
- ✅ Bug fixed (undefined variable eliminated)

**Commit**: `e563f1c` - "feat: make idle timeout configurable in config.json"

#### Analytics Suite Implementation (2025-01-12)

**Status**: ✅ **IMPLEMENTED**

**Key Features**:
- SQLite async logging with session validation (first Δt = valid session)
- Two views: Current Session + Cumulative History
- Consist filtering: color-coded charts (magenta C10, blue C11)
- Horizontal scroll navigation (60px/event, handles 1000+ events)
- Zombie session cleanup on close (safe timing)
- Keyboard shortcut: A key (desktop only)

**Architecture**: Async buffer (100 events, 10s flush) → Zero impact on YOLO tracking

**Complete documentation**: See [docs/ANALYTICS.md](docs/ANALYTICS.md)
- Database schema, API endpoints, UI/UX design
- Performance roadmap (scroll → sampling → LTTB → TimescaleDB)
- Failed approaches (Brush, startup cleanup) and lessons learned

**Commits**: `fa8b7cd` (connectNulls), `6edf315` (scroll), `dbc7778` (zombie cleanup)

---

### 2025-01-12 - 📊 **ANALYTICS UI IMPROVEMENTS - SESSION FILTERING & AUTO-REFRESH**

#### Session Filtering Fix (`1784f1e`)

**Problem**: Both Current and Overview views showed identical data (all 87 events)
- Stats cards not filtered by session
- Timestamp-based filtering incorrect (all events passed filter)

**Root Cause**: Used timestamp comparison instead of `session_id` matching

**Solution**:
- Added IIFE wrapper to filter events by session
- Current view: `filter(e => e.session_id === lastSession.id)`
- Overview view: all events unfiltered
- Stats cards now use `filteredEventsBySession` for accurate counts

**Result**:
- ✅ Current view shows only last session events (can start from 0 with new session)
- ✅ Overview view shows all cumulative data
- ✅ Stats cards properly differentiated between views

#### Stats Cards Refactor (`1784f1e`)

**Card 1 - Conditional**:
- Current view: Last Session Duration (mm:ss format)
- Overview view: Total Sessions count

**Card 2 - Gate Crossings**:
- Filtered by session + consist (All/C10/C11)
- Color-coded: fuchsia (C10), blue (C11), white (All)

**Card 3 - Critical Events**:
- Events with |Δt| ≥ 1.5s
- Filtered by session + consist
- Color-coded: fuchsia (C10), blue (C11), red (All)

#### Naming Change (`1784f1e`)

**Renamed "Detail" → "Current"**:
- More intuitive: "Current session" vs "All sessions history"
- Updated all UI elements, buttons, conditionals
- Arrow key navigation: ← (Current), → (Overview)

#### Auto-Refresh Implementation (`c1e5761`)

**Feature**: Auto-refresh Current view every 10s when locomotives moving

**Implementation**:
- **WebSocket monitoring**: Detects `consist_update` messages
- **Movement detection**: `speed > 0` for any locomotive
- **Conditional activation**: Only when panel open + Current view + isMoving=true
- **10-second interval**: Matches gate crossing frequency (~10s)
- **Auto-stop**: When locomotives stopped or switch to Overview

**Technical Details**:
```javascript
// WebSocket connection
useEffect(() => {
  const ws = new WebSocket(`ws://${window.location.hostname}:8000/ws`);
  ws.onmessage = (event) => {
    if (message.type === 'consist_update') {
      const isAnyLocoMoving = Object.values(message.data).some(c => c.speed > 0);
      setIsMoving(isAnyLocoMoving);
    }
  };
}, [isOpen]);

// Auto-refresh interval
useEffect(() => {
  if (!isOpen || viewMode !== 'current' || !isMoving) return;
  const interval = setInterval(() => loadCumulativeData(), 10000);
  return () => clearInterval(interval);
}, [isOpen, viewMode, isMoving]);
```

**Benefits**:
- ✅ Real-time updates during operations (Current view only)
- ✅ Zero overhead when idle (auto-stop when speed=0)
- ✅ Historical data stable (Overview view never auto-refreshes)
- ✅ Clean WebSocket lifecycle (connect/disconnect with panel)

**Testing Environment**: **PC Windows** via SSH (`riccardo@gaming-pc`)
- Deploy workflow: `z21-deploy-dev` (pull + build + restart)
- Real locomotive movement testing with Consist 10/11

**Commits**: `1784f1e` (session filtering + stats refactor), `c1e5761` (auto-refresh)

---

### 2025-01-12 - 🐛 **IDLE COOLDOWN TIMER FIX (VIRTUAL MODE)**

#### Problem
- Idle cooldown timer not working in Virtual Mode
- Locomotive stop didn't trigger 10s timer → tracking stayed at 30 FPS forever
- Expected behavior: Stop locos → 10s cooldown → switch to 1 FPS idle mode

#### Root Cause
Virtual Mode sends speed commands to individual locomotives (L7, L8), NOT consist address (11):
- Backend broadcast `consist_speed_update` only when `set_speed` called on consist address
- Virtual Mode: backend sets speed on individual locos → no broadcast to daemon
- Daemon never receives `speed=0` notification → timer never starts
- Missing `global tracking_daemon_ws` declaration caused WebSocket crash

#### Solution (3 commits)

**Commit 1**: `e8e1e74` - Debug logging to trace issue
- Added debug logs to track `consist_speed_update` broadcast
- Discovered `tracking_daemon_ws` access without `global` declaration

**Commit 2**: `8e255de` - CRITICAL fix for WebSocket crash
- Added `global tracking_daemon_ws` at start of `websocket_endpoint()`
- Fixed Python error: "cannot access local variable where it is not associated"
- Emergency fix deployed immediately (locos were running uncontrolled)

**Commit 3**: `e97c566` - Cleanup debug logging
- Removed temporary debug logs (not needed after verification)
- Verified cooldown timer working correctly

#### Test Log (Verification)
```
[STOP] STOP: both locos set to 0 (compensation reset)
[VIRT] Virtual Mode: L7=0, L8=0
[DETECT] All consists stopped - starting 10s cooldown timer...
[DETECT] Switched to Low-Power Mode (1 FPS) (after 10s cooldown)
[DETECT] YOLO tracking paused (idle @ 1 FPS, flushing RTSP buffer only)
```

#### Result
- ✅ Cooldown timer works in Virtual Mode
- ✅ Speed change notifications reach daemon correctly
- ✅ 10s delay → 1 FPS idle mode confirmed
- ✅ Virtual Mode + idle detection fully functional

**Commits**: `e8e1e74`, `8e255de`, `e97c566`

---

### 2025-01-12 - 🔄 **PAGE RELOAD TRACKING FREEZE FIX**

#### Problem (Corner Case)
User reloads page while locomotives moving (speed=70):
- Frontend reconnects, receives `initial_state` with `speed=70` ✅
- Slider shows 70 correctly ✅
- **Tracking daemon NOT notified** → stays in idle mode (1 FPS) ❌
- Video feed frozen (bbox stuck at last position) ❌
- Only new speed change (stop/restart) would unfreeze tracking ❌

#### Root Cause: Race Condition
First attempt (`506c03c`) synced daemon when client connects:
- Client connects → tries to send `consist_speed_update` to daemon
- `tracking_daemon_ws` is still `None` (daemon not connected yet)
- Daemon connects 100ms later → misses sync message
- Stays in idle mode

#### Solution
**Commit 1**: `506c03c` - Wrong timing (synced on client connect)
- Attempted sync in `websocket_endpoint()` when client connects
- Failed due to race condition (daemon connects after client)

**Commit 2**: `fd7d3bb` - Correct timing (sync on daemon connect)
- Moved sync to `websocket_tracking_endpoint()` when daemon connects
- Daemon receives current speeds immediately after WebSocket accept
- If any consist has `speed > 0` → daemon switches to active mode (30 FPS)
- Timing guaranteed: daemon is connected when we send sync

#### Test Log (Verification)
```
[WS] Tracking daemon connected
[INIT] Synced daemon on connect: consist 11 speed=88
[DETECT] Switched to Active Tracking (30 FPS)
[DETECT] YOLO tracking resumed (active @ 30 FPS)
[GATE] C11 Cross-gate: L7G2-L8G1 | dT=-0.143s
```

#### Result
- ✅ Page reload with moving locos → tracking active immediately
- ✅ No more frozen video feed on reload
- ✅ Daemon synchronized with locomotive state on connect
- ✅ Works for all scenarios: page refresh, multi-tab, browser restart

**Commits**: `506c03c` (wrong timing), `fd7d3bb` (correct fix)

---

## Changelog 2025-01-11

### 2025-01-11 - 🚀 **TENSORRT OPTIMIZATION & ONNX FALLBACK**

#### Motivation
- Reduce bbox lag from 2-3s to <0.5s via GPU acceleration
- YOLO inference on CPU too slow for real-time tracking

#### Implementation
- **Export script**: `scripts/utils/export_tensorrt.py`
  - Auto-detect standard vs OBB models
  - Export to TensorRT .engine format (FP16 half-precision)
- **Priority fallback**: `.engine` → `.onnx` → `.pt` (transparent, zero config changes)
- **Model files generated**:
  - `best_obb.pt`: 6.6 MB (PyTorch OBB - backup)
  - `best_obb.onnx`: 11.9 MB (ONNX OBB - intermediate speed)
  - `best_obb.engine`: 13.7 MB (TensorRT OBB - maximum speed, RTX 2060 optimized)

#### Critical Bug Found & Fixed
- **Problem**: ONNX/TensorRT had zero detection (bbox invisible, no console output)
- **Root cause**: ONNX/TensorRT export strips task metadata
  - YOLO assumed `task='detect'` instead of `task='obb'`
  - OBB model treated as standard detection → incompatible output format
- **Solution**: Explicitly specify `task='obb'` when loading OBB models
  ```python
  if yolo_obb:
      self.model = YOLO(model_path, task='obb')  # Fix for ONNX/TensorRT OBB
  else:
      self.model = YOLO(model_path)              # Standard detection
  ```
- **Key insight**: ONNX/TensorRT export strips model metadata → explicit task specification REQUIRED

#### Test Results (PC Windows + RTX 2060)
- ✅ **PyTorch .pt**: 30ms/frame (baseline)
- ✅ **ONNX .onnx**: 1.5-2x faster than PyTorch (intermediate speed)
- ✅ **TensorRT .engine**: 2-5x faster (6-15ms/frame) - **PRODUCTION ACTIVE**
- ✅ **Bbox lag eliminated**: <0.5s (was 2-3s)
- ✅ **Detection perfect**: All 4 locos with rotated bboxes
- ✅ **Gate timing accurate**: Real-time Δt calculation
- ✅ **Fallback compatible**: Works with both standard and OBB models

#### Files Modified
- `backend/tracking/yolo_tracker.py`: Priority fallback logic (.engine → .onnx → .pt)
- `scripts/utils/export_tensorrt.py`: Export script with auto-detection
- `.gitignore`: Added `*.engine`, `*.bak`, consolidated `*.onnx`

#### Documentation
- Complete export workflow: `docs/TENSORRT_OPTIMIZATION.md`

**Commits**: `1012ccb` (ONNX fallback), `2d17969` (task='obb' fix), `01f9fb2` (gitignore), `5880491`, `7d24a9f`, `9caf5fa`, `b306fea`

---

### 2025-01-11 - 🔧 **WEB DASHBOARD FIXES & POWERSHELL INVESTIGATION**

#### Debug Button Sync Fix
- **Problem**: Debug button showed disabled after page reload even when debug mode was active
- **Root cause**: Frontend state not synced with backend state on mount/expansion
- **Solution**:
  - Added GET `/api/debug-status` endpoint (no toggle, just status query)
  - Added `useEffect` in `App.jsx` to fetch debug status on mount
  - Added `useEffect` in `VideoFeedPanel.jsx` to sync when panel expands
- **Important lesson**: Frontend changes require **rebuild** (Vite HMR unreliable for hooks)
  - Development (Mac): Restart Vite dev server
  - Production (PC): `z21-deploy-dev` (pull + build + restart)
- **Commits**: `f9733a6`, `16aff39`, `cec53ca`, `606e238`

#### Performance Optimization
- **Removed repetitive console logs** that impacted performance during locomotive movement:
  - `consist_update received` (WebSocket loop)
  - `Updating consist/locomotive` (state updates)
  - `Address not found` messages
  - `📐 Container/Video rendered` (resize events)
- **Kept startup logs** (Wake Lock, CV Profile, WebSocket) - useful for debugging
- **Commit**: `c04f164`

#### PowerShell 7 Task Scheduler Investigation
- **Motivation**: Task Scheduler window showed garbled characters with PS7 instead of PS5.1
- **Root cause analysis**:
  - PS 5.1: Default encoding = Windows-1252 → console interprets correctly ✅
  - PS 7: Default encoding = UTF-8 → console expects codepage 850/1252 → garbled text ❌
  - PS 7 `$PSStyle` adds ANSI codes → legacy console shows raw codes instead of colors
- **Solution implemented** (retrocompatible PS 5.1 + PS 7):
  ```powershell
  [Console]::OutputEncoding = [System.Text.Encoding]::GetEncoding(850)
  if ($PSVersionTable.PSVersion.Major -ge 7) {
      $PSStyle.OutputRendering = 'PlainText'  # Disable ANSI
  }
  ```
- **Testing results**:
  - PlainText mode: Works but no colors (B/W only)
  - Ansi mode: Shows garbled ANSI codes `[97m[INIT][0m`
  - **Conclusion**: PS7 cannot display colors correctly in Task Scheduler console
- **Final configuration**:
  - **SSH**: PowerShell 7 (better command syntax, fewer retry attempts)
  - **Task Scheduler**: PowerShell 5.1 (perfect colors, no issues)
  - **start-backend.ps1**: Encoding fix present but inactive with PS5.1
- **Commits**: `18db66b` (fix), `c001b9b` (experiment), `4de7e32` (revert to PlainText)

#### Git Workflow
- **Fast-forward merge policy**: Documented in global CLAUDE.md CRITICAL REMINDERS
- **Branch sync**: `develop` merged from `main` to eliminate "53 commits behind" confusion
- **Commits**: `9dfaa64` (restore standard YOLO config), various merges

---

## Changelog 2025-01-10

### 2025-01-10 - 🔄 **YOLO OBB IMPLEMENTATION + AUTO MODEL SWITCHING + TESTING**

#### 🎯 YOLO OBB (Oriented Bounding Boxes) Implementation
- **Motivazione**: Locomotive diagonali con bbox axis-aligned causavano overlap eccessivo → NMS sopprimeva detection quando loco si passavano vicino
- **Soluzione**: YOLOv8-OBB con bbox ruotati che seguono l'orientamento delle locomotive

**Training OBB Model (v6)**:
- **Dataset**: Roboflow BiancAlice v5 - annotazioni smart select (contorni perfetti) → convertite automaticamente in OBB
- **Script**: `scripts/utils/3_train_yolo_colab.py` aggiornato per OBB
  - Download: `dataset = version.download("yolov8-obb")` invece di `"yolov8"`
  - Model: `YOLO('yolov8n-obb.pt')` invece di `'yolov8n.pt'`
- **Training**: Google Colab GPU T4, ~4 minuti
- **Results**: mAP50 = 0.917 (91.7%, leggermente inferiore a v5 93.1%)
- **Model size**: 6.6M (best_obb.pt creato)

**Config Changes**:
- **New parameter** `yolo_obb` (true/false) in `config.json` tracking section
  - `true` = Oriented Bounding Boxes (bbox ruotati)
  - `false` = Standard axis-aligned boxes
- **Initial config**: `yolo_confidence: 0.4`, `yolo_iou: 0.7`, `yolo_obb: true`

**Implementation Bugs (CRITICAL - Multi-iteration debugging)**:
1. **Array shape misunderstanding**: `box.xyxyxyxy[0]` ritorna shape `(4, 2)` non flat array
   - Fix: `points[:, 0].mean()` per center_x, `points[:, 1].mean()` per center_y
   - Commit: `3bb1a29`
2. **Detection storage indentation**: Salvataggio detection FUORI dal loop nel branch OBB
   - YOLO trovava 3 loco ma salvava solo 1
   - Fix: Spostato blocco dentro loop
   - Commit: `d4b553a`
3. **Video feed bbox length check**: `video_feed.py` assumeva `len(bbox) == 4`
   - Fix: Supporto sia 4 (standard) che 8 (OBB) valori
   - Commit: `f798a5f`
4. **JSON serialization**: numpy int64 non serializzabile → WebSocket disconnect loop
   - Fix: `bbox_json = [int(x) for x in det['bbox']]`
   - Commit: `e867cea`

**Files Modified**:
- `config.json`: +1 parameter (`yolo_obb`)
- `backend/tracking/yolo_tracker.py`: Dual mode (standard vs OBB)
- `backend/video_feed.py`: Draw bbox come polygon se 8 valori
- `backend/tracking_daemon.py`: JSON serialization fix
- `scripts/models/best.pt`: Updated a modello OBB (6.6M)
- `scripts/utils/3_train_yolo_colab.py`: Updated per OBB training

**Commits**: 11 totali (training script, config, tracker, video feed, daemon, debug, cleanup)

#### 🎨 Debug Overlay Improvements
- **Changed center markers** from large hollow circles (15px, thickness=2) to **small filled circles** (8px, filled)
- **Motivation**: User preference - pallini pieni piccoli more visually clean
- **Colors maintained**: Yellow (Gr675), Orange (D645), Green (E656), Red (E444)
- **Commit**: `c7b6393`

#### 🔄 Auto Model Switching Implementation
- **Problem**: Manual model renaming (`best.pt` ↔ `best_obb.pt`) tedious for testing
- **Solution**: Auto-select model based on `yolo_obb` config flag
  - `yolo_obb: false` → loads `best.pt` (standard axis-aligned)
  - `yolo_obb: true` → loads `best_obb.pt` (Oriented Bounding Boxes)
- **Implementation**:
  - `yolo_tracker.py`: Auto-detect model_path in `__init__` if not provided
  - `tracking_daemon.py`: Remove hardcoded MODEL_PATH
  - Log message: **ALWAYS visible** (not debug-gated) for critical info
- **Model files**:
  - `best.pt`: 6.3M (standard v5 restored from best.pt.v5.old)
  - `best_obb.pt`: 6.6M (OBB model from training)
- **Commits**: `cbc23c7`, `f952a1c`, `7ca18a7`

#### 🧪 Production Testing Results (PC Windows + GPU)
**Test 1: OBB Model** (`yolo_obb: true`, `yolo_iou: 0.85`)
- ✅ **Overlap handling**: Perfect - both locos visible when passing close
- ✅ **Bbox orientation**: Rotated polygons follow locomotive angle
- ❌ **Distant detection**: Loco 7 confidence drops <0.4 when far from camera
  - Required `yolo_confidence: 0.1` to detect distant loco 7
  - Side effect: False positives (wagons misclassified, double bbox)

**Test 2: Standard Model** (`yolo_obb: false`, `yolo_iou: 0.85`)
- ✅ **Distant detection**: Loco 7 confidence 0.4+ even when far
- ✅ **Consistent detection**: All locos detected across full track
- ⚠️ **Overlap handling**: NMS still suppresses one loco when passing close

**Test 3: Standard Model + High IoU** (`yolo_obb: false`, `yolo_iou: 0.95`)
- ✅ **Distant detection**: Perfect (all locos, all distances)
- ✅ **Overlap handling**: Both locos visible (NMS only if overlap >95%)
- ✅ **False positives**: Minimal (confidence 0.2 sufficient)

#### 🎯 Final Configuration (After Extensive Testing)
```json
{
  "tracking": {
    "yolo_confidence": 0.2,  // Was 0.4 → detect distant locomotives
    "yolo_iou": 0.95,        // Was 0.7 → reduce NMS suppression
    "yolo_obb": false        // Standard model wins
  }
}
```

**Decision: Standard Model Wins**
- **Why OBB loses**: Lower confidence on distant/small objects despite higher mAP50
  - Hypothesis: OBB learns orientation+shape (complex) → struggles on small objects
  - Training bias: More large/close locos in dataset → sacrifices small/distant
- **Why Standard wins**: Consistent detection + high IoU solves overlap
  - IoU 0.95: Allows locos to coexist unless overlap >95% (rare)
  - Confidence 0.2: Low enough for distant, high enough to avoid false positives
- **Trade-off accepted**: Occasional double bbox on extreme overlap (rare) vs losing distant locos (frequent)

**Commits**: `6b233ec` (config optimization), merged to main `4579182`

#### 📊 Key Insights
- **mAP50 ≠ Production Performance**: OBB higher mAP but worse on edge cases
- **Dataset matters**: Training bias toward large objects hurts small object detection
- **IoU sweet spot**: 0.95 balances overlap handling vs false positives
- **Confidence threshold**: Lower is better for recall if false positive rate acceptable

#### 🚀 PowerShell Deployment Aliases Refactor
- **Problem**: `z21-deploy` and `z21-deploy-dev` had duplicated code
- **Solution**: Extracted common logic to `Deploy-Z21Terminal` helper function
- **Implementation**: PowerShell parametrized function (DRY principle)
  - `function Deploy-Z21Terminal { param([string]$Branch) ... }`
  - `z21-deploy` calls with `"main"`
  - `z21-deploy-dev` calls with `"develop"`
- **Benefits**:
  - Single source of truth for deploy logic
  - Consistent behavior across both aliases
  - `config.local.json` preserved (gitignored)
- **Workflow**:
  - Development: `z21-deploy-dev` (deploy from develop)
  - Production: `z21-deploy` (deploy from main)
- **Files**: `~\Documents\PowerShell\Microsoft.PowerShell_profile.ps1` (PC)

#### 🔧 PowerShell 7 Migration (PC Windows)
- **Motivazione**: PowerShell 5.1 obsoleto, PS7 moderno e cross-platform
- **Migrazione**: SSH default shell PS5.1 → PS7.5.4
- **Registry**: `HKLM:\SOFTWARE\OpenSSH\DefaultShell` → pwsh.exe
- **posh-git**: Installato per PS7 (git autocompletion)
- **Profile structure**:
  - Master: `PowerShell\Microsoft.PowerShell_profile.ps1` (PS7)
  - Symlink: `WindowsPowerShell\Microsoft.PowerShell_profile.ps1` → PS7 master
  - Modifiche future: SOLO sul master PS7
- **⚠️ CRITICO**: SSH su PC usa SEMPRE PowerShell 7 da ora in poi

---

## Changelog 2025-01-09

### 2025-01-09 - 🔄 **LOG ROTATION - AUTOMATIC BACKEND.LOG CLEANUP**
- **🔄 Log Rotation Implementation** - Keep current log clean and fast
  - **Problema**: `backend.log` cresceva indefinitamente (100+ MB dopo settimane)
    - File giganti rallentano `z21-log` e editor
    - Nessun cleanup automatico implementato
  - **Soluzione**: Rotate al restart
    - `start-backend.ps1` rinomina `backend.log` → `backend.log.old` prima di avviare backend
    - Log corrente sempre piccolo e veloce da leggere
    - Ultimi 2 restart disponibili per debugging (current + old)
  - **Workflow**:
    ```powershell
    z21-restart  # Rotate automatico: backend.log → backend.log.old
    z21-log      # Sempre veloce (file piccolo)
    ```
  - **Benefici**:
    - ✅ Log corrente sempre pulito
    - ✅ Storico disponibile (.old file)
    - ✅ `.old` già gitignored (no commit accidentali)
    - ✅ Zero maintenance manuale
  - **File modificato**: `start-backend.ps1`
  - **Commit**: `fca1c47` - feat: add log rotation to start-backend.ps1
  - **Merged to main**: `69146d1`

### 2025-01-09 - 🔌 **Z21 CONNECTION STATUS - EXPLICIT STARTUP LOGGING**
- **🔌 Z21 Status Visibility** - Clear ONLINE/OFFLINE feedback at startup
  - **Problema**: Z21 offline all'avvio era silenzioso (nessun log)
    - UDP è connectionless → socket creato ma nessun error fino al primo comando
    - Badge rosso mostrato ma nessun messaggio nel log
    - Log `[INIT] Z21 connection: ONLINE` era sotto `debug_enabled` flag
  - **Soluzione**: Log esplicito per entrambi gli stati
    - `[OK] Z21 connection: ONLINE` (verde, sempre visibile)
    - `[FAIL] Z21 connection: OFFLINE` (rosso, sempre visibile)
    - Rimosso debug flag da ONLINE log
    - Aggiunto `else:` branch per offline detection
  - **Comportamento**:
    - **All'avvio**: Log immediato dello stato Z21 (online o offline)
    - **Durante runtime**: Health check ogni 5s logga solo su **cambio stato**
  - **Benefici**:
    - ✅ Feedback chiaro all'avvio (non più silenzioso quando offline)
    - ✅ Log consistenti (online e offline sempre visibili)
    - ✅ Debug più facile (stato Z21 evidente nei log)
  - **Edge case testato**: Z21 offline + Tapo camera in IR night mode
    - RTSP reconnect loop visibile (~2s delay tra tentativi)
    - Loop attivo SOLO se client WebSocket connesso
    - Client disconnesso → tracking daemon si ferma automaticamente
  - **File modificato**: `backend/main.py`
  - **Commit**: `73c0c23` - feat: add explicit Z21 connection status logging at startup
  - **Merged to main**: `e96f35f`

---

## Changelog 2025-01-08

### 2025-01-08 - 🎨 **LOGGING SYSTEM REFACTOR - CENTRALIZED PREFIX→COLOR MAPPING**
- **🎨 Complete Logging System Redesign** - From low-level constants to centralized design pattern
  - **Problema precedente**:
    - Ogni file importava N costanti colore individuali (`CYAN, YELLOW, RED, RESET, ...`)
    - Cambiare colore di un prefix richiedeva modificare 5+ files
    - Inconsistenze possibili (colori sbagliati per prefix)
    - Import verbosi e poco manutenibili
  - **Nuovo design**:
    - `backend/log_colors.py` (NEW) - Single source of truth con `PREFIXES = {[PREFIX]: COLOR}` mapping
    - `log(prefix, message)` helper function - Import centralizzato
    - Modificare colore = 1 linea nel dict, propagazione automatica ovunque
  - **Refactoring completato**: 9 backend files
    - `backend/config_loader.py`
    - `backend/main.py`
    - `backend/tracking/rtsp_handler.py`
    - `backend/tracking/yolo_tracker.py`
    - `backend/tracking_daemon.py`
    - `backend/tracking_manager.py`
    - `backend/video_feed.py`
    - `backend/z21_manager.py`
    - Pattern: `from log_colors import CYAN, YELLOW, ...` → `from log_colors import log`
  - **Nuovi log prefixes**:
    - `[ERROR]` - Errori critici (file not found, connection failed, JSON invalid) - Red bright (91m)
    - `[STOP]` - Emergency stop commands (distinto da compensation) - Red bright (91m)
  - **Prefixes rinominati**:
    - `[TRACK]` → `[DETECT]` - YOLO detection/tracking (più chiaro, evita ambiguità con "binario ferroviario")
  - **Colori aggiornati**:
    - `[INIT]`: Cyan dim → **White bright (97m)** - Alta visibilità per startup messages
    - `[SHUT]`: Cyan dim → **Purple (35m)** - Colore distintivo per shutdown
    - `[WS]`: Cyan dim → **Blue (34m)** - Network-related operations
    - `[WARN]`: Cyan dim → **Yellow bright (93m)** - Standard warning color
  - **Auto-compensation toggle fix**:
    - Aggiunta chiamata `_save_persisted_state()` per persistere setting su config.json
    - Log sempre visibile (non più sotto debug_enabled)
    - Prefix `[COMP]` invece di `[INIT]` per consistency
    - Messaggio: `Auto-compensation enabled/disabled for consist X (saved to config.json)`
  - **Benefici**:
    - ✅ Manutenibilità: cambia 1 file invece di 5+
    - ✅ Consistenza: impossibile usare colori sbagliati
    - ✅ Scalabilità: aggiungere prefix = 1 riga
    - ✅ Import semplificati: `from log_colors import log`
  - **Commit**: `99d46cf` - refactor: centralized logging system with PREFIX→COLOR mapping
  - **Merged to main**: `040458e`

### 2025-01-09 - 🧹 **UNICODE SYMBOLS CLEANUP - ASCII LOGGING**
- **🧹 Remove Unicode Symbols from Logs** - Added [OK] and [FAIL] prefixes
  - **Problema**:
    - Simboli unicode (✓✗✅❌⚠️) non visualizzati correttamente su Windows terminals
    - Output illeggibile: `Ô£ô Video stream opened` invece di checkmark
    - Encoding issues su PowerShell 5.1 (default Windows)
  - **Soluzione**:
    - Aggiunti `[OK]` (green bright) e `[FAIL]` (red bright) a PREFIXES dict
    - Sostituiti tutti i simboli unicode con `log('[OK]', ...)` e `log('[FAIL]', ...)`
    - Rimossi `⚠️` da return messages (plain text per frontend notifications)
  - **Files modificati** (5):
    - `backend/log_colors.py` - Added [OK] and [FAIL] to PREFIXES
    - `backend/video_feed.py` - 4 replacements (✓ → [OK], ✗ → [FAIL])
    - `backend/tracking_manager.py` - 2 replacements (✓ → [OK], ✅ → [OK])
    - `backend/main.py` - 3 replacements (✅/❌ → [OK]/[FAIL], ✗ → [FAIL])
    - `backend/z21_manager.py` - 4 replacements (✗ → [FAIL], ⚠️ removed)
  - **Sostituzioni totali**:
    - ✓ → `log('[OK]', ...)` (4 occorrenze)
    - ✗ → `log('[FAIL]', ...)` (4 occorrenze)
    - ✅/❌ → `log('[OK]'/'[FAIL]', ...)` (2 occorrenze)
    - ⚠️ rimosso da return messages (3 occorrenze)
  - **Benefici**:
    - ✅ Logging consistente ASCII-only (no encoding issues)
    - ✅ Readable su tutti i terminali (Windows, macOS, Linux)
    - ✅ Colori centralizzati via PREFIXES dict
    - ✅ Professional output su Windows PC production deployment
  - **Commit**: `4161bee` - refactor: remove unicode symbols from logs, use [OK] and [FAIL] prefixes
  - **Merged to main**: `493323c`
- **🔄 Unicode Symbols Cleanup** - Full ASCII conversion (Δt → dT, → → ->)
  - **Problema**: Simboli unicode visualizzati incorrettamente su Windows terminals
    - `Δt` → `╬öt` nei log, `??` in OpenCV video feed
    - `→` → `ÔåÆ` nei log (reset accumulated, CV profile toggle)
  - **Soluzione**: Sostituito tutti i simboli unicode con ASCII equivalenti
    - `Δt` → `dT` usando sed (62 occorrenze in 5 file)
    - `→` → `->` usando sed (7 occorrenze in z21_manager.py)
  - **Files modificati**:
    - Delta-t: main.py, yolo_tracker.py, tracking_daemon.py, video_feed.py, z21_manager.py
    - Arrow: z21_manager.py (log messages + comments)
  - **OpenCV issue**: HERSHEY_SIMPLEX font non supporta caratteri unicode → `dT` anche nel video feed panel
  - **Risultato**: ASCII consistente ovunque (logs + video overlay + code comments)
  - **Commits**:
    - `8bb59e1` - refactor: replace Δt unicode symbol with dT (ASCII)
    - `bebb2e2` - feat: use Δt unicode symbol in video feed panel (tentativo fallito)
    - `ec836dc` - fix: revert Δt to dT in video feed panel (OpenCV font encoding issue)
    - `6cfc99d` - fix: replace → arrow symbol with -> (ASCII) in logs
  - **Merged to main**: `9fcdd18`, `7b37695`, `979fd45`, `c87af0d`

### 2025-01-09 - 🔧 **WINDOWS TASK SCHEDULER - TRULY DETACHED BACKEND**
- **🔧 Task Scheduler Fix** - Backend ora sopravvive veramente a SSH close
  - **Problema**: `Start-Process -WindowStyle Hidden` NON è detached
    - Processo legato alla sessione SSH
    - Chiudi SSH → processo termina
    - Riapri SSH → backend morto, serviva z21-start di nuovo
  - **Soluzione**: Windows Task Scheduler
    - Task "z21-backend" creato automaticamente al primo `z21-start`
    - Esegue `C:\z21-Terminal\start-backend.ps1` (nuovo file committato)
    - Processo veramente detached dal sistema operativo
    - Sopravvive a: SSH close, logout, persino reboot (se configurato)
  - **Files aggiunti**:
    - `start-backend.ps1` (NEW) - Script startup per Task Scheduler
      - Location: Project root (tracked by git)
      - Eseguito da Task Scheduler con utente corrente
      - Log output: `C:\z21-Terminal\backend.log` via Tee-Object
  - **PowerShell aliases aggiornati** (su PC Windows):
    - `z21-start`: Crea task (se non esiste) + Start-ScheduledTask
    - `z21-stop`: Stop-ScheduledTask + cleanup Python processes
    - `z21-status`: Controlla Task Scheduler state invece di solo processi Python
    - `z21-restart`: Stop + Start via Task Scheduler
  - **Workflow:**
    ```powershell
    z21-start   # Prima volta: crea task automaticamente, poi lo avvia
    # Chiudi SSH completamente
    # Riapri SSH
    z21-status  # Backend ancora ATTIVO! ✅
    ```
  - **Benefici**:
    - ✅ Backend veramente persistente (not session-bound)
    - ✅ Zero setup manuale (task auto-creato al primo z21-start)
    - ✅ Gestibile via Task Scheduler GUI (taskschd.msc)
    - ✅ Può essere configurato per auto-start on reboot (opzionale)
  - **Documentazione aggiornata**:
    - `docs/GPU_DEPLOYMENT.md` - Funzioni PowerShell + caratteristiche chiave
    - Note: docs/ è gitignored (documentazione locale)
  - **Commit**: Script start-backend.ps1 committato (condiviso per Windows users)

### 2025-01-09 - 📖 **README UPDATE - CV PROFILES DOCUMENTATION**
- **📖 CV Profiles Documentation** - Added feature description to README
  - **Sezioni aggiornate**:
    - **Core Features**: Bullet point sintetico "CV Profiles: One-click TEST/NORMAL toggle"
    - **CV Operations checklist**: Dettagli tecnici (hotkey T, CV3/CV4, badge, config.json)
    - **Speed Matching notes**: Workflow pratico + warning importante
  - **Contenuto aggiunto**:
    - Hotkey T per toggle TEST/NORMAL (~1.2s)
    - Badge indicator (Flask = TEST, Check = NORMAL)
    - TEST mode: CV3≈0, CV4≈0 (risposta istantanea)
    - NORMAL mode: CV3/CV4 ripristinati (accelerazione realistica)
    - ⚠️ Warning: Tornare a NORMAL prima di chiudere/deployare
  - **Motivo**: Feature implementata 2025-01-08 ma non documentata in README
  - **File modificato**: `README.md`
  - **Commit**: `629cd12` - docs: add CV Profiles feature to README
  - **Merged to main**: `7104b51`

### 2025-01-09 - 🔔 **NOTIFICATION IMPROVEMENTS - ACCUMULATED CORRECTIONS**
- **🔔 Speed Correction Notifications** - Distinguish new vs maintained corrections
  - **Problema**: Notifica mostrava "Speed +2%" anche quando correzione era già attiva (WARNING zone)
  - **Comportamento precedente**:
    - CRITICAL +2 → notifica "Speed +2%" ✅
    - WARNING (ancora +2) → notifica "Speed +2%" ❌ (confuso, sembrava nuova modifica)
  - **Soluzione**: Messaggio diverso se correzione non cambia
    - **Nuova/cambiata**: "Loco 1: Speed +2%" (valore appena applicato o incrementato)
    - **Mantenuta**: "Loco 1: still at +2%" (stesso valore, WARNING zone)
    - **Sincronizzata**: "Consist 10: SYNCED" (correzione azzerata)
  - **Benefici**:
    - ✅ Chiaro quando correzione aumenta (+2 → +4 → +6)
    - ✅ Chiaro quando correzione è mantenuta (still at)
    - ✅ Mostra sempre valore accumulato totale
    - ✅ Evita confusione su correzioni persistenti
  - **File modificato**: `web/src/App.jsx` (notification logic)
  - **Commit**: `097c129` - feat: improve notification message for maintained speed corrections
  - **Merged to main**: `3548a70`

### 2025-01-09 - ⚡ **UVICORN AUTO-RELOAD - DEV MODE ONLY**
- **⚡ Development Workflow Optimization** - Auto-reload per sviluppo locale
  - **Problema**:
    - Flag `--reload` su `z21-start` (background) causa interruzioni log file
    - `--reload` + `Tee-Object` conflitto: log si ferma dopo poche righe
    - Uvicorn watchdog chiude file descriptor ad ogni restart
  - **Soluzione finale**: `--reload` SOLO su `z21-backend` (interactive mode)
    - `z21-backend`: Interactive mode con `--reload` ✅ (dev locale su PC)
    - `z21-start`: Background production SENZA `--reload` ✅ (log stabili)
  - **Production workflow** (backend-only changes via SSH):
    ```powershell
    git pull
    z21-restart  # ✅ Riavvio manuale veloce (~2s)
    ```
  - **Dev workflow** (locale su PC):
    ```powershell
    z21-backend  # ✅ Auto-reload attivo, vedi log real-time
    ```
  - **Quando serve z21-deploy**:
    - ✅ Modifiche frontend (rebuild Vite necessario)
    - ✅ Modifiche dipendenze (requirements*.txt)
    - ✅ Config critici (struttura config.json)
  - **Benefici**:
    - ✅ Log stabili su production (Tee-Object funziona correttamente)
    - ✅ Auto-reload disponibile per dev locale (z21-backend)
    - ✅ Workflow production: `git pull + z21-restart` (2 comandi, veloce)
  - **Documentazione aggiornata**:
    - `docs/GPU_DEPLOYMENT.md` - Sezione "Update Workflow" corretta
    - PowerShell alias: `z21-backend` con `--reload`, `z21-start` senza
  - **Note**: Documentazione solo locale (gitignored), commit non necessario

### 2025-01-08 - 📦 **REQUIREMENTS STRUCTURE REFACTOR - CPU/GPU SEPARATION**
- **📦 Requirements Files Refactor** - Separate CPU (Mac) and GPU (PC) dependencies
  - **Problema**:
    - Mac usa Python di sistema (Homebrew) → vulnerabile a `brew upgrade python` (break dependencies)
    - PC usa venv ma PyTorch GPU non tracciato (comando manuale da docs/GPU_DEPLOYMENT.md)
    - Nessuna protezione da upgrade, no reproducibility
  - **Soluzione**:
    - `requirements-cpu.txt` (NEW) - PyTorch CPU-only per macOS development (torch==2.2.2, torchvision==0.17.2)
    - `requirements-gpu.txt` (NEW) - PyTorch GPU + CUDA 11.8 per Windows PC production (con `--index-url`)
    - `INSTALL.md` (NEW) - Guida completa installazione: venv/conda, Mac/PC, troubleshooting
    - `README.md` - Link a INSTALL.md nella sezione Installation
    - `backend/requirements.txt` - FastAPI dependencies (unchanged)
    - `scripts/requirements.txt` - ultralytics + opencv-python (unchanged)
  - **docs/GPU_DEPLOYMENT.md** (local, gitignored) - Updated step 4 per usare requirements-gpu.txt
  - **Benefici**:
    - ✅ Versioni pinnate (reproducible builds)
    - ✅ Zero comandi manuali (no più `pip install torch --index-url ...`)
    - ✅ Separazione chiara CPU vs GPU
    - ✅ Protezione da Homebrew upgrades (con venv)
  - **Raccomandazione Mac**: Creare venv per isolare da system Python
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r backend/requirements.txt -r scripts/requirements.txt -r requirements-cpu.txt
    ```
  - **Commit**: `18bdb5d` - feat: separate CPU and GPU requirements files

### 2025-01-08 - 🔌 **PHASE 9: MOTOR LOAD MONITORING - TELEMETRY WIDGETS**
- **✅ Phase 9 Part 1 - Z21 Track-Level Telemetry** - Backend telemetry parsing
  - **z21.py extension**: `get_status()` now parses bytes 0-11 (telemetry data)
    - MainCurrent (mA), ProgCurrent (mA), FilteredCurrent (mA)
    - Temperature (°C), SupplyVoltage (V), VCCVoltage (V)
    - Little-endian uint16 parsing with proper unit conversion
  - **Backend API**: `/api/z21/telemetry` endpoint
    - Returns telemetry + quality checks + warnings array
    - Voltage thresholds: 14.0-18.0V normal range
    - Current thresholds: >2000mA high (short circuit risk)
    - Temperature thresholds: >50°C elevated, >60°C critical
  - **Test script**: `scripts/utils/test_z21_telemetry.py`
    - Validates telemetry parsing (211mA, 17.80V, 2.9°C measured)
    - Quality checks with descriptive output
  - **Commit**: `de565c6` - feat: Phase 9 Part 1 - Z21 track-level telemetry parsing
- **✅ Phase 9 Part 2 - Frontend Telemetry Popovers** - Hover/click UX widgets
  - **TrackTelemetryPopover.jsx** (⚡ badge) - Track power monitoring
    - Displays: MainCurrent, SupplyVoltage, FilteredCurrent, power state, short circuit
    - Warning banners for voltage/current issues (amber alert boxes)
    - Auto-refresh every 2s via polling
  - **Z21HealthPopover.jsx** (🖥️ badge) - Z21 system health
    - Displays: Temperature, VCC Voltage, hardware/firmware info, serial
    - Temperature warnings (elevated >50°C, critical >60°C)
    - Static system info (Model: Z21 White, Hardware: 0x0203, Firmware: 1.67, Serial: 111466)
  - **App.jsx enhancements**:
    - Background telemetry polling every 5s (warning detection)
    - Status badges wrapped in boxes (`bg-control-dark`, `rounded`, `border`)
    - **Desktop UX** (≥768px): Hover → instant popover (no animation, no backdrop)
    - **Mobile UX** (<768px): Tap → toggle popover (backdrop dismiss, slide-in animation)
    - Warning rings: `ring-2 ring-amber-500/50` when issues detected
    - Disabled state when Z21 offline
  - **Commit**: `99cb9e1` - feat: Phase 9 Part 2 - frontend telemetry popovers with hover/click UX
- **📚 Documentation Updates**:
  - `docs/MOTOR_LOAD_MONITORING.md`:
    - Status updated: ✅ PHASE 1-2 COMPLETED (2025-01-08)
    - Added Part 2 section with component architecture, UX design, API integration
    - Renamed RailCom section to Part 3 (future research)
  - `CLAUDE.md`: This changelog entry
- **🎯 Result**: Real-time telemetry monitoring con dual UX (hover on desktop, tap on mobile)
  - Professional UI with warning indicators
  - Graceful degradation (disabled when offline)
  - Production-ready Phase 9 implementation ✅

### 2025-01-08 - 🔬 **PHASE 9 PART 3 RESEARCH + LOG IMPROVEMENTS**
- **🔬 RailCom Plus Research (Phase 9 Part 3)** - Z21 White compatibility test
  - **Obiettivo**: Verificare se Z21 White (HW 0x0203) supporta RailCom Plus via LAN protocol
  - **Script creati**:
    - `scripts/utils/enable_railcom_plus.py` (227 righe) - Enable RailCom on ESU decoders
      - CV29 bit 3 (RailCom enable) + CV106=1 (RailCom Plus enable)
      - Operations mode programming con 3x retry (no ACK)
      - Warning per decoder non-ESU (Hornby TXS, Zimo MX630)
    - `scripts/utils/test_railcom_listener.py` (197 righe) - Monitor 0x0088 packets
      - Subscribe to Z21 broadcasts (flag 0x00000008 = RailCom bit 3)
      - Listen for LAN_RAILCOM_DATACHANGED (0x0088) packets
      - 60s monitoring window con statistics
  - **Test eseguito**: Loco 8 (E444 056 - ESU LokPilot 5)
    - CV29 = 30 (bit 3 already set), CV106 = 1 (written 3x)
    - Locomotive in movimento per 60s
    - **Risultato**: Zero 0x0088 packets received
  - **❌ Conclusione**: Z21 White does NOT expose RailCom Plus via LAN protocol
    - RailCom funziona internamente (POM read/write confermato)
    - Per-locomotive telemetry richiede Z21 Black o Z21 Pro
    - **Phase 9 Part 3 marked as NOT FEASIBLE** on current hardware
  - **Documentazione**: `docs/MOTOR_LOAD_MONITORING.md` updated with research findings
- **🐛 Temperature Bug Fix** - Z21 telemetry parsing
  - **Problema**: Dashboard mostrava 2.9°C invece di 29°C
  - **Root cause**: Incorrect `/10.0` division in `scripts/z21.py:171`
  - **Fix**: `temperature / 10.0` → `float(temperature)`
  - **Reason**: Z21 sends temperature as integer °C, not °C × 10 (unlike voltage in mV)
  - **Verifica**: App Z21 confermava 29°C
- **📱 iPhone WiFi Issue** - Z21 app connectivity
  - **Problema**: iPhone non connetteva a Z21 app, tablet OK
  - **Troubleshooting**: IP privato, tracciamento, subnet mask, DNS
  - **Soluzione**: "Forget network + reboot iPhone"
  - **Root cause**: Corrupted DHCP lease/cache (IP changed .7 → .32)
- **🖥️ PowerShell 7 Installation** - UTF-8 support attempt
  - **Installato**: PowerShell 7.5.4 via winget su PC Windows
  - **Obiettivo**: Fix emoji display in backend.log file
  - **Risultato**: Emoji scritte correttamente (UTF-8) ma font terminale non le visualizza
  - **Soluzione finale**: Lasciato z21-backend per emoji live, z21-start per production
  - **Note**: pwsh resta installato (~100MB), non interferisce con PowerShell 5.1
- **⚙️ z21-log Alias** - Quick log viewing
  - **Comando**: `Get-Content C:\z21-Terminal\backend.log -Wait -Tail 50`
  - **Aggiunto a**: PowerShell profile (`Microsoft.PowerShell_profile.ps1`)
  - **Usage**: `z21-log` per vedere log real-time (Ctrl+C to exit)
- **🔇 Telemetry HTTP Logs Filter** - Spam reduction
  - **Problema**: Log invaso da `GET /api/z21/telemetry` ogni 5s
  - **Soluzione**: Logging filter in `backend/main.py` lifespan startup
  - **Implementazione**:
    - `TelemetryFilter` class filters `/api/z21/telemetry` messages
    - Applied to `uvicorn.access` logger
    - Moved to `lifespan()` instead of `__main__` (uvicorn reload compatibility)
  - **Risultato**: Log pulito, mantiene WebSocket/GET/POST importanti
  - **Commits**:
    - `ac7702a` - feat: filter telemetry HTTP logs to reduce spam
    - `5fd100f` - fix: move telemetry filter to lifespan startup
- **📁 Files Modified**:
  - `scripts/z21.py`: Temperature parsing fix
  - `scripts/utils/enable_railcom_plus.py` (NEW)
  - `scripts/utils/test_railcom_listener.py` (NEW)
  - `backend/main.py`: Telemetry filter in lifespan
  - `C:\Users\Riccardo\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`: z21-log alias

### 2025-01-08 - 🐍 **VENV SETUP MAC - CPU DEPENDENCIES**
- **🐍 Virtual Environment Setup (macOS)** - Isolamento da system Python
  - **Setup eseguito**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r backend/requirements.txt -r scripts/requirements.txt -r requirements-cpu.txt
    ```
  - **Dependencies installate**:
    - FastAPI 0.115.5 + Uvicorn 0.32.1 + WebSocket 13.1
    - PyTorch 2.2.2 + torchvision 0.17.2 (CPU-only)
    - NumPy 1.26.4 (downgrade da 2.2.6 per compatibilità PyTorch)
    - OpenCV 4.12.0.88 + Ultralytics 8.3.249 (YOLO)
  - **NumPy compatibility fix**:
    - PyTorch 2.2.2 compilato con NumPy 1.x
    - opencv-python 4.12 richiede numpy>=2 (ma funziona con 1.26.4)
    - Pip warning su dependency resolver = **false positive**
    - Verifica: `import torch; import cv2; import numpy as np` → ✅ OK
  - **requirements-cpu.txt updated**: Aggiunto `numpy<2` constraint
  - **INSTALL.md updated**: Aggiunta sezione troubleshooting per NumPy warning
  - **Benefici**:
    - ✅ Protezione da `brew upgrade python` (isolation)
    - ✅ Dependencies pinnate per reproducibility
    - ✅ Alias bash attivano automaticamente venv se esiste
  - **Full stack test**: PyTorch + OpenCV + Ultralytics → ✅ YOLO ready

### 2025-01-08 - 🖥️ **WINDOWS PC ALIASES - STATUS CHECK & LOGGING FIX**
- **🖥️ z21-status Alias (Windows PC)** - Quick backend status check
  - **Funzione aggiunta a PowerShell profile**: `C:\Users\Riccardo\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`
  - **Check method**: Verifica porta 8000 in ascolto (TCP listen state)
  - **Output**:
    - `[OK] Backend ATTIVO (porta 8000 in ascolto)` - Backend running
    - `[X] Backend NON ATTIVO` - Backend stopped
  - **Motivo**: API localhost:8000 non risponde correttamente (timeout/CORS), più affidabile check porta TCP
- **🐛 Backend Logging Fix** - Unbuffered Python output
  - **Problema**: Backend.log non scriveva in tempo reale (buffering di `Tee-Object`)
  - **Soluzione**: Aggiunto flag `-u` (unbuffered) a Python in `z21-start`
  - **Before**: `python.exe -m uvicorn ...`
  - **After**: `python.exe -u -m uvicorn ...`
  - **Risultato**: Log scritti immediatamente su file, no più buffering delays
  - **Note**: Solo `z21-start` (background mode), NON `z21-backend` (interactive mode)
- **♻️ z21-reload → z21-restart** - Alias renamed for clarity
  - **Old**: `z21-reload` (ambiguo - reload vs restart?)
  - **New**: `z21-restart` (chiaro - stop + start backend)
  - **Usage**: `z21-restart` per riavviare backend in background dopo updates
- **📁 File Modified**:
  - `C:\Users\Riccardo\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1` (via SSH + scp workflow)

### 2025-01-08 - 🧹 **CLEANUP: CONSIST_STATE.JSON REMOVAL**
- **🧹 consist_state.json Deprecated** - Migration to config.json completed
  - **Files deleted**:
    - `backend/consist_state.json` (gitignored runtime file)
    - `backend/consist_state.json.example` (tracked template)
  - **Code cleanup**:
    - Removed `CONSIST_STATE_FILE` constant from `z21_manager.py`
    - Removed fallback migration code in `_load_persisted_state()`
  - **Reason**: Virtual Mode state (virtual_mode, auto_compensation_enabled) now fully managed via `config.json`
  - **Benefit**: Single source of truth, tracked by git, no manual file copying needed
  - **Documentation updated**: `docs/GPU_DEPLOYMENT.md` - removed all consist_state.json references
  - **Commit**: `463a9d8` - refactor: remove consist_state.json (migrated to config.json)
- **⚠️ Virtual Mode Warning** - Added safety check for misconfiguration
  - **Warning added**: `_load_persisted_state()` checks if consist has `virtual_mode=False`
  - **Message displayed**:
    ```
    ⚠️  WARNING: Consist {id} has virtual_mode=False
        → Speed commands will be sent to consist address {id} (DCC mode)
        → Locomotives may not respond unless CV19={id} is programmed
        → Set 'virtual_mode: true' in config.json consists.{id} for proper operation
    ```
  - **Benefit**: Prevents silent failures when locomotives don't respond (wrong address)
  - **Note**: Current config.json già ha `virtual_mode: true` per consist 10 e 11 ✅
  - **Commit**: `fdbe2db` - feat: add warning for consist virtual_mode misconfiguration

### 2025-01-08 - 🐛 **SHIFT+KEY BUG FIX - DUAL CONTROLLER RESPONSE**
- **🐛 SHIFT+key only triggered one controller** - Critical keyboard shortcut regression
  - **Problema rilevato**:
    - SHIFT+7 dovrebbe cambiare velocità su ENTRAMBI i controller (Consist 10 + Consist 11)
    - In realtà solo Controller #1 rispondeva (Consist 10)
    - Controller #2 (Consist 11) non rispondeva mai
    - Console logs mostravano Controller #1 trigger 3x volte invece di 1x
  - **Root cause identificata**:
    - Handler functions (`handleSpeedChange`, `handleDirectionChange`, `handleFunctionToggle`, `handleToggleVirtualMode`, `handleToggleAutoCompensation`, `showNotification`) erano **NON wrappati in useCallback**
    - Ad ogni render, React creava NUOVE istanze delle funzioni
    - ConsistController's `useEffect` dipendeva da questi handlers → re-run ad ogni cambio
    - Multiple event listeners venivano aggiunti senza cleanup → listener duplicati
    - Controller #1 processava evento, triggering re-render → nuovo listener aggiunto → stesso evento processato 3x
    - Controller #2's listener veniva corrotto dalle re-render continue
  - **Soluzione applicata**:
    - ✅ **web/src/App.jsx**: Wrapped all handlers in `useCallback` with proper dependencies
    - ✅ **web/src/hooks/useNotification.jsx**: Wrapped `showNotification` in `useCallback`
    - ✅ **web/src/components/ConsistController.jsx**: Removed debug console.log statements
  - **Verifica funzionamento**:
    - SHIFT+7 → Both controllers respond: "Controller #1 setting speed 70%" + "Controller #2 setting speed 70%"
    - SHIFT+backslash → Both controllers stop: "Controller #1 setting speed 0%" + "Controller #2 setting speed 0%"
    - Due notifiche appaiono correttamente (una per controller)
  - **Benefici**:
    - ✅ SHIFT shortcuts now work correctly on BOTH controllers simultaneously
    - ✅ No more duplicate event listeners
    - ✅ Cleaner re-render behavior (handlers stable across renders)
    - ✅ Consistent behavior with design intent
  - **Commit**: `8099b00` - fix: SHIFT+key now triggers both controllers correctly

### 2025-01-08 - 🐛 **TRACKING DAEMON RTSP RECONNECT FIX**
- **🐛 Tracking stops after long idle periods** - RTSP timeout breaks YOLO inference
  - **Problema rilevato**:
    - User apre video feed, lascia aperto per minuti/ore senza far partire locomotive
    - Quando locomotive partono, YOLO tracking non funziona più
    - Nessun bounding box visualizzato, nessun speed sync
    - Debug toggle on/off non risolve, tracking morto permanentemente
    - Video feed continua a funzionare correttamente (video visibile)
  - **Root cause identificata**:
    - **RTSP stream timeout** dopo periodo di idle prolungato (no activity)
    - `tracking_daemon.py` loop: `cap.read()` fallisce → log "Lost video connection" → `sleep(1)` → retry con **stesso cap object morto**
    - Loop infinito provando a leggere da VideoCapture object disconnesso
    - **video_feed.py** HA logica di reconnect (rilascia cap + riconnette) → per questo video funziona
    - **tracking_daemon.py** NON aveva logica di reconnect → tracking si bloccava
  - **Soluzione applicata**:
    - ✅ Import `reconnect_rtsp_stream()` da `tracking.rtsp_handler` (funzione già esistente)
    - ✅ Quando `cap.read()` fallisce: close vecchio cap + crea nuovo VideoCapture con `buffer=1`
    - ✅ Retry ogni 2s finché RTSP non risponde (consistent con video_feed.py)
    - ✅ Log state changes: "Lost video connection, reconnecting..." → "Video connection restored"
  - **Comportamento dopo fix**:
    - Tracking daemon sopravvive a RTSP timeout durante long idle periods
    - YOLO inference riprende automaticamente quando stream reconnects
    - Bounding boxes + speed sync funzionano normalmente dopo reconnect
    - Consistent behavior tra video_feed.py e tracking_daemon.py
  - **Benefici**:
    - ✅ No more permanent tracking death after long idle
    - ✅ RTSP stream resilience (auto-reconnect every 2s)
    - ✅ YOLO inference resumes transparently after reconnect
    - ✅ Production reliability improvement (daemon survives network hiccups)
  - **File modificato**: `backend/tracking_daemon.py` (6 lines: +3 import, +3 reconnect logic)
  - **Commit**: `c3d26b7` - fix: tracking daemon now reconnects RTSP on timeout

### 2025-01-08 - 🎚️ **CV PROFILES - GLOBAL TEST/NORMAL MODE TOGGLE**
- **🎚️ CV Profiles Feature** - One-click toggle tra Test e Normal mode per TUTTE le locomotive
  - **Problema**:
    - Loco 1 (ESU LokSound V4.0) e Loco 7 (Hornby TXS) NON hanno funzione "Momentum Off" (F4)
    - Altre loco (ESU LokPilot 5) hanno F4 nativo per bypassare CV3/CV4 temporaneamente
    - Per speed matching tests serve CV3≈0, CV4≈0 (risposta immediata)
    - Per uso quotidiano serve CV3/CV4 alti (accelerazione/decelerazione lenta tipo treno vero)
    - Cambio manuale CV via DecoderPro ogni volta = sbattimento
  - **Soluzione**: CV Profiles globali con toggle unico
    - **Hotkey T**: Toggle globale Test ↔ Normal mode per TUTTE le locomotive
    - **Badge header**: Flask icon (amber) per TEST / Check icon (green) per NORMAL
    - **Operations mode write**: CV scritti mentre loco circolano (no programming track)
    - **NO backup**: Config.json contiene ENTRAMBI i profili (normal + testing sempre presenti)
  - **CV Profiles configurati** (6 locomotive attive):
    ```json
    "cv_profiles": {
      "1": {"normal": {"cv3": 78, "cv4": 58}, "testing": {"cv3": 0, "cv4": 0}},
      "2": {"normal": {"cv3": 23, "cv4": 14}, "testing": {"cv3": 0, "cv4": 0}},
      "5": {"normal": {"cv3": 22, "cv4": 16}, "testing": {"cv3": 0, "cv4": 0}},
      "6": {"normal": {"cv3": 23, "cv4": 14}, "testing": {"cv3": 0, "cv4": 0}},
      "7": {"normal": {"cv3": 24, "cv4": 16}, "testing": {"cv3": 1, "cv4": 1}},
      "8": {"normal": {"cv3": 22, "cv4": 15}, "testing": {"cv3": 0, "cv4": 0}}
    },
    "cv_profile_mode": "normal"
    ```
  - **Note valori CV**:
    - **Loco 1**: CV3=78, CV4=58 (motore molto reattivo, serve "frenarlo" per matchare altre)
    - **Loco 7**: CV3=24, CV4=16 normal, **CV3=1, CV4=1 testing** (0,0 troppo brusco vs loco 8)
    - **Altre loco**: CV3=22-23, CV4=14-16 (ESU LokPilot 5 standard)
    - **Loco 4**: Non inclusa (in disuso, mai utilizzata)
  - **Workflow utente**:
    1. Premi **T** → Badge cambia immediatamente (ottimistico)
    2. Backend controlla track power + short circuit (errore immediato se off)
    3. Backend scrive CV testing/normal da config.json (**~1.2s totali**, fire-and-forget + 100ms delays)
    4. Notifica finale conferma successo (3s duration) o errore con dettagli
    5. Fai speed matching tests (slider risponde istantaneamente)
    6. **⚠️ IMPORTANTE**: Ripremi **T** per tornare a normal mode **PRIMA** di chiudere/deployare
  - **⚠️ CRITICAL: Deploy Consistency Rule**:
    - **PC deployment**: `z21-deploy` esegue `git reset --hard` → **config.json sovrascritto**
    - **SE dimentichi di tornare a normal**: Locomotive hanno CV test (0,0) ma config dice "normal"
    - **Conseguenza**: Disallineamento stato fisico vs backend (treni rispondono istantaneamente)
    - **Fix**: Premi T due volte (test → normal → test → normal) per riallineare
    - **Procedura operativa corretta**:
      1. Premi T → TEST mode
      2. Fai speed matching
      3. **Premi T → NORMAL mode** (ripristina CV)
      4. OK per chiudere/deployare
  - **Ottimizzazioni implementate**:
    - ✅ **Fire-and-forget CV write**: Rimosso get_loco_info() + wait error loop → da 6s a ~1.2s
    - ✅ **NO backup file**: Config.json ha entrambi i profili → niente da sovrascrivere
    - ✅ **NO CV read**: Config.json è SoT → zero delay lettura (~20s risparmiati)
    - ✅ **Track power check**: Validazione preventiva → errore chiaro se power off
    - ✅ **Success/failure count**: Messaggio dettagliato se alcune loco falliscono
    - ✅ **Dynamic notification duration**: Fix CSS animation hardcoded 2s → rispetta duration parametro
  - **Benefici**:
    - ✅ Approccio uniforme per TUTTE le locomotive (non serve ricordare chi ha F4)
    - ✅ Velocissimo: ~1.2s invece di manuale DecoderPro
    - ✅ Funziona anche su Hornby TXS (che non avrà mai Momentum Off hardware)
    - ✅ Config.json tracked by git → valori CV versionati
    - ✅ Zero cognitive load: premi T, lavori, ripremi T, fatto
  - **Implementazione**:
    - `config.json`: Sezione `cv_profiles` + `cv_profile_mode` state persistence
    - Backend: `toggle_cv_profile_mode()` con track power validation + error handling
    - Backend endpoints: `/api/toggle-cv-profile-mode` (POST), `/api/cv-profile-mode` (GET)
    - Frontend: Hotkey T + clickable badge (flask/check icon) + rollback su errore
    - Operations mode: CV3/CV4 scritti via `z21.write_cv_ops_mode()` fire-and-forget
  - **Files modificati**:
    - `config.json`: Added cv_profiles + cv_profile_mode
    - `backend/z21_manager.py`: toggle_cv_profile_mode() method
    - `backend/main.py`: API endpoints
    - `scripts/z21.py`: Optimized write_cv_ops_mode() (fire-and-forget)
    - `web/src/App.jsx`: Hotkey T handler + badge
    - `web/src/components/Notification.jsx`: Dynamic animation duration fix
  - **Commit**: `2e4abda` - feat: CV Profiles - global Test/Normal mode toggle for all locomotives

---

## Recent Changelog (2025-12-28 → 2025-01-05)

### 2025-01-05 - 🚀 **YOLO v5 SQUARE MODEL + GATE DISPLAY FIXES**
- **🎯 YOLO v5 Square Model (640x640)** - CPU-optimized training completato
  - **mAP50: 0.931** (better than v4 rectangular 0.919!)
  - Training script: supporto dual mode via `RECTANGULAR` flag
  - Roboflow preprocessing: "Stretch to 640x640" (v5) vs "Fit within 1280x1280" (v4)
  - Auto-fetch latest Roboflow version (no hardcoded version number)
  - Deploy strategy: v5 (square) for Mac CPU, v4 (rectangular) for PC GPU future deployment
  - Model: `scripts/models/best.pt` → BiancAlice_v5 (now committed to git)
- **⚙️ YOLO Inference Size Configurable** - From hardcoded to config-driven
  - Added `yolo_imgsz: 640` to `config.json` under `tracking` section
  - `tracking_daemon.py`: loads and uses `self.yolo_imgsz` from config
  - `track_consist_yolo.py`: loads and uses `self.yolo_imgsz` from config
  - Easy switch: 640 (fast CPU) ↔ [640, 1152] (accurate GPU) without code changes
  - Notes field explains: "640 for square models (fast, CPU), [640, 1152] for rectangular models (accurate, GPU)"
- **🎨 Gate Display Fixes** - Colori corretti finalmente visibili
  - **ROOT CAUSE**: `gate_json_to_dict()` non copiava il campo `color` dal config
  - **FIX**: Aggiunto `color` field a gate dict conversion (con fallback yellow)
  - **RGB→BGR**: `draw_gates_overlay()` ora converte correttamente `(R,G,B)` → `(B,G,R)` per OpenCV
  - **Color scheme**: Gate 1-2 Orange [255,165,0] (C11), Gate 3-4 Cyan [0,255,255] (C10)
  - Rimosso hardcoded `GATE_COLORS` array (ora legge da config)
- **✨ Immediate Gate Rendering After ENTER** - No more disappearing gates!
  - **PROBLEMA**: ENTER salvava solo in `marker_state.config['gates']`, `draw_gates_overlay()` leggeva da `tracker.gates`
  - **SOLUZIONE**: `save_current_gate(tracker)` ora aggiorna ENTRAMBI:
    - `config['gates']` (JSON format per S save)
    - `tracker.gates` (dict format per rendering immediato)
  - Workflow: ENTER → gate visibile subito con colore corretto ✅
  - Tracking: serve ancora riavvio script + assign gate_ids in config.json
- **🎬 Pause Feedback Banner** - Visual confirmation for SPACE key
  - **Design**: Semi-transparent black overlay (70% opaque) + white text centered
  - **Size**: 300x80px banner centro schermo
  - **Duration**: 2 seconds, then auto-disappears
  - **Text**: "PAUSED" or "RESUMED" (ASCII only, no emoji for OpenCV compatibility)
  - **Font**: `FONT_HERSHEY_SIMPLEX` with `thickness=4` for bold effect
  - Console log + visual feedback doppio conferma
- **📐 Config.json Inline Array Formatting** - Improved readability
  - Arrays reformatted from multi-line to inline: `"center": [1227, 213]`
  - File size reduced: 130 lines → 96 lines (26% smaller)
  - Gate restoration: Gate 2 retrieved from `git show HEAD:config.json`
  - Renamed gates: G5→G3, G6→G4 per consistency
- **📝 Files Modified**:
  - `scripts/utils/3_train_yolo_colab.py` - RECTANGULAR flag + auto-version fetch
  - `scripts/track_consist_yolo.py` - gate colors + pause banner + immediate render + gate_json_to_dict fix
  - `backend/tracking_daemon.py` - load yolo_imgsz from config
  - `config.json` - yolo_imgsz parameter + inline arrays + gate color scheme

### 2025-01-05 (tardi) - 🎥 **RTSP BUFFER LAG FIX + CLI FUNCTION STATES FIX**
- **🎥 CRITICAL FIX: RTSP Stream Buffer Accumulation** - Video feed no longer lags 20+ seconds
  - **Problem**: Video feed and gate tracking accumulated progressive lag over time
    - Initial: 3-4s delay, After 10+ min: 20+ seconds delay
    - Impact: Gate crossing detection missed locomotives (daemon saw them 20s late)
  - **Root Cause**: Default OpenCV buffer accumulates frames indefinitely
    - Camera: 15 FPS constant, Processing: ~14.9 FPS average
    - Buffer growth: ~1 frame per 10 seconds → 600 frames after 10 minutes
  - **Solution**: `cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)` on all RTSP streams
    - Always reads freshest frame available
    - Adaptive: fast systems (PC GPU) read most frames, slow systems (Mac CPU) skip old ones
    - Benefits both real-time tracking AND video feed visualization
  - **Files Modified**:
    - `backend/video_feed.py` - Added buffer=1 at init + reconnect (2 locations)
    - `backend/tracking_daemon.py` - Added buffer=1 at init
    - `scripts/track_consist_yolo.py` - Added buffer=1 at init
  - **Result**: Gate crossing detection now real-time, locomotives no longer miss gates
- **🎛️ FIX: CLI Function States for Locomotives in Consists** - Functions display correctly
  - **Problem**: Launching with loco 7 or switching to it showed all functions OFF
    - Applies to all locos in consists (1, 5, 7, 8)
    - Functions were active on decoder but not synced to display
  - **Root Cause**: String matching bug in `_sync_function_states()` (line 516)
    - Old: `if "CONSIST" in self.all_addresses.get(self.address, "")`
    - Loco 7 name: "E656 239 (Rivarossi HR2966S) [IN CONSIST 11]" contains "CONSIST"
    - Entered consist branch, tried to find address 7 in `self.consists`, failed, returned without sync
  - **Solution**: Changed to dict membership check
    - New: `if self.address in self.consists`
    - Precise: only matches actual consist addresses (10, 11)
    - Loco addresses (1, 5, 7, 8) correctly query directly
  - **DCC Architecture Note**: Functions are properties of individual locomotives, not consists
    - Consists only control speed/direction (CV19 in DCC mode)
    - Function states always read from locomotive decoders
  - **Files Modified**:
    - `scripts/z21_controller.py` - Fixed `_sync_function_states()` check
  - **Result**: Function states now display correctly for all locomotives, in consist or standalone
- **📊 Commits**:
  - `a5cdecc` - fix: RTSP stream buffer lag (CAP_PROP_BUFFERSIZE = 1)
  - `19a539a` - fix: CLI function state sync for locomotives in consists

### 2025-01-03 (sera) - ♻️ **REFACTOR: Centralized Config Loading**
- **🎯 Obiettivo**: Eliminare duplicazione config loading (~6 file con json.load/dump)
- **✅ Config Loader Module**: `backend/config_loader.py` creato
  - `load_config()`: carica config.json + merge config.local.json (gitignored)
  - `save_config()`: salva SOLO config.json (mai config.local.json)
  - `get_config_path()`: path centralizzato
  - Deep merge algorithm per override ricorsivo
  - Priority: config.local.json > config.json
- **✅ File Refactorati** (7 totali):
  - `backend/main.py` - API endpoints (~12 load_config chiamate)
  - `backend/tracking_daemon.py` - daemon startup + gate config
  - `backend/video_feed.py` - video overlay + FPS settings
  - `backend/z21_manager.py` - persisted state load/save
  - `backend/roster_loader.py` - consist loader
  - `scripts/track_consist_yolo.py` - standalone script con wrapper
  - `.gitignore` - aggiunto config.local.json
- **✅ Benefici**:
  - Single source of truth per config loading
  - Machine-specific settings (debug mode PC) senza git conflicts
  - DRY principle - zero duplicazione codice
  - Consistent error handling
  - First-load log (stampa solo 1 volta, no spam da 18 chiamate)
- **📄 Config.local.json Support**: Override machine-specific
  - Example file: `config.local.json.example` con istruzioni
  - Gitignored (mai committato)
  - Caso d'uso: `debug.enabled: true` su PC, `false` su Mac
- **📊 Testing**:
  - ✅ Config loading verified (Mac)
  - ✅ Override functionality tested
  - ✅ Git ignore verified
  - ✅ All syntax checks passed
- **📦 Commits**:
  - `132ad18` - refactor: centralized config loading
  - `93376c5` - config: disable debug mode for production (debug.enabled: true→false)
  - Merged develop→main→pushed entrambi

### 2025-01-03 (notte) - 🔧 **PHASE 6 ENHANCEMENTS: Virtual/DCC Mode + CV19 Management**
- **✅ Virtual/DCC Mode Selection** - Consist form con scelta modalità
  - Radio buttons: Virtual Mode (default) vs DCC Mode
  - Virtual Mode: CV19=0, software consist control (safe default)
  - DCC Mode: CV19=consist_address, hardware consist (writes CV)
  - Warning dinamico quando DCC Mode selezionato
  - Form context-aware: "Creating in" vs "Switching to" per edit
- **✅ CV19 Management Completo** - Backend gestisce CV19 automaticamente
  - **POST /api/consists**: scrive CV19 basato su virtual_mode parameter
  - **PUT /api/consists**: rileva mode change e scrive CV19 di conseguenza
  - **DELETE /api/consists**: scrive CV19=0 se consist in DCC mode
  - Reload consist_data dopo ogni CRUD prima di broadcast
- **✅ Delete Modal con CV19 Warning** - Conferma intelligente
  - DCC Mode: warning amber "⚠️ Will write CV19=0 to both locomotives"
  - Virtual Mode: messaggio generico "permanently remove from configuration"
  - Dual button: Cancel (grigio) + Delete (rosso)
  - Z-index 100/110 per overlay corretto
- **✅ WebSocket Real-Time Sync** - Auto-refresh dopo CRUD
  - Broadcast `initial_state` dopo create/update/delete
  - Frontend riceve update → dropdowns si aggiornano automaticamente
  - Multi-device sync: modifiche da un device aggiornano tutti
- **🛡️ Tracking Daemon Improvements** - Gestione errori robusta
  - Skip consists senza `gate_ids` (Virtual Consist software-only)
  - Skip consists con locomotive non-trained in YOLO (graceful degradation)
  - Warning chiaro: "Trained locomotives: [1, 5, 7, 8]"
  - Sistema non crasha mai, qualunque configurazione utente crei
- **🎨 UI Polish** - Header refinements
  - Status indicators: rimosso box background, solo contenuto
  - Track Power indicator: `w-4` invece di `w-7` (spacing compatto)
  - Reload Roster: solo icona (consistente con Add Controller, Consist Manager)
- **🖥️ Deploy Scripts Improvements** - Controllo remoto PC production
  - **z21-stop.bat** (NEW): killa backend Python processes via `taskkill`
  - **z21-deploy.bat** (MODIFIED): NON avvia backend automaticamente
  - Workflow: `z21-deploy` → `z21-backend` manuale → `z21-stop` quando necessario
  - SSH-friendly: pieno controllo da Mac, log visibili
- **📊 Testing & Deployment**:
  - ✅ Consist 12 creato/testato/cancellato (Virtual Mode senza gates)
  - ✅ CV19 write verificato per tutti i mode changes
  - ✅ Dropdowns aggiornati automaticamente dopo CRUD
  - ✅ Tracking daemon skip non-trained locos (no crash)
  - ✅ Merge develop→main completato
  - ✅ Push GitHub main branch
  - ✅ Deploy PC Windows production (GPU) - backend perfettamente funzionante
- **📁 File Modificati**:
  - Backend: `main.py` (+407/-43 righe), `tracking_daemon.py` (+48/-10)
  - Frontend: `ConsistForm.jsx` (+68 righe mode selection), `ConsistManagerModal.jsx` (+50 modal)
  - Frontend: `App.jsx` (header UI polish)
  - Scripts PC: `z21-stop.bat` (NEW), `z21-deploy.bat` (UPDATED)
- **🎯 Status**: Phase 6 completo e deployment live su entrambi Mac (dev) e PC (production)

### 2025-01-03 (sera) - 🎉 **PHASE 6: CONSIST MANAGER UI - COMPLETATA**
- **✅ Phase 6A: Mobile Header Refactor** - Responsive hamburger menu
  - MobileMenu component con slide-in animation (300ms ease-out)
  - Hamburger button mobile-only (<768px)
  - Desktop mantiene inline layout con pulsante "⚙️ Consists"
  - Menu items: Consist Manager, Add Controller, Reload Roster, Wake Lock
- **✅ Phase 6B: Backend CRUD API** - Consist management endpoints
  - **GET `/api/consists`**: restituisce consists + gates + tracking_assignments + reference_locos
  - **POST `/api/consists`**: crea nuovo consist con reference/adjust config
  - **PUT `/api/consists/{address}`**: aggiorna consist esistente
  - **DELETE `/api/consists/{address}`**: elimina consist da config.json + reference_locos
  - **POST `/api/restart-daemon`**: riavvia tracking daemon per reload config
  - Salvataggio automatico in `config.json` (tracking_assignments + reference_locos)
- **✅ Phase 6B: Frontend Components** - UI completa consist manager
  - **ConsistManagerModal.jsx**: modal overlay con backdrop, load/create/edit/delete consists
  - **ConsistCard.jsx**: display consist con badges Reference/Adjust colorati
  - **ConsistForm.jsx**: form create/edit con radio buttons "Reference Locomotive"
  - Integration App.jsx: sostituito placeholder con componente reale
- **🎯 Reference/Adjust Strategy FIX**: Lead/Rear fisica ≠ Reference/Adjust speed matching
  - **Decoupled logic**: Lead/Rear = posizione fisica, Reference/Adjust = speed matching role
  - **config.json**: sezione `reference_locos` con mapping consist → reference/adjust addresses
  - **UI badges**: verde "Reference" (mai toccata), amber "Adjust" (da compensare)
  - **Default**: Rear = Reference (decoder stabile), Lead = Adjust
  - **Esempio C11**: Lead=7 (Hornby, Adjust), Rear=8 (ESU, Reference)
- **📊 Features Implementate**:
  - View: lista consist con locomotive, gates, Virtual Mode status
  - Create: nuovo consist con selezione lead/rear/gates/reference
  - Edit: modifica consist esistente (address locked)
  - Delete: rimozione con conferma + cleanup reference_locos
  - Auto daemon restart dopo ogni CRUD operation
  - Validazione form: address required, lead≠rear, numero valido
- **📁 File Creati/Modificati**:
  - Backend: `main.py` (+168 righe API endpoints)
  - Frontend: `ConsistManagerModal.jsx` (NEW - 218 righe)
  - Frontend: `ConsistCard.jsx` (NEW - 152 righe)
  - Frontend: `ConsistForm.jsx` (NEW - 260 righe)
  - Frontend: `MobileMenu.jsx` (NEW - 82 righe)
  - Frontend: `App.jsx` (+5 righe import/integration)
  - CSS: `index.css` (+18 righe slide-in animation)
- **🎯 Next**: Testing Mac → Merge develop→main → Push → Deploy PC production

### 2025-01-03 (tardo pomeriggio) - 📚 **DOCUMENTATION REFACTOR: CLAUDE.md Reduction**
- **🎯 Obiettivo**: Ridurre CLAUDE.md spostando sezioni grandi in docs/ folder
  - File troppo pesante (2066 righe) difficile da navigare
  - Adottata strategia: file docs/ specializzati con link da CLAUDE.md
- **📝 File docs/ creati**:
  - **docs/CONSIST_ROSTER.md** (93 righe) - Consist 10/11 + roster completo 7 locomotive
  - **docs/WEB_DASHBOARD.md** (488 righe) - Stack tecnologico, features, workflow development
  - **docs/COMPUTER_VISION.md** (995 righe) - Sistema YOLO tracking, gate detection, Virtual Mode
  - **docs/CONFIG_REFACTOR.md** (280 righe) - Technical doc refactoring config.json (2025-01-03)
- **✂️ CLAUDE.md ridotto**:
  - **Sezione "Consist Configuration & Locomotive Roster"**: 93 righe → 9 righe summary + link
  - **Sezione "Web Dashboard"**: 488 righe → 26 righe summary + link
  - **Sezione "Computer Vision Tracking System"**: 995 righe → 34 righe summary + link
- **📊 Risultato**:
  - **Righe originali**: 2066
  - **Righe finali**: 643
  - **Riduzione totale**: 1423 righe (-68.9%)
  - **Totale estratto in docs/**: 1856 righe (4 files)
- **✅ Benefici**:
  - CLAUDE.md ora è un indice conciso con overview + link
  - Documentazione specializzata più facile da navigare
  - Stessa strategia usata per Z21_PROTOCOL.md, JMRI_INTEGRATION.md, etc.
  - Index completo in sezione "📚 Documentazione Estesa"

### 2025-01-03 - 🎉 **MILESTONE: Phase 4 FULLY COMPLETED + GPU Deployment LIVE**
- **✅ Task 4.1 COMPLETED**: Video Performance Optimization
  - Frame queue sharing architecture tested and verified
  - Video NO LONGER freezes durante Δt calculation
  - Performance confermata: smooth video feed con gate crossing detection
- **✅ Task 4.2 COMPLETED**: Generic Gate Tracking Refactor
  - Multi-consist support via config.json completato
  - `consist_data` dict sostituisce tutte le variabili hardcoded
  - Generic `_update_gate_timing()` funziona per ANY consist
  - Sistema ora completamente config-driven
- **✅ Phase 4B COMPLETED**: Virtual Consist Mode
  - CV19 toggle automatico implementato (DCC ↔ Virtual Mode)
  - Speed compensation con Δt feedback da gate timing funzionante
  - UI toggle in ConsistController con status indicators
  - Auto-compensation enable/disable implemented
  - Backend: z21_manager.py con enable/disable_virtual_mode()
  - WebSocket: toggle_virtual_mode + toggle_auto_compensation messages
  - Persist state: consist_state.json
- **🖥️ GPU Deployment LIVE**: PC Windows production deployment
  - ✅ SSH passwordless configurato
  - ✅ Python + CUDA environment setup completato
  - ✅ Repository clonato + dependencies installate
  - ✅ Tailscale Serve configurato (https://gaming-pc.tail9350d7.ts.net)
  - ✅ Backend running in production mode (porta 8000)
  - ✅ Frontend build servito da FastAPI (conditional serving)
  - ✅ YOLO tracking su GPU (CPU usage ridotto 800% → ~100%)
  - ✅ Deployment script `z21-deploy` funzionante
  - ✅ Testato e verificato: sistema completamente operativo

### 2025-12-30 (sera)
- **🎯 Phase 4: Gate Timing Detection COMPLETATA**: Cross-gate timing implementato per Consist 11
  - Gate 1 posizione aggiornata (spostato 80px più in alto)
  - Fix critico Δt calculation con "fresh timestamps" logic
  - Session summary al quit (durata, frames, gate crossings, stats)
  - Console logging ottimizzato (ridotto rumore)
- **🎨 Fix colori OpenCV**: Risolti problemi leggibilità
  - ⚠️ **REGOLA**: OpenCV NON supporta Unicode/emoji - solo ASCII
  - Colori Loco 8 corretti (rosso brillante)
  - Testo Δt waiting: bianco per leggibilità
- **🎯 Next: Phase 4B - Virtual Consist Mode** (pianificato 2025-12-31)

### 2025-12-31 (YOLO Integration - Phase 4 Complete)
- **🚀 Tracking Daemon Integrato**: Headless YOLO + WebSocket broadcast
  - `backend/tracking_daemon.py` - YOLO inference, gate timing, cross-gate Δt
  - Auto-reconnect WebSocket (exponential backoff 2s→30s)
  - Tracking continua offline, riconnette automaticamente
- **🎥 Video Feed con Overlay**: MJPEG stream + gate markers + Δt panel
  - `backend/video_feed.py` - RTSP→MJPEG, draw gates + Δt stats
  - Pannello Δt sempre visibile (anche "Waiting...")
  - Pallini YOLO rimossi (delay RTSP ingestibile)
- **📊 Frontend Δt Stats**: React component + WebSocket sync
  - VideoFeedPanel.jsx collapsible (default chiuso)
  - Prevent re-render inutili (check valore cambiato)
- **⚙️ Soglie Timing Aggiornate**: |Δt| < 1.0s SYNCED, 1.0-2.0s WARNING, >2.0s CRITICAL
  - Aggiornato daemon, yolo track, frontend
- **🔧 Fix Logica Cross-Gate**: Ripristinata logica originale identica
  - 4 detection points tutti cross-gate (L7@G1-L8@G2, L7@G2-L8@G1)
  - Rimosso check `< 5.0s` ridondante
  - Fresh timestamp check: `> self.last_delta_t_time`
- **📁 Camera Config Centralizzato**: `camera_config.json` project root
  - `scripts/camera_utils.py` loader condiviso
  - Tutti script aggiornati (tracking, video feed, utilities)
  - README_CAMERA.md istruzioni setup
- **🔄 Alias z21 Aggiornato**: 3 tab iTerm2 (backend + frontend + daemon)
- **⚠️ Issue Performance**: Daemon molto più lento di track_consist_yolo.py standalone
  - Detection ogni 5 giri vs ogni giro (yolo track)
  - Ritardo 10+ secondi vs immediato
  - Da investigare: WebSocket overhead, frame rate, RTSP buffering
- **🎯 Status**: MVP tracking integrato ma performance non accettabile - serve ottimizzazione

### 2025-12-31 (sera) - 🎯 **PERFORMANCE FIX CRITICO**
- **🐛 ROOT CAUSE IDENTIFICATA**: Doppio daemon in conflitto!
  - **Problema**: Alias `z21` lanciava daemon manuale + TrackingManager lanciava daemon auto
  - **Conflitto**: DUE processi leggevano stessa camera RTSP + YOLO inference contemporanea
  - **Sintomi**: Detection saltate, lag 10+ secondi, valori Δt errati/alternanti
- **✅ SOLUZIONE**: Rimosso daemon da alias `z21`
  - Alias aggiornato: solo 2 tab (backend + frontend)
  - TrackingManager gestisce daemon automaticamente (start/stop con cooldown 10s)
  - Nessun daemon manuale necessario
- **🚀 RISULTATO**: Performance perfette ripristinate!
  - Detection **ogni giro** (non più ogni 5 giri)
  - Δt **immediato** (non più ritardo 10+ secondi)
  - Valori **corretti** (0.156s, 0.309s SYNCED)
  - Cooldown funzionante (daemon auto-killed dopo 10s stop)
- **📝 File modificati**:
  - `~/.bash_aliases` - Funzione `z21()` aggiornata (rimossa 3a tab tracking)
  - `web/src/components/VideoFeedPanel.jsx` - Fix aspect ratio video (`objectFit: contain`)

### 2025-01-01 (sera - tardi) - 📋 **PHASE 4D PLANNING: Generic Gate Tracking Refactor**
- **🎯 Obiettivo**: Documentare refactoring necessario per supporto multi-consist config-driven
  - Gate tracking attualmente hardcoded per Consist 11 (8+ variabili `self.c11_*`)
  - `gate_config.json` ha già struttura corretta (`tracking_assignments`)
  - Codice daemon non usa questa struttura → refactor necessario
- **📝 Plan file aggiornato**: Phase 4D sezione completa
  - Architettura refactored: `self.consist_data` dict al posto di variabili hardcoded
  - Metodo generico `_update_gate_timing(consist_id, lead_pos, rear_pos)` per ANY consist
  - Loop dinamico su consist configurati (no più hardcode)
  - 7 implementation steps documentati
- **📋 CLAUDE.md aggiornato**: Roadmap chiarita
  - Task 4.1: Video Performance (frame queue) 🧪 IN TEST
  - Task 4.2: Generic Refactor 📋 BLOCKED BY 4.1
  - Phase 4B/4C: BLOCKED fino a completamento Task 4.1 e 4.2
- **⏭️ Next**: Test video lag fix (Task 4.1), poi procedere con refactor (Task 4.2)
- **Stima**: ~2-3 ore implementazione Task 4.2 dopo test OK

### 2025-01-01 (sera) - 🎯 **VIDEO LAG FIX CRITICO**
- **🐛 ROOT CAUSE IDENTIFICATA**: Dual VideoCapture RTSP contention
  - **Problema**: 1s+ video freeze quando entrambe le loco attraversano gate (Δt calculation)
  - **Causa**: `tracking_daemon.py` + `video_feed.py` entrambi con `cv2.VideoCapture(RTSP_URL)` sullo stesso stream
  - **Contesa**: Camera Tapo serve 2 client concorrenti → buffering → lag inaccettabile
- **✅ SOLUZIONE**: Frame Queue Sharing (asyncio.Queue)
  - **Architettura PRIMA**: Daemon (subprocess) + Video Feed → 2 VideoCapture separati ❌
  - **Architettura DOPO**: Daemon (asyncio.Task) → single VideoCapture → frame queue → Video Feed ✅
  - **Refactor TrackingManager**: Da subprocess a in-process asyncio.Task per memoria condivisa
  - **Daemon**: `asyncio.Queue(maxsize=2)` + `queue.put_nowait(frame.copy())` dopo YOLO
  - **Video Feed**: Rimosso VideoCapture, convertito async generator, legge da queue con timeout 2s
- **🚀 BENEFICI**:
  - ✅ Zero RTSP contention (single VideoCapture)
  - ✅ Frame letto una volta, usato due volte (efficiente)
  - ✅ Video feed legge da memory queue (non RTSP) → no lag
  - ✅ Backpressure: queue full → skip frame (no accumulo lag)
  - ✅ Startup immediato (no fork processo, accesso diretto frame_queue)
- **📊 SUBPROCESS vs ASYNCIO.TASK**:
  - **Subprocess**: memoria separata, IPC overhead 5-10ms/frame, isolamento crash
  - **Asyncio.Task**: memoria condivisa, zero overhead, GIL non problema (YOLO/OpenCV rilasciano GIL)
  - **Scelta**: asyncio.Task perfetto per frame sharing (requirement chiave)
- **📝 File modificati**:
  - `backend/tracking_daemon.py` - Aggiunto `asyncio.Queue(maxsize=2)`, push frame dopo YOLO
  - `backend/video_feed.py` - Rimosso VideoCapture, convertito async generator, legge da queue
  - `backend/main.py` - Wire `daemon.frame_queue` a video_feed endpoint, imports cv2/numpy
  - `backend/tracking_manager.py` - Da subprocess a asyncio.Task (in-process daemon)
- **🧪 TESTING**: Video NON freeze durante Δt calculation, solo 1 connessione RTSP attiva

### 2025-01-01 (pomeriggio) - 🔧 **STANDALONE SCRIPT ALIGNMENT**
- **🎯 Allineamento yolo track con daemon**: Centralized Δt calculation
  - **Problema**: Standalone aveva 4 calcoli inline Δt (race conditions, valori multipli per frame)
  - **Soluzione**: Refactor per matching esatto architettura daemon
  - **4 detection points**: salvano SOLO timestamp (no calcoli inline)
  - **Funzione centralizzata**: `calculate_delta_t_centralized()` - 2 check cross-gate (non 4!)
  - **Spam reduction**: throttling warnings (Δ>1s o 5s) con `last_ignored_delta_t1/2`
  - **max_delta_t threshold**: 15s caricato da gate_config.json (consistente daemon)
- **✅ BENEFICI**:
  - Elimina race conditions (niente più timestamp misti da lap diversi)
  - Un solo calcolo Δt per frame (non 4 conflittuali)
  - Parità esatta comportamento daemon/standalone
  - Filtraggio corretto valori impossibili (±19s ora ignorati)
- **📝 File modificati**:
  - `scripts/track_consist_yolo.py` - Centralized calculation + spam reduction (+86 righe, -64 inline)

### 2025-12-31 (tarda sera) - ⚙️ **THRESHOLD CENTRALIZATION**
- **🎯 Problema identificato**: Timing thresholds hardcoded in 4 posti diversi
  - `backend/tracking_daemon.py` - thresholds per calcolo status daemon
  - `scripts/track_consist_yolo.py` - thresholds per standalone script
  - `web/src/components/DeltaTStatsPanel.jsx` - thresholds per UI React
  - `backend/main.py` - thresholds per video overlay callback ← **BUG scoperto ultimo!**
- **✅ SOLUZIONE**: Single source of truth in `gate_config.json`
  - Aggiunta sezione `timing_thresholds: {normal: 1.0, warning: 2.0}` al config
  - Backend/daemon/script: caricano da file all'avvio
  - Frontend: riceve thresholds via WebSocket dal daemon
  - Video overlay: usa thresholds caricati nel backend startup
- **🔧 Refactor costanti**: Centralizzate defaults in `backend/main.py`
  - `DEFAULT_TIMING_THRESHOLDS` - fallback se gate_config.json mancante
  - `DEFAULT_CONTROLLER` - template controller vuoto
  - Pattern Path robusto: `Path(__file__).parent.parent / 'gate_config.json'`
- **🎯 Scoperta Tracking**: Funziona SEMPRE (indipendente da DCC/Virtual Mode)
  - DCC Mode (CV19 = 11): Δt monitoring attivo, speed compensation **disabilitato**
  - Virtual Mode (CV19 = 0): Δt monitoring attivo, speed compensation **abilitato**
  - CV19 toggle testato: valori tornano a 11 correttamente
- **📝 UI Decision**: Label "Speed compensation enabled/disabled"
  - Chiaro per utente: enabled = correzioni attive, disabled = solo monitoring
  - Icona: **`fa-gauge-high`** (tachimetro - tema ferroviario perfetto)
  - Da implementare in Phase 4B insieme a Virtual Mode auto-compensation
- **📝 File modificati**:
  - `backend/main.py` - Caricamento thresholds + constants refactor
  - `gate_config.json` - Aggiunta sezione `timing_thresholds`
  - Tutti i 4 componenti ora usano stesso config → zero duplicazione!

### 2025-12-30 (pomeriggio)
- **🎯 Milestone distance-based tracking**: Preservato lavoro completo
  - Commit: `810404b` - "milestone: distance-based tracking v1 (complete)"
  - C11: 217 samples (15.4% co-visibility)
  - Conclusione: funziona per C11, NON per C10
- **♻️ Refactor co-visibility tracking**: Pivot strategico da distance a timing
  - Rimosso distance calculation (-170 righe)
  - Aggiunto co-visibility counters (+54 righe)
  - Netto: -116 righe, codice più leggero
- **🎯 Strategia timing-based RIVISTA: Co-Presence Timing**
  - **C11**: 2 gate rettangolari condivisi (entrambe loco attraversano entrambi)
  - Δt = timestamp_loco7 - timestamp_loco8
  - Obiettivo: Δt ≈ 0 (passaggio quasi contemporaneo)
- **⚙️ Reference Loco Strategy** (CRITICO per Auto CV Adjust)
  - Reference: Loco 8 (ESU stabile) - MAI toccare
  - Adjust: Loco 7 (Hornby instabile) - sempre aggiustare

### 2025-12-30 (sera)
- **🎯 Phase 4: Gate Timing Detection COMPLETATA**: Cross-gate timing implementato per C11
  - Gate 1 posizione aggiornata: Y 293→213 (spostato 80px più in alto)
  - **Fix critico Δt**: "Fresh timestamps" logic - calcola solo con timestamp post-ultimo-Δt
  - Session summary al quit: durata, frames, crossing count, ultimo Δt
  - Log immediate commentati (solo periodic summary + 🚪 crossing logs attivi)
- **🎨 Fix colori OpenCV**: Risolti problemi leggibilità
  - **Regola**: cv2.putText() NON supporta Unicode/emoji - solo ASCII
  - Loco 8 marker: blu→rosso brillante (0,0,255 BGR)
  - Δt waiting text: grigio→bianco per leggibilità
- **📦 Gate Config JSON Integration COMPLETATA**: Sistema data-driven completo
  - Rimossi GATE_1/GATE_2 hardcoded, sostituiti con `self.gates[1]` e `self.gates[2]`
  - Interactive editing: drag & drop, resize 10px, rotation, save with S
  - Fix pause mode: UI sempre attiva (P, M, C funzionano)
  - Fix gate selection: click→edit existing gates
  - Save warnings: no auto-save al quit (solo log console)
- **✅ Decisione Strategica: 2 gate obbligatori per OGNI consist**
  - Approccio standardizzato (Opzione A): co-presence timing + cross-validation
  - C11: già implementato con 2 gate (G1, G2)
  - C10: userà stesso approccio (gate_ids: [3, 4] da configurare)
  - Vantaggi: check frequente, robusto, codice uniforme

### 2025-01-02
- **🖥️ GPU Deployment Guide COMPLETATA**: Documentazione completa Windows deployment
  - Setup SSH passwordless su PC Windows (OpenSSH Server)
  - Configurazione per utenti amministratori (`C:\ProgramData\ssh\administrators_authorized_keys`)
  - Network setup: IP locale + Tailscale Serve
  - Python + CUDA Toolkit installation guide
  - PowerShell functions: `z21-backend`, `z21-deploy`
  - Git branch strategy: develop (Mac) vs main (PC production)
- **✅ Production Mode Backend**: Conditional frontend serving implementato
  - `backend/main.py`: StaticFiles mount se `web/dist/` esiste
  - Development mode (Mac): Vite HMR porta 5173, dist/ NON esiste
  - Production mode (PC): `npm run build` genera dist/, FastAPI serve tutto porta 8000
  - Detection automatico modalità con console output
  - Route `/` riservata per frontend, API su `/api/status`
- **🔑 SSH Setup PC Windows COMPLETATO** (session live):
  - OpenSSH Server installato via Settings GUI
  - Servizio configurato automatic startup
  - SSH passwordless funzionante: Mac → PC senza password
  - Fix permessi `administrators_authorized_keys` per utenti admin
  - Test connessione: ✅ `ssh riccardo@192.168.1.3` senza password
- **📄 Guida accessibile via Tailscale**:
  - File copiato in `web/public/GPU_DEPLOYMENT.md`
  - HTML wrapper con markdown rendering: `GPU_DEPLOYMENT.html`
  - Accesso: `https://mbp16diriccardo.tail9350d7.ts.net/GPU_DEPLOYMENT.html`
- **🎯 Status GPU Deployment**: Step 1 (SSH) completato, resto pianificato
  - ✅ Step 1: SSH passwordless - COMPLETATO
  - ⏳ Step 2: Network/Tailscale (opzionale, IP locale già funziona)
  - ⏳ Step 3: Python + CUDA installation
  - ⏳ Step 4: Clone repository + dependencies
  - ⏳ Step 5: Production deployment con `z21-deploy`
- **♻️ REFACTOR CONFIG NAMING**: `gate_config.json` → `config.json`
  - Nome più generico (contiene gates, FPS, thresholds, debug, reference locos, etc.)
  - **Sostituiti** in tutto il progetto:
    - `GATE_CONFIG_PATH` → `CONFIG_PATH`
    - `load_gate_config()` → `load_config()`
    - `save_gate_config()` → `save_config()`
    - Variabile `gate_config` → `config`
  - **Files modificati**: 5 Python (backend + scripts) + 1 rename (88% similarity)
  - Commit: `28835b0` - "refactor: rename gate_config.json → config.json + debug mode"
- **🔇 DEBUG Mode IMPLEMENTATO**: Console logging intelligente
  - Flag `debug.enabled` in `config.json` (default: false)
  - **SEMPRE visibili** (debug=false): startup, gate crossing (🚦🚪), warnings (⚠️), mode changes (🔄⏸️)
  - **Soppressi** (debug=false): YOLO pause/resume verbose (🔇🔊)
  - **Files modificati**: `backend/tracking_daemon.py` + `config.json`
  - Goal: log puliti per production, verbose solo se necessario

### 2025-01-03
- **♻️ CONFIG.JSON REFACTOR COMPLETO**: Riorganizzazione struttura per maggiore chiarezza
  - **Problema identificato**: Configurazione frammentata e disorganizzata
    - Gates in cima (meno importante)
    - `tracking_assignments` conteneva consists ma `reference_locos` separato
    - Debug in fondo (dovrebbe essere prioritario)
    - Mix di `_comment` e `notes` (inconsistente)
  - **Nuova struttura gerarchica**:
    ```json
    {
      "debug": { ... },           // TOP: priorità massima
      "consists": {               // Consolidato (ex tracking_assignments + reference_locos)
        "10": {
          "name": "...",
          "lead_address": 1,
          "rear_address": 5,
          "gate_ids": [3, 4],
          "virtual_mode": true,
          "auto_compensation_enabled": true,
          "reference": {          // Integrato dentro ogni consist
            "loco": 5,
            "adjust": 1,
            "notes": "..."
          },
          "notes": "..."
        }
      },
      "gates": [ ... ],           // Infrastructure
      "tracking": {               // Grouped settings
        "fps": { ... },
        "timing_thresholds": { ... }
      }
    }
    ```
  - **Path changes** (tutti i file aggiornati):
    - `config['tracking_assignments']` → `config['consists']`
    - `config['reference_locos'][id]` → `config['consists'][id]['reference']`
    - `config['timing_thresholds']` → `config['tracking']['timing_thresholds']`
    - `config['tracking_fps']` → `config['tracking']['fps']`
  - **Files modificati** (7 totali):
    - `config.json` - struttura riorganizzata
    - `backend/main.py` - tutti gli endpoint API aggiornati
    - `backend/roster_loader.py` - load_consists_from_config()
    - `backend/z21_manager.py` - _load_persisted_state() + _save_persisted_state()
    - `backend/tracking_daemon.py` - config loading + reference_locos extraction
    - `backend/video_feed.py` - FPS loading
    - `scripts/track_consist_yolo.py` - standalone script
  - **Vantaggi**:
    - ✅ Ordine logico: debug → consists → gates → tracking
    - ✅ Consolidamento: reference dentro ogni consist (no più frammentazione)
    - ✅ Semantic grouping: fps + timing_thresholds sotto "tracking"
    - ✅ Naming consistente: solo "notes" (eliminato `_comment`)
    - ✅ Zero backward compatibility code (config.json in git, synced to PC)
  - **Decisione**: NO backward compatibility (config su git e sincronizzato su PC)

### 2025-12-30 (mattina)
- **🚂 YOLO Training v3 completato**: Model custom per 4 locomotive
  - Dataset: 137 immagini, training 4 minuti Colab GPU
  - mAP50 = 80.7% accuracy ✅
  - Model deployed: `BiancAlice_v3.pt`
  - Classi: 1_Gr675_017, 5_D645_014, 7_E656_239, 8_E444_056
- **⚠️ CRITICAL**: DCC address (CV1) come prefisso classe
  - MAI cambiare CV1 dopo training YOLO (rompe tutto)
- **📹 YOLO Workflow completo**: Pipeline end-to-end implementata
- **🎯 YOLO Tracking Test Completato**: Tutte e 4 locomotive detectate ✅
  - Confidence scores: 0.60-0.92
  - Distance measurement: 909.7px average (30 samples)
- **📐 Decisione Calibrazione**: Usare pixel direttamente (no cm conversion)
  - Camera grandangolo con distorsione fish-eye
  - Pixel/cm varia con distanza
- **✅ SOLUZIONE: Homography Perspective Correction**
  - Frame corretto: 600x1200px
  - Scala costante: 6 px/cm ovunque
  - Test completato: correzione verificata

### 2025-12-29 (sera)
- **✅ Phase 2: CV Operations Mode - COMPLETATA**
  - CV WRITE implementato e testato ✅
  - CV READ implementato (funziona solo ESU) ✅
- **🚀 Decisione: Adottare YOLO Object Detection**
  - Motion detection puro non sufficiente
  - YOLO training processo completo pianificato

### 2025-12-29 (mattina)
- **🎛️ Scalable UI (Phase 1)**: Controller dinamici implementati
  - Pulsante [+] aggiungi controller
  - Controller rimovibili, supporto N pannelli
- **🔄 Multi-Device Sync via WebSocket**: Sincronizzazione real-time
- **🐛 Fix WebSocket race condition** (CRITICO)
  - Soluzione: 50ms delay tra broadcast
- **⚡ Performance optimizations**: Fix hover lag e scroll glitch

### 2025-12-28
- **🎨 Function button styling refinement**
- **🔴 Indicatori dot color-coded**
- **🐛 Safari Mac animation bug RISOLTO**
  - Root cause: rimozione shadow/animation da elementi transition-all

---

## Recent Changelog (2025-12-25 → 2025-12-27)

### 2025-12-27
- **🔧 Decoder sostituzione E444 056**: ESU LokPilot 5 DCC
- **📝 Cambio indirizzo E656 182**: Address 3 → 2

### 2025-12-26 (Santo Stefano)
- **🎯 Mobile overflow RISOLTO**: Dropdown fix definitivo
- **✅ Tailscale Serve confermato permanente**

### 2025-12-25 (Natale) 🎄
- **Z21 Health Monitoring implementato**
- **Header UI migliorato**: Icone Font Awesome
- **Tailscale HTTPS support**: Dashboard accessibile via Tailscale
- **Favicon aggiornato**: Icona treno

---

## Failed Experiments Archive

### Esperimenti Phase 3 (2025-12-29 sera) - SOSPESA

**Status**: ❌ **Phase 3 SOSPESA** - approccio motion detection puro non praticabile

#### Hardware Setup Testato
- **Camera**: Tapo IP camera (192.168.1.4:554/stream2 - 720P)
- **Connessione**: RTSP stream via OpenCV (cv2.VideoCapture)
- **Snapshot test**: ✅ Funzionante, layout plastico visibile

#### Camera Setup e Prospettiva

**Posizione camera**: Lato corto del plastico (inquadratura laterale, NON top-down)

**Orientamento frame**:
- **BASSO del frame** (bottom, y alto) = VICINO alla camera (primo piano)
- **ALTO del frame** (top, y basso) = LONTANO dalla camera (sfondo, ~2 metri)

**⚠️ PROBLEMA CRITICO: Distorsione Prospettiva**

La distanza fisica costante sul plastico NON corrisponde a pixel costanti:
```
Frame Y=0 (top)    → Lontano dalla camera → 50cm físico = ~500px
          ↓
          ↓ 2 metri profondità
          ↓
Frame Y=720 (bottom) → Vicino alla camera → 50cm físico = ~800px
```

**Conseguenze**:
- **Misure in pixel NON affidabili** per distanza fisica senza correzione prospettiva
- Locomotive a diverse altezze del frame hanno scale px/cm diverse
- 909px baseline primo test vs 1007px secondo test potrebbero dipendere da profondità nel frame, NON da posizioni iniziali

**✅ SOLUZIONE IMPLEMENTATA: Homography Correction con OpenCV**

**Punti calibrazione misurati** (2025-12-30):
```python
# Source points (quadrilatero distorto nel frame originale 1280x720)
SRC_POINTS = np.float32([
    [7, 246],      # Top-left (P1-P2 da prima misura)
    [376, 31],     # Top-right
    [957, 37],     # Bottom-right (P3-P4 da seconda misura - più precisi)
    [257, 718]     # Bottom-left
])
```

**Frame corretto** (perspective transform):
- **Dimensioni**: 600x1200 px
- **Scala**: **6 px/cm costante ovunque** nel frame
- **Area visibile**: 1m x 2m (include plastico + binari sotto)
- **Proporzioni**: **1:2** (perfette!)

**Estensione**: I punti P3-P4 vengono estesi del 30% verso Y=720 per includere binari sotto il bordo plastico

**Test effettuato**: ✅ Correzione prospettica verificata come corretta
**Script**: `test_perspective_correction.py` - visualizza frame originale + frame corretto con griglia

**Residual distortion**: Camera Tapo ha curvatura di campo (fish-eye) - homography NON corregge distorsione radiale lente (solo prospettiva). Errore residuo stimato: 5-10% (accettabile per drift monitoring).

**Status**: ✅ COMPLETATO - pronto per integrazione in track_consist_yolo.py

#### Approcci Sperimentati

**1. Motion Detection con Pattern Analysis** (`track_consist.py`)
- Background subtraction MOG2 + scoring multi-marker
- Analisi tetti (luminosità), pantografi rossi, pattern carrozze
- **Problema**: Troppo complesso, detection instabile
- **Risultato**: Funziona solo angolo basso-dx, resto tracciato inaffidabile

**2. Calcolo Vettore Direzione** (per tracciato ovale)
- Position tracking (5 frames) → calcolo delta_x, delta_y
- Analisi estremità bounding box in base a direzione movimento
- LEFT/RIGHT/UP/DOWN → locomotiva sul bordo corretto
- **Problema**: Aggiunto complessità senza miglioramenti
- **Risultato**: Detection peggiorata, troppa logica

**3. Ottimizzazioni Background Subtractor**
- Provato `varThreshold=60` (meno sensibile)
- Provato `learningRate=0.001` (update lento)
- Provato kernel morphology `(11,11)` (pulizia aggressiva)
- **Problema**: Alcuni config causavano crash, nessun miglioramento significativo

**4. Versione Minimalista** (`track_consist_v2.py`)
- Solo motion detection puro: MOG2 + area filtering
- Prende 2 oggetti più grandi → pallini sui centri
- `varThreshold=60` per ridurre rumore
- **Risultato**: Stabile ma non migliore della v1, serve a poco

#### Problemi Identificati

1. **Motion detection troppo sensibile**
   - Troppo "bianco" nella maschera debug (rumore di fondo)
   - Flash periodici quando MOG2 aggiorna background model
   - Rileva case, edifici, elementi statici del plastico

2. **Pallino in coda invece che su locomotiva**
   - Bounding box include loco + 3 carrozze
   - Analizzando solo "primi 20%" funziona solo se treno va verso sinistra
   - Su tracciato ovale: direzioni multiple (LEFT/RIGHT/UP/DOWN)
   - Calcolo direzione non ha risolto il problema

3. **Tracking instabile**
   - Funziona discretamente solo nell'angolo basso-dx (più vicino)
   - Resto del tracciato: detection persa o errata
   - Distance measurement inaffidabile (centro-a-centro vs loco-a-loco)

#### Conclusioni

**Il solo motion detection NON è sufficiente** per tracking affidabile su tracciato ovale completo.

**Motivi**:
- Background subtraction troppo sensibile a illuminazione, ombre, elementi statici
- Impossible distinguere lead da rear senza features visive robuste
- Locomotive + carrozze = bounding box lungo, centro ≠ posizione locomotiva
- Tracciato ovale = direzioni multiple, pattern analysis complesso

**Alternative necessarie**:
- ✅ **Object detection ML** (YOLO/MobileNet) - training custom su locomotive specifiche
- ✅ **Migliore illuminazione** - LED strip dedicata sopra plastico
- ✅ **Markers fisici** - QR codes o ArUco markers sulle locomotive
- ❌ **Solo motion detection** - dimostrato insufficiente

**Raccomandazione**: Sospendere Phase 3 fino a disponibilità di:
1. Webcam USB di qualità (Logitech C920/C922)
2. Setup illuminazione dedicata
3. Tempo per training model YOLO custom

**Files creati**:
- `scripts/track_consist.py` - versione complessa (motion + scoring) - non funziona
- `scripts/track_consist_v2.py` - versione minimalista (solo motion) - non migliora
- `scripts/utils/view_camera.py` - viewer RTSP per test (funzionante)
- `scripts/utils/calibrate_colors.py` - tool HSV trackbar (creato ma non utile)
- `scripts/utils/pick_colors_from_image.py` - tool click-to-sample (creato ma non utile)

---

## Web Dashboard MVP Era (2025-12-24)

### 2025-12-24 (Vigilia di Natale)
- **🎄 Web Dashboard MVP completato**: Interfaccia web moderna per controllo locomotive
  - **Stack**: Vite 6.0 + React 18.3 + Tailwind CSS v3.4 + FastAPI + WebSocket
  - **Timeline**: 1 giorno (pianificati 2-3) - più veloce del previsto
  - **Estetica**: "Control Room Noir" - design industriale dark con accent amber
- **Frontend implementato** (`/web/`):
  - Vite build tool con Hot Module Replacement
  - React componenti: `App.jsx`, `ConsistController.jsx`
  - Custom hook `useWebSocket.js` per real-time communication
  - Tailwind CSS v3.4 con tema custom (fonts: Outfit, Manrope, JetBrains Mono)
  - Responsive design mobile-first (desktop/tablet/phone)
  - Touch-optimized controls (slider 48px thumb)
  - Grain texture overlay e signal glow effects
- **Backend implementato** (`/backend/`):
  - FastAPI server con WebSocket endpoint (`/ws`)
  - `z21_manager.py`: wrapper Z21 con gestione stato consist
  - `roster_loader.py`: parser JMRI XML per roster e consist
  - Auto-reload backend con Uvicorn
  - Initial state sync da Z21 (funzioni, velocità, direzione)
  - Broadcast updates a tutti i client connessi
- **Features funzionanti**:
  - ✅ Controllo velocità slider 0-126
  - ✅ Direzione toggle (forward/reverse)
  - ✅ Funzioni F0-F28 con indicatori stato ON/OFF
  - ✅ Emergency stop (power on/off con toggle)
  - ✅ Dual consist layout (consist 10 e 11)
  - ✅ Track visualization con posizione treno
  - ✅ Connection status indicator
  - ✅ Multi-device sync real-time via WebSocket
- **Fix critici risolti**:
  1. **Tailwind CSS v4 incompatibilità**: Downgrade a v3.4.0
  2. **Function state sync**: Frontend ora usa `functionStates` da backend
  3. **Function routing**: F0→lead+rear, F1-F28→lead (implementato in z21_manager)
  4. **Initial state loading**: Parsing corretto stati Z21 reali
- **Alias bash creati**: `z21-backend`, `z21-frontend`, `z21-dev`
  - `z21-dev` lancia backend e frontend in terminali separati automaticamente
- **Integrazione JMRI**: Lettura roster XML, indipendente (JMRI non richiesto running)
- **URL**: http://localhost:5173 (locale), http://192.168.1.xxx:5173 (rete)

### 2025-12-19 (sera)
- **Polling periodico implementato (TODO 3)**: Controller ora sincronizzato con Z21
  - Polling ogni 500ms in background (non blocca input tastiera)
  - **Track power**: sincronizzato sempre, rileva power on/off da Z21 fisico o JMRI
  - **Funzioni F0-F28**: sincronizzate con cooldown 2s dopo ultimo comando
  - **Velocità/direzione**: sincronizzazione disabilitata (conflitto con JMRI Throttle)
  - Suoni feedback automatici: Frog.aiff per power OFF, Funk.aiff per power ON
  - Sistema cooldown per evitare race condition tra comandi locali e polling
- **Parser Z21 status corretto**: `get_status()` in z21.py
- **Fix funzioni momentanee**: Ripristinata logica temporizzata
- **Repository Git creato**: https://github.com/rizal72/z21-Terminal (privato)
- **Piano Web Dashboard**: Decisione e pianificazione

### 2025-12-19 (mattina)
- **Vista unificata slider + funzioni**: Interfaccia completamente ridisegnata
- **Controllo funzioni con Shift+lettere**: Implementato hotkey system (Shift+A-Z)
- **Traduzione completa in inglese**: Coerenza con README
- **Test lettura CV via Z21 (fallito)**: Z21 White non supporta POM Read

### 2025-12-18 (sera)
- **Rinomina progetto**: **z21-Terminal**
- **Refocus progetto**: Da tool speed matching a Z21 Controller

### 2025-12-18 (mattina)
- **Lettura stato funzioni**: Implementata sincronizzazione automatica
- **Fix percentuali velocità**: Cambiato `int()` in `round()`
- **Aggiornamenti hardware roster**: Loco 6 decoder sostituito

### 2025-12-17 (notte)
- **Menu funzioni F0-F28**: Implementato completamente
- **z21_test.py → z21.py**: Rinominato in libreria completa
- **UI improvements**: Status bar fisso in alto con ANSI escape codes

### 2025-12-17 (sera)
- **Controller z21_controller.py**: Implementato controller interattivo completo
- **Emergency stop**: Toggle con backslash
- **Scoperta importante**: JMRI e Z21 direct possono coesistere

### 2025-12-17 (mattina)
- **Protocollo Z21 LAN**: Implementato e testato con successo
- **Script `z21_test.py`**: Libreria Z21 protocol completa
- **API JMRI**: Testati endpoint REST

### 2025-12-16
- Setup iniziale progetto
- Attivato JMRI Web Server
- Testata connessione API JSON
- Lette CV da file roster XML
- Documentato setup completo plastico e roster
- Creato script Python `read_cv_from_roster.py` e `read_consists.py`
