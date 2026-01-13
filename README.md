# z21-Terminal

Web-based DCC locomotive controller with real-time YOLO tracking, automatic speed compensation, and multi-device sync via Z21 LAN protocol.

**Project**: DCC Model Railway - BiancAlice

## Project Structure

```
z21-Terminal/
├── README.md          # This file
├── scripts/           # Python scripts (terminal controller, YOLO tracking, utilities)
├── backend/           # FastAPI backend + WebSocket + Z21Manager + Tracking Daemon
│   └── data/          # SQLite database for analytics (gitignored, auto-created)
├── web/               # React frontend (Vite + Tailwind CSS)
├── config.json        # Central configuration (consists, gates, thresholds, debug)
└── camera_config.json # Camera credentials (gitignored)
```

## Relationship with JMRI

**z21-Terminal started as a JMRI extension, now increasingly independent.**

- **JMRI is optional**: z21-Terminal can manage consists directly via web UI
  - Initial roster configuration can be imported from JMRI XML files
  - **Consist management**: Create/edit/delete consists via web dashboard (no JMRI needed)
  - **CV19 management**: Automatic DCC/Virtual mode toggle (no programming track needed)
  - JMRI does not need to be running
- **Coexistence**: Both systems can control locomotives simultaneously (if both installed)
- **Complementarity** (if using JMRI):
  - **JMRI**: Decoder configuration (DecoderPro), initial roster setup, programming track operations
  - **z21-Terminal**: Operational control, modern web UI, consist CRUD, YOLO tracking, automated compensation

**Typical workflow**:
1. (Optional) Import initial roster from JMRI, OR configure locomotives manually
2. Manage consists directly in z21-Terminal web dashboard
3. Use z21-Terminal for all operational control (tracking, compensation, multi-device sync)

## Setup

### Requirements
- **Control Station**: Roco Z21 (White, Black, or Pro) connected to your network
- **Network**: Z21 and computer on same network (or accessible via VPN/Tailscale)
- **Optional**: JMRI (for initial roster import or decoder programming)
- **Optional**: IP camera with RTSP support for YOLO tracking (Tapo camera tested)

### Hardware Setup
- **Z21**: Roco Z21 White (IP 192.168.1.111, firmware 1.67)
- **Camera** (optional): Tapo IP camera for YOLO tracking (720P RTSP stream)
- **Locomotives**: 7 locomotives configured with 2 consists (dual-track operations)
- **GPU** (optional): NVIDIA RTX 2060 for TensorRT acceleration (2-5x faster inference)

## Main Usage

### Web Dashboard 🌐
Modern web interface for locomotive control (mobile-first, multi-device, PWA):

#### macOS (Development)
```bash
z21              # Start backend + frontend (2 iTerm tabs, daemon auto-managed)
z21-backend      # Start only backend (FastAPI + WebSocket)
z21-frontend     # Start only frontend (Vite dev server)
```

Access at: **http://localhost:5173** (or network: `http://192.168.1.xxx:5173`)

#### Windows PC (Production - PowerShell)
```powershell
z21-deploy       # Full deployment: git pull + stop backend + build frontend
z21-start        # Start backend in background (hidden window, persists after SSH close)
z21-restart      # Restart backend (stop + start)
z21-stop         # Stop backend
z21-status       # Check if backend is running (port 8000 listen check)
z21-backend      # Interactive mode (see logs real-time, Ctrl+C to stop - no Y/N prompt)
z21-frontend     # Start frontend dev server
```

