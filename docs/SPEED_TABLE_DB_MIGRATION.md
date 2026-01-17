# Speed Table Database Migration + Config Refactoring

**Status**: ✅ **IMPLEMENTED AND DEPLOYED** (v1.0.0)
**Date**: 2025-01-17
**Implementation Time**: ~8 hours (design → code → test → deploy → bugfixes)
**Version**: v1.0.0 (Production Ready)

**Note**: This was the design document. For implementation details and testing results, see CLAUDE.md changelog entry for v1.0.0.

---

## Overview

### Objective
Eliminate dependency on JMRI roster XML for daily speed table CV67-94 management, maintaining JMRI only for initial locomotive setup.

### Current State (Before)
- ✅ Speed Table Viewer Phase 2 complete (interactive editing + direct CV write)
- ⚠️ CV67-94 read from JMRI roster XML every time
- ⚠️ Modifications invisible until JMRI roster manually updated
- ⚠️ Locomotive metadata scattered across 2 config sections

### Target State (After)
- ✅ CV67-94 stored in database (source of truth)
- ✅ Modifications visible immediately (no JMRI update needed)
- ✅ Locomotive metadata unified in single config section
- ✅ Undo support (1 level snapshot)
- ✅ Re-import button (sync from JMRI when needed)
- ✅ Backward compatible (fallback to JMRI if DB empty)

---

## Architecture

```
┌─────────────────┐
│  JMRI Roster    │ ← One-time import only (initial setup)
│   (XML files)   │
└────────┬────────┘
         │ import script (manual command)
         ↓
┌─────────────────┐      ┌──────────────────┐
│  config.json    │ ←──→ │  analytics.db    │
│  (locomotives)  │      │  (CV67-94 table) │
└────────┬────────┘      └─────────┬────────┘
         │                         │
         └──────────┬──────────────┘
                    ↓
         ┌──────────────────┐
         │   Backend API    │
         │ (speed_table.py) │
         └─────────┬────────┘
                   ↓
         ┌──────────────────┐
         │  Frontend UI     │
         │ (SpeedTableViewer)│
         └──────────────────┘
```

**Data Flow**:
1. **Import**: JMRI roster → config.json (metadata) + analytics.db (CV values)
2. **Read**: Frontend → Backend API → DB (primary) → JMRI fallback
3. **Write**: Frontend → Backend API → Z21 POM → DB update
4. **Undo**: Frontend → Backend API → DB previous_values → Z21 POM

---

## 1. Config.json Refactoring

### Before (scattered data)
```json
{
  "locomotive_colors": {
    "1": "#FFFF00",
    "5": "#FF8000",
    "7": "#00FF00",
    "8": "#FF0000"
  },

  "cv_profiles": {
    "1": {
      "normal": {"cv3": 78, "cv4": 58},
      "testing": {"cv3": 0, "cv4": 0}
    },
    "5": {
      "normal": {"cv3": 22, "cv4": 16},
      "testing": {"cv3": 0, "cv4": 0}
    }
    // ... (+ 5 more locos)
  }
}
```

**Problems**:
- Locomotive data in 2 separate sections
- No loco names (only addresses)
- Adding new loco = edit multiple places

---

