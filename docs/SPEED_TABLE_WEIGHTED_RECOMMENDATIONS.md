# Speed Table Weighted Recommendations

**Status**: 🚧 In Development (2026-01-20)
**Related**: SPEED_TABLE_VIEWER.md, DATABASE_SCHEMA.md, ANALYTICS.md

---

## Problem Statement

### Current Algorithm Issues

**Backend**: `backend/services/data_db.py:627-736` (`get_critical_events_by_speed()`)

**Current behavior** (all events weighted equally):
```sql
-- Count CRITICAL/WARNING per speed (ALL historical sessions)
SELECT speed, status, COUNT(*)
FROM events
WHERE consist_id = ? AND status IN ('CRITICAL', 'WARNING')
GROUP BY speed, status

-- Mean delta_t per speed (ALL events, all time)
SELECT speed, AVG(delta_t)
FROM events
WHERE consist_id = ?
GROUP BY speed
```

**Problems identified**:
1. ❌ **All events have equal weight** (event from 2 months ago = event from today)
2. ❌ **Does not detect speed table modifications** (if CV already corrected, still uses old data)
3. ❌ **Current session ignored** (even with 50 CRITICAL events today, uses cumulative history)
4. ⚠️ **"Fixed speeds" detection helps but insufficient** (only last session tested for that speed)

**Real-world example (Consist 11 - Loco 7 Hornby TXS)**:
- **Past (50 sessions)**: 100 CRITICAL events (too fast, delta_t < 0) → "slow down"
- **Present (current session)**: 20 CRITICAL events (too slow, delta_t > 0) → "speed up"
- **Cumulative mean delta_t**: Still negative → **recommends slowing down more!** ❌

---

## Solution: Weighted Recommendations Algorithm

### Design Goals

1. **Prioritize recent data** over historical data
2. **Detect CV modifications** and reset history for modified speeds
3. **Current session priority** when enough data available
4. **Configurable thresholds** per consist (symmetric vs asymmetric gates)
5. **Debug visibility** when debug mode enabled

---

## Algorithm Design

### Two-Stage Weighting System

```
Stage 1: Session Segmentation
  ↓ Current session vs Historical (last 5 sessions)

Stage 2: Weighted Averaging
  ↓ IF current >= threshold: 80% current + 20% historical
  ↓ ELSE: 20% current + 80% historical
```

**Note on CV Modification Filter** (removed 2026-01-21):
- **Original design**: Filter events by `timestamp >= cv_last_modified` per speed
- **Problem**: `last_modified` is per-locomotive (not per-CV), so modifying one CV invalidated ALL speeds
- **Solution**: Removed filter entirely - weighted logic (80/20) + last 5 sessions already sufficient to handle corrections

### Formula

**Weighted mean delta_t**:
```
IF current_session_events >= threshold:
    weight_current = 0.8  # WEIGHT_CURRENT_HIGH
    weight_historical = 0.2
ELSE:
    weight_current = 0.2  # WEIGHT_CURRENT_LOW
    weight_historical = 0.8

weighted_mean = (mean_current * weight_current) + (mean_historical * weight_historical)
```

**CRITICAL count** (similar weighting):
```
weighted_critical_count = (count_current * weight_current) + (count_historical * weight_historical)
```

---

## Configuration

### config.json - Per-Consist Thresholds

```json
{
  "consists": {
    "10": {
      "name": "C10 Interno",
      "recommendation_threshold": 5,  // NEW: Asymmetric gates (longer track, fewer crossings)
      "gate_assignment": {
        "reference": 3,
        "adjust": 4
      },
      ...
    },
    "11": {
      "name": "C11 Esterno",
      "recommendation_threshold": 10,  // NEW: Symmetric gates (more crossings per lap)
      "gate_assignment": null,
      ...
    }
  }
}
```

**Rationale**:
- **Symmetric gates** (Consist 11): 2 crossings per lap (both directions valid) → more events → higher threshold (10-15)
- **Asymmetric gates** (Consist 10): 1 crossing per lap (only one direction valid) → fewer events → lower threshold (5)
- **Track length**: Longer track = longer lap time = fewer events per session → lower threshold

**UI Editor**: Can be edited via **Consist Manager** (⚙️ button) → Edit Consist → "Recommendation Threshold (Advanced)" field (no need to manually edit config.json)

---

## Implementation Details

### Backend Changes

#### 1. Modified Query Strategy

**File**: `backend/services/data_db.py:627` (`get_critical_events_by_speed()`)

**New parameters**:
```python
def get_critical_events_by_speed(
    consist_id: int,
    current_session_id: Optional[int] = None,  # NEW
    recommendation_threshold: int = 10         # NEW (from config)
) -> Dict[str, Any]:
```

