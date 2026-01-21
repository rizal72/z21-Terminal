# Changelog Archive (2025-12-16 → 2026-01-21)

Archived changelog entries and failed experiments documentation.

For recent changes, see main CLAUDE.md file.

---

## Failed Experiments

### 2026-01-21 - ❌ **WebSocket Badge 3-State Indicator** (REVERTED)

**Attempt**: Add amber state to WebSocket badge (red/amber/green) to detect tracking idle
- Red: WebSocket disconnected
- Amber: Connected but tracking idle (session_id = null)
- Green: Connected and tracking active

**Implementation**:
- Frontend: Poll `/api/analytics/current` every 10s to get session_id
- Badge color based on `isConnected` + `currentSessionId` state
- Click amber badge → `window.location.reload()`

**Problems**:
1. **Burst of duplicate API calls** when switching browser spaces/visibility
   - Multiple interval instances active simultaneously
   - useEffect dependency on `API_URL` caused re-execution
2. **New FFmpeg warnings** (`global cap_ffmpeg`) not seen before
3. **Complexity without clear benefit** over manual refresh

**Revert**: Commit 38c75c4

**Lesson**: Polling approaches with visibility changes cause race conditions. Keep it simple: badge red/green + manual refresh when N/A.

---

## Changelog 2025-01-16 to 2025-01-18

### 2025-01-18 - ⚙️ **Settings UI Complete + Consist Manager Enhancements**

**Status**: ✅ **COMPLETE** - Unified settings management + gate assignment feature

**Major Features**:

**1. Settings UI - Complete Implementation** (Phases 1-3):

**Phase 1 - Backend Migration**:
- Created `scripts/utils/migrate_config_unified.py` (one-time migration script)
- Extracted Z21 settings from hardcoded values → `config.z21` section
- Merged camera_config.json → `config.camera` section
- Credentials split: `config.json` (versionated) + `config.local.json` (gitignored, auto-merged)
- Updated backend loaders: `main.py`, `z21_manager.py`, `video_feed.py`, `rtsp_handler.py`

**Phase 2 - Backend API Endpoints**:
- `POST /api/settings/update` - Rewritten for unified config structure
- `POST /api/settings/yolo-preset/load` - Load tracking_OBB/tracking_standard profiles
- `POST /api/settings/z21/test` - Test Z21 connection (host/port validation)
- `POST /api/settings/camera/test` - Test RTSP stream (IP/port/credentials validation)
- Restart detection matrix: backend/video_feed/tracker/none (hot reload)

**Phase 3 - Frontend 7 Tabs**:
- System: debug.enabled toggle
- Z21 Network: host, port + test button
- Camera: IP, port, stream, username, password + test button
- Video Feed: FPS slider (hot reload, no restart)
- YOLO Model: confidence, IoU, OBB toggle + preset buttons (OBB/Standard)
- Tracking: active/idle FPS, timing thresholds (normal/warning/max_delta_t)
- Locomotives: read-only display (name, decoder, functions count)

**Config Structure** (post-migration):
```json
{
  "z21": {"host": "192.168.1.111", "port": 21105},
  "camera": {"ip": "...", "port": 554, "stream": "stream2", "username": "", "password": ""},
  "video": {"fps": 30},
  "tracking": {"fps": {...}, "timing_thresholds": {...}, "yolo_*": ...}
}
```

**2. Consist Manager - Gate Assignment Feature**:

**Frontend** (`ConsistForm.jsx`):
- Added `gate_assignment` to formData state
- Created `handleGateAssignmentChange()` handler for dropdown logic
- New UI section: "Gate Tracking Mode (Advanced)" with two dropdowns:
  - Reference loco monitored by: [All gates / Gate 3 / Gate 4 / ...]
  - Adjust loco monitored by: [All gates / Gate 3 / Gate 4 / ...]
- Mode indicator: automatic detection (symmetric green / asymmetric amber)
- Logic: both="All gates" → `gate_assignment: null`, specific gates → `{reference: X, adjust: Y}`

**Backend** (`routers/config.py`, `services/broadcast.py`):
- `POST /api/consists`: Read `gate_assignment` from request
- `PUT /api/consists/{address}`: Update `gate_assignment`
- `build_consist_response()`: Include `gate_assignment` in consist data

**Examples**:
- Consist 10 (figure-8): `{"reference": 3, "adjust": 4}` = asymmetric, directional
- Consist 11 (oval): `null` = symmetric, bidirectional

**3. Bug Fixes**:
- Locomotive decoder field: Changed from `decoder_model` to `decoder` (correct field name)
- Settings modal width: `max-w-4xl` → `max-w-6xl` (match Analytics panel, remove scrollbar)
- Gate assignment not loaded: Added `gate_assignment` to `ConsistManagerModal` handleEdit
- Gate assignment not saved: Added `gate_assignment` to `ConsistForm` onSubmit payload
- Emoticons removal: Replaced emoji in `config.json` notes with ASCII text (encoding compliance)

**Commits** (30 total today):

**Database Refactoring** (Phase 0-2):
- `22b24c8` - refactor: centralize DB access - analytics_db → data_db (Phase 0)
- `d404c50` - refactor: rename database file analytics.db → data.db (Phase 1)
- `0923003` - refactor: rename cv_profile_mode → test_mode (systematic rename)
- `710a5c1` - feat(db): migrate operational state to database (Phase 2)
- `24a40e3` - fix: replace all Unicode emojis with ASCII in migration script
- `46156d8` - fix: add missing DataDB import in main.py
- `e8ea15a` - fix: migration script Unicode error on Windows
- `7d71995` - fix: update all remaining analytics.db → data.db references
- `473b864` - feat: add merge script for analytics.db → data.db
- `dd0eb91` - fix: correct merge script schema (event_type + data JSON)
- `735787c` - docs: update DB_REFACTORING.md with Phase 0-2 completion log

**Speed Correlation Chart Fixes**:
- `4ba4169` - fix: restore speed percentage labels on X-axis
- `285dd31` - fix: move CustomTick outside component and pass as reference
- `734c075` - fix: remove overlapping 'DCC Speed' label from X-axis

**Settings UI** (Phase 1-3):
- `0620ef7` - docs: add comprehensive Settings UI design document
- `19402d2` - refactor: remove Reload Roster button, add Settings button
- `e4395dc` - feat: add Settings modal component (Phase 3 - Part 1)
- `e131a9f` - feat: add config API endpoints (Phase 3 - Part 2)
- `2c4b022` - feat: Phase 1 - Backend migration to unified config structure
- `2c74aae` - feat: Phase 2 - Backend API expansion
- `0c880d2` - feat: Phase 3 - Frontend Settings UI (7 tabs)
- `1d64ed7` - fix: use correct decoder field name (decoder not decoder_model)
- `9afd825` - fix: increase Settings modal width to max-w-6xl

**Consist Manager - Gate Assignment**:
- `1acd7a6` - feat: gate_assignment UI implementation
- `734d0b1` - fix: load gate_assignment from config (broadcast.py)
- `8fc154a` - fix: pass gate_assignment to edit form
- `a61ad55` - fix: pass gate_assignment on submit

**Cleanup**:
- `0392b58` - refactor: remove emoticons from config.json notes

**Documentation**:
- `bfa1957` - docs: document timing_thresholds refactoring plan
- `f9f0764` - docs: complete changelog for 2025-01-18

**Files Modified** (15 total):
- **Migration**: `migrate_config_unified.py` (NEW)
- **Backend**: `main.py`, `z21_manager.py`, `video_feed.py`, `rtsp_handler.py`, `routers/config.py`, `services/broadcast.py` (6)
- **Frontend**: `SettingsModal.jsx`, `ConsistForm.jsx`, `ConsistManagerModal.jsx` (3)
- **Config**: `config.json`, `config.local.json` (2)

**Testing**: ✅ Complete deployment and functional testing on PC production environment

**User Feedback**: "stupendo pare funzioni tutto" (Settings UI save), gate_assignment load/save verified working

---

### 2025-01-17 - 🎉 **JMRI INDEPENDENCE ACHIEVED** (v1.0.0)

**Status**: ✅ **MILESTONE COMPLETE** - z21-Terminal is now fully autonomous for daily operations

**Implementation**: 17+ commits spanning function labels migration, broadcast fixes, and config-based locomotive loading

**Achievement**: **JMRI now optional** - only needed for import script when adding new locomotives to the roster

**Liberation Day**: Complete self-sufficiency for daily railway operations without external dependencies

**What Changed**:

1. **Function Labels F0-F28** → `config.json` (was: JMRI roster XML only):
   ```json
   {
     "locomotives": {
       "1": {
         "functions": [
           {"number": 0, "label": "light", "lockable": true},
           {"number": 1, "label": "sound", "lockable": true},
           ...
         ]
       }
     }
   }
   ```
   - New script: `import_functions_from_jmri.py` (one-time migration)
   - Backend reads config first, JMRI roster fallback
   - Web dashboard displays function labels from config

2. **Locomotive Roster** → `config.json` (was: JMRI roster XML required):
   - `load_all_locomotives_from_config()` in roster_loader.py
   - Backend loads all 7 locomotives from config (address, name, decoder, color, cv_profiles, functions)
   - Dropdown list shows consists + individual locomotives ✅
   - **Tested**: Renamed `roster/` → `roster.backup/` on PC → backend still works! 🎉

3. **Speed Tables CV67-94** → `analytics.db` (was: JMRI roster XML):
   - Editable via web UI (Speed Table Viewer)
   - Undo/Re-import functionality
   - See detailed changelog sections below for implementation

4. **CV19 Consist Management** → Automatic (was: JMRI required):
   - Virtual Mode / DCC Mode toggle in web UI
   - Operations mode CV write (no programming track needed)
   - State persisted in config.json

5. **Consist CRUD** → Web UI (was: JMRI required):
   - Create, edit, delete consists via web dashboard
   - Consist configuration in config.json

**The Ultimate Test** 🎯:

```bash
# PC Windows - Rename JMRI roster directory
Rename-Item 'roster' -NewName 'roster.backup'

# Restart backend
z21-restart

# Result:
[INIT] Loading all locomotives from config.json...
[INIT] Loaded 7 locomotives
[INIT] Initialized locomotive 1 (in consist 10)
[INIT] Initialized locomotive 2
[INIT] Initialized locomotive 4
[INIT] Initialized locomotive 5 (in consist 10)
[INIT] Initialized locomotive 6
[INIT] Initialized locomotive 7 (in consist 11)
[INIT] Initialized locomotive 8 (in consist 11)
```

✅ **Backend runs perfectly without JMRI roster!**
✅ **Web dashboard shows all 9 entries** (2 consists + 7 locomotives)
✅ **Function clicks work** (no more `[WARN] Address X not found`)
✅ **JMRI now optional** - only needed for import scripts when adding new locomotives

**Key Commits**:
- `f64da28` - Function labels migration to config.json
- `5192495` - Fix broadcast.py typo (_locomotive_dict → _locomotive_data)
- `5d77537` - Load locomotives from config.json (JMRI fallback)
- Plus all Speed Table DB Migration commits (see detailed section below)

**Import Scripts**:
- `scripts/utils/import_speed_tables_from_jmri.py` - Speed tables + config refactoring
- `scripts/utils/import_functions_from_jmri.py` - Function labels F0-F28 migration

**Documentation Updated**:
- ✅ `docs/LOCOMOTIVE_SYNC_MAC_PC.md` (Mac/PC workflow for adding new locos)
- ✅ `docs/JMRI_INTEGRATION.md` (updated independence status)
- ✅ `docs/Z21_PROTOCOL.md`, `docs/CONSIST_ROSTER.md` (comprehensive specs)

**User Quote**: "Questa è la vera release 1.0.0" 🎉

**For detailed implementation notes** (Speed Table DB Migration, Interactive Editing, etc.), see sections below.

---

**Detailed Implementation Sections** (Speed Table Feature Development):

**Backend Implementation**:

1. **`backend/services/config_helpers.py`** (NEW - 127 lines):
   - Backward compatible loaders for gradual migration
   - `get_locomotive_color(address)` - unified format with fallback
   - `get_locomotive_cv_profile(address, mode)` - cv3/cv4 retrieval
   - `get_locomotive_name(address)` - name from config
   - `get_all_locomotives()` - complete roster with fallback

2. **`backend/services/speed_table_helpers.py`** (MODIFIED - added 160 lines):
   - `read_cv_speed_table_from_db(loco_address)` - DB read (source of truth)
   - `update_cv_speed_table_in_db(loco_address, cv_values, source)` - DB write with undo snapshot
   - `undo_cv_speed_table(loco_address)` - Swap current ↔ previous values
   - All functions use `data/analytics.db` (PC production only)

3. **`backend/routers/speed_table.py`** (MODIFIED - added 164 lines):
   - **Modified GET** `/api/speed-table/{consist_id}` - Read DB first, JMRI fallback
   - **Modified POST** `/api/speed-table/write/{consist_id}` - Write POM + update DB
   - **NEW POST** `/api/speed-table/undo/{consist_id}` - Restore previous + write to decoder
   - **NEW POST** `/api/speed-table/reimport/{consist_id}` - Force sync from JMRI roster

4. **`backend/z21_manager.py`** + **`backend/video_feed.py`** (MODIFIED):
   - Updated to use `config_helpers` for locomotive data
   - Backward compatible with old config format

**Import Script**:

**`scripts/utils/import_speed_tables_from_jmri.py`** (NEW - 330 lines):
- Standalone script (no backend needed, works without GPU)
- Workflow:
  1. Load JMRI roster (reuses existing `Locomotive` class)
  2. Backup config.json (timestamped)
  3. Refactor config.json (merge scattered data → unified `locomotives`)
  4. Populate database (CV67-94 for all roster)
- Tested standalone on Mac (with DB copied from PC)
- Result: 7 locomotives imported successfully

**Frontend Implementation**:

**`web/src/components/charts/SpeedTableViewer.jsx`** (MAJOR CHANGES):

1. **Component-Level fetchSpeedTableData** (fixed scope bug):
   ```jsx
   const fetchSpeedTableData = async () => {
     // Moved from useEffect to component level
     // Now accessible from writeToDecoder, handleUndo, handleReimport
   };
   ```

2. **Undo Handler**:
   ```jsx
   const handleUndo = async () => {
     // POST /api/speed-table/undo/{consistId}
     // Restores previous_values from DB
     // Writes CVs to decoder via POM
     // Reloads UI (removes asterisks)
   };
   ```

3. **Re-import Handler**:
   ```jsx
   const handleReimport = async () => {
     // POST /api/speed-table/reimport/{consistId}
     // Reads CV67-94 from JMRI roster
     // Updates DB with JMRI values
     // Reloads UI (syncs with JMRI)
   };
   ```

4. **UI Redesign** (after user feedback):
   - **Primary buttons** (left-aligned, prominent): Write, Export CSV
   - **Secondary buttons** (right-aligned, icon-only, semitransparent):
     - Undo: `fa-undo` icon, amber color, tooltip "Undo last change"
     - Re-import: `fa-sync` icon, slate color, tooltip "Re-import from JMRI"
   - Visual hierarchy clear: write/export = main actions, undo/reimport = utilities

5. **UI Refresh After Operations**:
   - Write → `fetchSpeedTableData()` (removes asterisks, syncs CV values)
   - Undo → `fetchSpeedTableData()` (shows restored values)
   - Re-import → `fetchSpeedTableData()` (shows JMRI synced values)

**Critical Bugs Fixed During Testing**:

1. **Gate Crossings Count Bug** (`backend/routers/analytics.py`):
   - **Problem**: Overview tab showed 500 events (downsampled) instead of real count (2000+)
   - **Fix**: Save `original_delta_t_count` before downsampling, return as `total_delta_t_events`
   - **Frontend**: Use `cumulativeData.total_delta_t_events` for accurate stats card

2. **Button Design Rejected** (`web/src/components/charts/SpeedTableViewer.jsx`):
   - **User Feedback**: "i due nuovi bottoni fanno cacare. Solo icona, meglio se rimpicciliti"
   - **Fix**: Changed to icon-only, smaller (`px-2 py-2`), right-aligned with `ml-auto`

3. **UI Not Refreshing After Write/Undo**:
   - **Problem**: CV values updated in DB but asterisks remained in UI
   - **Fix**: Added `await fetchSpeedTableData()` after successful operations

4. **fetchSpeedTableData Scope Error**:
   - **Problem**: Function defined inside `useEffect`, not accessible from handlers
   - **Error**: `Can't find variable: fetchSpeedTableData`
   - **Fix**: Moved function definition to component level (after state declarations)

5. **Import Script Attribute Error**:
   - **Problem**: `AttributeError: 'Locomotive' object has no attribute 'decoder'`
   - **Fix**: Changed `loco.decoder` → `loco.decoder_model` (correct attribute name)

**Testing Results**:

**Mac (Development)**:
- ✅ Import script executed successfully (standalone, no backend)
- ✅ 7 locomotives imported to config.json + DB
- ✅ Config.json refactored (unified locomotives section)
- ✅ DB populated with CV67-94 values from JMRI roster
- ✅ Syntax check: All backend files compiled without errors

**PC (Production)**:
- ✅ Full deployment via `z21-deploy-dev` (frontend build + backend restart)
- ✅ Speed Table GET: DB values displayed correctly
- ✅ CV Write: 28 CVs written + DB updated (asterisks removed after reload)
- ✅ Undo: Previous values restored to decoder + DB swapped
- ✅ Re-import: JMRI roster synced to DB (manual override)
- ✅ Gate Crossings: Accurate count displayed (not downsampled)
- ✅ Button layout: Primary prominent, secondary icon-only

**Deployment Strategy**:

1. **DB Location**: `backend/data/analytics.db` (PC only, not Mac)
2. **Config Migration**: Backward compatible loaders (old format fallback)
3. **Testing Workflow**:
   - Copy DB from PC to Mac (temporary for import script test)
   - Run import script on Mac (no GPU needed)
   - Copy modified DB back to PC
   - Deploy to PC production (full backend + frontend)

**Backward Compatibility**:

- Old config format (`locomotive_colors`, `cv_profiles`) still supported
- `config_helpers.py` checks new format first, falls back to old
- Gradual migration: can run with mixed old/new config
- No breaking changes for existing code

**Key Benefits Achieved**:

1. ✅ **JMRI Independence**: Speed table operations work without JMRI running
2. ✅ **Instant Visibility**: CV changes reflected immediately (no JMRI export/import)
3. ✅ **Undo Support**: 1-click restore of previous CV values
4. ✅ **Centralized Metadata**: All locomotive data in unified config section
5. ✅ **Audit Trail**: Source tracking + timestamps for all DB changes
6. ✅ **Manual Override**: Re-import button syncs from JMRI when needed
7. ✅ **Zero Breaking Changes**: Backward compatible with existing code

**Documentation**:

- ✅ **Design Doc**: `docs/SPEED_TABLE_DB_MIGRATION.md` (634 lines)
  - Complete architecture, schema, workflow, testing plan
- ✅ **Usage Instructions**: Import script, undo, re-import workflows

**Commits** (14 total):
- `08353ce` - Speed table DB migration implementation (core feature)
- `6b8116a` - Show non-validated sessions with badge (UI improvement)
- `7b89eab` - Remove session_validated blocking (frontend fix)
- `9729422` - Fix cumulative scaling bug (critical backend fix)
- `fc7b313` - Change adjustment ±2 to ±1 (conservative iterative)
- `7e3f6a0` - Summary cards redesign (removed Problematic, added Fixed)
- `880ab5a` - Step prominence in speed recommendations (UI tweak)
- `0dd9b98` - Revert horizontal format (user preference)
- `3602259` - Auto-select consist (UX improvement)
- `37a8966` - Fix auto-select logic (use reportsData)
- `77c5822` - Debug console logging (temporary)
- `0190c1a` - Use ONLY last session for auto-select (critical fix)
- `5118e21` - Remove debug console.log (cleanup)
- `[final]` - UI refresh + function scope fix (production ready)

**Files Modified** (11 total):
- `backend/services/config_helpers.py` (NEW)
- `backend/services/speed_table_helpers.py` (MODIFIED)
- `backend/routers/speed_table.py` (MODIFIED)
- `backend/routers/analytics.py` (MODIFIED - Gate Crossings fix)
- `backend/z21_manager.py` (MODIFIED - use config_helpers)
- `backend/video_feed.py` (MODIFIED - use config_helpers)
- `web/src/components/charts/SpeedTableViewer.jsx` (MAJOR CHANGES)
- `web/src/components/AnalyticsPanel.jsx` (MODIFIED - accurate count)
- `scripts/utils/import_speed_tables_from_jmri.py` (NEW)
- `config.json` (TRANSFORMED - unified structure)
- `docs/SPEED_TABLE_DB_MIGRATION.md` (NEW - design doc)

**User Feedback**: "stupendo pare funzioni tutto" 🎯

**Versioning**: Tagged as **v1.0.0** (JMRI independence milestone achieved)

---

### 2025-01-17 - 🎯 **Speed Table Viewer Phase 2: Direct CV Write** (v1.0.0 FINAL)

**Status**: ✅ **PRODUCTION READY** - Complete interactive CV editor with direct decoder programming

**Objective**: Transform read-only Speed Table Viewer into full interactive editor with direct CV write via POM.

**Major Features**:
- Centralized CV write delay (z21.py refactoring - DRY principle)
- Direct CV write endpoint `POST /api/speed-table/write/{consist_id}` - 28 CVs in ~2.8s
- Dual-button workflow: "Apply & Write to Decoder" vs "Export CSV Only"
- Visual feedback: blue border + asterisk on modified CVs
- Button disable logic when no modifications present
- onBlur fix: prevent unwanted interpolation on click without change
- ESC key priority for emergency stop (safety first)
- CSV export backup suffix clarifies original vs modified
- Analytics downsampling bug fixed (parameter name mismatch)

**Production Testing**: ✅ All 28 CVs written successfully in ~2.8s, verified via Hornby Bluetooth app

**User Feedback**: "perfetto, valori scritti correttamente!" ✅

---

### 2025-01-16 - 📊 **SPEED TABLE VIEWER: Phase 1 Complete** (Read-Only CV Analysis)

**Status**: ✅ **PRODUCTION READY** - Visual JMRI-style speed table with CV recommendations

**Features**:
- 28 vertical bars displaying CV67-94 values from JMRI roster XML
- Color-coded highlighting (gray/amber/red) based on CRITICAL event counts
- Speed percentage labels (10%-100%) aligned to JMRI steps
- CV adjustment recommendations with direction based on mean Δt sign
- CSV export for manual JMRI DecoderPro import
- Real-time session tracking + running session highlight

**Algorithm**: `step = floor(dcc_speed / 4.5) + 1` | Direction: `delta_t < 0` → decrease CV, `delta_t > 0` → increase CV

**User Feedback**: "Stupendo, un lavoro fantastico" 🎯

**Documentation**: `docs/SPEED_TABLE_VIEWER.md` (complete technical spec)

---


---


### 2025-01-12 - 🔌 **Z21 OFFLINE HANDLING FIX**

#### Problem
- When Z21 went offline (startup or runtime disconnect), UI showed track power ON
- Dangerous state desync: Emergency stop button disabled, power badge green
- Backend had correct state but initial_state broadcast sent stale power state

#### Solution: Dual Fix (Frontend + Backend)

**Fix 1: Frontend Immediate Fallback** (`0d12c64` - 2025-01-11 23:46)
- **Location**: `web/src/App.jsx`
- **Trigger**: Runtime Z21 disconnect (health check detects offline)
- **Action**: WebSocket `z21_status` listener forces `trackPower = false` immediately
- **Result**: Instant visual feedback (power badge OFF, emergency stop button disabled, power OFF sound)

**Fix 2: Backend Startup State** (`d7e960d` - 2025-01-12 00:09)
- **Location**: `backend/main.py`
- **Trigger**: App startup with Z21 unreachable
- **Action**:
  - Force `last_track_power_state = False` when Z21 connection fails
  - Force `consist_state[address]['power'] = False` for all consists
  - Update log: `"Z21 connection: OFFLINE (track power: OFF)"`
- **Result**: initial_state broadcast correct → page reload shows OFF state

#### Result
- ✅ UI always synchronized with Z21 connection state
- ✅ Safe behavior: track power OFF when Z21 unreachable
- ✅ Works both at startup and runtime disconnect
- **Commits**: `0d12c64`, `d7e960d`

---

### 2025-01-12 - ⚙️ **CONFIGURABLE IDLE TIMEOUT & ANALYTICS PLANNING**

#### Configurable Idle Timeout (`e563f1c`)

**Problem**: `IDLE_COOLDOWN_SECONDS` was hardcoded and used but never defined in tracking_daemon.py

**Solution**: Made idle timeout configurable via `config.json`
- **Config parameter**: `tracking.idle_timeout_seconds` (default: 10)
- **Shared usage**:
  - YOLO tracking: Switch to idle mode (1 FPS) after timeout
  - Analytics: Session end detection (no gate crossings after timeout)
- **Files modified**:
  - `config.json`: Added `idle_timeout_seconds: 10` with documentation note
  - `backend/tracking_daemon.py`: Load from config, replace all hardcoded references

**Benefits**:
- ✅ Single source of truth for idle detection
- ✅ Configurable without code changes
- ✅ Bug fixed (undefined variable eliminated)

**Commit**: `e563f1c` - "feat: make idle timeout configurable in config.json"

#### Analytics Suite Implementation (2025-01-12)

**Status**: ✅ **IMPLEMENTED**

**Key Features**:
- SQLite async logging with session validation (first Δt = valid session)
- Two views: Current Session + Cumulative History
- Consist filtering: color-coded charts (magenta C10, blue C11)
- Horizontal scroll navigation (60px/event, handles 1000+ events)
- Zombie session cleanup on close (safe timing)
- Keyboard shortcut: A key (desktop only)

**Architecture**: Async buffer (100 events, 10s flush) → Zero impact on YOLO tracking

