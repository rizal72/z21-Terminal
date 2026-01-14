# Motor Load Monitoring - Technical Analysis

**Status**: ✅ **PHASE 1-2 COMPLETED** (2025-01-08) | ❌ **Phase 3 NOT FEASIBLE** (2025-01-08)

**Goal**: Monitor motor load and decoder telemetry for preventive maintenance and troubleshooting

---

## Executive Summary

Z21 **already exposes track-level telemetry** (current, voltage, temperature) which is now implemented in Parts 1-2. ESU LokPilot 5 decoders support **RailCom Plus** for per-locomotive telemetry, but Z21 White does NOT expose this data via LAN protocol.

**Implementation Status**:

1. ✅ **Part 1 - COMPLETED (2025-01-08)**: Extended `z21.py` to parse existing Z21 track telemetry
2. ✅ **Part 2 - COMPLETED (2025-01-08)**: Frontend telemetry popovers (hover/click UX)
3. ❌ **Part 3 - NOT FEASIBLE (2025-01-08)**: Z21 White does not support RailCom Plus via LAN (requires Z21 Black/Pro)

---

## Part 1: Z21 Track-Level Telemetry (Already Available!)

### What Z21 Already Sends

Command `LAN_GET_STATUS` (0x10) returns `LAN_STATUS_CHANGED` (0x84) with:

```
Byte offset | Field                  | Size | Description
------------|------------------------|------|----------------------------------
0-1         | MainCurrent            | u16  | Track current (mA)
2-3         | ProgCurrent            | u16  | Programming track current (mA)
4-5         | FilteredMainCurrent    | u16  | Filtered track current (mA)
6-7         | Temperature            | u16  | Z21 internal temp (°C × 10)
8-9         | SupplyVoltage          | u16  | Input voltage (mV)
10-11       | VCCVoltage             | u16  | Logic voltage (mV)
12          | CentralState           | u8   | Status bits (power, estop, etc.)
13          | CentralStateEx         | u8   | Extended status bits
```

**Current Implementation**: `z21.py::get_status()` only parses byte 12 (CentralState), **ignores telemetry data** (bytes 0-11)!

### Implementation Plan (Quick Win - 1-2 hours)

#### Step 1: Extend `z21.py::get_status()`

```python
def get_status(self) -> Optional[dict]:
    """
    Legge stato sistema Z21 + telemetria track-level.

    Returns:
        dict con:
        - track_power_on, emergency_stop, programming_mode, short_circuit
        - telemetry: {
            'main_current_ma': int,          # Track current (mA)
            'filtered_current_ma': int,       # Filtered current (mA)
            'temperature_c': float,           # Z21 temp (°C)
            'supply_voltage_v': float,        # Input voltage (V)
            'vcc_voltage_v': float            # Logic voltage (V)
          }
    """
    self._send_packet(self.LAN_GET_STATUS)
    response = self._receive_packet(timeout=1.0)

    if response:
        header, data = response
        if header == 0x84 and len(data) >= 14:  # Need 14 bytes for full telemetry
            # Parse telemetry (little-endian uint16)
            main_current = struct.unpack('<H', data[0:2])[0]
            prog_current = struct.unpack('<H', data[2:4])[0]
            filtered_current = struct.unpack('<H', data[4:6])[0]
            temperature = struct.unpack('<H', data[6:8])[0]
            supply_voltage = struct.unpack('<H', data[8:10])[0]
            vcc_voltage = struct.unpack('<H', data[10:12])[0]
            central_state = data[12]

            # Parse CentralState bits (existing logic)
            emergency_stop = bool(central_state & 0x01)
            track_power_off = bool(central_state & 0x02)
            short_circuit = bool(central_state & 0x04)
            programming_mode = bool(central_state & 0x08)

            return {
                'track_power_on': not track_power_off,
                'emergency_stop': emergency_stop,
                'programming_mode': programming_mode,
                'short_circuit': short_circuit,
                'telemetry': {
                    'main_current_ma': main_current,
                    'prog_current_ma': prog_current,
                    'filtered_current_ma': filtered_current,
                    'temperature_c': temperature / 10.0,  # Stored as °C × 10
                    'supply_voltage_v': supply_voltage / 1000.0,  # Stored as mV
                    'vcc_voltage_v': vcc_voltage / 1000.0
                }
            }

    return None
```

