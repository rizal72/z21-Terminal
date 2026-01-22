# Settings UI - Unified Configuration Design

**Status**: ✅ **IMPLEMENTED** (Settings UI with 8 tabs + Auto-Reload)
**Date**: 2025-01-18 (Updated: 2025-01-19)
**Objective**: Unify ALL configuration settings into single `config.json` + comprehensive Settings UI
**Version**: 1.0.0

---

## 📋 Executive Summary

**Problem**: Configuration fragmented across 3 locations:
- ✅ `config.json` - tracking, consists, gates, locomotives (well structured)
- ❌ `camera_config.json` - camera credentials (separate file)
- ❌ Hardcoded - Z21 IP/port in `main.py:318` and `z21_manager.py:34`

**Solution**:
1. **Unify ALL settings** into single `config.json` with semantic hierarchy
2. **Build comprehensive Settings UI** with 7 tabs covering system configuration
3. **Security-conscious design** for camera credentials (via config.local.json override)
4. **Intelligent restart detection** - only restart affected services
5. **Migration path** from current state to unified config

**What Settings UI Manages**:
- ✅ **System settings** (debug mode)
- ✅ **Network settings** (Z21 IP/port, camera RTSP)
- ✅ **Model settings** (YOLO confidence/IoU/OBB with preset profiles)
- ✅ **Tracking settings** (FPS, idle timeout, timing thresholds)
- ✅ **Locomotive function labels** (inline edit F0-F28)

**What's Already Managed Elsewhere**:
- ✅ **Gate Editor** (hotkey 'E') - position/size/angle/color (visual editing)
- ✅ **Consist Manager** (fa-link button) - CRUD consists + gate_ids assignment
- ✅ **Test Mode** (badge 'T' header) - CV3/CV4 normal ↔ testing (stored in DB)

**What Remains Manual** (for now):
- ⏳ Locomotive name/decoder/color (manual config.json edit)
- ⏳ Gate-to-consist asymmetric assignment (will be added to Consist Manager)

**Impact**:
- ✅ One source of truth for all settings
- ✅ User-friendly web UI for common configuration tasks
- ✅ Reduced manual config.json editing
- ✅ Quick model switching with preset profiles (OBB ↔ Standard)
- ✅ Function label localization (rename "light" → "luci", etc.)

---

## 🎯 Design Goals

1. **Unification**: ALL settings in one place (`config.json`)
2. **Usability**: Web UI for all common configuration tasks
3. **Security**: Camera credentials remain gitignored (via config.local.json override pattern)
4. **Semantic Structure**: Logical grouping of related settings
5. **Backward Compatibility**: Gradual migration, no breaking changes
6. **Smart Restarts**: Context-aware service restart notifications

---

## 📁 Proposed Unified config.json Structure

### Final Structure (Target State)

```json
{
  "system": {
    "debug": {
      "enabled": false,
      "notes": "Debug mode: false = only important logs, true = verbose frame processing"
    }
  },

  "z21": {
    "host": "192.168.1.111",
    "port": 21105,
    "notes": "Roco Z21 Bianca hardware controller (Serial 111466, Firmware 1.67)"
  },

  "camera": {
    "ip": "192.168.1.4",
    "port": 554,
    "stream": "stream2",
    "resolution": {
      "width": 1280,
      "height": 720
    },
    "username": "",
    "password": "",
    "notes": "Tapo IP camera RTSP stream (stream2 = 720p). Credentials MUST be in config.local.json (gitignored)"
  },

  "video": {
    "fps": 30,
    "notes": "MJPEG video stream frame rate (independent from tracking FPS)"
  },

  "yolo": {
    "model": "best_obb",
    "confidence": 0.3,
    "iou": 0.6,
    "imgsz": 640,
    "obb": true,
    "device": "cuda",
    "notes": "YOLO model: best_obb.engine (TensorRT GPU), confidence 0.0-1.0, IoU for NMS, imgsz 640 for square"
  },

  "tracking": {
    "fps": {
      "active": 30,
      "idle": 1,
      "notes": "Tracking daemon FPS: 30 when moving, 1 when idle (all locos stopped)"
    },
    "idle_timeout_seconds": 10,
    "timing_thresholds": {
      "normal": 1.0,
      "warning": 1.5,
      "max_delta_t": 10.0,
      "notes": "Gate timing thresholds (seconds): |Δt| < normal = SYNCED, warning = CRITICAL, > max = outlier"
    }
  },

  "consists": {
    "10": { "name": "C10 Interno", "lead_address": 1, "rear_address": 5, ... },
    "11": { "name": "C11 Esterno", "lead_address": 7, "rear_address": 8, ... }
  },

  "gates": [
    { "id": 1, "name": "Gate 1", "center": [995, 27], "width": 65, "height": 43, ... }
  ],

  "locomotives": {
    "1": { "name": "Gr.675 017", "decoder": "LokSound V4.0", "color": "#FFFF00", ... }
  }
}
```

### Security Pattern for Camera Credentials

**Problem**: Camera username/password must NOT be committed to git

**Solution**: Use `config.local.json` override pattern (already implemented)

**config.json** (version controlled):
```json
{
  "camera": {
    "ip": "192.168.1.4",
    "port": 554,
    "stream": "stream2",
    "username": "",
    "password": "",
    "notes": "Credentials MUST be in config.local.json (gitignored)"
  }
}
```

**config.local.json** (gitignored, machine-specific):
```json
{
  "camera": {
    "username": "rizal72",
    "password": "***"
  }
}
```

**Result** (merged by `config_loader.py:load_config()`):
```json
{
  "camera": {
    "ip": "192.168.1.4",
    "port": 554,
    "stream": "stream2",
    "username": "rizal72",
    "password": "***"
  }
}
```

**Benefits**:
- ✅ Credentials never committed to git
- ✅ Team shares camera IP/port in config.json
- ✅ Each developer sets own credentials in config.local.json
- ✅ Settings UI can edit IP/port (safe to commit)
- ✅ Settings UI shows placeholder for username/password (read from merged config, saved to config.local.json)

