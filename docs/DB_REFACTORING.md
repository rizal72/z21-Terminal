# Database State Refactoring + Settings UI

**Date**: 2025-01-17
**Status**: 🟡 Planning Complete - Implementation Pending
**Goal**: Separate configuration from operational state, rename DB, implement Settings UI

---

## 📋 Executive Summary

**Problem**: config.json currently mixes configuration data (Z21 IP, gates geometry) with operational state (virtual_mode, auto_compensation, test_mode). This creates confusion and makes Settings UI design unclear.

**Solution**:
1. Rename `analytics.db` → `data.db` (more generic, not just analytics)
2. Move operational state from config.json → database
3. Implement Settings UI with proper separation of concerns

**Result**: Clean architecture with config.json = master data/settings, data.db = runtime state + time-series data

---

## 🎯 Architectural Decisions

### Configuration vs Operational State Separation

**✅ STAYS in config.json** (Configuration - user editable via Settings UI):
- Z21 network settings (IP, port)
- Video feed settings (width, height, fps, RTSP URL)
- YOLO model settings (confidence, iou, obb, device)
- Gate geometry (position, size, rotation, color)
- Gate → Consist assignment (which gates belong to which consist)
- Consist definitions (lead/rear address, reference/adjust loco)
- Locomotive roster (address, name, decoder, color, cv_profiles, functions)
- Tracking thresholds (timing_thresholds, idle_timeout)
- Debug mode toggle (backend logging level)

**🗄️ MOVES to data.db** (Operational State - UI toggle managed):
- `virtual_mode` (per-consist DCC mode toggle)
- `auto_compensation_enabled` (per-consist speed matching toggle)
- `test_mode` (global 'testing' vs 'normal' momentum)

