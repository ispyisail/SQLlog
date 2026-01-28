"""
SQLlog - Main entry point

Orchestrates PLC polling, SQL logging, and store-and-forward cache.
"""

import threading
import time
from pathlib import Path
from typing import Callable

from .utils.config import load_config
from .services.logger import setup_logger
from .core.plc_client import PLCClient
from .core.sql_client import SQLClient
from .core.local_cache import LocalCache
from .core.handshake import HandshakeStateMachine, ConnectionStatus
from .services.heartbeat import HeartbeatService


class SQLlogApp:
    """Main application class with proper lifecycle management."""

    def __init__(self, config_path: Path = None, stop_event: threading.Event = None):
        """
        Initialize SQLlog application.

        Args:
            config_path: Path to config.yaml (default: ../config.yaml relative to this file)
            stop_event: Threading event to signal shutdown (for Windows service)
        """
        self.config_path = config_path or Path(__file__).parent.parent / "config.yaml"
        self.stop_event = stop_event or threading.Event()

        self.config = None
        self.logger = None
        self.plc = None
        self.sql = None
        self.cache = None
        self.heartbeat = None
        self.state_machine = None

        self._status_callback = None
        self._force_sync_event = threading.Event()

    def set_status_callback(self, callback: Callable[[str], None]):
        """Set callback for status updates (used by tray app)."""
        self._status_callback = callback

    def request_force_sync(self):
        """Request immediate cache sync (from tray app menu)."""
        self._force_sync_event.set()

    def initialize(self):
        """Initialize all components."""
        # Load configuration
        self.config = load_config(self.config_path)

        # Setup logging
        self.logger = setup_logger(self.config.get("logging", {}))
        self.logger.info("SQLlog starting...")

        # Initialize components
        self.plc = PLCClient(self.config["plc"])
        self.sql = SQLClient(self.config["sql"])
        self.cache = LocalCache(self.config.get("local_cache", {}))
        self.heartbeat = HeartbeatService(self.plc, self.config.get("heartbeat", {}))

        # Build extra mappings from config
        extra_mappings = self._build_extra_mappings()

        # Create state machine with status callback
        self.state_machine = HandshakeStateMachine(
            plc=self.plc,
            sql=self.sql,
            cache=self.cache,
            mappings=self.config.get("mappings", {}),
            extra_mappings=extra_mappings,
            validation=self.config.get("validation", {}),
            logger=self.logger,
            status_callback=self._status_callback
        )

        self.logger.info("SQLlog initialized")

    def _build_extra_mappings(self) -> dict:
        """Build extra tag to SQL column mappings from config."""
        mappings = {}

        # Map extra_tags to SQL columns
        extra_tags = self.config.get("extra_tags", {})
        if "sequence_number" in extra_tags:
            mappings["sequence_number"] = "SEQ_Number"
        if "batch_ratio" in extra_tags:
            mappings["batch_ratio"] = "BATCH_RATIO"
        if "recycle_weight" in extra_tags:
            mappings["recycle_weight"] = "RECYCLE_Weight"

        # Map bulk_names to SQL columns
        bulk_names = self.config.get("bulk_names", {})
        for i in range(1, 10):
            key = f"slot_{i}"
            if key in bulk_names:
                mappings[key] = f"B00{i}_Name"

        return mappings

    def start(self):
        """Start background services."""
        # Start heartbeat thread
        self.heartbeat.start()

        # Start cache sync thread with force sync event
        self.cache.start_sync_thread(self.sql, self._force_sync_event)

        self.logger.info("Background services started")

    def stop(self):
        """Stop all services and cleanup."""
        if self.logger:
            self.logger.info("Shutdown requested")

        self.stop_event.set()

        if self.heartbeat:
            self.heartbeat.stop()
        if self.cache:
            self.cache.stop_sync_thread()
        if self.plc:
            self.plc.disconnect()
        if self.sql:
            self.sql.disconnect()

        if self.logger:
            self.logger.info("SQLlog stopped")

    def run(self):
        """Main application loop."""
        self.logger.info("Entering main loop")

        poll_interval = self.config["plc"].get("poll_interval_ms", 100) / 1000

        while not self.stop_event.is_set():
            try:
                self.state_machine.poll()
            except Exception as e:
                self.logger.error(f"Poll error: {e}")

            # Use wait instead of sleep to respond to stop event
            self.stop_event.wait(poll_interval)

        self.logger.info("Main loop exited")


def main(stop_event: threading.Event = None):
    """
    Main entry point.

    Args:
        stop_event: Optional threading event for service stop signal
    """
    app = SQLlogApp(stop_event=stop_event)

    try:
        app.initialize()
        app.start()
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        if app.logger:
            app.logger.error(f"Fatal error: {e}")
        raise
    finally:
        app.stop()


if __name__ == "__main__":
    main()
