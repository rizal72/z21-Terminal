#!/usr/bin/env python3
"""
Interactive tool for marking and drawing on camera feed.

Supports multiple modes:
- Mode 1 (POINT): Click to place single points
- Mode 2 (POLYGON): Click multiple points, close with ENTER
- Mode 3 (RECTANGLE): Drag and drop to draw rectangle

Useful for:
- Defining gate zones for tracking
- Marking calibration points
- Drawing reference areas
- Annotating regions of interest

Keyboard shortcuts:
  1 = Point mode
  2 = Polygon mode
  3 = Rectangle mode
  R = Reset current drawing
  C = Clear all
  S = Save zone
  F = Refresh snapshot (capture new frame)
  Q = Quit and export

Usage:
    python3 mark_frame.py <username> <password>
"""

import sys
import cv2
import numpy as np

# Camera settings
CAMERA_IP = "192.168.1.4"
CAMERA_PORT = 554
STREAM = "stream2"  # 720P

# Drawing modes
MODE_POINT = 1
MODE_POLYGON = 2
MODE_RECTANGLE = 3

# Colors (BGR)
COLOR_POINT = (0, 255, 0)      # Green
COLOR_POLYGON = (255, 0, 255)  # Magenta
COLOR_RECTANGLE = (0, 255, 255) # Yellow
COLOR_ACTIVE = (0, 165, 255)   # Orange (drawing in progress)

