# SafePath: Smart AI Assistive Cap for the Visually Impaired

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform: Raspberry Pi 5](https://img.shields.io/badge/Platform-Raspberry%20Pi%205-red.svg)](https://www.raspberrypi.com/)
[![Microcontroller: ESP8266](https://img.shields.io/badge/Co--Processor-ESP8266%20NodeMCU-00979D.svg)](https://www.espressif.com/)
[![IoT Protocol: MQTT](https://img.shields.io/badge/IoT-MQTT%20QoS%201-orange.svg)](https://mqtt.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests: Passing](https://img.shields.io/badge/Tests-TC01--TC09%20Passed-brightgreen.svg)](tests/)

---

## 📌 Abstract & Overview

Safe and independent navigation remains one of the most critical daily challenges faced by visually impaired individuals. Traditional mobility aids, such as white canes, offer limited physical reach without semantic context, while guide dogs demand extensive training and high maintenance costs.

**SafePath** is an AI-powered, wearable smart assistive system mounted on a lightweight cap. Driven by an embedded **Raspberry Pi 5** and supported by an **ESP8266 co-processor**, the device continuously monitors the user's surroundings through a vision camera and ultrasonic sonar array. SafePath operates in multiple assistive modes with real-time text-to-speech audio feedback and cloud-connected emergency GPS telemetry.

```
       +-------------------------------------------------------------+
       |               SAFEPATH WEARABLE CAP PLATFORM                |
       |                                                             |
       |   [ 8MP Camera Module ]            [ HC-SR04 Sonar Array ]  |
       |             \                                /              |
       |              v                              v               |
       |       +-------------------------------------------+         |
       |       |  Raspberry Pi 5 + ESP8266 Sensor Node     |         |
       |       |  - MobileNet-SSD v2 Object Classification |         |
       |       |  - Spatial Partitioning (Left/Center/Right)|        |
       |       |  - Face Recognition + Cooldown Engine     |         |
       |       |  - Indian Currency Recognition (₹10-₹500) |         |
       |       |  - u-blox NEO-7M GPS Tracking via UART    |         |
       |       +-------------------------------------------+         |
       |            /                      \                         |
       |           v                        v                        |
       |    [TTS Audio Feedback]      [MQTT Emergency Gateway]       |
       |    "Car on Center, 1.4m"    "SOS Alert -> Guardian App"     |
       +-------------------------------------------------------------+
```

---

## 🚀 Key System Features

### 1. Vision-Based Obstacle Detection & Spatial Partitioning
- Utilizes an optimized **MobileNet SSD v2** deep learning architecture for real-time inference on Raspberry Pi 5.
- Classifies pedestrians, vehicles, bicycles, signboards, furniture, and static obstacles.
- **Spatial ROI Partitioning**: The camera view is partitioned into three discrete horizontal zones:
  - **Left**: $0.00 \le x < 0.33$
  - **Center**: $0.33 \le x \le 0.67$
  - **Right**: $0.67 < x \le 1.00$
- Guides the wearer directionally (e.g., *"Pedestrian approaching on the right"*).

### 2. Distance Ranging & Temperature Compensation
- High-frequency ultrasonic ranging ($2\text{ cm} - 400\text{ cm}$) triggers vision-based processing only when obstacles breach the predefined threshold ($< 2.0\text{ m}$), conserving energy.
- Real-time sound velocity calibration based on ambient temperature:
  $$c = 331.5 + 0.607 \times T \quad (\text{m/s})$$

### 3. Face Recognition with Usability Cooldown
- Identifies enrolled caregivers, doctors, and family members using facial embeddings.
- **Cooldown Announcement Suppression**: Once an individual is announced, repetitive alerts are suppressed for a 10-second window to prevent cognitive audio fatigue.

### 4. Indian Currency Denomination Recognition
- Dedicated operational mode to facilitate financial independence during cash transactions.
- Classifies Indian Rupee banknotes: **₹10, ₹20, ₹50, ₹100, ₹200, and ₹500** notes with high confidence ($> 90\%$).

### 5. Emergency SOS Button & Live GPS Telemetry
- A tactile help button triggers an immediate emergency sequence.
- Parses NMEA `$GPGGA` and `$GPRMC` sentences from the **u-blox NEO-7M GPS module**.
- Publishes high-priority alerts with an actionable Google Maps link to cloud MQTT brokers (`broker.hivemq.com`).

### 6. Guardian Remote Web Portal
- Responsive caregiver web dashboard built with HTML5, CSS3, and **Leaflet.js (OpenStreetMap)**.
- Subscribes to MQTT over WebSockets, displaying real-time GPS markers, audio SOS sirens, and obstacle proximity.

---

## 🛠️ Hardware Requirements & Pinout

| Subsystem | Component | Specifications | Interface |
| :--- | :--- | :--- | :--- |
| **Main Processing Unit** | Raspberry Pi 5 | Quad-Core ARM Cortex-A76 @ 2.4GHz, 4GB/8GB LPDDR4X | CSI / USB 3.0 / GPIO |
| **Sensor Co-Processor** | ESP8266 NodeMCU v2 | Tensilica L106 32-bit @ 80-160MHz, Wi-Fi 802.11 b/g/n | Micro-USB to Pi USB |
| **Camera** | Raspberry Pi Camera v2 | 8 Megapixel Sony IMX219, 1080p30 / 720p60 | 15-pin CSI Ribbon |
| **Sonar Sensors** | HC-SR04 | $2\text{ cm} - 400\text{ cm}$ range, 30° cone, $10\mu\text{s}$ pulse | GPIO / ESP8266 Pins |
| **GPS Module** | u-blox NEO-7M | 56-channel engine, 2.5m CEP accuracy, 9600 baud | UART (TXD/RXD) |
| **Power Supply** | Li-Ion Battery Pack with BMS | 5V / 3A-5A regulated power via USB-C | USB-C Power Rail |
| **Audio Output** | 3.5mm Headset / BT Earbuds | Low latency text-to-speech audio feedback | 3.5mm Jack / Bluetooth |

### Pinout Mapping (Raspberry Pi 5)
- **HC-SR04 Trigger**: BCM GPIO 23 (Pin 16)
- **HC-SR04 Echo**: BCM GPIO 24 (Pin 18 via 1kΩ / 2kΩ voltage divider)
- **Mode Switch Button**: BCM GPIO 17 (Pin 11, Pull-Up)
- **Emergency SOS Button**: BCM GPIO 27 (Pin 13, Pull-Up)
- **u-blox NEO-7M GPS TX**: BCM GPIO 15 (Pin 10 / RXD)
- **u-blox NEO-7M GPS RX**: BCM GPIO 14 (Pin 8 / TXD)

*Refer to [hardware/WIRING_DIAGRAM.md](hardware/WIRING_DIAGRAM.md) and [hardware/schematic_pinout.csv](hardware/schematic_pinout.csv) for detailed circuit schematics.*

---

## 📂 Project Repository Structure

```
SafePath-AI-Cap-For-Blind/
│
├── .github/
│   └── workflows/
│       └── python-tests.yml        # Continuous integration pipeline (CI/CD)
│
├── data/
│   └── known_faces/                # Enrolled facial images database
│
├── docs/
│   └── SYSTEM_ARCHITECTURE.md      # DFD Level-0/1, UML Sequence, Data Dictionary
│
├── firmware/
│   └── esp8266_sonar_node/
│       └── esp8266_sonar_node.ino  # NodeMCU/ESP8266 firmware for ultrasonic ranging
│
├── guardian_dashboard/
│   ├── index.html                  # Responsive Caregiver web portal
│   ├── style.css                   # Dark-themed UI with pulse SOS alerts
│   └── app.js                      # Leaflet.js GPS map & MQTT over WebSockets
│
├── hardware/
│   ├── WIRING_DIAGRAM.md           # Full pinout and voltage divider diagrams
│   └── schematic_pinout.csv        # Hardware pin allocation matrix
│
├── models/
│   └── download_models.py          # Script to fetch MobileNet-SSD weights
│
├── safepath/
│   ├── __init__.py
│   ├── currency_detector.py        # Indian Rupee banknote classification engine
│   ├── detector.py                 # MobileNet SSD object detection & spatial ROI
│   ├── face_recognizer.py          # Facial embeddings & cooldown suppression
│   ├── gps_tracker.py              # NEO-7M NMEA-0183 GPS parser
│   ├── mqtt_client.py              # Cloud MQTT emergency and telemetry client
│   ├── sonar_sensor.py             # HC-SR04 sonar module with temperature calibration
│   ├── system_controller.py        # Closed-loop coordinator & state machine
│   └── tts_engine.py               # Priority-queued Text-to-Speech audio engine
│
├── tests/
│   └── test_safepath.py            # Comprehensive test suite (TC01 - TC09)
│
├── .gitignore                      # Git ignore patterns
├── config.py                       # Global system configuration
├── CONTRIBUTING.md                 # Contribution guidelines
├── enroll_faces.py                 # CLI utility to capture and enroll new faces
├── LICENSE                         # MIT License
├── main.py                         # Application entrypoint (Interactive GUI / CLI)
└── requirements.txt                # Python package dependencies
```

---

## ⚡ Installation & Quickstart

### 1. Prerequisites
- Python 3.10, 3.11, or 3.12
- Git
- (On Raspberry Pi OS):
  ```bash
  sudo apt-get update
  sudo apt-get install -y python3-pip python3-opencv espeak libespeak1
  ```

### 2. Setup Virtual Environment
```bash
git clone https://github.com/<your-username>/SafePath-AI-Cap-For-Blind.git
cd SafePath-AI-Cap-For-Blind

python -m venv venv
# On Linux / Raspberry Pi:
source venv/bin/activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 3. Download Deep Learning Weights (Optional)
```bash
python models/download_models.py
```
*(If weights are not downloaded, SafePath's automated computer vision heuristics will activate seamlessly).*

---

## 🎮 Running SafePath

### A. Live Interactive Mode (Desktop Simulation / Webcam)
```bash
python main.py
```
**Interactive Hotkeys:**
- `[M]` : Cycle Operating Mode (**Obstacle Detection** ➔ **Face Recognition** ➔ **Currency Detection**)
- `[S]` : Trigger **SOS Emergency Help** (Transmits coordinates to cloud MQTT)
- `[W]` / `[+]` : Simulate obstacle moving closer ($-20\text{ cm}$)
- `[X]` / `[-]` : Simulate obstacle moving farther ($+20\text{ cm}$)
- `[Q]` / `[ESC]` : Exit cleanly

### B. Headless Mode (On Raspberry Pi Cap)
```bash
python main.py --headless
```

### C. Enrolling Known Faces
To register a caregiver or doctor:
```bash
python enroll_faces.py --name "Caregiver_Sarah" --count 15
```

### D. Launching the Guardian Portal
Simply open `guardian_dashboard/index.html` in any web browser. When an emergency SOS button is pressed on the wearable cap, the portal will immediately:
1. Sound an audible alarm siren.
2. Flash a red emergency alert banner.
3. Center the OpenStreetMap view to the wearer's exact latitude and longitude.
4. Provide a direct 1-click link to Google Maps navigation.

---

## 🧪 Test Case Validation Matrix

All test cases from the official project validation plan have been automated and verified:

| Test ID | Module Tested | Test Steps | Expected Output | Status |
| :--- | :--- | :--- | :--- | :--- |
| **TC01** | System Activation | Power ON, initiate subsystem scan | Subsystems initialize; continuous scanning active | **PASS** |
| **TC02** | Obstacle Detection | Simulated obstacle placed $< 200\text{ cm}$ | Distance detected, triggers vision analysis | **PASS** |
| **TC03** | ROI Extraction | Feed frame, partition into spatial regions | Left, Center, Right partitions accurately identified | **PASS** |
| **TC04** | Position & Distance | Correlate visual ROI with sonar sensor data | Correct directional position and meter distance output | **PASS** |
| **TC05** | Audio TTS Feedback | Generate speech alert from obstacle metadata | Priority speech queue processes voice alert | **PASS** |
| **TC06** | Camera Integration | Continuous video frame capture | RGB video frames captured and annotated properly | **PASS** |
| **TC07** | AI Classification | Infer objects from frame | Bounding boxes, classes, and confidence generated | **PASS** |
| **TC08** | Emergency Alert | Press SOS button, query NEO-7M GPS | Alert published to MQTT with valid coordinates & timestamp | **PASS** |
| **TC09** | Usability / Modes | Cycle modes (Obstacle ➔ Face ➔ Currency) | State machine transitions with voice guidance | **PASS** |

### Running the Test Suite:
```bash
# Using Python Standard Library:
python -m unittest tests/test_safepath.py

# Using Pytest:
pytest tests/ -v
```

---

## 📤 Step-by-Step Guide: How to Push to GitHub

Follow these steps to upload this complete project to your personal GitHub account:

### Step 1: Create a New Repository on GitHub
1. Log in to [GitHub](https://github.com/).
2. Click **New Repository** (or visit `https://github.com/new`).
3. Repository name: `SafePath-AI-Cap-For-Blind` (or `SafePath-IoT-Assistive-Device`).
4. Set visibility to **Public** (or **Private**).
5. **Do NOT** initialize with a README, .gitignore, or license (these are already configured in this repo).
6. Click **Create repository**.

### Step 2: Initialize Git in Project Directory
Open your terminal or command prompt inside the `SafePath-AI-Cap-For-Blind` folder:

```bash
cd SafePath-AI-Cap-For-Blind

# Initialize local git repository
git init

# Add all files to staging
git add .

# Create the initial commit
git commit -m "Initial commit: Complete SafePath AI Cap for Blind IoT System"

# Rename default branch to main
git branch -M main

# Link to your newly created GitHub repository (replace with your GitHub URL)
git remote add origin https://github.com/<YOUR-GITHUB-USERNAME>/SafePath-AI-Cap-For-Blind.git

# Push code to GitHub
git push -u origin main
```

Your code, firmware, documentation, tests, and web dashboard are now live on GitHub!

---

## 📜 References
1. Shruti Dambhare, Prof. A. Sakhare, *"Smart stick for Blind: Obstacle Detection, Artificial vision and Real-time assistance via GPS"*, NCICCT, IJCA.
2. Osama Bader AL-Barrm, Jeen Vinouth, *"3D Ultrasonic Stick for Blind"*, IJLTET.
3. Ankit Agarwal, Deepak Kumar, Abhishek Bhardwaj, *"Ultrasonic Stick for Blind"*, IJECS.
4. Rohit Sheth, Surabhi Rajandekar, Shalaka Laddha, Rahul Chaudhari, *"Smart White Cane – An Elegant and Economic Walking Aid"*, AJER.
5. Shashank Chaurasia, K.V.N. Kavitha, *"An Electronic Walking Stick for Blinds"*, ICICES.
6. Kher Chaitrali S. et al., *"An Intelligent Walking Stick for the Blind"*, IJERGS.

---

## 📄 License
This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
