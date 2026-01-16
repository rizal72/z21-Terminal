# Speed Table Viewer - Phase 1 (Read-Only)

**Status**: ✅ COMPLETED (2025-01-16) | **Updated**: 2025-01-17 (Cumulative Recommendations)
**Version**: v1.2 Phase 1
**Next Phase**: Phase 2 - Interactive CV Editing + Auto-Apply + Smoothing

---

## 🆕 2025-01-17 Updates - Cumulative Intelligent Recommendations

**Status**: ✅ IMPLEMENTED

### Major Changes

**1. Cumulative Historical Data** (was: single session only)
- Recommendations now aggregate CRITICAL/WARNING events from **ALL historical sessions**
- Mean Δt calculated across full history (more accurate direction)
- Provides complete picture of CV performance over time

**2. Intelligent "Fixed" Detection**
- Speed considered **FIXED** if last tested session shows improvement:
  - **>= 3 Δt events** at that speed
  - **< 20% CRITICAL rate** (max 1 CRITICAL per 5 events)
- Fixed speeds excluded from recommendations (proven OK)
- Allows iterative testing: adjust CV → retest → recommendation disappears if improved

**3. Fixed ±1 Adjustment** (was: scaling with CRITICAL count)
- **OLD (WRONG)**: `adjustment = (critical_count // 5) * 2` → 83 CRITICAL = -32 adjustment 😱
- **NEW (CORRECT)**: `adjustment = 1` (fixed) → all speeds get ±1
- **Reasoning**: CV misconfiguration error is CONSTANT regardless of CRITICAL count
  - 10 CRITICAL events → CV too high by ~1
  - 100 CRITICAL events → STILL too high by ~1 (same config!)
  - More CRITICALs = more confirmation of problem, NOT bigger CV error
- **Iterative workflow**: adjust -1, retest, still problematic? -1 again, repeat until fixed

**4. Non-Validated Session Display**
- Speed Table now shows data even when session not validated (0 Δt events)
- Badge **"WAITING FOR FIRST ΔT"** (amber) appears if session exists but not validated
- Historical recommendations always visible (cumulative data independent from current session)

**5. Phase 2 Smoothing Requirement** (documented)
- Auto-adjust MUST smooth adjacent CVs to preserve speed curve
- Algorithm: CV target ±1, CV adjacent ±0.5 (rounded)
- Without smoothing: step/jump in speed curve → inconsistent behavior

### Workflow Example (Cumulative Approach)

```
Session 1: Test speeds 70% and 100%
  Speed 70%: 12 events, 8 CRITICAL (66.7% rate)
    → Recommendation: CV82 -1 (mean Δt = -1.2s)

  Speed 100%: 8 events, 7 CRITICAL (87.5% rate)
    → Recommendation: CV94 -1 (mean Δt = -1.5s)

Session 2: Test ONLY speed 70% (validate fix)
  Speed 70%: 6 events, 0 CRITICAL (0% rate)
    → FIXED! (>= 3 events, < 20% rate)
    → Recommendation CV82 DISAPPEARS ✅

  Speed 100%: NOT tested
    → Recommendation CV94 PERSISTS ⚠️ (problem not resolved)

Session 3: Test ONLY speed 100% (validate fix)
  Speed 100%: 6 events, 1 CRITICAL (16.7% rate)
    → FIXED! (>= 3 events, < 20% rate)
    → Recommendation CV94 DISAPPEARS ✅
```

### Benefits

- ✅ Zero cognitive load (system remembers all historical problems)
- ✅ Iterative testing workflow (adjust → retest → auto-clear if OK)
- ✅ Conservative adjustments (±1 prevents overshooting)
- ✅ Phase 2 ready (smoothing algorithm documented)

---

## Overview

Visual JMRI-style speed table viewer (CV67-94) with automatic CV adjustment recommendations based on real-time consist performance data.

**Core Features**:
- 28 vertical bars displaying current CV values from JMRI roster XML
- Highlighting problematic speeds based on CRITICAL event counts
- CV adjustment recommendations with direction based on mean Δt sign
- CSV export for manual JMRI DecoderPro import
- Real-time session tracking integration