**Query structure**:
```sql
-- Step 1: Get current session events per speed
SELECT speed, COUNT(*), AVG(delta_t), SUM(CASE WHEN status='CRITICAL' THEN 1 ELSE 0 END)
FROM events
WHERE consist_id = ?
  AND session_id = ?
GROUP BY speed

-- Step 2: Get historical events (last 5 sessions, excluding current)
SELECT speed, COUNT(*), AVG(delta_t), SUM(CASE WHEN status='CRITICAL' THEN 1 ELSE 0 END)
FROM events
WHERE consist_id = ?
  AND session_id IN (
    SELECT DISTINCT session_id FROM events
    WHERE consist_id = ? AND session_id != ?
    ORDER BY session_id DESC LIMIT 5  -- session_id format YYYYMMDD_HHMMSS is sortable
  )
GROUP BY speed

-- Step 3: Combine with weighting (Python logic)
```

**Return structure**:
```python
{
    'critical': {speed: weighted_count},
    'warning': {speed: weighted_count},
    'mean_delta_t': {speed: weighted_mean},
    'fixed_speeds': {speed, ...},
    'debug_info': {  # Always present (used for UI breakdown)
        speed: {
            'current_session': {
                'count': 12,
                'mean_delta_t': 1.5,
                'critical_count': 8,
                'weight': 0.7
            },
            'historical': {
                'count': 45,
                'mean_delta_t': -0.3,
                'critical_count': 20,
                'weight': 0.3,
                'session_ids': [123, 122, 121, 120, 119]
            },
            'weighted_result': {
                'mean_delta_t': 0.96,  # (1.5*0.7) + (-0.3*0.3)
                'critical_count': 11.6,  # (8*0.7) + (20*0.3)
                'meets_threshold': True,  # current_count >= 10
                'cv_last_modified': '2026-01-15T10:30:00Z'
            }
        },
        ...
    }
}
```

#### 2. Config Loading

**File**: `backend/routers/speed_table.py:116`

```python
# Load consist config for recommendation_threshold
consist_config = config.get('consists', {}).get(str(consist_id), {})
recommendation_threshold = consist_config.get('recommendation_threshold', 10)  # Default 10

# Get current session ID
current_session = DataDB.get_current_session(consist_id)
session_id = current_session['id'] if current_session else None

# Call with new parameters
events_by_status = DataDB.get_critical_events_by_speed(
    consist_id=consist_id,
    current_session_id=session_id,
    recommendation_threshold=recommendation_threshold
)
```

#### 3. API Response

**File**: `backend/routers/speed_table.py:135`

```python
return {
    'consist_id': consist_id,
    'adjust_loco_address': adjust_loco_address,
    'session_id': session_id,
    'cv_values': cv_values,
    'critical_events': critical_events,
    'warning_events': warning_events,
    'recommendations': recommendations,
    'fixed_count': len(fixed_speeds),
    'debug_info': events_by_status.get('debug_info', {})  # NEW
}
```

---

### Frontend Changes

#### Weighted Breakdown in Recommendations

**File**: `web/src/components/charts/SpeedTableViewer.jsx`

**Location**: Inline under each recommendation (always visible, compact format)

**Design** (expand existing recommendation display):
```jsx
{/* Existing recommendation display (lines 920-944) */}
<div className="flex items-center gap-4 text-xs">
  <span className={`font-mono ${rec.mean_delta_t < 0 ? 'text-blue-400' : 'text-amber-400'}`}>
    Δt {rec.mean_delta_t >= 0 ? '+' : ''}{rec.mean_delta_t.toFixed(2)}s
  </span>
  <span className="text-red-400">
    {rec.critical_count} critical
  </span>
  {rec.warning_count > 0 && (
    <span className="text-amber-400">
      {rec.warning_count} warning
    </span>
  )}
  <span className="text-slate-500">
    Speed {rec.speed}
  </span>
</div>

{/* NEW: Weighted breakdown (always visible, compact) */}
{rec.debug_info && (
  <div className="mt-1 pl-4 text-xs text-slate-400 flex items-center gap-4">
    <span>
      ┗━ Current: {rec.debug_info.current_session.count} events,
      Δt {rec.debug_info.current_session.mean_delta_t >= 0 ? '+' : ''}{rec.debug_info.current_session.mean_delta_t.toFixed(2)}s
      ({Math.round(rec.debug_info.current_session.weight * 100)}%)
    </span>
    <span>
      | Historical: {rec.debug_info.historical.count} events,
      Δt {rec.debug_info.historical.mean_delta_t >= 0 ? '+' : ''}{rec.debug_info.historical.mean_delta_t.toFixed(2)}s
      ({Math.round(rec.debug_info.historical.weight * 100)}%)
    </span>
  </div>
)}
```

**Example output**:
```
CV86 = 128 → 130 (+2)
Δt +0.96s   12 critical   5 warning   Speed 88
┗━ Current: 12 events, Δt +1.5s (70%) | Historical: 45 events, Δt -0.3s (30%)
```

