# z21-Terminal

**Web-based DCC locomotive controller** with real-time YOLO tracking, automatic speed compensation, and multi-device sync via Z21 LAN protocol.

**Version**: v1.0.0 (Production Ready - JMRI Independence Achieved)
**Repository**: https://github.com/rizal72/z21-Terminal (Private, SSH)
**Project**: BiancAlice Railway Layout
**Last Updated**: 2026-01-21

---

## ⚠️ CRITICAL: Read Deployment Skill First

**Location**: `~/.claude/skills/z21-deployment/SKILL.md`

Contains ALL critical rules for:
- Git workflow (develop/main branches, fast-forward merge)
- Deployment decision tree (docs/backend/frontend)
- PowerShell aliases (z21-deploy-dev, z21-restart, z21-log)
- 7 NON-NEGOTIABLE rules (venv, frontend rebuild, secrets, SSH, encoding, etc.)

**MUST read before any git/deployment operation!**

---

## 🎯 Quick Start

### What is z21-Terminal?

A professional DCC locomotive control system combining:
- **Modern Web Dashboard**: Mobile-first PWA with multi-device sync
- **YOLO Tracking**: Custom AI model for real-time locomotive detection (YOLOv8 OBB, mAP50 91.7%)
- **Automatic Compensation**: Real-time speed matching via gate timing (Δt-based)
- **JMRI Independence**: Autonomous for daily operations (v1.0.0 milestone)

### Quick Commands

**Mac (Development)**:
```bash
z21              # Start backend + frontend (iTerm tabs)
z21-backend      # Backend only (port 8000)
z21-frontend     # Frontend only (port 5173)
z21-terminal     # CLI controller
```

**PC Windows (Production)**:
```powershell
# Deployment
z21-deploy       # Full deployment from main branch (PRODUCTION)
z21-deploy-dev   # Full deployment from develop branch (DEVELOPMENT)

# Backend Management
z21-start        # Start backend (Task Scheduler background)
z21-restart      # Restart backend
z21-stop         # Stop backend
z21-status       # Check backend status

# Monitoring & Dev
z21-log          # View backend logs (tail -200)
z21-backend      # Run backend foreground (port 8000)
z21-frontend     # Run frontend dev server (port 5173)
```

### Access URLs

- **Mac Dev**: http://localhost:5173 or http://192.168.1.xxx:5173
- **Mac Dev (Tailscale)**: https://mbp16diriccardo.tail9350d7.ts.net
- **PC Prod Local**: http://localhost:8000
- **PC Prod (Tailscale)**: https://gaming-pc.tail9350d7.ts.net

---

## 📚 Complete Documentation Index

### Core Architecture
- **[DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)** - SQLite `data.db` complete reference (sessions, events, speed tables, consist state)
- **[WEB_DASHBOARD.md](docs/WEB_DASHBOARD.md)** - Frontend stack (React + Vite + Tailwind), features, development workflow
- **[Z21_PROTOCOL.md](docs/Z21_PROTOCOL.md)** - Z21 LAN protocol (UDP), XpressNet commands, POM operations (CV read/write)
- **[JMRI_INTEGRATION.md](docs/JMRI_INTEGRATION.md)** - JMRI relationship, coexistence, independence roadmap

### Locomotive Management
- **[CONSIST_ROSTER.md](docs/CONSIST_ROSTER.md)** - 7 locomotives, 2 consists, decoder specs (ESU/Hornby), CV profiles
- **[CONSIST_MAPPING.md](docs/CONSIST_MAPPING.md)** - Lead/Rear vs Reference/Adjust logic, decoder stability strategy
- **[SPEED_TABLE_DB_MIGRATION.md](docs/SPEED_TABLE_DB_MIGRATION.md)** - v1.0.0 milestone: CV67-94 in database, config refactoring
- **[SPEED_TABLE_VIEWER.md](docs/SPEED_TABLE_VIEWER.md)** - Phase 1+2: Read-only analysis + direct CV write (operations mode)
- **[SPEED_TABLE_WEIGHTED_RECOMMENDATIONS.md](docs/SPEED_TABLE_WEIGHTED_RECOMMENDATIONS.md)** - Weighted algorithm: current session priority, CV filtering, inline UI breakdown
- **[SPEED_TABLE_DECODER_BEHAVIOR.md](docs/SPEED_TABLE_DECODER_BEHAVIOR.md)** - ESU mfx vs NMRA speed table differences, implementation plan

### Computer Vision & Tracking
- **[COMPUTER_VISION.md](docs/COMPUTER_VISION.md)** - YOLO training workflow (4 classes), gate timing detection, Virtual Mode
- **[CONSIST_TRACKING.md](docs/CONSIST_TRACKING.md)** - Timing-based vs distance-based strategies, symmetric/asymmetric gates
- **[TENSORRT_OPTIMIZATION.md](docs/TENSORRT_OPTIMIZATION.md)** - GPU acceleration (2-5x faster), OBB model export workflow
- **[VIRTUAL_CONSIST_MODE.md](docs/VIRTUAL_CONSIST_MODE.md)** - CV19 management, speed compensation (bang-bang + decay), real-time feedback

### Analytics & Monitoring
- **[ANALYTICS.md](docs/ANALYTICS.md)** - Session tracking, Δt trends, YOLO performance, locomotive operating time
- **[DB_REFACTORING.md](docs/DB_REFACTORING.md)** - Database consolidation: analytics.db → data.db migration (2026-01-17)
- **[LOCOMOTIVE_SYNC_MAC_PC.md](docs/LOCOMOTIVE_SYNC_MAC_PC.md)** - Multi-environment config sync

