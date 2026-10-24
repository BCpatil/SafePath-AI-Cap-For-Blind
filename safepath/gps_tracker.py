"""
GPS Tracking Module for SafePath AI Cap
Interfaces with u-blox NEO-7M GPS receiver via UART (9600 bps).
Parses NMEA-0183 ($GPGGA and $GPRMC) sentences to extract real-time location.
"""

import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("SafePath.GPS")


@dataclass
class GPSCoordinates:
    """Represents a geographic location fix."""
    latitude: float
    longitude: float
    altitude_m: float
    speed_kmh: float
    satellites: int
    has_fix: bool
    timestamp: str

    def to_maps_url(self) -> str:
        """Returns direct Google Maps tracking link."""
        return f"https://maps.google.com/?q={self.latitude:.6f},{self.longitude:.6f}"


class GPSTracker:
    """
    u-blox NEO-7M GPS parser over serial UART.
    Includes simulated fallback coordinates for offline or indoor testing.
    """

    def __init__(
        self,
        port: str = "/dev/ttyAMA0",
        baud_rate: int = 9600,
        use_simulation: bool = False,
    ):
        self.port = port
        self.baud_rate = baud_rate
        self.use_simulation = use_simulation

        self._serial = None
        self._is_running = False
        self._worker_thread = None

        # Default fallback coordinate (Bengaluru, Karnataka)
        self.current_location = GPSCoordinates(
            latitude=12.971598,
            longitude=77.594566,
            altitude_m=920.0,
            speed_kmh=0.0,
            satellites=7,
            has_fix=True,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        if not self.use_simulation:
            self._connect_serial()

        if self._serial:
            self.start()

    def _connect_serial(self):
        """Attempts to open UART serial port to u-blox NEO-7M."""
        try:
            import serial
            self._serial = serial.Serial(self.port, self.baud_rate, timeout=1.0)
            logger.info(f"Opened GPS serial connection on {self.port} at {self.baud_rate} bps.")
        except Exception as e:
            logger.info(f"GPS serial unavailable on {self.port} ({e}). Using simulated GPS.")
            self._serial = None
            self.use_simulation = True

    def start(self):
        """Starts background reader thread for continuous NMEA parsing."""
        if not self._is_running and self._serial:
            self._is_running = True
            self._worker_thread = threading.Thread(target=self._read_nmea_loop, daemon=True)
            self._worker_thread.start()

    def stop(self):
        """Stops background reader thread."""
        self._is_running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
        if self._serial and self._serial.is_open:
            self._serial.close()

    def _read_nmea_loop(self):
        """Reads incoming NMEA strings from NEO-7M."""
        while self._is_running and self._serial:
            try:
                line = self._serial.readline().decode("ascii", errors="replace").strip()
                if line.startswith("$GPGGA") or line.startswith("$GNGGA"):
                    self._parse_gga(line)
                elif line.startswith("$GPRMC") or line.startswith("$GNRMC"):
                    self._parse_rmc(line)
            except Exception as e:
                logger.debug(f"NMEA read exception: {e}")
                time.sleep(0.1)

    def _convert_nmea_to_decimal(self, raw_coord: str, direction: str) -> Optional[float]:
        """Converts NMEA DDMM.MMMM format to decimal degrees."""
        if not raw_coord or not direction:
            return None
        try:
            # Degrees are first 2 digits for latitude, first 3 for longitude
            split_idx = 2 if direction in ["N", "S"] else 3
            degrees = float(raw_coord[:split_idx])
            minutes = float(raw_coord[split_idx:])
            decimal = degrees + (minutes / 60.0)
            if direction in ["S", "W"]:
                decimal = -decimal
            return decimal
        except Exception:
            return None

    def _parse_gga(self, line: str):
        """Parses $GPGGA Global Positioning System Fix Data."""
        parts = line.split(",")
        if len(parts) > 9:
            fix_quality = parts[6]
            if fix_quality != "0" and parts[2] and parts[4]:
                lat = self._convert_nmea_to_decimal(parts[2], parts[3])
                lon = self._convert_nmea_to_decimal(parts[4], parts[5])
                sats = int(parts[7]) if parts[7].isdigit() else 0
                alt = float(parts[9]) if parts[9] else 0.0

                if lat is not None and lon is not None:
                    self.current_location = GPSCoordinates(
                        latitude=lat,
                        longitude=lon,
                        altitude_m=alt,
                        speed_kmh=self.current_location.speed_kmh,
                        satellites=sats,
                        has_fix=True,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    )

    def _parse_rmc(self, line: str):
        """Parses $GPRMC Recommended Minimum Navigation Information."""
        parts = line.split(",")
        if len(parts) > 8 and parts[2] == "A":  # 'A' = Valid fix
            lat = self._convert_nmea_to_decimal(parts[3], parts[4])
            lon = self._convert_nmea_to_decimal(parts[5], parts[6])
            speed_knots = float(parts[7]) if parts[7] else 0.0
            speed_kmh = round(speed_knots * 1.852, 1)

            if lat is not None and lon is not None:
                self.current_location.latitude = lat
                self.current_location.longitude = lon
                self.current_location.speed_kmh = speed_kmh
                self.current_location.has_fix = True

    def get_coordinates(self) -> GPSCoordinates:
        """Returns the latest GPS coordinates."""
        # Update timestamp if in simulation
        if self.use_simulation:
            self.current_location.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return self.current_location

    def set_simulated_coordinates(self, lat: float, lon: float):
        """Allows testing scripts to set coordinates directly."""
        self.current_location.latitude = lat
        self.current_location.longitude = lon
        self.current_location.has_fix = True
