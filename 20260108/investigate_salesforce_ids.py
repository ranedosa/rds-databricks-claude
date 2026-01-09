#!/usr/bin/env python3
"""
Investigate property IDs in both product_property and property tables
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
    print("INVESTIGATING SALESFORCE PROPERTY ID FORMATS")
    print("=" * 80)
    print()

    # Sample from product_property
    print("=" * 80)
    print("SAMPLE FROM product_property")
    print("=" * 80)

    query = """
    SELECT
        id as salesforce_id,
        snappt_property_id_c,
        sf_property_id_c,
        short_id_c,
        id_verification_enabled_c,
        bank_linking_enabled_c
    FROM crm.salesforce.product_property
    WHERE snappt_property_id_c IS NOT NULL
    LIMIT 10
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)
    print(df.to_string(index=False))
    print()

    # Sample from property
    print("=" * 80)
    print("SAMPLE FROM property")
    print("=" * 80)

    query = """
    SELECT
        id as salesforce_id,
        snappt_property_id_c,
        name,
        id_verification_enabled_c,
        bank_linking_enabled_c
    FROM crm.salesforce.property
    WHERE snappt_property_id_c IS NOT NULL
    LIMIT 10
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)
    print(df.to_string(index=False))
    print()

    # Check if sf_property_id_c in product_property matches id in property
    print("=" * 80)
    print("CHECKING JOIN ON sf_property_id_c = property.id")
    print("=" * 80)

    query = """
    SELECT
        COUNT(*) as matching_records
    FROM crm.salesforce.product_property pp
    INNER JOIN crm.salesforce.property p ON pp.sf_property_id_c = p.id
    WHERE pp.sf_property_id_c IS NOT NULL
    """

    cursor.execute(query)
    results = cursor.fetchall()
    print(f"Matching records using sf_property_id_c: {results[0][0]}")
    print()

    # Check property ID formats
    print("=" * 80)
    print("PROPERTY ID NULL ANALYSIS")
    print("=" * 80)

    query = """
    SELECT
        'product_property' as table_name,
        COUNT(*) as total_records,
        SUM(CASE WHEN snappt_property_id_c IS NULL THEN 1 ELSE 0 END) as null_snappt_ids,
        SUM(CASE WHEN sf_property_id_c IS NULL THEN 1 ELSE 0 END) as null_sf_property_ids,
        SUM(CASE WHEN short_id_c IS NULL THEN 1 ELSE 0 END) as null_short_ids
    FROM crm.salesforce.product_property

    UNION ALL

    SELECT
        'property' as table_name,
        COUNT(*) as total_records,
        SUM(CASE WHEN snappt_property_id_c IS NULL THEN 1 ELSE 0 END) as null_snappt_ids,
        NULL as null_sf_property_ids,
        NULL as null_short_ids
    FROM crm.salesforce.property
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)
    print(df.to_string(index=False))
    print()

finally:
    cursor.close()
    connection.close()
