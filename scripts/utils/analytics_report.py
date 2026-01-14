#!/usr/bin/env python3
"""
Analytics Report Generator
Analyzes speed matching behavior from analytics database
"""

import sqlite3
import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Database path (relative to script location or absolute)
DB_PATH = Path(__file__).parent.parent.parent / "backend" / "data" / "analytics.db"


def get_sessions(conn, limit=10):
    """Get recent sessions"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, start_time, end_time, validated, event_count
        FROM sessions
        WHERE validated = 1
        ORDER BY start_time DESC
        LIMIT ?
    """, (limit,))

    sessions = []
    for row in cursor.fetchall():
        session_id, start_time, end_time, validated, event_count = row
        sessions.append({
            'id': session_id,
            'start_time': datetime.fromtimestamp(start_time),
            'end_time': datetime.fromtimestamp(end_time) if end_time else None,
            'duration_min': (end_time - start_time) / 60 if end_time else None,
            'event_count': event_count
        })

    return sessions


def analyze_session(conn, session_id):
    """Analyze Δt patterns for a specific session"""
    cursor = conn.cursor()

    # Get all delta_t events for this session
    cursor.execute("""
        SELECT timestamp, data
        FROM events
        WHERE session_id = ? AND event_type = 'delta_t'
        ORDER BY timestamp
    """, (session_id,))

    events = []
    for row in cursor.fetchall():
        timestamp, data_json = row
        data = json.loads(data_json)
        events.append({
            'timestamp': datetime.fromtimestamp(timestamp),
            'consist_id': data['consist_id'],
            'delta_t': data['delta_t'],
            'status': data['status']
        })

    if not events:
        return None

    # Aggregate statistics per consist
    stats = defaultdict(lambda: {
        'count': 0,
        'delta_t_values': [],
        'synced': 0,
        'warning': 0,
        'critical': 0
    })

    for event in events:
        cid = event['consist_id']
        delta_t = event['delta_t']
        status = event['status']

        stats[cid]['count'] += 1
        stats[cid]['delta_t_values'].append(delta_t)

        if status == 'SYNCED':
            stats[cid]['synced'] += 1
        elif status == 'WARNING':
            stats[cid]['warning'] += 1
        elif status == 'CRITICAL':
            stats[cid]['critical'] += 1

    # Calculate averages and patterns
    for cid in stats:
        values = stats[cid]['delta_t_values']
        stats[cid]['avg_delta_t'] = sum(values) / len(values)
        stats[cid]['min_delta_t'] = min(values)
        stats[cid]['max_delta_t'] = max(values)

        # Detect trend: positive avg = lead is faster, negative = rear is faster
        avg = stats[cid]['avg_delta_t']
        if avg > 0.2:
            stats[cid]['trend'] = 'LEAD FASTER (rear catching up)'
        elif avg < -0.2:
            stats[cid]['trend'] = 'REAR FASTER (lead catching up)'
        else:
            stats[cid]['trend'] = 'BALANCED'

    return {
        'session_id': session_id,
        'total_events': len(events),
        'consists': dict(stats)
    }


def print_report(sessions, analysis):
    """Print formatted report"""
    print("=" * 80)
    print("ANALYTICS REPORT - Speed Matching Analysis")
    print("=" * 80)
    print()

    # Recent sessions summary
    print("RECENT SESSIONS:")
    print("-" * 80)
    for i, session in enumerate(sessions, 1):
        status = "✓ CLOSED" if session['end_time'] else "⏱ RUNNING"
        duration = f"{session['duration_min']:.1f} min" if session['duration_min'] else "N/A"
        print(f"{i}. {session['id']} | {status} | Duration: {duration} | Events: {session['event_count']}")
    print()

    if not analysis:
        print("No Δt events found in selected session.")
        return

    # Detailed analysis
    print(f"SESSION ANALYSIS: {analysis['session_id']}")
    print("-" * 80)
    print(f"Total Gate Crossings: {analysis['total_events']}")
    print()

    for consist_id, stats in sorted(analysis['consists'].items()):
        print(f"CONSIST {consist_id}:")
        print(f"  Total Crossings: {stats['count']}")
        print(f"  Average Δt: {stats['avg_delta_t']:+.3f}s")
        print(f"  Range: {stats['min_delta_t']:+.3f}s to {stats['max_delta_t']:+.3f}s")
        print(f"  Trend: {stats['trend']}")
        print(f"  Status Distribution:")
        print(f"    - SYNCED: {stats['synced']} ({stats['synced']/stats['count']*100:.1f}%)")
        print(f"    - WARNING: {stats['warning']} ({stats['warning']/stats['count']*100:.1f}%)")
        print(f"    - CRITICAL: {stats['critical']} ({stats['critical']/stats['count']*100:.1f}%)")
        print()

    print("=" * 80)
    print("INTERPRETATION:")
    print("- Positive Δt: Lead locomotive arrives first (rear is slower)")
    print("- Negative Δt: Rear locomotive arrives first (lead is slower)")
    print("- Consist 11: Loco 7 (lead) + Loco 8 (rear)")
    print("=" * 80)


def main():
    """Main entry point"""
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))

    # Get recent sessions
    sessions = get_sessions(conn, limit=10)

    if not sessions:
        print("No sessions found in database.")
        conn.close()
        return

    # Analyze most recent session (or specify session_id as arg)
    target_session = sessions[0]['id']
    if len(sys.argv) > 1:
        target_session = sys.argv[1]

    analysis = analyze_session(conn, target_session)

    print_report(sessions, analysis)

    conn.close()


if __name__ == '__main__':
    main()
