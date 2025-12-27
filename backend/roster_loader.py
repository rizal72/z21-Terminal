"""
Utility per caricare dati roster e consist da file XML JMRI
"""
import os
import xml.etree.ElementTree as ET
from pathlib import Path

# Path al roster JMRI (standard macOS)
JMRI_ROSTER_PATH = Path.home() / "Library/Preferences/JMRI/La_mia_Ferrovia_in_JMRI.jmri/roster"
CONSIST_FILE = JMRI_ROSTER_PATH / "consist/consist.xml"


def load_consist_from_jmri():
    """
    Carica configurazione consist da JMRI consist.xml

    Returns:
        dict: {
            10: {'lead': 1, 'rear': 5, 'lead_name': 'Gr.675 017', ...},
            11: {'lead': 7, 'rear': 6, 'lead_name': 'E656 239', ...}
        }
    """
    consists = {}

    if not CONSIST_FILE.exists():
        print(f"Warning: Consist file not found: {CONSIST_FILE}")
        return consists

    try:
        tree = ET.parse(CONSIST_FILE)
        root = tree.getroot()

        for consist_elem in root.findall('.//consist'):
            consist_number = consist_elem.get('consistNumber')
            consist_type = consist_elem.get('type', 'DAC')

            if not consist_number:
                continue

            try:
                consist_address = int(consist_number)
            except ValueError:
                continue

            locomotives = []  # Array of locomotives in order: [lead, rear1, rear2, ...]

            for loco_elem in consist_elem.findall('.//loco'):
                loco_id = loco_elem.get('dccLocoAddress')
                loco_direction = loco_elem.get('locoDir', 'normal')
                loco_role = loco_elem.get('locoName', '')  # 'lead' or 'rear'
                roster_entry = loco_elem.get('locoRosterId')

                if not loco_id:
                    continue

                try:
                    loco_address = int(loco_id)
                except ValueError:
                    continue

                # Add to locomotives array (lead first, then rear)
                if loco_role == 'lead':
                    # Insert at beginning (lead is always first)
                    locomotives.insert(0, {
                        'address': loco_address,
                        'name': roster_entry or f'Loco {loco_address}'
                    })
                else:
                    # Append rear locomotives
                    locomotives.append({
                        'address': loco_address,
                        'name': roster_entry or f'Loco {loco_address}'
                    })

            # Consist valid if has at least 1 locomotive (lead)
            if locomotives:
                consists[consist_address] = {
                    'locomotives': locomotives,  # Array: first = lead, rest = rear
                    'type': consist_type
                }

    except Exception as e:
        print(f"Error loading consist file: {e}")

    return consists


def load_functions_from_roster(address):
    """
    Carica funzioni F0-F28 dal file roster XML per una locomotiva

    Args:
        address (int): DCC address della locomotiva

    Returns:
        list: [
            {'number': 0, 'label': 'Light', 'lockable': True},
            {'number': 1, 'label': 'Sound', 'lockable': True},
            ...
        ]
    """
    functions = []

    # Find roster file for this address
    if not JMRI_ROSTER_PATH.exists():
        return functions

    try:
        for roster_file in JMRI_ROSTER_PATH.glob('*.xml'):
            if roster_file.name == 'roster.xml' or roster_file.name.startswith('.'):
                continue

            try:
                tree = ET.parse(roster_file)
                root = tree.getroot()

                # Check if this is the right locomotive
                # Address is in the locomotive element attribute
                loco_elem = root.find('.//locomotive')
                if loco_elem is None:
                    continue

                file_address_str = loco_elem.get('dccAddress')
                if not file_address_str:
                    continue

                file_address = int(file_address_str)
                if file_address != address:
                    continue

                # Found the right locomotive, load functions
                for fn_elem in root.findall('.//functionlabel'):
                    fn_num = int(fn_elem.get('num', -1))
                    fn_label = fn_elem.text or f"F{fn_num}"
                    fn_lockable = fn_elem.get('lockable', 'true').lower() == 'true'

                    if fn_num >= 0:
                        functions.append({
                            'number': fn_num,
                            'label': fn_label,
                            'lockable': fn_lockable
                        })

                # Sort by function number
                functions.sort(key=lambda x: x['number'])
                break

            except Exception as e:
                continue

    except Exception as e:
        print(f"Error loading functions for address {address}: {e}")

    return functions


