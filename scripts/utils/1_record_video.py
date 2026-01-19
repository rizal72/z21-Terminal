#!/usr/bin/env python3
"""
Step 1: Record video from camera for YOLO training dataset.

Usage:
    python3 1_record_video.py

    Camera credentials loaded from config.json + config.local.json
    (see README_CAMERA.md for setup)

Controls:
    - Q: Quit
    - R: Start/Stop video recording
    - S: Save current frame as snapshot
    - SPACE: Pause/Resume

Output:
    Video saved in: data/videos/camera_video_YYYYMMDD_HHMMSS.mp4
"""

import sys
import cv2
import time
from pathlib import Path

# Camera settings
CAMERA_IP = "192.168.1.4"
CAMERA_PORT = 554
STREAM = "stream1"  # 2K/1080P stream (maximum resolution)


def view_camera():
    """View live camera feed."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))  # Add scripts/ to path
    from camera_utils import load_camera_config

    # Load camera config
    rtsp_url, camera_ip, camera_port, stream = load_camera_config()

    print("🎥 Opening camera feed...")
    print("Controls:")
    print("  Q - Quit")
    print("  R - Start/Stop recording")
    print("  S - Save snapshot")
    print("  SPACE - Pause/Resume")
    print()

    # Connect to camera
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        print("❌ Failed to connect to camera")
        return

    print("✅ Camera connected!")

    # Get actual resolution
    ret, test_frame = cap.read()
    if not ret:
        print("❌ Failed to read first frame")
        return

    actual_height, actual_width = test_frame.shape[:2]
    print(f"📐 Stream resolution: {actual_width}x{actual_height}")
    print("Opening window...")
    print()

    # Create window
    window_name = "z21 Camera Feed - Press Q to quit"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, actual_width, actual_height)

    paused = False
    recording = False
    video_writer = None
    frame_count = 0
    last_frame = test_frame.copy()

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("❌ Lost connection to camera")
                break

            last_frame = frame.copy()
            frame_count += 1

            # Write frame to video if recording
            if recording and video_writer is not None:
                video_writer.write(frame)

            # Create semi-transparent overlay for text backgrounds
            overlay = frame.copy()

            # Add info overlay with background
            info_text = f"Frame: {frame_count} | FPS: 15 | Resolution: {actual_width}x{actual_height}"
            cv2.rectangle(overlay, (5, 5), (750, 45), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
            cv2.putText(frame, info_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Add controls hint with background
            overlay = frame.copy()
            controls_text = "Q=Quit | R=Record | S=Save | SPACE=Pause"
            cv2.rectangle(overlay, (5, 45), (500, 75), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
            cv2.putText(frame, controls_text, (10, 65),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Recording indicator with background (below controls)
            if recording:
                overlay = frame.copy()
                rec_text = "● REC"
                cv2.rectangle(overlay, (5, 80), (120, 110), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
                cv2.putText(frame, rec_text, (10, 100),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            if paused:
                pause_text = "PAUSED"
                cv2.putText(frame, pause_text, (actual_width // 2 - 150, actual_height // 2),
                           cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)

        else:
            frame = last_frame.copy()
            pause_text = "PAUSED - Press SPACE to resume"
            cv2.putText(frame, pause_text, (actual_width // 2 - 350, actual_height // 2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Display frame
        cv2.imshow(window_name, frame)

        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q') or key == ord('Q'):
            print("\nQuitting...")
            break
        elif key == ord('r') or key == ord('R'):
            # Toggle recording
            recording = not recording
            if recording:
                # Start recording
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"camera_video_{timestamp}.mp4"
                script_dir = Path(__file__).parent
                videos_dir = script_dir / "data" / "videos"
                videos_dir.mkdir(parents=True, exist_ok=True)
                filepath = videos_dir / filename

                # Setup video writer (H.264 codec)
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                fps = 15  # Match camera FPS
                video_writer = cv2.VideoWriter(
                    str(filepath),
                    fourcc,
                    fps,
                    (actual_width, actual_height)
                )
                print(f"🔴 Recording started: {filepath}")
            else:
                # Stop recording
                if video_writer is not None:
                    video_writer.release()
                    video_writer = None
                print("⏹️  Recording stopped")
        elif key == ord('s') or key == ord('S'):
            # Save snapshot in data/ directory
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"camera_snapshot_{timestamp}.jpg"
            script_dir = Path(__file__).parent
            data_dir = script_dir / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            filepath = data_dir / filename
            cv2.imwrite(str(filepath), last_frame)
            print(f"📸 Snapshot saved: {filepath}")
        elif key == ord(' '):
            # Toggle pause
            paused = not paused
            print(f"{'⏸️  Paused' if paused else '▶️  Resumed'}")

    # Cleanup
    if video_writer is not None:
        video_writer.release()
        print("💾 Video file saved and closed")
    cap.release()
    cv2.destroyAllWindows()
    print("Camera closed.")


def main():
    view_camera()


if __name__ == '__main__':
    main()
