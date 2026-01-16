"""
FastAPI backend per z21-Terminal Web Dashboard
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any, Optional
import json
import asyncio
import time
import cv2
import numpy as np
from contextlib import asynccontextmanager
from pathlib import Path

from z21_manager import Z21Manager
from roster_loader import load_consist_with_functions, load_all_locomotives, load_consists_from_config
from tracking_manager import TrackingManager
import video_feed as video_feed_module
from video_feed import generate_video_frames
from config_loader import load_config, save_config, get_config_path
from log_colors import log, colorize_status, enable_auto_coloring
from services.broadcast import (
    init_broadcast_service,
    update_z21_status,
    update_track_power,
    broadcast_z21_status,
    broadcast_controllers_update,
    broadcast_state_update,
    broadcast_initial_state,
    build_consist_response
)
from services.config_manager import ConfigManager
import dependencies
from routers import analytics, config, roster, status, speed_table
from routers.roster import get_full_roster
from websocket_handlers.ws_control import handle_ws_control
from websocket_handlers.ws_tracking import handle_ws_tracking

# Enable automatic coloring of error/warning messages in all print() output
enable_auto_coloring()

# Default constants (single source of truth)
DEFAULT_TIMING_THRESHOLDS = {'normal': 1.0, 'warning': 1.5}
DEFAULT_CONTROLLER = {'id': None, 'type': None, 'address': None}

# Configuration paths (all in project root)
CONFIG_PATH = get_config_path()  # Centralized config path

# Global instances
z21_manager: Z21Manager = None
tracking_manager: TrackingManager = None
connected_clients: List[WebSocket] = []
consist_data: Dict[int, Dict[str, Any]] = {}
locomotive_data: Dict[int, Dict[str, Any]] = {}
controllers_config: List[Dict[str, Any]] = []  # Shared controller configuration
timing_thresholds: Dict[str, float] = DEFAULT_TIMING_THRESHOLDS.copy()  # Dynamic thresholds from config.json
reference_locos: Dict[str, Dict[str, int]] = {}  # Reference loco strategy from config.json
tracked_consist_ids: List[int] = []  # Consist IDs with gate tracking configured (from tracking_assignments)
loco_start_times: Dict[int, float] = {}  # Track locomotive movement start times (address -> timestamp)


polling_task = None
health_check_task = None
last_track_power_state = True
z21_online = False
z21_consecutive_failures = 0  # Track consecutive health check failures (requires 2 before marking offline)
debug_enabled = False  # Debug mode flag (loaded from config.json)


async def poll_track_power():
    """Background task to monitor Z21 track power state"""
    global last_track_power_state

    log('[INIT]', f"Starting track power polling (500ms interval)")

    while True:
        await asyncio.sleep(0.5)  # Poll every 500ms

        if not z21_manager or not z21_manager.z21:
            continue

        try:
            # Get current track power status from Z21
            status = z21_manager.z21.get_status()

            if status:
                current_power = status.get('track_power_on', True)

                # If power state changed, broadcast to all clients
                if current_power != last_track_power_state:
                    log('[INIT]', f"Track power changed: {'ON' if current_power else 'OFF'}")
                    last_track_power_state = current_power
                    update_track_power(current_power)

                    # Update all consist states
                    for address in consist_data.keys():
                        if address in z21_manager.consist_state:
                            z21_manager.consist_state[address]['power'] = current_power
                            await broadcast_state_update(address)

        except Exception as e:
            print(f"Error polling track power: {e}")


async def health_check_z21():
    """Background task to monitor Z21 connection health (requires 2 consecutive failures)"""
    global z21_online, last_track_power_state, z21_consecutive_failures

    log('[INIT]', f"Starting Z21 health check (5s interval, 2 failures grace period)")

    while True:
        await asyncio.sleep(5)  # Check every 5 seconds

        if not z21_manager or not z21_manager.z21:
            continue

        previous_state = z21_online

        try:
            # Try to get status from Z21 (acts as ping)
            status = z21_manager.z21.get_status()

            if status is not None:
                # Success - reset failure counter and mark online
                z21_consecutive_failures = 0
                z21_online = True
                update_z21_status(True)
            else:
                # Failed - increment failure counter
                z21_consecutive_failures += 1
                if z21_consecutive_failures >= 2:
                    z21_online = False
                    update_z21_status(False)
                elif z21_consecutive_failures == 1:
                    log('[WARN]', f"Z21 health check failed (1/2) - grace period")

        except Exception as e:
            # Exception - increment failure counter
            z21_consecutive_failures += 1
            if z21_consecutive_failures >= 2:
                z21_online = False
                update_z21_status(False)
                if previous_state:  # Only log when transitioning to offline
                    log('[WARN]', f"Z21 connection lost after 2 failures: {e}")
            elif z21_consecutive_failures == 1:
                log('[WARN]', f"Z21 health check exception (1/2) - grace period: {e}")

        # If state changed, broadcast to all clients
        if z21_online != previous_state:
            status_text = "ONLINE" if z21_online else "OFFLINE"
            prefix = '[OK]' if z21_online else '[FAIL]'
            log(prefix, f"Z21 status changed: {status_text}")

            # If Z21 went offline, set track power to OFF
            if not z21_online:
                log('[INIT]', f"Setting track power to OFF (Z21 offline)")
                last_track_power_state = False
                update_track_power(False)
                # Update all consist states
                for address in consist_data.keys():
                    if address in z21_manager.consist_state:
                        z21_manager.consist_state[address]['power'] = False
                        await broadcast_state_update(address)

            await broadcast_z21_status()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global z21_manager, tracking_manager, consist_data, locomotive_data, polling_task, health_check_task, last_track_power_state, z21_online, controllers_config, timing_thresholds, reference_locos, tracked_consist_ids, debug_enabled

    # Filter out repetitive telemetry GET logs (called every 5s)
    import logging
    class TelemetryFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return '/api/z21/telemetry' not in record.getMessage()
    logging.getLogger("uvicorn.access").addFilter(TelemetryFilter())

    log('[INIT]', f"z21-Terminal Backend Starting...")

    # Load debug mode configuration FIRST
    debug_enabled = ConfigManager.get_debug_enabled()

    # Load timing thresholds from config.json
    log('[INIT]', f"Loading timing thresholds from config.json...")
    try:
        timing_thresholds = ConfigManager.get_timing_thresholds()
        if debug_enabled:
            log('[INIT]', f"Timing thresholds: SYNCED < {timing_thresholds['normal']}s, WARNING < {timing_thresholds['warning']}s")
    except FileNotFoundError:
        log('[WARN]', f"config.json not found, using default thresholds ({DEFAULT_TIMING_THRESHOLDS['normal']}s/{DEFAULT_TIMING_THRESHOLDS['warning']}s)")
        timing_thresholds = DEFAULT_TIMING_THRESHOLDS.copy()
    except Exception as e:
        log('[WARN]', f"Error loading config.json: {e}, using defaults")
        timing_thresholds = DEFAULT_TIMING_THRESHOLDS.copy()

    # Load reference loco configuration (from consists)
    log('[INIT]', f"Loading reference loco configuration...")
    try:
        reference_locos = ConfigManager.get_reference_locos()
        if debug_enabled:
            log('[INIT]', f"Reference locos: {len(reference_locos)} consists configured")
            for consist_addr, ref_config in reference_locos.items():
                print(f"    Consist {consist_addr}: reference={ref_config['reference']}, adjust={ref_config['adjust']}")
    except Exception as e:
        log('[WARN]', f"Error loading reference locos: {e}")
        reference_locos = {}

    # Load tracked consist IDs (only consists with gate tracking configured)
    log('[INIT]', f"Loading tracked consist IDs...")
    try:
        tracked_consist_ids = ConfigManager.get_tracked_consist_ids()
        if debug_enabled:
            log('[INIT]', f"Tracked consists: {tracked_consist_ids}")
    except Exception as e:
        log('[WARN]', f"Error loading tracked consists: {e}")
        tracked_consist_ids = []

    # Load consist configuration
    # Priority: config.json consists → JMRI (bootstrap only)
    try:
        config = load_config()
        consists = config.get('consists', {})
    except Exception:
        consists = {}

    if consists:
        # Load from config.json (source of truth)
        log('[INIT]', f"Loading consists from config.json (source of truth)...")
        consist_data = load_consists_from_config(CONFIG_PATH)
        if debug_enabled and consist_data:
            for addr, data in consist_data.items():
                locomotives = data.get('locomotives', [])
                if locomotives:
                    names = ' + '.join([loco['name'] for loco in locomotives])
                    log('[INIT]', f"Consist {addr}: {names} ({len(data['functions'])} functions)")
    else:
        # Bootstrap from JMRI (one-time only, then save to config.json)
        log('[INIT]', f"Bootstrapping consists from JMRI (first run)...")
        consist_data = load_consist_with_functions()

        if not consist_data:
            log('[WARN]', f"Warning: No consists loaded from JMRI")
        else:
            if debug_enabled:
                for addr, data in consist_data.items():
                    locomotives = data.get('locomotives', [])
                    if locomotives:
                        names = ' + '.join([loco['name'] for loco in locomotives])
                        log('[INIT]', f"Consist {addr}: {names} ({len(data['functions'])} functions)")
                    else:
                        log('[INIT]', f"Consist {addr}: (empty) ({len(data['functions'])} functions)")

            # Save to config.json for future use
            log('[INIT]', f"Saving consists to config.json for future use...")
            # Reload config to ensure we have latest version
            try:
                config = load_config()
            except Exception:
                config = {}

            if 'consists' not in config:
                config['consists'] = {}

            for consist_addr, consist_info in consist_data.items():
                locomotives = consist_info.get('locomotives', [])
                if len(locomotives) >= 2:
                    config['consists'][str(consist_addr)] = {
                        'name': f"Consist {consist_addr}",
                        'lead_address': locomotives[0]['address'],
                        'rear_address': locomotives[1]['address'],
                        'gate_ids': [],  # Empty by default, user can configure in UI
                        'virtual_mode': False,
                        'auto_compensation_enabled': False,
                        'notes': ''
                    }

            # Save updated config
            save_config(config)
            log('[INIT]', f"Saved {len(consist_data)} consists to config.json")

    # Load all locomotives from JMRI
    log('[INIT]', f"Loading all locomotives from JMRI...")
    locomotive_data = load_all_locomotives()

    if not locomotive_data:
        log('[WARN]', f"Warning: No locomotives loaded from JMRI")
    else:
        if debug_enabled:
            log('[INIT]', f"Loaded {len(locomotive_data)} locomotives")
            for addr, data in locomotive_data.items():
                in_consist = f" (in consist {data['in_consist']})" if data['in_consist'] else ""
                print(f"    Loco {addr}: {data['name']}{in_consist}")

    # Initialize default controllers configuration
    # Try to pre-select consist 10 and 11 if they exist, otherwise leave empty
    log('[INIT]', f"Initializing default controllers...")
    controller1 = {'id': 1, 'type': 'consist', 'address': 10} if 10 in consist_data else {**DEFAULT_CONTROLLER, 'id': 1}
    controller2 = {'id': 2, 'type': 'consist', 'address': 11} if 11 in consist_data else {**DEFAULT_CONTROLLER, 'id': 2}
    controllers_config = [controller1, controller2]

    if debug_enabled:
        if controller1['type'] and controller2['type']:
            log('[INIT]', f"Initialized 2 controllers (consist {controller1['address']} + consist {controller2['address']})")
        elif controller1['type']:
            log('[INIT]', f"Initialized 2 controllers (consist {controller1['address']} + empty)")
        elif controller2['type']:
            log('[INIT]', f"Initialized 2 controllers (empty + consist {controller2['address']})")
        else:
            log('[INIT]', f"Initialized 2 empty controllers")

    # Initialize Z21 Manager
    log('[INIT]', f"Connecting to Z21...")
    z21_manager = Z21Manager(z21_ip='192.168.1.111', verbose=False, reference_locos=reference_locos, timing_thresholds=timing_thresholds, debug_enabled=debug_enabled, config_path=CONFIG_PATH)

    if z21_manager.connect():
        if debug_enabled:
            log('[INIT]', f"Connected to Z21 at 192.168.1.111")

        # Initialize consist states in Z21 Manager
        for address, data in consist_data.items():
            z21_manager.initialize_consist(address, data)
            if debug_enabled:
                log('[INIT]', f"Initialized consist {address}")

        # Initialize locomotive states in Z21 Manager
        # Initialize ALL locomotives (standalone + those in consist)
        # Even locos in consist need state tracking for individual function control
        for address, data in locomotive_data.items():
            z21_manager.initialize_consist(address, {
                'locomotives': [{'address': address, 'name': data['name']}],  # Single loco array
                'functions': data['functions']
            })
            if debug_enabled:
                in_consist_note = f" (in consist {data['in_consist']})" if data.get('in_consist') else ""
                log('[INIT]', f"Initialized locomotive {address}{in_consist_note}")

        # Initialize compensation variables for existing consists (backwards compatibility)
        for consist_addr, consist in z21_manager.consist_state.items():
            if 'compensation_accumulated' not in consist:
                consist['compensation_accumulated'] = 0
            if 'decay_applied' not in consist:
                consist['decay_applied'] = False
            # auto_compensation_enabled is now handled in z21_manager._load_persisted_state()

        # Get initial track power state (with error handling for unreachable Z21)
        try:
            status = z21_manager.z21.get_status()
            if status:
                last_track_power_state = not status.get('track_power_off', False)
                if debug_enabled:
                    log('[INIT]', f"Initial track power: {'ON' if last_track_power_state else 'OFF'}")
                z21_online = True
                log('[OK]', 'Z21 connection: ONLINE')
            else:
                # Z21 not responding - force track power OFF
                last_track_power_state = False
                z21_online = False
                log('[FAIL]', 'Z21 connection: OFFLINE (track power: OFF)')
        except (OSError, ConnectionError, TimeoutError) as e:
            log('[WARN]', f"Z21 not responding (will retry in background): {e}")
            # Z21 unreachable - force track power OFF
            last_track_power_state = False
            z21_online = False
            log('[FAIL]', 'Z21 connection: OFFLINE (track power: OFF)')
            # Backend continues startup - health check will retry connection

        # If Z21 is offline at startup, force all consist states to power: False
        if not z21_online:
            for address in consist_data.keys():
                if address in z21_manager.consist_state:
                    z21_manager.consist_state[address]['power'] = False
            if debug_enabled:
                log('[INIT]', f"Set all consists power to OFF (Z21 offline at startup)")

        # Start background polling tasks
        polling_task = asyncio.create_task(poll_track_power())
        health_check_task = asyncio.create_task(health_check_z21())

        # Initialize Tracking Manager
        log('[INIT]', f"Initializing Tracking Manager...")
        tracking_manager = TrackingManager(z21_manager, connected_clients)
        if debug_enabled:
            log('[INIT]', f"Tracking Manager ready")

    else:
        log('[FAIL]', "Failed to connect to Z21")
        z21_online = False

    # Initialize broadcast service with global references
    init_broadcast_service(
        clients=connected_clients,
        z21_mgr=z21_manager,
        consist_dict=consist_data,
        locomotive_dict=locomotive_data,
        controllers=controllers_config
    )
    # Set initial runtime values
    update_z21_status(z21_online)
    update_track_power(last_track_power_state)

    # Initialize dependency injection system for routers
    dependencies.init_dependencies(
        z21_mgr=z21_manager,
        tracking_mgr=tracking_manager,
        clients=connected_clients,
        consists=consist_data,
        locomotives=locomotive_data,
        controllers=controllers_config,
        thresholds=timing_thresholds,
        ref_locos=reference_locos,
        tracked_ids=tracked_consist_ids,
        debug=debug_enabled
    )

    log('[INIT]', f"Backend ready!")
    log('[INIT]', f"WebSocket endpoint: ws://localhost:8000/ws")
    log('[INIT]', f"WebSocket tracking endpoint: ws://localhost:8000/ws/tracking")

    yield

    # Shutdown
    log('[SHUT]', f"Shutting down...")
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    if health_check_task:
        health_check_task.cancel()
        try:
            await health_check_task
        except asyncio.CancelledError:
            pass
    if tracking_manager:
        await tracking_manager.shutdown()
    if z21_manager:
        z21_manager.disconnect()
    log('[INIT]', f"Cleanup complete")


# FastAPI app
app = FastAPI(
    title="z21-Terminal Backend",
    description="WebSocket API for DCC locomotive control via Z21",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analytics.router)
app.include_router(analytics.router_no_prefix)  # For endpoints outside /api/analytics prefix
app.include_router(config.router)
app.include_router(roster.router)
app.include_router(status.router)
app.include_router(speed_table.router)


async def reload_roster_data():
    """Reload roster and consists from config.json (and locomotives from JMRI)"""
    global consist_data, locomotive_data

    log('[INIT]', f"Reloading roster...")

    # Load config to check consists
    try:
        config = load_config()
    except Exception as e:
        log('[WARN]', f"Error loading config: {e}")
        return False

    # Load consists from config.json (source of truth)
    consists = config.get('consists', {})

    if consists:
        log('[INIT]', f"Loading consists from config.json...")
        consist_data = load_consists_from_config(CONFIG_PATH)
        if debug_enabled and consist_data:
            log('[INIT]', f"Loaded {len(consist_data)} consists from config.json")
    else:
        log('[WARN]', f"No consists in config.json, trying JMRI bootstrap...")
        consist_data = load_consist_with_functions()
        if debug_enabled and consist_data:
            log('[INIT]', f"Loaded {len(consist_data)} consists from JMRI")

    # Always load locomotives from JMRI (names, functions)
    log('[INIT]', f"Loading locomotives from JMRI...")
    locomotive_data = load_all_locomotives()

    if not locomotive_data:
        log('[WARN]', f"Warning: No locomotives loaded from JMRI")
    else:
        if debug_enabled:
            log('[INIT]', f"Loaded {len(locomotive_data)} locomotives")

    if not z21_manager or not z21_manager.z21:
        log('[FAIL]', "Z21 not connected, cannot reinitialize")
        return False

    # Re-initialize consist states
    for address, data in consist_data.items():
        z21_manager.initialize_consist(address, data)
        if debug_enabled:
            log('[INIT]', f"Re-initialized consist {address}")

    # Re-initialize locomotive states
    for address, data in locomotive_data.items():
        z21_manager.initialize_consist(address, {
            'locomotives': [{'address': address, 'name': data['name']}],  # Single loco array
            'functions': data['functions']
        })
        if debug_enabled:
            in_consist_note = f" (in consist {data['in_consist']})" if data.get('in_consist') else ""
            log('[INIT]', f"Re-initialized locomotive {address}{in_consist_note}")

    # Broadcast new state to all connected clients
    await broadcast_initial_state()
    if debug_enabled:
        log('[INIT]', f"Broadcasted new state to all clients")

    log('[INIT]', f"Roster reload complete!\n")
    return True


@app.post("/api/restart-daemon")
async def restart_tracking_daemon():
    """Restart tracking daemon to reload config changes"""
    try:
        global tracking_manager
        if tracking_manager:
            # Stop current daemon
            await tracking_manager.stop()
            # Start with reloaded config
            await tracking_manager.start()
            return {"success": True, "message": "Tracking daemon restarted"}
        else:
            return {"success": False, "error": "Tracking manager not initialized"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/toggle-panel")
async def toggle_panel():
    """Toggle dT panel visibility in video feed (press 'P' in UI)"""
    video_feed_module.SHOW_DELTA_T_PANEL = not video_feed_module.SHOW_DELTA_T_PANEL
    status = "visible" if video_feed_module.SHOW_DELTA_T_PANEL else "hidden"
    log('[WS]', f"dT panel toggled: {status}")
    return {
        "status": "success",
        "panel_visible": video_feed_module.SHOW_DELTA_T_PANEL
    }


@app.get("/api/debug-status")
async def get_debug_status():
    """Get current debug overlay status (no toggle)"""
    return {
        "status": "success",
        "debug_visible": video_feed_module.SHOW_DEBUG_OVERLAY
    }


@app.post("/api/toggle-debug")
async def toggle_debug():
    """Toggle debug overlay in video feed (press 'B' in UI)"""
    video_feed_module.SHOW_DEBUG_OVERLAY = not video_feed_module.SHOW_DEBUG_OVERLAY
    status = "visible" if video_feed_module.SHOW_DEBUG_OVERLAY else "hidden"
    log('[WS]', f"Debug overlay toggled: {status}")
    return {
        "status": "success",
        "debug_visible": video_feed_module.SHOW_DEBUG_OVERLAY
    }


@app.post("/api/toggle-cv-profile-mode")
async def toggle_cv_profile_mode():
    """Toggle CV profile mode between 'normal' and 'testing' for ALL locomotives (hotkey T in UI)"""
    success, new_mode, message = z21_manager.toggle_cv_profile_mode()
    return {"status": "success" if success else "error", "mode": new_mode, "message": message}


@app.get("/api/cv-profile-mode")
async def get_cv_profile_mode():
    """Get current CV profile mode ('normal' or 'testing')"""
    config = load_config()
    return {"mode": config.get('cv_profile_mode', 'normal')}


@app.get("/api/video_feed")
async def video_feed():
    """
    MJPEG video stream with gate overlay and tracking info

    Returns:
        StreamingResponse: MJPEG stream
    """
    # Cache to preserve last valid delta_t for video feed (when locos stop)
    _last_valid_delta_t = {}  # consist_id → last valid tracking data dict

    def get_tracking_data():
        """
        Callback to get latest tracking data for video feed overlay - MULTI-CONSIST

        Reads data from consist_state (populated by tracking_daemon WebSocket).
        Single source of truth: tracking_daemon calculates delta_t, status, time_str.

        Preserves last valid delta_t when locos stop (matches React panel behavior).
        """
        nonlocal _last_valid_delta_t

        if not z21_manager:
            return {}

        all_tracking_data = {}

        # Loop ONLY over tracked consists (those with gate_ids configured)
        for consist_id in tracked_consist_ids:
            if consist_id not in z21_manager.consist_state:
                continue

            state = z21_manager.consist_state[consist_id]
            delta_t = state.get('delta_t')

            if delta_t is not None:
                # Valid delta_t: read from consist_state (no calculations)
                tracking_data = {
                    'consist_address': consist_id,
                    'delta_t': delta_t,
                    'status': state.get('delta_t_status', 'UNKNOWN'),
                    'timestamp': state.get('delta_t_timestamp'),
                    'time_str': state.get('delta_t_time_str', '')
                }
                all_tracking_data[consist_id] = tracking_data
                # Cache for when locos stop (preserve last value)
                _last_valid_delta_t[consist_id] = tracking_data.copy()
            else:
                # delta_t is None (locos stopped or no tracking yet)
                # Use cached value to preserve display (matches React behavior)
                if consist_id in _last_valid_delta_t:
                    all_tracking_data[consist_id] = _last_valid_delta_t[consist_id]
                else:
                    # No cache yet (first run): show placeholder panel for this consist
                    all_tracking_data[consist_id] = {
                        'consist_address': consist_id,
                        'delta_t': None,
                        'status': None,
                        'timestamp': None,
                        'time_str': ''
                    }

        return all_tracking_data

    def get_yolo_detections():
        """Callback to get latest YOLO detections for locomotive markers"""
        detections = dependencies.get_yolo_detections()
        return detections.get('detections', [])

    return StreamingResponse(
        generate_video_frames(
            tracking_data_callback=get_tracking_data,
            yolo_detections_callback=get_yolo_detections
        ),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time control (delegates to ws_control handler)"""
    await handle_ws_control(
        websocket=websocket,
        connected_clients=connected_clients,
        consist_data=consist_data,
        locomotive_data=locomotive_data,
        z21_manager=z21_manager,
        tracking_manager=tracking_manager,
        controllers_config=controllers_config,
        last_track_power_state=last_track_power_state,
        z21_online=z21_online,
        debug_enabled=debug_enabled,
        loco_start_times=loco_start_times
    )


