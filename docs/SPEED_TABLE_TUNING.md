# Speed Table Auto-Tuning

**Obiettivo principale del progetto z21-Terminal**

## Overview

Automatically calibrate locomotive decoder speed tables (CV67-94) using real-world YOLO tracking data to achieve perfect speed matching across entire speed range.

**Core Problem**: Manual CV tuning is time-consuming and imprecise. Even with matched locomotives, non-linear motor characteristics cause speed drift at different speed steps.

**Solution**: Track Δt (speed delta between consist locomotives) at each speed setting, automatically adjust CV speed table values to eliminate drift.

---

## Why Speed Tables Over Global CVs?

**Global CV Adjustment (Mode 2)** - Limited effectiveness:
- CV2 (Vstart): Affects only minimum speed
- CV5 (Vmax): Affects only maximum speed
- CV6 (Vmid): Single midpoint adjustment
- ❌ **Cannot correct non-linear behavior** (e.g., loco 7 stable at speed 40-60 but drifts at 80+)

**Speed Table CV Adjustment** - Precision tuning:
- CV29 bit 4 = 1: Enable speed table mode
- CV67-94: 28 independent speed steps (0-127 range each)
- ✅ **Corrects every speed step independently**
- ✅ **Handles non-linear motor curves**
- ✅ **Fixes hardware issues** (e.g., loco 7 capacitor detachment)

---

## Use Case: Loco 7 Hardware Issue

**Background** (from `docs/CONSIST_ROSTER.md`):
- Loco 7 (E656 239, Hornby TXS decoder): Micro SMD capacitor detached from PCB
- Impact: Unstable motor power, erratic speed behavior
- Current workaround: Virtual Mode (software compensation via CV19)

**Speed Table Tuning Advantage**:
- Calibrate decoder DIRECTLY instead of software compensation
- Permanent fix in decoder (works even without z21-Terminal running)
- Optimal for non-linear issues: stable at low speeds, drifts at high speeds

**Example Calibration**:
```
Speed 20 (CV67): Δt avg +0.5s → Loco 7 slower → Increase CV67 by +3
Speed 40 (CV69): Δt avg -0.3s → Loco 7 faster → Decrease CV69 by -2
Speed 80 (CV77): Δt avg -1.2s → Loco 7 MUCH faster → Decrease CV77 by -8
```

Result: Perfect speed matching across ALL speed steps, eliminating need for Virtual Mode.

---

## Implementation Strategy

### Phase 1: Speed Tracking & Correlation Analytics (v1.3) ✅ COMPLETED

**Status**: ✅ **IMPLEMENTED** (2026-01-15) - Live in production

**Goal**: Collect speed setting data with Δt measurements and visualize correlation

**Data Model**:
```python
# New event type: speed_change
{
  "event_type": "speed_change",
  "timestamp": 1736900000,
  "session_id": "20260115_143000",
  "data": {
    "consist_id": 11,
    "speed": 80,  # DCC speed setting (0-126)
    "direction": "forward"
  }
}

# Enhanced delta_t events with speed correlation
{
  "event_type": "delta_t",
  "timestamp": 1736900015,
  "session_id": "20260115_143000",
  "data": {
    "consist_id": 11,
    "delta_t": -1.23,
    "speed": 80  # Current speed at gate crossing
  }
}
```

**Backend Changes**:
- Track consist speed in WebSocket handler (`backend/main.py`)
- Log `speed_change` events on speed slider updates
- Add `speed` field to `delta_t` events
- New API endpoint: `GET /api/analytics/speed-correlation?consist_id=<id>`

**Frontend Changes**:
- Analytics tab: New chart "Δt by Speed" (scatter plot or grouped bar)
- X-axis: Speed bins (0-9, 10-19, ..., 120-126)
- Y-axis: Average Δt with error bars (min/max range)
- Color-coded: Green (<1.0s), Amber (1.0-1.5s), Red (≥1.5s)

**Implementation Results** (2026-01-15):

✅ **Backend** (3 files modified):
- `ws_control.py`: Speed event logging (`speed_setting` event type)
- `analytics_db.py`: `get_speed_correlation()` with "Next N Events" strategy (N=10 default)
- `routers/analytics.py`: `/api/analytics/speed-correlation` endpoint

