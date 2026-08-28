# Refactor Plan - Code Modularization

**Goal**: Split monolithic files into modular, maintainable structure before implementing Speed Table Auto-Tuning.

**Current State**:
- `backend/main.py`: 2340 lines (67 functions, 27 endpoints)
- `web/src/components/AnalyticsPanel.jsx`: 1684 lines (monolithic component)

**Timeline**: ~10-14 hours total (backend 4-6h, frontend 6-8h)

---

## Testing Workflow (Mac Development → PC Production)

**Branch**: `refactor` (isolated from `develop`)

### Mac (Development)
```bash
# Create refactor branch (one-time)
git checkout -b refactor
git push -u origin refactor

# Development cycle
# 1. Make changes
# 2. Commit frequently
git add <files>
git commit -m "refactor: <description>"

# 3. Push to test on PC
git push
```

### PC (Production Testing)

**Manual deploy to refactor branch** (repeat after each Mac push):

```powershell
# Open PowerShell 7, SSH to PC, run these commands:
cd C:\z21-Terminal
git fetch origin
git checkout refactor
git reset --hard origin/refactor
npm install --prefix web
npm run build --prefix web
z21-restart
```

**Testing checklist after deploy**:
1. Backend starts without errors: Check `z21-log` (no Python exceptions)
2. Frontend loads: Open browser `https://hostname.tailXXXXXX.ts.net`
3. Locomotive control works: Speed/direction/functions respond
4. Analytics opens: Click Analytics button
5. WebSocket connected: Check badges (WS, Z21 green)

**Rollback to develop** (if major issues):
```powershell
cd C:\z21-Terminal
git checkout develop
git reset --hard origin/develop
npm install --prefix web
npm run build --prefix web
z21-restart
```

### After Refactor Complete

**Merge to develop**:
```bash
# On Mac
git checkout develop
git merge refactor
git push

# On PC - use normal deploy
z21-deploy-dev  # Back to standard workflow
```

**Delete refactor branch**:
```bash
# On Mac (after successful merge)
git branch -d refactor
git push origin --delete refactor
```

---

## Phase 1: Backend Refactoring (4-6 hours)

### Step 1.1: Create Router Structure (1 hour)

**New files**:
```
backend/
├── routers/
│   ├── __init__.py
│   ├── locomotives.py   # Locomotive control endpoints
│   ├── analytics.py     # Analytics endpoints
│   ├── config.py        # Config management endpoints
│   └── tracking.py      # WebSocket + YOLO tracking
```

**Migration mapping**:

**locomotives.py** (8 endpoints):
- `GET /api/roster` - Get roster from JMRI
- `POST /api/loco/speed` - Set locomotive speed
- `POST /api/loco/function` - Toggle function
- `POST /api/loco/direction` - Change direction
- `POST /api/consist/speed` - Set consist speed
- `POST /api/consist/function` - Toggle consist function
- `POST /api/emergency-stop` - Emergency stop
- `GET /api/loco/{address}/functions` - Get function states

**analytics.py** (6 endpoints):
- `GET /api/analytics/current` - Current session stats
- `GET /api/analytics/session/{session_id}` - Session by ID
- `GET /api/analytics/cumulative` - Cumulative events
- `GET /api/analytics/reports` - Reports data
- `GET /api/analytics/locomotive-stats` - Operating time stats
- `POST /api/close-session` - Close current session

**config.py** (7 endpoints):
- `GET /api/config` - Get full config
- `PUT /api/config` - Update config
- `GET /api/config/tracking` - Get tracking config
- `GET /api/consists` - List consists
- `POST /api/consists` - Create consist
- `PUT /api/consists/{consist_id}` - Update consist
- `DELETE /api/consists/{consist_id}` - Delete consist

**tracking.py** (2 WebSocket + helper functions):
- `WebSocket /ws` - Locomotive state sync
- `WebSocket /ws/tracking` - YOLO tracking stream
- Helper: `broadcast_loco_state()` function
- Helper: `broadcast_tracking_data()` function

**Remaining in main.py**:
- `GET /` - Serve frontend
- `GET /api/track-power/{state}` - Track power control
- `GET /api/video-feed` - MJPEG video stream
- `GET /api/z21/health` - Z21 health check
- App initialization + startup/shutdown events

### Step 1.2: Extract Service Layer (2 hours)

**New files**:
```
backend/
├── services/
│   ├── __init__.py
│   ├── z21_service.py       # Z21 protocol operations
│   ├── analytics_service.py # Analytics business logic
│   └── config_service.py    # Config CRUD operations
```

