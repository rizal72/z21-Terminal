import { useState, useEffect, useRef, memo, useMemo } from 'react';
import { LineChart, Line, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, Brush } from 'recharts';

// Locomotive colors (matches config.json locomotive_colors)
const LOCO_COLORS = {
  1: '#FFFF00',  // Yellow (Gr675 017)
  5: '#FF8000',  // Orange (D645 014)
  7: '#00FF00',  // Green (E656 239)
  8: '#FF0000',  // Red (E444 056)
};

// Consist colors (dynamic assignment, cyclic if > colors available)
const CONSIST_COLOR_PALETTE = ['#d946ef', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
const CONSIST_COLOR_CLASSES = ['text-fuchsia-400', 'text-blue-400', 'text-green-400', 'text-amber-400', 'text-red-400', 'text-purple-400'];
const CONSIST_BG_CLASSES = ['bg-fuchsia-600', 'bg-blue-600', 'bg-green-600', 'bg-amber-600', 'bg-red-600', 'bg-purple-600'];

// Shared chart styles (dark mode)
const TOOLTIP_STYLES = {
  contentStyle: { backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' },
  labelStyle: { color: '#e2e8f0' },
  itemStyle: { color: '#e2e8f0' }
};

const CHART_AXIS_STYLES = {
  grid: { strokeDasharray: '3 3', stroke: '#374151' },
  axis: { stroke: '#9CA3AF' }
};

// Helper functions
const filterEventsBySession = (events, viewMode, currentSession) => {
  if (viewMode === 'current' && currentSession && events) {
    return events.filter(e => e.session_id === currentSession.session_id);
  }
  return events || [];
};

// Helper: get locomotive addresses for consist filter (dynamic from config)
const getAddressFilter = (consistFilter, consistConfig) => {
  if (consistFilter === 'all') {
    // All consists: flatten all addresses
    return Object.values(consistConfig).flatMap(c => c.addresses);
  }
  return consistConfig[consistFilter]?.addresses || [];
};

// Helper: get consist stroke color (cyclic palette)
const getConsistStrokeColor = (consistId, consistConfig) => {
  const consistIds = Object.keys(consistConfig).map(Number).sort((a, b) => a - b);
  const index = consistIds.indexOf(consistId);
  return index >= 0 ? CONSIST_COLOR_PALETTE[index % CONSIST_COLOR_PALETTE.length] : '#9CA3AF';
};

// Helper: get consist text color class (cyclic palette)
const getConsistColorClass = (consistFilter, consistConfig, defaultColor = 'text-white') => {
  if (consistFilter === 'all') return defaultColor;
  const consistIds = Object.keys(consistConfig).map(Number).sort((a, b) => a - b);
  const index = consistIds.indexOf(consistFilter);
  return index >= 0 ? CONSIST_COLOR_CLASSES[index % CONSIST_COLOR_CLASSES.length] : defaultColor;
};

// Helper: get consist background color class for buttons (cyclic palette)
const getConsistBgClass = (consistId, consistConfig) => {
  const consistIds = Object.keys(consistConfig).map(Number).sort((a, b) => a - b);
  const index = consistIds.indexOf(consistId);
  return index >= 0 ? CONSIST_BG_CLASSES[index % CONSIST_BG_CLASSES.length] : 'bg-slate-600';
};

export default function AnalyticsPanel({ isOpen, onClose }) {
  const [viewMode, setViewMode] = useState('current'); // 'current' or 'overview'
  const [cumulativeData, setCumulativeData] = useState(null);
  const [currentSession, setCurrentSession] = useState(null); // Current session metadata
  const [locoStats, setLocoStats] = useState(null); // Locomotive operating time stats
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [consistFilter, setConsistFilter] = useState('all'); // 'all', 10, 11, etc. (dynamic)
  const [trackingConfig, setTrackingConfig] = useState({
    idle_timeout_seconds: 10,
    consists: {} // { 10: { name, lead_address, rear_address, addresses: [...] }, 11: {...} }
  });

  // Refs for auto-scroll to end
  const scrollRefSession = useRef(null);
  const scrollRefFps = useRef(null);

  // Desktop-only enforcement
  useEffect(() => {
    if (isOpen && window.innerWidth < 1024) {
      alert('Analytics dashboard is optimized for desktop (1024px+). Some features may not work properly on smaller screens.');
    }
  }, [isOpen]);

  // Prevent body scroll when panel is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'auto';
    }

    // Cleanup on unmount
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, [isOpen]);

  // Fetch tracking config on mount (idle timeout for line breaks)
  useEffect(() => {
    if (isOpen) {
      fetch('/api/config/tracking')
        .then(res => res.json())
        .then(data => setTrackingConfig(data))
        .catch(err => console.warn('Failed to load tracking config, using default 10s:', err));
    }
  }, [isOpen]);

  // Load cumulative data on mount and when view mode changes
  useEffect(() => {
    if (isOpen) {
      loadCumulativeData();
    }
  }, [isOpen, viewMode]);

  // Auto-scroll to END (most recent events) - ALWAYS, for all filters
  useEffect(() => {
    if (cumulativeData) {
      // Wait for DOM to resize chart after filter change, then scroll to end
      requestAnimationFrame(() => {
        // Scroll dT chart
        if (scrollRefSession.current) {
          scrollRefSession.current.scrollLeft = scrollRefSession.current.scrollWidth;
        }
        // Scroll FPS chart
        if (scrollRefFps.current) {
          scrollRefFps.current.scrollLeft = scrollRefFps.current.scrollWidth;
        }
      });
    }
  }, [cumulativeData, viewMode, consistFilter]);

  // Arrow key navigation between Current/Overview
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyPress = (e) => {
      if (e.key === 'ArrowLeft' && viewMode === 'overview') {
        handleViewToggle('current');
      } else if (e.key === 'ArrowRight' && viewMode === 'current') {
        handleViewToggle('overview');
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [isOpen, viewMode]);

  const loadCumulativeData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Build API URL with view-specific parameters
      // Current view: tail (last N events, full resolution)
      // Overview view: maxPoints (sampling across entire history)
      const params = viewMode === 'current' ? 'tail=1000' : 'maxPoints=500';
      const cumulativeUrl = `/api/analytics/cumulative?${params}`;

      // Fetch cumulative data, current session, AND locomotive stats in parallel
      const [cumulativeResponse, currentResponse, locoStatsResponse] = await Promise.all([
        fetch(cumulativeUrl),
        fetch('/api/analytics/current'),
        fetch('/api/analytics/locomotive-stats')
      ]);

      const cumulativeData = await cumulativeResponse.json();
      const currentData = await currentResponse.json();
      const locoStatsData = await locoStatsResponse.json();

      if (cumulativeData.error) {
        setError(cumulativeData.error);
        setCumulativeData(null);
        setCurrentSession(null);
        return;
      }

      setCumulativeData(cumulativeData);
      setCurrentSession(currentData.error ? null : currentData);
      setLocoStats(locoStatsData.error ? null : locoStatsData.locomotives);
    } catch (err) {
      setError(`Failed to load data: ${err.message}`);
      setCumulativeData(null);
      setCurrentSession(null);
      setLocoStats(null);
    } finally {
      setLoading(false);
    }
  };

  const handleViewToggle = (newView) => {
    setViewMode(newView);

    // Auto-refresh data on view change
    loadCumulativeData();

    // Force GPU cleanup after view change (Chrome rendering fix)
    requestAnimationFrame(() => {
      document.body.offsetHeight;
    });
  };

  const handleClose = () => {
    onClose();

    // Force GPU cleanup on close (Chrome rendering fix)
    requestAnimationFrame(() => {
      document.body.offsetHeight;
    });
  };

  // Format timestamp for chart X-axis
  const formatTime = (timestamp) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  // Format duration (seconds → mm:ss)
  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Memoize filtered events to avoid recalculation on every render
  const filteredDeltaTEvents = useMemo(() => {
    if (!cumulativeData?.delta_t_events) return [];
    return consistFilter === 'all' ?
      cumulativeData.delta_t_events :
      cumulativeData.delta_t_events.filter(e => e.consist_id === consistFilter);
  }, [cumulativeData?.delta_t_events, consistFilter]);

  // Memoize chart data preparation with session segments
  const { chartData, segmentCount } = useMemo(() => {
    if (!filteredDeltaTEvents || filteredDeltaTEvents.length === 0) return { chartData: [], segmentCount: 0 };

    const consistIds = Object.keys(trackingConfig.consists).map(Number);
    const sortedEvents = [...filteredDeltaTEvents].sort((a, b) => a.timestamp - b.timestamp);

    // Identify segment boundaries (session_id changes)
    let currentSegment = 0;
    const eventSegments = []; // Array to track which segment each event belongs to

    sortedEvents.forEach((event, idx) => {
      const prevEvent = idx > 0 ? sortedEvents[idx - 1] : null;

      // Detect session boundary
      if (prevEvent && event.session_id !== prevEvent.session_id) {
        currentSegment++;
      }

      eventSegments.push(currentSegment);
    });

    const totalSegments = currentSegment + 1;

    // Build unified dataset with segmented dataKeys
    const result = [];
    let eventIndex = 1;

    sortedEvents.forEach((event, idx) => {
      const segment = eventSegments[idx];

      // Create fields for ALL consist+segment combinations (mostly null)
      const deltaFields = {};
      consistIds.forEach(cid => {
        for (let seg = 0; seg < totalSegments; seg++) {
          const dataKey = `delta_t_c${cid}_seg${seg}`;
          // Value only if this event belongs to this consist AND this segment
          deltaFields[dataKey] = (event.consist_id === cid && segment === seg)
            ? parseFloat(event.delta_t.toFixed(2))
            : null;
        }
      });

      result.push({
        index: eventIndex++,
        timestamp: event.timestamp,
        time: formatTime(event.timestamp),
        ...deltaFields,
        status: event.status,
        gate_type: event.gate_type
      });
    });

    return { chartData: result, segmentCount: totalSegments };
  }, [filteredDeltaTEvents, trackingConfig.consists]);

  // Memoize chart width calculation
  const chartWidth = useMemo(() => {
    return viewMode === 'current' ? Math.max(chartData.length * 40, 800) : '100%';
  }, [chartData.length, viewMode]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={handleClose}
    >
      <div
        className="relative w-full max-w-6xl max-h-[90vh] overflow-y-auto bg-gradient-to-br from-slate-900 to-slate-800 rounded-xl shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between p-6 bg-gradient-to-r from-blue-600 to-indigo-600 border-b border-blue-500/30">
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <i className="fa-solid fa-chart-line"></i>
            Analytics Dashboard
          </h2>
          <button
            onClick={handleClose}
            className="p-2 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-all"
          >
            <i className="fa-solid fa-xmark text-xl"></i>
          </button>
        </div>

        {/* View Toggle & Filters - Sticky below header */}
        <div className="sticky top-[88px] z-10 p-4 bg-slate-800/50 border-b border-slate-700 shadow-lg space-y-3">
          {/* Row 1: View tabs + Refresh button */}
          <div className="flex gap-2 items-center justify-between">
            <div className="flex gap-2">
              <button
                onClick={() => handleViewToggle('current')}
                className={`px-6 py-2 rounded-lg font-medium transition-all ${
                  viewMode === 'current'
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                <i className="fa-solid fa-magnifying-glass-chart mr-2"></i>
                Current
              </button>
              <button
                onClick={() => handleViewToggle('overview')}
                className={`px-6 py-2 rounded-lg font-medium transition-all ${
                  viewMode === 'overview'
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                <i className="fa-solid fa-chart-area mr-2"></i>
                Overview
              </button>
            </div>

            {/* Refresh Button */}
            <button
              onClick={() => loadCumulativeData()}
              disabled={loading}
              className="px-4 py-2 bg-slate-700 text-slate-300 hover:bg-slate-600 rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              title="Refresh data"
            >
              <i className={`fa-solid fa-refresh mr-2 ${loading ? 'fa-spin' : ''}`}></i>
              Refresh
            </button>
          </div>

          {/* Row 2: Consist filters */}
          <div className="flex gap-2 items-center">
            <span className="text-sm text-slate-400 mr-2">Filter:</span>
            <button
              onClick={() => setConsistFilter('all')}
              className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                consistFilter === 'all'
                  ? 'bg-slate-600 text-white'
                  : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
              }`}
            >
              All Consists
            </button>
            {/* Dynamic consist filter buttons (from config) */}
            {Object.keys(trackingConfig.consists)
              .map(Number)
              .sort((a, b) => a - b)
              .map((consistId) => (
                <button
                  key={consistId}
                  onClick={() => setConsistFilter(consistId)}
                  className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                    consistFilter === consistId
                      ? `${getConsistBgClass(consistId, trackingConfig.consists)} text-white`
                      : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
                  }`}
                >
                  Consist {consistId}
                </button>
              ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {loading && (
            <div className="text-center py-12">
              <i className="fa-solid fa-spinner fa-spin text-4xl text-blue-500"></i>
              <p className="mt-4 text-slate-400">Loading analytics data...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300">
              <i className="fa-solid fa-exclamation-triangle mr-2"></i>
              {error}
            </div>
          )}

          {/* Analytics View (Unified) */}
          {cumulativeData && !loading && (
            <div className="space-y-6">
              {/* Session Not Validated Warning (Current view only) */}
              {viewMode === 'current' && currentSession && !currentSession.validated && (
                <div className="bg-amber-900/30 border border-amber-700 rounded-lg p-4 text-amber-300">
                  <i className="fa-solid fa-clock mr-2"></i>
                  Session not validated - waiting for first gate crossing
                </div>
              )}

              {/* Stats Cards (view-dependent) */}
              <div className="grid grid-cols-3 gap-4">
                {/* Card 1: Session Duration (Current) or Total Sessions (Overview) */}
                <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                  <div className="text-sm text-slate-400">
                    {viewMode === 'current' ? 'Session Duration' : 'Total Sessions'}
                  </div>
                  <div className="text-3xl font-bold text-white mt-1">
                    {viewMode === 'current'
                      ? (() => {
                          if (!currentSession || !currentSession.start_time) return 'N/A';
                          const duration = currentSession.end_time
                            ? currentSession.end_time - currentSession.start_time
                            : Date.now() / 1000 - currentSession.start_time;
                          const minutes = Math.floor(duration / 60);
                          const seconds = Math.floor(duration % 60);
                          return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
                        })()
                      : cumulativeData.total_sessions
                    }
                  </div>
                </div>

                {/* Card 2: Gate Crossings (filtered by session in Current view) */}
                <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                  <div className="text-sm text-slate-400">
                    Gate Crossings
                    {consistFilter === 'all' ? ' (All)' : ` (C${consistFilter})`}
                  </div>
                  <div className={`text-3xl font-bold mt-1 ${getConsistColorClass(consistFilter, trackingConfig.consists, 'text-white')}`}>
                    {(() => {
                      let events = cumulativeData.delta_t_events || [];

                      // Filter by session if Current view
                      if (viewMode === 'current' && currentSession) {
                        events = events.filter(e => e.session_id === currentSession.session_id);
                      }

                      // Filter by consist
                      if (consistFilter !== 'all') {
                        events = events.filter(e => e.consist_id === consistFilter);
                      }

                      return events.length;
                    })()}
                  </div>
                </div>

                {/* Card 3: Critical Events (filtered by session in Current view) */}
                <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                  <div className="text-sm text-slate-400">
                    Critical Events
                    {consistFilter === 'all' ? ' (All)' : ` (C${consistFilter})`}
                  </div>
                  <div className={`text-3xl font-bold mt-1 ${getConsistColorClass(consistFilter, trackingConfig.consists, 'text-red-400')}`}>
                    {(() => {
                      let events = cumulativeData.delta_t_events || [];

                      // Filter by session if Current view
                      if (viewMode === 'current' && currentSession) {
                        events = events.filter(e => e.session_id === currentSession.session_id);
                      }

                      // Filter by critical threshold (|Δt| >= 1.5s)
                      events = events.filter(e => Math.abs(e.delta_t) >= 1.5);

                      // Filter by consist
                      if (consistFilter !== 'all') {
                        events = events.filter(e => e.consist_id === consistFilter);
                      }

                      return events.length;
                    })()}
                  </div>
                </div>
              </div>

              {/* Δt Trends Chart - ALL sessions concatenated */}
              {cumulativeData.delta_t_events && cumulativeData.delta_t_events.length > 0 && (
                <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700">
                  <h3 className="text-xl font-bold text-white mb-4">Δt Trends (All Sessions)</h3>

                  {chartData.length > 0 && (
                    <div
                      key={consistFilter}
                      ref={viewMode === 'current' ? scrollRefSession : null}
                      style={{ width: '100%', overflowX: viewMode === 'current' ? 'auto' : 'visible' }}
                    >
                      <ResponsiveContainer width={chartWidth} height={400}>
                          <LineChart data={chartData}>
                            <CartesianGrid {...CHART_AXIS_STYLES.grid} />
                      {/* XAxis: time in Current (readable), index in Overview (compressed) */}
                      <XAxis
                        dataKey={viewMode === 'current' ? 'time' : 'index'}
                        {...CHART_AXIS_STYLES.axis}
                        label={viewMode === 'overview' ? { value: 'Event #', position: 'insideBottom', offset: -5, fill: '#9CA3AF' } : undefined}
                      />
                      <YAxis {...CHART_AXIS_STYLES.axis} label={{ value: 'Δt (seconds)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }} />
                      <Tooltip
                        {...TOOLTIP_STYLES}
                        formatter={(value) => value !== null ? value.toFixed(2) + 's' : 'N/A'}
                      />
                      {/* Only show Legend when All filter (prevents chart height shift on filter change) */}
                      {consistFilter === 'all' && <Legend />}
                      <ReferenceLine y={0} stroke="#10b981" strokeDasharray="3 3" />
                      <ReferenceLine y={1} stroke="#f59e0b" strokeDasharray="3 3" label="WARNING" />
                      <ReferenceLine y={-1} stroke="#f59e0b" strokeDasharray="3 3" />
                      <ReferenceLine y={1.5} stroke="#ef4444" strokeDasharray="3 3" label="CRITICAL" />
                      <ReferenceLine y={-1.5} stroke="#ef4444" strokeDasharray="3 3" />

                          {/* Dynamic lines: one Line per consist+segment (session breaks) */}
                          {Object.keys(trackingConfig.consists)
                            .map(Number)
                            .sort((a, b) => a - b)
                            .filter(consistId => consistFilter === 'all' || consistFilter === consistId)
                            .flatMap((consistId) => {
                              // Create one Line per segment for this consist
                              return Array.from({ length: segmentCount }, (_, segIdx) => (
                                <Line
                                  key={`${consistId}_seg${segIdx}`}
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

                            {/* Brush for zoom/pan - only in Overview mode */}
                            {viewMode === 'overview' && (
                              <Brush
                                dataKey="index"
                                height={30}
                                stroke="#3b82f6"
                                fill="#1e293b"
                              />
                            )}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </div>
              )}

              {/* YOLO Performance Monitoring - FPS & Confidence */}
              {cumulativeData.yolo_performance && cumulativeData.yolo_performance.length > 0 && (
                <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700 space-y-6">
                  <h3 className="text-xl font-bold text-white">YOLO Performance Monitoring</h3>

                  {/* FPS Line Chart */}
                  <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
                    <h4 className="text-lg font-semibold text-amber-400 mb-4">Inference FPS Over Time</h4>
                    {(() => {
                      // NO session filtering - FPS chart shows ALL sessions like dT chart
                      const chartData = cumulativeData.yolo_performance.map((e, idx) => ({
                        index: idx + 1,
                        time: formatTime(e.timestamp),
                        fps: parseFloat(e.avg_fps.toFixed(1))
                      }));

                      const chartWidth = viewMode === 'current' ? Math.max(chartData.length * 60, 800) : '100%';
                      const chartContent = (
                        <ResponsiveContainer width={chartWidth} height={300}>
                          <LineChart data={chartData}>
                            <CartesianGrid {...CHART_AXIS_STYLES.grid} />
                            {/* XAxis: time in Current (readable), index in Overview (compressed) */}
                            <XAxis
                              dataKey={viewMode === 'current' ? 'time' : 'index'}
                              {...CHART_AXIS_STYLES.axis}
                              label={viewMode === 'overview' ? { value: 'Sample #', position: 'insideBottom', offset: -5, fill: '#9CA3AF' } : undefined}
                            />
                            <YAxis {...CHART_AXIS_STYLES.axis} domain={[0, 140]} label={{ value: 'FPS', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }} />
                            <Tooltip
                              {...TOOLTIP_STYLES}
                              formatter={(value) => value.toFixed(1) + ' FPS'}
                            />
                            <ReferenceLine y={30} stroke="#10b981" strokeDasharray="5 5" label={{ value: 'Target (30 FPS)', position: 'top', fill: '#10b981' }} />
                            <Line type="monotone" dataKey="fps" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} name="Inference FPS" />
                          </LineChart>
                        </ResponsiveContainer>
                      );

                      return viewMode === 'current' ? (
                        <div key={`fps-${consistFilter}`} ref={scrollRefFps} className="overflow-x-auto">
                          <div style={{ minWidth: chartWidth }}>
                            {chartContent}
                          </div>
                        </div>
                      ) : chartContent;
                    })()}
                  </div>

                  {/* Confidence Bar Chart - Per Locomotive (DCC addresses) */}
                  <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
                    <h4 className="text-lg font-semibold text-amber-400 mb-4">Average Confidence per Locomotive</h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={(() => {
                        // Confidence chart: snapshot view, NOT time series
                        const events = filterEventsBySession(cumulativeData.yolo_performance, viewMode, currentSession);
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
                      })()}>
                        <CartesianGrid {...CHART_AXIS_STYLES.grid} />
                        <XAxis dataKey="loco" {...CHART_AXIS_STYLES.axis} />
                        <YAxis {...CHART_AXIS_STYLES.axis} domain={[0, 100]} label={{ value: 'Confidence (%)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }} />
                        <Tooltip
                          {...TOOLTIP_STYLES}
                          formatter={(value) => value.toFixed(1) + '%'}
                        />
                        <ReferenceLine y={50} stroke="#ffffff" strokeDasharray="5 5" label={{ value: 'Min Threshold (50%)', position: 'top', fill: '#ffffff' }} />
                        <Bar dataKey="confidence">
                          {(() => {
                            const events = filterEventsBySession(cumulativeData.yolo_performance, viewMode, currentSession);
                            if (events.length === 0) return [];

                            const latestEvent = events[events.length - 1];
                            const avgConfidence = latestEvent.avg_confidence;
                            const addressFilter = getAddressFilter(consistFilter, trackingConfig.consists);

                            return Object.entries(avgConfidence)
                              .filter(([addr]) => addressFilter.includes(parseInt(addr)))
                              .map(([dcc_addr], index) => (
                                <Cell key={`cell-${index}`} fill={LOCO_COLORS[parseInt(dcc_addr)] || '#9CA3AF'} />
                              ));
                          })()}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Locomotive Operating Time - ONLY in Overview (cumulative historic data) */}
              {viewMode === 'overview' && locoStats && locoStats.length > 0 && (() => {
                // Filter locomotives by consist (All/C10/C11)
                const addressFilter = getAddressFilter(consistFilter, trackingConfig.consists);
                const filteredLocoStats = locoStats.filter(loco => addressFilter.includes(loco.address));

                return filteredLocoStats.length > 0 && (
                  <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700">
                    <h3 className="text-xl font-bold text-white mb-4">Locomotive Operating Time</h3>

                    <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
                      <h4 className="text-lg font-semibold text-amber-400 mb-4">Total Operating Hours</h4>
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={filteredLocoStats}>
                          <CartesianGrid {...CHART_AXIS_STYLES.grid} />
                          <XAxis dataKey="name" {...CHART_AXIS_STYLES.axis} />
                          <YAxis {...CHART_AXIS_STYLES.axis} label={{ value: 'Operating Hours', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }} />
                          <Tooltip
                            {...TOOLTIP_STYLES}
                            formatter={(value) => `${value} hours`}
                          />
                          <Bar dataKey="total_operating_hours">
                            {filteredLocoStats.map((loco, index) => (
                              <Cell key={`cell-${index}`} fill={LOCO_COLORS[loco.address] || '#9CA3AF'} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
