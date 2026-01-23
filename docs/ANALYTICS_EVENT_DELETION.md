# Event Deletion Feature (YOLO False Positive Cleanup)

**Status**: 📋 Planned (Future Implementation)
**Complexity**: ⭐⭐☆☆☆ (2/5 - BASSA-MEDIA)
**Estimated Time**: 4-5 hours (1-2 days with testing)
**Version Target**: v1.1.0

---

## Overview

**Problem**: YOLO tracking occasionally generates false positive detections that create outlier Δt events (e.g., single event with |Δt| > 3s without context). Currently these must be manually deleted via SQL.

**Solution**: Add click-to-delete functionality directly in the Analytics Δt Chart (Current view), allowing users to remove false positive events with a confirmation modal.

---

## User Flow

1. **Open Analytics** → Current view shows Δt chart with all events
2. **Hover over point** → Tooltip shows event details + "Click to delete" hint
3. **Click point** → Confirmation modal appears:
   ```
   Delete this event?

   Δt = -2.3s
   Time: 23 Jan 2026, 14:32:15
   Status: CRITICAL
   Speed: 88 (70%)

   [Cancel]  [Delete]
   ```
4. **Confirm delete** → Event removed from database + chart reloads
5. **Success feedback** → Toast notification "Event deleted"

---

## Technical Implementation

### 1. Frontend Changes (2-3 hours)

**File**: `web/src/components/DeltaTChart.jsx`

#### A. Make points clickable (Recharts CustomDot)

```jsx
const CustomDot = (props) => {
  const { cx, cy, payload, fill } = props;

  return (
    <circle
      cx={cx}
      cy={cy}
      r={4}
      fill={fill}
      style={{
        cursor: 'pointer',
        transition: 'r 0.2s'
      }}
      onMouseEnter={(e) => e.target.setAttribute('r', 6)}
      onMouseLeave={(e) => e.target.setAttribute('r', 4)}
      onClick={() => handleDeleteEvent(payload)}
    />
  );
};
```

#### B. Delete event handler

```jsx
const handleDeleteEvent = async (eventData) => {
  setEventToDelete(eventData);  // Open modal
};

const confirmDelete = async () => {
  try {
    const response = await fetch(`/api/analytics/events/${eventToDelete.id}`, {
      method: 'DELETE'
    });

    if (!response.ok) throw new Error('Delete failed');

    // Show success toast
    toast.success('Event deleted');

    // Reload chart data
    await loadAnalyticsData();

    setEventToDelete(null);  // Close modal
  } catch (error) {
    toast.error('Failed to delete event');
  }
};
```

#### C. Confirmation modal (Tailwind)

```jsx
{eventToDelete && (
  <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div className="bg-gray-800 rounded-lg p-6 max-w-sm w-full">
      <h3 className="text-xl font-bold text-white mb-4">Delete Event?</h3>

      <div className="space-y-2 mb-6 text-sm text-gray-300">
        <div>
          <span className="font-semibold">Δt:</span> {eventToDelete.delta_t.toFixed(2)}s
        </div>
        <div>
          <span className="font-semibold">Time:</span> {formatTimestamp(eventToDelete.timestamp)}
        </div>
        <div>
          <span className="font-semibold">Status:</span>
          <span className={getStatusColor(eventToDelete.status)}>
            {eventToDelete.status}
          </span>
        </div>
        {eventToDelete.speed && (
          <div>
            <span className="font-semibold">Speed:</span> {eventToDelete.speed} ({getSpeedPercent(eventToDelete.speed)}%)
          </div>
        )}
      </div>

      <p className="text-amber-400 text-xs mb-4">
        ⚠️ This action cannot be undone
      </p>

      <div className="flex gap-2">
        <button
          onClick={() => setEventToDelete(null)}
          className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
        >
          Cancel
        </button>
        <button
          onClick={confirmDelete}
          className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-500 rounded"
        >
          Delete
        </button>
      </div>
    </div>
  </div>
)}
```

#### D. Update tooltip (add hint)

```jsx
const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;

  const data = payload[0].payload;

  return (
    <div className="bg-gray-800 border border-gray-600 p-3 rounded shadow-lg">
      {/* Existing tooltip content */}

      <div className="mt-2 pt-2 border-t border-gray-600 text-xs text-gray-400">
        💡 Click point to delete
      </div>
    </div>
  );
};
```

---

### 2. Backend Changes (1 hour)

**File**: `backend/routers/analytics.py` (add new endpoint)

