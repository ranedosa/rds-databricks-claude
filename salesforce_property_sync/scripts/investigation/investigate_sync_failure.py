#!/usr/bin/env python3
"""Investigate why Fivetran isn't syncing 3,398 rows from PostgreSQL."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
import json

config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

table_name = "rds.pg_rds_enterprise_public.enterprise_property"

print("=" * 80)
print("FIVETRAN SYNC FAILURE INVESTIGATION")
print("=" * 80)
print("\n⚠️  CRITICAL ISSUE IDENTIFIED:")
print("   PostgreSQL: 3,398 rows")
print("   Databricks: 1 row")
print("   Missing: 3,397 rows")
print()

# Load the history data
with open('enterprise_property_history_20days.json', 'r') as f:
    operations = json.load(f)

try:
    warehouses = list(w.warehouses.list())
    warehouse = warehouses[0]

    # Check 1: When was the last successful MERGE with significant data?
    print("=" * 80)
    print("1. ANALYZING RECENT MERGE OPERATIONS")
    print("=" * 80)

    merge_ops = [op for op in operations if op.get('operation') == 'MERGE']
    merge_ops.sort(key=lambda x: x['timestamp'], reverse=True)

    print(f"\nLast 20 MERGE operations:")
    print(f"{'Version':<10} {'Timestamp':<25} {'Source Rows':<15} {'Inserted':<12} {'Updated':<12}")
    print("-" * 85)

    for op in merge_ops[:20]:
        version = op.get('version')
        timestamp = op.get('timestamp', '')[:19]
        metrics = op.get('operationMetrics', {})
        source_rows = metrics.get('numSourceRows', 0)
        inserted = metrics.get('numTargetRowsInserted', 0)
        updated = metrics.get('numTargetRowsUpdated', 0)
        print(f"{version:<10} {timestamp:<25} {source_rows:<15} {inserted:<12} {updated:<12}")

    # Check 2: Look for operations that removed massive amounts of data
    print("\n" + "=" * 80)
    print("2. LOOKING FOR DATA REMOVAL EVENTS")
    print("=" * 80)

    large_removals = []
    for op in operations:
        metrics = op.get('operationMetrics', {})
        bytes_removed = int(metrics.get('numTargetBytesRemoved', 0) or 0)
        rows_deleted = int(metrics.get('numTargetRowsDeleted', 0) or 0)
        rows_copied = int(metrics.get('numTargetRowsCopied', 0) or 0)

        if bytes_removed > 10000000 or rows_deleted > 100 or rows_copied > 100000:
            large_removals.append({
                'version': op.get('version'),
                'timestamp': op.get('timestamp'),
                'operation': op.get('operation'),
                'bytes_removed': bytes_removed,
                'rows_deleted': rows_deleted,
                'rows_copied': rows_copied,
                'metrics': metrics
            })

    if large_removals:
        large_removals.sort(key=lambda x: x['bytes_removed'], reverse=True)
        print(f"\nFound {len(large_removals)} operations with significant data changes:")
        print(f"\n{'Version':<10} {'Timestamp':<25} {'Operation':<12} {'Bytes Removed (MB)':<20} {'Rows Deleted':<15}")
        print("-" * 95)
        for op in large_removals[:10]:
            mb_removed = op['bytes_removed'] / 1024 / 1024
            print(f"{op['version']:<10} {op['timestamp'][:19]:<25} {op['operation']:<12} {mb_removed:<20.2f} {op['rows_deleted']:<15}")

    # Check 3: Look at UPDATE operations (not MERGE)
    print("\n" + "=" * 80)
    print("3. CHECKING UPDATE OPERATIONS")
    print("=" * 80)

    update_ops = [op for op in operations if op.get('operation') == 'UPDATE']

    if update_ops:
        print(f"\nFound {len(update_ops)} UPDATE operations:")
        for op in update_ops:
            print(f"\nVersion {op['version']} - {op['timestamp']}")
            metrics = op.get('operationMetrics', {})
            params = op.get('operationParameters', {})

            print(f"  Rows Updated: {metrics.get('numUpdatedRows', 0)}")
            print(f"  Rows Copied: {metrics.get('numCopiedRows', 0)}")

            if params.get('predicate'):
                print(f"  Predicate: {params['predicate']}")

    # Check 4: Query current table state details
    print("\n" + "=" * 80)
    print("4. CURRENT TABLE STATE")
    print("=" * 80)

    query = f"""
    SELECT
        MIN(_fivetran_synced) as first_sync,
        MAX(_fivetran_synced) as last_sync,
        COUNT(DISTINCT id) as unique_ids,
        COUNT(*) as total_rows
    FROM {table_name}
    """

    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        row = result.result.data_array[0]
        print(f"\nCurrent visible data:")
        print(f"  First Sync: {row[0]}")
        print(f"  Last Sync: {row[1]}")
        print(f"  Unique IDs: {row[2]}")
        print(f"  Total Rows: {row[3]}")

    # Check 5: Get details of the 1 visible row
    query = f"""
    SELECT *
    FROM {table_name}
    LIMIT 1
    """

    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        columns = [col.name for col in result.manifest.schema.columns] if result.manifest and result.manifest.schema else []
        row = result.result.data_array[0]

        print(f"\nThe 1 visible row:")
        for col, val in zip(columns, row):
            if col in ['id', 'snappt_property_id', 'enterprise_integration_id', '_fivetran_synced', '_fivetran_deleted', 'created_at', 'updated_at']:
                print(f"  {col}: {val}")

    print("\n" + "=" * 80)
    print("5. ROOT CAUSE ANALYSIS")
    print("=" * 80)

    # Look for the specific operation that might have caused the issue
    # Check operations on Oct 27 (when the 1 row was synced)
    oct27_ops = [op for op in operations if '2025-10-27T19:' in op.get('timestamp', '')]

    print(f"\nOperations around Oct 27, 19:32 (when the 1 visible row was synced):")
    for op in oct27_ops:
        print(f"\n  Version {op['version']} - {op['timestamp']}")
        print(f"  Operation: {op['operation']}")
        metrics = op.get('operationMetrics', {})
        if metrics:
            print(f"  Source Rows: {metrics.get('numSourceRows', 0)}")
            print(f"  Target Rows Inserted: {metrics.get('numTargetRowsInserted', 0)}")
            print(f"  Target Rows Updated: {metrics.get('numTargetRowsUpdated', 0)}")

    print("\n" + "=" * 80)
    print("CRITICAL FINDINGS & NEXT STEPS")
    print("=" * 80)
    print("""