#### Step 2: Backend API Endpoint

```python
# backend/main.py

@app.get("/api/z21/telemetry")
async def get_z21_telemetry():
    """Get Z21 track-level telemetry (current, voltage, temperature)"""
    try:
        status = z21_manager.z21.get_status()
        if status and 'telemetry' in status:
            return {
                "status": "success",
                "telemetry": status['telemetry'],
                "timestamp": time.time()
            }
        else:
            return {"status": "error", "message": "No telemetry data available"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

#### Step 3: Frontend Display (Optional - can be Phase 9)

```jsx
// Small telemetry widget in header or footer
<div className="telemetry-widget">
  <div className="telemetry-item">
    <i className="fa-solid fa-bolt"></i>
    <span>{telemetry.main_current_ma} mA</span>
  </div>
  <div className="telemetry-item">
    <i className="fa-solid fa-plug"></i>
    <span>{telemetry.supply_voltage_v.toFixed(1)} V</span>
  </div>
  <div className="telemetry-item">
    <i className="fa-solid fa-temperature-half"></i>
    <span>{telemetry.temperature_c.toFixed(1)} °C</span>
  </div>
</div>
```

### Use Cases (Track-Level Telemetry)

1. **Track Power Quality Monitoring**:
   - Alert if voltage drops below 14V (dirty track, poor connection)
   - Alert if current spikes (short circuit risk, excessive load)

2. **Preventive Maintenance**:
   - Track cleaning reminder (voltage trend declining over time)
   - Z21 overheating detection (temperature > 60°C)

3. **Troubleshooting**:
   - Derailment detection (current spike then drop to zero)
   - Power supply issues (voltage unstable)

---

## Part 2: Frontend Implementation ✅ COMPLETED (2025-01-08)

### Component Architecture

**Two new popover components** integrated into Web Dashboard:

1. **TrackTelemetryPopover.jsx** (⚡ badge)
   - Displays track-level telemetry from Z21
   - Shows: Main Current, Supply Voltage, Filtered Current, Track Power state
   - Warning banners for voltage/current issues
   - Auto-refresh every 2 seconds

2. **Z21HealthPopover.jsx** (🖥️ badge)
   - Displays Z21 system health metrics
   - Shows: Temperature, VCC Voltage, Hardware/Firmware info, Serial number
   - Temperature warnings (elevated >50°C, critical >60°C)
   - Static system info panel

### UX Design

**Desktop (≥768px)**:
- **Hover trigger**: Mouse enter shows popover, mouse leave hides
- **No animation**: Instant display for quick reference
- **No backdrop**: Clean, non-intrusive

**Mobile (<768px)**:
- **Tap trigger**: Click badge to toggle popover
- **Backdrop dismiss**: Dark overlay with tap-to-close
- **Slide-in animation**: Smooth entrance

### Visual Feedback

**Warning Indicators**:
- **Amber ring**: `ring-2 ring-amber-500/50` when issues detected
- **Pulsing effect**: Draws attention to warnings
- **Background polling**: Checks telemetry every 5s in background
- **Auto-update**: Badge rings appear/disappear based on current telemetry

**Badge Styling**:
- All status badges now wrapped in boxes (`bg-control-dark`, `px-2 py-2`, `rounded`, `border`)
- Consistent spacing and hover effects
- Disabled state when Z21 offline

### API Integration

**Endpoint**: `/api/z21/telemetry`

**Response Format**:
```json
{
  "status": "success",
  "telemetry": {
    "main_current_ma": 211,
    "prog_current_ma": 0,
    "filtered_current_ma": 184,
    "temperature_c": 2.9,
    "supply_voltage_v": 17.80,
    "vcc_voltage_v": 5.12
  },
  "quality_checks": {
    "voltage_ok": true,
    "voltage_warning": false,
    "current_high": false,
    "temperature_high": false,
    "temperature_elevated": false
  },
  "warnings": [],
  "timestamp": 1704701234.567
}
```

**Quality Thresholds**:
- **Voltage**: 14.0-18.0V normal range
- **Current**: >2000mA considered high (short circuit risk)
- **Temperature**: >50°C elevated, >60°C critical

### Files Modified

- `web/src/App.jsx`: State management, badge event handlers, popover rendering
- `web/src/components/TrackTelemetryPopover.jsx`: New component (155 lines)
- `web/src/components/Z21HealthPopover.jsx`: New component (162 lines)

---

## Part 3: Per-Locomotive Motor Load (RailCom Plus) ❌ NOT FEASIBLE

**Status**: ❌ **NOT FEASIBLE** on Z21 White (HW 0x0203) - Research completed 2025-01-08

### Research Summary (2025-01-08)

After empirical testing, we confirmed that **Z21 White does NOT expose RailCom Plus telemetry via LAN protocol**:

**Test Configuration**:
- Locomotive: Loco 8 (E444 056 - ESU LokPilot 5)
- RailCom enabled: CV29 = 30 (bit 3 set), CV106 = 1 (RailCom Plus enabled)
- Monitoring: 60s with locomotive movement on track
- Broadcast subscription: Flag 0x00000008 (RailCom bit 3)

**Result**: ❌ **Zero 0x0088 packets received**

**Conclusion**:
- RailCom works **internally** (POM read/write confirmed working)
- Z21 White does NOT expose per-locomotive telemetry via LAN
- Per-locomotive motor load monitoring requires **Z21 Black or Z21 Pro** upgrade

**Alternative**: Continue using track-level telemetry (Part 1-2) which provides useful current monitoring for entire layout.

**Scripts Created** (archived for reference):
- `scripts/utils/enable_railcom_plus.py` - Enable RailCom on ESU decoders (CV29, CV106)
- `scripts/utils/test_railcom_listener.py` - Monitor for 0x0088 packets (60s window)

---

### What is RailCom Plus?

RailCom Plus is an **ESU proprietary extension** to RailCom that allows decoders to send telemetry back to the command station:

- **Motor current** (mA) - actual load on motor
- **Decoder voltage** (V) - voltage at decoder input
- **Decoder temperature** (°C) - internal decoder temp
- **Actual speed** (speed steps) - real speed vs commanded (slip detection!)
- **Function states** - confirmation of function activation

### ESU Decoder Support

**Our roster**:
- ✅ **Loco 1** (Gr.675 017): ESU LokSound V4.0 - RailCom Plus supported
- ✅ **Loco 2** (E656 182): ESU LokPilot 5 - RailCom Plus supported
- ✅ **Loco 5** (D645 014): ESU LokPilot 5 - RailCom Plus supported
- ✅ **Loco 6** (D445 1140): ESU LokPilot 5 - RailCom Plus supported
- ✅ **Loco 8** (E444 056): ESU LokPilot 5 - RailCom Plus supported
- ❌ **Loco 7** (E656 239): Hornby TXS - No RailCom support
- ⚠️ **Loco 4** (2048): Zimo MX630 - RailCom supported but NOT RailCom Plus (ESU proprietary)

**Coverage**: 5/7 locomotives (71%) support RailCom Plus telemetry!

### Required CV Configuration (ESU Decoders)

**Enable RailCom** (CV29):
```python
# CV29 bit 3 = 1 (enable RailCom)
# Example: CV29 = 14 (default) → CV29 = 14 | 0x08 = 22
cv29 = z21.read_cv_on_main(address=1, cv_number=29)
if not (cv29 & 0x08):
    z21.write_cv_ops_mode(address=1, cv_number=29, value=cv29 | 0x08)