**Philosophy**: Phase 1 provides **read-only visualization and recommendations** to help users understand which CVs need tuning. Phase 2 will add interactive editing and auto-apply capabilities.

---

## User Interface

### Location
**Analytics Panel → Speed Tuning tab** (requires consist selection - C10 or C11)

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Summary Cards (3 columns)                                   │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│ │ Adjust Loco │ │ Problematic │ │ Recommend.  │           │
│ │ E656 239    │ │ Speeds: 3   │ │ CVs: 2      │           │
│ │ Addr 7,28CV │ │             │ │             │           │
│ └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Header: Adjust Loco: 7 | Session: 20260115_182345          │
│                                     [Export CSV] button      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 28 Vertical Bars (CV67-94)                                  │
│                                                              │
│  128  135  142  ...  (CV values - top)                      │
│  │▓▓  │▓▓  │▓▓  ...  (bars with color coding)              │
│  │▓▓  │▓▓  │▓▓                                              │
│  │▓▓  │▓▓  │▓▓  Red/Amber bars = problematic speeds        │
│  │▓▓  │▓▓  │▓▓                                              │
│  ▼    ▼    ▼                                                │
│  1    2    3   ...  28  (JMRI step - middle)               │
│            10%      100% (speed % - bottom, only 10% incr) │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ CV Adjustment Recommendations                                │
│                                                              │
│ CV86  128→126  -2    Δt -1.20s  12 critical  5 warning     │
│ CV89  135→133  -2    Δt -0.85s   7 critical  3 warning     │
│                                                              │
│ 💡 Export to CSV and import via JMRI DecoderPro             │
└─────────────────────────────────────────────────────────────┘
```

### Color Coding

**Bars** (border + fill):
- **Gray** (default) - No issues, speed within tolerance
- **Amber** - 5-9 CRITICAL events (moderate issues)
- **Red** - 10+ CRITICAL events (severe issues)

**Recommendations Δt** (mean delta_t sign):
- **Blue** - Negative Δt (adjust loco FASTER, need to slow down)
- **Amber** - Positive Δt (adjust loco SLOWER, need to speed up)

**CV Delta**:
- **Green** (+N) - Increase CV (speed up)
- **Red** (-N) - Decrease CV (slow down)

---

## Technical Implementation

### Backend Architecture

**File Structure**:
```
backend/
├── routers/
│   └── speed_table.py          # API endpoint /api/speed-table/{consist_id}
├── services/
│   ├── speed_table_helpers.py  # CV calculation logic
│   └── analytics_db.py         # Query CRITICAL events + mean Δt
└── scripts/utils/cv_operations/
    └── read_cv_from_roster.py  # Reused JMRI roster XML parser
```

**Key Functions**:

1. **`read_cv_speed_table(loco_address)`** - Read CV67-94 from JMRI roster XML
   - Reuses existing `Locomotive` class (DRY principle)
   - Returns: `{67: 10, 68: 15, ..., 94: 255}`

2. **`speed_to_jmri_step(dcc_speed)`** - Map DCC speed (0-126) to JMRI step (1-28)
   - Formula: `step = floor(speed / 4.5) + 1`
   - Example: DCC 63 → Step 15

3. **`jmri_step_to_cv(step)`** - Map JMRI step to CV index
   - Formula: `cv_index = 66 + step`
   - Example: Step 15 → CV81

4. **`calculate_cv_recommendations()`** - Generate CV adjustment suggestions
   - Uses mean Δt sign for direction (negative → decrease CV, positive → increase CV)
   - **Fixed ±1 adjustment** (2025-01-17 update - was scaling with count)
   - Excludes "fixed" speeds (proven OK in last session: >= 3 events, < 20% CRITICAL rate)
   - Clamps suggested CV between 0-255

### Frontend Components

**File**: `web/src/components/charts/SpeedTableViewer.jsx`

**Key Features**:
- 28 vertical bars with percentage labels (10%, 20%, ..., 100% at correct steps)
- Real-time session tracking (fetches on `sessionId` prop change)
- Loading/error/no-data states
- CSV export with full recommendation data

**Data Flow**:
```
AnalyticsPanel (parent)
  ↓ props: consistId, sessionId
