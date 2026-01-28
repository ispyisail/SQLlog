# Project Scope: Robust PLC Recipe Data Logger (v1.1)

## 1. Project Overview

The objective is to replace the existing PeakHMI data logging system with a custom, high-reliability Python service. This service will act as a bridge between an Allen-Bradley (Logix) PLC and a Microsoft SQL Server. The system must be "set-and-forget," featuring automatic recovery from network or database failures.

## 2. System Architecture

- **Host Environment:** Windows PC
- **PLC Interface:** Ethernet/IP via the `pycomm3` library (Optimized for UDT/Array reading)
- **Database Interface:** `pyodbc` with Microsoft ODBC Driver 18 for SQL Server
- **Local Storage:** SQLite-based persistent buffer for "Store-and-Forward" functionality

### Two-Process Architecture

1. **SQLlog Service** - Windows service that runs headless
   - Auto-starts on system boot (before user login)
   - Handles all PLC communication and SQL logging
   - Writes status to `%APPDATA%\SQLlog\status.json`

2. **SQLlog Tray** - Separate monitoring application
   - Auto-starts on user login (via Windows startup registry)
   - Reads status file to display connection state
   - Can start/stop the service via Windows Service Control Manager
   - Service continues running even if tray is closed

## 3. Functional Requirements

### 3.1. The "Bulletproof" Handshake

To prevent duplicate records or missed data, the system will use a 4-state handshake:

| State | Name | Description |
|-------|------|-------------|
| 0 | Idle | Python waits for `SQLlog_Trigger == 1` |
| 1 | Triggered | PLC sets `SQLlog_Trigger` to 1 |
| 2 | Acknowledge | Python sees the 1, reads the recipe UDT, and writes 2 back to the PLC |
| 0 | Complete | After successful SQL write (or local cache commit), Python writes 0 to the PLC |
| 99 | Fault | If an unrecoverable error occurs, Python writes 99 and an Error Code to `SQLlog_Error_Code` |

### 3.2. Reliability & Robustness

- **Store-and-Forward:** If the MS SQL server is unreachable, the service will log data to a local SQLite database. Once restored, data is uploaded in First-In-First-Out (FIFO) order.
- **Connection Resiliency:** Implementation of exponential backoff for connection retries.
- **Watchdog/Heartbeat:** Python will increment `SQLlog_Heartbeat` (INT) every 2s. The PLC must alarm if this stops for >10s.
- **Time Authority:** All records will be timestamped using the Local PC System Time (ISO 8601 format) to ensure consistency across the database.

### 3.3. Logging & Diagnostics

**Structured Logs:** Using `loguru` with automatic rotation (e.g., 10MB per file, keep 30 days).

**Tray Icon Status:**
| Color | Meaning |
|-------|---------|
| 🟢 Green | Connected to PLC & SQL |
| 🟡 Yellow | SQL Offline (Buffering to Local Cache) |
| 🔴 Red | PLC Disconnected or Service Error |
| ⚪ Gray | Service Not Running |

**Tray Menu Options:**
- Start Service - Start the SQLlog Windows service
- Stop Service - Stop service (auto-restarts on reboot)
- View Logs - Open the main log file
- Open Log Folder - Open logs directory in Explorer
- Quit Tray - Close tray app only (service keeps running)

## 4. Technical Specifications

### 4.1. Data Validation & Configuration

- **Config File:** Use a `config.yaml` file to define PLC IP, SQL Connection Strings, and Tag-to-Column mappings.
- **Sanity Checks:** Validate that numeric recipe values are within "Reasonable Limits" (defined in config) before committing to SQL.

### 4.2. SQL Transaction Integrity

- Use of Parameterized Queries to ensure data integrity and security.
- Explicit transaction handling (commit/rollback) to prevent partial data writes.

## 5. Success Criteria

| Criteria | Target |
|----------|--------|
| Zero Data Loss | 100% of triggered recipes reach SQL, regardless of network state |
| Autonomous Operation | Zero manual intervention required after a power cycle |
| Transparency | Fault finding can be completed in <2 minutes using the provided event logs |

## 6. Out of Scope

- HMI Screen design (beyond status/trigger indicators)
- Historical data visualization or reporting tools