✅ **Frontend** (4 files):
- `SpeedCorrelationChart.jsx`: NEW scatter chart with error bars + dynamic reference lines
- `AnalyticsPanel.jsx`: 4th tab "Speed Tuning" (187 lines added)
- `analyticsHelpers.js`: 3 helper functions (no hardcoded thresholds)
- `analyticsConstants.js`: `SPEED_STATUS_COLORS` constants

✅ **Database Migrations**:
- Migration 1: Added `speed: 70` to 352 historical delta_t events
- Migration 2: Created 2 `speed_setting` events (C10, C11: 0→70 at session start)
- Backups: `analytics.db.backup_20260115_151846.backup`, `analytics.db.backup_20260115_163137.backup`

✅ **Production Testing**:
- Consist 10 @ speed 70: Mean Δt +1.07s (±0.60s) - 50% SYNCED, 30% CRITICAL
- Consist 11 @ speed 70: Mean Δt -0.80s (±1.15s) - 60% SYNCED, 30% CRITICAL
- Status: Both under action threshold (1.5s) → "All speeds well synchronized!"

**Key Features**:
- ✅ "Next N Events" correlation (adaptive to track length differences)
- ✅ Dynamic thresholds from config.json (no hardcoding)
- ✅ Color-coded scatter points by dominant status
- ✅ Error bars showing standard deviation
- ✅ Summary cards (speed changes, samples, buckets)
- ✅ Generic CV recommendations (Phase 1 scope: text only)
- ✅ Consist filter enforcement (must select C10 or C11)

---

### Phase 2: Specific CV Recommendations with JMRI Roster Integration (v1.4)

**Status**: ⏳ **PLANNED** - Enhancement to Phase 1 (not yet implemented)

**Goal**: Provide specific CV recommendations with exact before/after values and JMRI-style step numbering

**Enhancement Motivation** (discussed 2026-01-15):
- ✅ CV speed table values ALREADY in JMRI roster (CV67-94)
- ✅ Can read them like other roster data (already implemented)
- ✅ JMRI uses 1-28 step numbering (more user-friendly than CV67-94)
- ✅ Enable specific recommendations: "Step 16 (CV82): 128 → 135 (+7)" instead of generic text

**JMRI Speed Table Mapping**:
```python
# DCC Speed (0-126) → JMRI Step (1-28) → CV Index (67-94)
dcc_speed = 70
step_index = dcc_speed // 4.5  # 70 // 4.5 = 15
jmri_step = step_index + 1      # 16 (JMRI numbering starts at 1)
cv_index = 67 + step_index      # CV82

# Example speed ranges per JMRI step:
# Step 1  (CV67): Speed 0-4
# Step 2  (CV68): Speed 5-9
# ...
# Step 16 (CV82): Speed 68-72  ← Speed 70 falls here
# ...
# Step 28 (CV94): Speed 122-126
```

**Enhanced Data Model**:
```python
# Backend: Extend speed_correlation API response with CV data
{
    "consist_id": 11,
    "adjust_loco_address": 8,  # Rear loco in consist 11 (E444 056)
    "speed_buckets": [
        {
            "speed_bucket": 70,
            "mean_delta_t": -0.80,
            "std_dev": 0.60,
            "samples": 10,
            # NEW FIELDS:
            "jmri_step": 16,           # Human-readable step number
            "cv_index": 82,             # Actual CV to modify
            "current_cv_value": 128,    # Read from JMRI roster
            "recommended_cv_value": 135, # Calculated adjustment
            "cv_delta": +7,             # +7 to speed up adjust loco
            "recommendation": "Adjust loco is faster. Decrease CV82 by 7."
        }
    ]
}
```

