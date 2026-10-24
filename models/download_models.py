#!/usr/bin/env python3
"""
Model Downloader for SafePath AI Cap
Downloads pre-trained MobileNet SSD v2 weights and prototxt files for obstacle detection.
"""

import logging
from pathlib import Path
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("SafePath.ModelDownloader")

MODELS_DIR = Path(__file__).resolve().parent

MODELS = {
    "MobileNetSSD_deploy.prototxt": (
        "https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/deploy.prototxt"
    ),
    "MobileNetSSD_deploy.caffemodel": (
        "https://github.com/chuanqi305/MobileNet-SSD/releases/download/v1.0/MobileNetSSD_deploy.caffemodel"
    ),
}


def download_file(url: str, dest_path: Path):
    """Downloads a file with basic progress display."""
    logger.info(f"Downloading {dest_path.name} from {url}...")
    try:
        urllib.request.urlretrieve(url, str(dest_path))
        logger.info(f"Successfully saved {dest_path.name} ({dest_path.stat().st_size} bytes)")
    except Exception as e:
        logger.warning(f"Could not download {dest_path.name}: {e}")
        logger.info("SafePath will seamlessly utilize the embedded vision heuristic fallback.")


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print("\n--- SafePath Deep Learning Model Setup ---")
    for filename, url in MODELS.items():
        dest = MODELS_DIR / filename
        if dest.exists() and dest.stat().st_size > 1000:
            logger.info(f"Model file '{filename}' already present ({dest.stat().st_size} bytes).")
        else:
            download_file(url, dest)
    print("Model check complete.\n")


if __name__ == "__main__":
    main()
