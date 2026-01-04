#!/usr/bin/env python3
"""
YOLO-based tracking for multiple consists (config-driven).

Dynamically tracks N consists based on config.json:
    - Consist 10 (Tracciato Interno): Gr.675 017 + D645 014
    - Consist 11 (Tracciato Esterno): E656 239 + E444 056
    - Additional consists can be added via config

Uses custom trained YOLOv8 model for real-time locomotive detection.

Perspective Correction:
    - Display: original camera view (oblique perspective)
    - Distance calculations: perspective-corrected frame (6px/cm uniform scale)
    - Coordinates transformed in background for accurate measurements

Usage:
    python track_consist_yolo.py [--model best.pt]

    Camera credentials are loaded from backend/camera_config.json
    (see backend/README_CAMERA.md for setup)

Controls:
    - Q: Quit
    - SPACE: Pause/Resume video
    - D: Toggle debug view (show bounding boxes with confidence)
    - P: Toggle info panels (clean view, gates+markers only)
    - Y: Toggle YOLO inference (disable = pause video for fast gate editing)
    - M: Toggle Marker Mode (gate positioning/editing)
    - S: Save gate positions to config.json (Marker Mode only)
    - R: Reset distance history (both consists)

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

# Camera settings
CAMERA_IP = "192.168.1.4"
CAMERA_PORT = 554
STREAM = "stream2"  # 720P stream (better for real-time)

# Detection settings
CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence for detection
DISTANCE_HISTORY_SIZE = 10000  # Number of distance measurements to store (large for baseline testing)

# Config paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Add backend to path for config_loader import
backend_dir = PROJECT_ROOT / 'backend'
sys.path.insert(0, str(backend_dir))

from config_loader import load_config, save_config as save_config_central, get_config_path

# === CONFIGURATION ===
# load_config() now imported from config_loader (supports config.local.json override)

# Class IDs (from Roboflow training - BiancAlice v3)
# Roboflow orders alphabetically by class name
# NOTE: These are YOLO class IDs, not DCC addresses!
CLASS_NAMES = {
    0: "1_Gr675_017",   # DCC address 1 (Consist 10 lead)
    1: "5_D645_014",    # DCC address 5 (Consist 10 rear)
    2: "7_E656_239",    # DCC address 7 (Consist 11 lead)
    3: "8_E444_056"     # DCC address 8 (Consist 11 rear)
}

# Build mapping: DCC address → YOLO class ID (reverse lookup)
# This allows config.json to reference DCC addresses (7, 8) and map to YOLO classes (2, 3)
DCC_TO_YOLO_CLASS = {}
for yolo_class_id, class_name in CLASS_NAMES.items():
    dcc_address = int(class_name.split('_')[0])  # Extract "7" from "7_E656_239"
    DCC_TO_YOLO_CLASS[dcc_address] = yolo_class_id

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

    def save_current_gate(self):
        """Save current gate to config (new or update existing)."""
        if self.current_gate:
            if self.editing_gate_id is not None:
                # Update existing gate
                gate = next((g for g in self.config['gates'] if g['id'] == self.editing_gate_id), None)
                if gate:
                    gate['center'] = [self.current_gate['center_x'], self.current_gate['center_y']]
                    gate['width'] = self.current_gate['width']
                    gate['height'] = self.current_gate['height']
                    gate['angle'] = self.current_gate['angle']
                    print(f"✅ Gate {self.editing_gate_id} updated")
            else:
                # Add new gate
                gate_id = get_next_gate_id(self.config)
                new_gate = {
                    'id': gate_id,
                    'name': f"Gate {gate_id}",
                    'center': [self.current_gate['center_x'], self.current_gate['center_y']],
                    'width': self.current_gate['width'],
                    'height': self.current_gate['height'],
                    'angle': self.current_gate['angle'],
                    'color': [255, 255, 0],  # Yellow (BGR)
                    'notes': "Added in marker mode"
                }
                self.config['gates'].append(new_gate)
                print(f"✅ Gate {gate_id} saved (total: {len(self.config['gates'])})")

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
            print(f"💾 Saved {len(self.config['gates'])} gates to {CONFIG_FILE.name}")
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


def gate_json_to_dict(gate_json):
    """
    Convert gate from JSON format to is_point_in_gate() format.

    Args:
        gate_json: dict with 'center' [x, y], 'width', 'height', 'angle'

    Returns:
        dict with 'center_x', 'center_y', 'width', 'height', 'angle'
    """
    return {
        'center_x': gate_json['center'][0],
        'center_y': gate_json['center'][1],
        'width': gate_json['width'],
        'height': gate_json['height'],
        'angle': gate_json['angle']
    }


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
    """
    YOLO-based locomotive tracker with cross-gate timing detection.

    NOMENCLATURE (CRITICAL):
    - lead/rear = JMRI consist roles (NOT physical position!)
      - lead: receives function commands (F0-F28)
      - rear: "succube" loco (follows lead for movement)
    - reference/adjust = Speed matching roles (gate_config.json)
      - reference: stable decoder, NEVER modified
      - adjust: unstable decoder, ALWAYS compensated

    CONSIST 11 MAPPING:
    - Lead JMRI (loco 7, E656_239) = Adjust (Hornby unstable)
    - Rear JMRI (loco 8, E444_056) = Reference (ESU stable)

    CROSS-GATE TIMING STRATEGY:
    - 2 gates per consist (both locos pass through BOTH gates)
    - Δt = timestamp_lead - timestamp_rear
    - Δt > 0: lead passes first (adjust too fast) → slow down
    - Δt < 0: rear passes first (adjust too slow) → speed up
    - Cross-validation: |Δt₁ - Δt₂| < threshold confirms drift

    FRESH TIMESTAMPS LOGIC:
    - self.last_delta_t_time = max(timestamp1, timestamp2)
    - Ensures BOTH timestamps are fresh (> last_delta_t_time)
    - Prevents spurious Δt from stale timestamps

    NOTE: Currently hardcoded for Consist 11 only.
    Future refactoring (Phase 4C) will support multiple consists dynamically.
    """

    def __init__(self, model_path: str):
        """Initialize tracker with YOLO model."""
        print(f"🤖 Loading YOLO model: {model_path}")
        self.model = YOLO(model_path)

        # Load gates and thresholds from config
        config = load_config()
        self.gates = {}
        for gate in config['gates']:
            self.gates[gate['id']] = gate_json_to_dict(gate)
        print(f"🚪 Loaded {len(self.gates)} gates from config")

        # Load timing thresholds
        tracking_config = config.get('tracking', {})
        thresholds = tracking_config.get('timing_thresholds', {'normal': 1.0, 'warning': 2.0})
        self.threshold_normal = thresholds.get('normal', 1.0)
        self.threshold_warning = thresholds.get('warning', 2.0)
        print(f"⏱️  Timing thresholds: SYNCED < {self.threshold_normal}s, WARNING < {self.threshold_warning}s")

        # Load Δt sanity check threshold (ignore outliers from video lag)
        self.delta_t_max_threshold = thresholds.get('max_delta_t', 15.0)
        print(f"⚠️  Δt sanity check: ignore |Δt| > {self.delta_t_max_threshold}s")

        # === PHASE 5: CONFIG-DRIVEN MULTI-CONSIST SUPPORT ===
        # Load consists from config.json
        consists = config.get('consists', {})

        # Build consist_config (mapping consist_id → addresses + YOLO class IDs + gates)
        self.consist_config = {}
        for consist_key, consist_info in consists.items():

            consist_id = int(consist_key)  # "11" → 11
            lead_addr = consist_info['lead_address']
            rear_addr = consist_info.get('rear_address')  # Can be null for single locos
            gate_ids = consist_info.get('gate_ids', [])

            # Map DCC addresses to YOLO class IDs
            lead_yolo_class = DCC_TO_YOLO_CLASS.get(lead_addr)
            rear_yolo_class = DCC_TO_YOLO_CLASS.get(rear_addr) if rear_addr else None

            if lead_yolo_class is None:
                print(f"⚠️  Warning: Lead address {lead_addr} not found in YOLO model classes")
                continue

            self.consist_config[consist_id] = {
                'lead_address': lead_addr,
                'rear_address': rear_addr,
                'lead_yolo_class': lead_yolo_class,
                'rear_yolo_class': rear_yolo_class,
                'gate_ids': gate_ids,
                'name': consist_info.get('name', f'Consist {consist_id}')
            }

        print(f"🚂 Loaded {len(self.consist_config)} consists from config:")
        for consist_id, cfg in self.consist_config.items():
            gates_str = f" → gates {cfg['gate_ids']}" if cfg['gate_ids'] else ""
            print(f"   Consist {consist_id}: lead={cfg['lead_address']}, rear={cfg['rear_address']}{gates_str}")

        # Initialize consist_data (dynamic state for all consists)
        self.consist_data = {}
        for consist_id in self.consist_config.keys():
            gate_ids = self.consist_config[consist_id]['gate_ids']

            # Initialize gate timing state (2 gates per consist)
            gate_state = {}
            for gate_id in gate_ids:
                gate_state[gate_id] = {
                    'lead_timestamp': None,
                    'rear_timestamp': None,
                    'lead_in_gate': False,
                    'rear_in_gate': False
                }

            self.consist_data[consist_id] = {
                'lead_pos': None,
                'rear_pos': None,
                'lead_conf': None,
                'rear_conf': None,
                'visible_together_count': 0,
                'gate_state': gate_state,  # Per-gate timing state
                'delta_t': None,           # Latest Δt value
                'delta_t_type': None,      # e.g. "L7G1-L8G2"
                'gate_crossing_count': 0,  # Total Δt calculations for this consist
                'last_delta_t_time': 0,    # Last Δt calc time (fresh timestamps check)
                # Spam reduction for ignored Δt warnings
                'last_ignored_delta_t1': None,
                'last_ignored_delta_t1_time': 0,
                'last_ignored_delta_t2': None,
                'last_ignored_delta_t2_time': 0
            }

        print("✅ YOLO model loaded (multi-consist tracking ready)")

    def calculate_delta_t_centralized(self):
        """
        Centralized Δt calculation for ALL consists with 2 cross-gate checks each.

        Called once per frame after all gate detection points updated.
        Iterates over all consists with 2+ gates configured.
        """
        for consist_id, consist in self.consist_data.items():
            gate_ids = self.consist_config[consist_id]['gate_ids']

            # Skip consists without 2 gates configured
            if len(gate_ids) < 2:
                continue

            gate1_id, gate2_id = gate_ids[0], gate_ids[1]
            gate1_state = consist['gate_state'][gate1_id]
            gate2_state = consist['gate_state'][gate2_id]

            lead_addr = self.consist_config[consist_id]['lead_address']
            rear_addr = self.consist_config[consist_id]['rear_address']

            # Check 1: Δt₁ = lead@G1 - rear@G2 (cross-gate timing)
            if (gate1_state['lead_timestamp'] is not None and
                gate2_state['rear_timestamp'] is not None):

                max_t1 = max(gate1_state['lead_timestamp'], gate2_state['rear_timestamp'])

                # Calculate only if BOTH timestamps are fresh (prevents mixing laps)
                if (max_t1 > consist['last_delta_t_time'] and
                    gate1_state['lead_timestamp'] > consist['last_delta_t_time'] and
                    gate2_state['rear_timestamp'] > consist['last_delta_t_time']):
                    delta_t1 = gate1_state['lead_timestamp'] - gate2_state['rear_timestamp']

                    # Sanity check: ignore impossible Δt values (outliers from video lag)
                    if abs(delta_t1) > self.delta_t_max_threshold:
                        # Throttle spam: only print if value changed significantly or 5s passed
                        current_time = time.time()
                        should_print = (
                            consist['last_ignored_delta_t1'] is None or
                            abs(delta_t1 - consist['last_ignored_delta_t1']) > 1.0 or
                            (current_time - consist['last_ignored_delta_t1_time']) > 5.0
                        )
                        if should_print:
                            print(f"⚠️  C{consist_id} Ignored Δt₁ = {delta_t1:+.3f}s (|Δt| > {self.delta_t_max_threshold}s)")
                            consist['last_ignored_delta_t1'] = delta_t1
                            consist['last_ignored_delta_t1_time'] = current_time
                    else:
                        consist['delta_t'] = delta_t1
                        consist['delta_t_type'] = f"L{lead_addr}G{gate1_id}-L{rear_addr}G{gate2_id}"
                        consist['gate_crossing_count'] += 1
                        consist['last_delta_t_time'] = max_t1
                        print(f"🚪 C{consist_id} Cross-gate: {consist['delta_t_type']} = Δt = {consist['delta_t']:+.3f}s")
                        continue  # Calculated, move to next consist

            # Check 2: Δt₂ = lead@G2 - rear@G1 (cross-gate timing)
            if (gate2_state['lead_timestamp'] is not None and
                gate1_state['rear_timestamp'] is not None):

                max_t2 = max(gate2_state['lead_timestamp'], gate1_state['rear_timestamp'])

                # Calculate only if BOTH timestamps are fresh (prevents mixing laps)
                if (max_t2 > consist['last_delta_t_time'] and
                    gate2_state['lead_timestamp'] > consist['last_delta_t_time'] and
                    gate1_state['rear_timestamp'] > consist['last_delta_t_time']):
                    delta_t2 = gate2_state['lead_timestamp'] - gate1_state['rear_timestamp']

                    # Sanity check: ignore impossible Δt values (outliers from video lag)
                    if abs(delta_t2) > self.delta_t_max_threshold:
                        # Throttle spam: only print if value changed significantly or 5s passed
                        current_time = time.time()
                        should_print = (
                            consist['last_ignored_delta_t2'] is None or
                            abs(delta_t2 - consist['last_ignored_delta_t2']) > 1.0 or
                            (current_time - consist['last_ignored_delta_t2_time']) > 5.0
                        )
                        if should_print:
                            print(f"⚠️  C{consist_id} Ignored Δt₂ = {delta_t2:+.3f}s (|Δt| > {self.delta_t_max_threshold}s)")
                            consist['last_ignored_delta_t2'] = delta_t2
                            consist['last_ignored_delta_t2_time'] = current_time
                    else:
                        consist['delta_t'] = delta_t2
                        consist['delta_t_type'] = f"L{lead_addr}G{gate2_id}-L{rear_addr}G{gate1_id}"
                        consist['gate_crossing_count'] += 1
                        consist['last_delta_t_time'] = max_t2
                        print(f"🚪 C{consist_id} Cross-gate: {consist['delta_t_type']} = Δt = {consist['delta_t']:+.3f}s")

    def detect_locomotives(self, frame):
        """
        Detect all locomotives using YOLO.

        Returns:
            detections: dict {class_id: (pos, conf)}
            results: YOLO results object
        """
        # Run inference with rectangular image size (matches training)
        # (640, 1152) = 16:9 aspect ratio, no letterboxing waste
        results = self.model(frame, conf=CONFIDENCE_THRESHOLD, imgsz=(640, 1152), verbose=False)

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
        Update tracking with new frame for ALL consists dynamically.

        Returns:
            Dictionary with consist data and shared detection info
        """
        detections, results = self.detect_locomotives(frame)

        # === DYNAMIC CONSIST TRACKING ===
        # Iterate over all configured consists
        for consist_id, consist in self.consist_data.items():
            config = self.consist_config[consist_id]

            # Get YOLO class IDs from config
            lead_yolo_class = config['lead_yolo_class']
            rear_yolo_class = config['rear_yolo_class']

            # Get lead detection
            lead_data = detections.get(lead_yolo_class)
            consist['lead_pos'] = lead_data[0] if lead_data else None
            consist['lead_conf'] = lead_data[1] if lead_data else 0.0

            # Get rear detection (if consist has rear locomotive)
            if rear_yolo_class is not None:
                rear_data = detections.get(rear_yolo_class)
                consist['rear_pos'] = rear_data[0] if rear_data else None
                consist['rear_conf'] = rear_data[1] if rear_data else 0.0
            else:
                # Single locomotive (no rear)
                consist['rear_pos'] = None
                consist['rear_conf'] = 0.0

            # Track visibility (both locomotives visible together)
            if consist['lead_pos'] and consist['rear_pos']:
                consist['visible_together_count'] += 1

            # === GATE TIMING DETECTION ===
            # Only if consist has 2+ gates configured
            gate_ids = config['gate_ids']
            if len(gate_ids) >= 2:
                # Iterate over all gates for this consist
                for gate_id in gate_ids:
                    gate_state = consist['gate_state'][gate_id]
                    gate = self.gates.get(gate_id)

                    if gate is None:
                        continue

                    # Lead locomotive gate detection (rising edge)
                    lead_in_gate = is_point_in_gate(consist['lead_pos'], gate)
                    if lead_in_gate and not gate_state['lead_in_gate']:
                        # Rising edge: loco just entered gate
                        gate_state['lead_timestamp'] = time.time()
                        gate_state['lead_in_gate'] = True
                    elif not lead_in_gate:
                        gate_state['lead_in_gate'] = False

                    # Rear locomotive gate detection (rising edge)
                    if consist['rear_pos'] is not None:
                        rear_in_gate = is_point_in_gate(consist['rear_pos'], gate)
                        if rear_in_gate and not gate_state['rear_in_gate']:
                            # Rising edge: loco just entered gate
                            gate_state['rear_timestamp'] = time.time()
                            gate_state['rear_in_gate'] = True
                        elif not rear_in_gate:
                            gate_state['rear_in_gate'] = False

        # Centralized Δt calculation (called once per frame after all gate detection points)
        self.calculate_delta_t_centralized()

        # Build return dictionary with all consist data
        consist_results = {}
        for consist_id, consist in self.consist_data.items():
            consist_results[consist_id] = {
                'lead_pos': consist['lead_pos'],
                'rear_pos': consist['rear_pos'],
                'lead_conf': consist['lead_conf'],
                'rear_conf': consist['rear_conf'],
                'delta_t': consist['delta_t'],
                'delta_t_type': consist['delta_t_type']
            }

        return {
            'consist_data': consist_results,
            'detections': detections,
            'results': results
        }

    def get_visibility_stats(self, consist_id, total_frames):
        """Get visibility statistics for specified consist ID."""
        if consist_id in self.consist_data:
            count = self.consist_data[consist_id]['visible_together_count']
            percentage = (count / total_frames * 100) if total_frames > 0 else 0
            return count, percentage
        return 0, 0.0


