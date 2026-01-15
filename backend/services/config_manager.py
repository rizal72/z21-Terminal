"""
Configuration Manager Service

Centralizes access to configuration data with domain-specific helpers.
Reduces direct load_config() calls and provides typed, validated access.
"""

from typing import Dict, List, Any, Optional
from config_loader import load_config

# Default constants
DEFAULT_TIMING_THRESHOLDS = {'normal': 1.0, 'warning': 1.5}
DEFAULT_IDLE_TIMEOUT = 10


class ConfigManager:
    """Centralized configuration access with domain-specific methods"""

    @staticmethod
    def get_tracking_config() -> Dict[str, Any]:
        """
        Get complete tracking configuration (timing, thresholds, consists).

        Returns:
            Dict with keys: idle_timeout_seconds, timing_thresholds, consists
        """
        config = load_config()
        tracking_config = config.get('tracking', {})

        return {
            'idle_timeout_seconds': tracking_config.get('idle_timeout_seconds', DEFAULT_IDLE_TIMEOUT),
            'timing_thresholds': tracking_config.get('timing_thresholds', DEFAULT_TIMING_THRESHOLDS),
            'consists': config.get('consists', {})
        }

    @staticmethod
    def get_timing_thresholds() -> Dict[str, float]:
        """
        Get timing thresholds for delta_t status classification.

        Returns:
            Dict with keys: normal, warning (thresholds in seconds)
        """
        config = load_config()
        tracking_config = config.get('tracking', {})
        thresholds = tracking_config.get('timing_thresholds', DEFAULT_TIMING_THRESHOLDS)

        return {
            'normal': thresholds.get('normal', DEFAULT_TIMING_THRESHOLDS['normal']),
            'warning': thresholds.get('warning', DEFAULT_TIMING_THRESHOLDS['warning'])
        }

    @staticmethod
    def get_idle_timeout() -> int:
        """
        Get idle timeout in seconds (for session validation).

        Returns:
            Idle timeout in seconds (default: 10)
        """
        config = load_config()
        tracking_config = config.get('tracking', {})
        return tracking_config.get('idle_timeout_seconds', DEFAULT_IDLE_TIMEOUT)

    @staticmethod
    def get_reference_locos() -> Dict[str, Dict[str, int]]:
        """
        Get reference loco configuration per consist.

        Returns:
            Dict mapping consist_id (str) → {'reference': addr, 'adjust': addr}

        Example:
            {
                '10': {'reference': 1, 'adjust': 5},
                '11': {'reference': 7, 'adjust': 8}
            }
        """
        config = load_config()
        consists = config.get('consists', {})

        reference_locos = {}
        for consist_addr, consist_info in consists.items():
            reference_locos[consist_addr] = {
                'reference': consist_info.get('reference_loco'),
                'adjust': consist_info.get('adjust_loco')
            }

        return reference_locos

    @staticmethod
    def get_tracked_consist_ids() -> List[int]:
        """
        Get list of consist IDs with gate tracking configured.

        Returns:
            List of consist IDs (integers) with tracking_assignments

        Example:
            [10, 11]
        """
        config = load_config()
        consists = config.get('consists', {})

        tracked_ids = []
        for consist_addr, consist_info in consists.items():
            # Check if consist has tracking_assignments (gate mapping)
            if consist_info.get('tracking_assignments'):
                try:
                    tracked_ids.append(int(consist_addr))
                except ValueError:
                    pass  # Skip invalid consist IDs

        return tracked_ids

    @staticmethod
    def get_consist_config(consist_id: int) -> Optional[Dict[str, Any]]:
        """
        Get full configuration for a specific consist.

        Args:
            consist_id: Consist DCC address

        Returns:
            Consist configuration dict or None if not found
        """
        config = load_config()
        consists = config.get('consists', {})
        return consists.get(str(consist_id))

    @staticmethod
    def get_gates() -> List[Dict[str, Any]]:
        """
        Get all configured gate zones.

        Returns:
            List of gate configuration dicts with keys:
            id, x, y, width, height, rotation, type
        """
        config = load_config()
        return config.get('gates', [])

    @staticmethod
    def get_debug_enabled() -> bool:
        """
        Get debug mode flag.

        Returns:
            True if debug logging is enabled, False otherwise
        """
        try:
            config = load_config()
            debug_config = config.get('debug', {'enabled': False})
            return debug_config.get('enabled', False)
        except Exception:
            return False

    @staticmethod
    def get_yolo_config() -> Dict[str, Any]:
        """
        Get YOLO model configuration.

        Returns:
            Dict with YOLO settings: confidence, iou, model_path, etc.
        """
        config = load_config()
        return config.get('yolo', {
            'confidence': 0.3,
            'iou': 0.6,
            'obb': True
        })
