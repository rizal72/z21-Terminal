#!/usr/bin/env python3
"""
YOLO-based tracking for multiple consists (config-driven).

Dynamically tracks N consists based on config.json:
    - Consist 10 (Tracciato Interno): Gr.675 017 + D645 014
    - Consist 11 (Tracciato Esterno): E656 239 + E444 056
    - Additional consists can be added via config

Uses custom trained YOLOv8 model for real-time locomotive detection.

Gate Timing Detection:
    - Dual-gate co-presence timing for speed matching
    - Cross-gate Δt calculation (timing-based, not distance-based)
    - Real-time delta-t monitoring per consist

Usage:
    python track_consist_yolo.py [--model best.pt]

    Camera credentials are loaded from backend/camera_config.json
    (see backend/README_CAMERA.md for setup)

Controls:
    - Q: Quit
    - SPACE: Pause/Resume video
    - D: Toggle debug view (shows detection markers + confidence + connection lines)
    - P: Toggle info panels (clean view, gates+markers only)
    - Y: Toggle YOLO inference (disable = pause video for fast gate editing)
    - M: Toggle Marker Mode (gate positioning/editing)
    - S: Save gate positions to config.json (Marker Mode only)
    - R: Reset gate crossing counters (all consists)

Marker Mode (M key):
    - Click: Place new gate OR select existing gate
    - Drag: Move gate (click+hold on gate, drag, release)
    - Arrow ↑↓: Increase/decrease height (±10px)
    - Arrow ←→: Decrease/increase width (±10px)
    - Q/E: Rotate gate (±10°)
    - ENTER: Commit gate changes
    - BACKSPACE: Delete selected gate
    - S: Save ALL gates to config.json

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
import json

try:
    from ultralytics import YOLO
except ImportError:
    print("❌ Error: ultralytics not installed")
    print("Install with: pip3 install ultralytics")
    sys.exit(1)

# Detection settings
CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence for detection
# DISTANCE_HISTORY_SIZE = 10000  # [LEGACY - NOT USED] Distance measurements (replaced by gate timing)

# Config paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Add backend to path for config_loader and tracking imports
backend_dir = PROJECT_ROOT / 'backend'
sys.path.insert(0, str(backend_dir))

from config_loader import load_config, save_config as save_config_central, get_config_path

# Import shared tracking modules (YOLO tracker, gate utilities, RTSP handler)
from tracking.yolo_tracker import (
    YOLOTracker,
    gate_json_to_dict,
    get_rotated_rect_points,
    is_point_in_gate,
    CLASS_NAMES,
    ADDRESS_TO_CLASS
)
from tracking.rtsp_handler import load_camera_config, setup_rtsp_stream

# === CONFIGURATION ===
# CLASS_NAMES and ADDRESS_TO_CLASS now imported from tracking.yolo_tracker

# Alias for semantic clarity (same as ADDRESS_TO_CLASS)
DCC_TO_YOLO_CLASS = ADDRESS_TO_CLASS

# === LEGACY CODE - Perspective Correction (NOT USED) ===
# Previously used for distance calculations (6px/cm uniform scale)
# Now replaced by gate timing detection (no distance needed)
# Kept for potential future use
#
# SRC_POINTS = np.float32([
#     [7, 246],      # Top-left
#     [376, 31],     # Top-right
#     [957, 37],     # Bottom-right
#     [257, 718]     # Bottom-left
# ])
#
# DST_WIDTH = 600
# DST_HEIGHT = 1200
# Y_OFFSET = 50
# LAYOUT_HEIGHT = 950
#
# DST_POINTS = np.float32([
#     [0, Y_OFFSET],
#     [DST_WIDTH, Y_OFFSET],
#     [DST_WIDTH, Y_OFFSET + LAYOUT_HEIGHT],
#     [0, Y_OFFSET + LAYOUT_HEIGHT]
# ])
#
# PERSPECTIVE_MATRIX = cv2.getPerspectiveTransform(
#     np.float32([
#         SRC_POINTS[0],
#         SRC_POINTS[1],
#         [SRC_POINTS[2][0] + (SRC_POINTS[2][0] - SRC_POINTS[1][0]) * 0.05,
#          SRC_POINTS[2][1] + (720 - SRC_POINTS[2][1]) * 0.3],
#         [SRC_POINTS[3][0] - (SRC_POINTS[0][0] - SRC_POINTS[3][0]) * 0.05,
#          SRC_POINTS[3][1] + (720 - SRC_POINTS[3][1]) * 0.3]
#     ]),
#     DST_POINTS
# )
# === END LEGACY CODE ===

# PX_PER_CM = 6.0  # [LEGACY - NOT USED] Scale for distance calculations

# Marker mode settings
DEFAULT_GATE_WIDTH = 100
DEFAULT_GATE_HEIGHT = 100
DEFAULT_GATE_ANGLE = 0  # Degrees (starts horizontal)
ROTATION_STEP = -15  # Degrees per R key press (counter-clockwise, negative for OpenCV coords)
GATE_COLOR = (0, 255, 255)  # Yellow
GATE_SAVED_COLOR = (0, 255, 0)  # Green

# Gate timing detection (Phase 4 - loaded from config.json)
# Consist 11: 2 shared gates - both locos cross both gates
# Gates and timing thresholds loaded dynamically from JSON config

# load_config() now imported from config_loader (centralized)


def save_config(config):
    """Save system configuration to JSON file (with automatic backup)."""
    try:
        # Create backup before overwriting
        config_file = get_config_path()
        if config_file.exists():
            import shutil
            backup_file = config_file.with_suffix('.json.backup')
            shutil.copy2(config_file, backup_file)
            print(f"💾 Backup created: {backup_file.name}")

        # Save using centralized config_loader (writes to config.json, NOT config.local.json)
        save_config_central(config)
        print(f"✅ Config saved: {len(config.get('gates', []))} gates")
        return True
    except Exception as e:
        print(f"❌ Error saving config: {e}")
        return False


def get_next_gate_id(config):
    """Get next available gate ID."""
    gates = config.get('gates', [])
    if not gates:
        return 1
    return max(g['id'] for g in gates) + 1


class MarkerState:
    """State management for gate marker mode with config loading/saving."""

    def __init__(self):
        self.enabled = False
        self.current_gate = None  # Current gate being positioned/edited
        self.editing_gate_id = None  # ID of gate being edited (None if new gate)
        self.config = load_config()  # Load from JSON
        # Mouse state for drag & drop
        self.dragging = False
        self.drag_gate_id = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0

    def toggle(self):
        """Toggle marker mode on/off."""
        self.enabled = not self.enabled
        if not self.enabled:
            # Warn if exiting with unsaved current_gate
            if self.current_gate:
                print("⚠️  Unsaved gate discarded (press ENTER to save before exiting marker mode)")
            self.current_gate = None
            self.editing_gate_id = None
            self.dragging = False
        return self.enabled

    def place_gate(self, x, y):
        """Place a new gate at position (x, y)."""
        self.current_gate = {
            'center_x': x,
            'center_y': y,
            'width': DEFAULT_GATE_WIDTH,
            'height': DEFAULT_GATE_HEIGHT,
            'angle': DEFAULT_GATE_ANGLE
        }
        self.editing_gate_id = None  # New gate, not editing existing

    def select_gate(self, gate_id):
        """Select an existing gate for editing."""
        gate = next((g for g in self.config['gates'] if g['id'] == gate_id), None)
        if gate:
            # Load gate into current_gate for editing
            self.current_gate = {
                'center_x': gate['center'][0],
                'center_y': gate['center'][1],
                'width': gate['width'],
                'height': gate['height'],
                'angle': gate['angle']
            }
            self.editing_gate_id = gate_id
            print(f"✏️  Editing Gate {gate_id}")

    def adjust_width(self, delta):
        """Adjust current gate width (10px steps)."""
        if self.current_gate:
            new_width = max(20, self.current_gate['width'] + delta)
            self.current_gate['width'] = new_width

    def adjust_height(self, delta):
        """Adjust current gate height (10px steps)."""
        if self.current_gate:
            new_height = max(20, self.current_gate['height'] + delta)
            self.current_gate['height'] = new_height

    def adjust_angle(self, delta):
        """Adjust current gate rotation angle."""
        if self.current_gate:
            new_angle = (self.current_gate['angle'] + delta) % 360
            self.current_gate['angle'] = new_angle

    def save_current_gate(self, tracker=None):
        """Save current gate to config (new or update existing)."""
        if self.current_gate:
            gate_id_to_update = None
            if self.editing_gate_id is not None:
                # Update existing gate
                gate = next((g for g in self.config['gates'] if g['id'] == self.editing_gate_id), None)
                if gate:
                    gate['center'] = [self.current_gate['center_x'], self.current_gate['center_y']]
                    gate['width'] = self.current_gate['width']
                    gate['height'] = self.current_gate['height']
                    gate['angle'] = self.current_gate['angle']
                    gate_id_to_update = self.editing_gate_id
                    print(f"✅ Gate {self.editing_gate_id} updated")
            else:
                # Add new gate
                gate_id = get_next_gate_id(self.config)

                # Cycle through consist colors in pairs (Orange for C11, Cyan for C10)
                # Gate 1,2: Orange | Gate 3,4: Cyan | Gate 5,6: Orange | etc.
                # Yellow reserved for edit mode
                if ((gate_id - 1) // 2) % 2 == 0:
                    color = [255, 165, 0]  # Orange (C11)
                else:
                    color = [0, 255, 255]  # Cyan (C10)

                new_gate = {
                    'id': gate_id,
                    'name': f"Gate {gate_id}",
                    'center': [self.current_gate['center_x'], self.current_gate['center_y']],
                    'width': self.current_gate['width'],
                    'height': self.current_gate['height'],
                    'angle': self.current_gate['angle'],
                    'color': color
                }
                self.config['gates'].append(new_gate)
                gate_id_to_update = gate_id
                print(f"✅ Gate {gate_id} saved (total: {len(self.config['gates'])})")

            # Update tracker.gates if tracker provided (for immediate rendering)
            if tracker and gate_id_to_update:
                gate_json = next((g for g in self.config['gates'] if g['id'] == gate_id_to_update), None)
                if gate_json:
                    tracker.gates[gate_id_to_update] = gate_json_to_dict(gate_json)

            self.current_gate = None
            self.editing_gate_id = None

    def find_gate_at(self, x, y):
        """Find gate ID at position (x, y). Returns gate_id or None."""
        for gate in self.config['gates']:
            cx, cy = gate['center']
            w, h = gate['width'], gate['height']
            # Simple bounding box check (ignoring rotation for click)
            if abs(x - cx) < w/2 and abs(y - cy) < h/2:
                return gate['id']
        return None

    def start_drag(self, gate_id, mouse_x, mouse_y):
        """Start dragging a gate."""
        gate = next((g for g in self.config['gates'] if g['id'] == gate_id), None)
        if gate:
            self.dragging = True
            self.drag_gate_id = gate_id
            cx, cy = gate['center']
            self.drag_offset_x = cx - mouse_x
            self.drag_offset_y = cy - mouse_y

    def update_drag(self, mouse_x, mouse_y):
        """Update gate position during drag."""
        if self.dragging and self.drag_gate_id:
            gate = next((g for g in self.config['gates'] if g['id'] == self.drag_gate_id), None)
            if gate:
                gate['center'] = [mouse_x + self.drag_offset_x, mouse_y + self.drag_offset_y]

    def stop_drag(self):
        """Stop dragging."""
        self.dragging = False
        self.drag_gate_id = None

    def delete_gate(self, gate_id):
        """Delete gate by ID."""
        self.config['gates'] = [g for g in self.config['gates'] if g['id'] != gate_id]
        print(f"🗑️  Gate {gate_id} deleted")

    def clear_current(self):
        """Clear current gate (or delete if editing existing)."""
        if self.current_gate:
            if self.editing_gate_id is not None:
                # Deleting existing gate
                self.delete_gate(self.editing_gate_id)
                self.editing_gate_id = None
            else:
                # Discarding new gate
                print("🗑️  Current gate discarded")
            self.current_gate = None
            return True
        return False

    def save_to_config(self):
        """Save all gates to JSON config file."""
        if save_config(self.config):
            config_path = get_config_path()
            print(f"💾 Saved {len(self.config['gates'])} gates to {config_path.name}")
            return True
        return False

    def export_gates(self):
        """Export gates as JSON to console."""
        if not self.config['gates']:
            print("⚠️  No gates to export")
            return

        print("\n" + "="*60)
        print("GATE CONFIG (JSON format)")
        print("="*60)
        print(json.dumps(self.config, indent=2))
        print("="*60)


# === LEGACY FUNCTION - transform_to_corrected (NOT USED) ===
# Previously used for perspective correction in distance calculations
# Now replaced by gate timing detection (no distance needed)
#
# def transform_to_corrected(point):
#     """
#     Transform point from original frame to perspective-corrected frame.
#     Used for accurate distance calculations.
#
#     Args:
#         point: (x, y) tuple in original frame coordinates
#
#     Returns:
#         (x, y) tuple in corrected frame coordinates
#     """
#     pts = np.array([[point]], dtype=np.float32)
#     transformed = cv2.perspectiveTransform(pts, PERSPECTIVE_MATRIX)
#     return (transformed[0][0][0], transformed[0][0][1])
# === END LEGACY FUNCTION ===


