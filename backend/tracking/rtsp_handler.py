"""
RTSP Handler - Shared RTSP stream utilities

Used by both:
- backend/tracking_daemon.py (headless YOLO tracking)
- scripts/track_consist_yolo.py (standalone GUI testing)
- backend/video_feed.py (MJPEG stream for web browser)

All use the same 'stream' from unified config.json (credentials from config.local.json).
Handles camera config loading and RTSP stream setup with optimal buffering.
"""
import os
import json
import sys
from pathlib import Path

# TCP transport + 5s socket timeout (UDP over WiFi = packet loss = decode errors)
os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp|stimeout;5000000'

import cv2

# Add backend to path for log_colors and config_loader imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))
from log_colors import log
from config_loader import load_config


def load_camera_config():
    """
    Load camera configuration from unified config.json and build RTSP URL.

    Reads from config['camera'] section (credentials auto-merged from config.local.json).

    Returns:
        rtsp_url: RTSP URL string

    Raises:
        SystemExit on config errors (missing credentials, invalid config)
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
            log('[ERROR]', 'Camera credentials missing')
            print('   Add credentials to config.local.json (gitignored):')
            print('   { "camera": { "username": "...", "password": "..." } }')
            sys.exit(1)

        rtsp_url = f"rtsp://{username}:{password}@{camera_ip}:{camera_port}/{stream}"
        return rtsp_url
    except Exception as e:
        log('[ERROR]', f"Error loading camera config: {e}")
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
    log('[INIT]', f"Opening {description}: {rtsp_url}")
    cap = cv2.VideoCapture(rtsp_url)

    # CRITICAL: Set minimal buffer to prevent lag accumulation
    # RTSP streams buffer frames causing 20+ second delays over time
    # buffer=1 = always read FRESHEST frame available (adaptive skip if processing is slow)
    # This ensures gate crossings are detected in real-time, not 20s late!
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        log('[ERROR]', f"Failed to open {description}")
        return None

    log('[INIT]', f"{description.capitalize()} opened")
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

    log('[INIT]', f"Reconnecting {description}...")
    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Restore buffer=1 after reconnect

    if cap.isOpened():
        log('[INIT]', f"{description.capitalize()} reconnected")
    else:
        log('[ERROR]', f"Failed to reconnect {description}")

    return cap