**Complete documentation**: See [docs/ANALYTICS.md](docs/ANALYTICS.md)
- Database schema, API endpoints, UI/UX design
- Performance roadmap (scroll → sampling → LTTB → TimescaleDB)
- Failed approaches (Brush, startup cleanup) and lessons learned

**Commits**: `fa8b7cd` (connectNulls), `6edf315` (scroll), `dbc7778` (zombie cleanup)

---

### 2025-01-12 - 📊 **ANALYTICS UI IMPROVEMENTS - SESSION FILTERING & AUTO-REFRESH**

#### Session Filtering Fix (`1784f1e`)

**Problem**: Both Current and Overview views showed identical data (all 87 events)
- Stats cards not filtered by session
- Timestamp-based filtering incorrect (all events passed filter)

**Root Cause**: Used timestamp comparison instead of `session_id` matching

**Solution**:
- Added IIFE wrapper to filter events by session
- Current view: `filter(e => e.session_id === lastSession.id)`
- Overview view: all events unfiltered
- Stats cards now use `filteredEventsBySession` for accurate counts

**Result**:
- ✅ Current view shows only last session events (can start from 0 with new session)
- ✅ Overview view shows all cumulative data
- ✅ Stats cards properly differentiated between views

#### Stats Cards Refactor (`1784f1e`)

**Card 1 - Conditional**:
- Current view: Last Session Duration (mm:ss format)
- Overview view: Total Sessions count

**Card 2 - Gate Crossings**:
- Filtered by session + consist (All/C10/C11)
- Color-coded: fuchsia (C10), blue (C11), white (All)

**Card 3 - Critical Events**:
- Events with |Δt| ≥ 1.5s
- Filtered by session + consist
- Color-coded: fuchsia (C10), blue (C11), red (All)

#### Naming Change (`1784f1e`)

**Renamed "Detail" → "Current"**:
- More intuitive: "Current session" vs "All sessions history"
- Updated all UI elements, buttons, conditionals
- Arrow key navigation: ← (Current), → (Overview)

#### Auto-Refresh Implementation (`c1e5761`)

**Feature**: Auto-refresh Current view every 10s when locomotives moving

**Implementation**:
- **WebSocket monitoring**: Detects `consist_update` messages
- **Movement detection**: `speed > 0` for any locomotive
- **Conditional activation**: Only when panel open + Current view + isMoving=true
- **10-second interval**: Matches gate crossing frequency (~10s)
- **Auto-stop**: When locomotives stopped or switch to Overview

**Technical Details**:
```javascript
// WebSocket connection
useEffect(() => {
  const ws = new WebSocket(`ws://${window.location.hostname}:8000/ws`);
  ws.onmessage = (event) => {
    if (message.type === 'consist_update') {
      const isAnyLocoMoving = Object.values(message.data).some(c => c.speed > 0);
      setIsMoving(isAnyLocoMoving);
    }
  };
}, [isOpen]);

