#!/usr/bin/env python3
"""
One-time migration: Backfill locomotive operating time from existing consist sessions.

Assumption: Locomotives in same consist always operated together (same duration).

Run once after deploying locomotive_stats table schema:
    python scripts/migrate_operating_time.py
"""

import sqlite3
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def migrate_existing_sessions():
    """
    Calculate locomotive operating time from existing consist sessions.

    Logic:
    1. For each validated session, check which consists were active (has delta_t events)
    2. Map consist to locomotives (C10=1,5 | C11=7,8)
    3. Assign session duration to each loco in that consist
    4. Create loco_operating_time events + update locomotive_stats table
    """

    # Database path (relative to project root)
    db_path = Path(__file__).parent.parent / 'data' / 'analytics.db'

    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        print("Run the backend at least once to create analytics.db")
        return False

    print(f"[INFO] Connecting to {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Get all validated sessions
    cursor.execute('SELECT id, start_time, end_time FROM sessions WHERE validated = 1 ORDER BY start_time')
    sessions = cursor.fetchall()

    if not sessions:
        print("[INFO] No validated sessions found - nothing to migrate")
        conn.close()
        return True

    print(f"[INFO] Found {len(sessions)} validated sessions to process")

    # Consist to locomotive mapping
    CONSIST_LOCOS = {
        10: [1, 5],  # Consist 10: Gr.675 017, D645 014
        11: [7, 8],  # Consist 11: E656 239, E444 056
    }

    migrated_events = 0
    skipped_sessions = 0

    for session_id, start_time, end_time in sessions:
        if not end_time:
            print(f"[SKIP] Session {session_id} has no end_time")
            skipped_sessions += 1
            continue

        duration = end_time - start_time

        if duration <= 0:
            print(f"[SKIP] Session {session_id} has invalid duration: {duration}")
            skipped_sessions += 1
            continue

        # Check which consists were active in this session
        cursor.execute('''
            SELECT DISTINCT json_extract(data, '$.consist_id') as consist_id
            FROM events
            WHERE session_id = ? AND event_type = 'delta_t'
        ''', (session_id,))

        active_consists = cursor.fetchall()

        if not active_consists:
            print(f"[SKIP] Session {session_id} has no delta_t events")
            skipped_sessions += 1
            continue

        for (consist_id,) in active_consists:
            if consist_id not in CONSIST_LOCOS:
                print(f"[WARN] Unknown consist_id {consist_id} in session {session_id}")
                continue

            addresses = CONSIST_LOCOS[consist_id]

            # Log operating time event for each loco in consist
            for address in addresses:
                # Create event in events table
                event_data = {
                    'address': address,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_seconds': duration,
                    'session_id': session_id,
                    'consist_id': consist_id
                }

                cursor.execute('''
                    INSERT INTO events (session_id, timestamp, event_type, data)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, end_time, 'loco_operating_time', json.dumps(event_data)))

                # Update aggregate stats in locomotive_stats table
                cursor.execute('''
                    INSERT INTO locomotive_stats (address, total_operating_seconds, total_sessions, last_active_time, created_at, updated_at)
                    VALUES (?, ?, 1, ?, ?, ?)
                    ON CONFLICT(address) DO UPDATE SET
                        total_operating_seconds = total_operating_seconds + ?,
                        total_sessions = total_sessions + 1,
                        last_active_time = MAX(last_active_time, ?),
                        updated_at = ?
                ''', (address, duration, end_time, start_time, end_time,
                      duration, end_time, end_time))

                migrated_events += 1

    conn.commit()

    # Print summary
    cursor.execute('SELECT address, total_operating_seconds FROM locomotive_stats ORDER BY address')
    stats = cursor.fetchall()

    print("\n" + "="*60)
    print(f"[SUCCESS] Migration complete!")
    print(f"  Sessions processed: {len(sessions) - skipped_sessions}/{len(sessions)}")
    print(f"  Events created: {migrated_events}")
    print(f"  Skipped sessions: {skipped_sessions}")
    print("\nLocomotives operating time:")
    for address, total_seconds in stats:
        hours = total_seconds / 3600
        print(f"  Loco {address}: {hours:.2f} hours ({total_seconds} seconds)")
    print("="*60)

    conn.close()
    return True


if __name__ == '__main__':
    success = migrate_existing_sessions()
    sys.exit(0 if success else 1)
