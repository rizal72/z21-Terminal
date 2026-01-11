"""
YOLO Tracker - Shared locomotive tracking logic

Used by both:
- backend/tracking_daemon.py (headless WebSocket daemon)
- scripts/track_consist_yolo.py (standalone GUI testing)

Handles YOLO inference, gate timing detection, and multi-consist tracking.
"""
import cv2
import time
import numpy as np
from pathlib import Path
from ultralytics import YOLO

# Import centralized config loader (relative import from backend/)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config_loader import load_config
from log_colors import log

# === CONFIGURATION ===
# Class mapping (YOLO model classes)
CLASS_NAMES = {
    0: '1_Gr675_017',    # Consist 10 lead
    1: '5_D645_014',     # Consist 10 rear
    2: '7_E656_239',     # Consist 11 lead
    3: '8_E444_056'      # Consist 11 rear
}

# Reverse mapping: DCC address → YOLO class ID (matches JMRI consist definition)
ADDRESS_TO_CLASS = {
    1: 0,  # Gr.675 017 (Consist 10 LEAD - sound loco)
    5: 1,  # D645 014 (Consist 10 REAR - reference loco)
    7: 2,  # E656 239 (Consist 11 LEAD - sound loco)
    8: 3   # E444 056 (Consist 11 REAR - reference loco)
}


# === HELPER FUNCTIONS ===

def gate_json_to_dict(gate_json):
    """
    Convert gate from JSON format to internal dict format.

    JSON format: {'id': 1, 'center': [x, y], 'width': w, 'height': h, 'angle': deg, 'color': [r, g, b]}
    Internal format: {'center_x': x, 'center_y': y, 'width': w, 'height': h, 'angle': deg, 'color': [r, g, b]}
    """
    return {
        'center_x': gate_json['center'][0],
        'center_y': gate_json['center'][1],
        'width': gate_json['width'],
        'height': gate_json['height'],
        'angle': gate_json['angle'],
        'color': gate_json.get('color', [255, 255, 0])  # Default yellow if missing
    }


def get_rotated_rect_points(center_x, center_y, width, height, angle_deg):
    """
    Get 4 corner points of a rotated rectangle.

    Args:
        center_x, center_y: Center point
        width, height: Dimensions
        angle_deg: Rotation angle in degrees (counter-clockwise)

    Returns:
        np.array of shape (4, 2) with corner points
    """
    angle_rad = np.deg2rad(angle_deg)
    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)

    hw = width / 2.0
    hh = height / 2.0

    # Corner offsets (before rotation)
    corners = np.array([
        [-hw, -hh],
        [hw, -hh],
        [hw, hh],
        [-hw, hh]
    ])

    # Rotation matrix
    rot_matrix = np.array([
        [cos_a, -sin_a],
        [sin_a, cos_a]
    ])

    # Rotate and translate
    rotated = corners @ rot_matrix.T
    points = rotated + np.array([center_x, center_y])

    return points.astype(np.int32)


def is_point_in_gate(point, gate):
    """
    Check if a point is inside a gate (rotated rectangle).

    Args:
        point: (x, y) tuple or None
        gate: dict with 'center_x', 'center_y', 'width', 'height', 'angle'

    Returns:
        bool: True if point is inside gate
    """
    if point is None:
        return False

    gate_points = get_rotated_rect_points(
        gate['center_x'], gate['center_y'],
        gate['width'], gate['height'],
        gate['angle']
    )

    # Use OpenCV pointPolygonTest (returns positive if inside)
    result = cv2.pointPolygonTest(gate_points, point, False)
    return result >= 0  # >= 0 means inside or on edge


# === YOLO TRACKER CLASS ===

