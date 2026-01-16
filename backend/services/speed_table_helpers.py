"""
Speed Table Helper Functions

Utilities for Speed Table Viewer feature:
- Reading CV67-94 from JMRI roster XML (reuses existing Locomotive class)
- Reading CV67-94 from database (source of truth after migration)
- Writing CV67-94 to database (with undo snapshot)
- Speed to JMRI step mapping
- CV recommendations calculation
"""

import sys
import sqlite3
import json
from pathlib import Path
from typing import Dict, Optional, List
from log_colors import log

# Add scripts/utils/cv_operations to path for Locomotive class import
SCRIPT_DIR = Path(__file__).parent.parent.parent / "scripts" / "utils" / "cv_operations"
sys.path.insert(0, str(SCRIPT_DIR))

from read_cv_from_roster import Locomotive, load_all_locomotives


def speed_to_jmri_step(dcc_speed: int) -> int:
    """
    Map DCC speed (0-126) to JMRI step (1-28).

    Args:
        dcc_speed: DCC speed value (0-126)

    Returns:
        JMRI step index (1-28)

    Example:
        speed_to_jmri_step(0) -> 1
        speed_to_jmri_step(4) -> 1
        speed_to_jmri_step(88) -> 20
        speed_to_jmri_step(126) -> 28
    """
    step_index = int(dcc_speed // 4.5)  # 0-27
    return min(step_index + 1, 28)  # JMRI uses 1-based indexing, cap at 28


def jmri_step_to_cv(step: int) -> int:
    """
    Map JMRI step (1-28) to CV index (67-94).

    Args:
        step: JMRI step (1-28)

    Returns:
        CV index (67-94)

    Example:
        jmri_step_to_cv(1) -> 67
        jmri_step_to_cv(20) -> 86
        jmri_step_to_cv(28) -> 94
    """
    return 66 + step


def read_cv_speed_table(loco_address: int) -> Optional[Dict[int, int]]:
    """
    Read CV67-94 (28-step speed table) from JMRI roster XML for a locomotive.
    Reuses existing Locomotive class from scripts/utils/cv_operations/read_cv_from_roster.py

    Args:
        loco_address: Locomotive DCC address

    Returns:
        Dict mapping CV index (67-94) to value (0-255), or None if roster file not found

    Example:
        {67: 10, 68: 15, 69: 20, ..., 94: 255}
    """
    # Load all locomotives using existing function
    locos = load_all_locomotives()

    # Find locomotive by address (address is stored as string in dict)
    loco = locos.get(str(loco_address))

    if loco is None:
        return None

    # Extract CV67-94 from locomotive's CV dict
    cv_speed_table = {}
    for cv_index in range(67, 95):  # CV67-94 (28 steps)
        if cv_index in loco.cv:
            cv_speed_table[cv_index] = loco.cv[cv_index]

    # Return even if empty (locomotive exists but no speed table configured)
    return cv_speed_table if cv_speed_table else {}


def calculate_cv_recommendations(
    cv_values: Dict[int, int],
    critical_events: Dict[int, int],
    warning_events: Dict[int, int],
    mean_delta_t_by_speed: Dict[int, float],
    fixed_speeds: set,
    critical_threshold: int = 5
) -> List[Dict]:
    """
    Calculate CV adjustment recommendations based on historical CRITICAL counts and delta_t sign.

    Excludes speeds that are "fixed" in their last tested session (proven OK with >= 3 events, < 20% CRITICAL rate).

    Args:
        cv_values: Current CV67-94 values (CV index -> value)
        critical_events: Historical CRITICAL event counts per speed (speed -> count)
        warning_events: Historical WARNING event counts per speed (speed -> count)
        mean_delta_t_by_speed: Historical mean delta_t per speed (speed -> avg_delta_t)
        fixed_speeds: Set of speeds proven OK in last session (no recommendation needed)
        critical_threshold: Minimum CRITICAL count to trigger recommendation (default: 5)

    Returns:
        List of recommendation dicts:
        [
            {
                'speed': 88,
                'jmri_step': 20,
                'cv_index': 86,
                'cv_current': 128,
                'cv_suggested': 126,  # Could be lower OR higher
                'cv_delta': -2,       # Negative = decrease, Positive = increase
                'critical_count': 12,
                'warning_count': 5,
                'mean_delta_t': -1.2  # Negative = adjust faster
            },
            ...
        ]

    Strategy:
        - For each speed with historical CRITICAL count >= threshold
        - Skip if speed is in fixed_speeds set (proven OK in last session)
        - Use mean delta_t sign to determine adjustment direction:
          * delta_t < 0 → adjust loco FASTER (arrives first) → DECREASE CV (slow down)
          * delta_t > 0 → adjust loco SLOWER (arrives second) → INCREASE CV (speed up)
        - Adjustment magnitude based on critical count severity
    """
    recommendations = []

    # Iterate over speeds with CRITICAL events
    for speed, critical_count in critical_events.items():
        if critical_count < critical_threshold:
            continue  # Not severe enough

        # Skip if speed proven fixed in last session
        if speed in fixed_speeds:
            continue  # Speed is OK now

        # Map speed to JMRI step and CV index
        jmri_step = speed_to_jmri_step(speed)
        cv_index = jmri_step_to_cv(jmri_step)

        # Get current CV value (default 0 if not configured)
        cv_current = cv_values.get(cv_index, 0)

        # Get mean delta_t for this speed (default 0 if no data)
        mean_delta_t = mean_delta_t_by_speed.get(speed, 0.0)

        # Fixed adjustment: ±1 (iterative conservative approach)
        # CV misconfiguration is constant regardless of CRITICAL count
        # More CRITICALs = more confirmation of problem, not bigger CV error
        # Iterative workflow: adjust -1, retest, still problematic? -1 again
        # Phase 2 auto-adjust will need smoothing (±1 on adjacent CVs too)
        adjustment_magnitude = 1

        # Determine direction based on delta_t sign
        # delta_t = arrival_adjust - arrival_reference
        # Negative delta_t → adjust arrives first (faster) → need to DECREASE CV (slow down)
        # Positive delta_t → adjust arrives second (slower) → need to INCREASE CV (speed up)
        if mean_delta_t < 0:
            # Adjust loco is FASTER → slow it down (decrease CV)
            cv_delta = -adjustment_magnitude
        else:
            # Adjust loco is SLOWER → speed it up (increase CV)
            cv_delta = adjustment_magnitude

        # Calculate suggested CV (clamp between 0-255)
        cv_suggested = max(0, min(cv_current + cv_delta, 255))
        cv_delta = cv_suggested - cv_current  # Recalculate actual delta after clamping

        # Get warning count for this speed (if any)
        warning_count = warning_events.get(speed, 0)

        recommendations.append({
            'speed': speed,
            'jmri_step': jmri_step,
            'cv_index': cv_index,
            'cv_current': cv_current,
            'cv_suggested': cv_suggested,
            'cv_delta': cv_delta,
            'critical_count': critical_count,
            'warning_count': warning_count,
            'mean_delta_t': round(mean_delta_t, 3)
        })

    # Sort by CV index (ascending)
    recommendations.sort(key=lambda x: x['cv_index'])

    return recommendations


# ============================================================================
# Database Functions (Speed Table Migration)
# ============================================================================

def read_cv_speed_table_from_db(loco_address: int) -> Optional[Dict[int, int]]:
    """
    Read CV67-94 from database (source of truth after migration).

    Args:
        loco_address: Locomotive DCC address (1-8)

    Returns:
        Dict {67: value, 68: value, ..., 94: value} or None if not found
    """
    conn = sqlite3.connect('data/analytics.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cv67, cv68, cv69, cv70, cv71, cv72, cv73, cv74, cv75, cv76,
               cv77, cv78, cv79, cv80, cv81, cv82, cv83, cv84, cv85, cv86,
               cv87, cv88, cv89, cv90, cv91, cv92, cv93, cv94
        FROM locomotive_speed_table
        WHERE loco_address = ?
    """, (loco_address,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    # Convert tuple to dict {67: value, 68: value, ..., 94: value}
    return {67 + i: row[i] for i in range(28)}


def update_cv_speed_table_in_db(
    loco_address: int,
    cv_values: Dict[int, int],
    source: str = 'web_ui'
) -> bool:
    """
    Update CV67-94 in database after successful POM write.

    Saves previous values as JSON snapshot (1-level undo).

    Args:
        loco_address: Locomotive DCC address
        cv_values: Dict {67: value, 68: value, ..., 94: value}
        source: 'web_ui', 'test_mode', 'jmri_import', 'jmri_reimport', 'undo'

    Returns:
        True if successful, False if error
    """
    try:
        conn = sqlite3.connect('data/analytics.db')
        cursor = conn.cursor()

        # Get current values (for undo snapshot)
        cursor.execute("""
            SELECT cv67, cv68, cv69, cv70, cv71, cv72, cv73, cv74, cv75, cv76,
                   cv77, cv78, cv79, cv80, cv81, cv82, cv83, cv84, cv85, cv86,
                   cv87, cv88, cv89, cv90, cv91, cv92, cv93, cv94
            FROM locomotive_speed_table
            WHERE loco_address = ?
        """, (loco_address,))

        row = cursor.fetchone()
        previous_values = None

        if row:
            # Save current as previous (undo snapshot)
            previous_values = json.dumps({67 + i: row[i] for i in range(28)})

        # Prepare new values (cv67-cv94 in order)
        new_values = [cv_values.get(67 + i, 0) for i in range(28)]

        # Insert or replace
        cursor.execute("""
            INSERT OR REPLACE INTO locomotive_speed_table (
                loco_address,
                cv67, cv68, cv69, cv70, cv71, cv72, cv73, cv74, cv75, cv76,
                cv77, cv78, cv79, cv80, cv81, cv82, cv83, cv84, cv85, cv86,
                cv87, cv88, cv89, cv90, cv91, cv92, cv93, cv94,
                previous_values, last_modified, source
            ) VALUES (
                ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, CURRENT_TIMESTAMP, ?
            )
        """, (loco_address, *new_values, previous_values, source))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        log('[ERROR]', f"Failed to update DB for loco {loco_address}: {e}")
        return False


def undo_cv_speed_table(loco_address: int) -> Optional[Dict[int, int]]:
    """
    Undo last speed table change (restore previous_values).

    Swaps current ↔ previous (so you can undo the undo).

    Args:
        loco_address: Locomotive DCC address

    Returns:
        Dict {67: value, ..., 94: value} (previous values) or None if no undo available
    """
    conn = sqlite3.connect('data/analytics.db')
    cursor = conn.cursor()

    # Get previous_values
    cursor.execute("""
        SELECT previous_values
        FROM locomotive_speed_table
        WHERE loco_address = ?
    """, (loco_address,))

    row = cursor.fetchone()

    if not row or not row[0]:
        conn.close()
        return None  # No undo available

    # Parse JSON
    previous_values = json.loads(row[0])

    # Swap: current ↔ previous (so we can undo the undo)
    cursor.execute("""
        SELECT cv67, cv68, cv69, cv70, cv71, cv72, cv73, cv74, cv75, cv76,
               cv77, cv78, cv79, cv80, cv81, cv82, cv83, cv84, cv85, cv86,
               cv87, cv88, cv89, cv90, cv91, cv92, cv93, cv94
        FROM locomotive_speed_table
        WHERE loco_address = ?
    """, (loco_address,))

    current_row = cursor.fetchone()
    current_values_json = json.dumps({67 + i: current_row[i] for i in range(28)})

    # Update DB with previous values (current → previous snapshot)
    new_values = [previous_values[str(67 + i)] for i in range(28)]

    cursor.execute("""
        UPDATE locomotive_speed_table
        SET cv67=?, cv68=?, cv69=?, cv70=?, cv71=?, cv72=?, cv73=?, cv74=?, cv75=?, cv76=?,
            cv77=?, cv78=?, cv79=?, cv80=?, cv81=?, cv82=?, cv83=?, cv84=?, cv85=?, cv86=?,
            cv87=?, cv88=?, cv89=?, cv90=?, cv91=?, cv92=?, cv93=?, cv94=?,
            previous_values=?, last_modified=CURRENT_TIMESTAMP, source='undo'
        WHERE loco_address=?
    """, (*new_values, current_values_json, loco_address))

    conn.commit()
    conn.close()

    return previous_values
