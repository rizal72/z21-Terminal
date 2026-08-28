#!/usr/bin/env python3
"""
Bump z21-Terminal version (PURE - no git operations).

Updates the single source of truth (backend/version.py) and the doc version
references (AGENTS.md, CLAUDE.md). Git commit/push/merge/tag must be done manually.

Usage:
    python scripts/release/bump_version.py 1.0.0
"""
import re
import sys
from pathlib import Path

# Paths (relative to project root)
ROOT = Path(__file__).parent.parent.parent
VERSION_PY = ROOT / "backend" / "version.py"
AGENTS_MD = ROOT / "AGENTS.md"
CLAUDE_MD = ROOT / "CLAUDE.md"


def validate_version(new_version: str) -> bool:
    """Validate semantic version format X.Y.Z (allow optional pre-release like 1.0.0-rc1)."""
    return bool(re.match(r"^\d+\.\d+\.\d+([.-][0-9A-Za-z.-]+)?$", new_version))


def update_version_py(new_version: str) -> None:
    """Update __version__ in backend/version.py."""
    content = VERSION_PY.read_text(encoding="utf-8")
    new_content = re.sub(
        r'__version__ = "[^"]+"',
        f'__version__ = "{new_version}"',
        content,
        count=1,
    )
    VERSION_PY.write_text(new_content, encoding="utf-8")
    print(f"[OK] backend/version.py -> {new_version}")


def update_md_doc(path: Path, new_version: str) -> None:
    """Update the **Version** line in a Markdown doc (AGENTS.md / CLAUDE.md).

    Handles lines like:
      **Version**: v0.9.11 (Development - v1.0.0 Coming Soon)
    -> **Version**: v1.0.0
    """
    if not path.exists():
        print(f"[SKIP] {path.name} not found")
        return
    content = path.read_text(encoding="utf-8")
    new_content = re.sub(
        r"\*\*Version\*\*:\s*v?[0-9][^\n]*",
        f"**Version**: v{new_version}",
        content,
        count=1,
    )
    if new_content == content:
        print(f"[WARN] No **Version** line found in {path.name}")
        return
    path.write_text(new_content, encoding="utf-8")
    print(f"[OK] {path.name} -> v{new_version}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/release/bump_version.py <new_version>")
        sys.exit(1)

    new_version = sys.argv[1]

    if not validate_version(new_version):
        print(f"[ERROR] Invalid version format: {new_version} (expected X.Y.Z)")
        sys.exit(1)

    print(f"Bumping z21-Terminal to v{new_version}")
    print("-" * 40)

    if not VERSION_PY.exists():
        print(f"[ERROR] {VERSION_PY} not found - run once from repo root")
        sys.exit(1)

    update_version_py(new_version)
    update_md_doc(AGENTS_MD, new_version)
    update_md_doc(CLAUDE_MD, new_version)

    print("-" * 40)
    print("Version files updated. NO git operations performed (by design).")
    print("Next (manual): commit, push, create git tag v{0}, merge to main.".format(new_version))


if __name__ == "__main__":
    main()