**Command Flow Diagram**:
```
┌─────────────────────────────────────────────────────────────┐
│                    PC Windows Production                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1️⃣  First Time Setup / Full Deployment                     │
│      z21-deploy  →  [git pull + stop + build] → z21-start   │
│                                                              │
│  2️⃣  Backend Updates (code changes)                         │
│      git pull  →  z21-restart                                │
│                                                              │
│  3️⃣  Frontend Updates (UI changes)                          │
│      z21-deploy  →  z21-start                                │
│                                                              │
│  4️⃣  Development/Debug                                       │
│      z21-backend  (interactive, see logs, Ctrl+C to stop)    │
│                                                              │
│  5️⃣  Stop Production Backend                                 │
│      z21-stop                                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Access**:
- Local: **http://localhost:8000** (production mode - FastAPI serves frontend dist/)
- Tailscale: **https://gaming-pc.tail9350d7.ts.net** (remote access via VPN)

**Core Features:**
- **Consist Manager**: Create/edit/delete consists via web UI (CRUD operations, no JMRI needed)
- **Scalable UI**: Dynamic controller panels with [+] button (add/remove controllers on-the-fly)
- **Virtual Consist Mode**: Automatic CV19 management + real-time speed compensation based on Δt
- **CV Profiles**: One-click TEST/NORMAL toggle (hotkey T) for instant speed matching across all locomotives (~1.2s)
- **Analytics Dashboard**: Session tracking with real-time charts (keyboard shortcut: A)
  - Session statistics (duration, gate crossings, critical events)
  - Δt trends visualization (speed matching quality over time)
  - YOLO performance monitoring (FPS + detection confidence per locomotive)
  - Locomotive operating time tracking (maintenance planning)
  - Current vs Overview views (session-specific vs cumulative historical data)
- **Touch-optimized**: Speed slider with 200ms throttling, 48px touch targets, responsive hamburger menu
- **Real-time sync**: WebSocket multi-device support (iPad + Phone + Laptop simultaneously)
- **PWA**: Installable on iPad/iPhone home screen (standalone app experience)
- **Wake Lock API**: Prevent screen sleep on mobile during operations (iOS/Android)
- **Emergency stop**: ESC keyboard shortcut + audio feedback
- **Function control**: F0-F28 with color-coded indicators (lockable/momentary, auto-release 800ms)
- **Z21 health monitoring**: 5s polling with 2-failure grace period (eliminates false positives)
- **Elegant UI**: "Control Room Noir" dark theme, Font Awesome 6 icons

### YOLO Tracking System 🎯
Real-time locomotive tracking via IP camera with automatic speed compensation:

**Features:**
- **YOLO Object Detection**: Custom YOLOv8 nano OBB model trained on 4 locomotives (mAP50 = 91.7%)
  - TensorRT GPU acceleration (2-5x faster inference, <0.5s bbox lag)
  - Oriented bounding boxes for accurate overlap handling
- **Gate Timing Detection**: Symmetric (oval track) and asymmetric (figure-8 track) timing modes
- **Multi-Consist Support**: Config-driven tracking (supports N consists via `config.json`)
- **Speed Compensation**: Automatic Δt-based compensation in Virtual Mode (bang-bang + decay)
- **Video Feed**: Real-time MJPEG stream with gate overlay + Δt stats panel
- **Dynamic FPS**: 30 FPS active tracking, 1 FPS idle (auto-switches based on movement)

**Usage:**
- Tracking daemon auto-starts when frontend connects (managed by TrackingManager)
- Video feed accessible at `/api/video_feed` (gate markers + Δt panels overlay)
- Console logs show: 🚪 Δt updates, 🎯 Virtual Mode speeds, 🎚️ Compensations

**Technical Details:**
- **Model**: YOLOv8 nano (6MB) trained on 137 images
- **Classes**: DCC address as prefix (e.g., `7_E656_239`, `8_E444_056`)
- **Gates**: Rectangular zones (configurable position/size in `config.json`)
- **Thresholds**: SYNCED < 1.0s, WARNING < 1.5s (configurable)

### Terminal Controller ⌨️ (Optional CLI Utility)
Interactive keyboard control for CLI enthusiasts:

```bash
cd scripts/

