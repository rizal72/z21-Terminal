"""
Video Feed Module - MJPEG stream with gate overlay
"""
import sys
import os

# Silence FFmpeg/H264 decoder warnings BEFORE importing cv2
os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'  # Quiet mode
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'
os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp|stimeout;5000000'  # TCP transport + 5s socket timeout

import cv2
import json
import time
import threading
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional

from config_loader import load_config, get_config_path
from services.config_helpers import get_all_locomotives
from log_colors import log


# Configuration paths (all in project root)
project_root = Path(__file__).parent.parent  # z21-Terminal/ root
CONFIG_PATH = get_config_path()  # Use centralized config path


def hex_to_bgr(hex_color: str) -> tuple:
    """
    Convert hex color (#RRGGBB) to BGR tuple for OpenCV.

    Args:
        hex_color: Hex color string (e.g., "#FFFF00")

    Returns:
        BGR tuple (e.g., (0, 255, 255))
    """
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (rgb[2], rgb[1], rgb[0])  # Swap to BGR


def load_locomotive_colors() -> Dict[int, tuple]:
    """
    Load locomotive colors from config.json and convert to BGR.

    Uses config_helpers.get_all_locomotives() (backward compatible with old format).

    Returns:
        Dict mapping DCC address to BGR tuple
    """
    try:
        locomotives = get_all_locomotives()

        # Convert hex to BGR and int keys
        colors = {}
        for address_str, loco_data in locomotives.items():
            hex_color = loco_data.get('color', '#808080')
            colors[int(address_str)] = hex_to_bgr(hex_color)

        return colors
    except Exception as e:
        log(f"[VIDEO] Error loading locomotive colors: {e}", "error")
        # Fallback to default colors (old hardcoded values - WRONG BGR)
        return {
            1: (0, 255, 255),   # Yellow
            5: (0, 128, 255),   # Orange
            7: (0, 255, 0),     # Green
            8: (0, 0, 255)      # Red
        }


def load_camera_config() -> str:
    """
    Load camera configuration from unified config.json and build RTSP URL.

    Reads from config['camera'] section (credentials auto-merged from config.local.json).

    Returns:
        RTSP URL string or None on error
    """
    try:
        config = load_config()  # Auto-merges config.local.json credentials
        camera = config.get('camera', {})

        camera_ip = camera.get('ip', '192.168.1.4')
        camera_port = camera.get('port', 554)
        stream = camera.get('stream', 'stream2')
        username = camera.get('username', '')
        password = camera.get('password', '')

        if not username or not password:
            log('[WARN]', 'Camera credentials missing - add to config.local.json')
            log('[WARN]', '   { "camera": { "username": "...", "password": "..." } }')
            return None

        rtsp_url = f"rtsp://{username}:{password}@{camera_ip}:{camera_port}/{stream}"
        return rtsp_url
    except Exception as e:
        log('[ERROR]', f"Error loading camera config: {e}")
        return None


RTSP_URL = load_camera_config()

# load_config() now imported from config_loader (supports config.local.json override)


