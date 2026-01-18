"""
Config Router

Handles all configuration-related endpoints:
- Consists CRUD operations (create, read, update, delete)
- Gate configuration management
- Tracking configuration access
"""

from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from pathlib import Path
from config_loader import load_config, save_config, get_config_path
from roster_loader import load_consists_from_config
from services.broadcast import build_consist_response, broadcast_initial_state
from services.config_manager import ConfigManager
from dependencies import get_consist_data, get_z21_manager
from z21_manager import Z21Manager
from log_colors import log

router = APIRouter(tags=["config"])

# Configuration paths
CONFIG_PATH = get_config_path()


@router.get("/api/config")
async def get_config():
    """Get entire config.json for Settings UI"""
    return load_config()


@router.post("/api/settings/update")
async def update_settings(request: dict):
    """
    Update config.json and determine which services need restart

    Handles unified config structure:
    - System (debug.enabled)
    - Z21 Network (z21.host, z21.port)
    - Camera (camera.* - credentials split to config.local.json)
    - Video Feed (video.fps - hot reload)
    - YOLO Model (tracking.yolo_* - restart tracker)
    - Tracking (tracking.fps, tracking.timing_thresholds - restart tracker)

    Returns:
        {
            "status": "success",
            "message": "Settings saved",
            "restart_needed": ["backend", "video_feed", "tracker"]
        }
    """
    try:
        # Load current config
        config = load_config()
        config_local = {}  # Credentials to save separately

        # Track which services need restart
        restart_needed = []

        # System settings (debug.enabled)
        if "debug" in request:
            old_debug = config.get("debug", {}).get("enabled", False)
            new_debug = request["debug"].get("enabled", False)

            if old_debug != new_debug:
                restart_needed.append("backend")

            if "debug" not in config:
                config["debug"] = {}
            config["debug"]["enabled"] = new_debug

        # Z21 Network settings (z21.host, z21.port)
        if "z21" in request:
            old_z21 = config.get("z21", {})
            new_z21 = request["z21"]

            if (old_z21.get("host") != new_z21.get("host") or
                old_z21.get("port") != new_z21.get("port")):
                restart_needed.append("backend")

            config["z21"] = {
                "host": new_z21.get("host", "192.168.1.111"),
                "port": new_z21.get("port", 21105),
                "notes": config.get("z21", {}).get("notes", "Roco Z21 Bianca hardware controller")
            }

        # Camera settings (camera.* - split credentials to config.local.json)
        if "camera" in request:
            old_camera = config.get("camera", {})
            new_camera = request["camera"]

            # Check if RTSP-related settings changed (requires restart)
            if (old_camera.get("ip") != new_camera.get("ip") or
                old_camera.get("port") != new_camera.get("port") or
                old_camera.get("stream") != new_camera.get("stream")):
                restart_needed.append("video_feed")
                restart_needed.append("tracker")

            # Split: public settings → config.json, credentials → config.local.json
            config["camera"] = {
                "ip": new_camera.get("ip", "192.168.1.4"),
                "port": new_camera.get("port", 554),
                "stream": new_camera.get("stream", "stream2"),
                "resolution": new_camera.get("resolution", {"width": 1280, "height": 720}),
                "username": "",  # Empty in config.json
                "password": "",  # Empty in config.json
                "notes": config.get("camera", {}).get("notes", "Camera credentials MUST be in config.local.json (gitignored)")
            }

            # Save credentials to config.local.json (gitignored)
            if new_camera.get("username") or new_camera.get("password"):
                config_local["camera"] = {
                    "username": new_camera.get("username", ""),
                    "password": new_camera.get("password", "")
                }

        # Video Feed settings (video.fps - hot reload, no restart)
        if "video" in request:
            new_video = request["video"]
            config["video"] = {
                "fps": new_video.get("fps", 30),
                "notes": config.get("video", {}).get("notes", "MJPEG video stream frame rate (hot reload, no restart needed)")
            }
            # Note: video FPS is hot reload, no restart needed

        # Tracking settings (tracking.* - restart tracker)
        if "tracking" in request:
            old_tracking = config.get("tracking", {})
            new_tracking = request["tracking"]

            # Check if any tracking setting changed
            tracking_changed = False

            # FPS settings
            if "fps" in new_tracking:
                old_fps = old_tracking.get("fps", {})
                new_fps = new_tracking["fps"]
                if (old_fps.get("active") != new_fps.get("active") or
                    old_fps.get("idle") != new_fps.get("idle") or
                    old_fps.get("video_feed") != new_fps.get("video_feed")):
                    tracking_changed = True

            # Idle timeout
            if "idle_timeout_seconds" in new_tracking:
                if old_tracking.get("idle_timeout_seconds") != new_tracking["idle_timeout_seconds"]:
                    tracking_changed = True

            # Timing thresholds
            if "timing_thresholds" in new_tracking:
                old_thresholds = old_tracking.get("timing_thresholds", {})
                new_thresholds = new_tracking["timing_thresholds"]
                if (old_thresholds.get("warning") != new_thresholds.get("warning") or
                    old_thresholds.get("critical") != new_thresholds.get("critical") or
                    old_thresholds.get("max_delta_t") != new_thresholds.get("max_delta_t")):
                    tracking_changed = True

            # YOLO settings (confidence, iou, imgsz, obb)
            yolo_keys = ["yolo_confidence", "yolo_iou", "yolo_imgsz", "yolo_obb"]
            for key in yolo_keys:
                if key in new_tracking and old_tracking.get(key) != new_tracking[key]:
                    tracking_changed = True

            if tracking_changed:
                restart_needed.append("tracker")

            # Update tracking section
            if "tracking" not in config:
                config["tracking"] = {}
            config["tracking"].update(new_tracking)

        # Save config.json
        save_config(config)

        # Save config.local.json (credentials only)
        if config_local:
            from pathlib import Path
            config_local_path = get_config_path().parent / "config.local.json"

            # Load existing config.local.json to merge
            try:
                with open(config_local_path, 'r') as f:
                    existing_local = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                existing_local = {}

            # Merge camera credentials
            existing_local.update(config_local)

            # Save merged config.local.json
            with open(config_local_path, 'w') as f:
                json.dump(existing_local, f, indent=2)

            log('[SETTINGS]', 'Camera credentials saved to config.local.json')

        # Deduplicate restart list
        restart_needed = list(set(restart_needed))

        log('[SETTINGS]', f"Settings saved, restart needed: {restart_needed if restart_needed else 'none'}")

        return {
            "status": "success",
            "message": "Settings saved successfully",
            "restart_needed": restart_needed
        }

    except Exception as e:
        log('[ERROR]', f"Settings update failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "restart_needed": []
        }


