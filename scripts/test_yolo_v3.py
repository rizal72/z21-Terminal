#!/usr/bin/env python3
"""
Quick test script for BiancAlice_v3 YOLO model.
Shows all detected locomotives in real-time.
"""

import sys
import cv2
from ultralytics import YOLO
from pathlib import Path

# Camera settings
CAMERA_IP = "192.168.1.4"
CAMERA_PORT = 554
STREAM = "stream2"  # 720P
CONFIDENCE_THRESHOLD = 0.6

# Class names from model
CLASS_NAMES = {
    0: "1_Gr675_017",
    1: "5_D645_014",
    2: "7_E656_239",
    3: "8_E444_056"
}


def test_tracking(username: str, password: str):
    """Test YOLO detection on all 4 locomotives."""

    rtsp_url = f"rtsp://{username}:{password}@{CAMERA_IP}:{CAMERA_PORT}/{STREAM}"

    print("🎥 Connecting to camera...")
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        print("❌ Failed to connect")
        return

    print("✅ Camera connected")
    print("🤖 Loading YOLO model...")

    model = YOLO("models/best.pt")

    print("✅ Model loaded")
    print("🚂 Press Q to quit\n")

    window_name = "BiancAlice v3 Test - All Locomotives"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Run detection
        results = model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)

        # Draw all detections
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                cls = int(box.cls[0])

                class_name = CLASS_NAMES.get(cls, f"Unknown_{cls}")

                # Draw bounding box
                color = [(0, 255, 0), (255, 0, 0), (0, 255, 255), (255, 0, 255)][cls]
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)

                # Draw label
                label = f"{class_name} {conf:.2f}"
                cv2.putText(frame, label, (int(x1), int(y1) - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Show frame
        cv2.imshow(window_name, frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\n✅ Test complete!")


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 test_yolo_v3.py <username> <password>")
        return

    test_tracking(sys.argv[1], sys.argv[2])


if __name__ == '__main__':
    main()
