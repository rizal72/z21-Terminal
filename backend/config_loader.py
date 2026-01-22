"""
Centralized configuration loader for z21-Terminal

Supports base config.json + optional config.local.json override (gitignored)
"""

import json
from pathlib import Path
from typing import Dict, Any
from log_colors import log

# Track first load to print local override message only once
_first_load = True


def deep_merge(base: Dict[Any, Any], override: Dict[Any, Any]) -> Dict[Any, Any]:
    """
    Deep merge two dictionaries, with override taking precedence.

    Args:
        base: Base configuration dict
        override: Override configuration dict

    Returns:
        Merged configuration dict
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursive merge for nested dicts
            result[key] = deep_merge(result[key], value)
        else:
            # Override value (or add new key)
            result[key] = value

    return result


def load_config(config_path: Path = None) -> Dict[str, Any]:
    """
    Load configuration from config.json with optional config.local.json override.

    Priority (highest to lowest):
    1. config.local.json (gitignored, machine-specific overrides)
    2. config.json (tracked in git, shared configuration)

    Args:
        config_path: Path to config.json (defaults to project root)

    Returns:
        Merged configuration dict

    Raises:
        FileNotFoundError: If config.json not found
        json.JSONDecodeError: If config files contain invalid JSON
    """
    # Default to project root/config.json
    if config_path is None:
        # Assume config_loader.py is in backend/ folder
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config.json"

    # Load base config (required)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            f"Expected location: project_root/config.json"
        )

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Load local override (optional)
    global _first_load
    local_config_path = config_path.parent / "config.local.json"
    if local_config_path.exists():
        try:
            with open(local_config_path, 'r', encoding='utf-8') as f:
                local_config = json.load(f)

            # Deep merge: local overrides base
            config = deep_merge(config, local_config)

            # Print only on first load (avoid spam)
            if _first_load:
                log('[INIT]', f"Config loaded with local overrides: {local_config_path.name}")
                _first_load = False
        except json.JSONDecodeError as e:
            log('[WARN]', f"Warning: Invalid JSON in {local_config_path}, ignoring: {e}")

    return config


def get_config_path() -> Path:
    """
    Get the path to config.json in project root.

    Returns:
        Path to config.json
    """
    project_root = Path(__file__).parent.parent
    return project_root / "config.json"


def save_config(config: Dict[str, Any], config_path: Path = None) -> None:
    """
    Save configuration to config.json (does NOT save to config.local.json).

    Camera credentials (username/password) are automatically removed before saving
    (they belong in config.local.json only).

    Args:
        config: Configuration dict to save
        config_path: Path to config.json (defaults to project root)

    Raises:
        IOError: If unable to write config file
    """
    if config_path is None:
        config_path = get_config_path()

    # Deep copy to avoid modifying the original config
    import copy
    filtered_config = copy.deepcopy(config)

    # Filter out keys starting with _ (comments, metadata)
    filtered_config = {k: v for k, v in filtered_config.items() if not k.startswith('_')}

    # Remove local-only settings (they belong in config.local.json only)
    # Camera credentials
    if 'camera' in filtered_config:
        filtered_config['camera'].pop('username', None)
        filtered_config['camera'].pop('password', None)

    # Debug mode (local development setting)
    if 'debug' in filtered_config and 'enabled' in filtered_config['debug']:
        filtered_config['debug']['enabled'] = False  # Always false in config.json (fallback)

    # Generate JSON with standard formatting
    json_str = json.dumps(filtered_config, indent=2, ensure_ascii=False)

    with open(config_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json_str)
        f.write('\n')  # Add trailing newline (POSIX standard)


def save_local_config(local_overrides: Dict[str, Any]) -> None:
    """
    Save local-only settings to config.local.json (gitignored).

    Used for machine-specific overrides (camera credentials, debug mode, etc.)

    Args:
        local_overrides: Dict with local overrides (e.g., {"debug": {"enabled": true}})

    Raises:
        IOError: If unable to write config.local.json
    """
    project_root = Path(__file__).parent.parent
    local_config_path = project_root / "config.local.json"

    # Load existing config.local.json (if exists)
    existing_local = {}
    if local_config_path.exists():
        try:
            with open(local_config_path, 'r', encoding='utf-8') as f:
                existing_local = json.load(f)
        except json.JSONDecodeError:
            pass  # Ignore, will overwrite

    # Deep merge new overrides into existing
    merged_local = deep_merge(existing_local, local_overrides)

    # Write to config.local.json
    json_str = json.dumps(merged_local, indent=2, ensure_ascii=False)
    with open(local_config_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json_str)
        f.write('\n')  # Add trailing newline


def save_config_backup(config: Dict[str, Any], config_path: Path = None) -> None:
    """Save configuration backup to config.json.backup (unified backup for gates + CV profiles + future features)."""
    if config_path is None:
        config_path = get_config_path()
    backup_path = config_path.parent / f"{config_path.name}.backup"
    json_str = json.dumps(config, indent=2, ensure_ascii=False)
    with open(backup_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json_str)
        f.write('\n')


def load_config_backup(config_path: Path = None) -> Dict[str, Any]:
    """Load configuration from config.json.backup if exists, otherwise return empty dict."""
    if config_path is None:
        config_path = get_config_path()
    backup_path = config_path.parent / f"{config_path.name}.backup"
    if not backup_path.exists():
        return {}
    with open(backup_path, 'r', encoding='utf-8') as f:
        return json.load(f)
