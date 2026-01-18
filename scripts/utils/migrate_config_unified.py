#!/usr/bin/env python3
"""
Config Migration Script - Unified Settings Structure

Migrates z21-Terminal configuration to unified structure for Settings UI:
1. Extracts hardcoded Z21 settings → config.json
2. Merges camera_config.json → config.json (credentials → config.local.json)
3. Adds video section → config.json
4. Creates config.local.json (gitignored) for credentials
5. Backs up existing config.json

Run this ONCE during Settings UI migration.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime


def load_json(filepath):
    """Load JSON file with error handling"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in {filepath}: {e}")
        return None


def save_json(filepath, data, indent=2):
    """Save JSON file with UTF-8 encoding"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    print(f"[OK] Saved: {filepath}")


def backup_file(filepath):
    """Create timestamped backup of file"""
    if not filepath.exists():
        return None

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = filepath.parent / f"{filepath.stem}.backup_{timestamp}{filepath.suffix}"
    shutil.copy(filepath, backup_path)
    print(f"[BACKUP] {filepath} -> {backup_path}")
    return backup_path


def main():
    # Paths
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / 'config.json'
    camera_config_path = project_root / 'camera_config.json'
    config_local_path = project_root / 'config.local.json'
    gitignore_path = project_root / '.gitignore'

    print("=" * 60)
    print("Config Migration - Unified Settings Structure")
    print("=" * 60)

    # Step 1: Backup config.json
    print("\n[STEP 1] Backing up config.json...")
    if not config_path.exists():
        print(f"[ERROR] config.json not found: {config_path}")
        return
    backup_file(config_path)

    # Step 2: Load existing config
    print("\n[STEP 2] Loading existing config.json...")
    config = load_json(config_path)
    if config is None:
        print("[ERROR] Failed to load config.json")
        return
    print(f"[OK] Loaded config.json")

    # Step 3: Load camera_config.json (if exists)
    print("\n[STEP 3] Loading camera_config.json...")
    camera_config = load_json(camera_config_path)
    if camera_config:
        print(f"[OK] Loaded camera_config.json")
    else:
        print("[WARN] camera_config.json not found, using defaults")
        camera_config = {}

    # Step 4: Add z21 section (extract hardcoded values)
    print("\n[STEP 4] Adding z21 section...")
    if 'z21' not in config:
        config['z21'] = {
            'host': '192.168.1.111',  # Hardcoded in main.py:318 and z21_manager.py:34
            'port': 21105,
            'notes': 'Roco Z21 Bianca hardware controller'
        }
        print("[OK] Added z21 section")
    else:
        print("[SKIP] z21 section already exists")

    # Step 5: Add camera section (merge from camera_config.json)
    print("\n[STEP 5] Adding camera section...")
    if 'camera' not in config:
        config['camera'] = {
            'ip': camera_config.get('camera_ip', '192.168.1.4'),
            'port': camera_config.get('camera_port', 554),
            'stream': camera_config.get('stream', 'stream2'),
            'resolution': {
                'width': 1280,
                'height': 720
            },
            'username': '',  # Empty in config.json (versionated)
            'password': '',  # Empty in config.json (versionated)
            'notes': 'Camera credentials MUST be in config.local.json (gitignored)'
        }
        print("[OK] Added camera section")
    else:
        print("[SKIP] camera section already exists")

    # Step 6: Add video section (extract from tracking.fps.video_feed)
    print("\n[STEP 6] Adding video section...")
    if 'video' not in config:
        video_fps = config.get('tracking', {}).get('fps', {}).get('video_feed', 30)
        config['video'] = {
            'fps': video_fps,
            'notes': 'MJPEG video stream frame rate (hot reload, no restart needed)'
        }
        print(f"[OK] Added video section (fps: {video_fps})")
    else:
        print("[SKIP] video section already exists")

    # Step 7: Save updated config.json
    print("\n[STEP 7] Saving updated config.json...")
    save_json(config_path, config)

    # Step 8: Create config.local.json with camera credentials
    print("\n[STEP 8] Creating config.local.json...")
    config_local_exists = config_local_path.exists()

    if not config_local_exists:
        # Extract credentials from camera_config.json
        username = camera_config.get('username', '')
        password = camera_config.get('password', '')

        config_local = {
            'camera': {
                'username': username,
                'password': password
            },
            '_notes': 'This file is gitignored and contains machine-specific secrets'
        }

        save_json(config_local_path, config_local)

        if username or password:
            print(f"[OK] Created config.local.json with camera credentials")
        else:
            print(f"[OK] Created config.local.json (empty credentials)")
    else:
        print("[SKIP] config.local.json already exists (not overwriting)")

    # Step 9: Update .gitignore
    print("\n[STEP 9] Updating .gitignore...")
    gitignore_content = gitignore_path.read_text() if gitignore_path.exists() else ''

    if 'config.local.json' not in gitignore_content:
        with open(gitignore_path, 'a') as f:
            if gitignore_content and not gitignore_content.endswith('\n'):
                f.write('\n')
            f.write('\n# Config overrides (machine-specific secrets)\n')
            f.write('config.local.json\n')
        print("[OK] Added config.local.json to .gitignore")
    else:
        print("[SKIP] config.local.json already in .gitignore")

    # Step 10: Summary
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print("\nChanges made:")
    print("  [+] config.json - Added z21, camera, video sections")
    print("  [+] config.local.json - Camera credentials (gitignored)")
    print("  [+] .gitignore - Ensured config.local.json is ignored")

    if camera_config_path.exists():
        print(f"\n[INFO] You can now delete camera_config.json (deprecated)")
        print(f"       Credentials moved to config.local.json")

    print("\nNext steps:")
    print("  1. Update backend loaders (main.py, z21_manager.py, video_feed.py)")
    print("  2. Test backend startup with unified config")
    print("  3. Implement Settings UI frontend")
    print("\nSee docs/SETTINGS_UI_DESIGN.md for complete implementation plan.")
    print("=" * 60)


if __name__ == '__main__':
    main()