```

**ESU-Specific RailCom Plus CVs** (CVs 105-106, 112-113):
```
CV105 (Register 105): RailCom configuration
CV106 (Register 106): RailCom Plus enable
CV112-113: Telemetry transmission interval (ms)
```

**Test Script** (`scripts/utils/enable_railcom_plus.py`):
```python
#!/usr/bin/env python3
"""
Enable RailCom Plus on ESU decoder
Usage: python enable_railcom_plus.py <address>
"""
import sys
sys.path.insert(0, '../..')
from z21 import Z21

def enable_railcom_plus(z21, address):
    print(f"🔧 Enabling RailCom Plus on loco {address}...")

    # Read current CV29
    cv29 = z21.read_cv_on_main(address, 29)
    if cv29 is None:
        print("❌ Failed to read CV29")
        return False

    print(f"   Current CV29 = {cv29} (0b{cv29:08b})")

    # Enable RailCom (bit 3)
    if not (cv29 & 0x08):
        new_cv29 = cv29 | 0x08
        print(f"   Setting CV29 = {new_cv29} (enable RailCom)")
        z21.write_cv_ops_mode(address, 29, new_cv29)
    else:
        print("   ✓ RailCom already enabled")

    # ESU-specific: Enable RailCom Plus (CV106)
    # Note: Value depends on decoder model, consult ESU manual
    print(f"   Setting CV106 (RailCom Plus enable)")
    z21.write_cv_ops_mode(address, 106, 1)  # 1 = enable

    print("✅ RailCom Plus enabled")
    return True

