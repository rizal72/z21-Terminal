# Analytics Dashboard

**Status**: ✅ **IMPLEMENTED** (2025-01-12)
**Location**: `backend/analytics_logger.py`, `web/src/components/AnalyticsPanel.jsx`

---

## Overview

SQLite-based async event logging for locomotive tracking performance analysis. Session-based data collection with zero impact on real-time YOLO tracking.

**Key Features**:
- **Two views**: Current Session + Cumulative History (all sessions)
- **Consist filtering**: Color-coded multi-line charts (magenta C10, blue C11)
- **Time-series charts**: Horizontal scroll navigation (60px/event)
- **Session validation**: Discards brief movements, keeps only coordinated operations
- **Keyboard shortcuts**: A key to toggle analytics panel (desktop only)

---

## Architecture

### Data Flow

```
YOLO Tracking → Gate Crossing Detected → Analytics Logger (async)
                                              ↓
                                         Buffer (100 events)
                                              ↓
                                         Flush (10s) → SQLite
                                              ↓
                                         Frontend (on-demand load)
```

### Session Lifecycle (VERIFIED BEHAVIOR - 2025-01-13)

**Session Creation**:
1. **Backend startup** → TrackingManager created (daemon NOT started yet)
2. **First WebSocket client connects** (`/ws`) → `tracking_manager.on_client_connected()` called
3. **TrackingDaemon starts** → `daemon.run()` executes
4. **AnalyticsLogger created** → **NEW SESSION CREATED**
   - Session ID format: `20260113_003045` (YYYYMMDD_HHMMSS)
   - Session starts with `validated=0` (not yet valid)
   - DB record created immediately in `sessions` table

**Code Evidence**:
- `tracking_manager.py:72` - `self.daemon = TrackingDaemon()` created
- `tracking_daemon.py:383` - `self.analytics_logger = AnalyticsLogger()` created
- `analytics_logger.py:40` - `self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')`

**Session Validation**:
- **First Δt calculation** → Session becomes `validated=1`
- Requires both locomotives of consist to pass gates (coordinated operation)
- Invalid sessions (no Δt, brief movements) **deleted on daemon stop** (not kept in DB)

**Code Evidence**:
- `analytics_logger.py:170-177` - `close_session()` deletes if `not session_validated`

**Session End** (✅ FULLY IMPLEMENTED):
- ✅ Session **CLOSES when last WebSocket client disconnects**
- ✅ TrackingManager detects `len(connected_clients) == 0` → calls `stop_tracking()`
- ✅ Daemon shutdown → `analytics_logger.close_session()` called in finally block
- ✅ If validated: saves session with `end_time` in DB
- ✅ If NOT validated: **deletes session + all events** (purged completely)

**Code Evidence**:
- `main.py:1462-1467` - Client disconnect removes from `connected_clients` list
- `tracking_manager.py:126-128` - `if len(self.connected_clients) == 0` → stop daemon
- `tracking_daemon.py:455-460` - finally block calls `close_session()`
- `analytics_logger.py:170-177` - Delete or save based on `session_validated`

**Page Refresh Behavior** (✅ DETERMINISTIC since 2025-01-13):
- **Implementation**: `navigator.sendBeacon('/api/close-session')` on `beforeunload` event
- **Flow**:
  1. User refreshes page → `beforeunload` fires
  2. `sendBeacon` sends POST (reliable even during page close)
  3. Backend receives POST → calls `tracking_manager.stop_tracking()`
  4. **Daemon STOPS** → session closes (end_time set or deleted if invalid)
  5. Browser reloads → new WebSocket connects
  6. Backend starts NEW daemon → NEW AnalyticsLogger → **NEW SESSION**
- **Result**: **Every page refresh = NEW session (100% deterministic)**

**Code Evidence**:
- `App.jsx:769-779` - beforeunload listener with sendBeacon
- `main.py:1121-1137` - POST `/api/close-session` endpoint
- `tracking_manager.py:84-111` - `stop_tracking()` stops daemon + closes session

**Why sendBeacon**:
- Standard fetch/XHR unreliable during page unload (browser may cancel)
- `sendBeacon` designed for analytics: guaranteed delivery even during close/refresh
- Browser queues request and sends it regardless of page lifecycle

**Result**: **One session = one page load (from open to refresh/close)**

**Orphaned Session Cleanup** (✅ GUARANTEED CONSISTENCY - Updated 2025-01-14):
- **Mechanism**: Single-session guarantee enforced at session creation
- **When**: Every time a new session is created (`_create_session()`)
- **How**: Closes ALL orphaned sessions (end_time = NULL) before creating new one
- **Result**: ALWAYS exactly 1 open session (or 0 if idle), never multiple orphans

**Orphaned Session Handling**:
1. Query: `SELECT id FROM sessions WHERE end_time IS NULL`
2. For each orphaned session:
   - If has delta_t events (valid session) → close and validate (set end_time, validated=1)
   - If NO delta_t events (invalid session) → delete session + all events
3. Then create new session

**Why this approach**:
- ✅ **Proactive**: Catches orphans before they accumulate (not reactive cleanup)
- ✅ **Consistent**: Guaranteed single open session (no timing dependencies)
- ✅ **Robust**: Handles crashes, force-kills, network disconnects automatically
- ✅ **Simple**: One cleanup point (session creation), not scattered across codebase

**Code Evidence**:
- `analytics_logger.py:95-140` - `_create_session()` with orphan cleanup

### Database Schema

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,              -- 20260112_131732 format
    start_time REAL,                  -- Unix timestamp
    end_time REAL,                    -- Unix timestamp (NULL if running)
    validated BOOLEAN DEFAULT 0,      -- 1 if first Δt calculated
    event_count INTEGER DEFAULT 0     -- Total events in session
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    timestamp REAL,                   -- Unix timestamp
    event_type TEXT,                  -- 'delta_t', 'gate_crossing', etc.
    data TEXT,                        -- JSON: {consist_id, delta_t, status, gate_type}
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

---

## Implementation Details

### Backend (`analytics_logger.py`)

**Key Methods**:
- `log_event(event_type, data)` - Async, non-blocking, returns immediately
- `close_session()` - Flush buffer, cleanup zombies, close DB
- `get_session_info()` - Lightweight metadata for frontend

**Session Validation Logic**:
```python
# Session becomes valid on FIRST Δt calculation
if event_type == 'delta_t' and not self.session_validated:
    self.session_validated = True
    # Update DB: validated = 1
```

**Orphaned Session Cleanup** (2025-01-14):
```python
def _create_session(self):
    """Close ALL orphaned sessions before creating new one"""

    # 1. Find all sessions with end_time = NULL
    cursor.execute("SELECT id FROM sessions WHERE end_time IS NULL")
    orphaned_sessions = cursor.fetchall()

    # 2. Close or delete each orphan
    for orphan_id in orphaned_sessions:
        # Check if session has delta_t events (valid session)
        cursor.execute(
            "SELECT COUNT(*) FROM events WHERE session_id = ? AND event_type = 'delta_t'",
            (orphan_id,)
        )
        delta_t_count = cursor.fetchone()[0]

        if delta_t_count > 0:
            # Valid session - close and validate
            UPDATE sessions SET end_time = ?, validated = 1 WHERE id = ?
        else:
            # Invalid session - delete completely
            DELETE FROM events WHERE session_id = ?
            DELETE FROM sessions WHERE id = ?

    # 3. Now create new session (guaranteed single open session)
    INSERT INTO sessions (id, start_time, validated, event_count) VALUES (?, ?, 0, 0)
```

**Why cleanup on session creation**:
- ✅ **Proactive**: Prevents orphan accumulation (catches at root cause)
- ✅ **Single-session guarantee**: Enforced structurally, not by timing
- ✅ **Crash-proof**: Handles ANY abnormal termination (crash, kill -9, network loss)
- ✅ **Simple**: One cleanup point, clear logic, no race conditions

---

### Frontend (`AnalyticsPanel.jsx`)

**Two View Modes**:

1. **Current Session**:
   - Real-time data from active session
   - Endpoint: `GET /api/analytics/current` (metadata), `GET /api/analytics/session/{id}` (events)
   - Updates on Refresh button click

2. **Cumulative History**:
   - All validated sessions concatenated
   - Endpoint: `GET /api/analytics/cumulative`
   - Stats: total sessions, gate crossings per consist, uptime