@app.websocket("/ws/tracking")
async def websocket_tracking_endpoint(websocket: WebSocket):
    """WebSocket endpoint for tracking daemon connection (delegates to ws_tracking handler)"""
    await handle_ws_tracking(
        websocket=websocket,
        z21_manager=z21_manager,
        consist_data=consist_data,
        connected_clients=connected_clients,
        timing_thresholds=timing_thresholds
    )


# ========================================
# Conditional Frontend Production Serving
# ========================================
# Serve frontend production build (web/dist/) if it exists.
# Development mode: dist/ doesn't exist → use Vite dev server (port 5173)
# Production mode: dist/ exists → FastAPI serves everything on port 8000

frontend_dist = Path(__file__).parent.parent / "web" / "dist"
if frontend_dist.exists() and frontend_dist.is_dir():
    # Production mode: serve static files
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    log('[INIT]', f"Production mode: Serving frontend from {frontend_dist}")
    print(f"   Access dashboard at: http://localhost:8000")
else:
    log('[WARN]', f"Development mode: Frontend dist not found")
    print(f"   Expected: {frontend_dist}")
    print(f"   Use Vite dev server: cd web && npm run dev")
    print(f"   Access dashboard at: http://localhost:5173")


if __name__ == "__main__":
    import uvicorn

    print("""
╔═══════════════════════════════════════════════════════════╗
║                 z21-Terminal Backend                      ║
║           DCC Locomotive Control Dashboard                ║
╚═══════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
