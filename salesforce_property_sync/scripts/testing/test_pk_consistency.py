#!/usr/bin/env python3
"""Test primary key consistency between PostgreSQL and Databricks."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

table_name = "rds.pg_rds_enterprise_public.enterprise_property"

print("=" * 80)
print("PRIMARY KEY CONSISTENCY TEST")
print("=" * 80)

try:
    warehouses = list(w.warehouses.list())
    warehouse = warehouses[0]
    print(f"\nUsing SQL Warehouse: {warehouse.name}")

    # Test 1: Check PK constraint in Databricks
    print(f"\n{'=' * 80}")
    print("1. DATABRICKS PRIMARY KEY CONSTRAINT")
    print(f"{'=' * 80}")

    query = f"DESCRIBE TABLE EXTENDED {table_name}"
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        print("\nLooking for PRIMARY KEY constraint...")
        for row in result.result.data_array:
            if row[0] and 'PRIMARY' in str(row[0]).upper():
                print(f"  {row[0]}: {row[1]}")

    # Test 2: Check for duplicate PKs in Databricks
    print(f"\n{'=' * 80}")
    print("2. DATABRICKS PK UNIQUENESS CHECK")
    print(f"{'=' * 80}")

    query = f"""
    SELECT
        COUNT(*) as total_rows,
        COUNT(DISTINCT ctid_fivetran_id) as unique_pks,
        COUNT(*) - COUNT(DISTINCT ctid_fivetran_id) as duplicate_count
    FROM {table_name}
    """

    print("\nChecking for duplicate primary keys in Databricks...")
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    databricks_total = 0
    databricks_unique = 0
    if result.result and result.result.data_array:
        row = result.result.data_array[0]
        databricks_total = int(row[0]) if row[0] else 0
        databricks_unique = int(row[1]) if row[1] else 0
        duplicate_count = int(row[2]) if row[2] else 0

        print(f"\nDatabricks Results:")
        print(f"  Total Rows: {databricks_total}")
        print(f"  Unique PKs (ctid_fivetran_id): {databricks_unique}")
        print(f"  Duplicates: {duplicate_count}")

        if duplicate_count > 0:
            print(f"\n  ⚠️  WARNING: {duplicate_count} duplicate PKs found in Databricks!")
        else:
            print(f"\n  ✓ No duplicate PKs in Databricks")

    # Test 3: Get sample PKs from Databricks
    print(f"\n{'=' * 80}")
    print("3. SAMPLE PRIMARY KEYS IN DATABRICKS")
    print(f"{'=' * 80}")

    query = f"""
    SELECT
        ctid_fivetran_id,
        id,
        _fivetran_deleted,
        _fivetran_synced
    FROM {table_name}
    LIMIT 10
    """

    print("\nSample PKs currently in Databricks:")
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    databricks_pks = []
    if result.result and result.result.data_array:
        print(f"\n{'ctid_fivetran_id':<50} {'id':<40} {'Deleted':<10}")
        print("-" * 100)
        for row in result.result.data_array:
            pk = row[0]
            id_val = row[1]
            deleted = row[2]
            databricks_pks.append(pk)
            print(f"{str(pk):<50} {str(id_val):<40} {str(deleted):<10}")

    # Test 4: Check history for PK constraint violations
    print(f"\n{'=' * 80}")
    print("4. CHECKING HISTORY FOR PK VIOLATIONS")
    print(f"{'=' * 80}")

    query = f"DESCRIBE HISTORY {table_name} LIMIT 50"
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    print("\nSearching for operations that might indicate PK conflicts...")
    pk_issues_found = False

    if result.result and result.result.data_array:
        columns = [col.name for col in result.manifest.schema.columns] if result.manifest and result.manifest.schema else []

        for row in result.result.data_array:
            operation_metrics = None
            operation = None
            version = None
            timestamp = None

            for i, col in enumerate(columns):
                if col == 'operation':
                    operation = row[i]
                elif col == 'version':
                    version = row[i]
                elif col == 'timestamp':
                    timestamp = row[i]
                elif col == 'operationMetrics':
                    operation_metrics = row[i]

            # Look for failed operations or unusual metrics
            if operation_metrics and 'error' in str(operation_metrics).lower():
                print(f"\n  Version {version} - {timestamp}")
                print(f"    Operation: {operation}")
                print(f"    Metrics: {operation_metrics}")
                pk_issues_found = True

    if not pk_issues_found:
        print("\n  ✓ No obvious PK constraint violations found in recent history")

    # Test 5: Check if NULL PKs exist
    print(f"\n{'=' * 80}")
    print("5. CHECKING FOR NULL PRIMARY KEYS")
    print(f"{'=' * 80}")

    query = f"""
    SELECT COUNT(*) as null_pk_count
    FROM {table_name}
    WHERE ctid_fivetran_id IS NULL
    """

    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        null_count = result.result.data_array[0][0]
        if int(null_count or 0) > 0:
            print(f"\n  ⚠️  WARNING: {null_count} rows with NULL primary key!")
        else:
            print("\n  ✓ No NULL primary keys found")

    # Generate PostgreSQL queries
    print(f"\n{'=' * 80}")
    print("6. POSTGRESQL QUERIES TO RUN")
    print(f"{'=' * 80}")

    print("""
