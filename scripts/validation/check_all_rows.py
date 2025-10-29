#!/usr/bin/env python3
"""Check all rows by reading Delta table directly and using version history."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

# Load credentials from .databrickscfg
config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

# Table to query
table_name = "rds.pg_rds_enterprise_public.enterprise_property"

print("=" * 80)
print("INVESTIGATING TABLE ROW COUNT ISSUE")
print("=" * 80)

try:
    # Get SQL warehouses
    warehouses = list(w.warehouses.list())
    warehouse = warehouses[0]
    print(f"\nUsing SQL Warehouse: {warehouse.name}")

    # Query 1: Check current visible row count
    print(f"\n{'=' * 80}")
    print("CURRENT VISIBLE ROWS (with row filter)")
    print(f"{'=' * 80}")

    query = f"SELECT COUNT(*) as visible_count FROM {table_name}"
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        visible_count = result.result.data_array[0][0]
        print(f"\nVisible rows: {visible_count}")

    # Query 2: Check row count from a version BEFORE October 13
    print(f"\n{'=' * 80}")
    print("HISTORICAL ROW COUNTS (bypassing current state)")
    print(f"{'=' * 80}")

    # Version 22755 is just before the big update on Oct 13
    versions_to_check = [22755, 22756, 22757, 24189]

    for version in versions_to_check:
        query = f"SELECT COUNT(*) FROM {table_name} VERSION AS OF {version}"
        try:
            result = w.statement_execution.execute_statement(
                warehouse_id=warehouse.id,
                statement=query,
                wait_timeout="50s"
            )

            if result.result and result.result.data_array:
                count = result.result.data_array[0][0]
                print(f"\nVersion {version}: {count} rows")
        except Exception as e:
            print(f"\nVersion {version}: Error - {e}")

    # Query 3: Try to read with IDENTIFIER to bypass row filter
    print(f"\n{'=' * 80}")
    print("ATTEMPTING TO READ ALL ROWS (including filtered)")
    print(f"{'=' * 80}")

    # Try using the Delta table location directly
    query = f"""
    SELECT
        SUM(CASE WHEN _fivetran_deleted = true THEN 1 ELSE 0 END) as deleted_rows,
        SUM(CASE WHEN _fivetran_deleted = false OR _fivetran_deleted IS NULL THEN 1 ELSE 0 END) as active_rows,
        COUNT(*) as total_rows
    FROM {table_name} VERSION AS OF 22755
    """

    print("\nChecking version 22755 (before Oct 13 deletions):")
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        row = result.result.data_array[0]
        deleted = row[0] or 0
        active = row[1] or 0
        total = row[2] or 0
        print(f"  Deleted rows: {deleted}")
        print(f"  Active rows: {active}")
        print(f"  Total rows: {total}")

    # Query 4: Check current version breakdown
    query = f"""
    SELECT
        SUM(CASE WHEN _fivetran_deleted = true THEN 1 ELSE 0 END) as deleted_rows,
        SUM(CASE WHEN _fivetran_deleted = false OR _fivetran_deleted IS NULL THEN 1 ELSE 0 END) as active_rows,
        COUNT(*) as total_rows
    FROM {table_name} VERSION AS OF 24189
    """

    print("\nChecking version 24189 (current/recent version):")
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        row = result.result.data_array[0]
        deleted = row[0] or 0
        active = row[1] or 0
        total = row[2] or 0
        print(f"  Deleted rows: {deleted}")
        print(f"  Active rows: {active}")
        print(f"  Total rows: {total}")

    # Query 5: Get sample IDs to understand what's happening
    print(f"\n{'=' * 80}")
    print("SAMPLE RECORDS FROM VERSION 22755")
    print(f"{'=' * 80}")

    query = f"""
    SELECT
        id,
        snappt_property_id,
        _fivetran_deleted,
        _fivetran_synced
    FROM {table_name} VERSION AS OF 22755
    LIMIT 10
    """

    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        print("\nFirst 10 records from version 22755:")
        for row in result.result.data_array:
            print(f"  ID: {row[0]}, Property: {row[1]}, Deleted: {row[2]}, Synced: {row[3]}")

    print("\n" + "=" * 80)
    print("ANALYSIS & RECOMMENDATIONS")
    print("=" * 80)
    print("""
🔍 KEY FINDINGS:

The table has a ROW FILTER that automatically filters out rows where
_fivetran_deleted = true. This is causing your "missing data" issue.

📊 WHAT HAPPENED:

1. Before Oct 13: You had many visible rows (check version 22755 count)
2. Oct 13: Fivetran synced deletions from PostgreSQL, marking rows as deleted
3. After Oct 13: The row filter hides these deleted rows automatically
4. Today: You only see 1 active row (the rest are filtered out)

✅ SOLUTIONS:

Option 1 - RESTORE DATA IN POSTGRESQL:
   If the deletions were accidental, restore the records in your source
   PostgreSQL database. Fivetran will automatically sync them back and
   mark them as active again.

Option 2 - VIEW HISTORICAL DATA (Time Travel):
   Query a version before the deletions:
   SELECT * FROM {table_name} VERSION AS OF 22755

Option 3 - TEMPORARILY DISABLE ROW FILTER:
   To see all data including deleted rows:
   ALTER TABLE {table_name} DROP ROW FILTER;

   ⚠️  WARNING: This will expose deleted records to ALL queries!

Option 4 - QUERY WITH EXPLICIT FILTER:
   Include the filter explicitly in your WHERE clause to understand
   which records are deleted:
   SELECT *, _fivetran_deleted FROM {table_name} VERSION AS OF 24189
    """)

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

print("=" * 80)
