"""
SQL Client - Microsoft SQL Server communication via pyodbc
"""

import time
import pyodbc
from loguru import logger


class SQLClient:
    """Handles SQL Server database operations with retry logic."""

    def __init__(self, config: dict):
        self.connection_string = config["connection_string"]
        self.table = config.get("table", "dbo.X_RecipeLog")
        self.max_retries = config.get("max_retries", 3)
        self.retry_base_delay = config.get("retry_base_delay_s", 1)
        self.retry_max_delay = config.get("retry_max_delay_s", 60)

        # Configurable timestamp column (default matches existing schema)
        self.timestamp_column = config.get("timestamp_column", "Manufacture_Date")

        self._connection = None
        self._connected = False

    def connect(self) -> bool:
        """Establish connection to SQL Server."""
        try:
            self._connection = pyodbc.connect(self.connection_string, timeout=10)
            self._connected = True
            logger.info("Connected to SQL Server")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to SQL Server: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Close SQL connection."""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None
            self._connected = False
            logger.info("Disconnected from SQL Server")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def insert_record(self, data: dict, mappings: dict) -> bool:
        """
        Insert a recipe record into SQL Server.

        Args:
            data: Recipe data from PLC
            mappings: PLC field -> SQL column mappings

        Returns:
            True if successful, False otherwise
        """
        for attempt in range(self.max_retries):
            try:
                if not self._ensure_connected():
                    raise ConnectionError("Cannot connect to SQL Server")

                # Build parameterized INSERT statement
                columns = []
                placeholders = []
                values = []

                for plc_field, sql_column in mappings.items():
                    if plc_field in data:
                        value = data[plc_field]
                        # Skip None values
                        if value is not None:
                            columns.append(sql_column)
                            placeholders.append("?")
                            values.append(value)

                # Add timestamp (ISO 8601 format)
                if self.timestamp_column:
                    columns.append(self.timestamp_column)
                    placeholders.append("?")
                    values.append(time.strftime("%Y-%m-%d %H:%M:%S"))

                if not columns:
                    logger.warning("No data to insert - all fields were None or unmapped")
                    return True  # Nothing to insert, but not an error

                sql = f"INSERT INTO {self.table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

                cursor = self._connection.cursor()
                cursor.execute(sql, values)
                self._connection.commit()
                cursor.close()

                logger.info(f"Inserted record to {self.table} ({len(columns)} columns)")
                return True

            except pyodbc.IntegrityError as e:
                # Duplicate key or constraint violation - don't retry
                logger.error(f"SQL integrity error (not retrying): {e}")
                return False

            except Exception as e:
                logger.warning(f"SQL insert attempt {attempt + 1} failed: {e}")
                self._connected = False

                if attempt < self.max_retries - 1:
                    delay = self._calculate_backoff(attempt)
                    logger.info(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)

        logger.error("All SQL insert attempts failed")
        return False

    def test_connection(self) -> bool:
        """Test if SQL connection is alive."""
        if not self._connected or not self._connection:
            return False

        try:
            cursor = self._connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except Exception:
            self._connected = False
            return False

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        delay = self.retry_base_delay * (2 ** attempt)
        return min(delay, self.retry_max_delay)

    def _ensure_connected(self) -> bool:
        """Ensure SQL connection is active, reconnect if needed."""
        if self._connected and self._connection:
            # Test connection with simple query
            if self.test_connection():
                return True

        # Need to reconnect
        self._connected = False
        return self.connect()