class YOLOTracker:
    """
    YOLO-based locomotive tracker with cross-gate timing detection (config-driven multi-consist).

    NOMENCLATURE (CRITICAL):
    - lead/rear = JMRI consist roles (NOT physical position!)
      - lead: receives function commands (F0-F28)
      - rear: "succube" loco (follows lead for movement)
    - reference/adjust = Speed matching roles (config.json)
      - reference: stable decoder, NEVER modified
      - adjust: unstable decoder, ALWAYS compensated

    CONSIST 11 MAPPING EXAMPLE:
    - Lead JMRI (loco 7, E656_239) = Adjust (Hornby unstable)
    - Rear JMRI (loco 8, E444_056) = Reference (ESU stable)

    CROSS-GATE TIMING STRATEGY:
    - 2 gates per consist (both locos pass through BOTH gates)
    - dT = timestamp_lead - timestamp_rear
    - dT > 0: lead passes first (adjust too fast) → slow down
    - dT < 0: rear passes first (adjust too slow) → speed up
    - Cross-validation: |dT₁ - dT₂| < threshold confirms drift

    FRESH TIMESTAMPS LOGIC:
    - last_delta_t_time = max(timestamp1, timestamp2)
    - Ensures BOTH timestamps are fresh (> last_delta_t_time)
    - Prevents spurious dT from stale timestamps

    PHASE 5 COMPLETE: Generic multi-consist support (consists loaded from config.json).
    """

    def __init__(self, model_path: str = None):
        """Initialize tracker with YOLO model (config-driven multi-consist support)."""
        # Load config first to get debug mode and OBB flag
        config = load_config()

        # Load debug mode FIRST
        debug_config = config.get('debug', {'enabled': False})
        self.debug_enabled = debug_config.get('enabled', False)

        # Log debug mode status
        if self.debug_enabled:
            log('[INIT]', "Debug mode: ENABLED (verbose logging)")
        else:
            log('[INIT]', "Debug mode: DISABLED (only connections, dT updates, and speed corrections)")

        # Auto-detect model path if not provided (based on yolo_obb flag)
        if model_path is None:
            tracking_config = config.get('tracking', {})
            yolo_obb = tracking_config.get('yolo_obb', False)
            # Get models directory (relative to this file: backend/tracking/yolo_tracker.py)
            project_root = Path(__file__).parent.parent.parent  # z21-Terminal/ root
            models_dir = project_root / 'scripts' / 'models'
            if yolo_obb:
                base_name = 'best_obb'
            else:
                base_name = 'best'

            # Check for TensorRT engine first (priority: .engine > .pt)
            engine_path = models_dir / f'{base_name}.engine'
            pt_path = models_dir / f'{base_name}.pt'

            if engine_path.exists():
                model_path = str(engine_path)
                # ALWAYS show TensorRT usage (critical performance info)
                log('[INIT]', f"🚀 Using TensorRT engine: {engine_path.name} (GPU-optimized, 2-5x faster)")
            elif pt_path.exists():
                model_path = str(pt_path)
                # ALWAYS show which model was auto-selected (critical info)
                log('[INIT]', f"Auto-selected model: {pt_path.name} (yolo_obb={yolo_obb})")
                log('[INIT]', f"💡 Tip: Export to TensorRT for 2-5x faster inference: python scripts/utils/export_tensorrt.py")
            else:
                raise FileNotFoundError(f"No YOLO model found: checked {engine_path} and {pt_path}")

        if self.debug_enabled:
            log('[INIT]', f"Loading YOLO model: {model_path}")
        self.model = YOLO(model_path)

        # Load gates and thresholds from config
        self.gates = {}
        for gate in config['gates']:
            self.gates[gate['id']] = gate_json_to_dict(gate)
        if self.debug_enabled:
            log('[INIT]', f"Loaded {len(self.gates)} gates from config")

        # Load timing thresholds
        tracking_config = config.get('tracking', {})
        thresholds = tracking_config.get('timing_thresholds', {'normal': 1.0, 'warning': 2.0})
        self.threshold_normal = thresholds.get('normal', 1.0)
        self.threshold_warning = thresholds.get('warning', 2.0)
        if self.debug_enabled:
            log('[INIT]', f"Timing thresholds: SYNCED < {self.threshold_normal}s, WARNING < {self.threshold_warning}s")

        # Load dT sanity check threshold (ignore outliers from video lag)
        self.delta_t_max_threshold = thresholds.get('max_delta_t', 15.0)
        if self.debug_enabled:
            log('[WARN]', f"dT sanity check: ignore |dT| > {self.delta_t_max_threshold}s")

        # Load YOLO inference parameters
        self.yolo_imgsz = tracking_config.get('yolo_imgsz', 640)
        self.confidence_threshold = tracking_config.get('yolo_confidence', 0.5)
        self.iou_threshold = tracking_config.get('yolo_iou', 0.45)
        self.yolo_obb = tracking_config.get('yolo_obb', False)
        if self.debug_enabled:
            log('[INIT]', f"YOLO inference size: {self.yolo_imgsz}")
            log('[INIT]', f"YOLO confidence threshold: {self.confidence_threshold}")
            log('[INIT]', f"YOLO IoU threshold (NMS): {self.iou_threshold}")
            log('[INIT]', f"YOLO mode: {'OBB (Oriented Bounding Boxes)' if self.yolo_obb else 'Standard (axis-aligned boxes)'}")

        # Load reference loco configuration (from consists)
        consists = config.get('consists', {})
        self.reference_locos = {}
        for consist_addr, consist_info in consists.items():
            self.reference_locos[consist_addr] = {
                'reference': consist_info.get('reference_loco'),
                'adjust': consist_info.get('adjust_loco')
            }
        if self.reference_locos and self.debug_enabled:
            log('[INIT]', f"Reference locos: {len(self.reference_locos)} consists configured")

        # === PHASE 5: CONFIG-DRIVEN MULTI-CONSIST SUPPORT ===
        # Load consists from config.json
        consists = config.get('consists', {})

        # Build consist_config (mapping consist_id → addresses + YOLO class IDs)
        self.consist_config = {}
        for consist_key, consist_info in consists.items():

            consist_id = int(consist_key)  # "11" → 11 (simplified keys)
            lead_addr = consist_info['lead_address']
            rear_addr = consist_info['rear_address']  # Can be null for single locos
            gate_ids = consist_info['gate_ids']

            # Skip consists without tracking (no gates configured)
            # These are software-only consists that don't require YOLO training
            if not gate_ids or len(gate_ids) == 0:
                if self.debug_enabled:
                    log('[INIT]', f"Skipping consist {consist_id} (no gates - tracking disabled)")
                continue

            # Verify locomotives are in YOLO training set
            if lead_addr not in ADDRESS_TO_CLASS:
                log('[WARN]', f"Skipping consist {consist_id}: lead loco {lead_addr} not in YOLO training set")
                print(f"    Trained locomotives: {list(ADDRESS_TO_CLASS.keys())}")
                continue
            if rear_addr and rear_addr not in ADDRESS_TO_CLASS:
                log('[WARN]', f"Skipping consist {consist_id}: rear loco {rear_addr} not in YOLO training set")
                print(f"    Trained locomotives: {list(ADDRESS_TO_CLASS.keys())}")
                continue

            self.consist_config[consist_id] = {
                'name': consist_info.get('name', f'Consist {consist_id}'),
                'lead_address': lead_addr,
                'rear_address': rear_addr,
                'reference_loco': consist_info.get('reference_loco'),
                'adjust_loco': consist_info.get('adjust_loco'),
                'gate_ids': gate_ids,
                'gate_assignment': consist_info.get('gate_assignment'),  # None = symmetric, dict = asymmetric
                'lead_class_id': ADDRESS_TO_CLASS[lead_addr],
                'rear_class_id': ADDRESS_TO_CLASS[rear_addr] if rear_addr else None
            }

        if self.debug_enabled:
            log('[INIT]', f"Loaded {len(self.consist_config)} consists from config:")
            for cid, cinfo in self.consist_config.items():
                gates_str = f"{cinfo['gate_ids']}" if cinfo['gate_ids'] else "[]"
                lead_class = cinfo['lead_class_id']
                rear_class = cinfo['rear_class_id']
                print(f"   Consist {cid}: lead={cinfo['lead_address']} (class {lead_class}), rear={cinfo['rear_address']} (class {rear_class}), gates={gates_str}")

        # Initialize consist_data dict (tracking state for each consist)
        self.consist_data = {}
        for consist_id, consist_info in self.consist_config.items():
            gate_ids = consist_info['gate_ids']

            self.consist_data[consist_id] = {
                'lead_pos': None,
                'rear_pos': None,
                'gate_timestamps': {
                    'lead': {gid: None for gid in gate_ids},
                    'rear': {gid: None for gid in gate_ids}
                },
                'gate_states': {
                    'lead': {gid: False for gid in gate_ids},
                    'rear': {gid: False for gid in gate_ids}
                },
                'delta_t': None,
                'delta_t_type': None,
                'last_delta_t_time': 0,
                'gate_crossing_count': 0,
                # Spam reduction for ignored dT warnings
                'last_ignored_delta_t1': None,
                'last_ignored_delta_t1_time': 0,
                'last_ignored_delta_t2': None,
                'last_ignored_delta_t2_time': 0
            }

        if self.debug_enabled:
            log('[INIT]', "YOLO model loaded")

    def detect_locomotives(self, frame):
        """
        Detect all locomotives using YOLO.

        Returns:
            detections: dict {class_id: {'pos': (x,y), 'bbox': (x1,y1,x2,y2) or OBB points, 'conf': float, 'name': str}}
        """
        # Run inference (imgsz, confidence, and IoU from config.json)
        results = self.model(frame, conf=self.confidence_threshold, iou=self.iou_threshold, imgsz=self.yolo_imgsz, verbose=False)

        detections = {}  # {class_id: {'pos': (x,y), 'bbox': bbox_data, 'conf': float, 'name': str}}

        for result in results:
            if self.yolo_obb:
                # OBB mode: Oriented Bounding Boxes
                boxes = result.obb if hasattr(result, 'obb') else result.boxes
                for box in boxes:
                    # OBB format: box.xyxyxyxy = 4 corner points [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    if hasattr(box, 'xyxyxyxy'):
                        points = box.xyxyxyxy[0].cpu().numpy()  # Shape (4, 2): 4 corners
                        # Calculate center as average of 4 corners
                        center_x = int(points[:, 0].mean())
                        center_y = int(points[:, 1].mean())
                        bbox_data = tuple(points.flatten().astype(int))  # Flatten to 8 values
                    else:
                        # Fallback to xywhr format if xyxyxyxy not available
                        xywhr = box.xywhr[0].cpu().numpy()  # [cx, cy, w, h, rotation]
                        center_x = int(xywhr[0])
                        center_y = int(xywhr[1])
                        bbox_data = tuple(xywhr.astype(float))

                    conf = float(box.conf[0])
                    cls = int(box.cls[0])

                    # Get class name (e.g., "7_E656_239")
                    class_name = CLASS_NAMES.get(cls, f"Unknown_{cls}")

                    # Store detection (keep highest confidence if multiple)
                    if cls not in detections or conf > detections[cls]['conf']:
                        detections[cls] = {
                            'pos': (center_x, center_y),
                            'bbox': bbox_data,
                            'conf': conf,
                            'name': class_name
                        }
            else:
                # Standard mode: axis-aligned bounding boxes
                boxes = result.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])

                    # Calculate center point
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    bbox_data = (int(x1), int(y1), int(x2), int(y2))

                    # Get class name (e.g., "7_E656_239")
                    class_name = CLASS_NAMES.get(cls, f"Unknown_{cls}")

                    # Store detection (keep highest confidence if multiple)
                    if cls not in detections or conf > detections[cls]['conf']:
                        detections[cls] = {
                            'pos': (center_x, center_y),
                            'bbox': bbox_data,
                            'conf': conf,
                            'name': class_name
                        }

        return detections

    def calculate_delta_t_centralized(self, consist_id: int):
        """
        Centralized dT calculation with support for asymmetric and symmetric gate timing.

        Args:
            consist_id: Consist ID (10, 11, etc.)

        Called once per frame after all gate detection points updated.

        GATE TIMING MODES:
        - Asymmetric (gate_assignment defined): dT = adjust_loco@adj_gate - reference_loco@ref_gate
        - Symmetric (gate_assignment null): dT = lead@gate_i - rear@gate_j (cross-gate, both directions)

        UNIVERSAL INTERPRETATION (both modes):
        - dT > 0: reference passes first → adjust too slow → speed up adjust
        - dT < 0: adjust passes first → adjust too fast → slow down adjust
        """
        consist_info = self.consist_config[consist_id]
        cdata = self.consist_data[consist_id]
        gate_ids = consist_info['gate_ids']
        lead_addr = consist_info['lead_address']
        rear_addr = consist_info['rear_address']
        gate_assignment = consist_info.get('gate_assignment')

        # Require exactly 2 gates for timing
        if len(gate_ids) != 2:
            return  # Not configured for dual-gate timing

        g1, g2 = gate_ids[0], gate_ids[1]

        # === ASYMMETRIC MODE: Single direction only ===
        if gate_assignment:
            # Get gate IDs from assignment
            ref_gate = gate_assignment.get('reference')
            adj_gate = gate_assignment.get('adjust')
            ref_loco = consist_info['reference_loco']
            adj_loco = consist_info['adjust_loco']

            # Determine which role (lead/rear) matches reference/adjust
            if ref_loco == lead_addr:
                ref_ts = cdata['gate_timestamps']['lead'].get(ref_gate)
            else:  # ref_loco == rear_addr
                ref_ts = cdata['gate_timestamps']['rear'].get(ref_gate)

            if adj_loco == lead_addr:
                adj_ts = cdata['gate_timestamps']['lead'].get(adj_gate)
            else:  # adj_loco == rear_addr
                adj_ts = cdata['gate_timestamps']['rear'].get(adj_gate)

            # Calculate if both timestamps available
            if ref_ts is not None and adj_ts is not None:
                max_t = max(ref_ts, adj_ts)

                # Fresh timestamp check
                if (max_t > cdata['last_delta_t_time'] and
                    ref_ts > cdata['last_delta_t_time'] and
                    adj_ts > cdata['last_delta_t_time']):
                    # CRITICAL: Same logic as symmetric mode
                    # dT = adjust_ts - reference_ts (consistent with symmetric cross-gate)
                    # dT > 0: reference passes first → adjust too slow → speed up adjust
                    # dT < 0: adjust passes first → adjust too fast → slow down adjust
                    delta_t = adj_ts - ref_ts

                    # Sanity check
                    if abs(delta_t) > self.delta_t_max_threshold:
                        current_time = time.time()
                        should_print = (
                            cdata['last_ignored_delta_t1'] is None or
                            abs(delta_t - cdata['last_ignored_delta_t1']) > 0.01 or
                            (current_time - cdata['last_ignored_delta_t1_time']) > 5.0
                        )
                        if should_print:
                            log('[WARN]', f"C{consist_id}: Ignored dT = {delta_t:+.3f}s (|dT| > {self.delta_t_max_threshold}s)")
                            cdata['last_ignored_delta_t1'] = delta_t
                            cdata['last_ignored_delta_t1_time'] = current_time
                    else:
                        cdata['delta_t'] = delta_t
                        cdata['delta_t_type'] = f"L{ref_loco}G{ref_gate}-L{adj_loco}G{adj_gate}"
                        cdata['gate_crossing_count'] += 1
                        cdata['last_delta_t_time'] = max_t
                        log('[GATE]', f"C{consist_id} Asymmetric: L{ref_loco}G{ref_gate}-L{adj_loco}G{adj_gate} | dT={cdata['delta_t']:+.3f}s")
            return  # Asymmetric mode: only one calculation

        # === SYMMETRIC MODE: Cross-gate timing (both directions valid) ===

        # Check 1: dT₁ = lead@G1 - rear@G2 (cross-gate timing)
        lead_g1_ts = cdata['gate_timestamps']['lead'].get(g1)
        rear_g2_ts = cdata['gate_timestamps']['rear'].get(g2)

        if lead_g1_ts is not None and rear_g2_ts is not None:
            max_t1 = max(lead_g1_ts, rear_g2_ts)

            # Calculate only if BOTH timestamps are fresh (prevents mixing laps)
            if (max_t1 > cdata['last_delta_t_time'] and
                lead_g1_ts > cdata['last_delta_t_time'] and
                rear_g2_ts > cdata['last_delta_t_time']):
                delta_t1 = lead_g1_ts - rear_g2_ts

                # Sanity check: ignore impossible dT values (outliers from video lag)
                if abs(delta_t1) > self.delta_t_max_threshold:
                    # Throttle spam: only print if value changed significantly or 5s passed
                    current_time = time.time()
                    should_print = (
                        cdata['last_ignored_delta_t1'] is None or
                        abs(delta_t1 - cdata['last_ignored_delta_t1']) > 0.01 or  # Changed from 1.0 to 0.01 (dedupe identical values)
                        (current_time - cdata['last_ignored_delta_t1_time']) > 5.0
                    )
                    if should_print:
                        log('[WARN]', f"C{consist_id}: Ignored dT₁={delta_t1:+.3f}s (|dT| > {self.delta_t_max_threshold}s)")
                        cdata['last_ignored_delta_t1'] = delta_t1
                        cdata['last_ignored_delta_t1_time'] = current_time
                else:
                    cdata['delta_t'] = delta_t1
                    cdata['delta_t_type'] = f"L{lead_addr}G{g1}-L{rear_addr}G{g2}"
                    cdata['gate_crossing_count'] += 1
                    cdata['last_delta_t_time'] = max_t1
                    log('[GATE]', f"C{consist_id} Cross-gate: L{lead_addr}G{g1}-L{rear_addr}G{g2} | dT={cdata['delta_t']:+.3f}s")
                    return  # Calculated, done

        # Check 2: dT₂ = lead@G2 - rear@G1 (cross-gate timing)
        lead_g2_ts = cdata['gate_timestamps']['lead'].get(g2)
        rear_g1_ts = cdata['gate_timestamps']['rear'].get(g1)

        if lead_g2_ts is not None and rear_g1_ts is not None:
            max_t2 = max(lead_g2_ts, rear_g1_ts)

            # Calculate only if BOTH timestamps are fresh (prevents mixing laps)
            if (max_t2 > cdata['last_delta_t_time'] and
                lead_g2_ts > cdata['last_delta_t_time'] and
                rear_g1_ts > cdata['last_delta_t_time']):
                delta_t2 = lead_g2_ts - rear_g1_ts

                # Sanity check: ignore impossible dT values (outliers from video lag)
                if abs(delta_t2) > self.delta_t_max_threshold:
                    # Throttle spam: only print if value changed significantly or 5s passed
                    current_time = time.time()
                    should_print = (
                        cdata['last_ignored_delta_t2'] is None or
                        abs(delta_t2 - cdata['last_ignored_delta_t2']) > 0.01 or  # Changed from 1.0 to 0.01 (dedupe identical values)
                        (current_time - cdata['last_ignored_delta_t2_time']) > 5.0
                    )
                    if should_print:
                        log('[WARN]', f"C{consist_id}: Ignored dT₂={delta_t2:+.3f}s (|dT| > {self.delta_t_max_threshold}s)")
                        cdata['last_ignored_delta_t2'] = delta_t2
                        cdata['last_ignored_delta_t2_time'] = current_time
                else:
                    cdata['delta_t'] = delta_t2
                    cdata['delta_t_type'] = f"L{lead_addr}G{g2}-L{rear_addr}G{g1}"
                    cdata['gate_crossing_count'] += 1
                    cdata['last_delta_t_time'] = max_t2
                    log('[GATE]', f"C{consist_id} Cross-gate: L{lead_addr}G{g2}-L{rear_addr}G{g1} | dT={cdata['delta_t']:+.3f}s")

    def update(self, frame):
        """
        Update tracking with new frame for ALL consists (config-driven).

        Returns:
            dict with tracking data (positions, delta_t, detections)
        """
        detections = self.detect_locomotives(frame)

        # Loop over all consists (config-driven)
        for consist_id, consist_info in self.consist_config.items():
            lead_class = consist_info['lead_class_id']
            rear_class = consist_info['rear_class_id']

            # Get detection data
            lead_data = detections.get(lead_class)
            rear_data = detections.get(rear_class)

            lead_pos = lead_data['pos'] if lead_data else None
            rear_pos = rear_data['pos'] if rear_data else None

            # Update positions always (including None to hide marker when lost)
            self.consist_data[consist_id]['lead_pos'] = lead_pos
            self.consist_data[consist_id]['rear_pos'] = rear_pos

            # Gate timing detection (only if gates configured)
            if consist_info['gate_ids']:
                self._update_gate_timing(consist_id, lead_pos, rear_pos)

        # Build return dict with backward-compatible keys (c10, c11)
        result = {
            'detections': detections  # Full detection data for video overlay
        }

        # Add per-consist data
        for consist_id in self.consist_data.keys():
            cdata = self.consist_data[consist_id]
            result[f'c{consist_id}'] = {
                'lead': cdata['lead_pos'],
                'rear': cdata['rear_pos']
            }
            result[f'c{consist_id}_delta_t'] = cdata['delta_t']
            result[f'c{consist_id}_delta_t_type'] = cdata['delta_t_type']
            result[f'c{consist_id}_gate_crossings'] = cdata['gate_crossing_count']

        # Backward compatibility: delta_t = C11 dT (for now)
        if 11 in self.consist_data:
            result['delta_t'] = self.consist_data[11]['delta_t']
            result['delta_t_type'] = self.consist_data[11]['delta_t_type']
            result['gate_crossings'] = self.consist_data[11]['gate_crossing_count']

        return result

    def _update_gate_timing(self, consist_id: int, lead_pos, rear_pos):
        """
        Update gate timing detection for specified consist (generic method).

        Args:
            consist_id: Consist ID (10, 11, etc.)
            lead_pos: Lead locomotive position (x, y) or None
            rear_pos: Rear locomotive position (x, y) or None
        """
        consist_info = self.consist_config[consist_id]
        gate_ids = consist_info['gate_ids']
        cdata = self.consist_data[consist_id]

        # Loop over all gates assigned to this consist
        for gate_id in gate_ids:
            if gate_id not in self.gates:
                continue  # Gate not configured in gates array

            gate = self.gates[gate_id]

            # === LEAD LOCO ===
            in_gate = is_point_in_gate(lead_pos, gate)
            if in_gate and not cdata['gate_states']['lead'][gate_id]:
                # Rising edge: loco just entered gate
                timestamp = time.time()
                cdata['gate_timestamps']['lead'][gate_id] = timestamp
                cdata['gate_states']['lead'][gate_id] = True
                # IMMEDIATE LOG: show lead loco passing gate WITH COORDINATES
                lead_addr = consist_info['lead_address']
                timestamp_str = time.strftime('%H:%M:%S', time.localtime(timestamp))
                gate_center = (gate['center_x'], gate['center_y'])
                if self.debug_enabled:
                    log('[GATE]', f"C{consist_id}: Loco {lead_addr} (LEAD) passed G{gate_id} at {timestamp_str}.{int((timestamp % 1) * 1000):03d} | pos={lead_pos}, gate_center={gate_center}, gate_size={gate['width']}x{gate['height']}")
            elif not in_gate:
                cdata['gate_states']['lead'][gate_id] = False

            # === REAR LOCO ===
            in_gate = is_point_in_gate(rear_pos, gate)
            if in_gate and not cdata['gate_states']['rear'][gate_id]:
                # Rising edge: loco just entered gate
                timestamp = time.time()
                cdata['gate_timestamps']['rear'][gate_id] = timestamp
                cdata['gate_states']['rear'][gate_id] = True
                # IMMEDIATE LOG: show rear loco passing gate WITH COORDINATES
                rear_addr = consist_info['rear_address']
                timestamp_str = time.strftime('%H:%M:%S', time.localtime(timestamp))
                gate_center = (gate['center_x'], gate['center_y'])
                if self.debug_enabled:
                    log('[GATE]', f"C{consist_id}: Loco {rear_addr} (REAR) passed G{gate_id} at {timestamp_str}.{int((timestamp % 1) * 1000):03d} | pos={rear_pos}, gate_center={gate_center}, gate_size={gate['width']}x{gate['height']}")
            elif not in_gate:
                cdata['gate_states']['rear'][gate_id] = False

        # Centralized dT calculation (called once per frame after all gate detection points)
        self.calculate_delta_t_centralized(consist_id)

    def get_delta_t_status(self, consist_id: int):
        """
        Get dT status: SYNCED | WARNING | CRITICAL for specified consist.

        Args:
            consist_id: Consist ID (10, 11, etc.)

        Returns:
            'SYNCED' | 'WARNING' | 'CRITICAL' | None
        """
        if consist_id not in self.consist_data:
            return None

        delta_t = self.consist_data[consist_id]['delta_t']
        if delta_t is None:
            return None

        dt_abs = abs(delta_t)
        if dt_abs < self.threshold_normal:
            return 'SYNCED'
        elif dt_abs < self.threshold_warning:
            return 'WARNING'
        else:
            return 'CRITICAL'
