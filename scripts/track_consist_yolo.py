#!/usr/bin/env python3
"""
YOLO-based tracking for BOTH consists:
    - Consist 10 (Tracciato Interno): Gr.675 017 + D645 014
    - Consist 11 (Tracciato Esterno): E656 239 + E444 056

Uses custom trained YOLOv8 model for real-time locomotive detection.

Perspective Correction:
    - Display: original camera view (oblique perspective)
    - Distance calculations: perspective-corrected frame (6px/cm uniform scale)
    - Coordinates transformed in background for accurate measurements

Usage:
    python track_consist_yolo.py <username> <password> [--model best.pt]

Controls:
    - Q: Quit
    - R: Reset distance history (both consists)
    - D: Toggle debug view (show bounding boxes with confidence)
    - P: Toggle ALL panels (clean video, markers only, calculation continues)
    - S: Save current frame as snapshot
    - SPACE: Pause/Resume

Requirements:
    - Trained YOLOv8 model (best.pt) with all 4 locomotive classes
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
DISTANCE_HISTORY_SIZE = 10000  # Number of distance measurements to store (large for baseline testing)

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

# Perspective correction settings (calibrated 2025-12-30)
# Used ONLY for accurate distance calculations (6px/cm uniform scale)
# Detection and display remain on original camera frame
SRC_POINTS = np.float32([
    [7, 246],      # Top-left
    [376, 31],     # Top-right
    [957, 37],     # Bottom-right
    [257, 718]     # Bottom-left
])

DST_WIDTH = 600
DST_HEIGHT = 1200
Y_OFFSET = 50
LAYOUT_HEIGHT = 950

DST_POINTS = np.float32([
    [0, Y_OFFSET],
    [DST_WIDTH, Y_OFFSET],
    [DST_WIDTH, Y_OFFSET + LAYOUT_HEIGHT],
    [0, Y_OFFSET + LAYOUT_HEIGHT]
])

# Pre-compute perspective transform matrix (for distance calculations)
PERSPECTIVE_MATRIX = cv2.getPerspectiveTransform(
    np.float32([
        SRC_POINTS[0],
        SRC_POINTS[1],
        [SRC_POINTS[2][0] + (SRC_POINTS[2][0] - SRC_POINTS[1][0]) * 0.05,
         SRC_POINTS[2][1] + (720 - SRC_POINTS[2][1]) * 0.3],
        [SRC_POINTS[3][0] - (SRC_POINTS[0][0] - SRC_POINTS[3][0]) * 0.05,
         SRC_POINTS[3][1] + (720 - SRC_POINTS[3][1]) * 0.3]
    ]),
    DST_POINTS
)

# Scale: 6 px/cm on corrected frame
PX_PER_CM = 6.0


def transform_to_corrected(point):
    """
    Transform point from original frame to perspective-corrected frame.
    Used for accurate distance calculations.

    Args:
        point: (x, y) tuple in original frame coordinates

    Returns:
        (x, y) tuple in corrected frame coordinates
    """
    pts = np.array([[point]], dtype=np.float32)
    transformed = cv2.perspectiveTransform(pts, PERSPECTIVE_MATRIX)
    return (transformed[0][0][0], transformed[0][0][1])


class YOLOTracker:
    """YOLO-based locomotive tracker."""

    def __init__(self, model_path: str):
        """Initialize tracker with YOLO model."""
        print(f"🤖 Loading YOLO model: {model_path}")
        self.model = YOLO(model_path)

        # Consist 10 (Tracciato Interno)
        self.c10_lead_pos = None
        self.c10_rear_pos = None
        self.c10_distance_history = deque(maxlen=DISTANCE_HISTORY_SIZE)
        self.c10_min_distance = float('inf')
        self.c10_max_distance = 0.0

        # Consist 11 (Tracciato Esterno)
        self.c11_lead_pos = None
        self.c11_rear_pos = None
        self.c11_distance_history = deque(maxlen=DISTANCE_HISTORY_SIZE)
        self.c11_min_distance = float('inf')
        self.c11_max_distance = 0.0

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
        Update tracking with new frame for BOTH consists.

        Returns:
            Dictionary with consist data and shared detection info
        """
        detections, results = self.detect_locomotives(frame)

        # === CONSIST 10 (Tracciato Interno) ===
        c10_lead_data = detections.get(0)  # Gr675_017 (class 0)
        c10_rear_data = detections.get(1)  # D645_014 (class 1)

        c10_lead_pos = c10_lead_data[0] if c10_lead_data else None
        c10_lead_conf = c10_lead_data[1] if c10_lead_data else 0.0

        c10_rear_pos = c10_rear_data[0] if c10_rear_data else None
        c10_rear_conf = c10_rear_data[1] if c10_rear_data else 0.0

        c10_distance = None
        if c10_lead_pos and c10_rear_pos:
            lead_corrected = transform_to_corrected(c10_lead_pos)
            rear_corrected = transform_to_corrected(c10_rear_pos)
            c10_distance = np.sqrt(
                (lead_corrected[0] - rear_corrected[0]) ** 2 +
                (lead_corrected[1] - rear_corrected[1]) ** 2
            )
            self.c10_lead_pos = c10_lead_pos
            self.c10_rear_pos = c10_rear_pos
            self.c10_distance_history.append(c10_distance)
            if c10_distance < self.c10_min_distance:
                self.c10_min_distance = c10_distance
            if c10_distance > self.c10_max_distance:
                self.c10_max_distance = c10_distance

        # === CONSIST 11 (Tracciato Esterno) ===
        c11_lead_data = detections.get(2)  # E656_239 (class 2)
        c11_rear_data = detections.get(3)  # E444_056 (class 3)

        c11_lead_pos = c11_lead_data[0] if c11_lead_data else None
        c11_lead_conf = c11_lead_data[1] if c11_lead_data else 0.0

        c11_rear_pos = c11_rear_data[0] if c11_rear_data else None
        c11_rear_conf = c11_rear_data[1] if c11_rear_data else 0.0

        c11_distance = None
        if c11_lead_pos and c11_rear_pos:
            lead_corrected = transform_to_corrected(c11_lead_pos)
            rear_corrected = transform_to_corrected(c11_rear_pos)
            c11_distance = np.sqrt(
                (lead_corrected[0] - rear_corrected[0]) ** 2 +
                (lead_corrected[1] - rear_corrected[1]) ** 2
            )
            self.c11_lead_pos = c11_lead_pos
            self.c11_rear_pos = c11_rear_pos
            self.c11_distance_history.append(c11_distance)
            if c11_distance < self.c11_min_distance:
                self.c11_min_distance = c11_distance
            if c11_distance > self.c11_max_distance:
                self.c11_max_distance = c11_distance

        return {
            'c10': {'lead_pos': c10_lead_pos, 'rear_pos': c10_rear_pos, 'distance': c10_distance,
                    'lead_conf': c10_lead_conf, 'rear_conf': c10_rear_conf},
            'c11': {'lead_pos': c11_lead_pos, 'rear_pos': c11_rear_pos, 'distance': c11_distance,
                    'lead_conf': c11_lead_conf, 'rear_conf': c11_rear_conf},
            'detections': detections,
            'results': results
        }

    def get_average_distance(self, consist='c11'):
        """Get average distance from history for specified consist."""
        history = self.c11_distance_history if consist == 'c11' else self.c10_distance_history
        if len(history) > 0:
            return np.mean(history)
        return None


