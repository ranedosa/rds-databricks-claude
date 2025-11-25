#!/usr/bin/env python3
"""
Validate DLT Pipeline Output vs Original Table
==============================================

This script compares the sandbox DLT pipeline output with the production
product.fde.dim_fde table to ensure they match.

Usage:
    python validate_dlt_output.py

Requirements:
    - DLT pipeline must have run successfully
    - Access to both team_sandbox and product catalogs
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.service.sql import StatementState
import time
import json

# Load credentials
config = Config(profile="DEFAULT", config_file=".databrickscfg")
w = WorkspaceClient(config=config)

# Configuration
WAREHOUSE_ID = "95a8f5979c3f8740"  # fivetran SQL warehouse (currently running)
PROD_TABLE = "product.fde.dim_fde"
SANDBOX_TABLE = "team_sandbox.data_engineering.dlt_test_dim_fde"

print("=" * 80)
print("DLT PIPELINE VALIDATION")
print("=" * 80)
print(f"\nProduction Table: {PROD_TABLE}")
print(f"Sandbox Table: {SANDBOX_TABLE}")
print(f"Warehouse: {WAREHOUSE_ID}")
print()


def execute_query(query, description):
    """Execute a SQL query and return results."""
    print(f"Running: {description}")
    print(f"Query: {query[:100]}..." if len(query) > 100 else f"Query: {query}")

    try:
        statement = w.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID,
            statement=query,
            wait_timeout="50s"
        )

        if statement.status and statement.status.state == StatementState.SUCCEEDED:
            # Extract results
            if statement.result and statement.result.data_array:
                return statement.result.data_array
            return []
        else:
            error_msg = statement.status.error.message if statement.status and statement.status.error else "Unknown error"
            print(f"  ❌ Query failed: {error_msg}")
            return None

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


print("=" * 80)
print("STEP 1: Check Table Existence")
print("=" * 80)
print()

# Check if both tables exist
for table in [PROD_TABLE, SANDBOX_TABLE]:
    query = f"DESCRIBE TABLE {table}"
    result = execute_query(query, f"Checking {table}")

    if result is not None:
        print(f"  ✓ {table} exists")
    else:
        print(f"  ❌ {table} does not exist or not accessible")
    print()


print("=" * 80)
print("STEP 2: Row Count Comparison")
print("=" * 80)
print()

# Get row counts
prod_count_query = f"SELECT COUNT(*) as count FROM {PROD_TABLE}"
sandbox_count_query = f"SELECT COUNT(*) as count FROM {SANDBOX_TABLE}"

prod_count_result = execute_query(prod_count_query, "Production row count")
sandbox_count_result = execute_query(sandbox_count_query, "Sandbox row count")

if prod_count_result and sandbox_count_result:
    prod_count = int(prod_count_result[0][0])
    sandbox_count = int(sandbox_count_result[0][0])

    print(f"\n  Production rows: {prod_count:,}")
    print(f"  Sandbox rows: {sandbox_count:,}")
    print(f"  Difference: {abs(prod_count - sandbox_count):,} rows")

    if prod_count == sandbox_count:
        print("  ✓ Row counts match!")
    else:
        diff_pct = abs(prod_count - sandbox_count) / prod_count * 100
        print(f"  ⚠️  Row counts differ by {diff_pct:.2f}%")

        if diff_pct < 1:
            print("     (Small difference - likely due to real-time updates)")
        else:
            print("     (Significant difference - investigate further)")
print()


print("=" * 80)
print("STEP 3: Schema Comparison")
print("=" * 80)
print()

# Get schema for both tables
prod_schema_query = f"DESCRIBE TABLE {PROD_TABLE}"
sandbox_schema_query = f"DESCRIBE TABLE {SANDBOX_TABLE}"

prod_schema = execute_query(prod_schema_query, "Production schema")
sandbox_schema = execute_query(sandbox_schema_query, "Sandbox schema")

if prod_schema and sandbox_schema:
    # Extract column names and types (first two columns of DESCRIBE output)
    prod_cols = {row[0]: row[1] for row in prod_schema if row[0] and not row[0].startswith('#')}
    sandbox_cols = {row[0]: row[1] for row in sandbox_schema if row[0] and not row[0].startswith('#')}

    print(f"\n  Production columns: {len(prod_cols)}")
    print(f"  Sandbox columns: {len(sandbox_cols)}")

    # Find differences
    missing_in_sandbox = set(prod_cols.keys()) - set(sandbox_cols.keys())
    missing_in_prod = set(sandbox_cols.keys()) - set(prod_cols.keys())
    type_mismatches = []

    for col in set(prod_cols.keys()) & set(sandbox_cols.keys()):
        if prod_cols[col] != sandbox_cols[col]:
            type_mismatches.append((col, prod_cols[col], sandbox_cols[col]))

    if not missing_in_sandbox and not missing_in_prod and not type_mismatches:
        print("  ✓ Schemas match perfectly!")
    else:
        if missing_in_sandbox:
            print(f"\n  ⚠️  Columns in production but missing in sandbox:")
            for col in sorted(missing_in_sandbox)[:10]:
                print(f"     - {col} ({prod_cols[col]})")

        if missing_in_prod:
            print(f"\n  ⚠️  Columns in sandbox but missing in production:")
            for col in sorted(missing_in_prod)[:10]:
                print(f"     - {col} ({sandbox_cols[col]})")

        if type_mismatches:
            print(f"\n  ⚠️  Columns with type mismatches:")
            for col, prod_type, sandbox_type in type_mismatches[:10]:
                print(f"     - {col}: {prod_type} (prod) vs {sandbox_type} (sandbox)")
print()


print("=" * 80)
print("STEP 4: Key Column Statistics")
print("=" * 80)
print()

# Compare statistics for key columns
key_columns = [
    "company_id",
    "property_id",
    "submission_id",
    "document_id",
    "folder_id"
]

print("Comparing distinct counts for key columns:\n")

for col in key_columns:
    prod_query = f"SELECT COUNT(DISTINCT {col}) as distinct_count FROM {PROD_TABLE}"
    sandbox_query = f"SELECT COUNT(DISTINCT {col}) as distinct_count FROM {SANDBOX_TABLE}"

    prod_result = execute_query(prod_query, f"{col} distinct count (prod)")
    sandbox_result = execute_query(sandbox_query, f"{col} distinct count (sandbox)")

    if prod_result and sandbox_result:
        prod_distinct = int(prod_result[0][0])
        sandbox_distinct = int(sandbox_result[0][0])

        match_symbol = "✓" if prod_distinct == sandbox_distinct else "⚠️"
        print(f"  {match_symbol} {col}:")
        print(f"     Production: {prod_distinct:,}")
        print(f"     Sandbox: {sandbox_distinct:,}")

        if prod_distinct != sandbox_distinct:
            diff_pct = abs(prod_distinct - sandbox_distinct) / prod_distinct * 100 if prod_distinct > 0 else 0
            print(f"     Difference: {diff_pct:.2f}%")
        print()


print("=" * 80)
print("STEP 5: Data Quality Checks")
print("=" * 80)
print()

# Check for NULL values in critical columns
critical_columns = [
    "company_id",
    "property_id",
    "property_name"
]

print("Checking for NULL values in critical columns:\n")

for col in critical_columns:
    prod_query = f"SELECT COUNT(*) FROM {PROD_TABLE} WHERE {col} IS NULL"
    sandbox_query = f"SELECT COUNT(*) FROM {SANDBOX_TABLE} WHERE {col} IS NULL"

    prod_result = execute_query(prod_query, f"{col} NULL count (prod)")
    sandbox_result = execute_query(sandbox_query, f"{col} NULL count (sandbox)")

    if prod_result and sandbox_result:
        prod_nulls = int(prod_result[0][0])
        sandbox_nulls = int(sandbox_result[0][0])

        match_symbol = "✓" if prod_nulls == sandbox_nulls else "⚠️"
        print(f"  {match_symbol} {col} NULLs:")
        print(f"     Production: {prod_nulls:,}")
        print(f"     Sandbox: {sandbox_nulls:,}")
        print()


print("=" * 80)
print("STEP 6: Sample Data Comparison")
print("=" * 80)
print()

# Compare a sample of records
sample_query = f"""
SELECT
    company_id,
    company_name,
    property_id,
    property_name,
    submission_id,
    submission_datetime
