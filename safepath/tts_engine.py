"""
Text-to-Speech (TTS) Module for SafePath AI Cap
Provides non-blocking, queued auditory feedback to visually impaired users.
"""

import logging
import queue
import threading
import time

logger = logging.getLogger("SafePath.TTS")


class TTSEngine:
    """Thread-safe, priority-queued Text-to-Speech engine."""

    def __init__(self, speech_rate: int = 150, volume: float = 1.0, enabled: bool = True):
        self.speech_rate = speech_rate
        self.volume = volume
        self.enabled = enabled
        self._speech_queue = queue.PriorityQueue()
        self._is_running = False
        self._worker_thread = None
        self._engine = None
        self._last_spoken_text = ""
        self._last_spoken_time = 0.0

        if self.enabled:
            self._init_engine()
            self.start()

    def _init_engine(self):
        """Initializes pyttsx3 engine safely."""
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.speech_rate)
            self._engine.setProperty("volume", self.volume)
            logger.info("pyttsx3 Text-to-Speech engine initialized successfully.")
        except Exception as e:
            logger.warning(f"pyttsx3 initialization failed ({e}). Falling back to terminal narration.")
            self._engine = None

    def start(self):
        """Starts the speech worker thread."""
        if not self._is_running:
            self._is_running = True
            self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
            self._worker_thread.start()
            logger.debug("TTS worker thread started.")

    def stop(self):
        """Stops the speech worker thread."""
        self._is_running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
        logger.debug("TTS worker thread stopped.")

    def speak(self, text: str, priority: int = 2, deduplicate_sec: float = 2.0):
        """
        Enqueues text for spoken audio.
        Priority 0 = Critical / SOS Emergency
        Priority 1 = Obstacle warning
        Priority 2 = Routine feedback
        """
        if not text or not text.strip():
            return

        clean_text = text.strip()
        now = time.time()

        # Deduplication check for identical message within window
        if clean_text == self._last_spoken_text and (now - self._last_spoken_time) < deduplicate_sec:
            logger.debug(f"Suppressed duplicate speech: {clean_text}")
            return

        # Add to priority queue (lower number = higher priority)
        # Entry format: (priority, timestamp, text)
        self._speech_queue.put((priority, now, clean_text))

    def _process_queue(self):
        """Worker loop that sequentially speaks enqueued messages."""
        while self._is_running:
            try:
                priority, timestamp, message = self._speech_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            logger.info(f"[AUDIO OUT (P{priority})]: \"{message}\"")
            self._last_spoken_text = message
            self._last_spoken_time = time.time()

            if self._engine:
                try:
                    self._engine.say(message)
                    self._engine.runAndWait()
                except Exception as ex:
                    logger.error(f"TTS playback error: {ex}")
            else:
                # Fallback: sleep proportional to reading time
                words = len(message.split())
                simulated_delay = max(0.5, words * 0.25)
                time.sleep(simulated_delay)

            self._speech_queue.task_done()

    def clear(self):
        """Clears all pending speech messages from queue."""
        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
                self._speech_queue.task_done()
            except queue.Empty:
                break
