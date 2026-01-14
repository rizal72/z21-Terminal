# Reports Tab - Analytics Dashboard

**Status**: ✅ MVP Completato (2026-01-14)
**Version**: v1.2

## Overview

Reports tab fornisce analisi session-by-session per identificare cambiamenti nel comportamento delle locomotive nel tempo. Risponde alla domanda: **"Quando il comportamento di loco 7 è cambiato da slower (dT positivo) a faster (dT negativo)?"**

## Architecture

**3-tab layout**: Current | Overview | **Reports**

- **Current**: Dati sessione corrente (real-time)
- **Overview**: Aggregati storici (cumulative)
- **Reports**: Analisi per sessione (historical trend)

## Components

### 1. Session History Table

**Location**: `web/src/components/AnalyticsPanel.jsx` lines 1088-1168

**Features**:
- Mostra ultime 30 sessioni validate (escluse sessioni running con `end_time = NULL`)
- Colonne dinamiche basate su consist configurati
- Color-coded avg Δt: verde (<1.0s), ambra (1.0-1.5s), rosso (≥1.5s)
- Clickable rows → apre Session Detail Modal
- Consist filter: "All" mostra tutte sessioni con N/A per consist non girato, "C10"/"C11" filtra via sessioni senza quel consist

**Table Columns**:
- Session ID (font-mono)
- Date (YYYY-MM-DD)
- Duration (HH:MM:SS)
- Events (total delta_t count)
- **Per consist** (dynamic):
  - CXX Avg Δt (seconds, color-coded)
  - CXX Synced% (percentage)

**Session Filtering Logic**:
```javascript
// filteredReportsSessions useMemo
if (consistFilter === 'all') return reportsData.sessions;
return reportsData.sessions.filter(session =>
  session.consists?.[String(consistFilter)] !== undefined
);
```

**Critical**: `String(consistFilter)` conversion necessaria perché backend ritorna consist IDs come stringhe nel JSON, ma frontend usa numeri per filtri.

### 2. Historical Trend Chart

**Location**: `web/src/components/AnalyticsPanel.jsx` lines 1170-1240

**Features**:
- LineChart con X-axis = date, Y-axis = avg Δt (seconds)
- Reference lines: 0 (green), ±1.0 (amber), ±1.5 (red)
- Dynamic lines per consist (color-coded)
- Clickable points → apre Session Detail Modal
- Consist filter: mostra solo line del consist selezionato
- Custom tooltip (inline component)

**Chart Data Structure**:
```javascript
reportsChartData = [
  {
    session_id: "20260113_151319",
    date: "2026-01-13",
    timestamp: 1768313599.470149,
    avg_delta_t_c10: 0.92,   // null se consist non girato
    avg_delta_t_c11: -0.64   // null se consist non girato
  },
  // ...
]
```

**Line Configuration**:
- `dataKey`: `avg_delta_t_c${cid}` (dynamic)
- `stroke`: getConsistStrokeColor() - cyclic palette
- `strokeWidth`: 2
- `dot`: { r: 5 }
- `activeDot`: { r: 7 }
- `connectNulls`: false (evita linee false tra gap)
- `name`: `C${cid}` (per tooltip)

### 3. Session Detail Modal

**Location**: `web/src/components/AnalyticsPanel.jsx` lines 1247-1349

**Features**:
- z-index 60 (sopra main Analytics modal z-50)
- Session metadata grid: ID, Date, Duration, Total Events
- Per-consist breakdown cards:
  - **Left column**: Total crossings, Avg Δt (color-coded), Range (min/max), Trend badge
  - **Right column**: Status distribution (SYNCED/WARNING/CRITICAL con colored dots e percentuali)
- Interpretation guide con bullet points
- Click backdrop o X button per chiudere

**Trend Badges**:
- LEAD FASTER (blue): avg_delta_t > 0.2
- REAR FASTER (purple): avg_delta_t < -0.2
- BALANCED (gray): -0.2 ≤ avg_delta_t ≤ 0.2

## Backend API

### Endpoint: `/api/analytics/reports`

**File**: `backend/main.py` lines 2092-2250

