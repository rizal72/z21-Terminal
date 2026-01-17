# Locomotive Synchronization: Mac ↔ PC

**Status**: 📋 DOCUMENTED - Not Yet Implemented
**Priority**: LOW (current manual workaround acceptable for rare operations)
**Date**: 2025-01-17

---

## Problem Statement

**Core Issue**: Adding new locomotives requires manual coordination between Mac (JMRI) and PC (production)

**Mac Environment**:
- ✅ Has JMRI DecoderPro (programming track setup)
- ✅ Has JMRI roster XML files (locomotive definitions)
- ❌ No `analytics.db` (production DB only on PC)

**PC Environment**:
- ✅ Has `analytics.db` (locomotive_speed_table with CV67-94)
- ❌ No JMRI (roster XML manually copied from Mac)
- ✅ Production deployment

**Workflow Breakdown**:
1. **Mac**: Setup new loco with JMRI → roster XML created
2. **Manual Copy**: Roster XML Mac → PC (error-prone)
3. **PC**: Run import script → writes CV to analytics.db
4. **Result**: New loco available in z21-Terminal

**Why This Is a Problem**:
- ❌ Manual file copying (friction, error-prone)
- ❌ Can't test import script on Mac (no analytics.db)
- ❌ CV modifications via web UI not synced Mac ↔ PC
- ❌ DB in gitignore → no git sync possible
- ❌ Architecture issue: CV (configuration) mixed with analytics (runtime) in same DB

---

## Current Workaround

**For Adding New Locomotives**:

1. **Mac** (has JMRI roster XML):
   - Setup locomotive with JMRI DecoderPro (programming track)
   - Create roster entry with CV configuration

2. **Manual Roster Copy** (temporary solution):
   - Copy JMRI roster XML files from Mac to PC
   - `~/Library/Preferences/JMRI/.../roster/*.xml` → PC equivalent path

3. **Run Import Script on PC**:
   ```bash
   # PC (has analytics.db)
   python scripts\utils\import_speed_tables_from_jmri.py
   ```
   - Reads JMRI roster XML (copied from Mac)
   - Writes CV67-94 to `analytics.db`
   - Updates `config.json` locomotive metadata

**Problems**:
- ❌ Manual file copying (error-prone)
- ❌ Can't test import script on Mac (no analytics.db)
- ❌ PC and Mac DB always out of sync
- ❌ CV modifications via web UI not synced across machines

---

## Proposed Solution: CV Speed Table in config.json

**Move CV67-94 from DB to config.json**:

```json
{
  "locomotives": {
    "1": {
      "name": "Gr.675 017",
      "decoder": "LokSound V4.0",
      "color": "#FFFF00",
      "cv_profiles": {
        "normal": {"cv3": 78, "cv4": 58},
        "testing": {"cv3": 0, "cv4": 0}
      },
      "cv_speed_table": {
        "67": 10,
        "68": 15,
        "69": 20,
        ...
        "94": 255
      }
    }
  }
}
```

### Benefits

1. **Git Sync** ✅:
   - `config.json` in git → CV changes synced Mac ↔ PC
   - `git pull` receives CV modifications immediately

2. **Architecture Clean** ✅:
   - Configuration in config files (git tracked)
   - Analytics in database (gitignored, runtime)

3. **Mac Testing** ✅:
   - Import script works on Mac (no DB dependency)
   - Test modifications locally before PC deployment

4. **JMRI Independence** ✅:
   - Import script runs on Mac (where JMRI lives)
   - PC receives via git (no JMRI dependency)

5. **Backup with Git** ✅:
   - CV history tracked in git commits
   - Easy rollback to previous values

---

## Implementation Plan

### Phase 1: Backend Refactor

**1. Update `speed_table_helpers.py`**:

