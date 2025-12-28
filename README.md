# z21-Terminal

Interactive terminal controller for DCC locomotives via Z21 LAN protocol.

**Project**: DCC Model Railway - BiancAlice

## Project Structure

```
z21-Terminal/
├── README.md          # This file
├── scripts/           # Python scripts (terminal controller, utilities)
├── backend/           # FastAPI backend + WebSocket + Z21Manager
├── web/               # React frontend (Vite + Tailwind)
├── docs/              # Additional documentation
└── data/              # Exported data, logs, CV backups
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
  - **z21-Terminal**: Fast operational control, modern web UI, automation, Python scripting

**Typical workflow**:
1. Configure locomotives and consists in JMRI (DecoderPro)
2. Use z21-Terminal for operational control (web dashboard or terminal)
3. Both software can remain open and work together (last command has priority)

## Setup

### Requirements
- **Control Station**: Roco Z21 (White, Black, or Pro) connected to your network
- **Software**: JMRI installed with configured roster (does not need to be running)
- **Network**: Z21 and computer on same network (or accessible via VPN/Tailscale)

### Example Setup
Your specific layout and roster are configured in JMRI:
- Configure locomotives in JMRI DecoderPro (assign DCC addresses, program CVs)
- Create consists for synchronized operations (e.g., multiple locomotives on same track)
- z21-Terminal automatically loads roster and consists from JMRI XML files

**Example roster**: 7 locomotives with 2 consists configured for dual-track operations

## Main Usage

### Web Dashboard 🌐
Modern web interface for locomotive control (mobile-first, multi-device):

```bash
z21              # Start backend + frontend (opens in new iTerm tabs)
z21-backend      # Start only backend (FastAPI + WebSocket)
z21-frontend     # Start only frontend (Vite dev server)
```

Access at: **http://localhost:5173** (or from network: `http://192.168.1.xxx:5173`)

**Features:**
- Dual controller layout (control 2 consists/locomotives simultaneously)
- Touch-optimized controls (speed slider with 200ms throttling for stability)
- Real-time sync via WebSocket (multi-device support)
- Empty state UX: dropdown always visible even without selection
- Emergency stop with audio feedback (ESC keyboard shortcut)
- STOP button for each controller (speed=0 quick action)
- Power-on speed reset (prevents locomotives from restarting at previous speed)
- Function state sync with Z21
- Color-coded function indicators (red dot=toggle, amber dot=temporary, green=ON)
- Support for standalone locomotives and consists
- Elegant UI with Font Awesome 6 icons
- Performance optimized for Chrome Mac Intel (backdrop-blur removed)
- Safari Mac animation compatibility (smooth transitions)

### Terminal Controller ⌨️
Interactive keyboard control:

```bash
cd ~/Documents/_PROGETTI/z21-Terminal/scripts

# Interactive Z21 controller
python3 z21_controller.py               # Interactive loco selection
python3 z21_controller.py 1             # Control loco address 1
python3 z21_controller.py 10            # Control consist 10
```

## Utility Scripts

```bash
# Read CV from JMRI roster (reference)
python3 read_cv_from_roster.py          # List all locomotives
python3 read_cv_from_roster.py 1 5      # Compare loco 1 and 5

# View consists
python3 read_consists.py                # List configured consists
python3 read_consists.py 10             # Consist 10 details
```

## Features

### Web Dashboard ✅
- [x] Modern web UI (Vite + React + Tailwind CSS + Font Awesome 6)
- [x] FastAPI backend with WebSocket real-time sync
- [x] Dual controller layout (2 consists/locomotives simultaneously)
- [x] Flexible roster selection (consists + standalone locomotives)
- [x] Empty state UX: dropdown always visible for recovery
- [x] Touch-optimized controls (mobile-first design)
- [x] Speed control slider with 200ms throttling (prevents Z21 disconnections)
- [x] STOP button for each controller (quick speed=0)
- [x] Direction toggle (forward/reverse)
- [x] Functions F0-F28 with color-coded indicators (red=toggle, amber=temporary)
- [x] Global emergency stop with ESC keyboard shortcut
- [x] Power-on speed reset (prevents restart at previous speed)
- [x] Multi-device support (iPad, phone, desktop)
- [x] Track power polling (500ms) with auto-sync
- [x] Function state sync from Z21
- [x] Z21 connection health monitoring (5s polling)
- [x] Status indicators with Font Awesome icons (power, WebSocket, Z21)
- [x] Auto-disable controls when Z21 offline
- [x] Tailscale HTTPS support (wss:// auto-detection)
- [x] Performance optimized for Chrome Mac Intel
- [x] Safari Mac animation compatibility

### Terminal Controller ✅
- [x] Complete speed control (w/s, 0-9, hotkeys)
- [x] Emergency stop with power toggle and audio feedback
- [x] Function control F0-F28 (dynamic loading from roster, Shift+A-Z hotkeys)
- [x] Periodic polling sync (track power, functions - 500ms interval)
- [x] Support for single locomotives and consists
- [x] Real-time unified UI (functions always visible)
- [x] On-the-fly locomotive switching

### Z21 Library ✅
- [x] Complete Z21 LAN protocol (UDP)
- [x] Locomotive movement control
- [x] Functions F0-F28 control
- [x] Read locomotive state (speed, direction, functions)
- [x] Emergency stop and power control
- [x] Coexistence with JMRI

### Utilities ✅
- [x] Read CV from JMRI roster (XML files)
- [x] View configured consists

### TODO ⏳
- [ ] Direct CV reading from locomotives (via Z21 programming track)
- [ ] CV writing via Z21 (for decoder configuration)
- [ ] Progressive Web App (installable on iPad)
- [ ] Custom automation scenarios

## Notes

- **Roster Management**: Configure your locomotives in JMRI DecoderPro
  - z21-Terminal automatically loads roster from JMRI XML files
  - Supports individual locomotives and consists (DAC software-based)
  - No limit on number of locomotives (tested with 7+ locomotives)
- **Speed Matching**: Managed manually in JMRI using speed tables (CV67-94)
- **Z21 Protocol**:
  - Direct Z21 LAN control (UDP port 21105) ✅
  - Tested on Z21 White (also compatible with Z21 Black/Pro)
  - Coexists with JMRI: both can control locomotives simultaneously
  - Read locomotive state (speed, direction, functions F0-F28) implemented
  - Slider throttling (200ms) prevents buffer overflow and disconnections
- **CV Operations**: CV read/write to be implemented (via Z21 programming track)
- **Browser Compatibility**: Optimized for Safari Mac, Chrome Mac, and mobile browsers
