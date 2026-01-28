"""
Windows Service Wrapper - pywin32 service implementation
"""

import sys
import threading
import win32serviceutil
import win32service
import win32event
import servicemanager


class SQLlogService(win32serviceutil.ServiceFramework):
    """Windows Service wrapper for SQLlog."""

    _svc_name_ = "SQLlog"
    _svc_display_name_ = "SQLlog PLC Data Logger"
    _svc_description_ = "Logs recipe data from Allen-Bradley PLC to SQL Server with store-and-forward capability"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = threading.Event()
        self.main_thread = None

    def SvcStop(self):
        """Handle service stop request."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

        # Signal the main loop to stop
        self.stop_event.set()

        # Wait for main thread to finish
        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=30)

        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcDoRun(self):
        """Main service entry point."""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, "")
        )

        try:
            self.main()
        except Exception as e:
            servicemanager.LogErrorMsg(f"SQLlog fatal error: {e}")
            raise

    def main(self):
        """Run the main application logic."""
        from .main import SQLlogApp
        from .services.status_file import StatusWriter

        status_writer = None
        app = None

        try:
            # Create status writer for tray app communication
            status_writer = StatusWriter()
            status_writer.start()

            # Create app with our stop event
            app = SQLlogApp(stop_event=self.stop_event)

            # Status callback updates the status file
            def update_status(status: str):
                status_writer.set_status(status)
                if app.cache:
                    status_writer.set_pending_count(app.cache.get_pending_count())

            app.set_status_callback(update_status)
            app.initialize()
            app.start()

            # Run main loop in current thread
            app.run()

        except Exception as e:
            servicemanager.LogErrorMsg(f"SQLlog error: {e}")
            if status_writer:
                status_writer.set_error(str(e))
            raise
        finally:
            # Ensure cleanup
            if status_writer:
                status_writer.stop()
            if app:
                try:
                    app.stop()
                except Exception:
                    pass


def install_service():
    """Handle service installation and command line."""
    if len(sys.argv) == 1:
        # Running as service
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SQLlogService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Handle command line (install, remove, start, stop, etc.)
        win32serviceutil.HandleCommandLine(SQLlogService)


if __name__ == "__main__":
    install_service()
