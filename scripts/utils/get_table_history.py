#!/usr/bin/env python3
"""Get table history information for a Databricks table."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
import json
import time

# Load credentials from .databrickscfg
config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

# Table to query
table_name = "rds.pg_rds_enterprise_public.enterprise_property"

print("=" * 80)
print(f"TABLE HISTORY: {table_name}")
print("=" * 80)

try:
    # Get SQL warehouses to execute the query
    warehouses = list(w.warehouses.list())

    if not warehouses:
        print("No SQL warehouses found. Please create a SQL warehouse first.")
        exit(1)

    # Use the first available warehouse
    warehouse = warehouses[0]
    print(f"\nUsing SQL Warehouse: {warehouse.name} (ID: {warehouse.id})")
    print(f"State: {warehouse.state.value if warehouse.state else 'UNKNOWN'}")

    # First, check table properties
    print(f"\n{'=' * 80}")
    print("TABLE PROPERTIES")
    print(f"{'=' * 80}")
    print(f"\nExecuting: DESCRIBE EXTENDED {table_name}")

    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=f"DESCRIBE EXTENDED {table_name}",
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        print("\nTable Details:")
        for row in result.result.data_array:
            if row and len(row) >= 2:
                col_name = row[0]
                data_type = row[1]
                if col_name:
                    print(f"  {col_name}: {data_type}")

    # Execute DESCRIBE HISTORY query
    print(f"\n{'=' * 80}")
    print("TABLE HISTORY")
    print(f"{'=' * 80}")
    print(f"\nExecuting: DESCRIBE HISTORY {table_name}")
    print("Waiting for results...")

    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=f"DESCRIBE HISTORY {table_name}",
        wait_timeout="50s"
    )

    if result.status and result.status.state:
        print(f"Query Status: {result.status.state.value}")

    # Print results
    if result.result and result.result.data_array:
        # Get column names from manifest
        columns = []
        if result.manifest and result.manifest.schema and result.manifest.schema.columns:
            columns = [col.name for col in result.manifest.schema.columns]
            print(f"\nColumns: {', '.join(columns)}")

        print(f"\nFound {len(result.result.data_array)} history record(s)\n")

        # Print each history record
        for idx, row in enumerate(result.result.data_array, 1):
            print(f"{'=' * 80}")
            print(f"Record #{idx}")
            print(f"{'=' * 80}")

            # Print each column value
            for col_name, value in zip(columns, row):
                # Format nested values nicely
                if value and isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                    try:
                        parsed = json.loads(value)
                        value = json.dumps(parsed, indent=2)
                    except:
                        pass
                print(f"{col_name}: {value}")
            print()
    else:
        print("\nNo history records found or empty result.")
        print("This might not be a Delta table, or it has no version history yet.")

        # Check if there's an error
        if result.status and result.status.error:
            print(f"\nError details: {result.status.error}")

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

print("=" * 80)
