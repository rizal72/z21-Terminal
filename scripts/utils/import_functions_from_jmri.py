"""
Import Function Labels from JMRI Roster to config.json

What it does:
1. Reads JMRI roster XML files (via existing Locomotive class)
2. Reads current config.json (locomotives section)
3. Creates backup of config.json
4. Adds 'functions' field to each locomotive in config
5. Does NOT touch database
6. Does NOT touch CV67-94 (speed tables remain in DB)

Usage:
    cd ~/Documents/_PROGETTI/z21-Terminal
    source venv/bin/activate
    python scripts/utils/import_functions_from_jmri.py

Idempotent: Can run multiple times (overwrites functions only)
Safe: Automatic config backup before modification
Targeted: ONLY adds/updates 'functions' field
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict

# Add scripts/utils/cv_operations to path for Locomotive class import
SCRIPT_DIR = Path(__file__).parent.parent.parent / "scripts" / "utils" / "cv_operations"
sys.path.insert(0, str(SCRIPT_DIR))

from read_cv_from_roster import load_all_locomotives

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.json"


def backup_config():
    """
    Create timestamped backup of config.json.

    Returns:
        Path to backup file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = CONFIG_PATH.with_suffix(f'.json.backup_{timestamp}')

    shutil.copy2(CONFIG_PATH, backup_path)
    print(f"[BACKUP] Created config backup: {backup_path.name}")

    return backup_path


def import_functions_to_config(locos: Dict) -> bool:
    """
    Import function labels to config.json (add 'functions' field to locomotives).

    ONLY updates the 'functions' field for each locomotive.
    Does NOT touch: name, decoder, color, cv_profiles, notes.
    Does NOT touch: database, CV67-94, anything else.

    Args:
        locos: Dict from load_all_locomotives() {address_str: Locomotive}

    Returns:
        True if successful, False if error
    """
    try:
        # Read current config
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)

        # Get locomotives section (should already exist from v1.0.0)
        locomotives = config.get('locomotives', {})

        if not locomotives:
            print("[ERROR] No 'locomotives' section found in config.json")
            print("Run import_speed_tables_from_jmri.py first to create unified config")
            return False

        updated_count = 0
        skipped_count = 0

        # Iterate over JMRI roster locomotives
        for address_str, loco in locos.items():
            # Check if locomotive exists in config
            if address_str not in locomotives:
                print(f"[SKIP] Loco {address_str} not in config.json (run speed_tables import first)")
                skipped_count += 1
                continue

            # Add/update functions field
            locomotives[address_str]['functions'] = loco.functions

            print(f"[CONFIG] Updated loco {address_str}: {len(loco.functions)} function labels")
            updated_count += 1

        # Write updated config (pretty print with 2-space indent)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"[CONFIG] Updated {updated_count} locomotives, skipped {skipped_count}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to update config.json: {e}")
        return False


def main():
    """
    Main import workflow.
    """
    print("=" * 60)
    print("JMRI Roster Import: Function Labels -> config.json")
    print("=" * 60)
    print()

    # Step 1: Load JMRI roster
    print("[STEP 1/3] Loading JMRI roster XML...")
    locos = load_all_locomotives()

    if not locos:
        print("[ERROR] No locomotives found in JMRI roster")
        print("Make sure JMRI roster files exist in ~/Library/Preferences/JMRI/.../roster/")
        return False

    print(f"[ROSTER] Found {len(locos)} locomotives")
    for address, loco in locos.items():
        func_count = len(loco.functions)
        print(f"  - Loco {address}: {loco.name} ({func_count} functions)")
    print()

    # Step 2: Backup config.json
    print("[STEP 2/3] Creating config.json backup...")
    backup_path = backup_config()
    print()

    # Step 3: Import to config.json
    print("[STEP 3/3] Importing function labels to config.json...")
    if not import_functions_to_config(locos):
        print("[ERROR] Function labels import failed")
        return False
    print()

    # Summary
    print("=" * 60)
    print("IMPORT COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print()
    print(f"Config backup: {backup_path.name}")
    print(f"Config updated: 'functions' field added to locomotives")
    print()
    print("Next steps:")
    print("1. Verify config.json: cat config.json | jq '.locomotives[\"1\"].functions'")
    print("2. Test in web dashboard: Open locomotive control, check function buttons")
    print()

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
