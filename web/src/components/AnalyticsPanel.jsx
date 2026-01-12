import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';

export default function AnalyticsPanel({ isOpen, onClose }) {
  const [viewMode, setViewMode] = useState('current'); // 'current' or 'cumulative'
  const [currentSession, setCurrentSession] = useState(null);
  const [sessionData, setSessionData] = useState(null);
  const [cumulativeData, setCumulativeData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [consistFilter, setConsistFilter] = useState('all'); // 'all', 10, 11

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

  // Load current session metadata on mount
  useEffect(() => {
    if (isOpen && viewMode === 'current') {
      loadCurrentSession();
    }
  }, [isOpen, viewMode]);

  // Load cumulative data on view switch
  useEffect(() => {
    if (isOpen && viewMode === 'cumulative') {
      loadCumulativeData();
    }
  }, [isOpen, viewMode]);

  const loadCurrentSession = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/analytics/current');
      const data = await response.json();

      if (data.error) {
        setError(data.error);
        setCurrentSession(null);
        return;
      }

      setCurrentSession(data);

      // Load full session data if validated
      if (data.validated && data.session_id) {
        const sessionResponse = await fetch(`/api/analytics/session/${data.session_id}`);
        const sessionData = await sessionResponse.json();
        setSessionData(sessionData);
      }
    } catch (err) {
      setError(`Failed to load session: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

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
    setSessionData(null);
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
        delta_t_c10: event.consist_id === 10 ? event.delta_t : null,
        delta_t_c11: event.consist_id === 11 ? event.delta_t : null,
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
              onClick={() => handleViewToggle('current')}
              className={`px-6 py-2 rounded-lg font-medium transition-all ${
                viewMode === 'current'
                  ? 'bg-blue-600 text-white shadow-lg'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              <i className="fa-solid fa-clock mr-2"></i>
              Current Session
            </button>
            <button
              onClick={() => handleViewToggle('cumulative')}
              className={`px-6 py-2 rounded-lg font-medium transition-all ${
                viewMode === 'cumulative'
                  ? 'bg-blue-600 text-white shadow-lg'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              <i className="fa-solid fa-database mr-2"></i>
              Cumulative History
            </button>
          </div>

          {/* Refresh Button */}
          <button
            onClick={() => {
              if (viewMode === 'current') {
                loadCurrentSession();
              } else {
                loadCumulativeData();
              }
            }}
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

          {/* Current Session View */}
          {viewMode === 'current' && currentSession && !loading && (
            <div className="space-y-6">
              {/* Session Info */}
              <div className="grid grid-cols-4 gap-4">
                <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                  <div className="text-sm text-slate-400">Session ID</div>
                  <div className="text-lg font-bold text-white mt-1">{currentSession.session_id}</div>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                  <div className="text-sm text-slate-400">Uptime</div>
                  <div className="text-lg font-bold text-white mt-1">{formatDuration(currentSession.uptime)}</div>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                  <div className="text-sm text-slate-400">Event Count</div>
                  <div className="text-lg font-bold text-white mt-1">{currentSession.event_count}</div>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                  <div className="text-sm text-slate-400">Status</div>
                  <div className={`text-lg font-bold mt-1 ${currentSession.validated ? 'text-green-400' : 'text-amber-400'}`}>
                    {currentSession.validated ? 'Validated' : 'Pending'}
                  </div>
                </div>
              </div>

              {/* Δt Trends Chart */}
              {sessionData && sessionData.events && sessionData.events.length > 0 && (
                <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700 overflow-x-hidden">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xl font-bold text-white">Δt Trends</h3>

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

                  <ResponsiveContainer width="100%" height={400}>
                    <LineChart data={prepareChartData()}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="time" stroke="#9CA3AF" />
                      <YAxis stroke="#9CA3AF" label={{ value: 'Δt (seconds)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                        labelStyle={{ color: '#e2e8f0' }}
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
                          strokeWidth={2}
                          dot={{ r: 4 }}
                          name="Consist 10"
                          connectNulls={false}
                        />
                      )}
                      {(consistFilter === 'all' || consistFilter === 11) && (
                        <Line
                          type="monotone"
                          dataKey="delta_t_c11"
                          stroke="#3b82f6"
                          strokeWidth={2}
                          dot={{ r: 4 }}
                          name="Consist 11"
                          connectNulls={false}
                        />
                      )}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {!sessionData && currentSession.validated && (
                <div className="text-center py-8 text-slate-400">
                  <i className="fa-solid fa-chart-line text-4xl mb-4"></i>
                  <p>No Δt data yet. Start tracking to see trends.</p>
                </div>
              )}

              {!currentSession.validated && (
                <div className="text-center py-8 text-amber-400">
                  <i className="fa-solid fa-clock text-4xl mb-4"></i>
                  <p>Session pending validation. First Δt calculation required.</p>
                </div>
              )}
            </div>
          )}

          {/* Cumulative History View */}
          {viewMode === 'cumulative' && cumulativeData && !loading && (
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
                  <div className="text-sm text-slate-400">Gate Crossings (Consist 11)</div>
                  <div className="text-3xl font-bold text-white mt-1">{cumulativeData.gate_crossings?.[11] || 0}</div>
                </div>
              </div>

              {/* Δt Trends Chart - ALL sessions concatenated */}
              {cumulativeData.delta_t_events && cumulativeData.delta_t_events.length > 0 && (
                <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700 overflow-x-hidden">
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

                  <ResponsiveContainer width="100%" height={400}>
                    <LineChart data={cumulativeData.delta_t_events
                      .filter(event => consistFilter === 'all' || event.consist_id === consistFilter)
                      .map((event, idx) => ({
                        index: idx + 1,
                        timestamp: event.timestamp,
                        time: formatTime(event.timestamp),
                        delta_t_c10: event.consist_id === 10 ? event.delta_t : null,
                        delta_t_c11: event.consist_id === 11 ? event.delta_t : null,
                        status: event.status,
                        gate_type: event.gate_type
                      }))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="time" stroke="#9CA3AF" />
                      <YAxis stroke="#9CA3AF" label={{ value: 'Δt (seconds)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                        labelStyle={{ color: '#e2e8f0' }}
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
                          strokeWidth={2}
                          dot={{ r: 4 }}
                          name="Consist 10"
                          connectNulls={false}
                        />
                      )}
                      {(consistFilter === 'all' || consistFilter === 11) && (
                        <Line
                          type="monotone"
                          dataKey="delta_t_c11"
                          stroke="#3b82f6"
                          strokeWidth={2}
                          dot={{ r: 4 }}
                          name="Consist 11"
                          connectNulls={false}
                        />
                      )}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
