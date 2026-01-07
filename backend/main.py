"""
FastAPI backend per z21-Terminal Web Dashboard
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any
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

# Default constants (single source of truth)
DEFAULT_TIMING_THRESHOLDS = {'normal': 1.0, 'warning': 1.5}
DEFAULT_CONTROLLER = {'id': None, 'type': None, 'address': None}

# Configuration paths (all in project root)
CONFIG_PATH = get_config_path()  # Centralized config path

# Global instances
z21_manager: Z21Manager = None
tracking_manager: TrackingManager = None
tracking_daemon_ws: WebSocket = None  # WebSocket connection to tracking daemon
connected_clients: List[WebSocket] = []
consist_data: Dict[int, Dict[str, Any]] = {}
locomotive_data: Dict[int, Dict[str, Any]] = {}
controllers_config: List[Dict[str, Any]] = []  # Shared controller configuration
yolo_detections: Dict[str, Any] = {}  # Latest YOLO detections for video overlay
timing_thresholds: Dict[str, float] = DEFAULT_TIMING_THRESHOLDS.copy()  # Dynamic thresholds from config.json
reference_locos: Dict[str, Dict[str, int]] = {}  # Reference loco strategy from config.json
tracked_consist_ids: List[int] = []  # Consist IDs with gate tracking configured (from tracking_assignments)


polling_task = None
health_check_task = None
last_track_power_state = True
z21_online = False
debug_enabled = False  # Debug mode flag (loaded from config.json)


async def poll_track_power():
    """Background task to monitor Z21 track power state"""
    global last_track_power_state

    print("🔄 Starting track power polling (500ms interval)")

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
                    print(f"⚡ Track power changed: {'ON' if current_power else 'OFF'}")
                    last_track_power_state = current_power

                    # Update all consist states
                    for address in consist_data.keys():
                        if address in z21_manager.consist_state:
                            z21_manager.consist_state[address]['power'] = current_power
                            await broadcast_state_update(address)

        except Exception as e:
            print(f"Error polling track power: {e}")


async def health_check_z21():
    """Background task to monitor Z21 connection health"""
    global z21_online, last_track_power_state

    print("🏥 Starting Z21 health check (5s interval)")

    while True:
        await asyncio.sleep(5)  # Check every 5 seconds

        if not z21_manager or not z21_manager.z21:
            continue

        previous_state = z21_online

        try:
            # Try to get status from Z21 (acts as ping)
            status = z21_manager.z21.get_status()

            if status is not None:
                z21_online = True
            else:
                z21_online = False

        except Exception as e:
            z21_online = False
            if previous_state:  # Only log when transitioning to offline
                print(f"⚠️ Z21 connection lost: {e}")

        # If state changed, broadcast to all clients
        if z21_online != previous_state:
            status_emoji = "✅" if z21_online else "❌"
            status_text = "ONLINE" if z21_online else "OFFLINE"
            print(f"{status_emoji} Z21 status changed: {status_text}")

            # If Z21 went offline, set track power to OFF
            if not z21_online:
                print("⚡ Setting track power to OFF (Z21 offline)")
                last_track_power_state = False
                # Update all consist states
                for address in consist_data.keys():
                    if address in z21_manager.consist_state:
                        z21_manager.consist_state[address]['power'] = False
                        await broadcast_state_update(address)

            await broadcast_z21_status()


async def broadcast_z21_status():
    """Broadcast Z21 connection status to all connected clients"""
    message = {
        'type': 'z21_status',
        'online': z21_online
    }

    disconnected_clients = []
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception as e:
            disconnected_clients.append(client)

    # Remove disconnected clients
    for client in disconnected_clients:
        if client in connected_clients:
            connected_clients.remove(client)


async def broadcast_controllers_update():
    """Broadcast controllers configuration to all connected clients"""
    message = {
        'type': 'controllers_update',
        'controllers': controllers_config
    }

    disconnected_clients = []
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception as e:
            disconnected_clients.append(client)

    # Remove disconnected clients
    for client in disconnected_clients:
        if client in connected_clients:
            connected_clients.remove(client)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global z21_manager, tracking_manager, tracking_daemon_ws, consist_data, locomotive_data, polling_task, health_check_task, last_track_power_state, z21_online, controllers_config, timing_thresholds, reference_locos, tracked_consist_ids, debug_enabled

    print("🚂 z21-Terminal Backend Starting...")

    # Load debug mode configuration FIRST
    try:
        config = load_config()
        debug_config = config.get('debug', {'enabled': False})
        debug_enabled = debug_config.get('enabled', False)
    except Exception:
        debug_enabled = False

    # Load timing thresholds from config.json
    print("⏱️  Loading timing thresholds from config.json...")
    try:
        config = load_config()
        tracking_config = config.get('tracking', {})
        thresholds = tracking_config.get('timing_thresholds', DEFAULT_TIMING_THRESHOLDS)
        timing_thresholds = {
            'normal': thresholds.get('normal', DEFAULT_TIMING_THRESHOLDS['normal']),
            'warning': thresholds.get('warning', DEFAULT_TIMING_THRESHOLDS['warning'])
        }
        if debug_enabled:
            print(f"  ✓ Timing thresholds: SYNCED < {timing_thresholds['normal']}s, WARNING < {timing_thresholds['warning']}s")
    except FileNotFoundError:
        print(f"  ⚠️  config.json not found, using default thresholds ({DEFAULT_TIMING_THRESHOLDS['normal']}s/{DEFAULT_TIMING_THRESHOLDS['warning']}s)")
        timing_thresholds = DEFAULT_TIMING_THRESHOLDS.copy()
    except Exception as e:
        print(f"  ⚠️  Error loading config.json: {e}, using defaults")
        timing_thresholds = DEFAULT_TIMING_THRESHOLDS.copy()

    # Load reference loco configuration (from consists)
    print("🎯 Loading reference loco configuration...")
    try:
        config = load_config()
        consists = config.get('consists', {})
        # Extract reference info from each consist
        reference_locos = {}
        for consist_addr, consist_info in consists.items():
            reference_locos[consist_addr] = {
                'reference': consist_info.get('reference_loco'),
                'adjust': consist_info.get('adjust_loco')
            }
        if debug_enabled:
            print(f"  ✓ Reference locos: {len(reference_locos)} consists configured")
            for consist_addr, ref_config in reference_locos.items():
                print(f"    Consist {consist_addr}: reference={ref_config['reference']}, adjust={ref_config['adjust']}")
    except Exception as e:
        print(f"  ⚠️  Error loading reference locos: {e}")

    # Load tracked consist IDs (only consists with gate tracking configured)
    print("📍 Loading tracked consist IDs...")
    try:
        config = load_config()
        consists = config.get('consists', {})
        # Filter only consist IDs with gate_ids configured
        for consist_key, consist_info in consists.items():
            consist_id = int(consist_key)
            gate_ids = consist_info.get('gate_ids', [])
            if gate_ids:  # Only add if gates configured
                tracked_consist_ids.append(consist_id)
        tracked_consist_ids.sort()
        if debug_enabled:
            print(f"  ✓ Tracked consists: {tracked_consist_ids}")
    except Exception as e:
        print(f"  ⚠️  Error loading tracked consists: {e}")
        reference_locos = {}
        consists = {}

    # Load consist configuration
    # Priority: config.json consists → JMRI (bootstrap only)
    if not consists:
        try:
            config = load_config()
            consists = config.get('consists', {})
        except Exception:
            consists = {}

    if consists:
        # Load from config.json (source of truth)
        print("📋 Loading consists from config.json (source of truth)...")
        consist_data = load_consists_from_config(CONFIG_PATH)
        if debug_enabled and consist_data:
            for addr, data in consist_data.items():
                locomotives = data.get('locomotives', [])
                if locomotives:
                    names = ' + '.join([loco['name'] for loco in locomotives])
                    print(f"  ✓ Consist {addr}: {names} ({len(data['functions'])} functions)")
    else:
        # Bootstrap from JMRI (one-time only, then save to config.json)
        print("📋 Bootstrapping consists from JMRI (first run)...")
        consist_data = load_consist_with_functions()

        if not consist_data:
            print("⚠️  Warning: No consists loaded from JMRI")
        else:
            if debug_enabled:
                for addr, data in consist_data.items():
                    locomotives = data.get('locomotives', [])
                    if locomotives:
                        names = ' + '.join([loco['name'] for loco in locomotives])
                        print(f"  ✓ Consist {addr}: {names} ({len(data['functions'])} functions)")
                    else:
                        print(f"  ✓ Consist {addr}: (empty) ({len(data['functions'])} functions)")

            # Save to config.json for future use
            print("💾 Saving consists to config.json for future use...")
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
            print(f"  ✓ Saved {len(consist_data)} consists to config.json")

    # Load all locomotives from JMRI
    print("📋 Loading all locomotives from JMRI...")
    locomotive_data = load_all_locomotives()

    if not locomotive_data:
        print("⚠️  Warning: No locomotives loaded from JMRI")
    else:
        if debug_enabled:
            print(f"  ✓ Loaded {len(locomotive_data)} locomotives")
            for addr, data in locomotive_data.items():
                in_consist = f" (in consist {data['in_consist']})" if data['in_consist'] else ""
                print(f"    Loco {addr}: {data['name']}{in_consist}")

    # Initialize default controllers configuration
    # Try to pre-select consist 10 and 11 if they exist, otherwise leave empty
    print("🎮 Initializing default controllers...")
    controller1 = {'id': 1, 'type': 'consist', 'address': 10} if 10 in consist_data else {**DEFAULT_CONTROLLER, 'id': 1}
    controller2 = {'id': 2, 'type': 'consist', 'address': 11} if 11 in consist_data else {**DEFAULT_CONTROLLER, 'id': 2}
    controllers_config = [controller1, controller2]

    if debug_enabled:
        if controller1['type'] and controller2['type']:
            print(f"  ✓ Initialized 2 controllers (consist {controller1['address']} + consist {controller2['address']})")
        elif controller1['type']:
            print(f"  ✓ Initialized 2 controllers (consist {controller1['address']} + empty)")
        elif controller2['type']:
            print(f"  ✓ Initialized 2 controllers (empty + consist {controller2['address']})")
        else:
            print("  ✓ Initialized 2 empty controllers")

    # Initialize Z21 Manager
    print("🔌 Connecting to Z21...")
    z21_manager = Z21Manager(z21_ip='192.168.1.111', verbose=False, reference_locos=reference_locos, timing_thresholds=timing_thresholds, debug_enabled=debug_enabled, config_path=CONFIG_PATH)

    if z21_manager.connect():
        if debug_enabled:
            print("  ✓ Connected to Z21 at 192.168.1.111")

        # Initialize consist states in Z21 Manager
        for address, data in consist_data.items():
            z21_manager.initialize_consist(address, data)
            if debug_enabled:
                print(f"  ✓ Initialized consist {address}")

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
                print(f"  ✓ Initialized locomotive {address}{in_consist_note}")

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
                    print(f"  ✓ Initial track power: {'ON' if last_track_power_state else 'OFF'}")
                z21_online = True
                if debug_enabled:
                    print(f"  ✓ Z21 connection: ONLINE")
        except (OSError, ConnectionError, TimeoutError) as e:
            print(f"⚠️  Z21 not responding (will retry in background): {e}")
            z21_online = False
            # Backend continues startup - health check will retry connection

        # Start background polling tasks
        polling_task = asyncio.create_task(poll_track_power())
        health_check_task = asyncio.create_task(health_check_z21())

        # Initialize Tracking Manager
        print("🎯 Initializing Tracking Manager...")
        tracking_manager = TrackingManager(z21_manager, connected_clients)
        if debug_enabled:
            print("  ✓ Tracking Manager ready")

    else:
        print("  ✗ Failed to connect to Z21")
        z21_online = False

    print("✅ Backend ready!")
    print("🌐 WebSocket endpoint: ws://localhost:8000/ws")
    print("🎥 WebSocket tracking endpoint: ws://localhost:8000/ws/tracking")

    yield

    # Shutdown
    print("\n🛑 Shutting down...")
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
    print("✅ Cleanup complete")


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


async def broadcast_state_update(address: int):
    """Broadcast consist/locomotive state update to all connected clients"""
    # Check if address exists in either consists or locomotives
    is_consist = address in consist_data
    is_locomotive = address in locomotive_data

    if not (is_consist or is_locomotive):
        print(f"⚠️ Address {address} not found in consists or locomotives")
        return

    state = z21_manager.get_consist_state(address)

    # Get function definitions from roster data
    if is_consist:
        function_definitions = consist_data[address].get('functions', [])
    else:
        function_definitions = locomotive_data[address].get('functions', [])

    message = {
        'type': 'consist_update',  # Same type for both (backwards compatible)
        'address': address,
        'data': {
            'speed': state.get('speed', 0),
            'direction': state.get('direction', 'forward'),
            'power': state.get('power', True),
            'functions': function_definitions,  # Function definitions (array)
            'functionStates': state.get('functions', {}),  # Function states (object)
            'virtual_mode': state.get('virtual_mode', False),  # NEW: Virtual Mode status
            'auto_compensation_enabled': state.get('auto_compensation_enabled', False),  # NEW: Auto-compensation flag
            'delta_t': state.get('delta_t'),  # NEW: Latest Δt from tracking (or None)
            'delta_t_timestamp': state.get('delta_t_timestamp')  # NEW: Timestamp
        }
    }

    # Send to all connected clients
    disconnected_clients = []
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected_clients.append(client)

    # Remove disconnected clients
    for client in disconnected_clients:
        if client in connected_clients:
            connected_clients.remove(client)


async def broadcast_initial_state():
    """Broadcast complete initial state to all connected clients"""
    # Build consists state using helper function (DRY principle)
    consists_state = {}
    for address, data in consist_data.items():
        state = z21_manager.get_consist_state(address) if z21_manager else {}
        consists_state[address] = build_consist_response(address, data, state)

    # Build locomotives state
    locomotives_state = {}
    for address, data in locomotive_data.items():
        state = z21_manager.get_consist_state(address) if z21_manager else {}
        locomotives_state[address] = {
            'address': address,
            'name': data.get('name', ''),
            'in_consist': data.get('in_consist'),
            'speed': state.get('speed', 0),
            'direction': state.get('direction', 'forward'),
            'functions': data.get('functions', []),
            'functionStates': state.get('functions', {})
        }

    message = {
        'type': 'initial_state',
        'consists': consists_state,
        'locomotives': locomotives_state,
        'controllers': controllers_config,
        'trackPower': last_track_power_state,
        'z21Online': z21_online
    }

    # Send to all connected clients
    disconnected_clients = []
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception as e:
            print(f"Error broadcasting initial state: {e}")
            disconnected_clients.append(client)

    # Remove disconnected clients
    for client in disconnected_clients:
        if client in connected_clients:
            connected_clients.remove(client)


async def reload_roster_data():
    """Reload roster and consists from config.json (and locomotives from JMRI)"""
    global consist_data, locomotive_data

    print("\n🔄 Reloading roster...")

    # Load config to check consists
    try:
        config = load_config()
    except Exception as e:
        print(f"⚠️  Error loading config: {e}")
        return False

    # Load consists from config.json (source of truth)
    consists = config.get('consists', {})

    if consists:
        print("📋 Loading consists from config.json...")
        consist_data = load_consists_from_config(CONFIG_PATH)
        if debug_enabled and consist_data:
            print(f"  ✓ Loaded {len(consist_data)} consists from config.json")
    else:
        print("⚠️  No consists in config.json, trying JMRI bootstrap...")
        consist_data = load_consist_with_functions()
        if debug_enabled and consist_data:
            print(f"  ✓ Loaded {len(consist_data)} consists from JMRI")

    # Always load locomotives from JMRI (names, functions)
    print("📋 Loading locomotives from JMRI...")
    locomotive_data = load_all_locomotives()

    if not locomotive_data:
        print("⚠️  Warning: No locomotives loaded from JMRI")
    else:
        if debug_enabled:
            print(f"  ✓ Loaded {len(locomotive_data)} locomotives")

    if not z21_manager or not z21_manager.z21:
        print("  ✗ Z21 not connected, cannot reinitialize")
        return False

    # Re-initialize consist states
    for address, data in consist_data.items():
        z21_manager.initialize_consist(address, data)
        if debug_enabled:
            print(f"  ✓ Re-initialized consist {address}")

    # Re-initialize locomotive states
    for address, data in locomotive_data.items():
        z21_manager.initialize_consist(address, {
            'locomotives': [{'address': address, 'name': data['name']}],  # Single loco array
            'functions': data['functions']
        })
        if debug_enabled:
            in_consist_note = f" (in consist {data['in_consist']})" if data.get('in_consist') else ""
            print(f"  ✓ Re-initialized locomotive {address}{in_consist_note}")

    # Broadcast new state to all connected clients
    await broadcast_initial_state()
    if debug_enabled:
        print("  ✓ Broadcasted new state to all clients")

    print("✅ Roster reload complete!\n")
    return True


@app.get("/api/status")
async def api_status():
    """API status endpoint"""
    return {
        "name": "z21-Terminal Backend",
        "version": "1.0.0",
        "status": "running",
        "z21_connected": z21_manager is not None and z21_manager.z21 is not None,
        "consists_loaded": len(consist_data),
        "connected_clients": len(connected_clients)
    }


def build_consist_response(address, data, state):
    """
    Single source of truth for consist response structure.
    Use this for ALL WebSocket/API responses to avoid duplication.
    """
    locomotives = data.get('locomotives', [])
    lead_name = locomotives[0]['name'] if locomotives else ''
    rear_names = [loco['name'] for loco in locomotives[1:]] if len(locomotives) > 1 else []
    rear_name = ' + '.join(rear_names) if rear_names else None

    # Load gate_ids from config consists
    gate_ids = []
    try:
        config = load_config()
        consists = config.get('consists', {})
        consist_info = consists.get(str(address), {})
        gate_ids = consist_info.get('gate_ids', [])
    except Exception:
        pass  # If config load fails, gate_ids stays empty

    return {
        'address': address,
        'type': 'consist',
        'trackName': 'INTERNAL TRACK' if address == 10 else 'EXTERNAL TRACK',
        'locomotives': locomotives,
        'lead_name': lead_name,
        'rear_name': rear_name,
        'functions': data['functions'],
        'gate_ids': gate_ids,  # Include gate_ids for frontend
        # Spread ALL state fields automatically (speed, direction, power, virtual_mode, etc.)
        # CRITICAL: Exclude 'functions' from spread to avoid overwriting function definitions with states
        **{k: v for k, v in state.items() if k not in ['address', 'locomotives', 'functions']},
        # Rename 'functions' state dict to 'functionStates' for clarity
        'functionStates': state.get('functions', {})
    }


@app.get("/api/consists")
async def get_consists():
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


@app.post("/api/consists")
async def create_consist(request: dict):
    """Create a new consist in config.json"""
    global consist_data

    try:
        consist_address = str(request.get("address"))
        lead_address = request.get("lead_address")
        rear_address = request.get("rear_address")
        gate_ids = request.get("gate_ids", [])
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
            "gate_assignment": None,  # Default: symmetric cross-gate mode
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
                print(f"⚙️  Creating consist {consist_address} in Virtual Mode - writing CV19=0")
                cv_value = 0
            else:
                # DCC Mode: write CV19=consist_address (enable hardware consist)
                print(f"⚙️  Creating consist {consist_address} in DCC Mode - writing CV19={consist_addr_int}")
                cv_value = consist_addr_int

            success_lead = z21_manager.z21.write_cv_ops_mode(lead_address, 19, cv_value)
            success_rear = z21_manager.z21.write_cv_ops_mode(rear_address, 19, cv_value)

            if not (success_lead and success_rear):
                mode_str = "Virtual" if virtual_mode else "DCC"
                return {"success": False, "error": f"Consist created in config but failed to write CV19 to locomotives ({mode_str} Mode)"}

        mode_str = "Virtual" if virtual_mode else "DCC"

        # Reload consist_data from updated config before broadcasting
        consist_data = load_consists_from_config(CONFIG_PATH)

        # Broadcast updated state to all connected clients (refresh dropdowns)
        await broadcast_initial_state()

        return {"success": True, "message": f"Consist {consist_address} created in {mode_str} Mode (CV19 written)"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.put("/api/consists/{address}")
async def update_consist(address: str, request: dict):
    """Update an existing consist in config.json"""
    global consist_data

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
                print(f"⚙️  Switching consist {address} to Virtual Mode - writing CV19=0")
                cv_value = 0
            else:
                # Switched to DCC Mode: write CV19=consist_address
                print(f"⚙️  Switching consist {address} to DCC Mode - writing CV19={consist_addr_int}")
                cv_value = consist_addr_int

            success_lead = z21_manager.z21.write_cv_ops_mode(lead_address, 19, cv_value)
            success_rear = z21_manager.z21.write_cv_ops_mode(rear_address, 19, cv_value)

            if not (success_lead and success_rear):
                mode_str = "Virtual" if new_virtual_mode else "DCC"
                return {"success": False, "error": f"Consist updated in config but failed to write CV19 ({mode_str} Mode)"}

            mode_str = "Virtual" if new_virtual_mode else "DCC"

            # Reload consist_data from updated config before broadcasting
            consist_data = load_consists_from_config(CONFIG_PATH)

            # Broadcast updated state to all connected clients (refresh dropdowns)
            await broadcast_initial_state()

            return {"success": True, "message": f"Consist {address} updated and switched to {mode_str} Mode (CV19 written)"}

        # Reload consist_data from updated config before broadcasting
        consist_data = load_consists_from_config(CONFIG_PATH)

        # Broadcast updated state to all connected clients (refresh dropdowns)
        await broadcast_initial_state()

        return {"success": True, "message": f"Consist {address} updated"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/api/consists/{address}")
async def delete_consist(address: str):
    """
    Delete a consist from config.json
    If consist is in DCC mode (virtual_mode=false), writes CV19=0 first
    """
    global consist_data

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
            print(f"⚠️  Consist {address} is in DCC mode - writing CV19=0 to disable consist on locomotives")
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

        # Broadcast updated state to all connected clients (refresh dropdowns)
        await broadcast_initial_state()

        return {"success": True, "message": f"Consist {address} deleted"}

    except Exception as e:
        return {"success": False, "error": str(e)}


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


@app.get("/api/locomotives")
async def get_locomotives():
    """Get all locomotives"""
    result = {}

    for address, data in locomotive_data.items():
        # Get state from z21_manager if available
        state = z21_manager.get_consist_state(address) if z21_manager else {}

        result[address] = {
            'address': address,
            'type': 'locomotive',
            'name': data['name'],
            'functions': data['functions'],
            'in_consist': data.get('in_consist'),
            'speed': state.get('speed', 0),
            'direction': state.get('direction', 'forward'),
            'power': state.get('power', True),
            'functionStates': state.get('functions', {})  # Actual function states from Z21
        }

    return result


@app.get("/api/roster")
async def get_full_roster():
    """Get full roster: consists + locomotives"""
    consists_data = await get_consists()
    # Extract only the consists dict (backward compatibility)
    # get_consists() now returns {consists: {...}, gates: [...], ...}
    return {
        'consists': consists_data.get('consists', {}),
        'locomotives': await get_locomotives()
    }


@app.post("/api/reload-roster")
async def reload_roster():
    """Reload roster and consists from JMRI XML files without restarting backend"""
    try:
        success = await reload_roster_data()
        if success:
            return {
                "status": "success",
                "message": "Roster reloaded successfully",
                "consists_loaded": len(consist_data),
                "locomotives_loaded": len(locomotive_data),
                "clients_notified": len(connected_clients)
            }
        else:
            return {
                "status": "error",
                "message": "Failed to reload roster (Z21 not connected)"
            }
    except Exception as e:
        print(f"❌ Error reloading roster: {e}")
        return {
            "status": "error",
            "message": f"Exception during reload: {str(e)}"
        }


@app.post("/api/toggle-panel")
async def toggle_panel():
    """Toggle Δt panel visibility in video feed (press 'P' in UI)"""
    video_feed_module.SHOW_DELTA_T_PANEL = not video_feed_module.SHOW_DELTA_T_PANEL
    status = "visible" if video_feed_module.SHOW_DELTA_T_PANEL else "hidden"
    print(f"  🎛️  Δt panel toggled: {status}")
    return {
        "status": "success",
        "panel_visible": video_feed_module.SHOW_DELTA_T_PANEL
    }


@app.post("/api/toggle-debug")
async def toggle_debug():
    """Toggle debug overlay in video feed (press 'B' in UI)"""
    video_feed_module.SHOW_DEBUG_OVERLAY = not video_feed_module.SHOW_DEBUG_OVERLAY
    status = "visible" if video_feed_module.SHOW_DEBUG_OVERLAY else "hidden"
    print(f"  🔍 Debug overlay toggled: {status}")
    return {
        "status": "success",
        "debug_visible": video_feed_module.SHOW_DEBUG_OVERLAY
    }


@app.get("/api/gates")
async def get_gates():
    """Get current gate configuration"""
    config = load_config()
    return config.get('gates', [])


@app.post("/api/save-gates")
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
        from pathlib import Path

        config_path = Path(__file__).parent.parent / 'config.json'
        backup_name = "config.json.backup"
        backup_path = config_path.parent / backup_name

        shutil.copy(config_path, backup_path)
        print(f"  💾 Config backup created: {backup_name}")

        # Update gates in config
        config['gates'] = gates

        # Save config (with inline array formatting)
        save_config(config)

        print(f"  💾 Gates configuration saved ({len(gates)} gates)")
        return {
            "status": "success",
            "message": f"Saved {len(gates)} gates (backup: {backup_name})"
        }
    except Exception as e:
        print(f"  ❌ Error saving gates: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


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
                # If no cache yet (first run), don't add to dict (shows "Waiting...")

        return all_tracking_data

    def get_yolo_detections():
        """Callback to get latest YOLO detections for locomotive markers"""
        global yolo_detections
        return yolo_detections.get('detections', [])

    return StreamingResponse(
        generate_video_frames(
            tracking_data_callback=get_tracking_data,
            yolo_detections_callback=get_yolo_detections
        ),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time control"""
    await websocket.accept()
    connected_clients.append(websocket)

    print(f"🔌 Client connected (total: {len(connected_clients)})")

    try:
        # Send initial state to new client
        roster_data = await get_full_roster()
        await websocket.send_json({
            'type': 'initial_state',
            'consists': roster_data['consists'],
            'locomotives': roster_data['locomotives'],
            'controllers': controllers_config,
            'trackPower': last_track_power_state,
            'z21Online': z21_online
        })
        if debug_enabled:
            print(f"  ✓ Sent initial state (trackPower={last_track_power_state}, z21Online={z21_online})")

        # Notify tracking manager of client connection
        if tracking_manager:
            await tracking_manager.on_client_connected()

        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                message_type = data.get('type')

                if message_type == 'set_speed':
                    address = data.get('address')
                    speed = data.get('speed', 0)
                    forward = data.get('forward', True)

                    if z21_manager and (address in consist_data or address in locomotive_data):
                        z21_manager.set_speed(address, speed, forward)
                        await broadcast_state_update(address)

                        # Notify tracking manager of speed change
                        if tracking_manager and address in consist_data:
                            await tracking_manager.on_speed_change(address, speed)

                        # Notify tracking daemon of speed change (for dynamic FPS)
                        if tracking_daemon_ws and address in consist_data:
                            try:
                                await tracking_daemon_ws.send_json({
                                    'type': 'consist_speed_update',
                                    'consist_address': address,
                                    'speed': speed
                                })
                            except Exception:
                                # Daemon disconnected, will be cleared on next loop
                                pass

                elif message_type == 'set_direction':
                    address = data.get('address')
                    direction = data.get('direction', 'forward')
                    forward = direction == 'forward'

                    if z21_manager and (address in consist_data or address in locomotive_data):
                        # Get current speed (from consist_state or default)
                        state = z21_manager.get_consist_state(address) if address in consist_data else {}
                        current_speed = state.get('speed', 0)
                        z21_manager.set_speed(address, current_speed, forward)
                        await broadcast_state_update(address)

                elif message_type == 'set_function':
                    address = data.get('address')
                    function_num = data.get('function')
                    state = data.get('state', False)

                    is_consist = address in consist_data
                    is_loco = address in locomotive_data

                    if z21_manager and (is_consist or is_loco):
                        z21_manager.set_function(address, function_num, state)
                        await broadcast_state_update(address)

                        # Also broadcast to individual loco panels if setting function on consist
                        if is_consist and address in consist_data:
                            locomotives = consist_data[address].get('locomotives', [])
                            for loco in locomotives:
                                loco_addr = loco['address']
                                if loco_addr in locomotive_data:
                                    # F0 goes to all, other functions only to lead
                                    if function_num == 0 or loco_addr == locomotives[0]['address']:
                                        await broadcast_state_update(loco_addr)

                elif message_type == 'emergency_stop':
                    power_on = data.get('powerOn', False)

                    if z21_manager:
                        if power_on:
                            z21_manager.track_power_on()
                        else:
                            z21_manager.track_power_off()

                        # Broadcast updates for all consists
                        for address in consist_data.keys():
                            await broadcast_state_update(address)

                elif message_type == 'sync':
                    # Sync specific consist from Z21
                    address = data.get('address')
                    if z21_manager and address in consist_data:
                        z21_manager.sync_consist_state(address)
                        await broadcast_state_update(address)

                elif message_type == 'add_controller':
                    # Add new controller to shared configuration
                    new_controller = data.get('controller')
                    if new_controller:
                        controllers_config.append(new_controller)
                        print(f"➕ Controller added: {new_controller}")
                        await broadcast_controllers_update()

                elif message_type == 'remove_controller':
                    # Remove controller from shared configuration
                    controller_id = data.get('id')
                    if controller_id:
                        # Don't allow removing last controller
                        if len(controllers_config) > 1:
                            controllers_config[:] = [c for c in controllers_config if c['id'] != controller_id]
                            print(f"➖ Controller removed: {controller_id}")
                            await broadcast_controllers_update()

                elif message_type == 'update_controller_selection':
                    # Update controller selection
                    controller_id = data.get('id')
                    selection = data.get('selection')
                    if controller_id and selection:
                        for controller in controllers_config:
                            if controller['id'] == controller_id:
                                controller['type'] = selection.get('type')
                                controller['address'] = selection.get('address')
                                print(f"🔄 Controller {controller_id} updated: {selection}")
                                await broadcast_controllers_update()

                                # Small delay to ensure controllers_update is processed first
                                await asyncio.sleep(0.05)  # 50ms delay

                                # Also broadcast current state of the selected consist/loco
                                # so the new panel gets updated functionStates
                                selected_address = selection.get('address')
                                if selected_address and (selected_address in consist_data or selected_address in locomotive_data):
                                    await broadcast_state_update(selected_address)
                                break

                elif message_type == 'toggle_virtual_mode':
                    # Toggle Virtual Consist Mode (CV19 write only, no speed compensation)
                    consist_address = data.get('address')
                    enable = data.get('enable', False)

                    if z21_manager and consist_address in consist_data:
                        if enable:
                            success = z21_manager.enable_virtual_mode(consist_address)
                        else:
                            success = z21_manager.disable_virtual_mode(consist_address)

                        if success:
                            # Broadcast updated state to all clients
                            await broadcast_state_update(consist_address)
                            if debug_enabled:
                                print(f"  ✓ Virtual Mode {'enabled' if enable else 'disabled'} for consist {consist_address}")
                        else:
                            print(f"  ✗ Failed to toggle Virtual Mode for consist {consist_address}")

                elif message_type == 'toggle_auto_compensation':
                    # Toggle Auto-Compensation (only allowed in Virtual Mode)
                    consist_address = data.get('address')
                    enable = data.get('enable', False)

                    if z21_manager and consist_address in z21_manager.consist_state:
                        consist = z21_manager.consist_state[consist_address]
                        is_virtual = consist.get('virtual_mode', False)

                        if is_virtual:
                            # Only allow toggle if in Virtual Mode
                            consist['auto_compensation_enabled'] = enable
                            # Broadcast updated state to all clients
                            await broadcast_state_update(consist_address)
                            if debug_enabled:
                                print(f"  ✓ Auto-compensation {'enabled' if enable else 'disabled'} for consist {consist_address}")
                        else:
                            print(f"  ✗ Cannot toggle auto-compensation: consist {consist_address} not in Virtual Mode")

            except json.JSONDecodeError:
                print("Invalid JSON received")
                continue

    except WebSocketDisconnect:
        print(f"🔌 Client disconnected (remaining: {len(connected_clients) - 1})")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

        # Notify tracking manager of client disconnection
        if tracking_manager:
            await tracking_manager.on_client_disconnected()


