#!/usr/bin/env python3
"""
Check the Census sync views status - are they ready for Day 3 rollout?
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
    print("CENSUS SYNC VIEWS STATUS CHECK")
    print("=" * 80)
    print()

    # Check if views exist
    print("=" * 80)
    print("Checking if Census sync views exist...")
    print("=" * 80)

    query = """
    SHOW TABLES IN crm.sfdc_dbx LIKE 'properties_to_*'
    """

    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()
        df = pd.DataFrame(results, columns=columns)
        print(df.to_string(index=False))
        print()
    except Exception as e:
        print(f"Error checking views: {e}")
        print("Views may not exist yet")
        print()

    # Check properties_to_create count
    print("=" * 80)
    print("Properties to CREATE count")
    print("=" * 80)

    query = """
    SELECT COUNT(*) as count
    FROM crm.sfdc_dbx.properties_to_create
    """

    try:
        cursor.execute(query)
        result = cursor.fetchall()[0][0]
        print(f"Properties to create: {result}")
        print(f"Expected from Day 3 plan: ~735")
        print(f"Match: {'✅ YES' if 700 < result < 800 else '⚠️ NO - Unexpected count'}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print("View may not exist or may have different name")
        print()

    # Check properties_to_update count
    print("=" * 80)
    print("Properties to UPDATE count")
    print("=" * 80)

    query = """
    SELECT COUNT(*) as count
    FROM crm.sfdc_dbx.properties_to_update
    """

    try:
        cursor.execute(query)
        result = cursor.fetchall()[0][0]
        print(f"Properties to update: {result}")
        print(f"Expected from Day 3 plan: ~7,881")
        print(f"Match: {'✅ YES' if 7000 < result < 9000 else '⚠️ NO - Unexpected count'}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print("View may not exist or may have different name")
        print()

    # Sample from properties_to_create
    print("=" * 80)
    print("Sample from properties_to_create")
    print("=" * 80)

    query = """
    SELECT *
    FROM crm.sfdc_dbx.properties_to_create
    LIMIT 5
    """

    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()
        df = pd.DataFrame(results, columns=columns)
        print(df.to_string(index=False))
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()

finally:
    cursor.close()
    connection.close()
