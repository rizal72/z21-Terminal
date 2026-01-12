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
from backend.utils.logger import log


class AnalyticsLogger:
    """Async event logger with SQLite backend and session validation"""

    def __init__(self, db_path='data/analytics.db', idle_timeout=10):
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

            CREATE INDEX IF NOT EXISTS idx_session_type
                ON events(session_id, event_type);
            CREATE INDEX IF NOT EXISTS idx_timestamp
                ON events(timestamp);
        """)
        self.conn.commit()

    def _create_session(self):
        """Create session record in DB"""
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
            log('[ANALYTICS]', f"Session {self.session_id} validated (first Δt calculation)")

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
            log('[ANALYTICS]', f"Discarded invalid session {self.session_id} (no Δt calculated)")
        else:
            log('[ANALYTICS]', f"Session {self.session_id} closed ({self.event_count} events)")

        # Close DB connection
        self.conn.close()

    def get_session_info(self):
        """Return current session metadata (lightweight)"""
        return {
            'session_id': self.session_id,
            'start_time': self.session_start,
            'uptime': time.time() - self.session_start,
            'event_count': self.event_count,
            'validated': self.session_validated
        }
