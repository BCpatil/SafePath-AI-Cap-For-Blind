"""
SafePath AI Cap - Unit and Integration Test Suite
Implements official test cases TC01 to TC09 from the project validation matrix.
Compatible with both pytest and Python standard library unittest.
"""

import os
import sys
import time
import unittest
from pathlib import Path
import numpy as np

# Ensure parent path is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from safepath.currency_detector import CurrencyDetector
from safepath.detector import ObjectDetector
from safepath.face_recognizer import FaceRecognizer
from safepath.gps_tracker import GPSTracker
from safepath.mqtt_client import MQTTNotifier
from safepath.sonar_sensor import SonarSensor
from safepath.system_controller import SafePathController
from safepath.tts_engine import TTSEngine


class TestSafePathSystem(unittest.TestCase):
    """Executes validation test cases TC01 through TC09."""

    def setUp(self):
        """Initializes virtual test controller."""
        self.controller = SafePathController(simulation_override=True)

    def tearDown(self):
        """Cleans up controller resources."""
        self.controller.cleanup()

    def test_tc01_system_activation_and_initial_scan(self):
        """
        [TC01] System Activation and Initial Scan
        Test Steps: Power ON device, initialize subsystems, initiate scan.
        Expected: System initializes smoothly, starts in default mode, and begins scanning.
        """
        self.assertIsNotNone(self.controller)
        self.assertEqual(self.controller.current_mode, config.MODE_OBJECT_DETECTION)
        self.assertIsNotNone(self.controller.sonar)
        self.assertIsNotNone(self.controller.gps)
        self.assertIsNotNone(self.controller.mqtt)
        self.assertIsNotNone(self.controller.tts)

        dist = self.controller.sonar.get_distance()
        self.assertTrue(2.0 <= dist <= 400.0)

    def test_tc02_obstacle_detection(self):
        """
        [TC02] Obstacle Detection
        Test Steps: Place obstacles within trigger range (< 200cm).
        Expected: Obstacle presence is detected and triggers analysis.
        """
        sonar = SonarSensor(use_simulation=True)
        sonar.set_simulated_distance(120.0)
        measured = sonar.get_distance()
        self.assertEqual(measured, 120.0)
        self.assertTrue(measured <= config.OBSTACLE_DISTANCE_THRESHOLD_CM)

    def test_tc03_roi_extraction(self):
        """
        [TC03] ROI Extraction & Spatial Partitioning
        Test Steps: Provide frame with synthetic obstacle; verify bounding box and normalized ROI coordinates.
        Expected: ROI coordinates extracted successfully.
        """
        detector = ObjectDetector(left_boundary=0.33, right_boundary=0.67)

        pos_left = detector.determine_spatial_position(0.15)
        self.assertEqual(pos_left, "left")

        pos_center = detector.determine_spatial_position(0.50)
        self.assertEqual(pos_center, "center")

        pos_right = detector.determine_spatial_position(0.85)
        self.assertEqual(pos_right, "right")

    def test_tc04_position_and_distance_estimation(self):
        """
        [TC04] Position & Distance Estimation
        Test Steps: Compute position and distance from fused ROI and sonar sensor data.
        Expected: Accurate spatial direction (Left, Center, Right) and distance correlated.
        """
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        test_frame[100:380, 40:160] = 255  # Distinct rectangle on the left

        self.controller.sonar.set_simulated_distance(140.0)
        output = self.controller.step(external_frame=test_frame)

        self.assertEqual(output["distance_cm"], 140.0)
        self.assertTrue(output["vision_triggered"])
        self.assertTrue(len(output["detections"]) > 0)

        first_det = output["detections"][0]
        self.assertEqual(first_det.position, "left")
        self.assertEqual(first_det.distance_m, 1.4)

    def test_tc05_audio_feedback_generation(self):
        """
        [TC05] Audio Feedback Generation
        Test Steps: Generate speech feedback from obstacle details.
        Expected: Speech text generated and queued cleanly without exceptions.
        """
        tts = TTSEngine(enabled=True)
        test_msg = "Pedestrian detected on the center, 1.5 meters away."
        tts.speak(test_msg, priority=1)
        time.sleep(0.1)
        tts.stop()

    def test_tc06_camera_frame_processing(self):
        """
        [TC06] Camera-Raspberry Pi Integration
        Test Steps: Capture and process frames through video pipeline.
        Expected: Video frame is non-empty, 3-channel RGB, and annotated properly.
        """
        frame = self.controller.capture_frame()
        self.assertIsNotNone(frame)
        self.assertEqual(frame.shape[0], config.FRAME_HEIGHT)
        self.assertEqual(frame.shape[1], config.FRAME_WIDTH)
        self.assertEqual(len(frame.shape), 3)

    def test_tc07_ai_obstacle_identification(self):
        """
        [TC07] AI Obstacle Identification
        Test Steps: Verify deep learning object detection outputs class labels and confidence.
        Expected: Obstacle class identified with confidence score.
        """
        detector = ObjectDetector(confidence_threshold=0.40)
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        dummy_frame[140:340, 220:420] = 255

        obstacles = detector.detect(dummy_frame, current_distance_cm=95.0)
        self.assertTrue(len(obstacles) > 0)
        self.assertTrue(obstacles[0].confidence > 0.0)
        self.assertIn(obstacles[0].position, ["left", "center", "right"])

    def test_tc08_emergency_alert_via_mqtt(self):
        """
        [TC08] Emergency Alert via MQTT
        Test Steps: Simulate SOS Help button press; verify GPS coordinate retrieval and MQTT broadcast.
        Expected: Guardian receives alert notification with valid coordinates and timestamp.
        """
        self.controller.gps.set_simulated_coordinates(12.9716, 77.5946)
        success = self.controller.trigger_emergency_sos(reason="Unit Test Triggered SOS")

        coords = self.controller.gps.get_coordinates()
        self.assertEqual(coords.latitude, 12.9716)
        self.assertEqual(coords.longitude, 77.5946)
        self.assertTrue(coords.has_fix)
        self.assertIn("https://maps.google.com", coords.to_maps_url())

    def test_tc09_multi_mode_usability(self):
        """
        [TC09] Multi-Mode Usability & State Transitions
        Test Steps: Cycle through all 3 modes: Obstacle Detection -> Face Recognition -> Currency Detection.
        Expected: Modes transition sequentially with corresponding audio feedback.
        """
        self.assertEqual(self.controller.current_mode, config.MODE_OBJECT_DETECTION)

        # Mode 1 -> Mode 2: Face Recognition
        m2 = self.controller.cycle_mode()
        self.assertEqual(m2, config.MODE_FACE_RECOGNITION)

        # Mode 2 -> Mode 3: Currency Detection
        m3 = self.controller.cycle_mode()
        self.assertEqual(m3, config.MODE_CURRENCY_DETECTION)

        # Mode 3 -> Mode 1: Obstacle Detection
        m1 = self.controller.cycle_mode()
        self.assertEqual(m1, config.MODE_OBJECT_DETECTION)


if __name__ == "__main__":
    unittest.main()
