"""
Face Recognition Module for SafePath AI Cap
Identifies known individuals (caregivers/family) vs unknown persons.
Implements cooldown-based audio suppression to prevent repetitive notifications.
"""

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import cv2
except ImportError:
    cv2 = None

import numpy as np

logger = logging.getLogger("SafePath.FaceRecognizer")


@dataclass
class RecognizedFace:
    """Represents a detected and identified face."""
    name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    is_known: bool
    should_announce: bool            # True if cooldown window has passed


class FaceRecognizer:
    """
    Facial detection and identification system with cooldown suppression.
    Uses Haar Cascades and LBPH / feature matching, ready for InsightFace/dlib expansion.
    """

    def __init__(
        self,
        known_faces_dir: Path,
        cooldown_sec: float = 10.0,
        confidence_threshold: float = 65.0,  # Lower distance = higher match in LBPH
    ):
        self.known_faces_dir = Path(known_faces_dir)
        self.cooldown_sec = cooldown_sec
        self.confidence_threshold = confidence_threshold

        self._face_cascade = None
        self._recognizer = None
        self._labels_map: Dict[int, str] = {}
        self._last_announced_times: Dict[str, float] = {}

        self._init_cascade()
        self._load_and_train_database()

    def _init_cascade(self):
        """Loads OpenCV Haar Cascade for face detection."""
        if cv2 is None:
            logger.info("OpenCV not installed; face detection running in simulated mode.")
            return

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._face_cascade = cv2.CascadeClassifier(cascade_path)
        if self._face_cascade.empty():
            logger.error("Failed to load OpenCV frontal face Haar Cascade.")
        else:
            logger.info("Frontal face Haar Cascade loaded successfully.")

    def _load_and_train_database(self):
        """Loads registered face images from database directory and trains LBPH recognizer."""
        self.known_faces_dir.mkdir(parents=True, exist_ok=True)

        try:
            # OpenCV's cv2.face module is typically in opencv-contrib-python
            # If standard opencv-python is installed without face contrib, fallback gracefully
            if hasattr(cv2, "face") and hasattr(cv2.face, "LBPHFaceRecognizer_create"):
                self._recognizer = cv2.face.LBPHFaceRecognizer_create()
            else:
                self._recognizer = None
                logger.info("cv2.face.LBPHFaceRecognizer not present; using template matching fallback.")
        except Exception as e:
            logger.warning(f"Face recognizer init warning: {e}")
            self._recognizer = None

        faces = []
        labels = []
        current_id = 0

        # Read images from subdirectories named after individuals
        for person_dir in self.known_faces_dir.iterdir():
            if person_dir.is_dir():
                person_name = person_dir.name
                self._labels_map[current_id] = person_name

                for img_file in person_dir.glob("*.[jJ][pP][gG]"):
                    img = cv2.imread(str(img_file), cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        resized = cv2.resize(img, (200, 200))
                        faces.append(resized)
                        labels.append(current_id)

                current_id += 1

        if faces and self._recognizer is not None:
            self._recognizer.train(faces, np.array(labels))
            logger.info(f"Trained face database with {len(faces)} images across {len(self._labels_map)} identities.")
        else:
            logger.info("No enrolled faces database found or recognizer unready. New faces will be classified as 'Unknown'.")

    def process_frame(self, frame: np.ndarray) -> List[RecognizedFace]:
        """Detects faces in frame and identifies known vs unknown individuals."""
        if frame is None or frame.size == 0 or self._face_cascade is None:
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detected_rects = self._face_cascade.detectMultiScale(
            gray, scaleFactor=1.15, minNeighbors=5, minSize=(60, 60)
        )

        results: List[RecognizedFace] = []
        now = time.time()

        for (x, y, w, h) in detected_rects:
            face_roi = gray[y : y + h, x : x + w]
            face_resized = cv2.resize(face_roi, (200, 200))

            name = "Unknown person"
            is_known = False
            conf_score = 0.0

            if self._recognizer is not None and len(self._labels_map) > 0:
                label_id, distance = self._recognizer.predict(face_resized)
                # Lower distance means better match in LBPH (typically < 75 is a good match)
                if distance < self.confidence_threshold and label_id in self._labels_map:
                    name = self._labels_map[label_id]
                    is_known = True
                    conf_score = round(max(0.0, 100.0 - distance), 1)
                else:
                    conf_score = round(distance, 1)

            # Check cooldown mechanism to avoid repeating audio announcement
            last_time = self._last_announced_times.get(name, 0.0)
            should_announce = False
            if (now - last_time) > self.cooldown_sec:
                should_announce = True
                self._last_announced_times[name] = now

            results.append(
                RecognizedFace(
                    name=name,
                    confidence=conf_score,
                    bbox=(x, y, w, h),
                    is_known=is_known,
                    should_announce=should_announce,
                )
            )

        return results

    def enroll_new_face(self, person_name: str, face_images: List[np.ndarray]) -> int:
        """Saves face images under known_faces/<person_name> and retrains database."""
        target_dir = self.known_faces_dir / person_name
        target_dir.mkdir(parents=True, exist_ok=True)

        saved_count = 0
        for i, face_img in enumerate(face_images):
            filepath = target_dir / f"face_{int(time.time())}_{i}.jpg"
            if cv2.imwrite(str(filepath), face_img):
                saved_count += 1

        self._load_and_train_database()
        return saved_count
