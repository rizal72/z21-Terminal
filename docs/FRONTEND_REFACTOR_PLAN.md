# Frontend Refactor Plan: AnalyticsPanel Modularization

## Executive Summary

**Current State**: `web/src/components/AnalyticsPanel.jsx` = 1684 lines, monolithic component
**Target State**: Modular architecture with chart components + tab views + utilities
**Estimated main component**: ~200-300 lines (state management only)

**Strategy**: Incremental extraction with testing after each phase
**Estimated Time**: 6-8 hours total (5 phases)

---

## Critical Context (⚠️ READ BEFORE ANY CHANGES)

**Analytics Dashboard took 200+ commits to work correctly.**

This refactoring MUST preserve:
1. ✅ All Current/Overview/Reports view differences (see Chart Analysis below)
2. ✅ Session breaks toggle + segmentation logic
3. ✅ Box-select zoom in Overview mode
4. ✅ Auto-scroll behavior in Current mode
5. ✅ Dynamic chart widths (horizontal scroll)
6. ✅ Duplicate Y-axis in Current mode (visible when scrolled)
7. ✅ Consist filtering (All/C10/C11/...)
8. ✅ Session filtering logic (`filterEventsBySession`)
9. ✅ Address filtering logic (`getAddressFilter`)

**Golden Rule**: If unsure, DON'T extract - keep in parent component.

---

## Current File Structure

```
AnalyticsPanel.jsx (1684 lines)
├── Constants (lines 5-27)
│   ├── LOCO_COLORS
│   ├── CONSIST_COLOR_PALETTE
│   ├── CONSIST_COLOR_CLASSES
│   ├── CONSIST_BG_CLASSES
│   ├── TOOLTIP_STYLES
│   └── CHART_AXIS_STYLES
│
├── Helper Functions (lines 30-85)
│   ├── filterEventsBySession()
│   ├── getAddressFilter()
│   ├── getConsistStrokeColor()
│   ├── getConsistColorClass()
│   ├── getConsistBgClass()
│   ├── formatDeltaT()
│   └── formatOperatingTime()
│
├── Component State (lines 88-132)
│   ├── viewMode: 'current' | 'overview' | 'reports'
│   ├── cumulativeData (delta_t + yolo_performance events)
│   ├── currentSession (metadata)
│   ├── locoStats (operating time)
│   ├── reportsData (session history)
│   ├── consistFilter: 'all' | 10 | 11 | ...
│   ├── trackingConfig (consists, timing_thresholds)
│   ├── zoomDomain (box-select state)
│   ├── showSessionBreaks (toggle)
│   └── collapsedPanels (accordion state)
│
├── Effects & API Calls (lines 135-302)
│   ├── Desktop enforcement check
│   ├── Body scroll prevention
│   ├── Keyboard shortcuts (Arrow keys, 1-3 keys)
│   ├── Load tracking config (on mount)
│   ├── Load current session (on mount)
│   ├── Load cumulative data (on mount + interval)
│   ├── Load reports data (on viewMode change)
│   ├── Load locomotive stats (on mount)
│   └── Auto-scroll to end (on data change)
│
├── Event Handlers (lines 304-450)
│   ├── Box-select zoom handlers (Overview only)
│   ├── Session break computation (useMemo)
│   └── Data preparation (useMemo)
│
├── Current/Overview Views (lines 452-1229)
│   ├── Stats Cards (3 cards - session-aware)
│   ├── Δt Trends Chart (LineChart with segments)
│   ├── FPS Chart (LineChart)
│   ├── Confidence Chart (BarChart - snapshot)
│   └── Operating Time Chart (BarChart - Overview only)
│
└── Reports Tab (lines 1230-1679)
    ├── Session History Table (30/50/100/200 rows)
    ├── Historical Trend Chart (LineChart - clickable)
    └── Session Detail Modal (per-consist breakdown)
```

---

## Chart Analysis (🔥 CRITICAL - Differences Between Views)

### 1. Δt Trends Chart (LineChart)
**Location**: Lines 924-1018
**Appears in**: Current + Overview (NOT Reports)

#### Critical Differences

| Feature | Current | Overview | Why Different |
|---------|---------|----------|---------------|
| **XAxis dataKey** | `time` | `index` | Readable timestamps vs compressed event numbers |
| **Scroll container** | `overflowX: auto` | `visible` | Horizontal scroll vs fit-to-width |
| **Chart width** | Dynamic (`length * 40, min 800`) | `100%` | Fixed width per event vs responsive |
| **Duplicate Y-axis** | ✅ Right side | ❌ None | Always visible when scrolling horizontally |
| **Stroke width** | 2px | 1.5px | Emphasis on recent data vs overview |
| **Dots** | `{ r: 4 }` | `false` | Visible data points vs smooth line |
| **Box-select zoom** | ❌ None | ✅ Mouse handlers | No zoom needed with scroll vs zoom for large datasets |
| **Auto-scroll ref** | ✅ `scrollRefSession` | ❌ None | Auto-scroll to latest event vs static view |

#### Shared Features (MUST preserve)
- Session breaks toggle (`showSessionBreaks`) - Segmented mode with `delta_t_c${id}_seg${idx}` dataKeys
- Reference lines: 0 (green), ±1.0 (amber), ±1.5 (red)
- Consist filtering (All/C10/C11/...)
- `connectNulls={true}` - Connect through natural nulls (other consist)
- Y-axis domain dynamic with 5% padding
- Stroke colors from `getConsistStrokeColor()`

#### Session Break Segmentation Logic (lines 323-425)
```javascript
// Detect session boundaries (gap > idle_timeout_seconds)
const eventSegments = events.map((e, i) => {
  if (i === 0) return 0;
  const prevTime = new Date(events[i-1].timestamp).getTime();
  const currTime = new Date(e.timestamp).getTime();
  const gap = (currTime - prevTime) / 1000;
  return gap > idle_timeout_seconds ? segments++ : segments;
});

// Build dataset with segmented dataKeys
chartData = events.map((e, i) => ({
  ...e,
  delta_t_c10_seg0: (consist === 10 && segment === 0) ? delta_t : null,
  delta_t_c10_seg1: (consist === 10 && segment === 1) ? delta_t : null,
  // ... for all consists + all segments
}));

// Render Lines (simple or segmented)
if (segmentCount === 0) {
  // SIMPLE: One Line per consist
  <Line dataKey={`delta_t_c${consistId}`} connectNulls={true} />
} else {
  // SEGMENTED: One Line per segment (first has legend, rest legendType="none")
  Array.from({ length: segmentCount }, (_, segIdx) => (
    <Line
      dataKey={`delta_t_c${consistId}_seg${segIdx}`}
      legendType={segIdx === 0 ? undefined : 'none'}
      connectNulls={true}
    />
  ))
}
```