def draw_gates_overlay(frame, tracker):
    """Draw timing gates on frame (ALWAYS visible, independent from tracking)."""
    # Collect all gate IDs from all consists
    all_gate_ids = set()
    for config in tracker.consist_config.values():
        all_gate_ids.update(config['gate_ids'])

    for gate_id in sorted(all_gate_ids):
        if gate_id not in tracker.gates:
            continue

        gate = tracker.gates[gate_id]
        gate_points = get_rotated_rect_points(
            gate['center_x'], gate['center_y'],
            gate['width'], gate['height'],
            gate['angle']
        )
        # Convert RGB (from config) to BGR (for OpenCV)
        color_rgb = gate.get('color', [255, 255, 0])  # Default yellow if missing
        color = (color_rgb[2], color_rgb[1], color_rgb[0])  # RGB → BGR
        cv2.polylines(frame, [gate_points], True, color, 2)
        cv2.putText(frame, f"G{gate_id}", (gate['center_x'] - 10, gate['center_y'] + 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    return frame


def draw_marker_mode_overlay(frame, marker_state):
    """Draw Marker Mode overlay (ALWAYS visible when marker_state.enabled, independent from tracking)."""
    if not marker_state:
        return frame

    # Color for marker mode
    GATE_COLOR = (0, 255, 255)  # Cyan for current gate being edited
    # Note: Saved gates are drawn by draw_gates_overlay() with their config colors

    # Draw current gate being positioned/edited (cyan)
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
        cv2.rectangle(overlay, (5, frame.shape[0] - 90), (430, frame.shape[0] - 5), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        cv2.putText(frame, "MARKER MODE (M to exit)", (15, frame.shape[0] - 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(frame, "CLICK/DRAG: move | UP/DOWN: height | LEFT/RIGHT: width", (15, frame.shape[0] - 53),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(frame, "ENTER: save | S: save all | C: clear", (15, frame.shape[0] - 33),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(frame, "Q/E: rotate | BACKSPACE: delete", (15, frame.shape[0] - 13),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    return frame


def draw_overlay(frame, tracker, track_data, debug_view, show_panels=True, total_frames=0, marker_state=None, tracking_enabled=True):
    """Draw tracking overlay on frame for ALL consists dynamically."""

    # If tracking disabled, skip all detection overlays (gates are drawn separately)
    if not tracking_enabled or track_data is None:
        return frame

    all_detections = track_data['detections']

    # Reconstruct consist_data from track_data (format: c10, c11, etc.)
    consist_data = {}
    for consist_id in tracker.consist_config.keys():
        consist_key = f'c{consist_id}'
        if consist_key in track_data:
            consist_data[consist_id] = {
                'lead_pos': track_data[consist_key]['lead'],
                'rear_pos': track_data[consist_key]['rear']
            }

    # Define colors for up to 4 consists (can be extended)
    CONSIST_COLORS = {
        10: {'lead': (255, 255, 0), 'rear': (255, 128, 0), 'line': (255, 200, 0)},  # Yellow/Orange
        11: {'lead': (0, 255, 0), 'rear': (0, 0, 255), 'line': (255, 255, 0)},      # Green/Red
        # Add more colors for additional consists if needed
    }

    # Draw markers for ALL consists (always visible - just colored dots)
    for consist_id, consist in consist_data.items():
        colors = CONSIST_COLORS.get(consist_id, {'lead': (255, 255, 255), 'rear': (128, 128, 128), 'line': (200, 200, 200)})

        if consist['lead_pos']:
            cv2.circle(frame, consist['lead_pos'], 10, colors['lead'], -1)

        if consist['rear_pos']:
            cv2.circle(frame, consist['rear_pos'], 10, colors['rear'], -1)

        # Connection line (debug mode only)
        if debug_view and consist['lead_pos'] and consist['rear_pos']:
            cv2.line(frame, consist['lead_pos'], consist['rear_pos'], colors['line'], 2)

    # Debug view - draw bounding boxes, center points, and confidence labels
    # (ALWAYS visible when debug_view=True, independent from show_panels)
    if debug_view and all_detections:
        colors = {0: (255, 255, 0), 1: (255, 128, 0), 2: (0, 255, 0), 3: (0, 0, 255)}
        for cls, det_data in all_detections.items():
            pos = det_data['pos']
            bbox = det_data.get('bbox')  # (x1, y1, x2, y2)
            conf = det_data['conf']
            class_name = CLASS_NAMES.get(cls, f"Class_{cls}")
            color = colors.get(cls, (255, 255, 255))

            # Draw bounding box
            if bbox:
                x1, y1, x2, y2 = bbox
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Draw center point (larger circle for debug)
            cv2.circle(frame, pos, 15, color, 2)  # Hollow circle

            # Draw label with confidence (above bounding box if available, else near center)
            label = f"{class_name} {conf:.2f}"
            label_pos = (bbox[0], bbox[1] - 10) if bbox else (pos[0] + 20, pos[1])
            cv2.putText(frame, label, label_pos,
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Note: Gates are drawn by draw_gates_overlay() and draw_marker_mode_overlay()
    # No need to draw them here again

    # Early return if panels hidden (P key pressed) - calculation continues in background
    # Gate markers also hidden when panels are off
    if not show_panels:
        return

    # All panels below (can be toggled with P key)
    # Controls panel (IN CIMA - always first)
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 5), (800, 35), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.putText(frame, "Q=Quit | SPACE=Pause | D=Debug | P=Panel | Y=YOLO | M=Marker | S=Save | E=Export | R=Reset", (10, 25),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # Info panel with background
    overlay = frame.copy()
    info_text = "Dual Consist YOLO Tracking"
    cv2.rectangle(overlay, (5, 45), (430, 75), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.putText(frame, info_text, (10, 65),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # All Locomotives Detected Panel
    locos_y = 85
    num_classes = len(CLASS_NAMES)
    locos_height = locos_y + 20 + (num_classes * 20) + 10
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, locos_y), (430, locos_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.putText(frame, "All Locomotives Detected:", (10, locos_y + 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # Show detection status for all YOLO classes
    y_pos = locos_y + 40
    for class_id in sorted(CLASS_NAMES.keys()):
        class_name = CLASS_NAMES.get(class_id, f"Class_{class_id}")
        detected = class_id in all_detections if all_detections else False

        if detected:
            conf = all_detections[class_id]['conf']
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

    # Gate Timing Panels (dynamic for all consists with 2+ gates)
    gate_timing_y = locos_height + 10
    y_offset = gate_timing_y

    for consist_id in sorted(consist_data.keys()):
        config = tracker.consist_config[consist_id]
        consist_state = tracker.consist_data[consist_id]
        gate_ids = config['gate_ids']

        # Skip consists without 2 gates configured
        if len(gate_ids) < 2:
            continue

        # Calculate panel height (header + timestamps + delta_t)
        panel_height_gate = 20 + 20 + (len(gate_ids) * 20) + 20 + 10
        overlay = frame.copy()
        cv2.rectangle(overlay, (5, y_offset), (430, y_offset + panel_height_gate), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

        # Panel title
        cv2.putText(frame, f"Gate Timing (Consist {consist_id} - Cross-gate):", (10, y_offset + 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # Last crossing timestamps header
        cv2.putText(frame, "Last crossing timestamps:", (15, y_offset + 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        # Show timestamps for lead and rear at each gate
        lead_addr = config['lead_address']
        rear_addr = config['rear_address']
        colors_consist = CONSIST_COLORS.get(consist_id, {'lead': (255, 255, 255), 'rear': (128, 128, 128)})

        y_timestamp = y_offset + 60

        # Lead loco timestamps (all gates) - use gate_timestamps['lead'][gate_id]
        gate_timestamps_lead = []
        for gate_id in gate_ids:
            ts = consist_state['gate_timestamps']['lead'].get(gate_id)
            ts_str = time.strftime("%H:%M:%S", time.localtime(ts)) if ts else "---"
            gate_timestamps_lead.append(f"G{gate_id}={ts_str}")

        lead_line = f"Loco {lead_addr}: " + "  ".join(gate_timestamps_lead)
        cv2.putText(frame, lead_line, (25, y_timestamp),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.35, colors_consist['lead'], 1)
        y_timestamp += 20

        # Rear loco timestamps (all gates) - use gate_timestamps['rear'][gate_id]
        if rear_addr:
            gate_timestamps_rear = []
            for gate_id in gate_ids:
                ts = consist_state['gate_timestamps']['rear'].get(gate_id)
                ts_str = time.strftime("%H:%M:%S", time.localtime(ts)) if ts else "---"
                gate_timestamps_rear.append(f"G{gate_id}={ts_str}")

            rear_line = f"Loco {rear_addr}: " + "  ".join(gate_timestamps_rear)
            cv2.putText(frame, rear_line, (25, y_timestamp),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, colors_consist['rear'], 1)
            y_timestamp += 20

        # Cross-gate Δt
        delta_t = consist_state['delta_t']
        if delta_t is not None:
            dt_abs = abs(delta_t)
            if dt_abs < tracker.threshold_normal:
                color = (0, 255, 0)  # Green
                status = "SYNCED"
            elif dt_abs < tracker.threshold_warning:
                color = (0, 255, 255)  # Yellow
                status = "WARNING"
            else:
                color = (0, 0, 255)  # Red
                status = "CRITICAL"

            cv2.putText(frame, f"Dt (cross-gate) = {delta_t:+.3f}s  {status}", (15, y_timestamp),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
        else:
            cv2.putText(frame, "Dt (cross-gate) = --- (waiting for crossing)", (15, y_timestamp),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        y_offset += panel_height_gate + 10


def track_consist(model_path: str):
    """Main tracking loop."""
    # Load RTSP URL from camera config (using shared rtsp_handler module)
    rtsp_url = load_camera_config()

    print("🎥 Starting YOLO Tracking...")
    print()

    # Connect to camera with optimal buffering
    cap = setup_rtsp_stream(rtsp_url, description="YOLO tracking stream")
    if not cap:
        print("❌ Failed to connect to camera")
        return

    # Get resolution
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to read first frame")
        return

    actual_height, actual_width = frame.shape[:2]
    print(f"📐 Stream resolution: {actual_width}x{actual_height}")

    # Initialize tracker
    tracker = YOLOTracker(model_path)
    print(f"⏱️  Gate timing detection: {len(tracker.consist_config)} consist(s) configured")
    print()

    # Create window
    window_name = "YOLO Consist Tracking - Press Q to quit"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, actual_width, actual_height)

    # Initialize marker state
    marker_state = MarkerState()

    # Mouse callback for marker mode
    def mouse_callback(event, x, y, flags, param):
        """Handle mouse events for gate editing."""
        if not marker_state.enabled:
            return

        if event == cv2.EVENT_LBUTTONDOWN:
            # Check if clicking on existing gate
            gate_id = marker_state.find_gate_at(x, y)
            if gate_id:
                # Select gate for editing (loads into current_gate)
                marker_state.select_gate(gate_id)
            elif not marker_state.current_gate:
                # Place new gate if none selected
                marker_state.place_gate(x, y)
                print(f"📍 New gate at ({x}, {y}) - size: 100x100px")

            # If we now have a current_gate, start dragging it
            if marker_state.current_gate:
                # Calculate offset from current_gate center
                cx, cy = marker_state.current_gate['center_x'], marker_state.current_gate['center_y']
                marker_state.dragging = True
                marker_state.drag_offset_x = cx - x
                marker_state.drag_offset_y = cy - y

        elif event == cv2.EVENT_MOUSEMOVE:
            # Update drag position (move current_gate)
            if marker_state.dragging and marker_state.current_gate:
                marker_state.current_gate['center_x'] = x + marker_state.drag_offset_x
                marker_state.current_gate['center_y'] = y + marker_state.drag_offset_y

        elif event == cv2.EVENT_LBUTTONUP:
            # Stop dragging
            if marker_state.dragging:
                marker_state.dragging = False
                print("✓ Gate moved")

    cv2.setMouseCallback(window_name, mouse_callback)

    # State
    paused = False
    debug_view = False
    show_panels = True
    tracking_enabled = True  # Toggle YOLO tracking overlay (Y key)
    frame_count = 0
    frame_clean = None  # Clean copy of frame for redrawing when paused
    frame_display = None  # Display frame with overlay
    track_data = None
    pause_feedback_text = None  # Text to show for pause toggle feedback
    pause_feedback_time = 0  # Timestamp when pause was toggled

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

            # Save clean copy for redrawing when paused
            frame_clean = frame.copy()

            frame_count += 1

            # Track BOTH consists (skip YOLO inference if tracking disabled for faster editing)
            if tracking_enabled:
                track_data = tracker.update(frame)
                all_detections = track_data['detections']
            # else: keep last track_data (or empty if none)

            # Log detection state changes (immediate) - COMMENTED OUT for cleaner logs
            current_detection_state = {}
            for class_id in range(4):  # Classes 0-3
                detected = class_id in all_detections
                if detected:
                    conf = all_detections[class_id]['conf']
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
                #         conf = all_detections[class_id]['conf']
                #         print(f"✅ {class_name} detected (confidence: {conf:.2f})")
                #     else:
                #         if class_id in all_detections:
                #             conf = all_detections[class_id]['conf']
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
                        conf = all_detections[class_id]['conf']
                        reliable = conf >= CONFIDENCE_THRESHOLD
                        if reliable:
                            print(f"   {class_name}: ✓ RELIABLE ({conf:.2f})")
                        else:
                            print(f"   {class_name}: ⚠ LOW CONFIDENCE ({conf:.2f})")
                    else:
                        print(f"   {class_name}: ✗ NOT DETECTED")
                print()

        # Draw overlay and display (ALWAYS, even when paused)
        if frame_clean is not None:
            # Use a fresh copy of the clean frame to redraw overlay
            frame_display = frame_clean.copy()

            # Draw gates ALWAYS (independent from tracking state)
            draw_gates_overlay(frame_display, tracker)

            # Draw Marker Mode overlay ALWAYS (independent from tracking state)
            draw_marker_mode_overlay(frame_display, marker_state)

            # Draw tracking overlay only if tracking enabled and data available
            if tracking_enabled and track_data is not None:
                draw_overlay(frame_display, tracker, track_data, debug_view, show_panels, frame_count, marker_state, tracking_enabled)

            # Draw pause feedback banner (2 seconds after toggle)
            if pause_feedback_text and (time.time() - pause_feedback_time) < 2.0:
                h, w = frame_display.shape[:2]
                # Semi-transparent background
                overlay = frame_display.copy()
                cv2.rectangle(overlay, (w//2 - 150, h//2 - 40), (w//2 + 150, h//2 + 40), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.7, frame_display, 0.3, 0, frame_display)
                # Text (use SIMPLEX with high thickness for bold effect)
                font_scale = 1.5
                thickness = 4
                color = (255, 255, 255)  # White
                text_size = cv2.getTextSize(pause_feedback_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
                text_x = w//2 - text_size[0]//2
                text_y = h//2 + text_size[1]//2
                cv2.putText(frame_display, pause_feedback_text, (text_x, text_y),
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

            # Downscale for display if HD (save rendering performance)
            # BUT: skip if Marker Mode enabled (mouse coordinates must match frame size)
            display_height, display_width = frame_display.shape[:2]
            if display_width > 1280 and not marker_state.enabled:  # Only downscale when NOT editing
                frame_display = cv2.resize(frame_display, (1280, 720), interpolation=cv2.INTER_AREA)

            cv2.imshow(window_name, frame_display)

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
                # Otherwise: reset tracking counters for ALL consists
                print("🔄 Reset tracking counters (gate crossings)")
                for consist_id, consist in tracker.consist_data.items():
                    consist['gate_crossing_count'] = 0
                    consist['last_delta_t_time'] = 0
                frame_count = 0  # Reset frame count too
        elif key == ord('d') or key == ord('D'):
            debug_view = not debug_view
            print(f"🐛 Debug view: {'ON' if debug_view else 'OFF'}")
        elif key == ord('p') or key == ord('P'):
            show_panels = not show_panels
            print(f"📋 All panels: {'ON' if show_panels else 'OFF (markers only)'}")
        elif key == ord('y') or key == ord('Y'):
            tracking_enabled = not tracking_enabled
            # When YOLO disabled, pause video for fast gate editing
            paused = not tracking_enabled
            print(f"🎯 YOLO Inference: {'ON' if tracking_enabled else 'OFF (fast editing mode - video paused)'}")
        elif key == ord('s') or key == ord('S'):
            # In marker mode, S = save ALL gates to JSON config
            if marker_state.enabled:
                print("\n⚠️  SAVING all gates to JSON config...")
                marker_state.save_to_config()
            else:
                # Save snapshot (only when NOT in marker mode)
                if frame_display is not None:
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    filename = f"tracking_snapshot_{timestamp}.jpg"
                    script_dir = Path(__file__).parent
                    filepath = script_dir / filename
                    cv2.imwrite(str(filepath), frame_display)
                    print(f"📸 Snapshot saved: {filepath}")
        elif key == ord(' '):
            paused = not paused
            pause_feedback_text = "PAUSED" if paused else "RESUMED"
            pause_feedback_time = time.time()
            print(f"{'⏸️  Paused' if paused else '▶️  Resumed'}")
        # Marker mode controls
        elif key == ord('m') or key == ord('M'):
            enabled = marker_state.toggle()
            print(f"🎯 Marker mode: {'ON' if enabled else 'OFF'}")
        elif key == 0 or key == 82:  # Arrow UP (Mac: 0, Linux: 82)
            if marker_state.current_gate:
                marker_state.adjust_height(10)
                h = marker_state.current_gate['height']
                print(f"^ Height increased: {h}px")
        elif key == 1 or key == 84:  # Arrow DOWN (Mac: 1, Linux: 84)
            if marker_state.current_gate:
                marker_state.adjust_height(-10)
                h = marker_state.current_gate['height']
                print(f"v Height decreased: {h}px")
        elif key == 2 or key == 81:  # Arrow LEFT (Mac: 2, Linux: 81)
            if marker_state.current_gate:
                marker_state.adjust_width(-10)
                w = marker_state.current_gate['width']
                print(f"< Width decreased: {w}px")
        elif key == 3 or key == 83:  # Arrow RIGHT (Mac: 3, Linux: 83)
            if marker_state.current_gate:
                marker_state.adjust_width(10)
                w = marker_state.current_gate['width']
                print(f"> Width increased: {w}px")
        elif key == 13:  # ENTER key
            if marker_state.current_gate:
                marker_state.save_current_gate(tracker)
        elif key == ord('c') or key == ord('C'):
            if marker_state.enabled:
                # Clear current gate being positioned (not saved gates)
                marker_state.clear_current()
        elif key == ord('e') or key == ord('E'):
            marker_state.export_gates()

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()

    # Export gates if any were saved
    if marker_state.config['gates']:
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

    # Gate timing statistics (dynamic for all consists with 2+ gates)
    print("🚪 GATE TIMING DETECTION")
    print("-" * 60)

    for consist_id in sorted(tracker.consist_data.keys()):
        config = tracker.consist_config[consist_id]
        consist = tracker.consist_data[consist_id]
        gate_ids = config['gate_ids']

        # Skip consists without 2 gates configured
        if len(gate_ids) < 2:
            continue

        print(f"\nConsist {consist_id} - {config['name']} (Cross-Gate):")
        print(f"   Gate crossings detected: {consist['gate_crossing_count']}")

        delta_t = consist['delta_t']
        if delta_t is not None:
            # Calculate status based on thresholds
            dt_abs = abs(delta_t)
            if dt_abs < tracker.threshold_normal:
                status = "🟢 SYNCED"
            elif dt_abs < tracker.threshold_warning:
                status = "🟡 WARNING"
            else:
                status = "🔴 CRITICAL DESYNC"

            print(f"   Last Δt measured: {delta_t:+.3f}s  {status}")
            print(f"   Crossing type: {consist['delta_t_type']}")
            print()
            print("   Δt Interpretation:")
            lead_addr = config['lead_address']
            rear_addr = config['rear_address']
            if delta_t > 0:
                print(f"   → Loco {lead_addr} (lead) passing first - running faster")
            else:
                print(f"   → Loco {rear_addr} (rear) passing first - lead running slower")
        else:
            print("   Last Δt: --- (no crossing detected)")
            print("   ⚠️  Locomotives not detected passing through gates")

    print()
    print("   Thresholds:")
    print(f"   🟢 |Δt| < {tracker.threshold_normal}s = SYNCED")
    print(f"   🟡 |Δt| {tracker.threshold_normal}-{tracker.threshold_warning}s = WARNING")
    print(f"   🔴 |Δt| > {tracker.threshold_warning}s = CRITICAL")
    print()
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="YOLO-based tracking for multiple consists (config-driven)"
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

    track_consist(str(model_path))


if __name__ == '__main__':
    main()
