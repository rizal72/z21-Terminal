import { useState, useEffect, useRef, memo, useMemo, Fragment } from 'react';
import { LineChart, Line, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, ReferenceArea } from 'recharts';

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
  const config = consistConfig || {};
  if (consistFilter === 'all') {
    // All consists: flatten all addresses
    return Object.values(config).flatMap(c => c.addresses);
  }
  return config[consistFilter]?.addresses || [];
};

// Helper: get consist stroke color (cyclic palette)
const getConsistStrokeColor = (consistId, consistConfig) => {
  const config = consistConfig || {};
  const consistIds = Object.keys(config).map(Number).sort((a, b) => a - b);
  const index = consistIds.indexOf(consistId);
  return index >= 0 ? CONSIST_COLOR_PALETTE[index % CONSIST_COLOR_PALETTE.length] : '#9CA3AF';
};

// Helper: get consist text color class (cyclic palette)
const getConsistColorClass = (consistFilter, consistConfig, defaultColor = 'text-white') => {
  if (consistFilter === 'all') return defaultColor;
  const config = consistConfig || {};
  const consistIds = Object.keys(config).map(Number).sort((a, b) => a - b);
  const index = consistIds.indexOf(consistFilter);
  return index >= 0 ? CONSIST_COLOR_CLASSES[index % CONSIST_COLOR_CLASSES.length] : defaultColor;
};

// Helper: get consist background color class for buttons (cyclic palette)
const getConsistBgClass = (consistId, consistConfig) => {
  const config = consistConfig || {};
  const consistIds = Object.keys(config).map(Number).sort((a, b) => a - b);
  const index = consistIds.indexOf(consistId);
  return index >= 0 ? CONSIST_BG_CLASSES[index % CONSIST_BG_CLASSES.length] : 'bg-slate-600';
};

