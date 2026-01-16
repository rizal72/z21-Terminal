import React, { useState, useEffect } from 'react';

/**
 * SpeedTableViewer Component (Phase 2 - Interactive Editing)
 *
 * Displays 28-step JMRI speed table (CV67-94) for consist's adjust locomotive.
 * Highlights problematic speeds based on CRITICAL/WARNING event counts.
 * Shows CV adjustment recommendations with interactive editing.
 * Supports checkpoint-based interpolation with float precision.
 *
 * Props:
 *   - consistId: Consist ID to analyze (10, 11, etc.)
 *   - sessionId: Current session ID (triggers refresh when changed)
 */
const SpeedTableViewer = ({ consistId, sessionId }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  // Float precision state for interpolation (CV67-94)
  // Stores decimal values internally, rounds only on display/export
  const [cvValuesFloat, setCvValuesFloat] = useState({});

  // Checkpoint system - steps marked as fixed points for interpolation
  // Default: operational speed percentages (10%, 20%, ..., 100%)
  const DEFAULT_CHECKPOINTS = [3, 6, 9, 12, 15, 17, 20, 23, 26, 28];
  const [checkpoints, setCheckpoints] = useState(DEFAULT_CHECKPOINTS);

  // Editing state - track which step is being edited
  const [editingStep, setEditingStep] = useState(null);
  const [editingValue, setEditingValue] = useState('');

  // Recommendations approval state
  const [selectedRecommendations, setSelectedRecommendations] = useState(new Set());

  // Initialize selected recommendations (default: all checked)
  useEffect(() => {
    if (!data || !data.recommendations) return;
    setSelectedRecommendations(new Set(data.recommendations.map(r => r.cv_index)));
  }, [data]);

  // Toggle recommendation selection
  const toggleRecommendation = (cvIndex) => {
    setSelectedRecommendations(prev => {
      const newSet = new Set(prev);
      if (newSet.has(cvIndex)) {
        newSet.delete(cvIndex);
      } else {
        newSet.add(cvIndex);
      }
      return newSet;
    });
  };

  // Select all recommendations
  const selectAllRecommendations = () => {
    if (!data || !data.recommendations) return;
    setSelectedRecommendations(new Set(data.recommendations.map(r => r.cv_index)));
  };

  // Deselect all recommendations
  const deselectAllRecommendations = () => {
    setSelectedRecommendations(new Set());
  };

  // Apply selected recommendations
  const applySelectedRecommendations = () => {
    if (!data || !data.recommendations || selectedRecommendations.size === 0) return;

    // Apply each selected recommendation
    data.recommendations.forEach(rec => {
      if (selectedRecommendations.has(rec.cv_index)) {
        const step = rec.jmri_step;
        applyInterpolation(step, rec.cv_suggested);
      }
    });

    // Clear selection after apply
    setSelectedRecommendations(new Set());
  };

  // Toggle checkpoint on/off
  const toggleCheckpoint = (step) => {
    setCheckpoints(prev => {
      if (prev.includes(step)) {
        // Remove checkpoint (but keep at least 2 for interpolation to work)
        return prev.length > 2 ? prev.filter(s => s !== step) : prev;
      } else {
        // Add checkpoint
        return [...prev, step].sort((a, b) => a - b);
      }
    });
  };

  // Linear interpolation formula
  const interpolate = (stepA, valueA, stepB, valueB, stepX) => {
    return valueA + (valueB - valueA) * (stepX - stepA) / (stepB - stepA);
  };

  // Apply interpolation after checkpoint modification
  const applyInterpolation = (modifiedStep, newValue) => {
    const sortedCheckpoints = [...checkpoints].sort((a, b) => a - b);
    const currentIdx = sortedCheckpoints.indexOf(modifiedStep);

    // Find previous and next checkpoints
    const prevCheckpoint = currentIdx > 0 ? sortedCheckpoints[currentIdx - 1] : null;
    const nextCheckpoint = currentIdx < sortedCheckpoints.length - 1 ? sortedCheckpoints[currentIdx + 1] : null;

    const updatedValues = { ...cvValuesFloat };

    // Update the modified checkpoint (exact value)
    updatedValues[66 + modifiedStep] = newValue;

    // Interpolate zone: prevCheckpoint → modifiedStep
    if (prevCheckpoint !== null) {
      const prevValue = updatedValues[66 + prevCheckpoint];
      for (let step = prevCheckpoint + 1; step < modifiedStep; step++) {
        if (!checkpoints.includes(step)) { // Only interpolate non-checkpoint steps
          updatedValues[66 + step] = interpolate(
            prevCheckpoint, prevValue,
            modifiedStep, newValue,
            step
          );
        }
      }
    }

    // Interpolate zone: modifiedStep → nextCheckpoint
    if (nextCheckpoint !== null) {
      const nextValue = updatedValues[66 + nextCheckpoint];
      for (let step = modifiedStep + 1; step < nextCheckpoint; step++) {
        if (!checkpoints.includes(step)) { // Only interpolate non-checkpoint steps
          updatedValues[66 + step] = interpolate(
            modifiedStep, newValue,
            nextCheckpoint, nextValue,
            step
          );
        }
      }
    }

    setCvValuesFloat(updatedValues);
  };

  // Start editing checkpoint value
  const startEditing = (step) => {
    if (!checkpoints.includes(step)) return; // Only checkpoints are editable
    setEditingStep(step);
    setEditingValue(Math.round(cvValuesFloat[66 + step] || 0).toString());
  };

  // Save edited value and apply interpolation
  const saveEdit = () => {
    if (editingStep === null) return;

    const newValue = parseInt(editingValue, 10);
    if (isNaN(newValue) || newValue < 0 || newValue > 255) {
      alert('CV value must be between 0 and 255');
      return;
    }

    applyInterpolation(editingStep, newValue);
    setEditingStep(null);
    setEditingValue('');
  };

  // Cancel editing
  const cancelEdit = () => {
    setEditingStep(null);
    setEditingValue('');
  };

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

  // Initialize cvValuesFloat from API data (convert integers to floats)
  useEffect(() => {
    if (!data || !data.cv_values) return;

    const floatValues = {};
    for (let step = 1; step <= 28; step++) {
      const cvIndex = 66 + step;
      // Convert integer CV values to floats (e.g., 128 → 128.0)
      floatValues[cvIndex] = parseFloat(data.cv_values[cvIndex] || 0);
    }

    setCvValuesFloat(floatValues);
  }, [data]); // Re-initialize when new data arrives

  // Export speed table to CSV (JMRI-compatible format)
  const exportToCSV = () => {
    if (!data || !cvValuesFloat || Object.keys(cvValuesFloat).length === 0) return;

    // JMRI-compatible CSV Header (CV,value format)
    let csv = 'CV,value\n';

    // Build rows (28 steps, CV67-94)
    // Phase 2: Export current cvValuesFloat (includes user edits + applied recommendations)
    for (let step = 1; step <= 28; step++) {
      const cvIndex = 66 + step; // CV67-94
      // Use cvValuesFloat (rounds to integer for JMRI compatibility)
      const finalValue = Math.round(cvValuesFloat[cvIndex] || 0);

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
    // Use float values for rendering (round for display)
    const cvValueFloat = cvValuesFloat[cvIndex] || 0;
    const cvValue = Math.round(cvValueFloat); // Display value (integer)
    const fillPercent = (cvValueFloat / 255) * 100; // Fill based on float (more accurate)

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
    const isCheckpoint = checkpoints.includes(step);
    const isEditing = editingStep === step;

    bars.push(
      <div key={step} className="flex flex-col items-center">
        {/* CV Value (top) - editable if checkpoint and in editing mode */}
        {isEditing ? (
          <div className="mb-1 h-4">
            <input
              type="number"
              min="0"
              max="255"
              value={editingValue}
              onChange={(e) => setEditingValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') saveEdit();
                if (e.key === 'Escape') cancelEdit();
              }}
              className="w-12 px-1 text-xs font-mono text-center bg-slate-700 text-white border border-blue-500 rounded"
              autoFocus
            />
          </div>
        ) : (
          <div
            className={`text-xs font-mono mb-1 h-4 ${isCheckpoint ? 'text-blue-400 font-bold cursor-pointer hover:text-blue-300' : 'text-slate-400'}`}
            onClick={() => isCheckpoint && startEditing(step)}
            title={isCheckpoint ? 'Click to edit' : 'Auto-interpolated'}
          >
            {cvValue}
          </div>
        )}

        {/* Vertical Bar */}
        <div
          className={`relative w-8 h-64 border-2 ${borderColor} rounded-sm bg-slate-800 ${isCheckpoint && !isEditing ? 'cursor-pointer' : ''}`}
          title={`Step ${step} - CV${cvIndex} = ${cvValue}${hasRecommendation ? ` (${recommendation.critical_count} critical)` : ''}`}
          onClick={() => isCheckpoint && !isEditing && startEditing(step)}
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

        {/* Checkpoint Checkbox */}
        <input
          type="checkbox"
          checked={isCheckpoint}
          onChange={() => toggleCheckpoint(step)}
          className="mt-1 cursor-pointer"
          title={isCheckpoint ? "Fixed checkpoint (click to uncheck)" : "Auto-interpolated (click to fix)"}
        />

        {/* Speed Percentage (bottom) - only for checkpoints */}
        <div className="text-xs font-mono text-blue-400 h-4">
          {isCheckpoint && percentLabel ? percentLabel : ''}
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
          {/* Header with action buttons */}
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-white font-semibold text-lg">
              CV Adjustment Recommendations ({data.recommendations.length})
            </h3>
            <div className="flex items-center gap-2">
              <button
                onClick={selectAllRecommendations}
                className="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors"
              >
                Select All
              </button>
              <button
                onClick={deselectAllRecommendations}
                className="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors"
              >
                Deselect All
              </button>
              <button
                onClick={applySelectedRecommendations}
                disabled={selectedRecommendations.size === 0}
                className="px-4 py-1 text-xs bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed text-white rounded transition-colors font-semibold"
              >
                Apply {selectedRecommendations.size > 0 ? `${selectedRecommendations.size} Selected` : ''}
              </button>
            </div>
          </div>

          <div className="space-y-2">
            {data.recommendations.map((rec) => {
              const isSelected = selectedRecommendations.has(rec.cv_index);
              return (
                <div
                  key={rec.cv_index}
                  className={`flex items-center gap-3 text-sm border-b border-slate-700 pb-2 ${isSelected ? 'opacity-100' : 'opacity-50'}`}
                >
                  {/* Checkbox */}
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleRecommendation(rec.cv_index)}
                    className="cursor-pointer"
                  />

                  <div className="flex items-center justify-between flex-1">
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
                </div>
              );
            })}
          </div>
          <p className="text-xs text-slate-500 mt-4">
            💡 Click Apply to update speed table with selected recommendations. Changes can be exported to CSV or written via POM.
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