### After (unified)
```json
{
  "locomotives": {
    "1": {
      "name": "Gr.675 017",
      "decoder": "ESU LokSound V4.0",
      "color": "#FFFF00",
      "cv_profiles": {
        "normal": {"cv3": 78, "cv4": 58},
        "testing": {"cv3": 0, "cv4": 0}
      },
      "notes": "Lead C10 Interno"
    },
    "5": {
      "name": "D645 014",
      "decoder": "ESU LokPilot 5",
      "color": "#FF8000",
      "cv_profiles": {
        "normal": {"cv3": 22, "cv4": 16},
        "testing": {"cv3": 0, "cv4": 0}
      },
      "notes": "Rear C10 Interno, reference loco"
    },
    "7": {
      "name": "E656 239",
      "decoder": "Hornby TXS",
      "color": "#00FF00",
      "cv_profiles": {
        "normal": {"cv3": 22, "cv4": 16},
        "testing": {"cv3": 1, "cv4": 1}
      },
      "notes": "Lead C11 Esterno, adjust loco"
    },
    "8": {
      "name": "E444 056",
      "decoder": "ESU LokPilot 5",
      "color": "#FF0000",
      "cv_profiles": {
        "normal": {"cv3": 22, "cv4": 15},
        "testing": {"cv3": 0, "cv4": 0}
      },
      "notes": "Rear C11 Esterno, reference loco"
    },
    "2": {
      "name": "E656 182",
      "decoder": "ESU LokPilot 5",
      "color": "#FFFFFF",
      "cv_profiles": {
        "normal": {"cv3": 23, "cv4": 14},
        "testing": {"cv3": 0, "cv4": 0}
      },
      "notes": "Single loco"
    },
    "4": {
      "name": "2048",
      "decoder": "ESU LokSound V4.0",
      "color": "#00FFFF",
      "cv_profiles": {
        "normal": {"cv3": 0, "cv4": 0},
        "testing": {"cv3": 0, "cv4": 0}
      },
      "notes": "Single loco (no momentum)"
    },
    "6": {
      "name": "D445 1140",
      "decoder": "ESU LokPilot 5",
      "color": "#FF00FF",
      "cv_profiles": {
        "normal": {"cv3": 23, "cv4": 14},
        "testing": {"cv3": 0, "cv4": 0}
      },
      "notes": "Single loco"
    }
  },

  "consists": {
    "10": { ... },  // ← UNCHANGED (consist logic separate)
    "11": { ... }
  }

  // REMOVED: "locomotive_colors" (merged into locomotives)
  // REMOVED: "cv_profiles" (merged into locomotives)
}
```

**Benefits**:
- ✅ Single source of truth per locomotive
- ✅ Clear separation: `locomotives` (individual) vs `consists` (groups)
- ✅ Add new loco = 1 block
- ✅ Human-readable names

---

## 2. Database Schema

### New Table: `locomotive_speed_table`

```sql
CREATE TABLE IF NOT EXISTS locomotive_speed_table (
    -- Primary Key
    loco_address INTEGER PRIMARY KEY,

    -- Current CV67-94 values (28 speed table steps)
    cv67 INTEGER NOT NULL CHECK(cv67 BETWEEN 0 AND 255),
    cv68 INTEGER NOT NULL CHECK(cv68 BETWEEN 0 AND 255),
    cv69 INTEGER NOT NULL CHECK(cv69 BETWEEN 0 AND 255),
    cv70 INTEGER NOT NULL CHECK(cv70 BETWEEN 0 AND 255),
    cv71 INTEGER NOT NULL CHECK(cv71 BETWEEN 0 AND 255),
    cv72 INTEGER NOT NULL CHECK(cv72 BETWEEN 0 AND 255),
    cv73 INTEGER NOT NULL CHECK(cv73 BETWEEN 0 AND 255),
    cv74 INTEGER NOT NULL CHECK(cv74 BETWEEN 0 AND 255),
    cv75 INTEGER NOT NULL CHECK(cv75 BETWEEN 0 AND 255),
    cv76 INTEGER NOT NULL CHECK(cv76 BETWEEN 0 AND 255),
    cv77 INTEGER NOT NULL CHECK(cv77 BETWEEN 0 AND 255),
    cv78 INTEGER NOT NULL CHECK(cv78 BETWEEN 0 AND 255),
    cv79 INTEGER NOT NULL CHECK(cv79 BETWEEN 0 AND 255),
    cv80 INTEGER NOT NULL CHECK(cv80 BETWEEN 0 AND 255),
    cv81 INTEGER NOT NULL CHECK(cv81 BETWEEN 0 AND 255),
    cv82 INTEGER NOT NULL CHECK(cv82 BETWEEN 0 AND 255),
    cv83 INTEGER NOT NULL CHECK(cv83 BETWEEN 0 AND 255),
    cv84 INTEGER NOT NULL CHECK(cv84 BETWEEN 0 AND 255),
    cv85 INTEGER NOT NULL CHECK(cv85 BETWEEN 0 AND 255),
    cv86 INTEGER NOT NULL CHECK(cv86 BETWEEN 0 AND 255),
    cv87 INTEGER NOT NULL CHECK(cv87 BETWEEN 0 AND 255),
    cv88 INTEGER NOT NULL CHECK(cv88 BETWEEN 0 AND 255),
    cv89 INTEGER NOT NULL CHECK(cv89 BETWEEN 0 AND 255),
    cv90 INTEGER NOT NULL CHECK(cv90 BETWEEN 0 AND 255),
    cv91 INTEGER NOT NULL CHECK(cv91 BETWEEN 0 AND 255),
    cv92 INTEGER NOT NULL CHECK(cv92 BETWEEN 0 AND 255),
    cv93 INTEGER NOT NULL CHECK(cv93 BETWEEN 0 AND 255),
    cv94 INTEGER NOT NULL CHECK(cv94 BETWEEN 0 AND 255),

    -- Undo snapshot (1 level - JSON string)
    previous_values TEXT,  -- {"cv67": 128, "cv68": 130, ..., "cv94": 255}

    -- Metadata
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'jmri_import'  -- 'jmri_import', 'web_ui', 'test_mode', 'undo', 'jmri_reimport'
);

-- Index for audit queries
CREATE INDEX IF NOT EXISTS idx_loco_speed_table_modified
ON locomotive_speed_table(last_modified DESC);
```

