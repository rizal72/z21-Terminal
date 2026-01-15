/**
 * HistoricalTrendChart Component
 *
 * Displays historical Δt trend across sessions (Reports tab only).
 *
 * Features:
 * - Session-by-session avg Δt over time
 * - Click on point → opens Session Detail Modal
 * - Custom tooltip showing ALL consists for that date
 * - Dynamic lines based on consist filter (All/C10/C11)
 * - XAxis shows date + time (DD-MM HH:MM)
 * - connectNulls={false} to avoid lines between sessions without data
 * - Reference lines for thresholds (0, ±1.0, ±1.5)
 * - Collapsible panel
 */

import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';
import {
  CHART_AXIS_STYLES,
  TOOLTIP_STYLES
} from '../../constants/analyticsConstants';
import {
  getConsistStrokeColor,
  formatDeltaT
} from '../../utils/analyticsHelpers';

const HistoricalTrendChart = ({
  reportsChartData,
  reportsData,
  consistFilter,
  trackingConfig,
  collapsed,
  onToggleCollapse,
  onSessionClick
}) => {
  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-700/30 transition-colors"
        onClick={onToggleCollapse}
      >
        <h3 className="text-lg font-semibold text-white">Historical Trend - Avg Δt</h3>
        <i className={`fa-solid fa-chevron-${collapsed ? 'right' : 'down'} text-slate-400 transition-transform`}></i>
      </div>

      {!collapsed && (
        <div className="p-6 pt-0">
          {/* Threshold Legend */}
          <div className="flex gap-6 justify-center mb-4 pb-3 border-b border-slate-700/50">
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

          {reportsChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart
                data={reportsChartData}
                onClick={(data) => {
                  if (data?.activePayload?.[0]) {
                    const sessionId = data.activePayload[0].payload.session_id;
                    const session = reportsData.sessions.find(s => s.id === sessionId);
                    if (session) {
                      onSessionClick(session);
                    }
                  }
                }}
                margin={{ top: 20, right: 30, left: 20, bottom: 35 }}
              >
                <CartesianGrid {...CHART_AXIS_STYLES.grid} />
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
                    // Format: DD-MM HH:MM (backend sends DD-MM-YYYY)
                    const [day, month, year] = item.date.split('-');
                    return `${day}-${month} ${item.time}`;
                  }}
                />
                <YAxis
                  {...CHART_AXIS_STYLES.axis}
                  label={{ value: 'Avg Δt (seconds)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
                />
                <Tooltip
                  {...TOOLTIP_STYLES}
                  content={({ active, payload, label }) => {
                    if (!active || !payload || payload.length === 0) return null;

                    // Get session data from payload
                    const sessionData = payload[0]?.payload;
                    if (!sessionData) return null;

                    return (
                      <div style={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px', padding: '12px' }}>
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
                <ReferenceLine y={0} stroke="#10b981" strokeDasharray="3 3" />
                <ReferenceLine y={1.0} stroke="#f59e0b" strokeDasharray="3 3" />
                <ReferenceLine y={-1.0} stroke="#f59e0b" strokeDasharray="3 3" />
                <ReferenceLine y={1.5} stroke="#ef4444" strokeDasharray="3 3" />
                <ReferenceLine y={-1.5} stroke="#ef4444" strokeDasharray="3 3" />

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
          ) : (
            <div className="text-center py-12 text-slate-400">
              <i className="fa-solid fa-chart-line text-4xl mb-4"></i>
              <p>No trend data available</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default HistoricalTrendChart;