**Backend Implementation**:
```python
def get_speed_correlation_with_cv_data(consist_id: int):
    """
    Enhanced speed correlation with CV-specific recommendations.
    Reads current CV values from JMRI roster for adjust loco.
    """
    # Get basic correlation data (Phase 1)
    correlation = get_speed_correlation(consist_id)

    # Load consist config to identify adjust loco
    config = load_config()
    consist = config['consists'][str(consist_id)]
    adjust_loco_address = consist['rear_address']  # Adjust = rear

    # Read CV speed table from JMRI roster (CV67-94)
    cv_speed_table = read_cv_speed_table_from_roster(adjust_loco_address)
    # Returns: {67: 12, 68: 24, ..., 94: 255}

    # Enhance each speed bucket with CV data
    for bucket in correlation['speed_buckets']:
        speed = bucket['speed_bucket']
        mean_delta_t = bucket['mean_delta_t']

        # Map speed to JMRI step
        step_index = int(speed // 4.5)
        jmri_step = step_index + 1
        cv_index = 67 + step_index

        # Get current CV value
        current_cv = cv_speed_table.get(cv_index, 128)  # Default 128 if missing

        # Calculate recommended adjustment
        # Δt > 0: adjust loco slower → increase CV (speed up)
        # Δt < 0: adjust loco faster → decrease CV (slow down)
        cv_delta = calculate_cv_adjustment(mean_delta_t)
        recommended_cv = max(0, min(255, current_cv + cv_delta))

        # Add CV-specific fields
        bucket['jmri_step'] = jmri_step
        bucket['cv_index'] = cv_index
        bucket['current_cv_value'] = current_cv
        bucket['recommended_cv_value'] = recommended_cv
        bucket['cv_delta'] = cv_delta

    correlation['adjust_loco_address'] = adjust_loco_address
    return correlation

def calculate_cv_adjustment(mean_delta_t: float) -> int:
    """
    Convert mean Δt to CV adjustment.

    Δt = rear_time - lead_time
    Δt > 0: Adjust loco is slower (arrives late) → increase CV to speed up
    Δt < 0: Adjust loco is faster (arrives early) → decrease CV to slow down

    Scale: ~0.2s Δt ≈ ±1 CV value (empirical, tune based on testing)
    """
    adjustment = int(mean_delta_t / 0.2)  # 0.2s per CV step
    return max(-20, min(20, adjustment))  # Safety clamp ±20
```

**Frontend UI Enhancement**:

**BEFORE** (Phase 1 - generic text):
```
Speed 70: Adjust loco is faster (-0.80s)
Consider decreasing CV speed table for adjust loco at this speed
```

**AFTER** (Phase 2 - specific values):
```
╔════════════════════════════════════════════════════════════╗
║ Speed 70 (68-72 range)                                     ║
║ JMRI Step 16 │ CV82                                        ║
╠════════════════════════════════════════════════════════════╣
║ Current Value:     128                                     ║
║ Recommended:       124  (-4)                               ║
║                                                            ║
║ Reason: Adjust loco arrives 0.80s early at this speed     ║
║ Action: Decrease CV82 by 4 to slow down adjust loco       ║
╚════════════════════════════════════════════════════════════╝

[Preview All Changes] [Apply via Operations Mode]
```

**UI Components**:
- Card layout with JMRI step number prominent
- Before/after CV value comparison
- Visual diff indicator (+/- with color)
- Clear reasoning text
- Preview button (show all changes before applying)
- Apply button (Phase 3 - writes CV via Operations Mode)

**Benefits**:
- ✅ User sees EXACT CV to change (no guessing)
- ✅ JMRI step numbering matches DecoderPro UI (cognitive alignment)
- ✅ Before/after preview reduces mistakes
- ✅ Foundation for Phase 3 (automatic CV writes)

**CV Harmonization/Smoothing** (JMRI Feature):

JMRI DecoderPro includes a critical feature when modifying speed table CVs: **automatic harmonization of adjacent CVs** to maintain a smooth velocity curve.

**How It Works**:
- When you modify a single CV (e.g., CV82 from 128 → 135), JMRI offers checkboxes to "harmonize before" and "harmonize after"
- You select the range (e.g., 3 steps before, 3 steps after)
- JMRI interpolates/smooths adjacent CV values to create a gradual transition
- **Purpose**: Avoid "jerks" or discontinuities in locomotive movement when speed table has abrupt value changes

**Example**:
```
BEFORE harmonization:
Step 13 (CV79): 100
Step 14 (CV80): 110
Step 15 (CV81): 120
Step 16 (CV82): 128 → 135 (user changes +7)
Step 17 (CV83): 140
Step 18 (CV84): 150
Step 19 (CV85): 160

AFTER harmonization (3 steps before/after):
Step 13 (CV79): 102  (+2)  ← interpolated
Step 14 (CV80): 112  (+2)  ← interpolated
Step 15 (CV81): 122  (+2)  ← interpolated
Step 16 (CV82): 135  (+7)  ← user change
Step 17 (CV83): 143  (+3)  ← interpolated
Step 18 (CV84): 152  (+2)  ← interpolated
Step 19 (CV85): 161  (+1)  ← interpolated
```

**Phase 2 Implementation Options**:

