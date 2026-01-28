# Troubleshooting Guide

Common issues and solutions for SQLlog.

## Quick Diagnostics

```bash
# Test connections
python test_connections.py

# Run in console mode to see errors
python -m src.main

# Check recent logs
type logs\sqllog.log
```

## PLC Connection Issues

### Cannot Connect to PLC

**Symptoms:**
- "CommError" in logs
- "Failed to connect to PLC" message
- Timeout errors

**Solutions:**

1. **Verify network connectivity:**
   ```bash
   ping 192.168.50.10
   ```

2. **Check Ethernet/IP port is open:**
   ```bash
   # PowerShell
   Test-NetConnection -ComputerName 192.168.50.10 -Port 44818
   ```

3. **Verify PLC is in Run mode** - Check PLC keyswitch or software

4. **Check slot number:**
   - CompactLogix: Usually slot 0
   - ControlLogix: Check backplane position

5. **Firewall settings:**
   - Allow outbound TCP port 44818
   - Allow outbound UDP port 2222 (CIP)

### Tag Read Errors

**Symptoms:**
- "Tag not found" errors
- "Invalid tag" in logs

**Solutions:**

1. **Verify tag exists in PLC:**
   - Check spelling and case
   - Verify tag scope (controller vs program scope)

2. **Check tag path for UDTs:**
   ```
   RECIPE[0]              # Correct
   Recipe[0]              # May fail (case sensitive)
   Program:Main.RECIPE[0] # Program-scoped tag
   ```

3. **Test tag with connection script:**
   ```python
   from pycomm3 import LogixDriver
   with LogixDriver("192.168.50.10") as plc:
       result = plc.read("RECIPE[0].RECIPE_NUMBER")
       print(result)
   ```

### Heartbeat Not Updating

**Symptoms:**
- PLC heartbeat tag stays constant
- Watchdog alarm in PLC

**Solutions:**

1. **Verify heartbeat tag name** matches config
2. **Check service is running:** `sc query SQLlogService`
3. **Look for connection errors** in logs
4. **Verify tag is writable** (not read-only)

## SQL Connection Issues

### Cannot Connect to SQL Server

**Symptoms:**
- "Connection failed" errors
- "Login failed" messages
- Timeout connecting

**Solutions:**

1. **Verify ODBC Driver installed:**
   ```powershell
   Get-OdbcDriver | Where-Object {$_.Name -like "*SQL Server*"}
   ```

2. **Test connection string:**
   ```bash
   python test_connections.py --sql
   ```

3. **Check SQL Server is running:**
   ```bash
   sc query MSSQLSERVER
   # or for named instance
   sc query MSSQL$SQLEXPRESS
   ```

4. **Verify remote connections enabled:**
   - SQL Server Configuration Manager
   - Enable TCP/IP protocol
   - Restart SQL Server

5. **Check firewall:**
   - Allow inbound TCP 1433 on SQL Server
   - Allow outbound TCP 1433 on client

6. **Verify credentials:**
   - Check `.env` file has correct password
   - Verify SQL login is enabled
   - Check user has database access

### Table Not Found

**Symptoms:**
- "Invalid object name" errors
- "Table does not exist"

**Solutions:**

1. **Verify table name in config:**
   ```yaml
   sql:
     table: "dbo.X_RecipeLog"  # Include schema
   ```

2. **Check database name** in connection string

3. **Verify user permissions:**
   ```sql
   GRANT SELECT, INSERT ON dbo.X_RecipeLog TO your_user;
   ```

### Insert Failures

**Symptoms:**
- "Column does not exist"
- "Cannot insert NULL"
- "String truncation"

**Solutions:**

1. **Verify column mappings** match actual table schema

2. **Check data types:**
   - PLC DINT → SQL INT/BIGINT
   - PLC STRING → SQL VARCHAR(length)
   - PLC REAL → SQL FLOAT/DECIMAL

3. **Check column lengths** for string fields

4. **Verify nullable columns** or provide defaults

## Windows Service Issues

### Service Won't Start

**Symptoms:**
- "Error 1053: Service did not respond"
- "Error 1067: Process terminated unexpectedly"

**Solutions:**

1. **Run in console mode first:**
   ```bash
   python -m src.main
   ```
   This shows startup errors interactively.

2. **Check config.yaml exists** and is valid

3. **Check .env file exists** with correct password

4. **Check Windows Event Viewer:**
   - Event Viewer → Windows Logs → Application
   - Look for "SQLlogService" errors

5. **Verify Python path** in service configuration

6. **Check permissions:**
   - Service account needs file access
   - Service account needs network access

### Service Stops Unexpectedly

**Symptoms:**
- Service status shows "Stopped"
- No error in service manager

**Solutions:**

1. **Check logs** for errors before stop

2. **Check available disk space** for logs

3. **Check memory usage** - possible leak

4. **Look for unhandled exceptions** in logs

## Data Issues

### Duplicate Records

**Symptoms:**
- Same record appears multiple times
- Sequence numbers repeated

**Solutions:**

1. **Check handshake timing** - PLC may be re-triggering

2. **Verify PLC logic** resets trigger only after seeing ACK (2)

3. **Check network stability** - retries may cause duplicates

### Missing Records

**Symptoms:**
- Gaps in sequence numbers
- Records triggered but not in SQL

**Solutions:**

1. **Check local cache:**
   ```bash
   sqlite3 cache.db "SELECT COUNT(*) FROM pending_records;"
   ```

2. **Look for validation failures** in logs

3. **Check for SQL errors** during insert

4. **Verify handshake completing** - check PLC sees reset to 0

### Wrong Data Values

**Symptoms:**
- Values don't match PLC
- Columns have wrong data

**Solutions:**

1. **Verify mappings** in config.yaml

2. **Check data type conversions:**
   - REAL precision
   - STRING encoding

3. **Verify correct tags** being read

## Performance Issues

### Slow Response

**Symptoms:**
- High latency between trigger and log
- Polling delays

**Solutions:**

1. **Reduce poll interval:**
   ```yaml
   plc:
     poll_interval_ms: 50  # Faster polling
   ```

2. **Check network latency:**
   ```bash
   ping -n 100 192.168.50.10
   ```

3. **Check SQL Server performance** - index optimization

### High CPU Usage

**Symptoms:**
- SQLlog using excessive CPU
- System slowdown

**Solutions:**

1. **Increase poll interval** if too aggressive

2. **Check for connection retry loops** in logs

3. **Review log verbosity:**
   ```yaml
   logging:
     level: "INFO"  # Not DEBUG
   ```

## Getting Help

### Collect Diagnostic Information

Before requesting help, gather:

1. **Log files:** `logs/sqllog.log`
2. **Configuration (sanitized):** Remove passwords
3. **Connection test output:** `python test_connections.py`
4. **Python version:** `python --version`
5. **OS version:** `winver`
6. **Error messages:** Exact text

### Log Levels

Increase logging for debugging:

```yaml
logging:
  level: "DEBUG"
```

Remember to set back to "INFO" after troubleshooting.
