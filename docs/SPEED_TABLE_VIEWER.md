# Speed Table Viewer - Complete (Interactive + Direct CV Write + DB Storage)

**Status**: ✅ **v1.0.0 COMPLETE** (2025-01-17) - JMRI Independence Achieved
**Version**: v1.0.0 (Production Ready)
**Phase 1**: Read-only visualization (2025-01-16)
**Phase 2**: Interactive editing + direct CV write (2025-01-17)
**DB Migration**: CV storage migrated to database (2025-01-17)

**✅ All Features Complete**:
- ✅ Interactive CV editing with checkpoint interpolation
- ✅ Direct CV write to decoder via Z21 POM
- ✅ CV67-94 stored in database (data.db - locomotive_speed_table table)
- ✅ Undo support (1-level, restore previous values)
- ✅ Re-import from JMRI roster (manual sync when needed)
- ✅ Backward compatible (JMRI roster fallback)

---

## 🆕 2025-01-17 Updates - Phase 2: Direct CV Write to Decoder

**Status**: ✅ **PRODUCTION TESTED** - Successfully wrote CV86 80→82 on loco 7

### Phase 2 Features Implemented

**1. Centralized CV Write Delay** (z21.py refactoring)
- Moved `time.sleep(0.1)` into `write_cv_ops_mode()` method
- DRY principle: automatic spacing between CV writes
- Prevents decoder overload without explicit sleeps in caller code

**2. Direct CV Write Endpoint**
- `POST /api/speed-table/write/{consist_id}`
- Writes all 28 CVs (CV67-94) via Z21 POM operations mode
- Returns: success status, failed CVs list, total time (~2.8s), loco address
- Compatible with ESU and Hornby decoders

**3. Dual-Button Workflow**
- **"Apply & Write to Decoder"**: Writes CVs to decoder + exports CSV backup
- **"Export CSV Only"**: Exports current values without decoder write
- Both buttons disabled when no modifications present
- Visual feedback: success/error messages with timing

**4. Visual Feedback for Modifications**
- Blue border on modified CV bars (`border-blue-400`)
- Blue asterisk next to CV value (e.g., "128*")
- Priority: CRITICAL (red/amber) > modified (blue) > default (slate)
- User sees EXACTLY which CVs were changed before writing

**5. Button Disable Logic**
- Compares `cvValuesFloat` vs original `data.cv_values`
- Write button disabled with tooltip: "No modifications to write"
- Button always visible (user knows feature exists)

**6. onBlur Fix** (prevent unwanted interpolation)
- Bug: Clicking checkpoint without changing value still triggered interpolation
- Fix: Compare old vs new value before calling `saveEdit()`
- Only interpolate if value actually changed

**7. ESC Key Priority** (emergency stop)
- Removed ESC handler from checkpoint editor
- ESC now always bubbles to global emergency stop handler
- Safety first: emergency stop > editor cancel

**8. CSV Export Backup Suffix**
- No modifications: `speed_table_consist_11_loco_7_backup.csv`
- With modifications: `speed_table_consist_11_loco_7.csv`
- Clarifies purpose: backup = original roster values

### Production Testing (2025-01-17)
- ✅ CV86 written from 80 → 82 on loco 7 (Consist 11)
- ✅ Verified via Hornby Bluetooth app (decoder shows CV86 = 82)
- ✅ All 28 CVs written successfully in 2.81 seconds
- ✅ Visual feedback worked (blue borders, asterisks)
- ✅ Button disable logic correct (no modifications = disabled)

### Technical Details
- CV write uses Z21 POM (Program On Main) - no programming track needed
- Float precision state preserved throughout editing workflow
- Checkpoint interpolation applied before write (smooth speed curves)
- Compatible with ESU (loco 1,2,5,6,8) and Hornby (loco 7) decoders

---

## 🆕 2026-01-20 Updates - ESU mfx Decoder Support

**Status**: ✅ IMPLEMENTED (v1.0.0)

### Overview

Added full support for **ESU mfx® decoders** (LokSound, LokPilot) with distinct UI behavior from NMRA standard decoders (Hornby TXS, Zimo).

**Key Differences**:
- **ESU mfx**: CV67 (step 1) and CV94 (step 28) are **read-only** (fixed at 1 and 255), CV68-93 are scaled between CV2 (Vstart) and CV5 (Vhigh)
- **NMRA standard**: All CV67-94 are editable (0-255)

### Database Schema Changes

Added 3 columns to `locomotive_speed_table`:
- `vstart` (INTEGER) - CV2 (Vstart) for ESU, NULL for NMRA
- `vhigh` (INTEGER) - CV5 (Vhigh) for ESU, NULL for NMRA
- `decoder_type` (TEXT) - 'esu_mfx' or 'nmra_standard'

**Migration**: ONE-SHOT script `scripts/migrate_decoder_metadata.py` reads from JMRI roster (Mac only), then database copied to PC.

### Frontend Changes (SpeedTableViewer.jsx)

**ESU Decoder UI** (loco 1, 2, 5, 6, 8):
1. **Vstart/Vhigh Panel** (blue border, top of component)
   - Inline editing for CV2 (Vstart) and CV5 (Vhigh)
   - Writes directly to decoder via `/api/speed-table/write-vstart-vhigh` endpoint
   - Badge: "ESU mfx®"
   - Help text: "Edit CV2/CV5 FIRST to set min/max speed. Then adjust CV68-93 to shape the curve."

2. **Grey Out Step 1/28**
   - Non-clickable, grey fill, grey border
   - Tooltip: "Step X is read-only for ESU decoders (fixed at Y)"
   - Shows value but cannot be edited

3. **ESU Endpoint Recommendations**
   - If CRITICAL events at speed 0-4 (step 1) → recommend **CV2 (Vstart)** instead of CV67
   - If CRITICAL events at speed 126 (step 28) → recommend **CV5 (Vhigh)** instead of CV94
   - Blue border + "ESU" badge + hint: "⚠️ Edit Vstart/Vhigh in panel above"

