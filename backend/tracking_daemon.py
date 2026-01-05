"""
Tracking Daemon - Headless YOLO + Gate Timing Detection

Runs YOLO inference and gate timing detection without GUI.
Broadcasts delta_t updates to FastAPI backend via WebSocket.
"""
import sys
import os

# Silence FFmpeg/H264 decoder warnings BEFORE importing cv2
os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'  # Quiet mode
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'

import cv2
import time
import json
import signal
import asyncio
import websockets
import numpy as np
from pathlib import Path
from ultralytics import YOLO

# Add scripts directory to path for z21.py imports if needed
scripts_dir = Path(__file__).parent.parent / 'scripts'
sys.path.insert(0, str(scripts_dir))

# Import centralized config loader
from config_loader import load_config

# === CONFIGURATION ===
project_root = Path(__file__).parent.parent  # z21-Terminal/ root
MODEL_PATH = scripts_dir / 'models' / 'best.pt'  # Symlink to current model version
CAMERA_CONFIG_PATH = project_root / 'camera_config.json'
BACKEND_WS_URL = "ws://localhost:8000/ws/tracking"  # WebSocket to FastAPI backend

# Load camera credentials from config file
def load_camera_config():
    """Load camera configuration from JSON file."""
    try:
        with open(CAMERA_CONFIG_PATH, 'r') as f:
            config = json.load(f)

        camera_ip = config.get('camera_ip', '192.168.1.4')
        camera_port = config.get('camera_port', 554)
        stream = config.get('stream', 'stream2')
        username = config['username']
        password = config['password']

        rtsp_url = f"rtsp://{username}:{password}@{camera_ip}:{camera_port}/{stream}"
        return rtsp_url
    except FileNotFoundError:
        print(f"❌ ERROR: Camera config not found at {CAMERA_CONFIG_PATH}")
        print(f"   Create it from template: cp {CAMERA_CONFIG_PATH}.example {CAMERA_CONFIG_PATH}")
        print(f"   Then edit with your camera credentials.")
        sys.exit(1)
    except KeyError as e:
        print(f"❌ ERROR: Missing required field in camera config: {e}")
        print(f"   Check {CAMERA_CONFIG_PATH} and ensure 'username' and 'password' are set.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in camera config: {e}")
        sys.exit(1)

RTSP_URL = load_camera_config()

# YOLO confidence threshold
CONFIDENCE_THRESHOLD = 0.5

# Idle mode cooldown (seconds to wait after movement stops before switching to low-power mode)
IDLE_COOLDOWN_SECONDS = 10.0

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

# === CONFIGURATION ===
# load_config() now imported from config_loader (supports config.local.json override)