**z21_service.py** - Extract from main.py:
- `get_loco_info()` - Z21 loco info query
- `set_loco_speed_internal()` - Z21 speed command
- `set_loco_function_internal()` - Z21 function command
- `emergency_stop_all()` - Z21 emergency stop
- `track_power_on()` / `track_power_off()` - Track power control
- All Z21 health check logic

**analytics_service.py** - Extract from main.py:
- `get_current_session()` - Query current session
- `get_session_by_id()` - Query specific session
- `get_cumulative_events()` - Query events with filtering
- `get_reports_data()` - Aggregate reports statistics
- `get_locomotive_stats()` - Operating time aggregation
- `close_current_session()` - Session lifecycle management
- Helper: `lttb_downsample()`, `smart_downsample_delta_t()`

**config_service.py** - Extract from main.py:
- `load_config()` - Read config.json + config.local.json
- `save_config()` - Write config.json
- `validate_config()` - Config validation
- `merge_local_overrides()` - Local config merge logic
- CRUD operations for consists

### Step 1.3: Update main.py (1 hour)

**After refactor, main.py structure** (~150 lines):
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from routers import locomotives, analytics, config, tracking
from services import z21_service

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await z21_service.connect()
    # ... other startup logic
    yield
    # Shutdown
    await z21_service.disconnect()

app = FastAPI(lifespan=lifespan)