Please run these queries in your PostgreSQL database:

-- Query 1: Check total rows and unique PKs
SELECT
    COUNT(*) as total_rows,
    COUNT(DISTINCT ctid_fivetran_id) as unique_pks,
    COUNT(*) - COUNT(DISTINCT ctid_fivetran_id) as duplicate_count
FROM pg_rds_enterprise_public.enterprise_property;

-- Query 2: Check for NULL PKs
SELECT COUNT(*)
FROM pg_rds_enterprise_public.enterprise_property
WHERE ctid_fivetran_id IS NULL;

-- Query 3: Find duplicate PKs (if any)
SELECT ctid_fivetran_id, COUNT(*) as occurrence_count
FROM pg_rds_enterprise_public.enterprise_property
GROUP BY ctid_fivetran_id
HAVING COUNT(*) > 1
ORDER BY occurrence_count DESC
LIMIT 20;

-- Query 4: Sample PKs from PostgreSQL
SELECT ctid_fivetran_id, id, created_at
FROM pg_rds_enterprise_public.enterprise_property
ORDER BY created_at DESC
LIMIT 10;
    """)

    # Save sample PKs to file for comparison
    if databricks_pks:
        with open('databricks_sample_pks.txt', 'w') as f:
            f.write("Sample Primary Keys from Databricks:\n")
            f.write("=" * 80 + "\n")
            for pk in databricks_pks:
                f.write(f"{pk}\n")
        print("\n✓ Saved sample Databricks PKs to: databricks_sample_pks.txt")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY & NEXT STEPS")
    print(f"{'=' * 80}")

    print(f"""
📊 DATABRICKS CURRENT STATE:
   Total Rows: {databricks_total}
   Unique PKs: {databricks_unique}

📊 POSTGRESQL REPORTED STATE:
   Total Rows: 3,398 (as you mentioned)

🔍 PRIMARY KEY CONSISTENCY ANALYSIS:

✅ IF PostgreSQL shows:
   - Total rows: 3,398
   - Unique PKs: 3,398
   - Duplicates: 0

   THEN: PostgreSQL PKs are fine. The issue is with Fivetran sync.

❌ IF PostgreSQL shows:
   - Duplicates > 0

   THEN: Duplicate PKs in PostgreSQL are preventing Fivetran from syncing.

   FIX: Remove duplicate PKs in PostgreSQL:

   -- Find duplicates
   SELECT ctid_fivetran_id, array_agg(id) as duplicate_ids
   FROM pg_rds_enterprise_public.enterprise_property
   GROUP BY ctid_fivetran_id
   HAVING COUNT(*) > 1;

   -- Then decide which rows to keep and delete the rest

⚠️  IF PostgreSQL shows NULL PKs:

   THEN: NULL PKs will prevent Fivetran from syncing those rows.

   FIX: Update NULL PKs with unique values.

🔧 AFTER FIXING PKs IN POSTGRESQL:

   1. In Fivetran Dashboard:
      - Navigate to your connector
      - Find 'enterprise_property' table
      - Click "Reset table" or "Re-sync"

   2. Monitor the sync:
      - Watch for "rows synced" count
      - Should sync all 3,398 rows
      - Check for any errors

   3. Verify in Databricks:
      SELECT COUNT(*) FROM {table_name};
      -- Should return 3,398
    """)

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
