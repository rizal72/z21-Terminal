#!/usr/bin/env python3
"""
Import locomotive pictures from the JMRI roster into web/public/loco_images.

The web UI shows each locomotive by its DCC address, so the files are named
<address>.jpg. The source is JMRI's `iconFilePath` (the side view DecoderPro
shows in its Icon column). Run on the Mac, where JMRI lives; the result is
committed, so the PC never needs JMRI.

Usage:
    venv/bin/python scripts/utils/import_loco_images.py            # all in config.json
    venv/bin/python scripts/utils/import_loco_images.py --address 2
    venv/bin/python scripts/utils/import_loco_images.py --dry-run
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).parent.parent.parent
ROSTER_PATH = Path.home() / "Library/Preferences/JMRI/La_mia_Ferrovia_in_JMRI.jmri/roster"
OUTPUT_DIR = PROJECT_ROOT / "web" / "public" / "loco_images"
WIDTH = 480
QUALITY = 85


def roster_images() -> dict:
    """DCC address -> picture file, from the icon attribute of each roster XML."""
    images = {}
    for xml in sorted(ROSTER_PATH.glob("*.xml")):
        try:
            loco = ET.parse(xml).getroot().find("locomotive")
        except ET.ParseError:
            continue
        if loco is None:
            continue
        address = loco.get("dccAddress")
        if not address or not address.isdigit():
            continue
        name = loco.get("iconFilePath") or loco.get("imageFilePath") or ""
        path = ROSTER_PATH / name.replace("preference:roster/", "")
        if path.is_file():
            images[int(address)] = path
    return images


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", type=int, help="import only this DCC address")
    parser.add_argument("--dry-run", action="store_true", help="show what would be written")
    args = parser.parse_args()

    config = json.loads((PROJECT_ROOT / "config.json").read_text())
    addresses = {int(a) for a in config.get("locomotives", {})}
    if args.address is not None:
        addresses &= {args.address}

    images = roster_images()
    missing = sorted(addresses - set(images))
    if missing:
        print(f"[WARN] no picture in the roster for: {missing}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for address in sorted(addresses & set(images)):
        source = images[address]
        target = OUTPUT_DIR / f"{address}.jpg"
        if args.dry_run:
            print(f"[DRY] {address}: {source.name} -> {target.relative_to(PROJECT_ROOT)}")
            continue
        with Image.open(source) as image:
            picture = image.convert("RGB")
            if picture.width > WIDTH:
                height = round(picture.height * WIDTH / picture.width)
                picture = picture.resize((WIDTH, height), Image.LANCZOS)
            picture.save(target, "JPEG", quality=QUALITY, optimize=True)
        print(f"[OK]  {address}: {source.name} -> {target.name} ({target.stat().st_size // 1024} KB)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