### UI & Configuration
- **[SETTINGS_UI_DESIGN.md](docs/SETTINGS_UI_DESIGN.md)** - Settings modal (8 tabs), locomotive function editor, gate editor
- **[CV3_CV4_EDITOR.md](docs/CV3_CV4_EDITOR.md)** - Acceleration/Deceleration editor (Settings > Locomotives)
- **[CONSIST_MANAGER_UI.md](docs/CONSIST_MANAGER_UI.md)** - Consist CRUD operations via web UI (Phase 6)
- **[CONFIG_REFACTOR.md](docs/CONFIG_REFACTOR.md)** - Config.json structure evolution (2025-01-03)

### Planning & Archive
- **[CHANGELOG_ARCHIVE.md](docs/CHANGELOG_ARCHIVE.md)** - Historical changes (2025-12-16 → 2026-01-16)
- **[FUTURE_IDEAS.md](docs/FUTURE_IDEAS.md)** - Enhancement ideas (Session Replay, Autopilot, Notifications, Multi-User, etc.)
- **[REFACTOR_PLAN.md](docs/REFACTOR_PLAN.md)** - Backend modular architecture design (2340 lines → 742 main + 2648 modular)
- **[FRONTEND_REFACTOR_PLAN.md](docs/FRONTEND_REFACTOR_PLAN.md)** - Frontend component refactoring
- **[LOG_REFACTORING.md](docs/LOG_REFACTORING.md)** - Debug mode strategy (config.json flag)
- **[MOTOR_LOAD_MONITORING.md](docs/MOTOR_LOAD_MONITORING.md)** - Phase 9: Z21 telemetry monitoring (future quick win)
- **[TRACK_MAP_IMPLEMENTATION.md](docs/TRACK_MAP_IMPLEMENTATION.md)** - Phase 7: SVG track visualization (postponed)
- **[GPU_DEPLOYMENT.md](docs/GPU_DEPLOYMENT.md)** - PC Windows deployment notes
- **[REPORTS_TAB.md](docs/REPORTS_TAB.md)** - Analytics reports design
- **[SPEED_TABLE_TUNING.md](docs/SPEED_TABLE_TUNING.md)** - Speed table tuning strategies

---

## 🏗️ Architecture Overview

### System Components

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│   Frontend  │────▶│   Backend    │────▶│    Z21     │
│  React PWA  │◀────│  FastAPI WS  │◀────│ Controller │
│ (port 5173) │     │ (port 8000)  │     │  (UDP)     │
└─────────────┘     └───────┬──────┘     └────────────┘
                            │
                    ┌───────┴────────┐
                    │                │
               ┌────▼─────┐   ┌─────▼──────┐
               │ data.db  │   │ YOLO Daemon│
               │ (SQLite) │   │ (Tracking) │
               └──────────┘   └────────────┘
