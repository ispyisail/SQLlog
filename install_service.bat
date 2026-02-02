@echo off
setlocal EnableDelayedExpansion

:: ============================================================================
:: SQLlog Service Installer
:: Installs SQLlog as a Windows Service with automatic startup
:: ============================================================================

title SQLlog Service Installer

:: Colors and formatting
echo.
echo ============================================================
echo            SQLlog Service Installer
echo ============================================================
echo.

:: ----------------------------------------------------------------------------
:: Check for Administrator privileges
:: ----------------------------------------------------------------------------
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARNING] This installer requires Administrator privileges.
    echo.
    echo Requesting elevation...
    echo.

    :: Create a temporary VBScript to request elevation
    set "vbsFile=%temp%\elevate_sqllog.vbs"
    echo Set UAC = CreateObject^("Shell.Application"^) > "!vbsFile!"
    echo UAC.ShellExecute "%~f0", "", "", "runas", 1 >> "!vbsFile!"

    :: Run the elevation script
    cscript //nologo "!vbsFile!"
    del "!vbsFile!" >nul 2>&1

    :: Exit the non-elevated instance
    exit /b 0
)

echo [OK] Running with Administrator privileges.
echo.

:: ----------------------------------------------------------------------------
:: Verify Python installation
:: ----------------------------------------------------------------------------
echo Checking Python installation...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo SOLUTION:
    echo   1. Install Python 3.10 or later from https://python.org
    echo   2. Ensure "Add Python to PATH" is checked during installation
    echo   3. Re-run this installer
    echo.
    goto :failure
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% found.
echo.

:: ----------------------------------------------------------------------------
:: Change to script directory (where SQLlog is installed)
:: ----------------------------------------------------------------------------
cd /d "%~dp0"
echo Working directory: %CD%
echo.

:: ----------------------------------------------------------------------------
:: Check for required files
:: ----------------------------------------------------------------------------
echo Checking required files...

if not exist "src\service.py" (
    echo.
    echo [ERROR] src\service.py not found.
    echo.
    echo SOLUTION:
    echo   This installer must be run from the SQLlog project directory.
    echo   Current directory: %CD%
    echo.
    goto :failure
)
echo   [OK] src\service.py found

if not exist "config.yaml" (
    echo.
    echo [WARNING] config.yaml not found.
    echo   The service may fail to start without proper configuration.
    echo   Please create config.yaml before starting the service.
    echo.
) else (
    echo   [OK] config.yaml found
)

if not exist "venv\Scripts\python.exe" (
    echo.
    echo [WARNING] Virtual environment not found at venv\
    echo   Using system Python instead.
    echo   For best results, create a venv: python -m venv venv
    echo.
    set PYTHON_EXE=python
) else (
    echo   [OK] Virtual environment found
    set PYTHON_EXE="%CD%\venv\Scripts\python.exe"
)

echo.

:: ----------------------------------------------------------------------------
:: Check if service already exists
:: ----------------------------------------------------------------------------
echo Checking for existing SQLlog service...
sc query SQLlog >nul 2>&1
if %errorLevel% equ 0 (
    echo.
    echo [INFO] SQLlog service already exists.
    echo.

    :: Check if running
    sc query SQLlog | find "RUNNING" >nul 2>&1
    if %errorLevel% equ 0 (
        echo   Service is currently RUNNING.
        echo   Stopping service before reinstall...
        sc stop SQLlog >nul 2>&1
        timeout /t 3 /nobreak >nul
    )

    echo   Removing existing service...
    sc delete SQLlog >nul 2>&1
    if %errorLevel% neq 0 (
        echo.
        echo [ERROR] Failed to remove existing service.
        echo.
        echo SOLUTION:
        echo   1. Open Services (services.msc)
        echo   2. Stop the SQLlog service if running
        echo   3. Try running this installer again
        echo.
        goto :failure
    )
    echo   [OK] Existing service removed.
    timeout /t 2 /nobreak >nul
    echo.
)

:: ----------------------------------------------------------------------------
:: Install the service
:: ----------------------------------------------------------------------------
echo Installing SQLlog service...
echo.

%PYTHON_EXE% -m src.service install
if %errorLevel% neq 0 (
    echo.
    echo [ERROR] Service installation failed.
    echo.
    echo POSSIBLE CAUSES:
    echo   1. Missing Python dependencies - run: pip install -r requirements.txt
    echo   2. pywin32 not installed - run: pip install pywin32
    echo   3. Permission denied - ensure you're running as Administrator
    echo.
    echo For detailed error information, check:
    echo   - logs\service_error.log
    echo   - Windows Event Viewer (Application log)
    echo.
    goto :failure
)

echo.
echo [OK] Service installed successfully.
echo.

:: ----------------------------------------------------------------------------
:: Configure service recovery options
:: ----------------------------------------------------------------------------
echo Configuring service recovery options...
sc failure SQLlog reset= 86400 actions= restart/60000/restart/60000/restart/60000 >nul 2>&1
if %errorLevel% equ 0 (
    echo [OK] Service will auto-restart on failure.
) else (
    echo [WARNING] Could not configure recovery options.
)
echo.

:: ----------------------------------------------------------------------------
:: Start the service
:: ----------------------------------------------------------------------------
echo Starting SQLlog service...
sc start SQLlog >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo [WARNING] Service installed but failed to start.
    echo.
    echo POSSIBLE CAUSES:
    echo   1. Missing or invalid config.yaml
    echo   2. PLC or SQL Server not reachable
    echo   3. Missing .env file with credentials
    echo.
    echo Check logs\service_error.log for details.
    echo You can start the service later with: sc start SQLlog
    echo.
) else (
    timeout /t 2 /nobreak >nul
    sc query SQLlog | find "RUNNING" >nul 2>&1
    if %errorLevel% equ 0 (
        echo [OK] Service is now RUNNING.
    ) else (
        echo [WARNING] Service may have failed to start. Check logs.
    )
)

echo.

:: ----------------------------------------------------------------------------
:: Success
:: ----------------------------------------------------------------------------
:success
echo ============================================================
echo            INSTALLATION COMPLETE
echo ============================================================
echo.
echo Service Name:    SQLlog
echo Display Name:    SQLlog PLC Data Logger
echo Startup Type:    Automatic (starts on boot)
echo.
echo USEFUL COMMANDS:
echo   sc start SQLlog     - Start the service
echo   sc stop SQLlog      - Stop the service
echo   sc query SQLlog     - Check service status
echo.
echo LOG LOCATIONS:
echo   %CD%\logs\
echo   %LOCALAPPDATA%\SQLlog\status.json
echo.
echo To add the system tray monitor (optional):
echo   python -m src.tray.tray_app --add-startup
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
echo            INSTALLATION FAILED
echo ============================================================
echo.
echo Please review the error messages above and try again.
echo.
echo For help, see:
echo   - PROJECT_SCOPE.md
echo   - docs\EXISTING_SYSTEM_REFERENCE.md
echo   - https://github.com/ispyisail/SQLlog/issues
echo.
echo ============================================================
echo.
pause
exit /b 1
