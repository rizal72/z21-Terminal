"""
Analytics Router

Handles all analytics-related endpoints:
- Current session metadata
- Session data retrieval
- Cumulative statistics with smart downsampling
- Reports (session-by-session analysis)
- Locomotive operating time statistics
- Session lifecycle management
"""

from fastapi import APIRouter, Depends
from typing import Optional
from services.analytics_db import AnalyticsDB
from services.downsampling import smart_downsample_delta_t, lttb_downsample, format_duration_hms
from dependencies import get_tracking_manager, get_debug_enabled
from tracking_manager import TrackingManager
from log_colors import log

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
router_no_prefix = APIRouter(tags=["analytics"])  # For endpoints outside /api/analytics prefix


@router.get("/current")
async def get_current_session(
    tracking_manager: TrackingManager = Depends(get_tracking_manager)
):
    """Get current analytics session metadata (lightweight)"""
    # Current session info from tracking daemon (if running)
    if tracking_manager and tracking_manager.daemon:
        logger = tracking_manager.daemon.analytics_logger
        if logger:
            return logger.get_session_info()
    return {"error": "Analytics not available"}


@router.get("/session/{session_id}")
async def get_session_data(session_id: str):
    """Load full session data (events, Δt trends)"""
    result = AnalyticsDB.get_session_by_id(session_id)
    if result is None:
        return {"error": "Session not found"}
    return result


@router.get("/cumulative")
async def get_cumulative_stats(
    tail: Optional[int] = None,
    maxPoints: Optional[int] = None,  # Changed to camelCase to match frontend
    tracking_manager: TrackingManager = Depends(get_tracking_manager),
    debug_enabled: bool = Depends(get_debug_enabled)
):
    """
    Get all sessions aggregated statistics with full event data for charts.

    Args:
        tail: Optional tail parameter. If provided, returns last N events (full resolution).
              Used by Current view to keep recent data intact.
              Example: ?tail=1000 (last 1000 events, no sampling)

        maxPoints: Optional sampling parameter. If provided, applies uniform sampling
                   to ALL event arrays across entire history.
                   Used by Overview view for historical trends.
                   Example: ?maxPoints=500

    Note: tail and maxPoints are mutually exclusive (tail takes precedence)
    """
    # Get validated sessions from DB
    sessions = AnalyticsDB.get_validated_sessions()

    # Include current session if running (validated but no end_time yet)
    if tracking_manager and tracking_manager.daemon and tracking_manager.daemon.analytics_logger:
        current_logger = tracking_manager.daemon.analytics_logger
        if current_logger.session_validated:
            sessions.insert(0, {  # Add at top (most recent)
                'id': current_logger.session_id,
                'start_time': current_logger.session_start,
                'end_time': None,  # Still running
                'event_count': current_logger.event_count,
                'duration': None  # Can't calculate yet
            })

    # Get overall stats
    total_sessions = len(sessions)

    # Get gate crossings aggregate
    gate_crossings = AnalyticsDB.get_gate_crossings_aggregate()

    # Get ALL events (chronologically ordered)
    delta_t_events = AnalyticsDB.get_delta_t_events()
    yolo_performance = AnalyticsDB.get_yolo_performance_events()
    loco_operating_time_events = AnalyticsDB.get_loco_operating_time_events()

    # Save original counts BEFORE tail/maxPoints (for accurate stats cards)
    original_delta_t_count = len(delta_t_events)

    # Apply tail or sampling based on view mode (mutually exclusive)
    if tail:
        # Current view: keep last N events (full resolution, no sampling)
        delta_t_events = delta_t_events[-tail:] if len(delta_t_events) > tail else delta_t_events
        yolo_performance = yolo_performance[-tail:] if len(yolo_performance) > tail else yolo_performance
        loco_operating_time_events = loco_operating_time_events[-tail:] if len(loco_operating_time_events) > tail else loco_operating_time_events
    elif maxPoints:
        # Overview view: intelligent downsampling (LTTB preserves shape, critical events always included)
        original_yolo_count = len(yolo_performance)

        if debug_enabled:
            log('[ANALYTICS]', f"Before downsampling: {original_delta_t_count} delta_t events, target: {maxPoints}")

        # Delta-t: Smart downsampling (all critical |Δt| ≥ 1.5s + LTTB on rest)
        delta_t_events = smart_downsample_delta_t(delta_t_events, maxPoints, critical_threshold=1.5)

        if debug_enabled:
            log('[ANALYTICS]', f"After downsampling: {len(delta_t_events)} delta_t events")

        # YOLO FPS: LTTB downsampling (preserves peaks/valleys)
        yolo_performance = lttb_downsample(yolo_performance, maxPoints, x_key='timestamp', y_key='avg_fps')
        # Note: loco_operating_time not sampled (aggregate stats chart, not timeline)

        # Log if sampling reduction is significant (always visible, not debug-only)
        delta_reduction = original_delta_t_count - len(delta_t_events)
        yolo_reduction = original_yolo_count - len(yolo_performance)

        # Significant = reduced >10% OR reduced >100 events
        is_significant = (delta_reduction > original_delta_t_count * 0.1 or delta_reduction > 100 or
                        yolo_reduction > original_yolo_count * 0.1 or yolo_reduction > 100)

        if is_significant:
            log('[ANALYTICS]', f"LTTB downsampling applied (maxPoints={maxPoints}) | "
                  f"dT: {original_delta_t_count}->{len(delta_t_events)} (critical preserved) | "
                  f"YOLO: {original_yolo_count}->{len(yolo_performance)}")

    # Note: delta_t_events already includes current session events (written by flush task every 10s)
    # Total count is accurate because query includes all events from DB
    return {
        'total_sessions': total_sessions,
        'total_delta_t_events': original_delta_t_count,  # ALWAYS pre-downsampling count (accurate for stats)
        'sessions': sessions,
        'gate_crossings': gate_crossings,
        'delta_t_events': delta_t_events,  # May be downsampled (for chart rendering)
        'yolo_performance': yolo_performance,
        'loco_operating_time': loco_operating_time_events
    }


