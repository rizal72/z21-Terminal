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


# Configuration paths (all in project root)
project_root = Path(__file__).parent.parent  # z21-Terminal/ root
GATE_CONFIG_PATH = project_root / 'gate_config.json'
CAMERA_CONFIG_PATH = project_root / 'camera_config.json'


def load_camera_config() -> str:
    """Load camera configuration and build RTSP URL."""
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
        print(f"❌ ERROR: Camera config not found at {CAMERA_CONFIG_PATH}")
        print(f"   Create it from template: cp {CAMERA_CONFIG_PATH}.example {CAMERA_CONFIG_PATH}")
        return None
    except KeyError as e:
        print(f"❌ ERROR: Missing required field in camera config: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in camera config: {e}")
        return None


RTSP_URL = load_camera_config()


def load_gate_config() -> Dict:
    """Load gate configuration from JSON"""
    try:
        with open(GATE_CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading gate config: {e}")
        return {'gates': []}


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
        color = tuple(gate.get('color', [255, 255, 0]))  # BGR format

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

        # Draw gate label
        label = f"G{gate_id}"
        label_pos = (cx - 15, cy - 10)
        cv2.putText(frame, label, label_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    return frame


def draw_tracking_info(frame: np.ndarray, tracking_data: Optional[Dict]) -> np.ndarray:
    """
    Draw tracking information panel (Δt stats, locomotive positions)

    Args:
        frame: Input frame
        tracking_data: Dict with tracking info (delta_t, status, etc.)

    Returns:
        Frame with tracking info overlay
    """
    # Panel background (semi-transparent, compact size)
    panel_height = 110  # Ridotto da 150
    panel_width = 250   # Ridotto da 300
    panel_x = 10
    # Position panel at BOTTOM left
    frame_height = frame.shape[0]
    panel_y = frame_height - panel_height - 10

    overlay = frame.copy()
    cv2.rectangle(overlay, (panel_x, panel_y),
                  (panel_x + panel_width, panel_y + panel_height),
                  (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)

    # Draw text (simple font for performance)
    text_color = (255, 255, 255)
    font = cv2.FONT_HERSHEY_PLAIN  # Simpler font (faster rendering)
    font_scale = 1.1
    line_height = 20  # Ridotto da 25
    y = panel_y + 18

    # Consist info
    consist_address = tracking_data.get('consist_address', 11) if tracking_data else 11
    cv2.putText(frame, f"Consist {consist_address}", (panel_x + 10, y),
                font, font_scale, text_color, 1)
    y += line_height

    # Delta t
    delta_t = tracking_data.get('delta_t') if tracking_data else None
    if delta_t is not None:
        sign = '+' if delta_t >= 0 else ''
        cv2.putText(frame, f"Delta t: {sign}{delta_t:.3f}s", (panel_x + 10, y),
                    font, font_scale, text_color, 1)
        y += line_height

        # Status (color-coded)
        status = tracking_data.get('status', 'UNKNOWN')
        if status == 'SYNCED':
            status_color = (0, 255, 0)  # Green
        elif status == 'WARNING':
            status_color = (0, 255, 255)  # Yellow
        elif status == 'CRITICAL':
            status_color = (0, 0, 255)  # Red
        else:
            status_color = (128, 128, 128)  # Gray

        cv2.putText(frame, f"Status: {status}", (panel_x + 10, y),
                    font, font_scale, status_color, 1)
        y += line_height
    else:
        cv2.putText(frame, "Delta t: Waiting...", (panel_x + 10, y),
                    font, font_scale, (128, 128, 128), 1)
        # y += line_height * 2  # Commented: not needed without timestamp

    # Timestamp - COMMENTED FOR PERFORMANCE (uncomment if needed)
    # timestamp = tracking_data.get('timestamp') if tracking_data else None
    # if timestamp:
    #     time_str = time.strftime('%H:%M:%S', time.localtime(timestamp))
    #     cv2.putText(frame, f"Updated: {time_str}", (panel_x + 10, y),
    #                 font, font_scale, (180, 180, 180), 1)

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
    config = load_gate_config()
    gates = config.get('gates', [])

    print(f"🎥 Opening video stream: {RTSP_URL}")
    cap = cv2.VideoCapture(RTSP_URL)

    if not cap.isOpened():
        print("  ✗ Failed to open video stream")
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

    print("  ✓ Video stream opened")

    frame_count = 0
    fps_target = 15  # Target FPS for stream (fluido per controllare loco)
    frame_delay = 1.0 / fps_target

    try:
        while True:
            start_time = time.time()

            ret, frame = cap.read()
            if not ret:
                print("  ⚠️  Failed to read frame, reconnecting...")
                cap.release()
                time.sleep(2)
                cap = cv2.VideoCapture(RTSP_URL)
                continue

            # Draw gate overlays
            frame = draw_gates(frame, gates)

            # Draw locomotive markers (pallini YOLO) - DISABLED: RTSP delay too high
            # if yolo_detections_callback:
            #     try:
            #         detections = yolo_detections_callback()
            #         if detections:
            #             frame = draw_locomotive_markers(frame, detections)
            #     except Exception as e:
            #         print(f"  ⚠️  Error getting YOLO detections: {e}")

            # === TRACKING INFO PANEL - COMMENTED (moved to HTML overlay for performance) ===
            # Get tracking data
            # tracking_data = None
            # if tracking_data_callback:
            #     try:
            #         tracking_data = tracking_data_callback()
            #     except Exception as e:
            #         print(f"  ⚠️  Error getting tracking data: {e}")

            # Draw tracking info panel (ALWAYS redraw, no cache)
            # frame = draw_tracking_info(frame, tracking_data)
            # === END COMMENTED SECTION ===

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
        print(f"  ✗ Video stream error: {e}")
    finally:
        cap.release()
        print("  ✓ Video stream closed")


if __name__ == '__main__':
    # Test video feed
    print("Testing video feed...")

    for i, frame_data in enumerate(generate_video_frames()):
        if i >= 100:  # Test 100 frames
            break
        print(f"Frame {i}: {len(frame_data)} bytes")

    print("✅ Video feed test complete")
