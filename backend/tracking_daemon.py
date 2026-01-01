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

# === CONFIGURATION ===
project_root = Path(__file__).parent.parent  # z21-Terminal/ root
MODEL_PATH = scripts_dir / 'models' / 'best.pt'  # Symlink to current model version
GATE_CONFIG_PATH = project_root / 'gate_config.json'
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

# === GATE CONFIGURATION ===
def load_gate_config():
    """Load gate configuration from JSON file."""
    try:
        with open(GATE_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"⚠️  Gate config not found: {GATE_CONFIG_PATH}")
        return {'gates': [], 'timing_thresholds': {'normal': 1.0, 'warning': 2.0}}
    except json.JSONDecodeError as e:
        print(f"⚠️  Invalid JSON in gate config: {e}")
        return {'gates': [], 'timing_thresholds': {'normal': 1.0, 'warning': 2.0}}


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
        config = load_gate_config()
        self.gates = {}
        for gate in config['gates']:
            self.gates[gate['id']] = gate_json_to_dict(gate)
        print(f"🚪 Loaded {len(self.gates)} gates from config")

        # Load timing thresholds
        thresholds = config.get('timing_thresholds', {'normal': 1.0, 'warning': 2.0})
        self.threshold_normal = thresholds.get('normal', 1.0)
        self.threshold_warning = thresholds.get('warning', 2.0)
        print(f"⏱️  Timing thresholds: SYNCED < {self.threshold_normal}s, WARNING < {self.threshold_warning}s")

        # Load Δt sanity check threshold (ignore outliers from video lag)
        self.delta_t_max_threshold = thresholds.get('max_delta_t', 15.0)
        print(f"⚠️  Δt sanity check: ignore |Δt| > {self.delta_t_max_threshold}s")

        # Load reference loco configuration (future-proofing for Phase 5)
        self.reference_locos = config.get('reference_locos', {})
        if self.reference_locos:
            print(f"🎯 Reference locos: {len(self.reference_locos)} consists configured")

        # Consist 10 (Tracciato Interno)
        self.c10_lead_pos = None
        self.c10_rear_pos = None

        # Consist 11 (Tracciato Esterno)
        self.c11_lead_pos = None
        self.c11_rear_pos = None

        # Gate timing detection (Phase 4 - Consist 11)
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
        self.delta_t = None
        self.delta_t_type = None

        # Gate crossing statistics
        self.gate_crossing_count = 0

        # Last Δt calculation time (to avoid calculating with stale timestamps)
        self.last_delta_t_time = 0

        # Spam reduction for ignored Δt warnings
        self.last_ignored_delta_t1 = None
        self.last_ignored_delta_t1_time = 0
        self.last_ignored_delta_t2 = None
        self.last_ignored_delta_t2_time = 0

        print("✅ YOLO model loaded")

    def detect_locomotives(self, frame):
        """
        Detect all locomotives using YOLO.

        Returns:
            detections: dict {class_id: {'pos': (x,y), 'conf': float, 'name': str}}
        """
        results = self.model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)

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

    def calculate_delta_t_centralized(self):
        """
        Centralized Δt calculation with 2 independent cross-gate checks.

        Called once per frame after all 4 detection points updated.
        """
        # Check 1: Δt₁ = lead@G1 - rear@G2 (cross-gate timing)
        if (self.c11_lead_gate1_timestamp is not None and
            self.c11_rear_gate2_timestamp is not None):

            max_t1 = max(self.c11_lead_gate1_timestamp, self.c11_rear_gate2_timestamp)

            # Calculate only if BOTH timestamps are fresh (prevents mixing laps)
            if (max_t1 > self.last_delta_t_time and
                self.c11_lead_gate1_timestamp > self.last_delta_t_time and
                self.c11_rear_gate2_timestamp > self.last_delta_t_time):
                delta_t1 = self.c11_lead_gate1_timestamp - self.c11_rear_gate2_timestamp

                # Sanity check: ignore impossible Δt values (outliers from video lag)
                if abs(delta_t1) > self.delta_t_max_threshold:
                    # Throttle spam: only print if value changed significantly or 5s passed
                    current_time = time.time()
                    should_print = (
                        self.last_ignored_delta_t1 is None or
                        abs(delta_t1 - self.last_ignored_delta_t1) > 1.0 or
                        (current_time - self.last_ignored_delta_t1_time) > 5.0
                    )
                    if should_print:
                        print(f"⚠️  Ignored Δt₁ = {delta_t1:+.3f}s (|Δt| > {self.delta_t_max_threshold}s)")
                        self.last_ignored_delta_t1 = delta_t1
                        self.last_ignored_delta_t1_time = current_time
                else:
                    self.delta_t = delta_t1
                    self.delta_t_type = "L7G1-L8G2"
                    self.gate_crossing_count += 1
                    self.last_delta_t_time = max_t1
                    print(f"🚪 Cross-gate: L7G1-L8G2 = Δt = {self.delta_t:+.3f}s")
                    return  # Calculated, done

        # Check 2: Δt₂ = lead@G2 - rear@G1 (cross-gate timing)
        if (self.c11_lead_gate2_timestamp is not None and
            self.c11_rear_gate1_timestamp is not None):

            max_t2 = max(self.c11_lead_gate2_timestamp, self.c11_rear_gate1_timestamp)

            # Calculate only if BOTH timestamps are fresh (prevents mixing laps)
            if (max_t2 > self.last_delta_t_time and
                self.c11_lead_gate2_timestamp > self.last_delta_t_time and
                self.c11_rear_gate1_timestamp > self.last_delta_t_time):
                delta_t2 = self.c11_lead_gate2_timestamp - self.c11_rear_gate1_timestamp

                # Sanity check: ignore impossible Δt values (outliers from video lag)
                if abs(delta_t2) > self.delta_t_max_threshold:
                    # Throttle spam: only print if value changed significantly or 5s passed
                    current_time = time.time()
                    should_print = (
                        self.last_ignored_delta_t2 is None or
                        abs(delta_t2 - self.last_ignored_delta_t2) > 1.0 or
                        (current_time - self.last_ignored_delta_t2_time) > 5.0
                    )
                    if should_print:
                        print(f"⚠️  Ignored Δt₂ = {delta_t2:+.3f}s (|Δt| > {self.delta_t_max_threshold}s)")
                        self.last_ignored_delta_t2 = delta_t2
                        self.last_ignored_delta_t2_time = current_time
                else:
                    self.delta_t = delta_t2
                    self.delta_t_type = "L7G2-L8G1"
                    self.gate_crossing_count += 1
                    self.last_delta_t_time = max_t2
                    print(f"🚪 Cross-gate: L7G2-L8G1 = Δt = {self.delta_t:+.3f}s")

    def update(self, frame):
        """
        Update tracking with new frame for BOTH consists.

        Returns:
            dict with tracking data (positions, delta_t, detections)
        """
        detections = self.detect_locomotives(frame)

        # === CONSIST 10 (Tracciato Interno) ===
        c10_lead_data = detections.get(0)
        c10_rear_data = detections.get(1)

        c10_lead_pos = c10_lead_data['pos'] if c10_lead_data else None
        c10_rear_pos = c10_rear_data['pos'] if c10_rear_data else None

        if c10_lead_pos and c10_rear_pos:
            self.c10_lead_pos = c10_lead_pos
            self.c10_rear_pos = c10_rear_pos

        # === CONSIST 11 (Tracciato Esterno) ===
        c11_lead_data = detections.get(2)
        c11_rear_data = detections.get(3)

        c11_lead_pos = c11_lead_data['pos'] if c11_lead_data else None
        c11_rear_pos = c11_rear_data['pos'] if c11_rear_data else None

        if c11_lead_pos and c11_rear_pos:
            self.c11_lead_pos = c11_lead_pos
            self.c11_rear_pos = c11_rear_pos

        # === GATE TIMING DETECTION (Consist 11) ===
        self._update_gate_timing(c11_lead_pos, c11_rear_pos)

        return {
            'c10': {'lead': c10_lead_pos, 'rear': c10_rear_pos},
            'c11': {'lead': c11_lead_pos, 'rear': c11_rear_pos},
            'delta_t': self.delta_t,
            'delta_t_type': self.delta_t_type,
            'gate_crossings': self.gate_crossing_count,
            'detections': detections  # NEW: Full detection data for video overlay
        }

    def _update_gate_timing(self, c11_lead_pos, c11_rear_pos):
        """Update gate timing detection for Consist 11."""
        if 1 not in self.gates or 2 not in self.gates:
            return  # Gates not configured

        # Gate 1 (VICINO) - Lead loco (E656_239)
        in_gate1 = is_point_in_gate(c11_lead_pos, self.gates[1])
        if in_gate1 and not self.c11_lead_in_gate1:
            # Rising edge: loco just entered gate
            self.c11_lead_gate1_timestamp = time.time()
            self.c11_lead_in_gate1 = True
        elif not in_gate1:
            self.c11_lead_in_gate1 = False

        # Gate 1 (VICINO) - Rear loco (E444_056)
        in_gate1 = is_point_in_gate(c11_rear_pos, self.gates[1])
        if in_gate1 and not self.c11_rear_in_gate1:
            # Rising edge: loco just entered gate
            self.c11_rear_gate1_timestamp = time.time()
            self.c11_rear_in_gate1 = True
        elif not in_gate1:
            self.c11_rear_in_gate1 = False

        # Gate 2 (LONTANO) - Lead loco (E656_239)
        in_gate2 = is_point_in_gate(c11_lead_pos, self.gates[2])
        if in_gate2 and not self.c11_lead_in_gate2:
            # Rising edge: loco just entered gate
            self.c11_lead_gate2_timestamp = time.time()
            self.c11_lead_in_gate2 = True
        elif not in_gate2:
            self.c11_lead_in_gate2 = False

        # Gate 2 (LONTANO) - Rear loco (E444_056)
        in_gate2 = is_point_in_gate(c11_rear_pos, self.gates[2])
        if in_gate2 and not self.c11_rear_in_gate2:
            # Rising edge: loco just entered gate
            self.c11_rear_gate2_timestamp = time.time()
            self.c11_rear_in_gate2 = True
        elif not in_gate2:
            self.c11_rear_in_gate2 = False

        # Centralized Δt calculation (called once per frame after all 4 detection points)
        self.calculate_delta_t_centralized()

    def get_delta_t_status(self):
        """Get Δt status: SYNCED | WARNING | CRITICAL"""
        if self.delta_t is None:
            return None

        dt_abs = abs(self.delta_t)
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

        # Load FPS settings from config
        try:
            with open(GATE_CONFIG_PATH, 'r') as f:
                config = json.load(f)
                fps_config = config.get('tracking_fps', {'active': 30, 'idle': 1})
                self.fps_active = fps_config.get('active', 30)
                self.fps_idle = fps_config.get('idle', 1)
        except Exception as e:
            print(f"⚠️  Error loading FPS config: {e}, using defaults")
            self.fps_active = 30
            self.fps_idle = 1

        # Dynamic FPS control
        self.consist_speeds = {}  # {consist_address: speed}
        self.active_tracking = False
        self.last_fps_mode = None  # Track mode changes for logging
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
        print(f"🔄 Attempting to reconnect to backend... (retry in {self.reconnect_delay:.1f}s if fails)")

        success = await self.connect_backend()

        if not success:
            # Exponential backoff
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
            print(f"⏳ Next retry in {self.reconnect_delay:.1f}s")

        return success

    async def broadcast_delta_t(self, tracking_data):
        """Broadcast delta_t update to backend (only when changed)."""
        if tracking_data['delta_t'] is None:
            return

        # Ensure connected before broadcasting
        if not await self.ensure_connected():
            return  # Not connected, skip broadcast

        # Only broadcast if Δt has changed (new calculation)
        current_delta_t = tracking_data['delta_t']
        current_type = tracking_data['delta_t_type']

        if (current_delta_t == self.last_broadcasted_delta_t and
            current_type == self.last_broadcasted_type):
            return  # Same value, don't broadcast again

        # New Δt calculated, broadcast it
        current_timestamp = time.time()

        # Calculate time_str (elapsed since PREVIOUS Δt)
        if self.last_broadcasted_timestamp:
            elapsed = current_timestamp - self.last_broadcasted_timestamp
            if elapsed < 1:
                time_str = "now"
            elif elapsed < 60:
                time_str = f"after {int(elapsed)}s"
            else:
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                time_str = f"after {minutes}m {seconds}s"
        else:
            # First Δt
            time_str = "now"

        # Update broadcast state
        self.last_broadcasted_delta_t = current_delta_t
        self.last_broadcasted_type = current_type
        self.last_broadcasted_timestamp = current_timestamp

        message = {
            'type': 'delta_t_update',
            'consist_address': 11,  # Consist 11 only for now
            'delta_t': current_delta_t,
            'gate_type': current_type,
            'status': self.tracker.get_delta_t_status(),
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
                    print("⚠️  Lost video connection")
                    await asyncio.sleep(1)
                    continue

                self.frame_count += 1

                # Update tracking
                tracking_data = self.tracker.update(frame)

                # Broadcast updates
                await self.broadcast_delta_t(tracking_data)

                # Optional: broadcast positions every 10 frames (reduce traffic)
                if self.frame_count % 10 == 0:
                    await self.broadcast_positions(tracking_data)

                # Dynamic FPS from config
                fps = self.fps_active if self.active_tracking else self.fps_idle
                await asyncio.sleep(1.0 / fps)

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

        if self.start_time:
            duration = time.time() - self.start_time
            print(f"\n📊 Session Summary:")
            print(f"   Duration: {duration:.1f}s")
            print(f"   Frames: {self.frame_count}")
            print(f"   Gate crossings: {self.tracker.gate_crossing_count}")
            if self.tracker.delta_t is not None:
                print(f"   Last Δt: {self.tracker.delta_t:+.3f}s ({self.tracker.get_delta_t_status()})")

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