```

### Directory Structure

```
z21-Terminal/
├── backend/                    # FastAPI backend (modular architecture v1.0.0)
│   ├── main.py                 # FastAPI app (742 lines, minimal delegation)
│   ├── dependencies.py         # Global state DI (Z21, WebSocket manager)
│   ├── routers/                # API endpoints (analytics, config, roster, status, video_feed)
│   ├── services/               # Business logic (analytics_db, broadcast, config_manager)
│   ├── websocket_handlers/     # Real-time handlers (ws_control, ws_tracking)
│   ├── tracking/               # YOLO tracking runtime components
│   │   ├── yolo_tracker.py     # YOLOTracker class (34k - inference, gate detection)
│   │   └── rtsp_handler.py     # RTSP stream utilities
│   ├── tracking_daemon.py      # Headless YOLO tracking daemon
│   └── data/
│       └── data.db             # SQLite database (auto-created, gitignored)
├── web/                        # React frontend
│   ├── src/
│   │   ├── App.jsx             # Main component
│   │   └── components/         # React components (ConsistController, Analytics, Settings, etc.)
│   ├── dist/                   # Production build (gitignored)
│   └── package.json
├── scripts/                    # Python utilities & YOLO training workspace
│   ├── z21.py                  # Z21 LAN protocol library (UDP commands, XpressNet)
│   ├── z21_controller.py       # CLI locomotive controller (46k)
│   ├── track_consist_yolo.py   # Standalone YOLO tracking script (43k)
│   ├── camera_utils.py         # RTSP camera utilities
│   ├── utils/                  # YOLO training pipeline (see docs/COMPUTER_VISION.md)
│   └── models/                 # YOLO model files (PC Windows only, gitignored)
│       ├── best_obb.pt         # OBB PyTorch (6.6 MB) - Active model
│       ├── best_obb.onnx       # OBB ONNX export (12.5 MB)
│       ├── best_obb.engine     # OBB TensorRT (8.1 MB) - GPU optimized
│       ├── best.pt             # Standard PyTorch (6.3 MB)
│       ├── best.onnx           # Standard ONNX (12.3 MB)
│       └── best.engine         # Standard TensorRT (7.7 MB)
├── docs/                       # Documentation (24 markdown files)
├── config.json                 # Central configuration (committed to git)
└── config.local.json           # Local overrides (gitignored, credentials)
```

### Backend Modular Architecture (v1.0.0)

**Refactored**: 2340 lines monolithic → 742 lines main + 2648 lines modular

- **main.py** (742): FastAPI app with minimal delegation
- **routers/** (839): API endpoints organized by domain (analytics, config, roster, status, video_feed)
- **services/** (993): Business logic (DB queries, broadcasting, config management)
- **websocket_handlers/** (586): Real-time locomotive control + tracking

**Benefits**: Single responsibility, testability, scalability, zero main.py changes for new features

See [docs/REFACTOR_PLAN.md](docs/REFACTOR_PLAN.md) for complete design

---

## 🚂 Locomotive Roster & Consists

### Hardware Configuration

**Control Station**:
- Roco Z21 Bianca (IP 192.168.1.111, port UDP 21105, firmware 1.67)

**Computer Vision**:
- Tapo IP camera (rtsp://192.168.1.4:554/stream2 - 720P, H.264)

**Locomotives** (7 total):
| Address | Name | Decoder | Color | Consist | Role |
|---------|------|---------|-------|---------|------|
| 1 | Gr.675 017 | ESU LokSound V4.0 | Yellow | C10 | Lead (adjust) |
| 5 | D645 014 | ESU LokPilot 5 | Orange | C10 | Rear (reference) |
| 7 | E656 239 | Hornby TXS | Green | C11 | Lead (adjust) |
| 8 | E444 056 | ESU LokPilot 5 | Red | C11 | Rear (reference) |
| 2 | E656 182 | ESU LokPilot 5 | White | - | Single |
| 4 | 2048 | Zimo MX630 | Cyan | - | Single |
| 6 | D445 1140 | ESU LokPilot 5 | Magenta | - | Single |

**Consists** (2 active):
- **Consist 10** (Internal Track - Figure-8): Loco 1 + 5, Asymmetric gates (G3/G4)
- **Consist 11** (External Track - Oval): Loco 7 + 8, Symmetric gates (G1/G2)

**Reference Loco Strategy**: Always rear loco (stable ESU decoders), adjust loco = lead (potentially unstable)

**Complete specs**: See [docs/CONSIST_ROSTER.md](docs/CONSIST_ROSTER.md)

---

## ⚙️ Configuration Files

### config.json (Central Configuration)

**Location**: `/Users/riccardosallusti/Documents/_PROGETTI/z21-Terminal/config.json`

**Key Sections**:
```json
{
  "debug": { "enabled": false },              // Production: false, Dev: true
  "z21": { "host": "192.168.1.111", "port": 21105 },
  "camera": {
    "ip": "192.168.1.4",
    "port": 554,
    "stream": "stream2",
    "resolution": { "width": 1280, "height": 720 },
    "notes": "Credentials in config.local.json"
  },
  "video": { "fps": 30 },                     // MJPEG stream FPS
  "consists": {
    "10": {
      "name": "C10 Interno",
      "lead_address": 1, "rear_address": 5,
      "reference_loco": 5, "adjust_loco": 1,
      "gate_ids": [3, 4],
      "gate_assignment": { "reference": 3, "adjust": 4 },  // Asymmetric
      "virtual_mode": false,
      "auto_compensation_enabled": false
    },
    "11": {
      "name": "C11 Esterno",
      "lead_address": 7, "rear_address": 8,
      "reference_loco": 8, "adjust_loco": 7,
      "gate_ids": [1, 2],
      "gate_assignment": null,                 // Symmetric (all gates)
      "virtual_mode": true,
      "auto_compensation_enabled": true
    }
  },
  "gates": [
    { "id": 1, "name": "Gate 1", "center": [995, 27], "width": 65, "height": 43, "angle": 0, "color": [255, 165, 0] },
    { "id": 2, "name": "Gate 2", "center": [10, 269], "width": 44, "height": 47, "angle": -30, "color": [255, 165, 0] },
    { "id": 3, "name": "Gate 3", "center": [1086, 326], "width": 80, "height": 80, "angle": 300, "color": [0, 255, 255] },
    { "id": 4, "name": "Gate 4", "center": [479, 29], "width": 50, "height": 50, "angle": 0, "color": [0, 255, 255] }
  ],
  "tracking": {
    "fps": { "active": 30, "idle": 1, "video_feed": 30 },
    "idle_timeout_seconds": 10,
    "timing_thresholds": {
      "warning": 1.0,                          // |Δt| >= 1.0s → WARNING
      "critical": 1.5,                         // |Δt| >= 1.5s → CRITICAL
      "max_delta_t": 10.0                      // Outlier filter
    },
    "yolo_confidence": 0.4,                    // OBB model optimized value
    "yolo_iou": 0.6,                           // Lower for OBB (reduced overlap)
    "yolo_imgsz": 640,
    "yolo_obb": true                           // Oriented Bounding Boxes
  },
  "tracking_OBB": {                            // Quick-load preset
    "yolo_confidence": 0.4,
    "yolo_iou": 0.6,
    "yolo_obb": true
  },
  "tracking_standard": {                       // Quick-load preset
    "yolo_confidence": 0.2,
    "yolo_iou": 0.95,
    "yolo_obb": false
  },
  "analytics": {
    "max_chart_events": 500                    // Chart optimization (100-2000)
  },
  "locomotives": {
    "1": {
      "name": "Gr.675 017",
      "decoder": "LokSound V4.0",
      "color": "#FFFF00",
      "cv_profiles": {
        "normal": { "cv3": 78, "cv4": 58 },
        "testing": { "cv3": 0, "cv4": 0 }
      },
      "notes": "",
      "functions": [                           // F0-F28 labels and lockable flags
        { "number": 0, "label": "light", "lockable": true },
        { "number": 1, "label": "sound", "lockable": true },
        ...
      ]
    },
    ...
  }
}
```

**Migration History** (v1.0.0):
- Unified `locomotives` section (was split across `locomotive_colors`, `cv_profiles`)
- Removed dependency on JMRI roster XML for locomotive metadata
- CV67-94 speed tables moved to database
- Function labels F0-F28 in config.json (editable via Settings UI)

**Complete reference**: See [docs/CONFIG_REFACTOR.md](docs/CONFIG_REFACTOR.md)

---

### config.local.json (Local Overrides)

**Location**: Root directory (gitignored)

**Purpose**: Machine-specific overrides (credentials, test mode, local IP changes)

**Example**:
```json
{
  "camera": {
    "username": "your_username",
    "password": "your_password"
  },
  "debug": {
    "enabled": true
  }
}
```

**Merging**: `load_config()` from `config_loader.py` deep-merges config.local.json over config.json at runtime

**Setup**: Copy `config.local.json.example` and add credentials

See `README_CAMERA.md` for camera setup instructions

---

### data.db (SQLite Database)

**Location**: `backend/data/data.db` (auto-created, gitignored)

**Tables**:
- **sessions** - Analytics session tracking (id, start_time, end_time, event_count)
- **events** - Time-series events (delta_t, speed_setting, yolo_performance, loco_operating_time)
- **locomotive_stats** - Aggregate statistics per locomotive (operating time, session count)
- **locomotive_speed_table** - CV67-94 speed tables (28 steps per locomotive)
- **consist_state** - Virtual Mode + Auto Compensation state per consist
- **system_state** - System-wide key-value state

**Event Types** (JSON in `events.data`):
- `delta_t` - Gate crossing timing delta (consist_id, delta_t, status, gate_type, speed)
- `speed_setting` - DCC speed changes (address, speed_old, speed_new, forward, source)
- `loco_operating_time` - Locomotive operating duration (address, start_time, end_time, duration_seconds)
- `yolo_performance` - YOLO tracking metrics (avg_fps, avg_confidence per loco, miss_rate)

**Complete schema**: See [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)

**Common Queries**:
```sql
-- Find all CRITICAL delta_t events for consist 11
SELECT datetime(timestamp, 'unixepoch', 'localtime') as time,
       json_extract(data, '$.delta_t') as delta_t,
       json_extract(data, '$.status') as status
