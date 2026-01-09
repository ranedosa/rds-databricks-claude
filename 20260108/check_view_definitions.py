#!/usr/bin/env python3
"""
Check if Census views have LIMIT clauses from pilot testing
"""
import os
from databricks import sql

# Connect to Databricks
host = os.getenv("DATABRICKS_HOST", "").replace("https://", "").replace("http://", "")

connection = sql.connect(
    server_hostname=host,
    http_path="/sql/1.0/warehouses/25145408b75455a6",
    access_token=os.getenv("DATABRICKS_TOKEN")
)

cursor = connection.cursor()

try:
    print("=" * 80)
    print("CHECKING VIEW DEFINITIONS FOR LIMIT CLAUSES")
    print("=" * 80)
    print()

    # Check properties_to_create
    print("=" * 80)
    print("View: properties_to_create")
    print("=" * 80)

    query = "SHOW CREATE TABLE crm.sfdc_dbx.properties_to_create"

    cursor.execute(query)
    result = cursor.fetchall()
    view_def = result[0][0]

    has_limit_create = "LIMIT" in view_def.upper()

    print(f"Has LIMIT clause: {'⚠️ YES' if has_limit_create else '✅ NO'}")

    if has_limit_create:
        print("\n⚠️ WARNING: View has LIMIT clause")
        print("You need to recreate this view without LIMIT for full rollout")
        # Extract the LIMIT line
        for line in view_def.split('\n'):
            if 'LIMIT' in line.upper():
                print(f"Found: {line.strip()}")
    else:
        print("\n✅ GOOD: View is ready for full rollout")

    print()

    # Check properties_to_update
    print("=" * 80)
    print("View: properties_to_update")
    print("=" * 80)

    query = "SHOW CREATE TABLE crm.sfdc_dbx.properties_to_update"

    cursor.execute(query)
    result = cursor.fetchall()
    view_def = result[0][0]

    has_limit_update = "LIMIT" in view_def.upper()

    print(f"Has LIMIT clause: {'⚠️ YES' if has_limit_update else '✅ NO'}")

    if has_limit_update:
        print("\n⚠️ WARNING: View has LIMIT clause")
        print("You need to recreate this view without LIMIT for full rollout")
        # Extract the LIMIT line
        for line in view_def.split('\n'):
            if 'LIMIT' in line.upper():
                print(f"Found: {line.strip()}")
    else:
        print("\n✅ GOOD: View is ready for full rollout")

    print()

    # Get current counts
    print("=" * 80)
    print("CURRENT VIEW COUNTS")
    print("=" * 80)

    query = "SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create"
    cursor.execute(query)
    create_count = cursor.fetchall()[0][0]

    query = "SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update"
    cursor.execute(query)
    update_count = cursor.fetchall()[0][0]

    print(f"properties_to_create: {create_count} records")
    print(f"properties_to_update: {update_count} records")
    print()
    print(f"Expected for full rollout:")
    print(f"  - CREATE: ~735 records")
    print(f"  - UPDATE: ~7,881 records")
    print()

    if 700 < create_count < 800 and 7000 < update_count < 9000:
        print("✅ COUNTS LOOK GOOD: Views appear to be at full rollout size")
    else:
        print("⚠️ WARNING: Counts don't match expected full rollout numbers")

    print()

    # Summary
    print("=" * 80)
    print("SUMMARY & RECOMMENDATION")
    print("=" * 80)
    print()

    if not has_limit_create and not has_limit_update and 700 < create_count < 800 and 7000 < update_count < 9000:
        print("✅ READY FOR DAY 3 ROLLOUT")
        print()
        print("Both views:")
        print("  - Have NO LIMIT clauses")
        print("  - Show full rollout counts")
        print()
        print("Next steps:")
        print("  1. Check Census UI for any filters (not view filters)")
        print("  2. Remove Census UI filters if present")
        print("  3. Proceed with Day 3 rollout")
    elif has_limit_create or has_limit_update:
        print("⚠️ ACTION REQUIRED: Recreate views without LIMIT")
        print()
        print("Views have LIMIT clauses from pilot testing")
        print("You need to:")
        print("  1. Find the original view creation SQL")
        print("  2. Remove LIMIT clauses")
        print("  3. Run CREATE OR REPLACE VIEW statements")
    else:
        print("⚠️ COUNTS DON'T MATCH EXPECTED")
        print()
        print("Investigate why counts differ from expected Day 3 numbers")

finally:
    cursor.close()
    connection.close()