**Design Rationale**:
- 28 separate columns (easier SQL queries, typed, no JSON parsing)
- CHECK constraints (0-255 range validation at DB level)
- `previous_values` JSON (flexible, compact, 1 undo level)
- `source` tracking (audit trail: where did values come from?)
- `loco_address` PRIMARY KEY (exactly 1 row per locomotive)

**Storage**: ~350 bytes per locomotive (28 CV + metadata + snapshot)

---

## 3. Implementation Components

### 3.1 Import Script

**File**: `scripts/utils/import_speed_tables_from_jmri.py`

**What it does**:
1. Reads JMRI roster XML files
2. Extracts: locomotive name, CV67-94 speed table
3. Writes to config.json: `locomotives` section (unified metadata)
4. Writes to analytics.db: `locomotive_speed_table` table (CV values)
5. Creates backup of config.json before modifying
6. Removes deprecated sections (`locomotive_colors`, `cv_profiles`)

**Usage**:
```bash
cd ~/Documents/_PROGETTI/z21-Terminal
source venv/bin/activate
python scripts/utils/import_speed_tables_from_jmri.py
```

**Idempotent**: Can run multiple times (INSERT OR REPLACE)
**Safe**: Automatic config backup before modification

---

### 3.2 Backend Helper Functions

**File**: `backend/services/speed_table_helpers.py`

**New functions**:
- `read_cv_speed_table_from_db(loco_address)` - Read CV67-94 from DB
- `update_cv_speed_table_in_db(loco_address, cv_values, source)` - Update DB + save undo snapshot
- `undo_cv_speed_table(loco_address)` - Restore previous_values (swap current ↔ previous)

**File**: `backend/services/config_helpers.py` (NEW)

**Backward compatible loaders**:
- `get_locomotive_color(address)` - Read from new or old format
- `get_locomotive_cv_profile(address, mode)` - Read from new or old format
- `get_locomotive_name(address)` - Read from new format
- `get_all_locomotives()` - Get all locomotives dict

**Transitional support**: Fallback to old sections if `locomotives` not found

---

### 3.3 API Endpoints

**File**: `backend/routers/speed_table.py`

**Updated endpoints**:

1. **GET `/api/speed-table/{consist_id}`**:
   - Read loco name from config.json (`locomotives` section)
   - Read CV67-94 from DB (primary)
   - Fallback to JMRI roster if not in DB
   - Log warning if fallback used (recommend import)

2. **POST `/api/speed-table/write/{consist_id}`**:
   - Write CV67-94 to decoder via Z21 POM (unchanged)
   - After success: `update_cv_speed_table_in_db()` (NEW)
   - Saves undo snapshot automatically

3. **POST `/api/speed-table/reimport/{consist_id}`** (NEW):
   - Force re-read from JMRI roster
   - Update DB with JMRI values
   - Use case: User modified CV via JMRI DecoderPro

4. **POST `/api/speed-table/undo/{consist_id}`** (NEW):
   - Restore `previous_values` from DB
   - Write previous CV to decoder via POM
   - Swap current ↔ previous (can undo the undo)

---

### 3.4 Frontend UI

**File**: `web/src/components/charts/SpeedTableViewer.jsx`

**New buttons** (below existing "Export CSV Only"):

1. **"Undo Last Change"** (amber):
   - Calls `/api/speed-table/undo/{consist_id}`
   - Confirmation dialog before execution
   - Disabled if no previous_values available

2. **"Re-import from JMRI"** (slate):
   - Calls `/api/speed-table/reimport/{consist_id}`
   - Confirmation dialog (overwrites DB)
   - Use when CV modified via JMRI DecoderPro

**Visual feedback**:
- Success/error messages
- Auto-refresh after successful operation

---

## 4. Migration Workflow