def draw_gates(frame: np.ndarray, gates: List[Dict]) -> np.ndarray:
    """
    Draw gate markers on frame

    Args:
        frame: Input frame
        gates: List of gate dictionaries

    Returns:
        Frame with gate overlays
    """
    for gate in gates:
        gate_id = gate.get('id')
        center = tuple(gate.get('center', [0, 0]))
        width = gate.get('width', 100)
        height = gate.get('height', 100)
        angle = gate.get('angle', 0)
        # Convert RGB (from JSON) to BGR (for OpenCV)
        color_rgb = gate.get('color', [255, 255, 0])
        color = (color_rgb[2], color_rgb[1], color_rgb[0])  # RGB → BGR

        # Calculate rectangle corners
        cx, cy = center
        w2, h2 = width // 2, height // 2

        # Top-left, top-right, bottom-right, bottom-left
        points = np.array([
            [-w2, -h2],
            [w2, -h2],
            [w2, h2],
            [-w2, h2]
        ], dtype=np.float32)

        # Apply rotation if needed
        if angle != 0:
            theta = np.radians(angle)
            cos_a, sin_a = np.cos(theta), np.sin(theta)
            rotation_matrix = np.array([
                [cos_a, -sin_a],
                [sin_a, cos_a]
            ])
            points = points @ rotation_matrix.T

        # Translate to center position
        points += np.array([cx, cy])
        points = points.astype(np.int32)

        # Draw rectangle
        cv2.polylines(frame, [points], isClosed=True, color=color, thickness=2)

        # Draw gate label (centered)
        label = f"G{gate_id}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
        # Center text: subtract half width and add half height (text origin is bottom-left)
        label_pos = (cx - text_width // 2, cy + text_height // 2)
        cv2.putText(frame, label, label_pos, font, font_scale, color, thickness)

    return frame


def draw_tracking_info(frame: np.ndarray, tracking_data: Optional[Dict[int, Dict]]) -> np.ndarray:
    """
    Draw tracking information panels for ALL consists - MULTI-CONSIST support

    Args:
        frame: Input frame
        tracking_data: Dict of consist_id → tracking info (delta_t, status, etc.)

    Returns:
        Frame with tracking info overlays (one panel per consist, stacked vertically)
    """
    if not tracking_data:
        # No tracking data: show "Waiting..." message
        panel_height = 60
        panel_width = 220
        panel_x = 10
        frame_height = frame.shape[0]
        panel_y = frame_height - panel_height - 10

        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x, panel_y),
                      (panel_x + panel_width, panel_y + panel_height),
                      (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)

        font = cv2.FONT_HERSHEY_PLAIN
        font_scale = 1.1
        text_x = panel_x + 10
        y = panel_y + 18
        cv2.putText(frame, "Tracking: Waiting...", (text_x, y), font, font_scale, (128, 128, 128), 1)
        return frame

    # Panel dimensions (compact for multi-consist)
    panel_height = 75  # Compact height per consist
    panel_width = 220
    panel_x = 10
    panel_gap = 5  # Gap between panels
    frame_height = frame.shape[0]

    # Font settings
    font = cv2.FONT_HERSHEY_PLAIN
    font_scale = 1.0
    line_height = 18

    # Sort consist IDs for consistent display order
    sorted_consist_ids = sorted(tracking_data.keys())

    # Draw panels from BOTTOM to TOP
    for i, consist_id in enumerate(sorted_consist_ids):
        data = tracking_data[consist_id]

        # Calculate panel Y position (stack from bottom)
        panel_y = frame_height - (i + 1) * (panel_height + panel_gap) - 10

        # Draw panel background (semi-transparent black)
        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x, panel_y),
                      (panel_x + panel_width, panel_y + panel_height),
                      (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)

        # Text starting position
        text_x = panel_x + 10
        y = panel_y + 16

        # Line 1: Consist ID
        cv2.putText(frame, f"Consist {consist_id}", (text_x, y), font, font_scale, (255, 255, 255), 1)
        y += line_height

        # Line 2: Delta t
        delta_t = data.get('delta_t')
        if delta_t is not None:
            sign = '+' if delta_t >= 0 else ''
            cv2.putText(frame, f"dT: {sign}{delta_t:.3f}s", (text_x, y), font, font_scale, (255, 255, 255), 1)
            y += line_height

            # Line 3: Status (color-coded)
            status = data.get('status', 'UNKNOWN')
            if status == 'SYNCED':
                status_color = (0, 255, 0)  # Green (BGR)
            elif status == 'WARNING':
                status_color = (0, 255, 255)  # Yellow (BGR)
            elif status == 'CRITICAL':
                status_color = (0, 0, 255)  # Red (BGR)
            else:
                status_color = (128, 128, 128)  # Gray (BGR)
            cv2.putText(frame, f"{status}", (text_x, y), font, font_scale, status_color, 1)
            y += line_height

            # Line 4: Time string (if available)
            time_str = data.get('time_str', '')
            if time_str:
                cv2.putText(frame, time_str, (text_x, y), font, font_scale, (180, 180, 180), 1)
        else:
            # No delta_t available yet
            cv2.putText(frame, "dT: Waiting...", (text_x, y), font, font_scale, (128, 128, 128), 1)

    return frame


