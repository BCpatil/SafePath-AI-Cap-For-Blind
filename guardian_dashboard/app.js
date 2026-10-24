/**
 * SafePath AI Guardian Dashboard - MQTT Real-time Telemetry & Emergency Map
 */

const CONFIG = {
  deviceId: "SAFEPATH_CAP_001",
  mqttHost: "broker.hivemq.com",
  mqttPort: 8000, // WebSocket port for HiveMQ
  mqttPath: "/mqtt",
  defaultLat: 12.971598,
  defaultLon: 77.594566,
  topics: {
    emergency: "safepath/SAFEPATH_CAP_001/emergency",
    telemetry: "safepath/SAFEPATH_CAP_001/telemetry",
    status: "safepath/SAFEPATH_CAP_001/status",
  },
};

// State variables
let map = null;
let userMarker = null;
let currentCoords = [CONFIG.defaultLat, CONFIG.defaultLon];
let mqttClient = null;
let audioCtx = null;

// Initialize when DOM ready
document.addEventListener("DOMContentLoaded", () => {
  initMap();
  initUIListeners();
  connectMQTT();
});

// Initialize Leaflet Map
function initMap() {
  map = L.map("liveMap").setView(currentCoords, 16);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
  }).addTo(map);

  // Custom User Icon
  const userIcon = L.divIcon({
    className: "custom-user-marker",
    html: `<div style="background-color: #38bdf8; width: 22px; height: 22px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 15px #38bdf8;"></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });

  userMarker = L.marker(currentCoords, { icon: userIcon }).addTo(map);
  userMarker.bindPopup("<b>SafePath Wearer</b><br>Active and transmitting").openPopup();
}

// Setup Event Listeners
function initUIListeners() {
  document.getElementById("btnDismissSos").addEventListener("click", () => {
    document.getElementById("sosAlertBanner").style.display = "none";
    addLog("Guardian acknowledged emergency alert.", "normal");
  });

  document.getElementById("btnCenterMap").addEventListener("click", () => {
    map.setView(currentCoords, 17);
    userMarker.openPopup();
  });

  document.getElementById("btnSimulateSos").addEventListener("click", () => {
    handleEmergencyEvent({
      event: "EMERGENCY_SOS",
      device_id: CONFIG.deviceId,
      timestamp: new Date().toISOString(),
      latitude: currentCoords[0] + (Math.random() - 0.5) * 0.001,
      longitude: currentCoords[1] + (Math.random() - 0.5) * 0.001,
      operating_mode: "OBJECT_DETECTION",
      message: "Test Emergency Triggered from Guardian Dashboard",
      battery_percent: 85,
    });
  });
}

// Connect to HiveMQ Public WebSocket Broker
function connectMQTT() {
  const badge = document.getElementById("brokerStatusBadge");
  const badgeText = document.getElementById("brokerStatusText");

  badge.className = "status-badge connecting";
  badgeText.textContent = "Connecting to Cloud...";

  const clientId = `guardian_web_${Math.random().toString(16).substr(2, 8)}`;
  mqttClient = new Paho.MQTT.Client(CONFIG.mqttHost, CONFIG.mqttPort, CONFIG.mqttPath, clientId);

  mqttClient.onConnectionLost = (responseObject) => {
    badge.className = "status-badge disconnected";
    badgeText.textContent = "Disconnected from Cloud";
    addLog(`MQTT Disconnected: ${responseObject.errorMessage}`, "normal");
    setTimeout(connectMQTT, 5000); // Auto reconnect
  };

  mqttClient.onMessageArrived = (message) => {
    try {
      const topic = message.destinationName;
      const data = JSON.parse(message.payloadString);
      routeMqttMessage(topic, data);
    } catch (e) {
      console.warn("Error parsing MQTT payload", e);
    }
  };

  mqttClient.connect({
    onSuccess: () => {
      badge.className = "status-badge";
      badgeText.textContent = "Connected (HiveMQ Cloud)";
      addLog("Successfully subscribed to SafePath telemetry topics.", "normal");

      // Subscribe to all topics
      mqttClient.subscribe(CONFIG.topics.emergency, { qos: 1 });
      mqttClient.subscribe(CONFIG.topics.telemetry, { qos: 0 });
      mqttClient.subscribe(CONFIG.topics.status, { qos: 1 });
    },
    onFailure: (err) => {
      badge.className = "status-badge disconnected";
      badgeText.textContent = "Connection Failed";
      addLog(`Failed to connect to MQTT broker: ${err.errorMessage}`, "normal");
      setTimeout(connectMQTT, 6000);
    },
    useSSL: false,
    keepAliveInterval: 30,
  });
}

// Route incoming MQTT messages
function routeMqttMessage(topic, data) {
  if (topic === CONFIG.topics.emergency) {
    handleEmergencyEvent(data);
  } else if (topic === CONFIG.topics.telemetry) {
    handleTelemetryUpdate(data);
  } else if (topic === CONFIG.topics.status) {
    document.getElementById("deviceStateBadge").textContent = data.status || "ONLINE";
  }
}

// Handle Emergency SOS Alerts
function handleEmergencyEvent(data) {
  const banner = document.getElementById("sosAlertBanner");
  banner.style.display = "block";

  document.getElementById("sosMessageText").textContent =
    data.message || "Wearer pressed emergency button!";
  document.getElementById("sosTimestamp").innerHTML =
    `<i class="fa-regular fa-clock"></i> ${new Date().toLocaleTimeString()}`;
  document.getElementById("sosCoords").innerHTML =
    `<i class="fa-solid fa-location-dot"></i> Lat: ${data.latitude.toFixed(4)}, Lon: ${data.longitude.toFixed(4)}`;

  const mapsUrl = `https://maps.google.com/?q=${data.latitude},${data.longitude}`;
  document.getElementById("btnGoogleMaps").href = mapsUrl;

  // Move Map
  updateLocation(data.latitude, data.longitude, true);

  // Play Audible SOS Tone
  playSirenTone();

  // Log
  addLog(`EMERGENCY ALERT: ${data.message} at (${data.latitude.toFixed(4)}, ${data.longitude.toFixed(4)})`, "emergency");
}

// Handle Routine Telemetry
function handleTelemetryUpdate(data) {
  if (data.mode) {
    document.getElementById("metricMode").textContent = data.mode.replace("MODE_", "");
  }
  if (data.distance_cm !== undefined) {
    const dist = parseFloat(data.distance_cm);
    document.getElementById("metricDistance").textContent = `${dist.toFixed(0)} cm`;
    const sub = document.getElementById("metricDistanceSub");
    if (dist < 80) {
      sub.textContent = "Obstacle Close!";
      sub.style.color = "#ef4444";
    } else {
      sub.textContent = "Path Clear";
      sub.style.color = "#38bdf8";
    }
  }
  if (data.latitude && data.longitude) {
    updateLocation(data.latitude, data.longitude, false);
  }
}

function updateLocation(lat, lon, isEmergency = false) {
  currentCoords = [lat, lon];
  document.getElementById("coordsDisplay").textContent = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;

  if (userMarker) {
    userMarker.setLatLng(currentCoords);
    if (isEmergency) {
      userMarker.bindPopup(`<b style="color:red;">EMERGENCY SOS ALERT</b><br>Lat: ${lat}<br>Lon: ${lon}`).openPopup();
      map.setView(currentCoords, 18);
    }
  }
}

// Web Audio API SOS Siren Sound
function playSirenTone() {
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(880, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.4);
    osc.frequency.exponentialRampToValueAtTime(880, audioCtx.currentTime + 0.8);
    gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
    gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 1.2);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 1.2);
  } catch (e) {
    console.log("Audio not allowed without prior user interaction.");
  }
}

function addLog(text, type = "normal") {
  const container = document.getElementById("logContainer");
  const div = document.createElement("div");
  div.className = `log-item ${type}`;
  const time = new Date().toLocaleTimeString();
  div.innerHTML = `<span class="log-time">[${time}]</span> <span class="log-text">${text}</span>`;
  container.insertBefore(div, container.firstChild);
}