def load_all_locomotives():
    """
    Carica tutte le locomotive dal roster JMRI

    Returns:
        dict: {
            1: {'address': 1, 'name': 'Gr.675 017', 'functions': [...], 'in_consist': 10},
            5: {'address': 5, 'name': 'D645 014', 'functions': [...], 'in_consist': 10},
            ...
        }
    """
    locomotives = {}

    if not JMRI_ROSTER_PATH.exists():
        return locomotives

    # First, find which locomotives are in consists
    consists = load_consist_from_jmri()
    locos_in_consist = {}  # {loco_address: consist_address}

    for consist_addr, consist_data in consists.items():
        # All locomotives in the consist array belong to this consist
        for loco in consist_data.get('locomotives', []):
            locos_in_consist[loco['address']] = consist_addr

    # Load all roster files
    try:
        for roster_file in JMRI_ROSTER_PATH.glob('*.xml'):
            if roster_file.name == 'roster.xml' or roster_file.name.startswith('.'):
                continue

            try:
                tree = ET.parse(roster_file)
                root = tree.getroot()

                loco_elem = root.find('.//locomotive')
                if loco_elem is None:
                    continue

                # Get address
                address_str = loco_elem.get('dccAddress')
                if not address_str:
                    continue

                address = int(address_str)

                # Get name (roster ID)
                name = loco_elem.get('id', f'Loco {address}')

                # Load functions
                functions = []
                for fn_elem in root.findall('.//functionlabel'):
                    fn_num = int(fn_elem.get('num', -1))
                    fn_label = fn_elem.text or f"F{fn_num}"
                    fn_lockable = fn_elem.get('lockable', 'true').lower() == 'true'

                    if fn_num >= 0:
                        functions.append({
                            'number': fn_num,
                            'label': fn_label,
                            'lockable': fn_lockable
                        })

                functions.sort(key=lambda x: x['number'])

                locomotives[address] = {
                    'address': address,
                    'name': name,
                    'functions': functions,
                    'in_consist': locos_in_consist.get(address),  # None if not in consist
                    'speed': 0,
                    'direction': 'forward',
                    'power': True
                }

            except Exception as e:
                continue

    except Exception as e:
        print(f"Error loading locomotives: {e}")

    return locomotives


def load_consist_with_functions():
    """
    Carica consist con funzioni delle locomotive lead

    Returns:
        dict: {
            10: {
                'address': 10,
                'locomotives': [
                    {'address': 1, 'name': 'Gr.675 017'},  # First = lead
                    {'address': 5, 'name': 'D645 014'}     # Rest = rear
                ],
                'functions': [...]
            },
            ...
        }
    """
    consists = load_consist_from_jmri()
    result = {}

    for consist_addr, consist_data in consists.items():
        locomotives = consist_data.get('locomotives', [])

        # Load functions from lead locomotive (first in array)
        functions = []
        if locomotives:
            lead_address = locomotives[0]['address']
            functions = load_functions_from_roster(lead_address)

        result[consist_addr] = {
            'address': consist_addr,
            'locomotives': locomotives,  # Array: [lead, rear1, rear2, ...]
            'functions': functions,
            'speed': 0,
            'direction': 'forward',
            'power': True
        }

    return result


if __name__ == '__main__':
    # Test
    print("Loading consists from JMRI...")
    consists = load_consist_with_functions()

    for addr, data in consists.items():
        locomotives = data['locomotives']
        print(f"\nConsist {addr}:")
        print(f"  Locomotives: {len(locomotives)}")
        for i, loco in enumerate(locomotives):
            role = "Lead" if i == 0 else f"Rear {i}"
            print(f"    {role}: {loco['address']} - {loco['name']}")
        print(f"  Functions: {len(data['functions'])} found")
        for fn in data['functions'][:5]:  # Show first 5
            print(f"    F{fn['number']}: {fn['label']} ({'lockable' if fn['lockable'] else 'momentary'})")
