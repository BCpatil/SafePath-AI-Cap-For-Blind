# Contributing to SafePath AI Cap

Thank you for your interest in contributing to the **SafePath AI Smart Assistive Cap** project! This project aims to bring affordable, open-source AI assistive navigation and emergency telemetry to visually impaired individuals worldwide.

---

## Code of Conduct
We are committed to providing a welcoming, inclusive, and harassment-free environment for everyone. Please be respectful and constructive in all discussions and pull requests.

---

## How Can You Contribute?
1. **Reporting Bugs**: Open an issue detailing your hardware setup (e.g., Raspberry Pi 4 vs 5, camera type), operating system, steps to reproduce, and terminal logs.
2. **Feature Additions**:
   - Enhancing MobileNet SSD model accuracy or quantization (INT8/TFLite).
   - Expanding Indian currency recognition to additional banknote series.
   - Adding haptic feedback support (vibrating motors for directional cues).
   - Integrating Bluetooth Low Energy (BLE) audio headsets.
3. **Improving Documentation**: Fixing typos, improving wiring diagrams, or translating audio prompts.

---

## Development & Testing Workflow
1. Fork and clone the repository.
2. Create a clean Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Run the automated test suite before committing:
   ```bash
   pytest tests/ -v
   # or
   python -m unittest tests/test_safepath.py
   ```
4. Submit a Pull Request targeting the `main` branch with a clear description of changes.
