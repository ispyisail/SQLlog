# SQLlog

A high-reliability Python service that bridges Allen-Bradley (Logix) PLCs to Microsoft SQL Server. Designed as a "set-and-forget" system with automatic recovery from network and database failures.

## Features

- **Bulletproof Handshake** - 4-state handshake protocol prevents duplicate records and missed data
- **Store-and-Forward** - Local SQLite cache ensures zero data loss during SQL Server outages
- **Automatic Recovery** - Exponential backoff retries with fault recovery
- **Windows Service** - Runs unattended with automatic startup
- **System Tray App** - Real-time status monitoring with color-coded indicators
- **Configurable Mappings** - YAML-based PLC tag to SQL column configuration
- **Data Validation** - Sanity checks with configurable limits before database commits

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Allen-Bradley Logix PLC (ControlLogix, CompactLogix)
- Microsoft SQL Server with ODBC Driver 18
- Windows 10/11 or Windows Server

### Installation

```bash
# Clone the repository
git clone https://github.com/ispyisail/SQLlog.git
cd SQLlog

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure
copy config.yaml.example config.yaml
copy .env.example .env

# Edit .env with your SQL password
notepad .env

# Edit config.yaml with your PLC IP and settings
notepad config.yaml
```

### Test Connections

```bash
# Test both PLC and SQL connections (read-only)
python test_connections.py

# Test PLC only
python test_connections.py --plc

# Test SQL only
python test_connections.py --sql
```

### Run (Development)

```bash
# Console mode (no UI)
python -m src.main

# With system tray (recommended for development)
python -m src.run_with_tray
```

### Production Install

For production, the system runs as two separate processes:
1. **SQLlog Service** - Windows service that auto-starts on boot
2. **SQLlog Tray** - Status monitor that auto-starts on user login

```bash
# Step 1: Install and start the service (Run as Administrator)
python -m src.service install
python -m src.service start

# Step 2: Add tray app to Windows startup (Run as normal user)
python -m src.tray.tray_app --add-startup

# Step 3: Start the tray app now (or log out/in)
python -m src.tray.tray_app
```

The service runs in the background even when no user is logged in. The tray provides status monitoring and service control.

### Uninstall

```bash
# Stop and remove the service (Run as Administrator)
python -m src.service stop
python -m src.service remove

# Remove tray from Windows startup
python -m src.tray.tray_app --remove-startup
```

## Architecture

In production, SQLlog runs as two processes:

1. **SQLlog Service** - Headless Windows service, auto-starts on boot
2. **SQLlog Tray** - UI monitor, auto-starts on user login

The service writes status to `%APPDATA%\SQLlog\status.json`, which the tray reads to display connection state.

```
SQLlog/
├── src/
│   ├── main.py              # Application entry point
│   ├── service.py           # Windows service wrapper
│   ├── run_with_tray.py     # Development runner (combined mode)
│   ├── core/
│   │   ├── plc_client.py    # Thread-safe PLC communication
│   │   ├── sql_client.py    # SQL Server with retry logic
│   │   ├── local_cache.py   # SQLite store-and-forward buffer
│   │   └── handshake.py     # State machine controller
│   ├── services/
│   │   ├── logger.py        # Loguru configuration
│   │   ├── heartbeat.py     # PLC watchdog (2s interval)
│   │   └── status_file.py   # Service↔Tray communication
│   ├── tray/
│   │   └── tray_app.py      # System tray monitor/controller
│   └── utils/
│       ├── config.py        # YAML loader with env substitution
│       └── validators.py    # Data validation
├── tests/                   # pytest test suite
├── docs/                    # Additional documentation
├── config.yaml.example      # Configuration template
└── requirements.txt         # Python dependencies
```

## Handshake Protocol

The system uses a 4-state handshake to ensure reliable data transfer:

| State | Value | Description |
|-------|-------|-------------|
| Idle | 0 | Waiting for PLC trigger |
| Triggered | 1 | PLC requests data logging |
| Acknowledge | 2 | Python confirms read, processing |
| Fault | 99 | Error occurred (check error code) |

### PLC Tags Required

Create these tags in your PLC program:

```
SQLlog_Trigger      : INT    // 0=Idle, 1=Request, 2=Ack, 99=Fault
SQLlog_Heartbeat    : INT    // Python increments every 2s
SQLlog_Error_Code   : INT    // Error code on fault
```

## Configuration

### Environment Variables (.env)

```ini
# SQL Server password (keep secret)
SQL_PASSWORD=your_password_here
```

### Main Configuration (config.yaml)

```yaml
plc:
  ip: "192.168.50.10"
  slot: 0
  poll_interval_ms: 100
  trigger_tag: "SQLlog_Trigger"
  heartbeat_tag: "SQLlog_Heartbeat"
  recipe_tag: "RECIPE[0]"

sql:
  connection_string: "Driver={ODBC Driver 18 for SQL Server};Server=...;PWD=${SQL_PASSWORD}"
  table: "dbo.X_RecipeLog"
  timestamp_column: "Manufacture_Date"

mappings:
  RECIPE_NUMBER: "Recipe_Number"
  PRODUCT_NAME1: "Product_Name"
  # ... see config.yaml.example for full list
```

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for complete configuration reference.

## System Tray

### Icon Colors

| Color | Status |
|-------|--------|
| Green | PLC and SQL connected |
| Yellow | SQL offline (caching locally) |
| Red | PLC disconnected or fault |
| Gray | Service not running |

### Menu Options

Right-click the tray icon for:

- **Start Service** - Start the SQLlog service
- **Stop Service** - Stop the service (auto-restarts on reboot)
- **View Logs** - Open the log file
- **Open Log Folder** - Open logs directory
- **Quit Tray** - Close the tray app (service keeps running)

## Logging

Logs are written to the `logs/` directory with automatic rotation:

- **Rotation:** 10 MB per file
- **Retention:** 30 days
- **Format:** Structured with timestamps and log levels

```bash
# View live logs
type logs\sqllog.log

# Follow logs (PowerShell)
Get-Content logs\sqllog.log -Wait
```

## Windows Service Commands

All service commands require Administrator privileges.

```bash
# Install/Uninstall
python -m src.service install
python -m src.service remove

# Start/Stop/Restart
python -m src.service start
python -m src.service stop
python -m src.service restart

# Check status in Windows
sc query SQLlog
```

## Tray Startup Commands

```bash
# Add tray to Windows startup (starts on login)
python -m src.tray.tray_app --add-startup

# Remove tray from Windows startup
python -m src.tray.tray_app --remove-startup

# Run tray manually
python -m src.tray.tray_app
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_handshake.py -v
```

## Troubleshooting

### PLC Connection Issues

1. Verify PLC IP address is reachable: `ping 192.168.50.10`
2. Check slot number matches your configuration
3. Ensure no firewall blocking port 44818 (Ethernet/IP)
4. Verify PLC is in Run mode

### SQL Connection Issues

1. Test SQL connectivity: `python test_connections.py --sql`
2. Verify ODBC Driver 18 is installed
3. Check SQL Server is accepting remote connections
4. Verify credentials in `.env` file

### Service Won't Start

1. Check Windows Event Viewer for errors
2. Verify `config.yaml` exists and is valid
3. Run in console mode first to see errors: `python -m src.main`
4. Check logs in `logs/` directory

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for more solutions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Acknowledgments

- [pycomm3](https://github.com/ottowayi/pycomm3) - Allen-Bradley PLC communication
- [loguru](https://github.com/Delgan/loguru) - Python logging made simple
- [pystray](https://github.com/moses-palmer/pystray) - System tray icon support
