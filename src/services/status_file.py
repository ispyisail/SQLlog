"""
Status File - Shared status communication between service and tray app.

The service writes status to a JSON file, the tray app reads it.
"""

import json
import os
import threading
import time
from pathlib import Path
from typing import Optional
from datetime import datetime

from loguru import logger


def get_status_file_path() -> Path:
    """Get the path to the status file.

    Uses the project directory for reliable access by both the service
    (running as SYSTEM) and the tray app (running as user).
    """
    # Use project directory - both service and tray can access this
    # This is more reliable than LOCALAPPDATA which differs between SYSTEM and user
    project_dir = Path(__file__).parent.parent.parent.resolve()
    status_dir = project_dir / "data"
    status_dir.mkdir(parents=True, exist_ok=True)
    return status_dir / "status.json"


class StatusWriter:
    """Writes service status to a file for the tray app to read."""

    def __init__(self, update_interval: float = 1.0):
        self._status = {
            "status": "starting",
            "plc_connected": False,
            "sql_connected": False,
            "pending_count": 0,
            "last_update": None,
            "error": None
        }
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._update_interval = update_interval
        self._file_path = get_status_file_path()

    def set_status(self, status: str):
        """Update connection status."""
        with self._lock:
            # Map status to individual flags
            self._status["status"] = status
            self._status["plc_connected"] = status in ("connected", "sql_offline")
            self._status["sql_connected"] = status == "connected"
            self._status["error"] = None if status != "fault" else self._status.get("error")

    def set_pending_count(self, count: int):
        """Update pending cache count."""
        with self._lock:
            self._status["pending_count"] = count

    def set_error(self, error: str):
        """Set error message."""
        with self._lock:
            self._status["error"] = error

    def _write_status(self):
        """Write current status to file.

        Uses direct write instead of atomic rename because Windows file
        locking can cause os.replace() to fail when another process
        (like the tray app) has the file open for reading.
        """
        with self._lock:
            self._status["last_update"] = datetime.now().isoformat()
            status_copy = self._status.copy()

        try:
            # Write directly to the file - Windows handles concurrent reads
            with open(self._file_path, "w") as f:
                json.dump(status_copy, f, indent=2)

        except PermissionError:
            # File might be locked by tray app reading it - skip this update
            # The next update will succeed when the lock is released
            pass
        except Exception as e:
            logger.error(f"Failed to write status file: {e}")

    def _writer_loop(self):
        """Background thread that periodically writes status."""
        while not self._stop_event.is_set():
            self._write_status()
            self._stop_event.wait(self._update_interval)

    def start(self):
        """Start the status writer thread."""
        self._thread = threading.Thread(target=self._writer_loop, daemon=True, name="StatusWriter")
        self._thread.start()
        logger.debug(f"Status writer started, writing to {self._file_path}")

    def stop(self):
        """Stop the status writer thread."""
        self._stop_event.set()
        # Write final "stopped" status
        with self._lock:
            self._status["status"] = "stopped"
        self._write_status()
        if self._thread:
            self._thread.join(timeout=2)


class StatusReader:
    """Reads service status from the status file."""

    def __init__(self):
        self._file_path = get_status_file_path()

    def read_status(self) -> dict:
        """Read current status from file."""
        try:
            if not self._file_path.exists():
                return {"status": "not_running", "plc_connected": False, "sql_connected": False}

            with open(self._file_path, "r") as f:
                status = json.load(f)

            # Check if status is stale (more than 5 seconds old)
            last_update = status.get("last_update")
            if last_update:
                last_dt = datetime.fromisoformat(last_update)
                age = (datetime.now() - last_dt).total_seconds()
                if age > 5:
                    status["status"] = "not_running"
                    status["plc_connected"] = False
                    status["sql_connected"] = False

            return status

        except Exception as e:
            logger.error(f"Failed to read status file: {e}")
            return {"status": "error", "plc_connected": False, "sql_connected": False, "error": str(e)}

    def is_service_running(self) -> bool:
        """Check if service appears to be running."""
        status = self.read_status()
        return status.get("status") not in ("not_running", "stopped", "error")
