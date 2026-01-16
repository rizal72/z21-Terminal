"""
Config loader with backward compatibility for locomotive data.

Supports both:
- New format: config['locomotives'][address]
- Old format: config['locomotive_colors'][address], config['cv_profiles'][address]

Allows gradual migration without breaking existing code.
"""

from config_loader import load_config
from typing import Dict, Any, Optional


def get_locomotive_color(address: int) -> str:
    """
    Get locomotive color (hex string) with fallback.

    Args:
        address: Locomotive DCC address (1-8)

    Returns:
        Hex color string (e.g., "#FFFF00")
    """
    config = load_config()
    address_str = str(address)

    # New format (preferred)
    if 'locomotives' in config and address_str in config['locomotives']:
        return config['locomotives'][address_str].get('color', '#808080')

    # Old format (fallback)
    if 'locomotive_colors' in config and address_str in config['locomotive_colors']:
        return config['locomotive_colors'][address_str]

    # Default gray
    return '#808080'


def get_locomotive_cv_profile(address: int, mode: str = 'normal') -> Dict[str, int]:
    """
    Get CV3/CV4 profile for locomotive with fallback.

    Args:
        address: Locomotive DCC address (1-8)
        mode: 'normal' or 'testing'

    Returns:
        Dict with cv3 and cv4 values (e.g., {'cv3': 78, 'cv4': 58})
    """
    config = load_config()
    address_str = str(address)

    # New format (preferred)
    if 'locomotives' in config and address_str in config['locomotives']:
        cv_profiles = config['locomotives'][address_str].get('cv_profiles', {})
        return cv_profiles.get(mode, {'cv3': 0, 'cv4': 0})

    # Old format (fallback)
    if 'cv_profiles' in config and address_str in config['cv_profiles']:
        return config['cv_profiles'][address_str].get(mode, {'cv3': 0, 'cv4': 0})

    # Default no momentum
    return {'cv3': 0, 'cv4': 0}


def get_locomotive_name(address: int) -> str:
    """
    Get locomotive name from config.

    Args:
        address: Locomotive DCC address (1-8)

    Returns:
        Locomotive name (e.g., "Gr.675 017") or fallback "Loco {address}"
    """
    config = load_config()
    address_str = str(address)

    if 'locomotives' in config and address_str in config['locomotives']:
        return config['locomotives'][address_str].get('name', f"Loco {address}")

    # Fallback
    return f"Loco {address}"


def get_locomotive_decoder(address: int) -> Optional[str]:
    """
    Get locomotive decoder type from config.

    Args:
        address: Locomotive DCC address (1-8)

    Returns:
        Decoder type (e.g., "ESU LokSound V4.0") or None
    """
    config = load_config()
    address_str = str(address)

    if 'locomotives' in config and address_str in config['locomotives']:
        return config['locomotives'][address_str].get('decoder')

    return None


def get_all_locomotives() -> Dict[str, Dict[str, Any]]:
    """
    Get all locomotives from config (new format only).

    Returns:
        Dict of locomotives keyed by address string (e.g., {'1': {...}, '5': {...}})
        Returns empty dict if 'locomotives' section doesn't exist
    """
    config = load_config()
    return config.get('locomotives', {})


def has_new_locomotive_format() -> bool:
    """
    Check if config uses new unified locomotive format.

    Returns:
        True if 'locomotives' section exists, False otherwise
    """
    config = load_config()
    return 'locomotives' in config
