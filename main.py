#!/usr/bin/env python3
"""
SafePath AI Cap for Blind - Main Application Entrypoint
Runs the real-time AI assistance pipeline on Raspberry Pi 5 / PC.

Usage:
    python main.py
    python main.py --simulate
    python main.py --headless

Interactive Controls (GUI Mode):
    [M] : Cycle Operating Modes (Obstacle -> Face -> Currency)
    [S] : Trigger SOS Emergency Alert
    [+] : Simulate Obstacle Moving Closer (-15 cm)
    [-] : Simulate Obstacle Moving Farther (+15 cm)
    [Q] / [ESC] : Exit Application
"""

import argparse
import logging
import sys
import time
import cv2

import config
from safepath.system_controller import SafePathController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("SafePath.Main")


def parse_args():
    parser = argparse.ArgumentParser(description="SafePath AI Assistive System")
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run in virtual simulation mode without physical hardware",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless terminal mode without graphical OpenCV window",
    )
    parser.add_argument(
        "--mode",
        choices=[
            config.MODE_OBJECT_DETECTION,
            config.MODE_FACE_RECOGNITION,
            config.MODE_CURRENCY_DETECTION,
        ],
        default=config.MODE_OBJECT_DETECTION,
        help="Initial operating mode",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print("=" * 65)
    print("      SAFE PATH: SMART AI CAP & WEARABLE ASSISTIVE SYSTEM       ")
    print("=" * 65)
    print("Hardware: Raspberry Pi 5 | ESP8266 Co-processor | HC-SR04 Sonar")
    print("Vision:   MobileNet-SSD Object Detection + Facial Embeddings   ")
    print("Cloud:    MQTT Emergency GPS Alerting & Guardian Telemetry     ")
    print("=" * 65)

    controller = SafePathController(simulation_override=args.simulate)
    controller.set_mode(args.mode)

    print("\n[ACTIVE CONTROLS]")
    print("  'm' -> Switch Modes (Obstacle / Face / Currency)")
    print("  's' -> Trigger SOS Help Button (Publishes GPS to MQTT)")
    print("  'w' -> Move obstacle closer (-20 cm)")
    print("  'x' -> Move obstacle farther (+20 cm)")
    print("  'q' -> Quit\n")

    simulated_dist = 140.0
    controller.sonar.set_simulated_distance(simulated_dist)

    window_name = "SafePath AI Assistive Cap Feed"
    if not args.headless:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 800, 600)

    try:
        while True:
            # Execute one controller step
            step_output = controller.step()

            # Display GUI window
            if not args.headless and step_output["frame"] is not None:
                cv2.imshow(window_name, step_output["frame"])
                key = cv2.waitKey(30) & 0xFF

                if key in [ord("q"), 27]:  # 'q' or ESC
                    logger.info("Exit command received. Shutting down...")
                    break
                elif key in [ord("m"), ord("M")]:
                    controller.cycle_mode()
                elif key in [ord("s"), ord("S")]:
                    controller.trigger_emergency_sos("User Pressed SOS Button (Keyboard Hotkey)")
                elif key in [ord("w"), ord("W"), ord("+")]:
                    simulated_dist = max(10.0, simulated_dist - 20.0)
                    controller.sonar.set_simulated_distance(simulated_dist)
                    logger.info(f"Simulated Sonar distance adjusted: {simulated_dist:.1f} cm")
                elif key in [ord("x"), ord("X"), ord("-")]:
                    simulated_dist = min(350.0, simulated_dist + 20.0)
                    controller.sonar.set_simulated_distance(simulated_dist)
                    logger.info(f"Simulated Sonar distance adjusted: {simulated_dist:.1f} cm")
            else:
                # In headless mode, sleep slightly between steps
                time.sleep(0.08)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received.")
    finally:
        controller.cleanup()
        if not args.headless:
            cv2.destroyAllWindows()
        print("\nSafePath system safely stopped.")


if __name__ == "__main__":
    main()