@router.post("/api/settings/yolo-preset/load")
async def load_yolo_preset(request: dict):
    """
    Load YOLO preset profile from config.json

    Request body:
        {"preset": "tracking_OBB"}  or  {"preset": "tracking_standard"}

    Returns preset values to populate Settings UI form
    """
    try:
        preset_name = request.get("preset")
        if not preset_name:
            return {"status": "error", "message": "Missing preset name"}

        config = load_config()
        preset_data = config.get(preset_name)

        if not preset_data:
            return {"status": "error", "message": f"Preset '{preset_name}' not found"}

        log('[SETTINGS]', f"Loaded YOLO preset: {preset_name}")

        return {
            "status": "success",
            "preset": preset_data,
            "message": f"Preset '{preset_name}' loaded"
        }

    except Exception as e:
        log('[ERROR]', f"Failed to load YOLO preset: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/api/settings/z21/test")
async def test_z21_connection(request: dict):
    """
    Test Z21 connection with provided IP/port

    Request body:
        {"host": "192.168.1.111", "port": 21105}

    Returns connection status
    """
    try:
        import sys
        from pathlib import Path

        # Add scripts directory to path for z21.py import
        scripts_dir = Path(__file__).parent.parent.parent / 'scripts'
        sys.path.insert(0, str(scripts_dir))

        from z21 import Z21

        host = request.get("host", "192.168.1.111")
        port = request.get("port", 21105)

        log('[SETTINGS]', f"Testing Z21 connection: {host}:{port}")

        # Try to connect and get status
        z21 = Z21(ip=host, port=port, verbose=False)
        status = z21.get_status()

        if status:
            log('[SETTINGS]', f"Z21 connection test: SUCCESS ({host}:{port})")
            return {
                "status": "success",
                "message": f"Connected to Z21 at {host}:{port}",
                "details": {
                    "track_power": not status.get('track_power_off', False),
                    "emergency_stop": status.get('emergency_stop', False)
                }
            }
        else:
            log('[SETTINGS]', f"Z21 connection test: FAILED ({host}:{port})")
            return {
                "status": "error",
                "message": f"Failed to connect to Z21 at {host}:{port}"
            }

    except Exception as e:
        log('[ERROR]', f"Z21 connection test failed: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/api/settings/camera/test")
