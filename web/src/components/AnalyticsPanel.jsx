import { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';

export default function AnalyticsPanel({ isOpen, onClose }) {
  const [viewMode, setViewMode] = useState('detail'); // 'detail' or 'overview'
  const [cumulativeData, setCumulativeData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [consistFilter, setConsistFilter] = useState('all'); // 'all', 10, 11

  // Ref for auto-scroll to end
  const scrollRefSession = useRef(null);

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

  // Load cumulative data on mount
  useEffect(() => {
    if (isOpen) {
      loadCumulativeData();
    }
  }, [isOpen]);

  // Auto-scroll to end when data loads (Detail view only)
  useEffect(() => {
    if (viewMode === 'detail' && cumulativeData && scrollRefSession.current) {
      scrollRefSession.current.scrollLeft = scrollRefSession.current.scrollWidth;
    }
  }, [cumulativeData, viewMode]);

  const loadCumulativeData = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/analytics/cumulative');
      const data = await response.json();

      if (data.error) {
        setError(data.error);
        setCumulativeData(null);
        return;
      }

      setCumulativeData(data);
    } catch (err) {
      setError(`Failed to load cumulative data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleViewToggle = (newView) => {
    setViewMode(newView);
    setCumulativeData(null);

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

        {/* View Toggle */}
        <div className="flex gap-2 p-4 bg-slate-800/50 border-b border-slate-700 items-center justify-between">
          <div className="flex gap-2">
            <button
              onClick={() => handleViewToggle('detail')}
              className={`px-6 py-2 rounded-lg font-medium transition-all ${
                viewMode === 'detail'
                  ? 'bg-blue-600 text-white shadow-lg'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              <i className="fa-solid fa-magnifying-glass-chart mr-2"></i>
              Detail
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
              {/* Overall Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                  <div className="text-sm text-slate-400">Total Sessions</div>
                  <div className="text-3xl font-bold text-white mt-1">{cumulativeData.total_sessions}</div>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                  <div className="text-sm text-slate-400">Total Δt Events</div>
                  <div className="text-3xl font-bold text-white mt-1">{cumulativeData.total_delta_t_events}</div>
                </div>
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
                    {consistFilter === 'all'
                      ? (cumulativeData.gate_crossings?.[10] || 0) + (cumulativeData.gate_crossings?.[11] || 0)
                      : (cumulativeData.gate_crossings?.[consistFilter] || 0)
                    }
                  </div>
                </div>
              </div>

              {/* Δt Trends Chart - ALL sessions concatenated */}
              {cumulativeData.delta_t_events && cumulativeData.delta_t_events.length > 0 && (
                <div key={viewMode} className="bg-slate-800/50 rounded-lg p-6 border border-slate-700">
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

                    const chartWidth = viewMode === 'detail' ? Math.max(chartData.length * 40, 800) : '100%';
                    const chartContent = (
                      <ResponsiveContainer width={chartWidth} height={400}>
                          <LineChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="time" stroke="#9CA3AF" />
                      <YAxis stroke="#9CA3AF" label={{ value: 'Δt (seconds)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                        labelStyle={{ color: '#e2e8f0' }}
                        formatter={(value) => value !== null ? value.toFixed(2) + 's' : 'N/A'}
                      />
                      <Legend />
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
                              strokeWidth={viewMode === 'detail' ? 2 : 1.5}
                              dot={viewMode === 'detail' ? { r: 4 } : false}
                              name="Consist 10"
                              connectNulls={true}
                            />
                          )}
                          {(consistFilter === 'all' || consistFilter === 11) && (
                            <Line
                              type="monotone"
                              dataKey="delta_t_c11"
                              stroke="#3b82f6"
                              strokeWidth={viewMode === 'detail' ? 2 : 1.5}
                              dot={viewMode === 'detail' ? { r: 4 } : false}
                              name="Consist 11"
                              connectNulls={true}
                            />
                          )}
                        </LineChart>
                      </ResponsiveContainer>
                    );

                    return viewMode === 'detail' ? (
                      <div ref={scrollRefSession} className="overflow-x-auto">
                        {chartContent}
                      </div>
                    ) : chartContent;
                  })()}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
