"""
System Tray Application - Monitors and controls the SQLlog service.

This runs as a separate process from the service, started on user login.
"""

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw
import pystray
from loguru import logger

from ..services.status_file import StatusReader


class TrayStatus:
    """Tray icon status states."""
    GREEN = "green"    # PLC + SQL connected
    YELLOW = "yellow"  # SQL offline, caching
    RED = "red"        # PLC disconnected or error
    GRAY = "gray"      # Service not running


class TrayApp:
    """
    System tray application for SQLlog service monitoring and control.

    Icon colors:
    - Green: Connected to PLC & SQL
    - Yellow: SQL Offline (Buffering to Local Cache)
    - Red: PLC Disconnected or Service Error
    - Gray: Service not running
    """

    SERVICE_NAME = "SQLlog"

    def __init__(self, log_directory: Path = None):
        """
        Initialize tray application.

        Args:
            log_directory: Path to log directory
        """
        self.log_directory = log_directory or Path("logs")
        self._status_reader = StatusReader()

        self._status = TrayStatus.GRAY
        self._icon = None
        self._icons = self._create_icons()
        self._pending_count = 0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._monitor_thread = None

    def _create_icons(self) -> dict:
        """Create colored circle icons."""
        icons = {}
        colors = {
            TrayStatus.GREEN: "#22c55e",
            TrayStatus.YELLOW: "#eab308",
            TrayStatus.RED: "#ef4444",
            TrayStatus.GRAY: "#6b7280"
        }

        for status, color in colors.items():
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([4, 4, 60, 60], fill=color)
            icons[status] = img

        return icons

    def _update_status_from_file(self):
        """Read status from file and update icon."""
        status_data = self._status_reader.read_status()

        # Map status to tray status
        status_str = status_data.get("status", "not_running")

        if status_str in ("not_running", "stopped"):
            new_status = TrayStatus.GRAY
        elif status_str == "connected":
            new_status = TrayStatus.GREEN
        elif status_str == "sql_offline":
            new_status = TrayStatus.YELLOW
        else:
            new_status = TrayStatus.RED

        pending = status_data.get("pending_count", 0)

        with self._lock:
            status_changed = new_status != self._status
            self._status = new_status
            self._pending_count = pending

            if self._icon and status_changed:
                self._icon.icon = self._icons[self._status]
                self._icon.title = self._get_title()

    def _monitor_loop(self):
        """Background thread that monitors service status."""
        while not self._stop_event.is_set():
            try:
                self._update_status_from_file()
            except Exception as e:
                logger.error(f"Status monitor error: {e}")
            self._stop_event.wait(1.0)

    def _get_title(self) -> str:
        """Get tooltip text."""
        status_text = {
            TrayStatus.GREEN: "Connected",
            TrayStatus.YELLOW: "SQL Offline (Caching)",
            TrayStatus.RED: "Error",
            TrayStatus.GRAY: "Service Not Running"
        }.get(self._status, "Unknown")

        title = f"SQLlog - {status_text}"

        if self._pending_count > 0:
            title += f" | {self._pending_count} pending"

        return title

    def _create_menu(self):
        """Create the tray icon context menu."""
        return pystray.Menu(
            pystray.MenuItem("SQLlog Service", None, enabled=False),
            pystray.MenuItem(lambda _: self._get_title(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start Service", self._on_start_service),
            pystray.MenuItem("Stop Service", self._on_stop_service),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("View Logs", self._on_view_logs),
            pystray.MenuItem("Open Log Folder", self._on_open_log_folder),
            pystray.MenuItem("Clear Logs", self._on_clear_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Tray", self._on_quit)
        )

    def _on_start_service(self, icon, item):
        """Start the SQLlog service."""
        logger.info("Starting SQLlog service from tray")
        try:
            import win32serviceutil
            win32serviceutil.StartService(self.SERVICE_NAME)
            logger.info("Service start command sent")
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            self._show_error(f"Failed to start service: {e}")

    def _on_stop_service(self, icon, item):
        """Stop the SQLlog service."""
        logger.info("Stopping SQLlog service from tray")
        try:
            import win32serviceutil
            win32serviceutil.StopService(self.SERVICE_NAME)
            logger.info("Service stop command sent")
        except Exception as e:
            logger.error(f"Failed to stop service: {e}")
            self._show_error(f"Failed to stop service: {e}")

    def _show_error(self, message: str):
        """Show error notification (Windows toast if available)."""
        try:
            if self._icon:
                self._icon.notify(message, "SQLlog Error")
        except Exception:
            pass

    def _on_view_logs(self, icon, item):
        """Open main log file."""
        log_path = self.log_directory / "sqllog.log"
        self._open_file(log_path)

    def _on_open_log_folder(self, icon, item):
        """Open log directory in explorer."""
        if self.log_directory.exists():
            os.startfile(self.log_directory)
        else:
            logger.warning(f"Log directory not found: {self.log_directory}")

    def _on_clear_logs(self, icon, item):
        """Clear all log files."""
        logger.info("Clearing log files")
        cleared = 0
        try:
            if self.log_directory.exists():
                for log_file in self.log_directory.glob("*.log*"):
                    try:
                        log_file.unlink()
                        cleared += 1
                    except PermissionError:
                        # File might be in use by service - truncate instead
                        try:
                            with open(log_file, "w") as f:
                                pass  # Truncate to empty
                            cleared += 1
                        except Exception:
                            pass
                    except Exception as e:
                        logger.warning(f"Could not clear {log_file}: {e}")

            if cleared > 0:
                self._show_notification(f"Cleared {cleared} log file(s)")
            else:
                self._show_notification("No log files to clear")

        except Exception as e:
            logger.error(f"Failed to clear logs: {e}")
            self._show_error(f"Failed to clear logs: {e}")

    def _show_notification(self, message: str):
        """Show info notification."""
        try:
            if self._icon:
                self._icon.notify(message, "SQLlog")
        except Exception:
            pass

    def _open_file(self, path: Path):
        """Open a file with default application."""
        if path.exists():
            os.startfile(path)
        else:
            logger.warning(f"File not found: {path}")

    def _on_quit(self, icon, item):
        """Quit the tray application (service keeps running)."""
        logger.info("Tray application quit requested")
        self._stop_event.set()
        icon.stop()

    def run(self):
        """Run the tray application (blocking)."""
        # Start status monitor thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="StatusMonitor"
        )
        self._monitor_thread.start()

        # Initial status update
        self._update_status_from_file()

        self._icon = pystray.Icon(
            name="sqllog",
            icon=self._icons[self._status],
            title=self._get_title(),
            menu=self._create_menu()
        )
        logger.info("Tray application started")
        self._icon.run()

    def stop(self):
        """Stop the tray application."""
        self._stop_event.set()
        if self._icon:
            self._icon.stop()


def add_to_startup():
    """Add tray app to Windows startup."""
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "SQLlog Tray"

    # Get path to this script
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        exe_path = sys.executable
    else:
        # Running as script - use pythonw.exe for no console window
        python_dir = Path(sys.executable).parent
        pythonw = python_dir / "pythonw.exe"
        if pythonw.exists():
            exe_path = f'"{pythonw}" -m src.tray.tray_app'
        else:
            # Fallback to python.exe if pythonw not found
            exe_path = f'"{sys.executable}" -m src.tray.tray_app'

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        print(f"Added to startup: {exe_path}")
        return True
    except Exception as e:
        print(f"Failed to add to startup: {e}")
        return False


def remove_from_startup():
    """Remove tray app from Windows startup."""
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "SQLlog Tray"

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, app_name)
        winreg.CloseKey(key)
        print("Removed from startup")
        return True
    except FileNotFoundError:
        print("Not in startup")
        return True
    except Exception as e:
        print(f"Failed to remove from startup: {e}")
        return False


def main():
    """Run tray app as standalone."""
    import argparse

    parser = argparse.ArgumentParser(description="SQLlog Tray Application")
    parser.add_argument("--add-startup", action="store_true", help="Add to Windows startup")
    parser.add_argument("--remove-startup", action="store_true", help="Remove from Windows startup")
    args = parser.parse_args()

    if args.add_startup:
        add_to_startup()
        return

    if args.remove_startup:
        remove_from_startup()
        return

    # Run tray app
    app = TrayApp(log_directory=Path("logs"))
    app.run()


if __name__ == "__main__":
    main()
