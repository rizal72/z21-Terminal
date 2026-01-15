"""
WebSocket Control Handler

Handles real-time locomotive control WebSocket endpoint:
- Connection lifecycle (accept, initial state, disconnect)
- 10 message types (speed, direction, function, emergency stop, sync, controllers, virtual mode, auto-compensation)
- Broadcast updates to all connected clients
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio
import time

from z21_manager import Z21Manager
from tracking_manager import TrackingManager
from routers.roster import get_full_roster
from services.broadcast import broadcast_state_update, broadcast_controllers_update
from log_colors import log
from dependencies import get_tracking_daemon_ws, get_analytics_logger


async def handle_ws_control(
    websocket: WebSocket,
    connected_clients: List[WebSocket],
    consist_data: Dict[int, Dict[str, Any]],
    locomotive_data: Dict[int, Dict[str, Any]],
    z21_manager: Z21Manager,
    tracking_manager: TrackingManager,
    controllers_config: List[Dict[str, Any]],
    last_track_power_state: bool,
    z21_online: bool,
    debug_enabled: bool,
    loco_start_times: Dict[int, float]
):
    """
    Main control WebSocket handler for real-time locomotive control.

    Args:
        websocket: Client WebSocket connection
        connected_clients: Global list of connected clients
        consist_data: Consist configuration data
        locomotive_data: Locomotive configuration data
        z21_manager: Z21 manager instance
        tracking_manager: Tracking manager instance
        controllers_config: Shared controller configuration
        last_track_power_state: Last known track power state
        z21_online: Z21 connection status
        debug_enabled: Debug mode flag
        loco_start_times: Locomotive movement start times (for operating time tracking)
    """
    await websocket.accept()
    connected_clients.append(websocket)

    log('[WS]', f"Client connected (total: {len(connected_clients)})")

    try:
        # Send initial state to new client
        roster_data = await get_full_roster(consist_data, locomotive_data, z21_manager)
        await websocket.send_json({
            'type': 'initial_state',
            'consists': roster_data['consists'],
            'locomotives': roster_data['locomotives'],
            'controllers': controllers_config,
            'trackPower': last_track_power_state,
            'z21Online': z21_online
        })
        if debug_enabled:
            log('[INIT]', f"Sent initial state (trackPower={last_track_power_state}, z21Online={z21_online})")

        # Notify tracking manager of client connection
        if tracking_manager:
            await tracking_manager.on_client_connected()

        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                message_type = data.get('type')

                if message_type == 'set_speed':
                    await handle_set_speed(
                        data, websocket, consist_data, locomotive_data, z21_manager,
                        tracking_manager, loco_start_times
                    )

                elif message_type == 'set_direction':
                    await handle_set_direction(
                        data, consist_data, locomotive_data, z21_manager
                    )

                elif message_type == 'set_function':
                    await handle_set_function(
                        data, consist_data, locomotive_data, z21_manager
                    )

                elif message_type == 'emergency_stop':
                    await handle_emergency_stop(
                        data, consist_data, z21_manager
                    )

                elif message_type == 'sync':
                    await handle_sync(
                        data, consist_data, z21_manager
                    )

                elif message_type == 'add_controller':
                    await handle_add_controller(
                        data, controllers_config
                    )

                elif message_type == 'remove_controller':
                    await handle_remove_controller(
                        data, controllers_config
                    )

                elif message_type == 'update_controller_selection':
                    await handle_update_controller_selection(
                        data, consist_data, locomotive_data, controllers_config
                    )

                elif message_type == 'toggle_virtual_mode':
                    await handle_toggle_virtual_mode(
                        data, consist_data, z21_manager, debug_enabled
                    )

                elif message_type == 'toggle_auto_compensation':
                    await handle_toggle_auto_compensation(
                        data, z21_manager
                    )

            except json.JSONDecodeError:
                print("Invalid JSON received")
                continue

    except WebSocketDisconnect:
        log('[WS]', f"Client disconnected (remaining: {len(connected_clients) - 1})")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

        # Notify tracking manager of client disconnection
        if tracking_manager:
            await tracking_manager.on_client_disconnected()


# ============================================
# Message Handler Functions
# ============================================

async def handle_set_speed(
    data: dict,
    websocket: WebSocket,
    consist_data: Dict,
    locomotive_data: Dict,
    z21_manager: Z21Manager,
    tracking_manager: TrackingManager,
    loco_start_times: Dict[int, float]
):
    """Handle speed change message"""
    address = data.get('address')
    speed = data.get('speed', 0)
    forward = data.get('forward', True)

    if z21_manager and (address in consist_data or address in locomotive_data):
        # Get old speed before changing (for speed_setting event logging)
        old_speed = z21_manager.consist_state.get(address, {}).get('speed', 0)

        z21_manager.set_speed(address, speed, forward)

        # Log speed_setting event (for speed correlation analysis)
        analytics_logger = get_analytics_logger()
        if analytics_logger:
            # Determine if address is a consist
            consist_id = None
            if address in consist_data:
                consist_id = address

            # Log speed change event (skip if speed unchanged)
            if old_speed != speed:
                await analytics_logger.log_event(
                    event_type='speed_setting',
                    data={
                        'address': address,
                        'consist_id': consist_id,
                        'speed_old': old_speed,
                        'speed_new': speed,
                        'forward': forward,
                        'source': 'user'  # WebSocket messages are always user-initiated
                    }
                )
                log('[SPEED]', f"Address {address}: {old_speed} -> {speed} (direction: {'FWD' if forward else 'REV'})")

        await broadcast_state_update(address)

        # Track locomotive operating time (individual locos only, not consists)
        if address in locomotive_data and analytics_logger:
            current_time = time.time()

            # Movement started (speed > 0 and was stopped)
            if speed > 0 and address not in loco_start_times:
                loco_start_times[address] = current_time
                log('[TRACK]', f"Loco {address} movement started")

            # Movement stopped (speed == 0 and was moving)
            elif speed == 0 and address in loco_start_times:
                start_time = loco_start_times.pop(address)
                duration = current_time - start_time

                # Log operating time event
                analytics_logger.log_loco_operating_time(
                    address=address,
                    start_time=start_time,
                    end_time=current_time,
                    duration_seconds=duration
                )

                log('[TRACK]', f"Loco {address} movement stopped (duration: {duration:.1f}s)")

        # Notify tracking manager of speed change
        if tracking_manager and address in consist_data:
            await tracking_manager.on_speed_change(address, speed)

        # Notify tracking daemon of speed change (for dynamic FPS)
        tracking_daemon_ws = get_tracking_daemon_ws()
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


async def handle_set_direction(
    data: dict,
    consist_data: Dict,
    locomotive_data: Dict,
    z21_manager: Z21Manager
):
    """Handle direction change message"""
    address = data.get('address')
    direction = data.get('direction', 'forward')
    forward = direction == 'forward'

    if z21_manager and (address in consist_data or address in locomotive_data):
        # Get current speed (from consist_state or default)
        state = z21_manager.get_consist_state(address) if address in consist_data else {}
        current_speed = state.get('speed', 0)
        z21_manager.set_speed(address, current_speed, forward)
        await broadcast_state_update(address)


async def handle_set_function(
    data: dict,
    consist_data: Dict,
    locomotive_data: Dict,
    z21_manager: Z21Manager
):
    """Handle function toggle message"""
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


async def handle_emergency_stop(
    data: dict,
    consist_data: Dict,
    z21_manager: Z21Manager
):
    """Handle emergency stop / track power toggle"""
    power_on = data.get('powerOn', False)

    if z21_manager:
        if power_on:
            z21_manager.track_power_on()
        else:
            z21_manager.track_power_off()

        # Broadcast updates for all consists
        for address in consist_data.keys():
            await broadcast_state_update(address)


async def handle_sync(
    data: dict,
    consist_data: Dict,
    z21_manager: Z21Manager
):
    """Handle sync consist state from Z21"""
    address = data.get('address')
    if z21_manager and address in consist_data:
        z21_manager.sync_consist_state(address)
        await broadcast_state_update(address)


async def handle_add_controller(
    data: dict,
    controllers_config: List[Dict[str, Any]]
):
    """Handle add controller message"""
    new_controller = data.get('controller')
    if new_controller:
        controllers_config.append(new_controller)
        log('[WS]', f"Controller added: {new_controller}")
        await broadcast_controllers_update()


async def handle_remove_controller(
    data: dict,
    controllers_config: List[Dict[str, Any]]
):
    """Handle remove controller message"""
    controller_id = data.get('id')
    if controller_id:
        # Don't allow removing last controller
        if len(controllers_config) > 1:
            controllers_config[:] = [c for c in controllers_config if c['id'] != controller_id]
            log('[WS]', f"Controller removed: {controller_id}")
            await broadcast_controllers_update()


async def handle_update_controller_selection(
    data: dict,
    consist_data: Dict,
    locomotive_data: Dict,
    controllers_config: List[Dict[str, Any]]
):
    """Handle controller selection update message"""
    controller_id = data.get('id')
    selection = data.get('selection')
    if controller_id and selection:
        for controller in controllers_config:
            if controller['id'] == controller_id:
                controller['type'] = selection.get('type')
                controller['address'] = selection.get('address')
                log('[WS]', f"Controller {controller_id} updated: {selection}")
                await broadcast_controllers_update()

                # Small delay to ensure controllers_update is processed first
                await asyncio.sleep(0.05)  # 50ms delay

                # Also broadcast current state of the selected consist/loco
                # so the new panel gets updated functionStates
                selected_address = selection.get('address')
                if selected_address and (selected_address in consist_data or selected_address in locomotive_data):
                    await broadcast_state_update(selected_address)
                break


async def handle_toggle_virtual_mode(
    data: dict,
    consist_data: Dict,
    z21_manager: Z21Manager,
    debug_enabled: bool
):
    """Handle toggle Virtual Consist Mode (CV19 write only, no speed compensation)"""
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
                log('[INIT]', f"Virtual Mode {'enabled' if enable else 'disabled'} for consist {consist_address}")
        else:
            log('[WARN]', f"Failed to toggle Virtual Mode for consist {consist_address}")


async def handle_toggle_auto_compensation(
    data: dict,
    z21_manager: Z21Manager
):
    """Handle toggle Auto-Compensation (only allowed in Virtual Mode)"""
    consist_address = data.get('address')
    enable = data.get('enable', False)

    if z21_manager and consist_address in z21_manager.consist_state:
        consist = z21_manager.consist_state[consist_address]
        is_virtual = consist.get('virtual_mode', False)

        if is_virtual:
            # Only allow toggle if in Virtual Mode
            consist['auto_compensation_enabled'] = enable
            # Persist to config.json (critical: preserves setting across restarts)
            z21_manager._save_persisted_state()
            # Always log (important operation that modifies config.json)
            log('[COMP]', f"Auto-compensation {'enabled' if enable else 'disabled'} for consist {consist_address} (saved to config.json)")
            # Broadcast updated state to all clients
            await broadcast_state_update(consist_address)
        else:
            log('[WARN]', f"Cannot toggle auto-compensation: consist {consist_address} not in Virtual Mode")
