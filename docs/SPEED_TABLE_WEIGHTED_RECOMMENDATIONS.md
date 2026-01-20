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

### Three-Stage Weighting System

```
Stage 1: CV Modification Detection
  ↓ Filter events after last CV write for each speed

Stage 2: Session Segmentation
  ↓ Current session vs Historical (last 5 sessions)

Stage 3: Weighted Averaging
  ↓ IF current >= threshold: 70% current + 30% historical
  ↓ ELSE: 30% current + 70% historical
```

### Formula

**Weighted mean delta_t**:
```
IF current_session_events >= threshold:
    weight_current = 0.7
    weight_historical = 0.3
ELSE:
    weight_current = 0.3
    weight_historical = 0.7

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
    recommendation_threshold: int = 10,        # NEW (from config)
    debug: bool = False                        # NEW (from config.debug.enabled)
) -> Dict[str, Any]:
```

**Query structure**:
```sql
-- Step 1: Get CV modification timestamps
SELECT address, step, last_modified
FROM locomotive_speed_table
WHERE address = ?

-- Step 2: Get current session events per speed
SELECT speed, COUNT(*), AVG(delta_t), SUM(CASE WHEN status='CRITICAL' THEN 1 ELSE 0 END)
FROM events
WHERE consist_id = ?
  AND session_id = ?
  AND timestamp >= cv_last_modified  -- Filter by CV modification
GROUP BY speed

-- Step 3: Get historical events (last 5 sessions, excluding current)
SELECT speed, COUNT(*), AVG(delta_t), SUM(CASE WHEN status='CRITICAL' THEN 1 ELSE 0 END)
FROM events
WHERE consist_id = ?
  AND session_id IN (
    SELECT DISTINCT session_id FROM events
    WHERE consist_id = ? AND session_id != ?
    ORDER BY timestamp DESC LIMIT 5
  )
  AND timestamp >= cv_last_modified
GROUP BY speed

-- Step 4: Combine with weighting (Python logic)
```

**Return structure**:
```python
{
    'critical': {speed: weighted_count},
    'warning': {speed: weighted_count},
    'mean_delta_t': {speed: weighted_mean},
    'fixed_speeds': {speed, ...},
    'debug_info': {  # Only if debug=True
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
debug_enabled = config.get('debug', {}).get('enabled', False)

# Get current session ID
current_session = DataDB.get_current_session(consist_id)
session_id = current_session['id'] if current_session else None

# Call with new parameters
events_by_status = DataDB.get_critical_events_by_speed(
    consist_id=consist_id,
    current_session_id=session_id,
    recommendation_threshold=recommendation_threshold,
    debug=debug_enabled
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

#### Debug Panel in SpeedTableViewer

**File**: `web/src/components/SpeedTableViewer.jsx`

**Location**: Below recommendations panel, only visible if `config.debug.enabled = true`

**Design**:
```jsx
{debugInfo && Object.keys(debugInfo).length > 0 && (
  <div className="mt-4 p-4 bg-pink-500/10 border border-pink-500/30 rounded">
    <h4 className="text-sm font-semibold text-pink-200 mb-3 flex items-center gap-2">
      <i className="fa-solid fa-bug"></i>
      Debug: Weighted Recommendations
    </h4>

    {Object.entries(debugInfo).map(([speed, info]) => (
      <div key={speed} className="mb-3 p-3 bg-slate-900/50 rounded text-xs">
        <div className="font-medium text-white mb-2">Speed {speed}%</div>

        {/* Current Session */}
        <div className="mb-2">
          <span className="text-green-400">Current Session:</span>
          <span className="ml-2">{info.current_session.count} events</span>
          <span className="ml-2">Δt: {info.current_session.mean_delta_t.toFixed(3)}s</span>
          <span className="ml-2">CRITICAL: {info.current_session.critical_count}</span>
          <span className="ml-2 text-slate-400">(weight: {info.current_session.weight})</span>
        </div>

        {/* Historical */}
        <div className="mb-2">
          <span className="text-blue-400">Historical (5 sessions):</span>
          <span className="ml-2">{info.historical.count} events</span>
          <span className="ml-2">Δt: {info.historical.mean_delta_t.toFixed(3)}s</span>
          <span className="ml-2">CRITICAL: {info.historical.critical_count}</span>
          <span className="ml-2 text-slate-400">(weight: {info.historical.weight})</span>
        </div>

        {/* Weighted Result */}
        <div className="pt-2 border-t border-slate-700">
          <span className="text-signal-amber">Weighted Result:</span>
          <span className="ml-2 font-medium">Δt: {info.weighted_result.mean_delta_t.toFixed(3)}s</span>
          <span className="ml-2">CRITICAL: {info.weighted_result.critical_count.toFixed(1)}</span>
          {info.weighted_result.meets_threshold && (
            <span className="ml-2 text-green-400">✓ Threshold met</span>
          )}
        </div>

        {info.weighted_result.cv_last_modified && (
          <div className="mt-1 text-slate-400">
            Last CV write: {new Date(info.weighted_result.cv_last_modified).toLocaleString()}
          </div>
        )}
      </div>
    ))}
  </div>
)}
```

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

### Debug Verification

With `config.debug.enabled = true`:
- Open Speed Table Viewer
- Run session with 10+ events at specific speed
- Verify debug panel shows:
  - Current session: high weight (0.7)
  - Historical: low weight (0.3)
  - Weighted result matches expectation

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
- [ ] Add `recommendation_threshold` to config.json (consist 10: 5, consist 11: 10)
- [ ] Refactor `get_critical_events_by_speed()` with new parameters
- [ ] Implement CV modification timestamp filtering
- [ ] Implement current/historical session splitting (last 5 sessions)
- [ ] Implement weighted averaging logic
- [ ] Add debug_info to return structure
- [ ] Pass `recommendation_threshold` and `debug` from router
- [ ] Update API response to include `debug_info`

### Frontend
- [ ] Parse `debug_info` from API response
- [ ] Implement debug panel UI (collapsible, pink theme)
- [ ] Conditional rendering based on `config.debug.enabled`
- [ ] Display current/historical/weighted breakdown per speed

### Testing
- [ ] Test consist 11 with 10+ events (symmetric, threshold 10)
- [ ] Test consist 10 with 5+ events (asymmetric, threshold 5)
- [ ] Test CV write invalidation (write CV, verify old events ignored)
- [ ] Test debug panel visibility (debug on/off)
- [ ] Compare recommendations old vs new algorithm (sanity check)

### Documentation
- [ ] Update SPEED_TABLE_VIEWER.md (reference this doc)
- [ ] Update CLAUDE.md changelog
- [ ] Update FUTURE_IDEAS.md (if applicable)

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
