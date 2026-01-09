#!/usr/bin/env python3
"""
Explore RDS property_features table structure
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
    print("EXPLORING RDS PROPERTY_FEATURES TABLE")
    print("=" * 80)
    print()

    # Sample data
    print("=" * 80)
    print("SAMPLE DATA FROM rds.pg_rds_public.property_features")
    print("=" * 80)

    query = """
    SELECT *
    FROM rds.pg_rds_public.property_features
    LIMIT 20
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)
    print(df.to_string(index=False))
    print()

    # Feature codes
    print("=" * 80)
    print("DISTINCT FEATURE CODES")
    print("=" * 80)

    query = """
    SELECT
        feature_code,
        COUNT(*) as count,
        COUNT(DISTINCT property_id) as distinct_properties
    FROM rds.pg_rds_public.property_features
    GROUP BY feature_code
    ORDER BY feature_code
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)
    print(df.to_string(index=False))
    print()

    # State values
    print("=" * 80)
    print("DISTINCT STATE VALUES")
    print("=" * 80)

    query = """
    SELECT
        state,
        COUNT(*) as count
    FROM rds.pg_rds_public.property_features
    GROUP BY state
    ORDER BY state
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)
    print(df.to_string(index=False))
    print()

    # Total properties
    print("=" * 80)
    print("TOTAL PROPERTIES WITH FEATURES")
    print("=" * 80)

    query = """
    SELECT
        COUNT(DISTINCT property_id) as total_properties
    FROM rds.pg_rds_public.property_features
    """

    cursor.execute(query)
    result = cursor.fetchall()[0][0]
    print(f"Total properties: {result}")
    print()

finally:
    cursor.close()
    connection.close()
