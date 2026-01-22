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

  // Helper: Convert DCC speed command (0-126) to percentage (0-100%)
  const speedToPercentage = (dccSpeed) => Math.round((dccSpeed / 126) * 100);

  // Float precision state for interpolation (CV67-94)
  // Stores decimal values internally, rounds only on display/export
  const [cvValuesFloat, setCvValuesFloat] = useState({});

  // Decoder metadata state (vstart, vhigh, decoder_type)
  const [vstart, setVstart] = useState(null);
  const [vhigh, setVhigh] = useState(null);
  const [decoderType, setDecoderType] = useState('nmra_standard');

  // CV modification timestamps (step → Unix timestamp, for green border indicator)
  const [cvTimestamps, setCvTimestamps] = useState({});

  // Vstart/Vhigh editing state (ESU only)
  const [editingVstart, setEditingVstart] = useState(false);
  const [editingVstartValue, setEditingVstartValue] = useState('');
  const [editingVhigh, setEditingVhigh] = useState(false);
  const [editingVhighValue, setEditingVhighValue] = useState('');

  // Checkpoint system - steps marked as fixed points for interpolation
  // Default: operational speed percentages (10%, 20%, ..., 100%)
  const DEFAULT_CHECKPOINTS = [3, 6, 9, 12, 15, 17, 20, 23, 26, 28];
  const [checkpoints, setCheckpoints] = useState(DEFAULT_CHECKPOINTS);

  // Editing state - track which step is being edited
  const [editingStep, setEditingStep] = useState(null);
  const [editingValue, setEditingValue] = useState('');

  // Recommendations approval state
  const [selectedRecommendations, setSelectedRecommendations] = useState(new Set());

  // CV write state (Phase 2 - Direct decoder write)
  const [writing, setWriting] = useState(false);
  const [writeError, setWriteError] = useState(null);
  const [writeSuccess, setWriteSuccess] = useState(null);

  // Undo/Reimport state
  const [undoing, setUndoing] = useState(false);
  const [reimporting, setReimporting] = useState(false);

  // Debug panel state
  const [debugEnabled, setDebugEnabled] = useState(false);
  const [debugPanelOpen, setDebugPanelOpen] = useState(true);

  // Fetch config to check debug mode
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await fetch('/api/config');
        if (response.ok) {
          const config = await response.json();
          setDebugEnabled(config.debug?.enabled || false);
        }
      } catch (err) {
        console.error('Failed to fetch config:', err);
      }
    };
    fetchConfig();
  }, []);

  // Fetch speed table data from API
  const fetchSpeedTableData = async () => {
    if (!consistId) return;

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

      // Set decoder metadata
      setVstart(result.vstart);
      setVhigh(result.vhigh);
      setDecoderType(result.decoder_type || 'nmra_standard');

      // Set CV modification timestamps (for green border indicator)
      setCvTimestamps(result.cv_timestamps || {});
    } catch (err) {
      console.error('Speed table fetch error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

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
        // Skip smoothing for ESU endpoints (CV2/CV5 for step 1/28)
        // User will manually adjust adjacent CVs if needed (like JMRI behavior)
        if (rec.esu_endpoint === true) {
          return; // ESU endpoints don't apply smoothing
        }

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

  // Load speed table data on mount and when consistId/sessionId changes
  useEffect(() => {
    fetchSpeedTableData();
  }, [consistId, sessionId]);

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

    // Add "_backup" suffix if no modifications (exporting original roster values)
    const suffix = hasModifications ? '' : '_backup';
    link.download = `speed_table_consist_${consistId}_loco_${data.adjust_loco_address}${suffix}.csv`;

    link.click();
    URL.revokeObjectURL(url);
  };

  // Write speed table to decoder (Phase 2 - Direct CV Write)
  const writeToDecoder = async () => {
    if (!data || !cvValuesFloat || Object.keys(cvValuesFloat).length === 0) return;

    setWriting(true);
    setWriteError(null);
    setWriteSuccess(null);

    try {
      // Prepare cv_values payload (all 28 CVs, rounded to integers)
      const cvValues = {};
      for (let step = 1; step <= 28; step++) {
        const cvIndex = 66 + step; // CV67-94
        cvValues[cvIndex] = Math.round(cvValuesFloat[cvIndex] || 0);
      }

      const response = await fetch(`/api/speed-table/write/${consistId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cv_values: cvValues })
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || 'Failed to write CVs to decoder');
      }

      if (result.success) {
        // Success message (acknowledge blocked CVs if any)
        const blockedCount = result.blocked_cvs?.length || 0;
        const successMsg = blockedCount > 0
          ? `Successfully wrote ${result.cvs_written}/28 CVs to loco ${result.adjust_loco_address} (${blockedCount} read-only) [${result.total_time}s]`
          : `Successfully wrote 28 CVs to loco ${result.adjust_loco_address} [${result.total_time}s]`;
        setWriteSuccess(successMsg);
        // Reload speed table data to sync UI (remove asterisks and highlights)
        await fetchSpeedTableData();
      } else {
        setWriteError(`Partial write: ${result.cvs_written}/28 CVs written (failed: ${result.failed_cvs.join(', ')})`);
      }
    } catch (err) {
      setWriteError(err.message);
    } finally {
      setWriting(false);
    }
  };

  // Write CV2 (Vstart) and/or CV5 (Vhigh) to ESU decoder (ESU only)
  const writeVstartVhigh = async (newVstart, newVhigh) => {
    if (!consistId) return;

    setWriting(true);
    setWriteError(null);
    setWriteSuccess(null);

    try {
      const payload = {};
      if (newVstart !== null && newVstart !== undefined) payload.vstart = newVstart;
      if (newVhigh !== null && newVhigh !== undefined) payload.vhigh = newVhigh;

      const response = await fetch(`/api/speed-table/write-vstart-vhigh/${consistId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || 'Failed to write CV2/CV5');
      }

      if (result.success) {
        setWriteSuccess(`CV2/CV5 written successfully (${result.total_time}s)`);
        // Reload data to sync UI
        await fetchSpeedTableData();
      } else {
        setWriteError('Failed to write CV2/CV5');
      }
    } catch (err) {
      setWriteError(err.message);
    } finally {
      setWriting(false);
    }
  };

  // Apply & Write: Write to decoder then export CSV
  const applyAndWrite = async () => {
    await writeToDecoder();
    // Export CSV after write completes (or fails)
    setTimeout(() => exportToCSV(), 500); // Small delay to show write result first
  };

  // Undo Last Change: Restore previous CV values from DB and write to decoder
  const handleUndo = async () => {
    if (!confirm('Restore previous CV values and write them to decoder? This will undo the last change.')) {
      return;
    }

    setUndoing(true);
    setWriteError(null);
    setWriteSuccess(null);

    try {
      const response = await fetch(`/api/speed-table/undo/${consistId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Undo failed');
      }

      const result = await response.json();

      if (result.success) {
        setWriteSuccess(`Undo successful! ${result.cvs_written}/28 CVs restored in ${result.total_time}s`);
        // Reload speed table data
        await fetchSpeedTableData();
      } else {
        setWriteError(`Undo partially successful: ${result.failed_cvs.length}/28 CVs failed`);
      }
    } catch (err) {
      console.error('Undo error:', err);
      setWriteError(err.message);
    } finally {
      setUndoing(false);
    }
  };

  // Re-import from JMRI: Force re-read CV from JMRI roster and update DB
  const handleReimport = async () => {
    if (!confirm('Re-import speed table from JMRI roster? This will overwrite current database values with JMRI values.')) {
      return;
    }

    setReimporting(true);
    setWriteError(null);
    setWriteSuccess(null);

    try {
      const response = await fetch(`/api/speed-table/reimport/${consistId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Re-import failed');
      }

      const result = await response.json();

      if (result.success) {
        setWriteSuccess(`Re-import successful! CV values synced from JMRI roster for loco ${result.adjust_loco_address}`);
        // Reload speed table data
        await fetchSpeedTableData();
      } else {
        setWriteError('Re-import failed');
      }
    } catch (err) {
      console.error('Re-import error:', err);
      setWriteError(err.message);
    } finally {
      setReimporting(false);
    }
  };

  // Check if any CVs were modified (manual edit or applied recommendations)
  const hasModifications = data && Object.keys(cvValuesFloat).some(cvIndex => {
    const cvIndexInt = parseInt(cvIndex);
    return cvValuesFloat[cvIndexInt] !== data.cv_values[cvIndexInt];
  });

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

    // Check if this CV was modified (manual edit or applied recommendation)
    const isModified = data.cv_values && cvValueFloat !== data.cv_values[cvIndex];

    // Check if this CV has been modified via web UI (persistent, from DB)
    const cvTimestamp = cvTimestamps[step] || 0;
    const isPersistentlyModified = cvTimestamp > 0;

    // ESU decoder: step 1 and 28 are read-only (fixed at 1 and 255)
    const isStepEditable = decoderType === 'esu_mfx' ? (step !== 1 && step !== 28) : true;

    // Border/fill color based on severity (priority: read-only > CRITICAL > modified > default)
    let borderColor = 'border-slate-600'; // Default
    let fillColor = 'bg-slate-600'; // Default
    let leftBorderClass = ''; // Green left border for persistent modifications

    if (!isStepEditable) {
      // ESU read-only steps (grey)
      borderColor = 'border-slate-700';
      fillColor = 'bg-slate-700';
    } else if (hasRecommendation && recommendation) {
      // CRITICAL overrides everything
      if (recommendation.critical_count >= 10) {
        borderColor = 'border-red-500';
        fillColor = 'bg-red-500';
      } else if (recommendation.critical_count >= 5) {
        borderColor = 'border-amber-500';
        fillColor = 'bg-amber-500';
      }
    } else if (isModified) {
      // Modified (no CRITICAL) shows blue border
      borderColor = 'border-blue-400';
    }

    // Green left border if CV was modified via web UI (persistent state)
    if (isPersistentlyModified && isStepEditable) {
      leftBorderClass = 'border-l-2 border-l-green-500';
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
              }}
              onBlur={() => {
                // Only save + interpolate if value actually changed
                const currentValue = Math.round(cvValuesFloat[66 + editingStep] || 0);
                const newValue = parseInt(editingValue);

                if (!isNaN(newValue) && newValue !== currentValue) {
                  saveEdit(); // Save + interpolate
                } else {
                  cancelEdit(); // Close without interpolating
                }
              }}
              className="w-12 px-1 text-xs font-mono text-center bg-slate-700 text-white border border-blue-500 rounded"
              autoFocus
            />
          </div>
        ) : (
          <div
            className={`text-xs font-mono mb-1 h-4 flex items-center gap-0.5 ${
              !isStepEditable
                ? 'text-slate-600'
                : isCheckpoint
                ? 'text-blue-400 font-bold cursor-pointer hover:text-blue-300'
                : 'text-slate-400'
            }`}
            onClick={() => isStepEditable && isCheckpoint && startEditing(step)}
            title={
              !isStepEditable
                ? `Step ${step} is read-only for ESU decoders (fixed at ${cvValue})`
                : isCheckpoint
                ? 'Click to edit'
                : 'Auto-interpolated'
            }
          >
            <span>{cvValue}</span>
            {isModified && <span className="text-blue-400 text-xs">*</span>}
          </div>
        )}

        {/* Vertical Bar */}
        <div
          className={`relative w-8 h-64 border-2 ${borderColor} ${leftBorderClass} rounded-sm bg-slate-800 ${
            isStepEditable && isCheckpoint && !isEditing ? 'cursor-pointer' : ''
          }`}
          title={
            !isStepEditable
              ? `Step ${step} - CV${cvIndex} = ${cvValue} (read-only for ESU)`
              : `Step ${step} - CV${cvIndex} = ${cvValue}${hasRecommendation ? ` (${recommendation.critical_count} critical)` : ''}${isPersistentlyModified ? ' [Modified]' : ''}`
          }
          onClick={() => isStepEditable && isCheckpoint && !isEditing && startEditing(step)}
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

        {/* CV Number (67-94) */}
        <div className="text-[10px] font-mono text-slate-600 mt-0.5">
          CV{cvIndex}
        </div>

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
      <div className="grid grid-cols-2 gap-4">
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
        {/* Fixed Speeds card removed (2026-01-22): Redundant with per-CV filtering */}
        {/* Recommendations disappear after CV write, implicit "fixed" when not reappearing */}
      </div>

      {/* ESU Decoder - Vstart/Vhigh Panel (only for ESU) */}
      {decoderType === 'esu_mfx' && (
        <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-white font-semibold text-lg">
                ESU Decoder - Vstart/Vhigh Endpoints
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Edit CV2/CV5 FIRST to set min/max speed. Then adjust CV68-93 to shape the curve.
              </p>
            </div>
            <span className="px-3 py-1 text-xs bg-blue-600 text-white rounded">
              ESU mfx
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* CV2 Vstart */}
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700">
              <div className="text-sm text-slate-400 mb-2">CV2 - Vstart (Step 1)</div>
              {editingVstart ? (
                <input
                  type="number"
                  min="0"
                  max="255"
                  value={editingVstartValue}
                  onChange={(e) => setEditingVstartValue(e.target.value)}
                  onBlur={() => {
                    const val = parseInt(editingVstartValue);
                    if (!isNaN(val) && val !== vstart) {
                      writeVstartVhigh(val, null);
                    }
                    setEditingVstart(false);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const val = parseInt(editingVstartValue);
                      if (!isNaN(val) && val !== vstart) {
                        writeVstartVhigh(val, null);
                      }
                      setEditingVstart(false);
                    }
                  }}
                  className="w-full px-3 py-2 text-lg font-mono bg-slate-700 text-white border border-blue-500 rounded"
                  autoFocus
                />
              ) : (
                <div
                  onClick={() => {
                    setEditingVstart(true);
                    setEditingVstartValue((vstart || 0).toString());
                  }}
                  className="text-2xl font-mono text-white cursor-pointer hover:text-blue-400"
                >
                  {vstart !== null ? vstart : 'N/A'}
                </div>
              )}
            </div>

            {/* CV5 Vhigh */}
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700">
              <div className="text-sm text-slate-400 mb-2">CV5 - Vhigh (Step 28)</div>
              {editingVhigh ? (
                <input
                  type="number"
                  min="0"
                  max="255"
                  value={editingVhighValue}
                  onChange={(e) => setEditingVhighValue(e.target.value)}
                  onBlur={() => {
                    const val = parseInt(editingVhighValue);
                    if (!isNaN(val) && val !== vhigh) {
                      writeVstartVhigh(null, val);
                    }
                    setEditingVhigh(false);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const val = parseInt(editingVhighValue);
                      if (!isNaN(val) && val !== vhigh) {
                        writeVstartVhigh(null, val);
                      }
                      setEditingVhigh(false);
                    }
                  }}
                  className="w-full px-3 py-2 text-lg font-mono bg-slate-700 text-white border border-blue-500 rounded"
                  autoFocus
                />
              ) : (
                <div
                  onClick={() => {
                    setEditingVhigh(true);
                    setEditingVhighValue((vhigh || 0).toString());
                  }}
                  className="text-2xl font-mono text-white cursor-pointer hover:text-blue-400"
                >
                  {vhigh !== null ? vhigh : 'N/A'}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

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
        <div className="flex items-center gap-2">
          <button
            onClick={applyAndWrite}
            disabled={!hasModifications || writing}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-semibold"
            title={!hasModifications ? "No modifications to write" : "Write all CVs to decoder and export CSV"}
          >
            {writing ? (
              <>
                <i className="fa-solid fa-spinner fa-spin"></i>
                <span>Writing CVs...</span>
              </>
            ) : (
              <>
                <i className="fa-solid fa-microchip"></i>
                <span>Apply & Write to Decoder</span>
              </>
            )}
          </button>
          <button
            onClick={exportToCSV}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            <i className="fa-solid fa-download"></i>
            <span>Export CSV Only</span>
          </button>

          {/* Secondary actions (icon only, right-aligned) */}
          <button
            onClick={handleUndo}
            disabled={undoing}
            className="ml-auto px-2 py-2 bg-amber-600/80 hover:bg-amber-600 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed text-white rounded transition-colors"
            title="Undo last change (restore previous CV values)"
          >
            <i className={`fa-solid ${undoing ? 'fa-spinner fa-spin' : 'fa-undo'}`}></i>
          </button>
          {/* Re-import button DEPRECATED (2026-01-22) - Hidden from UI, backend code preserved */}
          {/* JMRI used ONLY for initial new locomotive setup via scripts/import_single_locomotive.py */}
          {/*
          <button
            onClick={handleReimport}
            disabled={reimporting}
            className="px-2 py-2 bg-slate-600/80 hover:bg-slate-600 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed text-white rounded transition-colors"
            title="Re-import from JMRI roster (sync database with JMRI)"
          >
            <i className={`fa-solid ${reimporting ? 'fa-spinner fa-spin' : 'fa-sync'}`}></i>
          </button>
          */}
        </div>
      </div>

      {/* Write feedback messages */}
      {writeSuccess && (
        <div className="mt-4 p-3 bg-green-900/30 border border-green-600 rounded-lg text-green-400 text-sm">
          <i className="fa-solid fa-check-circle mr-2"></i>
          {writeSuccess}
        </div>
      )}
      {writeError && (
        <div className="mt-4 p-3 bg-red-900/30 border border-red-600 rounded-lg text-red-400 text-sm">
          <i className="fa-solid fa-exclamation-triangle mr-2"></i>
          {writeError}
        </div>
      )}

      {/* 28 Vertical Bars */}
      <div className="flex justify-center gap-1 overflow-x-auto pb-4">
        {bars}
      </div>

      {/* Speed Analysis Debug Panel (only if debug enabled) */}
      {debugEnabled && data.debug_info && Object.keys(data.debug_info).length > 0 && (
        <div className="mt-6 bg-purple-900/20 border border-purple-700 rounded-lg overflow-hidden">
          {/* Collapsible Header */}
          <button
            onClick={() => setDebugPanelOpen(!debugPanelOpen)}
            className="w-full flex items-center justify-between p-4 hover:bg-purple-900/30 transition-colors"
          >
            <div className="flex items-center gap-3">
              <i className={`fa-solid fa-chart-line text-purple-400 text-lg`}></i>
              <h3 className="text-white font-semibold text-lg">Speed Analysis Debug</h3>
              <span className="px-2 py-1 text-xs bg-purple-600 text-white rounded">
                {Object.keys(data.debug_info).length} speeds analyzed
              </span>
            </div>
            <i className={`fa-solid fa-chevron-${debugPanelOpen ? 'up' : 'down'} text-purple-400`}></i>
          </button>

          {/* Debug Content */}
          {debugPanelOpen && (
            <div className="p-4 pt-0 space-y-3">
              {/* Header Info */}
              <div className="text-xs text-slate-400 flex items-center gap-4 border-b border-purple-700/50 pb-2">
                <span>Consist {data.consist_id}</span>
                <span>Session: {data.session_id || 'None'}</span>
                <span>Threshold: {data.recommendation_threshold || 10} events</span>
              </div>

              {/* Speed Analysis Rows */}
              <div className="space-y-3">
                {Object.entries(data.debug_info)
                  .sort(([speedA], [speedB]) => parseInt(speedA) - parseInt(speedB))
                  .map(([speed, debugInfo]) => {
                    const hasRecommendation = data.recommendations?.some(r => r.speed === parseInt(speed));
                    const meetsThreshold = debugInfo.weighted_result?.meets_threshold;

                    return (
                      <div key={speed} className="bg-slate-800/50 rounded-lg p-3 border border-slate-700">
                        {/* Speed Header */}
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-mono text-white font-semibold">Speed {speed} ({speedToPercentage(parseInt(speed))}%)</span>
                          <div className="flex items-center gap-2 text-xs">
                            {meetsThreshold && (
                              <span className="px-2 py-0.5 bg-green-600 text-white rounded">
                                Sufficient data
                              </span>
                            )}
                            {hasRecommendation && (
                              <span className="px-2 py-0.5 bg-amber-600 text-white rounded">
                                Has recommendation
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Current Session Stats */}
                        <div className="text-xs text-slate-300 mb-1">
                          <span className="text-blue-400 font-semibold">Current:</span>{' '}
                          {debugInfo.current_session.count} events, Δt{' '}
                          {debugInfo.current_session.mean_delta_t >= 0 ? '+' : ''}
                          {debugInfo.current_session.mean_delta_t.toFixed(2)}s{' '}
                          <span className="text-slate-500">
                            ({Math.round(debugInfo.current_session.weight * 100)}% weight)
                          </span>
                          <span className={debugInfo.current_session.critical_count > 0 ? 'text-red-400 ml-2' : 'text-slate-500 ml-2'}>
                            {debugInfo.current_session.critical_count} critical
                          </span>
                          <span className={debugInfo.current_session.warning_count > 0 ? 'text-amber-400 ml-2' : 'text-slate-500 ml-2'}>
                            {debugInfo.current_session.warning_count} warning
                          </span>
                        </div>

                        {/* Historical Stats */}
                        <div className="text-xs text-slate-300 mb-1">
                          <span className="text-green-400 font-semibold">Historical:</span>{' '}
                          {debugInfo.historical.count} events, Δt{' '}
                          {debugInfo.historical.mean_delta_t >= 0 ? '+' : ''}
                          {debugInfo.historical.mean_delta_t.toFixed(2)}s{' '}
                          <span className="text-slate-500">
                            ({Math.round(debugInfo.historical.weight * 100)}% weight)
                          </span>
                          <span className={debugInfo.historical.critical_count > 0 ? 'text-red-400 ml-2' : 'text-slate-500 ml-2'}>
                            {debugInfo.historical.critical_count} critical
                          </span>
                          <span className={debugInfo.historical.warning_count > 0 ? 'text-amber-400 ml-2' : 'text-slate-500 ml-2'}>
                            {debugInfo.historical.warning_count} warning
                          </span>
                        </div>

                        {/* Weighted Result */}
                        <div className="text-xs mt-2 pt-2 border-t border-slate-700">
                          <span className="text-purple-400 font-semibold">→ Weighted:</span>{' '}
                          <span className={`font-mono ${debugInfo.weighted_result.mean_delta_t < 0 ? 'text-blue-400' : 'text-amber-400'}`}>
                            Δt {debugInfo.weighted_result.mean_delta_t >= 0 ? '+' : ''}
                            {debugInfo.weighted_result.mean_delta_t.toFixed(2)}s
                          </span>
                          {!meetsThreshold && debugInfo.current_session.count > 0 && (
                            <span className="text-slate-500 ml-2">
                              (below threshold, historical weighted)
                            </span>
                          )}
                          {debugInfo.current_session.count === 0 && (
                            <span className="text-slate-500 ml-2">
                              (no current data)
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </div>
      )}

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
              const isEsuEndpoint = rec.esu_endpoint === true;
              return (
                <div
                  key={rec.cv_index}
                  className={`flex items-center gap-3 text-sm border-b pb-2 ${
                    isEsuEndpoint
                      ? 'border-blue-500 bg-blue-900/10'
                      : 'border-slate-700'
                  } ${isSelected ? 'opacity-100' : 'opacity-50'}`}
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
                      {isEsuEndpoint && (
                        <span className="px-2 py-0.5 text-xs bg-blue-600 text-white rounded font-semibold">
                          ESU
                        </span>
                      )}
                      <span className="font-mono text-white font-semibold w-28">
                        Step {rec.jmri_step} <span className="text-slate-500 font-normal">(CV{rec.cv_index})</span>
                      </span>
                      <span className="text-slate-300">
                        {rec.cv_current} → {rec.cv_suggested}
                      </span>
                      <span className={`font-mono ${rec.cv_delta > 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {rec.cv_delta > 0 ? '+' : ''}{rec.cv_delta}
                      </span>
                      {isEsuEndpoint && (
                        <span className="text-xs text-blue-300">
                          ⚠️ Edit {rec.cv_index === 2 ? 'Vstart' : 'Vhigh'} in panel above
                        </span>
                      )}
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
                        Speed {rec.speed} ({speedToPercentage(rec.speed)}%)
                      </span>
                    </div>

                    {/* Weighted breakdown (always visible if debug_info present) */}
                    {rec.debug_info && (
                      <div className="mt-1 pl-4 text-xs text-slate-400 flex items-center gap-4 flex-wrap">
                        <span>
                          → Current: {rec.debug_info.current_session.count} events,
                          Δt {rec.debug_info.current_session.mean_delta_t >= 0 ? '+' : ''}{rec.debug_info.current_session.mean_delta_t.toFixed(2)}s
                          ({Math.round(rec.debug_info.current_session.weight * 100)}%)
                        </span>
                        <span>
                          | Historical: {rec.debug_info.historical.count} events,
                          Δt {rec.debug_info.historical.mean_delta_t >= 0 ? '+' : ''}{rec.debug_info.historical.mean_delta_t.toFixed(2)}s
                          ({Math.round(rec.debug_info.historical.weight * 100)}%)
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          <p className="text-xs text-slate-500 mt-4">
            💡 Click Apply to update speed table with selected recommendations. Use "Apply & Write to Decoder" to write CVs directly via POM (includes CSV export), or "Export CSV Only" for JMRI manual import.
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