async def test_camera_stream(request: dict):
    """
    Test camera RTSP stream with provided settings

    Request body:
        {
            "ip": "192.168.1.4",
            "port": 554,
            "stream": "stream2",
            "username": "user",
            "password": "pass"
        }

    Returns stream test result (can open, resolution)
    """
    try:
        import cv2

        ip = request.get("ip", "192.168.1.4")
        port = request.get("port", 554)
        stream = request.get("stream", "stream2")
        username = request.get("username", "")
        password = request.get("password", "")

        if not username or not password:
            return {"status": "error", "message": "Camera credentials required"}

        rtsp_url = f"rtsp://{username}:{password}@{ip}:{port}/{stream}"

        log('[SETTINGS]', f"Testing camera stream: {ip}:{port}/{stream}")

        # Try to open stream
        cap = cv2.VideoCapture(rtsp_url)

        if not cap.isOpened():
            log('[SETTINGS]', f"Camera stream test: FAILED (cannot open)")
            return {"status": "error", "message": "Failed to open camera stream"}

        # Read one frame to verify
        ret, frame = cap.read()
        cap.release()

        if ret and frame is not None:
            height, width = frame.shape[:2]
            log('[SETTINGS]', f"Camera stream test: SUCCESS ({width}x{height})")
            return {
                "status": "success",
                "message": f"Camera stream OK: {width}x{height}",
                "details": {
                    "resolution": {"width": width, "height": height}
                }
            }
        else:
            log('[SETTINGS]', f"Camera stream test: FAILED (cannot read frame)")
            return {"status": "error", "message": "Failed to read frame from camera"}

    except Exception as e:
        log('[ERROR]', f"Camera stream test failed: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/api/consists")
async def get_consists(
    consist_data: Dict = Depends(get_consist_data),
    z21_manager: Z21Manager = Depends(get_z21_manager)
):
    """Get all consists configuration and available gates"""
    # Load config to get gates
    config = load_config()

    consists_result = {}
    for address, data in consist_data.items():
        state = z21_manager.get_consist_state(address) if z21_manager else {}
        consists_result[address] = build_consist_response(address, data, state)

    # Get consists configuration
    consists_config = config.get("consists", {})

    # Extract reference_locos from consists for backward compatibility
    reference_locos = {}
    for consist_addr, consist_info in consists_config.items():
        reference_locos[consist_addr] = {
            'reference': consist_info.get('reference_loco'),
            'adjust': consist_info.get('adjust_loco')
        }

    return {
        "consists": consists_result,
        "gates": config.get("gates", []),
        "tracking_assignments": consists_config,  # For frontend compatibility (renamed but same structure)
        "reference_locos": reference_locos
    }


