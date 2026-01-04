#!/usr/bin/env python3
"""
Step 2: Extract frames from video for YOLO training dataset.

Usage:
    python3 2_extract_frames.py <video_file> [--interval 25]

Arguments:
    video_file: Path to MP4 video file
    --interval: Extract 1 frame every N frames (default: 10)

Example:
    python3 2_extract_frames.py data/videos/camera_video_20251229_183000.mp4 --interval 25

Output:
    Frames saved in: data/frames/img_0001.jpg, img_0002.jpg, etc.
"""

import sys
import cv2
from pathlib import Path
import argparse


def extract_frames(video_path, interval=10):
    """Extract frames from video at specified interval."""

    video_path = Path(video_path)
    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}")
        return

    # Create output directory in utils/data/frames/
    script_dir = Path(__file__).parent
    output_dir = script_dir / "data" / "frames"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clear existing frames before extracting new ones
    existing_frames = list(output_dir.glob("*.jpg"))
    if existing_frames:
        print(f"🗑️  Clearing {len(existing_frames)} existing frames from {output_dir}")
        for frame in existing_frames:
            frame.unlink()
        print()

    print(f"🎥 Opening video: {video_path.name}")
    print(f"📁 Output directory: {output_dir}")
    print(f"⏭️  Extracting 1 frame every {interval} frames")
    print()

    # Open video
    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print("❌ Failed to open video")
        return

    # Get video properties
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration_sec = total_frames / fps if fps > 0 else 0

    print(f"📊 Video info:")
    print(f"   Total frames: {total_frames}")
    print(f"   FPS: {fps:.1f}")
    print(f"   Duration: {duration_sec:.1f} seconds")
    print(f"   Expected output: ~{total_frames // interval} images")
    print()

    frame_count = 0
    saved_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Save frame at interval
        if frame_count % interval == 0:
            filename = f"img_{saved_count:04d}.jpg"
            filepath = output_dir / filename
            cv2.imwrite(str(filepath), frame)
            saved_count += 1

            # Progress indicator
            if saved_count % 10 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"📸 Extracted {saved_count} frames ({progress:.1f}%)")

        frame_count += 1

    cap.release()

    print()
    print(f"✅ Extraction complete!")
    print(f"   Saved {saved_count} frames to: {output_dir}")
    print(f"   Next step: Annotate with LabelImg")


def main():
    parser = argparse.ArgumentParser(
        description="Extract frames from video for YOLO training"
    )
    parser.add_argument(
        "video_file",
        help="Path to video file (MP4)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Extract 1 frame every N frames (default: 10)"
    )

    args = parser.parse_args()
    extract_frames(args.video_file, args.interval)


if __name__ == '__main__':
    main()