SpeedTableViewer
  ↓ fetch /api/speed-table/{consistId}
Backend Router
  ↓ queries analytics_db + roster
Returns:
  - cv_values (CV67-94 current values)
  - critical_events (speed → count)
  - warning_events (speed → count)
  - mean_delta_t (speed → avg_delta_t)
  - recommendations (CV adjustment list)
```

---

## API Endpoint

### `GET /api/speed-table/{consist_id}`

**Description**: Get speed table data for a consist (Phase 1 - Read-Only)

**Parameters**:
- `consist_id` (path) - Consist ID (10, 11, etc.)

**Response** (success):
```json
{
  "consist_id": 11,
  "adjust_loco_address": 7,
  "adjust_loco_name": "E656 239",
  "session_id": "20260115_182345",
  "session_validated": true,
  "cv_values": {
    "67": 10,
    "68": 15,
    ...
    "94": 255
  },
  "critical_events": {
    "88": 12,
    "126": 7
  },
  "warning_events": {
    "88": 5,
    "126": 3
  },
  "recommendations": [
    {
      "speed": 88,
      "jmri_step": 20,
      "cv_index": 86,
      "cv_current": 128,
      "cv_suggested": 126,
      "cv_delta": -2,
      "critical_count": 12,
      "warning_count": 5,
      "mean_delta_t": -1.2
    }
  ]
}
```

**Response** (no session yet):
```json
{
  "consist_id": 11,
  "adjust_loco_address": 7,
  "adjust_loco_name": "E656 239",
  "session_id": null,
  "session_validated": false,
  "cv_values": { ... },
  "critical_events": {},
  "warning_events": {},
  "recommendations": [],
  "message": "No active session - waiting for locomotive movement"
}
```

**Error Codes**:
- `404` - Consist not found in config
- `400` - Consist has no adjust_loco configured
- `404` - Roster file not found for locomotive

---

## Key Algorithms

### Speed Percentage Calculation

**Goal**: Show intuitive speed percentages (10%, 20%, ..., 100%) aligned to JMRI steps

**Challenge**: 28 steps don't divide evenly into 126 DCC speeds

**Solution**: Calculate which step corresponds to each 10% increment

```javascript
// For each percentage (10%, 20%, ..., 100%)
for (let percent = 10; percent <= 100; percent += 10) {
  const dccSpeed = (percent / 100) * 126;           // 10% = 12.6 DCC
  const step = Math.floor(dccSpeed / 4.5) + 1;      // 12.6 → Step 3
  const cappedStep = Math.min(step, 28);            // Cap at 28
  percentToStep[cappedStep] = `${percent}%`;        // Display "10%" under step 3
}
```

**Result**:
- 10% → Step 3 (CV69)
- 20% → Step 6 (CV72)
- 30% → Step 9 (CV75)
- ...
- 100% → Step 28 (CV94)

### CV Adjustment Direction (Critical Bug Fix)

**Problem**: Original logic always suggested INCREASING CV regardless of Δt sign

**Root Cause**: Didn't consider whether adjust loco was faster or slower

**Solution**: Use mean Δt sign to determine direction

```python
# Δt = arrival_adjust - arrival_reference
mean_delta_t = mean_delta_t_by_speed.get(speed, 0.0)

if mean_delta_t < 0:
    # Adjust loco arrives FIRST (faster) → DECREASE CV (slow down)
    cv_delta = -adjustment_magnitude
else:
    # Adjust loco arrives SECOND (slower) → INCREASE CV (speed up)
    cv_delta = adjustment_magnitude