**⚠️ DO NOT EXTRACT** - Keep segmentation logic in AnalyticsPanel (too complex)

---

### 2. FPS Chart (LineChart)
**Location**: Lines 1088-1113
**Appears in**: Current + Overview (NOT Reports)

#### Critical Differences

| Feature | Current | Overview | Why Different |
|---------|---------|----------|---------------|
| **XAxis dataKey** | `time` | `index` | Same reason as Δt Chart |
| **Scroll wrapper** | ✅ Div with `overflow-x-auto` | ❌ None | Horizontal scroll vs fit-to-width |
| **Chart width** | Dynamic (`length * 60, min 800`) | `100%` | Fixed width per sample vs responsive |
| **Duplicate Y-axis** | ✅ Right side | ❌ None | Same reason as Δt Chart |
| **Auto-scroll ref** | ✅ `scrollRefFps` | ❌ None | Auto-scroll to latest sample vs static view |

#### Shared Features
- Fixed Y domain `[0, 140]` (FPS range)
- Reference line: 30 FPS target (green dashed)
- Single line (no segmentation, no consist filtering)
- Stroke: green (`#10b981`)
- Stroke width: 2px (both views)
- Dots: `{ r: 3 }` (both views)

#### FPS Average Badge (lines 1030-1049)
```javascript
// Visible in both Current and Overview
// Current mode: session average or N/A if not loaded
// Overview mode: global average (all events)
// Idle filtering: Excludes FPS ≤ 10 to measure real tracking performance
const fpsAvg = useMemo(() => {
  const events = viewMode === 'current'
    ? filterEventsBySession(cumulativeData.yolo_performance, viewMode, currentSession)
    : cumulativeData?.yolo_performance || [];

  if (events.length === 0) return null;
  const fps = events.map(e => e.fps).filter(f => f > 10); // Idle filter
  return fps.length > 0 ? (fps.reduce((a, b) => a + b, 0) / fps.length).toFixed(1) : null;
}, [cumulativeData, viewMode, currentSession]);

// Badge position: top-right of chart container
<div className="absolute top-4 right-4 bg-slate-800/90 px-3 py-1.5 rounded-lg border border-slate-600">
  <span className="text-sm text-slate-300">
    FPS avg: <span className="font-semibold text-green-400">{fpsAvg || 'N/A'}</span>
  </span>
</div>
```

---

### 3. Confidence Chart (BarChart)
**Location**: Lines 1134-1175
**Appears in**: Current + Overview (NOT Reports)

#### Differences
❌ **NONE** - Same rendering in both views

#### Session Filtering
✅ Uses `filterEventsBySession(cumulativeData.yolo_performance, viewMode, currentSession)`

#### Address Filtering
✅ Uses `getAddressFilter(consistFilter, trackingConfig.consists)`

#### ⚠️ DRY VIOLATION (lines 1134-1150 + 1160-1173)
Data preparation logic duplicated:
1. Lines 1134-1150: Compute data for BarChart
2. Lines 1160-1173: Re-compute SAME data for Cell colors

**Refactoring opportunity**: Extract data preparation to useMemo, pass to both BarChart data and Cell mapping.

---

### 4. Operating Time Chart (BarChart)
**Location**: Lines 1204-1221
**Appears in**: Overview ONLY (line 1184)

#### Rationale
Operating Time = cumulative aging/maintenance metric, NOT session metric.

#### Features
- Y-axis: Minutes (tickFormatter divides seconds by 60)
- Tooltip: `formatOperatingTime()` ("Xh Ym")
- Bars: Color-coded by LOCO_COLORS
- Address filtering: ✅ Uses `getAddressFilter()`
- No session filtering (always shows global stats)

---

### 5. Historical Trend Chart (LineChart - Reports Tab)
**Location**: Lines 1439-1522
**Appears in**: Reports tab ONLY

#### Unique Features
- **Click handler**: Opens Session Detail modal (lines 1441-1450)
- **Custom tooltip**: Shows all consists for date (lines 1475-1497)
- **XAxis**: `index` with date formatter (DD-MM HH:MM) (lines 1461-1467)
- **connectNulls**: `false` (vs `true` in Δt Trends) - Don't connect across missing sessions
- **Dots**: `{ r: 5 }`, `activeDot: { r: 7 }` (larger than Δt Trends)
- **No box-select zoom** (static chart)
- **No session breaks** (each point = one session)

#### Data Structure
```javascript
reportsChartData = sessions.map((s, idx) => ({
  index: idx + 1,  // 1-based index for X-axis
  session_id: s.id,
  date: s.date,  // DD-MM-YYYY
  time: s.start_time.split(' ')[1].substring(0, 5),  // HH:MM
  avg_delta_t_c10: s.consists?.['10']?.avg_delta_t,
  avg_delta_t_c11: s.consists?.['11']?.avg_delta_t,
  // ... for all consists
}));
```

---

## Refactoring Constraints (⚠️ MUST FOLLOW)

### 1. Chart Components MUST Accept These Props

```typescript
interface ChartCommonProps {
  viewMode: 'current' | 'overview' | 'reports';  // CRITICAL for conditional rendering
  consistFilter: 'all' | number;                  // Filter by consist
  trackingConfig: {                               // Consist definitions + thresholds
    consists: Record<number, ConsistConfig>;
    timing_thresholds: { normal: number; warning: number; };
  };
}

interface DeltaTChartProps extends ChartCommonProps {
  chartData: Array<any>;          // Pre-processed (with segments if enabled)
  segmentCount: number;           // 0 = simple mode, >0 = segmented mode
  yDomain: [number, number];      // Dynamic Y-axis domain
  showSessionBreaks: boolean;     // Session breaks toggle state

  // Current mode only
  scrollRef?: React.RefObject;    // Auto-scroll ref (optional)

  // Overview mode only
  onMouseDown?: (e) => void;      // Box-select handlers (optional)
  onMouseMove?: (e) => void;
  onMouseUp?: (e) => void;
  onDoubleClick?: (e) => void;
  refAreaLeft?: number | null;    // Box-select state (optional)
  refAreaRight?: number | null;
  zoomDomain?: { x: [number, number]; y: [number, number]; } | null;
}

interface FPSChartProps extends ChartCommonProps {
  chartData: Array<any>;
  fpsAvg: number | null;          // Average FPS badge value

  // Current mode only
  scrollRef?: React.RefObject;    // Auto-scroll ref (optional)
}

interface ConfidenceChartProps extends ChartCommonProps {
  chartData: Array<any>;          // Pre-processed confidence data
  // No viewMode differences (same rendering both views)
}

interface OperatingTimeChartProps {
  locoStats: Array<any>;          // Locomotive operating time stats
  consistFilter: 'all' | number;
  trackingConfig: { consists: Record<number, ConsistConfig>; };
  // No viewMode prop (Overview only)
}

interface HistoricalTrendChartProps {
  reportsChartData: Array<any>;   // Session history data
  consistFilter: 'all' | number;
  trackingConfig: { consists: Record<number, ConsistConfig>; };
  onSessionClick: (session: any) => void;  // Click handler for modal
}
```