**NMRA Decoder UI** (loco 7, 4):
- No Vstart/Vhigh panel (not shown)
- All steps 1-28 editable (no grey out)
- Recommendations target CV67-94 directly (no CV2/CV5 redirects)

### Backend Changes

**New Endpoint**: `POST /api/speed-table/write-vstart-vhigh/{consist_id}`
- Writes CV2 and/or CV5 to decoder via POM
- ESU decoders only (validation check)
- Updates database after successful write

**Decoder Detection**: `services/decoder_helpers.py`
- `get_decoder_type_from_config()` - Detects decoder type from config.json
- `validate_cv_write_allowed()` - Blocks CV67/CV94 writes for ESU
- `enforce_esu_fixed_values()` - Forces CV67=1, CV94=255 for ESU

**Recommendation Logic**: `services/speed_table_helpers.py`
- `calculate_cv_recommendations()` now accepts `decoder_type`, `vstart`, `vhigh`
- ESU decoders: redirects CV67 → CV2, CV94 → CV5 in recommendations
- Added `esu_endpoint` flag to recommendation objects

### Decoder Compatibility

| Decoder | Type | CV67 | CV94 | CV68-93 | CV2/CV5 |
|---------|------|------|------|---------|---------|
| LokSound V4.0 (loco 1) | ESU mfx | Fixed (1) | Fixed (255) | Scaled | Endpoints |
| LokPilot 5 (loco 2,5,6,8) | ESU mfx | Fixed (1) | Fixed (255) | Scaled | Endpoints |
| Hornby TXS (loco 7) | NMRA | Editable | Editable | Editable | Not used |
| Zimo MX630 (loco 4) | NMRA | Editable | Editable | Editable | Not used |

### API Changes

**GET `/api/speed-table/{consist_id}`** - Returns additional fields:
```json
{
  "vstart": 2,                    // CV2 for ESU (null for NMRA)
  "vhigh": 133,                   // CV5 for ESU (null for NMRA)
  "decoder_type": "esu_mfx",      // or "nmra_standard"
  "recommendations": [
    {
      "cv_index": 2,              // CV2 instead of CV67 for ESU
      "esu_endpoint": true,       // Flag for frontend highlighting
      ...
    }
  ]
}
```

**POST `/api/speed-table/write/{consist_id}`** - Blocks CV67/CV94 for ESU:
- Validation via `validate_cv_write_allowed()`
- Logs error and skips if blocked
- Returns `failed_cvs` list

### See Also
- `docs/SPEED_TABLE_DECODER_BEHAVIOR.md` - Complete ESU mfx implementation plan
- `docs/DATABASE_SCHEMA.md` - Database schema with vstart/vhigh/decoder_type columns

### Related Future Enhancements
- **CV3/CV4 Editor** - Currently CV3 (Accel) and CV4 (Decel) are hardcoded in config.json. Future UI for editing these values would be useful during speed table tuning when testing with momentum enabled. See `docs/FUTURE_IDEAS.md` → "CV3/CV4 Acceleration/Deceleration Editor"

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

Visual JMRI-style speed table viewer (CV67-94) with interactive editing, direct CV write, and automatic recommendations based on real-time consist performance data.

**Core Features**:
- ✅ 28 vertical bars displaying current CV values from **database** (JMRI roster fallback)
- ✅ Interactive checkpoint editing with smooth interpolation
- ✅ Direct CV write to decoder via Z21 POM (no programming track needed)
- ✅ Highlighting problematic speeds based on CRITICAL event counts
- ✅ CV adjustment recommendations with direction based on mean Δt sign
- ✅ **Undo support** - Restore previous CV values with 1 click
- ✅ **Re-import from JMRI** - Manual sync when roster changes
- ✅ CSV export for backup/manual import
- ✅ Real-time session tracking integration

**Philosophy**: Complete JMRI independence for daily operations. CV modifications visible immediately without JMRI export/import cycle. JMRI still used for initial locomotive setup and as fallback source.

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

**CV Modification State** (border indicators - NEW 2026-01-22):
- **Green left border (2px)** - CV modified via web UI (persistent, `cv_last_modified > 0`)
  - Indicates: "This CV has been manually adjusted from JMRI import"
  - Persists across page reloads and sessions
  - **Removed by**: Undo operation (sets `cv_last_modified = 0`)
  - **NOT removed by**: Re-applying recommendations (updates timestamp, keeps border)
- **Blue border + asterisk** - CV modified but not saved (temporary, UI session only)
  - Indicates: "Pending changes not written to decoder"
  - Disappears after "Apply & Write to Decoder"
  - Does NOT persist across page reloads

**State Combinations**:
1. **Gray** - Original JMRI import value, never modified
2. **Green border** - Modified via web UI and saved (persistent)
3. **Blue border + asterisk** - Modified in current session, not saved yet (temporary)
4. **Green + Blue border + asterisk** - Previously modified (green) + new pending changes (blue)

**Recommendations Δt** (mean delta_t sign):
- **Blue** - Negative Δt (adjust loco FASTER, need to slow down)
- **Amber** - Positive Δt (adjust loco SLOWER, need to speed up)

**CV Delta**:
- **Green** (+N) - Increase CV (speed up)
- **Red** (-N) - Decrease CV (slow down)

### Action Buttons

**Primary Actions** (left-aligned, prominent with text):
- **Apply & Write to Decoder** - Writes all 28 CVs via Z21 POM + updates database + exports CSV backup
  - Disabled when no modifications present
  - Shows success/error message with timing (~2.8s)
  - Blue highlight on modified CVs (border + asterisk)
  - **Updates cv_modification_timestamps** (NEW 2026-01-21): Records timestamp for each modified CV
  - **Recommendations workflow**: Recommendation disappears immediately → test speed again → if still CRITICAL, reappears (based only on new data)

