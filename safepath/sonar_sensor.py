"""
Ultrasonic Sonar Sensor Interface for SafePath AI Cap
Implements distance measurement using HC-SR04 with temperature compensation,
ESP8266 serial bridge support, and virtual simulation for testing.
"""

import logging
import time
from typing import Optional

logger = logging.getLogger("SafePath.Sonar")


class SonarSensor:
    """
    HC-SR04 Ultrasonic Sonar Sensor Controller.
    Implements speed of sound compensation: c = 331.5 + 0.607 * t (m/s)
    """

    def __init__(
        self,
        trigger_pin: int = 23,
        echo_pin: int = 24,
        temperature_c: float = 25.0,
        use_simulation: bool = False,
        esp_serial_port: Optional[str] = None,
        esp_baud_rate: int = 115200,
    ):
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.temperature_c = temperature_c
        self.use_simulation = use_simulation
        self.esp_serial_port = esp_serial_port
        self.esp_baud_rate = esp_baud_rate

        self._gpio_available = False
        self._serial_connection = None
        self._last_distance = 250.0  # default clear distance (cm)

        # Calculate calibrated speed of sound
        self._recalculate_sound_speed()

        # Try connecting via ESP8266 Serial bridge if configured
        if self.esp_serial_port and not self.use_simulation:
            self._init_serial_bridge()

        # If not using serial and not simulation, initialize Raspberry Pi GPIO
        if not self._serial_connection and not self.use_simulation:
            self._init_gpio()

    def _recalculate_sound_speed(self):
        """Calculates temperature-dependent speed of sound in cm/microsecond."""
        # Formula: c = 331.5 + 0.607 * t (m/s)
        # Convert to cm / s: (331.5 + 0.607 * t) * 100
        # Convert to cm / microsecond: (331.5 + 0.607 * t) * 100 / 1,000,000
        speed_mps = 331.5 + (0.607 * self.temperature_c)
        self.speed_cm_per_us = (speed_mps * 100.0) / 1_000_000.0
        logger.debug(f"Speed of sound calibrated to {speed_mps:.2f} m/s at {self.temperature_c}°C")

    def _init_serial_bridge(self):
        """Initializes UART/USB serial connection to ESP8266 sensor node."""
        try:
            import serial
            self._serial_connection = serial.Serial(
                self.esp_serial_port, self.esp_baud_rate, timeout=0.1
            )
            logger.info(f"Connected to ESP8266 Sonar Node on {self.esp_serial_port}")
        except Exception as e:
            logger.warning(f"Could not connect to ESP8266 Serial ({e}). Falling back to GPIO/Simulation.")
            self._serial_connection = None

    def _init_gpio(self):
        """Initializes RPi.GPIO pins."""
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.trigger_pin, GPIO.OUT)
            GPIO.setup(self.echo_pin, GPIO.IN)
            GPIO.output(self.trigger_pin, GPIO.LOW)
            time.sleep(0.05)  # Allow sensor to settle
            self._gpio_available = True
            logger.info(f"HC-SR04 GPIO initialized on Trig:BCM{self.trigger_pin}, Echo:BCM{self.echo_pin}")
        except (ImportError, RuntimeError) as e:
            logger.info(f"RPi.GPIO not accessible ({e}). Enabling simulation mode.")
            self.use_simulation = True

    def get_distance(self) -> float:
        """
        Measures and returns current distance in centimeters (cm).
        Returns value between 2.0 and 400.0 cm.
        """
        # 1. ESP8266 Co-processor stream
        if self._serial_connection and self._serial_connection.is_open:
            try:
                line = self._serial_connection.readline().decode("utf-8").strip()
                if line:
                    # Expected format: "DIST:145.2" or JSON '{"distance":145.2}'
                    if "DIST:" in line:
                        val = float(line.split("DIST:")[1])
                        self._last_distance = max(2.0, min(400.0, val))
                        return self._last_distance
            except Exception as e:
                logger.debug(f"Serial read transient error: {e}")

        # 2. Direct Raspberry Pi GPIO pulse measurement
        if self._gpio_available:
            return self._measure_gpio_pulse()

        # 3. Virtual / Simulation mode
        return self._last_distance

    def _measure_gpio_pulse(self) -> float:
        """Triggers 10us ultrasonic pulse and measures echo roundtrip duration."""
        try:
            import RPi.GPIO as GPIO

            # Send 10us high pulse
            GPIO.output(self.trigger_pin, GPIO.HIGH)
            time.sleep(0.000010)  # 10 microseconds
            GPIO.output(self.trigger_pin, GPIO.LOW)

            pulse_start = time.time()
            timeout = pulse_start + 0.04  # 40ms timeout (max range ~4m roundtrip is ~24ms)

            # Wait for echo to go HIGH
            while GPIO.input(self.echo_pin) == GPIO.LOW:
                pulse_start = time.time()
                if pulse_start > timeout:
                    return self._last_distance

            # Wait for echo to go LOW
            pulse_end = pulse_start
            while GPIO.input(self.echo_pin) == GPIO.HIGH:
                pulse_end = time.time()
                if pulse_end > timeout:
                    return self._last_distance

            pulse_duration_us = (pulse_end - pulse_start) * 1_000_000.0
            distance_cm = (pulse_duration_us * self.speed_cm_per_us) / 2.0
            distance_cm = round(max(2.0, min(400.0, distance_cm)), 1)
            self._last_distance = distance_cm
            return distance_cm
        except Exception as e:
            logger.error(f"GPIO distance measurement failed: {e}")
            return self._last_distance

    def set_simulated_distance(self, distance_cm: float):
        """Allows test suites or simulation GUI to set a simulated distance."""
        self._last_distance = max(2.0, min(400.0, float(distance_cm)))

    def cleanup(self):
        """Releases GPIO and serial resources."""
        if self._gpio_available:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup([self.trigger_pin, self.echo_pin])
            except Exception:
                pass
        if self._serial_connection and self._serial_connection.is_open:
            self._serial_connection.close()
