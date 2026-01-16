"""
Speed Table Helper Functions

Utilities for Speed Table Viewer feature:
- Reading CV67-94 from JMRI roster XML
- Speed to JMRI step mapping
- CV recommendations calculation
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, List

# JMRI roster path (same as roster_loader.py)
ROSTER_DIR = Path.home() / "Library/Preferences/JMRI/La_mia_Ferrovia_in_JMRI.jmri/roster"


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
    Reuses Locomotive class pattern from scripts/utils/cv_operations/read_cv_from_roster.py

    Args:
        loco_address: Locomotive DCC address

    Returns:
        Dict mapping CV index (67-94) to value (0-255), or None if roster file not found

    Example:
        {67: 10, 68: 15, 69: 20, ..., 94: 255}
    """
    # Find roster file for this locomotive (format: "Loco_XXXX.xml" or by address scan)
    roster_files = list(ROSTER_DIR.glob("*.xml"))

    for roster_file in roster_files:
        try:
            tree = ET.parse(roster_file)
            root = tree.getroot()

            # Check if this is the right locomotive (by address)
            loco_elem = root.find('.//locomotive')
            if loco_elem is None:
                continue

            # Get DCC address from locomotive element attribute (same pattern as roster_loader.py)
            xml_address = loco_elem.get('dccAddress')
            if xml_address and int(xml_address) == loco_address:
                # Found the right locomotive! Read CV67-94
                cv_values = {}

                for cv_elem in root.findall('.//CVvalue'):
                    cv_name = cv_elem.get('name', '')
                    cv_value = cv_elem.get('value', '')

                    if cv_name and cv_value:
                        try:
                            cv_index = int(cv_name)
                            # Only include CV67-94 (28-step speed table)
                            if 67 <= cv_index <= 94:
                                cv_values[cv_index] = int(cv_value)
                        except ValueError:
                            pass

                # Return even if empty (locomotive exists but no speed table configured)
                return cv_values if cv_values else {}

        except (ET.ParseError, ValueError, AttributeError):
            # Skip malformed XML files
            continue

    # Locomotive not found in roster
    return None


def calculate_cv_recommendations(
    cv_values: Dict[int, int],
    critical_events: Dict[int, int],
    warning_events: Dict[int, int],
    critical_threshold: int = 5
) -> List[Dict]:
    """
    Calculate CV adjustment recommendations based on CRITICAL event counts.

    Args:
        cv_values: Current CV67-94 values (CV index -> value)
        critical_events: CRITICAL event counts per speed (speed -> count)
        warning_events: WARNING event counts per speed (speed -> count)
        critical_threshold: Minimum CRITICAL count to trigger recommendation (default: 5)

    Returns:
        List of recommendation dicts:
        [
            {
                'speed': 88,
                'jmri_step': 20,
                'cv_index': 86,
                'cv_current': 128,
                'cv_suggested': 135,
                'cv_delta': +7,
                'critical_count': 12,
                'warning_count': 5
            },
            ...
        ]

    Strategy:
        - For each speed with CRITICAL count >= threshold
        - Map speed -> JMRI step -> CV index
        - Suggest CV adjustment based on critical count severity
        - Higher critical count = larger adjustment
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

        # Calculate suggested adjustment based on severity
        # Basic heuristic: +5 per 5 CRITICAL events (can be refined later)
        adjustment_factor = (critical_count // 5) * 5
        cv_suggested = min(cv_current + adjustment_factor, 255)  # Cap at 255
        cv_delta = cv_suggested - cv_current

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
            'warning_count': warning_count
        })

    # Sort by CV index (ascending)
    recommendations.sort(key=lambda x: x['cv_index'])

    return recommendations