---

## 🎨 Settings UI Design

### Modal Structure

**Header**: Settings (fa-gears icon, amber accent)

**7 Tabs** (left-to-right):

1. 🖥️ **System** - Debug mode toggle
2. 🔌 **Z21 Network** - Host IP, UDP port, connection test
3. 📹 **Camera** - IP, port, stream, resolution, credentials (via config.local.json)
4. 🎬 **Video Feed** - FPS slider (hot reload, no restart)
5. 🤖 **YOLO Model** - Confidence, IoU, OBB toggle, preset profiles (OBB/Standard quick load)
6. 📡 **Tracking** - FPS (active/idle), idle timeout, timing thresholds
7. 🚂 **Locomotives** - Function labels (F0-F28) inline edit, lockable toggle

**Footer**:
- Cancel button (left)
- Save Changes button (right, amber accent)
- Restart notification toast (if tracking daemon restart needed)

### Tab 1: System

```
┌─ System ────────────────────────────────────────┐
│                                                  │
│  Debug Mode                                      │
│  ┌─────────────────────────────────────────┐    │
│  │ [Toggle Switch: OFF]                     │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  ℹ️  Debug mode enables verbose logging for:    │
│      • YOLO frame processing                     │
│      • Gate crossing detection                   │
│      • WebSocket messages                        │
│                                                  │
│  ⚠️  Requires backend restart after change       │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Settings**:
- `system.debug.enabled` (boolean toggle)

**Restart**: Backend (FastAPI reload)

---

### Tab 2: Z21 Network

```
┌─ Z21 Network ───────────────────────────────────┐
│                                                  │
│  Z21 Host                                        │
│  ┌─────────────────────────────────────────┐    │
│  │ 192.168.1.111                            │    │
│  └─────────────────────────────────────────┘    │
│  💡 IP address of your Z21 command station       │
│                                                  │
│  UDP Port                                        │
│  ┌─────────────────────────────────────────┐    │
│  │ 21105                                    │    │
│  └─────────────────────────────────────────┘    │
│  💡 Z21 LAN protocol port (default: 21105)       │
│                                                  │
│  [Test Connection]                               │
│                                                  │
│  ℹ️  Current: Roco Z21 Bianca                    │
│      Serial: 111466                              │
│      Firmware: 1.67                              │
│                                                  │
│  ⚠️  Requires backend restart after change       │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Settings**:
- `z21.host` (IP address input with validation)
- `z21.port` (numeric input, range 1-65535)

**Validation**:
- IP format: `xxx.xxx.xxx.xxx` (regex validation)
- Port range: 1-65535

**Test Button**:
- Calls `POST /api/z21/test-connection`
- Shows modal with result: ✅ Connected (Serial, Firmware) or ❌ Failed (error message)

**Restart**: Backend (Z21Manager reconnect)

---

### Tab 3: Camera

```
┌─ Camera ─────────────────────────────────────────┐
│                                                   │
│  Camera IP                                        │
│  ┌──────────────────────────────────────────┐    │
│  │ 192.168.1.4                               │    │
│  └──────────────────────────────────────────┘    │
│                                                   │
│  RTSP Port                                        │
│  ┌──────────────────────────────────────────┐    │
│  │ 554                                       │    │
│  └──────────────────────────────────────────┘    │
│                                                   │
│  Stream Path                                      │
│  ┌──────────────────────────────────────────┐    │
│  │ stream2  ▼                                │    │
│  └──────────────────────────────────────────┘    │
│  💡 stream1 = 1080p, stream2 = 720p (recommended) │
│                                                   │
│  Resolution                                       │
│  ┌──────────────────────────────────────────┐    │
│  │ Width:  1280   Height: 720               │    │
│  └──────────────────────────────────────────┘    │
│                                                   │
│  🔐 Credentials (stored in config.local.json)    │
│  Username                                         │
│  ┌──────────────────────────────────────────┐    │
│  │ rizal72                                   │    │
│  └──────────────────────────────────────────┘    │
│                                                   │
│  Password                                         │
│  ┌──────────────────────────────────────────┐    │
│  │ ••••••••••••••                         👁️  │    │
│  └──────────────────────────────────────────┘    │
│                                                   │
│  [Test RTSP Stream]                               │
│                                                   │
│  ⚠️  Camera settings require video feed restart   │
│  ⚠️  Credentials saved to config.local.json only  │
│                                                   │
└───────────────────────────────────────────────────┘
```

**Settings**:
- `camera.ip` (IP address input)
- `camera.port` (numeric input)
- `camera.stream` (dropdown: stream1, stream2)
- `camera.resolution.width` (numeric input)
- `camera.resolution.height` (numeric input)
- `camera.username` (text input, saved to config.local.json)
- `camera.password` (password input with visibility toggle, saved to config.local.json)
  - **Eye icon** (fa-eye / fa-eye-slash): Click to show/hide password text
  - Default: hidden (type="password"), click to reveal (type="text")

**Security**:
- Username/password read from merged config (includes config.local.json)
- On save, credentials written ONLY to config.local.json (not config.json)
- Backend API handles split: IP/port → config.json, credentials → config.local.json

**Test Button**:
- Calls `POST /api/camera/test-stream`
- Shows modal with: ✅ Stream accessible + resolution or ❌ Failed (RTSP error)

**Restart**: Video feed + tracking daemon (RTSP stream reconnect)

---

### Tab 4: Video Feed

