"""
Analytics Logger for z21-Terminal

Postgres async event logging with session validation.
Sessions become "valid" only when first Δt is calculated (coordinated operation).
Invalid sessions (no Δt) are discarded on close.

Zero impact on tracking: async logging with buffered writes. Every write opens a
short connection, so an unreachable database costs a two-second timeout and the
buffered events stay queued instead of being dropped.
"""

import asyncio
import json
import time
from collections import deque
from datetime import datetime
from typing import Optional

import psycopg

from services import db
from log_colors import log


class AnalyticsLogger:
    """Async event logger with a Postgres backend and session validation"""

    def __init__(self, db_path=None, idle_timeout=10):
        """
        Initialize analytics logger

        Args:
            db_path: kept for callers of the old SQLite version, unused
            idle_timeout: Seconds to wait before ending session (default: 10)
        """
        self.db_path = db_path
        # Another host holds the writer lock: serve reads, never touch sessions.
        self.writable = db.is_writer()

        # Session metadata
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_start = time.time()
        self.session_validated = False  # Becomes True at first Δt calculation

        # True once this process has created its session row; a late lock acquisition
        # must not insert the same id twice.
        self.session_created = False

        # Event buffer: a safety margin for a slow or unreachable database, not a
        # workload limiter. A flush is triggered at 100 and the ceiling is high enough
        # that a burst between two flushes is not silently dropped.
        self.event_buffer = deque(maxlen=1000)
        self._buffer_full_warned = False
        self.event_count = 0
        self.idle_timeout = idle_timeout
        self.last_activity = time.time()

        # Background flush task
        self.flush_task = None
        # One flush at a time: two concurrent flushes read the same batch and write it twice.
        self._flush_lock = asyncio.Lock()

        if self.writable:
            self._create_session()
            log('[ANALYTICS]', f"Session {self.session_id} started")
        else:
            log('[ANALYTICS]', "Another host holds the writer lock: sessions disabled on this instance")

    def _create_session(self):
        """Create session record in DB

        CRITICAL: Close ALL orphaned sessions (end_time = NULL) before creating new one.
        This ensures there's ALWAYS exactly 1 open session (or 0 if idle).
        """
        current_time = time.time()

        with db.connection() as conn:
            # Find orphaned sessions (never closed properly)
            orphaned_sessions = [
                row[0] for row in conn.execute(
                    "SELECT id FROM sessions WHERE end_time IS NULL"
                ).fetchall()
            ]

            if orphaned_sessions:
                log('[ANALYTICS]', f"Found {len(orphaned_sessions)} orphaned session(s), closing now...")

                for orphan_id in orphaned_sessions:
                    delta_t_count = conn.execute(
                        "SELECT COUNT(*) FROM events WHERE session_id = %s AND event_type = 'delta_t'",
                        (orphan_id,)
                    ).fetchone()[0]

                    if delta_t_count > 0:
                        conn.execute(
                            "UPDATE sessions SET end_time = %s, validated = 1 WHERE id = %s",
                            (current_time, orphan_id)
                        )
                        log('[ANALYTICS]', f"Closed orphaned session {orphan_id} ({delta_t_count} delta_t events)")
                    else:
                        conn.execute("DELETE FROM events WHERE session_id = %s", (orphan_id,))
                        conn.execute("DELETE FROM sessions WHERE id = %s", (orphan_id,))
                        log('[ANALYTICS]', f"Discarded orphaned session {orphan_id} (no delta_t events)")

            conn.execute(
                "INSERT INTO sessions (id, start_time, validated, event_count) VALUES (%s, %s, 0, 0)",
                (self.session_id, self.session_start)
            )
            self.session_created = True

    async def log_event(self, event_type: str, data: dict):
        """
        Non-blocking event logging - returns immediately

        Args:
            event_type: Type of event ('gate_crossing', 'delta_t', 'yolo_performance')
            data: Event data dictionary
        """
        if not self.writable:
            return

        event = {
            'session_id': self.session_id,
            'timestamp': time.time(),
            'event_type': event_type,
            'data': json.dumps(data)
        }

        if len(self.event_buffer) == self.event_buffer.maxlen:
            if not self._buffer_full_warned:
                log('[WARN]', f"Event buffer full ({self.event_buffer.maxlen}): older events are being dropped")
                self._buffer_full_warned = True
        else:
            self._buffer_full_warned = False
        self.event_buffer.append(event)
        self.event_count += 1
        self.last_activity = time.time()

        # Validate session on first Δt calculation
        if event_type == 'delta_t' and not self.session_validated:
            self.session_validated = True
            try:
                with db.connection() as conn:
                    conn.execute(
                        "UPDATE sessions SET validated = 1 WHERE id = %s",
                        (self.session_id,)
                    )
                log('[ANALYTICS]', f"Session {self.session_id} validated (first delta_t calculation)")
            except psycopg.Error as e:
                log('[WARN]', f"Session validation write failed: {e}")

        # Flush if buffer full (non-blocking)
        if len(self.event_buffer) >= 100:
            asyncio.create_task(self._flush_buffer())

    async def _flush_buffer(self):
        """Write buffered events to DB (async)"""
        async with self._flush_lock:
            if not self.event_buffer:
                return

            # Take the batch and empty the deque at once: new events land in a clean
            # buffer, so nothing appended during the write can be popped by mistake.
            events_to_write = list(self.event_buffer)
            self.event_buffer.clear()

            try:
                await asyncio.to_thread(self._write_events, events_to_write)
            except psycopg.Error as e:
                # Put them back in front, in order. If the buffer is full, the newest
                # give way: the deque holds 100 and the database is the sink.
                self.event_buffer.extendleft(reversed(events_to_write))
                log('[WARN]', f"Event flush failed, {len(events_to_write)} events kept: {e}")

    def _write_events(self, events):
        """Synchronous DB write (called in thread pool)"""
        # One transaction: an event batch and its session count move together, so a
        # retry after a failure cannot insert the same batch twice.
        conn = db.get_connection(autocommit=False)
        try:
            with conn.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO events (session_id, timestamp, event_type, data) "
                    "VALUES (%s, %s, %s, %s::jsonb)",
                    [(e['session_id'], e['timestamp'], e['event_type'], e['data']) for e in events]
                )
            conn.execute(
                "UPDATE sessions SET event_count = event_count + %s WHERE id = %s",
                (len(events), self.session_id)
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def refresh_writer_state(self) -> str:
        """
        Keep `writable` in line with the actual lock, once per flush tick.

        An outage is not a lost lock: while the database is unreachable the buffer keeps
        filling and nothing changes here. Only another host holding the lock stops this
        instance, and a session is created once, never re-inserted.
        """
        state = db.ensure_writer_lock()
        if state == db.WRITER_HOLDING:
            if not self.writable:
                self.writable = True
                log('[ANALYTICS]', "Writer lock available again")
            if not self.session_created:
                self._create_session()
                log('[ANALYTICS]', f"Session {self.session_id} started")
        elif state == db.WRITER_OTHER and self.writable:
            self.writable = False
            log('[WARN]', "Writer lock taken by another host: this instance stops recording analytics")
        return state

    async def start_flush_loop(self):
        """Flush buffer every 10 seconds (background task)"""
        while True:
            await asyncio.sleep(10)
            self.refresh_writer_state()
            await self._flush_buffer()

    async def close_session(self):
        """Final flush on shutdown - discards invalid sessions"""
        if not self.writable:
            return

        await self._flush_buffer()
        if self.flush_task:
            self.flush_task.cancel()

        with db.connection() as conn:
            # Update session end time
            conn.execute(
                "UPDATE sessions SET end_time = %s WHERE id = %s",
                (time.time(), self.session_id)
            )

            # Delete session if never validated (no Δt calculated)
            if not self.session_validated:
                conn.execute("DELETE FROM events WHERE session_id = %s", (self.session_id,))
                conn.execute("DELETE FROM sessions WHERE id = %s", (self.session_id,))
                log('[ANALYTICS]', f"Discarded invalid session {self.session_id} (no delta_t calculated)")
            else:
                log('[ANALYTICS]', f"Session {self.session_id} closed ({self.event_count} events)")

            # Cleanup OTHER zombie sessions (safe - current session already handled)
            try:
                cursor = conn.execute("DELETE FROM events WHERE session_id IN (SELECT id FROM sessions WHERE validated = 0)")
                cursor = conn.execute("DELETE FROM sessions WHERE validated = 0")
                deleted = cursor.rowcount
                if deleted > 0:
                    log('[ANALYTICS]', f"Cleaned up {deleted} zombie sessions on close")
            except psycopg.Error as e:
                log('[WARN]', f"Zombie session cleanup failed: {e}")

    def log_loco_operating_time(self, address: int, start_time: float, end_time: float, duration_seconds: float, consist_id: Optional[int] = None):
        """
        Log locomotive operating time event (both events table + stats table)

        Args:
            address: DCC address of locomotive
            start_time: Movement start timestamp
            end_time: End timestamp
            duration_seconds: Total duration in seconds
            consist_id: Optional consist ID (10 or 11)
        """
        if not self.writable:
            return

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
        try:
            asyncio.get_running_loop().create_task(self.log_event('loco_operating_time', event_data))
        except RuntimeError:
            # No running loop (script context): write it straight to the buffer path.
            self.event_buffer.append({
                'session_id': self.session_id,
                'timestamp': time.time(),
                'event_type': 'loco_operating_time',
                'data': json.dumps(event_data)
            })

        # Update aggregate stats table immediately (no buffering for aggregates)
        try:
            current_time = time.time()
            with db.connection() as conn:
                conn.execute('''
                    INSERT INTO locomotive_stats (address, total_operating_seconds, total_sessions, last_active_time, created_at, updated_at)
                    VALUES (%s, %s, 1, %s, %s, %s)
                    ON CONFLICT(address) DO UPDATE SET
                        total_operating_seconds = locomotive_stats.total_operating_seconds + %s,
                        total_sessions = locomotive_stats.total_sessions + 1,
                        last_active_time = GREATEST(locomotive_stats.last_active_time, %s),
                        updated_at = %s
                ''', (address, int(round(duration_seconds)), end_time, start_time, current_time,
                      int(round(duration_seconds)), end_time, current_time))
        except psycopg.Error as e:
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