**Always visible**: No `config.debug.enabled` check needed (compact enough to show always)

---

## Testing Strategy

### Test Cases

1. **Cold start** (no current session):
   - Should use 100% historical data
   - Verify recommendations match old algorithm

2. **Current session < threshold** (e.g., 3 events, threshold 10):
   - Should use 30% current + 70% historical
   - Verify weighted mean makes sense

3. **Current session >= threshold** (e.g., 12 events, threshold 10):
   - Should use 70% current + 30% historical
   - Verify recommendation flips if current contradicts history

4. **CV modified recently**:
   - Should ignore events before `last_modified` timestamp
   - Test by writing CV, then checking recommendations

5. **Symmetric vs Asymmetric**:
   - Consist 11 (threshold 10): Test with 12+ events
   - Consist 10 (threshold 5): Test with 6+ events

### Weighted Breakdown Verification

- Open Speed Table Viewer
- Run session with 10+ events at specific speed
- Verify breakdown shows below each recommendation:
  - Current session: count, mean delta_t, weight percentage
  - Historical: count, mean delta_t, weight percentage
  - Verify weighted result matches expectation
- Compare recommendation with old algorithm (sanity check)

---

## Migration Notes

### Backward Compatibility

- If `recommendation_threshold` missing in config: **default to 10** (safe fallback)
- Old sessions still work (historical queries unchanged)
- Frontend gracefully handles missing `debug_info` (just doesn't render panel)

### Data Cleanup

**Not required** - algorithm works with existing data.

Optional: Clean old outlier events (manual, not automated):
```sql
DELETE FROM events
WHERE event_type='delta_t'
  AND (json_extract(data, '$.delta_t') > 10.0 OR json_extract(data, '$.delta_t') < -10.0);
```

---

## Future Enhancements

### Phase 2 Ideas (Not Planned)

1. **Exponential time decay**: Events decay over days (not just session window)
   - Formula: `weight = exp(-days_ago / 7.0)`

2. **Confidence intervals**: Show recommendation confidence
   - High confidence: 50+ events, low variance
   - Low confidence: 5 events, high variance

3. **Automatic threshold tuning**: Learn optimal threshold per consist
   - Track recommendation accuracy over time
   - Adjust threshold to maximize accuracy

4. **Multi-speed smoothing**: Adjacent CV recommendations affect each other
   - If CV70 recommended -2, maybe CV71 should be -1 (gradual curve)

---

## Implementation Checklist

### Backend
- [x] Add `recommendation_threshold` to config.json (consist 10: 5, consist 11: 10)
- [x] Refactor `get_critical_events_by_speed()` with new parameters
- [x] Implement CV modification timestamp filtering
- [x] Implement current/historical session splitting (last 5 sessions)
- [x] Implement weighted averaging logic
- [x] Add debug_info to return structure (always calculated)
- [x] Pass `recommendation_threshold` from router
- [x] Update API response to include `debug_info`
- [x] Update `calculate_cv_recommendations()` to attach debug_info to each recommendation
- [x] Use validated sessions only (ignore non-validated current session)
- [x] Populate debug_info for ALL tested speeds (not just CRITICAL/WARNING)

### Frontend
- [x] Parse `debug_info` from recommendations array
- [x] Add weighted breakdown inline under each recommendation (always visible)
- [x] Display current/historical/weighted breakdown per recommendation
- [x] Format: compact single line with ┗━ prefix
- [x] **NEW**: Speed Analysis Debug panel (full breakdown, debug mode only)

### Debug Panel (2026-01-21)
- [x] Collapsible panel above speed table (open by default)
- [x] Shows ALL tested speeds (not just recommendations)
- [x] Current/Historical/Weighted stats per speed
- [x] Visible only when `debug.enabled=true` (config.local.json)
- [x] Purple theme (distinct from other sections)

### Testing
- [ ] Test consist 11 with 10+ events (symmetric, threshold 10)
- [ ] Test consist 10 with 5+ events (asymmetric, threshold 5)
- [ ] Test CV write invalidation (write CV, verify old events ignored)
- [ ] Verify breakdown line appears below each recommendation
- [ ] Compare recommendations old vs new algorithm (sanity check)

### Documentation
- [x] Update SPEED_TABLE_VIEWER.md (reference this doc)
- [x] Update CLAUDE.md changelog
- [x] z21-deployment skill (database debugging pattern)

---

## Performance Considerations

### Query Complexity

**Old algorithm**: 2 queries (all-time aggregates)
**New algorithm**: 3-4 queries (session-based + CV timestamps)

**Estimated impact**: +20-30ms per Speed Table Viewer load (negligible)

### Database Indexes

**Already optimized**:
- `events.session_id` indexed
- `events.consist_id` indexed
- `events.timestamp` indexed

**No new indexes needed**.

---

**Last Updated**: 2026-01-20
