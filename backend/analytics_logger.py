"""
Analytics Logger for z21-Terminal

SQLite-based async event logging with session validation.
Sessions become "valid" only when first Δt is calculated (coordinated operation).
Invalid sessions (no Δt) are discarded on close.

Zero impact on tracking: async logging with buffered writes.
"""

import asyncio
import sqlite3
import json
import time
from pathlib import Path
from collections import deque
from datetime import datetime
from log_colors import log


class AnalyticsLogger:
    """Async event logger with SQLite backend and session validation"""

    def __init__(self, db_path='data/data.db', idle_timeout=10):
        """
        Initialize analytics logger

        Args:
            db_path: Path to SQLite database file
            idle_timeout: Seconds to wait before ending session (default: 10)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # SQLite connection (single thread, check_same_thread=False for async)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_schema()

        # Session metadata
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_start = time.time()
        self.session_validated = False  # Becomes True at first Δt calculation

        # Event buffer (flush every 100 events or 10s)
        self.event_buffer = deque(maxlen=100)
        self.event_count = 0
        self.idle_timeout = idle_timeout
        self.last_activity = time.time()

        # Background flush task
        self.flush_task = None

        # Create session record
        self._create_session()

        log('[ANALYTICS]', f"Session {self.session_id} started")

    def _init_schema(self):
        """Create tables if they don't exist"""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                start_time REAL,
                end_time REAL,
                validated BOOLEAN DEFAULT 0,
                event_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp REAL,
                event_type TEXT,
                data TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS locomotive_stats (
                address INTEGER PRIMARY KEY,
                name TEXT,
                total_operating_seconds INTEGER DEFAULT 0,
                total_sessions INTEGER DEFAULT 0,
                last_active_time REAL,
                created_at REAL,
                updated_at REAL
            );

            CREATE INDEX IF NOT EXISTS idx_session_type
                ON events(session_id, event_type);
            CREATE INDEX IF NOT EXISTS idx_timestamp
                ON events(timestamp);
        """)
        self.conn.commit()

    def _create_session(self):
        """Create session record in DB

        CRITICAL: Close ALL orphaned sessions (end_time = NULL) before creating new one.
        This ensures there's ALWAYS exactly 1 open session (or 0 if idle).
        """
        current_time = time.time()

        # Find orphaned sessions (never closed properly)
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM sessions WHERE end_time IS NULL")
        orphaned_sessions = [row[0] for row in cursor.fetchall()]

        if orphaned_sessions:
            log('[ANALYTICS]', f"Found {len(orphaned_sessions)} orphaned session(s), closing now...")

            # Close each orphaned session
            for orphan_id in orphaned_sessions:
                # Check if session has any delta_t events (valid session)
                cursor.execute(
                    "SELECT COUNT(*) FROM events WHERE session_id = ? AND event_type = 'delta_t'",
                    (orphan_id,)
                )
                delta_t_count = cursor.fetchone()[0]

                if delta_t_count > 0:
                    # Valid session - close and validate it
                    self.conn.execute(
                        "UPDATE sessions SET end_time = ?, validated = 1 WHERE id = ?",
                        (current_time, orphan_id)
                    )
                    log('[ANALYTICS]', f"Closed orphaned session {orphan_id} ({delta_t_count} delta_t events)")
                else:
                    # Invalid session - delete it
                    self.conn.execute("DELETE FROM events WHERE session_id = ?", (orphan_id,))
                    self.conn.execute("DELETE FROM sessions WHERE id = ?", (orphan_id,))
                    log('[ANALYTICS]', f"Discarded orphaned session {orphan_id} (no delta_t events)")

            self.conn.commit()

        # Now create new session
        self.conn.execute(
            "INSERT INTO sessions (id, start_time, validated, event_count) VALUES (?, ?, 0, 0)",
            (self.session_id, self.session_start)
        )
        self.conn.commit()

    async def log_event(self, event_type: str, data: dict):
        """
        Non-blocking event logging - returns immediately

        Args:
            event_type: Type of event ('gate_crossing', 'delta_t', 'yolo_performance')
            data: Event data dictionary
        """
        event = {
            'session_id': self.session_id,
            'timestamp': time.time(),
            'event_type': event_type,
            'data': json.dumps(data)
        }

        self.event_buffer.append(event)
        self.event_count += 1
        self.last_activity = time.time()

        # Validate session on first Δt calculation
        if event_type == 'delta_t' and not self.session_validated:
            self.session_validated = True
            self.conn.execute(
                "UPDATE sessions SET validated = 1 WHERE id = ?",
                (self.session_id,)
            )
            self.conn.commit()
            log('[ANALYTICS]', f"Session {self.session_id} validated (first delta_t calculation)")

        # Flush if buffer full (non-blocking)
        if len(self.event_buffer) >= 100:
            asyncio.create_task(self._flush_buffer())

    async def _flush_buffer(self):
        """Write buffered events to DB (async)"""
        if not self.event_buffer:
            return

        events_to_write = list(self.event_buffer)
        self.event_buffer.clear()

        # Batch insert to DB (run in thread pool to avoid blocking)
        await asyncio.to_thread(self._write_events, events_to_write)

    def _write_events(self, events):
        """Synchronous DB write (called in thread pool)"""
        cursor = self.conn.cursor()
        cursor.executemany(
            "INSERT INTO events (session_id, timestamp, event_type, data) VALUES (?, ?, ?, ?)",
            [(e['session_id'], e['timestamp'], e['event_type'], e['data']) for e in events]
        )
        # Update session event count
        cursor.execute(
            "UPDATE sessions SET event_count = event_count + ? WHERE id = ?",
            (len(events), self.session_id)
        )
        self.conn.commit()

    async def start_flush_loop(self):
        """Flush buffer every 10 seconds (background task)"""
        while True:
            await asyncio.sleep(10)
            await self._flush_buffer()

    async def close_session(self):
        """Final flush on shutdown - discards invalid sessions"""
        await self._flush_buffer()
        if self.flush_task:
            self.flush_task.cancel()

        # Update session end time
        self.conn.execute(
            "UPDATE sessions SET end_time = ? WHERE id = ?",
            (time.time(), self.session_id)
        )
        self.conn.commit()

        # Delete session if never validated (no Δt calculated)
        if not self.session_validated:
            self.conn.execute("DELETE FROM events WHERE session_id = ?", (self.session_id,))
            self.conn.execute("DELETE FROM sessions WHERE id = ?", (self.session_id,))
            self.conn.commit()
            log('[ANALYTICS]', f"Discarded invalid session {self.session_id} (no delta_t calculated)")
        else:
            log('[ANALYTICS]', f"Session {self.session_id} closed ({self.event_count} events)")

        # Cleanup OTHER zombie sessions (safe - current session already handled)
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM events WHERE session_id IN (SELECT id FROM sessions WHERE validated = 0)")
            cursor.execute("DELETE FROM sessions WHERE validated = 0")
            deleted = cursor.rowcount
            self.conn.commit()
            if deleted > 0:
                log('[ANALYTICS]', f"Cleaned up {deleted} zombie sessions on close")
        except Exception as e:
            log('[WARN]', f"Zombie session cleanup failed: {e}")

        # Close DB connection
        self.conn.close()

    def log_loco_operating_time(self, address: int, start_time: float, end_time: float, duration_seconds: float, consist_id: int = None):
        """
        Log locomotive operating time event (both events table + stats table)

        Args:
            address: DCC address of locomotive
            start_time: Movement start timestamp
            end_time: Movement end timestamp
            duration_seconds: Total duration in seconds
            consist_id: Optional consist ID (10 or 11)
        """
        # Prepare event data
        event_data = {
            'address': address,
            'start_time': start_time,
            'end_time': end_time,
            'duration_seconds': duration_seconds,
            'session_id': self.session_id
        }
        if consist_id:
            event_data['consist_id'] = consist_id

        # Add to events buffer (async logging)
        asyncio.create_task(self.log_event('loco_operating_time', event_data))

        # Update aggregate stats table immediately (no buffering for aggregates)
        try:
            current_time = time.time()
            self.conn.execute('''
                INSERT INTO locomotive_stats (address, total_operating_seconds, total_sessions, last_active_time, created_at, updated_at)
                VALUES (?, ?, 1, ?, ?, ?)
                ON CONFLICT(address) DO UPDATE SET
                    total_operating_seconds = total_operating_seconds + ?,
                    total_sessions = total_sessions + 1,
                    last_active_time = MAX(last_active_time, ?),
                    updated_at = ?
            ''', (address, duration_seconds, end_time, start_time, current_time,
                  duration_seconds, end_time, current_time))
            self.conn.commit()
        except Exception as e:
            log('[WARN]', f"Error updating locomotive stats for address {address}: {e}")

    def get_session_info(self):
        """Return current session metadata (lightweight)"""
        return {
            'session_id': self.session_id,
            'start_time': self.session_start,
            'uptime': time.time() - self.session_start,
            'event_count': self.event_count,
            'validated': self.session_validated
        }