```python
# BEFORE (v1.0.0)
def read_cv_speed_table_from_db(loco_address):
    """Read CV67-94 from analytics.db"""
    conn = sqlite3.connect('data/analytics.db')
    # ...

# AFTER
def read_cv_speed_table_from_config(loco_address):
    """Read CV67-94 from config.json"""
    config = load_config()
    locomotives = config.get('locomotives', {})
    loco = locomotives.get(str(loco_address), {})
    return loco.get('cv_speed_table', None)

def write_cv_speed_table_to_config(loco_address, cv_values):
    """Write CV67-94 to config.json"""
    config = load_config()
    locomotives = config.get('locomotives', {})

    if str(loco_address) not in locomotives:
        locomotives[str(loco_address)] = {}

    locomotives[str(loco_address)]['cv_speed_table'] = cv_values
    config['locomotives'] = locomotives
    save_config(config)
```

**2. Undo Implementation**:

**Option A**: Separate history file (recommended)
```json
// cv_history.json (gitignored)
{
  "1": {
    "previous": {67: 10, 68: 15, ...},
    "timestamp": "2025-01-17T12:00:00",
    "source": "web_ui"
  }
}
```

**Option B**: Git-based undo
```bash
# Undo = revert config.json to previous commit
git diff HEAD~1 config.json | grep cv_speed_table
```

### Phase 2: Import Script Update

```python
def import_to_config(locos):
    """Import locomotive data including CV speed table"""
    config = load_config()

    for loco in locos:
        config['locomotives'][str(loco.address)] = {
            'name': loco.name,
            'decoder': loco.decoder_model,
            'color': get_color(loco.address),
            'cv_profiles': get_cv_profiles(loco.address),
            'cv_speed_table': {
                str(67 + i): loco.cv_speed_table[67 + i]
                for i in range(28)
            }
        }

    save_config(config)
```

### Phase 3: Database Cleanup

**Remove from analytics.db**:
- Drop `locomotive_speed_table` table
- Keep pure analytics tables (sessions, events, stats)

### Phase 4: Migration Script

```python
# scripts/utils/migrate_cv_to_config.py
"""
One-time migration: analytics.db → config.json

Reads locomotive_speed_table from DB and writes to config.json
Run once during upgrade to v1.1.0
"""

def migrate_cv_to_config():
    # Read all CV from DB
    # Write to config.json
    # Backup old DB
    # Drop locomotive_speed_table table
```

---

## Estimated Effort

**Implementation**: ~4-5 hours
- Backend refactor: 2 hours
- Import script update: 1 hour
- Migration script: 1 hour
- Testing: 1 hour

**Risk**: LOW (self-contained change, well-defined scope)

---

## When to Implement

**Triggers**:
- ✅ When adding new locomotive to roster (current workaround too manual)
- ✅ When user requests Mac/PC CV sync
- ✅ When time permits (not urgent, current system works)

**Not Urgent Because**:
- v1.0.0 implementation works correctly
- No immediate need to add new locomotives
- Manual workaround acceptable for rare operations

---

## Current Workaround for Adding Locomotives

**Until refactor is implemented**:

1. **Mac**: Setup with JMRI DecoderPro
2. **Mac**: Manually copy JMRI roster XML to PC
3. **PC**: Run import script
4. **PC**: Verify in web dashboard

**Pain Points**:
- Manual file copying
- Can't test on Mac
- CV edits not synced

---

## Related Issues

**JMRI Independence Roadmap**:
- ✅ CV67-94 management (implemented, but wrong storage location)
- ✅ CV19 consist management (Virtual/DCC Mode)
- ✅ Locomotive metadata (config.json)
- ❌ Function labels F0-F28 (still from JMRI roster XML)

**See**: `docs/JMRI_INTEGRATION.md` for complete independence status

---

## Conclusion

**Current State**: CV in DB works but violates architecture principles
**Desired State**: CV in config.json for proper separation of concerns
**Action**: Document now, implement when adding next locomotive or when convenient

**Decision**: Defer implementation until triggered by operational need. Current workaround acceptable for rare operations.
