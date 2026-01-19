#!/usr/bin/env python3
"""
Export standard (non-OBB) YOLO model to TensorRT engine format.

Usage:
    python scripts/utils/export_standard_tensorrt.py

This script exports best.pt (standard axis-aligned bboxes) to TensorRT.
For OBB model export, use export_tensorrt.py with yolo_obb: true in config.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ultralytics import YOLO


def main():
    """Export standard model to TensorRT."""
    model_path = project_root / "scripts" / "models" / "best.pt"

    if not model_path.exists():
        print(f"❌ Error: Model file not found: {model_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"🚀 Exporting STANDARD YOLO model to TensorRT")
    print(f"{'='*60}")
    print(f"📁 Model: {model_path.name}")
    print(f"🎯 Half precision: True (FP16)")
    print(f"\n⏳ This may take 2-5 minutes...\n")

    # Load model
    model = YOLO(str(model_path))

    # Export to TensorRT
    engine_path = model.export(
        format='engine',
        device=0,
        half=True,
        verbose=True
    )

    print(f"\n{'='*60}")
    print(f"✅ Export completed successfully!")
    print(f"{'='*60}")
    print(f"📁 Engine file: {engine_path}")

    pt_size = model_path.stat().st_size / (1024 * 1024)
    engine_size = Path(engine_path).stat().st_size / (1024 * 1024)
    print(f"📊 File sizes:")
    print(f"   .pt model:  {pt_size:.1f} MB")
    print(f"   .engine:    {engine_size:.1f} MB")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