### Step 1: Backup (CRITICAL)
```bash
# Manual backups before starting
cp config.json config.json.backup_manual
cp backend/analytics.db backend/analytics.db.backup_manual
```

### Step 2: Create Git Branch
```bash
git checkout -b feature/speed-table-db-migration
```

### Step 3: Implement Code Changes

**New files**:
- `scripts/utils/import_speed_tables_from_jmri.py` (import script)
- `backend/services/config_helpers.py` (backward compatible loaders)

**Modified files**:
- `backend/services/speed_table_helpers.py` (+3 functions)
- `backend/routers/speed_table.py` (+3 endpoints, update existing)
- `web/src/components/charts/SpeedTableViewer.jsx` (+2 buttons)
- `backend/z21_manager.py` (use config_helpers)
- `backend/services/yolo_tracker.py` (use config_helpers)
- Other files using `locomotive_colors` or `cv_profiles` (~5-10 locations)

**Estimate**: 3-4 hours coding + 1 hour testing

### Step 4: Run Import Script (Mac)
```bash
cd ~/Documents/_PROGETTI/z21-Terminal
source venv/bin/activate
python scripts/utils/import_speed_tables_from_jmri.py
```

**Verify**:
- ✅ `config.json` has `locomotives` section (7 entries)
- ✅ Old sections removed (`locomotive_colors`, `cv_profiles`)
- ✅ Backup created (`config.json.backup_YYYYMMDD_HHMMSS`)
- ✅ DB has 7 rows in `locomotive_speed_table`

```bash
sqlite3 backend/analytics.db "SELECT loco_address, cv67, cv94, source FROM locomotive_speed_table;"
```

### Step 5: Test Locally (Mac)
```bash
# Start backend
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Test endpoints (new terminal)
curl http://localhost:8000/api/speed-table/11 | jq '.cv_values'
```

**UI Testing**:
1. Open Speed Table Viewer (Consist 11)
2. Verify CV values load from DB
3. Edit CV86: 80 → 82, click "Apply & Write to Decoder"
4. Close tab, reopen → CV86 should show 82 immediately
5. Click "Undo Last Change" → CV86 back to 80
6. Click "Re-import from JMRI" → verify sync

### Step 6: Deploy to PC
```bash
# Commit changes
git add .
git commit -m "feat: speed table DB migration + config refactoring

- Unified locomotive metadata in config.json (locomotives section)
- CV67-94 stored in analytics.db (source of truth)
- Import script from JMRI roster (one-time setup)
- Undo support (1 level snapshot)
- Re-import button (sync from JMRI)
- Backward compatible config loaders
"

# Push to GitHub
git push origin feature/speed-table-db-migration

# Deploy to PC
ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-deploy-dev"

# Run import script on PC
ssh riccardo@gaming-pc "cd C:\z21-Terminal && python scripts\utils\import_speed_tables_from_jmri.py"
```

### Step 7: Production Testing (PC)
- ✅ Verify config.json updated
- ✅ Verify DB populated
- ✅ Test Speed Table Viewer (read, write, undo)
- ✅ Test fallback (if DB empty → JMRI roster)

### Step 8: Documentation
- Update `CLAUDE.md` (changelog entry)
- Update `docs/SPEED_TABLE_VIEWER.md` (DB architecture)
- Update `README.md` (setup instructions)

---

## 5. Testing Plan

### Unit Tests

**Test 1: Import Script**
```bash
python scripts/utils/import_speed_tables_from_jmri.py
```
Expected:
- 7 locomotives in config.json (`locomotives` section)
- 7 rows in DB (`locomotive_speed_table`)
- Old sections removed
- Backup created

**Test 2: Backend Read (DB priority)**
```bash
curl http://localhost:8000/api/speed-table/11 | jq
```
Expected:
- `cv_values` from DB (not JMRI)
- `adjust_loco_name` from config.json

**Test 3: Write + DB Update**
1. Edit CV86 via UI
2. Verify decoder (Hornby app or ESU)
3. Query DB:
```sql
SELECT cv86, source FROM locomotive_speed_table WHERE loco_address=7;
```
Expected: `82|web_ui`

**Test 4: Undo**
1. Click "Undo Last Change"
2. Verify decoder: CV86 back to original
3. Query DB:
```sql
SELECT cv86, source, previous_values FROM locomotive_speed_table WHERE loco_address=7;
```
Expected: `80|undo|{"cv67": ..., "cv86": 82, ...}`

