#!/usr/bin/env python3
"""
Check if pilot views exist and compare with production views
"""
import os
from databricks import sql
import pandas as pd

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
    print("CHECKING FOR PILOT VIEWS IN DATABRICKS")
    print("=" * 80)
    print()

    # Check what views exist
    print("All views in crm.sfdc_dbx:")
    print("-" * 80)

    query = "SHOW TABLES IN crm.sfdc_dbx"
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)

    # Filter to just views
    views = df[df['isTemporary'] == False]['tableName'].tolist()
    for view in sorted(views):
        print(f"  - {view}")
    print()

    # Check if pilot views exist
    has_pilot_create = 'pilot_create' in views
    has_pilot_update = 'pilot_update' in views
    has_prod_create = 'properties_to_create' in views
    has_prod_update = 'properties_to_update' in views

    print("=" * 80)
    print("VIEW EXISTENCE CHECK")
    print("=" * 80)
    print(f"pilot_create exists: {'✅ YES' if has_pilot_create else '❌ NO'}")
    print(f"pilot_update exists: {'✅ YES' if has_pilot_update else '❌ NO'}")
    print(f"properties_to_create exists: {'✅ YES' if has_prod_create else '❌ NO'}")
    print(f"properties_to_update exists: {'✅ YES' if has_prod_update else '❌ NO'}")
    print()

    # If pilot views exist, compare counts
    if has_pilot_create and has_prod_create:
        print("=" * 80)
        print("COMPARING VIEW COUNTS")
        print("=" * 80)

        query = "SELECT COUNT(*) FROM crm.sfdc_dbx.pilot_create"
        cursor.execute(query)
        pilot_create_count = cursor.fetchall()[0][0]

        query = "SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create"
        cursor.execute(query)
        prod_create_count = cursor.fetchall()[0][0]

        print(f"pilot_create: {pilot_create_count} records")
        print(f"properties_to_create: {prod_create_count} records")
        print()

        if pilot_create_count == prod_create_count:
            print("✅ Same count - might be same data")
        else:
            print(f"⚠️ Different counts - pilot has {pilot_create_count - prod_create_count} more/less records")
        print()

    if has_pilot_update and has_prod_update:
        query = "SELECT COUNT(*) FROM crm.sfdc_dbx.pilot_update"
        cursor.execute(query)
        pilot_update_count = cursor.fetchall()[0][0]

        query = "SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update"
        cursor.execute(query)
        prod_update_count = cursor.fetchall()[0][0]

        print(f"pilot_update: {pilot_update_count} records")
        print(f"properties_to_update: {prod_update_count} records")
        print()

        if pilot_update_count == prod_update_count:
            print("✅ Same count - might be same data")
        else:
            print(f"⚠️ Different counts - pilot has {pilot_update_count - prod_update_count} more/less records")
        print()

    # Recommendation
    print("=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print()

    if not has_pilot_create or not has_pilot_update:
        print("🚨 PROBLEM: Census is configured to use pilot views that don't exist!")
        print()
        print("Action Required:")
        print("1. Go to Census UI")
        print("2. Edit Sync A - change source from 'pilot_create' to 'properties_to_create'")
        print("3. Edit Sync B - change source from 'pilot_update' to 'properties_to_update'")
        print("4. Re-run dry run to verify")
    elif has_pilot_create and has_prod_create:
        if pilot_create_count < prod_create_count:
            print("⚠️ PILOT VIEWS HAVE LESS DATA")
            print()
            print(f"You're syncing {pilot_create_count} CREATE records")
            print(f"But production view has {prod_create_count} records")
            print()
            print("Action Required:")
            print("1. Update Census to use production views")
            print("2. This will increase sync volume from pilot to full production")
        elif pilot_create_count == prod_create_count:
            print("✅ PILOT VIEWS MATCH PRODUCTION")
            print()
            print("The pilot views have the same counts as production views.")
            print("However, for clarity and maintainability:")
            print("1. Update Census to use production view names")
            print("2. This ensures everyone knows you're running full production syncs")

finally:
    cursor.close()
    connection.close()
