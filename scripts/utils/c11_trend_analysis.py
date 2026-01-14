#!/usr/bin/env python3
"""
Consist 11 Historical Trend Analysis
Analizza il comportamento di loco 7 (Hornby) nel tempo
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def analyze_c11_trend():
    db_path = Path(__file__).parent.parent.parent / "backend" / "data" / "analytics.db"

    if not db_path.exists():
        print(f"ERROR: Database not found: {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Get all validated sessions
    cursor.execute("""
        SELECT id, start_time, end_time
        FROM sessions
        WHERE validated = 1
        ORDER BY start_time DESC
        LIMIT 30
    """)

    sessions = cursor.fetchall()

    if not sessions:
        print("ERROR: No validated sessions found")
        conn.close()
        return

    print("=" * 110)
    print("CONSIST 11 HISTORICAL TREND ANALYSIS")
    print("=" * 110)
    print("Loco 7 (Hornby TXS, adjust) vs Loco 8 (ESU, reference)")
    print("dT = rear_time - lead_time")
    print("  NEGATIVE dT = Loco 7 (lead) FASTER (arrives first)")
    print("  POSITIVE dT = Loco 8 (rear) FASTER (arrives first, loco 7 slower)")
    print("=" * 110)
    print()

    print(f"{'Session':<17} {'Date':<12} {'Events':>6} {'Avg dT':>8} {'Range':>18} {'Synced%':>8}  {'Trend':<25}")
    print("-" * 110)

    # Process sessions in chronological order (oldest first)
    for session_id, start_time, end_time in reversed(sessions):
        # Get delta_t events for C11
        cursor.execute("""
            SELECT data
            FROM events
            WHERE session_id = ? AND event_type = 'delta_t'
        """, (session_id,))

        events = []
        for (data_json,) in cursor.fetchall():
            data = json.loads(data_json)
            if data.get('consist_id') == 11:
                events.append(data)

        if not events:
            continue

        # Calculate statistics
        delta_t_values = [e['delta_t'] for e in events]
        avg_dt = sum(delta_t_values) / len(delta_t_values)
        min_dt = min(delta_t_values)
        max_dt = max(delta_t_values)

        synced = sum(1 for e in events if e.get('status') == 'SYNCED')
        synced_pct = (synced / len(events) * 100)

        # Parse date
        date = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d")

        # Trend indicator
        if avg_dt < -0.5:
            trend = "[RED] L7 FASTER"
        elif avg_dt > 0.5:
            trend = "[GREEN] L8 FASTER (L7 slower)"
        else:
            trend = "[YELLOW] BALANCED"

        print(f"{session_id:<17} {date:<12} {len(events):>6} {avg_dt:>7.2f}s {min_dt:>7.2f}s to {max_dt:>+6.2f}s {synced_pct:>7.1f}%  {trend}")

    conn.close()

    print()
    print("=" * 110)
    print("INTERPRETATION:")
    print("  - Look for trend changes: when did average dT flip from positive to negative?")
    print("  - Positive dT (green): Normal behavior, loco 7 was historically slower")
    print("  - Negative dT (red): Abnormal behavior, loco 7 suddenly faster")
    print("  - Possible causes: Hornby decoder drift, CV changes, mechanical issues, temperature")
    print("=" * 110)

if __name__ == "__main__":
    analyze_c11_trend()