FROM events
WHERE event_type='delta_t'
  AND json_extract(data, '$.consist_id')=11
  AND json_extract(data, '$.status')='CRITICAL'
ORDER BY timestamp DESC;

-- Get locomotive operating time summary
SELECT address, name,
       total_operating_seconds / 3600.0 as hours,
       total_sessions
FROM locomotive_stats
ORDER BY total_operating_seconds DESC;
```

---

## 🎮 Key Features & Workflows

### 1. JMRI Independence (v1.0.0 Milestone - 2026-01-17)

**What's Autonomous**:
- ✅ CV67-94 speed tables (database + web UI editor)
- ✅ CV19 consist management (Virtual/DCC Mode toggle)
- ✅ Locomotive metadata (config.json unified: name, decoder, color, notes)
- ✅ Consist CRUD (create/edit/delete via web UI)
- ✅ Function labels F0-F28 (config.json, editable via Settings UI)

**What Still Needs JMRI** (Initial Setup Only):
- Initial decoder configuration (CV1 address, decoder detection)
- Programming track operations (read/write all CVs for new decoder)
- Advanced CV programming (decoder-specific UI screens)

**Typical Workflow**:
1. **Initial Setup** (JMRI - one time): Configure decoder via DecoderPro
2. **Import** (One-time script): `python scripts/import_single_locomotive.py`
3. **Daily Operations** (z21-Terminal - no JMRI needed): Edit functions, tune speed tables, manage consists

**The Ultimate Test**: Renamed `roster/` → `roster.backup/` on PC → backend still works! 🎉

**Complete guide**: See [docs/JMRI_INTEGRATION.md](docs/JMRI_INTEGRATION.md)

---

### 2. YOLO Tracking & Speed Compensation

**System Overview**:
- **YOLO Model**: YOLOv8 nano OBB (mAP50 = 91.7%, 4 classes: loco 1, 5, 7, 8)
- **TensorRT Acceleration**: GPU-optimized (2-5x faster, <0.5s bbox lag)
- **Gate Timing Detection**: Symmetric (oval) and asymmetric (figure-8) modes
- **Dynamic FPS**: 30 FPS active tracking, 1 FPS idle (10s timeout)

**Virtual Consist Mode**:
- **Automatic CV19 Management**: Toggle DCC/Virtual mode via UI (writes CV19=0 or CV19=consist_id)
- **Speed Compensation**: Real-time Δt-based adjustment (bang-bang + decay algorithm)
- **Reference Loco Strategy**: Config-driven (never touch reference, adjust only unstable loco)

**Example**: Consist 11 (External Track - Symmetric Gates)
```
Gate 1 (995,27) ────▶ Loco 7 crosses ────▶ Timestamp T1
Gate 2 (10,269)  ────▶ Loco 8 crosses ────▶ Timestamp T2

Δt calculation (cross-gate):
  Option A: Δt = T1(L7@G1) - T2(L8@G2)  (valid)
  Option B: Δt = T1(L7@G2) - T2(L8@G1)  (valid)

