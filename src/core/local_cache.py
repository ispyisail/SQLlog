"""
Local Cache - SQLite store-and-forward buffer
"""

import sqlite3
import json
import threading
import time
from pathlib import Path
from loguru import logger


class LocalCache:
    """SQLite-based local cache for store-and-forward functionality."""

    def __init__(self, config: dict):
        self.db_path = Path(config.get("database", "cache.db"))
        self.sync_interval = config.get("sync_interval_s", 30)

        self._sync_thread = None
        self._stop_event = threading.Event()
        self._force_sync_event = None
        self._db_lock = threading.Lock()  # Thread safety for SQLite

        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection (thread-safe)."""
        return sqlite3.connect(str(self.db_path), check_same_thread=False)

    def _init_database(self):
        """Initialize SQLite database schema."""
        with self._db_lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pending_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    attempts INTEGER DEFAULT 0
                )
            """)

            # Store mappings separately (they don't change per record)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            conn.commit()
            conn.close()
        logger.debug("Local cache database initialized")

    def add_record(self, data: dict, mappings: dict) -> bool:
        """Add a record to the local cache."""
        with self._db_lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Store record
                cursor.execute(
                    "INSERT INTO pending_records (data, created_at) VALUES (?, ?)",
                    (json.dumps(data), time.strftime("%Y-%m-%dT%H:%M:%S"))
                )

                # Store/update mappings (only once, they're the same for all records)
                cursor.execute(
                    "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                    ("mappings", json.dumps(mappings))
                )

                conn.commit()
                conn.close()
                logger.info("Record added to local cache")
                return True
            except Exception as e:
                logger.error(f"Failed to add record to cache: {e}")
                return False

    def get_pending_count(self) -> int:
        """Get count of pending records."""
        with self._db_lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM pending_records")
                count = cursor.fetchone()[0]
                conn.close()
                return count
            except Exception:
                return 0

    def get_mappings(self) -> dict:
        """Get stored mappings from config table."""
        with self._db_lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM config WHERE key = ?", ("mappings",))
                row = cursor.fetchone()
                conn.close()

                if row:
                    return json.loads(row[0])
                return {}
            except Exception as e:
                logger.error(f"Failed to get mappings: {e}")
                return {}

    def get_oldest_record(self) -> tuple | None:
        """Get the oldest pending record (FIFO)."""
        with self._db_lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, data FROM pending_records ORDER BY id ASC LIMIT 1"
                )
                row = cursor.fetchone()
                conn.close()

                if row:
                    return (row[0], json.loads(row[1]))
                return None
            except Exception as e:
                logger.error(f"Failed to get oldest record: {e}")
                return None

    def remove_record(self, record_id: int) -> bool:
        """Remove a record from the cache after successful sync."""
        with self._db_lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM pending_records WHERE id = ?", (record_id,))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                logger.error(f"Failed to remove record {record_id}: {e}")
                return False

    def increment_attempts(self, record_id: int) -> bool:
        """Increment attempt counter for a record."""
        with self._db_lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE pending_records SET attempts = attempts + 1 WHERE id = ?",
                    (record_id,)
                )
                conn.commit()
                conn.close()
                return True
            except Exception:
                return False

    def start_sync_thread(self, sql_client, force_sync_event: threading.Event = None):
        """Start background thread to sync cached records to SQL."""
        self._stop_event.clear()
        self._force_sync_event = force_sync_event

        self._sync_thread = threading.Thread(
            target=self._sync_loop,
            args=(sql_client,),
            daemon=True
        )
        self._sync_thread.start()
        logger.info("Cache sync thread started")

    def stop_sync_thread(self):
        """Stop the sync thread."""
        self._stop_event.set()
        if self._force_sync_event:
            self._force_sync_event.set()  # Wake up if waiting

        if self._sync_thread:
            self._sync_thread.join(timeout=5)
        logger.info("Cache sync thread stopped")

    def _sync_loop(self, sql_client):
        """Background loop to sync cached records."""
        while not self._stop_event.is_set():
            try:
                self._sync_pending(sql_client)
            except Exception as e:
                logger.error(f"Sync loop error: {e}")

            # Wait for sync interval or force sync signal
            if self._force_sync_event:
                # Wait for either timeout or force sync
                triggered = self._force_sync_event.wait(self.sync_interval)
                if triggered:
                    self._force_sync_event.clear()
                    logger.info("Force sync triggered")
            else:
                self._stop_event.wait(self.sync_interval)

    def _sync_pending(self, sql_client):
        """Attempt to sync pending records to SQL Server."""
        pending = self.get_pending_count()
        if pending == 0:
            return

        logger.info(f"Attempting to sync {pending} cached records")

        # Get stored mappings
        mappings = self.get_mappings()
        if not mappings:
            logger.warning("No mappings found in cache, cannot sync")
            return

        synced = 0
        while not self._stop_event.is_set():
            record = self.get_oldest_record()
            if not record:
                break

            record_id, data = record

            if sql_client.insert_record(data, mappings):
                self.remove_record(record_id)
                synced += 1
                logger.info(f"Synced cached record {record_id}")
            else:
                # SQL still down, increment attempts and stop trying
                self.increment_attempts(record_id)
                break

        if synced > 0:
            logger.info(f"Sync complete: {synced} records uploaded")
