"""
Migration Script: Operational State config.json → data.db

Moves operational state from config.json to database:
- consist_state table: virtual_mode, auto_compensation_enabled per consist
- system_state table: test_mode global state

Usage:
    python scripts/utils/migrate_operational_state.py

Requirements:
    - config.json must exist with operational state data
    - backend/data/data.db will be created/updated with new tables
    - Backup of config.json created before modification

Phase: DB Refactoring Phase 2
Date: 2026-01-18
"""

import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Paths (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.json"
DB_PATH = PROJECT_ROOT / "backend" / "data" / "data.db"
BACKUP_DIR = PROJECT_ROOT / "backups"


def create_backup(filepath):
    """Create timestamped backup of file."""
    if not filepath.exists():
        print(f"[WARN]  File not found: {filepath}")
        return None

    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"{filepath.name}.backup.{timestamp}"

    import shutil
    shutil.copy2(filepath, backup_path)
    print(f"[OK] Backup created: {backup_path}")
    return backup_path


def create_tables(conn):
    """Create consist_state and system_state tables."""
    cursor = conn.cursor()

    # Create consist_state table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consist_state (
            consist_id INTEGER PRIMARY KEY,
            virtual_mode BOOLEAN NOT NULL DEFAULT 1,
            auto_compensation_enabled BOOLEAN NOT NULL DEFAULT 1,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create system_state table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    print("[OK] Database tables created (consist_state, system_state)")


def migrate_data(config, conn):
    """Migrate operational state from config.json to database."""
    cursor = conn.cursor()
    migrated_count = 0

    # Migrate consist states
    consists = config.get("consists", {})
    for consist_id_str, consist_data in consists.items():
        consist_id = int(consist_id_str)
        virtual_mode = consist_data.get("virtual_mode", True)
        auto_compensation = consist_data.get("auto_compensation_enabled", True)

        cursor.execute("""
            INSERT INTO consist_state (consist_id, virtual_mode, auto_compensation_enabled, last_updated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(consist_id) DO UPDATE SET
                virtual_mode = excluded.virtual_mode,
                auto_compensation_enabled = excluded.auto_compensation_enabled,
                last_updated = CURRENT_TIMESTAMP
        """, (consist_id, virtual_mode, auto_compensation))

        print(f"   Consist {consist_id}: virtual_mode={virtual_mode}, auto_compensation={auto_compensation}")
        migrated_count += 1

    # Migrate test_mode (global state)
    test_mode = config.get("test_mode", "normal")
    cursor.execute("""
        INSERT INTO system_state (key, value, last_updated)
        VALUES ('test_mode', ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            last_updated = CURRENT_TIMESTAMP
    """, (test_mode,))
    print(f"   System: test_mode={test_mode}")
    migrated_count += 1

    conn.commit()
    print(f"[OK] Migrated {migrated_count} operational state entries")
    return migrated_count


def remove_from_config(config):
    """Remove operational state from config.json (keep only configuration)."""
    removed_keys = []

    # Remove consist operational state
    consists = config.get("consists", {})
    for consist_id, consist_data in consists.items():
        if "virtual_mode" in consist_data:
            del consist_data["virtual_mode"]
            removed_keys.append(f"consists.{consist_id}.virtual_mode")

        if "auto_compensation_enabled" in consist_data:
            del consist_data["auto_compensation_enabled"]
            removed_keys.append(f"consists.{consist_id}.auto_compensation_enabled")

    # Remove global test_mode
    if "test_mode" in config:
        del config["test_mode"]
        removed_keys.append("test_mode")

    return removed_keys


def verify_migration(conn):
    """Verify data was migrated correctly."""
    cursor = conn.cursor()

    # Check consist_state
    cursor.execute("SELECT COUNT(*) FROM consist_state")
    consist_count = cursor.fetchone()[0]

    # Check system_state
    cursor.execute("SELECT COUNT(*) FROM system_state WHERE key = 'test_mode'")
    system_count = cursor.fetchone()[0]

    print(f"[OK] Verification: {consist_count} consists, {system_count} system state entries")

    if consist_count == 0 or system_count == 0:
        print("[WARN]  Warning: Migration may be incomplete")
        return False

    return True


def main():
    """Main migration workflow."""
    print("\n" + "="*70)
    print("MIGRATION: Operational State config.json -> data.db")
    print("="*70 + "\n")

    # Step 1: Validate files exist
    print("[1/7] Validating files...")
    if not CONFIG_PATH.exists():
        print(f"[ERROR] Error: config.json not found at {CONFIG_PATH}")
        sys.exit(1)

    if not DB_PATH.exists():
        print(f"[WARN]  Warning: Database not found at {DB_PATH}")
        print("   Creating new database...")

    print(f"   Config: {CONFIG_PATH}")
    print(f"   Database: {DB_PATH}")

    # Step 2: Backup config.json
    print("\n[2/7] Creating backup...")
    backup_path = create_backup(CONFIG_PATH)
    if not backup_path:
        print("[ERROR] Error: Failed to create backup")
        sys.exit(1)

    # Step 3: Load config.json
    print("\n[3/7] Loading config.json...")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    print(f"   Loaded {len(config)} top-level keys")

    # Step 4: Connect to database and create tables
    print("\n[4/7] Setting up database...")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)

    # Step 5: Migrate data
    print("\n[5/7] Migrating operational state...")
    migrated_count = migrate_data(config, conn)

    # Step 6: Verify migration
    print("\n[6/7] Verifying migration...")
    if not verify_migration(conn):
        print("[ERROR] Error: Migration verification failed")
        conn.close()
        sys.exit(1)

    conn.close()

    # Step 7: Update config.json (remove operational state)
    print("\n[7/7] Cleaning config.json...")
    removed_keys = remove_from_config(config)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"   Removed {len(removed_keys)} operational state keys:")
    for key in removed_keys:
        print(f"     - {key}")

    # Summary
    print("\n" + "="*70)
    print("[OK] MIGRATION COMPLETE")
    print("="*70)
    print(f"   Migrated entries: {migrated_count}")
    print(f"   Config backup: {backup_path}")
    print(f"   Database: {DB_PATH}")
    print(f"   Config cleaned: {CONFIG_PATH}")
    print("\nNext steps:")
    print("   1. Test backend with new database structure")
    print("   2. Deploy to PC production (rename DB + deploy code)")
    print("   3. Verify operational state persists across restarts")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
