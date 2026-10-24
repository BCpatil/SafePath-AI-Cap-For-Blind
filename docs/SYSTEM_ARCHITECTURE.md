# SafePath System Architecture & UML Documentation

This document provides a comprehensive technical overview of the **SafePath AI Wearable Assistive System for the Visually Impaired**, detailing system layers, Data Flow Diagrams (DFD Level 0 & Level 1), Sequence Diagrams, Use Case representations, and the complete Data Dictionary.

---

## 1. System Block Diagram

```mermaid
graph TD
    subgraph Hardware_Inputs["1. Sensing & Input Layer"]
        CAM["Camera Module (8MP CSI / USB)"]
        SONAR["HC-SR04 Ultrasonic Sensor"]
        GPS["u-blox NEO-7M GPS (UART)"]
        BTN_MODE["Mode Switch Button"]
        BTN_SOS["Emergency SOS Button"]
    end

    subgraph Processing_Unit["2. Main Processing & AI Layer (Raspberry Pi 5)"]
        COORDINATOR["Central Controller (Logic & Sensor Fusion)"]
        AI_SSD["MobileNet SSD v2 Object Detection"]
        AI_SPATIAL["Spatial Partitioning (Left / Center / Right)"]
        AI_FACE["Face Recognition & Cooldown Engine"]
        AI_CURRENCY["Indian Currency Classifier (₹10 - ₹500)"]
    end

    subgraph Output_Feedback["3. Output & Audio Feedback Layer"]
        TTS["Text-to-Speech Engine (pyttsx3)"]
        AUDIO_OUT["3.5mm Jack / Bluetooth Headphones"]
    end

    subgraph Cloud_Communication["4. IoT & Cloud Communication Layer"]
        MQTT_CLIENT["Paho MQTT Client"]
        MQTT_BROKER["Cloud MQTT Broker (broker.hivemq.com)"]
        GUARDIAN_APP["Guardian Mobile & Web Portal (Leaflet GPS Map)"]
    end

    CAM --> COORDINATOR
    SONAR --> COORDINATOR
    GPS --> COORDINATOR
    BTN_MODE --> COORDINATOR
    BTN_SOS --> COORDINATOR

    COORDINATOR --> AI_SSD
    AI_SSD --> AI_SPATIAL
    COORDINATOR --> AI_FACE
    COORDINATOR --> AI_CURRENCY

    AI_SPATIAL --> TTS
    AI_FACE --> TTS
    AI_CURRENCY --> TTS
    TTS --> AUDIO_OUT

    COORDINATOR --> MQTT_CLIENT
    MQTT_CLIENT --> MQTT_BROKER
    MQTT_BROKER --> GUARDIAN_APP
```

---

## 2. Level-0 Data Flow Diagram (Context Diagram)

The Level-0 Context DFD models SafePath as a single central process interacting with external entities:
- **Visually Impaired User**: Provides physical movement, mode selection, and SOS help button presses; receives real-time audio guidance.
- **GPS Satellite System**: Supplies continuous NMEA positioning sentences.
- **Guardian / Mobile Application**: Receives real-time telemetry, location updates, and emergency push alerts.

```mermaid
graph LR
    User(["Visually Impaired User"])
    GPS_Sat(["GPS Satellite System"])
    SafePathSystem(("0.0 SafePath Assistive System"))
    Guardian(["Guardian / Mobile App"])

    User -- "Mode Selection, Physical Presence, SOS Button" --> SafePathSystem
    SafePathSystem -- "Auditory Feedback (Obstacle, Face, Currency)" --> User

    GPS_Sat -- "NMEA GPS Coordinates (Lat/Long)" --> SafePathSystem

    SafePathSystem -- "Emergency Alert Notification & Telemetry via MQTT" --> Guardian
```

---

## 3. Level-1 Data Flow Diagram (DFD)

The Level-1 DFD breaks down internal processing into 5 interconnected sub-processes:
1. `1.0 Collect Sensor & Visual Data`
2. `2.0 Coordinate System Logic (Raspberry Pi)`
3. `3.0 Perform AI Inference (SSD, Face, Currency)`
4. `4.0 Generate Audio Output (TTS)`
5. `5.0 Broadcast Emergency (MQTT)`

