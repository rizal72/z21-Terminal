"""
WebSocket Tracking Handler

Handles tracking daemon WebSocket endpoint:
- Tracking daemon connection/disconnection lifecycle
- Delta-t updates from YOLO tracking (gate timing)
- Auto-compensation triggers (speed correction)
- YOLO detections broadcast to video feed
- Speed sync on connect (critical for page reload)
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Optional
import json

from z21_manager import Z21Manager
from log_colors import log
import dependencies


async def handle_ws_tracking(
    websocket: WebSocket,
    z21_manager: Optional[Z21Manager],
    consist_data: Dict[int, Dict[str, Any]],
    connected_clients: List[WebSocket],
    timing_thresholds: Dict[str, float]
):
    """
    Main tracking daemon WebSocket handler.

    Args:
        websocket: Tracking daemon WebSocket connection
        z21_manager: Z21 manager instance
        consist_data: Consist configuration data
        connected_clients: List of connected WebSocket clients (for broadcast)
        timing_thresholds: Timing thresholds for delta_t classification
    """
    await websocket.accept()

    # Save reference for bidirectional communication
    dependencies.set_tracking_daemon_ws(websocket)  # CRITICAL: sync with dependencies for ws_control

    log('[WS]', f"Tracking daemon connected")

    # Guard: z21_manager must be initialized
    if z21_manager is None:
        log('[ERROR]', "Tracking daemon connection rejected: z21_manager not initialized")
        await websocket.close(code=1011, reason="Backend not ready")
        dependencies.set_tracking_daemon_ws(None)
        return

    # Sync daemon with current speeds immediately on connect
    # Critical for page reload: daemon must know if locos are moving
    for consist_address, consist_state in z21_manager.consist_state.items():
            speed = consist_state.get('speed', 0)
            if speed > 0:
                try:
                    await websocket.send_json({
                        'type': 'consist_speed_update',
                        'consist_address': consist_address,
                        'speed': speed
                    })
                    log('[INIT]', f"Synced daemon on connect: consist {consist_address} speed={speed}")
                except Exception:
                    pass  # Ignore errors on initial sync

    try:
        # Handle incoming messages from tracking daemon
        while True:
            try:
                data = await websocket.receive_json()
                message_type = data.get('type')

                if message_type == 'delta_t_update':
                    await handle_delta_t_update(
                        data, z21_manager, consist_data, connected_clients, timing_thresholds
                    )

                elif message_type == 'yolo_detections':
                    await handle_yolo_detections(data)

                elif message_type == 'tracking_positions':
                    # Legacy position format (optional, for debugging)
                    pass

            except json.JSONDecodeError:
                print("Invalid JSON received from tracking daemon")
                continue

    except WebSocketDisconnect:
        log('[WS]', f"Tracking daemon disconnected")
        dependencies.set_tracking_daemon_ws(None)  # CRITICAL: sync with dependencies
        # Note: consist_state['delta_t'] may be reset to None by z21_manager on stop (correct for logic)
        # But video_feed cache keeps last value for display (matches React panel behavior)
        log('[DETECT]', f"dT display: video cache preserves last value")
    except Exception as e:
        print(f"Tracking WebSocket error: {e}")
        dependencies.set_tracking_daemon_ws(None)  # CRITICAL: sync with dependencies


# ============================================
# Message Handler Functions
# ============================================

async def handle_delta_t_update(
    data: dict,
    z21_manager: Z21Manager,
    consist_data: Dict,
    connected_clients: List[WebSocket],
    timing_thresholds: Dict[str, float]
):
    """Handle delta_t update from tracking daemon"""
    consist_address = data.get('consist_address')
    delta_t = data.get('delta_t')
    status = data.get('status', 'UNKNOWN')
    timestamp = data.get('timestamp')
    time_str = data.get('time_str', '')  # Pre-calculated elapsed time
    thresholds = data.get('thresholds', timing_thresholds)  # From daemon or fallback to loaded

    # Validate consist_address and delta_t
    if consist_address is None or delta_t is None:
        return
    consist_address = int(consist_address)
    delta_t = float(delta_t)

    if z21_manager and consist_address in consist_data:
        # Update consist state with ALL dT data from tracking_daemon (single source of truth)
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

        log('[DETECT]', f"dT update: consist {consist_address} = {delta_t:.3f}s ({colored_status})")

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
                is_critical = abs(delta_t) > thresholds['critical']  # > critical threshold
                is_synced = abs(delta_t) < thresholds['warning']      # < warning threshold

                if is_critical or is_synced:
                    if is_critical:
                        log('[COMP]', f"Auto-compensation triggered: |dT| = {abs(delta_t):.3f}s > {thresholds['critical']}s (CRITICAL)")
                    # Call set_speed with auto_compensation flag (handles both compensation and decay)
                    z21_manager.set_speed(consist_address, last_speed, last_direction, is_auto_compensation=True)

        # Get compensation data for UI display
        consist = z21_manager.consist_state[consist_address]
        adjust_loco_address = consist.get('adjust_loco_address')
        adjust_speed = consist.get('adjust_speed')
        adjust_correction = consist.get('adjust_correction')
        reference_loco_address = consist.get('reference_loco_address')
        reference_speed = consist.get('reference_speed')
        reference_correction = consist.get('reference_correction')

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
            'adjust_correction': adjust_correction,  # Difference from target (speed_adjust - speed)
            'reference_loco_address': reference_loco_address,  # Reference loco (compensated on overflow)
            'reference_speed': reference_speed,  # Actual speed sent to reference loco
            'reference_correction': reference_correction  # Difference from target (speed_reference - speed)
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


async def handle_yolo_detections(data: dict):
    """Handle YOLO detection positions for video overlay"""
    detections = {
        'detections': data.get('detections', []),
        'timestamp': data.get('timestamp')
    }
    dependencies.set_yolo_detections(detections)
