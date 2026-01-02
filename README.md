# z21-Terminal

Interactive terminal controller for DCC locomotives via Z21 LAN protocol with advanced YOLO-based tracking and automatic speed compensation.

**Project**: DCC Model Railway - BiancAlice

## Project Structure

```
z21-Terminal/
├── README.md          # This file
├── scripts/           # Python scripts (terminal controller, YOLO tracking, utilities)
├── backend/           # FastAPI backend + WebSocket + Z21Manager + Tracking Daemon
├── web/               # React frontend (Vite + Tailwind CSS)
├── docs/              # Technical documentation (Z21 protocol, JMRI integration, phases)
├── config.json        # Central configuration (gates, thresholds, reference locos, debug)
└── camera_config.json # Camera credentials (gitignored)
```

## Relationship with JMRI

**z21-Terminal is an extension of JMRI, not a replacement.**

- **JMRI is required**: z21-Terminal reads roster and consists from JMRI XML files
  - Your specific roster configuration lives in JMRI
  - z21-Terminal dynamically loads functions, consists, and locomotive data
  - JMRI does not need to be running (only XML files are read)
- **Coexistence**: Both systems can control locomotives simultaneously
- **Complementarity**:
  - **JMRI**: Decoder configuration (DecoderPro), programming track, roster/consist management
  - **z21-Terminal**: Fast operational control, modern web UI, YOLO tracking, automated compensation

**Typical workflow**:
1. Configure locomotives and consists in JMRI (DecoderPro)
2. Use z21-Terminal for operational control (web dashboard with real-time tracking)
3. Both software can remain open and work together (last command has priority)

## Setup

### Requirements
- **Control Station**: Roco Z21 (White, Black, or Pro) connected to your network
- **Software**: JMRI installed with configured roster (does not need to be running)
- **Network**: Z21 and computer on same network (or accessible via VPN/Tailscale)
- **Optional**: IP camera with RTSP support for YOLO tracking (Tapo camera tested)

### Hardware Setup
- **Z21**: Roco Z21 White (IP 192.168.1.111, firmware 1.67)
- **Camera** (optional): Tapo IP camera for YOLO tracking (720P RTSP stream)
- **Locomotives**: 7 locomotives configured with 2 consists (dual-track operations)

## Main Usage

### Web Dashboard 🌐
Modern web interface for locomotive control (mobile-first, multi-device, PWA):

```bash
z21              # Start backend + frontend + tracking daemon (3 iTerm tabs)
z21-backend      # Start only backend (FastAPI + WebSocket)
z21-frontend     # Start only frontend (Vite dev server)
```

Access at: **http://localhost:5173** (or network: `http://192.168.1.xxx:5173`)
**Tailscale HTTPS**: `https://mbp16diriccardo.tail9350d7.ts.net` (permanent, persists after reboot)

**Core Features:**
- **Scalable UI**: Dynamic controller panels with [+] button (add/remove controllers on-the-fly)
- **Virtual Consist Mode**: Automatic CV19 management + real-time speed compensation based on Δt
- **Touch-optimized**: Speed slider with 200ms throttling, 48px touch targets
- **Real-time sync**: WebSocket multi-device support (iPad + Phone + Laptop simultaneously)
- **PWA**: Installable on iPad/iPhone home screen (standalone app experience)
- **Wake Lock API**: Prevent screen sleep on mobile during operations (iOS/Android)
- **Emergency stop**: ESC keyboard shortcut + audio feedback
- **Function control**: F0-F28 with color-coded indicators (lockable/momentary, auto-release 800ms)
- **Z21 health monitoring**: 5s polling with online/offline status
- **Elegant UI**: "Control Room Noir" dark theme, Font Awesome 6 icons

### YOLO Tracking System 🎯
Real-time locomotive tracking via IP camera with automatic speed compensation:

**Features:**
- **YOLO Object Detection**: Custom YOLOv8 nano model trained on 4 locomotives (mAP50 = 80.7%)
- **Gate Timing Detection**: Cross-gate co-presence timing with dual-gate validation
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

### Terminal Controller ⌨️
Interactive keyboard control:

```bash
cd ~/Documents/_PROGETTI/z21-Terminal/scripts

# Interactive Z21 controller
python3 z21_controller.py               # Interactive loco selection
python3 z21_controller.py 1             # Control loco address 1
python3 z21_controller.py 10            # Control consist 10
```

## Features

### Web Dashboard ✅
- [x] Modern web UI (Vite + React + Tailwind CSS + Font Awesome 6)
- [x] FastAPI backend with WebSocket real-time sync
- [x] **Scalable UI**: Dynamic controller panels with [+] button (Phase 1 complete)
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