- **Export CSV Only** - Exports current values without decoder write
  - Useful for manual JMRI import or backup
  - Filename suffix: `_backup.csv` if no modifications, regular if modified

**Secondary Actions** (right-aligned, icon-only, semitransparent):
- **Undo** (fa-undo icon, amber) - Restore previous CV values
  - Reads `previous_values` from database
  - Writes to decoder via POM
  - Swaps current ↔ previous (can undo the undo)
  - **Removes green border** (sets `cv_last_modified = 0`)
  - Tooltip: "Undo last change (restore previous CV values)"

- ~~**Re-import** (DEPRECATED - Hidden from UI as of 2026-01-22)~~
  - **Reason**: JMRI used ONLY for initial new locomotive setup
  - **Alternative**: Use `scripts/import_single_locomotive.py` for new locomotives
  - Backend code preserved but button removed from UI
  - Daily operations never require JMRI interaction

---

## Technical Implementation

### Backend Architecture

**File Structure**:
```
backend/
├── routers/
│   └── speed_table.py             # API endpoints (GET, POST write/undo/reimport)
├── services/
│   ├── speed_table_helpers.py     # CV DB operations + calculations
│   ├── config_helpers.py          # Backward compatible config loaders
│   └── analytics_db.py            # Query CRITICAL events + mean Δt
└── scripts/utils/
    ├── cv_operations/
    │   └── read_cv_from_roster.py # JMRI roster XML parser (fallback)
    └── import_speed_tables_from_jmri.py  # One-time import script
```

**Key Functions** (speed_table_helpers.py):

1. **`read_cv_speed_table_from_db(loco_address)`** - Read CV67-94 from database (primary)
   - Queries `locomotive_speed_table` table in data.db
   - Returns: `{67: 10, 68: 15, ..., 94: 255}` or `None` if not found

2. **`read_cv_speed_table(loco_address)`** - Read CV67-94 from JMRI roster XML (fallback)
   - Reuses existing `Locomotive` class (DRY principle)
   - Used when DB entry doesn't exist or manual sync needed
   - Returns: `{67: 10, 68: 15, ..., 94: 255}`

3. **`update_cv_speed_table_in_db(loco_address, cv_values, source)`** - Update database after CV write
   - Saves previous values as JSON snapshot (1-level undo)
   - Tracks source: 'web_ui', 'jmri_import', 'undo', 'jmri_reimport'
   - Returns: `True` on success

4. **`undo_cv_speed_table(loco_address)`** - Restore previous CV values
   - Swaps current ↔ previous_values (can undo the undo)
   - Returns: Previous CV values dict or `None` if no undo available

5. **`speed_to_jmri_step(dcc_speed)`** - Map DCC speed (0-126) to JMRI step (1-28)
   - Formula: `step = floor(speed / 4.5) + 1`
   - Example: DCC 63 → Step 15

6. **`jmri_step_to_cv(step)`** - Map JMRI step to CV index
   - Formula: `cv_index = 66 + step`
   - Example: Step 15 → CV81

7. **`calculate_cv_recommendations()`** - Generate CV adjustment suggestions

---

### Green Border Implementation (2026-01-22)

**Purpose**: Visual indicator for CVs modified via web UI (persistent across sessions)

**Backend**:
- **Table**: `cv_modification_timestamps` (196 rows: 7 locos × 28 steps)
- **Query**: Load all 28 timestamps when fetching speed table data
```python
# backend/routers/speed_table.py - GET /api/speed-table/{consist_id}
cursor.execute('''
    SELECT step, cv_last_modified
    FROM cv_modification_timestamps
    WHERE loco_address = ?
''', (adjust_loco_address,))
cv_timestamps = {row[0]: row[1] for row in cursor.fetchall()}
# Returns: {1: 1737578400.0, 2: 0, 3: 1737492738.25, ..., 28: 0}
```

**Frontend Logic** (`web/src/components/SpeedTableViewer.jsx`):
```javascript
// For each bar (step 1-28):
const cvTimestamp = cvTimestamps[step] || 0;
const isModified = cvTimestamp > 0;  // Green border if > 0

// CSS classes:
const borderClass = isModified ? 'border-l-2 border-green-500' : '';
```

**State Transitions**:
1. **JMRI Import**: All `cv_last_modified = 0` → no green border
2. **Apply & Write**: Modified CVs get `cv_last_modified = NOW()` → green border appears
3. **Undo**: Sets `cv_last_modified = 0` → green border disappears
4. **Page Reload**: Green border persists (based on DB query)

**API Response Structure**:
```json
{
  "speed_table": {
    "67": 10, "68": 15, ..., "94": 255
  },
  "cv_timestamps": {
    "1": 0, "2": 1737492738.25, ..., "28": 0
  },
  "previous_values": {...}
}
```

---

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

## API Endpoints

### `GET /api/speed-table/{consist_id}`

**Description**: Get speed table data for a consist (reads from DB, JMRI fallback)

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

### `POST /api/speed-table/write/{consist_id}`

**Description**: Write modified CV67-94 values to decoder via Z21 POM, then update database

**Parameters**:
- `consist_id` (path) - Consist ID (10, 11, etc.)
- `cv_values` (body) - Dict of CV values to write: `{"67": 10, "68": 15, ..., "94": 255}`

**Request Body**:
```json
{
  "cv_values": {
    "67": 10,
    "68": 15,
    ...
    "94": 255
  }
}
```

**Response** (success):
```json
{
  "success": true,
  "adjust_loco_address": 7,
  "cvs_written": 28,
  "cvs_failed": [],
  "total_time": "2.81s"
}
```

**Response** (partial failure):
```json
{
  "success": false,
  "adjust_loco_address": 7,
  "cvs_written": 26,
  "cvs_failed": [86, 89],
  "total_time": "2.95s"
}
```