**Rationale**:
- Virtual Mode and Auto Compensation change during daily operations via UI toggle
- User should NOT manually edit these in config.json
- Settings UI should NOT show these (they're in ConsistController toggle buttons)
- CV Profile Mode changes via T hotkey, persists across restarts

---

## 🗄️ Database Changes

### 1. Rename Database

**Current**: `backend/data/analytics.db`
**New**: `backend/data/data.db`

**Why**: More generic name, reflects broader usage beyond analytics (now includes operational state, speed tables, etc.)

### 2. New Schema - Operational State Tables

```sql
-- Consist operational state (virtual mode, auto compensation)
CREATE TABLE consist_state (
  consist_id INTEGER PRIMARY KEY,
  virtual_mode BOOLEAN DEFAULT 1,
  auto_compensation_enabled BOOLEAN DEFAULT 1,
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System-wide operational state (CV profile mode, etc.)
CREATE TABLE system_state (
  key TEXT PRIMARY KEY,
  value TEXT,
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initial data for system_state
INSERT INTO system_state (key, value) VALUES ('test_mode', 'testing');

-- Initial data for consist_state (migrate from config.json)
INSERT INTO consist_state (consist_id, virtual_mode, auto_compensation_enabled)
VALUES
  (10, 1, 1),  -- Consist 10: both enabled
  (11, 1, 1);  -- Consist 11: both enabled
```

### 3. Existing Tables (Unchanged)

```sql
-- Time-series analytics data
CREATE TABLE speed_data (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER,
  consist_address INTEGER,
  gate_id INTEGER,
  loco_address INTEGER,
  timestamp REAL,
  delta_t REAL,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Analytics sessions
CREATE TABLE sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  start_time TEXT,
  end_time TEXT,
  validated BOOLEAN DEFAULT 0,
  event_count INTEGER DEFAULT 0
);

-- Speed Table CV67-94 (with undo history)
CREATE TABLE cv_speed_table (
  loco_address INTEGER PRIMARY KEY,
  cv_values TEXT NOT NULL,
  previous_values TEXT,
  source TEXT,
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 📂 Files to Modify

### Phase 1: Database Rename (15 files)

**Backend Core**:
- `backend/services/analytics_db.py` - Core DB path definition (line 17: `DB_PATH`)
- `backend/tracking_daemon.py` - Analytics logger import
- `backend/analytics_logger.py` - Direct DB access
- `backend/services/speed_table_helpers.py` - Speed table CV read/write

**Scripts**:
- `scripts/utils/import_speed_tables_from_jmri.py` - JMRI import script
- `scripts/utils/c11_trend_analysis.py` - Analytics report generator
- `scripts/utils/analytics_report.py` - Analytics report generator

**Documentation**:
- `CLAUDE.md` - Project overview
- `docs/CHANGELOG_ARCHIVE.md` - Historical changelog
- `docs/LOCOMOTIVE_SYNC_MAC_PC.md` - Mac/PC workflow
- `docs/JMRI_INTEGRATION.md` - JMRI relationship
- `docs/SPEED_TABLE_VIEWER.md` - Speed Table UI docs
- `docs/SPEED_TABLE_DB_MIGRATION.md` - Speed Table migration docs
- `docs/SPEED_TABLE_TUNING.md` - Speed matching workflow
- `docs/ANALYTICS.md` - Analytics system docs

### Phase 2: Operational State Migration (7 backend files)

**State Read Locations** (need to read from DB instead of config.json):
- `backend/main.py` - Server startup, config loading
- `backend/z21_manager.py` - Consist initialization (virtual_mode, auto_compensation)
- `backend/services/broadcast.py` - Initial state broadcast to clients
- `backend/websocket_handlers/ws_control.py` - Toggle virtual mode handler
- `backend/websocket_handlers/ws_tracking.py` - Auto compensation logic
- `backend/routers/config.py` - CV profile mode endpoint
- `backend/tracking_manager.py` - Tracking daemon state

**State Write Locations** (need to persist to DB on toggle):
- `backend/websocket_handlers/ws_control.py` - Virtual mode toggle handler
- `backend/routers/config.py` - CV profile mode toggle handler
- `backend/z21_manager.py` - Auto compensation toggle handler

---

## 🎨 Settings UI Design

### Icon Changes

**Current**:
- Logo: `fa-train` (amber glow)
- Consist Manager: `fa-gears` ← **MOVE to Settings**

**New**:
- Logo: `fa-train` (unchanged)
- Consist Manager: `fa-link` (linked locomotives)
- Settings: `fa-gears` (moved from Consist Manager)

**Rationale**: `fa-train` already used in logo, `fa-link` semantically represents consist linking, `fa-gears` standard for settings.

### Settings Modal Structure

**Header Button**:
```jsx
<button
  onClick={() => setSettingsOpen(true)}
  className="... border-control-grey hover:border-signal-amber ..."
  title="Settings"
>
  <i className="fa-solid fa-gears text-lg"></i>
</button>
```

**Modal Tabs**:
1. **Z21 Network** - IP address, UDP port
2. **Video Feed** - Width, height, fps, camera RTSP URL
3. **YOLO Model** - Model path, confidence, iou, obb, device selection
4. **Gates** - Gate list + consist assignment + assignment strategy
5. **System** - Debug mode (backend logging level)

**NOT in Settings UI** (managed elsewhere):
- Virtual Mode / Auto Compensation (ConsistController toggle buttons)
- CV Profile Mode (T hotkey, badge in header)
- Locomotives / Functions (too complex, managed via JMRI + import scripts)

### Gates Tab Design

```
┌─ Gates Tab ───────────────────────────────────────┐
│                                                   │
│ ┌─ Gate 1 ──────────────────────────────────┐    │
│ │ Name: Gate 1                              │    │
│ │ Position: X=995, Y=27 (Size: 65x43)       │    │
│ │ [Edit Position] → Opens Gate Editor (E)    │    │
│ │ Assigned to: [Dropdown: Consist 11 ▼]     │    │
│ └───────────────────────────────────────────┘    │
│                                                   │
│ ┌─ Gate 2 ──────────────────────────────────┐    │
│ │ Name: Gate 2                              │    │
│ │ Position: X=10, Y=269 (Size: 44x47)       │    │
│ │ [Edit Position]                            │    │
│ │ Assigned to: [Dropdown: Consist 11 ▼]     │    │
│ └───────────────────────────────────────────┘    │
│                                                   │
│ ┌─ Gate 3 ──────────────────────────────────┐    │
│ │ Name: Gate 3                              │    │
│ │ Position: X=1086, Y=326 (Size: 80x80)     │    │
│ │ [Edit Position]                            │    │
│ │ Assigned to: [Dropdown: Consist 10 ▼]     │    │
│ └───────────────────────────────────────────┘    │
│                                                   │
│ ┌─ Gate 4 ──────────────────────────────────┐    │
│ │ Name: Gate 4                              │    │
│ │ Position: X=479, Y=29 (Size: 50x50)       │    │
│ │ [Edit Position]                            │    │
│ │ Assigned to: [Dropdown: Consist 10 ▼]     │    │
│ └───────────────────────────────────────────┘    │
│                                                   │
│ ┌─ Consist 10 Assignment Strategy ──────────┐    │
│ │ Mode: ● Asymmetric ○ Symmetric            │    │
│ │                                            │    │
│ │ Reference Loco (D645 014): Gate 3          │    │
│ │ Adjust Loco (Gr.675 017):  Gate 4          │    │
│ │                                            │    │
│ │ ℹ️ Asymmetric: Only ref@G3→adj@G4 valid    │    │
│ │    (figure-8 track geometry)               │    │
│ └────────────────────────────────────────────┘    │
│                                                   │
│ ┌─ Consist 11 Assignment Strategy ──────────┐    │
│ │ Mode: ○ Asymmetric ● Symmetric            │    │
│ │                                            │    │
│ │ ℹ️ Symmetric: Both G1→G2 and G2→G1 valid   │    │
│ │    (oval track geometry)                   │    │
│ └────────────────────────────────────────────┘    │
│                                                   │
│              [Save Changes] [Cancel]              │
└───────────────────────────────────────────────────┘
```

**Features**:
- Real-time validation (IP format, port range, file paths)
- Save button → `POST /api/settings/update` → restart affected services
- Restart warnings: "Changing this requires backend/tracker/video restart"
- Reset to defaults button per tab
- "Edit Position" button activates Gate Editor (key E)

### Separation of Concerns

**Gate Editor (key E)** - Visual editing:
- Drag/drop gate position
- Resize gate dimensions
- Rotate gate angle
- Real-time preview on video feed
- Saves to config.json

**Settings Gates Tab** - Logical assignment:
- Which gates belong to which consist (gate_ids)
- Assignment strategy (symmetric vs asymmetric)
- Reference/Adjust loco mapping (gate_assignment)
- Saves to config.json

---

## ⚠️ Critical Notes

### Database Location & Synchronization

**Production (PC Windows)**:
- Path: `C:\z21-Terminal\backend\data\analytics.db` (soon `data.db`)
- This is the **OFFICIAL database** (production data)

**Development (Mac)**:
- Path: `~/Documents/_PROGETTI/z21-Terminal/backend/data/analytics.db`
- This is a **COPY** - **potentially NOT up-to-date** with PC
- Used for testing only

**Synchronization Strategy**:
- Before DB rename testing: Copy PC DB → Mac (via SSH/scp)
- After successful rename on Mac: Deploy to PC (via `z21-deploy-dev`)
- Verify PC production still works after rename

### Migration Safety

**Pre-Migration Checklist**:
1. ✅ Backup PC database: `cp data/analytics.db data/analytics.db.backup`
2. ✅ Test rename on Mac first (dev environment)
3. ✅ Verify all backend endpoints still work
4. ✅ Verify frontend UI still loads data
5. ✅ Deploy to PC and test production

**Rollback Plan**:
- If rename breaks: `mv data/data.db data/analytics.db` (revert)
- If operational state migration breaks: Restore from config.json

---

## 🚀 Implementation Plan

### Phase 0: Centralize Database Access (FIRST - Architecture Refactoring)

**Why First**: Rename `analytics_db.py` → `data_db.py` and consolidate all DB access in one place BEFORE doing any other changes. This ensures we have a single source of truth for database operations.

**Step 0.1: Rename File + Class**
```bash
cd ~/Documents/_PROGETTI/z21-Terminal/backend/services
mv analytics_db.py data_db.py
```

**Step 0.2: Refactor Class Name**

File: `backend/services/data_db.py` (renamed from analytics_db.py)

```python
# OLD
class AnalyticsDB:
    """Analytics database access layer"""

# NEW
class DataDB:
    """Centralized database access - analytics, speed tables, operational state"""
```

**Step 0.3: Update All Imports Across Backend**

Find all files importing `AnalyticsDB`:
```bash
grep -r "from backend.services.analytics_db import" backend/
grep -r "from .services.analytics_db import" backend/
```

Replace in all files:
```python
# OLD
from backend.services.analytics_db import AnalyticsDB
conn = AnalyticsDB.get_connection()

# NEW
from backend.services.data_db import DataDB
conn = DataDB.get_connection()
```

**Files to update** (~10 files):
- `backend/routers/analytics.py`
- `backend/routers/speed_table.py`
- `backend/services/speed_table_helpers.py`
- `backend/tracking_daemon.py`
- `backend/analytics_logger.py`
- Any other backend file importing AnalyticsDB

**Step 0.4: Add Operational State Methods to DataDB**

Extend `backend/services/data_db.py` with new methods (add at end of class):

```python
class DataDB:
    """Centralized database access - analytics, speed tables, operational state"""

    # === Existing methods (keep unchanged) ===
    @staticmethod
    def get_connection() -> sqlite3.Connection:
        ...

    @staticmethod
    def get_latest_session():
        ...

    # ... all existing analytics methods ...

    # === NEW: Operational State Methods ===

    @staticmethod
    def get_consist_state(consist_id: int) -> dict:
        """Get consist operational state (virtual_mode, auto_compensation)"""
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT virtual_mode, auto_compensation_enabled
            FROM consist_state
            WHERE consist_id = ?
        """, (consist_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            # Default values if not found
            return {
                "virtual_mode": True,
                "auto_compensation_enabled": True
            }

        return {
            "virtual_mode": bool(row[0]),
            "auto_compensation_enabled": bool(row[1])
        }

    @staticmethod
    def set_virtual_mode(consist_id: int, enabled: bool):
        """Update consist virtual mode"""
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO consist_state (consist_id, virtual_mode, auto_compensation_enabled)
            VALUES (?, ?, (SELECT COALESCE(auto_compensation_enabled, 1) FROM consist_state WHERE consist_id = ?))
            ON CONFLICT(consist_id) DO UPDATE SET
                virtual_mode = excluded.virtual_mode,
                last_updated = CURRENT_TIMESTAMP
        """, (consist_id, enabled, consist_id))

        conn.commit()
        conn.close()

    @staticmethod
    def set_auto_compensation(consist_id: int, enabled: bool):
        """Update consist auto compensation"""
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO consist_state (consist_id, virtual_mode, auto_compensation_enabled)
            VALUES (?, (SELECT COALESCE(virtual_mode, 1) FROM consist_state WHERE consist_id = ?), ?)
            ON CONFLICT(consist_id) DO UPDATE SET
                auto_compensation_enabled = excluded.auto_compensation_enabled,
                last_updated = CURRENT_TIMESTAMP
        """, (consist_id, consist_id, enabled))

        conn.commit()
        conn.close()

    @staticmethod
    def get_test_mode() -> str:
        """Get CV profile mode (testing or normal)"""
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT value
            FROM system_state
            WHERE key = 'test_mode'
        """)

        row = cursor.fetchone()
        conn.close()

        return row[0] if row else "normal"

    @staticmethod
    def set_test_mode(mode: str):
        """Set CV profile mode (testing or normal)"""
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO system_state (key, value, last_updated)
            VALUES ('test_mode', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                last_updated = CURRENT_TIMESTAMP
        """, (mode,))

        conn.commit()
        conn.close()
```

**Step 0.5: Test Refactoring (Mac)**
```bash
# Start backend (should work with new imports)
z21-backend

# Check logs for errors
# Test existing features:
# - Speed Table Viewer (uses DataDB for CV read/write)
# - Analytics Dashboard (uses DataDB for sessions/events)
# - Gate crossing logging (uses DataDB)

# All should work identically (only internal refactoring)
```

**Expected Duration**: 1-2 hours

**Benefits**:
- ✅ Single source of truth for all DB access
- ✅ Easier to add new DB operations (just extend DataDB)
- ✅ Better naming (DataDB more generic than AnalyticsDB)
- ✅ Operational state methods ready for Phase 2

---

### Phase 1: Database File Rename (Safe, Low Risk)

**Step 1.1: Update DB Path in DataDB**
- File: `backend/services/data_db.py`
- Change: `DB_PATH = Path(...) / "data" / "analytics.db"` → `"data.db"`
- Impact: All backend code that imports `DataDB` will use new path

**Step 1.2: Update Documentation**
- Files: 10 markdown docs (CLAUDE.md, CHANGELOG_ARCHIVE.md, etc.)
- Change: Replace `analytics.db` → `data.db` in text

**Step 1.3: Rename Physical File (Mac)**
```bash
cd ~/Documents/_PROGETTI/z21-Terminal/backend/data
mv analytics.db data.db
```

**Step 1.4: Test on Mac**
```bash
# Start backend
z21-backend

# Check logs for DB connection success
# Test Speed Table Viewer (reads from DB)
# Test Analytics Dashboard (reads from DB)
```

**Step 1.5: Deploy to PC**
```powershell
# On PC (via SSH from Mac)
z21-deploy-dev  # Pulls code, restarts backend

# On PC, rename DB file
cd C:\z21-Terminal\backend\data
Rename-Item analytics.db -NewName data.db

# Verify backend restart successful
z21-log
```

**Step 1.6: Production Verification**
- Check Speed Table Viewer on PC
- Check Analytics Dashboard on PC
- Check gate crossing logging (new events written to DB)
- Run for 1 hour to ensure stability

**Expected Duration**: 30-60 minutes

---

### Phase 2: Operational State Migration (Complex, Higher Risk)

**Step 2.1: Create Migration Script**

File: `scripts/utils/migrate_operational_state.py`

```python
"""
Migrate operational state from config.json to data.db

Creates consist_state and system_state tables.
Populates with current values from config.json.
DOES NOT modify config.json (manual cleanup later).
"""

import json
import sqlite3
from pathlib import Path

def migrate_operational_state():
    # Load config.json
    config_path = Path(__file__).parent.parent.parent / "config.json"
    with open(config_path) as f:
        config = json.load(f)

    # Connect to database
    db_path = Path(__file__).parent.parent.parent / "backend" / "data" / "data.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consist_state (
            consist_id INTEGER PRIMARY KEY,
            virtual_mode BOOLEAN DEFAULT 1,
            auto_compensation_enabled BOOLEAN DEFAULT 1,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_state (
            key TEXT PRIMARY KEY,
            value TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migrate consist state
    for consist_id, consist_data in config.get("consists", {}).items():
        virtual_mode = consist_data.get("virtual_mode", True)
        auto_comp = consist_data.get("auto_compensation_enabled", True)

        cursor.execute("""
            INSERT OR REPLACE INTO consist_state (consist_id, virtual_mode, auto_compensation_enabled)
            VALUES (?, ?, ?)
        """, (int(consist_id), virtual_mode, auto_comp))

    # Migrate system state
    test_mode = config.get("test_mode", "normal")
    cursor.execute("""
        INSERT OR REPLACE INTO system_state (key, value)
        VALUES ('test_mode', ?)
    """, (test_mode,))

    conn.commit()
    conn.close()

    print("✅ Operational state migrated to database")
    print("   - consist_state: virtual_mode, auto_compensation_enabled")
    print("   - system_state: test_mode")

if __name__ == "__main__":
    migrate_operational_state()
```

**Step 2.2: Update Backend Code to Use DataDB**

Replace all config.json reads for operational state with DataDB calls (operational state methods added in Phase 0):

**Example 1**: `backend/z21_manager.py` - Consist initialization
```python
# OLD
consist_config = self.config["consists"][str(consist_address)]
virtual_mode = consist_config.get("virtual_mode", True)

# NEW
from backend.services.data_db import DataDB
state = DataDB.get_consist_state(consist_address)
virtual_mode = state["virtual_mode"]
```

**Example 2**: `backend/websocket_handlers/ws_control.py` - Toggle handler
```python
# OLD
self.config["consists"][str(address)]["virtual_mode"] = enable
save_config(self.config)  # Writes to config.json

# NEW
from backend.services.data_db import DataDB
DataDB.set_virtual_mode(address, enable)
```

**Example 3**: `backend/routers/config.py` - CV profile mode
```python
# OLD
config["test_mode"] = new_mode
save_config(config)

# NEW
from backend.services.data_db import DataDB
DataDB.set_test_mode(new_mode)
```

**Files to Update** (7 files - operational state reads):
- `backend/main.py` - Config loading, CV profile mode
- `backend/z21_manager.py` - Consist initialization (virtual_mode, auto_compensation)
- `backend/services/broadcast.py` - Initial state broadcast
- `backend/websocket_handlers/ws_control.py` - Virtual mode toggle
- `backend/websocket_handlers/ws_tracking.py` - Auto compensation logic
- `backend/routers/config.py` - CV profile mode toggle
- `backend/tracking_manager.py` - Tracking daemon state

**Step 2.3: Remove from config.json**

After successful migration and testing, manually edit config.json:

```json
{
  "consists": {
    "10": {
      "name": "C10 Interno",
      "lead_address": 1,
      "rear_address": 5,
      // REMOVE THESE LINES:
      // "virtual_mode": true,
      // "auto_compensation_enabled": true
    }
  },
  // REMOVE THIS LINE:
  // "test_mode": "testing"
}
```

**Step 2.5: Test Migration**
- Mac: Run migration script, test all toggles (Virtual Mode, Auto Comp, T key)
- PC: Deploy, run migration, test production
- Verify state persists across backend restarts
- Verify UI toggles update database correctly

**Expected Duration**: 2-3 hours

---

### Phase 3: Settings UI Implementation (Frontend Heavy)

**Step 3.1: Icon Redesign**

File: `web/src/App.jsx`

Line ~1070 (Consist Manager button):
```jsx
// OLD
<i className="fa-solid fa-gears text-lg md:text-xl"></i>

// NEW
<i className="fa-solid fa-link text-lg md:text-xl"></i>
```

New Settings button (after Consist Manager):
```jsx
<button
  onClick={() => setSettingsOpen(true)}
  disabled={!isConnected}
  className="flex items-center gap-2 px-2 py-2 bg-control-dark border border-control-grey rounded hover:border-signal-amber hover:text-signal-amber transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
  title="Settings"
>
  <i className="fa-solid fa-gears text-lg md:text-xl"></i>
</button>
```

**Step 3.2: Settings Modal Component**

File: `web/src/components/SettingsModal.jsx` (NEW)

Structure:
```jsx
import { useState } from 'react';

function SettingsModal({ isOpen, onClose, apiUrl }) {
  const [activeTab, setActiveTab] = useState('z21');
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);

  // Tabs: z21, video, yolo, gates, system

  return (
    <div className={`fixed inset-0 z-50 ${isOpen ? 'block' : 'hidden'}`}>
      {/* Backdrop */}
      {/* Modal */}
      {/* Tab Navigation */}
      {/* Tab Content */}
      {/* Save/Cancel buttons */}
    </div>
  );
}
```

**Step 3.3: Backend Settings Endpoint**

File: `backend/routers/settings.py` (NEW)

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import json

router = APIRouter()

class SettingsUpdate(BaseModel):
    z21_ip: str = None
    z21_port: int = None
    video_width: int = None
    video_height: int = None
    # ... all config fields

@router.post("/api/settings/update")
async def update_settings(update: SettingsUpdate):
    """Update configuration and restart affected services"""
    try:
        # Load config.json
        config_path = Path(__file__).parent.parent / "config.json"
        with open(config_path) as f:
            config = json.load(f)

        # Update fields (only non-None values)
        if update.z21_ip:
            config["z21"]["ip"] = update.z21_ip

        # Save config.json
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        # Determine which services need restart
        restart_needed = []
        if update.z21_ip or update.z21_port:
            restart_needed.append("backend")
        if update.video_width or update.video_height:
            restart_needed.append("video_feed")
        if update.yolo_confidence:
            restart_needed.append("tracker")

        return {
            "status": "success",
            "message": "Settings updated",
            "restart_needed": restart_needed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 3.4: Integration & Testing**
- Add SettingsModal to App.jsx imports
- Test each tab (Z21, Video, YOLO, Gates, System)
- Test validation (IP format, port range)
- Test save → backend restart workflow
- Test on Mac + deploy to PC

**Expected Duration**: 4-6 hours

---

## 📊 Testing Strategy

### Test 1: Database Rename (Mac)
```bash
cd ~/Documents/_PROGETTI/z21-Terminal/backend/data
mv analytics.db data.db
z21-backend  # Should start without errors
# Test Speed Table Viewer
# Test Analytics Dashboard
# Check logs for DB connection success
```

### Test 2: Database Rename (PC Production)
```powershell
# SSH to PC
ssh riccardo@gaming-pc

# Deploy code changes
z21-deploy-dev

# Rename DB
cd C:\z21-Terminal\backend\data
Rename-Item analytics.db -NewName data.db

# Restart backend
z21-restart

# Monitor logs
z21-log
```

### Test 3: Operational State Migration (Mac)
```bash
# Run migration script
python scripts/utils/migrate_operational_state.py

# Verify tables created
sqlite3 backend/data/data.db "SELECT * FROM consist_state;"
sqlite3 backend/data/data.db "SELECT * FROM system_state;"

# Start backend
z21-backend

# Test toggles in UI
# - Virtual Mode toggle (Consist Controller)
# - Auto Compensation toggle (Consist Controller)
# - T key (CV Profile Mode)

# Verify state persists after restart
```

### Test 4: Settings UI (Mac)
```bash
# Start frontend dev server
z21-frontend

# Test each tab:
# - Z21: Change IP, verify validation
# - Video: Change resolution, verify preview
# - YOLO: Change confidence, verify slider
# - Gates: Assign gate to consist, verify dropdown
# - System: Toggle debug mode, verify backend logs

# Test save button
# Verify config.json updated
# Verify restart warnings shown
```

---

## 🎯 Success Criteria

**Phase 0 Complete** when:
- ✅ `analytics_db.py` renamed to `data_db.py`
- ✅ `AnalyticsDB` class renamed to `DataDB`
- ✅ All imports updated (~10 backend files use `DataDB`)
- ✅ Operational state methods added to `DataDB` class
- ✅ Backend starts without errors (Mac)
- ✅ Speed Table Viewer and Analytics Dashboard work (Mac)
- ✅ No breaking changes (pure refactoring)

**Phase 1 Complete** when:
- ✅ All backend code references `data.db` instead of `analytics.db`
- ✅ All documentation updated
- ✅ Mac backend starts successfully with renamed DB
- ✅ PC production backend starts successfully with renamed DB
- ✅ Speed Table Viewer and Analytics Dashboard work on both machines
- ✅ No errors in backend logs related to DB connection

**Phase 2 Complete** when:
- ✅ Migration script successfully creates tables and populates data
- ✅ Backend reads operational state from DB (not config.json)
- ✅ UI toggles persist state to DB (not config.json)
- ✅ State persists across backend restarts
- ✅ Virtual Mode, Auto Compensation, CV Profile Mode work as before
- ✅ config.json cleaned up (operational state removed)

**Phase 3 Complete** when:
- ✅ Settings button in header with `fa-gears` icon
- ✅ Consist Manager button uses `fa-link` icon
- ✅ Settings modal opens with 5 tabs
- ✅ Each tab displays current config values
- ✅ Save button updates config.json
- ✅ Restart warnings shown when appropriate
- ✅ Gates tab allows consist assignment
- ✅ Works on Mac dev and PC production

---

## 📅 Timeline Estimate

**Phase 0** (Centralize DB Access): 1-2 hours
**Phase 1** (DB File Rename): 30-60 minutes
**Phase 2** (Operational State Migration): 2-3 hours
**Phase 3** (Settings UI): 4-6 hours

**Total**: 7.5-11.5 hours (2 work sessions)

---

## 🚨 Rollback Plan

**If Phase 0 fails**:
```bash
# Mac
cd ~/Documents/_PROGETTI/z21-Terminal/backend/services
mv data_db.py analytics_db.py
git checkout backend/  # Revert all import changes
z21-backend  # Test restart
```

**If Phase 1 fails**:
```bash
# Mac
cd ~/Documents/_PROGETTI/z21-Terminal/backend/data
mv data.db analytics.db
git checkout backend/services/data_db.py  # Revert DB path change

# PC
cd C:\z21-Terminal\backend\data
Rename-Item data.db -NewName analytics.db
z21-deploy-dev  # Pulls reverted code
```

**If Phase 2 fails**:
```bash
# Drop tables
sqlite3 backend/data/data.db "DROP TABLE consist_state;"
sqlite3 backend/data/data.db "DROP TABLE system_state;"

# Revert code changes
git checkout backend/  # Revert all backend files
z21-restart
```

**If Phase 3 fails**:
```bash
# Settings UI is pure frontend, no data risk
git checkout web/src/  # Revert frontend changes
z21-frontend  # Restart dev server
```

---

## ✅ Pre-Implementation Checklist

Before starting implementation tomorrow:

- [ ] Verify PC database is backed up (`cp analytics.db analytics.db.backup`)
- [ ] Copy PC database to Mac for testing (`scp riccardo@gaming-pc:C:/z21-Terminal/backend/data/analytics.db ~/Documents/_PROGETTI/z21-Terminal/backend/data/`)
- [ ] Verify Mac backend starts successfully with current DB
- [ ] Review this document and confirm plan with user
- [ ] Create feature branch: `git checkout -b feature/db-state-refactoring`
- [ ] Confirm no pending changes in working directory

---

## 📝 Notes

**Database Sync Status**:
- PC: `C:\z21-Terminal\backend\data\analytics.db` (OFFICIAL, production data)
- Mac: `~/Documents/_PROGETTI/z21-Terminal/backend/data/analytics.db` (COPY, potentially outdated)

**Recommendation**: Before testing, copy PC DB → Mac to ensure consistent state.

**Git Strategy**: Create feature branch for all changes, test thoroughly, then merge to develop.

**Documentation Updates**: After successful implementation, update CLAUDE.md and JMRI_INTEGRATION.md with new architecture.

---

**Status**: 🟡 Ready for implementation (2025-01-18)

**Code Status**: ✅ **NO CODE MODIFIED** - All source files unchanged, only documentation created

**Architecture Decision**: ✅ **CENTRALIZED DB ACCESS** - Single `DataDB` class instead of separate `state_db.py`

**Implementation Order**:
1. **Phase 0**: Centralize DB access (analytics_db.py → data_db.py, add operational state methods)
2. **Phase 1**: Rename DB file (analytics.db → data.db)
3. **Phase 2**: Migrate operational state (config.json → database tables)
4. **Phase 3**: Settings UI (icon redesign + modal with 5 tabs)
