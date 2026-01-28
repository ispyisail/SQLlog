# Configuration Reference

Complete reference for SQLlog configuration files.

## Configuration Files

| File | Purpose | Git Tracked |
|------|---------|-------------|
| `config.yaml` | Main application configuration | No (contains site-specific settings) |
| `config.yaml.example` | Configuration template | Yes |
| `.env` | Sensitive credentials | No (contains passwords) |
| `.env.example` | Environment template | Yes |

## Environment Variables (.env)

Store sensitive values in `.env` file:

```ini
# SQL Server password
SQL_PASSWORD=your_password_here

# Optional: Full connection string override
# SQL_CONNECTION_STRING=Driver={ODBC Driver 18 for SQL Server};...
```

Environment variables can be referenced in `config.yaml` using `${VAR_NAME}` syntax.

## Main Configuration (config.yaml)

### PLC Section

```yaml
plc:
  # PLC network settings
  ip: "192.168.50.10"        # PLC IP address
  slot: 0                     # Slot number (0 for CompactLogix)
  poll_interval_ms: 100       # Polling interval in milliseconds

  # Handshake tags (must exist in PLC)
  trigger_tag: "SQLlog_Trigger"       # INT: 0=Idle, 1=Request, 2=Ack, 99=Fault
  heartbeat_tag: "SQLlog_Heartbeat"   # INT: Incremented every 2s
  error_code_tag: "SQLlog_Error_Code" # INT: Error code on fault

  # Recipe data tag (UDT)
  recipe_tag: "RECIPE[0]"             # Full UDT read
```

### SQL Section

```yaml
sql:
  # Connection string with environment variable substitution
  connection_string: >-
    Driver={ODBC Driver 18 for SQL Server};
    Server=SVR\SQLEXPRESS;
    Database=EXO_Live;
    UID=SA;
    PWD=${SQL_PASSWORD};
    TrustServerCertificate=yes;

  # Target table
  table: "dbo.X_RecipeLog"

  # Timestamp column (set to empty string to disable)
  timestamp_column: "Manufacture_Date"

  # Retry settings
  max_retries: 3              # Maximum retry attempts
  retry_base_delay_s: 1       # Initial retry delay
  retry_max_delay_s: 60       # Maximum retry delay (exponential backoff cap)
```

### Mappings Section

Map PLC UDT fields to SQL columns:

```yaml
mappings:
  # PLC_FIELD: "SQL_Column"
  RECIPE_NUMBER: "Recipe_Number"
  PRODUCT_NAME1: "Product_Name"
  PRODUCT_NAME2: "Customer_Note"

  # Bulk ingredients
  B1_WT: "B001_Weight"
  B2_WT: "B002_Weight"
  # ... etc

  # Minor ingredients
  INGRE_1_WT: "ING001_Weight"
  INGRE_2_WT: "ING002_Weight"
  # ... etc
```

### Extra Tags Section

Read additional tags not in the recipe UDT:

```yaml
extra_tags:
  sequence_number: "A_DINT[10]"        # -> SEQ_Number
  batch_ratio: "RECIPE_REAL[0,0]"      # -> BATCH_RATIO
  recycle_weight: "RECIPE_DINT[0,29]"  # -> RECYCLE_Weight
```

### Bulk Names Section

Read ingredient names from separate tags:

```yaml
bulk_names:
  slot_1: "REC_P_N_B[1].Name"   # -> B001_Name
  slot_2: "REC_P_N_B[2].Name"   # -> B002_Name
  # ... etc
```

### Validation Section

Data validation rules (optional):

```yaml
validation:
  limits:
    TOTAL_WT:
      min: 0
      max: 50000
    RECIPE_NUMBER:
      min: 1
      max: 99
    BATCH_RATIO:
      min: 0
      max: 100
```

Records failing validation are logged but not inserted.

### Logging Section

```yaml
logging:
  directory: "logs"           # Log directory
  rotation: "10 MB"           # Rotate at this size
  retention: "30 days"        # Keep logs for this duration
  level: "INFO"               # Minimum log level (DEBUG, INFO, WARNING, ERROR)
```

### Heartbeat Section

```yaml
heartbeat:
  interval_s: 2               # Heartbeat increment interval
```

### Local Cache Section

```yaml
local_cache:
  database: "cache.db"        # SQLite database filename
  sync_interval_s: 30         # Background sync attempt interval
```

## Environment Variable Substitution

Use `${VAR_NAME}` syntax to reference environment variables:

```yaml
sql:
  connection_string: "...;PWD=${SQL_PASSWORD};..."
```

With default values:

```yaml
logging:
  level: "${LOG_LEVEL:-INFO}"  # Uses INFO if LOG_LEVEL not set
```

## Complete Example

```yaml
# SQLlog Configuration

plc:
  ip: "192.168.50.10"
  slot: 0
  poll_interval_ms: 100
  trigger_tag: "SQLlog_Trigger"
  heartbeat_tag: "SQLlog_Heartbeat"
  error_code_tag: "SQLlog_Error_Code"
  recipe_tag: "RECIPE[0]"

sql:
  connection_string: "Driver={ODBC Driver 18 for SQL Server};Server=SVR\\SQLEXPRESS;Database=EXO_Live;UID=SA;PWD=${SQL_PASSWORD};TrustServerCertificate=yes;"
  table: "dbo.X_RecipeLog"
  timestamp_column: "Manufacture_Date"
  max_retries: 3
  retry_base_delay_s: 1
  retry_max_delay_s: 60

mappings:
  RECIPE_NUMBER: "Recipe_Number"
  PRODUCT_NAME1: "Product_Name"
  PRODUCT_NAME2: "Customer_Note"
  B1_WT: "B001_Weight"
  B2_WT: "B002_Weight"
  B3_WT: "B003_Weight"
  TOTAL_WT: "TOTAL_Weight"

extra_tags:
  sequence_number: "A_DINT[10]"
  batch_ratio: "RECIPE_REAL[0,0]"

validation:
  limits:
    TOTAL_WT:
      min: 0
      max: 50000

logging:
  directory: "logs"
  rotation: "10 MB"
  retention: "30 days"
  level: "INFO"

heartbeat:
  interval_s: 2

local_cache:
  database: "cache.db"
  sync_interval_s: 30
```

## Validating Configuration

Test your configuration:

```bash
# This will load and validate config
python -c "from src.utils.config import load_config; load_config('config.yaml')"
```

Errors will indicate missing required fields or invalid values.