@app.websocket("/ws/tracking")
async def websocket_tracking_endpoint(websocket: WebSocket):
    """WebSocket endpoint for tracking daemon connection"""
    global tracking_daemon_ws

    await websocket.accept()
    tracking_daemon_ws = websocket  # Save reference for bidirectional communication

    print(f"🎥 Tracking daemon connected")

    try:
        # Handle incoming messages from tracking daemon
        while True:
            try:
                data = await websocket.receive_json()
                message_type = data.get('type')

                if message_type == 'delta_t_update':
                    # Update from tracking daemon with new Δt calculation
                    consist_address = data.get('consist_address')
                    delta_t = data.get('delta_t')
                    status = data.get('status', 'UNKNOWN')
                    timestamp = data.get('timestamp')
                    time_str = data.get('time_str', '')  # Pre-calculated elapsed time
                    thresholds = data.get('thresholds', timing_thresholds)  # From daemon or fallback to loaded

                    if z21_manager and consist_address in consist_data:
                        # Update consist state with ALL Δt data from tracking_daemon (single source of truth)
                        z21_manager.consist_state[consist_address]['delta_t'] = delta_t
                        z21_manager.consist_state[consist_address]['delta_t_timestamp'] = timestamp
                        z21_manager.consist_state[consist_address]['delta_t_status'] = status
                        z21_manager.consist_state[consist_address]['delta_t_time_str'] = time_str

                        # Colored status log (only status word colored)
                        if status == 'CRITICAL':
                            colored_status = f"\033[91m{status}\033[0m"
                        elif status == 'WARNING':
                            colored_status = f"\033[93m{status}\033[0m"
                        elif status == 'SYNCED':
                            colored_status = f"\033[92m{status}\033[0m"
                        else:
                            colored_status = status

                        print(f"  📊 Δt update: consist {consist_address} = {delta_t:.3f}s ({colored_status})")

                        # ⚡ AUTO-COMPENSATION: Trigger for CRITICAL (compensation) or SYNCED (decay)
                        if consist_address in z21_manager.consist_state:
                            consist = z21_manager.consist_state[consist_address]
                            is_virtual = consist.get('virtual_mode', False)
                            auto_comp_enabled = consist.get('auto_compensation_enabled', False)
                            last_speed = consist.get('speed', 0)
                            last_direction = consist.get('direction', 'forward') == 'forward'

                            # Trigger set_speed() for both CRITICAL and SYNCED zones (not WARNING)
                            # Only if Virtual Mode AND auto-compensation enabled
                            if is_virtual and auto_comp_enabled and last_speed > 0:
                                is_critical = abs(delta_t) > thresholds['warning']  # > warning threshold
                                is_synced = abs(delta_t) < thresholds['normal']      # < normal threshold

                                if is_critical or is_synced:
                                    if is_critical:
                                        print(f"  ⚡ Auto-compensation triggered: |Δt| = {abs(delta_t):.3f}s > {thresholds['warning']}s")
                                    # Call set_speed with auto_compensation flag (handles both compensation and decay)
                                    z21_manager.set_speed(consist_address, last_speed, last_direction, is_auto_compensation=True)

                        # Get compensation data for UI display
                        consist = z21_manager.consist_state[consist_address]
                        adjust_loco_address = consist.get('adjust_loco_address')
                        adjust_speed = consist.get('adjust_speed')
                        adjust_correction = consist.get('adjust_correction')

                        # Broadcast to all frontend clients (include thresholds and time_str)
                        message = {
                            'type': 'delta_t_update',
                            'consist_address': consist_address,
                            'delta_t': delta_t,
                            'status': status,
                            'timestamp': timestamp,
                            'time_str': time_str,  # Pre-calculated elapsed time
                            'thresholds': thresholds,  # Dynamic thresholds from daemon
                            'adjust_loco_address': adjust_loco_address,  # Which loco is being adjusted
                            'adjust_speed': adjust_speed,  # Actual speed sent to adjust loco
                            'adjust_correction': adjust_correction  # Difference from target (speed_adjust - speed)
                        }

                        disconnected_clients = []
                        for client in connected_clients:
                            try:
                                await client.send_json(message)
                            except Exception:
                                disconnected_clients.append(client)

                        # Remove disconnected clients
                        for client in disconnected_clients:
                            if client in connected_clients:
                                connected_clients.remove(client)

                elif message_type == 'yolo_detections':
                    # YOLO detection positions for video overlay
                    global yolo_detections
                    yolo_detections = {
                        'detections': data.get('detections', []),
                        'timestamp': data.get('timestamp')
                    }

                elif message_type == 'tracking_positions':
                    # Legacy position format (optional, for debugging)
                    pass

            except json.JSONDecodeError:
                print("Invalid JSON received from tracking daemon")
                continue

    except WebSocketDisconnect:
        print(f"🎥 Tracking daemon disconnected")
        tracking_daemon_ws = None  # Clear reference
        # Note: consist_state['delta_t'] may be reset to None by z21_manager on stop (correct for logic)
        # But video_feed cache keeps last value for display (matches React panel behavior)
        print(f"  📊 Δt display: video cache preserves last value")
    except Exception as e:
        print(f"Tracking WebSocket error: {e}")
        tracking_daemon_ws = None  # Clear reference on error


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
    print(f"✅ Production mode: Serving frontend from {frontend_dist}")
    print(f"   Access dashboard at: http://localhost:8000")
else:
    print(f"⚠️  Development mode: Frontend dist not found")
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