@router.get("/reports")
async def get_analytics_reports(
    limit: int = 30,
    consist_filter: Optional[int] = None
):
    """
    Get session-by-session analysis reports for historical trend analysis.

    Returns per-session aggregated statistics (avg dT, range, status distribution)
    for the last N validated sessions.

    Args:
        limit: Number of sessions to return (default 30, configurable via UI: 30/50/100/200)
        consist_filter: Optional consist ID to filter by (10, 11, etc.)

    Returns:
        {
            "sessions": [
                {
                    "id": "20250114_143022",
                    "date": "2025-01-14",
                    "start_time": timestamp,
                    "end_time": timestamp,
                    "duration_seconds": 3600,
                    "duration_formatted": "01:00:00",
                    "total_events": 145,
                    "consists": {
                        "10": {
                            "total_crossings": 72,
                            "avg_delta_t": 0.52,
                            "min_delta_t": -0.15,
                            "max_delta_t": 1.82,
                            "trend": "LEAD FASTER" | "REAR FASTER" | "BALANCED",
                            "synced_count": 58,
                            "warning_count": 10,
                            "critical_count": 4,
                            "synced_percent": 80.6
                        },
                        ...
                    }
                },
                ...
            ]
        }
    """
    try:
        sessions = AnalyticsDB.get_reports_data(
            limit=limit,
            consist_filter=consist_filter,
            format_duration_callback=format_duration_hms
        )
        return {"sessions": sessions}
    except Exception as e:
        return {"error": f"Failed to load reports: {str(e)}", "sessions": []}


@router.get("/locomotive-stats")
async def get_locomotive_stats():
    """Get aggregated locomotive operating time statistics"""
    try:
        locomotives = AnalyticsDB.get_locomotive_stats()
        return {'locomotives': locomotives}
    except Exception as e:
        log('[ERROR]', f"Failed to load locomotive stats: {e}")
        return {'error': str(e), 'locomotives': []}


@router.get("/speed-correlation")
async def get_speed_correlation(
    consist_id: int,
    limit: int = 1000,
    bucket_size: int = 5,
    events_per_speed: int = 10
):
    """
    Get speed vs delta_t correlation analysis for a consist.

    Uses "Next N Events" strategy: For each speed change, collect next N delta_t
    events to build statistical correlation between speed settings and sync quality.

    Query Parameters:
        consist_id: Consist ID to analyze (required)
        limit: Max speed_setting events to analyze (default: 1000, most recent)
        bucket_size: Speed bucketing interval in DCC steps (default: 5, e.g., 45-49 → bucket 50)
        events_per_speed: Delta_t events to collect after each speed change (default: 10)

    Returns:
        {
            "consist_id": int,
            "total_speed_changes": int,
            "correlated_samples": int,
            "speed_buckets": [
                {
                    "speed_bucket": int,
                    "speed_min": int,
                    "speed_max": int,
                    "mean_delta_t": float,
                    "std_dev": float,
                    "min_delta_t": float,
                    "max_delta_t": float,
                    "samples": int,
                    "status_distribution": {"SYNCED": int, "WARNING": int, "CRITICAL": int},
                    "raw_speeds": [int]
                }
            ]
        }
    """
    try:
        result = AnalyticsDB.get_speed_correlation(
            consist_id=consist_id,
            limit=limit,
            bucket_size=bucket_size,
            events_per_speed=events_per_speed
        )
        return result
    except Exception as e:
        log('[ERROR]', f"Failed to get speed correlation for consist {consist_id}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'error': str(e),
            'consist_id': consist_id,
            'total_speed_changes': 0,
            'correlated_samples': 0,
            'speed_buckets': []
        }


# Session lifecycle management (outside /api/analytics prefix)
@router_no_prefix.post("/api/close-session")
async def close_session(
    tracking_manager: TrackingManager = Depends(get_tracking_manager)
):
    """Force close current analytics session (called via sendBeacon on page unload/refresh)

    This ensures deterministic session boundaries:
    - Page refresh → daemon stops → session closes → new page load → daemon restarts → NEW session
    - Without this: session continues if daemon doesn't stop between disconnect/reconnect
    """
    if tracking_manager:
        try:
            await tracking_manager.stop_tracking()
            log('[SESSION]', 'Analytics session closed via page unload')
            return {"status": "ok"}
        except Exception as e:
            log('[ERROR]', f'Failed to close session: {e}')
            return {"status": "error", "message": str(e)}
    return {"status": "ok"}  # No tracking manager = nothing to close
