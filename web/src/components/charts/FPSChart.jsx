/**
 * FPSChart Component
 *
 * Displays YOLO inference FPS performance over time.
 *
 * Features:
 * - Current vs Overview modes (different XAxis, scroll, width, duplicate Y-axis)
 * - FPS average badge (session-specific in Current, global in Overview)
 * - Idle filtering: Excludes FPS ≤ 10 from average calculation (1 FPS idle mode)
 * - NO session filtering for chart data (shows all events like DeltaTChart)
 * - Dynamic width calculation (Current: per-event, Overview: 100%)
 * - Auto-scroll support via ref prop
 */

import React, { useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';
import {
  CHART_AXIS_STYLES,
  TOOLTIP_STYLES
} from '../../constants/analyticsConstants';

const FPSChart = ({
  yoloPerformanceData,
  viewMode,
  currentSession,
  consistFilter,
  scrollRef,
  formatTime
}) => {
  // NO session filtering for CHART - FPS chart shows ALL sessions like dT chart
  const chartData = useMemo(() => {
    return yoloPerformanceData.map((e, idx) => ({
      index: idx + 1,
      time: formatTime(e.timestamp),
      fps: parseFloat(e.avg_fps.toFixed(1))
    }));
  }, [yoloPerformanceData, formatTime]);

  // Calculate average FPS: Current = session only, Overview = all data
  // IMPORTANT: Filter out idle mode (FPS <= 10) to measure real tracking performance
  const avgFps = useMemo(() => {
    if (viewMode === 'current') {
      // Current mode: session-specific or N/A if not loaded
      if (!currentSession) {
        return 'N/A';  // Session not loaded yet
      } else {
        // Filter by current session + exclude idle (FPS > 10)
        const sessionEvents = yoloPerformanceData.filter(e =>
          e.session_id === currentSession.session_id && e.avg_fps > 10
        );
        if (sessionEvents.length > 0) {
          return (sessionEvents.reduce((sum, e) => sum + e.avg_fps, 0) / sessionEvents.length).toFixed(1);
        }
        return 'N/A'; // No active tracking events in session
      }
    } else {
      // Overview: all data, exclude idle (FPS > 10)
      const activeEvents = yoloPerformanceData.filter(e => e.avg_fps > 10);
      return activeEvents.length > 0
        ? (activeEvents.reduce((sum, e) => sum + e.avg_fps, 0) / activeEvents.length).toFixed(1)
        : 'N/A';
    }
  }, [yoloPerformanceData, viewMode, currentSession]);

  // Memoize chart width calculation
  const chartWidth = useMemo(() => {
    return viewMode === 'current' ? Math.max(chartData.length * 60, 800) : '100%';
  }, [chartData.length, viewMode]);

  const chartContent = (
    <ResponsiveContainer width={chartWidth} height={300}>
      <LineChart data={chartData}>
        <CartesianGrid {...CHART_AXIS_STYLES.grid} />
        {/* XAxis: time in Current (readable), index in Overview (compressed) */}
        <XAxis
          dataKey={viewMode === 'current' ? 'time' : 'index'}
          {...CHART_AXIS_STYLES.axis}
        />
        <YAxis
          yAxisId="left"
          {...CHART_AXIS_STYLES.axis}
          domain={[0, 140]}
          label={{ value: 'FPS', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
        />
        {/* Duplicate YAxis on right for Current mode (always visible when scrolling) */}
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
  );

  return (
    <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
      {/* Header with FPS avg badge */}
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-lg font-semibold text-amber-400">Inference FPS Over Time</h4>
        <span className="px-3 py-1 bg-slate-800 border border-slate-600 rounded text-sm font-mono text-green-400">
          FPS avg: {avgFps}
        </span>
      </div>

      {/* Chart with conditional scroll wrapper */}
      {viewMode === 'current' ? (
        <div key={`fps-${consistFilter}`} ref={scrollRef} className="overflow-x-auto">
          <div style={{ minWidth: chartWidth }}>
            {chartContent}
          </div>
        </div>
      ) : chartContent}
    </div>
  );
};

export default FPSChart;