class FrameMarker:
    def __init__(self):
        self.mode = MODE_RECTANGLE  # Start with rectangle mode
        self.current_points = []
        self.saved_zones = []  # List of (mode, points) tuples

        # Rectangle drawing state
        self.rect_start = None
        self.rect_dragging = False

        # Polygon state
        self.polygon_closed = False

    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse events for all modes."""

        if self.mode == MODE_POINT:
            if event == cv2.EVENT_LBUTTONDOWN:
                self.current_points.append((x, y))
                print(f"Point added: ({x}, {y})")

        elif self.mode == MODE_POLYGON:
            if event == cv2.EVENT_LBUTTONDOWN:
                if not self.polygon_closed:
                    self.current_points.append((x, y))
                    print(f"Polygon point {len(self.current_points)}: ({x}, {y})")

        elif self.mode == MODE_RECTANGLE:
            if event == cv2.EVENT_LBUTTONDOWN:
                self.rect_start = (x, y)
                self.rect_dragging = True
                self.current_points = [(x, y)]

            elif event == cv2.EVENT_MOUSEMOVE:
                if self.rect_dragging:
                    # Update rectangle as we drag
                    self.current_points = [
                        self.rect_start,
                        (x, self.rect_start[1]),  # Top-right
                        (x, y),                    # Bottom-right
                        (self.rect_start[0], y)    # Bottom-left
                    ]

            elif event == cv2.EVENT_LBUTTONUP:
                if self.rect_dragging:
                    self.rect_dragging = False
                    # Finalize rectangle
                    self.current_points = [
                        self.rect_start,
                        (x, self.rect_start[1]),
                        (x, y),
                        (self.rect_start[0], y)
                    ]
                    print(f"Rectangle: TL={self.rect_start}, BR=({x}, {y})")
                    print(f"  Width: {abs(x - self.rect_start[0])}, Height: {abs(y - self.rect_start[1])}")

    def draw_overlay(self, frame):
        """Draw all zones and current drawing on frame."""
        overlay = frame.copy()

        # Draw saved zones
        for zone_mode, points in self.saved_zones:
            if zone_mode == MODE_POINT:
                for pt in points:
                    cv2.circle(overlay, pt, 8, COLOR_POINT, -1)
                    cv2.circle(overlay, pt, 10, (255, 255, 255), 2)
            elif zone_mode == MODE_POLYGON:
                pts = np.array(points, np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(overlay, [pts], True, COLOR_POLYGON, 2)
                for pt in points:
                    cv2.circle(overlay, pt, 5, COLOR_POLYGON, -1)
            elif zone_mode == MODE_RECTANGLE:
                pts = np.array(points, np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(overlay, [pts], True, COLOR_RECTANGLE, 2)

        # Draw current drawing
        if self.current_points:
            if self.mode == MODE_POINT:
                for pt in self.current_points:
                    cv2.circle(overlay, pt, 8, COLOR_ACTIVE, -1)
                    cv2.circle(overlay, pt, 10, (255, 255, 255), 2)
            elif self.mode == MODE_POLYGON:
                if len(self.current_points) > 1:
                    pts = np.array(self.current_points, np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    cv2.polylines(overlay, [pts], False, COLOR_ACTIVE, 2)
                for pt in self.current_points:
                    cv2.circle(overlay, pt, 5, COLOR_ACTIVE, -1)
            elif self.mode == MODE_RECTANGLE:
                if len(self.current_points) == 4:
                    pts = np.array(self.current_points, np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    color = COLOR_ACTIVE if self.rect_dragging else COLOR_RECTANGLE
                    cv2.polylines(overlay, [pts], True, color, 2)

        # Draw mode indicator
        mode_names = {MODE_POINT: "POINT", MODE_POLYGON: "POLYGON", MODE_RECTANGLE: "RECTANGLE"}
        mode_text = f"Mode: {mode_names[self.mode]} (press 1/2/3 to change)"
        cv2.putText(overlay, mode_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Draw help text
        help_lines = [
            "1=Point | 2=Polygon | 3=Rectangle",
            "R=Reset | C=Clear all | S=Save | Q=Quit"
        ]
        if self.mode == MODE_POLYGON and self.current_points:
            help_lines.insert(0, "ENTER=Close polygon")

        y_offset = 60
        for line in help_lines:
            cv2.putText(overlay, line, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 25

        # Draw zone count
        info_text = f"Saved zones: {len(self.saved_zones)}"
        cv2.putText(overlay, info_text, (10, frame.shape[0] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return overlay

    def save_current_zone(self):
        """Save current drawing as a zone."""
        if self.current_points:
            self.saved_zones.append((self.mode, self.current_points.copy()))
            print(f"Zone saved: {len(self.saved_zones)} total")
            self.current_points = []
            self.polygon_closed = False
            self.rect_dragging = False
            self.rect_start = None

    def reset_current(self):
        """Reset current drawing."""
        self.current_points = []
        self.polygon_closed = False
        self.rect_dragging = False
        self.rect_start = None
        print("Current drawing reset")

    def clear_all(self):
        """Clear all zones."""
        self.saved_zones = []
        self.current_points = []
        self.polygon_closed = False
        self.rect_dragging = False
        self.rect_start = None
        print("All zones cleared")

    def export_zones(self):
        """Export zones as Python code."""
        if not self.saved_zones:
            print("No zones to export")
            return

        print("\n" + "="*60)
        print("MARKED ZONES (Copy-paste ready for Python code)")
        print("="*60)

        for i, (zone_mode, points) in enumerate(self.saved_zones):
            mode_names = {MODE_POINT: "POINT", MODE_POLYGON: "POLYGON", MODE_RECTANGLE: "RECTANGLE"}
            print(f"\n# Zone {i+1}: {mode_names[zone_mode]}")

            if zone_mode == MODE_POINT:
                for j, (x, y) in enumerate(points):
                    print(f"point_{i+1}_{j+1} = ({x}, {y})")
            elif zone_mode == MODE_POLYGON:
                print(f"polygon_{i+1} = np.float32([")
                for x, y in points:
                    print(f"    [{x}, {y}],")
                print("])")
            elif zone_mode == MODE_RECTANGLE:
                x_coords = [pt[0] for pt in points]
                y_coords = [pt[1] for pt in points]
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                print(f"rect_{i+1} = {{")
                print(f"    'x': {x_min},")
                print(f"    'y': {y_min},")
                print(f"    'width': {x_max - x_min},")
                print(f"    'height': {y_max - y_min}")
                print(f"}}")
                print(f"# Or as polygon: np.float32([")
                for x, y in points:
                    print(f"#     [{x}, {y}],")
                print(f"# ])")

        print("\n" + "="*60)


def main():
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))  # Add scripts/ to path
    from camera_utils import load_camera_config

    rtsp_url, camera_ip, camera_port, stream = load_camera_config()

    print("🎥 Connecting to camera...")
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        print("❌ Failed to connect to camera")
        return

    print("✅ Camera connected")
    print("📸 Capturing snapshot...")

    # Capture initial frame
    ret, snapshot = cap.read()
    if not ret:
        print("❌ Failed to capture frame")
        cap.release()
        return

    # Close camera connection (we work on static snapshot)
    cap.release()
    print("✅ Snapshot captured (working on frozen frame)")

    print("\nFrame Marker Tool")
    print("=" * 50)
    print("Modes:")
    print("  1 = POINT mode (click to place points)")
    print("  2 = POLYGON mode (click points, ENTER to close)")
    print("  3 = RECTANGLE mode (drag and drop)")
    print("\nControls:")
    print("  R = Reset current drawing")
    print("  C = Clear all zones")
    print("  S = Save current zone")
    print("  F = Refresh snapshot (capture new frame)")
    print("  Q = Quit and export\n")

    marker = FrameMarker()
    window_name = "Mark Frame"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window_name, marker.mouse_callback)

    while True:
        # Draw overlay on frozen snapshot
        display_frame = marker.draw_overlay(snapshot)
        cv2.imshow(window_name, display_frame)

        # Handle keyboard
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q') or key == ord('Q'):
            # Save current zone if any
            if marker.current_points:
                marker.save_current_zone()
            break
        elif key == ord('1'):
            marker.mode = MODE_POINT
            print("Switched to POINT mode")
        elif key == ord('2'):
            marker.mode = MODE_POLYGON
            print("Switched to POLYGON mode")
        elif key == ord('3'):
            marker.mode = MODE_RECTANGLE
            print("Switched to RECTANGLE mode")
        elif key == ord('r') or key == ord('R'):
            marker.reset_current()
        elif key == ord('c') or key == ord('C'):
            marker.clear_all()
        elif key == ord('s') or key == ord('S'):
            marker.save_current_zone()
        elif key == ord('f') or key == ord('F'):
            # Refresh snapshot
            print("📸 Refreshing snapshot...")
            temp_cap = cv2.VideoCapture(rtsp_url)
            if temp_cap.isOpened():
                ret, new_snapshot = temp_cap.read()
                if ret:
                    snapshot = new_snapshot
                    print("✅ Snapshot refreshed")
                else:
                    print("⚠️ Failed to capture new frame")
                temp_cap.release()
            else:
                print("⚠️ Failed to reconnect to camera")
        elif key == 13:  # ENTER key
            if marker.mode == MODE_POLYGON and marker.current_points:
                marker.save_current_zone()

    cv2.destroyAllWindows()

    # Export zones
    marker.export_zones()
    print("\n✅ Done!")


if __name__ == '__main__':
    main()
