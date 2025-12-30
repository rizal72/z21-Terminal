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

Marker Mode (for gate positioning):
    - M: Toggle marker mode ON/OFF
    - CLICK: Place gate rectangle at mouse position
    - W/S: Increase/decrease height (+/- 10px)
    - Z/X: Decrease/increase width (+/- 20px)
    - R: Rotate counter-clockwise (15° steps)
    - ENTER: Save current gate
    - C: Clear (current gate if present, otherwise all saved gates)
    - E: Export gates to console

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
import time

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

# Marker mode settings
DEFAULT_GATE_WIDTH = 100
DEFAULT_GATE_HEIGHT = 100
DEFAULT_GATE_ANGLE = 0  # Degrees (starts horizontal)
ROTATION_STEP = -15  # Degrees per R key press (counter-clockwise, negative for OpenCV coords)
GATE_COLOR = (0, 255, 255)  # Yellow
GATE_SAVED_COLOR = (0, 255, 0)  # Green

# Gate timing detection (Phase 4 - hardcoded from marker mode 2025-12-30)
# Consist 11: 2 shared gates - both locos cross both gates
GATE_1 = {  # VICINO (bottom right, larger - near camera)
    'center_x': 1227,
    'center_y': 213,  # Moved up 80px from 293
    'width': 100,
    'height': 100,
    'angle': 0
}

GATE_2 = {  # LONTANO (top left, smaller - far from camera)
    'center_x': 141,
    'center_y': 162,
    'width': 60,
    'height': 60,
    'angle': 0
}

# Timing thresholds (seconds)
TIMING_THRESHOLD_NORMAL = 0.5   # |Δt| < 0.5s = green (synced)
TIMING_THRESHOLD_WARNING = 1.0  # |Δt| 0.5-1.0s = yellow (warning)
# |Δt| > 1.0s = red (critical desync)


class MarkerState:
    """State management for gate marker mode."""

    def __init__(self):
        self.enabled = False
        self.current_gate = None  # Current gate being positioned: {'x', 'y', 'width', 'height'}
        self.saved_gates = []  # List of saved gates

    def toggle(self):
        """Toggle marker mode on/off."""
        self.enabled = not self.enabled
        if not self.enabled:
            self.current_gate = None
        return self.enabled

    def place_gate(self, x, y):
        """Place a new gate at position (x, y)."""
        self.current_gate = {
            'center_x': x,
            'center_y': y,
            'width': DEFAULT_GATE_WIDTH,
            'height': DEFAULT_GATE_HEIGHT,
            'angle': DEFAULT_GATE_ANGLE  # Rotation in degrees
        }

    def adjust_width(self, delta):
        """Adjust current gate width (expands from center)."""
        if self.current_gate:
            new_width = max(50, self.current_gate['width'] + delta)
            self.current_gate['width'] = new_width

    def adjust_height(self, delta):
        """Adjust current gate height (expands from center)."""
        if self.current_gate:
            new_height = max(30, self.current_gate['height'] + delta)
            self.current_gate['height'] = new_height

    def adjust_angle(self, delta):
        """Adjust current gate rotation angle."""
        if self.current_gate:
            new_angle = (self.current_gate['angle'] + delta) % 360
            self.current_gate['angle'] = new_angle

    def save_current_gate(self):
        """Save current gate to list."""
        if self.current_gate:
            self.saved_gates.append(self.current_gate.copy())
            print(f"✅ Gate saved: {len(self.saved_gates)} total")
            self.current_gate = None

    def clear_current(self):
        """Clear current gate only."""
        if self.current_gate:
            self.current_gate = None
            print("🗑️  Current gate discarded")
            return True
        return False

    def clear_all_saved(self):
        """Clear all saved gates."""
        if self.saved_gates:
            self.saved_gates = []
            print("🗑️  All saved gates cleared")
            return True
        return False

    def export_gates(self):
        """Export gates as Python code."""
        if not self.saved_gates:
            print("⚠️  No gates to export")
            return

        print("\n" + "="*60)
        print("GATE ZONES (Copy-paste ready for Python code)")
        print("="*60)

        for i, gate in enumerate(self.saved_gates):
            cx, cy = gate['center_x'], gate['center_y']
            w, h = gate['width'], gate['height']
            angle = gate['angle']

            print(f"\n# Gate {i+1}")
            print(f"gate_{i+1} = {{")
            print(f"    'center_x': {cx},")
            print(f"    'center_y': {cy},")
            print(f"    'width': {w},")
            print(f"    'height': {h},")
            print(f"    'angle': {angle}  # degrees")
            print(f"}}")

            # Also show as rotated polygon coordinates
            import math
            angle_rad = math.radians(angle)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            hw, hh = w / 2.0, h / 2.0

            corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
            print(f"# Or as rotated polygon:")
            print(f"# gate_{i+1}_poly = np.float32([")
            for x, y in corners:
                x_rot = int(cx + x * cos_a - y * sin_a)
                y_rot = int(cy + x * sin_a + y * cos_a)
                print(f"#     [{x_rot}, {y_rot}],")
            print(f"# ])")

        print("\n" + "="*60)