**Option A** (Simpler - Recommended):
- Our tool shows specific CV recommendations: "CV82: 128 → 135 (+7)"
- User applies changes manually via JMRI DecoderPro
- JMRI handles harmonization automatically with its UI checkboxes
- **Pros**: Leverage existing JMRI feature, less code complexity, user maintains control
- **Cons**: Requires JMRI for applying changes (but we already use it for roster management)

**Option B** (Standalone):
- Implement smoothing algorithm in our tool
- UI includes "Harmonize" checkbox with range selector (±N steps)
- Calculate interpolated values for adjacent CVs
- Apply all CV writes via Operations Mode (Phase 3 prerequisite)
- **Pros**: Fully standalone, no JMRI required for tuning
- **Cons**: More complex implementation, need to replicate JMRI's proven algorithm

**Recommendation**: Start with **Option A** for Phase 2. If user feedback demands standalone capability, implement Option B in Phase 3 alongside auto-tuning.

---

### Phase 3: Auto-Tuning (v1.5)

**Goal**: Apply CV adjustments via Operations Mode programming

**Safety Features**:
- **Dry-run mode**: Preview all changes before applying
- **Confirmation dialog**: Show all CV writes with before/after values
- **Backup**: Save current CV values to file before modifying
- **Rollback**: Restore from backup if results unsatisfactory
- **Incremental**: Apply 50% of recommended adjustment first, iterate

**Implementation**:
```python
async def auto_tune_speed_table(consist_id: int, dry_run: bool = True):
    """
    Auto-tune speed table CVs based on analytics
    """
    config = load_config()
    consist = config["consists"][str(consist_id)]
    rear_address = consist["rear_address"]  # Adjust rear loco

    # Analyze Δt distribution
    analysis = analyze_speed_table(consist_id, min_samples=10)

    # Read current CV values (backup)
    current_cvs = {}
    for step, data in analysis.items():
        cv_index = data["cv_index"]
        current_cvs[cv_index] = await read_cv_on_main(rear_address, cv_index)

    # Calculate new CV values
    new_cvs = {}
    for step, data in analysis.items():
        cv_index = data["cv_index"]
        current = current_cvs[cv_index]
        adjustment = data["recommended_adjustment"]
        new_value = max(0, min(255, current + adjustment))  # Clamp 0-255
        new_cvs[cv_index] = new_value

    if dry_run:
        return {"current": current_cvs, "new": new_cvs, "analysis": analysis}

    # Apply changes (Operations Mode)
    for cv_index, new_value in new_cvs.items():
        await write_cv_ops_mode(rear_address, cv_index, new_value)
        await asyncio.sleep(0.5)  # Rate limit

    return {"success": True, "cvs_modified": len(new_cvs)}
```

**Frontend UI**:
- Button: "Auto-Tune Speed Table" (Reports tab)
- Step 1: Preview modal with CV changes table
- Step 2: Confirmation checkbox "I have backed up my decoder settings"
- Step 3: Progress bar during CV writes (28 CVs × 0.5s = ~14s)
- Step 4: Success message with "Test & Rollback" button

### Phase 4: Validation & Iteration (v1.6)

**Goal**: Verify tuning effectiveness, iterate if needed

**Process**:
1. Apply tuning → Run test session → Collect new Δt data
2. Compare before/after statistics (avg Δt, synced %, critical events)
3. If improved but not perfect → Apply 50% of remaining error
4. Repeat until target achieved (e.g., 95% SYNCED across all speeds)

**Analytics Dashboard**:
- "Before/After" comparison chart
- Session comparison: Pre-tuning vs Post-tuning
- Speed step heatmap: Δt distribution across 28 steps

---

## Technical Considerations

### CV Read/Write Compatibility

**Operations Mode (POM)**:
- ✅ **ESU LokPilot/LokSound** (Loco 1, 2, 5, 6, 8): Full read/write support
- ⚠️ **Hornby TXS** (Loco 7): Write OK, Read via Bluetooth app only
- Solution: Manual CV backup for Hornby before tuning

**Programming Track** (alternative):
- Requires physical isolation of locomotive
- Full read/write for all decoders
- NOT practical for frequent tuning

### Data Quality Requirements

**Minimum samples per speed step**:
- 10+ gate crossings per speed step for reliable statistics
- Mixed session data (multiple dates) to avoid environmental bias
- Balanced speed distribution (avoid over-sampling certain speeds)

