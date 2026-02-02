@echo off
setlocal EnableDelayedExpansion

:: ============================================================================
:: SQLlog Service Uninstaller
:: Removes the SQLlog Windows Service
:: ============================================================================

title SQLlog Service Uninstaller

echo.
echo ============================================================
echo            SQLlog Service Uninstaller
echo ============================================================
echo.

:: ----------------------------------------------------------------------------
:: Check for Administrator privileges
:: ----------------------------------------------------------------------------
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARNING] This uninstaller requires Administrator privileges.
    echo.
    echo Requesting elevation...
    echo.

    :: Use cmd /k to keep the window open after the script finishes
    set "vbsFile=%temp%\elevate_sqllog_uninstall.vbs"
    echo Set UAC = CreateObject^("Shell.Application"^) > "!vbsFile!"
    echo UAC.ShellExecute "cmd.exe", "/k ""%~f0""", "%~dp0", "runas", 1 >> "!vbsFile!"

    cscript //nologo "!vbsFile!"
    del "!vbsFile!" >nul 2>&1

    exit /b 0
)

echo [OK] Running with Administrator privileges.
echo.

:: ----------------------------------------------------------------------------
:: Check if service exists
:: ----------------------------------------------------------------------------
echo Checking for SQLlog service...
sc query SQLlog >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo [INFO] SQLlog service is not installed.
    echo        Nothing to uninstall.
    echo.
    goto :done
)

echo [OK] SQLlog service found.
echo.

:: ----------------------------------------------------------------------------
:: Stop the service if running
:: ----------------------------------------------------------------------------
echo Checking service status...
sc query SQLlog | find "RUNNING" >nul 2>&1
if %errorLevel% equ 0 (
    echo Service is RUNNING. Stopping...
    sc stop SQLlog >nul 2>&1

    :: Wait for service to stop (up to 30 seconds)
    set /a attempts=0
    :wait_stop
    timeout /t 1 /nobreak >nul
    sc query SQLlog | find "STOPPED" >nul 2>&1
    if %errorLevel% equ 0 (
        echo [OK] Service stopped.
        goto :remove_service
    )
    set /a attempts+=1
    if !attempts! lss 30 goto :wait_stop

    echo [WARNING] Service did not stop gracefully. Forcing removal...
) else (
    echo [OK] Service is not running.
)
echo.

:: ----------------------------------------------------------------------------
:: Remove the service
:: ----------------------------------------------------------------------------
:remove_service
echo Removing SQLlog service...
sc delete SQLlog >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo [ERROR] Failed to remove the service.
    echo.
    echo POSSIBLE CAUSES:
    echo   1. Service is still running or stopping
    echo   2. Another process has the service open
    echo.
    echo SOLUTION:
    echo   1. Open Services (services.msc)
    echo   2. Wait for the service to fully stop
    echo   3. Close any windows showing service properties
    echo   4. Try running this uninstaller again
    echo.
    goto :failure
)

echo [OK] Service removed successfully.
echo.

:: ----------------------------------------------------------------------------
:: Optional: Remove tray from startup
:: ----------------------------------------------------------------------------
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
    set PYTHON_EXE="%CD%\venv\Scripts\python.exe"
) else (
    set PYTHON_EXE=python
)

echo Removing tray app from Windows startup (if present)...
%PYTHON_EXE% -m src.tray.tray_app --remove-startup >nul 2>&1
echo [OK] Startup entry removed (if it existed).
echo.

:: ----------------------------------------------------------------------------
:: Success
:: ----------------------------------------------------------------------------
:done
echo ============================================================
echo            UNINSTALL COMPLETE
echo ============================================================
echo.
echo The SQLlog service has been removed.
echo.
echo NOTE: The following items were NOT removed:
echo   - Application files in %CD%
echo   - Log files in %CD%\logs\
echo   - Status file in %LOCALAPPDATA%\SQLlog\
echo   - Configuration in config.yaml
echo.
echo To completely remove SQLlog, delete the project folder.
echo.
echo ============================================================
echo.
pause
exit /b 0

:: ----------------------------------------------------------------------------
:: Failure
:: ----------------------------------------------------------------------------
:failure
echo.
echo ============================================================
echo            UNINSTALL FAILED
echo ============================================================
echo.
echo Please review the error messages above.
echo.
echo ============================================================
echo.
pause
exit /b 1