```
┌─ Video Feed ────────────────────────────────────┐
│                                                  │
│  Frame Rate (FPS)                                │
│  ┌─────────────────────────────────────────┐    │
│  │  [===========●===========]  30 FPS       │    │
│  └─────────────────────────────────────────┘    │
│  💡 MJPEG stream frame rate (1-60 FPS)           │
│                                                  │
│  ℹ️  Current stream: rtsp://192.168.1.4/stream2  │
│      Resolution: 1280x720                        │
│      Independent from tracking FPS               │
│                                                  │
│  ⚠️  High FPS increases network bandwidth         │
│      Recommended: 15-30 FPS for smooth display   │
│                                                  │
│  ✅ No restart required (hot reload)             │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Settings**:
- `video.fps` (slider 1-60, step 5, default 30)

**Validation**:
- Range: 1-60 FPS
- Recommended: 15-30 FPS

**Restart**: None (hot reload via video feed config)

---

### Tab 5: YOLO Model

```
┌─ YOLO Model ────────────────────────────────────┐
│                                                  │
│  Model Type                                      │
│  ┌─────────────────────────────────────────┐    │
│  │ ● Oriented Bounding Boxes (OBB)          │    │
│  │ ○ Standard Axis-Aligned Boxes            │    │
│  └─────────────────────────────────────────┘    │
│  💡 OBB handles rotated locomotives better       │
│                                                  │
│  Confidence Threshold                            │
│  ┌─────────────────────────────────────────┐    │
│  │  [===●===================]  0.30         │    │
│  └─────────────────────────────────────────┘    │
│  💡 Minimum detection confidence (0.0-1.0)       │
│                                                  │
│  IoU Threshold (NMS)                             │
│  ┌─────────────────────────────────────────┐    │
│  │  [============●==========]  0.60         │    │
│  └─────────────────────────────────────────┘    │
│  💡 Bounding box overlap threshold for NMS       │
│                                                  │
│  Image Size                                      │
│  ┌─────────────────────────────────────────┐    │
│  │ 640                                      │    │
│  └─────────────────────────────────────────┘    │
│  💡 Model input size (640 standard, 1152 wide)   │
│                                                  │
│  Device                                          │
│  ┌─────────────────────────────────────────┐    │
│  │ cuda ▼                                   │    │
│  └─────────────────────────────────────────┘    │
│  💡 Inference device (cuda, cpu)                 │
│                                                  │
│  📊 Quick Presets (one-click load):              │
│      [Load OBB Profile] [Load Standard Profile]  │
│  💡 Presets from config.json:                     │
│     • OBB: conf=0.3, iou=0.6, obb=true          │
│     • Standard: conf=0.2, iou=0.95, obb=false   │
│                                                  │
│  ⚠️  YOLO settings require tracking daemon restart│
│                                                  │
└──────────────────────────────────────────────────┘
```

**Settings**:
- `yolo.obb` (radio button: OBB / Standard)
- `yolo.confidence` (slider 0.0-1.0, step 0.05, default 0.3)
- `yolo.iou` (slider 0.0-1.0, step 0.05, default 0.6)
- `yolo.imgsz` (numeric input, common values: 640, 1152)
- `yolo.device` (dropdown: cuda, cpu)

**Preset Profiles** (from config.json):
- `tracking_OBB`: `{confidence: 0.3, iou: 0.6, obb: true}` - Optimized for OBB model
- `tracking_standard`: `{confidence: 0.2, iou: 0.95, obb: false}` - Optimized for standard model

**How Presets Work**:
1. Presets stored in config.json (versionated, shared optimal values)
2. User clicks "Load OBB Profile" → form fields populated from `tracking_OBB`
3. User can tweak values if needed
4. User clicks "Save Changes" → values written to `tracking.yolo_*` (active settings)
5. Backend reads `tracking.yolo_*` for inference

**Use Case**: Quick A/B testing between model types, switch on-the-fly with one click

**Restart**: Tracking daemon (reload YOLO model with new settings)
- Endpoint: `POST /api/restart-daemon` (already exists in main.py:539)

---

### Tab 6: Tracking

```
┌─ Tracking ──────────────────────────────────────┐
│                                                  │
│  📊 Frame Rates                                  │
│                                                  │
│  Active FPS (locomotives moving)                 │
│  ┌─────────────────────────────────────────┐    │
│  │  [============●==========]  30 FPS       │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  Idle FPS (all locomotives stopped)              │
│  ┌─────────────────────────────────────────┐    │
│  │  [●=======================]  1 FPS       │    │
│  └─────────────────────────────────────────┘    │
│  💡 Low FPS when idle saves CPU/GPU resources    │
│                                                  │
│  Idle Timeout (seconds)                          │
│  ┌─────────────────────────────────────────┐    │
│  │  [==========●============]  10 sec       │    │
│  └─────────────────────────────────────────┘    │
│  💡 Switch to idle mode after N seconds stopped  │
│                                                  │
│  ⏱️  Timing Thresholds                            │
│                                                  │
│  SYNCED Threshold (seconds)                      │
│  ┌─────────────────────────────────────────┐    │
│  │  [==========●============]  1.0s         │    │
│  └─────────────────────────────────────────┘    │
│  💡 |Δt| < threshold = synchronized              │
│                                                  │
│  WARNING Threshold (seconds)                     │
│  ┌─────────────────────────────────────────┐    │
│  │  [=============●=========]  1.5s         │    │
│  └─────────────────────────────────────────┘    │
│  💡 SYNCED < |Δt| < WARNING = critical           │
│                                                  │
│  Max Δt (outlier filter, seconds)                │
│  ┌─────────────────────────────────────────┐    │
│  │  [===================●===]  10.0s        │    │
│  └─────────────────────────────────────────┘    │
│  💡 Ignore Δt > max (video lag / detection noise)│
│                                                  │
│  ⚠️  Tracking settings require daemon restart     │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Settings**:
- `tracking.fps.active` (slider 1-60, step 5, default 30)
- `tracking.fps.idle` (slider 1-10, step 1, default 1)
- `tracking.idle_timeout_seconds` (slider 5-60, step 5, default 10)
- `tracking.timing_thresholds.normal` (slider 0.5-5.0, step 0.1, default 1.0)
- `tracking.timing_thresholds.warning` (slider 0.5-5.0, step 0.1, default 1.5)
- `tracking.timing_thresholds.max_delta_t` (slider 5-30, step 1, default 10.0)

