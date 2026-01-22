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
from dependencies import get_z21_manager, get_debug_enabled
from z21_manager import Z21Manager
from log_colors import log
from math_utils import js_round

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

    # Read CV67-94 + decoder metadata from DB (primary), fallback to JMRI roster
    speed_table_data = read_cv_speed_table_from_db(adjust_loco_address)

    if speed_table_data is None:
        # Fallback to JMRI roster XML (legacy format, no decoder metadata)
        log('[SPEED-TABLE]', f"Loco {adjust_loco_address}: not in DB, reading from JMRI roster (fallback)")
        cv_values = read_cv_speed_table(adjust_loco_address)

        if cv_values is None:
            raise HTTPException(
                status_code=404,
                detail=f"Speed table not found in DB or JMRI roster for locomotive {adjust_loco_address}"
            )

        # Legacy format (no decoder metadata)
        speed_table_data = {
            'cv_values': cv_values,
            'vstart': None,
            'vhigh': None,
            'decoder_type': 'nmra_standard'  # Safe default for legacy data
        }

    # Extract fields from speed_table_data
    cv_values = speed_table_data['cv_values']
    vstart = speed_table_data.get('vstart')
    vhigh = speed_table_data.get('vhigh')
    decoder_type = speed_table_data.get('decoder_type', 'nmra_standard')

    # Get locomotive name from config
    adjust_loco_name = get_locomotive_name(adjust_loco_address)

    # Get latest validated session (with at least one delta_t event)
    # Non-validated sessions (no delta_t yet) are ignored for recommendations
    # Filter by consist_id to ensure we get the correct session for this consist
    validated_sessions = DataDB.get_validated_sessions(limit=1, consist_id=consist_id)
    current_session = validated_sessions[0] if validated_sessions else None

    # Extract session info (or None if no validated sessions exist)
    session_id = current_session['id'] if current_session else None
    session_validated = True if current_session else False  # Always True if we have a session (filtered by validated=1)

    # Load consist config for recommendation_threshold
    consist_config = config.get('consists', {}).get(str(consist_id), {})
    recommendation_threshold = consist_config.get('recommendation_threshold', 10)  # Default 10

    # Get CRITICAL/WARNING events with weighted algorithm (current session prioritized)
    # Per-CV timestamp filtering: ignore events before specific CV modification
    events_by_status = DataDB.get_critical_events_by_speed(
        consist_id=consist_id,
        current_session_id=session_id,
        recommendation_threshold=recommendation_threshold,
        adjust_loco_address=adjust_loco_address
    )
    critical_events = events_by_status.get('critical', {})
    warning_events = events_by_status.get('warning', {})
    mean_delta_t_by_speed = events_by_status.get('mean_delta_t', {})
    fixed_speeds = events_by_status.get('fixed_speeds', set())
    debug_info = events_by_status.get('debug_info', {})

    # Calculate CV recommendations (with debug_info for UI breakdown)
    recommendations = calculate_cv_recommendations(
        cv_values=cv_values,
        critical_events=critical_events,
        warning_events=warning_events,
        mean_delta_t_by_speed=mean_delta_t_by_speed,
        fixed_speeds=fixed_speeds,
        decoder_type=decoder_type,
        vstart=vstart,
        vhigh=vhigh,
        critical_threshold=5,  # Configurable threshold
        debug_info=debug_info
    )

    # Load cv_timestamps for green border indicator (persistent modification state)
    conn = DataDB.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT step, cv_last_modified
        FROM cv_modification_timestamps
        WHERE loco_address = ?
    ''', (adjust_loco_address,))
    cv_timestamps = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    return {
        'consist_id': consist_id,
        'adjust_loco_address': adjust_loco_address,
        'adjust_loco_name': adjust_loco_name,
        'session_id': session_id,
        'session_validated': session_validated,
        'cv_values': cv_values,
        'vstart': vstart,  # CV2 for ESU (None for NMRA)
        'vhigh': vhigh,    # CV5 for ESU (None for NMRA)
        'decoder_type': decoder_type,  # 'esu_mfx' or 'nmra_standard'
        'critical_events': critical_events,
        'warning_events': warning_events,
        'recommendations': recommendations,
        'fixed_count': len(fixed_speeds),  # Number of speeds proven OK in last session
        'recommendation_threshold': recommendation_threshold,  # Threshold used for weighting
        'debug_info': debug_info,  # Current/historical breakdown per speed (for debug UI)
        'cv_timestamps': cv_timestamps  # Per-CV modification timestamps (step → Unix timestamp)
    }


@router.post("/api/speed-table/write/{consist_id}")
async def write_speed_table_to_decoder(
    consist_id: int,
    request: Dict[str, Any],
    z21_manager: Z21Manager = Depends(get_z21_manager),
    debug_enabled: bool = Depends(get_debug_enabled)
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

    # Detect decoder type for ESU validation
    from services.decoder_helpers import get_decoder_type_from_config, validate_cv_write_allowed

    decoder_type = get_decoder_type_from_config(adjust_loco_address)

    # Write CV67-94 (28 speed table values)
    log('[CV]', f"Writing speed table CV67-94 to loco {adjust_loco_address} (consist {consist_id}, decoder={decoder_type})...")
    blocked_cvs = []  # Read-only CVs (expected, not errors)
    failed_cvs = []   # Real write errors

    for cv_index in range(67, 95):  # CV67-94 (28 values)
        cv_value = cv_values.get(str(cv_index))

        if cv_value is None:
            log('[CV]', f"CV{cv_index} missing in request, skipping")
            failed_cvs.append(cv_index)
            continue

        # Validate if CV write is allowed (blocks ESU step 1/28)
        try:
            validate_cv_write_allowed(adjust_loco_address, cv_index, decoder_type)
        except ValueError as e:
            if debug_enabled:
                log('[CV]', f"Write blocked: {e}")
            blocked_cvs.append(cv_index)  # Track separately (not a failure)
            continue

        # Round float to int (0-255)
        cv_value_int = max(0, min(255, js_round(cv_value)))

        try:
            success = z21_manager.z21.write_cv_ops_mode(adjust_loco_address, cv_index, cv_value_int)
            if not success:
                log('[CV]', f"Loco {adjust_loco_address}: CV{cv_index} write failed")
                failed_cvs.append(cv_index)
        except Exception as e:
            log('[CV]', f"Loco {adjust_loco_address}: CV{cv_index} write error: {e}")
            failed_cvs.append(cv_index)

    total_time = time.time() - start_time
    # Success = all modifiable CVs written (blocked CVs don't count as failures)
    all_success = len(failed_cvs) == 0

    if all_success:
        # Log success message (acknowledge blocked CVs if any)
        cvs_written = 28 - len(blocked_cvs)
        if len(blocked_cvs) > 0:
            log('[CV]', f"Speed table write complete: {cvs_written}/28 CVs written ({len(blocked_cvs)} blocked, read-only) [{total_time:.2f}s]")
        else:
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

            # Update cv_modification_timestamps ONLY for CVs that actually changed
            conn = DataDB.get_connection()
            cursor = conn.cursor()
            current_timestamp = time.time()

            # First, read OLD values from database (previous_values JSON in locomotive_speed_table)
            cursor.execute('''
                SELECT previous_values FROM locomotive_speed_table
                WHERE loco_address = ?
            ''', (adjust_loco_address,))
            row = cursor.fetchone()
            old_values = {}
            if row and row[0]:
                import json
                try:
                    # previous_values stores the OLD values (before this write)
                    old_values = {int(k): int(v) for k, v in json.loads(row[0]).items()}
                except:
                    pass

            # Update timestamps ONLY for CVs that changed value
            modified_count = 0
            changed_cvs_details = []  # Track changed CVs for detailed log
            for cv_index in range(67, 95):  # CV67-94
                step = cv_index - 66  # CV67 → step 1, CV94 → step 28
                new_value = cv_values_int.get(cv_index)

                # Skip if: blocked CV, missing value, or value unchanged
                if cv_index in blocked_cvs or new_value is None:
                    continue

                old_value = old_values.get(cv_index)
                if old_value is not None and new_value == old_value:
                    # Value unchanged, don't update timestamp
                    continue

                # Value changed or first write, update timestamp
                cursor.execute('''
                    UPDATE cv_modification_timestamps
                    SET cv_last_modified = ?
                    WHERE loco_address = ? AND step = ?
                ''', (current_timestamp, adjust_loco_address, step))
                modified_count += 1

                # Track change details for log
                if old_value is not None:
                    changed_cvs_details.append(f"CV{cv_index}({old_value}->{new_value})")
                else:
                    changed_cvs_details.append(f"CV{cv_index}(new:{new_value})")

            conn.commit()
            conn.close()

            # Log with detailed CV changes
            if changed_cvs_details:
                changes_str = ", ".join(changed_cvs_details)
                log('[SPEED-TABLE]', f"CV modification timestamps updated for loco {adjust_loco_address} ({modified_count} CVs changed)")
                log('[SPEED-TABLE]', f"Changed CVs: {changes_str}")
            else:
                log('[SPEED-TABLE]', f"CV modification timestamps updated for loco {adjust_loco_address} (0 CVs changed, all values identical)")
        else:
            log('[ERROR]', f"Failed to update database for loco {adjust_loco_address}")
    else:
        log('[CV]', f"Speed table write FAILED: {28 - len(failed_cvs) - len(blocked_cvs)}/{28 - len(blocked_cvs)} modifiable CVs written [{total_time:.2f}s]")

    return {
        'success': all_success,
        'blocked_cvs': blocked_cvs,  # Read-only CVs (not errors)
        'failed_cvs': failed_cvs,    # Real write errors
        'total_time': js_round(total_time, 2),
        'adjust_loco_address': adjust_loco_address,
        'cvs_written': 28 - len(blocked_cvs) - len(failed_cvs)
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

    # Read CV67-94 + CV2/CV5 + decoder type from JMRI roster (force re-read)
    log('[SPEED-TABLE]', f"Re-importing speed table from JMRI roster for loco {adjust_loco_address}...")

    # Load full locomotive from JMRI to get all CVs and decoder metadata
    from read_cv_from_roster import load_all_locomotives
    from services.decoder_helpers import enforce_esu_fixed_values, DECODER_TYPE_MAP

    locos = load_all_locomotives()
    loco = locos.get(str(adjust_loco_address))

    if loco is None:
        raise HTTPException(
            status_code=404,
            detail=f"JMRI roster not found for locomotive {adjust_loco_address}"
        )

    # Extract CV67-94 (speed table)
    cv_values = {}
    for cv_index in range(67, 95):
        if cv_index in loco.cv:
            cv_values[cv_index] = loco.cv[cv_index]

    if not cv_values:
        raise HTTPException(
            status_code=404,
            detail=f"Speed table CV67-94 not found in JMRI roster for loco {adjust_loco_address}"
        )

    # Extract CV2 (Vstart) and CV5 (Vhigh)
    vstart = loco.cv.get(2)
    vhigh = loco.cv.get(5)

    # Detect decoder type from JMRI decoder model
    decoder_model = loco.decoder_model or ""
    decoder_type = "nmra_standard"  # Default
    for key, value in DECODER_TYPE_MAP.items():
        if key in decoder_model:
            decoder_type = value
            break

    log('[SPEED-TABLE]', f"Loco {adjust_loco_address}: CV2={vstart}, CV5={vhigh}, decoder={decoder_type}")

    # Enforce ESU fixed values if needed
    if decoder_type == "esu_mfx":
        cv_values = enforce_esu_fixed_values(cv_values, decoder_type)
        log('[SPEED-TABLE]', f"Loco {adjust_loco_address}: ESU decoder, enforced CV67=1, CV94=255")

    # Update database with JMRI values (CV67-94 + decoder metadata)
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

    # Update decoder metadata (vstart, vhigh, decoder_type)
    from services.speed_table_helpers import update_decoder_metadata_in_db
    update_decoder_metadata_in_db(adjust_loco_address, vstart, vhigh, decoder_type)

    log('[SPEED-TABLE]', f"Re-import complete: loco {adjust_loco_address} synced from JMRI roster (CV67-94 + decoder metadata)")

    return {
        'success': True,
        'adjust_loco_address': adjust_loco_address,
        'cv_values': cv_values,
        'vstart': vstart,
        'vhigh': vhigh,
        'decoder_type': decoder_type,
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
        'total_time': js_round(total_time, 2),
        'cvs_written': 28 - len(failed_cvs)
    }


@router.post("/api/speed-table/write-vstart-vhigh/{consist_id}")
async def write_vstart_vhigh_to_decoder(
    consist_id: int,
    request: Dict[str, Any],
    z21_manager: Z21Manager = Depends(get_z21_manager)
) -> Dict[str, Any]:
    """
    Write CV2 (Vstart) and CV5 (Vhigh) to ESU decoder (operations mode).

    **ESU decoders only**: CV2/CV5 are the min/max endpoints of the speed table curve.
    Changing these values scales the entire CV68-93 range.

    Args:
        consist_id: Consist ID (10, 11, etc.)
        request: JSON body with optional 'vstart' (CV2) and 'vhigh' (CV5) integer values (0-255)
        z21_manager: Z21Manager instance (injected dependency)

    Returns:
        - success: True if at least one CV written successfully
        - vstart_written: Boolean, CV2 write success
        - vhigh_written: Boolean, CV5 write success
        - adjust_loco_address: Address of locomotive
        - decoder_type: Should be 'esu_mfx'

    Raises:
        404: Consist not found
        400: Not an ESU decoder, Z21 not connected, or invalid values
    """
    start_time = time.time()

    # Validate request body
    vstart = request.get('vstart')
    vhigh = request.get('vhigh')

    if vstart is None and vhigh is None:
        raise HTTPException(status_code=400, detail="Must provide at least one of 'vstart' or 'vhigh'")

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

    # Check decoder type (ESU only)
    from services.decoder_helpers import get_decoder_type_from_config

    decoder_type = get_decoder_type_from_config(adjust_loco_address)
    if decoder_type != "esu_mfx":
        raise HTTPException(
            status_code=400,
            detail=f"Vstart/Vhigh only for ESU decoders. Loco {adjust_loco_address} is {decoder_type}."
        )

    # Check Z21 connection
    if not z21_manager or not z21_manager.z21:
        raise HTTPException(status_code=400, detail="Z21 not connected")

    # Write CV2 (Vstart) if provided
    vstart_written = False
    vhigh_written = False

    if vstart is not None:
        vstart_int = max(0, min(255, js_round(vstart)))
        log('[CV]', f"Writing CV2 (Vstart) = {vstart_int} to loco {adjust_loco_address}...")

        try:
            success = z21_manager.z21.write_cv_ops_mode(adjust_loco_address, 2, vstart_int)
            if success:
                vstart_written = True
                log('[CV]', f"CV2 (Vstart) written successfully")
            else:
                log('[CV]', f"CV2 (Vstart) write failed")
        except Exception as e:
            log('[CV]', f"CV2 (Vstart) write error: {e}")

    # Write CV5 (Vhigh) if provided
    if vhigh is not None:
        vhigh_int = max(0, min(255, js_round(vhigh)))
        log('[CV]', f"Writing CV5 (Vhigh) = {vhigh_int} to loco {adjust_loco_address}...")

        try:
            success = z21_manager.z21.write_cv_ops_mode(adjust_loco_address, 5, vhigh_int)
            if success:
                vhigh_written = True
                log('[CV]', f"CV5 (Vhigh) written successfully")
            else:
                log('[CV]', f"CV5 (Vhigh) write failed")
        except Exception as e:
            log('[CV]', f"CV5 (Vhigh) write error: {e}")

    total_time = time.time() - start_time
    overall_success = vstart_written or vhigh_written

    # Update database if any write succeeded
    if overall_success:
        from services.speed_table_helpers import update_decoder_metadata_in_db

        # Read current values from DB to preserve unchanged ones
        speed_table_data = read_cv_speed_table_from_db(adjust_loco_address)
        current_vstart = speed_table_data.get('vstart') if speed_table_data else None
        current_vhigh = speed_table_data.get('vhigh') if speed_table_data else None

        # Use new values if written, otherwise keep current
        final_vstart = vstart_int if vstart_written else current_vstart
        final_vhigh = vhigh_int if vhigh_written else current_vhigh

        update_decoder_metadata_in_db(adjust_loco_address, final_vstart, final_vhigh, decoder_type)
        log('[SPEED-TABLE]', f"Database updated for loco {adjust_loco_address}: CV2={final_vstart}, CV5={final_vhigh}")

    if overall_success:
        log('[SPEED-TABLE]', f"Vstart/Vhigh write complete [{total_time:.2f}s]")
    else:
        log('[SPEED-TABLE]', f"Vstart/Vhigh write failed [{total_time:.2f}s]")

    return {
        'success': overall_success,
        'vstart_written': vstart_written,
        'vhigh_written': vhigh_written,
        'adjust_loco_address': adjust_loco_address,
        'decoder_type': decoder_type,
        'total_time': js_round(total_time, 2)
    }
