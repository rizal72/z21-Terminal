"""
Roster Router

Handles all roster-related endpoints:
- Locomotives list (individual locomotives)
- Full roster (consists + locomotives)
- Roster reload from JMRI XML files
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
from dependencies import get_locomotive_data, get_consist_data, get_z21_manager
from z21_manager import Z21Manager
from log_colors import log

router = APIRouter(tags=["roster"])


@router.get("/api/locomotives")
async def get_locomotives(
    locomotive_data: Dict = Depends(get_locomotive_data),
    z21_manager: Z21Manager = Depends(get_z21_manager)
):
    """Get all locomotives (individual locomotives not in consists)"""
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


@router.get("/api/roster")
async def get_full_roster(
    consist_data: Dict = Depends(get_consist_data),
    locomotive_data: Dict = Depends(get_locomotive_data),
    z21_manager: Z21Manager = Depends(get_z21_manager)
):
    """
    Get full roster: consists + locomotives

    This endpoint provides backward compatibility by combining
    consists (from config router) and locomotives data.
    """
    # Import get_consists from config router to get full consists data
    from routers.config import get_consists

    # Get consists data (includes gates, tracking_assignments, etc.)
    consists_response = await get_consists(consist_data, z21_manager)

    # Get locomotives data
    locomotives = await get_locomotives(locomotive_data, z21_manager)

    # Return combined roster
    return {
        'consists': consists_response.get('consists', {}),
        'locomotives': locomotives
    }


@router.post("/api/reload-roster")
async def reload_roster(
    consist_data: Dict = Depends(get_consist_data),
    locomotive_data: Dict = Depends(get_locomotive_data)
):
    """
    Reload roster and consists from JMRI XML files without restarting backend

    This endpoint calls the reload_roster_data() function from main.py
    which updates global consist_data and locomotive_data dictionaries.
    """
    # Import main module to access reload_roster_data
    import main
    from dependencies import get_connected_clients

    try:
        success = await main.reload_roster_data()
        if success:
            connected_clients = get_connected_clients()
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
        log('[WARN]', f"Error reloading roster: {e}")
        return {
            "status": "error",
            "message": f"Exception during reload: {str(e)}"
        }