```

**Example** (Consist 11, Loco 7 adjust):
- **Before**: Speed 126, Δt=-1.2s → suggested +2 CV ❌ (makes it even faster!)
- **After**: Speed 126, Δt=-1.2s → suggested -2 CV ✅ (slows down to sync)

---

## Session Tracking Integration

### Session ID Display

**Current View**:
- Session ID shown inside "Session Duration" card (below timer)
- Visible immediately when tracking starts (even before first Δt)
- Format: `20260115_182345` (YYYYMMDD_HHMMSS)

**Reports Tab**:
- Running session highlighted with:
  - Green border (`border-green-500/50`)
  - Light green background (`bg-green-900/10`)
  - "RUNNING" badge next to session ID
- Always at top of list (most recent)

### Session Validation States

**Not Validated** (`session_validated = false`):
- ✅ Visible in Current view (session ID generated at start)
- ❌ NOT in Reports list (requires validation)
- ✅ **VISIBLE in Speed Table** (2025-01-17 update) with **"WAITING FOR FIRST ΔT"** badge
- ✅ Historical cumulative recommendations shown (independent from current session)

**Validated** (`session_validated = true`):
- ✅ Visible in all tabs (Current, Reports, Speed Table)
- ✅ All tabs synchronized on same session
- ✅ CV recommendations based on session data

**Trigger**: First gate crossing (first Δt event)

---

## CSV Export Format

**Filename**: `speed_table_consist_{id}_loco_{address}.csv`

**Columns**:
- JMRI Step (1-28)
- CV Index (67-94)
- Current Value (0-255)
- Suggested Value (0-255)
- Delta (+/- adjustment)
- Critical Count (CRITICAL events at this speed)
- Warning Count (WARNING events at this speed)
- Notes ("Needs adjustment" or "OK")

**Example**:
```csv
JMRI Step,CV Index,Current Value,Suggested Value,Delta,Critical Count,Warning Count,Notes
1,67,10,10,0,0,0,"OK"
2,68,15,15,0,0,0,"OK"
...
20,86,128,126,-2,12,5,"Needs adjustment"
...
28,94,255,255,0,0,0,"OK"
```

**Import Workflow**:
1. Export CSV from Speed Table Viewer
2. Open JMRI DecoderPro
3. Select locomotive (adjust loco)
4. Import speed table from CSV
5. Write to decoder (programming track or ops mode)

---

## Critical Bugs Fixed

### 1. Emoji in Backend Logs
**Issue**: Used emoji in roster loader error messages
**Impact**: Garbled output on PC Windows console
**Fix**: Replaced with ASCII `[ERROR]` prefix
**Commit**: `5d64b74`

### 2. macOS Metadata Files
**Issue**: XML parser tried to read `._*.xml` files
**Impact**: XML parsing errors, spam in logs
**Fix**: Skip files starting with `._` before parsing
**Commit**: `5d64b74`

### 3. CV Recommendation Direction
**Issue**: Always suggested INCREASING CV (ignored Δt sign)
**Impact**: Wrong adjustments (made faster locos even faster!)
**Fix**: Use mean Δt sign to determine direction
**Commit**: `91f7ce6` (CRITICAL fix)

### 4. Step Percentage Alignment
**Issue**: Used `Math.round()` instead of `Math.floor()` for step calculation
**Impact**: Percentages misaligned (50% at step 14 instead of 15)
**Fix**: Match backend formula exactly: `Math.floor(speed / 4.5) + 1`
**Commit**: `eb7c844`

---

## Known Limitations (Phase 2 Roadmap)

### Not Implemented in Phase 1

1. **CV Smoothing** - No interpolation of ±3 adjacent steps
   - Phase 2 will add Gaussian/linear interpolation for smooth curves

2. **Interactive Editing** - No direct CV editing via UI
   - Phase 2 will add keyboard arrows, drag-to-adjust

3. **Auto-Apply to Decoder** - Must export CSV and import via JMRI
   - Phase 2 will add direct CV writes via operations mode (POM)

4. **Speed Table Validation** - No sanity checks (monotonicity, jumps)
   - Phase 2 will warn about invalid configurations

5. **Multi-Session Analysis** - Only uses current/last validated session
   - Phase 2 could average recommendations across multiple sessions

### Design Decisions

**Why read-only in Phase 1?**
- Lower risk (no accidental decoder writes)
- User can review and validate recommendations before applying
- CSV export provides audit trail

**Why no smoothing?**
- User requested targeted fixes (not automatic interpolation)
- Manual control preferred for initial tuning
- Phase 2 can add as optional feature

---

## Testing Notes

### Production Testing Results

**Environment**: PC Windows, Consist 11 (E656 239 + E444 056)
**Session**: 20260115_182345
**Data**: 7 CRITICAL events at speed 126

**Observations**:
- ✅ Session tracking works perfectly (visible in all tabs after first Δt)
- ✅ CV recommendations direction correct (Δt negative → suggests -CV)
- ✅ Percentage labels aligned to correct steps (10%→step 3, 50%→step 15, 100%→step 28)
- ✅ Export CSV format compatible with JMRI DecoderPro
- ✅ No macOS metadata file errors on PC
- ✅ No emoji encoding issues

**User Feedback**: "Stuoendo, un lavoro fantastico" 🎯

---

## Code Quality

### DRY Principle
- Reuses existing `Locomotive` class for roster XML parsing (no duplication)
- Reuses `AnalyticsDB` queries for event data
- Shares session tracking with Current/Reports views

### Error Handling
- Graceful degradation when roster file not found
- Clear error messages for missing consist config
- Loading/error/no-data states in UI

### Performance
- Single API call per consist load
- No unnecessary re-fetches (updates only on `sessionId` change)
- Smart downsampling already in place for charts (not needed here, small dataset)

---

## Documentation

**See Also**:
- `docs/CONSIST_ROSTER.md` - Locomotive specifications and decoder compatibility
- `docs/CONSIST_MAPPING.md` - Lead/Rear → Reference/Adjust mapping logic
- `docs/Z21_PROTOCOL.md` - CV operations (POM read/write)

---

## Phase 2 Preview

**Features Planned**:
1. Interactive CV editing (keyboard arrows, drag, numeric input)
2. CV smoothing (±3 adjacent steps with Gaussian/linear interpolation)
3. Auto-apply to decoder (direct POM writes, no JMRI required)
4. Speed table validation (warn about monotonicity violations, large jumps)
5. Multi-session recommendations (average across sessions for stability)
6. Undo/redo for CV changes
7. Preset curves (linear, exponential, S-curve templates)

**Timeline**: TBD (after Phase 1 user validation)

---

## Commits (Phase 1 Implementation)

**Feature Development**:
- `078b215` - Initial Speed Table Viewer backend (analytics query, helpers, router)
- `522c9bc` - Add locomotive name to first summary card
- `9849896` - Add speed percentage labels below JMRI steps
- `dafba7a` - Align speed percentage ticks to regular 10% intervals (chart)
- `3783d6d` - Show speed percentage only for round 10% intervals (bars)
- `4b58098` - Change percentage labels to white for better visibility
- `13a06a1` - Show all round percentage labels (10%-100%) in CV bars
- `b18d84f` - Add 100% label to last CV bar (step 28)
- `1a6620e` - Show full session ID in Speed Table header

**Critical Fixes**:
- `5d64b74` - Remove emoji from roster loader + filter macOS metadata files
- `91f7ce6` - **CRITICAL** - Correct CV recommendation direction using mean Δt sign
- `eb7c844` - Use correct step formula (floor instead of round)

**Session Tracking Integration**:
- `e763cb2` - Show current session ID in Current view + highlight running session in Reports
- `1d1d752` - Move session ID inside duration card (better UX)

**Total Commits**: 14
**Lines Changed**: ~800 added (backend + frontend)
**Files Created**: 3 (speed_table.py, speed_table_helpers.py, SpeedTableViewer.jsx)

---

**Implementation Date**: 2025-01-16
**Status**: ✅ Phase 1 Complete, Production Ready
**Next Phase**: Phase 2 - Interactive Editing (TBD)