**Error Codes**:
- `404` - Consist not found
- `400` - Invalid CV values

---

### `POST /api/speed-table/undo/{consist_id}`

**Description**: Restore previous CV values from database and write to decoder

**Parameters**:
- `consist_id` (path) - Consist ID (10, 11, etc.)

**Response** (success):
```json
{
  "success": true,
  "adjust_loco_address": 7,
  "previous_values": {
    "67": 10,
    "68": 15,
    ...
    "94": 255
  },
  "cvs_written": 28,
  "cvs_failed": [],
  "total_time": "2.82s"
}
```

**Response** (no undo available):
```json
{
  "success": false,
  "error": "No undo available for loco 7"
}
```

**Note**: Undo uses swap mechanism - can undo the undo (1-level only)

---

### `POST /api/speed-table/reimport/{consist_id}`

**Description**: Force re-import CV67-94 from JMRI roster to database (manual sync)

**IMPORTANT**: Re-imports ONLY the adjust_loco of the specified consist. Safe targeted operation - does NOT touch other locomotives.

**Parameters**:
- `consist_id` (path) - Consist ID (10, 11, etc.)

**Response** (success):
```json
{
  "success": true,
  "adjust_loco_address": 7,
  "cv_values": {
    "67": 10,
    "68": 15,
    ...
    "94": 255
  },
  "source": "jmri_reimport"
}
```

**Response** (error):
```json
{
  "success": false,
  "error": "Locomotive roster file not found"
}
```

**Use Case**: Manual sync when JMRI roster CV values changed outside the system

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

## Phase 2 Planning - Interactive CV Editing with Smoothing

**Status**: 📋 DESIGN PHASE (2025-01-17)
**Target**: TBD (after Phase 1 production validation)

---

### Overview

Phase 2 will add **interactive CV editing** with **automatic smoothing** via JMRI-compatible checkpoint system. This allows users to adjust problematic CV values directly in the UI while maintaining smooth speed curves through linear interpolation.

**Key Principle**: Match JMRI DecoderPro's checkpoint-based interpolation workflow for zero cognitive load and seamless integration.

---

### JMRI Checkpoint System (How It Works)

**JMRI DecoderPro Speed Table Editor** uses a checkpoint-based interpolation system:

1. **Checkpoints**: Each of the 28 CV bars has a **checkbox** underneath
2. **Fixed Points**: Checked steps are "fixed" - their values are manually controlled
3. **Interpolation**: Unchecked steps are **automatically interpolated** between checkpoints
4. **Edit Behavior**: When you modify a checkpoint value, all intermediate steps recalculate automatically

**Example**:
```
Steps:     1    5    10   15   20   25   28
Checkbox:  ☑    ☐    ☑    ☐    ☑    ☐    ☑   ← User controls checkpoints
Values:    10   ?    80   ?    128  ?    255 ← ? = auto-calculated

When user modifies step 20 (128 → 127):
- Steps 11-19 recalculate (linear interpolation between 80 and 127)
- Steps 21-27 recalculate (linear interpolation between 127 and 255)
- Step 10 and 28 remain unchanged (fixed checkpoints)
```

**Interpolation Formula** (linear between checkpoints A and B):
```python
value_x = value_a + (value_b - value_a) * (step_x - step_a) / (step_b - step_a)

# Example: Interpolate step 15 between checkpoint 10 (value 80) and 20 (value 127)
value_15 = 80 + (127 - 80) * (15 - 10) / (20 - 10)
         = 80 + 47 * 0.5
         = 103.5
```

---

### Checkpoint Strategy: Operational Speed Percentages

**Default Checkpoints**: Steps corresponding to controller speed percentages (10%, 20%, ..., 100%)

**Rationale**: Users always control locomotives using percentage steps (not intermediate values), so checkpoints should match operational usage.

**Mapping** (DCC Speed → JMRI Step → CV Index):
```
Percentage → DCC Speed → JMRI Step → CV Index → Checkpoint
10%        →    13      →   step 3  →  CV69    → ☑
20%        →    25      →   step 6  →  CV72    → ☑
30%        →    38      →   step 9  →  CV75    → ☑
40%        →    50      →   step 12 →  CV78    → ☑
50%        →    63      →   step 15 →  CV81    → ☑
60%        →    76      →   step 17 →  CV83    → ☑
70%        →    88      →   step 20 →  CV86    → ☑
80%        →   101      →   step 23 →  CV89    → ☑
90%        →   113      →   step 26 →  CV92    → ☑
100%       →   126      →   step 28 →  CV94    → ☑
```

**Default Checkpoints**: `[3, 6, 9, 12, 15, 17, 20, 23, 26, 28]` (10 checkpoints)

**Benefit**: When adjusting step 20 (70%), intermediate steps (18, 19, 21, 22) auto-recalculate. These intermediate values are ONLY used by decoder during acceleration/deceleration, never commanded directly.

**User Workflow**:
```
1. User commands: 70% speed
2. Backend translates: DCC speed 88
3. Decoder reads: CV86 (step 20) ← CHECKPOINT VALUE
4. During acceleration from 60% to 70%:
   - Decoder interpolates through steps 18-19 (auto-calculated by Phase 2)
   - Result: Smooth speed curve, no jumps
```

---

### The Rounding Problem (Float Precision Required)

**Issue**: CV values are integers (0-255), but interpolation produces floats. Naive rounding causes loss of precision and prevents gradual adjustments from propagating.

#### Scenario: Gradual CV Adjustment (-1 per iteration)

**Setup**:
```
Step 17 (60%): 140  ← checkpoint (FIXED)
Step 20 (70%): 160  ← checkpoint (will adjust)
Step 23 (80%): 180  ← checkpoint (FIXED)

Intermediate steps (18, 19, 21, 22) interpolated between checkpoints
```

