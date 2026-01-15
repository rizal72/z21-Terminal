import { useState, useEffect, useRef, memo, useMemo, Fragment } from 'react';
import { LineChart, Line, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import {
  LOCO_COLORS,
  CONSIST_COLOR_PALETTE,
  CONSIST_COLOR_CLASSES,
  CONSIST_BG_CLASSES,
  TOOLTIP_STYLES,
  CHART_AXIS_STYLES
} from '../constants/analyticsConstants';
import {
  filterEventsBySession,
  getAddressFilter,
  getConsistStrokeColor,
  getConsistColorClass,
  getConsistBgClass,
  formatDeltaT,
  formatOperatingTime
} from '../utils/analyticsHelpers';
import DeltaTChart from './charts/DeltaTChart';
import FPSChart from './charts/FPSChart';
import ConfidenceChart from './charts/ConfidenceChart';
import OperatingTimeChart from './charts/OperatingTimeChart';
import HistoricalTrendChart from './charts/HistoricalTrendChart';

export default function AnalyticsPanel({ isOpen, onClose }) {
  const [viewMode, setViewMode] = useState('current'); // 'current', 'overview', or 'reports'
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

  // Reports tab state
  const [reportsData, setReportsData] = useState(null); // Session history data for Reports tab
  const [selectedSession, setSelectedSession] = useState(null); // Session selected for detail modal
  const [showSessionDetail, setShowSessionDetail] = useState(false); // Session detail modal visibility
  const [sessionLimit, setSessionLimit] = useState(30); // Number of sessions to display (30, 50, 100, 200)

  // Zoom state for Overview mode (box-select)
  const [refAreaLeft, setRefAreaLeft] = useState(null);
  const [refAreaRight, setRefAreaRight] = useState(null);
  const [zoomDomain, setZoomDomain] = useState(null); // { x: [min, max], y: [min, max] }
  const [showSessionBreaks, setShowSessionBreaks] = useState(false); // Toggle for session boundary visualization

  // Collapsible panels state (all expanded by default)
  const [collapsedPanels, setCollapsedPanels] = useState({
    statsCards: false,
    deltaTrends: false,
    yoloPerformance: false,
    locoOperatingTime: false,
    sessionHistory: false,
    historicalTrend: false
  });

  // Toggle collapse for a panel
  const togglePanel = (panelName) => {
    setCollapsedPanels(prev => ({ ...prev, [panelName]: !prev[panelName] }));
  };

  // Refs for auto-scroll to end
  const scrollRefSession = useRef(null);
  const scrollRefFps = useRef(null);

  // Ref for throttling mouseMove during box-select
  const lastMouseMoveTime = useRef(0);

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
        .then(data => setTrackingConfig({
          idle_timeout_seconds: data.idle_timeout_seconds || 10,
          consists: data.consists || {}
        }))
        .catch(err => console.warn('Failed to load tracking config, using default 10s:', err));
    }
  }, [isOpen]);

  // Load data on mount and when view mode changes
  useEffect(() => {
    if (isOpen) {
      if (viewMode === 'reports') {
        loadReportsData();
      } else {
        loadCumulativeData();
      }
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

  // Reload Reports data when consist filter or session limit changes (Reports tab only)
  useEffect(() => {
    if (isOpen && viewMode === 'reports') {
      loadReportsData();
    }
  }, [consistFilter, sessionLimit]);

  // Arrow key navigation between Current/Overview/Reports
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyPress = (e) => {
      if (e.key === 'ArrowLeft') {
        // Cycle backward: Reports → Overview → Current
        if (viewMode === 'overview') {
          handleViewToggle('current');
        } else if (viewMode === 'reports') {
          handleViewToggle('overview');
        }
      } else if (e.key === 'ArrowRight') {
        // Cycle forward: Current → Overview → Reports
        if (viewMode === 'current') {
          handleViewToggle('overview');
        } else if (viewMode === 'overview') {
          handleViewToggle('reports');
        }
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

  const loadReportsData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Build API URL with consist filter if specified (limit from sessionLimit state)
      const baseParams = `limit=${sessionLimit}`;
      const params = consistFilter === 'all' ? `?${baseParams}` : `?${baseParams}&consist_filter=${consistFilter}`;
      const response = await fetch(`/api/analytics/reports${params}`);
      const data = await response.json();

      if (data.error) {
        setError(data.error);
        setReportsData(null);
        return;
      }

      // Validate response structure
      if (!data.sessions || !Array.isArray(data.sessions)) {
        setError('Invalid reports data format');
        setReportsData(null);
        return;
      }

      // Ensure each session has a consists object (even if empty)
      const validatedData = {
        ...data,
        sessions: data.sessions.map(session => ({
          ...session,
          consists: session.consists || {}
        }))
      };

      setReportsData(validatedData);
    } catch (err) {
      setError(`Failed to load reports: ${err.message}`);
      setReportsData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleViewToggle = (newView) => {
    setViewMode(newView);

    // Auto-refresh data on view change
    if (newView === 'reports') {
      loadReportsData();
    } else {
      loadCumulativeData();
    }

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

  // Zoom handlers for Overview mode (box-select + brush + double-click reset)
  const handleMouseDown = (e) => {
    if (viewMode !== 'overview' || !e) return;
    setRefAreaLeft(e.activeLabel);
    setRefAreaRight(e.activeLabel);
  };

  const handleMouseMove = (e) => {
    if (viewMode !== 'overview' || !refAreaLeft || !e) return;

    // Throttle to 50ms (20 updates/sec max) to reduce re-renders during drag
    const now = Date.now();
    if (now - lastMouseMoveTime.current < 50) return;
    lastMouseMoveTime.current = now;

    setRefAreaRight(e.activeLabel);
  };

  const handleMouseUp = () => {
    if (viewMode !== 'overview' || !refAreaLeft || !refAreaRight) {
      setRefAreaLeft(null);
      setRefAreaRight(null);
      return;
    }

    // Determine zoom direction (left-to-right or right-to-left)
    let [left, right] = [refAreaLeft, refAreaRight];
    if (left > right) [left, right] = [right, left];

    // Ignore single-click (no drag) - minimum 5 events difference
    if (Math.abs(right - left) < 5) {
      setRefAreaLeft(null);
      setRefAreaRight(null);
      return;
    }

    // Calculate Y domain from visible data in selected X range
    const visibleData = chartData.filter(d => {
      const x = viewMode === 'current' ? d.time : d.index;
      return x >= left && x <= right;
    });

    const consistIds = Object.keys(trackingConfig.consists || {}).map(Number);
    let yMin = Infinity, yMax = -Infinity;

    // Different dataKey structure based on session breaks mode
    if (segmentCount === 0) {
      // SIMPLE MODE: delta_t_c10, delta_t_c11
      visibleData.forEach(d => {
        consistIds.forEach(cid => {
          const value = d[`delta_t_c${cid}`];
          if (value !== null && value !== undefined && !isNaN(value)) {
            yMin = Math.min(yMin, value);
            yMax = Math.max(yMax, value);
          }
        });
      });
    } else {
      // SEGMENTED MODE: delta_t_c10_seg0, delta_t_c10_seg1, etc.
      visibleData.forEach(d => {
        for (let seg = 0; seg < segmentCount; seg++) {
          consistIds.forEach(cid => {
            const value = d[`delta_t_c${cid}_seg${seg}`];
            if (value !== null && value !== undefined && !isNaN(value)) {
              yMin = Math.min(yMin, value);
              yMax = Math.max(yMax, value);
            }
          });
        }
      });
    }

    // Add 10% padding to Y axis
    const yPadding = (yMax - yMin) * 0.1;
    yMin -= yPadding;
    yMax += yPadding;

    setZoomDomain({ x: [left, right], y: [yMin, yMax] });
    setRefAreaLeft(null);
    setRefAreaRight(null);
  };

  const handleDoubleClick = () => {
    if (viewMode !== 'overview') return;
    // Reset zoom to full view
    setZoomDomain(null);
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

  // Memoize chart data preparation (with optional session segments)
  const { chartData, segmentCount } = useMemo(() => {
    if (!filteredDeltaTEvents || filteredDeltaTEvents.length === 0) return { chartData: [], segmentCount: 0 };

    const consistIds = Object.keys(trackingConfig.consists || {}).map(Number);
    const sortedEvents = [...filteredDeltaTEvents].sort((a, b) => a.timestamp - b.timestamp);

    // FAST PATH: No session breaks (default) - simple dataset
    if (!showSessionBreaks) {
      const result = sortedEvents.map((event, idx) => {
        const deltaFields = {};
        consistIds.forEach(cid => {
          deltaFields[`delta_t_c${cid}`] = event.consist_id === cid ? parseFloat(event.delta_t.toFixed(2)) : null;
        });

        return {
          index: idx + 1,
          timestamp: event.timestamp,
          time: formatTime(event.timestamp),
          ...deltaFields,
          status: event.status,
          gate_type: event.gate_type
        };
      });

      return { chartData: result, segmentCount: 0 };
    }

    // SLOW PATH: Session breaks enabled - segmented dataset
    let currentSegment = 0;
    const eventSegments = [];

    sortedEvents.forEach((event, idx) => {
      const prevEvent = idx > 0 ? sortedEvents[idx - 1] : null;
      if (prevEvent && event.session_id !== prevEvent.session_id) {
        currentSegment++;
      }
      eventSegments.push(currentSegment);
    });

    const totalSegments = currentSegment + 1;
    const result = [];
    let eventIndex = 1;

    sortedEvents.forEach((event, idx) => {
      const segment = eventSegments[idx];
      const deltaFields = {};

      consistIds.forEach(cid => {
        for (let seg = 0; seg < totalSegments; seg++) {
          const dataKey = `delta_t_c${cid}_seg${seg}`;
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
  }, [filteredDeltaTEvents, trackingConfig.consists, showSessionBreaks]);


  // Reports chart data (historical trend)
  const reportsChartData = useMemo(() => {
    if (!reportsData?.sessions || !trackingConfig?.consists) return [];
    const chartData = [...reportsData.sessions].reverse().map((session, idx) => {
      const dataPoint = {
        index: idx + 1, // Session number for X-axis (unique)
        session_id: session.id,
        date: session.date,
        time: new Date(session.start_time * 1000).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' }),
        timestamp: session.start_time
      };
      Object.keys(trackingConfig.consists || {}).forEach(cid => {
        const stats = session.consists?.[cid];
        dataPoint[`avg_delta_t_c${cid}`] = stats ? stats.avg_delta_t : null;
      });
      return dataPoint;
    });

    return chartData;
  }, [reportsData, trackingConfig]);

  // Filtered sessions for Reports table (filter by consist)
  const filteredReportsSessions = useMemo(() => {
    if (!reportsData?.sessions) return [];
    if (consistFilter === 'all') return reportsData.sessions;
    // Show only sessions that have data for the selected consist
    // Backend returns consist IDs as strings, convert consistFilter to string
    return reportsData.sessions.filter(session => session.consists?.[String(consistFilter)] !== undefined);
  }, [reportsData, consistFilter]);

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

        {/* Compact Controls - Sticky below header */}
        <div className="sticky top-[88px] z-10 px-4 py-2.5 bg-slate-800/50 border-b border-slate-700 shadow-lg">
          <div className="flex gap-3 items-center">
            {/* View Toggle */}
            <div className="flex gap-1.5">
              <button
                onClick={() => handleViewToggle('current')}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  viewMode === 'current'
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
                title="Current Session"
              >
                <i className="fa-solid fa-magnifying-glass-chart mr-1.5"></i>
                Current
              </button>
              <button
                onClick={() => handleViewToggle('overview')}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  viewMode === 'overview'
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
                title="Historical Overview"
              >
                <i className="fa-solid fa-chart-area mr-1.5"></i>
                Overview
              </button>
              <button
                onClick={() => handleViewToggle('reports')}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  viewMode === 'reports'
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
                title="Session Analysis Reports"
              >
                <i className="fa-solid fa-table-list mr-1.5"></i>
                Reports
              </button>
            </div>

            {/* Divider */}
            <div className="h-6 w-px bg-slate-600"></div>

            {/* Consist Filters */}
            <div className="flex gap-1.5 items-center">
              <span className="text-xs text-slate-400 mr-1">Filter:</span>
              <button
                onClick={() => setConsistFilter('all')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  consistFilter === 'all'
                    ? 'bg-slate-600 text-white'
                    : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
                }`}
              >
                All
              </button>
              {Object.keys(trackingConfig.consists || {})
                .map(Number)
                .sort((a, b) => a - b)
                .map((consistId) => (
                  <button
                    key={consistId}
                    onClick={() => setConsistFilter(consistId)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      consistFilter === consistId
                        ? `${getConsistBgClass(consistId, trackingConfig.consists)} text-white`
                        : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
                    }`}
                  >
                    C{consistId}
                  </button>
                ))}
            </div>

            {/* Divider */}
            <div className="h-6 w-px bg-slate-600"></div>

            {/* Session Breaks Toggle */}
            <div
              className="flex items-center gap-2 cursor-pointer"
              onClick={() => setShowSessionBreaks(!showSessionBreaks)}
              title="Show line breaks at session boundaries"
            >
              <input
                type="checkbox"
                checked={showSessionBreaks}
                onChange={() => {}}
                className="w-4 h-4 text-blue-600 bg-slate-700 border-slate-600 rounded focus:ring-blue-500 focus:ring-2 cursor-pointer pointer-events-none"
                readOnly
              />
              <span className="text-xs text-slate-300">
                <i className="fa-solid fa-pause mr-1.5"></i>
                Session Breaks
              </span>
            </div>

            {/* Spacer */}
            <div className="flex-grow"></div>

            {/* Refresh Button (icon only) */}
            <button
              onClick={() => loadCumulativeData()}
              disabled={loading}
              className="p-2 bg-slate-700 text-slate-300 hover:bg-slate-600 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              title="Refresh data"
            >
              <i className={`fa-solid fa-refresh ${loading ? 'fa-spin' : ''}`}></i>
            </button>
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

          {/* Analytics View (Current / Overview) */}
          {cumulativeData && !loading && viewMode !== 'reports' && (
            <div className="space-y-6">
              {/* Session Not Validated Warning (Current view only) */}
              {viewMode === 'current' && currentSession && !currentSession.validated && (
                <div className="bg-amber-900/30 border border-amber-700 rounded-lg p-4 text-amber-300">
                  <i className="fa-solid fa-clock mr-2"></i>
                  Session not validated - waiting for first gate crossing
                </div>
              )}

              {/* Stats Cards (view-dependent) */}
              <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
                <div
                  className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-700/30 transition-colors"
                  onClick={() => togglePanel('statsCards')}
                >
                  <h3 className="text-lg font-semibold text-white">Session Statistics</h3>
                  <i className={`fa-solid fa-chevron-${collapsedPanels.statsCards ? 'right' : 'down'} text-slate-400 transition-transform`}></i>
                </div>
                {!collapsedPanels.statsCards && (
                  <div className="grid grid-cols-3 gap-4 p-4 pt-0">
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
                )}
              </div>

              {/* Δt Trends Chart - ALL sessions concatenated */}
              {cumulativeData.delta_t_events && cumulativeData.delta_t_events.length > 0 && (
                <DeltaTChart
                  chartData={chartData}
                  segmentCount={segmentCount}
                  viewMode={viewMode}
                  consistFilter={consistFilter}
                  trackingConfig={trackingConfig}
                  scrollRef={scrollRefSession}
                  zoomDomain={zoomDomain}
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onDoubleClick={handleDoubleClick}
                  refAreaLeft={refAreaLeft}
                  refAreaRight={refAreaRight}
                  collapsed={collapsedPanels.deltaTrends}
                  onToggleCollapse={() => togglePanel('deltaTrends')}
                />
              )}

              {/* YOLO Performance Monitoring - FPS & Confidence */}
              {cumulativeData.yolo_performance && cumulativeData.yolo_performance.length > 0 && (
                <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
                  <div
                    className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-700/30 transition-colors"
                    onClick={() => togglePanel('yoloPerformance')}
                  >
                    <h3 className="text-lg font-semibold text-white">YOLO Performance Monitoring</h3>
                    <i className={`fa-solid fa-chevron-${collapsedPanels.yoloPerformance ? 'right' : 'down'} text-slate-400 transition-transform`}></i>
                  </div>
                  {!collapsedPanels.yoloPerformance && (
                    <div className="p-6 pt-0 space-y-6">

                  {/* FPS Line Chart */}
                  <FPSChart
                    yoloPerformanceData={cumulativeData.yolo_performance}
                    viewMode={viewMode}
                    currentSession={currentSession}
                    consistFilter={consistFilter}
                    scrollRef={scrollRefFps}
                    formatTime={formatTime}
                  />

                  {/* Confidence Bar Chart - Per Locomotive (DCC addresses) */}
                  <ConfidenceChart
                    yoloPerformanceData={cumulativeData.yolo_performance}
                    viewMode={viewMode}
                    currentSession={currentSession}
                    consistFilter={consistFilter}
                    trackingConfig={trackingConfig}
                  />
                    </div>
                  )}
                </div>
              )}

              {/* Locomotive Operating Time - ONLY in Overview (cumulative historic data) */}
              {viewMode === 'overview' && locoStats && locoStats.length > 0 && (
                <OperatingTimeChart
                  locoStats={locoStats}
                  consistFilter={consistFilter}
                  trackingConfig={trackingConfig}
                  collapsed={collapsedPanels.locoOperatingTime}
                  onToggleCollapse={() => togglePanel('locoOperatingTime')}
                />
              )}
            </div>
          )}

          {/* Reports Tab Content */}
          {viewMode === 'reports' && reportsData && !loading && trackingConfig?.consists && (
            <div className="space-y-6">
              {/* Overview Stats Cards (same as Overview tab) */}
              {cumulativeData && (
                <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
                  <div
                    className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-700/30 transition-colors"
                    onClick={() => togglePanel('statsCards')}
                  >
                    <h3 className="text-lg font-semibold text-white">Overview Statistics</h3>
                    <i className={`fa-solid fa-chevron-${collapsedPanels.statsCards ? 'right' : 'down'} text-slate-400 transition-transform`}></i>
                  </div>
                  {!collapsedPanels.statsCards && (
                    <div className="grid grid-cols-3 gap-4 p-4 pt-0">
                  {/* Card 1: Total Sessions */}
                  <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                    <div className="text-sm text-slate-400">Total Sessions</div>
                    <div className="text-3xl font-bold text-white mt-1">
                      {cumulativeData.total_sessions}
                    </div>
                  </div>

                  {/* Card 2: Gate Crossings (filtered by consist) */}
                  <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                    <div className="text-sm text-slate-400">
                      Gate Crossings
                      {consistFilter === 'all' ? ' (All)' : ` (C${consistFilter})`}
                    </div>
                    <div className={`text-3xl font-bold mt-1 ${getConsistColorClass(consistFilter, trackingConfig.consists, 'text-white')}`}>
                      {(() => {
                        let events = cumulativeData.delta_t_events || [];
                        // Filter by consist
                        if (consistFilter !== 'all') {
                          events = events.filter(e => e.consist_id === consistFilter);
                        }
                        return events.length;
                      })()}
                    </div>
                  </div>

                  {/* Card 3: Critical Events (filtered by consist) */}
                  <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                    <div className="text-sm text-slate-400">
                      Critical Events
                      {consistFilter === 'all' ? ' (All)' : ` (C${consistFilter})`}
                    </div>
                    <div className={`text-3xl font-bold mt-1 ${getConsistColorClass(consistFilter, trackingConfig.consists, 'text-red-400')}`}>
                      {(() => {
                        let events = cumulativeData.delta_t_events || [];
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
                  )}
                </div>
              )}

              {/* Session History Table */}
              <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
                <div
                  className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-700/30 transition-colors"
                  onClick={() => togglePanel('sessionHistory')}
                >
                  <h3 className="text-lg font-semibold text-white">Session History</h3>
                  <div className="flex items-center gap-4">
                    {!collapsedPanels.sessionHistory && (
                      <>
                        <span className="text-slate-400 text-sm">
                          {filteredReportsSessions.length} sessions
                        </span>
                        <select
                          value={sessionLimit}
                          onChange={(e) => setSessionLimit(Number(e.target.value))}
                          onClick={(e) => e.stopPropagation()}
                          className="bg-slate-700 text-slate-300 text-sm pl-2 pr-7 py-1 rounded border border-slate-600 hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value={30}>Last 30</option>
                          <option value={50}>Last 50</option>
                          <option value={100}>Last 100</option>
                          <option value={200}>Last 200</option>
                        </select>
                      </>
                    )}
                    <i className={`fa-solid fa-chevron-${collapsedPanels.sessionHistory ? 'right' : 'down'} text-slate-400 transition-transform`}></i>
                  </div>
                </div>
                {!collapsedPanels.sessionHistory && (
                  <div className="p-6 pt-0">

                {filteredReportsSessions.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full">
                      <thead>
                        <tr className="border-b border-slate-700 text-left">
                          <th className="px-4 py-3 text-sm font-semibold text-slate-300">Session ID</th>
                          <th className="px-4 py-3 text-sm font-semibold text-slate-300">Date</th>
                          <th className="px-4 py-3 text-sm font-semibold text-slate-300">Duration</th>
                          <th className="px-4 py-3 text-sm font-semibold text-slate-300">Events</th>
                          {Object.keys(trackingConfig.consists || {}).sort((a, b) => a - b).map(cid => {
                            if (consistFilter === 'all' || consistFilter == cid) {
                              return (
                                <Fragment key={cid}>
                                  <th className="px-4 py-3 text-sm font-semibold text-slate-300">C{cid} Avg Δt</th>
                                  <th className="px-4 py-3 text-sm font-semibold text-slate-300">C{cid} Synced%</th>
                                </Fragment>
                              );
                            }
                            return null;
                          })}
                        </tr>
                      </thead>
                      <tbody>
                        {filteredReportsSessions.map(session => (
                          <tr
                            key={session.id}
                            onClick={() => {
                              setSelectedSession(session);
                              setShowSessionDetail(true);
                            }}
                            className="border-b border-slate-700/50 hover:bg-slate-700/30 cursor-pointer transition-colors"
                          >
                            <td className="px-4 py-3 text-sm font-mono text-slate-300">{session.id}</td>
                            <td className="px-4 py-3 text-sm text-slate-300">{session.date}</td>
                            <td className="px-4 py-3 text-sm text-slate-300">{session.duration_formatted}</td>
                            <td className="px-4 py-3 text-sm text-slate-300">{session.total_events}</td>
                            {Object.keys(trackingConfig.consists || {}).sort((a, b) => a - b).map(cid => {
                              if (consistFilter === 'all' || consistFilter == cid) {
                                // JSON keys are always strings, but we convert to numbers with .map(Number)
                                const stats = session.consists?.[String(cid)];
                                if (stats) {
                                  const avgDt = stats.avg_delta_t;
                                  const absAvg = Math.abs(avgDt);
                                  const colorClass = absAvg < 1.0 ? 'text-green-400' : absAvg < 1.5 ? 'text-amber-400' : 'text-red-400';
                                  return (
                                    <Fragment key={cid}>
                                      <td className={`px-4 py-3 text-sm font-medium ${colorClass}`}>
                                        {formatDeltaT(avgDt)}s
                                      </td>
                                      <td className="px-4 py-3 text-sm text-slate-300">
                                        {stats.synced_percent.toFixed(1)}%
                                      </td>
                                    </Fragment>
                                  );
                                } else {
                                  return (
                                    <Fragment key={cid}>
                                      <td className="px-4 py-3 text-sm text-slate-500">N/A</td>
                                      <td className="px-4 py-3 text-sm text-slate-500">N/A</td>
                                    </Fragment>
                                  );
                                }
                              }
                              return null;
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-12 text-slate-400">
                    <i className="fa-solid fa-inbox text-4xl mb-4"></i>
                    <p>No sessions found</p>
                  </div>
                )}
                  </div>
                )}
              </div>

              {/* Historical Trend Chart */}
              <HistoricalTrendChart
                reportsChartData={reportsChartData}
                reportsData={reportsData}
                consistFilter={consistFilter}
                trackingConfig={trackingConfig}
                collapsed={collapsedPanels.historicalTrend}
                onToggleCollapse={() => togglePanel('historicalTrend')}
                onSessionClick={(session) => {
                  setSelectedSession(session);
                  setShowSessionDetail(true);
                }}
              />
            </div>
          )}

          {/* Reports Tab - Loading trackingConfig */}
          {viewMode === 'reports' && !trackingConfig?.consists && !loading && (
            <div className="text-center py-12">
              <i className="fa-solid fa-spinner fa-spin text-4xl text-blue-500"></i>
              <p className="mt-4 text-slate-400">Loading configuration...</p>
            </div>
          )}

          {/* Session Detail Modal */}
          {showSessionDetail && selectedSession && (
            <div
              className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-sm"
              onClick={() => setShowSessionDetail(false)}
            >
              <div
                className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto bg-slate-900 rounded-xl border-2 border-slate-700 shadow-2xl p-8"
                onClick={(e) => e.stopPropagation()}
              >
                {/* Close Button */}
                <button
                  onClick={() => setShowSessionDetail(false)}
                  className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
                >
                  <i className="fa-solid fa-xmark text-2xl"></i>
                </button>

                {/* Session Header */}
                <h2 className="text-2xl font-bold text-white mb-6">Session Analysis</h2>

                {/* Session Info Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div>
                    <div className="text-slate-400 text-sm mb-1">Session ID</div>
                    <div className="font-mono text-white">{selectedSession.id}</div>
                  </div>
                  <div>
                    <div className="text-slate-400 text-sm mb-1">Date</div>
                    <div className="text-white">{selectedSession.date}</div>
                  </div>
                  <div>
                    <div className="text-slate-400 text-sm mb-1">Duration</div>
                    <div className="text-white">{selectedSession.duration_formatted}</div>
                  </div>
                  <div>
                    <div className="text-slate-400 text-sm mb-1">Total Events</div>
                    <div className="text-white">{selectedSession.total_events}</div>
                  </div>
                </div>

                {/* Per-Consist Breakdown */}
                <div className="space-y-4">
                  {Object.entries(selectedSession.consists || {}).map(([cid, stats]) => {
                    const consistName = trackingConfig.consists?.[cid]?.name || `Consist ${cid}`;
                    const consistColor = getConsistStrokeColor(Number(cid));

                    return (
                      <div key={cid} className="bg-slate-800/50 rounded-lg p-6 border border-slate-700">
                        <h3 className="text-lg font-semibold mb-4" style={{ color: consistColor }}>
                          {consistName}
                        </h3>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {/* Left: Statistics */}
                          <div className="space-y-2">
                            <div className="flex justify-between">
                              <span className="text-slate-400">Total Crossings:</span>
                              <span className="font-medium text-white">{stats.total_crossings}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-400">Average Δt:</span>
                              <span className={`font-medium ${
                                Math.abs(stats.avg_delta_t) < 1.0 ? 'text-green-400' :
                                Math.abs(stats.avg_delta_t) < 1.5 ? 'text-amber-400' : 'text-red-400'
                              }`}>
                                {formatDeltaT(stats.avg_delta_t, 3)}s
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-400">Range:</span>
                              <span className="font-mono text-sm text-white">
                                {formatDeltaT(stats.min_delta_t)}s to {formatDeltaT(stats.max_delta_t)}s
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-400">Trend:</span>
                              <span className={`px-2 py-1 rounded text-sm ${
                                stats.trend === 'LEAD FASTER' ? 'bg-blue-900/50 text-blue-300' :
                                stats.trend === 'REAR FASTER' ? 'bg-purple-900/50 text-purple-300' :
                                'bg-slate-700 text-slate-300'
                              }`}>
                                {stats.trend}
                              </span>
                            </div>
                          </div>

                          {/* Right: Status Distribution */}
                          <div className="space-y-2">
                            <div className="text-slate-400 mb-2 text-sm">Status Distribution:</div>
                            <div className="flex justify-between items-center">
                              <span className="flex items-center gap-2 text-sm">
                                <span className="w-3 h-3 rounded-full bg-green-500"></span>
                                SYNCED
                              </span>
                              <span className="font-medium text-white text-sm">
                                {stats.synced_count} ({stats.synced_percent.toFixed(1)}%)
                              </span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="flex items-center gap-2 text-sm">
                                <span className="w-3 h-3 rounded-full bg-amber-500"></span>
                                WARNING
                              </span>
                              <span className="font-medium text-white text-sm">
                                {stats.warning_count} ({((stats.warning_count / stats.total_crossings) * 100).toFixed(1)}%)
                              </span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="flex items-center gap-2 text-sm">
                                <span className="w-3 h-3 rounded-full bg-red-500"></span>
                                CRITICAL
                              </span>
                              <span className="font-medium text-white text-sm">
                                {stats.critical_count} ({((stats.critical_count / stats.total_crossings) * 100).toFixed(1)}%)
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Interpretation */}
                <div className="mt-6 p-4 bg-blue-900/20 border border-blue-700 rounded-lg">
                  <h4 className="font-semibold text-white mb-2">Interpretation:</h4>
                  <ul className="text-sm text-slate-300 space-y-1 list-disc list-inside">
                    <li>Positive Δt: Lead locomotive arrives first (rear is slower)</li>
                    <li>Negative Δt: Rear locomotive arrives first (lead is slower)</li>
                    <li>SYNCED: |Δt| &lt; 1.0s, WARNING: 1.0-1.5s, CRITICAL: ≥ 1.5s</li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
