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
    calculate_cv_recommendations
)
from services.config_manager import get_config

router = APIRouter()


@router.get("/api/speed-table/{consist_id}")
async def get_speed_table_data(consist_id: int) -> Dict[str, Any]:
    """
    Get Speed Table Viewer data for a consist (Phase 1 - Read-Only).

    Returns:
        - cv_values: CV67-94 current values from JMRI roster
        - critical_events: CRITICAL event counts per speed (current session)
        - warning_events: WARNING event counts per speed (current session)
        - recommendations: List of CV adjustment suggestions
        - adjust_loco_address: Address of the locomotive being analyzed
        - session_id: Current session ID (or None if no active session)
        - session_validated: Whether session is validated

    Args:
        consist_id: Consist ID (10, 11, etc.)

    Raises:
        404: Consist not found in config
        500: Roster file not found or other errors
    """
    # Get config to identify adjust loco
    config = get_config()

    # Find consist in config
    consist_config = None
    for consist in config.get('consists', []):
        if consist['address'] == consist_id:
            consist_config = consist
            break

    if not consist_config:
        raise HTTPException(status_code=404, detail=f"Consist {consist_id} not found in config")

    # Get adjust loco address from reference_locos mapping
    reference_locos = consist_config.get('reference_locos', {})
    adjust_loco_address = reference_locos.get('adjust')

    if not adjust_loco_address:
        raise HTTPException(
            status_code=400,
            detail=f"Consist {consist_id} has no adjust loco configured in reference_locos"
        )

    # Read CV67-94 from JMRI roster for adjust loco
    cv_values = read_cv_speed_table(adjust_loco_address)

    if cv_values is None:
        raise HTTPException(
            status_code=404,
            detail=f"Roster file not found for locomotive {adjust_loco_address}"
        )

    # Get current session (if any)
    # Find most recent validated session (or running session)
    sessions = AnalyticsDB.get_validated_sessions(limit=1, exclude_running=False)

    if not sessions:
        # No sessions yet - return empty data
        return {
            'consist_id': consist_id,
            'adjust_loco_address': adjust_loco_address,
            'session_id': None,
            'session_validated': False,
            'cv_values': cv_values,
            'critical_events': {},
            'warning_events': {},
            'recommendations': [],
            'message': 'No active session - waiting for locomotive movement'
        }

    current_session = sessions[0]
    session_id = current_session['id']
    session_validated = True  # get_validated_sessions only returns validated=1

    # Get CRITICAL/WARNING events for current session
    events_by_status = AnalyticsDB.get_critical_events_by_speed(consist_id, session_id)
    critical_events = events_by_status.get('critical', {})
    warning_events = events_by_status.get('warning', {})

    # Calculate CV recommendations
    recommendations = calculate_cv_recommendations(
        cv_values=cv_values,
        critical_events=critical_events,
        warning_events=warning_events,
        critical_threshold=5  # Configurable threshold
    )

    return {
        'consist_id': consist_id,
        'adjust_loco_address': adjust_loco_address,
        'session_id': session_id,
        'session_validated': session_validated,
        'cv_values': cv_values,
        'critical_events': critical_events,
        'warning_events': warning_events,
        'recommendations': recommendations
    }
