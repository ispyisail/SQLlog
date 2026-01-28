"""
Connection Test Script - Test PLC and SQL connections without writing data

Usage:
    python test_connections.py          # Test both
    python test_connections.py --plc    # Test PLC only
    python test_connections.py --sql    # Test SQL only
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


def test_plc_connection(ip: str, slot: int = 0) -> bool:
    """
    Test PLC connection by reading a tag.

    Returns True if successful.
    """
    print(f"\n{'='*50}")
    print("PLC CONNECTION TEST")
    print(f"{'='*50}")
    print(f"IP: {ip}")
    print(f"Slot: {slot}")

    try:
        from pycomm3 import LogixDriver

        print("\nConnecting to PLC...")
        with LogixDriver(ip, slot=slot) as plc:
            print("[OK] Connected successfully")

            # Try to read PLC info
            print("\nReading PLC info...")
            info = plc.get_plc_info()
            print(f"  Product Name: {info.get('product_name', 'N/A')}")
            print(f"  Vendor: {info.get('vendor', 'N/A')}")
            print(f"  Serial: {info.get('serial', 'N/A')}")

            # Try to read RECIPE[0].RECIPE_NUMBER
            print("\nReading test tag (RECIPE[0].RECIPE_NUMBER)...")
            result = plc.read("RECIPE[0].RECIPE_NUMBER")
            if result.error:
                print(f"  [ERR] Error: {result.error}")
            else:
                print(f"  [OK] Value: {result.value}")

            # Try to read the full RECIPE[0] structure
            print("\nReading RECIPE[0] structure...")
            result = plc.read("RECIPE[0]")
            if result.error:
                print(f"  [ERR] Error: {result.error}")
            else:
                print(f"  [OK] Successfully read RECIPE[0]")
                if isinstance(result.value, dict):
                    print(f"  Fields: {len(result.value)} items")
                    # Show first few fields
                    for i, (key, value) in enumerate(result.value.items()):
                        if i >= 5:
                            print(f"    ... and {len(result.value) - 5} more")
                            break
                        print(f"    {key}: {value}")

            print("\n[OK] PLC connection test PASSED")
            return True

    except ImportError:
        print("[ERR] pycomm3 not installed. Run: pip install pycomm3")
        return False
    except Exception as e:
        print(f"\n[ERR] PLC connection test FAILED: {e}")
        return False


def test_sql_connection(connection_string: str) -> bool:
    """
    Test SQL Server connection by running a simple query.

    Returns True if successful.
    """
    print(f"\n{'='*50}")
    print("SQL SERVER CONNECTION TEST")
    print(f"{'='*50}")

    # Mask password in output
    masked_conn = connection_string
    if "PWD=" in masked_conn:
        start = masked_conn.find("PWD=") + 4
        end = masked_conn.find(";", start)
        if end == -1:
            end = len(masked_conn)
        masked_conn = masked_conn[:start] + "****" + masked_conn[end:]
    print(f"Connection: {masked_conn}")

    try:
        import pyodbc

        print("\nConnecting to SQL Server...")
        conn = pyodbc.connect(connection_string, timeout=10)
        print("[OK] Connected successfully")

        cursor = conn.cursor()

        # Test basic query
        print("\nTesting basic query (SELECT 1)...")
        cursor.execute("SELECT 1 AS test")
        row = cursor.fetchone()
        print(f"  [OK] Result: {row[0]}")

        # Get database info
        print("\nGetting database info...")
        cursor.execute("SELECT DB_NAME() AS db_name, @@VERSION AS version")
        row = cursor.fetchone()
        print(f"  Database: {row.db_name}")
        print(f"  Version: {row.version[:50]}...")

        # Check if X_RecipeLog table exists
        print("\nChecking for X_RecipeLog table...")
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'X_RecipeLog'
        """)
        exists = cursor.fetchone()[0] > 0
        if exists:
            print("  [OK] Table X_RecipeLog exists")

            # Get column info
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'X_RecipeLog'
                ORDER BY ORDINAL_POSITION
            """)
            columns = cursor.fetchall()
            print(f"  Columns: {len(columns)}")
            for col in columns[:10]:
                print(f"    - {col.COLUMN_NAME} ({col.DATA_TYPE})")
            if len(columns) > 10:
                print(f"    ... and {len(columns) - 10} more")

            # Get row count
            cursor.execute("SELECT COUNT(*) FROM X_RecipeLog")
            count = cursor.fetchone()[0]
            print(f"  Row count: {count}")
        else:
            print("  [WARN] Table X_RecipeLog not found")

        cursor.close()
        conn.close()

        print("\n[OK] SQL connection test PASSED")
        return True

    except ImportError:
        print("[ERR] pyodbc not installed. Run: pip install pyodbc")
        return False
    except Exception as e:
        print(f"\n[ERR] SQL connection test FAILED: {e}")
        return False


def build_connection_string() -> str:
    """Build SQL connection string from config and environment."""
    # Check for full connection string override
    if os.getenv("SQL_CONNECTION_STRING"):
        return os.getenv("SQL_CONNECTION_STRING")

    # Build from components
    password = os.getenv("SQL_PASSWORD", "")
    if not password:
        print("Warning: SQL_PASSWORD not set in .env file")

    return (
        f"Driver={{ODBC Driver 18 for SQL Server}};"
        f"Server=SVR\\SQLEXPRESS;"
        f"Database=EXO_Live;"
        f"UID=SA;"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
    )


def main():
    parser = argparse.ArgumentParser(description="Test PLC and SQL connections")
    parser.add_argument("--plc", action="store_true", help="Test PLC only")
    parser.add_argument("--sql", action="store_true", help="Test SQL only")
    parser.add_argument("--plc-ip", default="192.168.50.10", help="PLC IP address")
    args = parser.parse_args()

    # Default to testing both if neither specified
    test_plc = args.plc or (not args.plc and not args.sql)
    test_sql = args.sql or (not args.plc and not args.sql)

    results = {}

    if test_plc:
        results["PLC"] = test_plc_connection(args.plc_ip)

    if test_sql:
        conn_str = build_connection_string()
        results["SQL"] = test_sql_connection(conn_str)

    # Summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    for name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  {name}: {status}")

    # Exit code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
