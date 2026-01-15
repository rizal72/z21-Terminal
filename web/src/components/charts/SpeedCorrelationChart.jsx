import React from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  ErrorBar
} from 'recharts';
import {
  TOOLTIP_STYLES,
  CHART_AXIS_STYLES
} from '../../constants/analyticsConstants';
import {
  getSpeedTuningReferenceLines,
  getSpeedBucketColor,
  formatDeltaT
} from '../../utils/analyticsHelpers';

/**
 * SpeedCorrelationChart Component
 *
 * Displays speed vs delta-t correlation with error bars.
 * Shows which speeds require CV tuning based on mean delta-t.
 *
 * Props:
 *   - data: Speed correlation data from API (speed_buckets array)
 *   - thresholds: Delta-t thresholds from config (synced_threshold, warning_threshold, critical_threshold)
 *   - consistColor: Consist color for scatter points (optional, falls back to status-based color)
 */
const SpeedCorrelationChart = ({ data, thresholds, consistColor }) => {
  // Transform data for Recharts (speed_buckets → chart data)
  const chartData = (data?.speed_buckets || []).map(bucket => ({
    speed: bucket.speed_bucket,
    meanDeltaT: bucket.mean_delta_t,
    stdDev: bucket.std_dev,
    samples: bucket.samples,
    statusDistribution: bucket.status_distribution,
    speedRange: `${bucket.speed_min}-${bucket.speed_max}`,
    fill: consistColor || getSpeedBucketColor(bucket.status_distribution)
  }));

  // Generate reference lines from config thresholds
  const referenceLines = getSpeedTuningReferenceLines(thresholds);

  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload || payload.length === 0) return null;

    const point = payload[0].payload;
    const statusDist = point.statusDistribution || {};
    const total = Object.values(statusDist).reduce((sum, count) => sum + count, 0);

    return (
      <div
        className="p-3 rounded-lg shadow-lg border"
        style={{
          backgroundColor: TOOLTIP_STYLES.contentStyle.backgroundColor,
          borderColor: TOOLTIP_STYLES.contentStyle.border.split(' ')[2]
        }}
      >
        <p className="text-white font-semibold mb-2">
          Speed {point.speed} ({point.speedRange})
        </p>
        <div className="text-slate-300 text-sm space-y-1">
          <p>Mean Δt: <span className="font-mono">{formatDeltaT(point.meanDeltaT)}</span>s</p>
          <p>Std Dev: ±{point.stdDev.toFixed(2)}s</p>
          <p>Samples: {point.samples}</p>
          {total > 0 && (
            <div className="mt-2 pt-2 border-t border-slate-600">
              <p className="font-semibold mb-1">Status Distribution:</p>
              {statusDist.SYNCED > 0 && (
                <p className="text-green-400">
                  SYNCED: {statusDist.SYNCED} ({Math.round((statusDist.SYNCED / total) * 100)}%)
                </p>
              )}
              {statusDist.WARNING > 0 && (
                <p className="text-amber-400">
                  WARNING: {statusDist.WARNING} ({Math.round((statusDist.WARNING / total) * 100)}%)
                </p>
              )}
              {statusDist.CRITICAL > 0 && (
                <p className="text-red-400">
                  CRITICAL: {statusDist.CRITICAL} ({Math.round((statusDist.CRITICAL / total) * 100)}%)
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  if (!data || !data.speed_buckets || data.speed_buckets.length === 0) {
    return (
      <div className="h-96 flex items-center justify-center text-slate-400">
        <div className="text-center">
          <p className="text-lg mb-2">No speed correlation data available</p>
          <p className="text-sm">Change speed during sessions to collect data</p>
        </div>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={400}>
      <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 20 }}>
        <CartesianGrid {...CHART_AXIS_STYLES.grid} />
        <XAxis
          type="number"
          dataKey="speed"
          name="Speed"
          domain={[0, 126]}
          ticks={[0, 20, 40, 60, 80, 100, 120]}
          label={{ value: 'DCC Speed', position: 'insideBottom', offset: -10, fill: '#9CA3AF' }}
          {...CHART_AXIS_STYLES.axis}
        />
        <YAxis
          type="number"
          dataKey="meanDeltaT"
          name="Mean Δt"
          domain={['auto', 'auto']}
          label={{ value: 'Mean Δt (seconds)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
          {...CHART_AXIS_STYLES.axis}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />

        {/* Reference lines (thresholds from config) */}
        {referenceLines.map((line, idx) => (
          <ReferenceLine
            key={idx}
            y={line.y}
            stroke={line.stroke}
            strokeDasharray={line.strokeDasharray}
            label={line.label ? { value: line.label, position: 'right', fill: line.stroke } : null}
          />
        ))}

        {/* Scatter plot with error bars */}
        <Scatter
          name="Speed Buckets"
          data={chartData}
          fill={consistColor || '#8884d8'}
        >
          <ErrorBar dataKey="stdDev" width={4} strokeWidth={2} stroke="#64748b" />
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  );
};

export default SpeedCorrelationChart;