**Adjust 1**: Step 20: 160 → 159
```
Step 18 = 140 + (159-140) * 1/3 = 140 + 6.33 = 146.33 → round(146.33) = 146
Step 19 = 140 + (159-140) * 2/3 = 140 + 12.67 = 152.67 → round(152.67) = 153

Problem: If step 18 was already 146 before adjustment, NO VISUAL CHANGE!
         Rounding suppresses propagation of -1 adjustment to adjacent steps.
```

**After 4 adjustments** (160 → 156):
```
Step 18 finally changes from 146 → 145 (took -4 to checkpoint before propagating!)
Step 19 changed earlier at 158 (took -2)
```

**Problem Summary**: Integer-only math requires -3 to -4 adjustments to checkpoint before adjacent steps visibly change. This breaks the "gradual adjustment" workflow.

#### Solution: Float Precision Internally, Round Only on Export

**Implementation**:
1. **Internal State**: Store CV values as **floats** (decimal precision)
2. **Interpolation**: Calculate without rounding (pure float math)
3. **Display**: Round for UI (show integer to user)
4. **Export CSV**: Round for JMRI import (integer 0-255)

**Code Example**:
```javascript
// State stores floats (decimal precision)
const [cvValuesFloat, setCvValuesFloat] = useState({
  67: 10.0,
  68: 18.333,
  69: 26.667,
  // ...
});

// Interpolation preserves float precision
function interpolate(stepA, valueA, stepB, valueB, stepX) {
  return valueA + (valueB - valueA) * (stepX - stepA) / (stepB - stepA);
  // Returns float! (e.g., 146.333...)
}

// Apply checkpoint adjustment (maintains float precision)
function applyInterpolation(modifiedStep, newValue) {
  const updatedValues = { ...cvValuesFloat };

  // Update checkpoint (exact integer or float)
  updatedValues[66 + modifiedStep] = newValue;

  // Recalculate intermediate steps (float math, NO rounding)
  for (let step = prevCheckpoint + 1; step < modifiedStep; step++) {
    updatedValues[66 + step] = interpolate(...); // Float result preserved
  }

  setCvValuesFloat(updatedValues);
}

// Display in UI (round only for presentation)
function getDisplayValue(step) {
  return Math.round(cvValuesFloat[66 + step]);
}

// Export CSV (round only for JMRI compatibility)
function exportToCSV() {
  for (let step = 1; step <= 28; step++) {
    const value = Math.round(cvValuesFloat[66 + step]); // Integer for decoder
    csv += `${66 + step},${value}\n`;
  }
}
```

**Result with Float Precision**:
```
Adjust 1: Step 20: 160.0 → 159.0
  Step 18: 146.333... (display: 146)
  Step 19: 152.667... (display: 153)
  Internal state changes, but display unchanged (OK!)

Adjust 2: Step 20: 159.0 → 158.0
  Step 18: 146.0 (display: 146) ← still unchanged
  Step 19: 152.0 (display: 152) ← VISUAL CHANGE! ✅

Adjust 3: Step 20: 158.0 → 157.0
  Step 18: 145.667... (display: 146) ← still 146
  Step 19: 151.333... (display: 151) ← VISUAL CHANGE! ✅

Adjust 4: Step 20: 157.0 → 156.0
  Step 18: 145.333... (display: 145) ← VISUAL CHANGE! ✅
  Step 19: 150.667... (display: 151)
```

**Benefits**:
- ✅ Gradual propagation works correctly (no "stuck" values)
- ✅ Mathematically accurate interpolation (no cumulative rounding errors)
- ✅ JMRI-compatible export (final rounding to integer)
- ✅ User-friendly display (shows integers, hides float complexity)

---

### CSV Export Format (JMRI-Compatible)

**Implemented**: 2025-01-17 (Phase 1 update)

**Format**: Simple 2-column CSV (`CV,value`) compatible with JMRI DecoderPro File → Import → CSV

**Before** (Phase 1 initial):
```csv
JMRI Step,CV Index,Current Value,Suggested Value,Delta,Critical Count,Warning Count,Notes
1,67,10,10,0,0,0,"OK"
20,86,128,126,-2,12,5,"Needs adjustment"
```

**After** (JMRI-ready):
```csv
CV,value
67,10
86,126
94,255
```

**Logic**:
- If CV has recommendation → use **suggested value** ✅
- If CV is OK → use **current value** ✅
- Result: CSV contains optimized speed table ready to apply

**User Workflow**:
1. Click "Export for JMRI" in Speed Table Viewer
2. Download `speed_table_consist_11_loco_7_JMRI.csv`
3. JMRI DecoderPro → File → Import → CSV → Select file
4. Write to decoder (operations mode or programming track)

**Filename**: `speed_table_consist_{id}_loco_{addr}_JMRI.csv` (suffix clarifies purpose)

**Button Label**: "Export for JMRI" (was "Export CSV")

**Tooltip**: "Export to CSV and import via JMRI DecoderPro (File → Import → CSV) to apply these adjustments"

---

### Implementation Plan (Phase 2)

#### UI Changes

**1. Checkpoint Checkboxes**
```jsx
// SpeedTableViewer.jsx - Add checkbox below each bar

const DEFAULT_CHECKPOINTS = [3, 6, 9, 12, 15, 17, 20, 23, 26, 28]; // 10%-100%
const [checkpoints, setCheckpoints] = useState(DEFAULT_CHECKPOINTS);

{bars.map((bar, idx) => {
  const step = idx + 1;
  const isCheckpoint = checkpoints.includes(step);

  return (
    <div key={idx} className="flex flex-col items-center">
      {bar}
      <input
        type="checkbox"
        checked={isCheckpoint}
        onChange={() => toggleCheckpoint(step)}
        className="mt-1"
      />
      {isCheckpoint && (
        <span className="text-xs text-blue-400 mt-1">
          {getPercentageLabel(step)} {/* "70%" etc. */}
        </span>
      )}
    </div>
  );
})}
```

