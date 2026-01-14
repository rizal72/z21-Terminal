# Consist Configuration & Locomotive Roster

**Last Updated**: 2025-01-03  
**Project**: z21-Terminal - BiancAlice Railway Layout

This document contains the complete configuration of consists and locomotive roster for the BiancAlice DCC layout.

---

## Consist Configuration

### Consist 10 - TRACCIATO INTERNO
- **Address**: 10 (DAC software-based)
- **Lead**: Address 1 - Gr.675 017 (ESU LokSound V4.0 🔊)
- **Rear**: Address 5 - D645 014 (ESU LokPilot 5 DCC)

### Consist 11 - TRACCIATO ESTERNO
- **Address**: 11 (DAC software-based)
- **Lead**: Address 7 - E656 239 (Hornby TXS 🔊)
- **Rear**: Address 8 - E444 056 (ESU LokPilot 5 DCC ✅)

**Note**:
- CV19 non usata (consist gestito via software)
- Locomotive in consist: NON controllabili singolarmente per movimento
- File config: `~/Library/Preferences/JMRI/.../roster/consist/consist.xml`

---
## Roster Locomotive

### TRACCIATO INTERNO - Consist 10

#### 1. Gr.675 017 (Os.kar OS1806) - LEAD 🔊
- **Address DCC**: 1
- **Role**: Lead locomotive (consist 10)
- **Decoder**: ESU LokSound V4.0
- **Speed Control CV**: Vstart=2, Vmid=56, Vhigh=132
- **Lettura CV**: ✅ OK (operations mode)

#### 2. D645 014 (Rivarossi HR2933) - REAR
- **Address DCC**: 5
- **Role**: Rear locomotive (consist 10)
- **Decoder**: ESU LokPilot 5 DCC
- **Speed Control CV**: Vstart=2, Vmid=48, Vhigh=110
- **Nota**: Profilo Rivarossi STANDARD (reference)

### TRACCIATO ESTERNO - Consist 11

#### 3. E656 239 (Rivarossi HR2966S) - LEAD 🔊
- **Address DCC**: 7
- **Role**: Lead locomotive (consist 11)
- **Decoder**: Hornby TXS Class 91 Electric
- **Speed Control CV**: Vstart=2, Vmid=48, Vhigh=110
- **Lettura CV**: ❌ NO (decoder Hornby TXS non supporta ops mode)
  - Lettura via: programming track o app Hornby Bluetooth
  - Scrittura CV: ✅ OK anche in operations mode

**⚠️ KNOWN HARDWARE ISSUE - SMD Capacitor Detached**

**Problem**: Micro SMD capacitor (~0.5mm) detached from PCB board during maintenance
- **Location**: Peripheral side of PCB (opposite decoder), near short edge (tail/head end)
- **Function**: Power smoothing/filtering capacitor for motor drive circuit
- **Impact**: Erratic speed behavior despite constant speed setting (70%)

**Symptoms** (Analytics Data - 2026-01-12 to 2026-01-14):
- **Unstable dT values**: Ranges from -3.52s to +1.09s (6.6 seconds variability!)
- **Average dT trends**: Fluctuates between BALANCED (-0.06s) and CRITICAL (-1.23s)
- **Worst session**: 2026-01-14 avg dT = -1.23s, only 51.6% SYNCED
- **Pattern**: Chronically unstable since first tracking session (no sudden change)

**Root Cause**: Without smoothing capacitor:
- Unstable motor power supply → speed fluctuates even at constant DCC speed
- Electrical noise on DCC signal → decoder reads commands less reliably
- Temperature sensitivity → behavior varies with ambient conditions
- Unfiltered voltage spikes → random micro-accelerations/decelerations

**Why Not Fixed**:
- Capacitor available but too small (~0.5mm) for manual soldering
- Requires professional SMD rework tools (microscope, fine tip iron, steady hands)
- **Cannot replace decoder**: Sound decoder (most expensive component)
- Professional repair possible but system workaround functional

**Current Workaround**: ✅ **Virtual Mode Active**
- Real-time speed compensation via Z21 protocol
- System automatically adjusts for erratic behavior
- Analytics tracking validates compensation effectiveness
- Acceptable performance for daily operations

**Historical Note**: This hardware issue was the primary motivation for developing the YOLO-based tracking system and Virtual Consist Mode with automatic speed compensation.

#### 4. E444 056 (ACME 60108) - REAR 🔧
- **Address DCC**: 8
- **Role**: Rear locomotive (consist 11)
- **Decoder**: ESU LokPilot 5 DCC ✅ (sostituito 2025-12-27)
- **Decoder originale**: Zimo MX690S (SW v20)
- **Speed Control CV**: Vstart=2, Vmid=48, Vhigh=255
- **Speed Table**: CV67-94 custom (importata da Zimo)
- **Consist CV**: CV21=51, CV22=51 (F0+F3+F4 attive)

### Altre Locomotive

#### 5. E656 182 (ACME 60397) 🔄
- **Address DCC**: 2 (cambiato da 3 il 2025-12-27)
- **Decoder**: ESU LokPilot 5 DCC
- **Speed Control CV**: Vstart=3, Vmid=63, Vhigh=148

#### 6. D445 1140 (Os.kar 1128)
- **Address DCC**: 6
- **Decoder**: ESU LokPilot 5 DCC
- **Speed Control CV**: Vstart=2, Vmid=72, Vhigh=144

### Riepilogo Roster

| Address | Locomotiva | Decoder | Consist |
|---------|------------|---------|---------|
| 1 | Gr.675 017 | ESU LokSound V4.0 🔊 | 10 Lead |
| 2 | E656 182 | ESU LokPilot 5 | - |
| 3 | - (libero) | - | - |
| 5 | D645 014 | ESU LokPilot 5 | 10 Rear |
| 6 | D445 1140 | ESU LokPilot 5 | - |
| 7 | E656 239 | Hornby TXS 🔊 | 11 Lead |
| 8 | E444 056 | ESU LokPilot 5 ✅ | 11 Rear |
| 10 | Consist interno | - | DAC |
| 11 | Consist esterno | - | DAC |

**Totale locomotive operative**: 6 (loco 4 esclusa - non utilizzata)  
**Consist configurati**: 2

---

