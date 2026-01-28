"""
SQLlog with Tray App - Runs main application with system tray monitoring.

Use this for development/testing. For production, install as Windows service
and run the tray app separately.
"""

import threading
from pathlib import Path

from .main import SQLlogApp
from .tray.tray_app import TrayApp
from .services.status_file import StatusWriter


def main():
    """Run SQLlog with system tray application (development mode)."""
    # Create shared events
    stop_event = threading.Event()

    # Determine log directory
    log_dir = Path("logs")

    # Create status writer (same as service uses)
    status_writer = StatusWriter()

    # Create tray app
    tray = TrayApp(log_directory=log_dir)

    # Create main app
    app = SQLlogApp(
        config_path=Path(__file__).parent.parent / "config.yaml",
        stop_event=stop_event
    )

    # Status update callback writes to status file
    def update_status(status: str):
        status_writer.set_status(status)
        if app.cache:
            status_writer.set_pending_count(app.cache.get_pending_count())

    app.set_status_callback(update_status)

    try:
        # Start status writer
        status_writer.start()

        # Initialize app
        app.initialize()

        # Update log directory from config
        log_config = app.config.get("logging", {})
        log_dir = Path(log_config.get("directory", "logs"))
        tray.log_directory = log_dir

        # Start tray app in background (it will read status from file)
        tray_thread = threading.Thread(target=tray.run, daemon=True, name="TrayApp")
        tray_thread.start()

        # Start main app background services
        app.start()

        # Run main loop (blocks until stop_event is set or tray quits)
        def watch_tray():
            """Watch for tray stop and set stop_event."""
            tray_thread.join()
            stop_event.set()

        watch_thread = threading.Thread(target=watch_tray, daemon=True)
        watch_thread.start()

        app.run()

    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        status_writer.stop()
        tray.stop()
        app.stop()


if __name__ == "__main__":
    main()
