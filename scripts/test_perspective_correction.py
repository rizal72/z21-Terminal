#!/usr/bin/env python3
"""
Test perspective correction using measured layout points.

Applies homography transformation to "straighten" the oblique camera view.
After correction, pixel distances should be proportional to physical distances.

Usage:
    python3 test_perspective_correction.py <username> <password>
"""

import sys
import cv2
import numpy as np
import os
import glob

# Camera settings
CAMERA_IP = "192.168.1.4"
CAMERA_PORT = 554
STREAM = "stream2"  # 720P

# Layout measurements (from measure_distance.py - 2025-12-30)
# Plastico: 1m (width) x 1.90m (depth)
# ⚠️ Camera has field curvature - homography will correct perspective but residual lens distortion remains

# Version 1 (initial measurement)
SRC_POINTS_V1 = np.float32([
    [7, 246],      # Top-left (far corner)
    [376, 31],     # Top-right (far corner)
    [1095, 44],    # Bottom-right (intermediate point)
    [230, 714]     # Bottom-left (intermediate point)
])

# Version 2 (refined measurement)
SRC_POINTS_V2 = np.float32([
    [15, 259],     # Top-left (far corner)
    [379, 29],     # Top-right (far corner)
    [957, 37],     # Bottom-right (near corner)
    [257, 718]     # Bottom-left (near corner)
])

# Version 3 (hybrid: P1,P2 from V1 + P3,P4 from V2)
SRC_POINTS_V3 = np.float32([
    [7, 246],      # Top-left from V1
    [376, 31],     # Top-right from V1
    [957, 37],     # Bottom-right from V2
    [257, 718]     # Bottom-left from V2
])

# Active version
SRC_POINTS = SRC_POINTS_V3  # Change to V1, V2, or V3 for comparison

# Destination rectangle (straightened view)
# Final proportions: 600:1200 = 1:2 (perfect ratio!)
DST_WIDTH = 600     # 100cm = 1m visible width @ 6px/cm
DST_HEIGHT = 1200   # 200cm = 2m visible depth @ 6px/cm

# Layout reference points (P1-P4 map to these positions in output)
# Leaving space below to show tracks beyond P3-P4
Y_OFFSET = 50       # Small offset from top
LAYOUT_HEIGHT = 950  # Layout portion (1.90m)

DST_POINTS = np.float32([
    [0, Y_OFFSET],                          # Top-left
    [DST_WIDTH, Y_OFFSET],                  # Top-right
    [DST_WIDTH, Y_OFFSET + LAYOUT_HEIGHT],  # Bottom-right
    [0, Y_OFFSET + LAYOUT_HEIGHT]           # Bottom-left
])

# This creates output: 50px top + 950px layout + 200px bottom extension = 1200px total


def apply_perspective_correction(frame):
    """Apply perspective transform to straighten the frame."""
    # Extend source points to include area below P3-P4 (to see tracks)
    # Calculate how much to extend based on layout geometry
    # P3-P4 are at Y~37-718, extend to bottom of frame (Y=720)

    # Create extended source quadrilateral
    p1, p2, p3, p4 = SRC_POINTS

    # Extend P3 and P4 down by moving them proportionally toward frame bottom
    # Add ~50-100px extension to see tracks below
    extend_factor = 1.15  # Extend by 15% beyond P3-P4 line

    # Calculate extension for bottom points
    # P3 (bottom-right): extend right and down
    p3_extended = [p3[0] + (p3[0] - p2[0]) * 0.05, p3[1] + (720 - p3[1]) * 0.3]
    # P4 (bottom-left): extend left and down
    p4_extended = [p4[0] - (p1[0] - p4[0]) * 0.05, p4[1] + (720 - p4[1]) * 0.3]

    src_extended = np.float32([
        p1,           # Top-left (unchanged)
        p2,           # Top-right (unchanged)
        p3_extended,  # Bottom-right (extended)
        p4_extended   # Bottom-left (extended)
    ])

    # Calculate perspective transform matrix
    matrix = cv2.getPerspectiveTransform(src_extended, DST_POINTS)

    # Apply transformation
    corrected = cv2.warpPerspective(frame, matrix, (DST_WIDTH, DST_HEIGHT))

    return corrected, matrix