def draw_overlay(frame, tracker, track_data, debug_view, show_panels=True):
    """Draw tracking overlay on frame for BOTH consists."""

    c10 = track_data['c10']
    c11 = track_data['c11']
    all_detections = track_data['detections']
    results = track_data['results']

    # Draw markers for BOTH consists (always visible - just colored dots)
    # Consist 10 (yellow/orange)
    if c10['lead_pos']:
        cv2.circle(frame, c10['lead_pos'], 10, (255, 255, 0), -1)  # Yellow

    if c10['rear_pos']:
        cv2.circle(frame, c10['rear_pos'], 10, (255, 128, 0), -1)  # Orange

    if c10['lead_pos'] and c10['rear_pos']:
        cv2.line(frame, c10['lead_pos'], c10['rear_pos'], (255, 200, 0), 2)

    # Consist 11 (green/red)
    if c11['lead_pos']:
        cv2.circle(frame, c11['lead_pos'], 10, (0, 255, 0), -1)  # Green

    if c11['rear_pos']:
        cv2.circle(frame, c11['rear_pos'], 10, (255, 0, 0), -1)  # Red

    if c11['lead_pos'] and c11['rear_pos']:
        cv2.line(frame, c11['lead_pos'], c11['rear_pos'], (255, 255, 0), 2)

    # Early return if panels hidden (P key pressed) - calculation continues in background
    if not show_panels:
        return

    # All panels below (can be toggled with P key)
    # Info panel with background
    overlay = frame.copy()
    info_text = "Dual Consist YOLO Tracking"
    cv2.rectangle(overlay, (5, 5), (400, 35), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.putText(frame, info_text, (10, 25),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # Distance info - ALWAYS VISIBLE (corrected frame values: 6px/cm uniform scale)
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 40), (650, 120), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    # Consist 10 distance (left side)
    c10_dist = c10['distance']
    if c10_dist:
        c10_cm = c10_dist / PX_PER_CM
        cv2.putText(frame, f"C10: {c10_dist:.1f}px ({c10_cm:.1f}cm)", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 0), 2)
    else:
        if len(tracker.c10_distance_history) > 0:
            last = tracker.c10_distance_history[-1]
            cv2.putText(frame, f"C10: {last:.1f}px LAST", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (128, 128, 0), 2)
        else:
            cv2.putText(frame, "C10: --", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (128, 128, 128), 2)

    # Consist 11 distance (right side)
    c11_dist = c11['distance']
    if c11_dist:
        c11_cm = c11_dist / PX_PER_CM
        cv2.putText(frame, f"C11: {c11_dist:.1f}px ({c11_cm:.1f}cm)", (330, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)
    else:
        if len(tracker.c11_distance_history) > 0:
            last = tracker.c11_distance_history[-1]
            cv2.putText(frame, f"C11: {last:.1f}px LAST", (330, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 128, 0), 2)
        else:
            cv2.putText(frame, "C11: --", (330, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (128, 128, 128), 2)

    # Average distances (bottom row)
    avg_c10 = tracker.get_average_distance('c10')
    avg_c11 = tracker.get_average_distance('c11')

    if avg_c10:
        cv2.putText(frame, f"Avg C10: {avg_c10:.1f}px ({len(tracker.c10_distance_history)} s)",
                   (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 200, 0), 1)
    else:
        cv2.putText(frame, "Avg C10: -- (0 s)", (10, 85),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 0), 1)

    if avg_c11:
        cv2.putText(frame, f"Avg C11: {avg_c11:.1f}px ({len(tracker.c11_distance_history)} s)",
                   (330, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    else:
        cv2.putText(frame, "Avg C11: -- (0 s)", (330, 85),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 128, 0), 1)

    # Status line
    c10_tracking = c10['lead_pos'] and c10['rear_pos']
    c11_tracking = c11['lead_pos'] and c11['rear_pos']
    status_c10 = "✓" if c10_tracking else "✗"
    status_c11 = "✓" if c11_tracking else "✗"
    cv2.putText(frame, f"Tracking: C10 {status_c10}  C11 {status_c11}", (10, 110),
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    # Controls
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 125), (550, 155), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.putText(frame, "Q=Quit | R=Reset | D=Debug | P=Panel | S=Save | SPACE=Pause", (10, 145),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # All Locomotives Detected Panel
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 160), (450, 280), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.putText(frame, "All Locomotives Detected:", (10, 180),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # Show detection status for all 4 classes
    y_pos = 200
    for class_id in range(4):
        class_name = CLASS_NAMES.get(class_id, f"Class_{class_id}")
        detected = class_id in all_detections if all_detections else False

        if detected:
            conf = all_detections[class_id][1]
            reliable = conf >= CONFIDENCE_THRESHOLD
            if reliable:
                indicator = "✓"
                color = (0, 255, 0)  # Green
                status_text = f"{indicator} {class_name} ({conf:.2f})"
            else:
                indicator = "✓"
                color = (0, 255, 255)  # Yellow
                status_text = f"{indicator} {class_name} ({conf:.2f}) LOW"
        else:
            indicator = "✗"
            color = (0, 0, 255)  # Red
            status_text = f"{indicator} {class_name}"

        cv2.putText(frame, status_text, (20, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        y_pos += 20

    # Debug view - draw all bounding boxes
    if debug_view and results:
        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            class_name = CLASS_NAMES.get(cls, f"Class_{cls}")

            # Draw bounding box (color by class)
            colors = {0: (255, 255, 0), 1: (255, 128, 0), 2: (0, 255, 0), 3: (255, 0, 0)}
            color = colors.get(cls, (255, 255, 255))
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
    print(f"🔧 Perspective correction: applied in background for distance calculations")
    print(f"   Display: original camera view")
    print(f"   Distance calculations: corrected frame (6px/cm uniform scale)")
    print()

    # Create window
    window_name = "YOLO Consist Tracking - Press Q to quit"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, actual_width, actual_height)

    # Initialize tracker
    tracker = YOLOTracker(model_path)

    # State
    paused = False
    debug_view = False
    show_panels = True
    frame_count = 0

    # Detection state tracking for logging
    prev_detection_state = {}  # {class_id: bool}
    log_interval = 150  # Log summary every 150 frames (~10s @ 15fps)

    print("🚂 Tracking started! Locomotives will be detected automatically...")
    print()

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("❌ Lost connection")
                break

            frame_count += 1

            # Track BOTH consists
            track_data = tracker.update(frame)
            all_detections = track_data['detections']

            # Log detection state changes (immediate)
            current_detection_state = {}
            for class_id in range(4):  # Classes 0-3
                detected = class_id in all_detections
                if detected:
                    conf = all_detections[class_id][1]
                    reliable = conf >= CONFIDENCE_THRESHOLD
                    current_detection_state[class_id] = reliable
                else:
                    current_detection_state[class_id] = False

                # Check if state changed
                if class_id not in prev_detection_state:
                    prev_detection_state[class_id] = False

                if current_detection_state[class_id] != prev_detection_state[class_id]:
                    class_name = CLASS_NAMES.get(class_id, f"Class_{class_id}")
                    if current_detection_state[class_id]:
                        conf = all_detections[class_id][1]
                        print(f"✅ {class_name} detected (confidence: {conf:.2f})")
                    else:
                        if class_id in all_detections:
                            conf = all_detections[class_id][1]
                            print(f"⚠️  {class_name} lost (low confidence: {conf:.2f})")
                        else:
                            print(f"❌ {class_name} lost (not detected)")

            prev_detection_state = current_detection_state.copy()

            # Periodic summary log (every 150 frames ~10s)
            if frame_count % log_interval == 0:
                detected_count = sum(1 for detected in current_detection_state.values() if detected)
                print(f"\n📊 Frame {frame_count}: {detected_count}/4 locomotives detected")
                for class_id in range(4):
                    class_name = CLASS_NAMES.get(class_id, f"Class_{class_id}")
                    if class_id in all_detections:
                        conf = all_detections[class_id][1]
                        reliable = conf >= CONFIDENCE_THRESHOLD
                        if reliable:
                            print(f"   {class_name}: ✓ RELIABLE ({conf:.2f})")
                        else:
                            print(f"   {class_name}: ⚠ LOW CONFIDENCE ({conf:.2f})")
                    else:
                        print(f"   {class_name}: ✗ NOT DETECTED")
                print()

            # Draw overlay
            draw_overlay(frame, tracker, track_data, debug_view, show_panels)

            # Display
            cv2.imshow(window_name, frame)

        # Handle keyboard
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q') or key == ord('Q'):
            print("\nQuitting...")
            break
        elif key == ord('r') or key == ord('R'):
            print("🔄 Reset distance history + min/max for BOTH consists")
            # Reset Consist 10
            tracker.c10_distance_history.clear()
            tracker.c10_min_distance = float('inf')
            tracker.c10_max_distance = 0.0
            # Reset Consist 11
            tracker.c11_distance_history.clear()
            tracker.c11_min_distance = float('inf')
            tracker.c11_max_distance = 0.0
        elif key == ord('d') or key == ord('D'):
            debug_view = not debug_view
            print(f"🐛 Debug view: {'ON' if debug_view else 'OFF'}")
        elif key == ord('p') or key == ord('P'):
            show_panels = not show_panels
            print(f"📋 All panels: {'ON' if show_panels else 'OFF (markers only)'}")
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

    # Summary (perspective-corrected values)
    print(f"\n📊 Tracking Summary (perspective corrected @ 6px/cm):")
    print(f"   Frames processed: {frame_count}")
    print()

    # Consist 10 (Tracciato Interno)
    avg_c10 = tracker.get_average_distance('c10')
    if avg_c10:
        avg_c10_cm = avg_c10 / PX_PER_CM
        print(f"🟡 Consist 10 (Tracciato Interno):")
        print(f"   Average distance: {avg_c10:.1f}px = {avg_c10_cm:.1f}cm")
        print(f"   Measurements: {len(tracker.c10_distance_history)}")

        # Min/Max tracking for baseline determination
        if tracker.c10_min_distance != float('inf'):
            min_c10_cm = tracker.c10_min_distance / PX_PER_CM
            suggested_alarm_c10_px = tracker.c10_min_distance + 50
            suggested_alarm_c10_cm = suggested_alarm_c10_px / PX_PER_CM
            print(f"   🚨 Safety Threshold Testing:")
            print(f"      🔴 MINIMUM distance: {tracker.c10_min_distance:.1f}px = {min_c10_cm:.1f}cm")
            print(f"      💡 Suggested alarm: {suggested_alarm_c10_px:.1f}px = {suggested_alarm_c10_cm:.1f}cm (+50px margin)")

        if tracker.c10_max_distance > 0:
            max_c10_cm = tracker.c10_max_distance / PX_PER_CM
            print(f"      🔵 MAXIMUM distance: {tracker.c10_max_distance:.1f}px = {max_c10_cm:.1f}cm")

        print(f"   📋 Baseline for drift monitoring:")
        target_variation_cm = 50 / PX_PER_CM
        warning_c10_cm = (avg_c10 + 100) / PX_PER_CM
        print(f"      Target: {avg_c10:.1f}px ({avg_c10_cm:.1f}cm) ±50px ({target_variation_cm:.1f}cm) normal variation")
        if tracker.c10_min_distance != float('inf'):
            print(f"      Critical: <{suggested_alarm_c10_px:.1f}px (<{suggested_alarm_c10_cm:.1f}cm) DANGER")
        print(f"      Warning: >{avg_c10 + 100:.1f}px (>{warning_c10_cm:.1f}cm) elongating")
        print()
    else:
        print(f"🟡 Consist 10 (Tracciato Interno): No data (locomotives not detected together)")
        print()

    # Consist 11 (Tracciato Esterno)
    avg_c11 = tracker.get_average_distance('c11')
    if avg_c11:
        avg_c11_cm = avg_c11 / PX_PER_CM
        print(f"🟢 Consist 11 (Tracciato Esterno):")
        print(f"   Average distance: {avg_c11:.1f}px = {avg_c11_cm:.1f}cm")
        print(f"   Measurements: {len(tracker.c11_distance_history)}")

        # Min/Max tracking for baseline determination
        if tracker.c11_min_distance != float('inf'):
            min_c11_cm = tracker.c11_min_distance / PX_PER_CM
            suggested_alarm_c11_px = tracker.c11_min_distance + 50
            suggested_alarm_c11_cm = suggested_alarm_c11_px / PX_PER_CM
            print(f"   🚨 Safety Threshold Testing:")
            print(f"      🔴 MINIMUM distance: {tracker.c11_min_distance:.1f}px = {min_c11_cm:.1f}cm")
            print(f"      💡 Suggested alarm: {suggested_alarm_c11_px:.1f}px = {suggested_alarm_c11_cm:.1f}cm (+50px margin)")

        if tracker.c11_max_distance > 0:
            max_c11_cm = tracker.c11_max_distance / PX_PER_CM
            print(f"      🔵 MAXIMUM distance: {tracker.c11_max_distance:.1f}px = {max_c11_cm:.1f}cm")

        print(f"   📋 Baseline for drift monitoring:")
        target_variation_cm = 50 / PX_PER_CM
        warning_c11_cm = (avg_c11 + 100) / PX_PER_CM
        print(f"      Target: {avg_c11:.1f}px ({avg_c11_cm:.1f}cm) ±50px ({target_variation_cm:.1f}cm) normal variation")
        if tracker.c11_min_distance != float('inf'):
            print(f"      Critical: <{suggested_alarm_c11_px:.1f}px (<{suggested_alarm_c11_cm:.1f}cm) DANGER")
        print(f"      Warning: >{avg_c11 + 100:.1f}px (>{warning_c11_cm:.1f}cm) elongating")
        print()
    else:
        print(f"🟢 Consist 11 (Tracciato Esterno): No data (locomotives not detected together)")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="YOLO-based tracking for BOTH Consist 10 and Consist 11"
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
