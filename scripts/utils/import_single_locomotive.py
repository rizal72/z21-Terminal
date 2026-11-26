#!/usr/bin/env python3
"""
Import Single Locomotive from JMRI Roster into the database

What it does:
1. Takes a DCC address as input (e.g., 2, 6)
2. Reads that single locomotive from JMRI roster XML
3. Adds the locomotive to the stored configuration (or updates it if already there)
4. Writes CV67-94 to the locomotive_speed_table
5. Does NOT touch other locomotives in the configuration or the database

The configuration lives in the database, shared by every host. Reload the roster in the
dashboard afterwards (POST /api/reload-roster) and the locomotive is there, on every
machine, without a restart.

Usage:
    cd ~/Documents/_PROGETTI/z21-Terminal
    source venv/bin/activate
    python scripts/utils/import_single_locomotive.py --address 2

    # Dry run (show what would be imported without changing anything)
    python scripts/utils/import_single_locomotive.py --address 2 --dry-run

Safety:
- Non-destructive: only adds/updates the specified locomotive
- Idempotent: can run multiple times safely
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Optional, List

# Add backend/ to path for the shared configuration loader
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

# Add scripts/utils/cv_operations to path for Locomotive class import
SCRIPT_DIR = Path(__file__).parent.parent.parent / "scripts" / "utils" / "cv_operations"
sys.path.insert(0, str(SCRIPT_DIR))

from read_cv_from_roster import load_all_locomotives
from config_loader import load_config, save_config

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Default colors for locomotives (fallback if not in config)
DEFAULT_COLORS = {
    "1": "#FFFF00",  # Yellow
    "2": "#FFFFFF",  # White
    "4": "#00FFFF",  # Cyan
    "5": "#FF8000",  # Orange
    "6": "#FF00FF",  # Magenta
    "7": "#00FF00",  # Green
    "8": "#FF0000"   # Red
}


def get_locomotive_from_jmri(address: int) -> Optional[object]:
    """
    Load single locomotive from JMRI roster by DCC address.

    Args:
        address: DCC address (1-10239)

    Returns:
        Locomotive object or None if not found
    """
    all_locos = load_all_locomotives()  # Returns Dict[str, Locomotive] where key is str(address)

    # Roster dict uses address as string key
    return all_locos.get(str(address))


def create_locomotive_config(loco) -> dict:
    """
    Create the stored configuration entry for locomotive.

    Args:
        loco: Locomotive object from JMRI roster

    Returns:
        Dict with locomotive configuration
    """
    # loco.functions is already a List[Dict] with correct format
    # No need to iterate - just use it directly
    functions = loco.functions

    # Get existing color from config or use default
    config = load_config()
    existing_locos = config.get('locomotives', {})
    existing_color = None

    if str(loco.address) in existing_locos:
        existing_color = existing_locos[str(loco.address)].get('color')

    color = existing_color or DEFAULT_COLORS.get(str(loco.address), "#FFFFFF")

    # Create locomotive entry
    loco_config = {
        "name": loco.name,
        "decoder": loco.decoder_model,
        "color": color,
        "cv_profiles": {
            "normal": {
                "cv3": loco.cv.get(3, 0),
                "cv4": loco.cv.get(4, 0)
            },
            "testing": {
                "cv3": 0,
                "cv4": 0
            }
        },
        "functions": functions
    }

    return loco_config


def write_speed_table_to_db(loco):
    """
    Write CV67-94 speed table + CV2/CV5 + decoder_type to data.db.

    Args:
        loco: Locomotive object from JMRI roster
    """
    # Add backend to path for decoder helpers
    BACKEND_DIR = PROJECT_ROOT / "backend"
    sys.path.insert(0, str(BACKEND_DIR))
    from services.decoder_helpers import DECODER_TYPE_MAP, enforce_esu_fixed_values

    # Writes go through the same helpers the web UI uses (Postgres, one schema).
    from services.speed_table_helpers import (
        update_cv_speed_table_in_db,
        update_decoder_metadata_in_db,
    )

    # Extract CV67-94 from loco.cv dict
    cv_values = {}
    for cv_index in range(67, 95):  # CV67-94 (28 steps)
        if cv_index in loco.cv:
            cv_values[cv_index] = loco.cv[cv_index]

    # Extract CV2 (Vstart) and CV5 (Vhigh)
    vstart = loco.cv.get(2)
    vhigh = loco.cv.get(5)

    # Detect decoder type from JMRI decoder model
    decoder_model = loco.decoder_model or ""
    decoder_type = "nmra_standard"  # Default
    for key, value in DECODER_TYPE_MAP.items():
        if key in decoder_model:
            decoder_type = value
            break

    print(f"   Decoder type: {decoder_type}")
    print(f"   CV2 (Vstart): {vstart}")
    print(f"   CV5 (Vhigh): {vhigh}")

    # Enforce ESU fixed values if needed
    if decoder_type == "esu_mfx":
        cv_values = enforce_esu_fixed_values(cv_values, decoder_type)
        print(f"   ESU decoder: enforced CV67=1, CV94=255")

    if not update_cv_speed_table_in_db(loco.address, cv_values, source='jmri_import'):
        print(f"[ERROR] Speed table write failed for loco {loco.address}")
        return
    update_decoder_metadata_in_db(loco.address, vstart, vhigh, decoder_type)

    print(f"[OK] Speed table CV67-94 + decoder metadata written to database for loco {loco.address}")


def import_locomotive(address: int, dry_run: bool = False) -> bool:
    """
    Import single locomotive from JMRI roster.

    Args:
        address: DCC address
        dry_run: If True, show what would be done without making changes

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Importing Locomotive {address} from JMRI Roster")
    print(f"{'='*60}\n")

    # Step 1: Load locomotive from JMRI
    print(f"[1/3] Loading locomotive {address} from JMRI roster...")
    loco = get_locomotive_from_jmri(address)

    if not loco:
        print(f"[ERROR] Locomotive with address {address} not found in JMRI roster")
        all_locos = load_all_locomotives()
        print(f"   Available addresses: {', '.join(str(addr) for addr in all_locos.keys())}")
        return False

    print(f"[OK] Found: {loco.name} (address {loco.address})")
    print(f"   Decoder: {loco.decoder_model}")
    max_func = max([f['number'] for f in loco.functions]) if loco.functions else 0
    print(f"   Functions: {len(loco.functions)} defined (F0-F{max_func})")

    # Count speed table CVs (CV67-94)
    cv_count = sum(1 for cv_index in range(67, 95) if cv_index in loco.cv)
    print(f"   Speed Table: CV67-94 ({cv_count}/28 values defined)")

    # Check if locomotive already exists in config
    config = load_config()
    exists_in_config = str(address) in config.get('locomotives', {})

    if exists_in_config:
        print(f"[INFO] Locomotive {address} already exists in the configuration (will be updated)")
    else:
        print(f"[INFO] Locomotive {address} is NEW (will be added to the configuration)")

    if dry_run:
        action = "update" if exists_in_config else "add"
        print(f"\n[DRY RUN] Would {action} in the stored configuration:")
        loco_config = create_locomotive_config(loco)
        print(json.dumps(loco_config, indent=2, ensure_ascii=False))

        # Show speed table CV values that would be written to DB
        print(f"\n[DRY RUN] Would write speed table to database (locomotive_speed_table):")
        cv_values = {}
        for cv_index in range(67, 95):  # CV67-94 (28 steps)
            if cv_index in loco.cv:
                cv_values[cv_index] = loco.cv[cv_index]
        print(json.dumps(cv_values, indent=2))
        return True

    # Step 2: Update the configuration (the database, shared by every host)
    print(f"\n[2/3] Updating the stored configuration...")
    config = load_config()

    # Ensure locomotives section exists
    if 'locomotives' not in config:
        config['locomotives'] = {}

    # Add or update locomotive
    loco_config = create_locomotive_config(loco)
    config['locomotives'][str(address)] = loco_config

    save_config(config)
    print(f"[OK] Locomotive {address} added/updated in the stored configuration")

    # Step 3: Write speed table to database
    print(f"\n[3/3] Writing speed table to database...")
    write_speed_table_to_db(loco)

    print(f"\n{'='*60}")
    print(f"[SUCCESS] Import Complete!")
    print(f"{'='*60}")
    print(f"\nLocomotive {address} ({loco.name}) imported successfully")
    print(f"Next steps:")
    print(f"  1. Reload the roster in the dashboard (POST /api/reload-roster)")
    print(f"  2. Verify the locomotive and its functions")
    print(f"  3. Test locomotive control in dashboard")

    return True


def main():
    """Main entry point."""
    # Show help if no arguments provided
    if len(sys.argv) == 1:
        sys.argv.append('--help')

    parser = argparse.ArgumentParser(
        description='Import single locomotive from JMRI roster',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import locomotive with address 2
  python import_single_locomotive.py --address 2

  # Dry run (show what would be imported)
  python import_single_locomotive.py --address 6 --dry-run
        """
    )

    parser.add_argument(
        '--address',
        type=int,
        required=True,
        help='DCC address of locomotive to import (e.g., 2, 6)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be imported without making changes'
    )

    args = parser.parse_args()

    # Validate address range
    if not (1 <= args.address <= 10239):
        print(f"[ERROR] Invalid DCC address {args.address} (must be 1-10239)")
        return 1

    # Import locomotive
    success = import_locomotive(args.address, dry_run=args.dry_run)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