if __name__ == '__main__':
    address = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    z21 = Z21(verbose=True)
    try:
        enable_railcom_plus(z21, address)
    finally:
        z21.close()
```

### Z21 LAN Protocol - RailCom Reception

**Critical Question**: Does **Z21 White** (our model) support receiving RailCom data via LAN protocol?

**Z21 Models**:
- **Z21 White** (0x0201): Entry level, 2A output
- **Z21 Black** (0x0202): 3A output, more features
- **Z21 Pro** (0x0211): 4A output, full features including RailCom reception

**LAN Protocol Commands**:
```
LAN_RAILCOM_DATACHANGED (0x0088):
  Broadcast from Z21 when RailCom data received from decoder

  Format:
  [DataLen(2)] [Header(0x88)] [RailComData]

  RailComData structure (needs verification from Z21 protocol doc):
  - Address (2 bytes)
  - Data type (1 byte): 0x01 = Speed, 0x02 = Current, 0x03 = Voltage, etc.
  - Value (2-4 bytes depending on type)
```

**Action Required**:
1. ✅ Check Z21 serial number to confirm model (already have: 111466, HW 0x0203)
   - **Result**: 0x0203 is **Z21 White** with firmware 1.67
2. 🔬 **Test RailCom reception**: Send `LAN_SYSTEMSTATE_DATACHANGED` subscription and monitor for 0x0088 packets
3. 📚 **Read Z21 LAN protocol documentation** (page on RailCom support per model)

**Documentation Link**: https://www.z21.eu/media/Kwc_Basic_DownloadTag_Component/47-2811-3715-customerdata-z21-lan-protokoll-en.pdf (already referenced in z21.py line 8)

---

## Implementation Roadmap

### Phase 1: Track-Level Telemetry (Quick Win - 1-2 hours) ✅ Ready to implement

1. Extend `z21.py::get_status()` to parse telemetry bytes
2. Add `/api/z21/telemetry` backend endpoint
3. Test with `test_z21_telemetry.py` script
4. Optional: Add telemetry widget to frontend header

**Deliverable**: Real-time track current, voltage, Z21 temperature in dashboard

**Use case**: Track power quality monitoring, preventive maintenance alerts

---

### Phase 2: RailCom Research (2-4 hours) 🔬 Feasibility study required

1. **Read Z21 LAN protocol PDF** (section on RailCom support)
   - Verify Z21 White (0x0203) supports RailCom reception via LAN
   - Document packet format for `LAN_RAILCOM_DATACHANGED` (0x0088)

2. **Test RailCom subscription** on Z21 White:
   ```python
   # Subscribe to RailCom broadcasts
   z21._send_packet(0x0050, bytes([0x01, 0x00, 0x00, 0x00]))  # Subscribe to RailCom

   # Monitor for 0x0088 packets
   while True:
       response = z21._receive_packet(timeout=5.0)
       if response:
           header, payload = response
           if header == 0x0088:
               print(f"RailCom data received: {payload.hex()}")
   ```

3. **Enable RailCom Plus on test loco** (address 1 - ESU LokSound):
   - Write CV29 bit 3 = 1
   - Write CV106 = 1 (ESU RailCom Plus enable)
   - Move loco on track, monitor Z21 for 0x0088 packets

**Decision Point**: If Z21 White does NOT support RailCom reception:
- ❌ **Stop here**: Per-loco telemetry not feasible without hardware upgrade
- ✅ **Track-level telemetry** still valuable (Phase 1 completed)

**Decision Point**: If Z21 White DOES support RailCom:
- ✅ **Proceed to Phase 3**: Implement RailCom listener

---

### Phase 3: RailCom Plus Implementation (2-3 days) ⚙️ Conditional on Phase 2 success

#### Step 1: Extend `z21.py` with RailCom listener

```python
class Z21:
    def __init__(self, ...):
        # ...
        self.railcom_callback = None  # User-defined callback for RailCom data

    def set_railcom_callback(self, callback):
        """
        Set callback for RailCom data reception.

        Callback signature: callback(address: int, telemetry: dict)

        telemetry dict:
        {
            'motor_current_ma': int,      # Motor load (mA)
            'decoder_voltage_v': float,   # Voltage at decoder (V)
            'temperature_c': float,       # Decoder temp (°C)
            'actual_speed': int,          # Real speed steps (0-126)
            'commanded_speed': int        # Commanded speed steps
        }
        """
        self.railcom_callback = callback

    def _handle_railcom_packet(self, payload):
        """Parse RailCom Plus packet from Z21"""
        # Parse address (2 bytes)
        address = struct.unpack('<H', payload[0:2])[0]

        # Parse data type (1 byte)
        data_type = payload[2]

        # Parse value based on type
        if data_type == 0x01:  # Speed
            actual_speed = payload[3]
            commanded_speed = payload[4]
            telemetry = {
                'actual_speed': actual_speed,
                'commanded_speed': commanded_speed
            }
        elif data_type == 0x02:  # Current
            motor_current = struct.unpack('<H', payload[3:5])[0]
            telemetry = {'motor_current_ma': motor_current}
        elif data_type == 0x03:  # Voltage
            decoder_voltage = struct.unpack('<H', payload[3:5])[0]
            telemetry = {'decoder_voltage_v': decoder_voltage / 1000.0}
        # ... more types

        # Invoke callback
        if self.railcom_callback:
            self.railcom_callback(address, telemetry)

    def subscribe_railcom(self):
        """Subscribe to RailCom broadcasts from Z21"""
        # Send subscription command (exact format from Z21 protocol doc)
        self._send_packet(0x0050, bytes([0x01, 0x00, 0x00, 0x00]))

    def poll_messages(self, timeout=0.1):
        """
        Non-blocking poll for Z21 messages (including RailCom).
        Call this in a background thread or periodically.
        """
        response = self._receive_packet(timeout=timeout)
        if response:
            header, payload = response
            if header == 0x0088:  # RailCom data
                self._handle_railcom_packet(payload)
            # Handle other broadcast messages