**Parameters**:
- `limit` (int, default 30): Max sessions to return
- `consist_filter` (int, optional): Filter by consist ID

**Response Structure**:
```json
{
  "sessions": [
    {
      "id": "20260113_151319",
      "date": "2026-01-13",
      "start_time": 1768313599.470149,
      "end_time": 1768313724.9677594,
      "duration_seconds": 125,
      "duration_formatted": "00:02:05",
      "total_events": 24,
      "consists": {
        "11": {
          "total_crossings": 6,
          "avg_delta_t": -0.102,
          "min_delta_t": -1.783,
          "max_delta_t": 2.349,
          "trend": "BALANCED",
          "synced_count": 4,
          "warning_count": 0,
          "critical_count": 2,
          "synced_percent": 66.7
        }
      }
    }
  ]
}
```

**Logic**:
1. Query validated sessions (`WHERE validated = 1 AND end_time IS NOT NULL`)
2. Order by `start_time DESC LIMIT {limit}`
3. For each session:
   - Query all `delta_t` events
   - Parse JSON data, group by `consist_id`
   - Calculate per-consist statistics:
     - `avg_delta_t`: `mean(delta_t_values)`
     - `min_delta_t`, `max_delta_t`
     - Status counts: `SYNCED` (<1.0s), `WARNING` (1.0-1.5s), `CRITICAL` (≥1.5s)
     - `synced_percent`: `(synced_count / total_crossings) * 100`
     - `trend`: Based on avg_delta_t thresholds (±0.2)
4. Format duration as HH:MM:SS
5. Return JSON response

**Helper Function**: `format_duration_hms()` (line 1701)

**Critical**: Consist IDs sono stringhe nel JSON (`"10"`, `"11"`) perché `str(consist_id)` usato nel dict (line 2214).

## State Management

**File**: `web/src/components/AnalyticsPanel.jsx`

**State Variables** (lines 81-84):
```javascript
const [reportsData, setReportsData] = useState(null);
const [selectedSession, setSelectedSession] = useState(null);
const [showSessionDetail, setShowSessionDetail] = useState(false);
```

**Data Loader** (lines 236-275):
```javascript
const loadReportsData = async () => {
  // Fetch /api/analytics/reports
  // Validate response structure
  // Ensure consists object exists for each session
  setReportsData(validatedData);
};
```

**Effects**:
- Load data on `viewMode` change to 'reports'
- Reload on `consistFilter` change (only in Reports mode)

**Memoized Data**:
- `reportsChartData`: Transform sessions to chart format (line 546)
- `filteredReportsSessions`: Filter sessions by consist (line 563)

## Critical Fixes Applied

### 1. Fragment Import (commit `1d97e9c`)
**Problem**: `React.Fragment` undefined (React not imported)
**Solution**: Import `Fragment` from 'react'

### 2. Rules of Hooks (commit `70e29af`)
**Problem**: `useMemo` inside IIFE violates Rules of Hooks
**Solution**: Move `reportsChartData` useMemo to component top level

### 3. Exclude Overview Charts (commit `e75a10b`)
**Problem**: Analytics View rendered anche in Reports mode (duplicate charts)
**Solution**: Add `viewMode !== 'reports'` to render condition

### 4. Helper Functions Null Safety (commit `fedf43c`)
**Problem**: `Object.keys(consistConfig)` crash quando `consistConfig` undefined
**Solution**: Add `const config = consistConfig || {}` in all helpers:
- `getAddressFilter`
- `getConsistStrokeColor`
- `getConsistColorClass`
- `getConsistBgClass`

### 5. TrackingConfig Load Race Condition (commits `93fc99b`, `e46e1f7`)
**Problem**: Reports tab rendered before `trackingConfig` loaded → `Object.keys(undefined)` crash
**Solutions**:
- Add `trackingConfig?.consists` check to Reports render condition
- Show "Loading configuration..." spinner durante load
- Validate `trackingConfig` fetch response structure

### 6. Object.keys Null Safety (commit `4acb406`)
**Problem**: `Object.keys(trackingConfig.consists)` in useMemo e JSX senza protezione
**Solution**: Add `|| {}` fallback a TUTTI gli `Object.keys(trackingConfig.consists)` (7 occorrenze)

