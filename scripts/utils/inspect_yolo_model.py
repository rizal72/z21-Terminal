#!/usr/bin/env python3
"""
Inspect YOLO model to see class names and order.
Shows exactly what YOLO learned during training.

Usage:
    python3 inspect_yolo_model.py [model_path]
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ultralytics import YOLO


def inspect_model(model_path):
    """Load and inspect YOLO model."""
    model_path = Path(model_path)

    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        return

    print(f"🔍 Inspecting YOLO model: {model_path.name}")
    print()

    # Load model
    model = YOLO(str(model_path))

    # Get class names
    class_names = model.names

    print("📋 Class Mapping (from data.yaml during training):")
    print()
    for class_id, class_name in class_names.items():
        print(f"   Class {class_id}: {class_name}")

    print()
    print("✅ This is the order YOLO uses for predictions")


def main():
    if len(sys.argv) > 1:
        model_path = sys.argv[1]
    else:
        # Default to models/best.pt
        model_path = Path(__file__).parent.parent / "models" / "best.pt"

    inspect_model(model_path)


if __name__ == '__main__':
    main()