**Validation**:
- `warning` threshold must be > `normal` threshold

**Restart**: Tracking daemon (reload config)

---

### Tab 7: Locomotives

```
┌─ Locomotives ───────────────────────────────────┐
│                                                  │
│  🚂 Configured Locomotives (7)                   │
│                                                  │
│  ┌─ Loco 1: Gr.675 017 ──────────────────┐      │
│  │ Decoder: LokSound V4.0                 │      │
│  │ Color: 🟡 #FFFF00                      │      │
│  │ Status: In consist 10 (C10 Interno)    │      │
│  │                                         │      │
│  │ Functions (21 configured):              │      │
│  │ [Expand Functions ▼]                   │      │
│  └─────────────────────────────────────────┘      │
│                                                  │
│  [Expanded view when clicked]:                  │
│                                                  │
│  ┌─ Functions F0-F21 ────────────────────┐      │
│  │ F0:  [light        ] ☑ Lockable       │      │
│  │ F1:  [sound        ] ☑ Lockable       │      │
│  │ F2:  [whistle L    ] ☐ Lockable       │      │
│  │ F3:  [whistle S    ] ☐ Lockable       │      │
│  │ ... (21 functions total)               │      │
│  └────────────────────────────────────────┘      │
│                                                  │
│  ℹ️  Function labels editable (click to rename)  │
│     Lockable = toggle stays ON when released    │
│                                                  │
│  💡 Name, decoder, color:                        │
│     Edit manually in config.json (advanced)     │
│                                                  │
│  ✅ Changes saved to config.json                 │
│  ⚠️  Requires backend reload after save          │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Settings**:
- Function `label` (inline text input - click to edit)
- Function `lockable` (checkbox toggle)

**Read-Only** (manual config.json edit):
- Locomotive `name` (e.g., "Gr.675 017")
- Locomotive `decoder` (e.g., "LokSound V4.0")
- Locomotive `color` (hex color for UI display)

**NOT Shown** (managed elsewhere):
- CV profiles (normal/testing) → **Test Mode badge** in header (already in DB)
- Consist assignment → **Consist Manager** (fa-link button)

**Restart**: Backend reload (to refresh function labels in memory)

---

## 🚪 Gates & Consists (NOT in Settings UI)

**Critical Design Decision**: Gates and consists are **NOT** in Settings UI tabs.

### Why Not in Settings?

**Gates** (visual editing):
- Already have **Gate Editor** (hotkey 'E' in video feed)
- Drag to move, resize corners, rotate with mouse wheel, change color
- Saves directly to config.json via `POST /api/save-gates`
- Hot reload (no restart needed)
- **Settings UI would be redundant** - visual editor is superior UX

**Consists** (CRUD + gate assignment):
- Already have **Consist Manager** (fa-link button in header)
- Full CRUD: create, edit, delete consists
- Assign locomotives (lead/rear)
- Select reference loco (for speed matching)
- Choose consist mode (Virtual/DCC with CV19 write)
- Assign tracking gates (`gate_ids` checkbox multi-select)
- **Gate assignment logic** (asymmetric vs symmetric):
  - If user selects specific gates for reference/adjust → asymmetric mode
  - If unspecified → symmetric mode (null, both locos tracked by all gates)
- **Requires expansion**: Add `gate_assignment` UI for asymmetric mode

### Gate Assignment Logic (Consist Manager Enhancement)

**Current** (in config.json):
```json
"consists": {
  "10": {
    "gate_ids": [3, 4],
    "gate_assignment": {"reference": 3, "adjust": 4}  // Asymmetric
  },
  "11": {
    "gate_ids": [1, 2],
    "gate_assignment": null  // Symmetric (default)
  }
}
```

**Consist Manager UI Enhancement** (future):

When user selects `gate_ids` (e.g., Gate 3 and Gate 4):

```
Gate Tracking Mode (Advanced):

Reference loco monitored by: [All gates ▼]
Adjust loco monitored by: [All gates ▼]

Options:
- All gates (default - symmetric, both locos tracked by all gates)
- Gate 3 (specific gate for this loco)
- Gate 4 (specific gate for this loco)
```

**Logic**:
- Both = "All gates" → `gate_assignment: null` (symmetric, Consist 11 pattern)
- Specific gates → `gate_assignment: {"reference": 3, "adjust": 4}` (asymmetric, Consist 10 pattern)

**Why Consist-Level, Not Loco-Level?**
- Gate assignment is **consist configuration**, not locomotive property
- Determines **tracking strategy** for that specific consist on that specific track geometry
- Example: Consist 10 on figure-8 track (asymmetric), Consist 11 on oval track (symmetric)

---

### ~~Tab 7: Gates~~ (REMOVED - See Above)

```
┌─ Gates ─────────────────────────────────────────┐
│                                                  │
│  📍 Configured Gates (4)                         │
│                                                  │
│  ┌─ Gate 1 ───────────────────────────────┐     │
│  │ Position: X=995, Y=27                   │     │
│  │ Size: 65 × 43 px                        │     │
│  │ Angle: 0°                               │     │
│  │ Color: 🟠 Orange (255,165,0)            │     │
│  │ Assigned to: Consist 11 (C11 Esterno)   │     │
│  └─────────────────────────────────────────┘     │
│                                                  │
│  ┌─ Gate 2 ───────────────────────────────┐     │
│  │ Position: X=10, Y=269                   │     │
│  │ Size: 44 × 47 px                        │     │
│  │ Angle: -30°                             │     │
│  │ Color: 🟠 Orange (255,165,0)            │     │
│  │ Assigned to: Consist 11 (C11 Esterno)   │     │
│  └─────────────────────────────────────────┘     │
│                                                  │
│  ┌─ Gate 3 ───────────────────────────────┐     │
│  │ Position: X=1086, Y=326                 │     │
│  │ Size: 80 × 80 px                        │     │
│  │ Angle: 300°                             │     │
│  │ Color: 🔵 Cyan (0,255,255)              │     │
│  │ Assigned to: Consist 10 (C10 Interno)   │     │
│  └─────────────────────────────────────────┘     │
│                                                  │
│  ┌─ Gate 4 ───────────────────────────────┐     │
│  │ Position: X=479, Y=29                   │     │
│  │ Size: 50 × 50 px                        │     │
│  │ Angle: 0°                               │     │
│  │ Color: 🔵 Cyan (0,255,255)              │     │
│  │ Assigned to: Consist 10 (C10 Interno)   │     │
│  └─────────────────────────────────────────┘     │
│                                                  │
│  [Open Gate Editor] (Press 'E' in video feed)   │
│                                                  │
│  ℹ️  Gate editor: drag to move, resize corners,  │
│      rotate with mouse wheel, change color       │
│                                                  │
│  ✅ Gate changes hot reload (no restart needed)  │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Settings**:
- Gate list (read-only display, links to gate editor)
- Gate-to-consist assignment (future: dropdown per gate)

