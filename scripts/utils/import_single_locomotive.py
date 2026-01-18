#!/usr/bin/env python3
"""
Import Single Locomotive from JMRI Roster to config.json + Database

What it does:
1. Takes a DCC address as input (e.g., 2, 6)
2. Reads that single locomotive from JMRI roster XML
3. Creates backup of config.json
4. Adds locomotive to config.json (or updates if already exists)
5. Writes CV67-94 to data.db (locomotive_speed_table)
6. Does NOT touch other locomotives in config or DB

Usage:
    cd ~/Documents/_PROGETTI/z21-Terminal
    source venv/bin/activate
    python scripts/utils/import_single_locomotive.py --address 2

    # Dry run (show what would be imported without changing anything)
    python scripts/utils/import_single_locomotive.py --address 2 --dry-run

Safety:
- Automatic config.json backup before modification
- Non-destructive: only adds/updates specified locomotive
- Idempotent: can run multiple times safely
"""

import sys
import sqlite3
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

# Add scripts/utils/cv_operations to path for Locomotive class import
SCRIPT_DIR = Path(__file__).parent.parent.parent / "scripts" / "utils" / "cv_operations"
sys.path.insert(0, str(SCRIPT_DIR))

from read_cv_from_roster import load_all_locomotives

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.json"
DB_PATH = PROJECT_ROOT / "backend" / "data" / "data.db"

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


def backup_config():
    """
    Create timestamped backup of config.json.

    Returns:
        Path to backup file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = CONFIG_PATH.with_suffix(f'.json.backup_{timestamp}')

    shutil.copy2(CONFIG_PATH, backup_path)
    print(f"[OK] Config backup created: {backup_path.name}")

    return backup_path


def load_config() -> dict:
    """Load current config.json."""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config: dict):
    """Save config.json with pretty formatting."""
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"[OK] Config saved: {CONFIG_PATH}")


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
    Create config.json entry for locomotive.

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
            }
        },
        "functions": functions
    }

    return loco_config


def write_speed_table_to_db(loco):
    """
    Write CV67-94 speed table to data.db (locomotive_speed_table table).

    Args:
        loco: Locomotive object from JMRI roster
    """
    # Create table if not exists
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locomotive_speed_table (
            loco_address INTEGER PRIMARY KEY,
            cv_values TEXT NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT DEFAULT 'jmri_import',
            previous_cv_values TEXT,
            previous_updated TIMESTAMP
        )
    """)

    # Get current values if exist (for backup)
    cursor.execute("""
        SELECT cv_values, last_updated
        FROM locomotive_speed_table
        WHERE loco_address = ?
    """, (loco.address,))

    existing_row = cursor.fetchone()
    previous_cv_values = existing_row[0] if existing_row else None
    previous_updated = existing_row[1] if existing_row else None

    # Extract CV67-94 from loco.cv dict
    cv_values = {}
    for cv_index in range(67, 95):  # CV67-94 (28 steps)
        if cv_index in loco.cv:
            cv_values[cv_index] = loco.cv[cv_index]

    # Convert to JSON string
    cv_values_json = json.dumps(cv_values)

    # Insert or replace (with backup of previous values)
    cursor.execute("""
        INSERT OR REPLACE INTO locomotive_speed_table
        (loco_address, cv_values, last_updated, source, previous_cv_values, previous_updated)
        VALUES (?, ?, CURRENT_TIMESTAMP, 'jmri_import', ?, ?)
    """, (loco.address, cv_values_json, previous_cv_values, previous_updated))

    conn.commit()
    conn.close()

    print(f"[OK] Speed table CV67-94 written to database for loco {loco.address}")


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
    print(f"[1/4] Loading locomotive {address} from JMRI roster...")
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
        print(f"[INFO] Locomotive {address} already exists in config.json (will be updated)")
    else:
        print(f"[INFO] Locomotive {address} is NEW (will be added to config.json)")

    if dry_run:
        action = "update" if exists_in_config else "add"
        print(f"\n[DRY RUN] Would {action} in config.json:")
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

    # Step 2: Backup config.json
    print(f"\n[2/4] Creating config.json backup...")
    backup_config()

    # Step 3: Update config.json
    print(f"\n[3/4] Updating config.json...")
    config = load_config()

    # Ensure locomotives section exists
    if 'locomotives' not in config:
        config['locomotives'] = {}

    # Add or update locomotive
    loco_config = create_locomotive_config(loco)
    config['locomotives'][str(address)] = loco_config

    save_config(config)
    print(f"[OK] Locomotive {address} added/updated in config.json")

    # Step 4: Write speed table to database
    print(f"\n[4/4] Writing speed table to database...")
    write_speed_table_to_db(loco)

    print(f"\n{'='*60}")
    print(f"[SUCCESS] Import Complete!")
    print(f"{'='*60}")
    print(f"\nLocomotive {address} ({loco.name}) imported successfully")
    print(f"Next steps:")
    print(f"  1. Verify config.json → locomotives.{address}")
    print(f"  2. Restart backend to load new locomotive")
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