def draw_gates_overlay(frame, tracker):
    """Draw timing gates on frame (ALWAYS visible, independent from tracking)."""
    # Collect all gate IDs from all consists
    all_gate_ids = set()
    for config in tracker.consist_config.values():
        all_gate_ids.update(config['gate_ids'])

    # Gate colors (cycling through colors for different gates)
    GATE_COLORS = [
        (255, 255, 0),   # Yellow (Gate 1)
        (255, 128, 0),   # Orange (Gate 2)
        (0, 255, 255),   # Cyan (Gate 3)
        (255, 0, 255),   # Magenta (Gate 4)
    ]

    for gate_id in sorted(all_gate_ids):
        if gate_id not in tracker.gates:
            continue

        gate = tracker.gates[gate_id]
        gate_points = get_rotated_rect_points(
            gate['center_x'], gate['center_y'],
            gate['width'], gate['height'],
            gate['angle']
        )
        color = GATE_COLORS[(gate_id - 1) % len(GATE_COLORS)]
        cv2.polylines(frame, [gate_points], True, color, 2)
        cv2.putText(frame, f"G{gate_id}", (gate['center_x'] - 10, gate['center_y'] + 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    return frame


def draw_marker_mode_overlay(frame, marker_state):
    """Draw Marker Mode overlay (ALWAYS visible when marker_state.enabled, independent from tracking)."""
    if not marker_state:
        return frame

    # Colors for marker mode
    GATE_COLOR = (0, 255, 255)  # Cyan for current gate being edited
    GATE_SAVED_COLOR = (0, 255, 0)  # Green for saved gates

    # Draw saved gates (green) - skip the one being edited
    for gate in marker_state.config['gates']:
        # Skip gate if it's currently being edited
        if marker_state.editing_gate_id == gate['id']:
            continue

        cx, cy = gate['center'][0], gate['center'][1]
        w, h = gate['width'], gate['height']
        angle = gate['angle']

        # Get rotated rectangle points
        points = get_rotated_rect_points(cx, cy, w, h, angle)
        cv2.polylines(frame, [points], True, GATE_SAVED_COLOR, 2)

        # Draw center crosshair
        cv2.line(frame, (cx - 10, cy), (cx + 10, cy), GATE_SAVED_COLOR, 1)
        cv2.line(frame, (cx, cy - 10), (cx, cy + 10), GATE_SAVED_COLOR, 1)

        # Draw gate ID label
        label = f"G{gate['id']}"
        cv2.putText(frame, label, (cx - 15, cy - h//2 - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, GATE_SAVED_COLOR, 1)

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

    consist_data = track_data['consist_data']
    all_detections = track_data['detections']
    results = track_data['results']

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

        if consist['lead_pos'] and consist['rear_pos']:
            cv2.line(frame, consist['lead_pos'], consist['rear_pos'], colors['line'], 2)

    # Draw gate markers (always visible, even if panels hidden)
    if marker_state:
        # Draw saved gates (green) - skip the one being edited
        for gate in marker_state.config['gates']:
            # Skip gate if it's currently being edited
            if marker_state.editing_gate_id == gate['id']:
                continue

            cx, cy = gate['center'][0], gate['center'][1]
            w, h = gate['width'], gate['height']
            angle = gate['angle']

            # Get rotated rectangle points
            points = get_rotated_rect_points(cx, cy, w, h, angle)
            cv2.polylines(frame, [points], True, GATE_SAVED_COLOR, 2)

            # Draw center crosshair
            cv2.line(frame, (cx - 10, cy), (cx + 10, cy), GATE_SAVED_COLOR, 1)
            cv2.line(frame, (cx, cy - 10), (cx, cy + 10), GATE_SAVED_COLOR, 1)

            # Draw gate ID label
            label = f"G{gate['id']}"
            cv2.putText(frame, label, (cx - 15, cy - h//2 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, GATE_SAVED_COLOR, 1)

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
    cv2.rectangle(overlay, (5, 45), (400, 75), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.putText(frame, info_text, (10, 65),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # Co-Visibility Stats Panel (dynamic for all consists)
    overlay = frame.copy()
    panel_height = 80 + 25 * len(consist_data) + 10
    cv2.rectangle(overlay, (5, 80), (550, panel_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.putText(frame, "Co-Visibility (Lead + Rear together):", (10, 100),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # Dynamic consist stats (iterate over all consists)
    y_pos = 125
    for consist_id in sorted(consist_data.keys()):
        consist = consist_data[consist_id]
        consist_state = tracker.consist_data[consist_id]

        count = consist_state['visible_together_count']
        pct = (count / total_frames * 100) if total_frames > 0 else 0
        status = "YES" if (consist['lead_pos'] and consist['rear_pos']) else "NO"

        colors = CONSIST_COLORS.get(consist_id, {'line': (255, 255, 255)})
        cv2.putText(frame, f"C{consist_id}: {status}  {count} frames ({pct:.1f}%)", (20, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, colors['line'], 1)
        y_pos += 25

    # All Locomotives Detected Panel (position dynamically after co-visibility panel)
    locos_y = panel_height + 10
    num_classes = len(CLASS_NAMES)
    locos_height = locos_y + 20 + (num_classes * 20) + 10
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, locos_y), (450, locos_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    cv2.putText(frame, "All Locomotives Detected:", (10, locos_y + 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # Show detection status for all YOLO classes
    y_pos = locos_y + 40
    for class_id in sorted(CLASS_NAMES.keys()):
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
        cv2.rectangle(overlay, (5, y_offset), (450, y_offset + panel_height_gate), (0, 0, 0), -1)
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

        # Lead loco timestamps (all gates)
        gate_timestamps_lead = []
        for gate_id in gate_ids:
            ts = consist_state['gate_state'][gate_id]['lead_timestamp']
            ts_str = time.strftime("%H:%M:%S", time.localtime(ts)) if ts else "---"
            gate_timestamps_lead.append(f"G{gate_id}={ts_str}")

        lead_line = f"Loco {lead_addr}: " + "  ".join(gate_timestamps_lead)
        cv2.putText(frame, lead_line, (25, y_timestamp),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.35, colors_consist['lead'], 1)
        y_timestamp += 20

        # Rear loco timestamps (all gates)
        if rear_addr:
            gate_timestamps_rear = []
            for gate_id in gate_ids:
                ts = consist_state['gate_state'][gate_id]['rear_timestamp']
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


def track_consist(model_path: str):
    """Main tracking loop."""
    # Load camera config from shared config file
    from camera_utils import load_camera_config
    rtsp_url, camera_ip, camera_port, stream = load_camera_config()

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
                print("🔄 Reset tracking counters (visibility + gate crossings)")
                for consist_id, consist in tracker.consist_data.items():
                    consist['visible_together_count'] = 0
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
                marker_state.save_current_gate()
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

    # Co-visibility statistics (dynamic for all consists)
    print("👁️  CO-VISIBILITY STATISTICS")
    print("-" * 60)
    for consist_id in sorted(tracker.consist_data.keys()):
        config = tracker.consist_config[consist_id]
        count, pct = tracker.get_visibility_stats(consist_id, frame_count)
        print(f"   Consist {consist_id} ({config['name']}): {count} frames ({pct:.1f}%) - {count} co-detections")
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
