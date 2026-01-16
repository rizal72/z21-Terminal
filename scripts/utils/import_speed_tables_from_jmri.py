"""
Import Speed Tables from JMRI Roster to Database + Config.json Refactoring

What it does:
1. Reads JMRI roster XML files (via existing Locomotive class)
2. Reads current config.json (locomotive_colors, cv_profiles)
3. Creates backup of config.json
4. Merges data into new unified 'locomotives' section
5. Removes deprecated 'locomotive_colors' and 'cv_profiles' sections
6. Writes CV67-94 to analytics.db (locomotive_speed_table table)
7. Creates database table if not exists

Usage:
    cd ~/Documents/_PROGETTI/z21-Terminal
    source venv/bin/activate
    python scripts/utils/import_speed_tables_from_jmri.py

Idempotent: Can run multiple times (INSERT OR REPLACE)
Safe: Automatic config backup before modification
"""

import sys
import sqlite3
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# Add scripts/utils/cv_operations to path for Locomotive class import
SCRIPT_DIR = Path(__file__).parent.parent.parent / "scripts" / "utils" / "cv_operations"
sys.path.insert(0, str(SCRIPT_DIR))

from read_cv_from_roster import load_all_locomotives

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.json"
DB_PATH = PROJECT_ROOT / "backend" / "data" / "analytics.db"

# Default colors for locomotives without color in config (fallback)
DEFAULT_COLORS = {
    "1": "#FFFF00",
    "2": "#FFFFFF",
    "4": "#00FFFF",
    "5": "#FF8000",
    "6": "#FF00FF",
    "7": "#00FF00",
    "8": "#FF0000"
}


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


def import_to_config(locos: Dict) -> bool:
    """
    Import locomotive data to config.json (unified 'locomotives' section).

    Merges:
    - Old 'locomotive_colors' -> locomotives.color
    - Old 'cv_profiles' -> locomotives.cv_profiles
    - JMRI roster name -> locomotives.name

    Removes deprecated sections after merge.

    Args:
        locos: Dict from load_all_locomotives() {address_str: Locomotive}

    Returns:
        True if successful, False if error
    """
    try:
        # Read current config
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)

        # Initialize new locomotives section
        new_locomotives = {}

        # Get existing data from old sections
        old_colors = config.get('locomotive_colors', {})
        old_profiles = config.get('cv_profiles', {})

        # Iterate over JMRI roster locomotives
        for address_str, loco in locos.items():
            # Build locomotive entry
            loco_entry = {
                "name": loco.name or f"Loco {address_str}",
                "decoder": loco.decoder_model,
                "color": old_colors.get(address_str, DEFAULT_COLORS.get(address_str, "#808080")),
                "cv_profiles": old_profiles.get(address_str, {
                    "normal": {"cv3": 0, "cv4": 0},
                    "testing": {"cv3": 0, "cv4": 0}
                }),
                "notes": ""
            }

            new_locomotives[address_str] = loco_entry
            print(f"[CONFIG] Merged loco {address_str}: {loco.name}")

        # Replace locomotives section
        config['locomotives'] = new_locomotives

        # Remove deprecated sections
        removed_sections = []
        if 'locomotive_colors' in config:
            del config['locomotive_colors']
            removed_sections.append('locomotive_colors')

        if 'cv_profiles' in config:
            del config['cv_profiles']
            removed_sections.append('cv_profiles')

        if removed_sections:
            print(f"[CONFIG] Removed deprecated sections: {', '.join(removed_sections)}")

        # Write updated config (pretty print with 2-space indent)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"[CONFIG] Updated config.json with {len(new_locomotives)} locomotives")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to update config.json: {e}")
        return False


def create_db_table():
    """
    Create locomotive_speed_table table if not exists.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locomotive_speed_table (
            loco_address INTEGER PRIMARY KEY,

            cv67 INTEGER NOT NULL CHECK(cv67 BETWEEN 0 AND 255),
            cv68 INTEGER NOT NULL CHECK(cv68 BETWEEN 0 AND 255),
            cv69 INTEGER NOT NULL CHECK(cv69 BETWEEN 0 AND 255),
            cv70 INTEGER NOT NULL CHECK(cv70 BETWEEN 0 AND 255),
            cv71 INTEGER NOT NULL CHECK(cv71 BETWEEN 0 AND 255),
            cv72 INTEGER NOT NULL CHECK(cv72 BETWEEN 0 AND 255),
            cv73 INTEGER NOT NULL CHECK(cv73 BETWEEN 0 AND 255),
            cv74 INTEGER NOT NULL CHECK(cv74 BETWEEN 0 AND 255),
            cv75 INTEGER NOT NULL CHECK(cv75 BETWEEN 0 AND 255),
            cv76 INTEGER NOT NULL CHECK(cv76 BETWEEN 0 AND 255),
            cv77 INTEGER NOT NULL CHECK(cv77 BETWEEN 0 AND 255),
            cv78 INTEGER NOT NULL CHECK(cv78 BETWEEN 0 AND 255),
            cv79 INTEGER NOT NULL CHECK(cv79 BETWEEN 0 AND 255),
            cv80 INTEGER NOT NULL CHECK(cv80 BETWEEN 0 AND 255),
            cv81 INTEGER NOT NULL CHECK(cv81 BETWEEN 0 AND 255),
            cv82 INTEGER NOT NULL CHECK(cv82 BETWEEN 0 AND 255),
            cv83 INTEGER NOT NULL CHECK(cv83 BETWEEN 0 AND 255),
            cv84 INTEGER NOT NULL CHECK(cv84 BETWEEN 0 AND 255),
            cv85 INTEGER NOT NULL CHECK(cv85 BETWEEN 0 AND 255),
            cv86 INTEGER NOT NULL CHECK(cv86 BETWEEN 0 AND 255),
            cv87 INTEGER NOT NULL CHECK(cv87 BETWEEN 0 AND 255),
            cv88 INTEGER NOT NULL CHECK(cv88 BETWEEN 0 AND 255),
            cv89 INTEGER NOT NULL CHECK(cv89 BETWEEN 0 AND 255),
            cv90 INTEGER NOT NULL CHECK(cv90 BETWEEN 0 AND 255),
            cv91 INTEGER NOT NULL CHECK(cv91 BETWEEN 0 AND 255),
            cv92 INTEGER NOT NULL CHECK(cv92 BETWEEN 0 AND 255),
            cv93 INTEGER NOT NULL CHECK(cv93 BETWEEN 0 AND 255),
            cv94 INTEGER NOT NULL CHECK(cv94 BETWEEN 0 AND 255),

            previous_values TEXT,
            last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT DEFAULT 'jmri_import'
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_loco_speed_table_modified
        ON locomotive_speed_table(last_modified DESC)
    """)

    conn.commit()
    conn.close()

    print("[DB] Created/verified locomotive_speed_table table")