def draw_layout_overlay(frame):
    """Draw the measured layout quadrilateral on original frame."""
    overlay = frame.copy()

    # Draw quadrilateral
    points = SRC_POINTS.astype(np.int32)
    cv2.polylines(overlay, [points], True, (0, 255, 0), 2)

    # Draw corner markers
    for i, (x, y) in enumerate(points):
        cv2.circle(overlay, (int(x), int(y)), 8, (0, 255, 0), -1)
        cv2.circle(overlay, (int(x), int(y)), 10, (255, 255, 255), 2)
        cv2.putText(overlay, f"P{i+1}", (int(x) + 15, int(y) - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Info text
    cv2.putText(overlay, "Layout: 1m x 1.90m", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    return overlay


def draw_grid_overlay(frame, grid_spacing_cm=20):
    """Draw grid on corrected frame (every 20cm)."""
    overlay = frame.copy()

    # Scale based on height: 1200px ≈ 200cm visible area
    # This gives consistent scale regardless of width adjustments
    px_per_cm = DST_HEIGHT / 200.0  # 1200px / 200cm = 6 px/cm
    grid_spacing_px = int(grid_spacing_cm * px_per_cm)

    # Vertical lines
    for x in range(0, DST_WIDTH, grid_spacing_px):
        cv2.line(overlay, (x, 0), (x, DST_HEIGHT), (0, 255, 0), 1)
        # Label every 40cm
        if x % (grid_spacing_px * 2) == 0:
            cm = int(x / px_per_cm)
            cv2.putText(overlay, f"{cm}cm", (x + 5, 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

    # Horizontal lines
    for y in range(0, DST_HEIGHT, grid_spacing_px):
        cv2.line(overlay, (0, y), (DST_WIDTH, y), (0, 255, 0), 1)
        # Label every 40cm
        if y % (grid_spacing_px * 2) == 0:
            cm = int(y / px_per_cm)
            cv2.putText(overlay, f"{cm}cm", (5, y + 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

    # Info
    cv2.putText(overlay, f"Grid: {grid_spacing_cm}cm | Scale: {px_per_cm:.2f}px/cm",
               (10, DST_HEIGHT - 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(overlay, f"Image: {DST_WIDTH}x{DST_HEIGHT}px | Ratio: 1:{DST_HEIGHT/DST_WIDTH:.2f}",
               (10, DST_HEIGHT - 10),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    return overlay


def test_correction(username, password):
    """Test perspective correction on live feed."""
    rtsp_url = f"rtsp://{username}:{password}@{CAMERA_IP}:{CAMERA_PORT}/{STREAM}"

    print("🎥 Connecting to camera...")
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        print("❌ Failed to connect to camera")
        return

    print("✅ Camera connected")
    print("\nPerspective Correction Test:")
    print(f"  Layout: 1m x 1.90m")
    print(f"  Scale: {DST_WIDTH / 100:.1f} px/cm")
    print(f"  Corrected frame: {DST_WIDTH}x{DST_HEIGHT}px")
    print("\nControls:")
    print("  D: Toggle debug view (show source quadrilateral)")
    print("  G: Toggle grid overlay (20cm spacing)")
    print("  S: Save snapshot")
    print("  Q: Quit\n")

    cv2.namedWindow("Original + Layout", cv2.WINDOW_NORMAL)
    cv2.namedWindow("Corrected View", cv2.WINDOW_NORMAL)

    show_debug = True
    show_grid = True

    # Find next available snapshot number
    existing_snapshots = glob.glob("corrected_snapshot_*.jpg")
    if existing_snapshots:
        # Extract numbers from filenames
        numbers = [int(f.split('_')[-1].replace('.jpg', '')) for f in existing_snapshots]
        snapshot_count = max(numbers)
    else:
        snapshot_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Lost connection")
            break

        # Original frame with layout overlay
        if show_debug:
            display_original = draw_layout_overlay(frame)
        else:
            display_original = frame.copy()

        # Apply perspective correction
        corrected, matrix = apply_perspective_correction(frame)

        # Corrected frame with grid
        if show_grid:
            display_corrected = draw_grid_overlay(corrected)
        else:
            display_corrected = corrected.copy()

        # Display
        cv2.imshow("Original + Layout", display_original)
        cv2.imshow("Corrected View", display_corrected)

        # Handle keyboard
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q') or key == ord('Q'):
            break
        elif key == ord('d') or key == ord('D'):
            show_debug = not show_debug
            print(f"Debug overlay: {'ON' if show_debug else 'OFF'}")
        elif key == ord('g') or key == ord('G'):
            show_grid = not show_grid
            print(f"Grid overlay: {'ON' if show_grid else 'OFF'}")
        elif key == ord('s') or key == ord('S'):
            snapshot_count += 1
            cv2.imwrite(f"corrected_snapshot_{snapshot_count}.jpg", display_corrected)
            cv2.imwrite(f"original_snapshot_{snapshot_count}.jpg", display_original)
            print(f"💾 Saved: corrected_snapshot_{snapshot_count}.jpg + original_snapshot_{snapshot_count}.jpg")

    cap.release()
    cv2.destroyAllWindows()

    print("\n✅ Test complete!")
    print(f"\n📊 Perspective transform matrix:")
    print(matrix)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 test_perspective_correction.py <username> <password>")
        return

    test_correction(sys.argv[1], sys.argv[2])


if __name__ == '__main__':
    main()
