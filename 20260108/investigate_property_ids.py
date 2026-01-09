#!/usr/bin/env python3
"""
Investigate why property IDs don't match between staging and production
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
    print("INVESTIGATING PROPERTY ID MISMATCH")
    print("=" * 80)
    print()

    # Sample property IDs from staging
    print("=" * 80)
    print("SAMPLE PROPERTY IDs FROM STAGING (crm.sfdc.product_property__c)")
    print("=" * 80)

    query = """
    SELECT
        Snappt_Property_ID__c,
        Name,
        ID_Verification_Enabled__c,
        Bank_Linking_Enabled__c
    FROM crm.sfdc.product_property__c
    WHERE Snappt_Property_ID__c IS NOT NULL
    LIMIT 10
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)
    print(df.to_string(index=False))
    print()

    # Sample property IDs from production
    print("=" * 80)
    print("SAMPLE PROPERTY IDs FROM PRODUCTION (crm.salesforce.property)")
    print("=" * 80)

    query = """
    SELECT
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

    # Check ID formats
    print("=" * 80)
    print("PROPERTY ID FORMATS")
    print("=" * 80)

    query = """
    SELECT
        'Staging' as source,
        COUNT(*) as total_records,
        COUNT(DISTINCT Snappt_Property_ID__c) as distinct_ids,
        MIN(LENGTH(Snappt_Property_ID__c)) as min_id_length,
        MAX(LENGTH(Snappt_Property_ID__c)) as max_id_length
    FROM crm.sfdc.product_property__c
    WHERE Snappt_Property_ID__c IS NOT NULL

    UNION ALL

    SELECT
        'Production' as source,
        COUNT(*) as total_records,
        COUNT(DISTINCT snappt_property_id_c) as distinct_ids,
        MIN(LENGTH(snappt_property_id_c)) as min_id_length,
        MAX(LENGTH(snappt_property_id_c)) as max_id_length
    FROM crm.salesforce.property
    WHERE snappt_property_id_c IS NOT NULL
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)
    print(df.to_string(index=False))
    print()

    # Check for NULL property IDs
    print("=" * 80)
    print("NULL PROPERTY ID ANALYSIS")
    print("=" * 80)

    query = """
    SELECT
        'Staging' as source,
        COUNT(*) as total_records,
        SUM(CASE WHEN Snappt_Property_ID__c IS NULL THEN 1 ELSE 0 END) as null_ids,
        SUM(CASE WHEN Snappt_Property_ID__c IS NOT NULL THEN 1 ELSE 0 END) as non_null_ids
    FROM crm.sfdc.product_property__c

    UNION ALL

    SELECT
        'Production' as source,
        COUNT(*) as total_records,
        SUM(CASE WHEN snappt_property_id_c IS NULL THEN 1 ELSE 0 END) as null_ids,
        SUM(CASE WHEN snappt_property_id_c IS NOT NULL THEN 1 ELSE 0 END) as non_null_ids
    FROM crm.salesforce.property
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)
    print(df.to_string(index=False))
    print()

    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

finally:
    cursor.close()
    connection.close()
