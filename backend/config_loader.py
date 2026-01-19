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

    Args:
        config: Configuration dict to save
        config_path: Path to config.json (defaults to project root)

    Raises:
        IOError: If unable to write config file
    """
    if config_path is None:
        config_path = get_config_path()

    # Filter out keys starting with _ (comments, metadata)
    filtered_config = {k: v for k, v in config.items() if not k.startswith('_')}

    # Generate JSON with standard formatting
    json_str = json.dumps(filtered_config, indent=2, ensure_ascii=False)

    with open(config_path, 'w', encoding='utf-8', newline='\n') as f:
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
