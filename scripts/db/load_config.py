#!/usr/bin/env python3
"""Load config.seed.json into the database.

The database is the truth; config.seed.json is the seed for an empty one. This command is
how a hand edit of the file gets in. It refuses when a document is already stored,
unless --force, so an old file cannot silently wipe months of edits made in the UI.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from config_loader import get_config_path, load_config, replace_stored, stored_document


def main() -> int:
    force = "--force" in sys.argv[1:]

    try:
        current = stored_document()
    except Exception as e:
        print(f"Database unreachable: {e}")
        return 1

    if current is not None and not force:
        print("The database already holds a configuration, and that one is the truth.")
        print("Re-run with --force to replace it with config.seed.json.")
        return 2

    # The path forces a read of the file: load_config() alone would return the
    # stored row, and the command would write it back over itself.
    replace_stored(load_config(get_config_path()))
    print("Configuration loaded into the database from config.seed.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
