"""
SQL Integration Test - Verifies database connection and record insertion.
"""

import sys
from pathlib import Path
from uuid import uuid4

# Add src to path to allow imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.sql_client import SQLClient
from utils.config import load_config


def main():
    """
    Runs a test to check SQL connectivity, insert a record, and verify it.
    """
    print("--- Running SQL Integration Test ---")
    
    # --- 1. Load Configuration ---
    try:
        config_path = Path(__file__).parent / "config.yaml"
        if not config_path.exists():
            print(f"FAIL: Configuration file not found at {config_path}")
            print("Please copy config.yaml.example to config.yaml and configure it.")
            return

        config = load_config(config_path)
        sql_config = config.get("sql")
        mappings = config.get("mappings", {})
        
        # We need a field to store our unique ID. Let's find the SQL column for 'sequence_number'
        # This is mapped in `main.py` but we can replicate the logic here.
        if "sequence_number" in config.get("extra_tags", {}):
            unique_id_field = "SEQ_Number"
        else:
            # Fallback to another potential field if sequence_number isn't used
            # This part might need adjustment based on the user's config.yaml
            # For now, we'll assume SEQ_Number is available from the mappings.
            plc_field = next((k for k, v in mappings.items() if v == "SEQ_Number"), None)
            if plc_field is None:
                print("FAIL: The test requires a mapping to the 'SEQ_Number' SQL column.")
                print("Please ensure 'sequence_number' is in 'extra_tags' or a mapping to 'SEQ_Number' exists.")
                return
            unique_id_field = "SEQ_Number"

        print("✅ 1. Configuration loaded successfully.")
    except Exception as e:
        print(f"FAIL: Failed to load or parse configuration: {e}")
        return

    # --- 2. Connect to Database ---
    sql_client = SQLClient(sql_config)
    if not sql_client.connect():
        print("FAIL: Could not connect to the SQL Server.")
        print("Please check the 'sql.connection_string' in your config.yaml.")
        return
    print("✅ 2. Database connection successful.")

    # --- 3. Insert Test Record ---
    test_id = str(uuid4())
    test_record_plc_data = {
        "sequence_number": test_id,
        # Add a couple of other fields to make the record more realistic
        "recipe_name": "Test Recipe",
        "recipe_sp": 100.0,
    }
    
    # Combine standard mappings with extra mappings for insertion
    full_mappings = mappings.copy()
    full_mappings["sequence_number"] = unique_id_field
    full_mappings["recipe_name"] = "Recipe_Name"
    full_mappings["recipe_sp"] = "RECIPE_SP"

    print(f"Attempting to insert a test record with {unique_id_field} = {test_id}...")
    if not sql_client.insert_record(test_record_plc_data, full_mappings):
        print("FAIL: Failed to insert the test record into the database.")
        sql_client.disconnect()
        return
    print("✅ 3. Test record inserted successfully.")

    # --- 4. Verify Record Existence ---
    print(f"Verifying the test record by querying for {unique_id_field} = {test_id}...")
    verified_record = sql_client.find_record_by_field(unique_id_field, test_id)
    
    sql_client.disconnect() # Disconnect after we're done with DB operations

    if not verified_record:
        print(f"FAIL: Could not find the test record with {unique_id_field} = {test_id} after insertion.")
        return

    print("✅ 4. Test record successfully found in the database.")
    
    # --- 5. Final Result ---
    print("\n--- ✅ PASS: SQL Integration Test Successful ---")
    print(f"Verified record content for {unique_id_field}: {verified_record.get(unique_id_field)}")


if __name__ == "__main__":
    main()