```python
from fastapi import HTTPException
from log_colors import log
from services.data_db import DataDB

@router.delete("/api/analytics/events/{event_id}")
async def delete_event(event_id: int):
    """
    Delete a single delta_t event (YOLO false positive cleanup).

    Validates:
    - Event exists
    - Event type is 'delta_t' (only delta_t events can be deleted)

    Side effects:
    - Session event_count updated (-1)
    - Session validation might be invalidated if this was the only delta_t event
    - Weighted recommendations recalculated on next Speed Table Viewer load
    - Fixed speeds detection might change

    Args:
        event_id: Event ID from events table (INTEGER PRIMARY KEY)

    Returns:
        {"success": True, "event_id": 123, "session_id": "20260123_143215"}

    Raises:
        404: Event not found
        400: Event is not delta_t type (cannot delete speed_setting, loco_operating_time, yolo_performance)
    """
    conn = DataDB.get_connection()
    cursor = conn.cursor()

    # Verify event exists and is delta_t
    cursor.execute('''
        SELECT event_type, session_id FROM events WHERE id = ?
    ''', (event_id,))

    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found")

    event_type, session_id = row

    if event_type != 'delta_t':
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Only delta_t events can be deleted (found: {event_type})"
        )

    # Delete event
    cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))

    # Update session event_count (-1)
    cursor.execute('''
        UPDATE sessions
        SET event_count = event_count - 1
        WHERE id = ?
    ''', (session_id,))

    # Check if session still has delta_t events (for validation)
    cursor.execute('''
        SELECT COUNT(*) FROM events
        WHERE session_id = ? AND event_type = 'delta_t'
    ''', (session_id,))

    remaining_delta_t = cursor.fetchone()[0]

    # If no more delta_t events, invalidate session
    if remaining_delta_t == 0:
        cursor.execute('''
            UPDATE sessions
            SET validated = 0
            WHERE id = ?
        ''', (session_id,))
        log('[ANALYTICS]', f"Session {session_id} invalidated (no delta_t events after deletion)")

    conn.commit()
    conn.close()

    log('[ANALYTICS]', f"Deleted event {event_id} (session: {session_id}, user action)")

    return {
        "success": True,
        "event_id": event_id,
        "session_id": session_id,
        "session_invalidated": remaining_delta_t == 0
    }
```

---

### 3. Database Schema (No Changes Required)

**Table**: `events`
- `id INTEGER PRIMARY KEY AUTOINCREMENT` ✅ Already indexed
- Event deletion is a simple `DELETE WHERE id = ?`
- No schema migration needed

**Side Effects**:
- `sessions.event_count` decremented (-1)
- `sessions.validated` set to 0 if no delta_t events remain
- Weighted recommendations recalculated on next Speed Table Viewer GET request
- Fixed speeds detection might change (if deleted event was in last session)

---

## Side Effects & Considerations

### A. Session Validation
- If deleted event was the **only delta_t event** in session → `validated = 0`
- Session still visible in Analytics but marked as invalid
- Speed Table Viewer ignores invalid sessions for recommendations

### B. Weighted Recommendations
- Recommendations are **recalculated on-demand** (GET `/api/speed-table/{consist_id}`)
- Deleting a CRITICAL event might:
  - Remove a recommendation (if CRITICAL count drops below threshold)
  - Move a speed into `fixed_speeds` (if remaining events are OK)
- **No manual refresh needed** - next Speed Table Viewer load sees updated data

### C. Fixed Speeds Detection
- Deleting an event from **last session** might affect `fixed_speeds` set
- Example: Had 4 events (3 OK, 1 CRITICAL = 25% CRITICAL rate) → not fixed
- Delete CRITICAL → now 3 events (3 OK, 0 CRITICAL = 0% rate) → becomes fixed ✅

### D. Analytics Charts
- **Current view**: Point disappears immediately after deletion + reload
- **Overview view**: Historical data resampled (LTTB algorithm recalculates)
- **Session stats**: event_count decremented, other metrics unchanged

---

## UX Considerations

### ✅ Advantages
- **One-click cleanup** for obvious YOLO false positives
- **Visual feedback** (point disappears, toast notification)
- **Confirmation modal** prevents accidental deletions
- **No SQL knowledge required** (user-friendly)

### ⚠️ Design Decisions

#### 1. Undo Support?
**Decision**: **NO** (Phase 1)
- Adds complexity (need undo history table or soft-delete flag)
- False positives are obvious (|Δt| > 3s, single event)
- Users can be cautious with confirmation modal
- **Future**: Could add soft-delete if users request it

#### 2. Batch Delete?
**Decision**: **NO** (Phase 1)
- Rare need (false positives are isolated, not in groups)
- Keeps UI simple (no checkbox selection state)
- **Future**: Could add if users need to clean multiple outliers

#### 3. Delete from Overview View?
**Decision**: **NO** (Current view only)
- Overview uses downsampled data (LTTB) → event IDs might not match visible points
- Current view shows all events → reliable mapping
- False positives are recent → users check Current view first

