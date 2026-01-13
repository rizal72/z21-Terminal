import { useState, useEffect, useRef } from 'react';
import { LineChart, Line, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';

// Locomotive colors (matches config.json locomotive_colors)
const LOCO_COLORS = {
  1: '#FFFF00',  // Yellow (Gr675 017)
  5: '#FF8000',  // Orange (D645 014)
  7: '#00FF00',  // Green (E656 239)
  8: '#FF0000',  // Red (E444 056)
};

export default function AnalyticsPanel({ isOpen, onClose }) {
  const [viewMode, setViewMode] = useState('current'); // 'current' or 'overview'
  const [cumulativeData, setCumulativeData] = useState(null);
  const [currentSession, setCurrentSession] = useState(null); // Current session metadata
  const [locoStats, setLocoStats] = useState(null); // Locomotive operating time stats
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [consistFilter, setConsistFilter] = useState('all'); // 'all', 10, 11

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

  // Prepare chart data from session events (with consist separation)
  const prepareChartData = () => {
    if (!sessionData || !sessionData.events) return [];

    return sessionData.events
      .filter(event => consistFilter === 'all' || event.consist_id === consistFilter)
      .map((event, idx) => ({
        index: idx + 1,
        timestamp: event.timestamp,
        time: formatTime(event.timestamp),
        delta_t_c10: event.consist_id === 10 ? parseFloat(event.delta_t.toFixed(2)) : null,
        delta_t_c11: event.consist_id === 11 ? parseFloat(event.delta_t.toFixed(2)) : null,
        status: event.status,
        gate_type: event.gate_type
      }));
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="relative w-full max-w-6xl max-h-[90vh] overflow-y-auto bg-gradient-to-br from-slate-900 to-slate-800 rounded-xl shadow-2xl">
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

        {/* View Toggle - Sticky below header */}
        <div className="sticky top-[88px] z-10 flex gap-2 p-4 bg-slate-800/50 border-b border-slate-700 items-center justify-between shadow-lg">
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
                    {consistFilter === 'all' ? ' (All)' : consistFilter === 10 ? ' (C10)' : ' (C11)'}
                  </div>
                  <div className={`text-3xl font-bold mt-1 ${
                    consistFilter === 10 ? 'text-fuchsia-400' :
                    consistFilter === 11 ? 'text-blue-400' :
                    'text-white'
                  }`}>
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
                    {consistFilter === 'all' ? ' (All)' : consistFilter === 10 ? ' (C10)' : ' (C11)'}
                  </div>
                  <div className={`text-3xl font-bold mt-1 ${
                    consistFilter === 10 ? 'text-fuchsia-400' :
                    consistFilter === 11 ? 'text-blue-400' :
                    'text-red-400'
                  }`}>
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
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xl font-bold text-white">Δt Trends (All Sessions)</h3>

                    {/* Consist Filter Toggle */}
                    <div className="flex gap-2">
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
                      <button
                        onClick={() => setConsistFilter(10)}
                        className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                          consistFilter === 10
                            ? 'bg-fuchsia-600 text-white'
                            : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
                        }`}
                      >
                        Consist 10
                      </button>
                      <button
                        onClick={() => setConsistFilter(11)}
                        className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                          consistFilter === 11
                            ? 'bg-blue-600 text-white'
                            : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
                        }`}
                      >
                        Consist 11
                      </button>
                    </div>
                  </div>

                  {(() => {
                    const chartData = cumulativeData.delta_t_events
                      .filter(event => consistFilter === 'all' || event.consist_id === consistFilter)
                      .map((event, idx) => ({
                        index: idx + 1,
                        timestamp: event.timestamp,
                        time: formatTime(event.timestamp),
                        delta_t_c10: event.consist_id === 10 ? parseFloat(event.delta_t.toFixed(2)) : null,
                        delta_t_c11: event.consist_id === 11 ? parseFloat(event.delta_t.toFixed(2)) : null,
                        status: event.status,
                        gate_type: event.gate_type
                      }));

                    const chartWidth = viewMode === 'current' ? Math.max(chartData.length * 40, 800) : '100%';
                    const chartContent = (
                      <ResponsiveContainer width={chartWidth} height={400}>
                          <LineChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="time" stroke="#9CA3AF" />
                      <YAxis stroke="#9CA3AF" label={{ value: 'Δt (seconds)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                        labelStyle={{ color: '#e2e8f0' }}
                        itemStyle={{ color: '#e2e8f0' }}
                        formatter={(value) => value !== null ? value.toFixed(2) + 's' : 'N/A'}
                      />
                      {/* Only show Legend when All filter (prevents chart height shift on filter change) */}
                      {consistFilter === 'all' && <Legend />}
                      <ReferenceLine y={0} stroke="#10b981" strokeDasharray="3 3" />
                      <ReferenceLine y={1} stroke="#f59e0b" strokeDasharray="3 3" label="WARNING" />
                      <ReferenceLine y={-1} stroke="#f59e0b" strokeDasharray="3 3" />
                      <ReferenceLine y={1.5} stroke="#ef4444" strokeDasharray="3 3" label="CRITICAL" />
                      <ReferenceLine y={-1.5} stroke="#ef4444" strokeDasharray="3 3" />

                          {/* Show both lines when 'all', single line when filtered */}
                          {(consistFilter === 'all' || consistFilter === 10) && (
                            <Line
                              type="monotone"
                              dataKey="delta_t_c10"
                              stroke="#d946ef"
                              strokeWidth={viewMode === 'current' ? 2 : 1.5}
                              dot={viewMode === 'current' ? { r: 4 } : false}
                              name="Consist 10"
                              connectNulls={true}
                            />
                          )}
                          {(consistFilter === 'all' || consistFilter === 11) && (
                            <Line
                              type="monotone"
                              dataKey="delta_t_c11"
                              stroke="#3b82f6"
                              strokeWidth={viewMode === 'current' ? 2 : 1.5}
                              dot={viewMode === 'current' ? { r: 4 } : false}
                              name="Consist 11"
                              connectNulls={true}
                            />
                          )}
                        </LineChart>
                      </ResponsiveContainer>
                    );

                    return viewMode === 'current' ? (
                      <div ref={scrollRefSession} className="overflow-x-auto">
                        <div style={{ minWidth: chartWidth }}>
                          {chartContent}
                        </div>
                      </div>
                    ) : chartContent;
                  })()}
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
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis dataKey="time" stroke="#9CA3AF" />
                            <YAxis stroke="#9CA3AF" domain={[0, 140]} label={{ value: 'FPS', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }} />
                            <Tooltip
                              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                              labelStyle={{ color: '#e2e8f0' }}
                              itemStyle={{ color: '#e2e8f0' }}
                              formatter={(value) => value.toFixed(1) + ' FPS'}
                            />
                            <ReferenceLine y={30} stroke="#10b981" strokeDasharray="5 5" label={{ value: 'Target (30 FPS)', position: 'top', fill: '#10b981' }} />
                            <Line type="monotone" dataKey="fps" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} name="Inference FPS" />
                          </LineChart>
                        </ResponsiveContainer>
                      );

                      return viewMode === 'current' ? (
                        <div ref={scrollRefFps} className="overflow-x-auto">
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
                        // Current view: only current session (empty if no data yet)
                        // Overview view: latest event globally
                        let events = cumulativeData.yolo_performance;

                        if (viewMode === 'current' && currentSession) {
                          events = events.filter(e => e.session_id === currentSession.session_id);
                        }

                        if (events.length === 0) return [];

                        const latestEvent = events[events.length - 1];
                        const avgConfidence = latestEvent.avg_confidence;

                        // Convert to bar chart data with consist filtering
                        // Consist 10: addresses 1, 5 | Consist 11: addresses 7, 8
                        const consistAddresses = {
                          10: [1, 5],
                          11: [7, 8]
                        };

                        const addressFilter = consistFilter === 'all'
                          ? [1, 5, 7, 8]
                          : consistAddresses[consistFilter];

                        return Object.entries(avgConfidence)
                          .filter(([addr]) => addressFilter.includes(parseInt(addr)))
                          .map(([dcc_addr, conf]) => ({
                            loco: `Loco ${dcc_addr}`,
                            address: parseInt(dcc_addr),  // Store address for color mapping
                            confidence: parseFloat((conf * 100).toFixed(1)) // Convert to percentage
                          }));
                      })()}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="loco" stroke="#9CA3AF" />
                        <YAxis stroke="#9CA3AF" domain={[0, 100]} label={{ value: 'Confidence (%)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                          labelStyle={{ color: '#e2e8f0' }}
                          itemStyle={{ color: '#e2e8f0' }}
                          formatter={(value) => value.toFixed(1) + '%'}
                        />
                        <ReferenceLine y={50} stroke="#ef4444" strokeDasharray="5 5" label={{ value: 'Min Threshold (50%)', position: 'top', fill: '#ef4444' }} />
                        <Bar dataKey="confidence">
                          {(() => {
                            // Map Cell colors using same data preparation logic
                            let events = cumulativeData.yolo_performance;
                            if (viewMode === 'current' && currentSession) {
                              events = events.filter(e => e.session_id === currentSession.session_id);
                            }
                            if (events.length === 0) return [];

                            const latestEvent = events[events.length - 1];
                            const avgConfidence = latestEvent.avg_confidence;

                            const consistAddresses = {
                              10: [1, 5],
                              11: [7, 8]
                            };
                            const addressFilter = consistFilter === 'all'
                              ? [1, 5, 7, 8]
                              : consistAddresses[consistFilter];

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

              {/* Locomotive Operating Time */}
              {(() => {
                // Filter locomotive stats by view mode
                let displayStats;

                if (viewMode === 'current' && currentSession && cumulativeData) {
                  // Current view: Calculate from loco_operating_time events for current session
                  const locoEvents = cumulativeData.loco_operating_time?.filter(e =>
                    e.session_id === currentSession.session_id &&
                    e.address !== undefined &&
                    e.duration_seconds !== undefined
                  ) || [];

                  // Aggregate by address
                  const statsMap = {};
                  locoEvents.forEach(event => {
                    const addr = event.address;
                    if (!statsMap[addr]) {
                      statsMap[addr] = { address: addr, name: `Loco ${addr}`, total_seconds: 0 };
                    }
                    statsMap[addr].total_seconds += event.duration_seconds;
                  });

                  // Convert to array and calculate hours
                  displayStats = Object.values(statsMap).map(stat => ({
                    address: stat.address,
                    name: stat.name,
                    total_operating_hours: Math.round((stat.total_seconds / 3600) * 100) / 100
                  })).sort((a, b) => a.address - b.address);
                } else {
                  // Overview view: Use global stats from API
                  displayStats = locoStats || [];
                }

                // Always render chart (like Confidence chart), even with empty data
                return (
                  <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700">
                    <h3 className="text-xl font-bold text-white mb-4">Locomotive Operating Time</h3>

                    <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
                      <h4 className="text-lg font-semibold text-amber-400 mb-4">Total Operating Hours</h4>
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={displayStats}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                          <XAxis dataKey="name" stroke="#9CA3AF" />
                          <YAxis stroke="#9CA3AF" label={{ value: 'Operating Hours', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }} />
                          <Tooltip
                            contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                            labelStyle={{ color: '#e2e8f0' }}
                            itemStyle={{ color: '#e2e8f0' }}
                            formatter={(value) => `${value} hours`}
                          />
                          <Bar dataKey="total_operating_hours">
                            {displayStats.map((loco, index) => (
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