def get_rotated_rect_points(center_x, center_y, width, height, angle_deg):
    """
    Calculate 4 corner points of a rotated rectangle.

    Args:
        center_x, center_y: Center of rectangle
        width, height: Dimensions
        angle_deg: Rotation angle in degrees (negative = clockwise)

    Returns:
        np.array of 4 points (TL, TR, BR, BL)
    """
    import math
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    # Half dimensions
    hw = width / 2.0
    hh = height / 2.0

    # 4 corners relative to center (before rotation)
    corners = [
        (-hw, -hh),  # Top-left
        (hw, -hh),   # Top-right
        (hw, hh),    # Bottom-right
        (-hw, hh)    # Bottom-left
    ]

    # Rotate and translate to absolute position
    rotated = []
    for x, y in corners:
        # Rotation matrix
        x_rot = x * cos_a - y * sin_a
        y_rot = x * sin_a + y * cos_a
        # Translate to center
        rotated.append((int(center_x + x_rot), int(center_y + y_rot)))

    return np.array(rotated, dtype=np.int32)


def is_point_in_gate(point, gate):
    """
    Check if a point (locomotive center) is inside a gate zone.

    Args:
        point: (x, y) tuple
        gate: dict with 'center_x', 'center_y', 'width', 'height', 'angle'

    Returns:
        bool: True if point is inside gate
    """
    if point is None:
        return False

    # Get gate polygon points
    gate_points = get_rotated_rect_points(
        gate['center_x'], gate['center_y'],
        gate['width'], gate['height'],
        gate['angle']
    )

    # Use OpenCV pointPolygonTest (returns positive if inside)
    result = cv2.pointPolygonTest(gate_points, point, False)
    return result >= 0  # >= 0 means inside or on edge


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
        self.c10_visible_together_count = 0

        # Consist 11 (Tracciato Esterno)
        self.c11_lead_pos = None
        self.c11_rear_pos = None
        self.c11_visible_together_count = 0

        # Gate timing detection (Phase 4 - Consist 11 only for now)
        # CRITICAL: Locomotives travel in OPPOSITE directions on oval track!
        # When loco7 is at G1, loco8 is at G2 (and vice versa)
        # So we calculate CROSS-GATE Δt, not same-gate

        # Track last timestamp for each loco crossing each gate
        self.c11_lead_gate1_timestamp = None
        self.c11_lead_gate2_timestamp = None
        self.c11_rear_gate1_timestamp = None
        self.c11_rear_gate2_timestamp = None

        # Track if loco is currently inside gate (for edge detection)
        self.c11_lead_in_gate1 = False
        self.c11_lead_in_gate2 = False
        self.c11_rear_in_gate1 = False
        self.c11_rear_in_gate2 = False

        # Latest Δt value (cross-gate)
        self.delta_t = None  # Δt = loco7_gate1 - loco8_gate2 OR loco7_gate2 - loco8_gate1
        self.delta_t_type = None  # "L7G1-L8G2" or "L7G2-L8G1"

        # Gate crossing statistics
        self.gate_crossing_count = 0  # Total number of Δt calculations

        # Last Δt calculation time (to avoid calculating with stale timestamps)
        self.last_delta_t_time = 0  # Initialize to 0 (epoch start)

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

        # Track visibility (both locomotives visible together)
        if c10_lead_pos and c10_rear_pos:
            self.c10_lead_pos = c10_lead_pos
            self.c10_rear_pos = c10_rear_pos
            self.c10_visible_together_count += 1

        # === CONSIST 11 (Tracciato Esterno) ===
        c11_lead_data = detections.get(2)  # E656_239 (class 2)
        c11_rear_data = detections.get(3)  # E444_056 (class 3)

        c11_lead_pos = c11_lead_data[0] if c11_lead_data else None
        c11_lead_conf = c11_lead_data[1] if c11_lead_data else 0.0

        c11_rear_pos = c11_rear_data[0] if c11_rear_data else None
        c11_rear_conf = c11_rear_data[1] if c11_rear_data else 0.0

        # Track visibility (both locomotives visible together)
        if c11_lead_pos and c11_rear_pos:
            self.c11_lead_pos = c11_lead_pos
            self.c11_rear_pos = c11_rear_pos
            self.c11_visible_together_count += 1

        # === GATE TIMING DETECTION (Phase 4 - Consist 11) ===
        # CRITICAL: Locomotives travel in OPPOSITE directions!
        # When Loco7 is at G1, Loco8 is at G2 (cross-gate timing)

        # Gate 1 (VICINO) - Lead loco (E656_239)
        in_gate1 = is_point_in_gate(c11_lead_pos, GATE_1)
        if in_gate1 and not self.c11_lead_in_gate1:
            # Rising edge: loco just entered gate
            self.c11_lead_gate1_timestamp = time.time()
            self.c11_lead_in_gate1 = True
            # Calculate CROSS-GATE Δt: Loco7@G1 - Loco8@G2
            # Only if BOTH timestamps are fresh (after last Δt calculation)
            if (self.c11_rear_gate2_timestamp is not None and
                self.c11_rear_gate2_timestamp > self.last_delta_t_time):
                self.delta_t = self.c11_lead_gate1_timestamp - self.c11_rear_gate2_timestamp
                self.delta_t_type = "L7G1-L8G2"
                self.gate_crossing_count += 1
                self.last_delta_t_time = time.time()
                print(f"🚪 Cross-gate: Loco7@G1 - Loco8@G2 = Δt = {self.delta_t:+.3f}s")
        elif not in_gate1:
            self.c11_lead_in_gate1 = False

        # Gate 1 (VICINO) - Rear loco (E444_056)
        in_gate1 = is_point_in_gate(c11_rear_pos, GATE_1)
        if in_gate1 and not self.c11_rear_in_gate1:
            # Rising edge: loco just entered gate
            self.c11_rear_gate1_timestamp = time.time()
            self.c11_rear_in_gate1 = True
            # Calculate CROSS-GATE Δt: Loco7@G2 - Loco8@G1
            # Only if BOTH timestamps are fresh (after last Δt calculation)
            if (self.c11_lead_gate2_timestamp is not None and
                self.c11_lead_gate2_timestamp > self.last_delta_t_time):
                self.delta_t = self.c11_lead_gate2_timestamp - self.c11_rear_gate1_timestamp
                self.delta_t_type = "L7G2-L8G1"
                self.gate_crossing_count += 1
                self.last_delta_t_time = time.time()
                print(f"🚪 Cross-gate: Loco7@G2 - Loco8@G1 = Δt = {self.delta_t:+.3f}s")
        elif not in_gate1:
            self.c11_rear_in_gate1 = False

        # Gate 2 (LONTANO) - Lead loco (E656_239)
        in_gate2 = is_point_in_gate(c11_lead_pos, GATE_2)
        if in_gate2 and not self.c11_lead_in_gate2:
            # Rising edge: loco just entered gate
            self.c11_lead_gate2_timestamp = time.time()
            self.c11_lead_in_gate2 = True
            # Calculate CROSS-GATE Δt: Loco7@G2 - Loco8@G1
            # Only if BOTH timestamps are fresh (after last Δt calculation)
            if (self.c11_rear_gate1_timestamp is not None and
                self.c11_rear_gate1_timestamp > self.last_delta_t_time):
                self.delta_t = self.c11_lead_gate2_timestamp - self.c11_rear_gate1_timestamp
                self.delta_t_type = "L7G2-L8G1"
                self.gate_crossing_count += 1
                self.last_delta_t_time = time.time()
                print(f"🚪 Cross-gate: Loco7@G2 - Loco8@G1 = Δt = {self.delta_t:+.3f}s")
        elif not in_gate2:
            self.c11_lead_in_gate2 = False

        # Gate 2 (LONTANO) - Rear loco (E444_056)
        in_gate2 = is_point_in_gate(c11_rear_pos, GATE_2)
        if in_gate2 and not self.c11_rear_in_gate2:
            # Rising edge: loco just entered gate
            self.c11_rear_gate2_timestamp = time.time()
            self.c11_rear_in_gate2 = True
            # Calculate CROSS-GATE Δt: Loco7@G1 - Loco8@G2
            # Only if BOTH timestamps are fresh (after last Δt calculation)
            if (self.c11_lead_gate1_timestamp is not None and
                self.c11_lead_gate1_timestamp > self.last_delta_t_time):
                self.delta_t = self.c11_lead_gate1_timestamp - self.c11_rear_gate2_timestamp
                self.delta_t_type = "L7G1-L8G2"
                self.gate_crossing_count += 1
                self.last_delta_t_time = time.time()
                print(f"🚪 Cross-gate: Loco7@G1 - Loco8@G2 = Δt = {self.delta_t:+.3f}s")
        elif not in_gate2:
            self.c11_rear_in_gate2 = False

        return {
            'c10': {'lead_pos': c10_lead_pos, 'rear_pos': c10_rear_pos,
                    'lead_conf': c10_lead_conf, 'rear_conf': c10_rear_conf},
            'c11': {'lead_pos': c11_lead_pos, 'rear_pos': c11_rear_pos,
                    'lead_conf': c11_lead_conf, 'rear_conf': c11_rear_conf},
            'detections': detections,
            'results': results
        }

    def get_visibility_stats(self, consist, total_frames):
        """Get visibility statistics for specified consist."""
        count = self.c11_visible_together_count if consist == 'c11' else self.c10_visible_together_count
        percentage = (count / total_frames * 100) if total_frames > 0 else 0
        return count, percentage


