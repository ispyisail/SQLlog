# Installation Guide

Complete installation instructions for SQLlog.

## Prerequisites

### System Requirements

- **Operating System:** Windows 10/11 or Windows Server 2016+
- **Python:** 3.10 or higher
- **Memory:** 512 MB RAM minimum
- **Disk:** 100 MB for application, additional space for logs and cache

### Network Requirements

- Access to PLC on Ethernet/IP port 44818
- Access to SQL Server (default port 1433)
- No firewall blocking between host PC and PLC/SQL Server

### PLC Requirements

- Allen-Bradley Logix PLC (ControlLogix, CompactLogix, Micro800 series)
- Ethernet/IP communication enabled
- Recipe UDT structure accessible at configured tag

### SQL Server Requirements

- Microsoft SQL Server 2016 or later (including Express edition)
- Database and table created
- User account with INSERT permissions
- ODBC Driver 18 for SQL Server installed

## Step-by-Step Installation

### 1. Install Python

Download and install Python 3.10+ from [python.org](https://www.python.org/downloads/).

During installation:
- Check "Add Python to PATH"
- Check "Install pip"

Verify installation:
```bash
python --version
pip --version
```

### 2. Install ODBC Driver

Download and install [ODBC Driver 18 for SQL Server](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server).

Verify installation:
```bash
# PowerShell
Get-OdbcDriver | Where-Object {$_.Name -like "*SQL Server*"}
```

### 3. Clone or Download SQLlog

```bash
# Clone with git
git clone https://github.com/yourusername/SQLlog.git
cd SQLlog

# Or download and extract ZIP
```

### 4. Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

Dependencies installed:
- `pycomm3` - PLC communication
- `pyodbc` - SQL Server connection
- `loguru` - Logging
- `pystray` - System tray
- `Pillow` - Icon support
- `PyYAML` - Configuration
- `python-dotenv` - Environment variables
- `pywin32` - Windows service

### 6. Configure Environment

Create `.env` file for sensitive credentials:

```bash
copy .env.example .env
notepad .env
```

Edit `.env`:
```ini
SQL_PASSWORD=your_actual_password
```

### 7. Configure Application

```bash
copy config.yaml.example config.yaml
notepad config.yaml
```

Key settings to update:
- `plc.ip` - Your PLC's IP address
- `sql.connection_string` - Your SQL Server details
- `sql.table` - Target table name
- `mappings` - PLC tag to SQL column mappings

### 8. Create PLC Tags

Add these tags to your PLC program:

| Tag Name | Data Type | Description |
|----------|-----------|-------------|
| `SQLlog_Trigger` | INT | Handshake trigger (0/1/2/99) |
| `SQLlog_Heartbeat` | INT | Watchdog counter |
| `SQLlog_Error_Code` | INT | Error code on fault |

### 9. Create SQL Table

Ensure your target table exists with appropriate columns. Example:

```sql
CREATE TABLE dbo.X_RecipeLog (
    id INT IDENTITY(1,1) PRIMARY KEY,
    Manufacture_Date DATETIME DEFAULT GETDATE(),
    SEQ_Number VARCHAR(50),
    Recipe_Number VARCHAR(50),
    Product_Name VARCHAR(100),
    -- Add columns matching your mappings
);
```

### 10. Test Connections

```bash
python test_connections.py
```

Expected output:
```
PLC CONNECTION TEST
==================================================
[OK] Connected successfully
[OK] PLC connection test PASSED

SQL SERVER CONNECTION TEST
==================================================
[OK] Connected successfully
[OK] SQL connection test PASSED
```

### 11. Run Application

Console mode (for testing):
```bash
python -m src.main
```

With system tray:
```bash
python -m src.run_with_tray
```

## Windows Service Installation

For production deployment, install as a Windows service:

### Install Service

Run Command Prompt as Administrator:

```bash
cd C:\path\to\SQLlog
venv\Scripts\activate
python -m src.service install
```

### Configure Service

The service is installed with:
- **Name:** SQLlogService
- **Display Name:** SQLlog PLC Data Logger
- **Startup Type:** Automatic

### Start Service

```bash
python -m src.service start

# Or use Windows Services Manager
services.msc
```

### Service Management

```bash
# Stop service
python -m src.service stop

# Restart service
python -m src.service restart

# Remove service
python -m src.service remove

# Check status
sc query SQLlogService
```

## Verify Installation

1. Check service is running: `sc query SQLlogService`
2. Check logs: `type logs\sqllog.log`
3. Verify heartbeat incrementing in PLC
4. Trigger a test log and verify in SQL Server

## Updating

To update SQLlog:

```bash
# Stop service
python -m src.service stop

# Pull updates
git pull

# Update dependencies
pip install -r requirements.txt --upgrade

# Start service
python -m src.service start
```

## Uninstallation

```bash
# Remove service
python -m src.service remove

# Delete application folder
rmdir /s SQLlog
```
