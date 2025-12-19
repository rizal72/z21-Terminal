# z21-Terminal

Interactive terminal controller for DCC locomotives via Z21 LAN protocol.

**Project**: DCC Model Railway - BiancAlice

## Project Structure

```
z21-Terminal/
├── CLAUDE.md          # Detailed setup and configuration documentation (Italian)
├── README.md          # This file
├── scripts/           # Python scripts for automation
├── docs/              # Additional documentation
└── data/              # Exported data, logs, CV backups
```

## Relationship with JMRI

**z21-Terminal is an extension of JMRI, not a replacement.**

- **JMRI is required**: z21-Terminal reads roster and consists from JMRI XML files
- **Coexistence**: Both systems can control locomotives simultaneously
- **Complementarity**:
  - **JMRI**: Decoder configuration (DecoderPro), programming track, roster/consist management
  - **z21-Terminal**: Fast terminal control, automation, Python scripting

**Typical workflow**:
1. Configure locomotives and consists in JMRI (DecoderPro)
2. Use z21-Terminal for operational keyboard control
3. Both software can remain open and work together

## Setup

### Hardware
- **Control Station**: Roco Z21 White (192.168.1.111)
- **Software**: JMRI (for roster/consist management - does not need to be running)

### Layout Tracks
- **Inner** (long): 2 synchronized locomotives (address 1 and 5)
- **Outer** (oval): 2 synchronized locomotives (address 6 and 7)

## Locomotives

### Inner Track (Consist 10)
- **1**: Gr.675 017 (Os.kar) - Lead 🔊
- **5**: D645 014 (Rivarossi) - Rear

### Outer Track (Consist 11)
- **6**: D445 1140 (Os.kar) - Rear
- **7**: E656 239 (Rivarossi) - Lead 🔊

### Other Locomotives
- **3**: E656 182 (ACME)
- **4**: 2048 010-9 (Roco ÖBB)

## Main Usage

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

### Interactive Controller ✅
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
- [x] Periodic polling for real-time updates (track power, functions sync with JMRI)
- [ ] Web dashboard for remote control

## Notes

- **Current roster**: 6 locomotives (address 1, 3, 4, 5, 6, 7)
- **Consists**: 2 configured consists (10 and 11), controllable as single unit
- **Speed matching**: Managed manually by user (speed tables CV)
- **Z21 Protocol**:
  - Direct Z21 LAN control (UDP port 21105) ✅
  - Hardware: Z21 White (serial 111466, firmware 1.67)
  - Coexists with JMRI: both can control locomotives simultaneously
  - Read locomotive state (speed, direction, functions F0-F28) implemented
- **CV Operations**: CV read/write to be implemented (via Z21 programming track)

For complete details see `CLAUDE.md` (Italian)
