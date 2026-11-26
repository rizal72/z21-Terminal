"""
Centralized configuration loader for z21-Terminal

The configuration document lives in the database (one row), shared by every host.
config.local.json is merged on top of it: credentials and debug mode, which are per
machine and never enter the shared database. config.seed.json is only the seed, read when
the database has no document yet.
"""

import copy
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from log_colors import log

# The merged document (stored config + local overrides), built once the database
# answers and replaced on every save. load_config() runs in hot paths, some per
# frame, so a query per call is not an option. `_database_failed` keeps a broken
# database from costing a timeout on every call: one attempt per failure.
_cache: Optional[Dict[str, Any]] = None
_database_failed = False

# Bumped whenever the merged view changes. Readers that keep a copy (the video feed
# draws gate overlays) compare this instead of re-reading the document every frame.
_version = 0


def config_version() -> int:
    return _version


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


def _config_path(config_path: Optional[Path] = None) -> Path:
    if config_path is not None:
        return config_path
    # Assume config_loader.py is in backend/ folder
    return Path(__file__).parent.parent / "config.seed.json"


def _read_json(path: Path) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _file_document(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """config.seed.json, the seed. Required: a missing seed is an error, never a silent default."""
    path = _config_path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            f"Expected location: project_root/config.seed.json"
        )
    return _read_json(path)


def _local_document(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """config.local.json, machine-specific, optional."""
    path = _config_path(config_path).parent / "config.local.json"
    if not path.exists():
        return {}
    try:
        return _read_json(path)
    except json.JSONDecodeError as e:
        log('[WARN]', f"Warning: Invalid JSON in {path.name}, ignoring: {e}")
        return {}


def _shared(config: Dict[str, Any]) -> Dict[str, Any]:
    """What may be stored in the shared database: no machine secrets, no comment keys."""
    filtered = copy.deepcopy(config)
    filtered = {k: v for k, v in filtered.items() if not k.startswith('_')}

    # Camera credentials and debug mode belong to config.local.json only.
    camera = filtered.get('camera')
    if isinstance(camera, dict):
        camera.pop('username', None)
        camera.pop('password', None)
    debug = filtered.get('debug')
    if isinstance(debug, dict) and 'enabled' in debug:
        debug['enabled'] = False

    return filtered


def _stored() -> Tuple[bool, Optional[Dict[str, Any]]]:
    """(reachable, document). An unreachable database is not an empty one."""
    try:
        from services import db
        with db.connection() as conn:
            row = conn.execute("SELECT document FROM config WHERE id = 1").fetchone()
    except Exception as e:
        # Before init_schema() the table does not exist yet: expected, not a fault.
        if "does not exist" in str(e):
            return False, None
        log('[WARN]', f"Configuration in the database unavailable, using config.seed.json: {e}")
        return False, None
    return True, (row[0] if row else None)


def _write_stored(document: Dict[str, Any]) -> None:
    """Replace the stored document. Raises when the database is unreachable."""
    from psycopg.types.json import Jsonb
    from services import db
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO config (id, document, updated_at) "
            "VALUES (1, %s, extract(epoch from now())) "
            "ON CONFLICT (id) DO UPDATE "
            "SET document = EXCLUDED.document, updated_at = EXCLUDED.updated_at",
            (Jsonb(document),),
        )


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load the merged configuration.

    Priority (highest to lowest):
    1. config.local.json (per machine: credentials, debug mode)
    2. the document stored in the database
    3. config.seed.json, only before warm_config_cache() has run (import time) or when
       the database is unreachable

    The result is a copy: callers mutate what they get and hand it back to
    save_config(), so handing out the cache itself would corrupt it on a failed save.

    Args:
        config_path: Path to config.seed.json, for tests and one-off scripts (defaults to
            the project root)

    Returns:
        Merged configuration dict
    """
    if config_path is not None:
        return deep_merge(_file_document(config_path), _local_document(config_path))
    if _cache is None and not _database_failed:
        _warm()
    if _cache is not None:
        return copy.deepcopy(_cache)
    # The database is unreachable or the schema does not exist yet: video_feed and
    # tracking_daemon read the configuration at import time, before init_schema().
    return deep_merge(_file_document(), _local_document())


def _warm() -> bool:
    """Seed an empty database from config.seed.json, then cache the merged document."""
    global _cache, _database_failed

    reachable, document = _stored()
    if not reachable:
        _database_failed = True
        return False

    if document is None:
        seed = _shared(_file_document())
        try:
            _write_stored(seed)
            log('[INIT]', "Config seeded in the database from config.seed.json")
            document = seed
        except Exception as e:
            log('[ERROR]', f"Config could not be seeded in the database: {e}")
            _database_failed = True
            return False

    _cache = deep_merge(document, _local_document())
    _database_failed = False
    global _version
    _version += 1
    return True


def warm_config_cache() -> Dict[str, Any]:
    """Read the stored document into the cache. Called once, after init_schema()."""
    _warm()
    return load_config()


def reload_config() -> Dict[str, Any]:
    """Re-read the stored document: for a write made by a script, outside this process."""
    global _database_failed
    _database_failed = False
    return warm_config_cache()


def stored_document() -> Optional[Dict[str, Any]]:
    """The document in the database, or None when there is none. Raises when unreachable."""
    reachable, document = _stored()
    if not reachable:
        raise RuntimeError("Database unreachable")
    return document


def replace_stored(document: Dict[str, Any]) -> None:
    """Replace the stored document and the cache. Used by the seed command."""
    global _cache, _version
    filtered = _shared(document)
    _write_stored(filtered)
    _cache = deep_merge(filtered, _local_document())
    _version += 1


def get_config_path() -> Path:
    """
    Get the path to config.seed.json in project root.

    Returns:
        Path to config.seed.json
    """
    return _config_path()


def save_config(config: Dict[str, Any], config_path: Optional[Path] = None) -> None:
    """
    Save the configuration to the database, and refresh the cache.

    Camera credentials and debug mode are stripped: they belong to config.local.json.
    config.seed.json is not written at runtime; it is the seed for an empty database.

    Args:
        config: Configuration dict to save (the merged one returned by load_config)
        config_path: Write to this file instead of the database, for tests and
            one-off scripts

    Raises:
        RuntimeError: If the database is unreachable (the caller must report it, not
            pretend the save succeeded)
    """
    filtered = _shared(config)

    if config_path is not None:
        json_str = json.dumps(filtered, indent=2, ensure_ascii=False)
        with open(config_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json_str)
            f.write('\n')  # Add trailing newline (POSIX standard)
        return

    _write_stored(filtered)

    global _cache, _version
    _cache = deep_merge(filtered, _local_document())
    _version += 1


def save_local_config(local_overrides: Dict[str, Any]) -> None:
    """
    Save local-only settings to config.local.json (gitignored).

    Used for machine-specific overrides (camera credentials, debug mode, etc)

    Args:
        local_overrides: Dict with local overrides (e.g., {"debug": {"enabled": true}})

    Raises:
        IOError: If unable to write config.local.json
    """
    local_config_path = _config_path().parent / "config.local.json"

    merged_local = deep_merge(_local_document(), local_overrides)

    json_str = json.dumps(merged_local, indent=2, ensure_ascii=False)
    with open(local_config_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json_str)
        f.write('\n')  # Add trailing newline

    # The merged view must not keep the previous local values: the router saves the
    # shared document first, and the local file afterwards.
    global _cache, _version
    if _cache is not None:
        _cache = deep_merge(_cache, local_overrides)
        _version += 1