### 7. Consist ID Type Mismatch (commit `3044810`)
**Problem**: Table mostra N/A per tutti i consist quando filter="All"
**Root Cause**:
- `trackingConfig.consists` keys sono NUMERI (dopo `Object.keys().map(Number)`)
- `session.consists` keys sono STRINGHE (backend usa `str(consist_id)`)
- Lookup `session.consists[cid]` con `cid` numerico fallisce

**Solution**: Convert `cid` to string before accessing:
```javascript
const stats = session.consists?.[String(cid)];
```

### 8. Session Filtering by Consist (commit `e54eb23`)
**Problem**: Quando filtro C10/C11, tabella mostra ancora tutte le sessioni con N/A
**Solution**: Add `filteredReportsSessions` useMemo che filtra via sessioni senza consist selezionato:
```javascript
return reportsData.sessions.filter(session =>
  session.consists?.[String(consistFilter)] !== undefined
);
```

### 9. Custom Tooltip (commit `cb66119`)
**Problem**: Default Recharts tooltip mostra solo primo consist quando hover
**Solution**: Custom tooltip component con `payload.map()` per mostrare tutti valori non-null

## Known Limitations

### Multiple Sessions Same Date

**Issue**: Quando più sessioni diverse girano nello stesso giorno (es. C10 mattina, C11 sera), il chart mostra DUE PUNTI sulla stessa data ma tooltip mostra solo UNA sessione.

**Root Cause**:
- Chart data structure: 1 row per sessione
- X-axis: `dataKey="date"` (non session_id)
- Due sessioni stesso giorno = due righe con stesso `date` value
- Recharts tooltip mostra solo payload della riga su cui passi mouse

**Example** (2026-01-12):
- Session 1 (mattina): `{ date: "2026-01-12", avg_delta_t_c10: 0.92, avg_delta_t_c11: null }`
- Session 2 (sera): `{ date: "2026-01-12", avg_delta_t_c10: null, avg_delta_t_c11: -0.64 }`
- Chart mostra 2 punti verticalmente allineati
- Tooltip mostra solo session su cui hover

**Possible Solutions** (future enhancement):

**Option A**: Aggregate by date (backend change)
- Endpoint `/api/analytics/reports?aggregate_by=date`
- Return: 1 row per date con avg di tutte sessioni quel giorno
- Pro: Tooltip mostra sempre tutti consist per data
- Con: Perde granularità session-level (non puoi clickare session specifica)

**Option B**: Custom tooltip with date-based lookup
- Tooltip fetches ALL sessions for hovered date
- Shows all consists from all sessions
- Pro: Mantiene session-level data
- Con: Complesso, richiede accesso a `reportsData.sessions` in tooltip

**Option C**: Group sessions by date in chart data
- Transform `reportsChartData` to aggregate sessions per date
- Pro: Semplice frontend-only fix
- Con: Stesso problema di Option A (perde granularità)

**Decision**: Posticipato a future release. Frequency: bassa (raramente 2+ sessioni stesso giorno con consist diversi).

## Testing

### Manual Test Checklist

**Reports Tab Navigation**:
- [ ] Click Reports button → mostra Reports content
- [ ] Keyboard Right arrow da Overview → apre Reports
- [ ] Keyboard Left arrow da Reports → torna Overview

**Session History Table**:
- [ ] Table mostra 30 sessioni (o meno se DB ha meno)
- [ ] Session count header corretto
- [ ] Colonne dinamiche basate su consist configurati
- [ ] Filter "All": mostra tutte sessioni con colonne C10+C11
- [ ] Filter "C10": mostra solo sessioni con C10, solo colonne C10
- [ ] Filter "C11": mostra solo sessioni con C11, solo colonne C11
- [ ] Session count si aggiorna con filter
- [ ] Avg Δt color-coded: verde/ambra/rosso
- [ ] Click row → apre Session Detail Modal
- [ ] N/A mostrato solo quando consist non ha girato in quella sessione

