#!/usr/bin/env python3
"""
Run staging vs production comparison queries against Databricks
"""
import os
from databricks import sql
import pandas as pd

# Define queries directly
QUERIES = {
    "Summary Statistics": """
WITH staging_features AS (
  SELECT
    Snappt_Property_ID__c as property_id,
    ID_Verification_Enabled__c as idv_enabled,
    Bank_Linking_Enabled__c as bank_linking_enabled,
    Connected_Payroll_Enabled__c as connected_payroll_enabled,
    Income_Verification_Enabled__c as income_verification_enabled,
    Fraud_Detection_Enabled__c as fraud_detection_enabled
  FROM crm.sfdc.product_property__c
  WHERE Snappt_Property_ID__c IS NOT NULL
),

production_features AS (
  SELECT
    snappt_property_id_c as property_id,
    id_verification_enabled_c as idv_enabled,
    bank_linking_enabled_c as bank_linking_enabled,
    connected_payroll_enabled_c as connected_payroll_enabled,
    income_verification_enabled_c as income_verification_enabled,
    fraud_detection_enabled_c as fraud_detection_enabled
  FROM crm.salesforce.property
  WHERE snappt_property_id_c IS NOT NULL
)

SELECT
  'Total Properties in Staging' as metric,
  COUNT(DISTINCT s.property_id) as count
FROM staging_features s

UNION ALL

SELECT
  'Total Properties in Production' as metric,
  COUNT(DISTINCT p.property_id) as count
FROM production_features p

UNION ALL

SELECT
  'Properties in Both Environments' as metric,
  COUNT(DISTINCT s.property_id) as count
FROM staging_features s
INNER JOIN production_features p ON s.property_id = p.property_id

UNION ALL

SELECT
  'Properties Only in Staging' as metric,
  COUNT(DISTINCT s.property_id) as count
FROM staging_features s
LEFT JOIN production_features p ON s.property_id = p.property_id
WHERE p.property_id IS NULL

UNION ALL

SELECT
  'Properties Only in Production' as metric,
  COUNT(DISTINCT p.property_id) as count
FROM production_features p
LEFT JOIN staging_features s ON s.property_id = p.property_id
WHERE s.property_id IS NULL

UNION ALL

SELECT
  'IDV Flag Mismatches' as metric,
  COUNT(DISTINCT s.property_id) as count
FROM staging_features s
INNER JOIN production_features p ON s.property_id = p.property_id
WHERE s.idv_enabled != p.idv_enabled

UNION ALL

SELECT
  'Bank Linking Flag Mismatches' as metric,
  COUNT(DISTINCT s.property_id) as count
FROM staging_features s
INNER JOIN production_features p ON s.property_id = p.property_id
WHERE s.bank_linking_enabled != p.bank_linking_enabled

UNION ALL

SELECT
  'Connected Payroll Flag Mismatches' as metric,
  COUNT(DISTINCT s.property_id) as count
FROM staging_features s
INNER JOIN production_features p ON s.property_id = p.property_id
WHERE s.connected_payroll_enabled != p.connected_payroll_enabled

UNION ALL

SELECT
  'Income Verification Flag Mismatches' as metric,
  COUNT(DISTINCT s.property_id) as count
FROM staging_features s
INNER JOIN production_features p ON s.property_id = p.property_id
WHERE s.income_verification_enabled != p.income_verification_enabled

UNION ALL

SELECT
  'Fraud Detection Flag Mismatches' as metric,
  COUNT(DISTINCT s.property_id) as count
FROM staging_features s
INNER JOIN production_features p ON s.property_id = p.property_id
WHERE s.fraud_detection_enabled != p.fraud_detection_enabled
""",

    "Mismatch Details": """
WITH staging_features AS (
  SELECT
    Snappt_Property_ID__c as property_id,
    Name as property_name,
    ID_Verification_Enabled__c as idv_enabled,
    Bank_Linking_Enabled__c as bank_linking_enabled,
    Connected_Payroll_Enabled__c as connected_payroll_enabled,
    Income_Verification_Enabled__c as income_verification_enabled,
    Fraud_Detection_Enabled__c as fraud_detection_enabled
  FROM crm.sfdc.product_property__c
  WHERE Snappt_Property_ID__c IS NOT NULL
),

production_features AS (
  SELECT
    snappt_property_id_c as property_id,
    name as property_name,
    id_verification_enabled_c as idv_enabled,
    bank_linking_enabled_c as bank_linking_enabled,
    connected_payroll_enabled_c as connected_payroll_enabled,
    income_verification_enabled_c as income_verification_enabled,
    fraud_detection_enabled_c as fraud_detection_enabled
  FROM crm.salesforce.property
  WHERE snappt_property_id_c IS NOT NULL
)

SELECT
  s.property_id,
  s.property_name,
  CASE WHEN s.idv_enabled != p.idv_enabled
    THEN CONCAT('IDV: ', CAST(s.idv_enabled AS STRING), ' -> ', CAST(p.idv_enabled AS STRING))
    ELSE NULL
  END as idv_mismatch,
  CASE WHEN s.bank_linking_enabled != p.bank_linking_enabled
    THEN CONCAT('Bank: ', CAST(s.bank_linking_enabled AS STRING), ' -> ', CAST(p.bank_linking_enabled AS STRING))
    ELSE NULL
  END as bank_mismatch,
  CASE WHEN s.connected_payroll_enabled != p.connected_payroll_enabled
    THEN CONCAT('Payroll: ', CAST(s.connected_payroll_enabled AS STRING), ' -> ', CAST(p.connected_payroll_enabled AS STRING))
    ELSE NULL
  END as payroll_mismatch,
  CASE WHEN s.income_verification_enabled != p.income_verification_enabled
    THEN CONCAT('Income: ', CAST(s.income_verification_enabled AS STRING), ' -> ', CAST(p.income_verification_enabled AS STRING))
    ELSE NULL
  END as income_mismatch,
  CASE WHEN s.fraud_detection_enabled != p.fraud_detection_enabled
    THEN CONCAT('Fraud: ', CAST(s.fraud_detection_enabled AS STRING), ' -> ', CAST(p.fraud_detection_enabled AS STRING))
    ELSE NULL
  END as fraud_mismatch
FROM staging_features s
INNER JOIN production_features p ON s.property_id = p.property_id
WHERE
  s.idv_enabled != p.idv_enabled
  OR s.bank_linking_enabled != p.bank_linking_enabled
  OR s.connected_payroll_enabled != p.connected_payroll_enabled
  OR s.income_verification_enabled != p.income_verification_enabled
  OR s.fraud_detection_enabled != p.fraud_detection_enabled
ORDER BY s.property_name
"""
}

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
    print("STAGING vs PRODUCTION FEATURE FLAG COMPARISON")
    print("=" * 80)
    print()

    for query_name, query in QUERIES.items():
        print(f"\n{'=' * 80}")
        print(f"{query_name}")
        print(f"{'=' * 80}")

        # Execute query
        cursor.execute(query)

        # Fetch results
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()

        if results:
            # Convert to DataFrame for better display
            df = pd.DataFrame(results, columns=columns)

            # Show results
            print(f"\nResults: {len(df)} rows\n")

            # For large result sets, show first 50 rows
            if len(df) > 50:
                print(df.head(50).to_string(index=False))
                print(f"\n... ({len(df) - 50} more rows)")
            else:
                print(df.to_string(index=False))
        else:
            print("\nNo results returned")

        print()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

finally:
    cursor.close()
    connection.close()
