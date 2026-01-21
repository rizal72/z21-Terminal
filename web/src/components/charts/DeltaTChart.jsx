/**
 * DeltaTChart Component
 *
 * Displays Δt (delta-time) trends for consist synchronization monitoring.
 *
 * Features:
 * - Current vs Overview modes (different XAxis, scroll, width, dots, stroke)
 * - Session breaks support (segmented lines when enabled)
 * - Box-select zoom in Overview mode
 * - Duplicate Y-axis in Current mode (visible when scrolled)
 * - Dynamic width calculation (Current: per-event, Overview: 100%)
 * - Auto-scroll support via ref prop
 * - Day boundary markers in Current mode (vertical amber lines with "DD MMM" labels)
 */

import React, { useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, ReferenceArea
} from 'recharts';
import {
  CHART_AXIS_STYLES,
  TOOLTIP_STYLES
} from '../../constants/analyticsConstants';
import {
  getConsistStrokeColor,
  formatDeltaT
} from '../../utils/analyticsHelpers';

const DeltaTChart = ({
  chartData,
  segmentCount,
  viewMode,
  consistFilter,
  trackingConfig,
  scrollRef,
  zoomDomain,
  onMouseDown,
  onMouseMove,
  onMouseUp,
  onDoubleClick,
  refAreaLeft,
  refAreaRight,
  collapsed,
  onToggleCollapse
}) => {
  // Apply zoom filter if zoomDomain is set (Overview mode only)
  const displayData = useMemo(() => {
    if (viewMode !== 'overview' || !zoomDomain) return chartData;

    // Filter data to show only zoomed range
    const [xMin, xMax] = zoomDomain.x;
    return chartData.filter(d => d.index >= xMin && d.index <= xMax);
  }, [chartData, zoomDomain, viewMode]);

  // Calculate Y domain to ensure all points are visible (5% padding)
  const yDomain = useMemo(() => {
    if (zoomDomain) return zoomDomain.y; // Use zoom domain if active

    if (displayData.length === 0) return ['auto', 'auto'];

    const consistIds = Object.keys(trackingConfig.consists || {}).map(Number);
    let yMin = Infinity, yMax = -Infinity;

    // Scan all data to find min/max
    if (segmentCount === 0) {
      // SIMPLE MODE
      displayData.forEach(d => {
        consistIds.forEach(cid => {
          const value = d[`delta_t_c${cid}`];
          if (value !== null && value !== undefined && !isNaN(value)) {
            yMin = Math.min(yMin, value);
            yMax = Math.max(yMax, value);
          }
        });
      });
    } else {
      // SEGMENTED MODE
      displayData.forEach(d => {
        for (let seg = 0; seg < segmentCount; seg++) {
          consistIds.forEach(cid => {
            const value = d[`delta_t_c${cid}_seg${seg}`];
            if (value !== null && value !== undefined && !isNaN(value)) {
              yMin = Math.min(yMin, value);
              yMax = Math.max(yMax, value);
            }
          });
        }
      });
    }

    // No valid data found
    if (yMin === Infinity || yMax === -Infinity) return ['auto', 'auto'];

    // Add 5% padding
    const range = yMax - yMin;
    const padding = range * 0.05;
    return [yMin - padding, yMax + padding];
  }, [displayData, segmentCount, trackingConfig.consists, zoomDomain]);

  // Memoize chart width calculation
  const chartWidth = useMemo(() => {
    return viewMode === 'current' ? Math.max(chartData.length * 40, 800) : '100%';
  }, [chartData.length, viewMode]);

  // Calculate day boundaries for Current mode (vertical lines at day changes)
  const dayBoundaries = useMemo(() => {
    if (viewMode !== 'current' || chartData.length === 0) return [];

    const boundaries = [];
    let previousDate = null;

    chartData.forEach((point) => {
      const date = new Date(point.timestamp * 1000);
      const dateStr = date.toLocaleDateString('en-US', { day: '2-digit', month: 'short' }); // "21 Jan"

      // Check if day changed
      const currentDay = date.getDate();
      const currentMonth = date.getMonth();
      const currentYear = date.getFullYear();

      if (previousDate) {
        const prevDay = previousDate.getDate();
        const prevMonth = previousDate.getMonth();
        const prevYear = previousDate.getFullYear();

        if (currentDay !== prevDay || currentMonth !== prevMonth || currentYear !== prevYear) {
          // Day boundary found!
          boundaries.push({
            x: point.time, // HH:MM:SS format (X-axis value in Current mode)
            label: dateStr  // "21 Jan"
          });
        }
      } else {
        // First point - always show the date
        boundaries.push({
          x: point.time,
          label: dateStr
        });
      }

      previousDate = date;
    });

    return boundaries;
  }, [chartData, viewMode]);

  if (chartData.length === 0) return null;

  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-700/30 transition-colors"
        onClick={onToggleCollapse}
      >
        <h3 className="text-lg font-semibold text-white">Δt Trends (All Sessions)</h3>
        <div className="flex items-center gap-4">
          {!collapsed && viewMode === 'overview' && (
            <span className="text-xs text-slate-400">
              Click & drag to zoom • Double-click to reset
            </span>
          )}
          <i className={`fa-solid fa-chevron-${collapsed ? 'right' : 'down'} text-slate-400 transition-transform`}></i>
        </div>
      </div>

      {!collapsed && (
        <div className="p-6 pt-0">
          {/* Threshold Legend - SYNCED/WARNING/CRITICAL */}
          <div className="flex gap-6 justify-center mb-3 pb-3 border-b border-slate-700/50">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span className="text-xs text-slate-400">SYNCED (&lt;1.0s)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-amber-500"></div>
              <span className="text-xs text-slate-400">WARNING (1.0-1.5s)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <span className="text-xs text-slate-400">CRITICAL (≥1.5s)</span>
            </div>
          </div>

          {/* Custom Legend (always shown when All filter, both Current and Overview) */}
          {consistFilter === 'all' && (
            <div className="flex gap-4 justify-center mb-4 pb-3 border-b border-slate-700">
              {Object.keys(trackingConfig.consists || {})
                .map(Number)
                .sort((a, b) => a - b)
                .map((consistId) => (
                  <div key={consistId} className="flex items-center gap-2">
                    <div
                      className="w-4 h-1"
                      style={{ backgroundColor: getConsistStrokeColor(consistId, trackingConfig.consists) }}
                    ></div>
                    <span className="text-sm text-slate-300">
                      {trackingConfig.consists[consistId]?.name || `Consist ${consistId}`}
                    </span>
                  </div>
                ))}
            </div>
          )}

          {/* Chart */}
          <div
            key={consistFilter}
            ref={viewMode === 'current' ? scrollRef : null}
            style={{ width: '100%', overflowX: viewMode === 'current' ? 'auto' : 'visible' }}
          >
            <ResponsiveContainer width={chartWidth} height={400}>
              <LineChart
                data={displayData}
                onMouseDown={onMouseDown}
                onMouseMove={onMouseMove}
                onMouseUp={onMouseUp}
                onDoubleClick={onDoubleClick}
              >
                <CartesianGrid {...CHART_AXIS_STYLES.grid} />
                {/* XAxis: time in Current (readable), index in Overview (compressed) */}
                <XAxis
                  dataKey={viewMode === 'current' ? 'time' : 'index'}
                  {...CHART_AXIS_STYLES.axis}
                />
                <YAxis
                  yAxisId="left"
                  {...CHART_AXIS_STYLES.axis}
                  domain={yDomain}
                  allowDataOverflow={true}
                  tickFormatter={(value) => formatDeltaT(value)}
                  label={{ value: 'Δt (seconds)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
                />
                {/* Duplicate YAxis on right for Current mode (always visible when scrolling) */}
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
                <Tooltip
                  {...TOOLTIP_STYLES}
                  formatter={(value) => value !== null ? formatDeltaT(value) + 's' : 'N/A'}
                />
                <ReferenceLine yAxisId="left" y={0} stroke="#10b981" strokeDasharray="3 3" />
                <ReferenceLine yAxisId="left" y={trackingConfig.timing_thresholds?.warning || 1.0} stroke="#f59e0b" strokeDasharray="3 3" />
                <ReferenceLine yAxisId="left" y={-(trackingConfig.timing_thresholds?.warning || 1.0)} stroke="#f59e0b" strokeDasharray="3 3" />
                <ReferenceLine yAxisId="left" y={trackingConfig.timing_thresholds?.critical || 1.5} stroke="#ef4444" strokeDasharray="3 3" />
                <ReferenceLine yAxisId="left" y={-(trackingConfig.timing_thresholds?.critical || 1.5)} stroke="#ef4444" strokeDasharray="3 3" />

                {/* Day boundary markers - Current mode only */}
                {viewMode === 'current' && dayBoundaries.map((boundary, idx) => (
                  <ReferenceLine
                    key={`day-${idx}`}
                    x={boundary.x}
                    stroke="#f59e0b"
                    strokeWidth={1.5}
                    strokeDasharray="5 5"
                    label={{
                      value: boundary.label,
                      position: 'top',
                      fill: '#f59e0b',
                      fontSize: 12,
                      fontWeight: 'bold'
                    }}
                  />
                ))}

                {/* Dynamic lines: simple or segmented based on showSessionBreaks */}
                {Object.keys(trackingConfig.consists || {})
                  .map(Number)
                  .sort((a, b) => a - b)
                  .filter(consistId => consistFilter === 'all' || consistFilter === consistId)
                  .flatMap((consistId) => {
                    // SIMPLE MODE: One Line per consist (no session breaks)
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

                    // SEGMENTED MODE: One Line per segment (session breaks enabled)
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

                {/* ReferenceArea for box-select zoom - only during drag in Overview */}
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
        </div>
      )}
    </div>
  );
};

export default DeltaTChart;
