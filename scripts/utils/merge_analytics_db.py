"""
Merge analytics.db → data.db (Phase 1 cleanup)

Copies sessions and events from old analytics.db to data.db.
Safe to run multiple times (uses ON CONFLICT IGNORE for idempotency).

Usage:
    python scripts/utils/merge_analytics_db.py
"""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
OLD_DB = PROJECT_ROOT / "backend" / "data" / "analytics.db"
NEW_DB = PROJECT_ROOT / "backend" / "data" / "data.db"


def merge_databases():
    """Merge sessions and events from analytics.db to data.db"""

    if not OLD_DB.exists():
        print(f"[OK] No old database found at {OLD_DB}")
        print("     Migration not needed")
        return

    if not NEW_DB.exists():
        print(f"[ERROR] New database not found at {NEW_DB}")
        print("        Create it first with migration script")
        return

    print("="*70)
    print("MERGE: analytics.db -> data.db")
    print("="*70)

    # Connect to both databases
    old_conn = sqlite3.connect(OLD_DB)
    new_conn = sqlite3.connect(NEW_DB)

    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()

    # Count records in old DB
    old_cursor.execute("SELECT COUNT(*) FROM sessions")
    old_sessions = old_cursor.fetchone()[0]

    old_cursor.execute("SELECT COUNT(*) FROM events")
    old_events = old_cursor.fetchone()[0]

    print(f"\nOld DB (analytics.db):")
    print(f"  Sessions: {old_sessions}")
    print(f"  Events: {old_events}")

    # Count records in new DB (before merge)
    new_cursor.execute("SELECT COUNT(*) FROM sessions")
    new_sessions_before = new_cursor.fetchone()[0]

    new_cursor.execute("SELECT COUNT(*) FROM events")
    new_events_before = new_cursor.fetchone()[0]

    print(f"\nNew DB (data.db) - BEFORE merge:")
    print(f"  Sessions: {new_sessions_before}")
    print(f"  Events: {new_events_before}")

    # Copy sessions
    print("\n[1/2] Copying sessions...")
    old_cursor.execute("SELECT id, start_time, end_time, validated FROM sessions")
    sessions = old_cursor.fetchall()

    copied_sessions = 0
    newly_copied_session_ids = []
    for session in sessions:
        try:
            new_cursor.execute("""
                INSERT OR IGNORE INTO sessions (id, start_time, end_time, validated)
                VALUES (?, ?, ?, ?)
            """, session)
            if new_cursor.rowcount > 0:
                copied_sessions += 1
                newly_copied_session_ids.append(session[0])  # Track newly copied sessions
        except Exception as e:
            print(f"  Warning: Failed to copy session {session[0]}: {e}")

    print(f"  Copied {copied_sessions} new sessions")

    # Copy events (only for newly copied sessions to avoid duplicates)
    print("\n[2/2] Copying events...")

    if not newly_copied_session_ids:
        print("  No new sessions copied - skipping events (idempotent)")
        copied_events = 0
    else:
        # Build placeholders for IN clause
        placeholders = ','.join('?' * len(newly_copied_session_ids))
        old_cursor.execute(f"""
            SELECT session_id, timestamp, event_type, data
            FROM events
            WHERE session_id IN ({placeholders})
        """, newly_copied_session_ids)
        events = old_cursor.fetchall()

        copied_events = 0
        for event in events:
            try:
                new_cursor.execute("""
                    INSERT INTO events (session_id, timestamp, event_type, data)
                    VALUES (?, ?, ?, ?)
                """, event)
                copied_events += 1
            except Exception as e:
                print(f"  Warning: Failed to copy event: {e}")

        print(f"  Copied {copied_events} events for {len(newly_copied_session_ids)} new sessions")

    # Commit changes
    new_conn.commit()

    # Count records in new DB (after merge)
    new_cursor.execute("SELECT COUNT(*) FROM sessions")
    new_sessions_after = new_cursor.fetchone()[0]

    new_cursor.execute("SELECT COUNT(*) FROM events")
    new_events_after = new_cursor.fetchone()[0]

    print(f"\nNew DB (data.db) - AFTER merge:")
    print(f"  Sessions: {new_sessions_after} (+{new_sessions_after - new_sessions_before})")
    print(f"  Events: {new_events_after} (+{new_events_after - new_events_before})")

    # Close connections
    old_conn.close()
    new_conn.close()

    print("\n" + "="*70)
    print("[OK] MERGE COMPLETE")
    print("="*70)
    print(f"  Old DB: {OLD_DB}")
    print(f"  New DB: {NEW_DB}")
    print(f"  Merged: {copied_sessions} sessions, {copied_events} events")
    print("\nYou can now delete analytics.db if no longer needed:")
    print(f"  rm {OLD_DB}")
    print("="*70)


if __name__ == "__main__":
    merge_databases()