### 2. Width Calculation MUST Be Dynamic

```javascript
// Δt Trends Chart
const chartWidth = viewMode === 'current'
  ? Math.max(chartData.length * 40, 800)  // 40px per event, min 800px
  : '100%';  // Fit to container

// FPS Chart
const chartWidth = viewMode === 'current'
  ? Math.max(chartData.length * 60, 800)  // 60px per sample, min 800px
  : '100%';  // Fit to container
```

**⚠️ DO NOT HARDCODE** - Width depends on data length

### 3. Scroll Refs MUST Be Optional Props

```javascript
// In AnalyticsPanel (parent)
const scrollRefSession = useRef(null);
const scrollRefFps = useRef(null);

// Pass to chart components
<DeltaTChart
  scrollRef={viewMode === 'current' ? scrollRefSession : undefined}
  // ... other props
/>

// In chart component
<div ref={props.scrollRef} style={{ overflowX: viewMode === 'current' ? 'auto' : 'visible' }}>
  <ResponsiveContainer width={chartWidth} height={400}>
    {/* ... chart */}
  </ResponsiveContainer>
</div>
```

### 4. Session Breaks Logic STAYS in Parent

**DO NOT EXTRACT** - Too complex, too many edge cases

Parent computes:
- `eventSegments` array (segment number per event)
- `segmentCount` (total number of segments)
- `chartData` with segmented dataKeys (`delta_t_c10_seg0`, etc.)

Child receives:
- `chartData` (pre-processed)
- `segmentCount` (0 = simple, >0 = segmented)
- `showSessionBreaks` (toggle state)

### 5. Box-Select Zoom Handlers MUST Be Props

```javascript
// In AnalyticsPanel (parent)
const [refAreaLeft, setRefAreaLeft] = useState(null);
const [refAreaRight, setRefAreaRight] = useState(null);
const [zoomDomain, setZoomDomain] = useState(null);

const handleMouseDown = (e) => { /* ... */ };
const handleMouseMove = (e) => { /* ... */ };
const handleMouseUp = (e) => { /* ... */ };
const handleDoubleClick = (e) => { /* ... */ };

// Pass to chart (Overview only)
<DeltaTChart
  onMouseDown={viewMode === 'overview' ? handleMouseDown : undefined}
  onMouseMove={viewMode === 'overview' ? handleMouseMove : undefined}
  onMouseUp={viewMode === 'overview' ? handleMouseUp : undefined}
  onDoubleClick={viewMode === 'overview' ? handleDoubleClick : undefined}
  refAreaLeft={refAreaLeft}
  refAreaRight={refAreaRight}
  zoomDomain={zoomDomain}
  // ... other props
/>
```

---

## Phase 1: Extract Constants (30 min)

### Goal
Move constants to `web/src/constants/analyticsConstants.js`

### Files to Create
```
web/src/constants/analyticsConstants.js
```

### Constants to Extract
```javascript
// LOCO_COLORS (lines 5-10)
export const LOCO_COLORS = {
  1: '#FFFF00',  // Yellow (Gr675 017)
  5: '#FF8000',  // Orange (D645 014)
  7: '#00FF00',  // Green (E656 239)
  8: '#FF0000',  // Red (E444 056)
};

// CONSIST_COLOR_PALETTE (line 13)
export const CONSIST_COLOR_PALETTE = ['#d946ef', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

// CONSIST_COLOR_CLASSES (line 14)
export const CONSIST_COLOR_CLASSES = ['text-fuchsia-400', 'text-blue-400', 'text-green-400', 'text-amber-400', 'text-red-400', 'text-purple-400'];

// CONSIST_BG_CLASSES (line 15)
export const CONSIST_BG_CLASSES = ['bg-fuchsia-600', 'bg-blue-600', 'bg-green-600', 'bg-amber-600', 'bg-red-600', 'bg-purple-600'];

// TOOLTIP_STYLES (lines 18-22)
export const TOOLTIP_STYLES = {
  contentStyle: { backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' },
  labelStyle: { color: '#e2e8f0' },
  itemStyle: { color: '#e2e8f0' }
};

// CHART_AXIS_STYLES (lines 24-27)
export const CHART_AXIS_STYLES = {
  grid: { strokeDasharray: '3 3', stroke: '#374151' },
  axis: { stroke: '#9CA3AF' }
};
```

### Update AnalyticsPanel.jsx
```javascript
import {
  LOCO_COLORS,
  CONSIST_COLOR_PALETTE,
  CONSIST_COLOR_CLASSES,
  CONSIST_BG_CLASSES,
  TOOLTIP_STYLES,
  CHART_AXIS_STYLES
} from '../constants/analyticsConstants';
```

### Testing
- ✅ All charts render correctly
- ✅ Colors match previous version
- ✅ Tooltips styled correctly

### Commit
```
refactor(frontend): extract analytics constants (Phase 1)

- Created web/src/constants/analyticsConstants.js
- Extracted LOCO_COLORS, CONSIST_COLOR_PALETTE, TOOLTIP_STYLES, CHART_AXIS_STYLES
- Updated AnalyticsPanel.jsx imports
- Zero visual changes, ready for Phase 2
```

---

## Phase 2: Extract Helper Functions (1 hour)

### Goal
Move pure helper functions to `web/src/utils/analyticsHelpers.js`

### Files to Create
```
web/src/utils/analyticsHelpers.js
```

### Helpers to Extract (lines 30-85)

