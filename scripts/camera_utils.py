"""
Camera Utilities - Shared camera config loader

This module provides a centralized way to load camera credentials
from the backend/camera_config.json file.
"""
import json
import sys
from pathlib import Path


def load_camera_config():
    """
    Load camera configuration from camera_config.json in project root.

    Returns:
        tuple: (rtsp_url, camera_ip, camera_port, stream)

    Raises:
        SystemExit: If config file not found or invalid
    """
    # Config is in project root (one level up from scripts/)
    config_path = Path(__file__).parent.parent / 'camera_config.json'

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        camera_ip = config.get('camera_ip', '192.168.1.4')
        camera_port = config.get('camera_port', 554)
        stream = config.get('stream', 'stream2')
        username = config['username']
        password = config['password']

        rtsp_url = f"rtsp://{username}:{password}@{camera_ip}:{camera_port}/{stream}"

        return rtsp_url, camera_ip, camera_port, stream

    except FileNotFoundError:
        print(f"\n❌ ERROR: Camera config not found at {config_path}")
        print(f"   Create it from template:")
        print(f"   cd ~/Documents/_PROGETTI/z21-Terminal")
        print(f"   cp camera_config.json.example camera_config.json")
        print(f"   micro camera_config.json  # Edit with your credentials")
        print(f"\n   See README_CAMERA.md for details.\n")
        sys.exit(1)

    except KeyError as e:
        print(f"\n❌ ERROR: Missing required field in camera config: {e}")
        print(f"   Check {config_path} and ensure 'username' and 'password' are set.")
        print(f"   See backend/README_CAMERA.md for details.\n")
        sys.exit(1)

    except json.JSONDecodeError as e:
        print(f"\n❌ ERROR: Invalid JSON in camera config: {e}")
        print(f"   Check {config_path} for syntax errors.\n")
        sys.exit(1)


if __name__ == '__main__':
    # Test the loader
    rtsp_url, ip, port, stream = load_camera_config()
    print(f"✅ Camera config loaded successfully!")
    print(f"   IP: {ip}:{port}")
    print(f"   Stream: {stream}")
    print(f"   RTSP URL: rtsp://***:***@{ip}:{port}/{stream}")