FROM {PROD_TABLE}
WHERE submission_id IS NOT NULL
ORDER BY submission_datetime DESC
LIMIT 5
"""

print("Sample records from production:\n")
prod_sample = execute_query(sample_query, "Production sample")

if prod_sample:
    print("\n  Company ID | Property ID | Submission ID | Submission Date")
    print("  " + "-" * 70)
    for row in prod_sample:
        company_id = str(row[0])[:8] + "..." if row[0] else "NULL"
        property_id = str(row[2])[:8] + "..." if row[2] else "NULL"
        submission_id = str(row[4])[:8] + "..." if row[4] else "NULL"
        submission_date = str(row[5])[:19] if row[5] else "NULL"
        print(f"  {company_id} | {property_id} | {submission_id} | {submission_date}")

# Check if these same records exist in sandbox
if prod_sample and len(prod_sample) > 0:
    print("\n\nChecking if sample records exist in sandbox...\n")

    # Use submission_id as unique identifier
    submission_ids = [row[4] for row in prod_sample if row[4]]

    if submission_ids:
        # Format for SQL IN clause
        ids_str = ", ".join([f"'{id}'" for id in submission_ids])

        sandbox_check_query = f"""
        SELECT COUNT(*) as found_count
        FROM {SANDBOX_TABLE}
        WHERE submission_id IN ({ids_str})
        """

        sandbox_check = execute_query(sandbox_check_query, "Sandbox record check")

        if sandbox_check:
            found_count = int(sandbox_check[0][0])
            expected_count = len(submission_ids)

            if found_count == expected_count:
                print(f"  ✓ All {expected_count} sample records found in sandbox!")
            else:
                print(f"  ⚠️  Only {found_count}/{expected_count} sample records found in sandbox")
print()


print("=" * 80)
print("STEP 7: Date Range Comparison")
print("=" * 80)
print()

# Compare date ranges for submission_datetime
date_comparison_query = """
SELECT
    MIN(submission_datetime) as earliest,
    MAX(submission_datetime) as latest,
    COUNT(DISTINCT DATE(submission_datetime)) as distinct_days
