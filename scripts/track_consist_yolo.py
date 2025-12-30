#!/usr/bin/env python3
"""
YOLO-based tracking for Consist 11 (E656 239 + E444 056).
Uses custom trained YOLOv8 model for real-time locomotive detection.

Usage:
    python track_consist_yolo.py <username> <password> [--model best.pt]

Controls:
    - Q: Quit
    - R: Reset distance history
    - D: Toggle debug view (show bounding boxes confidence)
    - SPACE: Pause/Resume
    - S: Save current frame as snapshot

Requirements:
    - Trained YOLOv8 model (best.pt) in same directory
    - Camera accessible at 192.168.1.4:554/stream2 (720P)
"""

import sys
import cv2
import numpy as np
from pathlib import Path
from collections import deque
import argparse

try:
    from ultralytics import YOLO
except ImportError:
    print("❌ Error: ultralytics not installed")
    print("Install with: pip3 install ultralytics")
    sys.exit(1)

# Camera settings
CAMERA_IP = "192.168.1.4"
CAMERA_PORT = 554
STREAM = "stream2"  # 720P stream (better for real-time)

# Detection settings
CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence for detection
DISTANCE_HISTORY_SIZE = 30  # Number of distance measurements to average

# Class IDs (from Roboflow training - BiancAlice v3)
# Roboflow orders alphabetically by class name
CLASS_NAMES = {
    0: "1_Gr675_017",   # Consist 10 lead
    1: "5_D645_014",    # Consist 10 rear
    2: "7_E656_239",    # Consist 11 lead
    3: "8_E444_056"     # Consist 11 rear
}

# Consist groupings
CONSIST_10 = [0, 1]  # Gr675 + D645
CONSIST_11 = [2, 3]  # E656 + E444


class YOLOTracker:
    """YOLO-based locomotive tracker."""

    def __init__(self, model_path: str):
        """Initialize tracker with YOLO model."""
        print(f"🤖 Loading YOLO model: {model_path}")
        self.model = YOLO(model_path)

        self.lead_pos = None
        self.rear_pos = None
        self.distance_history = deque(maxlen=DISTANCE_HISTORY_SIZE)

        print("✅ YOLO model loaded")

    def detect_locomotives(self, frame):
        """
        Detect all locomotives using YOLO.

        Returns:
            detections: dict {class_id: (pos, conf)}
            results: YOLO results object
        """
        # Run inference
        results = self.model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)

        detections = {}  # {class_id: (pos, conf)}

        # Parse detections
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Get box info
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                cls = int(box.cls[0])

                # Calculate center point
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)

                # Store detection (keep highest confidence if multiple)
                if cls not in detections or conf > detections[cls][1]:
                    detections[cls] = ((center_x, center_y), conf)

        return detections, results[0] if results else None

    def update(self, frame):
        """
        Update tracking with new frame.

        Returns:
            lead_pos, rear_pos, distance, lead_conf, rear_conf, lead_cls, rear_cls, results
        """
        lead_pos, rear_pos, lead_conf, rear_conf, lead_cls, rear_cls, results = self.detect_locomotives(frame)

        distance = None

        if lead_pos and rear_pos:
            # Calculate distance
            distance = np.sqrt(
                (lead_pos[0] - rear_pos[0]) ** 2 +
                (lead_pos[1] - rear_pos[1]) ** 2
            )

            self.lead_pos = lead_pos
            self.rear_pos = rear_pos
            self.distance_history.append(distance)

        return lead_pos, rear_pos, distance, lead_conf, rear_conf, lead_cls, rear_cls, results

    def get_average_distance(self):
        """Get average distance from history."""
        if len(self.distance_history) > 0:
            return np.mean(self.distance_history)
        return None