If Δt > 0: Loco 7 too fast → slow down Loco 7
If Δt < 0: Loco 7 too slow → speed up Loco 7
```

**Status Thresholds** (from config.json):
- `SYNCED`: |Δt| < 1.0s (green)
- `WARNING`: 1.0s ≤ |Δt| < 1.5s (amber)
- `CRITICAL`: |Δt| ≥ 1.5s (red)

**Complete workflow**: See [docs/COMPUTER_VISION.md](docs/COMPUTER_VISION.md), [docs/VIRTUAL_CONSIST_MODE.md](docs/VIRTUAL_CONSIST_MODE.md)

**TensorRT Export**: See [docs/TENSORRT_OPTIMIZATION.md](docs/TENSORRT_OPTIMIZATION.md)

---

### 3. Analytics Dashboard

**Features**:
- **Session Tracking**: Automatic lifecycle (first Δt validates, idle timeout or page close ends)
- **Δt Trends Chart**: Speed matching quality over time (color-coded zones)
- **YOLO Performance**: FPS trends + per-locomotive confidence
- **Locomotive Operating Time**: Cumulative hours per locomotive (maintenance planning)
- **Current vs Overview Views**: Session-specific vs cumulative historical data
- **Intelligent Downsampling**: LTTB algorithm + critical event preservation (|Δt| ≥ 1.5s always visible)

**Keyboard Shortcut**: Press `A` to toggle Analytics panel

**Configuration**: `config.json` → `analytics.max_chart_events` (100-2000, default 500)
- **Current view**: Shows last N events (no downsampling, full resolution)
- **Overview view**: Downsamples to N events if total > N (LTTB + critical events)

**Complete implementation**: See [docs/ANALYTICS.md](docs/ANALYTICS.md)

---

### 4. Speed Table Tuning

**Phase 1** (Read-Only Analysis - v1.0.0):
- 28-bar visualization of CV67-94 (step 1-28, values 0-255)
- Color-coded highlighting based on CRITICAL event counts
- CV adjustment recommendations
- Interactive bars (click to edit in Phase 2)

**Phase 2** (Direct CV Write - v1.0.0):
- Interactive editing (click bar to adjust, drag vertical slider)
- Direct write to decoder (operations mode, no programming track needed)
- Undo support (1-level snapshot via `previous_values` JSON column)
- Re-import from JMRI when needed

**CV Operations Mode Support**:
- **ESU LokPilot/LokSound** (loco 1, 2, 5, 6, 8): ✅ CV read + write supported
- **Hornby TXS** (loco 7): ⚠️ CV write supported, CV read NOT supported (use Hornby BT app)
- **Zimo MX630** (loco 4): ✅ CV read + write supported

**Complete guide**: See [docs/SPEED_TABLE_VIEWER.md](docs/SPEED_TABLE_VIEWER.md)

---

### 5. CV Profiles (TEST/NORMAL Mode)

**Quick Toggle** (Hotkey `T`):
- **TEST mode**: CV3=0, CV4=0 (instant response for testing/tuning)
- **NORMAL mode**: CV3/CV4 restored (realistic acceleration/deceleration from cv_profiles.normal)
- Writes CV3/CV4 to all locomotives in consists (~1.2s total via POM)
- Badge indicator in UI (Flask icon = TEST, Check icon = NORMAL)

**IMPORTANT**: Press `T` to return to NORMAL before closing app or deploying to PC

**Configuration**: `config.json` → `locomotives.X.cv_profiles.normal` and `locomotives.X.cv_profiles.testing`

---

### 6. Consist Manager

**Features** (Phase 6 - Completed 2026-01-03):
- **Create Consist**: Add new consist via modal form
- **Edit Consist**: Modify addresses, gates, mode, reference loco
- **Delete Consist**: Remove consist with confirmation
- **Gate Assignment**: Symmetric (all gates) or Asymmetric (specific gate per loco)
- **Virtual Mode Toggle**: Enable/disable Virtual Consist Mode per consist
- **Auto Compensation Toggle**: Enable/disable real-time speed compensation

**Access**:
- Desktop: [⚙️ Consists] button in header (inline)
- Mobile: Hamburger menu → ⚙️ Consist Manager

**Complete guide**: See [docs/CONSIST_MANAGER_UI.md](docs/CONSIST_MANAGER_UI.md)

---

### 7. Settings UI

**8 Tabs** (Phase 3 - Completed 2025-12-28):
1. **System**: Debug mode toggle
2. **Z21 Network**: IP, port, test connection
3. **Camera**: IP, port, stream, credentials, test stream
4. **Video Feed**: FPS slider (hot reload)
5. **YOLO Model**: Confidence, IoU, OBB toggle, preset load buttons
6. **Tracking**: FPS active/idle, idle timeout, timing thresholds (warning/critical/max_delta_t)
7. **Analytics**: Max chart events (100-2000, performance tuning)
8. **Locomotives**: Function labels F0-F28 editor (accordion, inline edit)

**Hot Reload** (No Restart Required):
- ✅ Video Feed FPS
- ✅ Locomotive functions
- ✅ Analytics max_chart_events

**Restart Required**:
- Backend: Debug mode, Z21 network, camera settings, YOLO model, tracking FPS/thresholds
- Frontend: Locomotive function changes (page reload)

**Complete guide**: See [docs/SETTINGS_UI_DESIGN.md](docs/SETTINGS_UI_DESIGN.md)

---

## 🛠️ Critical Workflows

### Deployment Workflow (Mac → PC)

**IMPORTANT**: Read `~/.claude/skills/z21-deployment/SKILL.md` for complete rules

**Mac Development**:
```bash
# Make changes, test locally
z21              # Test backend + frontend
git add .
git commit -m "feat: description"
git push origin develop
```

**PC Production Deployment**:
```powershell
# Full deployment - PRODUCTION (main branch)
ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-deploy"

# Full deployment - DEVELOPMENT (develop branch)
ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-deploy-dev"

