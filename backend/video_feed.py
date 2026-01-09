"""
Video Feed Module - MJPEG stream with gate overlay
"""
import sys
import os

# Silence FFmpeg/H264 decoder warnings BEFORE importing cv2
os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'  # Quiet mode
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'

import cv2
import json
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional

from config_loader import load_config
from log_colors import log


# Configuration paths (all in project root)
project_root = Path(__file__).parent.parent  # z21-Terminal/ root
CONFIG_PATH = project_root / 'config.json'
CAMERA_CONFIG_PATH = project_root / 'camera_config.json'


def load_camera_config() -> str:
    """Load camera configuration and build RTSP URL for video feed."""
    try:
        with open(CAMERA_CONFIG_PATH, 'r') as f:
            config = json.load(f)

        camera_ip = config.get('camera_ip', '192.168.1.4')
        camera_port = config.get('camera_port', 554)
        stream = config.get('stream', 'stream2')
        username = config['username']
        password = config['password']

        rtsp_url = f"rtsp://{username}:{password}@{camera_ip}:{camera_port}/{stream}"
        return rtsp_url
    except FileNotFoundError:
        log('[ERROR]', f"Camera config not found at {CAMERA_CONFIG_PATH}")
        print(f"   Create it from template: cp {CAMERA_CONFIG_PATH}.example {CAMERA_CONFIG_PATH}")
        return None
    except KeyError as e:
        log('[ERROR]', f"Missing required field in camera config: {e}")
        return None
    except json.JSONDecodeError as e:
        log('[ERROR]', f"Invalid JSON in camera config: {e}")
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
            cv2.putText(frame, f"Dt: {sign}{delta_t:.3f}s", (text_x, y), font, font_scale, (255, 255, 255), 1)
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
            cv2.putText(frame, "Dt: Waiting...", (text_x, y), font, font_scale, (128, 128, 128), 1)

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
    # Color mapping for addresses (same as track_consist_yolo.py for consistency)
    COLORS = {
        1: (255, 255, 0),   # Loco 1 (Gr675) - Yellow
        5: (255, 128, 0),   # Loco 5 (D645) - Orange
        7: (0, 255, 0),     # Loco 7 (E656) - Green
        8: (0, 0, 255)      # Loco 8 (E444) - Red
    }

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
    # Color mapping for addresses (same as track_consist_yolo.py for consistency)
    COLORS = {
        1: (255, 255, 0),   # Loco 1 (Gr675) - Yellow
        5: (255, 128, 0),   # Loco 5 (D645) - Orange
        7: (0, 255, 0),     # Loco 7 (E656) - Green
        8: (0, 0, 255)      # Loco 8 (E444) - Red
    }

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
        if bbox and len(bbox) == 4:
            x1, y1, x2, y2 = [int(coord) for coord in bbox]
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Draw center point (larger hollow circle for debug visibility)
        cv2.circle(frame, (x, y), 15, color, 2)  # Hollow circle

        # Draw confidence label (above bbox if available, else near center)
        label = f"{name} {confidence:.2f}"
        if bbox and len(bbox) == 4:
            label_pos = (int(bbox[0]), int(bbox[1]) - 10)
        else:
            label_pos = (x + 20, y)

        cv2.putText(frame, label, label_pos, cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, color, 2)

    return frame


# Global toggle for Δt panel (can be toggled via API endpoint)
SHOW_DELTA_T_PANEL = True

# Global toggle for debug overlay (bounding boxes + pallini + confidence)
SHOW_DEBUG_OVERLAY = False


def generate_video_frames(tracking_data_callback=None, yolo_detections_callback=None):
    """
    Generator for MJPEG video stream with overlay

    Args:
        tracking_data_callback: Optional function to get latest tracking data
        yolo_detections_callback: Optional function to get latest YOLO detections

    Yields:
        bytes: MJPEG frame data
    """
    # Load gate configuration
    config = load_config()
    gates = config.get('gates', [])

    # Load FPS from config (feature added in Phase 4 - keep it)
    tracking_config = config.get('tracking', {})
    fps_settings = tracking_config.get('fps', {})
    fps_target = fps_settings.get('video_feed', 15)  # Load from config, fallback to 15

    log('[INIT]', f"Opening video stream: {RTSP_URL}")
    cap = cv2.VideoCapture(RTSP_URL)

    # CRITICAL: Set minimal buffer to prevent lag accumulation
    # RTSP streams buffer frames causing 20+ second delays over time
    # buffer=1 = always read FRESHEST frame available (adaptive skip if processing is slow)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        log('[FAIL]', "Failed to open video stream")
        # Return a black frame with error message
        error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(error_frame, "Video stream unavailable", (100, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        ret, buffer = cv2.imencode('.jpg', error_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_bytes = buffer.tobytes()
        while True:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(1)

    log('[OK]', "Video stream opened")

    frame_count = 0
    frame_delay = 1.0 / fps_target

    try:
        while True:
            start_time = time.time()

            ret, frame = cap.read()
            if not ret:
                log('[WARN]', f"Failed to read frame, reconnecting...")
                cap.release()
                time.sleep(2)
                cap = cv2.VideoCapture(RTSP_URL)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Restore buffer=1 after reconnect
                continue

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
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                continue

            frame_bytes = buffer.tobytes()

            # Yield multipart frame
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            frame_count += 1

            # Frame rate limiting
            elapsed = time.time() - start_time
            sleep_time = frame_delay - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except Exception as e:
        log('[FAIL]', f"Video stream error: {e}")
    finally:
        cap.release()
        log('[OK]', "Video stream closed")


if __name__ == '__main__':
    # Test video feed
    print("Testing video feed...")

    for i, frame_data in enumerate(generate_video_frames()):
        if i >= 100:  # Test 100 frames
            break
        print(f"Frame {i}: {len(frame_data)} bytes")

    log('[INIT]', "Video feed test complete")
