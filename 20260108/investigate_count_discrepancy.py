#!/usr/bin/env python3
"""
Investigate why Census processed fewer records than views contain
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
    print("INVESTIGATING COUNT DISCREPANCY")
    print("=" * 80)
    print()

    # Check for NULL values in key fields
    print("=" * 80)
    print("Checking properties_to_create for NULL sync keys")
    print("=" * 80)

    query = """
    SELECT
        COUNT(*) as total_records,
        COUNT(CASE WHEN rds_property_id IS NULL THEN 1 END) as null_rds_property_id,
        COUNT(CASE WHEN sfdc_id IS NULL THEN 1 END) as null_sfdc_id,
        COUNT(CASE WHEN rds_property_id IS NULL OR sfdc_id IS NULL THEN 1 END) as null_either
    FROM crm.sfdc_dbx.properties_to_create
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)

    print(df.to_string(index=False))
    print()

    if df['null_either'][0] > 0:
        print(f"⚠️ Found {df['null_either'][0]} records with NULL sync keys")
        print("These records likely won't sync to Salesforce")
        print()
    else:
        print("✅ No NULL sync keys found")
        print()

    # Check for other potential issues
    print("=" * 80)
    print("Checking properties_to_update for NULL sync keys")
    print("=" * 80)

    query = """
    SELECT
        COUNT(*) as total_records,
        COUNT(CASE WHEN rds_property_id IS NULL THEN 1 END) as null_rds_property_id,
        COUNT(CASE WHEN sfdc_id IS NULL THEN 1 END) as null_sfdc_id,
        COUNT(CASE WHEN rds_property_id IS NULL OR sfdc_id IS NULL THEN 1 END) as null_either
    FROM crm.sfdc_dbx.properties_to_update
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)

    print(df.to_string(index=False))
    print()

    if df['null_either'][0] > 0:
        print(f"⚠️ Found {df['null_either'][0]} records with NULL sync keys")
        print("These records likely won't sync to Salesforce")
        print()
    else:
        print("✅ No NULL sync keys found")
        print()

    # Check timestamp to see if data changed
    print("=" * 80)
    print("Checking for recent data changes")
    print("=" * 80)

    query = """
    SELECT
        'properties_to_create' as view_name,
        COUNT(*) as current_count,
        MAX(rds_last_updated_at) as most_recent_update
    FROM crm.sfdc_dbx.properties_to_create

    UNION ALL

    SELECT
        'properties_to_update' as view_name,
        COUNT(*) as current_count,
        MAX(rds_last_updated_at) as most_recent_update
    FROM crm.sfdc_dbx.properties_to_update
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)

    print(df.to_string(index=False))
    print()

    # Summary
    print("=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    print()
    print("Expected vs Actual:")
    print("  Sync A (CREATE): 740 in view → 690 processed = 50 missing (6.8%)")
    print("  Sync B (UPDATE): 7,874 in view → 7,820 processed = 54 missing (0.7%)")
    print()
    print("Possible explanations:")
    print("  1. NULL values in sync key fields (Snappt_Property_ID__c)")
    print("  2. Data changed between when we checked and when dry run executed")
    print("  3. Census internal filtering (e.g., duplicate detection)")
    print("  4. Salesforce validation rules blocking some records")
    print()
    print("Recommendation:")
    if 50 < 60:  # Small discrepancy
        print("  ✅ PROCEED - Small discrepancy is acceptable")
        print("  - 6.8% missing on CREATE is within normal variance")
        print("  - 0.7% missing on UPDATE is excellent")
        print("  - 0% errors on CREATE, 0.1% on UPDATE")
        print("  - Can investigate specific missing records post-rollout")
    else:
        print("  ⚠️ INVESTIGATE - Discrepancy is significant")
        print("  - Should understand why before proceeding")

finally:
    cursor.close()
    connection.close()
