"""
Data Database Service

Centralizes all SQLite3 database access:
- Analytics (sessions, speed_data)
- Speed Tables (cv_speed_table)
- Operational State (consist_state, system_state)

Eliminates code duplication across endpoints.
"""

from pathlib import Path
import sqlite3
import json
import time
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime

# Database path (relative to this service file)
DB_PATH = Path(__file__).parent.parent / "data" / "analytics.db"


class DataDB:
    """Centralized database access layer - analytics, speed tables, operational state"""

    @staticmethod
    def get_connection() -> sqlite3.Connection:
        """Get database connection"""
        return sqlite3.connect(str(DB_PATH))

    @staticmethod
    def get_latest_session() -> Optional[Dict]:
        """
        Get most recent session from database (validated or not).

        Returns:
            Session dict with id, start_time, end_time, validated, event_count
            or None if no sessions exist
        """
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, start_time, end_time, validated, event_count
            FROM sessions
            ORDER BY start_time DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'id': row[0],
            'start_time': row[1],
            'end_time': row[2],
            'validated': bool(row[3]),
            'event_count': row[4],
            'duration': row[2] - row[1] if row[2] else None
        }

    @staticmethod
    def get_validated_sessions(limit: Optional[int] = None, exclude_running: bool = False) -> List[Dict]:
        """
        Get validated sessions from database.

        Args:
            limit: Maximum number of sessions to return (most recent first)
            exclude_running: If True, exclude sessions with NULL end_time

        Returns:
            List of session dicts with id, start_time, end_time, event_count, duration
        """
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        query = "SELECT id, start_time, end_time, event_count FROM sessions WHERE validated = 1"
        if exclude_running:
            query += " AND end_time IS NOT NULL"
        query += " ORDER BY start_time DESC"
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'id': row[0],
                'start_time': row[1],
                'end_time': row[2],
                'event_count': row[3],
                'duration': row[2] - row[1] if row[2] else None
            })

        conn.close()
        return sessions

    @staticmethod
    def get_delta_t_events(session_id: Optional[str] = None) -> List[Dict]:
        """
        Get delta_t events from database.

        Args:
            session_id: Optional session ID to filter by

        Returns:
            List of delta_t event dicts with session_id, timestamp, consist_id, delta_t, status, gate_type
        """
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        if session_id:
            cursor.execute(
                "SELECT session_id, timestamp, data FROM events WHERE session_id = ? AND event_type = 'delta_t' ORDER BY timestamp",
                (session_id,)
            )
        else:
            cursor.execute(
                "SELECT session_id, timestamp, data FROM events WHERE event_type = 'delta_t' ORDER BY timestamp"
            )

        events = []
        for row in cursor.fetchall():
            data = json.loads(row[2])
            events.append({
                'session_id': row[0],
                'timestamp': row[1],
                'consist_id': data['consist_id'],
                'delta_t': data['delta_t'],
                'status': data['status'],
                'gate_type': data['gate_type']
            })

        conn.close()
        return events

    @staticmethod
    def get_yolo_performance_events(session_id: Optional[str] = None) -> List[Dict]:
        """
        Get YOLO performance events from database.

        Args:
            session_id: Optional session ID to filter by

        Returns:
            List of YOLO event dicts with session_id, timestamp, avg_fps, avg_confidence, miss_rate
        """
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        if session_id:
            cursor.execute(
                "SELECT session_id, timestamp, data FROM events WHERE session_id = ? AND event_type = 'yolo_performance' ORDER BY timestamp",
                (session_id,)
            )
        else:
            cursor.execute(
                "SELECT session_id, timestamp, data FROM events WHERE event_type = 'yolo_performance' ORDER BY timestamp"
            )

        events = []
        for row in cursor.fetchall():
            data = json.loads(row[2])
            events.append({
                'session_id': row[0],
                'timestamp': row[1],
                'avg_fps': data.get('avg_fps', 0),
                'avg_confidence': data.get('avg_confidence', {}),
                'miss_rate': data.get('miss_rate', 0)
            })

        conn.close()
        return events

    @staticmethod
    def get_loco_operating_time_events(session_id: Optional[str] = None) -> List[Dict]:
        """
        Get locomotive operating time events from database.

        Args:
            session_id: Optional session ID to filter by

        Returns:
            List of operating time event dicts with session_id, timestamp, address, duration_seconds, start_time, end_time
        """
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        if session_id:
            cursor.execute(
                "SELECT session_id, timestamp, data FROM events WHERE session_id = ? AND event_type = 'loco_operating_time' ORDER BY timestamp",
                (session_id,)
            )
        else:
            cursor.execute(
                "SELECT session_id, timestamp, data FROM events WHERE event_type = 'loco_operating_time' ORDER BY timestamp"
            )

        events = []
        for row in cursor.fetchall():
            data = json.loads(row[2])
            events.append({
                'session_id': row[0],
                'timestamp': row[1],
                'address': data.get('address'),
                'duration_seconds': data.get('duration_seconds'),
                'start_time': data.get('start_time'),
                'end_time': data.get('end_time')
            })

        conn.close()
        return events

    @staticmethod
    def get_locomotive_stats() -> List[Dict]:
        """
        Get aggregated locomotive operating time statistics.

        Returns:
            List of locomotive stats with address, name, total_operating_seconds, total_sessions, last_active_time
        """
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                address,
                name,
                total_operating_seconds,
                total_sessions,
                last_active_time,
                created_at
            FROM locomotive_stats
            ORDER BY address
        ''')

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                'address': row[0],
                'name': row[1] or f"Loco {row[0]}",
                'total_operating_hours': round(row[2] / 3600, 2) if row[2] else 0,
                'total_operating_seconds': row[2],
                'total_sessions': row[3],
                'last_active_time': row[4],
                'created_at': row[5]
            }
            for row in rows
        ]

    @staticmethod
    def get_gate_crossings_aggregate() -> Dict[int, int]:
        """
        Get gate crossings count per consist.

        Returns:
            Dict mapping consist_id to total crossing count
        """
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT data FROM events WHERE event_type = 'delta_t'")
        gate_crossings = defaultdict(int)
        for row in cursor.fetchall():
            data = json.loads(row[0])
            gate_crossings[data['consist_id']] += 1

        conn.close()
        return dict(gate_crossings)

    @staticmethod
    def get_session_by_id(session_id: str) -> Optional[Dict]:
        """
        Get specific session with all delta_t events.

        Args:
            session_id: Session ID to query

        Returns:
            Dict with session metadata and events list, or None if not found
        """
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        # Get session metadata
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session_row = cursor.fetchone()
        if not session_row:
            conn.close()
            return None

        session_data = {
            'id': session_row[0],
            'start_time': session_row[1],
            'end_time': session_row[2],
            'validated': bool(session_row[3]),
            'event_count': session_row[4]
        }

        # Get all delta_t events for this session
        cursor.execute(
            "SELECT timestamp, data FROM events WHERE session_id = ? AND event_type = 'delta_t' ORDER BY timestamp",
            (session_id,)
        )

        events = []
        for row in cursor.fetchall():
            data = json.loads(row[1])
            events.append({
                'timestamp': row[0],
                'consist_id': data['consist_id'],
                'delta_t': data['delta_t'],
                'status': data['status'],
                'gate_type': data['gate_type']
            })

        conn.close()

        return {
            'session': session_data,
            'events': events
        }

    @staticmethod
    def get_reports_data(limit: int = 30, consist_filter: Optional[int] = None, format_duration_callback=None) -> List[Dict]:
        """
        Get session-by-session reports with aggregated statistics.

        Args:
            limit: Number of sessions to return (max 100)
            consist_filter: Optional consist ID to filter by
            format_duration_callback: Optional callback function for duration formatting (e.g., format_duration_hms)

        Returns:
            List of session dicts with id, date, duration, consists statistics
        """
        # Cap limit
        if limit > 100:
            limit = 100

        conn = DataDB.get_connection()
        cursor = conn.cursor()

        # Get validated sessions (include running sessions for real-time display)
        cursor.execute("""
            SELECT id, start_time, end_time, event_count
            FROM sessions
            WHERE validated = 1
            ORDER BY start_time DESC
            LIMIT ?
        """, (limit,))

        sessions = cursor.fetchall()

        if not sessions:
            conn.close()
            return []

        result_sessions = []

        for session_id, start_time, end_time, event_count in sessions:
            # Get all delta_t events for this session
            cursor.execute("""
                SELECT data
                FROM events
                WHERE session_id = ? AND event_type = 'delta_t'
                ORDER BY timestamp
            """, (session_id,))

            event_rows = cursor.fetchall()

            if not event_rows:
                # Skip sessions with no delta_t events
                continue

            # Parse events and group by consist
            consist_data = defaultdict(lambda: {
                'delta_t_values': [],
                'synced_count': 0,
                'warning_count': 0,
                'critical_count': 0
            })

            for (data_json,) in event_rows:
                data = json.loads(data_json)
                consist_id = data.get('consist_id')
                delta_t = data.get('delta_t')
                status = data.get('status')

                if consist_id is None or delta_t is None:
                    continue

                # Apply consist filter if specified
                if consist_filter is not None and consist_id != consist_filter:
                    continue

                consist_data[consist_id]['delta_t_values'].append(delta_t)

                if status == 'SYNCED':
                    consist_data[consist_id]['synced_count'] += 1
                elif status == 'WARNING':
                    consist_data[consist_id]['warning_count'] += 1
                elif status == 'CRITICAL':
                    consist_data[consist_id]['critical_count'] += 1

            # Calculate statistics for each consist
            consists = {}
            for consist_id, data in consist_data.items():
                values = data['delta_t_values']
                total_crossings = len(values)

                if total_crossings == 0:
                    continue

                avg_delta_t = sum(values) / total_crossings
                min_delta_t = min(values)
                max_delta_t = max(values)

                # Calculate trend indicator
                if avg_delta_t > 0.2:
                    trend = 'LEAD FASTER'
                elif avg_delta_t < -0.2:
                    trend = 'REAR FASTER'
                else:
                    trend = 'BALANCED'

                # Calculate synced percentage
                synced_percent = (data['synced_count'] / total_crossings) * 100

                consists[str(consist_id)] = {
                    'total_crossings': total_crossings,
                    'avg_delta_t': round(avg_delta_t, 3),
                    'min_delta_t': round(min_delta_t, 3),
                    'max_delta_t': round(max_delta_t, 3),
                    'trend': trend,
                    'synced_count': data['synced_count'],
                    'warning_count': data['warning_count'],
                    'critical_count': data['critical_count'],
                    'synced_percent': round(synced_percent, 1)
                }

            # Only include sessions that have consist data after filtering
            if not consists:
                continue

            # Format session data
            # For running sessions (end_time = None), use current time for duration
            effective_end_time = end_time if end_time is not None else time.time()
            duration_seconds = effective_end_time - start_time
            session_date = datetime.fromtimestamp(start_time).strftime('%d-%m-%Y')

            # Count ONLY delta_t events (gate crossings), not all event types
            total_delta_t_events = sum(cd['total_crossings'] for cd in consists.values())

            # Format duration if callback provided
            duration_formatted = format_duration_callback(duration_seconds) if format_duration_callback else None

            result_sessions.append({
                'id': session_id,
                'date': session_date,
                'start_time': start_time,
                'end_time': end_time,
                'duration_seconds': int(duration_seconds),
                'duration_formatted': duration_formatted,
                'total_events': total_delta_t_events,
                'consists': consists
            })

        conn.close()
        return result_sessions

    @staticmethod
    def get_speed_correlation(
        consist_id: int,
        limit: int = 1000,
        bucket_size: int = 5,
        events_per_speed: int = 10
    ) -> Dict:
        """
        Correlate speed_setting events with delta_t measurements.

        Strategy: "Next N Events" - For each speed change, collect next N delta_t events
        to build speed vs delta_t correlation statistics.

        Args:
            consist_id: Consist ID to analyze
            limit: Max speed_setting events to fetch (most recent)
            bucket_size: Speed bucketing interval (e.g., 5 = buckets 0-4, 5-9, etc.)
            events_per_speed: Number of delta_t events to collect after each speed change

        Returns:
            Dict with consist_id, total_speed_changes, correlated_samples, speed_buckets stats
        """
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        # Fetch recent speed_setting events for this consist (most recent first)
        cursor.execute("""
            SELECT timestamp, data
            FROM events
            WHERE event_type = 'speed_setting'
            AND json_extract(data, '$.consist_id') = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (consist_id, limit))

        speed_events = []
        for row in cursor.fetchall():
            data = json.loads(row[1])
            speed_events.append({
                'timestamp': row[0],
                'speed_new': data['speed_new']
            })

        # Reverse to chronological order (oldest first)
        speed_events.reverse()

        if not speed_events:
            conn.close()
            return {
                'consist_id': consist_id,
                'total_speed_changes': 0,
                'correlated_samples': 0,
                'speed_buckets': []
            }

        # Fetch ALL delta_t events for this consist (we'll filter in Python)
        cursor.execute("""
            SELECT timestamp, data
            FROM events
            WHERE event_type = 'delta_t'
            AND json_extract(data, '$.consist_id') = ?
            ORDER BY timestamp ASC
        """, (consist_id,))

        delta_t_events = []
        for row in cursor.fetchall():
            data = json.loads(row[1])
            delta_t_events.append({
                'timestamp': row[0],
                'delta_t': data['delta_t'],
                'status': data['status'],
                'speed': data.get('speed')  # May be None for old events
            })

        conn.close()

        # Correlate: For each speed_setting, find next N delta_t events
        correlated_deltas = []  # List of (speed, delta_t, status)

        for speed_event in speed_events:
            speed_timestamp = speed_event['timestamp']
            speed_value = speed_event['speed_new']

            # Skip speed 0 (stopped)
            if speed_value == 0:
                continue

            # Find next events_per_speed delta_t events after this speed change
            collected = 0
            for dt_event in delta_t_events:
                if dt_event['timestamp'] > speed_timestamp:
                    correlated_deltas.append({
                        'speed': speed_value,
                        'delta_t': dt_event['delta_t'],
                        'status': dt_event['status']
                    })
                    collected += 1
                    if collected >= events_per_speed:
                        break

        # Group by speed buckets and calculate statistics
        from collections import defaultdict
        import statistics

        speed_buckets_data = defaultdict(list)  # bucket_center -> list of delta_t

        for item in correlated_deltas:
            # Calculate bucket center (e.g., speed 47 with bucket_size 5 → bucket 50)
            bucket_center = int((item['speed'] // bucket_size) * bucket_size + bucket_size / 2)
            if bucket_size == 1:
                bucket_center = item['speed']  # No bucketing

            speed_buckets_data[bucket_center].append(item)

        # Calculate stats per bucket
        speed_buckets = []
        for bucket_center, items in sorted(speed_buckets_data.items()):
            if len(items) < 3:  # Skip buckets with insufficient data
                continue

            delta_t_values = [item['delta_t'] for item in items]
            raw_speeds = list(set([item['speed'] for item in items]))

            # Count status distribution
            status_counts = defaultdict(int)
            for item in items:
                status_counts[item['status']] += 1

            speed_buckets.append({
                'speed_bucket': bucket_center,
                'speed_min': min(raw_speeds),
                'speed_max': max(raw_speeds),
                'mean_delta_t': statistics.mean(delta_t_values),
                'std_dev': statistics.stdev(delta_t_values) if len(delta_t_values) > 1 else 0.0,
                'min_delta_t': min(delta_t_values),
                'max_delta_t': max(delta_t_values),
                'samples': len(items),
                'status_distribution': dict(status_counts),
                'raw_speeds': sorted(raw_speeds)
            })

        return {
            'consist_id': consist_id,
            'total_speed_changes': len([e for e in speed_events if e['speed_new'] > 0]),
            'correlated_samples': len(correlated_deltas),
            'speed_buckets': speed_buckets
        }

    @staticmethod
    def get_critical_events_by_speed(consist_id: int) -> Dict[str, Any]:
        """
        Get cumulative CRITICAL/WARNING events per speed (all historical sessions),
        with intelligent "fixed" detection.

        A speed is considered "fixed" if in its last tested session:
        - At least 3 delta_t events occurred at that speed
        - CRITICAL rate < 20% (max 1 CRITICAL every 5 events)

        Used by Speed Table Viewer Phase 1 for CV adjustment recommendations.

        Args:
            consist_id: Consist ID (10, 11, etc.)

        Returns:
            {
                'critical': {speed: count},      # Historical total CRITICAL count
                'warning': {speed: count},       # Historical total WARNING count
                'mean_delta_t': {speed: float},  # Historical average delta_t
                'fixed_speeds': {speed, ...}     # Speeds proven OK in last session
            }
        """
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        # Query 1a: Count CRITICAL/WARNING per speed (all historical sessions)
        cursor.execute('''
            SELECT
                json_extract(data, '$.speed') as speed,
                json_extract(data, '$.status') as status,
                COUNT(*) as count
            FROM events
            WHERE event_type = 'delta_t'
              AND json_extract(data, '$.consist_id') = ?
              AND json_extract(data, '$.status') IN ('CRITICAL', 'WARNING')
            GROUP BY speed, status
        ''', (consist_id,))

        results = {'critical': {}, 'warning': {}, 'mean_delta_t': {}, 'fixed_speeds': set()}

        for row in cursor.fetchall():
            speed, status, count = row
            if speed is not None:
                speed = int(speed)
                if status == 'CRITICAL':
                    results['critical'][speed] = count
                elif status == 'WARNING':
                    results['warning'][speed] = count

        # Query 1b: Calculate mean delta_t per speed (ALL events, all status)
        cursor.execute('''
            SELECT
                json_extract(data, '$.speed') as speed,
                AVG(json_extract(data, '$.delta_t')) as mean_delta_t
            FROM events
            WHERE event_type = 'delta_t'
              AND json_extract(data, '$.consist_id') = ?
            GROUP BY speed
        ''', (consist_id,))

        for row in cursor.fetchall():
            speed, mean_dt = row
            if speed is not None and mean_dt is not None:
                speed = int(speed)
                results['mean_delta_t'][speed] = float(mean_dt)

        # Query 2: For each speed with CRITICAL events, check if "fixed" in last session
        for speed in results['critical'].keys():
            # Find last session that tested this speed
            cursor.execute('''
                SELECT session_id
                FROM events
                WHERE event_type = 'delta_t'
                  AND json_extract(data, '$.consist_id') = ?
                  AND json_extract(data, '$.speed') = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (consist_id, speed))

            last_session_row = cursor.fetchone()
            if not last_session_row:
                continue

            last_session_id = last_session_row[0]

            # Count events in last session for this speed
            cursor.execute('''
                SELECT
                    COUNT(*) as total_events,
                    SUM(CASE WHEN json_extract(data, '$.status') = 'CRITICAL' THEN 1 ELSE 0 END) as critical_events
                FROM events
                WHERE event_type = 'delta_t'
                  AND json_extract(data, '$.consist_id') = ?
                  AND session_id = ?
                  AND json_extract(data, '$.speed') = ?
            ''', (consist_id, last_session_id, speed))

            last_session_stats = cursor.fetchone()
            if last_session_stats:
                total_events, critical_events = last_session_stats
                critical_events = critical_events or 0

                # Check if "fixed": >= 3 events AND < 20% CRITICAL rate
                if total_events >= 3:
                    critical_rate = critical_events / total_events
                    if critical_rate < 0.20:
                        results['fixed_speeds'].add(speed)

        conn.close()
        return results

    # === Operational State Methods ===

    @staticmethod
    def get_consist_state(consist_id: int) -> dict:
        """Get consist operational state (virtual_mode, auto_compensation)"""
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT virtual_mode, auto_compensation_enabled
            FROM consist_state
            WHERE consist_id = ?
        """, (consist_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            # Default values if not found
            return {
                "virtual_mode": True,
                "auto_compensation_enabled": True
            }

        return {
            "virtual_mode": bool(row[0]),
            "auto_compensation_enabled": bool(row[1])
        }

    @staticmethod
    def set_virtual_mode(consist_id: int, enabled: bool):
        """Update consist virtual mode"""
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO consist_state (consist_id, virtual_mode, auto_compensation_enabled)
            VALUES (?, ?, (SELECT COALESCE(auto_compensation_enabled, 1) FROM consist_state WHERE consist_id = ?))
            ON CONFLICT(consist_id) DO UPDATE SET
                virtual_mode = excluded.virtual_mode,
                last_updated = CURRENT_TIMESTAMP
        """, (consist_id, enabled, consist_id))

        conn.commit()
        conn.close()

    @staticmethod
    def set_auto_compensation(consist_id: int, enabled: bool):
        """Update consist auto compensation"""
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO consist_state (consist_id, virtual_mode, auto_compensation_enabled)
            VALUES (?, (SELECT COALESCE(virtual_mode, 1) FROM consist_state WHERE consist_id = ?), ?)
            ON CONFLICT(consist_id) DO UPDATE SET
                auto_compensation_enabled = excluded.auto_compensation_enabled,
                last_updated = CURRENT_TIMESTAMP
        """, (consist_id, consist_id, enabled))

        conn.commit()
        conn.close()

    @staticmethod
    def get_cv_profile_mode() -> str:
        """Get CV profile mode (testing or normal)"""
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT value
            FROM system_state
            WHERE key = 'cv_profile_mode'
        """)

        row = cursor.fetchone()
        conn.close()

        return row[0] if row else "normal"

    @staticmethod
    def set_cv_profile_mode(mode: str):
        """Set CV profile mode (testing or normal)"""
        conn = DataDB.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO system_state (key, value, last_updated)
            VALUES ('cv_profile_mode', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                last_updated = CURRENT_TIMESTAMP
        """, (mode,))

        conn.commit()
        conn.close()
