"""
Speed Table API Router

Endpoints for Speed Table Viewer feature (Phase 1 - Read-Only).
Provides CV67-94 data, CRITICAL event analysis, and CV adjustment recommendations.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import json

from services.analytics_db import AnalyticsDB
from services.speed_table_helpers import (
    read_cv_speed_table,
    speed_to_jmri_step,
    jmri_step_to_cv,
    calculate_cv_recommendations,
    load_all_locomotives
)
from config_loader import load_config

router = APIRouter()


@router.get("/api/speed-table/{consist_id}")
async def get_speed_table_data(consist_id: int) -> Dict[str, Any]:
    """
    Get Speed Table Viewer data for a consist (Phase 1 - Read-Only).

    Uses cumulative historical data with intelligent "fixed" detection:
    - Aggregates CRITICAL/WARNING counts from all sessions
    - Excludes speeds proven OK in their last tested session (>= 3 events, < 20% CRITICAL rate)

    Returns:
        - cv_values: CV67-94 current values from JMRI roster
        - critical_events: Historical CRITICAL event counts per speed
        - warning_events: Historical WARNING event counts per speed
        - recommendations: List of CV adjustment suggestions (excludes fixed speeds)
        - adjust_loco_address: Address of the locomotive being analyzed
        - session_id: Current session ID (for display only, or None if no active session)
        - session_validated: Whether session is validated

    Args:
        consist_id: Consist ID (10, 11, etc.)

    Raises:
        404: Consist not found in config
        500: Roster file not found or other errors
    """
    # Get config to identify adjust loco
    config = load_config()

    # Get consist from config (consists is a dict with string keys "10", "11", etc.)
    consists = config.get('consists', {})
    consist_config = consists.get(str(consist_id))

    if not consist_config:
        raise HTTPException(status_code=404, detail=f"Consist {consist_id} not found in config")

    # Get adjust loco address (direct field, not nested in reference_locos)
    adjust_loco_address = consist_config.get('adjust_loco')

    if not adjust_loco_address:
        raise HTTPException(
            status_code=400,
            detail=f"Consist {consist_id} has no adjust_loco configured"
        )

    # Read CV67-94 from JMRI roster for adjust loco
    cv_values = read_cv_speed_table(adjust_loco_address)

    if cv_values is None:
        raise HTTPException(
            status_code=404,
            detail=f"Roster file not found for locomotive {adjust_loco_address}"
        )

    # Get locomotive name from roster
    locos = load_all_locomotives()
    loco = locos.get(str(adjust_loco_address))
    adjust_loco_name = loco.name if loco else f"Loco {adjust_loco_address}"

    # Get latest session (validated or not)
    current_session = AnalyticsDB.get_latest_session()

    # Extract session info (or None if no sessions exist)
    session_id = current_session['id'] if current_session else None
    session_validated = current_session['validated'] if current_session else False

    # ALWAYS get CRITICAL/WARNING events (historical cumulative with "fixed" detection)
    # This is independent from current session state
    events_by_status = AnalyticsDB.get_critical_events_by_speed(consist_id)
    critical_events = events_by_status.get('critical', {})
    warning_events = events_by_status.get('warning', {})
    mean_delta_t_by_speed = events_by_status.get('mean_delta_t', {})
    fixed_speeds = events_by_status.get('fixed_speeds', set())

    # ALWAYS calculate CV recommendations (cumulative historical data)
    recommendations = calculate_cv_recommendations(
        cv_values=cv_values,
        critical_events=critical_events,
        warning_events=warning_events,
        mean_delta_t_by_speed=mean_delta_t_by_speed,
        fixed_speeds=fixed_speeds,
        critical_threshold=5  # Configurable threshold
    )

    return {
        'consist_id': consist_id,
        'adjust_loco_address': adjust_loco_address,
        'adjust_loco_name': adjust_loco_name,
        'session_id': session_id,
        'session_validated': session_validated,
        'cv_values': cv_values,
        'critical_events': critical_events,
        'warning_events': warning_events,
        'recommendations': recommendations,
        'fixed_count': len(fixed_speeds)  # Number of speeds proven OK in last session
    }
