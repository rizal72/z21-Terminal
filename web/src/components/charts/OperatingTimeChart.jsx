/**
 * OperatingTimeChart Component
 *
 * Displays total operating time per locomotive (Overview mode only).
 *
 * Features:
 * - Overview mode only (cumulative historic data)
 * - Consist filtering: Show only locomotives in selected consist
 * - Color-coded bars by locomotive (LOCO_COLORS)
 * - Y-axis in minutes (tickFormatter)
 * - Tooltip shows "Xh Ym" format
 * - Collapsible panel
 */

import React, { useMemo } from 'react';
import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import {
  LOCO_COLORS,
  CHART_AXIS_STYLES,
  TOOLTIP_STYLES
} from '../../constants/analyticsConstants';
import {
  getAddressFilter,
  formatOperatingTime
} from '../../utils/analyticsHelpers';

const OperatingTimeChart = ({
  locoStats,
  consistFilter,
  trackingConfig,
  collapsed,
  onToggleCollapse
}) => {
  // Filter locomotives by consist (All/C10/C11)
  const filteredLocoStats = useMemo(() => {
    const addressFilter = getAddressFilter(consistFilter, trackingConfig.consists);
    return locoStats.filter(loco => addressFilter.includes(loco.address));
  }, [locoStats, consistFilter, trackingConfig.consists]);

  // Don't render if no data after filtering
  if (filteredLocoStats.length === 0) return null;

  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-700/30 transition-colors"
        onClick={onToggleCollapse}
      >
        <h3 className="text-lg font-semibold text-white">Locomotive Operating Time</h3>
        <i className={`fa-solid fa-chevron-${collapsed ? 'right' : 'down'} text-slate-400 transition-transform`}></i>
      </div>

      {!collapsed && (
        <div className="p-6 pt-0">
          <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
            <h4 className="text-lg font-semibold text-amber-400 mb-4">Total Operating Time</h4>
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
          </div>
        </div>
      )}
    </div>
  );
};

export default OperatingTimeChart;
