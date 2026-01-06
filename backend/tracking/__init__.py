"""
Tracking Module - Shared YOLO tracking logic

This module contains shared components used by both:
- tracking_daemon.py (headless WebSocket daemon)
- scripts/track_consist_yolo.py (standalone GUI testing)
"""

from .yolo_tracker import YOLOTracker
from .rtsp_handler import setup_rtsp_stream, load_camera_config, reconnect_rtsp_stream

__all__ = ['YOLOTracker', 'setup_rtsp_stream', 'load_camera_config', 'reconnect_rtsp_stream']
