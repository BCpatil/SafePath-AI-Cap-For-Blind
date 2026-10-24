#!/usr/bin/env python3
"""
Face Enrollment Utility for SafePath AI Cap
Allows enrolling caregivers, friends, and family members for facial recognition.

Usage:
    python enroll_faces.py --name "Doctor_Rao" --count 15
"""

import argparse
import logging
import sys
import time
from pathlib import Path
import cv2

import config
from safepath.face_recognizer import FaceRecognizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("SafePath.EnrollFaces")


def parse_args():
    parser = argparse.ArgumentParser(description="Enroll known faces into SafePath database")
    parser.add_argument("--name", type=str, required=True, help="Name of the person (e.g. Caregiver_Sarah)")
    parser.add_argument("--count", type=int, default=15, help="Number of facial snapshots to capture")
    parser.add_argument("--cam", type=int, default=config.CAMERA_INDEX, help="Camera device index")
    return parser.parse_args()


def main():
    args = parse_args()
    clean_name = args.name.strip().replace(" ", "_")
    target_dir = config.FACES_DIR / clean_name
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n--- Enrolling Face for: {clean_name} ---")
    print(f"Target Directory: {target_dir}")
    print(f"Capturing {args.count} face images. Look directly into the camera...\n")

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    cap = cv2.VideoCapture(args.cam)
    if not cap.isOpened():
        logger.error(f"Cannot open camera index {args.cam}")
        sys.exit(1)

    captured_faces = []
    captured_count = 0

    try:
        while captured_count < args.count:
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80))

            display_frame = frame.copy()
            for (x, y, w, h) in faces:
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                face_crop = gray[y : y + h, x : x + w]
                face_resized = cv2.resize(face_crop, (200, 200))
                captured_faces.append(face_resized)

                # Save file
                filepath = target_dir / f"face_{captured_count:03d}.jpg"
                cv2.imwrite(str(filepath), face_resized)
                captured_count += 1
                logger.info(f"Captured snapshot {captured_count}/{args.count} -> {filepath.name}")
                time.sleep(0.15)  # brief pause between captures
                break

            cv2.putText(
                display_frame,
                f"Capturing for '{clean_name}': {captured_count}/{args.count}",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )
            cv2.imshow("SafePath Face Enrollment", display_frame)

            if cv2.waitKey(1) & 0xFF == 27:  # ESC to cancel
                logger.warning("Enrollment canceled by user.")
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()

    if captured_faces:
        recognizer = FaceRecognizer(known_faces_dir=config.FACES_DIR)
        print(f"\nSuccessfully enrolled {len(captured_faces)} images for '{clean_name}'.")
        print("Face database retrained and ready for SafePath assistive mode.\n")


if __name__ == "__main__":
    main()