def gate_json_to_dict(gate_json):
    """
    Convert gate from JSON format to internal dict format.

    JSON format: {'id': 1, 'center': [x, y], 'width': w, 'height': h, 'angle': deg}
    Internal format: {'center_x': x, 'center_y': y, 'width': w, 'height': h, 'angle': deg}
    """
    return {
        'center_x': gate_json['center'][0],
        'center_y': gate_json['center'][1],
        'width': gate_json['width'],
        'height': gate_json['height'],
        'angle': gate_json['angle']
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


# === YOLO TRACKER ===
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
    - Δt = timestamp_lead - timestamp_rear
    - Δt > 0: lead passes first (adjust too fast) → slow down
    - Δt < 0: rear passes first (adjust too slow) → speed up
    - Cross-validation: |Δt₁ - Δt₂| < threshold confirms drift

    FRESH TIMESTAMPS LOGIC:
    - last_delta_t_time = max(timestamp1, timestamp2)
    - Ensures BOTH timestamps are fresh (> last_delta_t_time)
    - Prevents spurious Δt from stale timestamps

    PHASE 5 COMPLETE: Generic multi-consist support (consists loaded from config.json).
    """

    def __init__(self, model_path: str):
        """Initialize tracker with YOLO model (config-driven multi-consist support)."""
        # Load config first to get debug mode
        config = load_config()

        # Load debug mode FIRST
        debug_config = config.get('debug', {'enabled': False})
        self.debug_enabled = debug_config.get('enabled', False)

        # Log debug mode status
        if self.debug_enabled:
            print("🐛 Debug mode: ENABLED (verbose logging)")
        else:
            print("🔇 Debug mode: DISABLED (only connections, Δt updates, and speed corrections)")

        if self.debug_enabled:
            print(f"🤖 Loading YOLO model: {model_path}")
        self.model = YOLO(model_path)

        # Load gates and thresholds from config
        self.gates = {}
        for gate in config['gates']:
            self.gates[gate['id']] = gate_json_to_dict(gate)
        if self.debug_enabled:
            print(f"🚪 Loaded {len(self.gates)} gates from config")

        # Load timing thresholds
        tracking_config = config.get('tracking', {})
        thresholds = tracking_config.get('timing_thresholds', {'normal': 1.0, 'warning': 2.0})
        self.threshold_normal = thresholds.get('normal', 1.0)
        self.threshold_warning = thresholds.get('warning', 2.0)
        if self.debug_enabled:
            print(f"⏱️  Timing thresholds: SYNCED < {self.threshold_normal}s, WARNING < {self.threshold_warning}s")

        # Load Δt sanity check threshold (ignore outliers from video lag)
        self.delta_t_max_threshold = thresholds.get('max_delta_t', 15.0)
        if self.debug_enabled:
            print(f"⚠️  Δt sanity check: ignore |Δt| > {self.delta_t_max_threshold}s")

        # Load YOLO inference image size
        self.yolo_imgsz = tracking_config.get('yolo_imgsz', 640)
        if self.debug_enabled:
            print(f"🔍 YOLO inference size: {self.yolo_imgsz}")

        # Load reference loco configuration (from consists)
        consists = config.get('consists', {})
        self.reference_locos = {}
        for consist_addr, consist_info in consists.items():
            if 'reference' in consist_info:
                ref = consist_info['reference']
                self.reference_locos[consist_addr] = {
                    'reference': ref.get('loco'),
                    'adjust': ref.get('adjust')
                }
        if self.reference_locos and self.debug_enabled:
            print(f"🎯 Reference locos: {len(self.reference_locos)} consists configured")

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
                    print(f"⏭️  Skipping consist {consist_id} (no gates - tracking disabled)")
                continue

            # Verify locomotives are in YOLO training set
            if lead_addr not in ADDRESS_TO_CLASS:
                print(f"⚠️  Skipping consist {consist_id}: lead loco {lead_addr} not in YOLO training set")
                print(f"    Trained locomotives: {list(ADDRESS_TO_CLASS.keys())}")
                continue
            if rear_addr and rear_addr not in ADDRESS_TO_CLASS:
                print(f"⚠️  Skipping consist {consist_id}: rear loco {rear_addr} not in YOLO training set")
                print(f"    Trained locomotives: {list(ADDRESS_TO_CLASS.keys())}")
                continue

            self.consist_config[consist_id] = {
                'lead_address': lead_addr,
                'rear_address': rear_addr,
                'gate_ids': gate_ids,
                'lead_class_id': ADDRESS_TO_CLASS[lead_addr],
                'rear_class_id': ADDRESS_TO_CLASS[rear_addr] if rear_addr else None
            }

        if self.debug_enabled:
            print(f"🚂 Loaded {len(self.consist_config)} consists from config:")
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
                # Spam reduction for ignored Δt warnings
                'last_ignored_delta_t1': None,
                'last_ignored_delta_t1_time': 0,
                'last_ignored_delta_t2': None,
                'last_ignored_delta_t2_time': 0
            }

        if self.debug_enabled:
            print("✅ YOLO model loaded")

    def detect_locomotives(self, frame):
        """
        Detect all locomotives using YOLO.

        Returns:
            detections: dict {class_id: {'pos': (x,y), 'conf': float, 'name': str}}
        """
        # Run inference (imgsz from config.json)
        results = self.model(frame, conf=CONFIDENCE_THRESHOLD, imgsz=self.yolo_imgsz, verbose=False)

        detections = {}  # {class_id: {'pos': (x,y), 'conf': float, 'name': str}}

        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                cls = int(box.cls[0])

                # Calculate center point
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)

                # Get class name (e.g., "7_E656_239")
                class_name = CLASS_NAMES.get(cls, f"Unknown_{cls}")

                # Store detection (keep highest confidence if multiple)
                if cls not in detections or conf > detections[cls]['conf']:
                    detections[cls] = {
                        'pos': (center_x, center_y),
                        'conf': conf,
                        'name': class_name
                    }

        return detections

    def calculate_delta_t_centralized(self, consist_id: int):
        """
        Centralized Δt calculation with 2 independent cross-gate checks (generic for any consist).

        Args:
            consist_id: Consist ID (10, 11, etc.)

        Called once per frame after all gate detection points updated.

        DUAL-GATE CROSS-GATE TIMING (2 gates per consist):
        - Check 1: Δt₁ = lead@G1 - rear@G2 (cross-gate)
        - Check 2: Δt₂ = lead@G2 - rear@G1 (cross-gate)
        """
        consist_info = self.consist_config[consist_id]
        cdata = self.consist_data[consist_id]
        gate_ids = consist_info['gate_ids']
        lead_addr = consist_info['lead_address']
        rear_addr = consist_info['rear_address']

        # Require exactly 2 gates for cross-gate timing
        if len(gate_ids) != 2:
            return  # Not configured for dual-gate timing

        g1, g2 = gate_ids[0], gate_ids[1]

        # Check 1: Δt₁ = lead@G1 - rear@G2 (cross-gate timing)
        lead_g1_ts = cdata['gate_timestamps']['lead'].get(g1)
        rear_g2_ts = cdata['gate_timestamps']['rear'].get(g2)

        if lead_g1_ts is not None and rear_g2_ts is not None:
            max_t1 = max(lead_g1_ts, rear_g2_ts)

            # Calculate only if BOTH timestamps are fresh (prevents mixing laps)
            if (max_t1 > cdata['last_delta_t_time'] and
                lead_g1_ts > cdata['last_delta_t_time'] and
                rear_g2_ts > cdata['last_delta_t_time']):
                delta_t1 = lead_g1_ts - rear_g2_ts

                # Sanity check: ignore impossible Δt values (outliers from video lag)
                if abs(delta_t1) > self.delta_t_max_threshold:
                    # Throttle spam: only print if value changed significantly or 5s passed
                    current_time = time.time()
                    should_print = (
                        cdata['last_ignored_delta_t1'] is None or
                        abs(delta_t1 - cdata['last_ignored_delta_t1']) > 1.0 or
                        (current_time - cdata['last_ignored_delta_t1_time']) > 5.0
                    )
                    if should_print:
                        print(f"⚠️  C{consist_id}: Ignored Δt₁ = {delta_t1:+.3f}s (|Δt| > {self.delta_t_max_threshold}s)")
                        cdata['last_ignored_delta_t1'] = delta_t1
                        cdata['last_ignored_delta_t1_time'] = current_time
                else:
                    cdata['delta_t'] = delta_t1
                    cdata['delta_t_type'] = f"L{lead_addr}G{g1}-L{rear_addr}G{g2}"
                    cdata['gate_crossing_count'] += 1
                    cdata['last_delta_t_time'] = max_t1
                    print(f"🚪 C{consist_id} Cross-gate: L{lead_addr}G{g1}-L{rear_addr}G{g2} = Δt = {cdata['delta_t']:+.3f}s")
                    return  # Calculated, done

        # Check 2: Δt₂ = lead@G2 - rear@G1 (cross-gate timing)
        lead_g2_ts = cdata['gate_timestamps']['lead'].get(g2)
        rear_g1_ts = cdata['gate_timestamps']['rear'].get(g1)

        if lead_g2_ts is not None and rear_g1_ts is not None:
            max_t2 = max(lead_g2_ts, rear_g1_ts)

            # Calculate only if BOTH timestamps are fresh (prevents mixing laps)
            if (max_t2 > cdata['last_delta_t_time'] and
                lead_g2_ts > cdata['last_delta_t_time'] and
                rear_g1_ts > cdata['last_delta_t_time']):
                delta_t2 = lead_g2_ts - rear_g1_ts

                # Sanity check: ignore impossible Δt values (outliers from video lag)
                if abs(delta_t2) > self.delta_t_max_threshold:
                    # Throttle spam: only print if value changed significantly or 5s passed
                    current_time = time.time()
                    should_print = (
                        cdata['last_ignored_delta_t2'] is None or
                        abs(delta_t2 - cdata['last_ignored_delta_t2']) > 1.0 or
                        (current_time - cdata['last_ignored_delta_t2_time']) > 5.0
                    )
                    if should_print:
                        print(f"⚠️  C{consist_id}: Ignored Δt₂ = {delta_t2:+.3f}s (|Δt| > {self.delta_t_max_threshold}s)")
                        cdata['last_ignored_delta_t2'] = delta_t2
                        cdata['last_ignored_delta_t2_time'] = current_time
                else:
                    cdata['delta_t'] = delta_t2
                    cdata['delta_t_type'] = f"L{lead_addr}G{g2}-L{rear_addr}G{g1}"
                    cdata['gate_crossing_count'] += 1
                    cdata['last_delta_t_time'] = max_t2
                    print(f"🚪 C{consist_id} Cross-gate: L{lead_addr}G{g2}-L{rear_addr}G{g1} = Δt = {cdata['delta_t']:+.3f}s")

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

            # Update positions if both detected
            if lead_pos and rear_pos:
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

        # Backward compatibility: delta_t = C11 Δt (for now)
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
                    print(f"🚦 C{consist_id}: Loco {lead_addr} (LEAD) passed G{gate_id} at {timestamp_str}.{int((timestamp % 1) * 1000):03d} | pos={lead_pos}, gate_center={gate_center}, gate_size={gate['width']}x{gate['height']}")
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
                    print(f"🚦 C{consist_id}: Loco {rear_addr} (REAR) passed G{gate_id} at {timestamp_str}.{int((timestamp % 1) * 1000):03d} | pos={rear_pos}, gate_center={gate_center}, gate_size={gate['width']}x{gate['height']}")
            elif not in_gate:
                cdata['gate_states']['rear'][gate_id] = False

        # Centralized Δt calculation (called once per frame after all gate detection points)
        self.calculate_delta_t_centralized(consist_id)

    def get_delta_t_status(self, consist_id: int):
        """
        Get Δt status: SYNCED | WARNING | CRITICAL for specified consist.

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


# === TRACKING DAEMON ===
class TrackingDaemon:
    """Main tracking daemon with WebSocket communication."""

    def __init__(self):
        self.tracker = YOLOTracker(str(MODEL_PATH))
        self.debug_enabled = self.tracker.debug_enabled  # Copy from tracker
        self.cap = None
        self.websocket = None
        self.running = False
        self.frame_count = 0
        self.start_time = None
        self.last_broadcasted_delta_t = None
        self.last_broadcasted_type = None
        self.last_broadcasted_timestamp = None  # Timestamp of previous Δt for time_str calculation

        # Auto-reconnect state
        self.reconnect_delay = 2.0  # Start with 2s
        self.max_reconnect_delay = 30.0  # Max 30s
        self.last_reconnect_attempt = 0

        # Load FPS settings from config (debug mode already loaded in tracker)
        try:
            config = load_config()
            tracking_config = config.get('tracking', {})
            fps_config = tracking_config.get('fps', {'active': 30, 'idle': 1})
            self.fps_active = fps_config.get('active', 30)
            self.fps_idle = fps_config.get('idle', 1)
        except Exception as e:
            if self.debug_enabled:
                print(f"⚠️  Error loading config: {e}, using defaults")
            self.fps_active = 30
            self.fps_idle = 1

        # Dynamic FPS control
        self.consist_speeds = {}  # {consist_address: speed}
        self.active_tracking = False
        self.last_fps_mode = None  # Track mode changes for logging
        self.video_connected = True  # Track video connection state for logging
        self.idle_timer_task = None  # Asyncio task for 10s cooldown timer

    async def connect_backend(self):
        """Connect to FastAPI backend via WebSocket."""
        try:
            self.websocket = await websockets.connect(BACKEND_WS_URL)
            print(f"✅ Connected to backend: {BACKEND_WS_URL}")
            # Reset reconnect delay on successful connection
            self.reconnect_delay = 2.0
            return True
        except Exception as e:
            print(f"❌ Failed to connect to backend: {e}")
            return False

    async def ensure_connected(self):
        """Ensure WebSocket is connected, attempt reconnect if needed."""
        # Check if already connected
        if self.websocket and not self.websocket.closed:
            return True

        # Check if we should attempt reconnect (rate limiting)
        now = time.time()
        if now - self.last_reconnect_attempt < self.reconnect_delay:
            return False  # Too soon to retry

        # Attempt reconnect
        self.last_reconnect_attempt = now
        if self.debug_enabled:
            print(f"🔄 Attempting to reconnect to backend... (retry in {self.reconnect_delay:.1f}s if fails)")

        success = await self.connect_backend()

        if not success:
            # Exponential backoff
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
            if self.debug_enabled:
                print(f"⏳ Next retry in {self.reconnect_delay:.1f}s")

        return success

    async def broadcast_delta_t(self, tracking_data):
        """Broadcast delta_t updates for ALL consists (multi-consist support)."""
        # Ensure connected before broadcasting
        if not await self.ensure_connected():
            return  # Not connected, skip broadcast

        # Loop over all consists and broadcast if Δt changed
        for consist_id, cdata in self.tracker.consist_data.items():
            delta_t = cdata['delta_t']
            if delta_t is None:
                continue  # No Δt for this consist

            # Get delta_t_type from tracking_data (backward compatible)
            current_type = tracking_data.get(f'c{consist_id}_delta_t_type', cdata['delta_t_type'])

            # Check if changed for this consist (need per-consist tracking)
            consist_key = f'c{consist_id}'
            if not hasattr(self, 'last_broadcasted_per_consist'):
                self.last_broadcasted_per_consist = {}

            if consist_key not in self.last_broadcasted_per_consist:
                self.last_broadcasted_per_consist[consist_key] = {
                    'delta_t': None,
                    'type': None,
                    'timestamp': None
                }

            last_broadcast = self.last_broadcasted_per_consist[consist_key]

            if (delta_t == last_broadcast['delta_t'] and
                current_type == last_broadcast['type']):
                continue  # Same value, skip

            # New Δt calculated, broadcast it
            current_timestamp = time.time()

            # Calculate time_str (elapsed since PREVIOUS Δt for this consist)
            if last_broadcast['timestamp']:
                elapsed = current_timestamp - last_broadcast['timestamp']
                if elapsed < 1:
                    time_str = "now"
                elif elapsed < 60:
                    time_str = f"after {int(elapsed)}s"
                else:
                    minutes = int(elapsed // 60)
                    seconds = int(elapsed % 60)
                    time_str = f"after {minutes}m {seconds}s"
            else:
                # First Δt for this consist
                time_str = "now"

            # Update broadcast state for this consist
            last_broadcast['delta_t'] = delta_t
            last_broadcast['type'] = current_type
            last_broadcast['timestamp'] = current_timestamp

            message = {
                'type': 'delta_t_update',
                'consist_address': consist_id,
                'delta_t': delta_t,
                'gate_type': current_type,
                'status': self.tracker.get_delta_t_status(consist_id),
                'timestamp': current_timestamp,
                'time_str': time_str,  # Pre-calculated elapsed time
                'thresholds': {
                    'normal': self.tracker.threshold_normal,
                    'warning': self.tracker.threshold_warning
                }
            }

            try:
                await self.websocket.send(json.dumps(message))
            except Exception as e:
                print(f"⚠️  Backend disconnected: {e}")
                self.websocket = None  # Mark as disconnected
                break  # Stop broadcasting if disconnected

    async def broadcast_positions(self, tracking_data):
        """Broadcast YOLO detection positions for video overlay (pallini)."""
        detections = tracking_data.get('detections', {})
        if not detections:
            return

        # Ensure connected before broadcasting (but don't block if not connected)
        if not self.websocket or self.websocket.closed:
            return  # Not connected, skip broadcast (silent)

        # Format detections for video overlay (pallini colorati)
        positions = []
        for class_id, det in detections.items():
            class_name = det['name']  # e.g., "7_E656_239"

            # Extract address and locomotive name
            try:
                parts = class_name.split('_')
                address = int(parts[0])
                loco_name = '_'.join(parts[1:])  # "E656_239" → "E656"
                # Simplify name: just first part (E656, not E656_239)
                loco_name_short = parts[1] if len(parts) > 1 else loco_name
            except (ValueError, IndexError):
                continue

            positions.append({
                'address': address,
                'name': loco_name_short,  # "E656" or "E444"
                'position': list(det['pos']),  # [x, y]
                'confidence': det['conf']
            })

        if not positions:
            return

        message = {
            'type': 'yolo_detections',
            'detections': positions,
            'timestamp': time.time()
        }

        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            # Silent fail for positions (less critical than Δt)
            self.websocket = None  # Mark as disconnected

    async def _idle_timer(self):
        """Timer che aspetta 10s prima di passare a idle mode"""
        try:
            await asyncio.sleep(IDLE_COOLDOWN_SECONDS)

            # Dopo 10s, controlla se ancora tutto fermo
            any_movement = any(s > 0 for s in self.consist_speeds.values())
            if not any_movement and self.active_tracking:
                self.active_tracking = False
                print(f"🔄 Switched to Low-Power Mode ({self.fps_idle} FPS) (after {IDLE_COOLDOWN_SECONDS:.0f}s cooldown)")
        except asyncio.CancelledError:
            # Timer cancellato (movimento ripreso)
            pass

    def update_consist_speed(self, consist_address: int, speed: int):
        """
        Update consist speed for FPS mode calculation with cooldown

        Args:
            consist_address: DCC address
            speed: Speed 0-126
        """
        self.consist_speeds[consist_address] = speed

        # Check if any consist is moving
        any_movement = any(s > 0 for s in self.consist_speeds.values())

        if any_movement:
            # Movement detected: cancella timer e passa subito ad active
            if self.idle_timer_task:
                self.idle_timer_task.cancel()
                self.idle_timer_task = None

            if not self.active_tracking:
                self.active_tracking = True
                print(f"🔄 Switched to Active Tracking ({self.fps_active} FPS)")
        else:
            # Tutto fermo: avvia timer 10s (se non già avviato)
            if not self.idle_timer_task and self.active_tracking:
                print(f"⏸️  All consists stopped - starting {IDLE_COOLDOWN_SECONDS:.0f}s cooldown timer...")
                self.idle_timer_task = asyncio.create_task(self._idle_timer())

    async def listen_backend_messages(self):
        """Listen for incoming messages from backend (runs in parallel with tracking loop)"""
        while self.running:
            try:
                # Ensure we're connected
                await self.ensure_connected()

                if not self.websocket:
                    await asyncio.sleep(1)
                    continue

                # Listen for messages
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    data = json.loads(message)

                    if data.get('type') == 'consist_speed_update':
                        consist_address = data.get('consist_address')
                        speed = data.get('speed', 0)
                        self.update_consist_speed(consist_address, speed)

                except asyncio.TimeoutError:
                    # Timeout is OK, just loop again
                    continue
                except websockets.exceptions.ConnectionClosed:
                    self.websocket = None
                    await asyncio.sleep(1)

            except Exception as e:
                # Don't crash the daemon on error, just log and retry
                await asyncio.sleep(1)

    async def run(self):
        """Main tracking loop with dynamic FPS."""
        self.running = True
        self.start_time = time.time()

        # Try initial connection (but don't fail if backend not ready)
        await self.connect_backend()

        # Open video capture
        print(f"📹 Opening video stream: {RTSP_URL}")
        self.cap = cv2.VideoCapture(RTSP_URL)

        # CRITICAL: Set minimal buffer to prevent lag accumulation
        # RTSP streams buffer frames causing 20+ second delays over time
        # buffer=1 = always read FRESHEST frame available (adaptive skip if processing is slow)
        # This ensures gate crossings are detected in real-time, not 20s late!
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self.cap.isOpened():
            print("❌ Failed to open video stream")
            return

        print(f"✅ Tracking daemon started - Low-Power Mode ({self.fps_idle} FPS)")
        print(f"   (switches to Active Tracking {self.fps_active} FPS when movement detected)")

        # Start backend message listener in parallel
        listener_task = asyncio.create_task(self.listen_backend_messages())

        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    # Log only on state change (avoid spam)
                    if self.video_connected:
                        print("⚠️  Lost video connection")
                        self.video_connected = False
                    await asyncio.sleep(1)
                    continue

                # Video connection restored
                if not self.video_connected:
                    print("✅ Video connection restored")
                    self.video_connected = True

                self.frame_count += 1

                # Skip YOLO in idle mode (save CPU, keep VideoCapture alive)
                if not self.active_tracking:
                    # Log only on state change (avoid spam) - verbose, only if debug enabled
                    if self.last_fps_mode != 'idle':
                        print(f"🔇 YOLO tracking paused (idle @ {self.fps_idle} FPS, flushing RTSP buffer only)")
                        self.last_fps_mode = 'idle'
                    # Idle: read frame to flush RTSP buffer, but skip YOLO + broadcast
                    await asyncio.sleep(1.0 / self.fps_idle)
                    continue

                # Active: YOLO tracking + broadcast
                # Log only on state change (avoid spam) - verbose, only if debug enabled
                if self.last_fps_mode != 'active':
                    print(f"🔊 YOLO tracking resumed (active @ {self.fps_active} FPS)")
                    self.last_fps_mode = 'active'

                tracking_data = self.tracker.update(frame)

                # Broadcast updates
                await self.broadcast_delta_t(tracking_data)

                # Optional: broadcast positions every 10 frames (reduce traffic)
                if self.frame_count % 10 == 0:
                    await self.broadcast_positions(tracking_data)

                # Dynamic FPS (active mode)
                await asyncio.sleep(1.0 / self.fps_active)

        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
        except Exception as e:
            print(f"❌ Error in tracking loop: {e}")
        finally:
            # Cancel listener task
            if listener_task:
                listener_task.cancel()
                try:
                    await listener_task
                except asyncio.CancelledError:
                    pass

            self.stop()

    def stop(self):
        """Stop tracking and cleanup."""
        self.running = False

        # Cancel idle timer if running
        if self.idle_timer_task:
            self.idle_timer_task.cancel()
            self.idle_timer_task = None

        if self.cap:
            self.cap.release()

        if self.start_time and self.debug_enabled:
            duration = time.time() - self.start_time
            print(f"\n📊 Session Summary:")
            print(f"   Duration: {duration:.1f}s")
            print(f"   Frames: {self.frame_count}")

            # Per-consist statistics
            for consist_id, cdata in self.tracker.consist_data.items():
                crossings = cdata['gate_crossing_count']
                delta_t = cdata['delta_t']
                if crossings > 0:
                    print(f"   Consist {consist_id}:")
                    print(f"     Gate crossings: {crossings}")
                    if delta_t is not None:
                        status = self.tracker.get_delta_t_status(consist_id)
                        print(f"     Last Δt: {delta_t:+.3f}s ({status})")

        if self.debug_enabled:
            print("✅ Tracking daemon stopped")


# === MAIN ===
shutdown_flag = False

def signal_handler(sig, frame):
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    global shutdown_flag
    print("\n⚠️  Shutdown signal received")
    shutdown_flag = True


async def main():
    """Main entry point."""
    global shutdown_flag

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("""
╔═══════════════════════════════════════════════════════════╗
║          z21-Terminal Tracking Daemon (Headless)          ║
║           YOLO + Gate Timing Detection                    ║
╚═══════════════════════════════════════════════════════════╝
    """)

    daemon = TrackingDaemon()

    # Run daemon in background task
    daemon_task = asyncio.create_task(daemon.run())

    # Wait for shutdown signal
    try:
        while not shutdown_flag:
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass

    # Graceful shutdown: stop daemon and wait for cleanup
    daemon.running = False
    try:
        await asyncio.wait_for(daemon_task, timeout=3.0)
    except asyncio.TimeoutError:
        daemon_task.cancel()
        try:
            await daemon_task
        except asyncio.CancelledError:
            pass


if __name__ == '__main__':
    asyncio.run(main())