# Interactive Z21 controller
python3 z21_controller.py               # Interactive loco selection
python3 z21_controller.py 1             # Control loco address 1
python3 z21_controller.py 10            # Control consist 10
```

## Installation

### Requirements
- Python 3.8+ with required packages (see `requirements.txt`)
- Node.js 18+ and npm (for frontend build)
- NVIDIA GPU with CUDA support (optional, for TensorRT acceleration)
- Z21 control station on the same network

### Quick Start
1. Clone repository: `git clone git@github.com:rizal72/z21-Terminal.git`
2. Install Python dependencies: `pip install -r requirements.txt`
3. Install frontend dependencies: `cd web && npm install`
4. Configure `config.json` and `camera_config.json` (if using YOLO tracking)
5. Start backend: `python backend/main.py`
6. Start frontend: `cd web && npm run dev` (development) or `npm run build` (production)

## Features

### Web Dashboard ✅
- [x] Modern web UI (Vite + React + Tailwind CSS + Font Awesome 6)
- [x] FastAPI backend with WebSocket real-time sync
- [x] **Consist Manager**: CRUD operations via web UI (create/edit/delete consists, gate assignment)
- [x] **Scalable UI**: Dynamic controller panels with [+] button
- [x] **Mobile Header**: Responsive hamburger menu (<768px)
- [x] Flexible roster selection (consists + standalone locomotives)
- [x] Touch-optimized controls (mobile-first design, 48px touch targets)
- [x] Speed control slider with 200ms throttling
- [x] Direction toggle (forward/reverse)
- [x] Functions F0-F28 with state indicators (lockable/momentary)
- [x] Global emergency stop (ESC keyboard + audio feedback)
- [x] Multi-device support (iPad, phone, desktop)
- [x] Track power polling (500ms) with auto-sync
- [x] Z21 connection health monitoring (5s polling)
- [x] **PWA**: Installable on iPad/iPhone home screen
- [x] **Wake Lock API**: Prevent screen sleep on mobile
- [x] Tailscale HTTPS support (permanent, persists after reboot)
- [x] Safari Mac animation compatibility

### YOLO Tracking System ✅
- [x] **YOLO Custom Training**: YOLOv8 nano OBB model trained on 4 locomotives (mAP50 = 91.7%)
- [x] **TensorRT Acceleration**: GPU-optimized inference (2-5x faster, <0.5s bbox lag)
- [x] **Oriented Bounding Boxes**: Accurate overlap handling with rotated bboxes
- [x] **Gate Timing Detection**: Symmetric (oval) and asymmetric (figure-8) timing modes
- [x] **Multi-Consist Support**: Config-driven tracking (supports N consists)
- [x] **Video Feed**: Real-time MJPEG stream with gate overlay + Δt stats panels
- [x] **Dynamic FPS Control**: 30 FPS active, 1 FPS idle (auto-switches on movement)
- [x] **WebSocket Streaming**: Δt updates broadcast to all connected clients
- [x] **Frame Queue Sharing**: Single RTSP capture, dual consumers (daemon + video feed)
- [x] **Timing Thresholds**: Configurable SYNCED/WARNING thresholds

### Virtual Consist Mode ✅
- [x] **Automatic CV19 Management**: Toggle DCC/Virtual mode via UI (writes CV19=0 or CV19=consist_address)
- [x] **Speed Compensation**: Real-time Δt-based adjustment (bang-bang control)
- [x] **Decay Mechanism**: One-shot proportional decay in SYNCED zone
- [x] **Reference Loco Strategy**: Config-driven (never touch reference loco, adjust only unstable loco)
- [x] **Transparent UX**: Single slider, dual locomotive control behind the scenes
- [x] **Auto-Compensation Toggle**: Enable/disable compensation per consist (UI switch)

### Analytics Dashboard ✅
- [x] **Session Tracking**: Automatic session lifecycle (first Δt validates session, page close ends session)
- [x] **Session Statistics**: Duration, gate crossings, critical events (|Δt| ≥ 1.5s)
- [x] **Δt Trends Chart**: Speed matching quality visualization over time (line chart with color-coded thresholds)
- [x] **YOLO Performance Monitoring**: FPS trends (line chart) + confidence per locomotive (bar chart)
- [x] **Locomotive Operating Time**: Cumulative operating hours per locomotive (maintenance planning)
- [x] **Current vs Overview Views**: Session-specific vs cumulative historical data
- [x] **Consist Filtering**: Filter charts by All/C10/C11 (color-coded, sticky header)
- [x] **Intelligent Downsampling**: LTTB algorithm preserves chart shape, critical events (|Δt| ≥ 1.5s) always visible
- [x] **Horizontal Scroll**: Navigate large datasets (1000+ events) with smooth scrolling
- [x] **Auto-Refresh**: Current view updates every 10s when locomotives moving
- [x] **SQLite Async Logging**: Zero impact on YOLO tracking (buffered writes)

### CV Operations (Operations Mode) ✅
- [x] **CV Write**: Write CV while locomotives running (XpressNet E6 30 command)
- [x] **CV Read**: Read CV from decoder (verify trick, ESU only, Hornby not supported)
- [x] **Tested Decoders**: ESU LokPilot/LokSound ✅, Hornby TXS (write only) ✅
- [x] **Use Cases**: Virtual Mode CV19 toggle, CV Profiles (TEST/NORMAL mode)
- [x] **CV Profiles**: Global TEST/NORMAL toggle (hotkey T) for instant speed matching
  - Writes CV3/CV4 on all locomotives (~1.2s total)
  - Badge indicator (Flask = TEST, Check = NORMAL)
  - Config-driven profiles tracked in config.json

### Debug Mode ✅
- [x] **Production Clean Logs**: Only critical operational events visible by default
- [x] **Configurable**: Toggle via `config.json` (`debug.enabled: true/false`)
- [x] **Always Visible**: 🚪 Δt, 🎯 speeds, 🎚️ compensations, 🔄 mode switches, ⚠️ warnings
- [x] **Debug Only**: ✓ startup logs, 🚦 gate details, 📊 session summary

### Z21 Library ✅
- [x] Complete Z21 LAN protocol (UDP)
- [x] Locomotive movement control
- [x] Functions F0-F28 control
- [x] Read locomotive state (speed, direction, functions)
- [x] Emergency stop and power control
- [x] Operations mode CV write/read (tested on ESU + Hornby decoders)
- [x] Coexistence with JMRI

### Utilities ✅
- [x] Read CV from JMRI roster (XML files)
- [x] View configured consists
- [x] YOLO training scripts (dataset creation, annotation, training)

### Future Enhancements ⏳
- [ ] **Phase 7: Track Occupancy Map** (Postponed): Real-time locomotive positions on SVG track layout
  - Complete implementation plan available in `docs/TRACK_MAP_IMPLEMENTATION.md`
  - Perspective transform (camera → orthogonal), SVG rendering, tunnel interpolation
  - Postponed: Video feed with debug overlay already sufficient
  - Revisit if advanced visualization becomes necessary

- [ ] **Phase 8: Auto CV Adjust** (Very Low Priority): Permanent CV tuning based on Δt statistics
  - Virtual Mode already provides real-time compensation
  - Revisit only if speed matching degrades significantly over time

- [ ] **Phase 9: Motor Load Monitoring** (Quick Win - 1-2 hours): Z21 track-level telemetry
  - Extend `z21.py` to parse existing Z21 telemetry (current, voltage, temperature)
  - Backend API endpoint for telemetry data
  - Track power quality monitoring, preventive maintenance alerts
  - Complete technical analysis in `docs/MOTOR_LOAD_MONITORING.md`
  - Phase 2-3 (RailCom Plus) conditional on Z21 White compatibility verification

## Configuration

### config.json
Central configuration file (project root):

```json
{
  "debug": {
    "enabled": false                 // Production: false, Verbose logs: true
  },
  "consists": {                      // Consist definitions (unified structure)
    "10": {
      "name": "Consist 10 - Internal Track",
      "lead_address": 1,
      "rear_address": 5,
      "reference_loco": 5,           // Never touch (stable decoder)
      "adjust_loco": 1,              // Speed compensation target
      "gate_ids": [3, 4],
      "gate_assignment": {           // Asymmetric mode (figure-8)
        "reference": 3,
        "adjust": 4
      },
      "virtual_mode": true,
      "auto_compensation_enabled": true
    },
    "11": {
      "name": "Consist 11 - External Track",
      "lead_address": 7,
      "rear_address": 8,
      "reference_loco": 8,
      "adjust_loco": 7,
      "gate_ids": [1, 2],
      "gate_assignment": null,       // Symmetric mode (oval)
      "virtual_mode": true,
      "auto_compensation_enabled": true
    }
  },
  "gates": [...],                    // Gate definitions (position, size, color)
  "tracking": {
    "fps": {                         // Dynamic FPS control
      "active": 30,
      "idle": 1
    },
    "timing_thresholds": {           // Δt thresholds
      "normal": 1.0,
      "warning": 1.5,
      "max_delta_t": 15.0
    },
    "yolo_imgsz": 640                // YOLO inference size (640 square, or [640,1152] rect)
  }
}
```

### camera_config.json
Camera credentials (gitignored):

```json
{
  "camera_ip": "192.168.1.4",
  "camera_port": 554,
  "stream": "stream2",
  "username": "your_username",
  "password": "your_password"
}
```

## Deployment Architecture

### Development Mode (macOS)
- **Environment**: Mac + iTerm2
- **Backend**: Port 8000 (API only)
- **Frontend**: Port 5173 (Vite dev server with HMR)
- **Features**: Hot module replacement, debug logs, fast iteration
- **Command**: `z21` (starts both in iTerm tabs)

### Production Mode (Windows PC)
- **Environment**: Windows PC + PowerShell + GPU (NVIDIA RTX 2060)
- **Backend**: Port 8000 (API + serves frontend dist/)
- **Frontend**: Built static files (web/dist/) served by FastAPI
- **Features**: TensorRT GPU acceleration (2-5x faster inference), optimized bundle, Tailscale HTTPS
- **Commands**: `z21-deploy` (build) + `z21-start` (run in background)
- **Performance**: 50-130 FPS YOLO inference (vs 30 FPS CPU target)

**Key Differences**:
| Aspect | macOS (Dev) | Windows PC (Prod) |
|--------|-------------|-------------------|
| Port | 5173 (frontend) + 8000 (backend) | 8000 (unified) |
| Frontend | Vite dev server | Static dist/ bundle |
| YOLO | CPU (slow) | GPU (fast) |
| Process | Foreground (Ctrl+C stops) | Background (persists after SSH close) |
| Log visibility | Console output | C:\z21-Terminal\backend.log |

## Notes

- **Consist Management**:
  - **Web UI**: Create/edit/delete consists directly in z21-Terminal (no JMRI needed)
  - **JMRI Integration** (optional): Can import initial roster from JMRI XML files
  - CV19 management handled automatically (DCC/Virtual mode toggle)
- **Speed Matching**:
  - **Virtual Mode**: Real-time compensation based on Δt feedback (session-based, no CV writes)
  - **CV Profiles**: Press **T** to toggle TEST/NORMAL mode for instant speed response (CV3/CV4 written on all locos)
    - **TEST mode**: CV3≈0, CV4≈0 (instant response for testing/tuning)
    - **NORMAL mode**: CV3/CV4 restored (realistic acceleration/deceleration)
    - ⚠️ **Important**: Press **T** to return to NORMAL before closing app or deploying (avoid CV misalignment)
  - **Manual tuning** (optional): JMRI speed tables (CV67-94) for permanent adjustments
  - **Auto CV Adjust**: Low priority (Virtual Mode already compensates in real-time)
- **Z21 Protocol**:
  - Direct Z21 LAN control (UDP port 21105) ✅
  - Tested on Z21 White (compatible with Z21 Black/Pro)
  - Operations mode CV write/read implemented (no programming track needed)
  - Coexists with JMRI if both installed (last command has priority)
- **YOLO Training**:
  - DCC address MUST be class prefix (e.g., `7_E656_239`)
  - ⚠️ **NEVER change CV1 after training** (breaks class mapping)
  - Re-training required if DCC addresses change
- **Browser Compatibility**: Optimized for Safari Mac, Chrome Mac, iOS Safari, and Android Chrome
- **Debug Mode**: Set `debug.enabled: true` in `config.json` for verbose startup/runtime logs
- **PowerShell Aliases** (Windows PC): All z21-* commands are PowerShell functions (no .bat files)
  - Located in: `$PROFILE` (`C:\Users\Riccardo\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`)
  - Reload profile: `. $PROFILE` (after modifications)

## License

Private project - All rights reserved