def draw_overlay(frame, tracker, track_data, debug_view, show_panels=True, total_frames=0, marker_state=None):
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
        cv2.circle(frame, c11['rear_pos'], 10, (0, 0, 255), -1)  # Red (readable on black)

    if c11['lead_pos'] and c11['rear_pos']:
        cv2.line(frame, c11['lead_pos'], c11['rear_pos'], (255, 255, 0), 2)

    # Draw gate markers (always visible, even if panels hidden)
    if marker_state:
        # Draw saved gates (green)
        for gate in marker_state.saved_gates:
            cx, cy = gate['center_x'], gate['center_y']
            w, h = gate['width'], gate['height']
            angle = gate['angle']

            # Get rotated rectangle points
            points = get_rotated_rect_points(cx, cy, w, h, angle)
            cv2.polylines(frame, [points], True, GATE_SAVED_COLOR, 2)

            # Draw center crosshair
            cv2.line(frame, (cx - 10, cy), (cx + 10, cy), GATE_SAVED_COLOR, 1)
            cv2.line(frame, (cx, cy - 10), (cx, cy + 10), GATE_SAVED_COLOR, 1)

        # Draw current gate being positioned (yellow)
        if marker_state.current_gate:
            gate = marker_state.current_gate
            cx, cy = gate['center_x'], gate['center_y']
            w, h = gate['width'], gate['height']
            angle = gate['angle']

            # Get rotated rectangle points
            points = get_rotated_rect_points(cx, cy, w, h, angle)
            cv2.polylines(frame, [points], True, GATE_COLOR, 2)

            # Draw center crosshair
            cv2.line(frame, (cx - 10, cy), (cx + 10, cy), GATE_COLOR, 1)
            cv2.line(frame, (cx, cy - 10), (cx, cy + 10), GATE_COLOR, 1)

            # Show dimensions and angle
            dim_text = f"{w}x{h}px @ {angle}deg"
            cv2.putText(frame, dim_text, (cx - 60, cy - h//2 - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, GATE_COLOR, 2)

        # Show marker mode indicator
        if marker_state.enabled:
            overlay = frame.copy()
            cv2.rectangle(overlay, (5, frame.shape[0] - 90), (380, frame.shape[0] - 5), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
            cv2.putText(frame, "MARKER MODE (M to exit)", (15, frame.shape[0] - 75),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(frame, "CLICK: place | W/S: height | Z/X: width", (15, frame.shape[0] - 53),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(frame, "R: rotate 15deg | ENTER: save | C: clear", (15, frame.shape[0] - 33),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(frame, "E: export gates to console", (15, frame.shape[0] - 13),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    # Draw timing gates (always visible - cyan/blue color for distinction)
    # Gate 1 (VICINO - bottom right)
    gate1_points = get_rotated_rect_points(
        GATE_1['center_x'], GATE_1['center_y'],
        GATE_1['width'], GATE_1['height'],
        GATE_1['angle']
    )
    cv2.polylines(frame, [gate1_points], True, (255, 255, 0), 2)  # Cyan
    cv2.putText(frame, "G1", (GATE_1['center_x'] - 10, GATE_1['center_y'] + 5),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

    # Gate 2 (LONTANO - top left)
    gate2_points = get_rotated_rect_points(
        GATE_2['center_x'], GATE_2['center_y'],
        GATE_2['width'], GATE_2['height'],
        GATE_2['angle']
    )
    cv2.polylines(frame, [gate2_points], True, (255, 128, 0), 2)  # Orange/cyan
    cv2.putText(frame, "G2", (GATE_2['center_x'] - 10, GATE_2['center_y'] + 5),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 128, 0), 2)

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

    # Co-Visibility Stats Panel
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 40), (550, 110), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.putText(frame, "Co-Visibility (Lead + Rear together):", (10, 60),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # Consist 10 stats
    c10_count, c10_pct = tracker.get_visibility_stats('c10', total_frames)
    c10_status = "YES" if (c10['lead_pos'] and c10['rear_pos']) else "NO"
    cv2.putText(frame, f"C10: {c10_status}  {c10_count} frames ({c10_pct:.1f}%)", (20, 85),
               cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 0), 1)

    # Consist 11 stats
    c11_count, c11_pct = tracker.get_visibility_stats('c11', total_frames)
    c11_status = "YES" if (c11['lead_pos'] and c11['rear_pos']) else "NO"
    cv2.putText(frame, f"C11: {c11_status}  {c11_count} frames ({c11_pct:.1f}%)", (280, 85),
               cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

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
                indicator = "+"
                color = (0, 255, 0)  # Green
                status_text = f"{indicator} {class_name} ({conf:.2f})"
            else:
                indicator = "+"
                color = (0, 255, 255)  # Yellow
                status_text = f"{indicator} {class_name} ({conf:.2f}) LOW"
        else:
            indicator = "X"
            color = (0, 0, 255)  # Red
            status_text = f"{indicator} {class_name}"

        cv2.putText(frame, status_text, (20, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        y_pos += 20

    # Gate Timing Panel (Consist 11) - Cross-gate detection
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 285), (450, 390), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.putText(frame, "Gate Timing (Consist 11 - Cross-gate):", (10, 305),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # Last timestamps
    cv2.putText(frame, "Last crossing timestamps:", (15, 325),
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

    # Loco 7 timestamps (both gates)
    l7g1_str = "---"
    l7g2_str = "---"
    if tracker.c11_lead_gate1_timestamp:
        l7g1_str = time.strftime("%H:%M:%S", time.localtime(tracker.c11_lead_gate1_timestamp))
    if tracker.c11_lead_gate2_timestamp:
        l7g2_str = time.strftime("%H:%M:%S", time.localtime(tracker.c11_lead_gate2_timestamp))

    cv2.putText(frame, f"Loco 7: G1={l7g1_str}  G2={l7g2_str}", (25, 345),
               cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)

    # Loco 8 timestamps (both gates)
    l8g1_str = "---"
    l8g2_str = "---"
    if tracker.c11_rear_gate1_timestamp:
        l8g1_str = time.strftime("%H:%M:%S", time.localtime(tracker.c11_rear_gate1_timestamp))
    if tracker.c11_rear_gate2_timestamp:
        l8g2_str = time.strftime("%H:%M:%S", time.localtime(tracker.c11_rear_gate2_timestamp))

    cv2.putText(frame, f"Loco 8: G1={l8g1_str}  G2={l8g2_str}", (25, 365),
               cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)  # Red (readable on black)

    # Cross-gate Δt (single value)
    if tracker.delta_t is not None:
        dt_abs = abs(tracker.delta_t)
        if dt_abs < TIMING_THRESHOLD_NORMAL:
            color = (0, 255, 0)  # Green
            status = "SYNCED"
        elif dt_abs < TIMING_THRESHOLD_WARNING:
            color = (0, 255, 255)  # Yellow
            status = "WARNING"
        else:
            color = (0, 0, 255)  # Red
            status = "CRITICAL"

        cv2.putText(frame, f"Dt (cross-gate) = {tracker.delta_t:+.3f}s  {status}", (15, 385),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
    else:
        cv2.putText(frame, "Dt (cross-gate) = --- (waiting for crossing)", (15, 385),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)  # White

    # Debug view - draw all bounding boxes
    if debug_view and results:
        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            class_name = CLASS_NAMES.get(cls, f"Class_{cls}")

            # Draw bounding box (color by class)
            colors = {0: (255, 255, 0), 1: (255, 128, 0), 2: (0, 255, 0), 3: (0, 0, 255)}
            color = colors.get(cls, (255, 255, 255))
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)

            # Draw label
            label = f"{class_name} {conf:.2f}"
            cv2.putText(frame, label, (int(x1), int(y1) - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Draw gate markers (always visible, even if panels hidden)
    if marker_state:
        # Draw saved gates (green)
        for gate in marker_state.saved_gates:
            cx, cy = gate['center_x'], gate['center_y']
            w, h = gate['width'], gate['height']
            angle = gate['angle']

            # Get rotated rectangle points
            points = get_rotated_rect_points(cx, cy, w, h, angle)
            cv2.polylines(frame, [points], True, GATE_SAVED_COLOR, 2)

            # Draw center crosshair
            cv2.line(frame, (cx - 10, cy), (cx + 10, cy), GATE_SAVED_COLOR, 1)
            cv2.line(frame, (cx, cy - 10), (cx, cy + 10), GATE_SAVED_COLOR, 1)

        # Draw current gate being positioned (yellow)
        if marker_state.current_gate:
            gate = marker_state.current_gate
            cx, cy = gate['center_x'], gate['center_y']
            w, h = gate['width'], gate['height']
            angle = gate['angle']

            # Get rotated rectangle points
            points = get_rotated_rect_points(cx, cy, w, h, angle)
            cv2.polylines(frame, [points], True, GATE_COLOR, 2)

            # Draw center crosshair
            cv2.line(frame, (cx - 10, cy), (cx + 10, cy), GATE_COLOR, 1)
            cv2.line(frame, (cx, cy - 10), (cx, cy + 10), GATE_COLOR, 1)

            # Show dimensions and angle
            dim_text = f"{w}x{h}px @ {angle}deg"
            cv2.putText(frame, dim_text, (cx - 60, cy - h//2 - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, GATE_COLOR, 2)

        # Show marker mode indicator
        if marker_state.enabled:
            overlay = frame.copy()
            cv2.rectangle(overlay, (5, frame.shape[0] - 90), (380, frame.shape[0] - 5), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
            cv2.putText(frame, "MARKER MODE (M to exit)", (15, frame.shape[0] - 75),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(frame, "CLICK: place | W/S: height | Z/X: width", (15, frame.shape[0] - 53),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(frame, "R: rotate 15deg | ENTER: save | C: clear", (15, frame.shape[0] - 33),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(frame, "E: export gates to console", (15, frame.shape[0] - 13),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)


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

    # Initialize marker state
    marker_state = MarkerState()

    # Mouse callback for marker mode
    def mouse_callback(event, x, y, flags, param):
        if marker_state.enabled and event == cv2.EVENT_LBUTTONDOWN:
            marker_state.place_gate(x, y)
            print(f"📍 Gate placed at ({x}, {y}) - size: 100x100px")

    cv2.setMouseCallback(window_name, mouse_callback)

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

    # Session tracking
    start_time = time.time()

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

            # Log detection state changes (immediate) - COMMENTED OUT for cleaner logs
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

                # Uncomment for immediate detection/lost logging (debug mode)
                # if current_detection_state[class_id] != prev_detection_state[class_id]:
                #     class_name = CLASS_NAMES.get(class_id, f"Class_{class_id}")
                #     if current_detection_state[class_id]:
                #         conf = all_detections[class_id][1]
                #         print(f"✅ {class_name} detected (confidence: {conf:.2f})")
                #     else:
                #         if class_id in all_detections:
                #             conf = all_detections[class_id][1]
                #             print(f"⚠️  {class_name} lost (low confidence: {conf:.2f})")
                #         else:
                #             print(f"❌ {class_name} lost (not detected)")

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
            draw_overlay(frame, tracker, track_data, debug_view, show_panels, frame_count, marker_state)

            # Display
            cv2.imshow(window_name, frame)

        # Handle keyboard
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q') or key == ord('Q'):
            print("\nQuitting...")
            break
        elif key == ord('r') or key == ord('R'):
            # In marker mode with current gate: rotate
            if marker_state.enabled and marker_state.current_gate:
                marker_state.adjust_angle(ROTATION_STEP)
                angle = marker_state.current_gate['angle']
                print(f"🔄 Rotated: {angle}°")
            else:
                # Otherwise: reset tracking counters
                print("🔄 Reset tracking counters (visibility + gate crossings)")
                tracker.c10_visible_together_count = 0
                tracker.c11_visible_together_count = 0
                tracker.gate_crossing_count = 0  # Reset gate crossing count
                tracker.last_delta_t_time = 0  # Reset last Δt time
                frame_count = 0  # Reset frame count too
        elif key == ord('d') or key == ord('D'):
            debug_view = not debug_view
            print(f"🐛 Debug view: {'ON' if debug_view else 'OFF'}")
        elif key == ord('p') or key == ord('P'):
            show_panels = not show_panels
            print(f"📋 All panels: {'ON' if show_panels else 'OFF (markers only)'}")
        elif key == ord('s') or key == ord('S'):
            # In marker mode, S = decrease height
            if marker_state.enabled and marker_state.current_gate:
                marker_state.adjust_height(-10)
                h = marker_state.current_gate['height']
                print(f"⬇️  Height decreased: {h}px")
            else:
                # Save snapshot (only when NOT in marker mode)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"tracking_snapshot_{timestamp}.jpg"
                script_dir = Path(__file__).parent
                filepath = script_dir / filename
                cv2.imwrite(str(filepath), frame)
                print(f"📸 Snapshot saved: {filepath}")
        elif key == ord(' '):
            paused = not paused
            print(f"{'⏸️  Paused' if paused else '▶️  Resumed'}")
        # Marker mode controls
        elif key == ord('m') or key == ord('M'):
            enabled = marker_state.toggle()
            print(f"🎯 Marker mode: {'ON' if enabled else 'OFF'}")
        elif key == ord('w') or key == ord('W'):
            if marker_state.current_gate:
                marker_state.adjust_height(10)
                h = marker_state.current_gate['height']
                print(f"⬆️  Height increased: {h}px")
        elif key == ord('z') or key == ord('Z'):
            if marker_state.current_gate:
                marker_state.adjust_width(-20)
                w = marker_state.current_gate['width']
                print(f"⬅️  Width decreased: {w}px")
        elif key == ord('x') or key == ord('X'):
            if marker_state.current_gate:
                marker_state.adjust_width(20)
                w = marker_state.current_gate['width']
                print(f"➡️  Width increased: {w}px")
        elif key == 13:  # ENTER key
            if marker_state.current_gate:
                marker_state.save_current_gate()
        elif key == ord('c') or key == ord('C'):
            if marker_state.enabled:
                # Smart clear: current gate first, then all saved
                if not marker_state.clear_current():
                    marker_state.clear_all_saved()
        elif key == ord('e') or key == ord('E'):
            marker_state.export_gates()

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()

    # Export gates if any were saved
    if marker_state.saved_gates:
        print("\n" + "="*60)
        print("🎯 GATES SAVED DURING SESSION:")
        print("="*60)
        marker_state.export_gates()

    # Session summary
    end_time = time.time()
    elapsed_time = end_time - start_time
    elapsed_minutes = int(elapsed_time // 60)
    elapsed_seconds = int(elapsed_time % 60)

    print(f"\n📊 SESSION SUMMARY")
    print("=" * 60)
    print(f"⏱️  Duration: {elapsed_minutes}m {elapsed_seconds}s")
    print(f"🎞️  Frames processed: {frame_count}")
    print()

    # Gate timing statistics (Consist 11)
    print("🚪 GATE TIMING DETECTION (Consist 11 - Cross-Gate)")
    print("-" * 60)
    print(f"   Gate crossings detected: {tracker.gate_crossing_count}")

    if tracker.delta_t is not None:
        # Calculate status based on thresholds
        dt_abs = abs(tracker.delta_t)
        if dt_abs < TIMING_THRESHOLD_NORMAL:
            status = "🟢 SYNCED"
        elif dt_abs < TIMING_THRESHOLD_WARNING:
            status = "🟡 WARNING"
        else:
            status = "🔴 CRITICAL DESYNC"

        print(f"   Last Δt measured: {tracker.delta_t:+.3f}s  {status}")
        print(f"   Crossing type: {tracker.delta_t_type}")
        print()
        print("   Δt Interpretation:")
        if tracker.delta_t > 0:
            print("   → Loco 7 (E656_239) passing first - running faster")
        else:
            print("   → Loco 8 (E444_056) passing first - Loco 7 running slower")
    else:
        print("   Last Δt: --- (no crossing detected)")
        print("   ⚠️  Locomotives not detected passing through gates")

    print()
    print("   Thresholds:")
    print(f"   🟢 |Δt| < {TIMING_THRESHOLD_NORMAL}s = SYNCED")
    print(f"   🟡 |Δt| {TIMING_THRESHOLD_NORMAL}-{TIMING_THRESHOLD_WARNING}s = WARNING")
    print(f"   🔴 |Δt| > {TIMING_THRESHOLD_WARNING}s = CRITICAL")
    print()

    # Co-visibility statistics (secondary)
    print("👁️  CO-VISIBILITY STATISTICS")
    print("-" * 60)
    c10_count, c10_pct = tracker.get_visibility_stats('c10', frame_count)
    c11_count, c11_pct = tracker.get_visibility_stats('c11', frame_count)
    print(f"   Consist 10 (Interno): {c10_count} frames ({c10_pct:.1f}%) - {c10_count} co-detections")
    print(f"   Consist 11 (Esterno): {c11_count} frames ({c11_pct:.1f}%) - {c11_count} co-detections")
    print()
    print("="*60)


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
