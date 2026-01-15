"""
Status Router

Handles all status-related endpoints:
- Backend API status (health check)
- Z21 telemetry (motor load monitoring)
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
import time
from dependencies import get_z21_manager, get_consist_data, get_connected_clients
from z21_manager import Z21Manager

router = APIRouter(tags=["status"])


@router.get("/api/status")
async def api_status(
    consist_data: Dict = Depends(get_consist_data),
    connected_clients: list = Depends(get_connected_clients),
    z21_manager: Z21Manager = Depends(get_z21_manager)
):
    """
    API status endpoint (health check)

    Returns:
        - name: Backend name
        - version: Backend version
        - status: running/error
        - z21_connected: Z21 connection status
        - consists_loaded: Number of consists loaded
        - connected_clients: Number of WebSocket clients
    """
    return {
        "name": "z21-Terminal Backend",
        "version": "1.0.0",
        "status": "running",
        "z21_connected": z21_manager is not None and z21_manager.z21 is not None,
        "consists_loaded": len(consist_data),
        "connected_clients": len(connected_clients)
    }


@router.get("/api/z21/telemetry")
async def get_z21_telemetry(
    z21_manager: Z21Manager = Depends(get_z21_manager)
):
    """
    Get Z21 track-level telemetry (Motor Load Monitoring).

    Returns:
        - status: success/error
        - telemetry: dict with current, voltage, temperature data
        - track_power_on: Track power status
        - emergency_stop: Emergency stop status
        - short_circuit: Short circuit status
        - timestamp: Unix timestamp
        - quality_checks: dict with warnings/alerts
        - warnings: list of human-readable warning messages

    Quality Checks:
        - voltage_ok: 14.0-18.0V (DCC standard range)
        - voltage_warning: Outside safe range
        - current_high: >2000mA (potential short circuit)
        - temperature_high: >60°C (critical)
        - temperature_elevated: 50-60°C (warning)
    """
    if not z21_manager or not z21_manager.z21:
        return {
            "status": "error",
            "message": "Z21 not connected"
        }

    try:
        status = z21_manager.z21.get_status()

        if status and 'telemetry' in status:
            t = status['telemetry']

            # Quality checks (DCC standard voltage: 14-18V, safe operating range)
            checks = {
                'voltage_ok': 14.0 <= t['supply_voltage_v'] <= 18.0,
                'voltage_warning': t['supply_voltage_v'] < 14.0 or t['supply_voltage_v'] > 18.0,
                'current_high': t['main_current_ma'] > 2000,
                'temperature_high': t['temperature_c'] > 60.0,
                'temperature_elevated': 50.0 < t['temperature_c'] <= 60.0
            }

            # Generate human-readable warnings
            warnings = []
            if not checks['voltage_ok']:
                if t['supply_voltage_v'] < 14.0:
                    warnings.append("Supply voltage low - Check power supply or track resistance")
                else:
                    warnings.append("Supply voltage high - Check power supply")

            if checks['current_high']:
                warnings.append(f"High track current ({t['main_current_ma']}mA) - Possible short circuit")

            if checks['temperature_high']:
                warnings.append(f"Z21 temperature critical ({t['temperature_c']:.1f}°C) - Check ventilation")
            elif checks['temperature_elevated']:
                warnings.append(f"Z21 temperature elevated ({t['temperature_c']:.1f}°C) - Monitor closely")

            return {
                "status": "success",
                "telemetry": t,
                "track_power_on": status['track_power_on'],
                "emergency_stop": status['emergency_stop'],
                "short_circuit": status['short_circuit'],
                "timestamp": time.time(),
                "quality_checks": checks,
                "warnings": warnings
            }
        else:
            return {
                "status": "error",
                "message": "No telemetry data available from Z21"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get telemetry: {str(e)}"
        }