# Include routers
app.include_router(locomotives.router, prefix="/api", tags=["locomotives"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(tracking.router, prefix="/api", tags=["tracking"])

# Remaining endpoints (video feed, track power, health)
@app.get("/api/track-power/{state}")
async def track_power(...):
    return await z21_service.set_track_power(state)

@app.get("/api/video-feed")
async def video_feed(...):
    # Keep video feed in main (needs access to tracking_daemon)
    ...

@app.get("/api/z21/health")
async def z21_health():
    return await z21_service.get_health()

# Serve frontend
app.mount("/", StaticFiles(directory="dist", html=True), name="dist")
```

### Step 1.4: Testing & Validation (1-2 hours)

**Test plan**:
1. ✅ Backend starts without errors
2. ✅ All endpoints respond (test with curl/Postman)
3. ✅ WebSocket connections work (locomotive control + tracking)
4. ✅ Analytics queries return correct data
5. ✅ Config CRUD operations functional
6. ✅ Video feed streaming works
7. ✅ Z21 health check passes

**Rollback points**:
- After Step 1.1: Tag `refactor-backend-routers`
- After Step 1.2: Tag `refactor-backend-services`
- After Step 1.3: Tag `refactor-backend-complete`

---

## Phase 2: Frontend Refactoring (6-8 hours)

### Step 2.1: Extract Chart Components (3 hours)

**New files**:
```
web/src/components/Analytics/
├── charts/
│   ├── DeltaTChart.jsx       # Δt Trends line chart
│   ├── FPSChart.jsx          # Inference FPS chart
│   ├── ConfidenceChart.jsx   # Confidence bar chart
│   └── OperatingTimeChart.jsx # Operating time bar chart
```

**Each chart component interface**:
```jsx
// Example: DeltaTChart.jsx
export default function DeltaTChart({
  data,              // Array of events
  viewMode,          // 'current' | 'overview'
  consistFilter,     // 'all' | consist_id
  trackingConfig,    // Tracking configuration
  currentSession,    // Current session object
  showSessionBreaks, // Boolean
  onZoomReset        // Callback for zoom reset
}) {
  // Chart-specific logic
  // Returns: <div> with ResponsiveContainer + LineChart
}
```

**Props to pass down**:
- Shared: `viewMode`, `consistFilter`, `trackingConfig`, `currentSession`
- Chart-specific: `data`, styling props, event handlers

**Benefits**:
- Each chart ~150-250 lines (manageable)
- Reusable across tabs (e.g., DeltaTChart in Current + Overview + Reports)
- Isolated testing per chart
- Easy to add SpeedCorrelationChart.jsx (Phase 1 speed tracking)

### Step 2.2: Extract Tab Views (2 hours)

**New files**:
```
web/src/components/Analytics/
├── CurrentView.jsx   # Current tab (session-specific stats + charts)
├── OverviewView.jsx  # Overview tab (historical stats + charts)
└── ReportsView.jsx   # Reports tab (session table + trend chart + modal)
```

**CurrentView.jsx** (~400 lines):
- Session stats cards (Duration, Gate Crossings, Critical Events)
- DeltaTChart (scrollable)
- FPSChart (scrollable)
- ConfidenceChart
- OperatingTimeChart (hidden in Current)
- Session validation banner
- Consist filters

**OverviewView.jsx** (~300 lines):
- Historical stats cards (Total Sessions, Total Events, etc.)
- DeltaTChart (compressed, zoom enabled)
- FPSChart (compressed)
- ConfidenceChart
- OperatingTimeChart (visible)
- Box-select zoom logic
- Session breaks toggle

**ReportsView.jsx** (~400 lines):
- Session history table (30 sessions)
- Historical trend chart
- Session detail modal
- Consist filtering

**Shared state management**:
- Parent (AnalyticsPanel) manages: `viewMode`, `consistFilter`, `currentSession`, API data
- Pass props down to child views
- Event handlers bubble up (e.g., `onConsistFilterChange`)

### Step 2.3: Refactor AnalyticsPanel.jsx (1 hour)

**After refactor, AnalyticsPanel.jsx structure** (~300 lines):
```jsx
export default function AnalyticsPanel({ isOpen, onClose }) {
  // State management (10-20 lines)
  const [viewMode, setViewMode] = useState('current');
  const [consistFilter, setConsistFilter] = useState('all');
  const [trackingConfig, setTrackingConfig] = useState(null);
  const [currentSession, setCurrentSession] = useState(null);
  const [cumulativeData, setCumulativeData] = useState(null);
  // ... other state

  // API calls (30-50 lines)
  useEffect(() => { /* fetch tracking config */ }, []);
  useEffect(() => { /* fetch current session */ }, [isOpen]);
  useEffect(() => { /* fetch cumulative data */ }, [viewMode]);
  // ... other effects

  // Event handlers (20-30 lines)
  const handleViewModeChange = (mode) => setViewMode(mode);
  const handleConsistFilterChange = (filter) => setConsistFilter(filter);
  const handleClose = () => onClose();

  // Render (150-200 lines)
  return (
    <div className="modal-backdrop">
      <div className="modal-panel">
        {/* Header with tabs */}
        <Header
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onClose={handleClose}
        />

        {/* Tab content */}
        {activeTab === 'current' && (
          <CurrentView
            viewMode={viewMode}
            consistFilter={consistFilter}
            trackingConfig={trackingConfig}
            currentSession={currentSession}
            cumulativeData={cumulativeData}
            onConsistFilterChange={handleConsistFilterChange}
          />
        )}

        {activeTab === 'overview' && (
          <OverviewView
            viewMode={viewMode}
            consistFilter={consistFilter}
            trackingConfig={trackingConfig}
            cumulativeData={cumulativeData}
            onConsistFilterChange={handleConsistFilterChange}
          />
        )}

        {activeTab === 'reports' && (
          <ReportsView
            consistFilter={consistFilter}
            trackingConfig={trackingConfig}
            onConsistFilterChange={handleConsistFilterChange}
          />
        )}
      </div>
    </div>
  );
}
```

**Extracted helper functions** (move to separate files):
- `utils/chartHelpers.js`: `formatDeltaT()`, `formatOperatingTime()`, `getConsistColor()`, etc.
- `utils/analyticsHelpers.js`: `filterEventsBySession()`, `getAddressFilter()`, etc.
- `constants/analyticsConstants.js`: `CHART_AXIS_STYLES`, `TOOLTIP_STYLES`, `CONSIST_COLOR_PALETTE`, etc.

### Step 2.4: Testing & Validation (1-2 hours)

**Test plan**:
1. ✅ Frontend builds without errors (`npm run build`)
2. ✅ Analytics modal opens/closes correctly
3. ✅ All 3 tabs render correctly
4. ✅ Charts display data (Current + Overview + Reports)
5. ✅ Consist filters work across all charts
6. ✅ Session breaks toggle works
7. ✅ Box-select zoom works (Overview mode)
8. ✅ Session detail modal works (Reports tab)
9. ✅ WebSocket updates reflected in real-time

**Rollback points**:
- After Step 2.1: Tag `refactor-frontend-charts`
- After Step 2.2: Tag `refactor-frontend-views`
- After Step 2.3: Tag `refactor-frontend-complete`

---

## Phase 3: Integration & Final Testing (1-2 hours)

### Step 3.1: End-to-End Testing

**Scenarios**:
1. Fresh start: Backend + Frontend from scratch
2. Locomotive control: Speed/direction/functions work
3. Analytics tracking: Δt events logged correctly
4. YOLO tracking: FPS/confidence updates in real-time
5. Config changes: Modify consist, see changes reflected
6. Session lifecycle: Open Analytics → Close → Reopen (new session)
7. Reports: 30 sessions display, detail modal works

### Step 3.2: Performance Validation

**Metrics to check**:
- Frontend bundle size: Should remain ~660 kB (not increase significantly)
- Backend memory: Should not increase (same data structures)
- API response times: Should remain <100ms (no regressions)
- WebSocket latency: Should remain <50ms (no impact)

### Step 3.3: Documentation Update

**Files to update**:
- `README.md`: Update project structure section
- `docs/WEB_DASHBOARD.md`: Update frontend architecture
- `CLAUDE.md`: Add refactor completion entry to changelog

---

## Migration Strategy

### Approach: Incremental with Safety Nets

1. **Branch strategy**:
   - Create `refactor-backend` branch from `develop`
   - Complete backend refactor → merge to `develop`
   - Create `refactor-frontend` branch from `develop`
   - Complete frontend refactor → merge to `develop`

2. **Commit frequency**:
   - Commit after each substep (e.g., "extract locomotives router")
   - Tag after each major step (rollback points)
   - Push frequently to backup progress

3. **Testing cadence**:
   - Test after each router extraction (backend)
   - Test after each chart component (frontend)
   - Full E2E test before merging to develop

4. **Rollback plan**:
   - Git tags mark stable points
   - `git reset --hard <tag>` if major issue
   - Document any breaking changes immediately

---

## Post-Refactor Benefits

### For Speed Table Auto-Tuning (v1.3+)

**Backend**:
- Add `routers/speed_tuning.py` for new endpoints (clean separation)
- Extend `analytics_service.py` with speed correlation logic
- Easy to add CV write operations in `z21_service.py`

**Frontend**:
- New `SpeedCorrelationChart.jsx` component (reusable pattern)
- New `SpeedTuningView.jsx` tab in Analytics (modular)
- Minimal changes to existing code (no 200+ line diffs)

### For Future Features

**Examples**:
- Add temperature tracking → new chart component + analytics endpoint
- Add train load monitoring → extend analytics service
- Add multi-user support → new auth router + service

**Maintenance**:
- Bug in Δt chart? → Fix in `DeltaTChart.jsx` (isolated)
- API change needed? → Modify `analytics.py` router only
- New decoder support? → Extend `z21_service.py` only

---

## Risk Mitigation

### Potential Issues

1. **Import path errors**: Lots of relative imports to update
   - Mitigation: Use IDE refactoring tools, test imports first

2. **Shared state breaking**: Props drilling might miss dependencies
   - Mitigation: Document props interface clearly, test each view

3. **WebSocket connection issues**: Refactoring might break real-time sync
   - Mitigation: Test WebSocket endpoints first, validate messages

4. **CSS/styling issues**: Component extraction might break Tailwind classes
   - Mitigation: Keep styling inline first, extract later if needed

### Safety Measures

- ✅ Git tags at every major step
- ✅ Branch-based workflow (not direct to develop)
- ✅ Testing after each substep
- ✅ Backup before starting (already on GitHub)
- ✅ Rollback documentation clear

---

## Timeline Estimate

**Conservative estimate** (with testing):
- Backend Phase 1: 6 hours (includes 2h contingency)
- Frontend Phase 2: 8 hours (includes 2h contingency)
- Integration Phase 3: 2 hours
- **Total**: ~16 hours (~2 full working days)

**Optimistic estimate** (smooth execution):
- Backend: 4 hours
- Frontend: 6 hours
- Integration: 1 hour
- **Total**: ~11 hours (~1.5 working days)

**Recommendation**: Plan for 2-3 days (allows for unexpected issues + thorough testing)

---

## Decision Points

### Before Starting

**Questions to confirm**:
1. ✅ Agreed to refactor before speed tracking? (YES - user confirmed)
2. Start with backend or frontend first? (Recommend: backend first - API stable foundation)
3. Branch per phase or single refactor branch? (Recommend: single branch, tags for rollback)
4. Full E2E testing required before merge? (Recommend: YES - production system)

### During Refactor

**Checkpoints**:
- After backend routers: Does backend start? All endpoints respond?
- After backend services: Logic working correctly? Tests passing?
- After frontend charts: Charts render? Data displayed correctly?
- After frontend views: Tabs functional? State management working?

**Go/No-Go criteria**:
- All tests passing → Continue
- Breaking changes found → Fix immediately or rollback
- Performance regression > 20% → Investigate before proceeding

---

## Success Criteria

**Refactor complete when**:
1. ✅ All endpoints functional (27 endpoints working)
2. ✅ Frontend builds without errors
3. ✅ Analytics dashboard fully functional (3 tabs, 4 charts)
4. ✅ WebSocket real-time sync working
5. ✅ No performance regressions
6. ✅ Code structure matches target architecture
7. ✅ Documentation updated
8. ✅ Merged to develop branch

**Then ready for**:
- Speed tracking implementation (Phase 1 - v1.3)
- Clean, modular codebase for future features
- Easier onboarding for new contributors