#### 4. Restrict to CRITICAL only?
**Decision**: **NO** (allow all delta_t events)
- Sometimes WARNING events are false positives too
- SYNCED events unlikely to be deleted (but allow flexibility)
- Backend validates event_type='delta_t' (safety check)

---

## Testing Checklist

### Frontend
- [ ] Click point → modal opens with correct event data
- [ ] Cancel → modal closes, point still visible
- [ ] Confirm delete → point disappears, toast shows success
- [ ] Chart reloads with updated data
- [ ] Hover → tooltip shows "Click to delete" hint
- [ ] Delete last event in session → session invalidated message

### Backend
- [ ] DELETE `/api/analytics/events/123` → event removed from database
- [ ] Verify event_type='delta_t' (reject speed_setting, loco_operating_time, etc.)
- [ ] Return 404 if event_id doesn't exist
- [ ] Return 400 if event_type not delta_t
- [ ] Update session event_count (-1)
- [ ] Invalidate session if no delta_t events remain
- [ ] Log deletion action with event_id and session_id

### Integration
- [ ] Speed Table Viewer recommendations update after deletion
- [ ] Fixed speeds detection works correctly after deletion
- [ ] Analytics Current view shows updated data
- [ ] Analytics Overview view resamples correctly
- [ ] Session list shows correct event_count
- [ ] Delete event from closed session (should still work)

---

## Alternative Approaches (Not Recommended)

### 1. Backend-only API (No UI)
**Pros**: Faster to implement (1 hour)
**Cons**: Requires browser console (`fetch()`), not user-friendly
**Decision**: Not sufficient for non-technical users

### 2. Bulk Delete Query (SQL filter)
**Example**: "Delete all delta_t events where |Δt| > 3.0s"
**Pros**: Clean many outliers at once
**Cons**: Risky (might delete legitimate events), harder UI
**Decision**: Too aggressive for Phase 1

### 3. Soft Delete (Flag instead of DELETE)
**Schema**: Add `deleted BOOLEAN DEFAULT 0` to events table
**Pros**: Allows undo, keeps data for audit
**Cons**: All queries need `WHERE deleted=0`, adds complexity
**Decision**: KISS principle - hard delete for Phase 1

---

## Future Enhancements (Post-v1.1.0)

### Phase 2: Advanced Features
- **Undo support** (soft-delete with `deleted` flag)
- **Batch delete** (select multiple points with checkboxes)
- **Delete from Overview view** (map downsampled points to original events)
- **Audit log** (track who deleted what, when)

### Phase 3: Smart Cleanup
- **Auto-detect outliers** (|Δt| > 3s with no speed context)
- **Bulk cleanup modal** ("Found 5 likely false positives - review & delete?")
- **ML confidence filter** ("Delete all events with YOLO confidence < 0.3?")

---

## Integration with Existing Code

### Files Modified
- ✅ `web/src/components/DeltaTChart.jsx` (frontend)
- ✅ `backend/routers/analytics.py` (backend endpoint)
- ✅ `docs/EVENT_DELETION_FEATURE.md` (this document)

### Files Unchanged
- ✅ `backend/services/data_db.py` (no new database methods needed)
- ✅ `docs/DATABASE_SCHEMA.md` (no schema changes)
- ✅ Speed Table Viewer (already recalculates on-demand)
- ✅ Analytics Dashboard (already reloads data after delete)

---

## Database Queries Reference

### Delete event (with validation)
```sql
-- Check event type before delete
SELECT event_type, session_id FROM events WHERE id = 123;

-- Delete event
DELETE FROM events WHERE id = 123;

-- Update session event_count
UPDATE sessions
SET event_count = event_count - 1
WHERE id = (SELECT session_id FROM events WHERE id = 123);

-- Check if session still has delta_t events
SELECT COUNT(*) FROM events
WHERE session_id = '20260123_143215'
  AND event_type = 'delta_t';

-- Invalidate session if no delta_t events
UPDATE sessions
SET validated = 0
WHERE id = '20260123_143215'
  AND (SELECT COUNT(*) FROM events WHERE session_id = '20260123_143215' AND event_type = 'delta_t') = 0;
```

### Find likely false positives (manual cleanup script)
```sql
-- Find outlier events (|Δt| > 3.0s without speed context)
SELECT
    id,
    session_id,
    datetime(timestamp, 'unixepoch', 'localtime') as time,
    json_extract(data, '$.delta_t') as delta_t,
    json_extract(data, '$.status') as status,
    json_extract(data, '$.speed') as speed
FROM events
WHERE event_type = 'delta_t'
  AND (json_extract(data, '$.delta_t') > 3.0
       OR json_extract(data, '$.delta_t') < -3.0)
  AND json_extract(data, '$.speed') IS NULL
ORDER BY timestamp DESC;
```

---

**End of EVENT_DELETION_FEATURE.md**
