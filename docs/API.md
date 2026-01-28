# API Reference

Developer reference for SQLlog modules.

## Core Modules

### src.core.plc_client

Thread-safe PLC communication using pycomm3.

```python
from src.core.plc_client import PLCClient

# Initialize
client = PLCClient(ip="192.168.50.10", slot=0)

# Connect
client.connect()

# Read recipe UDT
recipe = client.read_recipe("RECIPE[0]")
# Returns: dict with UDT fields or None

# Read single tag
value = client.read_tag("A_DINT[10]")
# Returns: tag value or None

# Read trigger
trigger = client.read_trigger()
# Returns: int (0, 1, 2, or 99)

# Write acknowledgment
client.write_trigger(2)

# Write error code
client.write_error_code(101)

# Increment heartbeat
client.increment_heartbeat()

# Read all data (UDT + extra tags)
data = client.read_all_recipe_data()

# Disconnect
client.disconnect()
```

### src.core.sql_client

SQL Server client with retry logic.

```python
from src.core.sql_client import SQLClient

# Initialize
client = SQLClient(
    connection_string="Driver={...};...",
    table="dbo.X_RecipeLog",
    mappings={"RECIPE_NUMBER": "Recipe_Number", ...},
    timestamp_column="Manufacture_Date"
)

# Connect
client.connect()

# Insert record
success = client.insert_record({"RECIPE_NUMBER": 46, "PRODUCT_NAME1": "Test"})
# Returns: True on success, False on failure (will retry)

# Check connection
if client.is_connected():
    pass

# Disconnect
client.disconnect()
```

### src.core.local_cache

SQLite store-and-forward cache.

```python
from src.core.local_cache import LocalCache

# Initialize
cache = LocalCache(db_path="cache.db")

# Add record to cache
cache.add_record({"field": "value", ...})

# Get pending records
records = cache.get_pending_records(limit=100)
# Returns: list of (id, data_dict) tuples

# Mark as synced
cache.mark_synced(record_id)

# Get pending count
count = cache.pending_count()

# Force sync attempt
cache.force_sync()
```

### src.core.handshake

State machine for handshake protocol.

```python
from src.core.handshake import HandshakeStateMachine, HandshakeState

# Initialize with clients
state_machine = HandshakeStateMachine(
    plc_client=plc,
    sql_client=sql,
    local_cache=cache,
    mappings=config["mappings"],
    status_callback=on_status_change
)

# Poll (call in loop)
state_machine.poll()

# Get current state
state = state_machine.current_state
# Returns: HandshakeState enum

# States
HandshakeState.IDLE        # 0 - Waiting
HandshakeState.TRIGGERED   # 1 - Request received
HandshakeState.ACKNOWLEDGE # 2 - Processing
HandshakeState.FAULT       # 99 - Error state
```

### Status Callback

```python
from src.core.handshake import ConnectionStatus

def on_status_change(status: ConnectionStatus):
    """Called when connection status changes."""
    if status == ConnectionStatus.ALL_CONNECTED:
        print("PLC and SQL connected")
    elif status == ConnectionStatus.SQL_OFFLINE:
        print("SQL offline, caching locally")
    elif status == ConnectionStatus.PLC_DISCONNECTED:
        print("PLC disconnected")
    elif status == ConnectionStatus.FAULT:
        print("System fault")
```

## Services

### src.services.logger

Loguru configuration.

```python
from src.services.logger import setup_logger

# Initialize logging
logger = setup_logger(
    log_dir="logs",
    rotation="10 MB",
    retention="30 days",
    level="INFO"
)

# Use loguru directly
from loguru import logger
logger.info("Message")
logger.error("Error: {}", error)
```

### src.services.heartbeat

PLC heartbeat manager.

```python
from src.services.heartbeat import HeartbeatService

# Initialize
heartbeat = HeartbeatService(
    plc_client=plc,
    interval_s=2
)

# Start (runs in background thread)
heartbeat.start()

# Stop
heartbeat.stop()
```

## Utilities

### src.utils.config

Configuration loading.

```python
from src.utils.config import load_config

# Load config with env var substitution
config = load_config("config.yaml")
# Returns: dict with all config sections

# Access sections
plc_config = config["plc"]
sql_config = config["sql"]
mappings = config["mappings"]
```

### src.utils.validators

Data validation.

```python
from src.utils.validators import validate_record

# Validate with limits
limits = {
    "TOTAL_WT": {"min": 0, "max": 50000},
    "RECIPE_NUMBER": {"min": 1, "max": 99}
}

errors = validate_record(data, limits)
# Returns: list of error strings (empty if valid)

if errors:
    for error in errors:
        print(f"Validation failed: {error}")
```

## Main Application

### src.main

Application entry point.

```python
from src.main import SQLlogApp

# Create application
app = SQLlogApp(
    config_path="config.yaml",
    stop_event=threading.Event()
)

# Run (blocking)
app.run()

# Stop (from another thread)
app.stop_event.set()
```

### src.run_with_tray

Run with system tray.

```python
from src.run_with_tray import run_with_tray

# Run application with tray icon
run_with_tray(config_path="config.yaml")
```

## Windows Service

### src.service

Windows service wrapper.

```bash
# Command line interface
python -m src.service install
python -m src.service start
python -m src.service stop
python -m src.service restart
python -m src.service remove
```

## Error Codes

Error codes written to PLC on fault:

| Code | Description |
|------|-------------|
| 0 | No error |
| 100 | PLC read error |
| 101 | PLC write error |
| 102 | PLC connection lost |
| 200 | SQL connection error |
| 201 | SQL insert error |
| 300 | Validation error |
| 400 | Configuration error |
| 500 | Unknown error |