```javascript
import { CONSIST_COLOR_PALETTE, CONSIST_COLOR_CLASSES, CONSIST_BG_CLASSES } from '../constants/analyticsConstants';

// Session filtering (lines 30-35)
export const filterEventsBySession = (events, viewMode, currentSession) => {
  if (viewMode === 'current' && currentSession && events) {
    return events.filter(e => e.session_id === currentSession.session_id);
  }
  return events || [];
};

// Address filtering (lines 38-45)
export const getAddressFilter = (consistFilter, consistConfig) => {
  const config = consistConfig || {};
  if (consistFilter === 'all') {
    return Object.values(config).flatMap(c => c.addresses);
  }
  return config[consistFilter]?.addresses || [];
};

// Consist stroke color (lines 48-53)
export const getConsistStrokeColor = (consistId, consistConfig) => {
  const config = consistConfig || {};
  const consistIds = Object.keys(config).map(Number).sort((a, b) => a - b);
  const index = consistIds.indexOf(consistId);
  return index >= 0 ? CONSIST_COLOR_PALETTE[index % CONSIST_COLOR_PALETTE.length] : '#9CA3AF';
};

// Consist text color class (lines 56-62)
export const getConsistColorClass = (consistFilter, consistConfig, defaultColor = 'text-white') => {
  if (consistFilter === 'all') return defaultColor;
  const config = consistConfig || {};
  const consistIds = Object.keys(config).map(Number).sort((a, b) => a - b);
  const index = consistIds.indexOf(consistFilter);
  return index >= 0 ? CONSIST_COLOR_CLASSES[index % CONSIST_COLOR_CLASSES.length] : defaultColor;
};

// Consist background class (lines 65-70)
export const getConsistBgClass = (consistId, consistConfig) => {
  const config = consistConfig || {};
  const consistIds = Object.keys(config).map(Number).sort((a, b) => a - b);
  const index = consistIds.indexOf(consistId);
  return index >= 0 ? CONSIST_BG_CLASSES[index % CONSIST_BG_CLASSES.length] : 'bg-slate-600';
};

// Format delta t with sign (lines 73-77)
export const formatDeltaT = (value, decimals = 2) => {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}`;
};

// Format operating time (lines 80-85)
export const formatOperatingTime = (seconds) => {
  if (!seconds || seconds === 0) return '0h 0m';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
};
```

### Update AnalyticsPanel.jsx
```javascript
import {
  filterEventsBySession,
  getAddressFilter,
  getConsistStrokeColor,
  getConsistColorClass,
  getConsistBgClass,
  formatDeltaT,
  formatOperatingTime
} from '../utils/analyticsHelpers';
```

### Testing
- ✅ All filtering works correctly (consist filters, session filters)
- ✅ Colors assigned correctly
- ✅ Formatting correct (Δt with sign, operating time "Xh Ym")

### Commit
```
refactor(frontend): extract analytics helper functions (Phase 2)

- Created web/src/utils/analyticsHelpers.js
- Extracted 7 pure helper functions (filtering, colors, formatting)
- Updated AnalyticsPanel.jsx imports
- Zero behavior changes, ready for Phase 3
```

---

## Phase 3: Extract Chart Components (3-4 hours)

### Goal
Create standalone chart components preserving ALL Current/Overview/Reports differences

### Files to Create
```
web/src/components/charts/DeltaTChart.jsx       (~200 lines)
web/src/components/charts/FPSChart.jsx          (~150 lines)
web/src/components/charts/ConfidenceChart.jsx   (~100 lines)
web/src/components/charts/OperatingTimeChart.jsx (~80 lines)
web/src/components/charts/HistoricalTrendChart.jsx (~100 lines)
```

### Phase 3.1: DeltaTChart.jsx (1.5 hours)

**⚠️ MOST COMPLEX CHART** - Has session breaks, box-select zoom, duplicate Y-axis

#### Component Structure
```javascript
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, ReferenceArea } from 'recharts';
import { TOOLTIP_STYLES, CHART_AXIS_STYLES } from '../../constants/analyticsConstants';
import { getConsistStrokeColor, formatDeltaT } from '../../utils/analyticsHelpers';

