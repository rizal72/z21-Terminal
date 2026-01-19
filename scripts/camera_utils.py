"""
Camera Utilities - Shared camera config loader

This module provides a centralized way to load camera credentials
from config.json + config.local.json (unified config system).
"""
import sys
from pathlib import Path

# Add backend to path for config_loader import
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))
from config_loader import load_config


def load_camera_config():
    """
    Load camera configuration from config.json (credentials from config.local.json).

    Returns:
        tuple: (rtsp_url, camera_ip, camera_port, stream)

    Raises:
        SystemExit: If config file not found or credentials missing
    """
    try:
        config = load_config()  # Auto-merges config.local.json
        camera = config.get('camera', {})

        camera_ip = camera.get('ip', '192.168.1.4')
        camera_port = camera.get('port', 554)
        stream = camera.get('stream', 'stream2')
        username = camera.get('username', '')
        password = camera.get('password', '')

        if not username or not password:
            print(f"\n❌ ERROR: Camera credentials missing")
            print(f"   Add credentials to config.local.json (gitignored):")
            print(f"   cd ~/Documents/_PROGETTI/z21-Terminal")
            print(f"   cp config.local.json.example config.local.json")
            print(f"   micro config.local.json  # Add username/password")
            print(f"\n   See README_CAMERA.md for details.\n")
            sys.exit(1)

        rtsp_url = f"rtsp://{username}:{password}@{camera_ip}:{camera_port}/{stream}"

        return rtsp_url, camera_ip, camera_port, stream

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: Config file not found: {e}")
        print(f"   Ensure config.json exists in project root.")
        print(f"   See README_CAMERA.md for setup instructions.\n")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ ERROR: Failed to load camera config: {e}\n")
        sys.exit(1)


if __name__ == '__main__':
    # Test the loader
    rtsp_url, ip, port, stream = load_camera_config()
    print(f"✅ Camera config loaded successfully!")
    print(f"   IP: {ip}:{port}")
    print(f"   Stream: {stream}")
    print(f"   RTSP URL: rtsp://***:***@{ip}:{port}/{stream}")
