"""
Dependency Injection System

Centralizes global state management with FastAPI Depends() pattern.
Provides typed, testable access to singleton instances.
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
from fastapi import WebSocket

# Avoid circular imports: use TYPE_CHECKING for type hints only
if TYPE_CHECKING:
    from z21_manager import Z21Manager
    from tracking_manager import TrackingManager

# Singleton instances (initialized by main.py lifespan)
_z21_manager: Optional["Z21Manager"] = None
_tracking_manager: Optional["TrackingManager"] = None
_tracking_daemon_ws: Optional[WebSocket] = None
_analytics_logger = None  # AnalyticsLogger instance (set when tracking daemon starts)
_connected_clients: List[WebSocket] = []
_consist_data: Dict[int, Dict[str, Any]] = {}
_locomotive_data: Dict[int, Dict[str, Any]] = {}
_controllers_config: List[Dict[str, Any]] = []
_yolo_detections: Dict[str, Any] = {}
_timing_thresholds: Dict[str, float] = {'warning': 1.0, 'critical': 1.5}
_reference_locos: Dict[str, Dict[str, int]] = {}
_tracked_consist_ids: List[int] = []
_loco_start_times: Dict[int, float] = {}

# Background task references
_polling_task = None
_health_check_task = None

# State flags
_last_track_power_state: bool = True
_z21_online: bool = False
_z21_consecutive_failures: int = 0
_debug_enabled: bool = False


def init_dependencies(
    z21_mgr: Optional["Z21Manager"],
    tracking_mgr: Optional["TrackingManager"],
    clients: List[WebSocket],
    consists: Dict[int, Dict[str, Any]],
    locomotives: Dict[int, Dict[str, Any]],
    controllers: List[Dict[str, Any]],
    thresholds: Dict[str, float],
    ref_locos: Dict[str, Dict[str, int]],
    tracked_ids: List[int],
    debug: bool
):
    """
    Initialize dependency injection system with references to global state.
    Called from main.py lifespan startup.

    Args:
        z21_mgr: Z21Manager instance
        tracking_mgr: TrackingManager instance
        clients: List of connected WebSocket clients
        consists: Consist data dictionary
        locomotives: Locomotive data dictionary
        controllers: Controllers configuration list
        thresholds: Timing thresholds (normal, warning)
        ref_locos: Reference locos per consist
        tracked_ids: Consist IDs with gate tracking
        debug: Debug mode flag
    """
    global _z21_manager, _tracking_manager, _connected_clients, _consist_data
    global _locomotive_data, _controllers_config, _timing_thresholds
    global _reference_locos, _tracked_consist_ids, _debug_enabled

    _z21_manager = z21_mgr
    _tracking_manager = tracking_mgr
    _connected_clients = clients
    _consist_data = consists
    _locomotive_data = locomotives
    _controllers_config = controllers
    _timing_thresholds = thresholds
    _reference_locos = ref_locos
    _tracked_consist_ids = tracked_ids
    _debug_enabled = debug


# Dependency getters (for FastAPI Depends())

def get_z21_manager() -> Optional["Z21Manager"]:
    """Get Z21Manager instance"""
    return _z21_manager


def get_tracking_manager() -> Optional["TrackingManager"]:
    """Get TrackingManager instance"""
    return _tracking_manager


def get_tracking_daemon_ws() -> Optional[WebSocket]:
    """Get tracking daemon WebSocket connection"""
    return _tracking_daemon_ws


def set_tracking_daemon_ws(ws: Optional[WebSocket]):
    """Set tracking daemon WebSocket connection"""
    global _tracking_daemon_ws
    _tracking_daemon_ws = ws


def get_analytics_logger():
    """Get AnalyticsLogger instance (set when tracking daemon starts)"""
    return _analytics_logger


def set_analytics_logger(logger):
    """Set AnalyticsLogger instance (called by tracking daemon on startup)"""
    global _analytics_logger
    _analytics_logger = logger


def get_connected_clients() -> List[WebSocket]:
    """Get list of connected WebSocket clients"""
    return _connected_clients


def get_consist_data() -> Dict[int, Dict[str, Any]]:
    """Get consist data dictionary"""
    return _consist_data


def get_locomotive_data() -> Dict[int, Dict[str, Any]]:
    """Get locomotive data dictionary"""
    return _locomotive_data


def get_controllers_config() -> List[Dict[str, Any]]:
    """Get controllers configuration list"""
    return _controllers_config


def get_yolo_detections() -> Dict[str, Any]:
    """Get latest YOLO detections for video overlay"""
    return _yolo_detections


def set_yolo_detections(detections: Dict[str, Any]):
    """Update YOLO detections"""
    global _yolo_detections
    _yolo_detections = detections


def get_timing_thresholds() -> Dict[str, float]:
    """Get timing thresholds (normal, warning)"""
    return _timing_thresholds


def get_reference_locos() -> Dict[str, Dict[str, int]]:
    """Get reference locos per consist"""
    return _reference_locos


def get_tracked_consist_ids() -> List[int]:
    """Get consist IDs with gate tracking configured"""
    return _tracked_consist_ids


def get_loco_start_times() -> Dict[int, float]:
    """Get locomotive movement start times"""
    return _loco_start_times


# Background task references

def get_polling_task():
    """Get polling background task"""
    return _polling_task


def set_polling_task(task):
    """Set polling background task"""
    global _polling_task
    _polling_task = task


def get_health_check_task():
    """Get health check background task"""
    return _health_check_task


def set_health_check_task(task):
    """Set health check background task"""
    global _health_check_task
    _health_check_task = task


# State flags getters/setters

def get_track_power_state() -> bool:
    """Get last track power state"""
    return _last_track_power_state


def set_track_power_state(state: bool):
    """Set track power state"""
    global _last_track_power_state
    _last_track_power_state = state


def get_z21_online() -> bool:
    """Get Z21 online status"""
    return _z21_online


def set_z21_online(online: bool):
    """Set Z21 online status"""
    global _z21_online
    _z21_online = online


def get_z21_consecutive_failures() -> int:
    """Get Z21 consecutive failures count"""
    return _z21_consecutive_failures


def set_z21_consecutive_failures(count: int):
    """Set Z21 consecutive failures count"""
    global _z21_consecutive_failures
    _z21_consecutive_failures = count


def increment_z21_consecutive_failures() -> int:
    """Increment Z21 consecutive failures count and return new value"""
    global _z21_consecutive_failures
    _z21_consecutive_failures += 1
    return _z21_consecutive_failures


def reset_z21_consecutive_failures():
    """Reset Z21 consecutive failures count to 0"""
    global _z21_consecutive_failures
    _z21_consecutive_failures = 0


def get_debug_enabled() -> bool:
    """Get debug mode flag"""
    return _debug_enabled