export default function DeltaTChart({
  // Data
  chartData,
  segmentCount,
  yDomain,

  // Config
  viewMode,
  consistFilter,
  trackingConfig,
  showSessionBreaks,

  // Current mode
  scrollRef,

  // Overview mode (box-select)
  onMouseDown,
  onMouseMove,
  onMouseUp,
  onDoubleClick,
  refAreaLeft,
  refAreaRight,
  zoomDomain
}) {
  // Width calculation
  const chartWidth = viewMode === 'current'
    ? Math.max(chartData.length * 40, 800)
    : '100%';

  // Render
  return (
    <div
      ref={scrollRef}
      style={{ width: '100%', overflowX: viewMode === 'current' ? 'auto' : 'visible' }}
    >
      <ResponsiveContainer width={chartWidth} height={400}>
        <LineChart
          data={chartData}
          onMouseDown={onMouseDown}
          onMouseMove={onMouseMove}
          onMouseUp={onMouseUp}
          onDoubleClick={onDoubleClick}
        >
          <CartesianGrid {...CHART_AXIS_STYLES.grid} />

          {/* XAxis: time in Current, index in Overview */}
          <XAxis
            dataKey={viewMode === 'current' ? 'time' : 'index'}
            {...CHART_AXIS_STYLES.axis}
          />

          {/* Left Y-axis */}
          <YAxis
            yAxisId="left"
            {...CHART_AXIS_STYLES.axis}
            domain={yDomain}
            allowDataOverflow={true}
            tickFormatter={(value) => formatDeltaT(value)}
            label={{ value: 'Δt (seconds)', angle: 90, position: 'insideLeft', fill: '#9CA3AF' }}
          />

          {/* Right Y-axis (Current mode only) */}
          {viewMode === 'current' && (
            <YAxis
              yAxisId="right"
              orientation="right"
              {...CHART_AXIS_STYLES.axis}
              domain={yDomain}
              allowDataOverflow={true}
              tickFormatter={(value) => formatDeltaT(value)}
              label={{ value: 'Δt (seconds)', angle: 90, position: 'insideRight', fill: '#9CA3AF' }}
            />
          )}

          {/* Tooltip */}
          <Tooltip
            {...TOOLTIP_STYLES}
            formatter={(value) => value !== null ? formatDeltaT(value) + 's' : 'N/A'}
          />

          {/* Reference lines */}
          <ReferenceLine yAxisId="left" y={0} stroke="#10b981" strokeDasharray="3 3" />
          <ReferenceLine yAxisId="left" y={trackingConfig.timing_thresholds?.normal || 1.0} stroke="#f59e0b" strokeDasharray="3 3" />
          <ReferenceLine yAxisId="left" y={-(trackingConfig.timing_thresholds?.normal || 1.0)} stroke="#f59e0b" strokeDasharray="3 3" />
          <ReferenceLine yAxisId="left" y={trackingConfig.timing_thresholds?.warning || 1.5} stroke="#ef4444" strokeDasharray="3 3" />
          <ReferenceLine yAxisId="left" y={-(trackingConfig.timing_thresholds?.warning || 1.5)} stroke="#ef4444" strokeDasharray="3 3" />

          {/* Dynamic lines: simple or segmented */}
          {Object.keys(trackingConfig.consists || {})
            .map(Number)
            .sort((a, b) => a - b)
            .filter(consistId => consistFilter === 'all' || consistFilter === consistId)
            .flatMap((consistId) => {
              // SIMPLE MODE
              if (segmentCount === 0) {
                return (
                  <Line
                    key={consistId}
                    yAxisId="left"
                    type="monotone"
                    dataKey={`delta_t_c${consistId}`}
                    stroke={getConsistStrokeColor(consistId, trackingConfig.consists)}
                    strokeWidth={viewMode === 'current' ? 2 : 1.5}
                    dot={viewMode === 'current' ? { r: 4 } : false}
                    name={trackingConfig.consists[consistId]?.name || `Consist ${consistId}`}
                    connectNulls={true}
                  />
                );
              }

              // SEGMENTED MODE
              return Array.from({ length: segmentCount }, (_, segIdx) => (
                <Line
                  key={`${consistId}_seg${segIdx}`}
                  yAxisId="left"
                  type="monotone"
                  dataKey={`delta_t_c${consistId}_seg${segIdx}`}
                  stroke={getConsistStrokeColor(consistId, trackingConfig.consists)}
                  strokeWidth={viewMode === 'current' ? 2 : 1.5}
                  dot={viewMode === 'current' ? { r: 4 } : false}
                  name={trackingConfig.consists[consistId]?.name || `Consist ${consistId}`}
                  legendType={segIdx === 0 ? undefined : 'none'}
                  connectNulls={true}
                />
              ));
            })}

          {/* ReferenceArea for box-select (Overview only) */}
          {refAreaLeft && refAreaRight && (
            <ReferenceArea
              yAxisId="left"
              x1={refAreaLeft}
              x2={refAreaRight}
              strokeOpacity={0.3}
              fill="#3b82f6"
              fillOpacity={0.3}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

#### Update AnalyticsPanel.jsx
```javascript
import DeltaTChart from './charts/DeltaTChart';

// Replace LineChart rendering (lines 924-1018) with:
<DeltaTChart
  chartData={displayData}
  segmentCount={segmentCount}
  yDomain={yDomain}
  viewMode={viewMode}
  consistFilter={consistFilter}
  trackingConfig={trackingConfig}
  showSessionBreaks={showSessionBreaks}
  scrollRef={viewMode === 'current' ? scrollRefSession : undefined}
  onMouseDown={viewMode === 'overview' ? handleMouseDown : undefined}
  onMouseMove={viewMode === 'overview' ? handleMouseMove : undefined}
  onMouseUp={viewMode === 'overview' ? handleMouseUp : undefined}
  onDoubleClick={viewMode === 'overview' ? handleDoubleClick : undefined}
  refAreaLeft={refAreaLeft}
  refAreaRight={refAreaRight}
  zoomDomain={zoomDomain}
/>
```

#### Testing Checklist
- ✅ Current view: horizontal scroll works
- ✅ Current view: duplicate Y-axis visible when scrolled right
- ✅ Current view: auto-scroll to latest event
- ✅ Overview view: box-select zoom works (drag + double-click reset)
- ✅ Session breaks toggle: segmented lines appear/disappear
- ✅ Consist filters: All/C10/C11 show correct lines
- ✅ Colors match original
- ✅ Reference lines visible (0, ±1.0, ±1.5)

#### Commit
```
refactor(frontend): extract DeltaTChart component (Phase 3.1)

- Created web/src/components/charts/DeltaTChart.jsx
- Preserved all Current/Overview differences (scroll, Y-axis, zoom)
- Session breaks logic still in parent (too complex to extract)
- Box-select zoom handlers passed as props
- All 8 test cases passing
```

---

### Phase 3.2: FPSChart.jsx (45 min)

**Simpler than DeltaT** - No session breaks, no consist filtering, single line

#### Component Structure
```javascript
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { TOOLTIP_STYLES, CHART_AXIS_STYLES } from '../../constants/analyticsConstants';

export default function FPSChart({
  chartData,
  fpsAvg,
  viewMode,
  scrollRef
}) {
  const chartWidth = viewMode === 'current'
    ? Math.max(chartData.length * 60, 800)
    : '100%';

  const chartContent = (
    <div className="relative">
      {/* FPS Average Badge */}
      {fpsAvg && (
        <div className="absolute top-4 right-4 bg-slate-800/90 px-3 py-1.5 rounded-lg border border-slate-600 z-10">
          <span className="text-sm text-slate-300">
            FPS avg: <span className="font-semibold text-green-400">{fpsAvg}</span>
          </span>
        </div>
      )}

      <ResponsiveContainer width={chartWidth} height={300}>
        <LineChart data={chartData}>
          <CartesianGrid {...CHART_AXIS_STYLES.grid} />

          {/* XAxis: time in Current, index in Overview */}
          <XAxis
            dataKey={viewMode === 'current' ? 'time' : 'index'}
            {...CHART_AXIS_STYLES.axis}
          />

          {/* Left Y-axis */}
          <YAxis
            yAxisId="left"
            {...CHART_AXIS_STYLES.axis}
            domain={[0, 140]}
            label={{ value: 'FPS', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
          />

          {/* Right Y-axis (Current mode only) */}
          {viewMode === 'current' && (
            <YAxis
              yAxisId="right"
              orientation="right"
              {...CHART_AXIS_STYLES.axis}
              domain={[0, 140]}
              allowDataOverflow={true}
              label={{ value: 'FPS', angle: 90, position: 'insideRight', fill: '#9CA3AF' }}
            />
          )}

          <Tooltip
            {...TOOLTIP_STYLES}
            formatter={(value) => value.toFixed(1) + ' FPS'}
          />

          <ReferenceLine
            yAxisId="left"
            y={30}
            stroke="#10b981"
            strokeDasharray="5 5"
            label={{ value: 'Target (30 FPS)', position: 'top', fill: '#10b981' }}
          />

          <Line
            yAxisId="left"
            type="monotone"
            dataKey="fps"
            stroke="#10b981"
            strokeWidth={2}
            dot={{ r: 3 }}
            name="Inference FPS"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );

  // Wrap in scroll container if Current mode
  return viewMode === 'current' ? (
    <div ref={scrollRef} className="overflow-x-auto">
      <div style={{ minWidth: chartWidth }}>
        {chartContent}
      </div>
    </div>
  ) : chartContent;
}
```

#### Update AnalyticsPanel.jsx
```javascript
import FPSChart from './charts/FPSChart';

// Replace FPS chart rendering with:
<FPSChart
  chartData={chartData}
  fpsAvg={fpsAvg}
  viewMode={viewMode}
  scrollRef={viewMode === 'current' ? scrollRefFps : undefined}
/>
```

#### Testing Checklist
- ✅ Current view: horizontal scroll works
- ✅ Current view: duplicate Y-axis visible
- ✅ Current view: auto-scroll to latest sample
- ✅ FPS avg badge visible in both views
- ✅ Target line (30 FPS) visible
- ✅ Chart width dynamic

#### Commit
```
refactor(frontend): extract FPSChart component (Phase 3.2)

- Created web/src/components/charts/FPSChart.jsx
- FPS average badge integrated in component
- Preserved Current/Overview scroll differences
- All 6 test cases passing
```

---

### Phase 3.3: ConfidenceChart.jsx (30 min)

**Simplest chart** - No viewMode differences, snapshot data only

#### Component Structure
```javascript
import React, { useMemo } from 'react';
import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { TOOLTIP_STYLES, CHART_AXIS_STYLES, LOCO_COLORS } from '../../constants/analyticsConstants';
import { filterEventsBySession, getAddressFilter } from '../../utils/analyticsHelpers';

export default function ConfidenceChart({
  cumulativeData,
  viewMode,
  currentSession,
  consistFilter,
  trackingConfig
}) {
  // Data preparation (DRY - single computation)
  const chartData = useMemo(() => {
    const events = filterEventsBySession(cumulativeData.yolo_performance, viewMode, currentSession);
    if (events.length === 0) return [];

    const latestEvent = events[events.length - 1];
    const avgConfidence = latestEvent.avg_confidence;
    const addressFilter = getAddressFilter(consistFilter, trackingConfig.consists);

    return Object.entries(avgConfidence)
      .filter(([addr]) => addressFilter.includes(parseInt(addr)))
      .map(([dcc_addr, conf]) => ({
        loco: `Loco ${dcc_addr}`,
        address: parseInt(dcc_addr),
        confidence: parseFloat((conf * 100).toFixed(1))
      }));
  }, [cumulativeData, viewMode, currentSession, consistFilter, trackingConfig]);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid {...CHART_AXIS_STYLES.grid} />
        <XAxis dataKey="loco" {...CHART_AXIS_STYLES.axis} />
        <YAxis
          {...CHART_AXIS_STYLES.axis}
          domain={[0, 100]}
          label={{ value: 'Confidence (%)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
        />
        <Tooltip
          {...TOOLTIP_STYLES}
          formatter={(value) => value.toFixed(1) + '%'}
        />
        <ReferenceLine
          y={50}
          stroke="#ffffff"
          strokeDasharray="5 5"
          label={{ value: 'Min Threshold (50%)', position: 'top', fill: '#ffffff' }}
        />
        <Bar dataKey="confidence">
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={LOCO_COLORS[entry.address] || '#9CA3AF'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
```

**⚠️ DRY Fix**: Data preparation logic now in `useMemo` (was duplicated in original)

#### Update AnalyticsPanel.jsx
```javascript
import ConfidenceChart from './charts/ConfidenceChart';

// Replace BarChart rendering with:
<ConfidenceChart
  cumulativeData={cumulativeData}
  viewMode={viewMode}
  currentSession={currentSession}
  consistFilter={consistFilter}
  trackingConfig={trackingConfig}
/>
```

#### Testing Checklist
- ✅ Current view: shows session-specific confidence
- ✅ Overview view: shows global confidence
- ✅ Consist filters work (All/C10/C11)
- ✅ Colors match LOCO_COLORS
- ✅ Min threshold line (50%) visible

#### Commit
```
refactor(frontend): extract ConfidenceChart component (Phase 3.3)

- Created web/src/components/charts/ConfidenceChart.jsx
- Fixed DRY violation (data prep now single useMemo)
- Session and address filtering preserved
- All 5 test cases passing
```

---

### Phase 3.4: OperatingTimeChart.jsx (30 min)

**Overview only** - No viewMode prop needed

#### Component Structure
```javascript
import React, { useMemo } from 'react';
import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TOOLTIP_STYLES, CHART_AXIS_STYLES, LOCO_COLORS } from '../../constants/analyticsConstants';
import { getAddressFilter, formatOperatingTime } from '../../utils/analyticsHelpers';

export default function OperatingTimeChart({
  locoStats,
  consistFilter,
  trackingConfig
}) {
  // Filter by consist
  const filteredLocoStats = useMemo(() => {
    const addressFilter = getAddressFilter(consistFilter, trackingConfig.consists);
    return locoStats.filter(loco => addressFilter.includes(loco.address));
  }, [locoStats, consistFilter, trackingConfig]);

  if (filteredLocoStats.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={filteredLocoStats}>
        <CartesianGrid {...CHART_AXIS_STYLES.grid} />
        <XAxis dataKey="name" {...CHART_AXIS_STYLES.axis} />
        <YAxis
          {...CHART_AXIS_STYLES.axis}
          tickFormatter={(value) => Math.floor(value / 60)}
          label={{ value: 'Operating Time (minutes)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
        />
        <Tooltip
          {...TOOLTIP_STYLES}
          formatter={(value) => formatOperatingTime(value)}
        />
        <Bar dataKey="total_operating_seconds">
          {filteredLocoStats.map((loco, index) => (
            <Cell key={`cell-${index}`} fill={LOCO_COLORS[loco.address] || '#9CA3AF'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
```

#### Update AnalyticsPanel.jsx
```javascript
import OperatingTimeChart from './charts/OperatingTimeChart';

// Replace BarChart rendering with:
<OperatingTimeChart
  locoStats={filteredLocoStats}
  consistFilter={consistFilter}
  trackingConfig={trackingConfig}
/>
```

#### Testing Checklist
- ✅ Visible only in Overview mode
- ✅ Consist filters work
- ✅ Y-axis shows minutes
- ✅ Tooltip shows "Xh Ym"
- ✅ Colors match LOCO_COLORS

#### Commit
```
refactor(frontend): extract OperatingTimeChart component (Phase 3.4)

- Created web/src/components/charts/OperatingTimeChart.jsx
- Overview-only chart (no viewMode prop)
- Address filtering preserved
- All 5 test cases passing
```

---

### Phase 3.5: HistoricalTrendChart.jsx (45 min)

**Reports tab only** - Unique click handler + custom tooltip

#### Component Structure
```javascript
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { TOOLTIP_STYLES, CHART_AXIS_STYLES } from '../../constants/analyticsConstants';
import { getConsistStrokeColor, formatDeltaT } from '../../utils/analyticsHelpers';

export default function HistoricalTrendChart({
  reportsChartData,
  consistFilter,
  trackingConfig,
  onSessionClick
}) {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart
        data={reportsChartData}
        onClick={(data) => {
          if (data?.activePayload?.[0]) {
            const sessionId = data.activePayload[0].payload.session_id;
            const session = reportsChartData.find(s => s.session_id === sessionId);
            if (session) {
              onSessionClick(session);
            }
          }
        }}
        margin={{ top: 20, right: 30, left: 20, bottom: 35 }}
      >
        <CartesianGrid {...CHART_AXIS_STYLES.grid} />

        {/* XAxis with date formatter */}
        <XAxis
          dataKey="index"
          {...CHART_AXIS_STYLES.axis}
          angle={-40}
          textAnchor="end"
          height={35}
          interval="preserveStartEnd"
          tickFormatter={(index) => {
            const item = reportsChartData[index - 1];
            if (!item) return index;
            const [day, month, year] = item.date.split('-');
            return `${day}-${month} ${item.time}`;
          }}
        />

        <YAxis
          {...CHART_AXIS_STYLES.axis}
          label={{ value: 'Avg Δt (seconds)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
        />

        {/* Custom tooltip showing all consists for date */}
        <Tooltip
          {...TOOLTIP_STYLES}
          content={({ active, payload, label }) => {
            if (!active || !payload || payload.length === 0) return null;

            const sessionData = payload[0]?.payload;
            if (!sessionData) return null;

            return (
              <div style={{
                backgroundColor: '#1e293b',
                border: '1px solid #475569',
                borderRadius: '8px',
                padding: '12px'
              }}>
                <p style={{ color: '#e2e8f0', marginBottom: '8px', fontWeight: 'bold' }}>
                  {sessionData.date} {sessionData.time}
                </p>
                {payload.map((entry, index) => {
                  if (entry.value === null || entry.value === undefined) return null;
                  return (
                    <p key={index} style={{ color: entry.color, margin: '4px 0' }}>
                      {entry.name}: {formatDeltaT(entry.value)}s
                    </p>
                  );
                })}
              </div>
            );
          }}
        />

        {/* Reference lines */}
        <ReferenceLine y={0} stroke="#10b981" strokeDasharray="3 3" />
        <ReferenceLine y={1.0} stroke="#f59e0b" strokeDasharray="3 3" />
        <ReferenceLine y={-1.0} stroke="#f59e0b" strokeDasharray="3 3" />
        <ReferenceLine y={1.5} stroke="#ef4444" strokeDasharray="3 3" />
        <ReferenceLine y={-1.5} stroke="#ef4444" strokeDasharray="3 3" />

        {/* Lines for each consist */}
        {Object.keys(trackingConfig.consists || {}).map(cid => {
          if (consistFilter === 'all' || consistFilter == cid) {
            return (
              <Line
                key={cid}
                dataKey={`avg_delta_t_c${cid}`}
                stroke={getConsistStrokeColor(Number(cid), trackingConfig.consists)}
                strokeWidth={2}
                dot={{ r: 5 }}
                activeDot={{ r: 7 }}
                connectNulls={false}
                name={`C${cid}`}
              />
            );
          }
          return null;
        })}
      </LineChart>
    </ResponsiveContainer>
  );
}
```

#### Update AnalyticsPanel.jsx
```javascript
import HistoricalTrendChart from './charts/HistoricalTrendChart';

// Replace LineChart rendering with:
<HistoricalTrendChart
  reportsChartData={reportsChartData}
  consistFilter={consistFilter}
  trackingConfig={trackingConfig}
  onSessionClick={(session) => {
    setSelectedSession(session);
    setShowSessionDetail(true);
  }}
/>
```

#### Testing Checklist
- ✅ Visible only in Reports tab
- ✅ Click on point opens Session Detail modal
- ✅ Custom tooltip shows all consists for date
- ✅ XAxis shows "DD-MM HH:MM"
- ✅ Consist filters work
- ✅ connectNulls={false} (doesn't connect across missing sessions)

#### Commit
```
refactor(frontend): extract HistoricalTrendChart component (Phase 3.5)

- Created web/src/components/charts/HistoricalTrendChart.jsx
- Reports-only chart with click handler
- Custom tooltip shows all consists per date
- All 6 test cases passing
```

---

**Phase 3 Complete**: ~3-4 hours, 5 chart components extracted, AnalyticsPanel reduced by ~600 lines

---

## Phase 4: Extract Tab Views (NOT PLANNED - TOO RISKY)

**⚠️ DECISION: DO NOT EXTRACT TAB VIEWS**

### Rationale
After Phase 3 (chart extraction), AnalyticsPanel will be ~1000 lines (manageable).

Tab views share:
- State (viewMode, consistFilter, collapsedPanels, etc.)
- Effects (keyboard shortcuts, auto-refresh, API calls)
- Event handlers (box-select, session breaks toggle)

Extracting tab views would require:
1. Passing 20+ props to each tab component
2. Lifting all state + handlers to parent
3. Complex prop drilling
4. High risk of breaking Current/Overview/Reports logic

**Better approach**: Keep tab rendering in AnalyticsPanel, extract only reusable pieces (charts ✅, constants ✅, helpers ✅).

---

## Phase 4 (Revised): Final Cleanup (1 hour)

### Goal
Verify refactoring complete, update documentation, merge to develop

### Tasks
1. ✅ **Line count verification**
   ```bash
   wc -l web/src/components/AnalyticsPanel.jsx web/src/components/charts/*.jsx web/src/constants/analyticsConstants.js web/src/utils/analyticsHelpers.js
   ```
   - Expected: AnalyticsPanel ~1000-1100 lines (down from 1684)
   - Charts: ~630 lines total (5 files)
   - Constants: ~30 lines
   - Helpers: ~70 lines

2. ✅ **Dead code check**
   - Remove unused imports
   - Remove commented code
   - Verify no duplicate logic

3. ✅ **Testing checklist** (deploy to PC, test all features)
   - ✅ Current view: all charts, scroll, auto-scroll, filters
   - ✅ Overview view: all charts, box-select zoom, filters
   - ✅ Reports tab: session history, trend chart, detail modal
   - ✅ Keyboard shortcuts: arrows, 1-3 keys
   - ✅ Session breaks toggle
   - ✅ Collapsible panels

4. ✅ **Update CLAUDE.md**
   - Add frontend refactor completion entry (2025-01-15)
   - Document files created (5 charts, 1 constants, 1 helpers)
   - Benefits: DRY, maintainability, testability

5. ✅ **Update README.md** (if needed)
   - No changes needed (frontend refactor internal)

6. ✅ **Merge to develop**
   ```bash
   git checkout develop
   git merge refactor-frontend --no-ff -m "refactor(frontend): modular analytics charts - Phase 1-4 complete"
   git push origin develop
   ```

7. ✅ **Delete refactor-frontend branch**
   ```bash
   git branch -D refactor-frontend
   git push origin --delete refactor-frontend
   ```

### Commit Message
```
refactor(frontend): modular analytics charts - Phase 1-4 complete

MILESTONE: Frontend analytics refactoring complete

Summary:
- AnalyticsPanel.jsx: 1684 → ~1000 lines (-40% reduction)
- Created 7 modular files (730 lines total)
  - 5 chart components (DeltaTChart, FPSChart, ConfidenceChart, OperatingTimeChart, HistoricalTrendChart)
  - 1 constants file (analyticsConstants.js)
  - 1 helpers file (analyticsHelpers.js)

Architecture:
- Chart components preserve ALL Current/Overview/Reports differences
- Session breaks logic kept in parent (too complex to extract)
- Box-select zoom handlers passed as props
- Width calculation dynamic (not hardcoded)
- Scroll refs optional props

Testing:
- All features verified on PC Windows production
- Current/Overview/Reports views fully functional
- Session breaks, box-select zoom, filters working
- Zero visual or behavior changes

Benefits:
- DRY: Fixed confidence chart data duplication
- Maintainability: Single responsibility per chart
- Testability: Each chart independently testable
- Readability: Clear separation of concerns

Commits: [first] → [last] (X commits across 4 phases)
Time Investment: ~6-8 hours (4 phases, incremental testing)

Next: Frontend tab views extraction deferred (tab rendering too coupled to state)
```

---

## Testing Checklist (After EACH Phase)

### Deploy to PC
```powershell
cd C:\z21-Terminal
git fetch origin
git checkout refactor-frontend
git reset --hard origin/refactor-frontend
npm install --prefix web
npm run build --prefix web
z21-restart
```

### Manual Tests (Current View)
1. ✅ Δt Trends chart renders correctly
2. ✅ Horizontal scroll works
3. ✅ Duplicate Y-axis visible when scrolled right
4. ✅ Auto-scroll to latest event
5. ✅ Session breaks toggle works
6. ✅ Consist filters work (All/C10/C11)
7. ✅ FPS chart renders correctly
8. ✅ FPS avg badge visible
9. ✅ Confidence chart renders correctly
10. ✅ Stats cards show session-specific data

### Manual Tests (Overview View)
1. ✅ Δt Trends chart renders correctly (fit-to-width)
2. ✅ Box-select zoom works (drag + double-click reset)
3. ✅ Session breaks toggle works
4. ✅ Consist filters work
5. ✅ FPS chart renders correctly
6. ✅ FPS avg badge visible
7. ✅ Confidence chart renders correctly
8. ✅ Operating time chart renders correctly
9. ✅ Stats cards show cumulative data

### Manual Tests (Reports Tab)
1. ✅ Session history table renders
2. ✅ Session limit dropdown works (30/50/100/200)
3. ✅ Consist filter works
4. ✅ Historical trend chart renders
5. ✅ Click on point opens Session Detail modal
6. ✅ Custom tooltip shows all consists per date

### Keyboard Shortcuts
1. ✅ Arrow keys switch Current/Overview
2. ✅ Keys 1-3 switch tabs (Current/Overview/Reports)
3. ✅ ESC closes modal

### Rollback If Needed
```powershell
cd C:\z21-Terminal
git checkout develop
git reset --hard origin/develop
npm install --prefix web
npm run build --prefix web
z21-restart
```

---

## Risk Mitigation

### High-Risk Areas
1. **Δt Chart segmentation** - Session breaks logic complex, easy to break
2. **Box-select zoom** - Mouse event handling fragile
3. **Width calculation** - Hardcoding width breaks scroll
4. **Duplicate Y-axis** - Conditional rendering must match scroll state
5. **Confidence chart data duplication** - DRY fix might break filtering

### Safety Measures
- Git tag after EVERY phase
- Deploy + test after EVERY phase
- Rollback immediately if any test fails
- Keep commit messages clear for easy revert
- Compare screenshots before/after (visual regression)

---

## Timeline Summary

| Phase | Time | Files Created | Risk |
|-------|------|--------------|------|
| Phase 0: Analysis | 1h | 1 doc | Low |
| Phase 1: Constants | 30min | 1 file | Low |
| Phase 2: Helpers | 1h | 1 file | Low |
| Phase 3.1: DeltaT | 1.5h | 1 chart | High |
| Phase 3.2: FPS | 45min | 1 chart | Medium |
| Phase 3.3: Confidence | 30min | 1 chart | Low |
| Phase 3.4: OpTime | 30min | 1 chart | Low |
| Phase 3.5: Historical | 45min | 1 chart | Medium |
| Phase 4: Cleanup | 1h | - | Low |
| **TOTAL** | **6-8h** | **7 files** | **Mixed** |

**Realistic Estimate**: 1-2 working days with thorough testing

---

## Success Criteria

✅ AnalyticsPanel.jsx < 1100 lines
✅ 5 chart components created
✅ 1 constants file created
✅ 1 helpers file created
✅ All Current/Overview/Reports differences preserved
✅ Zero visual changes
✅ Zero behavior changes
✅ All tests passing
✅ Merged to develop branch

---

## Post-Refactor Benefits

1. **For Speed Table Auto-Tuning (v1.4)**:
   - Reuse DeltaTChart for speed correlation chart
   - Reuse formatDeltaT for CV adjustment display
   - Add SpeedCorrelationChart.jsx (~150 lines)

2. **For Future Features**:
   - New chart? → Create standalone component, plug into tab view
   - Chart bug? → Fix in chart component, not in 1684-line monster
   - A/B test chart variant? → Create alternate component

3. **Maintenance**:
   - Chart rendering bug? → Grep for chart component name
   - Session filtering bug? → Fix in analyticsHelpers.js
   - Color scheme change? → Update analyticsConstants.js
   - Clear separation of concerns

---

## Notes

- **DO NOT extract tab views** (too coupled to state, high risk)
- **Keep segmentation logic in parent** (too complex, too many edge cases)
- **Test after EVERY phase** (200+ commits to get here, don't break it)
- **Preserve ALL Current/Overview/Reports differences** (documented in Chart Analysis)
- **Compare screenshots before/after** (visual regression detection)
- If stuck > 30 min on one step → ask user for guidance

---

**Ready to proceed with implementation!**
