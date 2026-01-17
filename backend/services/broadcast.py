"""
Broadcasting Service

Centralizes WebSocket broadcast functions for state updates.
Manages real-time synchronization across all connected clients.
"""

from typing import List, Dict, Any
from fastapi import WebSocket
from config_loader import load_config
from log_colors import log

# Global references (initialized by main.py via init_broadcast_service)
_connected_clients: List[WebSocket] = []
_z21_manager = None
_z21_online: bool = False
_consist_data: Dict[int, Dict[str, Any]] = {}
_locomotive_data: Dict[int, Dict[str, Any]] = {}
_controllers_config: List[Dict[str, Any]] = []
_last_track_power_state: bool = True


def init_broadcast_service(
    clients: List[WebSocket],
    z21_mgr,
    consist_dict: Dict,
    locomotive_dict: Dict,
    controllers: List
):
    """
    Initialize broadcast service with references to global state.

    Args:
        clients: List of connected WebSocket clients
        z21_mgr: Z21Manager instance
        consist_dict: Consist data dictionary
        locomotive_dict: Locomotive data dictionary
        controllers: Controllers configuration list
    """
    global _connected_clients, _z21_manager, _consist_data, _locomotive_data, _controllers_config

    _connected_clients = clients
    _z21_manager = z21_mgr
    _consist_data = consist_dict
    _locomotive_data = locomotive_dict
    _controllers_config = controllers


def update_z21_status(online: bool):
    """Update Z21 online status (called by main.py health check)"""
    global _z21_online
    _z21_online = online


def update_track_power(power: bool):
    """Update track power state (called by main.py polling)"""
    global _last_track_power_state
    _last_track_power_state = power


def build_consist_response(address: int, data: Dict, state: Dict) -> Dict:
    """
    Single source of truth for consist response structure.
    Use this for ALL WebSocket/API responses to avoid duplication.

    Args:
        address: Consist DCC address
        data: Consist configuration data (from consist_data)
        state: Current consist state (from z21_manager)

    Returns:
        Formatted consist response dict
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
        'gate_ids': gate_ids,
        # Spread ALL state fields automatically (speed, direction, power, virtual_mode, etc.)
        # CRITICAL: Exclude 'functions' from spread to avoid overwriting function definitions with states
        **{k: v for k, v in state.items() if k not in ['address', 'locomotives', 'functions']},
        # Rename 'functions' state dict to 'functionStates' for clarity
        'functionStates': state.get('functions', {})
    }


async def broadcast_z21_status():
    """Broadcast Z21 connection status to all connected clients"""
    message = {
        'type': 'z21_status',
        'online': _z21_online
    }

    disconnected_clients = []
    for client in _connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected_clients.append(client)

    # Remove disconnected clients
    for client in disconnected_clients:
        if client in _connected_clients:
            _connected_clients.remove(client)


async def broadcast_controllers_update():
    """Broadcast controllers configuration to all connected clients"""
    message = {
        'type': 'controllers_update',
        'controllers': _controllers_config
    }

    disconnected_clients = []
    for client in _connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected_clients.append(client)

    # Remove disconnected clients
    for client in disconnected_clients:
        if client in _connected_clients:
            _connected_clients.remove(client)


async def broadcast_state_update(address: int):
    """Broadcast consist/locomotive state update to all connected clients"""
    # Check if address exists in either consists or locomotives
    is_consist = address in _consist_data
    is_locomotive = address in _locomotive_data

    if not (is_consist or is_locomotive):
        log('[WARN]', f"Address {address} not found in consists or locomotives")
        return

    state = _z21_manager.get_consist_state(address)

    # Get function definitions from roster data
    if is_consist:
        function_definitions = _consist_data[address].get('functions', [])
    else:
        function_definitions = _locomotive_data[address].get('functions', [])

    message = {
        'type': 'consist_update',  # Same type for both (backwards compatible)
        'address': address,
        'data': {
            'speed': state.get('speed', 0),
            'direction': state.get('direction', 'forward'),
            'power': state.get('power', True),
            'functions': function_definitions,  # Function definitions (array)
            'functionStates': state.get('functions', {}),  # Function states (object)
            'virtual_mode': state.get('virtual_mode', False),
            'auto_compensation_enabled': state.get('auto_compensation_enabled', False),
            'delta_t': state.get('delta_t'),  # Latest dT from tracking (or None)
            'delta_t_timestamp': state.get('delta_t_timestamp')
        }
    }

    # Send to all connected clients
    disconnected_clients = []
    for client in _connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected_clients.append(client)

    # Remove disconnected clients
    for client in disconnected_clients:
        if client in _connected_clients:
            _connected_clients.remove(client)


async def broadcast_initial_state():
    """Broadcast complete initial state to all connected clients"""
    # Build consists state using helper function (DRY principle)
    consists_state = {}
    for address, data in _consist_data.items():
        state = _z21_manager.get_consist_state(address) if _z21_manager else {}
        consists_state[address] = build_consist_response(address, data, state)

    # Build locomotives state
    locomotives_state = {}
    for address, data in _locomotive_data.items():
        state = _z21_manager.get_consist_state(address) if _z21_manager else {}
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
        'controllers': _controllers_config,
        'trackPower': _last_track_power_state,
        'z21Online': _z21_online
    }

    # Send to all connected clients
    disconnected_clients = []
    for client in _connected_clients:
        try:
            await client.send_json(message)
        except Exception as e:
            print(f"Error broadcasting initial state: {e}")
            disconnected_clients.append(client)

    # Remove disconnected clients
    for client in disconnected_clients:
        if client in _connected_clients:
            _connected_clients.remove(client)
