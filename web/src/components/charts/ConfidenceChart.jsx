/**
 * ConfidenceChart Component
 *
 * Displays average YOLO detection confidence per locomotive.
 *
 * Features:
 * - Current mode: Snapshot view (last event only)
 * - Overview mode: Historical average across ALL events
 * - Session filtering: Current (session-specific) vs Overview (global)
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
    const events = filterEventsBySession(yoloPerformanceData, viewMode, currentSession);
    if (events.length === 0) return [];

    const addressFilter = getAddressFilter(consistFilter, trackingConfig.consists);

    if (viewMode === 'current') {
      // Current mode: snapshot view (last event only)
      const latestEvent = events[events.length - 1];
      const avgConfidence = latestEvent.avg_confidence;

      return Object.entries(avgConfidence)
        .filter(([addr]) => addressFilter.includes(parseInt(addr)))
        .map(([dcc_addr, conf]) => ({
          loco: `Loco ${dcc_addr}`,
          address: parseInt(dcc_addr),
          confidence: parseFloat((conf * 100).toFixed(1))
        }));
    } else {
      // Overview mode: aggregate historical average across ALL events
      const confidenceSum = {};
      const confidenceCount = {};

      // Aggregate confidence values for each loco across all events
      events.forEach(event => {
        Object.entries(event.avg_confidence).forEach(([addr, conf]) => {
          const address = parseInt(addr);
          if (addressFilter.includes(address)) {
            if (!confidenceSum[address]) {
              confidenceSum[address] = 0;
              confidenceCount[address] = 0;
            }
            confidenceSum[address] += conf;
            confidenceCount[address]++;
          }
        });
      });

      // Calculate average and build chart data
      return Object.keys(confidenceSum)
        .map(addr => {
          const address = parseInt(addr);
          const avgConf = confidenceSum[address] / confidenceCount[address];
          return {
            loco: `Loco ${address}`,
            address: address,
            confidence: parseFloat((avgConf * 100).toFixed(1))
          };
        })
        .sort((a, b) => a.address - b.address); // Sort by address for consistent order
    }
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
