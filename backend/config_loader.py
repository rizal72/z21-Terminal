"""
Centralized configuration loader for z21-Terminal

Supports base config.json + optional config.local.json override (gitignored)
"""

import json
from pathlib import Path
from typing import Dict, Any

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
                print(f"✅ Config loaded with local overrides: {local_config_path.name}")
                _first_load = False
        except json.JSONDecodeError as e:
            print(f"⚠️  Warning: Invalid JSON in {local_config_path}, ignoring: {e}")

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
    Save configuration to config.json with inline arrays (does NOT save to config.local.json).

    Arrays of primitives (numbers, strings, booleans) are formatted inline:
        "gate_ids": [3, 4]
        "center": [1227, 213]

    Arrays of objects remain multi-line:
        "gates": [
          { ... },
          { ... }
        ]

    Args:
        config: Configuration dict to save
        config_path: Path to config.json (defaults to project root)

    Raises:
        IOError: If unable to write config file
    """
    if config_path is None:
        config_path = get_config_path()

    # Generate JSON with standard formatting
    json_str = json.dumps(config, indent=2, ensure_ascii=False)

    # Compact arrays of primitives - multiple passes to handle nested arrays
    import re

    def compact_pass(text):
        """Single pass of array compaction. Returns (new_text, changed)."""
        lines = text.split('\n')
        result = []
        i = 0
        changed = False

        while i < len(lines):
            line = lines[i]

            # Check if this line opens an array (ends with [)
            if line.rstrip(',').rstrip().endswith('['):
                array_start = i
                array_content = []
                bracket_depth = 1  # We just found opening [
                i += 1

                # Collect lines until we find MATCHING closing ]
                while i < len(lines) and bracket_depth > 0:
                    current_line = lines[i]

                    # Count brackets in this line to track depth
                    bracket_depth += current_line.count('[') - current_line.count(']')

                    if bracket_depth == 0:
                        # Found matching closing bracket
                        # Check if array contains only primitives
                        content_str = ' '.join(array_content)

                        if '{' not in content_str and '[' not in content_str:
                            # Extract primitive values
                            values = re.findall(r'(-?\d+\.?\d*|"[^"]*"|true|false|null)', content_str)

                            # Reconstruct as inline
                            key_line = lines[array_start].rstrip()
                            stripped = current_line.strip()
                            trailing_comma = ',' if stripped.endswith(',') else ''
                            inline = key_line + ', '.join(values) + ']' + trailing_comma

                            result.append(inline)
                            changed = True
                        else:
                            # Keep multi-line (contains objects or nested arrays)
                            result.append(lines[array_start])
                            result.extend([lines[j] for j in range(array_start + 1, i + 1)])

                        i += 1
                        break
                    else:
                        # Still inside array, collect content
                        array_content.append(current_line)
                        i += 1
            else:
                result.append(line)
                i += 1

        return '\n'.join(result), changed

    # Run multiple passes until no more changes (handles nested arrays)
    max_passes = 10
    for pass_num in range(max_passes):
        json_str, changed = compact_pass(json_str)
        if not changed:
            break

    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(json_str)
        f.write('\n')  # Add trailing newline