**Consist Filtering**:
```javascript
const [consistFilter, setConsistFilter] = useState('all'); // 'all', 10, 11

// Chart data preparation
return events.map(event => ({
  time: formatTime(event.timestamp),
  delta_t_c10: event.consist_id === 10 ? event.delta_t : null,
  delta_t_c11: event.consist_id === 11 ? event.delta_t : null,
  // ...
}));

// Recharts Line components
<Line dataKey="delta_t_c10" stroke="#d946ef" connectNulls={true} />
<Line dataKey="delta_t_c11" stroke="#3b82f6" connectNulls={true} />
```

**Horizontal Scroll** (2025-01-12):
```javascript
// Chart width = 60px per event, minimum 800px
<div className="overflow-x-auto">
  <ResponsiveContainer width={Math.max(prepareChartData().length * 60, 800)} height={400}>
    <LineChart data={prepareChartData()}>
      {/* ... */}
    </LineChart>
  </ResponsiveContainer>
</div>
```

**Scroll appears when**: >13 events (800 / 60)

---

## UI/UX Design

### Desktop Optimizations
- **Minimum width**: 1024px enforced (alert on smaller screens)
- **Keyboard shortcut**: A key toggles panel
- **Chrome rendering fix**: GPU cleanup on view change/close
- **Body scroll lock**: Prevents page scroll when panel open