```

#### Step 2: Backend RailCom Manager

```python
# backend/railcom_manager.py

class RailComManager:
    """Manage RailCom Plus telemetry from ESU decoders"""

    def __init__(self, z21_instance):
        self.z21 = z21_instance
        self.telemetry_cache = {}  # address → latest telemetry dict
        self.running = False
        self.thread = None

        # Set Z21 callback
        self.z21.set_railcom_callback(self._on_railcom_data)
        self.z21.subscribe_railcom()

    def _on_railcom_data(self, address, telemetry):
        """Callback invoked by Z21 when RailCom data received"""
        if address not in self.telemetry_cache:
            self.telemetry_cache[address] = {}

        # Merge new telemetry data
        self.telemetry_cache[address].update(telemetry)
        self.telemetry_cache[address]['timestamp'] = time.time()

        # Log interesting events
        if 'motor_current_ma' in telemetry:
            current = telemetry['motor_current_ma']
            if current > 500:  # High current threshold
                print(f"⚠️  Loco {address}: High motor current {current}mA")

    def start(self):
        """Start background thread to poll Z21 for messages"""
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()

    def _poll_loop(self):
        """Background thread: poll Z21 for RailCom messages"""
        while self.running:
            self.z21.poll_messages(timeout=0.1)

    def get_telemetry(self, address):
        """Get latest telemetry for locomotive"""
        return self.telemetry_cache.get(address)

    def stop(self):
        """Stop polling thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
```

#### Step 3: Backend API Endpoints

```python
# backend/main.py

railcom_manager = None  # Initialized at startup if Z21 supports RailCom

@app.get("/api/railcom/telemetry/{address}")
async def get_loco_telemetry(address: int):
    """Get latest RailCom Plus telemetry for locomotive"""
    if not railcom_manager:
        return {"status": "error", "message": "RailCom not supported"}

    telemetry = railcom_manager.get_telemetry(address)
    if telemetry:
        return {"status": "success", "address": address, "telemetry": telemetry}
    else:
        return {"status": "error", "message": "No telemetry data for this locomotive"}

@app.get("/api/railcom/status")
async def get_railcom_status():
    """Check if RailCom Plus is supported and active"""
    return {
        "supported": railcom_manager is not None,
        "active_locos": list(railcom_manager.telemetry_cache.keys()) if railcom_manager else []
    }
```

#### Step 4: Frontend Display

```jsx
// components/LocomotiveTelemetry.jsx
export default function LocomotiveTelemetry({ address, apiUrl }) {
  const [telemetry, setTelemetry] = useState(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      const response = await fetch(`${apiUrl}/api/railcom/telemetry/${address}`);
      const data = await response.json();
      if (data.status === 'success') {
        setTelemetry(data.telemetry);
      }
    }, 1000);  // Poll every 1s

    return () => clearInterval(interval);
  }, [address, apiUrl]);

  if (!telemetry) return null;

  return (
    <div className="telemetry-panel">
      <h4>Loco {address} Telemetry</h4>
      {telemetry.motor_current_ma && (
        <div className="telemetry-row">
          <span>Motor Current:</span>
          <span className={telemetry.motor_current_ma > 500 ? 'alert' : ''}>
            {telemetry.motor_current_ma} mA
          </span>
        </div>
      )}
      {telemetry.decoder_voltage_v && (
        <div className="telemetry-row">
          <span>Decoder Voltage:</span>
          <span>{telemetry.decoder_voltage_v.toFixed(1)} V</span>
        </div>
      )}
      {telemetry.temperature_c && (
        <div className="telemetry-row">
          <span>Temperature:</span>
          <span className={telemetry.temperature_c > 70 ? 'alert' : ''}>
            {telemetry.temperature_c.toFixed(1)} °C
          </span>
        </div>
      )}
      {telemetry.actual_speed !== undefined && (
        <div className="telemetry-row">
          <span>Speed (actual/commanded):</span>
          <span>{telemetry.actual_speed} / {telemetry.commanded_speed}</span>
          {telemetry.actual_speed < telemetry.commanded_speed - 5 && (
            <span className="alert">⚠️  Wheel slip detected!</span>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## Use Cases (Per-Locomotive Telemetry)

### 1. Motor Load Monitoring
**Problem**: Dirty gears, binding mechanisms increase motor load
**Solution**: Alert if motor current > 500mA (indicates excessive load)
**Action**: Maintenance reminder (lubrication, cleaning)

### 2. Wheel Slip Detection
**Problem**: Locomotive wheels slip on dirty track, actual speed < commanded
**Solution**: Compare `actual_speed` vs `commanded_speed`, alert if delta > 5 steps
**Action**: Track cleaning reminder, reduce speed automatically

### 3. Decoder Overheating
**Problem**: Decoder temperature > 70°C can cause thermal shutdown
**Solution**: Real-time temperature monitoring, alert if approaching limit
**Action**: Reduce speed, increase ventilation, check motor load

### 4. Voltage Drop Detection
**Problem**: Track resistance causes voltage drop at distant track sections
**Solution**: Monitor `decoder_voltage_v`, alert if < 12V
**Action**: Track cleaning, improve power distribution (feeders)

### 5. Consist Load Balancing
**Problem**: In Virtual Mode, one loco may be working harder (higher current)
**Solution**: Compare motor current between lead/rear, adjust speed compensation
**Action**: Fine-tune Virtual Mode algorithm based on actual load data

---

## Testing Plan

### Phase 1 Testing (Track-Level Telemetry)

```bash
# Test script
cd scripts/utils
python test_z21_telemetry.py

# Expected output:
# ✅ Track current: 245 mA
# ✅ Supply voltage: 16.2 V
# ✅ Z21 temperature: 34.5 °C
```

### Phase 2 Testing (RailCom Reception)

```bash
# 1. Enable RailCom on test loco
python enable_railcom_plus.py 1

# 2. Monitor for RailCom packets
python test_railcom_listener.py

# Expected output (if supported):
# ✅ RailCom subscription active
# 🔊 Waiting for RailCom data...
# ✅ Loco 1: Motor current = 123 mA
# ✅ Loco 1: Decoder voltage = 14.8 V

# OR (if not supported):
# ❌ No RailCom packets received after 30s
# ⚠️  Z21 White may not support RailCom reception via LAN
```

### Phase 3 Testing (End-to-End)

1. Start backend with RailCom manager
2. Open dashboard, select loco with ESU decoder
3. Verify telemetry panel appears with real-time data
4. Test alerts:
   - Increase speed → verify motor current increases
   - Stop loco on dirty track → verify wheel slip alert
   - Run at high speed for 5 min → verify temperature increases

---

## Limitations & Known Issues

### Z21 White Hardware Limitations
- May not support RailCom reception via LAN (needs verification)
- If unsupported, requires hardware upgrade to Z21 Black or Z21 Pro

### Decoder Limitations
- **Hornby TXS** (loco 7): No RailCom support at all
- **Zimo MX630** (loco 4): RailCom supported but NOT RailCom Plus (no motor current telemetry)
- Only **ESU decoders** (5/7 locos) support full telemetry

### Protocol Limitations
- RailCom data transmission is **periodic** (not real-time), typical interval 1-5s
- Data may be lost if multiple locos transmit simultaneously (RailCom collision)
- Not all telemetry types may be supported by Z21 White (needs testing)

---

## Cost-Benefit Analysis

### Phase 1 (Track-Level Telemetry)
- **Effort**: 1-2 hours
- **Cost**: Zero (uses existing Z21 data, just parsing)
- **Benefit**: Track power quality monitoring, Z21 health monitoring, troubleshooting
- **Decision**: ✅ **DO IT** - Quick win, no risk

### Phase 2 (RailCom Research)
- **Effort**: 2-4 hours (reading docs, testing)
- **Cost**: Zero (just research)
- **Benefit**: Determine feasibility of per-loco telemetry
- **Decision**: ✅ **DO IT** - Low effort, critical decision point

### Phase 3 (RailCom Plus Implementation)
- **Effort**: 2-3 days
- **Cost**: High (dev time), Risk (may not work if Z21 doesn't support)
- **Benefit**: Per-loco motor load, wheel slip detection, preventive maintenance
- **Decision**: ⚠️ **CONDITIONAL** - Only if Phase 2 confirms Z21 support
  - If supported: ✅ Very valuable for 5/7 locos
  - If not supported: ❌ Don't waste time, Phase 1 telemetry is sufficient

---

## Next Steps

1. ✅ **Implement Phase 1** (track-level telemetry) - Quick win, no risk
2. 🔬 **Research Phase 2** (RailCom support verification)
   - Read Z21 LAN protocol PDF (RailCom section)
   - Test RailCom listener script
   - Document findings
3. ⏸️ **Decide on Phase 3** based on Phase 2 results
   - If Z21 supports RailCom: Implement Phase 3
   - If not: Stop at Phase 1, consider hardware upgrade in future

---

**Last Updated**: 2025-01-08
**Author**: Claude Sonnet 4.5 + Riccardo Sallusti
**Status**: Ready for Phase 1 implementation