**Gate Editor**:
- Launched via 'E' hotkey in video feed (existing feature)
- Drag gates, resize, rotate, change color
- Saves directly to config.json via `POST /api/save-gates`

**Future Enhancement** (not MVP):
- Dropdown per gate: "Assigned to: [Consist 10 ▼]"
- Save gate_ids array in consists section

**Restart**: None (hot reload via video overlay refresh)

---

### ~~Tab 8: Consists~~ (REMOVED - See "Gates & Consists" Section Above)

```
┌─ Consists ──────────────────────────────────────┐
│                                                  │
│  🚂 Configured Consists (2)                      │
│                                                  │
│  ┌─ Consist 10 (C10 Interno) ─────────────┐     │
│  │ Lead: 1 - Gr.675 017                    │     │
│  │ Rear: 5 - D645 014                      │     │
│  │ Gates: Gate 3, Gate 4                   │     │
│  │ Mode: Virtual (CV19=0)                  │     │
│  │ [Edit] [Delete]                         │     │
│  └─────────────────────────────────────────┘     │
│                                                  │
│  ┌─ Consist 11 (C11 Esterno) ─────────────┐     │
│  │ Lead: 7 - E656 239                      │     │
│  │ Rear: 8 - E444 056                      │     │
│  │ Gates: Gate 1, Gate 2                   │     │
│  │ Mode: Virtual (CV19=0)                  │     │
│  │ [Edit] [Delete]                         │     │
│  └─────────────────────────────────────────┘     │
│                                                  │
│  [Add New Consist]                               │
│                                                  │
│  💡 Consists are managed via Consist Manager    │
│      (fa-link button in header)                  │
│                                                  │
│  ℹ️  Consist changes broadcast to all clients    │
│      via WebSocket (real-time sync)              │
│                                                  │
│  ⚠️  Consist CRUD may require backend reload     │
│      (if new consist created)                    │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Settings**:
- Consist list (read-only display, links to consist manager)
- Add/Edit/Delete buttons launch Consist Manager modal

**Consist Manager**:
- Existing feature (fa-link button in header)
- Full CRUD: create, edit, delete consists
- CV19 write operations (Virtual Mode / DCC Mode toggle)
- Gate assignments

**Restart**: Backend reload if new consist created (rebuild consist_data dict)

---

## 🔄 Migration Strategy

### Phase 1: Backend - Unify config.json Structure

**Goal**: Merge camera_config.json into config.json, move Z21 from hardcoded to config

**Steps**:

1. **Update config.json schema** (add new sections):
   ```json
   {
     "system": { "debug": { ... } },
     "z21": { "host": "192.168.1.111", "port": 21105 },
     "camera": { "ip": "192.168.1.4", "port": 554, "stream": "stream2", "resolution": {...}, "username": "", "password": "" },
     "video": { "fps": 30 },
     "yolo": { ... },
     "tracking": { ... },
     ...
   }
   ```

2. **Migration script**: `scripts/utils/migrate_config_unified.py`
   - Read current config.json
   - Read camera_config.json
   - Merge into new structure
   - Backup old files
   - Write unified config.json
   - Create config.local.json with camera credentials (gitignored)

3. **Update backend loaders**:
   - `config_loader.py` - Add schema validation
   - `z21_manager.py` - Read `config['z21']['host']` instead of hardcoded IP
   - `main.py` - Read Z21 settings from config instead of hardcoded
   - `video_feed.py` - Read camera from `config['camera']` instead of `load_camera_config()`
   - `tracking/rtsp_handler.py` - Same as video_feed

4. **Backward compatibility**:
   - Keep `load_camera_config()` with deprecation warning
   - Fallback to old camera_config.json if new structure not found
   - Log migration recommendation

**Estimated Time**: 3-4 hours

---

### Phase 2: Frontend - Settings UI Modal

**Goal**: Build 8-tab Settings modal consuming GET/POST /api/config

**Steps**:

1. **Update Settings modal structure** (`SettingsModal.jsx`):
   - Expand from 5 tabs → 8 tabs
   - Implement all tab content (forms, sliders, toggles)
   - Add validation for each field (IP format, port range, threshold ordering)
   - Add test buttons (Z21 connection, camera RTSP)

2. **Create tab components**:
   - `SystemTab.jsx` - Debug toggle
   - `Z21NetworkTab.jsx` - Host, port, test button
   - `CameraTab.jsx` - IP, port, stream, resolution, credentials
   - `VideoFeedTab.jsx` - FPS slider
   - `YoloModelTab.jsx` - Model type, confidence, IoU, imgsz, device, presets
   - `TrackingTab.jsx` - FPS, idle timeout, timing thresholds
   - `GatesTab.jsx` - Gate list display, link to gate editor
   - `ConsistsTab.jsx` - Consist list display, link to consist manager

3. **Settings API integration**:
   - Call `GET /api/config` on modal open
   - Populate all form fields from config
   - On save: `POST /api/settings/update` with full config
   - Show toast notification with restart requirements
   - Handle errors gracefully (validation, save failures)

4. **UI/UX polish**:
   - Field validation with error messages
   - Unsaved changes warning (if user closes without saving)
   - Loading states (spinner during save)
   - Success/error toasts
   - Responsive design (mobile-friendly)

**Estimated Time**: 8-10 hours

---

### Phase 3: Backend API - Settings Update Logic

**Goal**: Smart restart detection + config validation

**Steps**:

1. **Expand `/api/settings/update` endpoint** (`routers/config.py`):
   - Handle new sections: `system`, `z21`, `camera`, `video`, `yolo`, `tracking`
   - Detect changes per section
   - Determine restart requirements:
     - `system.debug` → restart backend
     - `z21.*` → restart backend (Z21Manager reconnect)
     - `camera.*` → restart video feed + tracking daemon (RTSP reconnect)
     - `video.fps` → hot reload (no restart)
     - `yolo.*` → restart tracking daemon (reload model)
     - `tracking.*` → restart tracking daemon (reload config)
     - `gates` → hot reload (no restart)
     - `consists` → backend reload if new consist created
   - Return detailed restart_needed array

2. **Config validation**:
   - IP address format validation (regex)
   - Port range validation (1-65535)
   - Threshold ordering validation (warning > normal)
   - Required field validation

3. **Security handling**:
   - Camera credentials: write to config.local.json (NOT config.json)
   - Other settings: write to config.json
   - Implement `save_config_split(config, credentials)` in config_loader.py

4. **Test endpoints**:
   - `POST /api/z21/test-connection` - Try to connect to Z21, return status
   - `POST /api/camera/test-stream` - Try to open RTSP stream, return resolution + status

**Estimated Time**: 4-5 hours

---

### Phase 4: Testing & Documentation

**Goal**: End-to-end testing + update docs

**Steps**:

1. **Test scenarios**:
   - Fresh install (no config files)
   - Migration from old structure (camera_config.json exists)
   - Settings update with restart detection
   - Credential security (not committed to git)
   - Hot reload features (gates, video FPS)
   - Validation errors (invalid IP, port out of range, etc.)

2. **Update documentation**:
   - Update CLAUDE.md with Settings UI status
   - Update README.md with Settings button screenshot
   - Create SETTINGS_UI_USAGE.md user guide
   - Update CONFIG_REFACTOR.md with final structure

3. **Production deployment**:
   - Run migration script on PC
   - Test Settings UI on Mac (development)
   - Test Settings UI on PC (production)
   - Verify config.local.json gitignored
   - Verify credentials not leaked

**Estimated Time**: 3-4 hours

---

## 📊 Restart Requirements Matrix

| Setting Category | Settings Changed | Services to Restart | Hot Reload? |
|------------------|------------------|---------------------|-------------|
| System (Tab 1) | debug.enabled | Backend | No |
| Z21 Network (Tab 2) | host, port | Backend (Z21Manager) | No |
| Camera (Tab 3) | ip, port, stream, resolution, credentials | Video feed + Tracking daemon | No |
| Video Feed (Tab 4) | fps | None | ✅ Yes |
| YOLO Model (Tab 5) | confidence, iou, obb, imgsz, device, presets | **Tracking daemon** (`POST /api/restart-daemon`) | No |
| Tracking (Tab 6) | fps, idle_timeout, timing_thresholds | Tracking daemon | No |
| Locomotives (Tab 7) | function labels, lockable | Backend reload (function map) | No |
| **Gates** (NOT in Settings) | position, size, angle, color | None | ✅ Yes |
| **Consists** (NOT in Settings) | CRUD operations | Backend (if new consist) | No |

---

## 🔄 Automatic Page Reload Feature

**Status**: ✅ **IMPLEMENTED** (2025-01-19)

### Overview

Settings that require service restarts now trigger **automatic page reload** after save, eliminating the need for manual refresh or separate restart endpoints.

### How It Works

1. **User saves settings** → Backend processes changes
2. **Backend returns `restart_needed` array**:
   - Empty array `[]` → No reload (hot reload settings only)
   - Non-empty array `["backend"]`, `["tracker"]`, etc. → **Auto-reload triggered**
3. **Frontend shows alert** with list of services requiring restart
4. **Page reloads automatically** via `window.location.reload()`
5. **Session restored** from database (no data loss)

### Implementation

**File**: `web/src/components/SettingsModal.jsx` (lines 135-149)

```javascript
// Handle restart requirements
if (result.restart_needed.length > 0) {
  alert(`Settings saved successfully!\n\nPage will reload to apply changes.\n\nRestart needed for: ${result.restart_needed.join(', ')}`);
  window.location.reload(); // Force reload
} else {
  alert('Settings saved successfully!\n\nNo restart required.');
  onClose();
}
```

### Which Settings Trigger Reload

**Reload Required** (`restart_needed` not empty):
- ✅ **General Tab** (debug.enabled) → `["backend"]`
- ✅ **Z21 Network Tab** (host, port) → `["backend"]`
- ✅ **Camera Tab** (ip, port, stream, resolution) → `["video_feed", "tracker"]`
- ✅ **YOLO Model Tab** (confidence, iou, imgsz, obb, device) → `["tracker"]`
- ✅ **Tracking Tab** (fps, idle_timeout, timing_thresholds) → `["tracker"]`

**No Reload** (`restart_needed` empty):
- ❌ **Video Feed Tab** (fps) → Hot reload only
- ❌ **Analytics Tab** (max_chart_events) → Frontend-only parameter
- ❌ **Locomotives Tab** (function labels, lockable) → Roster reload only

### Safety Guarantees

**Why Auto-Reload is Safe**:
- ✅ **Analytics sessions database-persisted**: Active session state saved to `data.db`
- ✅ **Reload happens AFTER config save**: Config changes committed before reload
- ✅ **User notified before reload**: Alert explains what will restart
- ✅ **No data loss**: All operational state stored in database, not memory

**What Gets Preserved**:
- Active locomotive/consist selection
- Analytics session ID and metrics
- Gate positions and assignments
- Consist configurations
- Speed table profiles

**What Gets Restarted**:
- Backend FastAPI process (if backend in restart_needed)
- YOLO tracking daemon (if tracker in restart_needed)
- Video feed MJPEG stream (if video_feed in restart_needed)
- Z21 connection (if backend in restart_needed)
- RTSP camera stream (if video_feed in restart_needed)

### User Experience

**Scenario 1: YOLO Model Change**
```
1. User: Changes confidence 0.3 → 0.2
2. User: Clicks "Save Changes"
3. Backend: Saves to config.json, returns ["tracker"]
4. Alert: "Settings saved successfully!

          Page will reload to apply changes.

          Restart needed for: tracker"