**2. Interactive CV Editing**
- Click bar → numeric input popup
- Keyboard arrows ↑/↓ to adjust value
- Drag bar up/down for visual adjustment
- Accept/reject recommendation buttons

**3. Real-time Interpolation Preview**
- Show interpolated values in gray (non-checkpoint bars)
- Highlight modified checkpoints in different color
- Display float precision in tooltip (e.g., "146.33 → rounds to 146")

#### Data Structure Changes

**Float Precision State**:
```javascript
// Current: Integer values only
const [cvValues, setCvValues] = useState({ 67: 10, 68: 18, ... });

// Phase 2: Float precision for interpolation
const [cvValuesFloat, setCvValuesFloat] = useState({
  67: 10.0,
  68: 18.333,
  69: 26.667,
  // ...
});

// Display helper
function getDisplayValue(step) {
  return Math.round(cvValuesFloat[66 + step]);
}

// Export helper
function getExportValue(step) {
  return Math.round(cvValuesFloat[66 + step]); // Integer for JMRI/decoder
}
```

#### Backend Changes

**Minimal**: Export endpoint already returns complete cv_values (CV67-94), no changes needed.

**Optional Enhancements**:
- Validate speed table (monotonicity check, jump detection)
- Direct CV write via POM (operations mode) - requires Z21 integration
- Undo/redo tracking via database

#### Interpolation Logic

**Core Algorithm**:
```javascript
function applyInterpolation(modifiedStep, newValue) {
  const sortedCheckpoints = [...checkpoints].sort((a, b) => a - b);
  const currentIdx = sortedCheckpoints.indexOf(modifiedStep);
  const prevCheckpoint = sortedCheckpoints[currentIdx - 1] || 1;
  const nextCheckpoint = sortedCheckpoints[currentIdx + 1] || 28;

  const updatedValues = { ...cvValuesFloat };
  updatedValues[66 + modifiedStep] = newValue; // Update checkpoint

  // Interpolate zone: prevCheckpoint → modifiedStep
  for (let step = prevCheckpoint + 1; step < modifiedStep; step++) {
    const cvIndex = 66 + step;
    updatedValues[cvIndex] = interpolate(
      prevCheckpoint, cvValuesFloat[66 + prevCheckpoint],
      modifiedStep, newValue,
      step
    ); // Returns float, NO rounding
  }

  // Interpolate zone: modifiedStep → nextCheckpoint
  for (let step = modifiedStep + 1; step < nextCheckpoint; step++) {
    const cvIndex = 66 + step;
    updatedValues[cvIndex] = interpolate(
      modifiedStep, newValue,
      nextCheckpoint, cvValuesFloat[66 + nextCheckpoint],
      step
    ); // Returns float, NO rounding
  }

  setCvValuesFloat(updatedValues);
}

function interpolate(stepA, valueA, stepB, valueB, stepX) {
  return valueA + (valueB - valueA) * (stepX - stepA) / (stepB - stepA);
}
```

**Edge Cases**:
- First checkpoint (step 1): No prev checkpoint → interpolate to step 1 from step 1 (no-op)
- Last checkpoint (step 28): No next checkpoint → interpolate from step 28 to step 28 (no-op)
- Single checkpoint modified: Recalculates both zones (prev-current, current-next)

---

### User Approval Workflow (Semi-Automatic)

**Principle**: CV changes require user approval before writing to decoder. "It's not rocket science" - batch approval with real-time preview is sufficient.

**Approach**: Checkboxes + Real-Time Preview + Final Approval

---

#### UI Design

```
╔═══════════════════════════════════════════════════════════╗
║ Recommended CV Adjustments (3)                           ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║ ☑ Step 20 (CV86) - 70%                                   ║
║    128 → 127 (-1) | 12 CRITICAL, Δt -0.8s               ║
║                                                           ║
║ ☑ Step 23 (CV89) - 80%                                   ║
║    180 → 179 (-1) | 5 CRITICAL, Δt -0.5s                ║
║                                                           ║
║ ☐ Step 28 (CV94) - 100%                                  ║
║    255 → 254 (-1) | 8 CRITICAL, Δt -1.2s                ║
║                                                           ║
║ [Select All]  [Deselect All]                            ║
║                                                           ║
╟───────────────────────────────────────────────────────────╢
║                                                           ║
║ [28 vertical bars with real-time preview]                ║
║                                                           ║
║ Preview shows: 2 checkpoints + 8 interpolated = 10 CVs  ║
║ will change                                              ║
║                                                           ║
╟───────────────────────────────────────────────────────────╢
║                                                           ║
║ [Apply 2 Selected Changes]  [Export to JMRI]            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

#### Behavior

**1. Checkboxes (Select Recommendations)**:
- Default: All recommendations **checked** (opt-out model)
- User unchecks recommendations they don't want to apply
- `[Select All]` / `[Deselect All]` for bulk operations

**2. Real-Time Preview on Bars**:
- **When checkbox checked**: Bar changes color immediately (e.g., blue → orange)
  - Checkpoint bar: Solid color (e.g., orange)
  - Interpolated bars: Lighter shade (e.g., light orange)
  - Tooltip shows: "Current: 128 → New: 127 (float: 126.67)"
- **When checkbox unchecked**: Bar reverts to original color (blue)
- **Visual feedback**: User sees EXACTLY what will change before final approval

**3. Impact Summary**:
```
Preview Impact:
- 2 checkpoint values modified (CV86, CV89)
- 8 interpolated values changed (CV87-88, CV90-92)
- Total: 10 CVs will be written
```

**4. Final Approval Button**:
```jsx
[Apply 2 Selected Changes]  // Disabled if no checkboxes selected
```

Click → **Confirmation Dialog**:

```
╔═══════════════════════════════════════════════════════════╗
║ Apply CV Changes to Decoder?                             ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║ This will modify:                                        ║
║ • 2 checkpoint values (CV86, CV89)                       ║
║ • 8 interpolated values (CV87-88, CV90-92)               ║
║ • Total: 10 CVs                                          ║
║                                                           ║
║ Choose method:                                           ║
║                                                           ║
║ [Export to JMRI CSV]  [Write via POM (Z21)]             ║
║                                                           ║
║ [Cancel]                                                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