FROM {table}
WHERE submission_datetime IS NOT NULL
"""

print("Comparing date ranges:\n")

prod_dates = execute_query(
    date_comparison_query.format(table=PROD_TABLE),
    "Production date range"
)
sandbox_dates = execute_query(
    date_comparison_query.format(table=SANDBOX_TABLE),
    "Sandbox date range"
)

if prod_dates and sandbox_dates:
    print(f"  Production:")
    print(f"    Earliest: {prod_dates[0][0]}")
    print(f"    Latest: {prod_dates[0][1]}")
    print(f"    Distinct days: {int(prod_dates[0][2]):,}")

    print(f"\n  Sandbox:")
    print(f"    Earliest: {sandbox_dates[0][0]}")
    print(f"    Latest: {sandbox_dates[0][1]}")
    print(f"    Distinct days: {int(sandbox_dates[0][2]):,}")

    if prod_dates[0] == sandbox_dates[0]:
        print("\n  ✓ Date ranges match!")
    else:
        print("\n  ⚠️  Date ranges differ")
print()


print("=" * 80)
print("STEP 8: Test/Demo Data Exclusion Validation")
print("=" * 80)
print()

# Check that test/demo data is properly excluded
test_patterns = [
    "%TEST%",
    "%DEMO%",
    "%DELETE%",
    "%DUPLICATE%"
]

print("Verifying test/demo data exclusions:\n")

for pattern in test_patterns:
    prod_query = f"""
    SELECT COUNT(*)
    FROM {PROD_TABLE}
    WHERE UPPER(property_name) LIKE '{pattern}'
       OR UPPER(company_name) LIKE '{pattern}'
    """

    sandbox_query = f"""
    SELECT COUNT(*)
    FROM {SANDBOX_TABLE}
    WHERE UPPER(property_name) LIKE '{pattern}'
       OR UPPER(company_name) LIKE '{pattern}'
    """

    prod_result = execute_query(prod_query, f"Production {pattern}")
    sandbox_result = execute_query(sandbox_query, f"Sandbox {pattern}")

    if prod_result and sandbox_result:
        prod_test_count = int(prod_result[0][0])
        sandbox_test_count = int(sandbox_result[0][0])

        match_symbol = "✓" if prod_test_count == sandbox_test_count == 0 else "⚠️"
        print(f"  {match_symbol} Pattern '{pattern}':")
        print(f"     Production: {prod_test_count:,} records")
        print(f"     Sandbox: {sandbox_test_count:,} records")

        if prod_test_count == 0 and sandbox_test_count == 0:
            print(f"     ✓ Properly excluded!")
        elif prod_test_count > 0 or sandbox_test_count > 0:
            print(f"     ⚠️  Test data found - exclusions may not be working")
        print()


print("=" * 80)
print("VALIDATION SUMMARY")
print("=" * 80)
print()

print("""
To fully validate the DLT pipeline:

1. ✓ Both tables should exist and be accessible
2. ✓ Row counts should be identical (or very close if data is updating)
3. ✓ Schemas should match exactly (same columns, same types)
4. ✓ Distinct counts for key columns should match
5. ✓ NULL counts in critical columns should match
6. ✓ Sample records should exist in both tables
7. ✓ Date ranges should be identical
8. ✓ Test/demo data should be excluded from both

If all checks pass, the DLT pipeline is producing correct output!

Next steps:
  - Review any warnings or mismatches above
  - Run row-by-row comparison if needed
  - Check DLT pipeline metrics in Databricks UI
  - Monitor pipeline performance and data quality
""")

print("=" * 80)