5. Page reloads → tracker daemon restarts with new confidence
6. User sees updated YOLO detection immediately
```

**Scenario 2: Video FPS Change (No Reload)**
```
1. User: Changes video FPS 30 → 15
2. User: Clicks "Save Changes"
3. Backend: Saves to config.json, returns []
4. Alert: "Settings saved successfully!

          No restart required."
5. Modal closes, no reload
6. Video feed updates FPS via hot reload
```

### Backend Logic

**File**: `backend/routers/config.py` (lines 99-277)

**Restart Decision Tree**:
```python
restart_needed = []

# System settings (debug.enabled)
if "debug" in request and old_debug != new_debug:
    restart_needed.append("backend")

# Z21 Network (host/port)
if "z21" in request and (old_host != new_host or old_port != new_port):
    restart_needed.append("backend")

# Camera (ip/port/stream/resolution)
if "camera" in request and any_camera_setting_changed:
    restart_needed.append("video_feed")
    restart_needed.append("tracker")

# YOLO settings (confidence/iou/imgsz/obb/device)
if "tracking" in request and any_yolo_setting_changed:
    restart_needed.append("tracker")

# Video Feed (fps) - NO restart needed (hot reload)
if "video" in request:
    # Hot reload, do not append to restart_needed
    pass

# Analytics (max_chart_events) - NO restart needed (frontend only)
if "analytics" in request:
    # Frontend parameter, do not append to restart_needed
    pass