```mermaid
graph TD
    User(["Visually Impaired User"])
    GPS_Sat(["GPS Satellite System"])
    Guardian(["Guardian / Mobile App"])

    P1(("1.0 Collect Sensor & Visual Data"))
    P2(("2.0 Coordinate System Logic"))
    P3(("3.0 Perform AI Inference"))
    P4(("4.0 Generate Audio Output"))
    P5(("5.0 Broadcast Emergency"))

    User -- "Movement & Scene" --> P1
    User -- "Mode Selection Switch" --> P2
    User -- "SOS Button Press" --> P2

    P1 -- "Raw Distance Data & Video Frames" --> P2
    GPS_Sat -- "Raw NMEA Data" --> P2

    P2 -- "Image Data for Analysis & Mode Flag" --> P3
    P3 -- "Analysis Results (Class, ROI, Confidence)" --> P2

    P2 -- "Structured Speech Text" --> P4
    P4 -- "Audible Voice Alerts" --> User

    P2 -- "Formatted Alert Payload (GPS + Time)" --> P5
    P5 -- "MQTT Push Notification" --> Guardian
```

---

## 4. Sequence Diagram (Closed-Loop Operation)

```mermaid
sequenceDiagram
    autonumber
    actor User as Visually Impaired User
    participant Sonar as Ultrasonic Sensor
    participant Cam as Camera Module
    participant RPi as Raspberry Pi Controller
    participant AI as AI Vision Engine
    participant TTS as Text-to-Speech
    participant GPS as NEO-7M GPS
    participant MQTT as Cloud MQTT Broker
    participant Guardian as Guardian Mobile/Web App

    Note over User, Guardian: Normal Navigation Flow
    User->>Sonar: Moves forward in path
    Sonar->>RPi: Distance < 200 cm detected
    RPi->>Cam: Trigger image frame capture
    Cam-->>RPi: Return current RGB frame
    RPi->>AI: Send frame for MobileNet-SSD inference
    AI->>AI: Classify obstacle + Spatial ROI (Left/Center/Right)
    AI-->>RPi: Return obstacle class, position & bounding box
    RPi->>RPi: Correlate ultrasonic distance with visual obstacle
    RPi->>TTS: Enqueue speech: "Car detected in center, 1.2 meters away"
    TTS-->>User: Spoken voice alert through headset

    Note over User, Guardian: Emergency SOS Flow
    User->>RPi: Presses SOS Help Button
    RPi->>TTS: Spoken reassurance: "Emergency alert sent."
    TTS-->>User: Reassurance audio playback
    RPi->>GPS: Request current Lat/Lon
    GPS-->>RPi: Return valid GPS fix (e.g. 12.9716, 77.5946)
    RPi->>MQTT: Publish emergency JSON payload with Google Maps link
    MQTT->>Guardian: Deliver instant push alert & display pin on live map
```

---

## 5. Complete Data Dictionary

| Data Name | Description | Source | Destination | Data Type / Format |
| :--- | :--- | :--- | :--- | :--- |
| **Physical Presence / Movement** | Indicates movement of user triggering proximity sensing | Visually Impaired User | `1.0 Sensor & Visual Collection` | Boolean / Event |
| **Mode Selection** | User-selected operating mode (`OBJECT_DETECTION`, `FACE_RECOGNITION`, `CURRENCY_DETECTION`) | Visually Impaired User | `2.0 Coordinate System Logic` | String / Enum |
| **Raw Distance Data** | Distance measurements of obstacles ahead | HC-SR04 Ultrasonic Sensor | `2.0 Coordinate System Logic` | Float (cm) |
| **Video Frames** | Live captured environment frames | Camera Module | `2.0 Coordinate System Logic` | Image Frame (RGB array) |
| **Focused Images** | Cropped Region of Interest (ROI) | `2.0 Coordinate System Logic` | `3.0 AI Inference` | Image Tensor |
| **Analysis Results** | Detection results (class, confidence, ROI bbox) | `3.0 AI Inference` | `2.0 Coordinate System Logic` | Structured JSON / Dataclass |
| **Object Type** | Identified obstacle class (person, car, bike, dog, etc.) | `3.0 AI Inference` | `2.0 Coordinate System Logic` | String |
| **Relative Position** | Obstacle direction with respect to user (`left`, `center`, `right`) | `2.0 Coordinate System Logic` | `4.0 Audio Output (TTS)` | String |
| **Estimated Distance** | Approximate proximity from user | `2.0 Coordinate System Logic` | `4.0 Audio Output (TTS)` | Float (meters) |
| **Emergency SOS Signal** | Immediate help signal triggered by tactile button | Visually Impaired User | `2.0 Coordinate System Logic` | Hardware Interrupt Event |
| **GPS Fix Coordinates** | Latitude, Longitude, Altitude, Satellites count | u-blox NEO-7M GPS | `2.0 Coordinate System Logic` | NMEA Decimal Degrees |
| **Formatted Alert Data** | JSON emergency payload with map URL & timestamp | `2.0 Coordinate System Logic` | `5.0 Broadcast Emergency` | JSON Object string |
