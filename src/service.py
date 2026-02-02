"""
Windows Service Wrapper - pywin32 service implementation
"""

import os
import sys
import threading
from pathlib import Path

import win32serviceutil
import win32service
import win32event
import servicemanager


# Get the project root directory (where config.yaml lives)
SERVICE_DIR = Path(__file__).parent.parent.resolve()


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
        import time
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, "")
        )

        try:
            self.main()
        except Exception as e:
            import traceback
            
            # Log to file for easy debugging
            log_dir = SERVICE_DIR / "logs"
            log_dir.mkdir(exist_ok=True)
            with open(log_dir / "service_error.log", "a", encoding="utf-8") as f:
                f.write(f"--- Service failed to start at {time.ctime()} ---\n")
                traceback.print_exc(file=f)
                f.write("\n")

            # Also log to Windows Event Log
            error_message = f"SQLlog fatal error during startup: {e}\n{traceback.format_exc()}"
            servicemanager.LogErrorMsg(error_message)
            
            # Re-raise to ensure service manager knows it failed
            raise

    def main(self):
        """Run the main application logic."""
        # Add project root to path to allow absolute imports
        sys.path.insert(0, str(SERVICE_DIR))

        # Change to project directory so relative paths work
        os.chdir(SERVICE_DIR)

        # Load .env file for SYSTEM account (which doesn't have user env vars)
        from dotenv import load_dotenv
        env_path = SERVICE_DIR / ".env"
        if env_path.exists():
            load_dotenv(env_path)

        from src.main import SQLlogApp
        from src.services.status_file import StatusWriter

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
    elif len(sys.argv) > 1 and sys.argv[1].lower() == 'install':
        # Custom install logic using low-level API to guarantee correct PathName
        try:
            hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
            try:
                # Build the explicit command line
                script_path = os.path.abspath(sys.argv[0])
                command_line = f'"{sys.executable}" "{script_path}"'

                hs = win32service.CreateService(
                    hscm,
                    SQLlogService._svc_name_,
                    SQLlogService._svc_display_name_,
                    win32service.SERVICE_ALL_ACCESS,
                    win32service.SERVICE_WIN32_OWN_PROCESS,
                    win32service.SERVICE_AUTO_START,
                    win32service.SERVICE_ERROR_NORMAL,
                    command_line,
                    None, 0, None, None, None
                )

                # Set the service description (not available in CreateService)
                win32service.ChangeServiceConfig2(hs, win32service.SERVICE_CONFIG_DESCRIPTION, SQLlogService._svc_description_)

                win32service.CloseServiceHandle(hs)

                print(f"Service '{SQLlogService._svc_name_}' installed successfully.")
                print(f" -> PathName: {command_line}")
                sys.exit(0)
            finally:
                win32service.CloseServiceHandle(hscm)
        except Exception as e:
            print(f"Error installing service: {e}")
            sys.exit(1)
    else:
        # For 'remove', 'start', etc., the default handler is still fine.
        win32serviceutil.HandleCommandLine(SQLlogService)


if __name__ == "__main__":
    install_service()
