#!/usr/bin/env python3
"""Query to find the rows that were marked as deleted."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
import json

# Load credentials from .databrickscfg
config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

# Table to query
table_name = "rds.pg_rds_enterprise_public.enterprise_property"

print("=" * 80)
print("QUERYING DELETED ROWS")
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

    # Query 1: Count of deleted vs active rows
    print(f"\n{'=' * 80}")
    print("ROW COUNTS")
    print(f"{'=' * 80}")

    query = f"""
    SELECT
        _fivetran_deleted,
        COUNT(*) as row_count,
        MIN(_fivetran_synced) as first_synced,
        MAX(_fivetran_synced) as last_synced
    FROM {table_name}
    GROUP BY _fivetran_deleted
    ORDER BY _fivetran_deleted
    """

    print(f"\nExecuting query...")
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        print("\nResults:")
        print(f"{'Deleted':<15} {'Count':<15} {'First Synced':<30} {'Last Synced':<30}")
        print("-" * 90)
        for row in result.result.data_array:
            deleted = row[0] if row[0] else 'false'
            count = row[1]
            first = row[2]
            last = row[3]
            print(f"{deleted:<15} {count:<15} {first:<30} {last:<30}")

    # Query 2: Sample of deleted rows
    print(f"\n{'=' * 80}")
    print("SAMPLE OF DELETED ROWS")
    print(f"{'=' * 80}")

    query = f"""
    SELECT
        id,
        snappt_property_id,
        enterprise_integration_id,
        created_at,
        updated_at,
        _fivetran_synced,
        _fivetran_deleted
    FROM {table_name}
    WHERE _fivetran_deleted = true
    ORDER BY _fivetran_synced DESC
    LIMIT 20
    """

    print(f"\nExecuting query for deleted rows sample...")
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        columns = [col.name for col in result.manifest.schema.columns] if result.manifest and result.manifest.schema else []

        print(f"\nFound {len(result.result.data_array)} deleted rows (showing first 20)")
        print("\nSample deleted records:")

        for i, row in enumerate(result.result.data_array[:10], 1):
            print(f"\n--- Record {i} ---")
            for col, val in zip(columns, row):
                print(f"  {col}: {val}")

    # Query 3: Deletion timeline
    print(f"\n{'=' * 80}")
    print("DELETION TIMELINE")
    print(f"{'=' * 80}")

    query = f"""
    SELECT
        DATE(_fivetran_synced) as deletion_date,
        COUNT(*) as rows_marked_deleted
    FROM {table_name}
    WHERE _fivetran_deleted = true
    GROUP BY DATE(_fivetran_synced)
    ORDER BY deletion_date DESC
    LIMIT 30
    """

    print(f"\nExecuting deletion timeline query...")
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        print("\nDeletions by date:")
        print(f"{'Date':<20} {'Rows Marked Deleted':<20}")
        print("-" * 40)
        for row in result.result.data_array:
            date = row[0]
            count = row[1]
            print(f"{date:<20} {count:<20}")

    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print("""
1. CHECK SOURCE DATABASE:
   - Verify if these records were actually deleted in PostgreSQL
   - Check with your database admin about any bulk delete operations on Oct 13

2. RECOVER DATA (if needed):
   - If deletions were accidental, restore records in PostgreSQL
   - Fivetran will sync them back automatically

3. QUERY DELETED DATA:
   - Add WHERE _fivetran_deleted = false to see only active records
   - Or include deleted records explicitly in your queries

4. TIME TRAVEL (to see data before deletion):
   SELECT * FROM {table_name} VERSION AS OF 22755

   This will show you the table state before the Oct 13 deletions.

5. DISABLE ROW FILTER (if you want to see all records including deleted):
   ALTER TABLE {table_name} DROP ROW FILTER;

   WARNING: This will expose deleted records to all queries!
    """)

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

print("=" * 80)