return {"status": "success", "restart_needed": restart_needed}
```

### Advantages Over Manual Restart

**Before** (Manual Approach):
- User changes YOLO confidence
- User clicks Save → Modal closes
- User refreshes page manually (or doesn't, wonders why changes not applied)
- Inconsistent UX, confusion about when restart needed

**After** (Auto-Reload):
- User changes YOLO confidence
- User clicks Save → Alert explains restart
- Page reloads automatically
- Changes applied immediately, consistent UX

**Benefits**:
- ✅ **Zero confusion**: User always knows when restart needed
- ✅ **Consistent behavior**: All settings requiring restart handled uniformly
- ✅ **No forgotten refreshes**: Automatic, no manual intervention
- ✅ **Safe implementation**: Sessions persisted, no data loss
- ✅ **Clear communication**: Alert explains exactly what will restart

---

## 🔐 Security Considerations

### Camera Credentials

**Problem**: Username/password must NOT be committed to git

**Solution**:
1. `config.json` (version controlled):
   - Contains empty `camera.username` and `camera.password`
   - Includes note: "Credentials MUST be in config.local.json"

2. `config.local.json` (gitignored):
   - Contains actual credentials
   - Deep merged with config.json by `config_loader.py`

3. Settings UI:
   - Reads merged config (shows actual username/password)
   - On save: writes credentials to config.local.json ONLY
   - Other camera settings (IP, port) written to config.json

4. `.gitignore`:
   - Ensure `config.local.json` is gitignored
   - Add `camera_config.json` to .gitignore (legacy file)

**Risk Mitigation**:
- ✅ No credentials in version control
- ✅ Team shares camera IP/port safely
- ✅ Each developer uses own credentials
- ✅ Settings UI handles split automatically

---

## 🎯 Success Criteria

### Functional Requirements

✅ **FR1**: All settings unified in single config.json
✅ **FR2**: Settings UI with 8 tabs covering all configurations
✅ **FR3**: Smart restart detection (only restart affected services)
✅ **FR4**: Camera credentials remain gitignored (config.local.json pattern)
✅ **FR5**: Validation for all input fields (IP, port, thresholds)
✅ **FR6**: Test buttons for Z21 connection + camera RTSP stream
✅ **FR7**: Hot reload for gates + video FPS (no restart needed)
✅ **FR8**: Backward compatibility (graceful migration from old structure)
✅ **FR9**: Unsaved changes warning (if user closes modal)
✅ **FR10**: Responsive design (mobile-friendly)

### Non-Functional Requirements

✅ **NFR1**: Settings UI loads in <500ms
✅ **NFR2**: Save operation completes in <1s
✅ **NFR3**: Validation errors displayed inline (no blocking alerts)
✅ **NFR4**: Professional UI/UX (consistent with existing dashboard)
✅ **NFR5**: Settings documentation complete (user guide + dev docs)

---

## 📝 Implementation Checklist

### Backend (Estimated: 8 hours)

- [ ] Migration script: `scripts/utils/migrate_config_unified.py`
- [ ] Update `config_loader.py`: add schema validation
- [ ] Update `config_loader.py`: add `save_config_split()` for credentials
- [ ] Update `z21_manager.py`: read Z21 from config instead of hardcoded
- [ ] Update `main.py`: read Z21 from config instead of hardcoded
- [ ] Update `video_feed.py`: read camera from unified config
- [ ] Update `tracking/rtsp_handler.py`: read camera from unified config
- [ ] Update `routers/config.py`: expand `/api/settings/update` endpoint (7 tabs)
- [ ] Add `routers/locomotives.py`: GET/POST for function labels editing
- [ ] Add validation functions: IP format, port range, thresholds ordering
- [ ] Add test endpoints: `/api/z21/test-connection`, `/api/camera/test-stream`
- [ ] Deprecate `load_camera_config()` with warning
- [ ] Handle YOLO preset loading (tracking_OBB, tracking_standard)

### Frontend (Estimated: 10 hours)

- [ ] Expand `SettingsModal.jsx`: 5 tabs → 7 tabs (remove Gates/Consists)
- [ ] Implement `SystemTab.jsx` (debug toggle)
- [ ] Implement `Z21NetworkTab.jsx` (host, port, test button)
- [ ] Implement `CameraTab.jsx` (IP, port, stream, resolution, credentials)
- [ ] Implement `VideoFeedTab.jsx` (FPS slider)
- [ ] Implement `YoloModelTab.jsx` (confidence, IoU, OBB, presets with load buttons)
- [ ] Implement `TrackingTab.jsx` (FPS, idle timeout, timing thresholds)
- [ ] Implement `LocomotivesTab.jsx` (function labels inline edit, lockable toggle, expand/collapse per loco)
- [ ] Add field validation (IP, port, thresholds)
- [ ] Add preset load buttons for YOLO (populate form from tracking_OBB/tracking_standard)
- [ ] Add unsaved changes warning
- [ ] Add loading states (spinner during save)
- [ ] Add restart notification toast (tracking daemon restart needed)
- [ ] Add success/error toasts
- [ ] Responsive design testing (mobile/tablet)

### Consist Manager Enhancement (Estimated: 3 hours)

- [ ] Add `gate_assignment` UI in ConsistForm.jsx
- [ ] Add dropdowns: "Reference loco monitored by" / "Adjust loco monitored by"
- [ ] Options: "All gates" (default), "Gate 3", "Gate 4", etc.
- [ ] Logic: both="All gates" → gate_assignment=null, specific → gate_assignment={reference, adjust}
- [ ] Update backend `POST /api/consists` to handle gate_assignment
- [ ] Update backend `PUT /api/consists/{address}` to handle gate_assignment

### Testing (Estimated: 4 hours)

- [ ] Test migration script (fresh install + existing configs)
- [ ] Test Settings UI on Mac (development)
- [ ] Test Settings UI on PC (production)
- [ ] Test restart detection (each settings category)
- [ ] Test validation errors (invalid inputs)
- [ ] Test hot reload (gates, video FPS)
- [ ] Test credential security (config.local.json not committed)
- [ ] Test test buttons (Z21 connection, camera RTSP)

### Documentation (Estimated: 2 hours)

- [ ] Update CLAUDE.md with Settings UI status
- [ ] Create SETTINGS_UI_USAGE.md user guide
- [ ] Update README.md with Settings button screenshot
- [ ] Update CONFIG_REFACTOR.md with final structure
- [ ] Add migration guide (old → new config structure)

**Total Estimated Time**: ~24 hours (3 full days)
- Settings UI (7 tabs): ~18 hours
- Consist Manager gate_assignment: ~3 hours
- Testing + docs: ~3 hours

---

## 🚀 Next Steps

1. **Review this design document** - Feedback from user
2. **Approve architecture** - Confirm unified config.json structure
3. **Create feature branch**: `git checkout -b feature/settings-ui`
4. **Start Phase 1**: Backend migration (config.json unification)
5. **Test Phase 1**: Migration script + backend loaders
6. **Start Phase 2**: Frontend Settings UI
7. **Test Phase 2**: End-to-end Settings UI workflow
8. **Start Phase 3**: Backend API expansion
9. **Test Phase 3**: Smart restart detection + validation
10. **Start Phase 4**: Testing + documentation
11. **Deploy to production**: Mac + PC
12. **Tag release**: v1.1.0 (Settings UI Complete)

---

## 📚 Related Documentation

- `docs/CONFIG_REFACTOR.md` - Previous config.json refactoring (2025-01-03)
- `docs/DB_REFACTORING.md` - Database schema design (Phase 0-2 complete)
- `docs/WEB_DASHBOARD.md` - Frontend stack + development workflow
- `docs/COMPUTER_VISION.md` - YOLO tracking + gate timing detection
- `docs/Z21_PROTOCOL.md` - Z21 LAN UDP protocol specs

---

**Status**: ✅ **IMPLEMENTED AND DEPLOYED** (Settings UI Complete + Auto-Reload)

**Implementation Summary**:
- ✅ **Settings UI**: 8 tabs fully implemented (General, Z21 Network, Camera, Video Feed, YOLO Model, Tracking, Analytics, Locomotives)
- ✅ **Auto-Reload**: Automatic page reload when settings requiring restart are saved (2025-01-19)
- ✅ **Function Labels**: Editable F0-F28 labels with lockable toggle per locomotive
- ✅ **Hot Reload**: Video FPS, Analytics settings require no restart
- ✅ **Smart Restart Detection**: Backend returns restart_needed array, frontend handles automatically
- ✅ **Database-Persisted Sessions**: Safe page reload with no data loss

**Key Decisions Made**:
- ✅ Settings UI = 8 tabs (General, Z21, Camera, Video, YOLO, Tracking, Analytics, Locomotives)
- ✅ Gates/Consists NOT in Settings (already have dedicated editors)
- ✅ JMRI independence achieved (optional for initial roster import only)
- ✅ Test Mode NOT in Settings (already in DB + header badge)
- ✅ Function labels editable (inline edit per locomotive)
- ✅ Config.json remains source of truth (DB for operational state only)
- ✅ **Auto-reload replaces manual restart** (window.location.reload after save if restart_needed)

**Recent Additions** (2025-01-19):
- ✅ Analytics tab with max_chart_events configuration
- ✅ Automatic page reload for settings requiring service restart
- ✅ Safety guarantees: database-persisted sessions, no data loss

**Release**: v1.0.0 (JMRI Independence + Settings UI + Auto-Reload)
**Deployment**: Production on PC Windows + Mac development environment
