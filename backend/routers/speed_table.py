"""
Speed Table API Router

Endpoints for Speed Table Viewer feature (Phase 1 - Read-Only, Phase 2 - Write).
Provides CV67-94 data, CRITICAL event analysis, CV adjustment recommendations, and direct CV write.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import json
import time

from services.data_db import DataDB
from services.speed_table_helpers import (
    read_cv_speed_table,
    read_cv_speed_table_from_db,
    update_cv_speed_table_in_db,
    undo_cv_speed_table,
    speed_to_jmri_step,
    jmri_step_to_cv,
    calculate_cv_recommendations
)
from services.config_helpers import get_locomotive_name, get_all_locomotives
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

    # Read CV67-94 from DB (primary), fallback to JMRI roster
    cv_values = read_cv_speed_table_from_db(adjust_loco_address)

    if cv_values is None:
        # Fallback to JMRI roster XML
        log('[SPEED-TABLE]', f"Loco {adjust_loco_address}: not in DB, reading from JMRI roster (fallback)")
        cv_values = read_cv_speed_table(adjust_loco_address)

        if cv_values is None:
            raise HTTPException(
                status_code=404,
                detail=f"Speed table not found in DB or JMRI roster for locomotive {adjust_loco_address}"
            )

    # Get locomotive name from config
    adjust_loco_name = get_locomotive_name(adjust_loco_address)

    # Get latest session (validated or not)
    current_session = DataDB.get_latest_session()

    # Extract session info (or None if no sessions exist)
    session_id = current_session['id'] if current_session else None
    session_validated = current_session['validated'] if current_session else False

    # ALWAYS get CRITICAL/WARNING events (historical cumulative with "fixed" detection)
    # This is independent from current session state
    events_by_status = DataDB.get_critical_events_by_speed(consist_id)
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

        # Update database after successful write (with undo snapshot)
        cv_values_int = {int(k): int(v) for k, v in cv_values.items()}
        db_success = update_cv_speed_table_in_db(
            loco_address=adjust_loco_address,
            cv_values=cv_values_int,
            source='web_ui'
        )

        if db_success:
            log('[SPEED-TABLE]', f"Database updated for loco {adjust_loco_address} (undo snapshot saved)")
        else:
            log('[ERROR]', f"Failed to update database for loco {adjust_loco_address}")
    else:
        log('[CV]', f"Speed table write partial: {28 - len(failed_cvs)}/28 CVs written [{total_time:.2f}s]")

    return {
        'success': all_success,
        'failed_cvs': failed_cvs,
        'total_time': round(total_time, 2),
        'adjust_loco_address': adjust_loco_address,
        'cvs_written': 28 - len(failed_cvs)
    }


@router.post("/api/speed-table/reimport/{consist_id}")
async def reimport_speed_table_from_jmri(consist_id: int) -> Dict[str, Any]:
    """
    Re-import speed table CV67-94 from JMRI roster to database.

    **IMPORTANT**: Re-imports ONLY the adjust_loco of the specified consist.
    Does NOT touch other locomotives in the roster. Safe targeted operation.

    Use case: User modified CV via JMRI DecoderPro and wants to sync DB with JMRI.

    Args:
        consist_id: Consist ID (10, 11, etc.)

    Returns:
        - success: True if CV reimported successfully
        - adjust_loco_address: Address of locomotive (ONLY this loco is reimported)
        - cv_values: CV67-94 values read from JMRI roster
        - source: 'jmri_reimport'

    Raises:
        404: Consist not found, or JMRI roster not found for locomotive
    """
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

    # Read CV67-94 from JMRI roster (force re-read)
    log('[SPEED-TABLE]', f"Re-importing speed table from JMRI roster for loco {adjust_loco_address}...")
    cv_values = read_cv_speed_table(adjust_loco_address)

    if cv_values is None:
        raise HTTPException(
            status_code=404,
            detail=f"JMRI roster not found for locomotive {adjust_loco_address}"
        )

    # Update database with JMRI values
    db_success = update_cv_speed_table_in_db(
        loco_address=adjust_loco_address,
        cv_values=cv_values,
        source='jmri_reimport'
    )

    if not db_success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update database for loco {adjust_loco_address}"
        )

    log('[SPEED-TABLE]', f"Re-import complete: loco {adjust_loco_address} synced from JMRI roster")

    return {
        'success': True,
        'adjust_loco_address': adjust_loco_address,
        'cv_values': cv_values,
        'source': 'jmri_reimport'
    }


@router.post("/api/speed-table/undo/{consist_id}")
async def undo_speed_table_change(
    consist_id: int,
    z21_manager: Z21Manager = Depends(get_z21_manager)
) -> Dict[str, Any]:
    """
    Undo last speed table change (restore previous_values from DB).

    Restores previous CV67-94 values from database snapshot and writes them
    to decoder via Z21 operations mode (POM). Swaps current <-> previous in DB
    (so you can undo the undo).

    Args:
        consist_id: Consist ID (10, 11, etc.)
        z21_manager: Z21Manager instance (injected dependency)

    Returns:
        - success: True if CV restored successfully
        - adjust_loco_address: Address of locomotive
        - previous_values: CV67-94 values restored (before undo)
        - failed_cvs: List of CV indexes that failed to write

    Raises:
        404: Consist not found, or no undo available
        400: Z21 not connected
    """
    start_time = time.time()

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

    # Restore previous values from DB (swaps current <-> previous)
    log('[SPEED-TABLE]', f"Restoring previous speed table for loco {adjust_loco_address}...")
    previous_values = undo_cv_speed_table(adjust_loco_address)

    if previous_values is None:
        raise HTTPException(
            status_code=404,
            detail=f"No undo available for locomotive {adjust_loco_address}"
        )

    # Write previous CV67-94 to decoder via POM
    log('[CV]', f"Writing previous CV67-94 to loco {adjust_loco_address}...")
    failed_cvs = []

    for cv_index in range(67, 95):  # CV67-94 (28 values)
        cv_value = previous_values.get(str(cv_index))

        if cv_value is None:
            log('[CV]', f"CV{cv_index} missing in previous_values, skipping")
            failed_cvs.append(cv_index)
            continue

        try:
            success = z21_manager.z21.write_cv_ops_mode(adjust_loco_address, cv_index, cv_value)
            if not success:
                log('[CV]', f"Loco {adjust_loco_address}: CV{cv_index} undo write failed")
                failed_cvs.append(cv_index)
        except Exception as e:
            log('[CV]', f"Loco {adjust_loco_address}: CV{cv_index} undo write error: {e}")
            failed_cvs.append(cv_index)

    total_time = time.time() - start_time
    all_success = len(failed_cvs) == 0

    if all_success:
        log('[SPEED-TABLE]', f"Undo complete: loco {adjust_loco_address} restored [{total_time:.2f}s]")
    else:
        log('[SPEED-TABLE]', f"Undo partial: {28 - len(failed_cvs)}/28 CVs restored [{total_time:.2f}s]")

    return {
        'success': all_success,
        'adjust_loco_address': adjust_loco_address,
        'previous_values': previous_values,
        'failed_cvs': failed_cvs,
        'total_time': round(total_time, 2),
        'cvs_written': 28 - len(failed_cvs)
    }