**Filtering anomalies**:
- Exclude critical events (|Δt| ≥ 3.0s) from auto-tuning calculations
- Remove outliers: Values beyond 2× standard deviation
- Require consistent direction (forward/reverse tracked separately)

### Safety & Rollback

**Pre-tuning checklist**:
- [ ] Backup current CV values (CV2, CV5, CV6, CV67-94)
- [ ] Verify decoder compatibility (ESU recommended)
- [ ] Test read_cv_on_main() succeeds for target locomotive
- [ ] Close JMRI (avoid concurrent CV writes)

**Rollback procedure**:
1. Keep backup file: `data/cv_backups/loco_<addr>_<timestamp>.json`
2. UI button: "Restore Backup" in Speed Table Analysis section
3. Write all CVs from backup file
4. Verify restoration with read_cv_on_main()

---

## Expected Results

### Loco 7 (Consist 11) - Primary Use Case

**Current behavior** (hardware issue - capacitor detached):
- Speed 40-60: Mostly stable (avg Δt -0.3s to -0.5s)
- Speed 80+: Severe drift (avg Δt -1.2s to -3.5s)
- Variability: 6.6s range (-3.52s to +1.09s) in worst sessions

**After speed table tuning** (expected):
- All speeds 0-126: avg Δt within ±0.5s (SYNCED)
- Critical events: <5% of gate crossings (currently 15-30%)
- Consistency: <2.0s range across all speeds

**Alternative to Virtual Mode**:
- Virtual Mode: Real-time CV19 compensation (software workaround)
- Speed Table: Permanent decoder calibration (hardware fix)
- Benefit: Works even when z21-Terminal offline, lower CPU overhead

### Consist 10 - Optimization

**Current behavior** (already well-matched):
- Mostly SYNCED across speed range
- Occasional drift at extreme speeds (0-20, 100-126)

**After tuning**:
- Further optimization: 98%+ SYNCED at all speeds
- Eliminate remaining edge cases

---

## Future Enhancements

### Adaptive Tuning (v2.0)
- Continuous monitoring: Detect CV drift over time (decoder aging, motor wear)
- Auto-suggest re-tuning when Δt trends worsen
- Machine learning: Predict optimal CVs based on historical patterns

### Multi-Consist Support
- Batch tuning: Analyze all consists, apply adjustments simultaneously
- Cross-consist comparison: Identify common problematic speed steps

### Direction-Specific Tuning
- Separate speed tables for forward/reverse (CV29 bit 5)
- Some motors behave differently by direction

### Load Compensation
- Track Δt with/without train load (empty consist vs full train)
- Adjust CVs for typical operating conditions

---

## References

- **CV Operations Mode**: `docs/Z21_PROTOCOL.md` - POM read/write implementation
- **Loco 7 Hardware Issue**: `docs/CONSIST_ROSTER.md` - Capacitor detachment details
- **YOLO Tracking System**: `docs/COMPUTER_VISION.md` - Gate timing & Δt calculation
- **Analytics Dashboard**: `docs/WEB_DASHBOARD.md` - UI/UX patterns for speed correlation charts
- **Decoder Compatibility**: `docs/Z21_PROTOCOL.md` - ESU vs Hornby CV support

---

## Appendix: NMRA Speed Table Standard

**CV29 Configuration**:
- Bit 4 = 1: Use speed table (CV67-94)
- Bit 4 = 0: Use 3-point curve (CV2, CV5, CV6)

**Speed Table CVs** (CV67-94):
- 28 steps covering 0-126 speed range
- Each CV value: 0-255 (actual motor PWM voltage)
- Linear default: CV67=9, CV68=18, ..., CV94=255
- Custom curves: Adjust individual steps for non-linear motors

**Mapping DCC Speed to CV**:
```python
# DCC speed 0-126 → 28 steps (0-27)
step = dcc_speed // 4.5
cv_index = 67 + step

# Example:
# Speed 0-4 → CV67 (step 0)
# Speed 5-9 → CV68 (step 1)
# ...
# Speed 122-126 → CV94 (step 27)
```

**ESU Decoder Notes**:
- Full speed table support (all decoders)
- Can read/write via Operations Mode (POM)
- Advanced features: 128-step tables (proprietary)

**Hornby TXS Notes**:
- Speed table support (CV29 bit 4)
- Write via Operations Mode OK
- Read requires Bluetooth app (POM read not supported)
