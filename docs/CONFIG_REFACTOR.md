# config.json Structure Refactor

**Date**: 2025-01-03
**Status**: ✅ Completed
**Breaking Change**: Yes (no backward compatibility)

---

## Overview

Complete reorganization of `config.json` structure to improve clarity, reduce fragmentation, and establish a logical hierarchy.

---

## Problem Statement

The original `config.json` had grown organically with several issues:

1. **Illogical ordering**: `gates` at top (less important), `debug` at bottom (should be prioritized)
2. **Fragmentation**: `reference_locos` separated from `tracking_assignments` despite being conceptually part of consist configuration
3. **Inconsistent naming**: Mix of `_comment` and `notes` fields
4. **Confusing names**: `tracking_assignments` had become the de facto consist registry but name didn't reflect this
5. **Flat structure**: Related settings (fps, thresholds) not grouped semantically

---

## Solution: Hierarchical Structure

### New Structure

```json
{
  "debug": {
    "enabled": true,
    "notes": "Debug mode configuration"
  },

  "consists": {
    "10": {
      "name": "Consist 10 - Tracciato Interno",
      "lead_address": 1,
      "rear_address": 5,
      "gate_ids": [3, 4],
      "virtual_mode": true,
      "auto_compensation_enabled": true,
      "reference": {
        "loco": 5,
        "adjust": 1,
        "notes": "D645 014 (ESU) reference, Gr.675 017 adjust"
      },
      "notes": "Dual-gate timing. Lead=1 (sound), Rear=5 (reference)"
    },
    "11": { ... }
  },

  "gates": [
    {
      "id": 1,
      "name": "Bottom Right (vicino)",
      "center": [1227, 213],
      "width": 100,
      "height": 100,
      "angle": 0,
      "color": [255, 255, 0],
      "notes": "Consist 11 - GIALLO (RGB)"
    }
  ],

  "tracking": {
    "fps": {
      "active": 30,
      "idle": 1,
      "video_feed": 15,
      "notes": "YOLO tracking FPS and MJPEG stream FPS"
    },
    "timing_thresholds": {
      "normal": 1.0,
      "warning": 1.5,
      "max_delta_t": 15.0,
      "notes": "Δt thresholds in seconds"
    }
  }
}
```

### Design Principles

1. **Priority-based ordering**: Most important settings first (debug → consists → gates → tracking)
2. **Consolidation**: Related data grouped together (reference inside each consist)
3. **Semantic hierarchy**: Grouped settings under parent objects (tracking.fps, tracking.timing_thresholds)
4. **Consistent naming**: Use "notes" everywhere, eliminate `_comment`
5. **Rename for clarity**: `tracking_assignments` → `consists` (more accurate)

---

## Migration Details

### Path Changes

All code paths updated from old to new structure:

| Old Path | New Path |
|----------|----------|
| `config['tracking_assignments']` | `config['consists']` |
| `config['reference_locos'][id]` | `config['consists'][id]['reference']` |
| `config['timing_thresholds']` | `config['tracking']['timing_thresholds']` |
| `config['tracking_fps']` | `config['tracking']['fps']` |

### Files Modified

**Total: 7 files**

1. **config.json** - Structure reorganized
2. **backend/main.py** - All API endpoints updated
   - `lifespan()` startup config loading
   - `reload_roster_data()`
   - `build_consist_response()`
   - `GET /api/consists`
   - `POST /api/consists`
   - `PUT /api/consists/{address}`
   - `DELETE /api/consists/{address}`
3. **backend/roster_loader.py** - `load_consists_from_config()`
4. **backend/z21_manager.py** - `_load_persisted_state()` + `_save_persisted_state()`
5. **backend/tracking_daemon.py** - Config loading + reference_locos extraction
6. **backend/video_feed.py** - FPS loading
7. **scripts/track_consist_yolo.py** - Standalone script

### Code Examples

**Before:**
```python
# Load timing thresholds
thresholds = config.get('timing_thresholds', {'normal': 1.0, 'warning': 1.5})

# Load tracking assignments
tracking_assignments = config.get('tracking_assignments', {})

# Load reference locos (separate!)
reference_locos = config.get('reference_locos', {})
```

**After:**
```python
# Load timing thresholds (grouped under tracking)
tracking_config = config.get('tracking', {})
thresholds = tracking_config.get('timing_thresholds', {'normal': 1.0, 'warning': 1.5})

# Load consists (consolidated)
consists = config.get('consists', {})

# Extract reference locos from consists (integrated)
reference_locos = {}
for consist_addr, consist_info in consists.items():
    if 'reference' in consist_info:
        ref = consist_info['reference']
        reference_locos[consist_addr] = {
            'reference': ref.get('loco'),
            'adjust': ref.get('adjust')
        }
```

---

## Backward Compatibility

**Decision**: NO backward compatibility implemented.

**Rationale**:
- `config.json` is version controlled in git
- Config is synced to production PC automatically
- Single source of truth makes migration atomic (one file change)
- No migration logic needed = simpler codebase

**Impact**:
- ✅ Backend restart required after update
- ✅ All instances (Mac + PC) get new structure via git pull
- ⚠️ Old config.json format will cause startup errors (intentional - forces update)

---

## Benefits

### 1. Improved Maintainability
- ✅ Logical ordering makes it easier to find settings
- ✅ Grouped settings reduce cognitive load
- ✅ Consistent naming eliminates confusion

### 2. Reduced Fragmentation
- ✅ All consist data in one place (lead, rear, gates, reference, virtual_mode)
- ✅ No need to cross-reference multiple sections
- ✅ Easier to add new consists via Consist Manager UI

### 3. Better Extensibility
- ✅ Adding new tracking parameters: put under `tracking`
- ✅ Adding new consist fields: add to `consists[id]`
- ✅ Clear separation of concerns

### 4. Cleaner Code
- ✅ Fewer dict.get() chains in code
- ✅ More semantic variable names (consists vs tracking_assignments)
- ✅ Easier to understand code intent

---

## Testing Checklist

- [x] config.json syntax valid (JSON)
- [x] Backend startup successful
- [ ] Consist Manager UI loads correctly
- [ ] CRUD operations work (create/edit/delete consist)
- [ ] Virtual Mode toggle persists
- [ ] Auto Compensation toggle persists
- [ ] Tracking daemon loads config correctly
- [ ] Video feed loads FPS settings
- [ ] Standalone script (track_consist_yolo.py) works

---

## Rollback Plan

If issues arise:

1. **Revert config.json**:
   ```bash
   git checkout HEAD~1 config.json
   ```

2. **Revert code changes**:
   ```bash
   git revert <commit-hash>
   ```

3. **Alternative**: Keep new structure, restore old data manually
   - Use git history to view old values
   - Manually restructure into new format

---

## Future Considerations

### Potential Split (Future Refactor)

Consider splitting config into two files:

1. **config.json** - Static configuration (gates, thresholds, camera)
   - Safe for manual editing
   - Version controlled
   - Deployment-specific values

2. **state.json** - Runtime state (virtual_mode, auto_compensation_enabled)
   - Updated by application
   - Not version controlled (gitignored)
   - Instance-specific state

**Benefits**:
- Cleaner separation of concerns
- Safer manual editing (no risk of overwriting runtime state)
- Easier to reset state without touching config

**Trade-offs**:
- More complex state management
- Two files to maintain
- More code to handle file I/O

**Decision**: Keep consolidated for now, revisit if state management becomes complex.

---

## References

- **Commit**: TBD (pending commit)
- **Related Issues**: None
- **Discussion**: User request for config reorganization (2025-01-03)
