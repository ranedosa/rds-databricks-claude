#!/usr/bin/env python3
"""Check the actual current state of all rows in the table."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

# Load credentials from .databrickscfg
config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

table_name = "rds.pg_rds_enterprise_public.enterprise_property"

print("=" * 80)
print("CHECKING ACTUAL CURRENT ROW STATE")
print("=" * 80)

try:
    warehouses = list(w.warehouses.list())
    warehouse = warehouses[0]
    print(f"\nUsing SQL Warehouse: {warehouse.name}")

    # Query 1: Try to bypass the row filter by reading from delta table directly
    print(f"\n{'=' * 80}")
    print("ATTEMPT 1: Query all rows including _fivetran_deleted column")
    print(f"{'=' * 80}")

    # Use delta table path to bypass row filter
    query = f"""
    SELECT
        COUNT(*) as total_rows,
        SUM(CASE WHEN _fivetran_deleted = true THEN 1 ELSE 0 END) as deleted_count,
        SUM(CASE WHEN _fivetran_deleted = false THEN 1 ELSE 0 END) as active_count,
        SUM(CASE WHEN _fivetran_deleted IS NULL THEN 1 ELSE 0 END) as null_count
    FROM delta.`s3://snappt-metastore-prod/f6d2e06c-8023-4185-b6d6-fc5cdfcacbf3/tables/02f90026-acc1-4b27-9b5a-bbdc0734fdce`
    """

    print("\nQuerying Delta table directly (bypassing row filter)...")
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        row = result.result.data_array[0]
        total = row[0]
        deleted = row[1]
        active = row[2]
        null_count = row[3]

        print(f"\n📊 CURRENT STATE OF ALL ROWS:")
        print(f"   Total Rows: {total}")
        print(f"   _fivetran_deleted = true: {deleted}")
        print(f"   _fivetran_deleted = false: {active}")
        print(f"   _fivetran_deleted IS NULL: {null_count}")
        print(f"\n   Visible through row filter: {active}")
        print(f"   Hidden by row filter: {deleted}")

    # Query 2: Check when deleted rows were last synced
    print(f"\n{'=' * 80}")
    print("ATTEMPT 2: Check deleted rows timeline")
    print(f"{'=' * 80}")

    query = f"""
    SELECT
        DATE(_fivetran_synced) as sync_date,
        COUNT(*) as row_count
    FROM delta.`s3://snappt-metastore-prod/f6d2e06c-8023-4185-b6d6-fc5cdfcacbf3/tables/02f90026-acc1-4b27-9b5a-bbdc0734fdce`
    WHERE _fivetran_deleted = true
    GROUP BY DATE(_fivetran_synced)
    ORDER BY sync_date DESC
    LIMIT 30
    """

    print("\nChecking when deleted rows were last synced...")
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        print(f"\nDeleted rows by sync date:")
        print(f"{'Date':<20} {'Count':<10}")
        print("-" * 30)
        for row in result.result.data_array:
            print(f"{row[0]:<20} {row[1]:<10}")
    else:
        print("\nNo deleted rows found or query returned empty")

    # Query 3: Sample of deleted rows
    print(f"\n{'=' * 80}")
    print("ATTEMPT 3: Sample deleted rows")
    print(f"{'=' * 80}")

    query = f"""
    SELECT
        id,
        snappt_property_id,
        created_at,
        updated_at,
        _fivetran_synced,
        _fivetran_deleted
    FROM delta.`s3://snappt-metastore-prod/f6d2e06c-8023-4185-b6d6-fc5cdfcacbf3/tables/02f90026-acc1-4b27-9b5a-bbdc0734fdce`
    WHERE _fivetran_deleted = true
    ORDER BY _fivetran_synced DESC
    LIMIT 10
    """

    print("\nGetting sample of deleted rows...")
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        print(f"\nSample deleted rows (most recently synced):")
        for i, row in enumerate(result.result.data_array, 1):
            print(f"\n  Row {i}:")
            print(f"    ID: {row[0]}")
            print(f"    Property ID: {row[1]}")
            print(f"    Created: {row[2]}")
            print(f"    Updated: {row[3]}")
            print(f"    Last Synced: {row[4]}")
            print(f"    Deleted: {row[5]}")
    else:
        print("\nNo deleted rows found")

    # Query 4: Check the active row
    print(f"\n{'=' * 80}")
    print("ATTEMPT 4: Check the 1 active row")
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
    FROM delta.`s3://snappt-metastore-prod/f6d2e06c-8023-4185-b6d6-fc5cdfcacbf3/tables/02f90026-acc1-4b27-9b5a-bbdc0734fdce`
    WHERE _fivetran_deleted = false
    """

    print("\nGetting active rows...")
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        print(f"\nFound {len(result.result.data_array)} active row(s):")
        for i, row in enumerate(result.result.data_array, 1):
            print(f"\n  Active Row {i}:")
            print(f"    ID: {row[0]}")
            print(f"    Property ID: {row[1]}")
            print(f"    Integration ID: {row[2]}")
            print(f"    Created: {row[3]}")
            print(f"    Updated: {row[4]}")
            print(f"    Last Synced: {row[5]}")
            print(f"    Deleted: {row[6]}")

    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print("""
Based on the results above, we can now answer your question:

IF the deleted rows count is STILL high (e.g., 823 out of 824 rows):
   → The rows are STILL DELETED in your source PostgreSQL database
   → They were deleted on Oct 13 and NEVER restored
   → Fivetran is correctly reflecting the current state of PostgreSQL
   → Your question is correct: IF they were restored, Fivetran WOULD pick them up

IF the deleted rows count is low and we see many active rows:
   → The row filter might be configured differently
   → OR there's another issue with the query/permissions

Check the counts above to determine what's really happening.

NEXT STEP:
   Check your source PostgreSQL database directly:

   SELECT COUNT(*) FROM enterprise_property;
   SELECT COUNT(*) FROM enterprise_property WHERE [your_delete_condition];
    """)

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

print("=" * 80)