**Test 5: Re-import from JMRI**
1. Modify CV86 via JMRI: 80 → 85
2. Click "Re-import from JMRI" in UI
3. Query DB:
```sql
SELECT cv86, source FROM locomotive_speed_table WHERE loco_address=7;
```
Expected: `85|jmri_reimport`

**Test 6: Fallback (empty DB)**
1. Drop table: `DROP TABLE locomotive_speed_table;`
2. Open Speed Table Viewer
3. Expected: Values from JMRI roster
4. Expected log: `[SPEED-TABLE] Loco 7: not in DB, reading from JMRI roster`

---

## 6. Rollback Plan

### Quick Rollback (restore config)
```bash
# Mac or PC
cp config.json.backup_YYYYMMDD_HHMMSS config.json
z21-restart  # PC only
```

### Full Rollback (git)
```bash
git checkout develop
git branch -D feature/speed-table-db-migration
```

### DB Rollback (drop table)
```bash
sqlite3 backend/analytics.db "DROP TABLE IF EXISTS locomotive_speed_table;"
```

**Zero risk**: JMRI roster fallback always available.

---

## 7. Benefits

### User Experience
- ✅ **Instant CV updates**: Modifications visible immediately (no JMRI export/import)
- ✅ **Undo support**: Rollback bad changes with 1 click
- ✅ **JMRI independence**: Use JMRI only for initial setup or major changes

### Technical
- ✅ **Single source of truth**: DB for CV values, config for metadata
- ✅ **Audit trail**: Timestamp + source tracking for every change
- ✅ **Maintainability**: Config unified, zero redundancy
- ✅ **Backward compatible**: Fallback to JMRI if DB empty

### Future
- ✅ **Foundation for Step 2**: CRUD locomotives via UI (add/edit/delete)
- ✅ **Versioning ready**: Extend `previous_values` to multi-level undo
- ✅ **Complete JMRI independence**: When combined with UI locomotive management

---

## 8. Known Limitations

### Current Scope (NOT included)
- ⏳ Multi-level undo (only 1 snapshot)
- ⏳ CV history timeline (audit log UI)
- ⏳ CRUD locomotives via UI (Step 2 future)
- ⏳ Batch operations (import/export multiple locos)

### Rare Use Cases
- Adding new locomotive: Still requires JMRI + manual import script
- Modifying decoder type: Update config.json manually
- Programming track operations: Still via JMRI only

**Acceptable tradeoff**: These are rare events (weeks/months), not daily operations.

---

## 9. Success Criteria

### Definition of Done
- ✅ Import script populates config.json + DB successfully
- ✅ Speed Table Viewer reads CV from DB (primary)
- ✅ Write operation updates decoder + DB
- ✅ Undo restores previous CV values
- ✅ Re-import syncs from JMRI roster
- ✅ Fallback to JMRI works when DB empty
- ✅ Backward compatibility maintained (old config format)
- ✅ All tests pass (unit + integration)
- ✅ Deployed to PC production successfully
- ✅ Documentation updated (CLAUDE.md, SPEED_TABLE_VIEWER.md)

### Production Validation
- ✅ CV modifications persist across page reloads
- ✅ Undo works in production
- ✅ Re-import syncs correctly
- ✅ No regressions in existing features (Test mode, Virtual mode, etc.)

---

## 10. Time Estimate

| Task | Time |
|------|------|
| Config refactoring (helpers + loaders) | 1-1.5h |
| DB schema + speed_table_helpers | 1h |
| Import script | 1h |
| API endpoints (3 new + 1 update) | 1h |
| Frontend UI (2 buttons) | 30min |
| Backend search/replace (old config refs) | 30min |
| Testing (unit + integration) | 1h |
| **Total** | **4-5 hours** |

---

## 11. Next Steps

**Immediate** (this change):
1. Implement components (script, helpers, endpoints, UI)
2. Test locally (Mac)
3. Deploy to PC
4. Run import script on PC
5. Validate production

**Future** (Step 2 - optional):
- CRUD locomotives via UI (add/edit/delete)
- Multi-level undo (extend snapshot history)
- CV history timeline (audit log visualization)
- Batch import/export (multiple locos)

---

## References

- **SPEED_TABLE_VIEWER.md** - Phase 1 & 2 features
- **CONFIG_REFACTOR.md** - Config structure evolution (2025-01-03)
- **CHANGELOG_ARCHIVE.md** - Historical changes
- **Z21_PROTOCOL.md** - POM operations mode details
