"""
Tracking Daemon - Headless YOLO + Gate Timing Detection

Runs YOLO inference and gate timing detection without GUI.
Broadcasts delta_t updates to FastAPI backend via WebSocket.
"""
import sys
import os

# Silence FFmpeg/H264 decoder warnings BEFORE importing cv2
os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'  # Quiet mode
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'

import cv2
import time
import json
import signal
import asyncio
import websockets
from pathlib import Path

# Import centralized config loader
from config_loader import load_config

# Import shared tracking modules
from tracking.yolo_tracker import YOLOTracker
from tracking.rtsp_handler import load_camera_config, setup_rtsp_stream, reconnect_rtsp_stream
from analytics_logger import AnalyticsLogger
from log_colors import log
import dependencies

# === CONFIGURATION ===
project_root = Path(__file__).parent.parent  # z21-Terminal/ root
RTSP_URL = load_camera_config()  # Load RTSP URL from camera_config.json
BACKEND_WS_URL = "ws://localhost:8000/ws/tracking"  # WebSocket to FastAPI backend
# MODEL_PATH auto-selected by YOLOTracker based on yolo_obb flag in config.json

# === TRACKING DAEMON ===
class TrackingDaemon:
    """Main tracking daemon with WebSocket communication."""

    def __init__(self):
        self.tracker = YOLOTracker()  # Auto-selects model based on config yolo_obb flag
        self.debug_enabled = self.tracker.debug_enabled  # Copy from tracker
        self.cap = None
        self.websocket = None
        self.running = False
        self.frame_count = 0
        self.start_time = None
        self.last_broadcasted_delta_t = None
        self.last_broadcasted_type = None
        self.last_broadcasted_timestamp = None  # Timestamp of previous dT for time_str calculation

        # Analytics logger (initialized in run() to avoid creating DB before needed)
        self.analytics_logger = None
        self.analytics_flush_task = None
        self.last_yolo_perf_log = 0  # Track last YOLO performance log time

        # Auto-reconnect state
        self.reconnect_delay = 2.0  # Start with 2s
        self.max_reconnect_delay = 30.0  # Max 30s
        self.last_reconnect_attempt = 0

        # Load FPS settings and idle timeout from config (debug mode already loaded in tracker)
        try:
            config = load_config()
            tracking_config = config.get('tracking', {})
            fps_config = tracking_config.get('fps', {'active': 30, 'idle': 1})
            self.fps_active = fps_config.get('active', 30)
            self.fps_idle = fps_config.get('idle', 1)
            self.idle_timeout = tracking_config.get('idle_timeout_seconds', 10)
        except Exception as e:
            if self.debug_enabled:
                log('[WARN]', f"Error loading config: {e}, using defaults")
            self.fps_active = 30
            self.fps_idle = 1
            self.idle_timeout = 10

        # Dynamic FPS control
        self.consist_speeds = {}  # {consist_address: speed}
        self.active_tracking = False
        self.last_fps_mode = None  # Track mode changes for logging
        self.video_connected = True  # Track video connection state for logging
        self.idle_timer_task = None  # Asyncio task for 10s cooldown timer

    async def connect_backend(self):
        """Connect to FastAPI backend via WebSocket."""
        try:
            self.websocket = await websockets.connect(BACKEND_WS_URL)
            log('[INIT]', f"Connected to backend: {BACKEND_WS_URL}")
            # Reset reconnect delay on successful connection
            self.reconnect_delay = 2.0
            return True
        except Exception as e:
            log('[WARN]', f"Failed to connect to backend: {e}")
            return False

    async def ensure_connected(self):
        """Ensure WebSocket is connected, attempt reconnect if needed."""
        # Check if already connected
        if self.websocket and not self.websocket.closed:
            return True

        # Check if we should attempt reconnect (rate limiting)
        now = time.time()
        if now - self.last_reconnect_attempt < self.reconnect_delay:
            return False  # Too soon to retry

        # Attempt reconnect
        self.last_reconnect_attempt = now
        if self.debug_enabled:
            log('[DETECT]', f"Attempting to reconnect to backend... (retry in {self.reconnect_delay:.1f}s if fails)")

        success = await self.connect_backend()

        if not success:
            # Exponential backoff
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
            if self.debug_enabled:
                log('[DETECT]', f"Next retry in {self.reconnect_delay:.1f}s")

        return success

    async def broadcast_delta_t(self, tracking_data):
        """Broadcast delta_t updates for ALL consists (multi-consist support)."""
        # Ensure connected before broadcasting
        if not await self.ensure_connected():
            return  # Not connected, skip broadcast

        # Loop over all consists and broadcast if dT changed
        for consist_id, cdata in self.tracker.consist_data.items():
            delta_t = cdata['delta_t']
            if delta_t is None:
                continue  # No dT for this consist

            # Get delta_t_type from tracking_data (backward compatible)
            current_type = tracking_data.get(f'c{consist_id}_delta_t_type', cdata['delta_t_type'])

            # Check if changed for this consist (need per-consist tracking)
            consist_key = f'c{consist_id}'
            if not hasattr(self, 'last_broadcasted_per_consist'):
                self.last_broadcasted_per_consist = {}

            if consist_key not in self.last_broadcasted_per_consist:
                self.last_broadcasted_per_consist[consist_key] = {
                    'delta_t': None,
                    'type': None,
                    'timestamp': None
                }

            last_broadcast = self.last_broadcasted_per_consist[consist_key]

            if (delta_t == last_broadcast['delta_t'] and
                current_type == last_broadcast['type']):
                continue  # Same value, skip

            # New dT calculated, broadcast it
            current_timestamp = time.time()

            # Calculate time_str (elapsed since PREVIOUS dT for this consist)
            if last_broadcast['timestamp']:
                elapsed = current_timestamp - last_broadcast['timestamp']
                if elapsed < 1:
                    time_str = "now"
                elif elapsed < 60:
                    time_str = f"after {int(elapsed)}s"
                else:
                    minutes = int(elapsed // 60)
                    seconds = int(elapsed % 60)
                    time_str = f"after {minutes}m {seconds}s"
            else:
                # First dT for this consist
                time_str = "now"

            # Update broadcast state for this consist
            last_broadcast['delta_t'] = delta_t
            last_broadcast['type'] = current_type
            last_broadcast['timestamp'] = current_timestamp

            message = {
                'type': 'delta_t_update',
                'consist_address': consist_id,
                'delta_t': delta_t,
                'gate_type': current_type,
                'status': self.tracker.get_delta_t_status(consist_id),
                'timestamp': current_timestamp,
                'time_str': time_str,  # Pre-calculated elapsed time
                'thresholds': {
                    'normal': self.tracker.threshold_normal,
                    'warning': self.tracker.threshold_warning
                }
            }

            try:
                await self.websocket.send(json.dumps(message))

                # Log analytics event (async, non-blocking)
                if self.analytics_logger:
                    await self.analytics_logger.log_event('delta_t', {
                        'consist_id': consist_id,
                        'delta_t': delta_t,
                        'status': message['status'],
                        'gate_type': current_type
                    })
            except Exception as e:
                log('[WARN]', f"Backend disconnected: {e}")
                self.websocket = None  # Mark as disconnected
                break  # Stop broadcasting if disconnected

    async def broadcast_positions(self, tracking_data):
        """Broadcast YOLO detection positions for video overlay (pallini)."""
        detections = tracking_data.get('detections', {})
        if not detections:
            return

        # Ensure connected before broadcasting (but don't block if not connected)
        if not self.websocket or self.websocket.closed:
            return  # Not connected, skip broadcast (silent)

        # Format detections for video overlay (pallini colorati)
        positions = []
        for class_id, det in detections.items():
            class_name = det['name']  # e.g., "7_E656_239"

            # Extract address and locomotive name
            try:
                parts = class_name.split('_')
                address = int(parts[0])
                loco_name = '_'.join(parts[1:])  # "E656_239" → "E656"
                # Simplify name: just first part (E656, not E656_239)
                loco_name_short = parts[1] if len(parts) > 1 else loco_name
            except (ValueError, IndexError):
                continue

            # Convert bbox to JSON-serializable list (handle numpy types)
            bbox_json = None
            if 'bbox' in det and det['bbox'] is not None:
                bbox_json = [int(x) for x in det['bbox']]  # Convert to Python int

            positions.append({
                'address': address,
                'name': loco_name_short,  # "E656" or "E444"
                'position': list(det['pos']),  # [x, y]
                'confidence': det['conf'],
                'bbox': bbox_json  # [x1, y1, x2, y2] or [x1, y1, x2, y2, x3, y3, x4, y4] for OBB
            })

        if not positions:
            return

        message = {
            'type': 'yolo_detections',
            'detections': positions,
            'timestamp': time.time()
        }

        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            # Silent fail for positions (less critical than dT)
            self.websocket = None  # Mark as disconnected

    async def _idle_timer(self):
        """Timer che aspetta idle_timeout secondi prima di passare a idle mode"""
        try:
            await asyncio.sleep(self.idle_timeout)

            # Dopo timeout, controlla se ancora tutto fermo
            any_movement = any(s > 0 for s in self.consist_speeds.values())
            if not any_movement and self.active_tracking:
                self.active_tracking = False
                log('[DETECT]', f"Switched to Low-Power Mode ({self.fps_idle} FPS) (after {self.idle_timeout:.0f}s cooldown)")
                # Note: Analytics session stays open (closed only on daemon stop)
        except asyncio.CancelledError:
            # Timer cancellato (movimento ripreso)
            pass

    async def update_consist_speed(self, consist_address: int, speed: int):
        """
        Update consist speed for FPS mode calculation with cooldown

        Args:
            consist_address: DCC address
            speed: Speed 0-126
        """
        self.consist_speeds[consist_address] = speed

        # Reset dT timestamp for THIS consist if speed = 0 (so next dT shows "now" when it restarts)
        if speed == 0:
            # consist_key format: "c{consist_address}" (e.g., "c10", "c11")
            consist_key = f'c{consist_address}'
            if consist_key in self.last_broadcasted_per_consist:
                self.last_broadcasted_per_consist[consist_key]['timestamp'] = None

        # Check if any consist is moving
        any_movement = any(s > 0 for s in self.consist_speeds.values())

        if any_movement:
            # Movement detected: cancella timer e passa subito ad active
            if self.idle_timer_task:
                self.idle_timer_task.cancel()
                self.idle_timer_task = None

            if not self.active_tracking:
                self.active_tracking = True
                log('[DETECT]', f"Switched to Active Tracking ({self.fps_active} FPS)")
        else:
            # Tutto fermo: avvia timer (se non già avviato)
            if not self.idle_timer_task and self.active_tracking:
                log('[DETECT]', f"All consists stopped - starting {self.idle_timeout:.0f}s cooldown timer...")
                self.idle_timer_task = asyncio.create_task(self._idle_timer())

    async def listen_backend_messages(self):
        """Listen for incoming messages from backend (runs in parallel with tracking loop)"""
        while self.running:
            try:
                # Ensure we're connected
                await self.ensure_connected()

                if not self.websocket:
                    await asyncio.sleep(1)
                    continue

                # Listen for messages
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    data = json.loads(message)

                    if data.get('type') == 'consist_speed_update':
                        consist_address = data.get('consist_address')
                        speed = data.get('speed', 0)
                        await self.update_consist_speed(consist_address, speed)

                except asyncio.TimeoutError:
                    # Timeout is OK, just loop again
                    continue
                except websockets.exceptions.ConnectionClosed:
                    self.websocket = None
                    await asyncio.sleep(1)

            except Exception as e:
                # Don't crash the daemon on error, just log and retry
                await asyncio.sleep(1)

    async def run(self):
        """Main tracking loop with dynamic FPS."""
        self.running = True
        self.start_time = time.time()

        # Try initial connection (but don't fail if backend not ready)
        await self.connect_backend()

        # Open video capture with optimal buffering
        self.cap = setup_rtsp_stream(RTSP_URL, description="tracking daemon stream")
        if not self.cap:
            return

        log('[INIT]', f"Tracking daemon started - Low-Power Mode ({self.fps_idle} FPS)")
        log('[INIT]', f"(switches to Active Tracking {self.fps_active} FPS when movement detected)")

        # Initialize analytics logger (async, zero impact on tracking)
        try:
            config = load_config()
            tracking_config = config.get('tracking', {})
            idle_timeout = tracking_config.get('idle_timeout_seconds', 10)
            # Use absolute path to match endpoint expectations
            db_path = project_root / 'backend' / 'data' / 'analytics.db'

            # Cleanup zombie sessions from previous crashes/restarts (BEFORE creating new session)
            try:
                import sqlite3
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute("DELETE FROM events WHERE session_id IN (SELECT id FROM sessions WHERE validated = 0)")
                cursor.execute("DELETE FROM sessions WHERE validated = 0")
                deleted = cursor.rowcount
                conn.commit()
                conn.close()
                if deleted > 0:
                    log('[ANALYTICS]', f"Cleaned up {deleted} zombie sessions from previous runs")
            except Exception as e:
                log('[WARN]', f"Zombie cleanup failed: {e}")

            self.analytics_logger = AnalyticsLogger(db_path=str(db_path), idle_timeout=idle_timeout)
            self.analytics_flush_task = asyncio.create_task(self.analytics_logger.start_flush_loop())
            log('[ANALYTICS]', f"Analytics logging enabled (DB: {self.analytics_logger.db_path})")

            # Make analytics_logger globally accessible for speed_setting event logging
            dependencies.set_analytics_logger(self.analytics_logger)

        except Exception as e:
            log('[WARN]', f"Analytics logger init failed: {e} (tracking continues)")
            self.analytics_logger = None
            dependencies.set_analytics_logger(None)

        # Start backend message listener in parallel
        listener_task = asyncio.create_task(self.listen_backend_messages())

        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    # Log only on state change (avoid spam)
                    if self.video_connected:
                        log('[WARN]', f"Lost video connection, reconnecting...")
                        self.video_connected = False

                    # Reconnect RTSP stream (same logic as video_feed.py)
                    await asyncio.sleep(2)
                    self.cap = reconnect_rtsp_stream(self.cap, RTSP_URL, description="tracking daemon stream")
                    continue

                # Video connection restored
                if not self.video_connected:
                    log('[INIT]', f"Video connection restored")
                    self.video_connected = True

                self.frame_count += 1

                # Skip YOLO in idle mode (save CPU, keep VideoCapture alive)
                if not self.active_tracking:
                    # Log only on state change (avoid spam) - verbose, only if debug enabled
                    if self.last_fps_mode != 'idle':
                        log('[DETECT]', f"YOLO tracking paused (idle @ {self.fps_idle} FPS, flushing RTSP buffer only)")
                        self.last_fps_mode = 'idle'
                    # Idle: read frame to flush RTSP buffer, but skip YOLO + broadcast
                    await asyncio.sleep(1.0 / self.fps_idle)
                    continue

                # Active: YOLO tracking + broadcast
                # Log only on state change (avoid spam) - verbose, only if debug enabled
                if self.last_fps_mode != 'active':
                    log('[DETECT]', f"YOLO tracking resumed (active @ {self.fps_active} FPS)")
                    self.last_fps_mode = 'active'

                tracking_data = self.tracker.update(frame)

                # Broadcast updates
                await self.broadcast_delta_t(tracking_data)

                # Log YOLO performance to analytics (every 5 seconds to reduce event volume)
                current_time = time.time()
                if self.analytics_logger and (current_time - self.last_yolo_perf_log > 5.0):
                    try:
                        stats = self.tracker.get_performance_stats()
                        await self.analytics_logger.log_event('yolo_performance', {
                            'avg_fps': stats['avg_fps'],
                            'avg_confidence': stats['avg_confidence'],  # {1: 0.87, 5: 0.76, 7: 0.91, 8: 0.65}
                            'miss_rate': stats['miss_rate']
                        })
                        self.last_yolo_perf_log = current_time
                    except Exception as e:
                        log('[WARN]', f"Failed to log YOLO performance: {e}")

                # Optional: broadcast positions every 10 frames (reduce traffic)
                if self.frame_count % 10 == 0:
                    await self.broadcast_positions(tracking_data)

                # Dynamic FPS (active mode)
                await asyncio.sleep(1.0 / self.fps_active)

        except KeyboardInterrupt:
            log('[SHUT]', f"Interrupted by user")
        except Exception as e:
            log('[WARN]', f"Error in tracking loop: {e}")
        finally:
            # Cancel listener task
            if listener_task:
                listener_task.cancel()
                try:
                    await listener_task
                except asyncio.CancelledError:
                    pass

            # Close analytics session (async cleanup)
            if self.analytics_logger:
                try:
                    await self.analytics_logger.close_session()
                except Exception as e:
                    log('[WARN]', f"Analytics cleanup failed: {e}")

            # Cancel analytics flush task
            if self.analytics_flush_task and not self.analytics_flush_task.done():
                self.analytics_flush_task.cancel()
                try:
                    await self.analytics_flush_task
                except asyncio.CancelledError:
                    pass

            self.stop()

    def stop(self):
        """Stop tracking and cleanup."""
        self.running = False

        # Cancel idle timer if running
        if self.idle_timer_task:
            self.idle_timer_task.cancel()
            self.idle_timer_task = None

        if self.cap:
            self.cap.release()

        # Clear global analytics_logger reference
        dependencies.set_analytics_logger(None)

        if self.start_time and self.debug_enabled:
            duration = time.time() - self.start_time
            log('[SHUT]', f"Session Summary:")
            log('[SHUT]', f"Duration: {duration:.1f}s")
            log('[SHUT]', f"Frames: {self.frame_count}")

            # Per-consist statistics
            for consist_id, cdata in self.tracker.consist_data.items():
                crossings = cdata['gate_crossing_count']
                delta_t = cdata['delta_t']
                if crossings > 0:
                    log('[SHUT]', f"Consist {consist_id}:")
                    log('[SHUT]', f"  Gate crossings: {crossings}")
                    if delta_t is not None:
                        status = self.tracker.get_delta_t_status(consist_id)
                        log('[SHUT]', f"  Last dT: {delta_t:+.3f}s ({status})")

        if self.debug_enabled:
            log('[SHUT]', f"Tracking daemon stopped")


# === MAIN ===
shutdown_flag = False

def signal_handler(sig, frame):
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    global shutdown_flag
    log('[SHUT]', f"Shutdown signal received")
    shutdown_flag = True


async def main():
    """Main entry point."""
    global shutdown_flag

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("""
╔═══════════════════════════════════════════════════════════╗
║          z21-Terminal Tracking Daemon (Headless)          ║
║           YOLO + Gate Timing Detection                    ║
╚═══════════════════════════════════════════════════════════╝
    """)

    daemon = TrackingDaemon()

    # Run daemon in background task
    daemon_task = asyncio.create_task(daemon.run())

    # Wait for shutdown signal
    try:
        while not shutdown_flag:
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass

    # Graceful shutdown: stop daemon and wait for cleanup
    daemon.running = False
    try:
        await asyncio.wait_for(daemon_task, timeout=3.0)
    except asyncio.TimeoutError:
        daemon_task.cancel()
        try:
            await daemon_task
        except asyncio.CancelledError:
            pass


if __name__ == '__main__':
    asyncio.run(main())
