"""
MQTT Cloud Communication Client for SafePath AI Cap
Publishes emergency alerts, telemetry, and heartbeats to cloud broker for Guardian Mobile/Web App.
"""

import json
import logging
import time
from typing import Any, Callable, Dict, Optional

try:
    import paho.mqtt.client as mqtt
except ImportError:
    # Dummy mock class for testing environments without paho-mqtt
    class MockMQTTClient:
        MQTT_ERR_SUCCESS = 0
        def __init__(self, *args, **kwargs):
            self.on_connect = None
            self.on_disconnect = None
            self.on_message = None
        def will_set(self, *args, **kwargs): pass
        def connect_async(self, *args, **kwargs): pass
        def loop_start(self): pass
        def loop_stop(self): pass
        def disconnect(self): pass
        def subscribe(self, *args, **kwargs): pass
        def publish(self, topic, payload, qos=0, retain=False):
            class Res:
                rc = 0
            return Res()
    mqtt = MockMQTTClient()
    mqtt.Client = MockMQTTClient
    mqtt.MQTT_ERR_SUCCESS = 0

logger = logging.getLogger("SafePath.MQTT")


class MQTTNotifier:
    """
    Robust MQTT Client handling emergency alerts and device telemetry.
    Supports automatic reconnection and graceful error handling.
    """

    def __init__(
        self,
        broker: str = "broker.hivemq.com",
        port: int = 1883,
        device_id: str = "SAFEPATH_CAP_001",
        on_message_callback: Optional[Callable[[str, str], None]] = None,
    ):
        self.broker = broker
        self.port = port
        self.device_id = device_id
        self.on_message_callback = on_message_callback

        self.topic_emergency = f"safepath/{self.device_id}/emergency"
        self.topic_telemetry = f"safepath/{self.device_id}/telemetry"
        self.topic_status = f"safepath/{self.device_id}/status"

        self.client = mqtt.Client(client_id=f"{self.device_id}_{int(time.time())}")
        self._is_connected = False

        self._setup_callbacks()
        self.connect()

    def _setup_callbacks(self):
        """Sets up connection and message handlers."""
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._is_connected = True
            logger.info(f"Connected to MQTT broker: {self.broker}:{self.port}")
            # Publish online status with Will flag
            status_payload = json.dumps({
                "device_id": self.device_id,
                "status": "ONLINE",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
            self.client.publish(self.topic_status, status_payload, qos=1, retain=True)
            # Subscribe to remote control / ping topic
            self.client.subscribe(f"safepath/{self.device_id}/commands")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._is_connected = False
        logger.warning(f"Disconnected from MQTT broker (code {rc})")

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            logger.info(f"MQTT message received on {msg.topic}: {payload}")
            if self.on_message_callback:
                self.on_message_callback(msg.topic, payload)
        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")

    def connect(self):
        """Asynchronously connects to MQTT broker."""
        try:
            self.client.will_set(
                self.topic_status,
                json.dumps({"device_id": self.device_id, "status": "OFFLINE"}),
                qos=1,
                retain=True,
            )
            self.client.connect_async(self.broker, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            logger.warning(f"MQTT async connect warning: {e}. Will retry automatically.")

    def publish_emergency(
        self,
        latitude: float,
        longitude: float,
        altitude_m: float = 0.0,
        mode: str = "UNKNOWN",
        additional_info: str = "Emergency Help Button Pressed",
    ) -> bool:
        """
        Publishes immediate high-priority SOS emergency alert with GPS coordinates.
        QoS 1 ensures guaranteed delivery to MQTT broker.
        """
        maps_link = f"https://maps.google.com/?q={latitude:.6f},{longitude:.6f}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        alert_data = {
            "event": "EMERGENCY_SOS",
            "device_id": self.device_id,
            "timestamp": timestamp,
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
            "altitude_m": round(altitude_m, 1),
            "maps_url": maps_link,
            "operating_mode": mode,
            "message": additional_info,
            "battery_percent": 88,
        }

        payload_str = json.dumps(alert_data)
        logger.warning(f"BROADCASTING EMERGENCY ALERT TO GUARDIAN: {payload_str}")

        try:
            res = self.client.publish(self.topic_emergency, payload_str, qos=1)
            return res.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            logger.error(f"Failed to publish emergency message: {e}")
            return False

    def publish_telemetry(self, telemetry_data: Dict[str, Any]) -> bool:
        """Publishes routine navigation telemetry to cloud dashboard."""
        try:
            telemetry_data["device_id"] = self.device_id
            telemetry_data["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            payload = json.dumps(telemetry_data)
            self.client.publish(self.topic_telemetry, payload, qos=0)
            return True
        except Exception as e:
            logger.debug(f"Telemetry publish exception: {e}")
            return False

    def is_connected(self) -> bool:
        """Returns True if connected to MQTT broker."""
        return self._is_connected

    def disconnect(self):
        """Cleanly disconnects MQTT loop."""
        try:
            offline_payload = json.dumps({
                "device_id": self.device_id,
                "status": "OFFLINE",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
            self.client.publish(self.topic_status, offline_payload, qos=1, retain=True)
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass
