# SafePath Hardware Wiring & Interface Guide

This document describes the complete electrical wiring, pin assignments, and schematic interconnections for the **SafePath AI Assistive Cap System** (matching the EasyEDA schematic and system architecture).

---

## 1. System Hardware Components
| Component | Model / Specification | Purpose | Interfacing Protocol |
| :--- | :--- | :--- | :--- |
| **Main Processing Unit** | Raspberry Pi 5 (4GB / 8GB) | AI logic, Camera feed processing, MQTT client | GPIO, CSI, USB 3.0, UART |
| **Co-Processor Node** | NodeMCU v2 / ESP8266-12E | Offloads ultrasonic sensor polling | USB-UART Serial (115200 baud) |
| **Obstacle Sensor** | HC-SR04 Ultrasonic Sonar | 2cm - 400cm distance measurement | 10μs Trigger / Echo pulses |
| **Vision Camera** | Raspberry Pi Camera Module v2 (8MP IMX219) | Real-time video frame capture | CSI Ribbon / USB |
| **GPS Module** | u-blox NEO-7M | Real-time latitude, longitude & speed | TTL UART (9600 baud, NMEA-0183) |
| **Emergency Help Button** | SPST Tactile Momentary Switch | Immediate SOS triggering | Digital GPIO Input (Interrupt) |
| **Mode Switch Button** | SPST Tactile Push Switch | Toggle Obstacle / Face / Currency modes | Digital GPIO Input (Interrupt) |
| **Audio Feedback** | 3.5mm Headset or Bluetooth Earphone | Text-to-Speech audio narration | ALSA / PulseAudio |
| **Power Management** | Rechargeable Li-Ion Battery Pack with BMS | Portable 5V / 3A-5A regulated power | USB Type-C |

---

## 2. Raspberry Pi 5 GPIO Pinout Mapping

| Raspberry Pi Pin | BCM GPIO | Hardware Device Pin | Function / Description |
| :--- | :--- | :--- | :--- |
| **Pin 1** | 3.3V Power | GPS VCC (or 5V if supported) | Power source for 3.3V logic |
| **Pin 2** | 5.0V Power | HC-SR04 VCC | 5V Power for ultrasonic transducers |
| **Pin 6** | Ground (GND) | Common GND | System Ground reference |
| **Pin 8** | GPIO 14 (TXD) | NEO-7M RXD | Serial transmission from Pi to GPS |
| **Pin 10** | GPIO 15 (RXD) | NEO-7M TXD | Serial receive of NMEA strings ($GPGGA, $GPRMC) |
| **Pin 11** | GPIO 17 | Mode Switch Button | Active LOW mode toggle (Internal Pull-Up) |
| **Pin 13** | GPIO 27 | Emergency SOS Button | Active LOW emergency trigger (Internal Pull-Up) |
| **Pin 16** | GPIO 23 | HC-SR04 TRIG | 10μs Trigger pulse to initiate ultrasonic burst |
| **Pin 18** | GPIO 24 | HC-SR04 ECHO (via divider) | Receives roundtrip echo pulse (3.3V level) |
| **Pin 20** | Ground (GND) | HC-SR04 GND | Ultrasonic Ground |

> [!WARNING]
> **5V to 3.3V Voltage Divider on HC-SR04 Echo Pin:**
> The HC-SR04 Echo pin outputs 5V logic. Raspberry Pi GPIO pins tolerate a maximum of 3.3V. You **must** connect a voltage divider:
> `HC-SR04 Echo ---> [ 1 kΩ Resistor ] ---> GPIO 24 (Pin 18)`
> `                                     |`
> `                                [ 2 kΩ Resistor ]`
> `                                     |`
> `                                   GND`

---

## 3. ESP8266 Co-Processor Wiring (NodeMCU v2 - EasyEDA Schematic)

As designed in the project EasyEDA schematic (page 35), the ESP8266 can offload up to three sonar sensors (Center, Left, Right):

```
                   +------------------------+
                   |     NodeMCU ESP8266    |
                   |                        |
[Sonar Center Trig]| D1 (GPIO 5)            |
[Sonar Center Echo]| D2 (GPIO 4)            |
                   |                        |
[Sonar Left  Trig] | D5 (GPIO 14)           |
[Sonar Left  Echo] | D6 (GPIO 12)           |
                   |                        |
[Sonar Right Trig] | D7 (GPIO 13)           |
[Sonar Right Echo] | D8 (GPIO 15)           |
                   |                        |
[Micro-USB Port]   | === USB Serial Cable ===> Raspberry Pi 5 USB Port
                   +------------------------+
```

---

## 4. Speed of Sound Temperature Calibration

The ultrasonic module uses the temperature-compensated speed of sound formula:
$$c = 331.5 + 0.607 \times T \quad (\text{m/s})$$

Where $T$ is the ambient temperature in °C.
- At 20°C: $c \approx 343.64\text{ m/s}$
- At 25°C: $c \approx 346.68\text{ m/s}$
- At 35°C: $c \approx 352.75\text{ m/s}$

The measured distance is calculated as:
$$\text{Distance (cm)} = \frac{\text{Echo Pulse Duration (μs)} \times (c \times 100 / 10^6)}{2}$$