@router.post("/api/consists")
async def create_consist(
    request: dict,
    z21_manager: Z21Manager = Depends(get_z21_manager)
):
    """Create a new consist in config.json"""
    # Import dependencies module to access set functions
    import dependencies

    try:
        consist_address = str(request.get("address"))
        lead_address = request.get("lead_address")
        rear_address = request.get("rear_address")
        gate_ids = request.get("gate_ids", [])
        gate_assignment = request.get("gate_assignment")  # None = symmetric, object = asymmetric
        reference_loco = request.get("reference_loco", "rear")  # "lead" or "rear"
        virtual_mode = request.get("virtual_mode", True)  # Default: Virtual Mode (safe)

        if not consist_address or not lead_address or not rear_address:
            return {"success": False, "error": "Missing required fields"}

        # Load config
        config = load_config()

        # Check if consist already exists
        if consist_address in config.get("consists", {}):
            return {"success": False, "error": f"Consist {consist_address} already exists"}

        # Add to consists
        if "consists" not in config:
            config["consists"] = {}

        config["consists"][consist_address] = {
            "name": f"Consist {consist_address}",
            "lead_address": lead_address,
            "rear_address": rear_address,
            "reference_loco": rear_address if reference_loco == "rear" else lead_address,
            "adjust_loco": lead_address if reference_loco == "rear" else rear_address,
            "gate_ids": gate_ids,
            "gate_assignment": gate_assignment,  # From request: null = symmetric, object = asymmetric
            "virtual_mode": virtual_mode,
            "auto_compensation_enabled": False,
            "notes": ""
        }

        # Save config
        save_config(config)

        # Write CV19 based on mode
        if z21_manager and z21_manager.z21:
            consist_addr_int = int(consist_address)

            if virtual_mode:
                # Virtual Mode: write CV19=0 (disable hardware consist)
                log('[CV]', f"Creating consist {consist_address} in Virtual Mode - writing CV19=0")
                cv_value = 0
            else:
                # DCC Mode: write CV19=consist_address (enable hardware consist)
                log('[CV]', f"Creating consist {consist_address} in DCC Mode - writing CV19={consist_addr_int}")
                cv_value = consist_addr_int

            success_lead = z21_manager.z21.write_cv_ops_mode(lead_address, 19, cv_value)
            success_rear = z21_manager.z21.write_cv_ops_mode(rear_address, 19, cv_value)

            if not (success_lead and success_rear):
                mode_str = "Virtual" if virtual_mode else "DCC"
                return {"success": False, "error": f"Consist created in config but failed to write CV19 to locomotives ({mode_str} Mode)"}

        mode_str = "Virtual" if virtual_mode else "DCC"

        # Reload consist_data from updated config before broadcasting
        consist_data = load_consists_from_config(CONFIG_PATH)
        # Update global state
        dependencies._consist_data = consist_data

        # Broadcast updated state to all connected clients (refresh dropdowns)
        await broadcast_initial_state()

        return {"success": True, "message": f"Consist {consist_address} created in {mode_str} Mode (CV19 written)"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@router.put("/api/consists/{address}")
async def update_consist(
    address: str,
    request: dict,
    z21_manager: Z21Manager = Depends(get_z21_manager)
):
    """Update an existing consist in config.json"""
    import dependencies

    try:
        # Load config
        config = load_config()

        # Check if consist exists
        if address not in config.get("consists", {}):
            return {"success": False, "error": f"Consist {address} not found"}

        # Update consists fields
        consist = config["consists"][address]
        old_virtual_mode = consist.get("virtual_mode", True)

        if "lead_address" in request:
            consist["lead_address"] = request["lead_address"]
        if "rear_address" in request:
            consist["rear_address"] = request["rear_address"]
        if "gate_ids" in request:
            consist["gate_ids"] = request["gate_ids"]
        if "gate_assignment" in request:
            consist["gate_assignment"] = request["gate_assignment"]  # null = symmetric, object = asymmetric

        # Handle virtual_mode change (if present in request)
        virtual_mode_changed = False
        new_virtual_mode = old_virtual_mode
        if "virtual_mode" in request:
            new_virtual_mode = request["virtual_mode"]
            if new_virtual_mode != old_virtual_mode:
                virtual_mode_changed = True
                consist["virtual_mode"] = new_virtual_mode

        # Update reference if reference_loco specified
        if "reference_loco" in request:
            lead_address = consist["lead_address"]
            rear_address = consist["rear_address"]

            if request["reference_loco"] == "lead":
                consist["reference_loco"] = lead_address
                consist["adjust_loco"] = rear_address
            else:  # rear
                consist["reference_loco"] = rear_address
                consist["adjust_loco"] = lead_address

        # Save config
        save_config(config)

        # If virtual_mode changed, write CV19 accordingly
        if virtual_mode_changed and z21_manager and z21_manager.z21:
            consist_addr_int = int(address)
            lead_address = consist["lead_address"]
            rear_address = consist["rear_address"]

            if new_virtual_mode:
                # Switched to Virtual Mode: write CV19=0
                log('[CV]', f"Switching consist {address} to Virtual Mode - writing CV19=0")
                cv_value = 0
            else:
                # Switched to DCC Mode: write CV19=consist_address
                log('[CV]', f"Switching consist {address} to DCC Mode - writing CV19={consist_addr_int}")
                cv_value = consist_addr_int

            success_lead = z21_manager.z21.write_cv_ops_mode(lead_address, 19, cv_value)
            success_rear = z21_manager.z21.write_cv_ops_mode(rear_address, 19, cv_value)

            if not (success_lead and success_rear):
                mode_str = "Virtual" if new_virtual_mode else "DCC"
                return {"success": False, "error": f"Consist updated in config but failed to write CV19 ({mode_str} Mode)"}

            mode_str = "Virtual" if new_virtual_mode else "DCC"

            # Reload consist_data from updated config before broadcasting
            consist_data = load_consists_from_config(CONFIG_PATH)
            dependencies._consist_data = consist_data

            # Broadcast updated state to all connected clients (refresh dropdowns)
            await broadcast_initial_state()

            return {"success": True, "message": f"Consist {address} updated and switched to {mode_str} Mode (CV19 written)"}

        # Reload consist_data from updated config before broadcasting
        consist_data = load_consists_from_config(CONFIG_PATH)
        dependencies._consist_data = consist_data

        # Broadcast updated state to all connected clients (refresh dropdowns)
        await broadcast_initial_state()

        return {"success": True, "message": f"Consist {address} updated"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/api/consists/{address}")
async def delete_consist(
    address: str,
    z21_manager: Z21Manager = Depends(get_z21_manager)
):
    """
    Delete a consist from config.json
    If consist is in DCC mode (virtual_mode=false), writes CV19=0 first
    """
    import dependencies

    try:
        # Load config
        config = load_config()

        # Check if consist exists
        if address not in config.get("consists", {}):
            return {"success": False, "error": f"Consist {address} not found"}

        consist_config = config["consists"][address]

        # If consist is in DCC mode (virtual_mode=false), disable consist on locomotives first
        virtual_mode = consist_config.get("virtual_mode", False)
        if not virtual_mode and z21_manager:
            # Write CV19=0 to both locomotives to disable DCC consist
            log('[WARN]', f"Consist {address} is in DCC mode - writing CV19=0 to disable consist on locomotives")
            consist_address_int = int(address)
            # Use enable_virtual_mode() which writes CV19=0 (disables consist)
            # disable_virtual_mode() would write CV19=consist_address (restores consist)
            z21_manager.enable_virtual_mode(consist_address_int)

        # Delete from consists
        del config["consists"][address]

        # Save config
        save_config(config)

        # Reload consist_data from updated config before broadcasting
        consist_data = load_consists_from_config(CONFIG_PATH)
        dependencies._consist_data = consist_data

        # Broadcast updated state to all connected clients (refresh dropdowns)
        await broadcast_initial_state()

        return {"success": True, "message": f"Consist {address} deleted"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/api/config/tracking")
async def get_tracking_config():
    """Get tracking configuration (idle timeout + consist definitions + timing thresholds for dynamic analytics)"""
    config = load_config()
    idle_timeout = config.get('tracking', {}).get('idle_timeout_seconds', 10)
    timing_thresholds = config.get('tracking', {}).get('timing_thresholds', {
        'warning': 1.0,
        'critical': 1.5,
        'max_delta_t': 10.0
    })
    consists = config.get('consists', {})

    # Build consist definitions (id → name, addresses)
    consist_defs = {}
    for cid, cdata in consists.items():
        consist_id = int(cid)
        consist_defs[consist_id] = {
            "name": cdata.get('name', f'Consist {consist_id}'),
            "lead_address": cdata.get('lead_address'),
            "rear_address": cdata.get('rear_address'),
            "addresses": [cdata.get('lead_address'), cdata.get('rear_address')]
        }

    return {
        "idle_timeout_seconds": idle_timeout,
        "timing_thresholds": timing_thresholds,
        "consists": consist_defs
    }


@router.get("/api/config/analytics")
async def get_analytics_config():
    """Get analytics configuration (chart optimization parameters)"""
    config = load_config()
    max_chart_events = config.get('analytics', {}).get('max_chart_events', 500)

    return {
        "max_chart_events": max_chart_events
    }


@router.get("/api/gates")
async def get_gates():
    """Get current gate configuration"""
    return ConfigManager.get_gates()


@router.post("/api/save-gates")
async def save_gates(gates: List[Dict[str, Any]]):
    """Save gate configuration from web editor (press 'E' in UI)"""
    try:
        # Load current config
        config = load_config()

        # Validate gates format
        for gate in gates:
            required_fields = ['id', 'name', 'center', 'width', 'height', 'angle', 'color']
            if not all(field in gate for field in required_fields):
                return {
                    "status": "error",
                    "message": f"Invalid gate format, missing required fields"
                }

        # Create backup before saving
        import shutil
        from datetime import datetime

        config_path = get_config_path()  # Use centralized config path
        backup_name = "config.json.backup"
        backup_path = config_path.parent / backup_name

        shutil.copy(config_path, backup_path)
        log('[INIT]', f"Config backup created: {backup_name}")

        # Round all numeric values to integers (OpenCV requires int for coordinates)
        for gate in gates:
            gate['center'] = [int(round(gate['center'][0])), int(round(gate['center'][1]))]
            gate['width'] = int(round(gate['width']))
            gate['height'] = int(round(gate['height']))
            gate['angle'] = int(round(gate['angle']))
            gate['color'] = [int(round(c)) for c in gate['color']]

        # Update gates in config
        config['gates'] = gates

        # Save config (with inline array formatting)
        save_config(config)

        log('[INIT]', f"Gates configuration saved ({len(gates)} gates)")
        return {
            "status": "success",
            "message": f"Saved {len(gates)} gates (backup: {backup_name})"
        }
    except Exception as e:
        log('[WARN]', f"Error saving gates: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
