"""
SafePath AI Cap for Blind - System Configuration
Defines pinouts, network parameters, computer vision models, and operational thresholds.
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"
FACES_DIR = DATA_DIR / "known_faces"

# Operating Modes
MODE_OBJECT_DETECTION = "OBJECT_DETECTION"
MODE_FACE_RECOGNITION = "FACE_RECOGNITION"
MODE_CURRENCY_DETECTION = "CURRENCY_DETECTION"
ALL_MODES = [MODE_OBJECT_DETECTION, MODE_FACE_RECOGNITION, MODE_CURRENCY_DETECTION]

# Hardware GPIO Pin Assignments (Raspberry Pi BCM)
PIN_TRIGGER = 23            # HC-SR04 Ultrasonic Trigger
PIN_ECHO = 24               # HC-SR04 Ultrasonic Echo
PIN_MODE_SWITCH = 17        # Push button to cycle modes
PIN_EMERGENCY_BUTTON = 27   # SOS help button

# Ultrasonic Distance Sensing Thresholds (cm)
OBSTACLE_DISTANCE_THRESHOLD_CM = 200.0  # Triggers vision analysis if closer than 2.0m
CRITICAL_DISTANCE_THRESHOLD_CM = 80.0   # Immediate warning distance
DEFAULT_TEMPERATURE_C = 25.0            # Used for sound velocity calibration: c = 331.5 + 0.607*t

# Serial Communication Interfaces
GPS_SERIAL_PORT = os.getenv("SAFEPATH_GPS_PORT", "/dev/ttyAMA0")
GPS_BAUD_RATE = 9600

ESP8266_SERIAL_PORT = os.getenv("SAFEPATH_ESP_PORT", "/dev/ttyUSB0")
ESP8266_BAUD_RATE = 115200

# MQTT Cloud Communication
MQTT_BROKER = os.getenv("SAFEPATH_MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("SAFEPATH_MQTT_PORT", "1883"))
MQTT_WS_PORT = int(os.getenv("SAFEPATH_MQTT_WS_PORT", "8000"))
MQTT_KEEPALIVE = 60

DEVICE_ID = "SAFEPATH_CAP_001"
MQTT_TOPIC_EMERGENCY = f"safepath/{DEVICE_ID}/emergency"
MQTT_TOPIC_TELEMETRY = f"safepath/{DEVICE_ID}/telemetry"
MQTT_TOPIC_STATUS = f"safepath/{DEVICE_ID}/status"

# Camera Settings
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_FPS = 30

# Spatial Partitioning Fractions (Left, Center, Right)
ROI_LEFT_BOUNDARY = 0.33
ROI_RIGHT_BOUNDARY = 0.67

# Deep Learning / AI Object Detection Settings
DETECTION_CONFIDENCE_THRESHOLD = 0.45
RELEVANT_OBSTACLE_CLASSES = {
    "person", "bicycle", "car", "motorcycle", "bus", "train", "truck",
    "traffic light", "fire hydrant", "stop sign", "parking meter",
    "bench", "dog", "chair", "sofa", "potted plant", "door", "pole"
}

# Face Recognition Settings
FACE_RECOGNITION_COOLDOWN_SEC = 10.0   # Cooldown to avoid repetitive announcements
FACE_DETECTION_CONFIDENCE = 0.50

# Indian Currency Recognition Settings
CURRENCY_DENOMINATIONS = [10, 20, 50, 100, 200, 500]
CURRENCY_CONFIDENCE_THRESHOLD = 0.60

# Text-to-Speech (TTS) Settings
TTS_SPEECH_RATE = 150    # Words per minute for high clarity
TTS_VOLUME = 1.0         # 0.0 to 1.0
AUDIO_ANNOUNCEMENT_INTERVAL_SEC = 2.5  # Min interval between consecutive regular alerts

# Mock / Simulation Mode
# Automatically enabled if running on non-RPi platforms (e.g. Windows/Mac PC)
SIMULATION_MODE = os.getenv("SAFEPATH_SIMULATION", "auto").lower()
