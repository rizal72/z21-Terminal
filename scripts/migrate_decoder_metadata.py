#!/usr/bin/env python3
"""
ONE-SHOT Script: Migrate Decoder Metadata to Database

Populates vstart (CV2), vhigh (CV5), and decoder_type columns in locomotive_speed_table.

**Requirements**:
- JMRI roster XML files (reads CV2, CV5, decoder model)
- Existing CV67-94 data in database (already imported)

**What it does**:
1. Reads CV2 (Vstart) and CV5 (Vhigh) from JMRI roster for all locomotives
2. Detects decoder type from JMRI roster (manufacturer + model)
3. If ESU decoder: enforces CV67=1, CV94=255 (mfx fixed endpoints)
4. Updates database with vstart, vhigh, decoder_type (and CV67/CV94 if corrected)

**Usage**:
    python scripts/migrate_decoder_metadata.py

**IMPORTANT**:
- Run on Mac (requires JMRI roster access)
- Run ONCE, then copy database to PC
- Can be deleted after execution (one-time migration)

**Author**: Claude + Riccardo
**Date**: 2026-01-20
"""

import sys
import sqlite3
from pathlib import Path

# Add utils/cv_operations to path for Locomotive class
SCRIPT_DIR = Path(__file__).parent / "utils" / "cv_operations"
sys.path.insert(0, str(SCRIPT_DIR))

from read_cv_from_roster import load_all_locomotives

# Add backend to path for decoder helpers
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from services.decoder_helpers import DECODER_TYPE_MAP

# Database path
DB_PATH = Path(__file__).parent.parent / "backend" / "data" / "data.db"


def detect_decoder_type_from_roster(loco) -> str:
    """
    Detect decoder type from JMRI roster locomotive object.

    Args:
        loco: Locomotive object with decoder_mfg and decoder_model attributes

    Returns:
        'esu_mfx' or 'nmra_standard'
    """
    decoder_model = loco.decoder_model or ""

    # Check against known patterns
    for key, value in DECODER_TYPE_MAP.items():
        if key in decoder_model:
            return value

    # Default to NMRA standard
    return "nmra_standard"


def migrate_locomotive(loco_address: int, loco) -> bool:
    """
    Migrate single locomotive decoder metadata to database.

    Args:
        loco_address: Locomotive DCC address
        loco: Locomotive object from JMRI roster

    Returns:
        True if successful, False otherwise
    """
    # Read CV2 (Vstart) and CV5 (Vhigh) from JMRI
    vstart = loco.cv.get(2)
    vhigh = loco.cv.get(5)

    # Detect decoder type
    decoder_type = detect_decoder_type_from_roster(loco)

    print(f"[Loco {loco_address}] CV2={vstart}, CV5={vhigh}, decoder={decoder_type}")

    # Read current CV67-94 from database
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cv67, cv94
        FROM locomotive_speed_table
        WHERE loco_address = ?
    """, (loco_address,))

    row = cursor.fetchone()

    if not row:
        print(f"[Loco {loco_address}] ERROR: Not found in database. Run import_single_locomotive.py first.")
        conn.close()
        return False

    cv67_current = row[0]
    cv94_current = row[1]

    # Check if ESU needs correction
    needs_cv67_fix = False
    needs_cv94_fix = False

    if decoder_type == "esu_mfx":
        if cv67_current != 1:
            print(f"[Loco {loco_address}] ESU: CV67 correction needed ({cv67_current} → 1)")
            needs_cv67_fix = True
        if cv94_current != 255:
            print(f"[Loco {loco_address}] ESU: CV94 correction needed ({cv94_current} → 255)")
            needs_cv94_fix = True

    # Update database
    if needs_cv67_fix or needs_cv94_fix:
        # Update vstart, vhigh, decoder_type + CV67/CV94 correction
        cursor.execute("""
            UPDATE locomotive_speed_table
            SET vstart = ?, vhigh = ?, decoder_type = ?, cv67 = ?, cv94 = ?
            WHERE loco_address = ?
        """, (vstart, vhigh, decoder_type, 1 if needs_cv67_fix else cv67_current, 255 if needs_cv94_fix else cv94_current, loco_address))
        print(f"[Loco {loco_address}] Updated decoder metadata + corrected ESU fixed values")
    else:
        # Update only vstart, vhigh, decoder_type
        cursor.execute("""
            UPDATE locomotive_speed_table
            SET vstart = ?, vhigh = ?, decoder_type = ?
            WHERE loco_address = ?
        """, (vstart, vhigh, decoder_type, loco_address))
        print(f"[Loco {loco_address}] Updated decoder metadata")

    conn.commit()
    conn.close()

    return True


def main():
    """Main migration function"""
    print("=" * 60)
    print("ONE-SHOT Decoder Metadata Migration")
    print("=" * 60)
    print()

    # Check database exists
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Please run the backend at least once to create the database.")
        sys.exit(1)

    # Step 1: Add columns (idempotent, safe to run multiple times)
    print("Step 1: Adding vstart/vhigh/decoder_type columns to database...")
    from services.data_db import DataDB
    DataDB.migrate_speed_table_decoder_support()
    print()

    # Load all locomotives from JMRI roster
    print("Loading locomotives from JMRI roster...")
    locos = load_all_locomotives()

    if not locos:
        print("ERROR: No locomotives found in JMRI roster")
        print("Please ensure JMRI roster XML files exist in roster/ directory")
        sys.exit(1)

    print(f"Found {len(locos)} locomotives in JMRI roster")
    print()

    # Migrate each locomotive
    success_count = 0
    failed_count = 0

    for loco_address_str, loco in locos.items():
        loco_address = int(loco_address_str)

        try:
            if migrate_locomotive(loco_address, loco):
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"[Loco {loco_address}] ERROR: {e}")
            failed_count += 1

        print()

    # Summary
    print("=" * 60)
    print(f"Migration complete: {success_count} success, {failed_count} failed")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Test speed table viewer on Mac")
    print("2. Copy database to PC: scp backend/data/data.db riccardo@gaming-pc:C:/z21-Terminal/backend/data/")
    print("3. Delete this script (one-time use only)")


if __name__ == "__main__":
    main()