// Auto-refresh interval
useEffect(() => {
  if (!isOpen || viewMode !== 'current' || !isMoving) return;
  const interval = setInterval(() => loadCumulativeData(), 10000);
  return () => clearInterval(interval);
}, [isOpen, viewMode, isMoving]);
```

**Benefits**:
- ✅ Real-time updates during operations (Current view only)
- ✅ Zero overhead when idle (auto-stop when speed=0)
- ✅ Historical data stable (Overview view never auto-refreshes)
- ✅ Clean WebSocket lifecycle (connect/disconnect with panel)

**Testing Environment**: **PC Windows** via SSH (`riccardo@gaming-pc`)
- Deploy workflow: `z21-deploy-dev` (pull + build + restart)
- Real locomotive movement testing with Consist 10/11

**Commits**: `1784f1e` (session filtering + stats refactor), `c1e5761` (auto-refresh)

---

### 2025-01-12 - 🐛 **IDLE COOLDOWN TIMER FIX (VIRTUAL MODE)**

#### Problem
- Idle cooldown timer not working in Virtual Mode
- Locomotive stop didn't trigger 10s timer → tracking stayed at 30 FPS forever
- Expected behavior: Stop locos → 10s cooldown → switch to 1 FPS idle mode

#### Root Cause
Virtual Mode sends speed commands to individual locomotives (L7, L8), NOT consist address (11):
- Backend broadcast `consist_speed_update` only when `set_speed` called on consist address
- Virtual Mode: backend sets speed on individual locos → no broadcast to daemon
- Daemon never receives `speed=0` notification → timer never starts
- Missing `global tracking_daemon_ws` declaration caused WebSocket crash

#### Solution (3 commits)

**Commit 1**: `e8e1e74` - Debug logging to trace issue
- Added debug logs to track `consist_speed_update` broadcast
- Discovered `tracking_daemon_ws` access without `global` declaration

**Commit 2**: `8e255de` - CRITICAL fix for WebSocket crash
- Added `global tracking_daemon_ws` at start of `websocket_endpoint()`
- Fixed Python error: "cannot access local variable where it is not associated"
- Emergency fix deployed immediately (locos were running uncontrolled)

**Commit 3**: `e97c566` - Cleanup debug logging
- Removed temporary debug logs (not needed after verification)
- Verified cooldown timer working correctly

#### Test Log (Verification)
```
[STOP] STOP: both locos set to 0 (compensation reset)
[VIRT] Virtual Mode: L7=0, L8=0
[DETECT] All consists stopped - starting 10s cooldown timer...
[DETECT] Switched to Low-Power Mode (1 FPS) (after 10s cooldown)
[DETECT] YOLO tracking paused (idle @ 1 FPS, flushing RTSP buffer only)
```

#### Result
- ✅ Cooldown timer works in Virtual Mode
- ✅ Speed change notifications reach daemon correctly
- ✅ 10s delay → 1 FPS idle mode confirmed
- ✅ Virtual Mode + idle detection fully functional

**Commits**: `e8e1e74`, `8e255de`, `e97c566`

---

### 2025-01-12 - 🔄 **PAGE RELOAD TRACKING FREEZE FIX**

#### Problem (Corner Case)
User reloads page while locomotives moving (speed=70):
- Frontend reconnects, receives `initial_state` with `speed=70` ✅
- Slider shows 70 correctly ✅
- **Tracking daemon NOT notified** → stays in idle mode (1 FPS) ❌
- Video feed frozen (bbox stuck at last position) ❌
- Only new speed change (stop/restart) would unfreeze tracking ❌

#### Root Cause: Race Condition
First attempt (`506c03c`) synced daemon when client connects:
- Client connects → tries to send `consist_speed_update` to daemon
- `tracking_daemon_ws` is still `None` (daemon not connected yet)
- Daemon connects 100ms later → misses sync message
- Stays in idle mode

#### Solution
**Commit 1**: `506c03c` - Wrong timing (synced on client connect)
- Attempted sync in `websocket_endpoint()` when client connects
- Failed due to race condition (daemon connects after client)

**Commit 2**: `fd7d3bb` - Correct timing (sync on daemon connect)
- Moved sync to `websocket_tracking_endpoint()` when daemon connects
- Daemon receives current speeds immediately after WebSocket accept
- If any consist has `speed > 0` → daemon switches to active mode (30 FPS)
- Timing guaranteed: daemon is connected when we send sync

#### Test Log (Verification)
```
[WS] Tracking daemon connected
[INIT] Synced daemon on connect: consist 11 speed=88
[DETECT] Switched to Active Tracking (30 FPS)
[DETECT] YOLO tracking resumed (active @ 30 FPS)
[GATE] C11 Cross-gate: L7G2-L8G1 | dT=-0.143s
```

#### Result
- ✅ Page reload with moving locos → tracking active immediately
- ✅ No more frozen video feed on reload
- ✅ Daemon synchronized with locomotive state on connect
- ✅ Works for all scenarios: page refresh, multi-tab, browser restart

**Commits**: `506c03c` (wrong timing), `fd7d3bb` (correct fix)

---

## Changelog 2025-01-11

### 2025-01-11 - 🚀 **TENSORRT OPTIMIZATION & ONNX FALLBACK**

#### Motivation
- Reduce bbox lag from 2-3s to <0.5s via GPU acceleration
- YOLO inference on CPU too slow for real-time tracking

#### Implementation
- **Export script**: `scripts/utils/export_tensorrt.py`
  - Auto-detect standard vs OBB models
  - Export to TensorRT .engine format (FP16 half-precision)
- **Priority fallback**: `.engine` → `.onnx` → `.pt` (transparent, zero config changes)
- **Model files generated**:
  - `best_obb.pt`: 6.6 MB (PyTorch OBB - backup)
  - `best_obb.onnx`: 11.9 MB (ONNX OBB - intermediate speed)
  - `best_obb.engine`: 13.7 MB (TensorRT OBB - maximum speed, RTX 2060 optimized)

#### Critical Bug Found & Fixed
- **Problem**: ONNX/TensorRT had zero detection (bbox invisible, no console output)
- **Root cause**: ONNX/TensorRT export strips task metadata
  - YOLO assumed `task='detect'` instead of `task='obb'`
  - OBB model treated as standard detection → incompatible output format
- **Solution**: Explicitly specify `task='obb'` when loading OBB models
  ```python
  if yolo_obb:
      self.model = YOLO(model_path, task='obb')  # Fix for ONNX/TensorRT OBB
  else:
      self.model = YOLO(model_path)              # Standard detection
  ```
- **Key insight**: ONNX/TensorRT export strips model metadata → explicit task specification REQUIRED

#### Test Results (PC Windows + RTX 2060)
- ✅ **PyTorch .pt**: 30ms/frame (baseline)
- ✅ **ONNX .onnx**: 1.5-2x faster than PyTorch (intermediate speed)
- ✅ **TensorRT .engine**: 2-5x faster (6-15ms/frame) - **PRODUCTION ACTIVE**
- ✅ **Bbox lag eliminated**: <0.5s (was 2-3s)
- ✅ **Detection perfect**: All 4 locos with rotated bboxes
- ✅ **Gate timing accurate**: Real-time Δt calculation
- ✅ **Fallback compatible**: Works with both standard and OBB models

#### Files Modified
- `backend/tracking/yolo_tracker.py`: Priority fallback logic (.engine → .onnx → .pt)
- `scripts/utils/export_tensorrt.py`: Export script with auto-detection
- `.gitignore`: Added `*.engine`, `*.bak`, consolidated `*.onnx`

#### Documentation
- Complete export workflow: `docs/TENSORRT_OPTIMIZATION.md`

**Commits**: `1012ccb` (ONNX fallback), `2d17969` (task='obb' fix), `01f9fb2` (gitignore), `5880491`, `7d24a9f`, `9caf5fa`, `b306fea`

---

### 2025-01-11 - 🔧 **WEB DASHBOARD FIXES & POWERSHELL INVESTIGATION**

#### Debug Button Sync Fix
- **Problem**: Debug button showed disabled after page reload even when debug mode was active
- **Root cause**: Frontend state not synced with backend state on mount/expansion
- **Solution**:
  - Added GET `/api/debug-status` endpoint (no toggle, just status query)
  - Added `useEffect` in `App.jsx` to fetch debug status on mount
  - Added `useEffect` in `VideoFeedPanel.jsx` to sync when panel expands
- **Important lesson**: Frontend changes require **rebuild** (Vite HMR unreliable for hooks)
  - Development (Mac): Restart Vite dev server
  - Production (PC): `z21-deploy-dev` (pull + build + restart)
- **Commits**: `f9733a6`, `16aff39`, `cec53ca`, `606e238`

#### Performance Optimization
- **Removed repetitive console logs** that impacted performance during locomotive movement:
  - `consist_update received` (WebSocket loop)
  - `Updating consist/locomotive` (state updates)
  - `Address not found` messages
  - `📐 Container/Video rendered` (resize events)
- **Kept startup logs** (Wake Lock, CV Profile, WebSocket) - useful for debugging
- **Commit**: `c04f164`

#### PowerShell 7 Task Scheduler Investigation
- **Motivation**: Task Scheduler window showed garbled characters with PS7 instead of PS5.1
- **Root cause analysis**:
  - PS 5.1: Default encoding = Windows-1252 → console interprets correctly ✅
  - PS 7: Default encoding = UTF-8 → console expects codepage 850/1252 → garbled text ❌
  - PS 7 `$PSStyle` adds ANSI codes → legacy console shows raw codes instead of colors
- **Solution implemented** (retrocompatible PS 5.1 + PS 7):
  ```powershell
  [Console]::OutputEncoding = [System.Text.Encoding]::GetEncoding(850)
  if ($PSVersionTable.PSVersion.Major -ge 7) {
      $PSStyle.OutputRendering = 'PlainText'  # Disable ANSI
  }
  ```
- **Testing results**:
  - PlainText mode: Works but no colors (B/W only)
  - Ansi mode: Shows garbled ANSI codes `[97m[INIT][0m`
  - **Conclusion**: PS7 cannot display colors correctly in Task Scheduler console
- **Final configuration**:
  - **SSH**: PowerShell 7 (better command syntax, fewer retry attempts)
  - **Task Scheduler**: PowerShell 5.1 (perfect colors, no issues)
  - **start-backend.ps1**: Encoding fix present but inactive with PS5.1
- **Commits**: `18db66b` (fix), `c001b9b` (experiment), `4de7e32` (revert to PlainText)

#### Git Workflow
- **Fast-forward merge policy**: Documented in global CLAUDE.md CRITICAL REMINDERS
- **Branch sync**: `develop` merged from `main` to eliminate "53 commits behind" confusion
- **Commits**: `9dfaa64` (restore standard YOLO config), various merges

---

## Changelog 2025-01-10

### 2025-01-10 - 🔄 **YOLO OBB IMPLEMENTATION + AUTO MODEL SWITCHING + TESTING**

#### 🎯 YOLO OBB (Oriented Bounding Boxes) Implementation
- **Motivazione**: Locomotive diagonali con bbox axis-aligned causavano overlap eccessivo → NMS sopprimeva detection quando loco si passavano vicino
- **Soluzione**: YOLOv8-OBB con bbox ruotati che seguono l'orientamento delle locomotive

**Training OBB Model (v6)**:
- **Dataset**: Roboflow BiancAlice v5 - annotazioni smart select (contorni perfetti) → convertite automaticamente in OBB
- **Script**: `scripts/utils/3_train_yolo_colab.py` aggiornato per OBB
  - Download: `dataset = version.download("yolov8-obb")` invece di `"yolov8"`
  - Model: `YOLO('yolov8n-obb.pt')` invece di `'yolov8n.pt'`
- **Training**: Google Colab GPU T4, ~4 minuti
- **Results**: mAP50 = 0.917 (91.7%, leggermente inferiore a v5 93.1%)
- **Model size**: 6.6M (best_obb.pt creato)

**Config Changes**:
- **New parameter** `yolo_obb` (true/false) in `config.json` tracking section
  - `true` = Oriented Bounding Boxes (bbox ruotati)
  - `false` = Standard axis-aligned boxes
- **Initial config**: `yolo_confidence: 0.4`, `yolo_iou: 0.7`, `yolo_obb: true`

**Implementation Bugs (CRITICAL - Multi-iteration debugging)**:
1. **Array shape misunderstanding**: `box.xyxyxyxy[0]` ritorna shape `(4, 2)` non flat array
   - Fix: `points[:, 0].mean()` per center_x, `points[:, 1].mean()` per center_y
   - Commit: `3bb1a29`
2. **Detection storage indentation**: Salvataggio detection FUORI dal loop nel branch OBB
   - YOLO trovava 3 loco ma salvava solo 1
   - Fix: Spostato blocco dentro loop
   - Commit: `d4b553a`
3. **Video feed bbox length check**: `video_feed.py` assumeva `len(bbox) == 4`
   - Fix: Supporto sia 4 (standard) che 8 (OBB) valori
   - Commit: `f798a5f`
4. **JSON serialization**: numpy int64 non serializzabile → WebSocket disconnect loop
   - Fix: `bbox_json = [int(x) for x in det['bbox']]`
   - Commit: `e867cea`

**Files Modified**:
- `config.json`: +1 parameter (`yolo_obb`)
- `backend/tracking/yolo_tracker.py`: Dual mode (standard vs OBB)
- `backend/video_feed.py`: Draw bbox come polygon se 8 valori
- `backend/tracking_daemon.py`: JSON serialization fix
- `scripts/models/best.pt`: Updated a modello OBB (6.6M)
- `scripts/utils/3_train_yolo_colab.py`: Updated per OBB training

**Commits**: 11 totali (training script, config, tracker, video feed, daemon, debug, cleanup)

#### 🎨 Debug Overlay Improvements
- **Changed center markers** from large hollow circles (15px, thickness=2) to **small filled circles** (8px, filled)
- **Motivation**: User preference - pallini pieni piccoli more visually clean
- **Colors maintained**: Yellow (Gr675), Orange (D645), Green (E656), Red (E444)
- **Commit**: `c7b6393`

#### 🔄 Auto Model Switching Implementation
- **Problem**: Manual model renaming (`best.pt` ↔ `best_obb.pt`) tedious for testing
- **Solution**: Auto-select model based on `yolo_obb` config flag
  - `yolo_obb: false` → loads `best.pt` (standard axis-aligned)
  - `yolo_obb: true` → loads `best_obb.pt` (Oriented Bounding Boxes)
- **Implementation**:
  - `yolo_tracker.py`: Auto-detect model_path in `__init__` if not provided
  - `tracking_daemon.py`: Remove hardcoded MODEL_PATH
  - Log message: **ALWAYS visible** (not debug-gated) for critical info
- **Model files**:
  - `best.pt`: 6.3M (standard v5 restored from best.pt.v5.old)
  - `best_obb.pt`: 6.6M (OBB model from training)
- **Commits**: `cbc23c7`, `f952a1c`, `7ca18a7`

#### 🧪 Production Testing Results (PC Windows + GPU)
**Test 1: OBB Model** (`yolo_obb: true`, `yolo_iou: 0.85`)
- ✅ **Overlap handling**: Perfect - both locos visible when passing close
- ✅ **Bbox orientation**: Rotated polygons follow locomotive angle
- ❌ **Distant detection**: Loco 7 confidence drops <0.4 when far from camera
  - Required `yolo_confidence: 0.1` to detect distant loco 7
  - Side effect: False positives (wagons misclassified, double bbox)

**Test 2: Standard Model** (`yolo_obb: false`, `yolo_iou: 0.85`)
- ✅ **Distant detection**: Loco 7 confidence 0.4+ even when far
- ✅ **Consistent detection**: All locos detected across full track
- ⚠️ **Overlap handling**: NMS still suppresses one loco when passing close

**Test 3: Standard Model + High IoU** (`yolo_obb: false`, `yolo_iou: 0.95`)
- ✅ **Distant detection**: Perfect (all locos, all distances)
- ✅ **Overlap handling**: Both locos visible (NMS only if overlap >95%)
- ✅ **False positives**: Minimal (confidence 0.2 sufficient)

#### 🎯 Final Configuration (After Extensive Testing)
```json
{
  "tracking": {
    "yolo_confidence": 0.2,  // Was 0.4 → detect distant locomotives
    "yolo_iou": 0.95,        // Was 0.7 → reduce NMS suppression
    "yolo_obb": false        // Standard model wins
  }
}
```

**Decision: Standard Model Wins**
- **Why OBB loses**: Lower confidence on distant/small objects despite higher mAP50
  - Hypothesis: OBB learns orientation+shape (complex) → struggles on small objects
  - Training bias: More large/close locos in dataset → sacrifices small/distant
- **Why Standard wins**: Consistent detection + high IoU solves overlap
  - IoU 0.95: Allows locos to coexist unless overlap >95% (rare)
  - Confidence 0.2: Low enough for distant, high enough to avoid false positives
- **Trade-off accepted**: Occasional double bbox on extreme overlap (rare) vs losing distant locos (frequent)

**Commits**: `6b233ec` (config optimization), merged to main `4579182`

#### 📊 Key Insights
- **mAP50 ≠ Production Performance**: OBB higher mAP but worse on edge cases
- **Dataset matters**: Training bias toward large objects hurts small object detection
- **IoU sweet spot**: 0.95 balances overlap handling vs false positives
- **Confidence threshold**: Lower is better for recall if false positive rate acceptable

#### 🚀 PowerShell Deployment Aliases Refactor
- **Problem**: `z21-deploy` and `z21-deploy-dev` had duplicated code
- **Solution**: Extracted common logic to `Deploy-Z21Terminal` helper function
- **Implementation**: PowerShell parametrized function (DRY principle)
  - `function Deploy-Z21Terminal { param([string]$Branch) ... }`
  - `z21-deploy` calls with `"main"`
  - `z21-deploy-dev` calls with `"develop"`
- **Benefits**:
  - Single source of truth for deploy logic
  - Consistent behavior across both aliases
  - `config.local.json` preserved (gitignored)
- **Workflow**:
  - Development: `z21-deploy-dev` (deploy from develop)
  - Production: `z21-deploy` (deploy from main)
- **Files**: `~\Documents\PowerShell\Microsoft.PowerShell_profile.ps1` (PC)

#### 🔧 PowerShell 7 Migration (PC Windows)
- **Motivazione**: PowerShell 5.1 obsoleto, PS7 moderno e cross-platform
- **Migrazione**: SSH default shell PS5.1 → PS7.5.4
- **Registry**: `HKLM:\SOFTWARE\OpenSSH\DefaultShell` → pwsh.exe
- **posh-git**: Installato per PS7 (git autocompletion)
- **Profile structure**:
  - Master: `PowerShell\Microsoft.PowerShell_profile.ps1` (PS7)
  - Symlink: `WindowsPowerShell\Microsoft.PowerShell_profile.ps1` → PS7 master
  - Modifiche future: SOLO sul master PS7
- **⚠️ CRITICO**: SSH su PC usa SEMPRE PowerShell 7 da ora in poi

---

## Changelog 2025-01-09

### 2025-01-09 - 🔄 **LOG ROTATION - AUTOMATIC BACKEND.LOG CLEANUP**
- **🔄 Log Rotation Implementation** - Keep current log clean and fast
  - **Problema**: `backend.log` cresceva indefinitamente (100+ MB dopo settimane)
    - File giganti rallentano `z21-log` e editor
    - Nessun cleanup automatico implementato
  - **Soluzione**: Rotate al restart
    - `start-backend.ps1` rinomina `backend.log` → `backend.log.old` prima di avviare backend
    - Log corrente sempre piccolo e veloce da leggere
    - Ultimi 2 restart disponibili per debugging (current + old)
  - **Workflow**:
    ```powershell
    z21-restart  # Rotate automatico: backend.log → backend.log.old
    z21-log      # Sempre veloce (file piccolo)
    ```
  - **Benefici**:
    - ✅ Log corrente sempre pulito
    - ✅ Storico disponibile (.old file)
    - ✅ `.old` già gitignored (no commit accidentali)
    - ✅ Zero maintenance manuale
  - **File modificato**: `start-backend.ps1`
  - **Commit**: `fca1c47` - feat: add log rotation to start-backend.ps1
  - **Merged to main**: `69146d1`

### 2025-01-09 - 🔌 **Z21 CONNECTION STATUS - EXPLICIT STARTUP LOGGING**
- **🔌 Z21 Status Visibility** - Clear ONLINE/OFFLINE feedback at startup
  - **Problema**: Z21 offline all'avvio era silenzioso (nessun log)
    - UDP è connectionless → socket creato ma nessun error fino al primo comando
    - Badge rosso mostrato ma nessun messaggio nel log
    - Log `[INIT] Z21 connection: ONLINE` era sotto `debug_enabled` flag
  - **Soluzione**: Log esplicito per entrambi gli stati
    - `[OK] Z21 connection: ONLINE` (verde, sempre visibile)
    - `[FAIL] Z21 connection: OFFLINE` (rosso, sempre visibile)
    - Rimosso debug flag da ONLINE log
    - Aggiunto `else:` branch per offline detection
  - **Comportamento**:
    - **All'avvio**: Log immediato dello stato Z21 (online o offline)
    - **Durante runtime**: Health check ogni 5s logga solo su **cambio stato**
  - **Benefici**:
    - ✅ Feedback chiaro all'avvio (non più silenzioso quando offline)
    - ✅ Log consistenti (online e offline sempre visibili)
    - ✅ Debug più facile (stato Z21 evidente nei log)
  - **Edge case testato**: Z21 offline + Tapo camera in IR night mode
    - RTSP reconnect loop visibile (~2s delay tra tentativi)
    - Loop attivo SOLO se client WebSocket connesso
    - Client disconnesso → tracking daemon si ferma automaticamente
  - **File modificato**: `backend/main.py`
  - **Commit**: `73c0c23` - feat: add explicit Z21 connection status logging at startup
  - **Merged to main**: `e96f35f`

---

## Changelog 2025-01-08

### 2025-01-08 - 🎨 **LOGGING SYSTEM REFACTOR - CENTRALIZED PREFIX→COLOR MAPPING**
- **🎨 Complete Logging System Redesign** - From low-level constants to centralized design pattern
  - **Problema precedente**:
    - Ogni file importava N costanti colore individuali (`CYAN, YELLOW, RED, RESET, ...`)
    - Cambiare colore di un prefix richiedeva modificare 5+ files
    - Inconsistenze possibili (colori sbagliati per prefix)
    - Import verbosi e poco manutenibili
  - **Nuovo design**:
    - `backend/log_colors.py` (NEW) - Single source of truth con `PREFIXES = {[PREFIX]: COLOR}` mapping
    - `log(prefix, message)` helper function - Import centralizzato
    - Modificare colore = 1 linea nel dict, propagazione automatica ovunque
  - **Refactoring completato**: 9 backend files
    - `backend/config_loader.py`
    - `backend/main.py`
    - `backend/tracking/rtsp_handler.py`
    - `backend/tracking/yolo_tracker.py`
    - `backend/tracking_daemon.py`
    - `backend/tracking_manager.py`
    - `backend/video_feed.py`
    - `backend/z21_manager.py`
    - Pattern: `from log_colors import CYAN, YELLOW, ...` → `from log_colors import log`
  - **Nuovi log prefixes**:
    - `[ERROR]` - Errori critici (file not found, connection failed, JSON invalid) - Red bright (91m)
    - `[STOP]` - Emergency stop commands (distinto da compensation) - Red bright (91m)
  - **Prefixes rinominati**:
    - `[TRACK]` → `[DETECT]` - YOLO detection/tracking (più chiaro, evita ambiguità con "binario ferroviario")
  - **Colori aggiornati**:
    - `[INIT]`: Cyan dim → **White bright (97m)** - Alta visibilità per startup messages
    - `[SHUT]`: Cyan dim → **Purple (35m)** - Colore distintivo per shutdown
    - `[WS]`: Cyan dim → **Blue (34m)** - Network-related operations
    - `[WARN]`: Cyan dim → **Yellow bright (93m)** - Standard warning color
  - **Auto-compensation toggle fix**:
    - Aggiunta chiamata `_save_persisted_state()` per persistere setting su config.json
    - Log sempre visibile (non più sotto debug_enabled)
    - Prefix `[COMP]` invece di `[INIT]` per consistency
    - Messaggio: `Auto-compensation enabled/disabled for consist X (saved to config.json)`
  - **Benefici**:
    - ✅ Manutenibilità: cambia 1 file invece di 5+
    - ✅ Consistenza: impossibile usare colori sbagliati
    - ✅ Scalabilità: aggiungere prefix = 1 riga
    - ✅ Import semplificati: `from log_colors import log`
  - **Commit**: `99d46cf` - refactor: centralized logging system with PREFIX→COLOR mapping
  - **Merged to main**: `040458e`

### 2025-01-09 - 🧹 **UNICODE SYMBOLS CLEANUP - ASCII LOGGING**
- **🧹 Remove Unicode Symbols from Logs** - Added [OK] and [FAIL] prefixes
  - **Problema**:
    - Simboli unicode (✓✗✅❌⚠️) non visualizzati correttamente su Windows terminals
    - Output illeggibile: `Ô£ô Video stream opened` invece di checkmark
    - Encoding issues su PowerShell 5.1 (default Windows)
  - **Soluzione**:
    - Aggiunti `[OK]` (green bright) e `[FAIL]` (red bright) a PREFIXES dict
    - Sostituiti tutti i simboli unicode con `log('[OK]', ...)` e `log('[FAIL]', ...)`
    - Rimossi `⚠️` da return messages (plain text per frontend notifications)
  - **Files modificati** (5):
    - `backend/log_colors.py` - Added [OK] and [FAIL] to PREFIXES
    - `backend/video_feed.py` - 4 replacements (✓ → [OK], ✗ → [FAIL])
    - `backend/tracking_manager.py` - 2 replacements (✓ → [OK], ✅ → [OK])
    - `backend/main.py` - 3 replacements (✅/❌ → [OK]/[FAIL], ✗ → [FAIL])
    - `backend/z21_manager.py` - 4 replacements (✗ → [FAIL], ⚠️ removed)
  - **Sostituzioni totali**:
    - ✓ → `log('[OK]', ...)` (4 occorrenze)
    - ✗ → `log('[FAIL]', ...)` (4 occorrenze)
    - ✅/❌ → `log('[OK]'/'[FAIL]', ...)` (2 occorrenze)
    - ⚠️ rimosso da return messages (3 occorrenze)
  - **Benefici**:
    - ✅ Logging consistente ASCII-only (no encoding issues)
    - ✅ Readable su tutti i terminali (Windows, macOS, Linux)
    - ✅ Colori centralizzati via PREFIXES dict
    - ✅ Professional output su Windows PC production deployment
  - **Commit**: `4161bee` - refactor: remove unicode symbols from logs, use [OK] and [FAIL] prefixes
  - **Merged to main**: `493323c`
- **🔄 Unicode Symbols Cleanup** - Full ASCII conversion (Δt → dT, → → ->)
  - **Problema**: Simboli unicode visualizzati incorrettamente su Windows terminals
    - `Δt` → `╬öt` nei log, `??` in OpenCV video feed
    - `→` → `ÔåÆ` nei log (reset accumulated, CV profile toggle)
  - **Soluzione**: Sostituito tutti i simboli unicode con ASCII equivalenti
    - `Δt` → `dT` usando sed (62 occorrenze in 5 file)
    - `→` → `->` usando sed (7 occorrenze in z21_manager.py)
  - **Files modificati**:
    - Delta-t: main.py, yolo_tracker.py, tracking_daemon.py, video_feed.py, z21_manager.py
    - Arrow: z21_manager.py (log messages + comments)
  - **OpenCV issue**: HERSHEY_SIMPLEX font non supporta caratteri unicode → `dT` anche nel video feed panel
  - **Risultato**: ASCII consistente ovunque (logs + video overlay + code comments)
  - **Commits**:
    - `8bb59e1` - refactor: replace Δt unicode symbol with dT (ASCII)
    - `bebb2e2` - feat: use Δt unicode symbol in video feed panel (tentativo fallito)
    - `ec836dc` - fix: revert Δt to dT in video feed panel (OpenCV font encoding issue)
    - `6cfc99d` - fix: replace → arrow symbol with -> (ASCII) in logs
  - **Merged to main**: `9fcdd18`, `7b37695`, `979fd45`, `c87af0d`

### 2025-01-09 - 🔧 **WINDOWS TASK SCHEDULER - TRULY DETACHED BACKEND**
- **🔧 Task Scheduler Fix** - Backend ora sopravvive veramente a SSH close
  - **Problema**: `Start-Process -WindowStyle Hidden` NON è detached
    - Processo legato alla sessione SSH
    - Chiudi SSH → processo termina
    - Riapri SSH → backend morto, serviva z21-start di nuovo
  - **Soluzione**: Windows Task Scheduler
    - Task "z21-backend" creato automaticamente al primo `z21-start`
    - Esegue `C:\z21-Terminal\start-backend.ps1` (nuovo file committato)
    - Processo veramente detached dal sistema operativo
    - Sopravvive a: SSH close, logout, persino reboot (se configurato)
  - **Files aggiunti**:
    - `start-backend.ps1` (NEW) - Script startup per Task Scheduler
      - Location: Project root (tracked by git)
      - Eseguito da Task Scheduler con utente corrente
      - Log output: `C:\z21-Terminal\backend.log` via Tee-Object
  - **PowerShell aliases aggiornati** (su PC Windows):
    - `z21-start`: Crea task (se non esiste) + Start-ScheduledTask
    - `z21-stop`: Stop-ScheduledTask + cleanup Python processes
    - `z21-status`: Controlla Task Scheduler state invece di solo processi Python
    - `z21-restart`: Stop + Start via Task Scheduler
  - **Workflow:**
    ```powershell
    z21-start   # Prima volta: crea task automaticamente, poi lo avvia
    # Chiudi SSH completamente
    # Riapri SSH
    z21-status  # Backend ancora ATTIVO! ✅
    ```
  - **Benefici**:
    - ✅ Backend veramente persistente (not session-bound)
    - ✅ Zero setup manuale (task auto-creato al primo z21-start)
    - ✅ Gestibile via Task Scheduler GUI (taskschd.msc)
    - ✅ Può essere configurato per auto-start on reboot (opzionale)
  - **Documentazione aggiornata**:
    - `docs/GPU_DEPLOYMENT.md` - Funzioni PowerShell + caratteristiche chiave
    - Note: docs/ è gitignored (documentazione locale)
  - **Commit**: Script start-backend.ps1 committato (condiviso per Windows users)

### 2025-01-09 - 📖 **README UPDATE - CV PROFILES DOCUMENTATION**
- **📖 CV Profiles Documentation** - Added feature description to README
  - **Sezioni aggiornate**:
    - **Core Features**: Bullet point sintetico "CV Profiles: One-click TEST/NORMAL toggle"
    - **CV Operations checklist**: Dettagli tecnici (hotkey T, CV3/CV4, badge, config.json)
    - **Speed Matching notes**: Workflow pratico + warning importante
  - **Contenuto aggiunto**:
    - Hotkey T per toggle TEST/NORMAL (~1.2s)
    - Badge indicator (Flask = TEST, Check = NORMAL)
    - TEST mode: CV3≈0, CV4≈0 (risposta istantanea)
    - NORMAL mode: CV3/CV4 ripristinati (accelerazione realistica)
    - ⚠️ Warning: Tornare a NORMAL prima di chiudere/deployare
  - **Motivo**: Feature implementata 2025-01-08 ma non documentata in README
  - **File modificato**: `README.md`
  - **Commit**: `629cd12` - docs: add CV Profiles feature to README
  - **Merged to main**: `7104b51`

### 2025-01-09 - 🔔 **NOTIFICATION IMPROVEMENTS - ACCUMULATED CORRECTIONS**
- **🔔 Speed Correction Notifications** - Distinguish new vs maintained corrections
  - **Problema**: Notifica mostrava "Speed +2%" anche quando correzione era già attiva (WARNING zone)
  - **Comportamento precedente**:
    - CRITICAL +2 → notifica "Speed +2%" ✅
    - WARNING (ancora +2) → notifica "Speed +2%" ❌ (confuso, sembrava nuova modifica)
  - **Soluzione**: Messaggio diverso se correzione non cambia
    - **Nuova/cambiata**: "Loco 1: Speed +2%" (valore appena applicato o incrementato)
    - **Mantenuta**: "Loco 1: still at +2%" (stesso valore, WARNING zone)
    - **Sincronizzata**: "Consist 10: SYNCED" (correzione azzerata)
  - **Benefici**:
    - ✅ Chiaro quando correzione aumenta (+2 → +4 → +6)
    - ✅ Chiaro quando correzione è mantenuta (still at)
    - ✅ Mostra sempre valore accumulato totale
    - ✅ Evita confusione su correzioni persistenti
  - **File modificato**: `web/src/App.jsx` (notification logic)
  - **Commit**: `097c129` - feat: improve notification message for maintained speed corrections
  - **Merged to main**: `3548a70`

### 2025-01-09 - ⚡ **UVICORN AUTO-RELOAD - DEV MODE ONLY**
- **⚡ Development Workflow Optimization** - Auto-reload per sviluppo locale
  - **Problema**:
    - Flag `--reload` su `z21-start` (background) causa interruzioni log file
    - `--reload` + `Tee-Object` conflitto: log si ferma dopo poche righe
    - Uvicorn watchdog chiude file descriptor ad ogni restart
  - **Soluzione finale**: `--reload` SOLO su `z21-backend` (interactive mode)
    - `z21-backend`: Interactive mode con `--reload` ✅ (dev locale su PC)
    - `z21-start`: Background production SENZA `--reload` ✅ (log stabili)
  - **Production workflow** (backend-only changes via SSH):
    ```powershell
    git pull
    z21-restart  # ✅ Riavvio manuale veloce (~2s)
    ```
  - **Dev workflow** (locale su PC):
    ```powershell
    z21-backend  # ✅ Auto-reload attivo, vedi log real-time
    ```
  - **Quando serve z21-deploy**:
    - ✅ Modifiche frontend (rebuild Vite necessario)
    - ✅ Modifiche dipendenze (requirements*.txt)
    - ✅ Config critici (struttura config.json)
  - **Benefici**:
    - ✅ Log stabili su production (Tee-Object funziona correttamente)
    - ✅ Auto-reload disponibile per dev locale (z21-backend)
    - ✅ Workflow production: `git pull + z21-restart` (2 comandi, veloce)
  - **Documentazione aggiornata**:
    - `docs/GPU_DEPLOYMENT.md` - Sezione "Update Workflow" corretta
    - PowerShell alias: `z21-backend` con `--reload`, `z21-start` senza
  - **Note**: Documentazione solo locale (gitignored), commit non necessario

### 2025-01-08 - 📦 **REQUIREMENTS STRUCTURE REFACTOR - CPU/GPU SEPARATION**
- **📦 Requirements Files Refactor** - Separate CPU (Mac) and GPU (PC) dependencies
  - **Problema**:
    - Mac usa Python di sistema (Homebrew) → vulnerabile a `brew upgrade python` (break dependencies)
    - PC usa venv ma PyTorch GPU non tracciato (comando manuale da docs/GPU_DEPLOYMENT.md)
    - Nessuna protezione da upgrade, no reproducibility
  - **Soluzione**:
    - `requirements-cpu.txt` (NEW) - PyTorch CPU-only per macOS development (torch==2.2.2, torchvision==0.17.2)
    - `requirements-gpu.txt` (NEW) - PyTorch GPU + CUDA 11.8 per Windows PC production (con `--index-url`)
    - `INSTALL.md` (NEW) - Guida completa installazione: venv/conda, Mac/PC, troubleshooting
    - `README.md` - Link a INSTALL.md nella sezione Installation
    - `backend/requirements.txt` - FastAPI dependencies (unchanged)
    - `scripts/requirements.txt` - ultralytics + opencv-python (unchanged)
  - **docs/GPU_DEPLOYMENT.md** (local, gitignored) - Updated step 4 per usare requirements-gpu.txt
  - **Benefici**:
    - ✅ Versioni pinnate (reproducible builds)
    - ✅ Zero comandi manuali (no più `pip install torch --index-url ...`)
    - ✅ Separazione chiara CPU vs GPU
    - ✅ Protezione da Homebrew upgrades (con venv)
  - **Raccomandazione Mac**: Creare venv per isolare da system Python
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r backend/requirements.txt -r scripts/requirements.txt -r requirements-cpu.txt
    ```
  - **Commit**: `18bdb5d` - feat: separate CPU and GPU requirements files

### 2025-01-08 - 🔌 **PHASE 9: MOTOR LOAD MONITORING - TELEMETRY WIDGETS**
- **✅ Phase 9 Part 1 - Z21 Track-Level Telemetry** - Backend telemetry parsing
  - **z21.py extension**: `get_status()` now parses bytes 0-11 (telemetry data)
    - MainCurrent (mA), ProgCurrent (mA), FilteredCurrent (mA)
    - Temperature (°C), SupplyVoltage (V), VCCVoltage (V)
    - Little-endian uint16 parsing with proper unit conversion
  - **Backend API**: `/api/z21/telemetry` endpoint
    - Returns telemetry + quality checks + warnings array
    - Voltage thresholds: 14.0-18.0V normal range
    - Current thresholds: >2000mA high (short circuit risk)
    - Temperature thresholds: >50°C elevated, >60°C critical
  - **Test script**: `scripts/utils/test_z21_telemetry.py`
    - Validates telemetry parsing (211mA, 17.80V, 2.9°C measured)
    - Quality checks with descriptive output
  - **Commit**: `de565c6` - feat: Phase 9 Part 1 - Z21 track-level telemetry parsing
- **✅ Phase 9 Part 2 - Frontend Telemetry Popovers** - Hover/click UX widgets
  - **TrackTelemetryPopover.jsx** (⚡ badge) - Track power monitoring
    - Displays: MainCurrent, SupplyVoltage, FilteredCurrent, power state, short circuit
    - Warning banners for voltage/current issues (amber alert boxes)
    - Auto-refresh every 2s via polling
  - **Z21HealthPopover.jsx** (🖥️ badge) - Z21 system health
    - Displays: Temperature, VCC Voltage, hardware/firmware info, serial
    - Temperature warnings (elevated >50°C, critical >60°C)
    - Static system info (Model: Z21 White, Hardware: 0x0203, Firmware: 1.67, Serial: 111466)
  - **App.jsx enhancements**:
    - Background telemetry polling every 5s (warning detection)
    - Status badges wrapped in boxes (`bg-control-dark`, `rounded`, `border`)
    - **Desktop UX** (≥768px): Hover → instant popover (no animation, no backdrop)
    - **Mobile UX** (<768px): Tap → toggle popover (backdrop dismiss, slide-in animation)
    - Warning rings: `ring-2 ring-amber-500/50` when issues detected
    - Disabled state when Z21 offline
  - **Commit**: `99cb9e1` - feat: Phase 9 Part 2 - frontend telemetry popovers with hover/click UX
- **📚 Documentation Updates**:
  - `docs/MOTOR_LOAD_MONITORING.md`:
    - Status updated: ✅ PHASE 1-2 COMPLETED (2025-01-08)
    - Added Part 2 section with component architecture, UX design, API integration
    - Renamed RailCom section to Part 3 (future research)
  - `CLAUDE.md`: This changelog entry
- **🎯 Result**: Real-time telemetry monitoring con dual UX (hover on desktop, tap on mobile)
  - Professional UI with warning indicators
  - Graceful degradation (disabled when offline)
  - Production-ready Phase 9 implementation ✅

### 2025-01-08 - 🔬 **PHASE 9 PART 3 RESEARCH + LOG IMPROVEMENTS**
- **🔬 RailCom Plus Research (Phase 9 Part 3)** - Z21 White compatibility test
  - **Obiettivo**: Verificare se Z21 White (HW 0x0203) supporta RailCom Plus via LAN protocol
  - **Script creati**:
    - `scripts/utils/enable_railcom_plus.py` (227 righe) - Enable RailCom on ESU decoders
      - CV29 bit 3 (RailCom enable) + CV106=1 (RailCom Plus enable)
      - Operations mode programming con 3x retry (no ACK)
      - Warning per decoder non-ESU (Hornby TXS, Zimo MX630)
    - `scripts/utils/test_railcom_listener.py` (197 righe) - Monitor 0x0088 packets
      - Subscribe to Z21 broadcasts (flag 0x00000008 = RailCom bit 3)
      - Listen for LAN_RAILCOM_DATACHANGED (0x0088) packets
      - 60s monitoring window con statistics
  - **Test eseguito**: Loco 8 (E444 056 - ESU LokPilot 5)
    - CV29 = 30 (bit 3 already set), CV106 = 1 (written 3x)
    - Locomotive in movimento per 60s
    - **Risultato**: Zero 0x0088 packets received
  - **❌ Conclusione**: Z21 White does NOT expose RailCom Plus via LAN protocol
    - RailCom funziona internamente (POM read/write confermato)
    - Per-locomotive telemetry richiede Z21 Black o Z21 Pro
    - **Phase 9 Part 3 marked as NOT FEASIBLE** on current hardware
  - **Documentazione**: `docs/MOTOR_LOAD_MONITORING.md` updated with research findings
- **🐛 Temperature Bug Fix** - Z21 telemetry parsing
  - **Problema**: Dashboard mostrava 2.9°C invece di 29°C
  - **Root cause**: Incorrect `/10.0` division in `scripts/z21.py:171`
  - **Fix**: `temperature / 10.0` → `float(temperature)`
  - **Reason**: Z21 sends temperature as integer °C, not °C × 10 (unlike voltage in mV)
  - **Verifica**: App Z21 confermava 29°C
- **📱 iPhone WiFi Issue** - Z21 app connectivity
  - **Problema**: iPhone non connetteva a Z21 app, tablet OK
  - **Troubleshooting**: IP privato, tracciamento, subnet mask, DNS
  - **Soluzione**: "Forget network + reboot iPhone"
  - **Root cause**: Corrupted DHCP lease/cache (IP changed .7 → .32)
- **🖥️ PowerShell 7 Installation** - UTF-8 support attempt
  - **Installato**: PowerShell 7.5.4 via winget su PC Windows
  - **Obiettivo**: Fix emoji display in backend.log file
  - **Risultato**: Emoji scritte correttamente (UTF-8) ma font terminale non le visualizza
  - **Soluzione finale**: Lasciato z21-backend per emoji live, z21-start per production
  - **Note**: pwsh resta installato (~100MB), non interferisce con PowerShell 5.1
- **⚙️ z21-log Alias** - Quick log viewing
  - **Comando**: `Get-Content C:\z21-Terminal\backend.log -Wait -Tail 50`
  - **Aggiunto a**: PowerShell profile (`Microsoft.PowerShell_profile.ps1`)
  - **Usage**: `z21-log` per vedere log real-time (Ctrl+C to exit)
- **🔇 Telemetry HTTP Logs Filter** - Spam reduction
  - **Problema**: Log invaso da `GET /api/z21/telemetry` ogni 5s
  - **Soluzione**: Logging filter in `backend/main.py` lifespan startup
  - **Implementazione**:
    - `TelemetryFilter` class filters `/api/z21/telemetry` messages
    - Applied to `uvicorn.access` logger
    - Moved to `lifespan()` instead of `__main__` (uvicorn reload compatibility)
  - **Risultato**: Log pulito, mantiene WebSocket/GET/POST importanti
  - **Commits**:
    - `ac7702a` - feat: filter telemetry HTTP logs to reduce spam
    - `5fd100f` - fix: move telemetry filter to lifespan startup
- **📁 Files Modified**:
  - `scripts/z21.py`: Temperature parsing fix
  - `scripts/utils/enable_railcom_plus.py` (NEW)
  - `scripts/utils/test_railcom_listener.py` (NEW)
  - `backend/main.py`: Telemetry filter in lifespan
  - `C:\Users\Riccardo\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`: z21-log alias

### 2025-01-08 - 🐍 **VENV SETUP MAC - CPU DEPENDENCIES**
- **🐍 Virtual Environment Setup (macOS)** - Isolamento da system Python
  - **Setup eseguito**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r backend/requirements.txt -r scripts/requirements.txt -r requirements-cpu.txt
    ```
  - **Dependencies installate**:
    - FastAPI 0.115.5 + Uvicorn 0.32.1 + WebSocket 13.1
    - PyTorch 2.2.2 + torchvision 0.17.2 (CPU-only)
    - NumPy 1.26.4 (downgrade da 2.2.6 per compatibilità PyTorch)
    - OpenCV 4.12.0.88 + Ultralytics 8.3.249 (YOLO)
  - **NumPy compatibility fix**:
    - PyTorch 2.2.2 compilato con NumPy 1.x
    - opencv-python 4.12 richiede numpy>=2 (ma funziona con 1.26.4)
    - Pip warning su dependency resolver = **false positive**
    - Verifica: `import torch; import cv2; import numpy as np` → ✅ OK
  - **requirements-cpu.txt updated**: Aggiunto `numpy<2` constraint
  - **INSTALL.md updated**: Aggiunta sezione troubleshooting per NumPy warning
  - **Benefici**:
    - ✅ Protezione da `brew upgrade python` (isolation)
    - ✅ Dependencies pinnate per reproducibility
    - ✅ Alias bash attivano automaticamente venv se esiste
  - **Full stack test**: PyTorch + OpenCV + Ultralytics → ✅ YOLO ready

### 2025-01-08 - 🖥️ **WINDOWS PC ALIASES - STATUS CHECK & LOGGING FIX**
- **🖥️ z21-status Alias (Windows PC)** - Quick backend status check
  - **Funzione aggiunta a PowerShell profile**: `C:\Users\Riccardo\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`
  - **Check method**: Verifica porta 8000 in ascolto (TCP listen state)
  - **Output**:
    - `[OK] Backend ATTIVO (porta 8000 in ascolto)` - Backend running
    - `[X] Backend NON ATTIVO` - Backend stopped
  - **Motivo**: API localhost:8000 non risponde correttamente (timeout/CORS), più affidabile check porta TCP
- **🐛 Backend Logging Fix** - Unbuffered Python output
  - **Problema**: Backend.log non scriveva in tempo reale (buffering di `Tee-Object`)
  - **Soluzione**: Aggiunto flag `-u` (unbuffered) a Python in `z21-start`
  - **Before**: `python.exe -m uvicorn ...`
  - **After**: `python.exe -u -m uvicorn ...`
  - **Risultato**: Log scritti immediatamente su file, no più buffering delays
  - **Note**: Solo `z21-start` (background mode), NON `z21-backend` (interactive mode)
- **♻️ z21-reload → z21-restart** - Alias renamed for clarity
  - **Old**: `z21-reload` (ambiguo - reload vs restart?)
  - **New**: `z21-restart` (chiaro - stop + start backend)
  - **Usage**: `z21-restart` per riavviare backend in background dopo updates
- **📁 File Modified**:
  - `C:\Users\Riccardo\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1` (via SSH + scp workflow)

### 2025-01-08 - 🧹 **CLEANUP: CONSIST_STATE.JSON REMOVAL**
- **🧹 consist_state.json Deprecated** - Migration to config.json completed
  - **Files deleted**:
    - `backend/consist_state.json` (gitignored runtime file)
    - `backend/consist_state.json.example` (tracked template)
  - **Code cleanup**:
    - Removed `CONSIST_STATE_FILE` constant from `z21_manager.py`
    - Removed fallback migration code in `_load_persisted_state()`
  - **Reason**: Virtual Mode state (virtual_mode, auto_compensation_enabled) now fully managed via `config.json`
  - **Benefit**: Single source of truth, tracked by git, no manual file copying needed
  - **Documentation updated**: `docs/GPU_DEPLOYMENT.md` - removed all consist_state.json references
  - **Commit**: `463a9d8` - refactor: remove consist_state.json (migrated to config.json)
- **⚠️ Virtual Mode Warning** - Added safety check for misconfiguration
  - **Warning added**: `_load_persisted_state()` checks if consist has `virtual_mode=False`
  - **Message displayed**:
    ```
    ⚠️  WARNING: Consist {id} has virtual_mode=False
        → Speed commands will be sent to consist address {id} (DCC mode)
        → Locomotives may not respond unless CV19={id} is programmed
        → Set 'virtual_mode: true' in config.json consists.{id} for proper operation
    ```
  - **Benefit**: Prevents silent failures when locomotives don't respond (wrong address)
  - **Note**: Current config.json già ha `virtual_mode: true` per consist 10 e 11 ✅
  - **Commit**: `fdbe2db` - feat: add warning for consist virtual_mode misconfiguration

### 2025-01-08 - 🐛 **SHIFT+KEY BUG FIX - DUAL CONTROLLER RESPONSE**
- **🐛 SHIFT+key only triggered one controller** - Critical keyboard shortcut regression
  - **Problema rilevato**:
    - SHIFT+7 dovrebbe cambiare velocità su ENTRAMBI i controller (Consist 10 + Consist 11)
    - In realtà solo Controller #1 rispondeva (Consist 10)
    - Controller #2 (Consist 11) non rispondeva mai
    - Console logs mostravano Controller #1 trigger 3x volte invece di 1x
  - **Root cause identificata**:
    - Handler functions (`handleSpeedChange`, `handleDirectionChange`, `handleFunctionToggle`, `handleToggleVirtualMode`, `handleToggleAutoCompensation`, `showNotification`) erano **NON wrappati in useCallback**
    - Ad ogni render, React creava NUOVE istanze delle funzioni
    - ConsistController's `useEffect` dipendeva da questi handlers → re-run ad ogni cambio
    - Multiple event listeners venivano aggiunti senza cleanup → listener duplicati
    - Controller #1 processava evento, triggering re-render → nuovo listener aggiunto → stesso evento processato 3x
    - Controller #2's listener veniva corrotto dalle re-render continue
  - **Soluzione applicata**:
    - ✅ **web/src/App.jsx**: Wrapped all handlers in `useCallback` with proper dependencies
    - ✅ **web/src/hooks/useNotification.jsx**: Wrapped `showNotification` in `useCallback`
    - ✅ **web/src/components/ConsistController.jsx**: Removed debug console.log statements
  - **Verifica funzionamento**:
    - SHIFT+7 → Both controllers respond: "Controller #1 setting speed 70%" + "Controller #2 setting speed 70%"
    - SHIFT+backslash → Both controllers stop: "Controller #1 setting speed 0%" + "Controller #2 setting speed 0%"
    - Due notifiche appaiono correttamente (una per controller)
  - **Benefici**:
    - ✅ SHIFT shortcuts now work correctly on BOTH controllers simultaneously
    - ✅ No more duplicate event listeners
    - ✅ Cleaner re-render behavior (handlers stable across renders)
    - ✅ Consistent behavior with design intent
  - **Commit**: `8099b00` - fix: SHIFT+key now triggers both controllers correctly

### 2025-01-08 - 🐛 **TRACKING DAEMON RTSP RECONNECT FIX**
- **🐛 Tracking stops after long idle periods** - RTSP timeout breaks YOLO inference
  - **Problema rilevato**:
    - User apre video feed, lascia aperto per minuti/ore senza far partire locomotive
    - Quando locomotive partono, YOLO tracking non funziona più
    - Nessun bounding box visualizzato, nessun speed sync
    - Debug toggle on/off non risolve, tracking morto permanentemente
    - Video feed continua a funzionare correttamente (video visibile)
  - **Root cause identificata**:
    - **RTSP stream timeout** dopo periodo di idle prolungato (no activity)
    - `tracking_daemon.py` loop: `cap.read()` fallisce → log "Lost video connection" → `sleep(1)` → retry con **stesso cap object morto**
    - Loop infinito provando a leggere da VideoCapture object disconnesso
    - **video_feed.py** HA logica di reconnect (rilascia cap + riconnette) → per questo video funziona
    - **tracking_daemon.py** NON aveva logica di reconnect → tracking si bloccava
  - **Soluzione applicata**:
    - ✅ Import `reconnect_rtsp_stream()` da `tracking.rtsp_handler` (funzione già esistente)
    - ✅ Quando `cap.read()` fallisce: close vecchio cap + crea nuovo VideoCapture con `buffer=1`
    - ✅ Retry ogni 2s finché RTSP non risponde (consistent con video_feed.py)
    - ✅ Log state changes: "Lost video connection, reconnecting..." → "Video connection restored"
  - **Comportamento dopo fix**:
    - Tracking daemon sopravvive a RTSP timeout durante long idle periods
    - YOLO inference riprende automaticamente quando stream reconnects
    - Bounding boxes + speed sync funzionano normalmente dopo reconnect
    - Consistent behavior tra video_feed.py e tracking_daemon.py
  - **Benefici**:
    - ✅ No more permanent tracking death after long idle
    - ✅ RTSP stream resilience (auto-reconnect every 2s)
    - ✅ YOLO inference resumes transparently after reconnect
    - ✅ Production reliability improvement (daemon survives network hiccups)
  - **File modificato**: `backend/tracking_daemon.py` (6 lines: +3 import, +3 reconnect logic)
  - **Commit**: `c3d26b7` - fix: tracking daemon now reconnects RTSP on timeout

### 2025-01-08 - 🎚️ **CV PROFILES - GLOBAL TEST/NORMAL MODE TOGGLE**
- **🎚️ CV Profiles Feature** - One-click toggle tra Test e Normal mode per TUTTE le locomotive
  - **Problema**:
    - Loco 1 (ESU LokSound V4.0) e Loco 7 (Hornby TXS) NON hanno funzione "Momentum Off" (F4)
    - Altre loco (ESU LokPilot 5) hanno F4 nativo per bypassare CV3/CV4 temporaneamente
    - Per speed matching tests serve CV3≈0, CV4≈0 (risposta immediata)
    - Per uso quotidiano serve CV3/CV4 alti (accelerazione/decelerazione lenta tipo treno vero)
    - Cambio manuale CV via DecoderPro ogni volta = sbattimento
  - **Soluzione**: CV Profiles globali con toggle unico
    - **Hotkey T**: Toggle globale Test ↔ Normal mode per TUTTE le locomotive
    - **Badge header**: Flask icon (amber) per TEST / Check icon (green) per NORMAL
    - **Operations mode write**: CV scritti mentre loco circolano (no programming track)
    - **NO backup**: Config.json contiene ENTRAMBI i profili (normal + testing sempre presenti)
  - **CV Profiles configurati** (6 locomotive attive):
    ```json
    "cv_profiles": {
      "1": {"normal": {"cv3": 78, "cv4": 58}, "testing": {"cv3": 0, "cv4": 0}},
      "2": {"normal": {"cv3": 23, "cv4": 14}, "testing": {"cv3": 0, "cv4": 0}},
      "5": {"normal": {"cv3": 22, "cv4": 16}, "testing": {"cv3": 0, "cv4": 0}},
      "6": {"normal": {"cv3": 23, "cv4": 14}, "testing": {"cv3": 0, "cv4": 0}},
      "7": {"normal": {"cv3": 24, "cv4": 16}, "testing": {"cv3": 1, "cv4": 1}},
      "8": {"normal": {"cv3": 22, "cv4": 15}, "testing": {"cv3": 0, "cv4": 0}}
    },
    "test_mode": "normal"
    ```
  - **Note valori CV**:
    - **Loco 1**: CV3=78, CV4=58 (motore molto reattivo, serve "frenarlo" per matchare altre)
    - **Loco 7**: CV3=24, CV4=16 normal, **CV3=1, CV4=1 testing** (0,0 troppo brusco vs loco 8)
    - **Altre loco**: CV3=22-23, CV4=14-16 (ESU LokPilot 5 standard)
    - **Loco 4**: Non inclusa (in disuso, mai utilizzata)
  - **Workflow utente**:
    1. Premi **T** → Badge cambia immediatamente (ottimistico)
    2. Backend controlla track power + short circuit (errore immediato se off)
    3. Backend scrive CV testing/normal da config.json (**~1.2s totali**, fire-and-forget + 100ms delays)
    4. Notifica finale conferma successo (3s duration) o errore con dettagli
    5. Fai speed matching tests (slider risponde istantaneamente)
    6. **⚠️ IMPORTANTE**: Ripremi **T** per tornare a normal mode **PRIMA** di chiudere/deployare
  - **⚠️ CRITICAL: Deploy Consistency Rule**:
    - **PC deployment**: `z21-deploy` esegue `git reset --hard` → **config.json sovrascritto**
    - **SE dimentichi di tornare a normal**: Locomotive hanno CV test (0,0) ma config dice "normal"
    - **Conseguenza**: Disallineamento stato fisico vs backend (treni rispondono istantaneamente)
    - **Fix**: Premi T due volte (test → normal → test → normal) per riallineare
    - **Procedura operativa corretta**:
      1. Premi T → TEST mode
      2. Fai speed matching
      3. **Premi T → NORMAL mode** (ripristina CV)
      4. OK per chiudere/deployare
  - **Ottimizzazioni implementate**:
    - ✅ **Fire-and-forget CV write**: Rimosso get_loco_info() + wait error loop → da 6s a ~1.2s
    - ✅ **NO backup file**: Config.json ha entrambi i profili → niente da sovrascrivere
    - ✅ **NO CV read**: Config.json è SoT → zero delay lettura (~20s risparmiati)
    - ✅ **Track power check**: Validazione preventiva → errore chiaro se power off
    - ✅ **Success/failure count**: Messaggio dettagliato se alcune loco falliscono
    - ✅ **Dynamic notification duration**: Fix CSS animation hardcoded 2s → rispetta duration parametro
  - **Benefici**:
    - ✅ Approccio uniforme per TUTTE le locomotive (non serve ricordare chi ha F4)
    - ✅ Velocissimo: ~1.2s invece di manuale DecoderPro
    - ✅ Funziona anche su Hornby TXS (che non avrà mai Momentum Off hardware)
    - ✅ Config.json tracked by git → valori CV versionati
    - ✅ Zero cognitive load: premi T, lavori, ripremi T, fatto
  - **Implementazione**:
    - `config.json`: Sezione `cv_profiles` + `test_mode` state persistence
    - Backend: `toggle_test_mode()` con track power validation + error handling
    - Backend endpoints: `/api/toggle-test-mode` (POST), `/api/test-mode` (GET)
    - Frontend: Hotkey T + clickable badge (flask/check icon) + rollback su errore
    - Operations mode: CV3/CV4 scritti via `z21.write_cv_ops_mode()` fire-and-forget
  - **Files modificati**:
    - `config.json`: Added cv_profiles + test_mode
    - `backend/z21_manager.py`: toggle_test_mode() method
    - `backend/main.py`: API endpoints
    - `scripts/z21.py`: Optimized write_cv_ops_mode() (fire-and-forget)
    - `web/src/App.jsx`: Hotkey T handler + badge
    - `web/src/components/Notification.jsx`: Dynamic animation duration fix
  - **Commit**: `2e4abda` - feat: CV Profiles - global Test/Normal mode toggle for all locomotives

---

## Recent Changelog (2025-12-28 → 2025-01-05)

### 2025-01-05 - 🚀 **YOLO v5 SQUARE MODEL + GATE DISPLAY FIXES**
- **🎯 YOLO v5 Square Model (640x640)** - CPU-optimized training completato
  - **mAP50: 0.931** (better than v4 rectangular 0.919!)
  - Training script: supporto dual mode via `RECTANGULAR` flag
  - Roboflow preprocessing: "Stretch to 640x640" (v5) vs "Fit within 1280x1280" (v4)
  - Auto-fetch latest Roboflow version (no hardcoded version number)
  - Deploy strategy: v5 (square) for Mac CPU, v4 (rectangular) for PC GPU future deployment
  - Model: `scripts/models/best.pt` → BiancAlice_v5 (now committed to git)
- **⚙️ YOLO Inference Size Configurable** - From hardcoded to config-driven
  - Added `yolo_imgsz: 640` to `config.json` under `tracking` section
  - `tracking_daemon.py`: loads and uses `self.yolo_imgsz` from config
  - `track_consist_yolo.py`: loads and uses `self.yolo_imgsz` from config
  - Easy switch: 640 (fast CPU) ↔ [640, 1152] (accurate GPU) without code changes
  - Notes field explains: "640 for square models (fast, CPU), [640, 1152] for rectangular models (accurate, GPU)"
- **🎨 Gate Display Fixes** - Colori corretti finalmente visibili
  - **ROOT CAUSE**: `gate_json_to_dict()` non copiava il campo `color` dal config
  - **FIX**: Aggiunto `color` field a gate dict conversion (con fallback yellow)
  - **RGB→BGR**: `draw_gates_overlay()` ora converte correttamente `(R,G,B)` → `(B,G,R)` per OpenCV
  - **Color scheme**: Gate 1-2 Orange [255,165,0] (C11), Gate 3-4 Cyan [0,255,255] (C10)
  - Rimosso hardcoded `GATE_COLORS` array (ora legge da config)
- **✨ Immediate Gate Rendering After ENTER** - No more disappearing gates!
  - **PROBLEMA**: ENTER salvava solo in `marker_state.config['gates']`, `draw_gates_overlay()` leggeva da `tracker.gates`
  - **SOLUZIONE**: `save_current_gate(tracker)` ora aggiorna ENTRAMBI:
    - `config['gates']` (JSON format per S save)
    - `tracker.gates` (dict format per rendering immediato)
  - Workflow: ENTER → gate visibile subito con colore corretto ✅
  - Tracking: serve ancora riavvio script + assign gate_ids in config.json
- **🎬 Pause Feedback Banner** - Visual confirmation for SPACE key
  - **Design**: Semi-transparent black overlay (70% opaque) + white text centered
  - **Size**: 300x80px banner centro schermo
  - **Duration**: 2 seconds, then auto-disappears
  - **Text**: "PAUSED" or "RESUMED" (ASCII only, no emoji for OpenCV compatibility)
  - **Font**: `FONT_HERSHEY_SIMPLEX` with `thickness=4` for bold effect
  - Console log + visual feedback doppio conferma
- **📐 Config.json Inline Array Formatting** - Improved readability
  - Arrays reformatted from multi-line to inline: `"center": [1227, 213]`
  - File size reduced: 130 lines → 96 lines (26% smaller)
  - Gate restoration: Gate 2 retrieved from `git show HEAD:config.json`
  - Renamed gates: G5→G3, G6→G4 per consistency
- **📝 Files Modified**:
  - `scripts/utils/3_train_yolo_colab.py` - RECTANGULAR flag + auto-version fetch
  - `scripts/track_consist_yolo.py` - gate colors + pause banner + immediate render + gate_json_to_dict fix
  - `backend/tracking_daemon.py` - load yolo_imgsz from config
  - `config.json` - yolo_imgsz parameter + inline arrays + gate color scheme

### 2025-01-05 (tardi) - 🎥 **RTSP BUFFER LAG FIX + CLI FUNCTION STATES FIX**
- **🎥 CRITICAL FIX: RTSP Stream Buffer Accumulation** - Video feed no longer lags 20+ seconds
  - **Problem**: Video feed and gate tracking accumulated progressive lag over time
    - Initial: 3-4s delay, After 10+ min: 20+ seconds delay
    - Impact: Gate crossing detection missed locomotives (daemon saw them 20s late)
  - **Root Cause**: Default OpenCV buffer accumulates frames indefinitely
    - Camera: 15 FPS constant, Processing: ~14.9 FPS average
    - Buffer growth: ~1 frame per 10 seconds → 600 frames after 10 minutes
  - **Solution**: `cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)` on all RTSP streams
    - Always reads freshest frame available
    - Adaptive: fast systems (PC GPU) read most frames, slow systems (Mac CPU) skip old ones
    - Benefits both real-time tracking AND video feed visualization
  - **Files Modified**:
    - `backend/video_feed.py` - Added buffer=1 at init + reconnect (2 locations)
    - `backend/tracking_daemon.py` - Added buffer=1 at init
    - `scripts/track_consist_yolo.py` - Added buffer=1 at init
  - **Result**: Gate crossing detection now real-time, locomotives no longer miss gates
- **🎛️ FIX: CLI Function States for Locomotives in Consists** - Functions display correctly
  - **Problem**: Launching with loco 7 or switching to it showed all functions OFF
    - Applies to all locos in consists (1, 5, 7, 8)
    - Functions were active on decoder but not synced to display
  - **Root Cause**: String matching bug in `_sync_function_states()` (line 516)
    - Old: `if "CONSIST" in self.all_addresses.get(self.address, "")`
    - Loco 7 name: "E656 239 (Rivarossi HR2966S) [IN CONSIST 11]" contains "CONSIST"
    - Entered consist branch, tried to find address 7 in `self.consists`, failed, returned without sync
  - **Solution**: Changed to dict membership check
    - New: `if self.address in self.consists`
    - Precise: only matches actual consist addresses (10, 11)
    - Loco addresses (1, 5, 7, 8) correctly query directly
  - **DCC Architecture Note**: Functions are properties of individual locomotives, not consists
    - Consists only control speed/direction (CV19 in DCC mode)
    - Function states always read from locomotive decoders
  - **Files Modified**:
    - `scripts/z21_controller.py` - Fixed `_sync_function_states()` check
  - **Result**: Function states now display correctly for all locomotives, in consist or standalone
- **📊 Commits**:
  - `a5cdecc` - fix: RTSP stream buffer lag (CAP_PROP_BUFFERSIZE = 1)
  - `19a539a` - fix: CLI function state sync for locomotives in consists

### 2025-01-03 (sera) - ♻️ **REFACTOR: Centralized Config Loading**
- **🎯 Obiettivo**: Eliminare duplicazione config loading (~6 file con json.load/dump)
- **✅ Config Loader Module**: `backend/config_loader.py` creato
  - `load_config()`: carica config.json + merge config.local.json (gitignored)
  - `save_config()`: salva SOLO config.json (mai config.local.json)
  - `get_config_path()`: path centralizzato
  - Deep merge algorithm per override ricorsivo
  - Priority: config.local.json > config.json
- **✅ File Refactorati** (7 totali):
  - `backend/main.py` - API endpoints (~12 load_config chiamate)
  - `backend/tracking_daemon.py` - daemon startup + gate config
  - `backend/video_feed.py` - video overlay + FPS settings
  - `backend/z21_manager.py` - persisted state load/save
  - `backend/roster_loader.py` - consist loader
  - `scripts/track_consist_yolo.py` - standalone script con wrapper
  - `.gitignore` - aggiunto config.local.json
- **✅ Benefici**:
  - Single source of truth per config loading
  - Machine-specific settings (debug mode PC) senza git conflicts
  - DRY principle - zero duplicazione codice
  - Consistent error handling
  - First-load log (stampa solo 1 volta, no spam da 18 chiamate)
- **📄 Config.local.json Support**: Override machine-specific
  - Example file: `config.local.json.example` con istruzioni
  - Gitignored (mai committato)
  - Caso d'uso: `debug.enabled: true` su PC, `false` su Mac
- **📊 Testing**:
  - ✅ Config loading verified (Mac)
  - ✅ Override functionality tested
  - ✅ Git ignore verified
  - ✅ All syntax checks passed
- **📦 Commits**:
  - `132ad18` - refactor: centralized config loading
  - `93376c5` - config: disable debug mode for production (debug.enabled: true→false)
  - Merged develop→main→pushed entrambi

### 2025-01-03 (notte) - 🔧 **PHASE 6 ENHANCEMENTS: Virtual/DCC Mode + CV19 Management**
- **✅ Virtual/DCC Mode Selection** - Consist form con scelta modalità
  - Radio buttons: Virtual Mode (default) vs DCC Mode
  - Virtual Mode: CV19=0, software consist control (safe default)
  - DCC Mode: CV19=consist_address, hardware consist (writes CV)
  - Warning dinamico quando DCC Mode selezionato
  - Form context-aware: "Creating in" vs "Switching to" per edit
- **✅ CV19 Management Completo** - Backend gestisce CV19 automaticamente
  - **POST /api/consists**: scrive CV19 basato su virtual_mode parameter
  - **PUT /api/consists**: rileva mode change e scrive CV19 di conseguenza
  - **DELETE /api/consists**: scrive CV19=0 se consist in DCC mode
  - Reload consist_data dopo ogni CRUD prima di broadcast
- **✅ Delete Modal con CV19 Warning** - Conferma intelligente
  - DCC Mode: warning amber "⚠️ Will write CV19=0 to both locomotives"
  - Virtual Mode: messaggio generico "permanently remove from configuration"
  - Dual button: Cancel (grigio) + Delete (rosso)
  - Z-index 100/110 per overlay corretto
- **✅ WebSocket Real-Time Sync** - Auto-refresh dopo CRUD
  - Broadcast `initial_state` dopo create/update/delete
  - Frontend riceve update → dropdowns si aggiornano automaticamente
  - Multi-device sync: modifiche da un device aggiornano tutti
- **🛡️ Tracking Daemon Improvements** - Gestione errori robusta
  - Skip consists senza `gate_ids` (Virtual Consist software-only)
  - Skip consists con locomotive non-trained in YOLO (graceful degradation)
  - Warning chiaro: "Trained locomotives: [1, 5, 7, 8]"
  - Sistema non crasha mai, qualunque configurazione utente crei
- **🎨 UI Polish** - Header refinements
  - Status indicators: rimosso box background, solo contenuto
  - Track Power indicator: `w-4` invece di `w-7` (spacing compatto)
  - Reload Roster: solo icona (consistente con Add Controller, Consist Manager)
- **🖥️ Deploy Scripts Improvements** - Controllo remoto PC production
  - **z21-stop.bat** (NEW): killa backend Python processes via `taskkill`
  - **z21-deploy.bat** (MODIFIED): NON avvia backend automaticamente
  - Workflow: `z21-deploy` → `z21-backend` manuale → `z21-stop` quando necessario
  - SSH-friendly: pieno controllo da Mac, log visibili
- **📊 Testing & Deployment**:
  - ✅ Consist 12 creato/testato/cancellato (Virtual Mode senza gates)
  - ✅ CV19 write verificato per tutti i mode changes
  - ✅ Dropdowns aggiornati automaticamente dopo CRUD
  - ✅ Tracking daemon skip non-trained locos (no crash)
  - ✅ Merge develop→main completato
  - ✅ Push GitHub main branch
  - ✅ Deploy PC Windows production (GPU) - backend perfettamente funzionante
- **📁 File Modificati**:
  - Backend: `main.py` (+407/-43 righe), `tracking_daemon.py` (+48/-10)
  - Frontend: `ConsistForm.jsx` (+68 righe mode selection), `ConsistManagerModal.jsx` (+50 modal)
  - Frontend: `App.jsx` (header UI polish)
  - Scripts PC: `z21-stop.bat` (NEW), `z21-deploy.bat` (UPDATED)
- **🎯 Status**: Phase 6 completo e deployment live su entrambi Mac (dev) e PC (production)

### 2025-01-03 (sera) - 🎉 **PHASE 6: CONSIST MANAGER UI - COMPLETATA**
- **✅ Phase 6A: Mobile Header Refactor** - Responsive hamburger menu
  - MobileMenu component con slide-in animation (300ms ease-out)
  - Hamburger button mobile-only (<768px)
  - Desktop mantiene inline layout con pulsante "⚙️ Consists"
  - Menu items: Consist Manager, Add Controller, Reload Roster, Wake Lock
- **✅ Phase 6B: Backend CRUD API** - Consist management endpoints
  - **GET `/api/consists`**: restituisce consists + gates + tracking_assignments + reference_locos
  - **POST `/api/consists`**: crea nuovo consist con reference/adjust config
  - **PUT `/api/consists/{address}`**: aggiorna consist esistente
  - **DELETE `/api/consists/{address}`**: elimina consist da config.json + reference_locos
  - **POST `/api/restart-daemon`**: riavvia tracking daemon per reload config
  - Salvataggio automatico in `config.json` (tracking_assignments + reference_locos)
- **✅ Phase 6B: Frontend Components** - UI completa consist manager
  - **ConsistManagerModal.jsx**: modal overlay con backdrop, load/create/edit/delete consists
  - **ConsistCard.jsx**: display consist con badges Reference/Adjust colorati
  - **ConsistForm.jsx**: form create/edit con radio buttons "Reference Locomotive"
  - Integration App.jsx: sostituito placeholder con componente reale
- **🎯 Reference/Adjust Strategy FIX**: Lead/Rear fisica ≠ Reference/Adjust speed matching
  - **Decoupled logic**: Lead/Rear = posizione fisica, Reference/Adjust = speed matching role
  - **config.json**: sezione `reference_locos` con mapping consist → reference/adjust addresses
  - **UI badges**: verde "Reference" (mai toccata), amber "Adjust" (da compensare)
  - **Default**: Rear = Reference (decoder stabile), Lead = Adjust
  - **Esempio C11**: Lead=7 (Hornby, Adjust), Rear=8 (ESU, Reference)
- **📊 Features Implementate**:
  - View: lista consist con locomotive, gates, Virtual Mode status
  - Create: nuovo consist con selezione lead/rear/gates/reference
  - Edit: modifica consist esistente (address locked)
  - Delete: rimozione con conferma + cleanup reference_locos
  - Auto daemon restart dopo ogni CRUD operation
  - Validazione form: address required, lead≠rear, numero valido
- **📁 File Creati/Modificati**:
  - Backend: `main.py` (+168 righe API endpoints)
  - Frontend: `ConsistManagerModal.jsx` (NEW - 218 righe)
  - Frontend: `ConsistCard.jsx` (NEW - 152 righe)
  - Frontend: `ConsistForm.jsx` (NEW - 260 righe)
  - Frontend: `MobileMenu.jsx` (NEW - 82 righe)
  - Frontend: `App.jsx` (+5 righe import/integration)
  - CSS: `index.css` (+18 righe slide-in animation)
- **🎯 Next**: Testing Mac → Merge develop→main → Push → Deploy PC production

### 2025-01-03 (tardo pomeriggio) - 📚 **DOCUMENTATION REFACTOR: CLAUDE.md Reduction**
- **🎯 Obiettivo**: Ridurre CLAUDE.md spostando sezioni grandi in docs/ folder
  - File troppo pesante (2066 righe) difficile da navigare
  - Adottata strategia: file docs/ specializzati con link da CLAUDE.md
- **📝 File docs/ creati**:
  - **docs/CONSIST_ROSTER.md** (93 righe) - Consist 10/11 + roster completo 7 locomotive
  - **docs/WEB_DASHBOARD.md** (488 righe) - Stack tecnologico, features, workflow development
  - **docs/COMPUTER_VISION.md** (995 righe) - Sistema YOLO tracking, gate detection, Virtual Mode
  - **docs/CONFIG_REFACTOR.md** (280 righe) - Technical doc refactoring config.json (2025-01-03)
- **✂️ CLAUDE.md ridotto**:
  - **Sezione "Consist Configuration & Locomotive Roster"**: 93 righe → 9 righe summary + link
  - **Sezione "Web Dashboard"**: 488 righe → 26 righe summary + link
  - **Sezione "Computer Vision Tracking System"**: 995 righe → 34 righe summary + link
- **📊 Risultato**:
  - **Righe originali**: 2066
  - **Righe finali**: 643
  - **Riduzione totale**: 1423 righe (-68.9%)
  - **Totale estratto in docs/**: 1856 righe (4 files)
- **✅ Benefici**:
  - CLAUDE.md ora è un indice conciso con overview + link
  - Documentazione specializzata più facile da navigare
  - Stessa strategia usata per Z21_PROTOCOL.md, JMRI_INTEGRATION.md, etc.
  - Index completo in sezione "📚 Documentazione Estesa"

### 2025-01-03 - 🎉 **MILESTONE: Phase 4 FULLY COMPLETED + GPU Deployment LIVE**
- **✅ Task 4.1 COMPLETED**: Video Performance Optimization
  - Frame queue sharing architecture tested and verified
  - Video NO LONGER freezes durante Δt calculation
  - Performance confermata: smooth video feed con gate crossing detection
- **✅ Task 4.2 COMPLETED**: Generic Gate Tracking Refactor
  - Multi-consist support via config.json completato
  - `consist_data` dict sostituisce tutte le variabili hardcoded
  - Generic `_update_gate_timing()` funziona per ANY consist
  - Sistema ora completamente config-driven
- **✅ Phase 4B COMPLETED**: Virtual Consist Mode
  - CV19 toggle automatico implementato (DCC ↔ Virtual Mode)
  - Speed compensation con Δt feedback da gate timing funzionante
  - UI toggle in ConsistController con status indicators
  - Auto-compensation enable/disable implemented
  - Backend: z21_manager.py con enable/disable_virtual_mode()
  - WebSocket: toggle_virtual_mode + toggle_auto_compensation messages
  - Persist state: consist_state.json
- **🖥️ GPU Deployment LIVE**: PC Windows production deployment
  - ✅ SSH passwordless configurato
  - ✅ Python + CUDA environment setup completato
  - ✅ Repository clonato + dependencies installate
  - ✅ Tailscale Serve configurato (https://gaming-pc.tail9350d7.ts.net)
  - ✅ Backend running in production mode (porta 8000)
  - ✅ Frontend build servito da FastAPI (conditional serving)
  - ✅ YOLO tracking su GPU (CPU usage ridotto 800% → ~100%)
  - ✅ Deployment script `z21-deploy` funzionante
  - ✅ Testato e verificato: sistema completamente operativo

### 2025-12-30 (sera)
- **🎯 Phase 4: Gate Timing Detection COMPLETATA**: Cross-gate timing implementato per Consist 11
  - Gate 1 posizione aggiornata (spostato 80px più in alto)
  - Fix critico Δt calculation con "fresh timestamps" logic
  - Session summary al quit (durata, frames, gate crossings, stats)
  - Console logging ottimizzato (ridotto rumore)
- **🎨 Fix colori OpenCV**: Risolti problemi leggibilità
  - ⚠️ **REGOLA**: OpenCV NON supporta Unicode/emoji - solo ASCII
  - Colori Loco 8 corretti (rosso brillante)
  - Testo Δt waiting: bianco per leggibilità
- **🎯 Next: Phase 4B - Virtual Consist Mode** (pianificato 2025-12-31)

### 2025-12-31 (YOLO Integration - Phase 4 Complete)
- **🚀 Tracking Daemon Integrato**: Headless YOLO + WebSocket broadcast
  - `backend/tracking_daemon.py` - YOLO inference, gate timing, cross-gate Δt
  - Auto-reconnect WebSocket (exponential backoff 2s→30s)
  - Tracking continua offline, riconnette automaticamente
- **🎥 Video Feed con Overlay**: MJPEG stream + gate markers + Δt panel
  - `backend/video_feed.py` - RTSP→MJPEG, draw gates + Δt stats
  - Pannello Δt sempre visibile (anche "Waiting...")
  - Pallini YOLO rimossi (delay RTSP ingestibile)
- **📊 Frontend Δt Stats**: React component + WebSocket sync
  - VideoFeedPanel.jsx collapsible (default chiuso)
  - Prevent re-render inutili (check valore cambiato)
- **⚙️ Soglie Timing Aggiornate**: |Δt| < 1.0s SYNCED, 1.0-2.0s WARNING, >2.0s CRITICAL
  - Aggiornato daemon, yolo track, frontend
- **🔧 Fix Logica Cross-Gate**: Ripristinata logica originale identica
  - 4 detection points tutti cross-gate (L7@G1-L8@G2, L7@G2-L8@G1)
  - Rimosso check `< 5.0s` ridondante
  - Fresh timestamp check: `> self.last_delta_t_time`
- **📁 Camera Config Centralizzato**: `camera_config.json` project root
  - `scripts/camera_utils.py` loader condiviso
  - Tutti script aggiornati (tracking, video feed, utilities)
  - README_CAMERA.md istruzioni setup
- **🔄 Alias z21 Aggiornato**: 3 tab iTerm2 (backend + frontend + daemon)
- **⚠️ Issue Performance**: Daemon molto più lento di track_consist_yolo.py standalone
  - Detection ogni 5 giri vs ogni giro (yolo track)
  - Ritardo 10+ secondi vs immediato
  - Da investigare: WebSocket overhead, frame rate, RTSP buffering
- **🎯 Status**: MVP tracking integrato ma performance non accettabile - serve ottimizzazione

### 2025-12-31 (sera) - 🎯 **PERFORMANCE FIX CRITICO**
- **🐛 ROOT CAUSE IDENTIFICATA**: Doppio daemon in conflitto!
  - **Problema**: Alias `z21` lanciava daemon manuale + TrackingManager lanciava daemon auto
  - **Conflitto**: DUE processi leggevano stessa camera RTSP + YOLO inference contemporanea
  - **Sintomi**: Detection saltate, lag 10+ secondi, valori Δt errati/alternanti
- **✅ SOLUZIONE**: Rimosso daemon da alias `z21`
  - Alias aggiornato: solo 2 tab (backend + frontend)
  - TrackingManager gestisce daemon automaticamente (start/stop con cooldown 10s)
  - Nessun daemon manuale necessario
- **🚀 RISULTATO**: Performance perfette ripristinate!
  - Detection **ogni giro** (non più ogni 5 giri)
  - Δt **immediato** (non più ritardo 10+ secondi)
  - Valori **corretti** (0.156s, 0.309s SYNCED)
  - Cooldown funzionante (daemon auto-killed dopo 10s stop)
- **📝 File modificati**:
  - `~/.bash_aliases` - Funzione `z21()` aggiornata (rimossa 3a tab tracking)
  - `web/src/components/VideoFeedPanel.jsx` - Fix aspect ratio video (`objectFit: contain`)

### 2025-01-01 (sera - tardi) - 📋 **PHASE 4D PLANNING: Generic Gate Tracking Refactor**
- **🎯 Obiettivo**: Documentare refactoring necessario per supporto multi-consist config-driven
  - Gate tracking attualmente hardcoded per Consist 11 (8+ variabili `self.c11_*`)
  - `gate_config.json` ha già struttura corretta (`tracking_assignments`)
  - Codice daemon non usa questa struttura → refactor necessario
- **📝 Plan file aggiornato**: Phase 4D sezione completa
  - Architettura refactored: `self.consist_data` dict al posto di variabili hardcoded
  - Metodo generico `_update_gate_timing(consist_id, lead_pos, rear_pos)` per ANY consist
  - Loop dinamico su consist configurati (no più hardcode)
  - 7 implementation steps documentati
- **📋 CLAUDE.md aggiornato**: Roadmap chiarita
  - Task 4.1: Video Performance (frame queue) 🧪 IN TEST
  - Task 4.2: Generic Refactor 📋 BLOCKED BY 4.1
  - Phase 4B/4C: BLOCKED fino a completamento Task 4.1 e 4.2
- **⏭️ Next**: Test video lag fix (Task 4.1), poi procedere con refactor (Task 4.2)
- **Stima**: ~2-3 ore implementazione Task 4.2 dopo test OK

### 2025-01-01 (sera) - 🎯 **VIDEO LAG FIX CRITICO**
- **🐛 ROOT CAUSE IDENTIFICATA**: Dual VideoCapture RTSP contention
  - **Problema**: 1s+ video freeze quando entrambe le loco attraversano gate (Δt calculation)
  - **Causa**: `tracking_daemon.py` + `video_feed.py` entrambi con `cv2.VideoCapture(RTSP_URL)` sullo stesso stream
  - **Contesa**: Camera Tapo serve 2 client concorrenti → buffering → lag inaccettabile
- **✅ SOLUZIONE**: Frame Queue Sharing (asyncio.Queue)
  - **Architettura PRIMA**: Daemon (subprocess) + Video Feed → 2 VideoCapture separati ❌
  - **Architettura DOPO**: Daemon (asyncio.Task) → single VideoCapture → frame queue → Video Feed ✅
  - **Refactor TrackingManager**: Da subprocess a in-process asyncio.Task per memoria condivisa
  - **Daemon**: `asyncio.Queue(maxsize=2)` + `queue.put_nowait(frame.copy())` dopo YOLO
  - **Video Feed**: Rimosso VideoCapture, convertito async generator, legge da queue con timeout 2s
- **🚀 BENEFICI**:
  - ✅ Zero RTSP contention (single VideoCapture)
  - ✅ Frame letto una volta, usato due volte (efficiente)
  - ✅ Video feed legge da memory queue (non RTSP) → no lag
  - ✅ Backpressure: queue full → skip frame (no accumulo lag)
  - ✅ Startup immediato (no fork processo, accesso diretto frame_queue)
- **📊 SUBPROCESS vs ASYNCIO.TASK**:
  - **Subprocess**: memoria separata, IPC overhead 5-10ms/frame, isolamento crash
  - **Asyncio.Task**: memoria condivisa, zero overhead, GIL non problema (YOLO/OpenCV rilasciano GIL)
  - **Scelta**: asyncio.Task perfetto per frame sharing (requirement chiave)
- **📝 File modificati**:
  - `backend/tracking_daemon.py` - Aggiunto `asyncio.Queue(maxsize=2)`, push frame dopo YOLO
  - `backend/video_feed.py` - Rimosso VideoCapture, convertito async generator, legge da queue
  - `backend/main.py` - Wire `daemon.frame_queue` a video_feed endpoint, imports cv2/numpy
  - `backend/tracking_manager.py` - Da subprocess a asyncio.Task (in-process daemon)
- **🧪 TESTING**: Video NON freeze durante Δt calculation, solo 1 connessione RTSP attiva

### 2025-01-01 (pomeriggio) - 🔧 **STANDALONE SCRIPT ALIGNMENT**
- **🎯 Allineamento yolo track con daemon**: Centralized Δt calculation
  - **Problema**: Standalone aveva 4 calcoli inline Δt (race conditions, valori multipli per frame)
  - **Soluzione**: Refactor per matching esatto architettura daemon
  - **4 detection points**: salvano SOLO timestamp (no calcoli inline)
  - **Funzione centralizzata**: `calculate_delta_t_centralized()` - 2 check cross-gate (non 4!)
  - **Spam reduction**: throttling warnings (Δ>1s o 5s) con `last_ignored_delta_t1/2`
  - **max_delta_t threshold**: 15s caricato da gate_config.json (consistente daemon)
- **✅ BENEFICI**:
  - Elimina race conditions (niente più timestamp misti da lap diversi)
  - Un solo calcolo Δt per frame (non 4 conflittuali)
  - Parità esatta comportamento daemon/standalone
  - Filtraggio corretto valori impossibili (±19s ora ignorati)
- **📝 File modificati**:
  - `scripts/track_consist_yolo.py` - Centralized calculation + spam reduction (+86 righe, -64 inline)

### 2025-12-31 (tarda sera) - ⚙️ **THRESHOLD CENTRALIZATION**
- **🎯 Problema identificato**: Timing thresholds hardcoded in 4 posti diversi
  - `backend/tracking_daemon.py` - thresholds per calcolo status daemon
  - `scripts/track_consist_yolo.py` - thresholds per standalone script
  - `web/src/components/DeltaTStatsPanel.jsx` - thresholds per UI React
  - `backend/main.py` - thresholds per video overlay callback ← **BUG scoperto ultimo!**
- **✅ SOLUZIONE**: Single source of truth in `gate_config.json`
  - Aggiunta sezione `timing_thresholds: {normal: 1.0, warning: 2.0}` al config
  - Backend/daemon/script: caricano da file all'avvio
  - Frontend: riceve thresholds via WebSocket dal daemon
  - Video overlay: usa thresholds caricati nel backend startup
- **🔧 Refactor costanti**: Centralizzate defaults in `backend/main.py`
  - `DEFAULT_TIMING_THRESHOLDS` - fallback se gate_config.json mancante
  - `DEFAULT_CONTROLLER` - template controller vuoto
  - Pattern Path robusto: `Path(__file__).parent.parent / 'gate_config.json'`
- **🎯 Scoperta Tracking**: Funziona SEMPRE (indipendente da DCC/Virtual Mode)
  - DCC Mode (CV19 = 11): Δt monitoring attivo, speed compensation **disabilitato**
  - Virtual Mode (CV19 = 0): Δt monitoring attivo, speed compensation **abilitato**
  - CV19 toggle testato: valori tornano a 11 correttamente
- **📝 UI Decision**: Label "Speed compensation enabled/disabled"
  - Chiaro per utente: enabled = correzioni attive, disabled = solo monitoring
  - Icona: **`fa-gauge-high`** (tachimetro - tema ferroviario perfetto)
  - Da implementare in Phase 4B insieme a Virtual Mode auto-compensation
- **📝 File modificati**:
  - `backend/main.py` - Caricamento thresholds + constants refactor
  - `gate_config.json` - Aggiunta sezione `timing_thresholds`
  - Tutti i 4 componenti ora usano stesso config → zero duplicazione!

### 2025-12-30 (pomeriggio)
- **🎯 Milestone distance-based tracking**: Preservato lavoro completo
  - Commit: `810404b` - "milestone: distance-based tracking v1 (complete)"
  - C11: 217 samples (15.4% co-visibility)
  - Conclusione: funziona per C11, NON per C10
- **♻️ Refactor co-visibility tracking**: Pivot strategico da distance a timing
  - Rimosso distance calculation (-170 righe)
  - Aggiunto co-visibility counters (+54 righe)
  - Netto: -116 righe, codice più leggero
- **🎯 Strategia timing-based RIVISTA: Co-Presence Timing**
  - **C11**: 2 gate rettangolari condivisi (entrambe loco attraversano entrambi)
  - Δt = timestamp_loco7 - timestamp_loco8
  - Obiettivo: Δt ≈ 0 (passaggio quasi contemporaneo)
- **⚙️ Reference Loco Strategy** (CRITICO per Auto CV Adjust)
  - Reference: Loco 8 (ESU stabile) - MAI toccare
  - Adjust: Loco 7 (Hornby instabile) - sempre aggiustare

### 2025-12-30 (sera)
- **🎯 Phase 4: Gate Timing Detection COMPLETATA**: Cross-gate timing implementato per C11
  - Gate 1 posizione aggiornata: Y 293→213 (spostato 80px più in alto)
  - **Fix critico Δt**: "Fresh timestamps" logic - calcola solo con timestamp post-ultimo-Δt
  - Session summary al quit: durata, frames, crossing count, ultimo Δt
  - Log immediate commentati (solo periodic summary + 🚪 crossing logs attivi)
- **🎨 Fix colori OpenCV**: Risolti problemi leggibilità
  - **Regola**: cv2.putText() NON supporta Unicode/emoji - solo ASCII
  - Loco 8 marker: blu→rosso brillante (0,0,255 BGR)
  - Δt waiting text: grigio→bianco per leggibilità
- **📦 Gate Config JSON Integration COMPLETATA**: Sistema data-driven completo
  - Rimossi GATE_1/GATE_2 hardcoded, sostituiti con `self.gates[1]` e `self.gates[2]`
  - Interactive editing: drag & drop, resize 10px, rotation, save with S
  - Fix pause mode: UI sempre attiva (P, M, C funzionano)
  - Fix gate selection: click→edit existing gates
  - Save warnings: no auto-save al quit (solo log console)
- **✅ Decisione Strategica: 2 gate obbligatori per OGNI consist**
  - Approccio standardizzato (Opzione A): co-presence timing + cross-validation
  - C11: già implementato con 2 gate (G1, G2)
  - C10: userà stesso approccio (gate_ids: [3, 4] da configurare)
  - Vantaggi: check frequente, robusto, codice uniforme

### 2025-01-02
- **🖥️ GPU Deployment Guide COMPLETATA**: Documentazione completa Windows deployment
  - Setup SSH passwordless su PC Windows (OpenSSH Server)
  - Configurazione per utenti amministratori (`C:\ProgramData\ssh\administrators_authorized_keys`)
  - Network setup: IP locale + Tailscale Serve
  - Python + CUDA Toolkit installation guide
  - PowerShell functions: `z21-backend`, `z21-deploy`
  - Git branch strategy: develop (Mac) vs main (PC production)
- **✅ Production Mode Backend**: Conditional frontend serving implementato
  - `backend/main.py`: StaticFiles mount se `web/dist/` esiste
  - Development mode (Mac): Vite HMR porta 5173, dist/ NON esiste
  - Production mode (PC): `npm run build` genera dist/, FastAPI serve tutto porta 8000
  - Detection automatico modalità con console output
  - Route `/` riservata per frontend, API su `/api/status`
- **🔑 SSH Setup PC Windows COMPLETATO** (session live):
  - OpenSSH Server installato via Settings GUI
  - Servizio configurato automatic startup
  - SSH passwordless funzionante: Mac → PC senza password
  - Fix permessi `administrators_authorized_keys` per utenti admin
  - Test connessione: ✅ `ssh riccardo@192.168.1.3` senza password
- **📄 Guida accessibile via Tailscale**:
  - File copiato in `web/public/GPU_DEPLOYMENT.md`
  - HTML wrapper con markdown rendering: `GPU_DEPLOYMENT.html`
  - Accesso: `https://mbp16diriccardo.tail9350d7.ts.net/GPU_DEPLOYMENT.html`
- **🎯 Status GPU Deployment**: Step 1 (SSH) completato, resto pianificato
  - ✅ Step 1: SSH passwordless - COMPLETATO
  - ⏳ Step 2: Network/Tailscale (opzionale, IP locale già funziona)
  - ⏳ Step 3: Python + CUDA installation
  - ⏳ Step 4: Clone repository + dependencies
  - ⏳ Step 5: Production deployment con `z21-deploy`
- **♻️ REFACTOR CONFIG NAMING**: `gate_config.json` → `config.json`
  - Nome più generico (contiene gates, FPS, thresholds, debug, reference locos, etc.)
  - **Sostituiti** in tutto il progetto:
    - `GATE_CONFIG_PATH` → `CONFIG_PATH`
    - `load_gate_config()` → `load_config()`
    - `save_gate_config()` → `save_config()`
    - Variabile `gate_config` → `config`
  - **Files modificati**: 5 Python (backend + scripts) + 1 rename (88% similarity)
  - Commit: `28835b0` - "refactor: rename gate_config.json → config.json + debug mode"
- **🔇 DEBUG Mode IMPLEMENTATO**: Console logging intelligente
  - Flag `debug.enabled` in `config.json` (default: false)
  - **SEMPRE visibili** (debug=false): startup, gate crossing (🚦🚪), warnings (⚠️), mode changes (🔄⏸️)
  - **Soppressi** (debug=false): YOLO pause/resume verbose (🔇🔊)
  - **Files modificati**: `backend/tracking_daemon.py` + `config.json`
  - Goal: log puliti per production, verbose solo se necessario

### 2025-01-03
- **♻️ CONFIG.JSON REFACTOR COMPLETO**: Riorganizzazione struttura per maggiore chiarezza
  - **Problema identificato**: Configurazione frammentata e disorganizzata
    - Gates in cima (meno importante)
    - `tracking_assignments` conteneva consists ma `reference_locos` separato
    - Debug in fondo (dovrebbe essere prioritario)
    - Mix di `_comment` e `notes` (inconsistente)
  - **Nuova struttura gerarchica**:
    ```json
    {
      "debug": { ... },           // TOP: priorità massima
      "consists": {               // Consolidato (ex tracking_assignments + reference_locos)
        "10": {
          "name": "...",
          "lead_address": 1,
          "rear_address": 5,
          "gate_ids": [3, 4],
          "virtual_mode": true,
          "auto_compensation_enabled": true,
          "reference": {          // Integrato dentro ogni consist
            "loco": 5,
            "adjust": 1,
            "notes": "..."
          },
          "notes": "..."
        }
      },
      "gates": [ ... ],           // Infrastructure
      "tracking": {               // Grouped settings
        "fps": { ... },
        "timing_thresholds": { ... }
      }
    }
    ```
  - **Path changes** (tutti i file aggiornati):
    - `config['tracking_assignments']` → `config['consists']`
    - `config['reference_locos'][id]` → `config['consists'][id]['reference']`
    - `config['timing_thresholds']` → `config['tracking']['timing_thresholds']`
    - `config['tracking_fps']` → `config['tracking']['fps']`
  - **Files modificati** (7 totali):
    - `config.json` - struttura riorganizzata
    - `backend/main.py` - tutti gli endpoint API aggiornati
    - `backend/roster_loader.py` - load_consists_from_config()
    - `backend/z21_manager.py` - _load_persisted_state() + _save_persisted_state()
    - `backend/tracking_daemon.py` - config loading + reference_locos extraction
    - `backend/video_feed.py` - FPS loading
    - `scripts/track_consist_yolo.py` - standalone script
  - **Vantaggi**:
    - ✅ Ordine logico: debug → consists → gates → tracking
    - ✅ Consolidamento: reference dentro ogni consist (no più frammentazione)
    - ✅ Semantic grouping: fps + timing_thresholds sotto "tracking"
    - ✅ Naming consistente: solo "notes" (eliminato `_comment`)
    - ✅ Zero backward compatibility code (config.json in git, synced to PC)
  - **Decisione**: NO backward compatibility (config su git e sincronizzato su PC)

### 2025-12-30 (mattina)
- **🚂 YOLO Training v3 completato**: Model custom per 4 locomotive
  - Dataset: 137 immagini, training 4 minuti Colab GPU
  - mAP50 = 80.7% accuracy ✅
  - Model deployed: `BiancAlice_v3.pt`
  - Classi: 1_Gr675_017, 5_D645_014, 7_E656_239, 8_E444_056
- **⚠️ CRITICAL**: DCC address (CV1) come prefisso classe
  - MAI cambiare CV1 dopo training YOLO (rompe tutto)
- **📹 YOLO Workflow completo**: Pipeline end-to-end implementata
- **🎯 YOLO Tracking Test Completato**: Tutte e 4 locomotive detectate ✅
  - Confidence scores: 0.60-0.92
  - Distance measurement: 909.7px average (30 samples)
- **📐 Decisione Calibrazione**: Usare pixel direttamente (no cm conversion)
  - Camera grandangolo con distorsione fish-eye
  - Pixel/cm varia con distanza
- **✅ SOLUZIONE: Homography Perspective Correction**
  - Frame corretto: 600x1200px
  - Scala costante: 6 px/cm ovunque
  - Test completato: correzione verificata

### 2025-12-29 (sera)
- **✅ Phase 2: CV Operations Mode - COMPLETATA**
  - CV WRITE implementato e testato ✅
  - CV READ implementato (funziona solo ESU) ✅
- **🚀 Decisione: Adottare YOLO Object Detection**
  - Motion detection puro non sufficiente
  - YOLO training processo completo pianificato

### 2025-12-29 (mattina)
- **🎛️ Scalable UI (Phase 1)**: Controller dinamici implementati
  - Pulsante [+] aggiungi controller
  - Controller rimovibili, supporto N pannelli
- **🔄 Multi-Device Sync via WebSocket**: Sincronizzazione real-time
- **🐛 Fix WebSocket race condition** (CRITICO)
  - Soluzione: 50ms delay tra broadcast
- **⚡ Performance optimizations**: Fix hover lag e scroll glitch

### 2025-12-28
- **🎨 Function button styling refinement**
- **🔴 Indicatori dot color-coded**
- **🐛 Safari Mac animation bug RISOLTO**
  - Root cause: rimozione shadow/animation da elementi transition-all

---

## Recent Changelog (2025-12-25 → 2025-12-27)

### 2025-12-27
- **🔧 Decoder sostituzione E444 056**: ESU LokPilot 5 DCC
- **📝 Cambio indirizzo E656 182**: Address 3 → 2

### 2025-12-26 (Santo Stefano)
- **🎯 Mobile overflow RISOLTO**: Dropdown fix definitivo
- **✅ Tailscale Serve confermato permanente**

### 2025-12-25 (Natale) 🎄
- **Z21 Health Monitoring implementato**
- **Header UI migliorato**: Icone Font Awesome
- **Tailscale HTTPS support**: Dashboard accessibile via Tailscale
- **Favicon aggiornato**: Icona treno

---

## Failed Experiments Archive

### Esperimenti Phase 3 (2025-12-29 sera) - SOSPESA

**Status**: ❌ **Phase 3 SOSPESA** - approccio motion detection puro non praticabile

#### Hardware Setup Testato
- **Camera**: Tapo IP camera (192.168.1.4:554/stream2 - 720P)
- **Connessione**: RTSP stream via OpenCV (cv2.VideoCapture)
- **Snapshot test**: ✅ Funzionante, layout plastico visibile

#### Camera Setup e Prospettiva

**Posizione camera**: Lato corto del plastico (inquadratura laterale, NON top-down)

**Orientamento frame**:
- **BASSO del frame** (bottom, y alto) = VICINO alla camera (primo piano)
- **ALTO del frame** (top, y basso) = LONTANO dalla camera (sfondo, ~2 metri)

**⚠️ PROBLEMA CRITICO: Distorsione Prospettiva**

La distanza fisica costante sul plastico NON corrisponde a pixel costanti:
```
Frame Y=0 (top)    → Lontano dalla camera → 50cm físico = ~500px
          ↓
          ↓ 2 metri profondità
          ↓
Frame Y=720 (bottom) → Vicino alla camera → 50cm físico = ~800px
```

**Conseguenze**:
- **Misure in pixel NON affidabili** per distanza fisica senza correzione prospettiva
- Locomotive a diverse altezze del frame hanno scale px/cm diverse
- 909px baseline primo test vs 1007px secondo test potrebbero dipendere da profondità nel frame, NON da posizioni iniziali

**✅ SOLUZIONE IMPLEMENTATA: Homography Correction con OpenCV**

**Punti calibrazione misurati** (2025-12-30):
```python
# Source points (quadrilatero distorto nel frame originale 1280x720)
SRC_POINTS = np.float32([
    [7, 246],      # Top-left (P1-P2 da prima misura)
    [376, 31],     # Top-right
    [957, 37],     # Bottom-right (P3-P4 da seconda misura - più precisi)
    [257, 718]     # Bottom-left
])
```

**Frame corretto** (perspective transform):
- **Dimensioni**: 600x1200 px
- **Scala**: **6 px/cm costante ovunque** nel frame
- **Area visibile**: 1m x 2m (include plastico + binari sotto)
- **Proporzioni**: **1:2** (perfette!)

**Estensione**: I punti P3-P4 vengono estesi del 30% verso Y=720 per includere binari sotto il bordo plastico

**Test effettuato**: ✅ Correzione prospettica verificata come corretta
**Script**: `test_perspective_correction.py` - visualizza frame originale + frame corretto con griglia

**Residual distortion**: Camera Tapo ha curvatura di campo (fish-eye) - homography NON corregge distorsione radiale lente (solo prospettiva). Errore residuo stimato: 5-10% (accettabile per drift monitoring).

**Status**: ✅ COMPLETATO - pronto per integrazione in track_consist_yolo.py

#### Approcci Sperimentati

**1. Motion Detection con Pattern Analysis** (`track_consist.py`)
- Background subtraction MOG2 + scoring multi-marker
- Analisi tetti (luminosità), pantografi rossi, pattern carrozze
- **Problema**: Troppo complesso, detection instabile
- **Risultato**: Funziona solo angolo basso-dx, resto tracciato inaffidabile

**2. Calcolo Vettore Direzione** (per tracciato ovale)
- Position tracking (5 frames) → calcolo delta_x, delta_y
- Analisi estremità bounding box in base a direzione movimento
- LEFT/RIGHT/UP/DOWN → locomotiva sul bordo corretto
- **Problema**: Aggiunto complessità senza miglioramenti
- **Risultato**: Detection peggiorata, troppa logica

**3. Ottimizzazioni Background Subtractor**
- Provato `varThreshold=60` (meno sensibile)
- Provato `learningRate=0.001` (update lento)
- Provato kernel morphology `(11,11)` (pulizia aggressiva)
- **Problema**: Alcuni config causavano crash, nessun miglioramento significativo

**4. Versione Minimalista** (`track_consist_v2.py`)
- Solo motion detection puro: MOG2 + area filtering
- Prende 2 oggetti più grandi → pallini sui centri
- `varThreshold=60` per ridurre rumore
- **Risultato**: Stabile ma non migliore della v1, serve a poco

#### Problemi Identificati

1. **Motion detection troppo sensibile**
   - Troppo "bianco" nella maschera debug (rumore di fondo)
   - Flash periodici quando MOG2 aggiorna background model
   - Rileva case, edifici, elementi statici del plastico

2. **Pallino in coda invece che su locomotiva**
   - Bounding box include loco + 3 carrozze
   - Analizzando solo "primi 20%" funziona solo se treno va verso sinistra
   - Su tracciato ovale: direzioni multiple (LEFT/RIGHT/UP/DOWN)
   - Calcolo direzione non ha risolto il problema

3. **Tracking instabile**
   - Funziona discretamente solo nell'angolo basso-dx (più vicino)
   - Resto del tracciato: detection persa o errata
   - Distance measurement inaffidabile (centro-a-centro vs loco-a-loco)

#### Conclusioni

**Il solo motion detection NON è sufficiente** per tracking affidabile su tracciato ovale completo.

**Motivi**:
- Background subtraction troppo sensibile a illuminazione, ombre, elementi statici
- Impossible distinguere lead da rear senza features visive robuste
- Locomotive + carrozze = bounding box lungo, centro ≠ posizione locomotiva
- Tracciato ovale = direzioni multiple, pattern analysis complesso

**Alternative necessarie**:
- ✅ **Object detection ML** (YOLO/MobileNet) - training custom su locomotive specifiche
- ✅ **Migliore illuminazione** - LED strip dedicata sopra plastico
- ✅ **Markers fisici** - QR codes o ArUco markers sulle locomotive
- ❌ **Solo motion detection** - dimostrato insufficiente

**Raccomandazione**: Sospendere Phase 3 fino a disponibilità di:
1. Webcam USB di qualità (Logitech C920/C922)
2. Setup illuminazione dedicata
3. Tempo per training model YOLO custom

**Files creati**:
- `scripts/track_consist.py` - versione complessa (motion + scoring) - non funziona
- `scripts/track_consist_v2.py` - versione minimalista (solo motion) - non migliora
- `scripts/utils/view_camera.py` - viewer RTSP per test (funzionante)
- `scripts/utils/calibrate_colors.py` - tool HSV trackbar (creato ma non utile)
- `scripts/utils/pick_colors_from_image.py` - tool click-to-sample (creato ma non utile)

---

## Web Dashboard MVP Era (2025-12-24)

### 2025-12-24 (Vigilia di Natale)
- **🎄 Web Dashboard MVP completato**: Interfaccia web moderna per controllo locomotive
  - **Stack**: Vite 6.0 + React 18.3 + Tailwind CSS v3.4 + FastAPI + WebSocket
  - **Timeline**: 1 giorno (pianificati 2-3) - più veloce del previsto
  - **Estetica**: "Control Room Noir" - design industriale dark con accent amber
- **Frontend implementato** (`/web/`):
  - Vite build tool con Hot Module Replacement
  - React componenti: `App.jsx`, `ConsistController.jsx`
  - Custom hook `useWebSocket.js` per real-time communication
  - Tailwind CSS v3.4 con tema custom (fonts: Outfit, Manrope, JetBrains Mono)
  - Responsive design mobile-first (desktop/tablet/phone)
  - Touch-optimized controls (slider 48px thumb)
  - Grain texture overlay e signal glow effects
- **Backend implementato** (`/backend/`):
  - FastAPI server con WebSocket endpoint (`/ws`)
  - `z21_manager.py`: wrapper Z21 con gestione stato consist
  - `roster_loader.py`: parser JMRI XML per roster e consist
  - Auto-reload backend con Uvicorn
  - Initial state sync da Z21 (funzioni, velocità, direzione)
  - Broadcast updates a tutti i client connessi
- **Features funzionanti**:
  - ✅ Controllo velocità slider 0-126
  - ✅ Direzione toggle (forward/reverse)
  - ✅ Funzioni F0-F28 con indicatori stato ON/OFF
  - ✅ Emergency stop (power on/off con toggle)
  - ✅ Dual consist layout (consist 10 e 11)
  - ✅ Track visualization con posizione treno
  - ✅ Connection status indicator
  - ✅ Multi-device sync real-time via WebSocket
- **Fix critici risolti**:
  1. **Tailwind CSS v4 incompatibilità**: Downgrade a v3.4.0
  2. **Function state sync**: Frontend ora usa `functionStates` da backend
  3. **Function routing**: F0→lead+rear, F1-F28→lead (implementato in z21_manager)
  4. **Initial state loading**: Parsing corretto stati Z21 reali
- **Alias bash creati**: `z21-backend`, `z21-frontend`, `z21-dev`
  - `z21-dev` lancia backend e frontend in terminali separati automaticamente
- **Integrazione JMRI**: Lettura roster XML, indipendente (JMRI non richiesto running)
- **URL**: http://localhost:5173 (locale), http://192.168.1.xxx:5173 (rete)

### 2025-12-19 (sera)
- **Polling periodico implementato (TODO 3)**: Controller ora sincronizzato con Z21
  - Polling ogni 500ms in background (non blocca input tastiera)
  - **Track power**: sincronizzato sempre, rileva power on/off da Z21 fisico o JMRI
  - **Funzioni F0-F28**: sincronizzate con cooldown 2s dopo ultimo comando
  - **Velocità/direzione**: sincronizzazione disabilitata (conflitto con JMRI Throttle)
  - Suoni feedback automatici: Frog.aiff per power OFF, Funk.aiff per power ON
  - Sistema cooldown per evitare race condition tra comandi locali e polling
- **Parser Z21 status corretto**: `get_status()` in z21.py
- **Fix funzioni momentanee**: Ripristinata logica temporizzata
- **Repository Git creato**: https://github.com/rizal72/z21-Terminal (privato)
- **Piano Web Dashboard**: Decisione e pianificazione

### 2025-12-19 (mattina)
- **Vista unificata slider + funzioni**: Interfaccia completamente ridisegnata
- **Controllo funzioni con Shift+lettere**: Implementato hotkey system (Shift+A-Z)
- **Traduzione completa in inglese**: Coerenza con README
- **Test lettura CV via Z21 (fallito)**: Z21 White non supporta POM Read

### 2025-12-18 (sera)
- **Rinomina progetto**: **z21-Terminal**
- **Refocus progetto**: Da tool speed matching a Z21 Controller

### 2025-12-18 (mattina)
- **Lettura stato funzioni**: Implementata sincronizzazione automatica
- **Fix percentuali velocità**: Cambiato `int()` in `round()`
- **Aggiornamenti hardware roster**: Loco 6 decoder sostituito

### 2025-12-17 (notte)
- **Menu funzioni F0-F28**: Implementato completamente
- **z21_test.py → z21.py**: Rinominato in libreria completa
- **UI improvements**: Status bar fisso in alto con ANSI escape codes

### 2025-12-17 (sera)
- **Controller z21_controller.py**: Implementato controller interattivo completo
- **Emergency stop**: Toggle con backslash
- **Scoperta importante**: JMRI e Z21 direct possono coesistere

### 2025-12-17 (mattina)
- **Protocollo Z21 LAN**: Implementato e testato con successo
- **Script `z21_test.py`**: Libreria Z21 protocol completa
- **API JMRI**: Testati endpoint REST

### 2025-12-16
- Setup iniziale progetto
- Attivato JMRI Web Server
- Testata connessione API JSON
- Lette CV da file roster XML
- Documentato setup completo plastico e roster
- Creato script Python `read_cv_from_roster.py` e `read_consists.py`

---

## Changelog 2025-01-14 (Analytics UX & Session Boundaries)

### 2025-01-14 - 🎉 **SESSION BOUNDARY LINE BREAKS - RISOLTO!**

**Status**: ✅ **FEATURE COMPLETATA** dopo 10+ tentativi falliti

Soluzione finale: Segment-based rendering con dataKey separati (NON array separati!), singolo array condiviso con dataKey diversi per ogni segmento.

**Commits**: `250b863`, `863aa15`, `865387d`, `ed4cccb`, `35ea274` (soluzione finale)

---

### 2025-01-14 - 📊 **BOX-SELECT ZOOM & Y-AXIS IMPROVEMENTS**

**Status**: ✅ **FEATURE COMPLETATA** - Interactive zoom, rotated labels, sticky legend

- Box-select zoom in Overview mode, double-click reset
- Y-axis fixes (ReferenceLine visibility, decimali 2 cifre, padding 5%, rotation 180°)
- Sticky legend in Current mode
- Session breaks toggle checkbox

**Total commits**: 15

---

## Changelog 2025-01-13 (Analytics Suite Implementation)

### 2025-01-13 - 🏷️ **ANALYTICS WORKING TAG** (Rollback + Fix)

Context: Analytics panel was already working at commit `acfed1b` (2025-01-12 22:57).

**Issues Fixed**:
- Chart disappeared after session filtering → reverted to `acfed1b`
- Gate crossings stats showed 0 → fixed SQL query (`event_type = 'gate_crossing'` → `'delta_t'`)
- "Detail" naming unclear → renamed to "Current"

**Tag**: `analytics-working` (commit `418fc03`)

---

### 2025-01-13 - 🎯 **DETERMINISTIC SESSION BOUNDARIES**

Implemented `navigator.sendBeacon('/api/close-session')` on page unload.
**Result**: Every page refresh = NEW session (100% deterministic, no timing dependencies).

**Commit**: `f12cee5`

---

### 2025-01-13 - 📈 **ANALYTICS SUITE COMPLETATO - YOLO PERFORMANCE MONITORING**

**Status**: ✅ **MILESTONE COMPLETATO** (commit `5dd4ed3`) - 3/3 charts implementati

**Third Chart**: YOLO Performance Monitoring (FPS + Confidence)
- DCC address tracking (1, 5, 7, 8) NOT YOLO class
- 5-second logging (~720 events/hour vs 3600)
- Horizontal scroll + auto-scroll to right

**Production Results** (PC Windows + RTX 2060):
- FPS: 50-130 FPS (2-4x faster than 30 FPS target!)
- Confidence: Loco 1,7,8 = 60-75%, Loco 5 = 35%

**Commits**: `4bce745`, `4457541`, `01df6af`, `d2630a3`, `5dd4ed3`

---

### 2025-01-13 - 📊 **TAIL VS SAMPLING STRATEGY + CONDITIONAL DEBUG LOGGING**

**Solution: Tail vs Sampling** (mutually exclusive):
- **Current View** (`?tail=1000`): Last N events at full resolution (no sampling)
- **Overview View** (`?maxPoints=500`): Uniform sampling across entire history

**Conditional Debug Logging**: Log ONLY when `config.json` → `"debug": {"enabled": true}` AND reduction significant (>10% OR >100 events)

**Commit**: `2480eaf`

---

### 2025-01-13 - 📊 **ANALYTICS SESSION-FILTERED CARDS COMPLETATO**

**Status**: ✅ **MILESTONE VERIFIED** (commit `33345ba`) - Tested with real locomotive movement

- Current view: Cards filtered per session (Duration, Gate Crossings, Critical Events)
- Overview view: Historical data totals
- Consist filters: All/C10/C11 functional

**Tag**: `analytics-working` (verified at `33345ba`)

---

### 2025-01-13 - 🚂 **LOCOMOTIVE OPERATING TIME TRACKING**

**Status**: ✅ **IMPLEMENTED** - Hybrid approach (Events + Stats tables)

- Database Schema: `locomotive_stats` table
- Backend Tracking: `loco_start_times` dictionary (address → timestamp)
- Migration: One-time backfill from existing sessions (46 events)
- Frontend Chart: Bar chart, ONLY in Overview

**Commits**: `b7c4114`, `2e6bea9`, `a061d49`, `ff40c8b`, `4641995`, `db60bf6`, `6133ca4`, `d791f20`, `b547636`, `5642b8c`, `c79c83c`, `84c048d`

---

### 2025-01-13 - 🗂️ **DATA DIRECTORY REFACTORING**

**Change**: Moved `data/` → `backend/data/`
- Before: `Path(__file__).parent.parent / "data" / "analytics.db"` (2 levels up)
- After: `Path(__file__).parent / "data" / "analytics.db"` (1 level up)

**Commit**: `aa1d172`

---

### 2025-01-13 - ♻️ **ANALYTICSPANEL REFACTORING**

**Motivation**: Eliminate code duplication (~80 lines, 4+ duplications each)

**Constants & Helpers Extracted**: TOOLTIP_STYLES, CHART_AXIS_STYLES, filterEventsBySession, getAddressFilter, getConsistColor

**Result**: ~50 lines reduction, build size 658.74 kB → 658.26 kB

**Commit**: `e610f70`

---

### 2025-01-13 - 🔧 **Z21 HEALTH CHECK GRACE PERIOD**

**Solution**: Require 2 consecutive failures before marking offline (eliminates false positives)

**Detection time**: 10s (2 × 5s checks)

**Commit**: `5428a81`

---

### 2025-01-13 - ♻️ **ANALYTICS REFACTORING & CLEANUP**

**Revert All Idle/Break Line Experiments** (commit `a406909`):
- Double-null strategy failed when consists move independently
- Hard reset to commit `3512f8d` (88 lines deleted)

---

### 2025-01-13 - 🔧 **ANALYTICS UX IMPROVEMENTS**

Multiple improvements (commits `1e44b33`, `a7d88c7`, `e3eaa18`, `d1642d4`, `945b9e8`, `16b1f1f`, `10fee70`):
- Operating Time Chart Filtering (All/C10/C11 consistent)
- Sticky Header Filters (always visible)
- Chart Remount Fix (`key={consistFilter}`)
- Click Outside to Close modal
- X-Axis Improvements for Overview (event numbers instead of timestamps)
- Consist Names Shortened (C10 Interno, C11 Esterno)
- Min Threshold Line Styling (white)

---

### 2025-01-13 - 🚀 **LTTB DOWNSAMPLING WITH CRITICAL EVENT PRESERVATION**

**Motivation**: Analytics reaching >500 events → uniform sampling loses important peaks/valleys

**Implementation**:
- `lttb_downsample()` - Generic LTTB algorithm (~40 lines pure Python)
- `smart_downsample_delta_t()` - ALWAYS includes ALL critical events (|Δt| ≥ 1.5s)

**Performance**: <20ms with <1000 events, ~50-100ms with 5000 events

**Commit**: `683d263`, **Tag**: `analytics-working`

---

### 2025-01-13 - 📚 **README UPDATE & ANALYTICS DOCUMENTATION**

**README.md updated** (commit `207d411`):
- Added Analytics Dashboard section
- Updated Project Structure (`backend/data/`)
- Fixed GPU model (GTX 1050 Ti → RTX 2060)
- Added TensorRT acceleration details

---

### 2025-01-13 - ♻️ **ANALYTICSPANEL REFACTORING PHASE 2**

**Completato DRY cleanup** (commit `28882ef`):
- Card 2/3 color logic via helper
- All chart axes use shared constant
- Code eliminated: ~15 lines (Phase 1+2 total: ~65 lines)

---

### 2025-01-13 - 🔄 **DYNAMIC CHART LINE BREAKS (CONFIG-DRIVEN)**

**Backend** (`/api/config/tracking`): Returns `idle_timeout_seconds` from `config.json`
**Frontend**: `breakLineOnIdle()` helper inserts null points when gap > idle_timeout

**Commit**: `c4c536d`

---

### 2025-01-13 - 🐛 **IDLE LINE BREAKS FIX (ALL FILTER)**

**Solution: Double-Null Strategy**:
- Apply `breakLineOnIdle()` separately to C10 and C11, merge chronologically
- Creates double-null idle points (both consists null)
- `connectNulls={true}` connects single nulls (other consist) but NOT double nulls (idle)

**Commit**: `a9ab5d6`

---

### 2025-01-13 - 🎛️ **CONFIG-DRIVEN REFACTORING (DYNAMIC CONSIST SUPPORT)**

**Motivation**: Analytics hardcoded consist IDs 10/11 → adding/renaming required code changes

**Solution**: Dynamic consist support from `config.json`
- Removed hardcoded constants (CONSIST_ADDRESSES, CONSIST_COLORS)
- Added dynamic color palettes (cyclic, up to 6 consists)
- Helper functions (getConsistStrokeColor, getConsistColorClass, getConsistBgClass, getAddressFilter)

**Result**: Support for N consists (2, 3, 5, etc.), zero code changes needed

**Commits**: `658d636`, `3512f8d` (fix missing config load)

---

### 2025-01-13 - 🚧 **IDLE VISUALIZATION IMPROVEMENT (IN PROGRESS)**

**Planned Solution**: Dashed lines for idle periods (dual Line components per consist - active solid, idle dashed)

**Status**: Ready to implement (user approved)


---

## Changelog Archived: 2025-01-13 → 2025-01-15

**Note**: The entries below were moved from CLAUDE.md on 2025-01-15 to keep CLAUDE.md < 40KB

---

### 2025-01-14 - 🔍 **ROOT CAUSE ANALYSIS: Loco 7 Erratic Behavior**

**Investigation**: Analytics historical trend analysis su Consist 11 (30 sessioni, 2026-01-12 → 2026-01-14)

**Findings**:
- Loco 7 (Hornby TXS) comportamento **cronicamente instabile** fin dalla prima sessione tracked
- Average dT varia da -0.06s (BALANCED) a -1.23s (CRITICAL) senza pattern prevedibile
- Worst session: 2026-01-14 avg -1.23s, solo 51.6% SYNCED, range -3.52s to +1.09s (6.6s variabilità!)
- **NON esiste "cambio improvviso"**: problema esisteva già quando tracking iniziato

**Root Cause Identified**: 🎯 **Micro SMD capacitor (~0.5mm) staccato dalla PCB di loco 7**
- **Location**: Lato periferico PCB (opposto decoder), vicino bordo corto (coda/testa loco)
- **Function**: Smoothing/filtering capacitor per circuito alimentazione motore
- **Impact**: Senza filtro → alimentazione instabile, rumore elettrico, spikes non smorzati
- **Why not fixed**: Condensatore troppo piccolo per saldatura manuale, decoder sound troppo costoso per rischiare riparazione

**Workaround**: ✅ **Virtual Mode attivo e funzionante**
- Sistema compensa automaticamente comportamento erratico in real-time
- Analytics tracking valida efficacia compensazione
- Performance accettabile per operazioni quotidiane

**Documentation**: Dettagli completi → `docs/CONSIST_ROSTER.md` (sezione loco 7 - Known Hardware Issue)

**Tools Created**:
- `scripts/utils/analytics_report.py` - Session analysis con dT statistics
- `scripts/utils/c11_trend_analysis.py` - Historical trend C11 (30 sessions max)

**Key Insight**: Questo problema hardware è stata la motivazione principale per sviluppare sistema YOLO tracking + Virtual Mode con compensazione automatica velocità.

---

### 2025-01-14 - 📊 **REPORTS TAB MVP COMPLETATO**

**Status**: ✅ **v1.2 MILESTONE** - 3rd tab Analytics Dashboard implemented

**Obiettivo**: Sostituire CLI scripts (`analytics_report.py`, `c11_trend_analysis.py`) con web UI accessibile da tablet/smartphone per analisi session-by-session.

**Features Implemented**:

1. **Session History Table**:
   - Ultime 30 sessioni validate con colonne dinamiche (C10/C11 Avg Δt, Synced%)
   - Color-coded avg Δt: verde (<1.0s), ambra (1.0-1.5s), rosso (≥1.5s)
   - Consist filter: "All" mostra tutte sessioni con N/A per consist non girato, "C10"/"C11" filtra solo sessioni rilevanti
   - Clickable rows → Session Detail Modal

2. **Historical Trend Chart**:
   - LineChart con avg Δt over time (X-axis: date, Y-axis: seconds)
   - Reference lines: 0 (green), ±1.0 (amber), ±1.5 (red)
   - Dynamic lines per consist (color-coded)
   - Clickable points → Session Detail Modal
   - Custom tooltip mostra tutti consist non-null per data

3. **Session Detail Modal**:
   - Session metadata: ID, Date, Duration, Total Events
   - Per-consist breakdown: Total crossings, Avg Δt, Range, Trend, Status distribution (SYNCED/WARNING/CRITICAL)
   - Interpretation guide con bullet points
   - z-index 60 (sopra main Analytics modal)

**Backend API**:
- Endpoint: `GET /api/analytics/reports?limit=30&consist_filter=<id>`
- Helper: `format_duration_hms()` (HH:MM:SS formatting)
- Pre-aggregates statistics per session/consist (avg, min, max, status counts, synced%, trend)
- Returns consist IDs as strings in JSON (`"10"`, `"11"`)

**Critical Fixes**:
1. Fragment import (React.Fragment undefined)
2. Rules of Hooks (useMemo inside IIFE)
3. Exclude Overview charts da Reports tab
4. Helper functions null safety (`consistConfig || {}`)
5. TrackingConfig load race condition (spinner durante load)
6. Object.keys null safety (7 occorrenze con `|| {}`)
7. **Consist ID type mismatch**: Backend strings vs frontend numbers → `String(cid)` conversion necessaria
8. Session filtering by consist (`filteredReportsSessions` useMemo)
9. Custom tooltip per mostrare tutti consist per data

**Known Limitation**: ✅ RISOLTO
- ~~Multiple sessions same date: Custom tooltip mostra correttamente tutti i consist per data~~

**Documentation**:
- `docs/REPORTS_TAB.md` - Documentazione completa implementazione (architecture, components, API, fixes, testing, future enhancements)

**Testing**: ✅ Manual testing completato su PC Windows + GPU (production environment)

**Commits**: `0f8c6f8` → `f55bc8f` (13 commits totali, 6 fix critici per crash/rendering)

**Next Steps** (future releases):
- v1.3: Speed setting tracking (HIGH PRIORITY)
- v1.3+: Sortable columns, pagination, CSV export, date range filter

---

### 2025-01-15 - 🎉 **MILESTONE 1.2 COMPLETATA**

**Status**: ✅ **v1.2 RELEASED** - Analytics UX improvements & data quality fixes

**Features Implemented**:

1. **Delta T Sign Display** (commit `7f63e57`):
   - Added `formatDeltaT()` helper: always show "+" prefix for positive values
   - Applied to ALL 6 display locations: Y-axis, tooltips, Reports table, Historical chart, Session detail modal
   - Semantic clarity: "+" explicitly shows which loco is faster

2. **Locomotive Operating Time Data Fix**:
   - **Problem**: 22 anomalous events (10-14 hour durations) from bad migration showing 22-73 hours instead of minutes
   - **Solution**: Created `fix_loco_events.py` script to delete anomalous events (duration > 3600s)
   - **Result**: Correct data: Loco 1/5: 9.5 min, Loco 7/8: 249 min (4.15 hours over 11 movements)

3. **Operating Time Format** (commits `7cd7efb`, `c240196`):
   - Added `formatOperatingTime()` helper: "Xh Ym" format (e.g., "4h 9m")
   - Changed Y-axis from decimal hours (0.16h) to integer minutes
   - Tooltip shows human-readable "Xh Ym" format
   - Chart title: "Total Operating Hours" → "Total Operating Time"

4. **FPS Average Badge** (commits `344a135`, `fea3714`, `49d3ace`, `a07772f`):
   - Added top-right badge on Inference FPS chart: "FPS avg: XX.X"
   - Visible in both Current and Overview modes
   - **Idle filtering**: Excludes FPS ≤ 10 to measure real tracking performance (not idle 1 FPS)
   - **Session-specific logic**: Current mode shows session average or N/A if not loaded, Overview shows global average

5. **Duplicate Right Y-Axis for FPS Chart** (commits `15a9b58`, `5f26ac9`, `dc4c754`):
   - Added conditional right Y-axis in Current mode (always visible when scrolled right)
   - Matches Δt chart implementation: `yAxisId="left"/"right"`, `allowDataOverflow={true}`
   - Consistent UX across both time-series charts

**Failed Experiments** (7 commits reverted):
- **Date display on X-axis** (commits `f3c40da` → `8037997`, all reverted to `a07772f`):
  - Attempted to show date (DD-MM in amber) at start of each day, followed by times
  - 7 different strategies tried, all failed due to Recharts unpredictable tick sampling
  - Cost: 76 lines of code written and deleted, ~1 hour development time
  - Feature abandoned per user request

**Key Insights**:
- ✅ **Read complete implementation before modifying**: Avoid incremental commits by studying existing code patterns first
- ⚠️ **Files becoming enormous**: `AnalyticsPanel.jsx` 1600+ lines, `main.py` needs refactoring (planned for future milestone)
- 🎯 **Data quality matters**: Bad migration data corrupted statistics, manual cleanup required

**Commits**: `7f63e57` (delta T sign) → `dc4c754` (FPS right Y-axis) - 8 feature commits + 7 reverted experiments

**Next Steps** (v1.3):
- **HIGH PRIORITY**: Speed setting tracking in Analytics
- Refactor `main.py` and `AnalyticsPanel.jsx` (componentization)

---
### 2026-01-15 - 🎉 **SPEED TABLE AUTO-TUNING: Phase 1 MVP COMPLETATA**

**Status**: ✅ **PHASE 1 COMPLETE** - Speed correlation analytics live in production

**Implementation Summary**:
- **Time**: ~3 hours (stima: 8-12h) - ottimizzato grazie a modular architecture
- **Commits**: 5 commits (ba8d9e4 → f8669c7)
- **Deploy**: PC Windows production via `z21-deploy-dev`
- **Testing**: ✅ Live con dati reali (C10: 52 eventi, C11: 300 eventi a speed 70)

**Backend** (3 files modified):
- ✅ `ws_control.py`: Speed event logging in `handle_set_speed()` (logga solo se speed cambia)
- ✅ `analytics_db.py`: `get_speed_correlation()` con "Next N Events" strategy (default N=10)
- ✅ `routers/analytics.py`: Endpoint `/api/analytics/speed-correlation?consist_id=X`

**Frontend** (4 files: 3 modified, 1 new):
- ✅ `analyticsConstants.js`: `SPEED_STATUS_COLORS` (no hardcoded thresholds!)
- ✅ `analyticsHelpers.js`: 3 helper functions (reference lines, bucket color, recommendations)
- ✅ `SpeedCorrelationChart.jsx`: NEW scatter chart component con error bars + reference lines
- ✅ `AnalyticsPanel.jsx`: 4th tab "Speed Tuning" integrato (187 lines added)

**Features Implemented**:
- ✅ Speed vs Δt scatter chart con error bars (std dev)
- ✅ Dynamic reference lines da config thresholds (SYNCED/WARNING/ACTION)
- ✅ Color-coded points by dominant status (green/amber/red)
- ✅ Summary cards (speed changes, samples, buckets)
- ✅ CV tuning recommendations (text only - Phase 1, manual JMRI adjustment)
- ✅ Consist filter enforcement (must select C10 or C11, not "All")
- ✅ Auto-reload on consist filter change

**Database Migrations** (2 scripts, one-time execution):
1. **Migration 1** (`migrate_add_speed.py`): Aggiunto `speed: 70` a 352 eventi delta_t storici
   - Backup: `analytics.db.backup_20260115_151846.backup`
2. **Migration 2** (`add_historical_speed_events.py`): Creati 2 eventi `speed_setting` (0→70)
   - C10: 52 eventi delta_t utilizzabili
   - C11: 300 eventi delta_t utilizzabili
   - Backup: `analytics.db.backup_20260115_163137.backup`

**Production Results** (2026-01-15 16:30):
- **Consist 10**: Speed 70 → Mean Δt +1.07s (±0.60s) - 50% SYNCED, 30% CRITICAL
- **Consist 11**: Speed 70 → Mean Δt -0.80s (±1.15s) - 60% SYNCED, 30% CRITICAL
- **Status**: Entrambi sotto soglia action (1.5s) → "All speeds well synchronized!" ✅

**Critical Fixes Applied**:
- ✅ Exclude speed-tuning from Current/Overview charts rendering (efa54ba)
- ✅ Correct terminology: "Reference/Adjust loco" instead of "Lead/Rear" (f8669c7)
- ✅ Fix recommendation logic: Δt > 0 = adjust slower (not faster)

**Architecture Notes**:
- **No hardcoded thresholds**: Tutti i threshold da `config.json` (dynamic)
- **Modular design**: Chart component riutilizzabile, helpers DRY
- **"Next N Events" strategy**: Adattivo a track length (C10: 55s vs C11: 15s lap)
- **Phase 1 scope**: TEXT recommendations only (manual CV adjustment via JMRI)

**Next: Phase 2 Enhancement** (discussed, not implemented):
- Read CV speed table values from JMRI roster (CV67-94)
- JMRI-style step numbering (1-28 instead of CV67-94)
- Specific recommendations: "Step 16 (CV82): 128 → 135 (+7)" instead of generic text
- Before/after preview with exact CV values

**References**:
- Design: `docs/SPEED_TABLE_TUNING.md`
- Plan: `~/.claude/plans/glimmering-sleeping-starfish.md`

---

### 2026-01-15 - 🐛 **SPEED TUNING: 8 Critical Bugs Fixed After Phase 1 Deployment**

**Status**: ✅ **ALL BUGS FIXED** - Speed Tuning fully functional, v1.4 tag created

**Context**: After Phase 1 MVP deployment, extensive testing revealed 8 critical bugs preventing Speed Tuning from working correctly. This debugging session (~6 hours) identified and fixed all issues.

**Critical Bugs Discovered and Fixed**:

1. **🔴 WebSocket Crash - Missing `await` Keyword** (MOST CRITICAL)
   - **Error**: speed_setting events logged to console but NEVER reached database (0 events in DB)
   - **Cause**: `analytics_logger.log_event()` is async but called without `await` in `ws_control.py:184`
   - **Evidence**: 17 delta_t events at speed 126 existed (daemon logging worked), but 0 speed_setting events
   - **Fix**: Added `await` before `analytics_logger.log_event()` call
   - **File**: `backend/websocket_handlers/ws_control.py:184`
   - **Commit**: `9f50436`

2. **🔴 analytics_logger Not Accessible from ws_control.py**
   - **Error**: `AttributeError: 'TrackingManager' object has no attribute 'analytics_logger'`
   - **Cause**: analytics_logger lives in tracking_daemon, not tracking_manager
   - **User symptom**: "le loco partono solo la prima volta e poi non è più possibile fermarle"
   - **Fix**: Added analytics_logger to dependencies.py global state pattern
     - tracking_daemon sets it on startup via `dependencies.set_analytics_logger()`
     - ws_control.py gets it via `dependencies.get_analytics_logger()`
   - **Files**: `backend/dependencies.py`, `backend/tracking_daemon.py`, `backend/websocket_handlers/ws_control.py`
   - **Commits**: `cdf5f9c`, `d4c8c60`

3. **🟡 Circular Import - dependencies.py**
   - **Error**: `ImportError: cannot import name 'TrackingManager' from partially initialized module`
   - **Cause**: Import chain: main.py → tracking_manager → tracking_daemon → dependencies → tracking_manager
   - **Fix**: Used `TYPE_CHECKING` pattern in dependencies.py to avoid runtime circular import
     ```python
     from typing import TYPE_CHECKING
     if TYPE_CHECKING:
         from z21_manager import Z21Manager
         from tracking_manager import TrackingManager
     ```
   - **File**: `backend/dependencies.py`
   - **Commit**: `d4c8c60`

4. **🟡 Speed Field Missing in delta_t Events**
   - **Error**: delta_t events had no speed field → correlation algorithm couldn't work
   - **Evidence**: Recent events showed `speed: None` or missing speed field
   - **Fix**: Added `'speed': self.consist_speeds.get(consist_id, 0)` to delta_t event data
   - **File**: `backend/tracking_daemon.py:204`
   - **Commit**: `8d97f24`

5. **🟡 Gate Editor Path Wrong**
   - **Error**: `[Errno 2] No such file or directory: 'C:\\z21-Terminal\\backend\\config.json'`
   - **Cause**: Gate editor tried to save to backend/config.json instead of root
   - **Fix**: Changed to use `get_config_path()` instead of hardcoded path calculation
   - **File**: `backend/routers/config.py:347`
   - **Commit**: `5e04b62`

6. **🟡 Config Paths Not Centralized**
   - **User feedback**: "ci sono altri mille posti in cui qualcosa salva il config, ti prego di controllare tutti"
   - **Fix**: Systematic search and replace all config.json access with `get_config_path()`
   - **Files**: `backend/routers/config.py`, `backend/z21_manager.py`, `backend/video_feed.py`
   - **Commits**: `5e04b62`, `aaa8db5`

7. **🟡 Error Messages Not Visible in Logs**
   - **User feedback**: "ma perchè non ho visto l'errore nel log, perchè non era rosso?"
   - **Cause**: FastAPI/Starlette WebSocket handler uses print() instead of log()
   - **Fix**: Created `ColoredOutput` wrapper class to intercept sys.stdout.write() and add colored [ERROR]/[WARN] prefix
   - **File**: `backend/log_colors.py:69-112`
   - **Commit**: `0502e73`

8. **🟢 Orange Color for [SPEED] Log Prefix**
   - **User request**: "possiamo dare un colore anche agli eventi speed? Orange"
   - **Fix**: Added `'\033[38;5;208m'` (orange) to [SPEED] prefix in log_colors.py
   - **File**: `backend/log_colors.py:26`
   - **Commit**: `0a4e3cd`

**Database Migrations** (Historical Data Correction):

1. **Speed 70 → 88 Correction** (`fix_speed_70_to_88.py`):
   - **Context**: User meant 70% of 126 = 88 DCC speed, not literal 70
   - **User feedback**: "quando ti ho detto che i 333 eventi erano a speed 70, volevo dire 70% non 70, quindi speed 88!!!!!"
   - **Results**:
     - 352 delta_t events updated: speed 70 → 88
     - 2 speed_setting events updated: speed_new 70 → 88
   - **Backup**: `analytics.db.backup_20260115_181523.backup`

**Architecture Improvements**:
- ✅ **Global state pattern** in dependencies.py for analytics_logger access
- ✅ **TYPE_CHECKING guard** prevents circular imports
- ✅ **Centralized config path** via get_config_path() across all files
- ✅ **Auto-prefix error wrapper** for better log visibility

**Production Deployment**:
- ✅ All fixes deployed to PC Windows via `z21-deploy-dev`
- ✅ Speed Tuning chart now shows data correctly
- ✅ Speed_setting events logging to database (verified with test session)
- ✅ Orange [SPEED] log prefix visible in console
- ✅ Config.json synced from Mac to PC (gate modifications preserved)

**Final Status**:
- **Tag**: `v1.4` (moved from initial Phase 1 commit)
- **Commits**: `cdf5f9c` → `9f50436` (8 commits)
- **Testing**: ✅ Full verification on PC Windows production
- **User confirmation**: All features working correctly

**Time Investment**: ~6 hours debugging + testing
**Key Insight**: async/await bugs are silent killers - function appears to work (logs print) but never executes (no DB writes)

---

### 2025-01-15 - 🎨 **FRONTEND REFACTORING COMPLETATO** (Analytics Dashboard)

**Status**: ✅ **MILESTONE ACHIEVED** - Modular chart components, merged to develop

**Objective**: Reduce AnalyticsPanel.jsx from 1684 lines (monolithic) to modular architecture with extracted chart components + helpers + constants

**Final Results**:
- **AnalyticsPanel.jsx**: 1684 → 1151 lines (-31.6% reduction, -533 lines)
- **Total modular code**: 909 lines across 8 new files
- **Architecture**: 5 Chart Components + 1 Helpers Module + 1 Constants Module + 1 Plan Document
- **Chart compatibility**: 100% - all Current/Overview/Reports view differences preserved
- **Testing**: All features verified on PC Windows production (all charts, session filtering, consist filtering, click interactions)

**Files Created** (8 total):
1. `web/src/components/charts/DeltaTChart.jsx` (282 lines) - Δt Trends with session breaks + box-select zoom
2. `web/src/components/charts/FPSChart.jsx` (162 lines) - Inference FPS with average badge
3. `web/src/components/charts/ConfidenceChart.jsx` (138 lines) - Detection confidence per locomotive
4. `web/src/components/charts/OperatingTimeChart.jsx` (94 lines) - Total operating time (Overview only)
5. `web/src/components/charts/HistoricalTrendChart.jsx` (178 lines) - Session-by-session trend (Reports tab)
6. `web/src/utils/analyticsHelpers.js` (86 lines) - 7 pure utility functions
7. `web/src/constants/analyticsConstants.js` (31 lines) - Shared constants + styles
8. `docs/FRONTEND_REFACTOR_PLAN.md` (1535 lines) - Complete refactoring documentation

**Critical Features Preserved**:
- **DeltaTChart**: 8 Current/Overview differences (XAxis dataKey, scroll, width, dots, stroke, zoom, duplicate Y-axis, auto-scroll)
- **FPSChart**: 5 Current/Overview differences + FPS avg badge (idle filtering)
- **ConfidenceChart**: Snapshot (Current) vs Aggregated (Overview) logic
- **HistoricalTrendChart**: Custom tooltip showing ALL consists + clickable points for Session Detail Modal

**Bugs Fixed During Refactoring**:
1. **ConfidenceChart Overview mode**: Now aggregates all historical events (loco 5 missing fix)
2. **FPSChart dots alignment**: Dots only in Current mode (aligned with DeltaTChart behavior)
3. **DRY improvements**: Eliminated duplicate data prep logic in ConfidenceChart

**Time Investment**: ~6-8 hours across 4 phases
**Commits**: 17 commits (Phase 0 → Phase 4)
**Branch**: `refactor-frontend` → merged to `develop`

**Benefits**:
- ✅ Single Responsibility: Each chart component ~90-280 lines (manageable)
- ✅ Reusability: Charts can be used independently
- ✅ Testability: Isolated components easier to test
- ✅ Maintainability: Future chart additions follow established pattern
- ✅ DRY: Shared constants/helpers eliminate duplication
- ✅ Scalability: Adding SpeedCorrelationChart (v1.4) now straightforward

**Deployment**: Tested on PC Windows production after each phase (same workflow as backend refactoring)

**Git Workflow**:
- Merged: `refactor-frontend` → `develop` (--no-ff, preserve history)
- Tagged: `frontend-refactor-complete`
- Branch deleted: Local and remote cleaned up

**Production Deployment**: ✅ **VERIFIED** (2025-01-15)
- Deployed via `z21-deploy-dev` on PC Windows
- All 5 chart components working perfectly
- No regressions, all features functional
- User confirmed: "la perfezione!" 🎯

---

### 2025-01-15 - 🎉 **BACKEND REFACTORING COMPLETATO** (Phase 4)

**Status**: ✅ **MILESTONE ACHIEVED** - Modular architecture complete, merged to develop

**Objective**: Reduce main.py from 2340 lines (monolithic) to modular architecture with routers + services + WebSocket handlers

**Final Results**:
- **main.py**: 2340 → 742 lines (-68.3% reduction, -1598 lines)
- **Total modular code**: 3162 lines across 11 new files
- **Architecture**: Routers (4) + Services (4) + WebSocket Handlers (2) + Dependencies system
- **Endpoint compatibility**: 100% - all 27 endpoints functional, zero breaking changes
- **Testing**: All features verified on PC Windows production (locomotive control, tracking, YOLO, analytics, gate editor)

**Files Created** (11 total):
1. `backend/dependencies.py` (230 lines) - Global state dependency injection
2. `backend/routers/analytics.py` (226 lines) - 6 analytics endpoints
3. `backend/routers/config.py` (378 lines) - 7 config/consist/gate endpoints
4. `backend/routers/roster.py` (110 lines) - 3 roster endpoints
5. `backend/routers/status.py` (125 lines) - 2 status/telemetry endpoints
6. `backend/services/analytics_db.py` (435 lines) - SQLite analytics queries
7. `backend/services/broadcast.py` (237 lines) - WebSocket broadcast utilities
8. `backend/services/config_manager.py` (172 lines) - Configuration access helpers
9. `backend/services/downsampling.py` (149 lines) - LTTB + smart Δt downsampling
10. `backend/websocket_handlers/ws_control.py` (394 lines) - Real-time locomotive control (10 message types)
11. `backend/websocket_handlers/ws_tracking.py` (192 lines) - YOLO tracking daemon handler (3 message types)

**Critical Bugs Fixed During Refactoring**:
1. **Namespace Collision**: Renamed `websockets/` → `websocket_handlers/` (uvicorn conflict)
2. **WebSocket Crash**: Fixed `get_full_roster()` import from `routers.roster`
3. **Tracking Broken**: Synced `tracking_daemon_ws` with `dependencies.set_tracking_daemon_ws()`
4. **Video Panels Missing**: Updated `get_tracked_consist_ids()` to use `gate_ids` field (config schema change)
5. **YOLO Bbox Gone**: Changed video feed callback to use `dependencies.get_yolo_detections()`
6. **Dead Code**: Removed unused globals `tracking_daemon_ws` and `yolo_detections` (final cleanup)

**Architecture Achieved**:
```
backend/
├── main.py (742 lines - minimal delegation, FastAPI app)
├── dependencies.py (global state injection)
├── routers/
│   ├── analytics.py (6 endpoints)
│   ├── config.py (7 endpoints)
│   ├── roster.py (3 endpoints)
│   └── status.py (2 endpoints)
├── services/
│   ├── analytics_db.py (SQLite queries)
│   ├── broadcast.py (WebSocket utilities)
│   ├── config_manager.py (config helpers)
│   └── downsampling.py (LTTB + smart sampling)
└── websocket_handlers/
    ├── ws_control.py (10 control messages)
    └── ws_tracking.py (3 tracking messages)
```

**Benefits for Future Development**:
- ✅ **Maintainability**: Single responsibility per file (~150-400 lines each)
- ✅ **Testability**: Each router/service can be tested independently
- ✅ **Scalability**: New features (Speed Table Auto-Tuning v1.3) require zero main.py changes
- ✅ **Collaboration**: Multiple developers can work on different routers without conflicts
- ✅ **Debugging**: Clear separation of concerns, easier to locate bugs

**Time Investment**: ~10-12 hours total (4 phases, incremental testing after each)
**Rollback Safety**: Git tag created after each phase (rollback ready if needed)

**Commits**: `10d0bfd` → `0502e73` (14 commits across 4 phases)

**Documentation Updated**:
- `backend/README.md` - Project structure section
- `docs/REFACTOR_PLAN.md` - Complete implementation guide
- `CLAUDE.md` - This changelog entry

**Next Steps** (v1.3 Speed Table Auto-Tuning):
- Add `routers/speed_tuning.py` (clean separation)
- Extend `AnalyticsDB` with speed correlation queries
- Add CV write operations in `services/cv_manager.py`

---

### 2025-01-15 - ♻️ **BACKEND REFACTORING: Phase 2.2 Completato + Venv Documentation**

**Status**: ✅ **Config Router Extracted** - 7 endpoints migrated to `backend/routers/config.py`

**Phase 2.2 Implementation**:

1. **Config Router Created** (`backend/routers/config.py`, 378 lines):
   - GET `/api/consists` - List all consists with state and gates
   - POST `/api/consists` - Create new consist with CV19 write (Virtual/DCC mode)
   - PUT `/api/consists/{address}` - Update consist (mode switching, gate assignments)
   - DELETE `/api/consists/{address}` - Delete consist (writes CV19=0 if DCC mode)
   - GET `/api/config/tracking` - Get tracking configuration (idle_timeout, thresholds, consists)
   - GET `/api/gates` - Get current gate configuration
   - POST `/api/save-gates` - Save gate configuration from web editor

2. **Key Features**:
   - **CV19 Operations**: Automatic CV write for Virtual Mode (CV19=0) vs DCC Mode (CV19=consist_address)
   - **Global State Management**: Uses dependency injection via `dependencies.get_consist_data()`, `dependencies.get_z21_manager()`
   - **Broadcast Integration**: Updates global state and broadcasts to all connected clients after CRUD operations
   - **Backup Creation**: Gate editor creates `config.json.backup` before saving

3. **Testing Results** (PC Windows production):
   - ✅ GET `/api/consists` → 2 consists, 4 gates
   - ✅ GET `/api/gates` → 4 gates
   - ✅ GET `/api/config/tracking` → idle_timeout 10s, 2 consists

**Refactoring Progress**:
- **main.py**: 2340 → 1227 lines (-1113 lines, **-47.5%** reduction)
- **Routers extracted**: analytics.py (228 lines), config.py (378 lines)
- **Total endpoints migrated**: 13/27 (48%)

**Critical Documentation Added**:
- **Plan file updated** with **"⚠️ CRITICAL: Development Environment Requirements"** section
- **Emphasizes**: ALWAYS use venv on both Mac AND PC, every time calling python3
- **Includes**: Practical examples for Mac (`source venv/bin/activate`) and PC (`.\venv\Scripts\Activate.ps1`)
- **Explains**: Why it matters (dependency isolation, version control, reproducibility)
- **Warns**: What happens if forgotten (ModuleNotFoundError, wrong Python version, conflicts)

**Files Modified**:
- `backend/routers/config.py` (NEW - 378 lines)
- `backend/main.py` (removed 7 config endpoints, -334 lines)
- `~/.claude/plans/glimmering-sleeping-starfish.md` (venv requirements section added)

**Next Steps**: Phase 2.3 - Extract locomotives router (8 endpoints)

**Commits**: `cbd1e60` - Phase 2.2: Extract config router + Plan file venv documentation

---
---

## Archived Changelog Entries (Moved from CLAUDE.md 2025-01-17)

These entries were moved to keep CLAUDE.md under 40KB.
Only v1.0.0 JMRI Independence, Speed Table Phase 2, and Phase 1 remain in main file.

---

## ⛔ KNOWN ISSUES / FAILED EXPERIMENTS

**🚫 NON RIPROVARE QUESTI APPROCCI - GIÀ TESTATI E FALLITI**

### 1. ⛔ Start-Process per Finestre Detached (Windows)
**Tentato**: 2025-01-09 + 2025-01-11
**Problema**: `Start-Process pwsh.exe -WindowStyle Hidden/Normal` NON crea processi veramente detached
- Processo resta legato alla sessione SSH
- Chiudi SSH → processo termina
- Riapri SSH → backend morto
- La finestra non appare o si chiude immediatamente

**Soluzione funzionante**: ✅ **Windows Task Scheduler**
- `Register-ScheduledTask` + `Start-ScheduledTask`
- Processo veramente detached dal sistema operativo
- Sopravvive a: SSH close, logout, reboot
- Usato attualmente in `z21-start` function

**Riferimenti**: CHANGELOG_ARCHIVE.md riga 299-335

---

### 2. ⛔ Motion Detection Puro per Locomotive Tracking
**Tentato**: 2025-12-29 (Phase 3 sospesa)
**Problema**: Background subtraction MOG2 NON sufficiente per tracking affidabile
- Troppo sensibile a: illuminazione, ombre, elementi statici del plastico
- Impossibile distinguere lead da rear locomotive senza ML
- Bounding box include loco + carrozze → centro ≠ posizione reale locomotiva
- Tracciato ovale = direzioni multiple → pattern analysis troppo complesso

**Approcci falliti**:
- Motion detection con pattern analysis (tetti, pantografi, scoring)
- Calcolo vettore direzione per estremità bounding box
- Ottimizzazioni background subtractor (varThreshold, learningRate, morphology)
- Versione minimalista (solo area filtering)

**Soluzione funzionante**: ✅ **YOLO Custom Training**
- YOLOv8 nano trained su 4 locomotive specifiche
- Dataset Roboflow con annotazioni manuali
- mAP50 = 93.1% (standard) / 91.7% (OBB)
- Detection robusta a tutte le distanze e angoli

**Riferimenti**: CHANGELOG_ARCHIVE.md riga 1364-1497

---

### 3. ⛔ PowerShell 7 Task Scheduler con Colori ANSI
**Tentato**: 2025-01-11
**Problema**: PS7 encoding UTF-8 vs console Task Scheduler codepage 850/1252
- **PlainText mode** (`$PSStyle.OutputRendering = 'PlainText'`): Funziona ma solo B/N, niente colori
- **Ansi mode** (`$PSStyle.OutputRendering = 'Ansi'`): Mostra codici ANSI grezzi `[97m[INIT][0m` invece dei colori
- La console Task Scheduler non interpreta ANSI codes correttamente

**Soluzione funzionante**: ✅ **Hybrid Configuration**
- **SSH**: PowerShell 7 (migliore sintassi, comandi riescono al primo tentativo)
- **Task Scheduler**: PowerShell 5.1 (colori perfetti, encoding Windows-1252 nativo)
- `start-backend.ps1` ha fix encoding PS7 (inattivo con PS5.1, pronto se serve)

**Riferimenti**: CLAUDE.md 2025-01-11 changelog

---

### 4. ⛔ Idle Line Breaks Visualization in Δt Chart (Recharts Limitation)
**Tentato**: 2025-01-13 (5 approcci diversi, tutti falliti)
**Problema**: Recharts non supporta line breaks visuali basate su gap temporali in dataset con null naturali
- Ogni evento ha UN solo consist (gate crossing = single consist per timestamp)
- Dataset naturalmente ha: `{delta_t_c10: value, delta_t_c11: null}` OR viceversa
- Recharts `connectNulls` prop gestisce SOLO null consecutivi, non gap temporali

**Approcci falliti** (tutti revertati via git reset --hard):

1. **Segment-based + separate data arrays** (commit `f3c40da`)
   - Multiple Line components, ognuno con proprio data array
   - Problema: Tutti i segmenti sovrapposti a sinistra del chart (no timeline corretta)
   - Legend duplicata (7+ voci per consist invece di 2)

2. **Unified dataset + null boundaries** (commit `615f68e`)
   - Dataset unificato con null points inseriti ai gap boundaries
   - connectNulls={false} per rompere linee
   - Problema: Solo mini-segmenti 2-3 punti (rompe su OGNI null, inclusi naturali)

3. **Selective null boundaries** (commit `63e508e`)
   - Null SOLO per consist con gap, non tutti i consist
   - Problema: Stesso del #2 (ogni null naturale rompe la linea)

4. **Double-null strategy + connectNulls=true** (commit `f470b53`)
   - connectNulls={true} per connettere null singoli (naturali)
   - Null doppi (tutti i consist) ai gap boundaries
   - Problema: Recharts IGNORA completamente double-null points → nessun line break

5. **Segment-based + XAxis numerico** (commit `8037997`)
   - XAxis type="number" con timestamp domain
   - Multiple Line components con data separati
   - Problema DISASTROSO:
     - Punti allineati verticalmente (scale compressione)
     - Legend con 1000+ voci ("delta" ripetuto)
     - Overview chart illeggibile (legend riempie schermo)
     - Nessuna linea (rarissimi casi)

**Root Cause** (Recharts design limitation):
- Recharts non ha concetto di "gap temporale" tra punti
- `connectNulls` gestisce solo presenza/assenza valori, non timing
- XAxis numerico con data separati non condivide domain correttamente
- Multiple Line con data props generano legend entries duplicate

**Decisione**: ✅ **FEATURE ABBANDONATA**
- Hard reset a commit `19d227e` (ultima versione stabile)
- 5 commit revertati completamente
- Analytics Dashboard funziona perfettamente SENZA idle line breaks
- Linee continue = accettabile (user può vedere gap negli stats cards)

**Alternative considerate MA non perseguite**:
- Custom SVG paths (troppo complesso, reinventare Recharts)
- Switch a libreria diversa (Plotly, Victory) → breaking change enorme
- Dashed lines durante idle → già provato in passato, stesso problema

**Riferimenti**: Git commits f3c40da → 8037997 (tutti revertati)

---


**💡 REGOLA GENERALE**: Se un approccio è nell'archive come "FALLITO" o "SOSPESO", NON riprovarlo senza una ragione tecnica specifica nuova (es. nuova versione software, hardware diverso).

---


---

### 2025-01-17 - 🎉 **v1.0.0 - Production Release**

**Status**: ✅ **PRODUCTION READY** - Complete locomotive control system with AI-powered speed optimization

**Milestone**: First production release with full feature set:
- ✅ Dual consist control (C10, C11) with real-time WebSocket sync
- ✅ YOLO-based computer vision tracking (4 locomotives, OBB model, TensorRT GPU acceleration)
- ✅ Automatic speed compensation via Virtual Consist Mode
- ✅ Interactive Speed Table Viewer with direct CV write to decoder (POM)
- ✅ JMRI-compatible checkpoint interpolation with float precision
- ✅ Cumulative intelligent CV recommendations with auto-clear on fix
- ✅ Session tracking with running session display (green badge in Reports)
- ✅ Analytics dashboard with intelligent downsampling (LTTB algorithm)
- ✅ Mobile-first PWA design with Tailscale HTTPS access

**What's New in v1.0.0**:
- **Speed Table Viewer Phase 2** complete:
  - Interactive editing with checkpoint-based interpolation
  - Direct CV write to decoder via Z21 POM (28 CVs in ~2.8s)
  - Dual-button workflow (Apply & Write vs Export Only)
  - Visual feedback for modifications (blue borders, asterisks)
  - Float precision state (prevents rounding loss)
- **Analytics Downsampling Fix**: Fixed critical bug (673→500 events in Overview mode)
- **Running Sessions**: Visible in Reports tab with green border + "RUNNING" badge
- **Deployment Workflow**: Skill created for Mac → PC automation
- **Documentation**: Consolidated (CLAUDE.md, skills, comprehensive guides)

**Technical Stack**:
- Backend: FastAPI + WebSocket + SQLite + YOLO v8 nano OBB + TensorRT
- Frontend: React 18.3 + Vite 6.0 + Tailwind CSS
- Hardware: Roco Z21 Bianca, Tapo IP camera 720P, PC Windows 11 + GPU

**Production Deployment**: PC Windows (gaming-pc) via z21-deploy-dev

**Production Testing**: CV write verified on loco 7 (CV86: 80→82, confirmed via Hornby app)

**Next Phase**: v1.1.0+ (optional enhancements - system is feature-complete)

---

### 2025-01-17 - 🐛 **Fix: Running Sessions in Reports Tab**

**Status**: ✅ **FIXED AND DEPLOYED**

**Bug**: Running sessions (end_time = NULL) were excluded from Reports list due to SQL filter.

**Impact**: Current active session invisible in Reports tab despite UI supporting green badge.

**Fix**:
- Removed `AND end_time IS NOT NULL` filter in `get_reports_data()` query
- Calculate duration using `time.time()` if `end_time` is NULL (shows elapsed time)
- Added missing `import time` for time module

**Result**: Running sessions now visible in Reports with:
- Green border (`border-green-500/50`)
- Green background (`bg-green-900/10`)
- "RUNNING" badge (green)
- Real-time duration updates on refresh

**Commit**: `54d7e7d` - fix(reports): include running sessions in Reports tab

**Deployed**: Backend restarted on PC production

---

### 2025-01-17 - ⚙️ **Speed Table Viewer: Phase 2 Interactive Editing** (Complete)

**Status**: ✅ **DEPLOYED TO PRODUCTION** - JMRI-compatible checkpoint-based editing with float precision

**Objective**: Transform read-only speed table into fully interactive editor with automatic smoothing via checkpoint interpolation.

**Implementation Time**: ~2 hours (9 tasks)

**Features Implemented**:

1. **Float Precision State** (`cvValuesFloat`):
   - Stores CV values as floats internally (e.g., 146.333...)
   - Rounds only on display (UI shows integers)
   - Rounds only on export (JMRI CSV compatibility)
   - Prevents gradual adjustment propagation loss
   - Example: Adjust CV86 by -1, four times → adjacent CVs smoothly update (no "stuck" values)

2. **Checkpoint System**:
   - Default 10 checkpoints at operational speeds: `[3, 6, 9, 12, 15, 17, 20, 23, 26, 28]` (10%-100%)
   - Checkboxes under all 28 bars (user can customize)
   - Minimum 2 checkpoints enforced (interpolation requires bounds)
   - Toggle on/off with visual feedback

3. **Linear Interpolation**:
   - Auto-recalculates non-checkpoint steps when checkpoint modified
   - Formula: `value = valueA + (valueB - valueA) * (stepX - stepA) / (stepB - stepA)`
   - Interpolates both zones: prev→modified, modified→next
   - Pure float math (no rounding until display/export)

4. **Interactive Editing**:
   - Click checkpoint value (blue bold) → numeric input appears
   - Click checkpoint bar → same input
   - Type new value (0-255), Enter to save, Escape to cancel
   - Keyboard navigation, auto-focus, validation
   - Non-checkpoints: gray text, read-only (auto-interpolated)

5. **Recommendations Approval Workflow**:
   - Checkbox per recommendation (default all checked)
   - Select All / Deselect All buttons
   - "Apply N Selected" button (disabled if 0 selected)
   - Visual feedback: unchecked recommendations opacity 50%
   - Apply → calls `applyInterpolation()` for each selected CV
   - Selection clears after apply

6. **CSV Export Updated**:
   - Phase 1: Exported original + suggested recommendations
   - Phase 2: Exports current `cvValuesFloat` (includes all user edits + applied recommendations)
   - JMRI-compatible format unchanged (CV,value)

**UI/UX Enhancements**:
- Checkpoint values: **blue bold, cursor pointer** (click to edit)
- Non-checkpoint values: gray (auto-interpolated, read-only)
- Percent labels: shown only on checkpoints
- Tooltips: "Click to edit" vs "Auto-interpolated"
- Smooth Tailwind transitions on all changes

**Technical Details**:
- State: `cvValuesFloat` (CV67-94 as floats), `checkpoints` (Set), `editingStep`, `selectedRecommendations` (Set)
- Functions: `interpolate()`, `applyInterpolation()`, `startEditing()`, `saveEdit()`, `toggleCheckpoint()`, `toggleRecommendation()`
- Safety: CV range validation (0-255), minimum 2 checkpoints
- Real-time: interpolation on every checkpoint modification

**Commit**: `db1196a` - feat(speed-table): implement Phase 2 interactive editing (+295 lines, -57 lines)

**Deployment**:
- Deployed to PC production (z21-deploy-dev)
- Frontend rebuilt (Vite 7.3.0, 3.88s)
- Backend restarted (Task Scheduler)

**Skill Update**: Added "Complete Workflow (Mac → PC)" section to `z21-deployment` skill:
- Step 4 reminder: **MUST deploy to PC after push**
- Clarified: Mac = development, PC = production environment

**Testing**: Ready for user validation in production environment.

**Next Phase**: Phase 2B (future) - Direct POM write via Z21 (optional, alternative to CSV export).

---

### 2025-01-17 - 🧹 **CLAUDE.md Cleanup + Deployment Skill Creation**

**Status**: ✅ **COMPLETED** - Documentation consolidation and skill-based workflow enforcement

**Objective**: Eliminate duplication between CLAUDE.md and new deployment skill, enforce correct workflow usage

**Trigger**: I manually executed deployment commands instead of using PowerShell aliases. User corrected: "ma non hai eseguito l'alias!!! Hai fatto tutto a mano"

**Implementation**:

1. **Created Deployment Skill** (`~/.claude/skills/z21-deployment/SKILL.md` - 314 lines):
   - Deployment decision tree (docs/backend/frontend → correct command)
   - PowerShell aliases (z21-deploy-dev, z21-deploy, z21-restart, z21-stop, z21-log)
   - 8 CRITICAL rules (venv, CV test mode, git workflow, frontend rebuild, secrets, SSH protocol, encoding, README language)
   - Pre-deploy checklist (7 items)
   - Config files behavior (config.json vs config.local.json)
   - PC info (SSH, paths, shell, logs)

2. **Consolidated Skill** (404 → 314 lines, 22% reduction):
   - Removed CRITICAL Rule #9 (PowerShell Aliases) - redundant with dedicated section
   - Removed CRITICAL Rule #10 (SSH Username) - evident from examples
   - Removed Common Scenarios - redundant with Decision Tree
   - Removed Quick Reference Table - redundant with PowerShell Aliases

3. **Simplified CLAUDE.md** (~73 lines removed):
   - Python Virtual Environment section: 56 lines → 8 lines
   - Production Deployment section: 35 lines → 10 lines
   - Replaced with references to `~/.claude/skills/z21-deployment/SKILL.md`

**Benefits**:
- ✅ Single source of truth (skill file)
- ✅ Auto-triggered on deployment requests
- ✅ Prevents manual command execution
- ✅ CLAUDE.md cleaner, more maintainable
- ✅ Zero duplication

**User Feedback During Creation**:
- "dove possibile userei comandi one line"
- "SSH gaming-pc da solo ti da errore, serve sempre l'username"
- "ci sono altri aliases su PC che potrsti usare in altri scenari, uno su tutti z21-log"
- "recentemente abbiamo deciso di mettere su git anche claude ed altri files md, per cui quella parte la devi togliere"
- "hai fatto un check per vedere se alcune regole sono duplicate?"

**Files Created**:
- `~/.claude/skills/z21-deployment/SKILL.md` - Complete deployment workflow

**Files Modified**:
- `/Users/riccardosallusti/Documents/_PROGETTI/z21-Terminal/CLAUDE.md` - Simplified deployment sections

---

### 2025-01-17 - 🔄 **SPEED TABLE VIEWER: Cumulative Intelligent Recommendations** (v0.9.0)

**Status**: ✅ **MILESTONE ACHIEVED** - Iterative testing workflow with intelligent "fixed" detection

**Objective**: Transform single-session recommendations into cumulative historical analysis that persists across sessions but auto-clears when speeds are proven OK.

**Implementation Time**: ~6-8 hours (14 commits with multiple iterations on auto-select logic)

**Major Changes**:

1. **Cumulative Historical Data** (Backend):
   - `get_critical_events_by_speed()` now aggregates ALL sessions (removed `session_id` parameter)
   - Cumulative CRITICAL/WARNING counts provide complete problem picture
   - Commit: `08353ce`

2. **Intelligent "Fixed" Detection** (Backend):
   - Speed considered fixed if last tested session has ≥3 Δt events AND <20% CRITICAL rate
   - Fixed speeds excluded from recommendations (problem resolved)
   - Enables iterative workflow: adjust CV → retest → recommendation auto-disappears
   - Commit: `08353ce`

3. **Fixed ±1 CV Adjustment** (Backend - CRITICAL FIX):
   - **Bug**: Cumulative scaling caused massive adjustments (CV86 80→48 = -32!)
   - **User Insight**: "CV misconfiguration error is CONSTANT regardless of CRITICAL count"
   - **Fix**: Changed from `(critical_count // 5) * 2` to fixed `adjustment_magnitude = 1`
   - **Reasoning**: More CRITICALs = more confirmation, NOT bigger CV error
   - **Result**: Conservative iterative approach (adjust -1, retest, repeat)
   - Commits: `9729422`, `fc7b313`

4. **Non-Validated Session Display** (Frontend):
   - Show UI even when session not validated (was blocking entire UI)
   - Added amber badge "WAITING FOR FIRST ΔT" when session exists but no events yet
   - Backend returns latest session regardless of validation state
   - Commits: `6b8116a`, `7b89eab`

5. **Summary Cards Redesign** (Frontend):
   - **Removed**: "Problematic Speeds" card (redundant with Recommendations)
   - **Added**: "Fixed Speeds" card (positive feedback, green theme)
   - **Result**: Card 2 = actionable (what to do), Card 3 = success feedback (what you fixed)
   - Commit: `7e3f6a0`

6. **Step Prominence** (Frontend):
   - "Step 20 (CV86)" format with Step in white font-semibold
   - CV index secondary in gray parentheses
   - Horizontal layout preserved (user preference)
   - Commits: `880ab5a`, `0dd9b98`

7. **Auto-Select Consist** (Frontend - Multiple Iterations):
   - **Goal**: Avoid extra click when opening Speed Tuning tab
   - **Challenge**: Race conditions + wrong data source (cumulativeData has ALL history)
   - **Final Solution**: Use ONLY `reportsData.sessions[0].consists` (last validated session)
   - **Result**: Auto-selects whichever consist(s) ran most recently
   - Commits: `3602259`, `37a8966`, `77c5822` (debug), `0190c1a` (fix), `5118e21` (cleanup)

**Key User Insights Captured**:
- "se adjust continua a sommarsi solo su un CV, resta problema smoothing" → Phase 2 requirement documented
- "io manualmente vado sempre di + o - 2 al massimo" → informed ±1 conservative approach
- "la visualizzazione tutta orizzontale di prima mi piaceva!" → UI preference preserved

**Testing Results**:
- ✅ Cumulative recommendations aggregate historical data correctly
- ✅ Fixed detection works (speed 70% cleared after good session)
- ✅ Non-validated sessions show UI with amber badge
- ✅ Auto-select picks correct consist from last session
- ✅ ±1 adjustment prevents massive CV changes

**Documentation Updated**:
- `docs/SPEED_TABLE_VIEWER.md` - Added "🆕 2025-01-17 Updates" section
- Workflow example showing 3-session iterative testing
- Phase 2 smoothing requirement documented

**Commits**: 14 total (`08353ce` → `5118e21`)

**Files Modified**:
- `backend/services/analytics_db.py` - Cumulative queries + fixed detection
- `backend/services/speed_table_helpers.py` - Fixed ±1 adjustment
- `backend/routers/speed_table.py` - Latest session (any state)
- `web/src/components/charts/SpeedTableViewer.jsx` - UI improvements
- `web/src/components/AnalyticsPanel.jsx` - Auto-select consist logic
- `docs/SPEED_TABLE_VIEWER.md` - Feature documentation
- `CLAUDE.md` - This changelog entry

**Versioning Decision**: Tagged as **v0.9.0** (not v1.4)
- Current: Feature-complete Phase 1 (Speed Table Viewer read-only)
- Future v1.0.0: Phase 2 Auto CV Adjust with smoothing (automation completa)
- Reasoning: 0.x = "stable but evolving", 1.0 = production-ready auto-tuning

---

### 2025-01-17 - 📄 **CSV Export JMRI-Compatible + Phase 2 Design Documentation**

**Status**: ✅ **COMPLETED**

**Objective**: Finalize Phase 1 CSV export for seamless JMRI DecoderPro import workflow + comprehensive Phase 2 design documentation

**Implementation Time**: ~3-4 hours (research JMRI import, refactor CSV export, write extensive Phase 2 docs)

---

#### Part 1: CSV Export JMRI-Compatible

**Research**: JMRI DecoderPro CSV import capabilities
- ✅ Confirmed: JMRI supports CSV import via File → Import → CSV
- ✅ Format required: Simple 2-column `CV,value` (no extra metadata)
- ⚠️ Historical bug: Quoted headers caused import failures (fixed in JMRI 5.x+)

**Changes**:
```javascript
// OLD (multi-column, not importable):
'JMRI Step,CV Index,Current Value,Suggested Value,Delta,Critical Count,Warning Count,Notes\n'
'20,86,128,126,-2,12,5,"Needs adjustment"\n'

// NEW (JMRI-ready):
'CV,value\n'
'86,126\n'
```

**Logic Update**:
- If CV has recommendation → use **suggested value** (optimized)
- If CV is OK → use **current value** (no change)
- Result: CSV contains speed table ready to apply directly

**UI Changes**:
- Button label: "Export CSV" → **"Export for JMRI"**
- Filename suffix: `_JMRI.csv` (clarifies purpose)
- Tooltip: Added JMRI menu path "(File → Import → CSV)"

**User Workflow** (zero friction):
1. Click "Export for JMRI" in Speed Table Viewer
2. Download `speed_table_consist_11_loco_7_JMRI.csv`
3. JMRI DecoderPro → File → Import → CSV → Select file
4. Write to decoder (ops mode or programming track)

**Commits**:
- Frontend: `web/src/components/charts/SpeedTableViewer.jsx` (lines 48-77, 237-241, 293)

---

#### Part 2: Phase 2 Design Documentation (Comprehensive)

**Documented in**: `docs/SPEED_TABLE_VIEWER.md` (new section ~400 lines)

**Topics Covered**:

1. **JMRI Checkpoint System** (How It Works)
   - Checkbox-based fixed points (user controls which steps)
   - Automatic linear interpolation between checkpoints
   - Edit behavior (modify checkpoint → all intermediate steps recalculate)
   - Mathematical formula with examples

2. **Checkpoint Strategy: Operational Speed Percentages**
   - **Key Insight**: Checkpoints should match controller usage (10%, 20%, ..., 100%)
   - **Default checkpoints**: Steps `[3, 6, 9, 12, 15, 17, 20, 23, 26, 28]`
   - **Rationale**: Users never command intermediate steps directly (only used by decoder during acceleration)
   - Mapping table: Percentage → DCC Speed → JMRI Step → CV Index

3. **The Rounding Problem** (Critical Design Decision)
   - **Issue**: Integer-only math prevents gradual adjustments from propagating
   - **Example**: Adjusting step 20 by -1 requires -3 to -4 iterations before adjacent steps change
   - **Solution**: Float precision internally, round only on display/export
   - **Benefits**: Mathematically accurate, gradual propagation works correctly, JMRI-compatible

4. **Implementation Plan** (Detailed)
   - UI changes: Checkpoint checkboxes, interactive editing, real-time preview
   - Data structure: Float precision state (`cvValuesFloat`)
   - Interpolation algorithm: Linear between checkpoints (code examples)
   - Edge cases: First/last checkpoint handling
   - Backend changes: Minimal (endpoint already complete)

5. **Features Roadmap**
   - Core (required): Checkpoint editing, float precision, interactive adjustment
   - Optional: Auto-apply to decoder, validation, undo/redo, preset curves

6. **Timeline Estimate**: 12-16 hours total effort

**Code Examples**: Complete JavaScript/JSX snippets for all major functions

**Benefits**:
- ✅ Zero ambiguity for future implementation
- ✅ Captures JMRI workflow understanding
- ✅ Documents float precision rationale (critical decision)
- ✅ Ready for Phase 2 kickoff (no rework needed)

---

**Files Modified**:
- `web/src/components/charts/SpeedTableViewer.jsx` - CSV export refactor
- `docs/SPEED_TABLE_VIEWER.md` - Phase 2 section (~400 lines added)
- `CLAUDE.md` - This changelog entry

**Key Insight Captured** (from user):
> "I checkpoint attivi di default devono sempre essere quelli corrispondenti alle speed percentuali 10 20 30 40 etc, perchè muovendo le loco sempre usando gli step percentuali, che è come facciamo sempre noi, andiamo ad interpolare solo i valori intermedi"

**Result**: Phase 1 finalized (JMRI-ready export), Phase 2 fully designed and documented. Ready to implement when user validates Phase 1 in production.

---

### 2025-01-17 - 🎯 **Phase 2 User Approval Workflow Design**

**Status**: ✅ **DOCUMENTED**

**Objective**: Define semi-automatic CV adjustment workflow with user approval

**User Request**:
> "Io preferisco il 2 ma mi piacerebbe che la preview fosse cmq in realtime sulle barre e poi approve finale, la uno è troppo granulare, non è rocket science"

**Approach Finalized**: Checkboxes + Real-Time Preview + Final Approval

---

#### Design Decisions

**What User Wanted**:
- ✅ Batch approval (not per-CV granular)
- ✅ Real-time preview on bars (visual feedback immediate)
- ✅ Single final approval (not rocket science)

**How It Works**:

1. **Recommendations List** (with checkboxes)
   - Default: All recommendations checked (opt-out model)
   - User unchecks recommendations they don't want to apply
   - Select All / Deselect All buttons

2. **Real-Time Preview** (on speed table bars)
   - Checked recommendation → Bar changes color immediately (blue → orange)
   - Checkpoint bars: Solid orange (direct modification)
   - Interpolated bars: Light orange (auto-calculated)
   - Unchecked → Bar reverts to blue (no change)
   - Tooltip: "Current: 128 → New: 127 (float: 126.67)"

3. **Impact Summary**
   - "2 checkpoints + 8 interpolated = 10 CVs will change"
   - User sees EXACTLY what will be modified before approval

4. **Final Approval Button**
   - "Apply 2 Selected Changes"
   - Disabled if no checkboxes selected
   - Opens confirmation dialog with summary

5. **Confirmation Dialog**
   - Summary: "2 checkpoint values, 8 interpolated, Total: 10 CVs"
   - Choose method: Export to JMRI CSV OR Write via POM (Z21)
   - Cancel button always available

**Benefits**:
- ✅ Not too granular (single approval, not per-CV)
- ✅ Visual feedback (bars change in real-time)
- ✅ Safe (confirmation dialog before write)
- ✅ Flexible (user can select/deselect)
- ✅ Simple ("not rocket science")
- ✅ WYSIWYG (bars show exact effect)

**Implementation Details**: Full code examples in `docs/SPEED_TABLE_VIEWER.md` (~200 lines added)
- State management (selected recommendations, projected CV values)
- Checkbox handlers (toggle, select all, deselect all)
- Real-time preview calculation (useEffect on selection change)
- Bar rendering with color coding (checkpoint vs interpolated)
- Apply button handler (confirmation dialog + export/write)

**Safety Features**:
- Visual validation (color-coded bars)
- Tooltip precision (shows float values)
- Confirmation dialog (summary before write)
- Optional warnings (monotonicity, large jumps, range check)
- Undo capability (reset to original values)

**User Experience Flow**: 5 steps documented
1. View recommendations (all checked by default)
2. Adjust selections (uncheck unwanted, bars update real-time)
3. Review visual preview (hover for exact values)
4. Click "Apply Selected Changes" (confirmation dialog)
5. Choose method (Export CSV or POM write)

**Files Modified**:
- `docs/SPEED_TABLE_VIEWER.md` - User Approval Workflow section (~200 lines)
- `CLAUDE.md` - This changelog entry

**Key Insight Captured**: Batch approval with real-time preview strikes optimal balance between safety and usability. Per-CV approval is overkill for simple CV adjustments.

**Recommendation Persistence Clarified**:
- Recommendations are **persistent** (calculated on-the-fly from cumulative historical data)
- Cancel button does NOT consume recommendations (they remain until resolved)
- Two resolution paths:
  1. Manual: User applies changes via JMRI/POM
  2. Automatic: New test session shows speed FIXED (< 20% CRITICAL rate)
- Iterative workflow: Apply -1 → test → if still problematic, apply -1 again
- Database: No changes on Cancel, recommendations recalculated from same historical events

**Files Modified**:
- `docs/SPEED_TABLE_VIEWER.md` - Recommendation Persistence section (~80 lines)
- `CLAUDE.md` - This clarification

---

## 📋 TODO / Future Enhancements
