"""
FastAPI backend per z21-Terminal Web Dashboard
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any
import json
import asyncio
from contextlib import asynccontextmanager

from z21_manager import Z21Manager
from roster_loader import load_consist_with_functions, load_all_locomotives
from tracking_manager import TrackingManager
from video_feed import generate_video_frames

# Global instances
z21_manager: Z21Manager = None
tracking_manager: TrackingManager = None
connected_clients: List[WebSocket] = []
consist_data: Dict[int, Dict[str, Any]] = {}
locomotive_data: Dict[int, Dict[str, Any]] = {}
controllers_config: List[Dict[str, Any]] = []  # Shared controller configuration
yolo_detections: Dict[str, Any] = {}  # Latest YOLO detections for video overlay


polling_task = None
health_check_task = None
last_track_power_state = True
z21_online = False


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
    global z21_manager, tracking_manager, consist_data, locomotive_data, polling_task, health_check_task, last_track_power_state, z21_online, controllers_config

    print("🚂 z21-Terminal Backend Starting...")

    # Load consist configuration from JMRI
    print("📋 Loading consists from JMRI...")
    consist_data = load_consist_with_functions()

    if not consist_data:
        print("⚠️  Warning: No consists loaded from JMRI")
    else:
        for addr, data in consist_data.items():
            locomotives = data.get('locomotives', [])
            if locomotives:
                names = ' + '.join([loco['name'] for loco in locomotives])
                print(f"  ✓ Consist {addr}: {names} ({len(data['functions'])} functions)")
            else:
                print(f"  ✓ Consist {addr}: (empty) ({len(data['functions'])} functions)")

    # Load all locomotives from JMRI
    print("📋 Loading all locomotives from JMRI...")
    locomotive_data = load_all_locomotives()

    if not locomotive_data:
        print("⚠️  Warning: No locomotives loaded from JMRI")
    else:
        print(f"  ✓ Loaded {len(locomotive_data)} locomotives")
        for addr, data in locomotive_data.items():
            in_consist = f" (in consist {data['in_consist']})" if data['in_consist'] else ""
            print(f"    Loco {addr}: {data['name']}{in_consist}")

    # Initialize default controllers configuration
    # Try to pre-select consist 10 and 11 if they exist, otherwise leave empty
    print("🎮 Initializing default controllers...")
    controller1 = {'id': 1, 'type': 'consist', 'address': 10} if 10 in consist_data else {'id': 1, 'type': None, 'address': None}
    controller2 = {'id': 2, 'type': 'consist', 'address': 11} if 11 in consist_data else {'id': 2, 'type': None, 'address': None}
    controllers_config = [controller1, controller2]

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
    z21_manager = Z21Manager(z21_ip='192.168.1.111', verbose=False)

    if z21_manager.connect():
        print("  ✓ Connected to Z21 at 192.168.1.111")

        # Initialize consist states in Z21 Manager
        for address, data in consist_data.items():
            z21_manager.initialize_consist(address, data)
            print(f"  ✓ Initialized consist {address}")

        # Initialize locomotive states in Z21 Manager
        # Initialize ALL locomotives (standalone + those in consist)
        # Even locos in consist need state tracking for individual function control
        for address, data in locomotive_data.items():
            z21_manager.initialize_consist(address, {
                'locomotives': [{'address': address, 'name': data['name']}],  # Single loco array
                'functions': data['functions']
            })
            in_consist_note = f" (in consist {data['in_consist']})" if data.get('in_consist') else ""
            print(f"  ✓ Initialized locomotive {address}{in_consist_note}")

        # Get initial track power state
        status = z21_manager.z21.get_status()
        if status:
            last_track_power_state = not status.get('track_power_off', False)
            print(f"  ✓ Initial track power: {'ON' if last_track_power_state else 'OFF'}")
            z21_online = True
            print(f"  ✓ Z21 connection: ONLINE")

        # Start background polling tasks
        polling_task = asyncio.create_task(poll_track_power())
        health_check_task = asyncio.create_task(health_check_z21())

        # Initialize Tracking Manager
        print("🎯 Initializing Tracking Manager...")
        tracking_manager = TrackingManager(z21_manager, connected_clients)
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
    # Build consists state
    consists_state = {}
    for address, data in consist_data.items():
        state = z21_manager.get_consist_state(address) if z21_manager else {}
        locomotives = data.get('locomotives', [])
        # Build names for display
        lead_name = locomotives[0]['name'] if locomotives else ''
        rear_names = [loco['name'] for loco in locomotives[1:]] if len(locomotives) > 1 else []
        rear_name = ' + '.join(rear_names) if rear_names else None

        consists_state[address] = {
            'address': address,
            'type': 'consist',
            'trackName': 'INTERNAL TRACK' if address == 10 else 'EXTERNAL TRACK',
            'locomotives': locomotives,  # Array: [lead, rear1, rear2, ...]
            'lead_name': lead_name,  # For display convenience
            'rear_name': rear_name,  # For display convenience (None if solo)
            'speed': state.get('speed', 0),
            'direction': state.get('direction', 'forward'),
            'power': state.get('power', True),
            'functions': data.get('functions', []),
            'functionStates': state.get('functions', {}),
            'virtual_mode': state.get('virtual_mode', False),  # NEW
            'delta_t': state.get('delta_t'),  # NEW
            'delta_t_timestamp': state.get('delta_t_timestamp')  # NEW
        }

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
    """Reload roster and consists from JMRI XML files and reinitialize Z21 Manager"""
    global consist_data, locomotive_data

    print("\n🔄 Reloading roster from JMRI...")

    # Load data from XML
    consist_data, locomotive_data = load_consist_with_functions(), load_all_locomotives()

    if not consist_data:
        print("⚠️  Warning: No consists loaded from JMRI")
    else:
        print(f"  ✓ Loaded {len(consist_data)} consists")

    if not locomotive_data:
        print("⚠️  Warning: No locomotives loaded from JMRI")
    else:
        print(f"  ✓ Loaded {len(locomotive_data)} locomotives")

    if not z21_manager or not z21_manager.z21:
        print("  ✗ Z21 not connected, cannot reinitialize")
        return False

    # Re-initialize consist states
    for address, data in consist_data.items():
        z21_manager.initialize_consist(address, data)
        print(f"  ✓ Re-initialized consist {address}")

    # Re-initialize locomotive states
    for address, data in locomotive_data.items():
        z21_manager.initialize_consist(address, {
            'locomotives': [{'address': address, 'name': data['name']}],  # Single loco array
            'functions': data['functions']
        })
        in_consist_note = f" (in consist {data['in_consist']})" if data.get('in_consist') else ""
        print(f"  ✓ Re-initialized locomotive {address}{in_consist_note}")

    # Broadcast new state to all connected clients
    await broadcast_initial_state()
    print("  ✓ Broadcasted new state to all clients")

    print("✅ Roster reload complete!\n")
    return True


@app.get("/")
async def root():
    """API root"""
    return {
        "name": "z21-Terminal Backend",
        "version": "1.0.0",
        "status": "running",
        "z21_connected": z21_manager is not None and z21_manager.z21 is not None,
        "consists_loaded": len(consist_data),
        "connected_clients": len(connected_clients)
    }


@app.get("/api/consists")
async def get_consists():
    """Get all consists configuration"""
    result = {}

    for address, data in consist_data.items():
        state = z21_manager.get_consist_state(address) if z21_manager else {}

        locomotives = data.get('locomotives', [])
        # Build names for display
        lead_name = locomotives[0]['name'] if locomotives else ''
        rear_names = [loco['name'] for loco in locomotives[1:]] if len(locomotives) > 1 else []
        rear_name = ' + '.join(rear_names) if rear_names else None

        result[address] = {
            'address': address,
            'type': 'consist',
            'trackName': 'INTERNAL TRACK' if address == 10 else 'EXTERNAL TRACK',
            'locomotives': locomotives,  # Array: [lead, rear1, rear2, ...]
            'lead_name': lead_name,  # For display convenience
            'rear_name': rear_name,  # For display convenience (None if solo)
            'speed': state.get('speed', 0),
            'direction': state.get('direction', 'forward'),
            'power': state.get('power', True),
            'functions': data['functions'],
            'functionStates': state.get('functions', {}),  # Actual function states from Z21
            'virtual_mode': state.get('virtual_mode', False),  # NEW
            'delta_t': state.get('delta_t'),  # NEW
            'delta_t_timestamp': state.get('delta_t_timestamp')  # NEW
        }

    return result


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
    return {
        'consists': await get_consists(),
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


@app.get("/api/video_feed")
async def video_feed():
    """
    MJPEG video stream with gate overlay and tracking info

    Returns:
        StreamingResponse: MJPEG stream
    """
    def get_tracking_data():
        """Callback to get latest tracking data for overlay"""
        # For now, return Consist 11 data if available
        if z21_manager and 11 in z21_manager.consist_state:
            state = z21_manager.consist_state[11]
            delta_t = state.get('delta_t')
            if delta_t is not None:
                # Calculate status based on thresholds
                abs_delta_t = abs(delta_t)
                if abs_delta_t < 0.5:
                    status = 'SYNCED'
                elif abs_delta_t < 1.0:
                    status = 'WARNING'
                else:
                    status = 'CRITICAL'

                return {
                    'consist_address': 11,
                    'delta_t': delta_t,
                    'status': status,
                    'timestamp': state.get('delta_t_timestamp')
                }
        return None

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
                            print(f"  ✓ Virtual Mode {'enabled' if enable else 'disabled'} for consist {consist_address}")
                        else:
                            print(f"  ✗ Failed to toggle Virtual Mode for consist {consist_address}")

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
    await websocket.accept()

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

                    if z21_manager and consist_address in consist_data:
                        # Update consist state with Δt data
                        z21_manager.consist_state[consist_address]['delta_t'] = delta_t
                        z21_manager.consist_state[consist_address]['delta_t_timestamp'] = timestamp

                        # Broadcast to all frontend clients
                        message = {
                            'type': 'delta_t_update',
                            'consist_address': consist_address,
                            'delta_t': delta_t,
                            'status': status,
                            'timestamp': timestamp
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

                        print(f"  📊 Δt update: consist {consist_address} = {delta_t:.3f}s ({status})")

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
    except Exception as e:
        print(f"Tracking WebSocket error: {e}")


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
