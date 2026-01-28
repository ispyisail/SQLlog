"""
Heartbeat Service - PLC watchdog
"""

import threading
from loguru import logger


class HeartbeatService:
    """
    Maintains heartbeat with PLC.

    Increments Python_Heartbeat tag every N seconds.
    PLC should alarm if heartbeat stops for >10s.
    """

    def __init__(self, plc_client, config: dict):
        self.plc = plc_client
        self.interval = config.get("interval_s", 2)

        self._thread = None
        self._stop_event = threading.Event()
        self._current_value = 0

    def start(self):
        """Start the heartbeat thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()
        logger.info(f"Heartbeat service started (interval: {self.interval}s)")

    def stop(self):
        """Stop the heartbeat thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Heartbeat service stopped")

    def _heartbeat_loop(self):
        """Background loop to increment heartbeat."""
        while not self._stop_event.is_set():
            try:
                # Read current value first (in case PLC reset it)
                current = self.plc.read_heartbeat()
                if current is not None:
                    self._current_value = current

                # Increment and write
                if self.plc.increment_heartbeat(self._current_value):
                    self._current_value = (self._current_value + 1) % 32768
                    logger.debug(f"Heartbeat: {self._current_value}")
                else:
                    logger.warning("Failed to update heartbeat")

            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

            self._stop_event.wait(self.interval)