**Historical Trend Chart**:
- [ ] Chart mostra line per ogni consist
- [ ] Reference lines visibili (0, ±1.0, ±1.5)
- [ ] X-axis labels leggibili (rotated -45°)
- [ ] Y-axis label "Avg Δt (seconds)"
- [ ] Filter "All": mostra entrambe line C10+C11
- [ ] Filter "C10": mostra solo line C10
- [ ] Filter "C11": mostra solo line C11
- [ ] Tooltip mostra consist name e value
- [ ] Click point → apre Session Detail Modal
- [ ] connectNulls=false evita linee false tra gap

**Session Detail Modal**:
- [ ] Modal apre su click row o point
- [ ] z-index corretto (sopra main modal)
- [ ] Session metadata completa (ID, Date, Duration, Events)
- [ ] Per-consist breakdown mostra tutti consist della sessione
- [ ] Statistics correct (Total crossings, Avg Δt, Range, Trend)
- [ ] Status distribution percentages correct
- [ ] Color coding consistente (consist colors, status dots)
- [ ] Interpretation guide visibile
- [ ] Click backdrop → chiude modal
- [ ] Click X button → chiude modal

**Edge Cases**:
- [ ] Empty database → mostra empty state con icon
- [ ] Sessione con 1 solo consist → colonna altro consist N/A
- [ ] Filtered consist con 0 sessioni → empty state
- [ ] API fetch failure → mostra error banner
- [ ] TrackingConfig load race → mostra spinner "Loading configuration..."

## Performance

**Data Volume**: 30 sessions default (configurable via `?limit=` param)

**API Response Size**: ~15-30KB JSON (dipende da eventi per sessione)

**Render Performance**:
- Chart: 30 datapoints × 2 lines = 60 elements (negligible)
- Table: 30 rows × 6 columns = 180 cells (negligible)

**Optimizations**:
- `useMemo` per chart data transform
- `useMemo` per session filtering
- Backend pre-aggregates statistics (non calcolo frontend)

## Future Enhancements

### High Priority

**1. Speed Setting Tracking** (v1.3)
- Track user-set speed (not auto-sync) per session/event
- Correlate speed with locomotive behavior (loco 7 behaves differently at different speeds)
- Options: Session-level (simple), Event-level (complete), Separate events (clean)

**2. Multi-Session Same Date Tooltip** (v1.2.1)
- Implement Option B: Custom tooltip with date-based lookup
- Show ALL consists from ALL sessions for hovered date

### Medium Priority

**3. Sortable Table Columns** (v1.3)
- Click column header to sort ascending/descending
- Multi-column sort with Shift+Click

**4. Pagination / Load More** (v1.3+)
- Initial load: 30 sessions
- "Load More" button fetches next 30
- Infinite scroll alternative

**5. Export to CSV** (v1.3+)
- Export table data as CSV file
- Include all sessions (not just visible 30)

### Low Priority

**6. Date Range Filter** (v1.4)
- Date picker: start/end date
- Filter sessions by date range

**7. Session Comparison** (v1.4)
- Select 2 sessions for side-by-side comparison
- Highlight differences

**8. Full Mobile Support** (v1.5)
- Responsive table (card layout su mobile)
- Touch gestures per chart zoom/pan

## Documentation Files

**Related Documentation**:
- `docs/Z21_PROTOCOL.md` - Z21 LAN protocol details
- `docs/JMRI_INTEGRATION.md` - JMRI roster/consist integration
- `docs/CONSIST_ROSTER.md` - Locomotive roster + consist config
- `docs/WEB_DASHBOARD.md` - Web stack, features, workflow
- `docs/COMPUTER_VISION.md` - YOLO tracking, gate detection
- `docs/CONSIST_MAPPING.md` - Lead/Rear → Reference/Adjust logic
- `docs/CONFIG_REFACTOR.md` - Config.json structure refactoring
- `docs/ANALYTICS.md` - Analytics Dashboard (Current/Overview modes)
- **`docs/REPORTS_TAB.md`** - This file (Reports tab specifics)

**Note**: `docs/` folder è gitignored per default. Se vuoi committare documentazione, rimuovi da `.gitignore` o usa `git add -f docs/*.md`.

---

**Last Updated**: 2026-01-14
**Author**: Riccardo Sallusti + Claude Sonnet 4.5
