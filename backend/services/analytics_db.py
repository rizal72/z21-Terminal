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
