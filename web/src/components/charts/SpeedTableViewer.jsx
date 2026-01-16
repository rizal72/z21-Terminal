import React, { useState, useEffect } from 'react';

/**
 * SpeedTableViewer Component (Phase 1 - Read-Only)
 *
 * Displays 28-step JMRI speed table (CV67-94) for consist's adjust locomotive.
 * Highlights problematic speeds based on CRITICAL/WARNING event counts.
 * Shows CV adjustment recommendations below chart.
 *
 * Props:
 *   - consistId: Consist ID to analyze (10, 11, etc.)
 *   - sessionId: Current session ID (triggers refresh when changed)
 */
const SpeedTableViewer = ({ consistId, sessionId }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  // Fetch speed table data from API
  useEffect(() => {
    if (!consistId) return;

    const fetchSpeedTableData = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(`/api/speed-table/${consistId}`);

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch speed table data');
        }

        const result = await response.json();
        setData(result);
      } catch (err) {
        console.error('Speed table fetch error:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchSpeedTableData();
  }, [consistId, sessionId]); // Refresh when session changes

  // Export speed table to CSV (JMRI-compatible format)
  const exportToCSV = () => {
    if (!data || !data.cv_values) return;

    // JMRI-compatible CSV Header (CV,value format)
    let csv = 'CV,value\n';

    // Build rows (28 steps, CV67-94)
    for (let step = 1; step <= 28; step++) {
      const cvIndex = 66 + step; // CV67-94
      const currentValue = data.cv_values[cvIndex] || 0;

      // Find recommendation for this CV (if any)
      const recommendation = data.recommendations?.find(r => r.cv_index === cvIndex);

      // Use suggested value if recommendation exists, otherwise current value
      const finalValue = recommendation ? recommendation.cv_suggested : currentValue;

      csv += `${cvIndex},${finalValue}\n`;
    }

    // Download CSV file
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `speed_table_consist_${consistId}_loco_${data.adjust_loco_address}_JMRI.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Loading state
  if (loading) {
    return (
      <div className="h-96 flex items-center justify-center text-slate-400">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p>Loading speed table data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="h-96 flex items-center justify-center text-slate-400">
        <div className="text-center">
          <p className="text-lg mb-2 text-red-400">Error loading speed table</p>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  // No data state (shouldn't happen - backend always returns data)
  if (!data) {
    return (
      <div className="h-96 flex items-center justify-center text-slate-400">
        <div className="text-center">
          <p className="text-lg mb-2">Loading speed table data...</p>
        </div>
      </div>
    );
  }

  // Calculate which steps correspond to round percentages (10%, 20%, 30%...)
  // Use same formula as backend: step = floor(speed / 4.5) + 1
  const percentToStep = {};
  for (let percent = 10; percent <= 100; percent += 10) {
    const dccSpeed = (percent / 100) * 126; // 10% = 12.6, 20% = 25.2, etc.
    const step = Math.floor(dccSpeed / 4.5) + 1; // Same as backend speed_to_jmri_step()
    const cappedStep = Math.min(step, 28); // Cap at 28
    percentToStep[cappedStep] = `${percent}%`;
  }

  const getPercentLabel = (step) => {
    return percentToStep[step] || null;
  };

  // Render 28 vertical bars (CV67-94)
  const bars = [];
  for (let step = 1; step <= 28; step++) {
    const cvIndex = 66 + step; // CV67-94
    const cvValue = data.cv_values[cvIndex] || 0;
    const fillPercent = (cvValue / 255) * 100; // 0-255 → 0-100%

    // Check if this CV has recommendations (problematic speeds)
    const hasRecommendation = data.recommendations?.some(r => r.cv_index === cvIndex);
    const recommendation = data.recommendations?.find(r => r.cv_index === cvIndex);

    // Border/fill color based on severity
    let borderColor = 'border-slate-600'; // Default
    let fillColor = 'bg-slate-600'; // Default

    if (hasRecommendation && recommendation) {
      if (recommendation.critical_count >= 10) {
        borderColor = 'border-red-500';
        fillColor = 'bg-red-500';
      } else if (recommendation.critical_count >= 5) {
        borderColor = 'border-amber-500';
        fillColor = 'bg-amber-500';
      }
    }

    const percentLabel = getPercentLabel(step);

    bars.push(
      <div key={step} className="flex flex-col items-center">
        {/* CV Value (top) */}
        <div className="text-xs font-mono text-slate-400 mb-1 h-4">
          {cvValue}
        </div>

        {/* Vertical Bar */}
        <div
          className={`relative w-8 h-64 border-2 ${borderColor} rounded-sm bg-slate-800`}
          title={`Step ${step} - CV${cvIndex} = ${cvValue}${hasRecommendation ? ` (${recommendation.critical_count} critical)` : ''}`}
        >
          {/* Fill (bottom-up) */}
          <div
            className={`absolute bottom-0 left-0 right-0 ${fillColor} rounded-sm transition-all duration-300`}
            style={{ height: `${fillPercent}%` }}
          />
        </div>

        {/* JMRI Step Number (middle) */}
        <div className="text-xs font-mono text-slate-500 mt-1">
          {step}
        </div>

        {/* Speed Percentage (bottom) - only for round percentages */}
        <div className="text-xs font-mono text-white h-4">
          {percentLabel || ''}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <div className="text-sm text-slate-400">Adjust Locomotive</div>
          <div className="text-xl font-bold text-white mt-1">
            {data.adjust_loco_name}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Address {data.adjust_loco_address} • {Object.keys(data.cv_values).length}/28 CV
          </div>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <div className="text-sm text-slate-400">Recommendations</div>
          <div className="text-3xl font-bold text-white mt-1">
            {data.recommendations?.length || 0}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            CV adjustments needed
          </div>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-4 border border-green-700/50">
          <div className="text-sm text-slate-400">Fixed Speeds</div>
          <div className="text-3xl font-bold text-green-400 mt-1">
            {data.fixed_count || 0}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Proven OK recently
          </div>
        </div>
      </div>

      {/* Header: Loco info + Export button */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-slate-400 flex items-center gap-2">
          <span className="font-semibold">Adjust Loco:</span> {data.adjust_loco_address} |{' '}
          <span className="font-semibold">Session:</span>
          {data.session_id ? (
            <span className="font-mono text-slate-300">{data.session_id}</span>
          ) : (
            <span className="text-slate-500">None</span>
          )}
          {data.session_id && !data.session_validated && (
            <span className="ml-2 px-2 py-0.5 text-xs font-semibold bg-amber-600 text-white rounded">
              WAITING FOR FIRST ΔT
            </span>
          )}
        </div>
        <button
          onClick={exportToCSV}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          <i className="fa-solid fa-download"></i>
          <span>Export for JMRI</span>
        </button>
      </div>

      {/* 28 Vertical Bars */}
      <div className="flex justify-center gap-1 overflow-x-auto pb-4">
        {bars}
      </div>

      {/* CV Recommendations (below chart) */}
      {data.recommendations && data.recommendations.length > 0 ? (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <h3 className="text-white font-semibold mb-3 text-lg">
            CV Adjustment Recommendations
          </h3>
          <div className="space-y-2">
            {data.recommendations.map((rec) => (
              <div
                key={rec.cv_index}
                className="flex items-center justify-between text-sm border-b border-slate-700 pb-2"
              >
                <div className="flex items-center gap-4">
                  <span className="font-mono text-white font-semibold w-28">
                    Step {rec.jmri_step} <span className="text-slate-500 font-normal">(CV{rec.cv_index})</span>
                  </span>
                  <span className="text-slate-300">
                    {rec.cv_current} → {rec.cv_suggested}
                  </span>
                  <span className={`font-mono ${rec.cv_delta > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {rec.cv_delta > 0 ? '+' : ''}{rec.cv_delta}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-xs">
                  <span className={`font-mono ${rec.mean_delta_t < 0 ? 'text-blue-400' : 'text-amber-400'}`}>
                    Δt {rec.mean_delta_t >= 0 ? '+' : ''}{rec.mean_delta_t.toFixed(2)}s
                  </span>
                  <span className="text-red-400">
                    {rec.critical_count} critical
                  </span>
                  {rec.warning_count > 0 && (
                    <span className="text-amber-400">
                      {rec.warning_count} warning
                    </span>
                  )}
                  <span className="text-slate-500">
                    Speed {rec.speed}
                  </span>
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-500 mt-4">
            💡 Export to CSV and import via JMRI DecoderPro (File → Import → CSV) to apply these adjustments
          </p>
        </div>
      ) : (
        <div className="bg-green-900/20 border border-green-700 rounded-lg p-4 text-center">
          <p className="text-green-400 font-semibold">
            ✓ No CV adjustments needed
          </p>
          <p className="text-slate-400 text-sm mt-1">
            All speeds are within acceptable tolerance
          </p>
        </div>
      )}
    </div>
  );
};

export default SpeedTableViewer;