def draw_locomotive_markers(frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
    """
    Draw locomotive markers (pallini colorati) on frame

    Args:
        frame: Input frame
        detections: List of detections with {'address', 'name', 'position', 'confidence'}

    Returns:
        Frame with locomotive markers
    """
    # Load colors from config (auto-converted to BGR)
    COLORS = load_locomotive_colors()

    for det in detections:
        address = det.get('address')
        name = det.get('name', '')
        position = det.get('position', [0, 0])
        confidence = det.get('confidence', 0.0)

        if len(position) < 2:
            continue

        x, y = int(position[0]), int(position[1])
        color = COLORS.get(address, (255, 255, 255))  # Default white

        # Draw circle (pallino)
        cv2.circle(frame, (x, y), 8, color, -1)  # Filled circle
        cv2.circle(frame, (x, y), 8, (255, 255, 255), 1)  # White border

        # Draw label (name only, e.g., "E656")
        label = name
        label_pos = (x + 12, y + 5)
        cv2.putText(frame, label, label_pos, cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, color, 2)

    return frame


def draw_debug_overlay(frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
    """
    Draw debug overlay with bounding boxes, center points, and confidence labels
    (similar to track_consist_yolo.py debug view)

    Args:
        frame: Input frame
        detections: List of detections with {'address', 'name', 'position', 'confidence', 'bbox'}

    Returns:
        Frame with debug overlay
    """
    # Load colors from config (auto-converted to BGR)
    COLORS = load_locomotive_colors()

    for det in detections:
        address = det.get('address')
        name = det.get('name', f"Loco {address}")
        position = det.get('position', [0, 0])
        confidence = det.get('confidence', 0.0)
        bbox = det.get('bbox')  # Optional: [x1, y1, x2, y2] in camera coords

        if len(position) < 2:
            continue

        x, y = int(position[0]), int(position[1])
        color = COLORS.get(address, (255, 255, 255))  # Default white

        # Draw bounding box (if available)
        if bbox:
            if len(bbox) == 4:
                # Standard axis-aligned bbox
                x1, y1, x2, y2 = [int(coord) for coord in bbox]
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            elif len(bbox) == 8:
                # OBB (Oriented Bounding Box) - draw polygon
                points = np.array(bbox, dtype=np.int32).reshape((-1, 2))
                cv2.polylines(frame, [points], isClosed=True, color=color, thickness=2)

        # Draw center point (small filled circle - pallino pieno)
        cv2.circle(frame, (x, y), 8, color, -1)  # Filled circle

        # Draw confidence label (above bbox if available, else near center)
        label = f"{name} {confidence:.2f}"
        if bbox:
            if len(bbox) >= 2:
                label_pos = (int(bbox[0]), int(bbox[1]) - 10)
            else:
                label_pos = (x + 20, y)
        else:
            label_pos = (x + 20, y)

        cv2.putText(frame, label, label_pos, cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, color, 2)

    return frame


# Global toggle for dT panel (can be toggled via API endpoint)
SHOW_DELTA_T_PANEL = True

# Global toggle for debug overlay (bounding boxes + pallini + confidence)
SHOW_DEBUG_OVERLAY = False

# JPEG quality for streamed frames. The frame size, not the encoding time, is
# what limits a remote viewer: lower quality means more frames on the same link.
STREAM_JPEG_QUALITY = 65

_ERROR_FRAMES: Dict[str, bytes] = {}


def _stream_size() -> tuple:
    """Camera resolution, so the error frame matches the video's aspect ratio."""
    try:
        resolution = load_config().get('camera', {}).get('resolution', {})
        width = int(resolution.get('width', 1280))
        height = int(resolution.get('height', 720))
        if width > 0 and height > 0:
            return width, height
    except Exception:
        pass
    return 1280, 720


def _error_frame_bytes(text: str = "Video stream unavailable") -> bytes:
    """Build (once per message) a black frame carrying an error text."""
    frame_bytes = _ERROR_FRAMES.get(text)
    if frame_bytes is None:
        width, height = _stream_size()
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = max(0.6, width / 1600)
        thickness = max(1, width // 640)
        (text_w, text_h), _baseline = cv2.getTextSize(text, font, scale, thickness)
        origin = ((width - text_w) // 2, (height + text_h) // 2)
        cv2.putText(frame, text, origin, font, scale, (255, 255, 255), thickness)
        ok, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_bytes = buffer.tobytes() if ok else b''
        _ERROR_FRAMES[text] = frame_bytes
    return frame_bytes


class _LatestFrame:
    """
    One RTSP capture shared by every viewer, keeping only the newest frame.

    The old per-request capture read the stream in lockstep with the HTTP
    response: a slow viewer blocked the read, the RTSP buffer filled, and the
    stream fell behind by tens of seconds. Here a reader thread drains the
    capture and stores the newest frame, so a slow viewer skips frames instead
    of queueing them. The capture opens with the first viewer and closes with
    the last: the reader notices the stop between two reads, and a hung read can
    delay the close beyond the RTSP timeout the capture asks for.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._frame = None
        self._seq = 0
        self._ts = 0.0
        self._clients = 0
        self._thread = None
        self._stop = threading.Event()

    def _start_locked(self):
        """Start the reader thread. Caller holds the lock."""
        self._stop.clear()
        thread = threading.Thread(
            target=self._run, name="rtsp-latest-frame", daemon=True)
        try:
            thread.start()
        except Exception as e:
            # Leave _thread empty so the next viewer retries instead of
            # waiting forever on a reader that never existed.
            log('[FAIL]', f"Failed to start video reader: {e}")
            self._thread = None
            return
        self._thread = thread

    def add_client(self):
        with self._lock:
            self._clients += 1
            if self._thread is None:
                self._start_locked()
            else:
                self._stop.clear()  # cancel a pending shutdown

    def ensure_reader(self):
        """Restart the reader if it is missing while viewers are attached."""
        with self._lock:
            if self._thread is None and self._clients > 0:
                self._start_locked()

    def remove_client(self):
        with self._lock:
            self._clients = max(0, self._clients - 1)
            if self._clients == 0:
                self._stop.set()
                log('[OK]', "Video stream closing (no viewers)")

    def latest(self):
        """Newest frame, its sequence number and when it was read.

        The frame is returned without copying: the reader replaces the
        reference, never the array, so the caller can copy it after checking
        the sequence and skip that copy when nothing new arrived.
        """
        with self._lock:
            if self._frame is None:
                return None, -1, 0.0
            return self._frame, self._seq, self._ts

    def _run(self):
        cap = None
        try:
            log('[INIT]', f"Opening video stream (shared): {RTSP_URL}")
            while not self._stop.is_set():
                if cap is None:
                    cap = cv2.VideoCapture(RTSP_URL)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    if not cap.isOpened():
                        log('[FAIL]', "Failed to open video stream")
                        cap.release()
                        cap = None
                        self._stop.wait(2.0)
                        continue
                    log('[OK]', "Video stream opened")

                ret, frame = cap.read()
                if not ret or frame is None or frame.size == 0:
                    log('[WARN]', "Failed to read frame, reconnecting...")
                    cap.release()
                    cap = None
                    self._stop.wait(2.0)
                    continue

                with self._lock:
                    now = time.monotonic()
                    if self._ts > 0 and now - self._ts > 2.0:
                        log('[VIDEO]', f"frame gap {now - self._ts:.1f}s")
                    self._frame = frame
                    self._seq += 1
                    self._ts = now
        except Exception as e:
            log('[FAIL]', f"Video reader error: {e}")
        finally:
            # Bookkeeping must run even if releasing the capture raises,
            # otherwise _thread stays set and no viewer can start a reader.
            try:
                if cap is not None:
                    cap.release()
            except Exception as e:
                log('[WARN]', f"Failed to release video capture: {e}")
            with self._lock:
                self._thread = None
                if self._clients > 0:
                    # A viewer arrived while this thread was shutting down.
                    self._start_locked()
            log('[OK]', "Video stream closed")


_video_hub = _LatestFrame()


def generate_video_frames(tracking_data_callback=None, yolo_detections_callback=None):
    """
    Generator for MJPEG video stream with overlay.

    Sends the newest frame available, at most `fps.video_feed` times per second.
    That value is a ceiling, not a target: when the client is slower the loop
    simply picks a newer frame on the next pass, so latency stays constant
    instead of growing with the RTSP buffer.

    Args:
        tracking_data_callback: Optional function to get latest tracking data
        yolo_detections_callback: Optional function to get latest YOLO detections

    Yields:
        bytes: MJPEG frame data
    """
    # Load gate configuration
    config = load_config()
    gates = config.get('gates', [])

    # Video feed rate ceiling (not a target)
    tracking_config = config.get('tracking', {})
    fps_settings = tracking_config.get('fps', {})
    fps_ceiling = fps_settings.get('video_feed', 15)
    min_interval = (1.0 / fps_ceiling) if fps_ceiling else 0.0

    if not RTSP_URL:
        log('[FAIL]', "Camera credentials missing - video feed unavailable")
        frame_bytes = _error_frame_bytes("Camera credentials missing")
        while True:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(1)

    _video_hub.add_client()
    last_seq = -1
    last_chunk = None
    wait_started = None

    try:
        while True:
            frame, seq, _ts = _video_hub.latest()

            if frame is None:
                _video_hub.ensure_reader()  # a failed start must not leave a viewer stuck
                if wait_started is None:
                    wait_started = time.monotonic()
                # The RTSP handshake takes a moment: say what is happening
                # instead of claiming the stream is unavailable.
                text = ("Connecting to camera..." if time.monotonic() - wait_started < 5
                        else "Video stream unavailable")
                frame_bytes = _error_frame_bytes(text)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                time.sleep(1)
                continue

            if seq == last_seq:
                if last_chunk is not None and time.monotonic() - _ts > 1.0:
                    # A stalled capture: repeat the last frame as a keepalive.
                    # Flashing an error frame over a running video helps nobody.
                    # Also retry a reader that died while this frame is cached.
                    _video_hub.ensure_reader()
                    yield last_chunk
                    time.sleep(1.0)
                else:
                    time.sleep(0.01)
                continue

            last_seq = seq
            frame = frame.copy()  # drawing mutates it; the hub keeps the original
            start_time = time.time()

            # Draw gate overlays
            frame = draw_gates(frame, gates)

            # Draw debug overlay (bounding boxes + pallini + confidence) when enabled
            global SHOW_DEBUG_OVERLAY
            if SHOW_DEBUG_OVERLAY and yolo_detections_callback:
                try:
                    detections = yolo_detections_callback()
                    if detections:
                        frame = draw_debug_overlay(frame, detections)
                except Exception as e:
                    log('[WARN]', f"Error drawing debug overlay: {e}")

            # === TRACKING INFO PANEL (toggle with SHOW_DELTA_T_PANEL global) ===
            global SHOW_DELTA_T_PANEL
            if SHOW_DELTA_T_PANEL:
                # Get tracking data
                tracking_data = None
                if tracking_data_callback:
                    try:
                        tracking_data = tracking_data_callback()
                    except Exception as e:
                        log('[WARN]', f"Error getting tracking data: {e}")

                # Draw tracking info panel
                frame = draw_tracking_info(frame, tracking_data)

            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame,
                                       [cv2.IMWRITE_JPEG_QUALITY, STREAM_JPEG_QUALITY])
            if not ret:
                continue

            frame_bytes = buffer.tobytes()

            # Yield multipart frame
            chunk = (b'--frame\r\n'
                     b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            yield chunk
            last_chunk = chunk

            # Ceiling only: a slow client has already spent more than this.
            elapsed = time.time() - start_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)

    except Exception as e:
        log('[FAIL]', f"Video stream error: {e}")
    finally:
        _video_hub.remove_client()


if __name__ == '__main__':
    # Test video feed
    print("Testing video feed...")

    for i, frame_data in enumerate(generate_video_frames()):
        if i >= 100:  # Test 100 frames
            break
        print(f"Frame {i}: {len(frame_data)} bytes")

    log('[INIT]', "Video feed test complete")