🔴 SYNC FAILURE CONFIRMED:
   - PostgreSQL has 3,398 active rows
   - Databricks only shows 1 row (last synced Oct 27)
   - 3,397 rows are missing!

🔍 LIKELY CAUSES:

1. FIVETRAN CONNECTOR ISSUE:
   - The connector might have failed or been paused
   - Check Fivetran dashboard for sync errors
   - Look for "sync incomplete" or "rows rejected" messages

2. ROW FILTER BLOCKING INSERTS:
   - The row filter might be rejecting rows during MERGE
   - Fivetran might be trying to insert rows with _fivetran_deleted=true

3. PRIMARY KEY CONSTRAINT ISSUE:
   - Duplicate key conflicts could be causing inserts to fail
   - Check Fivetran logs for constraint violations

4. SCHEMA MISMATCH:
   - Column mismatches between PostgreSQL and Databricks
   - Check for data type incompatibilities

5. VACUUM OPERATION REMOVED DATA:
   - VACUUM permanently deleted the rows before they could be restored
   - Historical data (versions before Oct 25) might show more rows

IMMEDIATE ACTIONS:

✅ 1. CHECK FIVETRAN DASHBOARD:
      - Go to Fivetran console
      - Find the RDS → Databricks connector
      - Check sync status and error logs
      - Look for "rows synced" vs "rows in source"

✅ 2. CHECK FIVETRAN LOGS:
      Look for errors related to:
      - "enterprise_property" table
      - Primary key violations
      - Row filter errors
      - Schema mismatches

✅ 3. VERIFY PRIMARY KEY IN BOTH SYSTEMS:
      PostgreSQL:
        SELECT COUNT(DISTINCT ctid_fivetran_id) FROM enterprise_property;

      Should return 3,398 if PKs are unique

✅ 4. CHECK IF FIVETRAN IS RUNNING:
      - Is the connector enabled?
      - When was the last successful sync?
      - Are there any paused or error states?

✅ 5. REVIEW TABLE HISTORY BEFORE VACUUM:
      SELECT * FROM {table_name} VERSION AS OF 22714

      This shows data before the first VACUUM on Oct 11
    """)

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

print("=" * 80)
