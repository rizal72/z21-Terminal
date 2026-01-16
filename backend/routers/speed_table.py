"""
Speed Table API Router

Endpoints for Speed Table Viewer feature (Phase 1 - Read-Only, Phase 2 - Write).
Provides CV67-94 data, CRITICAL event analysis, CV adjustment recommendations, and direct CV write.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import json
import time

from services.analytics_db import AnalyticsDB
from services.speed_table_helpers import (
    read_cv_speed_table,
    speed_to_jmri_step,
    jmri_step_to_cv,
    calculate_cv_recommendations,
    load_all_locomotives
)
from config_loader import load_config
from dependencies import get_z21_manager
from z21_manager import Z21Manager
from log_colors import log

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


@router.post("/api/speed-table/write/{consist_id}")
async def write_speed_table_to_decoder(
    consist_id: int,
    request: Dict[str, Any],
    z21_manager: Z21Manager = Depends(get_z21_manager)
) -> Dict[str, Any]:
    """
    Write speed table CV67-94 to adjust loco decoder (Phase 2 - Direct CV Write).

    Receives cv_values from frontend (user edits + applied recommendations),
    writes them to the adjust loco decoder via Z21 operations mode (POM).

    Args:
        consist_id: Consist ID (10, 11, etc.)
        request: JSON body with cv_values dict {67: value, 68: value, ..., 94: value}
        z21_manager: Z21Manager instance (injected dependency)

    Returns:
        - success: True if all 28 CVs written successfully
        - failed_cvs: List of CV indexes that failed to write
        - total_time: Time taken to write all CVs (seconds)
        - adjust_loco_address: Address of locomotive that was written

    Raises:
        404: Consist not found in config
        400: Invalid cv_values or Z21 not connected
    """
    start_time = time.time()

    # Validate request body
    cv_values = request.get('cv_values')
    if not cv_values or not isinstance(cv_values, dict):
        raise HTTPException(status_code=400, detail="Missing or invalid cv_values in request body")

    # Get config to identify adjust loco
    config = load_config()
    consists = config.get('consists', {})
    consist_config = consists.get(str(consist_id))

    if not consist_config:
        raise HTTPException(status_code=404, detail=f"Consist {consist_id} not found in config")

    adjust_loco_address = consist_config.get('adjust_loco')
    if not adjust_loco_address:
        raise HTTPException(
            status_code=400,
            detail=f"Consist {consist_id} has no adjust_loco configured"
        )

    # Check Z21 connection
    if not z21_manager or not z21_manager.z21:
        raise HTTPException(status_code=400, detail="Z21 not connected")

    # Write CV67-94 (28 speed table values)
    log('[CV]', f"Writing speed table CV67-94 to loco {adjust_loco_address} (consist {consist_id})...")
    failed_cvs = []

    for cv_index in range(67, 95):  # CV67-94 (28 values)
        cv_value = cv_values.get(str(cv_index))

        if cv_value is None:
            log('[CV]', f"CV{cv_index} missing in request, skipping")
            failed_cvs.append(cv_index)
            continue

        # Round float to int (0-255)
        cv_value_int = max(0, min(255, round(cv_value)))

        try:
            success = z21_manager.z21.write_cv_ops_mode(adjust_loco_address, cv_index, cv_value_int)
            if not success:
                log('[CV]', f"Loco {adjust_loco_address}: CV{cv_index} write failed")
                failed_cvs.append(cv_index)
        except Exception as e:
            log('[CV]', f"Loco {adjust_loco_address}: CV{cv_index} write error: {e}")
            failed_cvs.append(cv_index)

    total_time = time.time() - start_time
    all_success = len(failed_cvs) == 0

    if all_success:
        log('[CV]', f"Speed table write complete: 28 CVs written successfully [{total_time:.2f}s]")
    else:
        log('[CV]', f"Speed table write partial: {28 - len(failed_cvs)}/28 CVs written [{total_time:.2f}s]")

    return {
        'success': all_success,
        'failed_cvs': failed_cvs,
        'total_time': round(total_time, 2),
        'adjust_loco_address': adjust_loco_address,
        'cvs_written': 28 - len(failed_cvs)
    }