def draw_overlay(frame, tracker, lead, rear, distance, lead_conf, rear_conf,
                lead_cls, rear_cls, debug_view, results=None):
    """Draw tracking overlay on frame."""

    # Create semi-transparent overlay for text backgrounds
    overlay = frame.copy()

    # Draw markers and bounding boxes
    if lead and lead_cls is not None:
        cv2.circle(frame, lead, 10, (0, 255, 0), -1)
        class_name = CLASS_NAMES.get(lead_cls, f"Class_{lead_cls}")
        cv2.putText(frame, f"{class_name} ({lead_conf:.2f})", (lead[0] - 70, lead[1] - 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    if rear and rear_cls is not None:
        cv2.circle(frame, rear, 10, (255, 0, 0), -1)
        class_name = CLASS_NAMES.get(rear_cls, f"Class_{rear_cls}")
        cv2.putText(frame, f"{class_name} ({rear_conf:.2f})", (rear[0] - 70, rear[1] - 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    # Draw line between locomotives
    if lead and rear:
        cv2.line(frame, lead, rear, (255, 255, 0), 2)

    # Info panel with background
    info_text = "Consist 11 YOLO Tracking"
    cv2.rectangle(overlay, (5, 5), (350, 35), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.putText(frame, info_text, (10, 25),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Distance info
    if distance:
        overlay = frame.copy()
        cv2.rectangle(overlay, (5, 40), (250, 95), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

        cv2.putText(frame, f"Distance: {distance:.1f} px", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        avg_distance = tracker.get_average_distance()
        if avg_distance:
            cv2.putText(frame, f"Avg: {avg_distance:.1f} px", (10, 85),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Status
    overlay = frame.copy()
    status = "Tracking" if (lead and rear) else "Searching..."
    color = (0, 255, 0) if (lead and rear) else (0, 165, 255)
    cv2.rectangle(overlay, (5, 100), (200, 130), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.putText(frame, status, (10, 120),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # Controls
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 135), (450, 165), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.putText(frame, "Q=Quit | R=Reset | D=Debug | S=Save | SPACE=Pause", (10, 155),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # Debug view - draw all bounding boxes
    if debug_view and results:
        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            class_name = CLASS_NAMES.get(cls, f"Class_{cls}")

            # Draw bounding box
            color = (0, 255, 0) if cls == CLASS_E656_LEAD else (255, 0, 0)
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)

            # Draw label
            label = f"{class_name} {conf:.2f}"
            cv2.putText(frame, label, (int(x1), int(y1) - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)


def track_consist(username: str, password: str, model_path: str):
    """Main tracking loop."""
    rtsp_url = f"rtsp://{username}:{password}@{CAMERA_IP}:{CAMERA_PORT}/{STREAM}"

    print("🎥 Starting YOLO Tracking...")
    print()

    # Connect to camera
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("❌ Failed to connect to camera")
        return

    print("✅ Camera connected!")

    # Get resolution
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to read first frame")
        return

    actual_height, actual_width = frame.shape[:2]
    print(f"📐 Stream resolution: {actual_width}x{actual_height}")

    # Create window
    window_name = "YOLO Consist Tracking - Press Q to quit"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, actual_width, actual_height)

    # Initialize tracker
    tracker = YOLOTracker(model_path)

    # State
    paused = False
    debug_view = False
    frame_count = 0

    print("🚂 Tracking started! Locomotives will be detected automatically...")
    print()

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("❌ Lost connection")
                break

            frame_count += 1

            # Track
            lead, rear, distance, lead_conf, rear_conf, lead_cls, rear_cls, results = tracker.update(frame)

            # Draw overlay
            draw_overlay(frame, tracker, lead, rear, distance, lead_conf, rear_conf,
                        lead_cls, rear_cls, debug_view, results)

            # Display
            cv2.imshow(window_name, frame)

        # Handle keyboard
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q') or key == ord('Q'):
            print("\nQuitting...")
            break
        elif key == ord('r') or key == ord('R'):
            print("🔄 Reset distance history")
            tracker.distance_history.clear()
        elif key == ord('d') or key == ord('D'):
            debug_view = not debug_view
            print(f"🐛 Debug view: {'ON' if debug_view else 'OFF'}")
        elif key == ord('s') or key == ord('S'):
            # Save snapshot
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"tracking_snapshot_{timestamp}.jpg"
            script_dir = Path(__file__).parent
            filepath = script_dir / filename
            cv2.imwrite(str(filepath), frame)
            print(f"📸 Snapshot saved: {filepath}")
        elif key == ord(' '):
            paused = not paused
            print(f"{'⏸️  Paused' if paused else '▶️  Resumed'}")

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()

    # Summary
    avg = tracker.get_average_distance()
    if avg:
        print(f"\n📊 Tracking Summary:")
        print(f"   Average distance: {avg:.1f} pixels")
        print(f"   Measurements: {len(tracker.distance_history)}")
        print(f"   Frames processed: {frame_count}")


def main():
    parser = argparse.ArgumentParser(
        description="YOLO-based tracking for Consist 11"
    )
    parser.add_argument(
        "username",
        help="Camera username"
    )
    parser.add_argument(
        "password",
        help="Camera password"
    )
    parser.add_argument(
        "--model",
        default="models/best.pt",
        help="Path to trained YOLO model (default: models/best.pt)"
    )

    args = parser.parse_args()

    # Check model exists
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        print(f"   Please download best.pt from Google Colab")
        print(f"   and place it in: {Path(__file__).parent / 'models'}")
        return

    track_consist(args.username, args.password, str(model_path))


if __name__ == '__main__':
    main()