### Color Scheme
- **Consist 10**: Magenta (#d946ef)
- **Consist 11**: Blue (#3b82f6)
- **Status zones**:
  - SYNCED: |Δt| < 1.0s (green reference line)
  - WARNING: 1.0s ≤ |Δt| < 1.5s (amber dashed lines)
  - CRITICAL: |Δt| ≥ 1.5s (red dashed lines)

### Chart Features
- **Time-series X-axis**: HH:MM:SS format
- **Δt Y-axis**: Seconds (positive = lead ahead, negative = rear ahead)
- **Tooltip**: Timestamp, Δt value, status, gate type
- **Legend**: Consist 10 / Consist 11 labels

---

## Performance Considerations

### Current Implementation
- **Buffer size**: 100 events
- **Flush interval**: 10s (async, non-blocking)
- **Chart width**: 60px/event
- **Scroll threshold**: >13 events

### Scalability Roadmap

| Events | Solution | When Needed |
|--------|----------|-------------|
| <1000 | Current (scroll) | ✅ Now - weeks of data |
| 1000-10k | Server-side sampling (`?maxPoints=500`) | Medium term |
| 10k-100k | LTTB downsampling algorithm | Long term |
| >100k | TimescaleDB migration | Production scale (if ever) |

**Event Volume Estimates**:
- **Δt events**: ~500/day → 15k/month → 180k/year
- **YOLO performance events**: ~720/hour → 17k/day (if continuous) → realistic ~2-3k/day
- **Typical session**: 2-4 hours → 100-200 Δt events + 300-600 YOLO events
- **Critical threshold**: ~1000 events per chart (when scroll becomes heavy)

**Current scroll handles**: ~1000-2000 events smoothly (weeks of data per view)

---

### STEP 1: Server-Side Sampling (When Reaching ~1000 Events)

**✅ UNIVERSAL APPROACH - Applies to ALL charts and event types**

**✅ NOW CONFIGURABLE** (2025-01-19): `tail` and `maxPoints` values no longer hardcoded
- Config: `analytics.max_chart_events` (default 500, range 100-2000)
- Settings UI: Analytics tab → Max Chart Events (hot reload, no restart)
- Backend: Dynamic config load instead of hardcoded 500/1000
- Current view: Shows last N events (full resolution)
- Overview view: Downsamples to N if total > N (LTTB + critical events)

**Concept**: Backend does intelligent sampling, frontend remains unchanged.

**Implementation**:

**Backend endpoint parameters** (mutually exclusive):
```python
# Current view: Full resolution recent data
# tail = config.analytics.max_chart_events (default 500)
GET /api/analytics/cumulative?tail=500

# Overview view: Sampling across entire history
# maxPoints = config.analytics.max_chart_events (default 500)
GET /api/analytics/cumulative?maxPoints=500
```

**Backend logic** (applies to ALL event arrays):
```python
def sample_events(events, max_points):
    """
    Uniform sampling for ANY event type.
    Takes 1 event every N to reach max_points.
    """
    if len(events) <= max_points:
        return events  # No sampling needed

    step = len(events) / max_points
    sampled = []
    for i in range(max_points):
        idx = int(i * step)
        sampled.append(events[idx])

    return sampled

# Apply tail OR sampling (mutually exclusive, tail takes precedence)
if tail:
    # Current view: keep last N events (full resolution, no sampling)
    delta_t_events = delta_t_events[-tail:] if len(delta_t_events) > tail else delta_t_events
    yolo_performance = yolo_performance[-tail:] if len(yolo_performance) > tail else yolo_performance
elif max_points:
    # Overview view: uniform sampling across entire history
    delta_t_events = sample_events(delta_t_events, max_points)
    yolo_performance = sample_events(yolo_performance, max_points)
    # Any future event types added here automatically
```

**Conditional Debug Logging**:
```python
# Log ONLY if debug enabled in config AND reduction is significant
if debug_enabled:
    delta_reduction = original_delta_t_count - len(delta_t_events)
    yolo_reduction = original_yolo_count - len(yolo_performance)

    # Significant = reduced >10% OR reduced >100 events
    is_significant = (delta_reduction > original_delta_t_count * 0.1 or delta_reduction > 100 or
                      yolo_reduction > original_yolo_count * 0.1 or yolo_reduction > 100)

    if is_significant:
        print(f"[DEBUG] Sampling applied (maxPoints={max_points}) | "
              f"dT: {original_delta_t_count}->{len(delta_t_events)} | "
              f"YOLO: {original_yolo_count}->{len(yolo_performance)}")
```

**Log Examples**:
- ❌ `501->500` (1 event, 0.2%) - No log (not significant)
- ❌ `550->500` (50 events, 9.1%) - No log (<10%)
- ✅ `600->500` (100 events, 16.7%) - **LOG** (>10%)
- ✅ `1000->500` (500 events, 50%) - **LOG** (>10% and >100)
- ❌ Any reduction if `config.json` → `debug.enabled = false` - No log

**Frontend**:
- **Zero changes required** - still receives array of events
- No knowledge of sampling (transparent)
- Charts render identically (just fewer data points)

**Strategy Rationale**:
- **Current view (`tail`)**: Keeps recent data at full resolution (important for active operations)
- **Overview view (`maxPoints`)**: Optimizes historical trends (less detail needed)
- **Mutually exclusive**: Only one strategy applied per request

**Why This Works**:
1. **Universal**: Same logic for ALL event types (Δt, YOLO performance, future charts)
2. **Transparent**: Frontend doesn't know/care about sampling
3. **Flexible**: `tail`/`maxPoints` parameters configurable per request
4. **Intelligent**: LTTB algorithm preserves visual shape, critical events always included
5. **Silent**: No log spam unless debug enabled + reduction significant

**Configuration**:
- Adjust via Settings UI → Analytics tab → Max Chart Events (100-2000)
- Or edit `config.json` → `analytics.max_chart_events` (default 500)
- Lower values = better performance, less history visible
- Higher values = more data, slower rendering
- Recommended: 300-1000 depending on hardware
- Debug log: `config.json` → `"debug": {"enabled": true}`

**✅ IMPLEMENTED** (2025-01-13 - commit `683d263`):
- ✅ **LTTB Downsampling** (Largest Triangle Three Buckets)
  - Generic `lttb_downsample()` function (~40 lines pure Python)
  - Selects points forming largest triangles (preserves visual shape)
  - Much better than uniform sampling for peaks/valleys
- ✅ **Smart Δt Downsampling** with critical event preservation
  - `smart_downsample_delta_t()` function
  - **ALWAYS includes ALL critical events** (|Δt| ≥ 1.5s, both ± signs)
  - Applies LTTB to remaining normal events
  - Critical anomalies NEVER lost regardless of sampling
- ✅ **Applied to**:
  - Δt events: `smart_downsample_delta_t()` (critical + LTTB)
  - YOLO FPS: `lttb_downsample()` (shape preservation)
- ✅ **Performance**: Runtime downsampling, <20ms with <1000 events, ~50-100ms with 5000 events
- ✅ **Result**: Ready for >500 events (weeks/months of data), frontend unchanged

---

## API Endpoints

### `GET /api/analytics/current`
Returns current session metadata (lightweight):
```json
{
  "session_id": "20260112_131732",
  "start_time": 1736683052.123,
  "uptime": 1234.567,
  "event_count": 42,
  "validated": true
}
```

### `GET /api/analytics/session/{session_id}`
Returns full session data with events:
```json
{
  "session": {
    "id": "20260112_131732",
    "start_time": 1736683052.123,
    "end_time": 1736684286.456,
    "validated": true,
    "event_count": 42
  },
  "events": [
    {
      "timestamp": 1736683084.789,
      "consist_id": 11,
      "delta_t": -0.143,
      "status": "SYNCED",
      "gate_type": "cross"
    },
    // ...
  ]
}
```

### `GET /api/analytics/cumulative`
Returns all validated sessions + aggregated stats:
```json
{
  "sessions": [
    {
      "id": "20260112_131732",
      "start_time": 1736683052.123,
      "end_time": 1736684286.456,
      "event_count": 42,
      "duration": 1234.333
    },
    // ... more sessions
  ],
  "total_sessions": 5,
  "total_gate_crossings": 210,
  "gate_crossings": {
    "10": 98,
    "11": 112
  },
  "total_uptime": 6789.123,
  "delta_t_events": [
    // All events from all sessions concatenated, ordered by timestamp
  ]
}
```

---

## Known Issues & Lessons Learned

### ❌ Failed Approaches

**1. Recharts Brush Component** (2025-01-12, rollback commit `fa8b7cd`)
- **Problem**: Zoom/pan state reset on re-renders
- **Attempted fix**: Controlled Brush with state management
- **Result**: Still buggy, overcomplicated
- **Solution**: Replaced with simple horizontal scroll
- **RESOLUTION** (2025-01-14): ✅ Fixed with React.memo + useMemo (commit `f8a4e22`)

**2. Zombie Cleanup at Startup** (2025-01-12, rollback commit `a03c597`)
- **Problem**: Deleted newly created sessions (timing race)
- **Root cause**: Cleanup ran AFTER `AnalyticsLogger()` created session with `validated=0`
- **Solution**: Moved cleanup to `close_session()` (safe - current session finalized first)

**3. Session Boundary Line Breaks - Recharts** (2025-01-13 → 2025-01-14, multiple attempts)
- **Goal**: Visual line breaks when `session_id` changes (deterministic)
- **Failed Approaches**:
  1. **Segment-based rendering with separate arrays** (commit `f3c40da`) - All segments overlapped on left, legend duplicated (7+ entries)
     - Tried passing different `data` prop to each Line component
     - **Root cause**: Recharts does NOT support `data` prop on Line - only on parent LineChart
  2. **Unified dataset + null boundaries** (commit `615f68e`) - Only 2-3 point mini-segments everywhere
  3. **Selective nulls** (single-consist nulls) - Same mini-segment problem
  4. **Double-null strategy** (commit `f470b53`) - Recharts ignored double-nulls, continuous lines
  5. **XAxis numeric + segments** (commit `8037997`) - Vertical alignment, 1000+ legend entries, illegible
  6. **Marker approach with undefined** (commit `250b863`) - Markers ignored by Recharts with `connectNulls={true}`
  7. **Marker approach with NaN** (commit `863aa15`) - Same result, NaN treated like null
  8. **connectNulls={false}** (commit `865387d`) - Broke lines on natural nulls (other consist data), not just session boundaries
- **Root Cause**: Recharts architectural limitation
  - All Line components must share parent LineChart's single data array
  - No way to distinguish "other consist null" (skip) vs "session boundary" (break)
- **✅ RESOLUTION** (2025-01-14, commit `35ea274`): **Segment-based rendering with separate dataKeys**
  - **Approach**: Single shared data array with segmented dataKeys
    ```javascript
    // Detect session boundaries, assign segment numbers
    const eventSegments = []; // [0, 0, 0, 1, 1, 2, 2, 2, ...]

    // Build unified dataset with per-segment dataKeys
    chartData = events.map(e => ({
      ...e,
      delta_t_c10_seg0: (e.consist === 10 && segment === 0) ? e.delta_t : null,
      delta_t_c10_seg1: (e.consist === 10 && segment === 1) ? e.delta_t : null,
      delta_t_c11_seg0: (e.consist === 11 && segment === 0) ? e.delta_t : null,
      delta_t_c11_seg1: (e.consist === 11 && segment === 1) ? e.delta_t : null,
      // ... etc for all consist+segment combinations
    }));

    // Render separate Line per segment
    <LineChart data={chartData}>  // <-- SAME array for all
      <Line dataKey="delta_t_c10_seg0" legendType={undefined} />
      <Line dataKey="delta_t_c10_seg1" legendType="none" />
      <Line dataKey="delta_t_c11_seg0" legendType={undefined} />
      <Line dataKey="delta_t_c11_seg1" legendType="none" />
    </LineChart>
    ```
  - **Key Difference from Failed Attempt #1**:
    - ❌ Before: Tried separate `data` arrays per Line (not supported)
    - ✅ Now: Single shared array, **different dataKeys** per segment (supported!)
  - **Legend Strategy**: `legendType="none"` on segments >0 (only first segment shows in legend)
  - **Result**:
    - ✅ Physical separation between segments → natural line breaks
    - ✅ Works in both Current and Overview modes
    - ✅ Clean legend (each consist shown once)
    - ✅ No marker artifacts in data
    - ✅ Brush zoom/pan unaffected
  - **Why It Works Now**: Recharts can handle multiple dataKeys pointing to same shared array, each Line draws only its own non-null values

**4. Session Boundary Line Breaks - Plotly Migration** (2025-01-14, commits `28bed61`-`a9c0e2f`)
- **Motivation**: Plotly supports independent traces with separate data arrays
- **Approach**: Each consist = independent trace with session boundary nulls
- **Implementation**:
  - Test HTML (`test_plotly_gaps.html`) - ✅ Worked perfectly with small test data
  - Relative timestamps (seconds from start) to avoid large numbers
  - `react-plotly.js` wrapper + vanilla `Plotly.newPlot()` attempts
  - React.memo + useMemo + revision prop for state preservation
- **Result**: ❌ **Chart illegible with real data**
  - Real data: 40-227 events over 109k seconds (~30 hours)
  - Sparse data created vertical spike pattern instead of readable timeline
  - Even with correct implementation (relative timestamps, no refresh), chart useless
  - Bundle size: 5.5 MB (8.5x larger than Recharts 658 KB)
- **Decision**: Reverted to Recharts (commit `7205b31`)
  - Session boundaries not critical feature - can live without it
  - Recharts readable with sparse data
  - Much smaller bundle
- **Commits**: `28bed61` (initial), `15e0d0b` (xaxis fix), `44bcaab` (vanilla Plotly), `d208aca` (debug), `4e1e76d` (relative timestamps), `8cfabac` (Plotly.react), `a9c0e2f` (back to react-plotly.js), `3257710` (component extraction), `1bd14c8` (memo + revision)
- **Cleanup**: Removed test files (`6b1a6a3`), uninstalled packages

### ✅ Working Solutions

**1. connectNulls for Multi-Consist Charts** (commit `fa8b7cd`)
- **Problem**: Lines broken when consists alternate (C10, C11, C10, C11...)
- **Solution**: `connectNulls={true}` → each line skips other consist's null values
- **Result**: Smooth, continuous lines for each consist

**2. Horizontal Scroll** (commit `6edf315`)
- **Approach**: Chart width = events × 60px, container with `overflow-x: auto`
- **Benefits**: Simple, no state, natural browser scrolling, predictable UX
- **Performance**: Handles hundreds of events smoothly

**3. React.memo + useMemo for State Preservation** (commit `d5bd4ab`, 2025-01-14)
- **Problem**: Charts re-rendering on every parent update, resetting Brush zoom/pan state
- **Root Cause**: Data preparation functions recalculating on every render
- **Solution**: Memoization at multiple levels
  ```javascript
  // 1. Memoize filtered events
  const filteredEvents = useMemo(() => {
    return consistFilter === 'all' ?
      data :
      data.filter(e => e.consist_id === consistFilter);
  }, [data, consistFilter]);

  // 2. Memoize chart data preparation
  const chartData = useMemo(() => {
    return prepareChartData(filteredEvents);
  }, [filteredEvents, trackingConfig]);

  // 3. Memoize chart width
  const chartWidth = useMemo(() => {
    return viewMode === 'current' ?
      Math.max(chartData.length * 40, 800) :
      '100%';
  }, [chartData.length, viewMode]);
  ```
- **Result**:
  - Chart only recalculates when dependencies actually change
  - Brush zoom/pan state preserved across re-renders
  - Enabled Brush restoration (commit `f8a4e22`)
- **Key Insight**: Same technique that "fixed" Plotly zoom preservation
  - Applied to Recharts with identical success
  - Should have been tried earlier instead of abandoning Brush

**4. Session Boundary Line Breaks** (commit `35ea274`, 2025-01-14)
- **Problem**: Continuous lines across session boundaries (idle periods)
- **Goal**: Visual breaks when `session_id` changes
- **Solution**: Segment-based rendering with separate dataKeys
  - Detect session boundaries by tracking `session_id` changes
  - Assign segment number to each event (0, 0, 0, 1, 1, 2, ...)
  - Create separate dataKey for each consist+segment combination:
    - `delta_t_c10_seg0`, `delta_t_c10_seg1`, `delta_t_c11_seg0`, etc.
  - Render multiple Line components:
    - Each segment = separate Line with same color
    - First segment shows in legend, others use `legendType="none"`
  - Physical separation between Line components = natural breaks
- **Result**:
  - ✅ Line breaks visible at every session boundary
  - ✅ Works in both Current and Overview modes
  - ✅ Works with sampling (segments preserved after LTTB)
  - ✅ Clean legend (each consist shown once)
  - ✅ No performance impact
- **Key Insight**:
  - Failed earlier with separate `data` arrays (not supported by Recharts)
  - Succeeded with separate **dataKeys** pointing to same shared array
  - Recharts limitation turned into feature: multi-dataKey support = segmentation

---

## Future Enhancements

### Short Term (if needed)
- [ ] Export session data (CSV/JSON download)
- [ ] Session notes/annotations

### Long Term (nice to have)
- [x] LTTB downsampling for >500 events - **✅ IMPLEMENTED** (2025-01-13, commit `683d263`)
  - Smart Δt downsampling with critical event preservation (|Δt| ≥ 1.5s always included)
  - LTTB shape-preserving downsampling for YOLO FPS
  - Runtime downsampling, transparent to frontend
- [x] Aggregate statistics per locomotive (not just consist) - **✅ IMPLEMENTED** (Operating Time Tracking)
- [ ] Speed profile analysis (average, min, max per session)
- [ ] Track utilization heatmap (which gate most used)

---

## Locomotive Operating Time Tracking

**Status**: 🔄 **IN PROGRESS** (2025-01-13)

### Problem Statement

Current analytics track data at **consist level** (C10, C11), not **locomotive level** (1, 5, 7, 8):
- `events` table stores `consist_id` in delta_t events
- Sessions track consist activity duration, not individual locos
- **Cannot deduce** individual loco operating time from existing data

### Solution: Hybrid Approach (Events + Stats Table)

**Dual storage strategy** for flexibility + performance:

#### 1. Events Table (Time-Series Analysis)

Store individual operating periods for historical analysis:

```sql
events:
  event_type = 'loco_operating_time'
  data = {
    "address": 1,
    "start_time": 1736738472.5,
    "end_time": 1736742072.5,
    "duration_seconds": 3600,
    "session_id": "20260113_041132",
    "consist_id": 10
  }
```

**Use cases**:
- Historical charts (operating time per day/week/month)
- Trend analysis (is loco usage increasing?)
- Session breakdown (which loco used when)

#### 2. Locomotive Stats Table (Fast Aggregates)

Dedicated table for quick lookups + future features:

```sql
CREATE TABLE locomotive_stats (
    address INTEGER PRIMARY KEY,          -- DCC address (1,2,5,6,7,8)
    name TEXT,                            -- Locomotive name (e.g., "Gr.675 017")
    total_operating_seconds INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    last_active_time REAL,                -- Unix timestamp
    created_at REAL,                      -- First tracking date
    updated_at REAL,                      -- Last update

    -- Future columns (ready for expansion):
    -- total_gate_crossings INTEGER,
    -- estimated_distance_km REAL,
    -- maintenance_due_hours INTEGER,
    -- fault_count INTEGER,
    -- last_maintenance_date REAL
);
```

**Use cases**:
- Fast bar chart rendering (single SELECT, no SUM aggregation)
- Maintenance alerts (check total_operating_seconds vs threshold)
- Dashboard widgets (last active, next maintenance due)

### Implementation Plan

#### Step 1: Database Schema Migration

Add `locomotive_stats` table creation in `analytics_logger.py`:

```python
def _initialize_db(self):
    # Existing tables...

    # New: Locomotive stats table
    self.conn.execute('''
        CREATE TABLE IF NOT EXISTS locomotive_stats (
            address INTEGER PRIMARY KEY,
            name TEXT,
            total_operating_seconds INTEGER DEFAULT 0,
            total_sessions INTEGER DEFAULT 0,
            last_active_time REAL,
            created_at REAL,
            updated_at REAL
        )
    ''')
```

#### Step 2: One-Time Migration Script

Backfill operating time from existing sessions (assumes consist locos = same duration):

```python
# scripts/migrate_operating_time.py

import sqlite3
from datetime import datetime

def migrate_existing_sessions():
    """
    One-time migration: Calculate loco operating time from existing consist sessions.
    Assumption: Locos in same consist always operated together (same duration).
    """

    conn = sqlite3.connect('analytics.db')
    cursor = conn.cursor()

    # Get all validated sessions
    cursor.execute('SELECT id, start_time, end_time FROM sessions WHERE validated = 1')
    sessions = cursor.fetchall()

    for session_id, start_time, end_time in sessions:
        duration = end_time - start_time if end_time else 0

        # Check which consists were active in this session
        cursor.execute('''
            SELECT DISTINCT json_extract(data, '$.consist_id') as consist_id
            FROM events
            WHERE session_id = ? AND event_type = 'delta_t'
        ''', (session_id,))

        active_consists = cursor.fetchall()

        for (consist_id,) in active_consists:
            # Map consist to locomotives
            if consist_id == 10:
                addresses = [1, 5]  # Gr.675 017, D645 014
            elif consist_id == 11:
                addresses = [7, 8]  # E656 239, E444 056
            else:
                continue

            # Log operating time event for each loco
            for address in addresses:
                # Create event
                event_data = {
                    'address': address,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_seconds': duration,
                    'session_id': session_id,
                    'consist_id': consist_id
                }

                cursor.execute('''
                    INSERT INTO events (session_id, timestamp, event_type, data)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, end_time, 'loco_operating_time', json.dumps(event_data)))

                # Update aggregate stats
                cursor.execute('''
                    INSERT INTO locomotive_stats (address, total_operating_seconds, total_sessions, last_active_time, created_at, updated_at)
                    VALUES (?, ?, 1, ?, ?, ?)
                    ON CONFLICT(address) DO UPDATE SET
                        total_operating_seconds = total_operating_seconds + ?,
                        total_sessions = total_sessions + 1,
                        last_active_time = MAX(last_active_time, ?),
                        updated_at = ?
                ''', (address, duration, end_time, start_time, end_time,
                      duration, end_time, end_time))

    conn.commit()
    conn.close()
    print(f"Migration complete: {len(sessions)} sessions processed")

if __name__ == '__main__':
    migrate_existing_sessions()
```

**Run once**: `python scripts/migrate_operating_time.py`

#### Step 3: Real-Time Tracking (Backend)

Track locomotive movement start/stop in `main.py`:

```python
# Global state for tracking loco movement
loco_start_times = {}  # {address: start_timestamp}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # ... existing code ...

    # Listen for speed changes
    if message.type == 'set_speed':
        address = message.data['address']
        speed = message.data['speed']
        timestamp = time.time()

        # Movement started (speed > 0 and was stopped)
        if speed > 0 and address not in loco_start_times:
            loco_start_times[address] = timestamp
            print(f"[TRACK] Loco {address} movement started")

        # Movement stopped (speed == 0 and was moving)
        elif speed == 0 and address in loco_start_times:
            start_time = loco_start_times.pop(address)
            duration = timestamp - start_time

            # Log event
            if analytics_logger:
                analytics_logger.log_loco_operating_time(
                    address=address,
                    start_time=start_time,
                    end_time=timestamp,
                    duration_seconds=duration
                )

            print(f"[TRACK] Loco {address} movement stopped (duration: {duration:.1f}s)")
```

Add method in `analytics_logger.py`:

```python
def log_loco_operating_time(self, address: int, start_time: float, end_time: float, duration_seconds: float):
    """Log locomotive operating time event"""
    event_data = {
        'address': address,
        'start_time': start_time,
        'end_time': end_time,
        'duration_seconds': duration_seconds,
        'session_id': self.session_id
    }

    # Add to events buffer
    self.log_event('loco_operating_time', event_data)

    # Update stats table immediately (no buffering for aggregates)
    try:
        self.conn.execute('''
            INSERT INTO locomotive_stats (address, total_operating_seconds, total_sessions, last_active_time, created_at, updated_at)
            VALUES (?, ?, 1, ?, ?, ?)
            ON CONFLICT(address) DO UPDATE SET
                total_operating_seconds = total_operating_seconds + ?,
                total_sessions = total_sessions + 1,
                last_active_time = MAX(last_active_time, ?),
                updated_at = ?
        ''', (address, duration_seconds, end_time, start_time, end_time,
              duration_seconds, end_time, end_time))
        self.conn.commit()
    except Exception as e:
        print(f"[ANALYTICS] Error updating locomotive stats: {e}")
```

#### Step 4: API Endpoint

```python
@app.get("/api/analytics/locomotive-stats")
async def get_locomotive_stats():
    """Get aggregated locomotive operating time statistics"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                address,
                name,
                total_operating_seconds,
                total_sessions,
                last_active_time,
                created_at
            FROM locomotive_stats
            ORDER BY address
        ''')

        rows = cursor.fetchall()
        conn.close()

        return {
            'locomotives': [
                {
                    'address': row[0],
                    'name': row[1],
                    'total_operating_hours': round(row[2] / 3600, 2),
                    'total_sessions': row[3],
                    'last_active_time': row[4],
                    'created_at': row[5]
                }
                for row in rows
            ]
        }
    except Exception as e:
        return {'error': str(e)}
```

#### Step 5: Bar Chart Visualization

```jsx
// In AnalyticsPanel.jsx
const [locoStats, setLocoStats] = useState(null);

useEffect(() => {
  if (isOpen) {
    fetch('/api/analytics/locomotive-stats')
      .then(res => res.json())
      .then(data => setLocoStats(data.locomotives));
  }
}, [isOpen]);

// Chart render
<BarChart data={locoStats}>
  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
  <XAxis dataKey="name" stroke="#9CA3AF" />
  <YAxis stroke="#9CA3AF" label={{ value: 'Operating Hours', angle: -90 }} />
  <Tooltip />
  <Bar dataKey="total_operating_hours">
    {locoStats?.map((loco, index) => (
      <Cell key={`cell-${index}`} fill={LOCO_COLORS[loco.address] || '#9CA3AF'} />
    ))}
  </Bar>
</BarChart>
```

### Future Features Enabled

With this infrastructure, future additions are trivial:

#### Maintenance Tracking
```sql
ALTER TABLE locomotive_stats ADD COLUMN maintenance_due_hours INTEGER DEFAULT 100;
ALTER TABLE locomotive_stats ADD COLUMN last_maintenance_date REAL;

-- Alert when due
SELECT address, name FROM locomotive_stats
WHERE total_operating_seconds / 3600 >= maintenance_due_hours;
```

#### Distance Estimation
```sql
ALTER TABLE locomotive_stats ADD COLUMN total_gate_crossings INTEGER DEFAULT 0;
ALTER TABLE locomotive_stats ADD COLUMN estimated_distance_km REAL DEFAULT 0;

-- Update on each gate crossing
UPDATE locomotive_stats
SET
  total_gate_crossings = total_gate_crossings + 1,
  estimated_distance_km = total_gate_crossings * 0.05  -- 50m track length
WHERE address = ?;
```

#### Fault/Derailment Tracking
```sql
ALTER TABLE locomotive_stats ADD COLUMN fault_count INTEGER DEFAULT 0;

-- New event type
INSERT INTO events (session_id, timestamp, event_type, data)
VALUES (?, ?, 'loco_fault', '{"address": 7, "fault_type": "derailment", "gate_id": 2}');
```

### Why Hybrid Works

| Aspect | Events Table | Stats Table |
|--------|-------------|-------------|
| **Query Speed** | Slow (SUM aggregation) | ⚡ Fast (direct SELECT) |
| **Storage** | Growing (1 row/movement) | Fixed (1 row/loco) |
| **Historical Analysis** | ✅ Full time-series | ❌ Aggregates only |
| **Future Columns** | ❌ Requires query changes | ✅ Add column, done |
| **Chart Rendering** | Use for trends | Use for current totals |

**Result**: Best of both worlds - fast charts + flexible analytics.

---

## Configuration

**In `config.json`**:
```json
{
  "tracking": {
    "idle_timeout_seconds": 10
  }
}
```

**Shared usage**:
- YOLO tracking: Switch to 1 FPS idle mode after timeout
- Analytics: Session duration measurement (no new events = idle)

---

## UI State - Current vs Overview (2025-01-13 00:30)

**Critical Design Decision**: Cards filter by session, Chart shows ALL events always.

### Cards (Top Stats) - Session Filtered

**Current View**:
- **Card 1**: Session Duration (calculated: `now - start_time` or `end_time - start_time`)
  - Shows N/A if no session or no start_time
  - Updates on: panel open, manual refresh
- **Card 2**: Gate Crossings (filtered by session + consist)
  - All: count all events in current session
  - C10: count only consist_id=10 events
  - C11: count only consist_id=11 events
  - Starts from 0 with new session
- **Card 3**: Critical Events (|Δt| ≥ 1.5s, filtered by session + consist)
  - Same filtering logic as Card 2
  - Starts from 0 with new session

**Overview View**:
- **Card 1**: Total Sessions (all time)
- **Card 2**: Gate Crossings (filtered by consist only, all sessions cumulative)
- **Card 3**: Critical Events (filtered by consist only, all sessions cumulative)

### Chart (Bottom Graph) - NEVER Filtered by Session

**Both Views (Current AND Overview)**:
- Shows **ALL events from ALL sessions** (cumulative history)
- Horizontal scroll: 40px per event
- Consist filter: All/C10/C11 shows/hides lines (NOT removes data points)
- New events append **on the right** (chronological order)
- Scrollable to beginning of time (first ever event)
- Auto-scroll to end on data load (via `scrollRefSession`)

**Why this design**:
- Users want to see **trends over time** in the chart (long-term patterns)
- Cards provide **current session metrics** (what's happening now)
- Chart is not session-specific, it's a **continuous timeline**

### User Interaction Flow

1. **Open Analytics (A key)** → Load all cumulative data
2. **Switch Current ↔ Overview (arrow keys ←/→)** → Cards change, chart stays same
3. **Filter by consist (All/C10/C11 buttons)** → Cards update counts, chart shows/hides lines
4. **Refresh button** → Reload data from API, cards update, chart extends right
5. **Close Analytics (X or A key)** → Nothing closes on backend (session continues)

### Known Behavior & Limitations (UPDATED 2025-01-14)

1. **Session closes on page close/refresh** ✅ DETERMINISTIC
   - **Every refresh = NEW session** (100% guaranteed via sendBeacon)
   - If you keep page open: ONE long session (same session_id)
   - If you refresh/close/reopen: NEW session ALWAYS (daemon forced to stop)
   - Cards in Current view show data from current page load

2. **Orphaned session recovery** ✅ AUTOMATIC (NEW 2025-01-14)
   - **Every new session closes ALL orphans** (end_time = NULL) before starting
   - Handles crashes, force-kills, network disconnects automatically
   - Valid orphans (with delta_t events) → closed and validated
   - Invalid orphans (no delta_t events) → deleted completely
   - Result: **ALWAYS exactly 1 open session (or 0 if idle)**, never orphans accumulate

3. **No auto-refresh** → Must manually click Refresh to see new events

4. **Session duration in Current** → Shows N/A if session not validated yet (no Δt calculated)

---

## Files Modified

**Backend**:
- `backend/analytics_logger.py` - Core logging engine
- `backend/tracking_daemon.py` - Analytics logger lifecycle

**Frontend**:
- `web/src/components/AnalyticsPanel.jsx` - Dashboard UI
- `web/src/App.jsx` - Keyboard shortcuts, state management

**Config**:
- `config.json` - Idle timeout parameter
- `backend/data/analytics.db` - SQLite database (gitignored)

---

## YOLO Performance Monitoring

**Status**: ✅ **IMPLEMENTED** (2025-01-13)
**Features**: FPS tracking + Confidence per locomotive (DCC addresses)

### Overview

Third chart in Analytics Suite: monitors YOLO detection quality in real-time.

**Two charts**:
1. **FPS Line Chart** (time-series): Inference speed over time
2. **Confidence Bar Chart** (snapshot): Per-locomotive detection quality

**Key Design Decisions**:
- **DCC address tracking**: Confidence keyed by DCC address (1, 5, 7, 8), NOT YOLO class
  - **Why**: Model switching compatibility (OBB ↔ Standard may have different class IDs)
  - **Result**: Analytics data consistent across model changes
- **5-second logging**: Reduces event volume (~720 events/hour vs 3600 if logged every frame)
- **Session filtering**: Different rules for time-series vs snapshot charts

### Implementation Approach (REUSABLE PATTERN)

**✅ This approach should be used for ALL future charts**

#### 1. Backend Performance Tracking

**File**: `backend/tracking/yolo_tracker.py`

```python
# Import statistics for mean calculation
from statistics import mean
from collections import deque, defaultdict

class YOLOTracker:
    def __init__(self, ...):
        # Performance tracking (60 frames = ~2s at 30fps)
        self.performance_stats = {
            'fps_history': deque(maxlen=60),
            'confidence_history': defaultdict(lambda: deque(maxlen=60)),  # Per DCC address
            'detection_count': 0,
            'miss_count': 0
        }

    def detect_locomotives(self, frame):
        start_time = time.time()

        # ... existing detection logic ...

        # Calculate FPS
        inference_time = time.time() - start_time
        fps = 1.0 / inference_time if inference_time > 0 else 0
        self.performance_stats['fps_history'].append(fps)

        # Track confidence PER DCC ADDRESS (NOT YOLO class!)
        for cls, det in detections.items():
            dcc_address = YOLO_CLASS_TO_DCC.get(cls)
            if dcc_address:
                self.performance_stats['confidence_history'][dcc_address].append(det['conf'])

        # Miss detection
        expected_locos = set(ADDRESS_TO_CLASS.values())
        detected_locos = set(detections.keys())
        if expected_locos - detected_locos:
            self.performance_stats['miss_count'] += 1

        self.performance_stats['detection_count'] += 1
        return detections

    def get_performance_stats(self):
        return {
            'avg_fps': mean(self.performance_stats['fps_history']) if self.performance_stats['fps_history'] else 0,
            'avg_confidence': {
                dcc_addr: mean(hist) if hist else 0
                for dcc_addr, hist in self.performance_stats['confidence_history'].items()
            },
            'miss_rate': self.performance_stats['miss_count'] / max(self.performance_stats['detection_count'], 1)
        }
```

#### 2. Event Logging

**File**: `backend/tracking_daemon.py`

```python
# Log performance every 5 seconds (reduce volume)
if self.analytics_logger and (current_time - self.last_yolo_perf_log > 5.0):
    stats = self.tracker.get_performance_stats()
    await self.analytics_logger.log_event('yolo_performance', {
        'avg_fps': stats['avg_fps'],
        'avg_confidence': stats['avg_confidence'],  # {1: 0.87, 5: 0.76, 7: 0.91, 8: 0.65}
        'miss_rate': stats['miss_rate']
    })
    self.last_yolo_perf_log = current_time
```

#### 3. Backend API Update

**File**: `backend/main.py`

Add `session_id` to query for session filtering support:

```python
cursor.execute(
    "SELECT session_id, timestamp, data FROM events WHERE event_type = 'yolo_performance' ORDER BY timestamp"
)
yolo_performance = []
for row in cursor.fetchall():
    data = json.loads(row[2])
    yolo_performance.append({
        'session_id': row[0],
        'timestamp': row[1],
        'avg_fps': data.get('avg_fps', 0),
        'avg_confidence': data.get('avg_confidence', {}),
        'miss_rate': data.get('miss_rate', 0)
    })
```

#### 4. Frontend Charts

**File**: `web/src/components/AnalyticsPanel.jsx`

**Import additional chart components**:
```javascript
import { LineChart, Line, BarChart, Bar, ... } from 'recharts';
```

**Add refs for scroll control**:
```javascript
const scrollRefFps = useRef(null);
```

**Update auto-scroll effect**:
```javascript
useEffect(() => {
  if (cumulativeData) {
    requestAnimationFrame(() => {
      if (scrollRefSession.current) {
        scrollRefSession.current.scrollLeft = scrollRefSession.current.scrollWidth;
      }
      if (scrollRefFps.current) {
        scrollRefFps.current.scrollLeft = scrollRefFps.current.scrollWidth;
      }
    });
  }
}, [cumulativeData, viewMode, consistFilter]);
```

### FPS Chart (Time-Series)

**Behavior**:
- **NO session filtering** - always shows all sessions (like Δt chart)
- Horizontal scroll in Current view (60px per data point)
- Auto-scroll to right (most recent data)
- YAxis domain: 0-140 (accommodates high TensorRT FPS)

**Implementation**:
```javascript
{(() => {
  // NO session filtering - show all sessions
  const chartData = cumulativeData.yolo_performance.map((e, idx) => ({
    index: idx + 1,
    time: formatTime(e.timestamp),
    fps: parseFloat(e.avg_fps.toFixed(1))
  }));

  const chartWidth = viewMode === 'current' ? Math.max(chartData.length * 60, 800) : '100%';
  const chartContent = (
    <ResponsiveContainer width={chartWidth} height={300}>
      <LineChart data={chartData}>
        <YAxis domain={[0, 140]} />
        <ReferenceLine y={30} stroke="#10b981" label="Target (30 FPS)" />
        <Line dataKey="fps" stroke="#10b981" />
      </LineChart>
    </ResponsiveContainer>
  );

  return viewMode === 'current' ? (
    <div ref={scrollRefFps} className="overflow-x-auto">
      {chartContent}
    </div>
  ) : chartContent;
})()}
```

### Confidence Chart (Snapshot)

**Behavior** (DIFFERENT from time-series charts):
- **Current view**: Only current session data (empty if no data yet)
- **Overview view**: Latest data globally
- Consist filtering applies (C10 = locos 1,5 | C11 = locos 7,8)

**Rationale**:
- NOT a time-series → doesn't benefit from showing all history
- Snapshot view → should reflect Current vs Overview semantics
- Empty chart in Current = waiting for first yolo_performance event

**Implementation**:
```javascript
{(() => {
  // Session filtering FOR SNAPSHOT CHARTS
  let events = cumulativeData.yolo_performance;

  if (viewMode === 'current' && currentSession) {
    events = events.filter(e => e.session_id === currentSession.session_id);
  }

  if (events.length === 0) return [];

  const latestEvent = events[events.length - 1];
  const avgConfidence = latestEvent.avg_confidence;

  // Consist filtering
  const consistAddresses = { 10: [1, 5], 11: [7, 8] };
  const addressFilter = consistFilter === 'all' ? [1, 5, 7, 8] : consistAddresses[consistFilter];

  return Object.entries(avgConfidence)
    .filter(([addr]) => addressFilter.includes(parseInt(addr)))
    .map(([dcc_addr, conf]) => ({
      loco: `Loco ${dcc_addr}`,
      confidence: parseFloat((conf * 100).toFixed(1))
    }));
})()}
```

### Session Filtering Rules (CRITICAL)

**Rule**: Different chart types require different filtering strategies

| Chart Type | Session Filtering | Rationale |
|-----------|------------------|-----------|
| **Δt Trends** (time-series) | ❌ NO | Historical context valuable |
| **FPS** (time-series) | ❌ NO | See performance trends over time |
| **Confidence** (snapshot) | ✅ YES | Current vs Overview semantics |
| **Stats Cards** | ✅ YES | Session-specific metrics |

**Implementation Pattern**:
```javascript
// Time-series charts: NO filtering
const chartData = cumulativeData.events.map(...);

// Snapshot charts: YES filtering
let events = cumulativeData.events;
if (viewMode === 'current' && currentSession) {
  events = events.filter(e => e.session_id === currentSession.session_id);
}
```

### Key Lessons Learned

1. **DCC Address Tracking**: ALWAYS use DCC addresses for analytics, NOT YOLO class IDs
   - Ensures data consistency across model changes (OBB ↔ Standard)
   - User switches models frequently for testing

2. **Event Volume**: Log performance events every 5s, NOT every frame
   - 720 events/hour vs 108,000 at 30fps
   - Reduces DB size without losing insight

3. **Chart Types Matter**: Session filtering depends on chart semantics
   - Time-series: Show all data for historical trends
   - Snapshot: Filter by view mode (Current/Overview)

4. **Empty Charts OK**: In Current view, empty Confidence chart = waiting for data
   - Better than showing stale data from previous sessions
   - User knows they need to start locomotives

5. **Horizontal Scroll**: Essential for time-series in Current view
   - Dynamic width based on data points
   - Auto-scroll to right for latest data
   - Pattern works for ANY time-series chart

### Files Modified

**Backend**:
- `backend/tracking/yolo_tracker.py` - Performance stats collection
- `backend/tracking_daemon.py` - Event logging (5s interval)
- `backend/main.py` - API query with session_id

**Frontend**:
- `web/src/components/AnalyticsPanel.jsx` - Charts implementation

### Production Results (2025-01-13)

**FPS Performance**:
- **TensorRT engine**: 50-130 FPS (2-4x faster than 30 FPS target!)
- Stable at 60-80 FPS during active tracking
- Peak 134 FPS at startup

**Confidence Levels**:
- Loco 1, 7, 8: 60-75% (excellent)
- Loco 5: ~35% (below 50% threshold - distant from camera or difficult angle)

**Chart Behavior**:
- ✅ FPS scrollbar working (Current view)
- ✅ Auto-scroll to right functional
- ✅ Confidence chart empty in Current (no data yet)
- ✅ Confidence chart populated in Overview (shows last session)
- ✅ Consist filtering works (C10/C11 buttons)

---

## Testing Notes

**Production Testing** (2025-01-12):
- ✅ Consist filtering works (magenta/blue lines)
- ✅ Scroll appears at >13 events
- ✅ Session validation correct (first Δt)
- ✅ Zombie cleanup safe (no active session deleted)
- ✅ Multi-device sync via refresh button
- ✅ Keyboard shortcut A functional

**Event Count Verified**:
- Session with 42 events: scroll visible, smooth navigation
- Cumulative 210+ events: no performance issues

---

## Changelog 2025-01-13

### Session Filtering Implementation + Revert

**Timeline**:
- **22:57** (`acfed1b`) - Arrow key navigation working, everything functional
- **23:12-23:28** - Added session filtering to cards AND chart (broke everything)
- **00:20** - Reverted to `acfed1b` (22:57 state)
- **00:30** (`0ef8f03`) - Implemented correct design: cards filtered, chart shows all

**What Broke (23:12-00:20)**:
- Session filtering applied to chart → Current view showed only 5 events (last session)
- Chart not scrollable (too few events)
- Auto-refresh attempts → WebSocket crashes, ResponsiveContainer errors
- Cards showed N/A, chart empty, complete mess

**What Works Now (`0ef8f03`)**:
- ✅ Cards filter by session in Current view (session data, starts from 0)
- ✅ Cards show totals in Overview view (all-time data)
- ✅ Chart ALWAYS shows all events (cumulative timeline)
- ✅ Chart scrollable, new events append right
- ✅ Consist filter works (All/C10/C11 buttons)
- ✅ Manual refresh updates cards + extends chart
- ✅ Arrow key navigation (← Current, → Overview)

**Rejected Features (Too Complex)**:
- ❌ Auto-refresh when locomotives moving (WebSocket monitoring)
- ❌ Real-time session duration updates (timer loop)
- ❌ Chart width as number (ResponsiveContainer wants string)

**Key Lesson**: Chart is a **continuous timeline viewer**, NOT a session-specific widget. Only cards provide session-specific metrics.

---

## Session Lifecycle - DEFINITIVE VERIFICATION (2025-01-13)

**Investigation 1** (codebase trace via Explore agent):

**VERIFIED FACTS** (with code evidence):
1. **TrackingDaemon created**: First WebSocket client connects (`tracking_manager.py:72`)
2. **AnalyticsLogger created**: When `daemon.run()` starts (`tracking_daemon.py:383`)
3. **Session closes**: When last client disconnects → daemon stops → `close_session()` called (`tracking_daemon.py:455-460`)
4. **Page refresh**: Creates NEW session if daemon stopped, CONTINUES if daemon still running
5. **Invalid sessions purged**: If no Δt calculated, session deleted entirely on close (`analytics_logger.py:170-177`)

**Key Discovery**: Sessions were NOT deterministic - timing-dependent on WebSocket reconnect speed.

---

**Investigation 2** (deterministic session boundaries implementation):

**PROBLEM**: Page refresh behavior was non-deterministic:
- Fast refresh → same session continued
- Slow refresh → new session created
- User had no control over session boundaries

**SOLUTION IMPLEMENTED** (2025-01-13):
- **Frontend**: `navigator.sendBeacon('/api/close-session')` on `beforeunload` event
- **Backend**: POST endpoint forces `tracking_manager.stop_tracking()`
- **Result**: **Every page refresh = NEW session (100% deterministic)**

**Code Changes**:
- `web/src/App.jsx:769-779` - beforeunload listener
- `backend/main.py:1121-1137` - `/api/close-session` endpoint

**Why sendBeacon**:
- Designed for analytics (guaranteed delivery during page close)
- Standard fetch/XHR unreliable (browser may cancel during unload)
- Works for: refresh, close tab, navigate away, browser close

**VERIFIED BEHAVIOR** (after implementation):
- Page refresh → daemon ALWAYS stops → session ALWAYS closes → new page load → NEW session
- No more timing dependencies or race conditions

---

**Investigation 3** (orphaned session recovery mechanism - 2025-01-14):

**PROBLEM DISCOVERED**: Orphaned sessions still possible despite sendBeacon
- Crash scenarios: power loss, kill -9, OS force-quit, network disconnect
- Result: Sessions left with `end_time = NULL` in database
- Reports tab didn't show these orphaned sessions (filtered by end_time IS NOT NULL)

**SOLUTION IMPLEMENTED** (2025-01-14):
- **Proactive cleanup at session creation** (not reactive cleanup on close)
- **Mechanism**: `_create_session()` closes ALL orphans before creating new session
- **Guarantee**: ALWAYS exactly 1 open session (or 0 if idle), never multiple orphans

**Algorithm**:
1. Query database: `SELECT id FROM sessions WHERE end_time IS NULL`
2. For each orphaned session:
   - Check if has delta_t events (valid coordinated operation)
   - **Valid orphan** → Set end_time, validated=1 (preserve historical data)
   - **Invalid orphan** → DELETE session + events (no useful data)
3. Create new session (now guaranteed to be the ONLY open session)

**Code Changes**:
- `backend/analytics_logger.py:95-140` - `_create_session()` with orphan cleanup
- Removed old zombie cleanup from `close_session()` (no longer needed)

**Why this approach**:
- ✅ **Structural guarantee**: Enforced at creation, not by timing
- ✅ **Crash-proof**: Handles ANY abnormal termination automatically
- ✅ **No accumulation**: Orphans cleaned up immediately on next session start
- ✅ **Data preservation**: Valid orphans (with delta_t) are recovered, not lost

**VERIFIED BEHAVIOR** (after implementation):
- Backend restart → finds orphaned session → closes it → creates new session
- Reports tab → shows recovered orphaned session in history
- Analytics → correct session count, no duplicate open sessions

---

**Last Updated**: 2025-01-14 (orphaned session recovery + Reports tab UX improvements)
**Working State**: Interactive zoom, rotated labels, sticky legend

---

## Changelog 2025-01-14 - Box-Select Zoom & Y-Axis Improvements

### Box-Select Zoom Implementation

**Feature**: Drag-to-zoom rectangle selection in Overview mode (Δt Trends chart)

**Implementation** (`AnalyticsPanel.jsx`):
```javascript
// State for zoom
const [refAreaLeft, setRefAreaLeft] = useState(null);
const [refAreaRight, setRefAreaRight] = useState(null);
const [zoomDomain, setZoomDomain] = useState(null); // { x: [min, max], y: [min, max] }
const lastMouseMoveTime = useRef(0);

// Handlers
handleMouseDown(e) → set refAreaLeft/refAreaRight
handleMouseMove(e) → throttle 50ms, update refAreaRight
handleMouseUp() → calculate zoomDomain, filter displayData
handleDoubleClick() → reset zoom (setZoomDomain(null))
```

**Key Challenges Solved**:

1. **XAxis categorical domain not supported** (commit `e728557`)
   - Problem: `domain={zoomDomain.x}` ignored on XAxis with `dataKey="index"`
   - Solution: Filter `displayData` instead of setting domain
   ```javascript
   const displayData = useMemo(() => {
     if (!zoomDomain) return chartData;
     return chartData.filter(d => d.index >= xMin && d.index <= xMax);
   }, [chartData, zoomDomain]);
   ```

2. **Performance - choppy drag** (commit `aa767e8`)
   - Problem: Many Line components → re-render on every mouseMove (60+ times/sec)
   - Solution: Throttle mouseMove to 50ms (20 updates/sec)
   ```javascript
   const now = Date.now();
   if (now - lastMouseMoveTime.current < 50) return;
   lastMouseMoveTime.current = now;
   ```

3. **Zoom broken after session breaks toggle** (commit `8d6b2a5`)
   - Problem: `handleMouseUp` looked for segmented dataKeys when `segmentCount === 0`
   - Solution: Conditional dataKey lookup based on `segmentCount`

4. **ReferenceArea invisible** (commit `a91ff52`)
   - Problem: Missing `yAxisId="left"` after adding dual Y-axis
   - Solution: Added `yAxisId="left"` to `<ReferenceArea>` component

**Commits**: `652fba6`, `e728557`, `aa767e8`, `8d6b2a5`, `a91ff52`

---

### Y-Axis Improvements

#### 1. ReferenceLine Visibility (commit `53dd9fd`)
**Problem**: Threshold lines (0, ±1, ±1.5) disappeared after adding right Y-axis
**Solution**: Added `yAxisId="left"` to all 5 `<ReferenceLine>` components
```javascript
<ReferenceLine yAxisId="left" y={0} stroke="#10b981" strokeDasharray="3 3" />
<ReferenceLine yAxisId="left" y={1} stroke="#f59e0b" strokeDasharray="3 3" label="WARNING" />
// ... etc
```

#### 2. Decimal Formatting (commit `53dd9fd`)
**Problem**: Y-axis values showed many decimals (e.g., "1.8734567")
**Solution**: Added `tickFormatter` to both Y-axes
```javascript
<YAxis yAxisId="left" tickFormatter={(value) => value.toFixed(2)} />
<YAxis yAxisId="right" tickFormatter={(value) => value.toFixed(2)} />
```

#### 3. Padding Reduction (commit `3a19c17`)
**User request**: Less padding to maximize chart area
**Change**: 10% → 5% in manual domain calculation
```javascript
const padding = range * 0.05; // was 0.1
return [yMin - padding, yMax + padding];
```

#### 4. Right Y-Axis Label (commit `ac257ed`)
**Problem**: Right Y-axis (Current mode) missing label
**Solution**: Added same label as left axis
```javascript
label={{ value: 'Δt (seconds)', angle: 90, position: 'insideRight', fill: '#9CA3AF' }}
```

#### 5. Label Rotation 180° (commit `41830f9`)
**User request**: Rotate labels so "Δt" is above and "seconds" below
**Change**: `angle: -90` → `angle: 90` on both left and right axes
```javascript
// BEFORE: seconds above, Δt below (angle: -90)
// AFTER: Δt above, seconds below (angle: 90)
label={{ value: 'Δt (seconds)', angle: 90, position: 'insideLeft', fill: '#9CA3AF' }}
```

**Offset attempt rejected** (commit `6d61741` → `22e9f31`):
- Tried `offset: -10` (left) and `offset: 10` (right) to center labels vertically
- Recharts `offset` moves horizontally (wrong direction for rotated text)
- Alternative `dx`/`dy` is pixel-based and not responsive
- **Decision**: Accept default positioning (good enough, no UX impact)

**Final config**: `angle: 90`, `position: 'insideLeft'/'insideRight'`, no offset

---

### Legend & Spacing Improvements

#### Sticky Legend in Current Mode (commit `8df7d62`)
**Problem**: Legend scrolls horizontally with chart, disappears when scrolling right

**Solution**: Dual legend approach
- **Current mode + All filter**: Custom HTML legend above chart (always visible)
  ```javascript
  <div className="flex gap-4 justify-center mb-4 pb-3 border-b border-slate-700">
    {consistIds.map(cid => (
      <div className="flex items-center gap-2">
        <div className="w-4 h-1" style={{ backgroundColor: getConsistStrokeColor(cid) }}></div>
        <span>{consistName}</span>
      </div>
    ))}
  </div>
  ```
- **Overview mode + All filter**: Recharts `<Legend />` inside chart (standard)
- **Single consist filter**: No legend in both modes (prevent height shift)

#### XAxis Spacing (commit `fa7a32a`)
**Problem**: "Event #" label overlapping with legend in Overview mode
**Solution**: Increased offset from -15 to +10 (push label down, away from legend)
```javascript
label={viewMode === 'overview' ?
  { value: 'Event #', position: 'insideBottom', offset: 10, fill: '#9CA3AF' }
  : undefined
}
```

**Note**: Offset direction confused initially (negative = closer, positive = away)

---

### Session Breaks Optimization (commit `2cf2cdd`)

**Background**: Segment-based rendering (10+ Line components) caused performance issues during box-select drag

**Solution**: Make session breaks optional with toggle
- **Default OFF**: Fast path, single dataKey per consist (`delta_t_c10`, `delta_t_c11`)
- **Toggle ON**: Slow path, segmented dataKeys (`delta_t_c10_seg0`, `delta_t_c10_seg1`, ...)

**UI**: Compact single-row header with all controls
```
[Current] [Overview] | [All] [C10] [C11] | [⏸️ Session Breaks] | [↻]
```

**Performance impact**:
- OFF: Smooth box-select drag, no lag
- ON: Slight choppiness (throttle helps but doesn't eliminate completely)

**User feedback**: Default OFF is preferred (most users don't need session boundaries visible)

---

### Implementation Summary

**Total Commits**: 15 (box-select + Y-axis + legend + spacing)

**Key Learnings**:
1. **Recharts XAxis categorical limitation**: Can't set domain on categorical axis → filter data instead
2. **Throttling essential**: Many Line components + mouseMove = performance bottleneck
3. **yAxisId required everywhere**: Adding second Y-axis requires explicit yAxisId on all chart elements
4. **Offset direction depends on rotation**: Standard offset doesn't work for rotated labels
5. **Good enough > perfect**: Attempted label centering not worth complexity/fragility

**Result**: ✅ Interactive zoom working, Y-axes properly configured, UI responsive and intuitive

---

## Speed Table Viewer (Phase 1)

**Status**: ✅ **COMPLETE** (2025-01-16)

JMRI-style 28-bar visualization of CV67-94 with automatic CV adjustment recommendations based on real-time consist performance data.

**See Complete Documentation**: [`docs/SPEED_TABLE_VIEWER.md`](SPEED_TABLE_VIEWER.md)

**Key Features**:
- 28 vertical bars displaying current CV values from JMRI roster XML
- Color-coded highlighting based on CRITICAL event counts
- CV adjustment recommendations with direction based on mean Δt sign
- CSV export for manual JMRI DecoderPro import
- Real-time session tracking integration

**Location**: Analytics Panel → Speed Tuning tab
