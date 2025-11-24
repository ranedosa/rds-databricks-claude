#!/usr/bin/env python3
"""Check the actual value of ctid_fivetran_id in detail."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

table_name = "rds.pg_rds_enterprise_public.enterprise_property"

print("=" * 80)
print("DETAILED PK VALUE INSPECTION")
print("=" * 80)

try:
    warehouses = list(w.warehouses.list())
    warehouse = warehouses[0]

    # Get the actual PK value with all details
    query = f"""
    SELECT
        ctid_fivetran_id,
        LENGTH(ctid_fivetran_id) as pk_length,
        CASE
            WHEN ctid_fivetran_id IS NULL THEN 'NULL'
            WHEN ctid_fivetran_id = '' THEN 'EMPTY STRING'
            ELSE 'HAS VALUE'
        END as pk_status,
        id,
        snappt_property_id,
        created_at,
        _fivetran_synced,
        _fivetran_deleted
    FROM {table_name}
    LIMIT 5
    """

    print("\nInspecting the 1 visible row in detail...")
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        columns = [col.name for col in result.manifest.schema.columns] if result.manifest and result.manifest.schema else []

        print(f"\nRow details:")
        print("=" * 80)
        for row in result.result.data_array:
            for col, val in zip(columns, row):
                print(f"  {col}: {val}")
            print("-" * 80)

    # Check the table schema for ctid_fivetran_id
    print("\n" + "=" * 80)
    print("TABLE SCHEMA FOR ctid_fivetran_id")
    print("=" * 80)

    query = f"DESCRIBE {table_name}"
    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        print("\nLooking for ctid_fivetran_id column definition...")
        for row in result.result.data_array:
            col_name = row[0]
            if 'ctid' in str(col_name).lower():
                print(f"  Column: {row[0]}")
                print(f"  Type: {row[1]}")
                print(f"  Comment: {row[2] if len(row) > 2 else 'N/A'}")

    # Check ctid column (not ctid_fivetran_id)
    print("\n" + "=" * 80)
    print("CHECKING 'ctid' COLUMN (PostgreSQL system column)")
    print("=" * 80)

    query = f"""
    SELECT
        ctid,
        ctid_fivetran_id,
        id
    FROM {table_name}
    LIMIT 5
    """

    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        print("\nComparing ctid vs ctid_fivetran_id:")
        print(f"{'ctid':<30} {'ctid_fivetran_id':<50} {'id':<40}")
        print("-" * 120)
        for row in result.result.data_array:
            print(f"{str(row[0]):<30} {str(row[1]):<50} {str(row[2]):<40}")

    # Check if maybe the PK is actually 'id' field
    print("\n" + "=" * 80)
    print("CHECKING IF 'id' COULD BE THE REAL PK")
    print("=" * 80)

    query = f"""
    SELECT
        COUNT(*) as total_rows,
        COUNT(DISTINCT id) as unique_ids,
        COUNT(*) - COUNT(DISTINCT id) as duplicate_ids
    FROM {table_name}
    """

    result = w.statement_execution.execute_statement(
        warehouse_id=warehouse.id,
        statement=query,
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        row = result.result.data_array[0]
        print(f"\n'id' column analysis:")
        print(f"  Total Rows: {row[0]}")
        print(f"  Unique 'id' values: {row[1]}")
        print(f"  Duplicate 'id' values: {row[2]}")

    print("\n" + "=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)

    print("""
🔍 KEY OBSERVATION:

The ctid_fivetran_id column appears to be EMPTY or NULL in the visible row.

This could mean:

1. FIVETRAN IS NOT SETTING THE PRIMARY KEY CORRECTLY
   → The ctid_fivetran_id is a composite key that Fivetran generates
   → Format is typically: (page_number,tuple_number)_fivetran_id
   → Example: "(0,1)_some_uuid"

2. THE MERGE IS FAILING BECAUSE OF EMPTY PKs
   → Fivetran tries to MERGE on ctid_fivetran_id
   → If PKs are empty/NULL, the MERGE can't match rows
   → Result: Inserts fail, only 1 row remains

3. THIS EXPLAINS THE SYNC FAILURE!
   → Fivetran processes 500+ rows per sync
   → But can't insert them because PK matching fails
   → Only 1 row has a valid (or matching) PK

NEXT STEPS:

1. Run the PostgreSQL queries I provided above
2. Check if ctid_fivetran_id in PostgreSQL has actual values
3. Check Fivetran configuration for PK column mapping
4. Consider if the PK should be 'id' instead of 'ctid_fivetran_id'
    """)

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
