/**
 * ConfidenceChart Component
 *
 * Displays average YOLO detection confidence per locomotive (snapshot view).
 *
 * Features:
 * - Snapshot view (NOT time-series): shows latest confidence values
 * - Session filtering: Current (session-specific) vs Overview (global latest)
 * - Consist filtering: Show only locomotives in selected consist
 * - Color-coded bars by locomotive (LOCO_COLORS)
 * - 50% minimum threshold reference line
 */

import React, { useMemo } from 'react';
import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';
import {
  LOCO_COLORS,
  CHART_AXIS_STYLES,
  TOOLTIP_STYLES
} from '../../constants/analyticsConstants';
import {
  filterEventsBySession,
  getAddressFilter
} from '../../utils/analyticsHelpers';

const ConfidenceChart = ({
  yoloPerformanceData,
  viewMode,
  currentSession,
  consistFilter,
  trackingConfig
}) => {
  // Calculate chart data (DRY: computed once, used for both data and Cell colors)
  const chartData = useMemo(() => {
    // Confidence chart: snapshot view, NOT time series
    const events = filterEventsBySession(yoloPerformanceData, viewMode, currentSession);
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
  }, [yoloPerformanceData, viewMode, currentSession, consistFilter, trackingConfig.consists]);

  return (
    <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
      <h4 className="text-lg font-semibold text-amber-400 mb-4">Average Confidence per Locomotive</h4>
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
    </div>
  );
};

export default ConfidenceChart;
