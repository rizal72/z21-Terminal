#!/usr/bin/env python3
"""
Export YOLO model to TensorRT engine format for faster inference on NVIDIA GPUs.

Usage:
    python scripts/utils/export_tensorrt.py

This script:
1. Loads the current YOLO model (best.pt or best_obb.pt based on config)
2. Exports to TensorRT .engine format (optimized for current GPU)
3. Saves engine file alongside .pt model
4. Reports expected FPS improvement

Requirements:
- NVIDIA GPU with CUDA support
- ultralytics package with TensorRT export support
- CUDA Toolkit installed (usually bundled with PyTorch)

Note:
- Engine file is GPU-specific (re-export if you change GPU)
- First run may take 2-5 minutes (model optimization)
- Subsequent loads are instant
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ultralytics import YOLO


def load_config():
    """Load config.json to determine which model to export."""
    config_path = project_root / "config.json"
    with open(config_path, encoding='utf-8') as f:
        return json.load(f)


def export_to_tensorrt(model_path: Path, half: bool = True):
    """
    Export YOLO model to TensorRT engine format.

    Args:
        model_path: Path to .pt model file
        half: Use FP16 half-precision (default: True for 2x speed)

    Returns:
        Path to exported .engine file
    """
    print(f"\n{'='*60}")
    print(f"🚀 Exporting YOLO model to TensorRT engine")
    print(f"{'='*60}")
    print(f"📁 Model: {model_path.name}")
    print(f"🎯 Half precision: {half} (FP16)")
    print(f"\n⏳ This may take 2-5 minutes (first time only)...")
    print(f"   TensorRT is optimizing the model for your GPU\n")

    # Load model
    model = YOLO(str(model_path))

    # Export to TensorRT
    # device=0 = use GPU 0
    # half=True = FP16 precision (2x faster, same accuracy)
    # verbose=True = show export progress
    engine_path = model.export(
        format='engine',
        device=0,
        half=half,
        verbose=True
    )

    print(f"\n{'='*60}")
    print(f"✅ Export completed successfully!")
    print(f"{'='*60}")
    print(f"📁 Engine file: {engine_path}")
    print(f"📊 File size comparison:")

    pt_size = model_path.stat().st_size / (1024 * 1024)
    engine_size = Path(engine_path).stat().st_size / (1024 * 1024)
    print(f"   .pt model:  {pt_size:.1f} MB")
    print(f"   .engine:    {engine_size:.1f} MB")

    print(f"\n🎯 Expected performance improvement:")
    print(f"   - Inference speed: 2-5x faster")
    print(f"   - Bbox lag: 2-3s → <0.5s")
    print(f"   - Frame skip: eliminated")

    print(f"\n💡 Next steps:")
    print(f"   1. Backend will auto-detect .engine file")
    print(f"   2. Restart backend: z21-restart")
    print(f"   3. Check logs for 'Using TensorRT engine' message")
    print(f"   4. Test bbox sync with locomotives")
    print(f"{'='*60}\n")

    return engine_path


def main():
    """Main export workflow."""
    # Load config to determine which model to export
    config = load_config()
    yolo_obb = config.get('tracking', {}).get('yolo_obb', False)

    # Determine model path
    if yolo_obb:
        model_filename = "best_obb.pt"
        print(f"📌 Config: yolo_obb = true")
        print(f"   Exporting OBB (Oriented Bounding Boxes) model")
    else:
        model_filename = "best.pt"
        print(f"📌 Config: yolo_obb = false")
        print(f"   Exporting standard axis-aligned model")

    model_path = project_root / "scripts" / "models" / model_filename

    if not model_path.exists():
        print(f"❌ Error: Model file not found: {model_path}")
        print(f"   Make sure {model_filename} exists in scripts/models/")
        sys.exit(1)

    # Export to TensorRT
    try:
        engine_path = export_to_tensorrt(model_path, half=True)
        print(f"✅ Success! TensorRT engine ready to use.")
        return 0
    except Exception as e:
        print(f"\n❌ Export failed with error:")
        print(f"   {type(e).__name__}: {e}")
        print(f"\n💡 Troubleshooting:")
        print(f"   - Make sure NVIDIA GPU drivers are up to date")
        print(f"   - Check CUDA Toolkit is installed")
        print(f"   - Verify PyTorch CUDA support: python -c \"import torch; print(torch.cuda.is_available())\"")
        return 1


if __name__ == "__main__":
    sys.exit(main())
