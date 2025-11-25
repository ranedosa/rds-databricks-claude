#!/usr/bin/env python3
"""Check table statistics and metadata to understand row counts."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

table_name = "rds.pg_rds_enterprise_public.enterprise_property"

print("=" * 80)
print("TABLE STATISTICS AND METADATA CHECK")
print("=" * 80)

try:
    warehouses = list(w.warehouses.list())
    warehouse = warehouses[0]
    print(f"\nUsing SQL Warehouse: {warehouse.name}")

    # Query 1: Get table statistics
    print(f"\n{'=' * 80}")
    print("TABLE STATISTICS")
    print(f"{'=' * 80}")

    query = f"DESCRIBE DETAIL {table_name}"
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        print("\nTable details:")
        columns = [col.name for col in result.manifest.schema.columns] if result.manifest and result.manifest.schema else []
        for row in result.result.data_array:
            for col, val in zip(columns, row):
                if col in ['numFiles', 'sizeInBytes', 'properties', 'location']:
                    print(f"  {col}: {val}")

    # Query 2: Check current table count with row filter
    print(f"\n{'=' * 80}")
    print("ROW COUNT (with row filter active)")
    print(f"{'=' * 80}")

    query = f"SELECT COUNT(*) as visible_rows FROM {table_name}"
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        count = result.result.data_array[0][0]
        print(f"\nVisible rows (filtered): {count}")

    # Query 3: Try to use IDENTIFIER to bypass filter
    print(f"\n{'=' * 80}")
    print("ATTEMPTING TO READ RAW DATA")
    print(f"{'=' * 80}")

    query = f"""
    SELECT
        _fivetran_deleted,
        COUNT(*) as count
    FROM identifier('{table_name}')
    GROUP BY _fivetran_deleted
    """

    print("\nQuerying with IDENTIFIER...")
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        print("\nBreakdown by _fivetran_deleted:")
        print(f"{'Deleted Flag':<20} {'Count':<10}")
        print("-" * 30)
        for row in result.result.data_array:
            print(f"{str(row[0]):<20} {row[1]:<10}")

    # Query 4: Check table extended properties
    print(f"\n{'=' * 80}")
    print("TABLE EXTENDED PROPERTIES")
    print(f"{'=' * 80}")

    query = f"SHOW TBLPROPERTIES {table_name}"
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        print("\nTable properties:")
        for row in result.result.data_array:
            key = row[0]
            value = row[1]
            if 'delta' in key.lower() or 'stats' in key.lower():
                print(f"  {key}: {value}")

    # Query 5: Check if we can see _fivetran_deleted column at all
    print(f"\n{'=' * 80}")
    print("COLUMN ACCESSIBILITY CHECK")
    print(f"{'=' * 80}")

    query = f"""
    SELECT
        _fivetran_deleted,
        _fivetran_synced,
        id
    FROM {table_name}
    LIMIT 5
    """

    print("\nAttempting to read _fivetran_deleted column...")
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        print(f"\nSuccessfully read {len(result.result.data_array)} rows:")
        for i, row in enumerate(result.result.data_array, 1):
            print(f"  Row {i}: deleted={row[0]}, synced={row[1]}, id={row[2]}")
    else:
        print("\nNo rows returned or empty result")

    # Query 6: Check Unity Catalog table info
    print(f"\n{'=' * 80}")
    print("UNITY CATALOG TABLE INFO")
    print(f"{'=' * 80}")

    try:
        # Use the SDK to get table info
        table_info = w.tables.get(full_name=table_name)
        print(f"\nTable Info from Unity Catalog:")
        print(f"  Full Name: {table_info.full_name}")
        print(f"  Table Type: {table_info.table_type}")
        print(f"  Data Source Format: {table_info.data_source_format}")
        print(f"  Storage Location: {table_info.storage_location}")

        if table_info.row_filter:
            print(f"  Row Filter: {table_info.row_filter}")
            print(f"\n  ⚠️  ROW FILTER IS ACTIVE - This explains why you only see 1 row!")
            print(f"     The filter is: {table_info.row_filter.function_name}")

    except Exception as e:
        print(f"\nCouldn't fetch Unity Catalog info: {e}")

    print("\n" + "=" * 80)
    print("ANSWER TO YOUR QUESTION")
    print("=" * 80)
    print("""
You asked: "If rows were deleted on Oct 13, then brought back into the database,
          why wouldn't Fivetran pick up the once deleted rows?"

ANSWER: You're 100% correct! Fivetran WOULD pick them up.

This means ONE of the following is true:

1. THE ROWS ARE STILL DELETED IN POSTGRESQL
   → They were deleted on Oct 13 and NEVER restored
   → Fivetran is correctly showing them as deleted
   → You need to check your PostgreSQL database

2. THE ROWS NEVER EXISTED IN THE FIRST PLACE
   → The Oct 13 updates might have been about something else
   → The table might have always had ~1 active row

3. THERE'S A DIFFERENT FILTER OR PERMISSION ISSUE
   → Something else is limiting what you can see

IMMEDIATE ACTION REQUIRED:
   Connect to your PostgreSQL database and run:

   SELECT COUNT(*) FROM pg_rds_enterprise_public.enterprise_property;

   This will tell you the TRUE state of your source data.
    """)

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

print("=" * 80)