**5. Apply Methods**:

**Option A: Export to JMRI** (Phase 1, available now)
- Downloads CSV with new values
- User imports via JMRI DecoderPro → File → Import → CSV
- JMRI writes to decoder (ops mode or programming track)

**Option B: Write via POM** (Phase 2B, future)
- Direct Z21 operations mode write (`write_cv_ops_mode()`)
- Progress bar: "Writing CV86... 1/10"
- Success notification: "10 CVs written successfully"
- Error handling: Retry on failure, rollback on critical error

---

#### Implementation (Phase 2)

**State Management**:
```javascript
// Selected recommendations (checkboxes)
const [selectedRecommendations, setSelectedRecommendations] = useState(
  new Set(data.recommendations.map(r => r.cv_index)) // Default: all checked
);

// Projected CV values (real-time preview)
const [projectedCVValues, setProjectedCVValues] = useState(null);

// Update preview when selections change
useEffect(() => {
  const projected = calculateProjectedValues(selectedRecommendations);
  setProjectedCVValues(projected);
}, [selectedRecommendations, data.recommendations]);

function calculateProjectedValues(selected) {
  const newValues = { ...cvValuesFloat };

  // Apply selected recommendations
  selected.forEach(cvIndex => {
    const rec = data.recommendations.find(r => r.cv_index === cvIndex);
    if (rec) {
      const step = cvIndex - 66;
      newValues[cvIndex] = rec.cv_suggested;

      // Recalculate interpolated values
      applyInterpolation(step, rec.cv_suggested, newValues);
    }
  });

  return newValues;
}
```

**Checkbox Handler**:
```javascript
function handleToggleRecommendation(cvIndex) {
  setSelectedRecommendations(prev => {
    const newSet = new Set(prev);
    if (newSet.has(cvIndex)) {
      newSet.delete(cvIndex); // Uncheck
    } else {
      newSet.add(cvIndex); // Check
    }
    return newSet;
  });
}
```

**Bar Rendering (with preview)**:
```javascript
{bars.map((bar, idx) => {
  const step = idx + 1;
  const cvIndex = 66 + step;

  // Determine bar color based on preview state
  const isModifiedCheckpoint = selectedRecommendations.has(cvIndex);
  const isModifiedInterpolated = projectedCVValues &&
    projectedCVValues[cvIndex] !== cvValuesFloat[cvIndex];

  let barColor = 'bg-blue-500'; // Default
  if (isModifiedCheckpoint) {
    barColor = 'bg-orange-500'; // Checkpoint modified
  } else if (isModifiedInterpolated) {
    barColor = 'bg-orange-300'; // Interpolated modified
  }

  return (
    <div key={idx} className={`bar ${barColor}`}>
      {/* Bar content */}
      <div className="tooltip">
        {projectedCVValues && projectedCVValues[cvIndex] !== cvValuesFloat[cvIndex] ? (
          <>
            Current: {Math.round(cvValuesFloat[cvIndex])} →
            New: {Math.round(projectedCVValues[cvIndex])}
            (float: {projectedCVValues[cvIndex].toFixed(2)})
          </>
        ) : (
          <>Value: {Math.round(cvValuesFloat[cvIndex])}</>
        )}
      </div>
    </div>
  );
})}
```

**Apply Button Handler**:
```javascript
function handleApplySelected() {
  if (selectedRecommendations.size === 0) return;

  // Count total changes (checkpoints + interpolated)
  const checkpointCount = selectedRecommendations.size;
  const interpolatedCount = countInterpolatedChanges(projectedCVValues);

  // Show confirmation dialog
  showConfirmDialog({
    title: "Apply CV Changes to Decoder?",
    message: `
      This will modify:
      • ${checkpointCount} checkpoint values
      • ${interpolatedCount} interpolated values
      • Total: ${checkpointCount + interpolatedCount} CVs
    `,
    actions: [
      {
        label: "Export to JMRI CSV",
        onClick: () => exportToJMRI(projectedCVValues)
      },
      {
        label: "Write via POM (Z21)", // Phase 2B
        onClick: () => writeToPOM(projectedCVValues),
        disabled: !isPOMWriteAvailable
      },
      {
        label: "Cancel",
        onClick: closeDialog
      }
    ]
  });
}
```

---

#### Safety Features

**1. Visual Validation**:
- Real-time bar color changes (see EXACTLY what will change)
- Tooltip shows old→new values with float precision
- Impact summary: "10 CVs will change"

**2. Confirmation Dialog**:
- Final approval before any decoder write
- Clear summary of modifications (checkpoint + interpolated)
- Cancel button always available

**3. Validation Checks** (optional warnings):
- **Monotonicity**: Warn if CV[n] > CV[n+1] (non-monotonic curve)
- **Large jumps**: Warn if |CV[n+1] - CV[n]| > 20 (jerky acceleration)
- **Range check**: Error if any value outside 0-255

**4. Undo Capability** (nice-to-have):
- "Reset All" button clears all selections
- Reverts to original values from roster XML
- No confirmation needed (just unchecking checkboxes)

---

#### User Experience Flow

**Step 1**: View recommendations
```
3 recommendations shown with checkboxes (all checked by default)
Bars show ORANGE preview (2 checkpoints + 8 interpolated)
```

