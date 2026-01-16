"""
Analytics Database Service

Centralizes all SQLite3 database access for analytics.
Eliminates code duplication across endpoints.
"""

from pathlib import Path
import sqlite3
import json
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime

# Database path (relative to this service file)
DB_PATH = Path(__file__).parent.parent / "data" / "analytics.db"


class AnalyticsDB:
    """Analytics database access layer"""

    @staticmethod
    def get_connection() -> sqlite3.Connection:
        """Get database connection"""
        return sqlite3.connect(str(DB_PATH))

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
        conn = AnalyticsDB.get_connection()
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
        conn = AnalyticsDB.get_connection()
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
        conn = AnalyticsDB.get_connection()
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
        conn = AnalyticsDB.get_connection()
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
        conn = AnalyticsDB.get_connection()
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
        conn = AnalyticsDB.get_connection()
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
        conn = AnalyticsDB.get_connection()
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

        conn = AnalyticsDB.get_connection()
        cursor = conn.cursor()

        # Get validated sessions (exclude running sessions)
        cursor.execute("""
            SELECT id, start_time, end_time, event_count
            FROM sessions
            WHERE validated = 1 AND end_time IS NOT NULL
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
            duration_seconds = end_time - start_time
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
        conn = AnalyticsDB.get_connection()
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
    def get_critical_events_by_speed(consist_id: int, session_id: str) -> Dict[str, Dict[int, int]]:
        """
        Count CRITICAL/WARNING events grouped by speed for current session only.
        Also calculates mean delta_t per speed (all events) for CV adjustment direction.
        Used by Speed Table Viewer to identify problematic speeds.

        Args:
            consist_id: Consist ID (10, 11, etc.)
            session_id: Current session ID for filtering

        Returns:
            {
                'critical': {10: 5, 20: 3, 88: 12, ...},
                'warning': {10: 2, 20: 1, 88: 7, ...},
                'mean_delta_t': {10: -0.5, 20: 0.3, 88: -1.2, ...}  # Avg delta_t per speed
            }
        """
        conn = AnalyticsDB.get_connection()
        cursor = conn.cursor()

        # Query 1: Count CRITICAL/WARNING events per speed
        cursor.execute('''
            SELECT
                json_extract(data, '$.speed') as speed,
                json_extract(data, '$.status') as status,
                COUNT(*) as count
            FROM events
            WHERE event_type = 'delta_t'
              AND json_extract(data, '$.consist_id') = ?
              AND session_id = ?
              AND json_extract(data, '$.status') IN ('CRITICAL', 'WARNING')
            GROUP BY speed, status
        ''', (consist_id, session_id))

        results = {'critical': {}, 'warning': {}, 'mean_delta_t': {}}
        for row in cursor.fetchall():
            speed, status, count = row
            if speed is not None:
                speed = int(speed)
                if status == 'CRITICAL':
                    results['critical'][speed] = count
                elif status == 'WARNING':
                    results['warning'][speed] = count

        # Query 2: Calculate mean delta_t per speed (ALL events, not just CRITICAL/WARNING)
        # This tells us if adjust loco is faster (negative) or slower (positive)
        cursor.execute('''
            SELECT
                json_extract(data, '$.speed') as speed,
                AVG(json_extract(data, '$.delta_t')) as mean_delta_t
            FROM events
            WHERE event_type = 'delta_t'
              AND json_extract(data, '$.consist_id') = ?
              AND session_id = ?
            GROUP BY speed
        ''', (consist_id, session_id))

        for row in cursor.fetchall():
            speed, mean_delta_t = row
            if speed is not None and mean_delta_t is not None:
                speed = int(speed)
                results['mean_delta_t'][speed] = float(mean_delta_t)

        conn.close()
        return results
