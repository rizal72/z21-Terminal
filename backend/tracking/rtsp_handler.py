"""
RTSP Handler - Shared RTSP stream utilities

Used by both:
- backend/tracking_daemon.py (headless YOLO tracking)
- scripts/track_consist_yolo.py (standalone GUI testing)
- backend/video_feed.py (MJPEG stream for web browser)

Handles camera config loading and RTSP stream setup with optimal buffering.
"""
import cv2
import json
import sys
from pathlib import Path

# Camera config path (project root)
project_root = Path(__file__).parent.parent.parent  # z21-Terminal/ root
CAMERA_CONFIG_PATH = project_root / 'camera_config.json'


def load_camera_config(stream_key='stream'):
    """
    Load camera configuration and build RTSP URL.

    Args:
        stream_key: Key in camera_config.json for stream ('stream', 'stream_video_feed', etc.)

    Returns:
        rtsp_url: RTSP URL string

    Raises:
        SystemExit on config errors (file not found, missing fields, invalid JSON)
    """
    try:
        with open(CAMERA_CONFIG_PATH, 'r') as f:
            config = json.load(f)

        camera_ip = config.get('camera_ip', '192.168.1.4')
        camera_port = config.get('camera_port', 554)
        stream = config.get(stream_key, 'stream2')  # Default to 'stream2' if key missing
        username = config['username']
        password = config['password']

        rtsp_url = f"rtsp://{username}:{password}@{camera_ip}:{camera_port}/{stream}"
        return rtsp_url
    except FileNotFoundError:
        print(f"❌ ERROR: Camera config not found at {CAMERA_CONFIG_PATH}")
        print(f"   Create it from template: cp {CAMERA_CONFIG_PATH}.example {CAMERA_CONFIG_PATH}")
        print(f"   Then edit with your camera credentials.")
        sys.exit(1)
    except KeyError as e:
        print(f"❌ ERROR: Missing required field in camera config: {e}")
        print(f"   Check {CAMERA_CONFIG_PATH} and ensure 'username' and 'password' are set.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in camera config: {e}")
        sys.exit(1)


def setup_rtsp_stream(rtsp_url, description="video stream"):
    """
    Open RTSP stream with optimal buffer settings (buffer=1 for real-time).

    Args:
        rtsp_url: RTSP URL string
        description: Human-readable description for logging

    Returns:
        cv2.VideoCapture: Opened video capture object (or None on failure)

    Note:
        Sets CAP_PROP_BUFFERSIZE=1 to prevent progressive lag accumulation.
        This ensures always-fresh frames (adaptive skip if processing is slow).
    """
    print(f"📹 Opening {description}: {rtsp_url}")
    cap = cv2.VideoCapture(rtsp_url)

    # CRITICAL: Set minimal buffer to prevent lag accumulation
    # RTSP streams buffer frames causing 20+ second delays over time
    # buffer=1 = always read FRESHEST frame available (adaptive skip if processing is slow)
    # This ensures gate crossings are detected in real-time, not 20s late!
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print(f"❌ Failed to open {description}")
        return None

    print(f"✅ {description.capitalize()} opened")
    return cap


def reconnect_rtsp_stream(cap, rtsp_url, description="video stream"):
    """
    Reconnect RTSP stream after failure (with buffer=1 restored).

    Args:
        cap: Existing VideoCapture object (will be released)
        rtsp_url: RTSP URL string
        description: Human-readable description for logging

    Returns:
        cv2.VideoCapture: New video capture object
    """
    if cap:
        cap.release()

    print(f"🔄 Reconnecting {description}...")
    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Restore buffer=1 after reconnect

    if cap.isOpened():
        print(f"✅ {description.capitalize()} reconnected")
    else:
        print(f"❌ Failed to reconnect {description}")

    return cap