### YOLO Tracking System ✅ (Phases 3-5 Complete)
- [x] **YOLO Custom Training**: YOLOv8 nano model trained on 4 locomotives
- [x] **Gate Timing Detection**: Cross-gate co-presence timing with dual-gate validation
- [x] **Multi-Consist Support**: Config-driven tracking (supports N consists)
- [x] **Video Feed**: Real-time MJPEG stream with gate overlay + Δt stats panels
- [x] **Dynamic FPS Control**: 30 FPS active, 1 FPS idle (auto-switches on movement)
- [x] **WebSocket Streaming**: Δt updates broadcast to all connected clients
- [x] **Frame Queue Sharing**: Single RTSP capture, dual consumers (daemon + video feed)
- [x] **Timing Thresholds**: Configurable SYNCED/WARNING thresholds

### Virtual Consist Mode ✅ (Phase 4B Complete)
- [x] **Automatic CV19 Management**: Toggle DCC/Virtual mode via UI (writes CV19=0 or CV19=consist_address)
- [x] **Speed Compensation**: Real-time Δt-based adjustment (bang-bang control)
- [x] **Decay Mechanism**: One-shot proportional decay in SYNCED zone (Phase 4C)
- [x] **Reference Loco Strategy**: Config-driven (never touch reference loco, adjust only unstable loco)
- [x] **Transparent UX**: Single slider, dual locomotive control behind the scenes
- [x] **Auto-Compensation Toggle**: Enable/disable compensation per consist (UI switch)

### CV Operations (Operations Mode) ✅
- [x] **CV Write**: Write CV while locomotives running (XpressNet E6 30 command)
- [x] **CV Read**: Read CV from decoder (verify trick, ESU only, Hornby not supported)
- [x] **Tested Decoders**: ESU LokPilot/LokSound ✅, Hornby TXS (write only) ✅
- [x] **Use Case**: Virtual Mode CV19 toggle (automatic, no programming track needed)

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
- [ ] **Consist Manager UI**: CRUD operations for consists (Phase 6)
  - Create/Edit/Delete consists via web UI
  - Gate assignment per consist
  - Single loco support (rear_address = null)
  - Eliminate JMRI dependency for consist management
- [ ] **Mobile Header Refactor**: Hamburger menu for mobile (<768px)
- [ ] **Consist 10 Tracking**: Configure gates for internal track (figura 8)
- [ ] **Auto CV Adjust** (Nice to Have): Permanent CV tuning based on Δt statistics
  - Low priority: Virtual Mode already provides real-time compensation
  - Revisit only if speed matching degrades over time

## Documentation

Complete technical documentation in `/docs`:

- **[Z21_PROTOCOL.md](docs/Z21_PROTOCOL.md)**: Z21 LAN protocol specification (UDP, XpressNet)
- **[JMRI_INTEGRATION.md](docs/JMRI_INTEGRATION.md)**: Relationship with JMRI (complementary, not replacement)
- **[CHANGELOG_ARCHIVE.md](docs/CHANGELOG_ARCHIVE.md)**: Historical changelog (2025-12-16 → 2025-12-27)
- **[PHASE5_CONSIST_TRACKING.md](docs/PHASE5_CONSIST_TRACKING.md)**: Multi-consist tracking refactor details

## Configuration

### config.json
Central configuration file (project root):

```json
{
  "gates": [...],                    // Gate definitions (position, size)
  "timing_thresholds": {             // Δt thresholds
    "normal": 1.0,                   // SYNCED threshold (seconds)
    "warning": 1.5,                  // WARNING threshold (seconds)
    "max_delta_t": 15.0              // Sanity check (ignore outliers)
  },
  "reference_locos": {               // Reference loco strategy
    "11": {"reference": 8, "adjust": 7},
    "10": {"reference": 5, "adjust": 1}
  },
  "tracking_assignments": {          // Multi-consist tracking
    "11": {
      "lead_address": 7,
      "rear_address": 8,
      "gate_ids": [1, 2]
    },
    "10": {
      "lead_address": 1,
      "rear_address": 5,
      "gate_ids": [3, 4]
    }
  },
  "tracking_fps": {                  // Dynamic FPS control
    "active": 30,
    "idle": 1
  },
  "debug": {                         // Debug mode
    "enabled": false
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

## Notes

- **Roster Management**: Configure your locomotives in JMRI DecoderPro
  - z21-Terminal automatically loads roster from JMRI XML files
  - Supports individual locomotives and consists (DAC software-based)
- **Speed Matching**:
  - Manual tuning via JMRI speed tables (CV67-94)
  - Virtual Mode provides real-time compensation (session-based)
  - Auto CV Adjust planned for future (permanent tuning)
- **Z21 Protocol**:
  - Direct Z21 LAN control (UDP port 21105) ✅
  - Tested on Z21 White (compatible with Z21 Black/Pro)
  - Operations mode CV write/read implemented (no programming track needed)
  - Coexists with JMRI: both can control locomotives simultaneously
- **YOLO Training**:
  - DCC address MUST be class prefix (e.g., `7_E656_239`)
  - ⚠️ **NEVER change CV1 after training** (breaks class mapping)
  - Re-training required if DCC addresses change
- **Browser Compatibility**: Optimized for Safari Mac, Chrome Mac, iOS Safari, and Android Chrome
- **Debug Mode**: Set `debug.enabled: true` in `config.json` for verbose startup/runtime logs

## License

Private project - All rights reserved
