"""
Speed Table Helper Functions

Utilities for Speed Table Viewer feature:
- Reading CV67-94 from JMRI roster XML (reuses existing Locomotive class)
- Speed to JMRI step mapping
- CV recommendations calculation
"""

import sys
from pathlib import Path
from typing import Dict, Optional, List

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
    critical_threshold: int = 5
) -> List[Dict]:
    """
    Calculate CV adjustment recommendations based on CRITICAL event counts and delta_t sign.

    Args:
        cv_values: Current CV67-94 values (CV index -> value)
        critical_events: CRITICAL event counts per speed (speed -> count)
        warning_events: WARNING event counts per speed (speed -> count)
        mean_delta_t_by_speed: Mean delta_t per speed (speed -> avg_delta_t)
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
        - For each speed with CRITICAL count >= threshold
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

        # Map speed to JMRI step and CV index
        jmri_step = speed_to_jmri_step(speed)
        cv_index = jmri_step_to_cv(jmri_step)

        # Get current CV value (default 0 if not configured)
        cv_current = cv_values.get(cv_index, 0)

        # Get mean delta_t for this speed (default 0 if no data)
        mean_delta_t = mean_delta_t_by_speed.get(speed, 0.0)

        # Calculate adjustment magnitude based on severity
        # Conservative heuristic: 2 per 5 CRITICAL events (user validated safe increment)
        adjustment_magnitude = (critical_count // 5) * 2

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
