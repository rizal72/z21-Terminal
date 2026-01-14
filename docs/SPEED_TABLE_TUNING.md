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

### Phase 1: Speed Tracking (v1.3)

**Goal**: Collect speed setting data with Δt measurements

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

### Phase 2: Speed Table Analysis (v1.4)

**Goal**: Aggregate Δt data per speed step, identify problematic CVs

**Algorithm**:
```python
def analyze_speed_table(consist_id: int, min_samples: int = 10):
    """
    Analyze Δt distribution per speed step
    Returns: Dict[speed_step, SpeedAnalysis]
    """
    # Group delta_t events by speed bins (28 bins, 0-126 range)
    speed_bins = {}  # speed_step (0-27) → List[delta_t]

    for event in get_delta_t_events(consist_id):
        speed_step = event.speed // 4.5  # Map 0-126 to 0-27
        speed_bins[speed_step].append(event.delta_t)

    # Calculate statistics per speed step
    results = {}
    for step, deltas in speed_bins.items():
        if len(deltas) < min_samples:
            continue  # Insufficient data

        results[step] = {
            "avg_delta_t": mean(deltas),
            "std_dev": std(deltas),
            "samples": len(deltas),
            "cv_index": 67 + step,  # CV67-94
            "recommended_adjustment": calculate_adjustment(mean(deltas))
        }

    return results

def calculate_adjustment(avg_delta_t: float) -> int:
    """
    Convert Δt to CV adjustment

    Δt > 0: Rear loco faster → Decrease rear CV (slow down rear)
    Δt < 0: Lead loco faster → Increase rear CV (speed up rear)

    Scale: ~0.1s Δt ≈ ±1 CV value (empirical, needs calibration)
    """
    # Adjust REAR locomotive CV (reference is lead)
    adjustment = -int(avg_delta_t * 10)  # Negative Δt → positive CV adjustment
    return max(-20, min(20, adjustment))  # Clamp to ±20 for safety
```

**Frontend UI**:
- Reports tab → "Speed Table Analysis" section
- Table view: Speed Step | CV Index | Avg Δt | Samples | Status | Recommended Adjustment
- Visual indicator: ✅ Good (<1.0s), ⚠️ Warning (1.0-1.5s), ❌ Critical (≥1.5s)
- Button: "Preview Adjustments" → Show before/after CV values

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
