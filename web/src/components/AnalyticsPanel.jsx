import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';

export default function AnalyticsPanel({ isOpen, onClose }) {
  const [viewMode, setViewMode] = useState('current'); // 'current' or 'cumulative'
  const [currentSession, setCurrentSession] = useState(null);
  const [sessionData, setSessionData] = useState(null);
  const [cumulativeData, setCumulativeData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Desktop-only enforcement
  useEffect(() => {
    if (isOpen && window.innerWidth < 1024) {
      alert('Analytics dashboard is optimized for desktop (1024px+). Some features may not work properly on smaller screens.');
    }
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

  // Prepare chart data from session events
  const prepareChartData = () => {
    if (!sessionData || !sessionData.events) return [];

    return sessionData.events.map((event, idx) => ({
      index: idx + 1,
      timestamp: event.timestamp,
      time: formatTime(event.timestamp),
      delta_t: event.delta_t,
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
        <div className="flex gap-2 p-4 bg-slate-800/50 border-b border-slate-700">
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
                <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700">
                  <h3 className="text-xl font-bold text-white mb-4">Δt Trends</h3>
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
                      <Line type="monotone" dataKey="delta_t" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
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
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                  <div className="text-sm text-slate-400">Total Sessions</div>
                  <div className="text-3xl font-bold text-white mt-1">{cumulativeData.total_sessions}</div>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                  <div className="text-sm text-slate-400">Total Δt Events</div>
                  <div className="text-3xl font-bold text-white mt-1">{cumulativeData.total_delta_t_events}</div>
                </div>
              </div>

              {/* Sessions Table */}
              <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700">
                <h3 className="text-xl font-bold text-white mb-4">Session History</h3>
                {cumulativeData.sessions && cumulativeData.sessions.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left">
                      <thead>
                        <tr className="border-b border-slate-700">
                          <th className="pb-3 text-slate-400 font-medium">Session ID</th>
                          <th className="pb-3 text-slate-400 font-medium">Start Time</th>
                          <th className="pb-3 text-slate-400 font-medium">Duration</th>
                          <th className="pb-3 text-slate-400 font-medium">Events</th>
                        </tr>
                      </thead>
                      <tbody>
                        {cumulativeData.sessions.map((session) => (
                          <tr key={session.id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                            <td className="py-3 text-white font-mono text-sm">{session.id}</td>
                            <td className="py-3 text-slate-300">{new Date(session.start_time * 1000).toLocaleString('it-IT')}</td>
                            <td className="py-3 text-slate-300">{formatDuration(session.duration)}</td>
                            <td className="py-3 text-slate-300">{session.event_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-8 text-slate-400">
                    <i className="fa-solid fa-database text-4xl mb-4"></i>
                    <p>No session history yet.</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
