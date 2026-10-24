"""
SafePath Central System Controller
Coordinates sensor fusion, computer vision inference, audio feedback, and emergency triggers.
Implements the exact closed-loop algorithm defined in the SafePath system architecture.
"""

import logging
import time
from typing import Optional

try:
    import cv2
except ImportError:
    cv2 = None

import numpy as np

import config
from safepath.currency_detector import CurrencyDetector
from safepath.detector import ObjectDetector
from safepath.face_recognizer import FaceRecognizer
from safepath.gps_tracker import GPSTracker
from safepath.mqtt_client import MQTTNotifier
from safepath.sonar_sensor import SonarSensor
from safepath.tts_engine import TTSEngine

logger = logging.getLogger("SafePath.Controller")


class SafePathController:
    """
    Central Controller for SafePath AI Assistive System.
    Manages:
    - Mode switching (Obstacle Detection / Face Recognition / Currency Detection)
    - Ultrasonic distance monitoring and camera capture triggering
    - Deep learning inference routing and spatial partitioning
    - Real-time auditory feedback (TTS)
    - SOS Emergency triggering with GPS tracking and MQTT notification
    """

    def __init__(self, simulation_override: Optional[bool] = None):
        logger.info("Initializing SafePath AI Assistive System...")

        # Determine if running in simulation / desktop mode
        if simulation_override is not None:
            self.is_simulation = simulation_override
        else:
            self.is_simulation = config.SIMULATION_MODE in ["true", "1", "yes"]

        # Current State
        self.current_mode = config.MODE_OBJECT_DETECTION
        self.distance_threshold_cm = config.OBSTACLE_DISTANCE_THRESHOLD_CM
        self.critical_distance_cm = config.CRITICAL_DISTANCE_THRESHOLD_CM
        self.is_running = False
        self._last_speech_time = 0.0

        # Subsystems
        self.tts = TTSEngine(
            speech_rate=config.TTS_SPEECH_RATE,
            volume=config.TTS_VOLUME,
        )

        self.sonar = SonarSensor(
            trigger_pin=config.PIN_TRIGGER,
            echo_pin=config.PIN_ECHO,
            temperature_c=config.DEFAULT_TEMPERATURE_C,
            use_simulation=self.is_simulation,
            esp_serial_port=config.ESP8266_SERIAL_PORT if not self.is_simulation else None,
        )

        self.gps = GPSTracker(
            port=config.GPS_SERIAL_PORT,
            baud_rate=config.GPS_BAUD_RATE,
            use_simulation=self.is_simulation,
        )

        self.mqtt = MQTTNotifier(
            broker=config.MQTT_BROKER,
            port=config.MQTT_PORT,
            device_id=config.DEVICE_ID,
        )

        # AI Subsystems
        self.object_detector = ObjectDetector(
            confidence_threshold=config.DETECTION_CONFIDENCE_THRESHOLD,
            left_boundary=config.ROI_LEFT_BOUNDARY,
            right_boundary=config.ROI_RIGHT_BOUNDARY,
        )

        self.face_recognizer = FaceRecognizer(
            known_faces_dir=config.FACES_DIR,
            cooldown_sec=config.FACE_RECOGNITION_COOLDOWN_SEC,
        )

        self.currency_detector = CurrencyDetector(
            confidence_threshold=config.CURRENCY_CONFIDENCE_THRESHOLD,
        )

        # Camera
        self.camera = None
        self._init_camera()

        # Hardware GPIO Button Setup (Raspberry Pi only)
        self._setup_hardware_buttons()

        # Initial Welcome Narration
        self.tts.speak("Safe Path assistive cap online. Obstacle detection mode activated.", priority=1)
        logger.info("SafePath initialization complete.")

    def _init_camera(self):
        """Initializes USB or CSI camera feed."""
        if cv2 is None:
            self.camera = None
            return

        try:
            self.camera = cv2.VideoCapture(config.CAMERA_INDEX)
            if self.camera.isOpened():
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
                self.camera.set(cv2.CAP_PROP_FPS, config.FRAME_FPS)
                logger.info(f"Camera opened successfully on index {config.CAMERA_INDEX}")
            else:
                logger.warning(f"Could not open camera {config.CAMERA_INDEX}. Synthetic frames will be used.")
                self.camera = None
        except Exception as e:
            logger.warning(f"Camera init error ({e}).")
            self.camera = None

    def _setup_hardware_buttons(self):
        """Configures Raspberry Pi GPIO interrupts for mode and SOS buttons."""
        if not self.is_simulation:
            try:
                import RPi.GPIO as GPIO
                GPIO.setup(config.PIN_MODE_SWITCH, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.setup(config.PIN_EMERGENCY_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

                GPIO.add_event_detect(
                    config.PIN_MODE_SWITCH,
                    GPIO.FALLING,
                    callback=lambda channel: self.cycle_mode(),
                    bouncetime=400,
                )
                GPIO.add_event_detect(
                    config.PIN_EMERGENCY_BUTTON,
                    GPIO.FALLING,
                    callback=lambda channel: self.trigger_emergency_sos(),
                    bouncetime=1000,
                )
                logger.info("Hardware buttons registered via GPIO interrupts.")
            except Exception as e:
                logger.info(f"RPi.GPIO button setup skipped: {e}")

    def cycle_mode(self) -> str:
        """Cycles to the next operational mode and notifies user via speech."""
        idx = config.ALL_MODES.index(self.current_mode)
        next_mode = config.ALL_MODES[(idx + 1) % len(config.ALL_MODES)]
        return self.set_mode(next_mode)

    def set_mode(self, mode: str) -> str:
        """Sets active system mode."""
        if mode in config.ALL_MODES:
            self.current_mode = mode
            mode_announcement = {
                config.MODE_OBJECT_DETECTION: "Obstacle detection mode activated",
                config.MODE_FACE_RECOGNITION: "Face recognition mode activated",
                config.MODE_CURRENCY_DETECTION: "Currency detection mode activated",
            }.get(mode, "Mode switched")
            logger.info(f"Switched mode to: {self.current_mode}")
            self.tts.speak(mode_announcement, priority=1, deduplicate_sec=1.0)
        return self.current_mode

    def trigger_emergency_sos(self, reason: str = "SOS Button Pressed") -> bool:
        """
        Triggers emergency protocol:
        1. Reads GPS coordinates (NEO-7M)
        2. Formats ISO timestamped alert
        3. Publishes MQTT payload to cloud broker
        4. Gives audio confirmation to user
        """
        logger.critical(f"EMERGENCY SOS TRIGGERED: {reason}")
        coords = self.gps.get_coordinates()

        # Immediate audio reassurance to visually impaired user
        self.tts.speak("Emergency alert sent. Location shared with guardian.", priority=0)

        # Broadcast over MQTT
        success = self.mqtt.publish_emergency(
            latitude=coords.latitude,
            longitude=coords.longitude,
            altitude_m=coords.altitude_m,
            mode=self.current_mode,
            additional_info=reason,
        )
        return success

    def capture_frame(self) -> np.ndarray:
        """Captures a video frame from camera or generates a simulated scene."""
        if self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret and frame is not None:
                return frame

        # Fallback synthetic frame with test patterns
        frame = np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), dtype=np.uint8)
        frame[:] = (40, 40, 40)
        if cv2 is not None:
            # Draw spatial guideline partitions for display
            w3 = config.FRAME_WIDTH // 3
            cv2.line(frame, (w3, 0), (w3, config.FRAME_HEIGHT), (70, 70, 70), 1)
            cv2.line(frame, (w3 * 2, 0), (w3 * 2, config.FRAME_HEIGHT), (70, 70, 70), 1)
            cv2.putText(
                frame,
                f"SafePath Cap [Simulated Cam] - Mode: {self.current_mode}",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 200),
                2,
            )
        return frame

    def step(self, external_frame: Optional[np.ndarray] = None) -> dict:
        """
        Executes a single closed-loop iteration matching Algorithm steps 2 to 12.
        Can receive an external frame for testing or uses live camera.
        """
        now = time.time()
        result = {
            "mode": self.current_mode,
            "distance_cm": 0.0,
            "vision_triggered": False,
            "detections": [],
            "speech_narrated": None,
            "gps": None,
            "frame": None,
        }

        # Step 3: Measure distance via Ultrasonic sensor
        distance_cm = self.sonar.get_distance()
        result["distance_cm"] = distance_cm

        # Capture frame
        frame = external_frame if external_frame is not None else self.capture_frame()
        annotated_frame = frame.copy()

        # Mode 1: Object Detection (Conditional on distance or active scanning)
        if self.current_mode == config.MODE_OBJECT_DETECTION:
            # Step 4: Check if obstacle is within predefined threshold
            is_obstacle_close = distance_cm <= self.distance_threshold_cm

            if is_obstacle_close:
                result["vision_triggered"] = True
                # Step 5 & 6: Deep learning inference + spatial partitioning
                obstacles = self.object_detector.detect(frame, current_distance_cm=distance_cm)
                result["detections"] = obstacles

                # Annotate on video frame
                if cv2 is not None:
                    for obs in obstacles:
                        xmin, ymin, xmax, ymax = obs.bbox
                        color = (0, 0, 255) if distance_cm < self.critical_distance_cm else (0, 200, 255)
                        cv2.rectangle(annotated_frame, (xmin, ymin), (xmax, ymax), color, 2)
                        label = f"{obs.class_name} ({obs.position}) - {obs.distance_m}m"
                        cv2.putText(annotated_frame, label, (xmin, max(20, ymin - 10)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # Steps 8 & 9: Generate structured feedback and narrate via TTS
                if obstacles:
                    primary = obstacles[0]
                    # Format: "[Obstacle] on [Left/Center/Right], [distance] meters away"
                    speech_msg = f"{primary.class_name} detected on the {primary.position}, {primary.distance_m} meters away."
                    if distance_cm < self.critical_distance_cm:
                        speech_msg = f"Warning! {primary.class_name} approaching close on {primary.position}!"

                    if (now - self._last_speech_time) > config.AUDIO_ANNOUNCEMENT_INTERVAL_SEC:
                        self.tts.speak(speech_msg, priority=1)
                        self._last_speech_time = now
                        result["speech_narrated"] = speech_msg

        # Mode 2: Face Recognition
        elif self.current_mode == config.MODE_FACE_RECOGNITION:
            faces = self.face_recognizer.process_frame(frame)
            result["detections"] = faces

            for face in faces:
                if cv2 is not None:
                    x, y, w, h = face.bbox
                    color = (0, 255, 0) if face.is_known else (0, 165, 255)
                    cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), color, 2)
                    cv2.putText(annotated_frame, f"{face.name}", (x, max(20, y - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

                if face.should_announce:
                    narration = f"{face.name} in front of you." if face.is_known else "Unfamiliar person in front of you."
                    self.tts.speak(narration, priority=2)
                    result["speech_narrated"] = narration

        # Mode 3: Currency Detection
        elif self.current_mode == config.MODE_CURRENCY_DETECTION:
            curr_result = self.currency_detector.classify_currency(frame)
            if curr_result:
                result["detections"] = [curr_result]
                if cv2 is not None:
                    x, y, w, h = curr_result.bbox
                    cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), (255, 200, 0), 2)
                    cv2.putText(annotated_frame, f"Rs {curr_result.denomination} ({int(curr_result.confidence * 100)}%)",
                                (x, max(20, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)

                if (now - self._last_speech_time) > config.AUDIO_ANNOUNCEMENT_INTERVAL_SEC:
                    self.tts.speak(curr_result.speech_text, priority=1)
                    self._last_speech_time = now
                    result["speech_narrated"] = curr_result.speech_text

        # Append overlay info
        gps_info = self.gps.get_coordinates()
        result["gps"] = gps_info
        if cv2 is not None:
            status_txt = f"Mode: {self.current_mode} | Sonar: {distance_cm:.1f} cm | GPS: {gps_info.latitude:.4f},{gps_info.longitude:.4f}"
            cv2.putText(annotated_frame, status_txt, (10, config.FRAME_HEIGHT - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        result["frame"] = annotated_frame

        # Publish telemetry periodically to cloud MQTT broker
        self.mqtt.publish_telemetry({
            "mode": self.current_mode,
            "distance_cm": distance_cm,
            "latitude": gps_info.latitude,
            "longitude": gps_info.longitude,
            "has_fix": gps_info.has_fix,
        })

        return result

    def cleanup(self):
        """Releases all resources cleanly."""
        logger.info("Cleaning up SafePath resources...")
        self.tts.stop()
        self.sonar.cleanup()
        self.gps.stop()
        self.mqtt.disconnect()
        if self.camera and self.camera.isOpened():
            self.camera.release()