// Helper: format delta t with sign (always show + for positive values)
const formatDeltaT = (value, decimals = 2) => {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}`;
};

// Helper: format operating time seconds to "Xh Ym" format
const formatOperatingTime = (seconds) => {
  if (!seconds || seconds === 0) return '0h 0m';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
};

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

  // Apply zoom filter if zoomDomain is set (Overview mode only)
  const displayData = useMemo(() => {
    if (viewMode !== 'overview' || !zoomDomain) return chartData;

    // Filter data to show only zoomed range
    const [xMin, xMax] = zoomDomain.x;
    return chartData.filter(d => d.index >= xMin && d.index <= xMax);
  }, [chartData, zoomDomain, viewMode]);

  // Calculate Y domain to ensure all points are visible (10% padding)
  const yDomain = useMemo(() => {
    if (zoomDomain) return zoomDomain.y; // Use zoom domain if active

    if (displayData.length === 0) return ['auto', 'auto'];

    const consistIds = Object.keys(trackingConfig.consists || {}).map(Number);
    let yMin = Infinity, yMax = -Infinity;

    // Scan all data to find min/max
    if (segmentCount === 0) {
      // SIMPLE MODE
      displayData.forEach(d => {
        consistIds.forEach(cid => {
          const value = d[`delta_t_c${cid}`];
          if (value !== null && value !== undefined && !isNaN(value)) {
            yMin = Math.min(yMin, value);
            yMax = Math.max(yMax, value);
          }
        });
      });
    } else {
      // SEGMENTED MODE
      displayData.forEach(d => {
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

    // No valid data found
    if (yMin === Infinity || yMax === -Infinity) return ['auto', 'auto'];

    // Add 5% padding
    const range = yMax - yMin;
    const padding = range * 0.05;
    return [yMin - padding, yMax + padding];
  }, [displayData, segmentCount, trackingConfig.consists, zoomDomain]);

  // Memoize chart width calculation
  const chartWidth = useMemo(() => {
    return viewMode === 'current' ? Math.max(chartData.length * 40, 800) : '100%';
  }, [chartData.length, viewMode]);

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
                <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
                  <div
                    className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-700/30 transition-colors"
                    onClick={() => togglePanel('deltaTrends')}
                  >
                    <h3 className="text-lg font-semibold text-white">Δt Trends (All Sessions)</h3>
                    <div className="flex items-center gap-4">
                      {!collapsedPanels.deltaTrends && (
                        <span className="text-xs text-slate-400">
                          Click & drag to zoom • Double-click to reset
                        </span>
                      )}
                      <i className={`fa-solid fa-chevron-${collapsedPanels.deltaTrends ? 'right' : 'down'} text-slate-400 transition-transform`}></i>
                    </div>
                  </div>
                  {!collapsedPanels.deltaTrends && (
                    <div className="p-6 pt-0">

                  {/* Threshold Legend - SYNCED/WARNING/CRITICAL */}
                  <div className="flex gap-6 justify-center mb-3 pb-3 border-b border-slate-700/50">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-green-500"></div>
                      <span className="text-xs text-slate-400">SYNCED (&lt;1.0s)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                      <span className="text-xs text-slate-400">WARNING (1.0-1.5s)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-500"></div>
                      <span className="text-xs text-slate-400">CRITICAL (≥1.5s)</span>
                    </div>
                  </div>

                  {/* Custom Legend (always shown when All filter, both Current and Overview) */}
                  {chartData.length > 0 && consistFilter === 'all' && (
                    <div className="flex gap-4 justify-center mb-4 pb-3 border-b border-slate-700">
                      {Object.keys(trackingConfig.consists || {})
                        .map(Number)
                        .sort((a, b) => a - b)
                        .map((consistId) => (
                          <div key={consistId} className="flex items-center gap-2">
                            <div
                              className="w-4 h-1"
                              style={{ backgroundColor: getConsistStrokeColor(consistId, trackingConfig.consists) }}
                            ></div>
                            <span className="text-sm text-slate-300">
                              {trackingConfig.consists[consistId]?.name || `Consist ${consistId}`}
                            </span>
                          </div>
                        ))}
                    </div>
                  )}

                  {chartData.length > 0 && (
                    <div
                      key={consistFilter}
                      ref={viewMode === 'current' ? scrollRefSession : null}
                      style={{ width: '100%', overflowX: viewMode === 'current' ? 'auto' : 'visible' }}
                    >
                      <ResponsiveContainer width={chartWidth} height={400}>
                          <LineChart
                            data={displayData}
                            onMouseDown={handleMouseDown}
                            onMouseMove={handleMouseMove}
                            onMouseUp={handleMouseUp}
                            onDoubleClick={handleDoubleClick}
                          >
                            <CartesianGrid {...CHART_AXIS_STYLES.grid} />
                      {/* XAxis: time in Current (readable), index in Overview (compressed) */}
                      <XAxis
                        dataKey={viewMode === 'current' ? 'time' : 'index'}
                        {...CHART_AXIS_STYLES.axis}
                      />
                      <YAxis
                        yAxisId="left"
                        {...CHART_AXIS_STYLES.axis}
                        domain={yDomain}
                        allowDataOverflow={true}
                        tickFormatter={(value) => formatDeltaT(value)}
                        label={{ value: 'Δt (seconds)', angle: 90, position: 'insideLeft', fill: '#9CA3AF' }}
                      />
                      {/* Duplicate YAxis on right for Current mode (always visible when scrolling) */}
                      {viewMode === 'current' && (
                        <YAxis
                          yAxisId="right"
                          orientation="right"
                          {...CHART_AXIS_STYLES.axis}
                          domain={yDomain}
                          allowDataOverflow={true}
                          tickFormatter={(value) => formatDeltaT(value)}
                          label={{ value: 'Δt (seconds)', angle: 90, position: 'insideRight', fill: '#9CA3AF' }}
                        />
                      )}
                      <Tooltip
                        {...TOOLTIP_STYLES}
                        formatter={(value) => value !== null ? formatDeltaT(value) + 's' : 'N/A'}
                      />
                      <ReferenceLine yAxisId="left" y={0} stroke="#10b981" strokeDasharray="3 3" />
                      <ReferenceLine yAxisId="left" y={trackingConfig.timing_thresholds?.normal || 1.0} stroke="#f59e0b" strokeDasharray="3 3" />
                      <ReferenceLine yAxisId="left" y={-(trackingConfig.timing_thresholds?.normal || 1.0)} stroke="#f59e0b" strokeDasharray="3 3" />
                      <ReferenceLine yAxisId="left" y={trackingConfig.timing_thresholds?.warning || 1.5} stroke="#ef4444" strokeDasharray="3 3" />
                      <ReferenceLine yAxisId="left" y={-(trackingConfig.timing_thresholds?.warning || 1.5)} stroke="#ef4444" strokeDasharray="3 3" />

                          {/* Dynamic lines: simple or segmented based on showSessionBreaks */}
                          {Object.keys(trackingConfig.consists || {})
                            .map(Number)
                            .sort((a, b) => a - b)
                            .filter(consistId => consistFilter === 'all' || consistFilter === consistId)
                            .flatMap((consistId) => {
                              // SIMPLE MODE: One Line per consist (no session breaks)
                              if (segmentCount === 0) {
                                return (
                                  <Line
                                    key={consistId}
                                    yAxisId="left"
                                    type="monotone"
                                    dataKey={`delta_t_c${consistId}`}
                                    stroke={getConsistStrokeColor(consistId, trackingConfig.consists)}
                                    strokeWidth={viewMode === 'current' ? 2 : 1.5}
                                    dot={viewMode === 'current' ? { r: 4 } : false}
                                    name={trackingConfig.consists[consistId]?.name || `Consist ${consistId}`}
                                    connectNulls={true}
                                  />
                                );
                              }

                              // SEGMENTED MODE: One Line per segment (session breaks enabled)
                              return Array.from({ length: segmentCount }, (_, segIdx) => (
                                <Line
                                  key={`${consistId}_seg${segIdx}`}
                                  yAxisId="left"
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

                            {/* ReferenceArea for box-select zoom - only during drag in Overview */}
                            {refAreaLeft && refAreaRight && (
                              <ReferenceArea
                                yAxisId="left"
                                x1={refAreaLeft}
                                x2={refAreaRight}
                                strokeOpacity={0.3}
                                fill="#3b82f6"
                                fillOpacity={0.3}
                              />
                            )}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                    </div>
                  )}
                </div>
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
                  <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
                    {(() => {
                      // NO session filtering - FPS chart shows ALL sessions like dT chart
                      const chartData = cumulativeData.yolo_performance.map((e, idx) => ({
                        index: idx + 1,
                        time: formatTime(e.timestamp),
                        fps: parseFloat(e.avg_fps.toFixed(1))
                      }));

                      // Calculate average FPS
                      const avgFps = chartData.length > 0
                        ? (chartData.reduce((sum, d) => sum + d.fps, 0) / chartData.length).toFixed(1)
                        : 'N/A';

                      return (
                        <>
                          <div className="flex items-center justify-between mb-4">
                            <h4 className="text-lg font-semibold text-amber-400">Inference FPS Over Time</h4>
                            <span className="px-3 py-1 bg-slate-800 border border-slate-600 rounded text-sm font-mono text-green-400">
                              FPS avg: {avgFps}
                            </span>
                          </div>
                          {(() => {

                      const chartWidth = viewMode === 'current' ? Math.max(chartData.length * 60, 800) : '100%';
                      const chartContent = (
                        <ResponsiveContainer width={chartWidth} height={300}>
                          <LineChart data={chartData}>
                            <CartesianGrid {...CHART_AXIS_STYLES.grid} />
                            {/* XAxis: time in Current (readable), index in Overview (compressed) */}
                            <XAxis
                              dataKey={viewMode === 'current' ? 'time' : 'index'}
                              {...CHART_AXIS_STYLES.axis}
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
                        </>
                      );
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
                </div>
              )}

              {/* Locomotive Operating Time - ONLY in Overview (cumulative historic data) */}
              {viewMode === 'overview' && locoStats && locoStats.length > 0 && (() => {
                // Filter locomotives by consist (All/C10/C11)
                const addressFilter = getAddressFilter(consistFilter, trackingConfig.consists);
                const filteredLocoStats = locoStats.filter(loco => addressFilter.includes(loco.address));

                return filteredLocoStats.length > 0 && (
                  <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
                    <div
                      className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-700/30 transition-colors"
                      onClick={() => togglePanel('locoOperatingTime')}
                    >
                      <h3 className="text-lg font-semibold text-white">Locomotive Operating Time</h3>
                      <i className={`fa-solid fa-chevron-${collapsedPanels.locoOperatingTime ? 'right' : 'down'} text-slate-400 transition-transform`}></i>
                    </div>
                    {!collapsedPanels.locoOperatingTime && (
                      <div className="p-6 pt-0">

                    <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
                      <h4 className="text-lg font-semibold text-amber-400 mb-4">Total Operating Time</h4>
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={filteredLocoStats}>
                          <CartesianGrid {...CHART_AXIS_STYLES.grid} />
                          <XAxis dataKey="name" {...CHART_AXIS_STYLES.axis} />
                          <YAxis
                            {...CHART_AXIS_STYLES.axis}
                            tickFormatter={(value) => Math.floor(value / 60)}
                            label={{ value: 'Operating Time (minutes)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
                          />
                          <Tooltip
                            {...TOOLTIP_STYLES}
                            formatter={(value) => formatOperatingTime(value)}
                          />
                          <Bar dataKey="total_operating_seconds">
                            {filteredLocoStats.map((loco, index) => (
                              <Cell key={`cell-${index}`} fill={LOCO_COLORS[loco.address] || '#9CA3AF'} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                      </div>
                    )}
                  </div>
                );
              })()}
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
              <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
                <div
                  className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-700/30 transition-colors"
                  onClick={() => togglePanel('historicalTrend')}
                >
                  <h3 className="text-lg font-semibold text-white">Historical Trend - Avg Δt</h3>
                  <i className={`fa-solid fa-chevron-${collapsedPanels.historicalTrend ? 'right' : 'down'} text-slate-400 transition-transform`}></i>
                </div>
                {!collapsedPanels.historicalTrend && (
                  <div className="p-6 pt-0">

                {/* Threshold Legend */}
                <div className="flex gap-6 justify-center mb-4 pb-3 border-b border-slate-700/50">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span className="text-xs text-slate-400">SYNCED (&lt;1.0s)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                    <span className="text-xs text-slate-400">WARNING (1.0-1.5s)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <span className="text-xs text-slate-400">CRITICAL (≥1.5s)</span>
                  </div>
                </div>

                {reportsChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={400}>
                    <LineChart
                      data={reportsChartData}
                      onClick={(data) => {
                        if (data?.activePayload?.[0]) {
                          const sessionId = data.activePayload[0].payload.session_id;
                          const session = reportsData.sessions.find(s => s.id === sessionId);
                          if (session) {
                            setSelectedSession(session);
                            setShowSessionDetail(true);
                          }
                        }
                      }}
                      margin={{ top: 20, right: 30, left: 20, bottom: 35 }}
                    >
                      <CartesianGrid {...CHART_AXIS_STYLES.grid} />
                      <XAxis
                        dataKey="index"
                        {...CHART_AXIS_STYLES.axis}
                        angle={-40}
                        textAnchor="end"
                        height={35}
                        interval="preserveStartEnd"
                        tickFormatter={(index) => {
                          const item = reportsChartData[index - 1];
                          if (!item) return index;
                          // Format: DD-MM HH:MM (backend sends DD-MM-YYYY)
                          const [day, month, year] = item.date.split('-');
                          return `${day}-${month} ${item.time}`;
                        }}
                      />
                      <YAxis
                        {...CHART_AXIS_STYLES.axis}
                        label={{ value: 'Avg Δt (seconds)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }}
                      />
                      <Tooltip
                        {...TOOLTIP_STYLES}
                        content={({ active, payload, label }) => {
                          if (!active || !payload || payload.length === 0) return null;

                          // Get session data from payload
                          const sessionData = payload[0]?.payload;
                          if (!sessionData) return null;

                          return (
                            <div style={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px', padding: '12px' }}>
                              <p style={{ color: '#e2e8f0', marginBottom: '8px', fontWeight: 'bold' }}>
                                {sessionData.date} {sessionData.time}
                              </p>
                              {payload.map((entry, index) => {
                                if (entry.value === null || entry.value === undefined) return null;
                                return (
                                  <p key={index} style={{ color: entry.color, margin: '4px 0' }}>
                                    {entry.name}: {formatDeltaT(entry.value)}s
                                  </p>
                                );
                              })}
                            </div>
                          );
                        }}
                      />
                      <ReferenceLine y={0} stroke="#10b981" strokeDasharray="3 3" />
                      <ReferenceLine y={1.0} stroke="#f59e0b" strokeDasharray="3 3" />
                      <ReferenceLine y={-1.0} stroke="#f59e0b" strokeDasharray="3 3" />
                      <ReferenceLine y={1.5} stroke="#ef4444" strokeDasharray="3 3" />
                      <ReferenceLine y={-1.5} stroke="#ef4444" strokeDasharray="3 3" />

                      {Object.keys(trackingConfig.consists || {}).map(cid => {
                        if (consistFilter === 'all' || consistFilter == cid) {
                          return (
                            <Line
                              key={cid}
                              dataKey={`avg_delta_t_c${cid}`}
                              stroke={getConsistStrokeColor(Number(cid), trackingConfig.consists)}
                              strokeWidth={2}
                              dot={{ r: 5 }}
                              activeDot={{ r: 7 }}
                              connectNulls={false}
                              name={`C${cid}`}
                            />
                          );
                        }
                        return null;
                      })}
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-center py-12 text-slate-400">
                    <i className="fa-solid fa-chart-line text-4xl mb-4"></i>
                    <p>No trend data available</p>
                  </div>
                )}
                  </div>
                )}
              </div>
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
