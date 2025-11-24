#!/usr/bin/env python3
"""Check if the 3,397 missing rows exist but are marked as deleted."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

table_name = "rds.pg_rds_enterprise_public.enterprise_property"

print("=" * 80)
print("CHECKING FOR HIDDEN ROWS WITH _fivetran_deleted = true")
print("=" * 80)

try:
    warehouses = list(w.warehouses.list())
    warehouse = warehouses[0]

    # Try to count all rows bypassing the filter using VERSION AS OF
    print("\nAttempting to read the CURRENT version of the table...")
    print("(This should show all rows including those marked as deleted)")

    # Get the latest version number
    query = f"DESCRIBE HISTORY {table_name} LIMIT 1"
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    latest_version = None
    if result.result and result.result.data_array:
        latest_version = result.result.data_array[0][0]
        print(f"\nLatest version: {latest_version}")

    if latest_version:
        # Query at that specific version to bypass some filters
        query = f"""
        SELECT
            _fivetran_deleted,
            COUNT(*) as count
        FROM {table_name} VERSION AS OF {latest_version}
        GROUP BY _fivetran_deleted
        """

        print(f"\nQuerying version {latest_version}...")
        result = w.statement_execution.execute_statement(
            warehouse_id=warehouse.id,
            statement=query,
            wait_timeout="50s"
        )

        if result.result and result.result.data_array:
            print("\nRow counts by _fivetran_deleted status:")
            print(f"{'Deleted':<15} {'Count':<10}")
            print("-" * 25)
            total = 0
            for row in result.result.data_array:
                deleted = row[0]
                count = row[1]
                total += int(count) if count else 0
                print(f"{str(deleted):<15} {count:<10}")
            print("-" * 25)
            print(f"{'TOTAL':<15} {total:<10}")

            print(f"\n🔍 PostgreSQL has: 3,398 rows")
            print(f"   Databricks has: {total} rows")
            print(f"   Difference: {3398 - total} rows")

    # Also try to query a version right after 24175 (the big UPDATE)
    print(f"\n{'=' * 80}")
    print("CHECKING VERSION RIGHT AFTER THE BIG UPDATE (24175)")
    print(f"{'=' * 80}")

    query = f"""
    SELECT
        _fivetran_deleted,
        COUNT(*) as count
    FROM {table_name} VERSION AS OF 24176
    GROUP BY _fivetran_deleted
    """

    print("\nQuerying version 24176 (right after the big update)...")
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        print("\nRow counts at version 24176:")
        print(f"{'Deleted':<15} {'Count':<10}")
        print("-" * 25)
        for row in result.result.data_array:
            deleted = row[0]
            count = row[1]
            print(f"{str(deleted):<15} {count:<10}")

    # Check version 24174 (before the UPDATE)
    print(f"\n{'=' * 80}")
    print("CHECKING VERSION BEFORE THE BIG UPDATE (24174)")
    print(f"{'=' * 80}")

    query = f"""
    SELECT
        _fivetran_deleted,
        COUNT(*) as count
    FROM {table_name} VERSION AS OF 24174
    GROUP BY _fivetran_deleted
    """

    print("\nQuerying version 24174 (before the big update)...")
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        print("\nRow counts at version 24174:")
        print(f"{'Deleted':<15} {'Count':<10}")
        print("-" * 25)
        for row in result.result.data_array:
            deleted = row[0]
            count = row[1]
            print(f"{str(deleted):<15} {count:<10}")

    print("\n" + "=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)
    print("""
Based on the results above, we can determine:

SCENARIO A: If current version shows ~823 rows (not 3,398):
   → The 3,397 rows DON'T exist in Databricks at all
   → Fivetran is NOT syncing them
   → Check Fivetran connector configuration and logs

SCENARIO B: If current version shows ~3,398 rows:
   → The rows DO exist in Databricks
   → But ~3,397 are marked with _fivetran_deleted = true
   → The row filter is hiding them
   → Check PostgreSQL: Are these rows actually deleted in the source?

The truth will be revealed in the counts above.
    """)

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

print("=" * 80)