def import_to_database(locos: Dict) -> bool:
    """
    Import CV67-94 speed tables to database.

    Args:
        locos: Dict from load_all_locomotives() {address_str: Locomotive}

    Returns:
        True if successful, False if error
    """
    try:
        # Create table if not exists
        create_db_table()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        imported_count = 0
        skipped_count = 0

        # Iterate over JMRI roster locomotives
        for address_str, loco in locos.items():
            address = int(address_str)

            # Extract CV67-94 from locomotive's CV dict
            cv_values = {}
            for cv_index in range(67, 95):  # CV67-94 (28 steps)
                if cv_index in loco.cv:
                    cv_values[cv_index] = loco.cv[cv_index]

            # Skip if no speed table configured
            if not cv_values:
                print(f"[DB] Skipped loco {address}: No speed table in JMRI roster")
                skipped_count += 1
                continue

            # Prepare values for INSERT (cv67-cv94 in order)
            values = [cv_values.get(67 + i, 0) for i in range(28)]

            # Insert or replace
            cursor.execute("""
                INSERT OR REPLACE INTO locomotive_speed_table (
                    loco_address,
                    cv67, cv68, cv69, cv70, cv71, cv72, cv73, cv74, cv75, cv76,
                    cv77, cv78, cv79, cv80, cv81, cv82, cv83, cv84, cv85, cv86,
                    cv87, cv88, cv89, cv90, cv91, cv92, cv93, cv94,
                    previous_values, last_modified, source
                ) VALUES (
                    ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?,
                    NULL, CURRENT_TIMESTAMP, 'jmri_import'
                )
            """, (address, *values))

            print(f"[DB] Imported loco {address}: CV67={cv_values.get(67, 0)} ... CV94={cv_values.get(94, 0)}")
            imported_count += 1

        conn.commit()
        conn.close()

        print(f"[DB] Imported {imported_count} locomotives, skipped {skipped_count}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to import to database: {e}")
        return False


def main():
    """
    Main import workflow.
    """
    print("=" * 60)
    print("JMRI Roster Import: Speed Tables -> Database + Config.json")
    print("=" * 60)
    print()

    # Step 1: Load JMRI roster
    print("[STEP 1/4] Loading JMRI roster XML...")
    locos = load_all_locomotives()

    if not locos:
        print("[ERROR] No locomotives found in JMRI roster")
        print("Make sure JMRI roster files exist in ~/.jmri/roster/")
        return False

    print(f"[ROSTER] Found {len(locos)} locomotives")
    for address, loco in locos.items():
        print(f"  - Loco {address}: {loco.name} ({loco.decoder_model})")
    print()

    # Step 2: Backup config.json
    print("[STEP 2/4] Creating config.json backup...")
    backup_path = backup_config()
    print()

    # Step 3: Import to config.json
    print("[STEP 3/4] Importing to config.json...")
    if not import_to_config(locos):
        print("[ERROR] Config import failed")
        return False
    print()

    # Step 4: Import to database
    print("[STEP 4/4] Importing to database...")
    if not import_to_database(locos):
        print("[ERROR] Database import failed")
        return False
    print()

    # Summary
    print("=" * 60)
    print("IMPORT COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print()
    print(f"Config backup: {backup_path.name}")
    print(f"Config updated: {len(locos)} locomotives in 'locomotives' section")
    print(f"Database updated: CV67-94 imported to locomotive_speed_table")
    print()
    print("Next steps:")
    print("1. Verify config.json: cat config.json | jq '.locomotives'")
    print("2. Verify database: sqlite3 backend/data/analytics.db \"SELECT loco_address, cv67, cv94, source FROM locomotive_speed_table;\"")
    print()

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
