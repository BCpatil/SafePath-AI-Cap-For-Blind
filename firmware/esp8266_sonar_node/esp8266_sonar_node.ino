/*
 * SafePath AI Cap for Blind - ESP8266 Sonar Co-Processor Node
 * 
 * Hardware:
 *   - NodeMCU v2 (ESP8266-12E) / Wemos D1 Mini
 *   - HC-SR04 Ultrasonic Sonar Sensors (Center, Left, Right as per EasyEDA schematic)
 * 
 * Function:
 *   - Offloads continuous ultrasonic ranging from Raspberry Pi 5.
 *   - Computes temperature-compensated distance: c = 331.5 + 0.607 * T (m/s).
 *   - Streams distance readings via USB-UART Serial (115200 baud) to Raspberry Pi.
 *   - Optionally connects to Wi-Fi & MQTT for standalone IoT telemetry.
 */

#include <ESP8266WiFi.h>
#include <PubSubClient.h>

// --- PIN DEFINITIONS (NodeMCU v2 / ESP8266) ---
// Primary Center Sonar Sensor
const int PIN_TRIG_CENTER = D1;  // GPIO5
const int PIN_ECHO_CENTER = D2;  // GPIO4

// Optional Auxiliary Left/Right Sonars (per Schematic Page 35)
const int PIN_TRIG_LEFT   = D5;  // GPIO14
const int PIN_ECHO_LEFT   = D6;  // GPIO12
const int PIN_TRIG_RIGHT  = D7;  // GPIO13
const int PIN_ECHO_RIGHT  = D8;  // GPIO15

// On-board LED indicator
const int PIN_LED = LED_BUILTIN; // Active LOW on NodeMCU

// --- CONFIGURATION ---
const float AMBIENT_TEMP_C = 25.0; // Ambient temperature in °C
float speed_of_sound_cm_per_us;    // Calibrated speed of sound

// Optional Wi-Fi & MQTT Settings (Can be left empty for direct USB Serial operation)
const char* WIFI_SSID     = "Your_WiFi_SSID";
const char* WIFI_PASSWORD = "Your_WiFi_Password";
const char* MQTT_BROKER   = "broker.hivemq.com";
const int   MQTT_PORT     = 1883;
const char* MQTT_TOPIC    = "safepath/SAFEPATH_CAP_001/sonar";

WiFiClient espClient;
PubSubClient mqttClient(espClient);
bool wifi_enabled = false;

// Function to calculate distance using HC-SR04
float measureDistance(int trigPin, int echoPin) {
  // Trigger 10us HIGH pulse
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Measure roundtrip pulse duration in microseconds (max timeout 30ms = ~5m)
  long duration = pulseIn(echoPin, HIGH, 30000);

  if (duration == 0) {
    return 400.0; // Timeout: no obstacle within range
  }

  // Distance = (Duration * Sound Speed) / 2
  float distance_cm = (duration * speed_of_sound_cm_per_us) / 2.0;
  if (distance_cm < 2.0) distance_cm = 2.0;
  if (distance_cm > 400.0) distance_cm = 400.0;
  return distance_cm;
}

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(PIN_TRIG_CENTER, OUTPUT);
  pinMode(PIN_ECHO_CENTER, INPUT);
  digitalWrite(PIN_TRIG_CENTER, LOW);

  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, HIGH); // Turn off LED initially

  // Calculate speed of sound based on temperature formula:
  // c = 331.5 + 0.607 * t (m/s)
  float speed_mps = 331.5 + (0.607 * AMBIENT_TEMP_C);
  speed_of_sound_cm_per_us = (speed_mps * 100.0) / 1000000.0;

  Serial.println("\n[SafePath ESP8266 Sonar Node Initialized]");
  Serial.print("Calibrated Speed of Sound: ");
  Serial.print(speed_mps);
  Serial.println(" m/s");

  // Optional: Connect to WiFi if credentials provided
  if (String(WIFI_SSID) != "Your_WiFi_SSID" && String(WIFI_SSID).length() > 0) {
    Serial.print("Connecting to Wi-Fi ");
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
      delay(500);
      Serial.print(".");
      attempts++;
    }
    if (WiFi.status() == WL_CONNECTED) {
      wifi_enabled = true;
      Serial.println("\nWi-Fi Connected! IP: " + WiFi.localIP().toString());
      mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    } else {
      Serial.println("\nWi-Fi connection timed out. Running in pure Serial mode.");
    }
  }
}

void loop() {
  // Read distance from center sonar sensor
  float distCenter = measureDistance(PIN_TRIG_CENTER, PIN_ECHO_CENTER);

  // Blink indicator LED briefly on obstacle detection (< 150cm)
  if (distCenter < 150.0) {
    digitalWrite(PIN_LED, LOW); // LED ON
  } else {
    digitalWrite(PIN_LED, HIGH); // LED OFF
  }

  // 1. Output Serial telemetry for Raspberry Pi 5
  // Fast parseable format: "DIST:125.4"
  Serial.print("DIST:");
  Serial.println(distCenter, 1);

  // Also output formatted JSON for debugging / logging
  // Serial.printf("{\"distance\":%.1f}\n", distCenter);

  // 2. Publish to MQTT if Wi-Fi is connected
  if (wifi_enabled) {
    if (!mqttClient.connected()) {
      if (mqttClient.connect("SafePath_ESP8266_Node")) {
        Serial.println("Reconnected to MQTT Broker.");
      }
    } else {
      mqttClient.loop();
      char jsonPayload[64];
      snprintf(jsonPayload, sizeof(jsonPayload), "{\"sensor\":\"HC-SR04\",\"distance_cm\":%.1f}", distCenter);
      mqttClient.publish(MQTT_TOPIC, jsonPayload);
    }
  }

  delay(60); // Sample rate: ~16 Hz
}