# Backend-only changes (skip frontend rebuild)
ssh riccardo@gaming-pc "cd C:\z21-Terminal && git pull && z21-restart"
```

**Deployment Decision Tree**:
- **Docs only** (`CLAUDE.md`, `docs/*`): Just `git push` (no deployment needed)
- **Backend only** (`backend/*`): `git pull && z21-restart`
- **Frontend only** (`web/src/*`): `z21-deploy-dev` (must rebuild dist/)
- **Both**: `z21-deploy-dev`

**CRITICAL Rules**:
1. ✅ Frontend changes require `z21-deploy-dev` (rebuild dist/)
2. ✅ Always use PowerShell aliases (NOT manual git/npm)
3. ✅ Always include username: `riccardo@gaming-pc` (NOT just `gaming-pc`)

**Complete guide**: See `~/.claude/skills/z21-deployment/SKILL.md`

---

### Git Workflow

**Branch Strategy**:
- `main` - Production stable releases
- `develop` - Daily development work

**Daily Workflow**:
```bash
git checkout develop           # Work on develop branch
# ... make changes ...
git add .
git commit -m "feat: description"
git push origin develop

# When ready for release
git checkout main
git merge develop --ff-only   # Fast-forward only (no merge commits)
git push origin main
git checkout develop           # ⚠️ CRITICAL: Always return to develop
```

**IMPORTANT**: Always return to `develop` after merging to `main`

**Git Remote**: Always use SSH (NOT HTTPS)
```bash
git remote -v
# Should show: git@github.com:rizal72/z21-Terminal.git ✅
```

---

### Database Queries (Common Operations)

**Find all gate crossings for consist 11 (last 24h)**:
```sql
SELECT
    datetime(timestamp, 'unixepoch', 'localtime') as time,
    json_extract(data, '$.delta_t') as delta_t,
    json_extract(data, '$.status') as status,
    json_extract(data, '$.speed') as speed
FROM events
WHERE event_type='delta_t'
  AND json_extract(data, '$.consist_id')=11
  AND timestamp > (strftime('%s', 'now') - 86400)
ORDER BY timestamp DESC;
```

**Get locomotive operating time summary**:
```sql
SELECT
    address,
    name,
    total_operating_seconds / 3600.0 as hours,
    total_sessions,
    datetime(last_active_time, 'unixepoch', 'localtime') as last_active
FROM locomotive_stats
ORDER BY total_operating_seconds DESC;
```

**Delete outlier delta_t events** (|Δt| > 3s without speed):
```sql
DELETE FROM events
WHERE id IN (
  SELECT id FROM events
  WHERE event_type='delta_t'
    AND (json_extract(data, '$.delta_t') > 3.0 OR json_extract(data, '$.delta_t') < -3.0)
    AND json_extract(data, '$.speed') IS NULL
);
```

**Database maintenance**:
```bash
# Vacuum (reclaim space after deletions)
sqlite3 backend/data/data.db "VACUUM;"

# Backup
cp backend/data/data.db backend/data/data.db.backup

# Copy between Mac and PC
scp backend/data/data.db riccardo@gaming-pc:C:/z21-Terminal/backend/data/data.db
```

**Complete queries**: See [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)

---

## 🐛 Troubleshooting

### Backend Won't Start

**Check venv activation**:
```bash
# Mac
source venv/bin/activate
python backend/main.py

# PC (automatic in aliases)
z21-backend  # Auto-activates venv
```

**Check Z21 connectivity**:
```bash
ping 192.168.1.111
```

**Check logs**:
```bash
# Mac
tail -f backend/z21-terminal.log

# PC
ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-log"
```

---

### Frontend Changes Not Visible

**Vite HMR limitations**:
- Frontend changes: Auto-reload (no action needed)
- Backend changes: Must restart backend (`z21-restart`)
- useEffect/hooks: May require manual refresh (Ctrl+R or Cmd+R)

**Production (PC)**: Always run `z21-deploy-dev` for frontend changes (must rebuild dist/)

---

### YOLO Not Detecting Locomotives

**Check TensorRT model**:
```bash
# PC
dir C:\z21-Terminal\best_obb.engine  # Should be ~13.7 MB

# Mac
ls -lh ~/Documents/_PROGETTI/z21-Terminal/best_obb.engine
```

**Fallback order**: `.engine` → `.onnx` → `.pt`

**Check config.json**:
```json
"tracking": {
  "yolo_confidence": 0.4,
  "yolo_iou": 0.6,
  "yolo_obb": true
}
```

**Complete guide**: See [docs/TENSORRT_OPTIMIZATION.md](docs/TENSORRT_OPTIMIZATION.md)

---

### Database Locked Error

**Close connections**:
```bash
sqlite3 backend/data/data.db "PRAGMA busy_timeout = 5000;"
```

**Check if backend is running**:
```bash
# Mac
ps aux | grep "python.*main.py"

# PC
ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-status"
```

---

### Git Shows Modified config.json (Line Endings)

**Fix** (already configured via .gitattributes):
```bash
# .gitattributes forces LF for config.json
git add .gitattributes
git add config.json
git commit -m "fix: normalize line endings"
```

**Verify**:
```bash
git diff config.json  # Should show no changes if normalized
```

---

## 📊 Recent Changes (Last 30 Days)

**2026-01-21** - Analytics Chart UX Improvements (Date Display + Speed in Tooltip):
- ✅ **CustomXAxisTick for date display**: Shows date in amber when day changes, time otherwise
  - X-axis labels: "21 Jan" (amber, bold) at start of day or day change, "18:05" (normal) for other ticks
  - First event always shows date for immediate context
  - Current mode only (no downsampling, reliable tick logic)
  - Solves 7 previous failed attempts (tick sampling issue was due to Overview downsampling)
- ✅ **Speed field in tooltip**: Format "88 (70%)" - DCC raw value + percentage
  - Backend fix: `get_delta_t_events()` now extracts `speed` from JSON data
  - Frontend: Added `speed` field to chart data preparation (both fast/slow path)
  - Tooltip simplified: removed time display (already on X-axis), shows only Δt, status, gate, speed
- 📄 Commits: `378055c` (backend speed fix) → `6162f1a` (cleanup) → `9903a8c` (CustomXAxisTick)

**2026-01-21** - Session Idle Timeout Completion, Model Fallback, Auto_compensation Disable:
- ✅ **Session idle timeout remaining time**: Countdown display in logs (debug mode only)
  - Changed from "idle X min (threshold Y min)" to "idle X min (Z min remaining)"
  - More useful for monitoring, shows time to timeout instead of fixed threshold
- ✅ **Session idle checker task cancellation**: Fixed zombie checker on daemon stop
  - Bug: old checker task not cancelled on page reload → multiple checkers running
  - Fix: cancel `session_idle_check_task` in finally block (like listener/flush tasks)
- ✅ **Auto_compensation auto-disable**: When no YOLO model found (FileNotFoundError)
  - Disables auto_compensation for all consists (requires tracking, persisted to DB)
  - Virtual Mode still available (does not require tracking, cleaner than DCC mode)
  - Clear logs: what happened, why, and how to fix (add models to scripts/models/)
- ✅ **Model fallback**: Automatic .engine → .onnx → .pt with exception handling
  - Mac with PC's .engine: auto-fallback to .onnx (no CUDA, but 1.5-2x faster than .pt)
  - Robust: one failing model doesn't crash tracking daemon
  - If all fail/missing: FileNotFoundError → auto_compensation disabled
- ✅ **ONNX models on Mac**: Copied from PC (12 MB each, 1.5-2x faster than PyTorch)

**2026-01-21** - Speed Analysis Debug Panel, Weighted Algorithm, Session Idle Timeout:
- ✅ **Speed Analysis Debug Panel**: Collapsible panel in Speed Table Viewer (purple theme)
  - Shows ALL tested speeds (not just recommendations)
  - Current/Historical/Weighted breakdown per speed
  - Critical/warning count always visible: colored (red/amber) if >0, grey if =0
  - Excludes speed 0 (stopped locomotives)
  - Visible only when `debug.enabled=true`
  - Open by default but collapsible, positioned after speed table
- ✅ **Debug mode as local-only setting**: Like camera credentials
  - `config.json` always has `debug.enabled=false` (committed default)
  - `config.local.json` stores local override (gitignored)
  - Settings UI saves to config.local.json (preserves local overrides)
- ✅ **Debug mode log unification**:
  - Moved from yolo_tracker.py to main.py (application-wide)
  - ENABLED/DISABLED colored in yellow (STATUS_YELLOW) for high visibility
  - Appears immediately at backend startup
- ✅ **Session idle timeout**: Auto-close after N min without movement (config: `analytics.session_idle_timeout_minutes`, default 30)
  - Continuous movement = 1 session, long pauses = new session
  - Prevents zombie sessions, accurate session duration
  - Settings UI: Analytics tab (5-120 min, backend restart required)
  - Periodic check logs every 60s (debug mode only), close/open logs always visible
  - Architecture: `analytics_logger.close_session()` + new `AnalyticsLogger()`, updates global reference
- ✅ **Weighted algorithm improvements**:
  - **Removed CV modification filter**: Was per-locomotive (not per-CV), too aggressive
  - **Changed weights to 80/20**: From 70/30 (more reactive to corrections)
  - **Weight constants**: `WEIGHT_CURRENT_HIGH = 0.8`, `WEIGHT_CURRENT_LOW = 0.2`
  - **Rationale**: Weighted logic + last 5 sessions sufficient without CV filter
- ✅ **Critical fixes**:
  - Fixed `cv_last_modified` timestamp comparison bug (string vs Unix timestamp)
  - Fixed `get_validated_sessions()` to filter by consist_id
  - Fixed debug_info population for ALL speeds (even with total_count=0)
  - Fixed speed 0 exclusion in query (stopped locomotives)
  - Validated session fix: Speed Table uses latest validated session (not non-validated current)
- ✅ **Database debugging pattern**: Added to z21-deployment skill (PC → Mac copy workflow)
- 📄 Docs: Updated SPEED_TABLE_WEIGHTED_RECOMMENDATIONS.md (two-stage system, 80/20 weights), z21-deployment skill

**2026-01-20** - Weighted Speed Table Recommendations:
- ✅ Algorithm: 2-stage weighted averaging (session split + weighted mean, CV filter removed 2026-01-21)
- ✅ Config: recommendation_threshold per consist (C10: 5 asymmetric, C11: 10 symmetric)
- ✅ Backend: Complete refactor of get_critical_events_by_speed() (230 lines)
- ✅ Weight logic: Current session >= threshold → 70%, else 30% (historical complementary)
- ✅ CV modification filtering: Ignore events before last CV write
- ✅ UI: Inline breakdown under each recommendation (always visible)
- ✅ Example: "┗━ Current: 12 events, Δt +1.5s (70%) | Historical: 45 events, Δt -0.3s (30%)"
- 📄 Docs: SPEED_TABLE_WEIGHTED_RECOMMENDATIONS.md

**2026-01-20** - CV3/CV4 Editor:
- ✅ Settings UI: Inline editor for CV3 (Acceleration) and CV4 (Deceleration)
- ✅ Compact design in Locomotives tab, before Functions list
- ✅ Values saved to config.json, applied on hotkey T toggle
- 📄 Docs: CV3_CV4_EDITOR.md

**2026-01-20** - ESU mfx Decoder Support:
- ✅ Database: Added vstart/vhigh/decoder_type columns to locomotive_speed_table
- ✅ Backend: ESU decoder detection, CV67/CV94 write validation (read-only for ESU)
- ✅ API: New endpoint POST /api/speed-table/write-vstart-vhigh (CV2/CV5 for ESU)
- ✅ Frontend: Grey out step 1/28 for ESU, Vstart/Vhigh panel (ESU only)
- ✅ Migration: ONE-SHOT script migrated 7 locomotives (5 ESU, 2 NMRA)
- 📄 Docs: SPEED_TABLE_DECODER_BEHAVIOR.md

**v1.0.0** (2026-01-17) - JMRI Independence Achieved:
- ✅ Speed tables CV67-94 migrated to database (`locomotive_speed_table` table)
- ✅ Function labels F0-F28 moved to config.json (editable via Settings UI)
- ✅ Locomotive metadata unified in config.json (name, decoder, color, notes)
- ✅ Complete consist CRUD via web UI (Consist Manager)
- ✅ JMRI now optional (only for initial setup)

**2026-01-20** - Database Schema Documentation:
- ✅ Complete DATABASE_SCHEMA.md reference (tables, queries, event types)
- ✅ Camera config cleanup (camera_config.json → config.local.json)
- ✅ Database outlier cleanup (removed 3 false positive Δt events)

**2026-01-19** - Analytics Configuration:
- ✅ Configurable `max_chart_events` (100-2000, default 500)
- ✅ Settings UI: Analytics tab for performance tuning
- ✅ Config reorganization (sections reordered to match UI flow)
- ✅ Locomotives sorted by ID (1,2,4,5,6,7,8)

**2026-01-18** - Timing Thresholds Refactoring:
- ✅ Renamed `normal` → `warning` (1.0s), `warning` → `critical` (1.5s)
- ✅ Consistent 3-level system: SYNCED (<1.0s), WARNING (≥1.0s), CRITICAL (≥1.5s)

**2026-01-14** - Analytics Dashboard:
- ✅ Session tracking with lifecycle management
- ✅ Δt trends chart (Current vs Overview views)
- ✅ YOLO performance monitoring (FPS + confidence)
- ✅ Locomotive operating time tracking

**Complete history**: See [docs/CHANGELOG_ARCHIVE.md](docs/CHANGELOG_ARCHIVE.md)

---

## 🔮 Future Enhancements

### Quick Wins (1-2 Days)
- **Motor Load Monitoring** (Phase 9): Z21 track-level telemetry (current, voltage, temperature)
- **Telegram/Email Notifications**: Critical event alerts (derailment, Δt > 2.0s, backend crash)
- **Function Test Mode**: Cycle F0-F28 automatically to verify decoder responses

### Medium Effort (3-5 Days)
- **Session Replay Mode**: Playback stored events with timeline scrubber
- **Consist Lock Mechanism**: Prevent control conflicts with multiple devices
- **Decoder Health Monitoring**: Periodic CV read (CV2, CV5, CV19, CV29) to detect drift

### Large Projects (1-2 Weeks)
- **Track Occupancy Map** (Phase 7 - postponed): Real-time locomotive positions on SVG track layout
- **Virtual Stations & Routes**: Gate-based triggers for automatic stops and scheduled operations
- **Spectator Mode**: View-only access for visitors (no controls, read-only dashboard)

### External Dependencies
- **Motor Load Monitoring**: Requires RailCom support (Z21 Pro or compatible decoder)
- **Track Power Telemetry**: Requires Z21 Pro or similar (voltage/current monitoring)

**Complete list**: See [docs/FUTURE_IDEAS.md](docs/FUTURE_IDEAS.md)

---

## 📁 Critical Files Reference

### Backend Core
- `backend/main.py` - FastAPI app entry point (742 lines, minimal delegation)
- `backend/dependencies.py` - Global state DI (Z21, WebSocket manager, config)
- `backend/routers/config.py` - Settings API (/api/settings/update, /api/config)
- `backend/routers/analytics.py` - Analytics API (/api/analytics/*)
- `backend/tracking_daemon.py` - Headless YOLO tracking daemon
- `backend/tracking/yolo_tracker.py` - YOLOTracker class (model loading, inference, gate detection)
- `backend/tracking/rtsp_handler.py` - RTSP stream utilities (load_camera_config, setup_rtsp_stream)
- `scripts/z21.py` - Z21 LAN protocol library (UDP commands, XpressNet encoding)
- `backend/config_loader.py` - Config loading (load_config, save_config, deep_merge)

### Frontend Core
- `web/src/App.jsx` - Main React component
- `web/src/components/ConsistController.jsx` - Locomotive controller UI
- `web/src/components/Analytics.jsx` - Analytics dashboard
- `web/src/components/SettingsModal.jsx` - Settings UI (8 tabs)
- `web/src/components/ConsistManagerModal.jsx` - Consist CRUD UI

### Configuration
- `config.json` - Central configuration (committed to git)
- `config.local.json` - Local overrides (gitignored, credentials)

### Database
- `backend/data/data.db` - SQLite database (auto-created, gitignored)

### Documentation
- `docs/DATABASE_SCHEMA.md` - Complete database schema reference
- `docs/COMPUTER_VISION.md` - YOLO training + gate timing detection
- `docs/JMRI_INTEGRATION.md` - JMRI relationship + independence roadmap
- `~/.claude/skills/z21-deployment/SKILL.md` - Deployment workflow + critical rules

---

**End of CLAUDE.md**