**Step 2**: Adjust selections (optional)
```
User unchecks CV94 (doesn't want to modify 100% speed)
Bars update in REAL-TIME: CV94 + interpolated steps 29-31 revert to BLUE
Preview summary updates: "2 checkpoints + 5 interpolated = 7 CVs"
```

**Step 3**: Review visual preview
```
User hovers bars to see exact values: "Current: 128 → New: 127"
Confirms changes look correct visually
```

**Step 4**: Click "Apply 2 Selected Changes"
```
Confirmation dialog appears with summary
User chooses "Export to JMRI CSV"
CSV downloads with 28 values (7 modified, 21 unchanged)
```

**Step 5**: Import to JMRI (Phase 1) or Auto-Write (Phase 2B)
```
Phase 1: Manual import via JMRI DecoderPro
Phase 2B: Direct POM write with progress bar
```

---

#### Why This Approach Works

✅ **Not too granular**: Single approval for all changes (not per-CV)
✅ **Visual feedback**: Real-time preview on bars (see effect immediately)
✅ **Safe**: Confirmation dialog before any write
✅ **Flexible**: User can select/deselect recommendations
✅ **Simple**: "It's not rocket science" - straightforward UX
✅ **Zero ambiguity**: Bars change color = WYSIWYG

**User Quote Captured**:
> "Io preferisco il 2 ma mi piacerebbe che la preview fosse cmq in realtime sulle barre e poi approve finale, la uno è troppo granulare, non è rocket science"

---

#### Recommendation Persistence & Cancel Behavior

**Important**: Recommendations are **persistent** and NOT consumed when you open the UI or click Cancel.

**How It Works**:

1. **Recommendations are calculated on-the-fly** from cumulative historical data
   - Backend queries ALL delta_t events (not just current session)
   - Calculates CRITICAL counts and mean Δt per speed
   - Applies "Fixed" detection (last session < 20% CRITICAL rate)
   - Generates CV recommendations with ±1 adjustment

2. **Cancel Button** (two places):
   - **Speed Table view**: "Cancel" button next to "Apply Selected"
     - Effect: Closes preview, no changes applied
     - Recommendations: Remain visible (nothing happens)
   - **Confirmation Dialog**: "Cancel" button
     - Effect: Closes dialog, returns to Speed Table
     - Recommendations: Still checked (can retry Apply)

3. **Recommendations persist until resolved**:
   - **Manual resolution**: User applies changes via JMRI/POM
   - **Automatic resolution**: New test session shows speed is FIXED (< 20% CRITICAL)
   - **NOT cleared**: By opening UI, by clicking Cancel, by refreshing page

**Examples**:

**Scenario A: User Cancels (Recommendations Persist)**
```
Day 1:
  Session 1: Speed 70% → 12 CRITICAL
  User opens Speed Table → Sees CV86 -1 recommendation
  User clicks Cancel (not ready to apply)

Day 2:
  User reopens Speed Table → SAME CV86 -1 recommendation ✅
  (Recommendation persists because underlying data unchanged)
```

**Scenario B: User Applies (Recommendations May Clear)**
```
Day 1:
  Session 1: Speed 70% → 12 CRITICAL
  User applies CV86 -1 via JMRI

Day 2:
  Session 2: Speed 70% tested → 6 events, 0 CRITICAL (0% rate)
  User reopens Speed Table → CV86 recommendation GONE ✅
  (Auto-cleared due to "Fixed" detection: 0% CRITICAL < 20% threshold)
```

**Scenario C: Problem Persists (Recommendation Stays)**
```
Day 1:
  Session 1: Speed 70% → 12 CRITICAL
  User applies CV86 -1 via JMRI

Day 2:
  Session 2: Speed 70% tested → 8 events, 5 CRITICAL (62.5% rate)
  User reopens Speed Table → CV86 -1 recommendation STILL THERE ✅
  (Not fixed yet: 62.5% CRITICAL > 20% threshold)
  User can apply -1 again (iterative adjustment)
```

**Why This Design**:
- ✅ **Safe**: User can review recommendations multiple times before applying
- ✅ **No loss**: Canceling doesn't "consume" recommendations
- ✅ **Auto-clearing**: Recommendations disappear when actually fixed (not manually dismissed)
- ✅ **Cumulative**: Historical data ensures recommendations persist until problem resolved
- ✅ **Iterative**: User can apply -1, test, apply -1 again if needed

**Database Perspective**:
```
Recommendations = f(cumulative_delta_t_events)

Click Cancel:
  → No database changes
  → cumulative_delta_t_events unchanged
  → f() returns same recommendations next time

Apply + Test Successful:
  → New delta_t events added (0% CRITICAL)
  → cumulative_delta_t_events updated
  → f() excludes this speed (Fixed detection)
  → Recommendation disappears
```

---

### Features Planned (Phase 2)

**Core** (Required):
1. ✅ Checkpoint-based editing (default: 10%-100% percentages)
2. ✅ Float precision interpolation (round only on display/export)
3. ✅ Interactive CV adjustment (click/drag/keyboard)
4. ✅ Real-time interpolation preview (gray bars for auto-calculated values)

**Optional** (Nice-to-Have):
5. Auto-apply to decoder (direct POM writes via Z21, bypass JMRI)
6. Speed table validation (monotonicity warnings, large jump detection)
7. Undo/redo for CV changes (database-backed history)
8. Preset curves (linear, exponential, S-curve templates)
9. Multi-session recommendation averaging (stability over time)

---

### Timeline

**Phase 2 Start**: TBD (after Phase 1 production validation and user feedback)

**Estimated Effort**: 12-16 hours
- UI changes: 4-6 hours (checkboxes, interactive edit, preview)
- Float precision refactor: 2-3 hours (state management, helpers)
- Interpolation logic: 3-4 hours (algorithm, edge cases, testing)
- Testing/debugging: 3-4 hours (production validation with real locomotives)

**Blockers**: None (Phase 1 complete, CSV export JMRI-compatible already implemented)

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
