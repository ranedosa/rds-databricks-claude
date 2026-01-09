#!/usr/bin/env python3
"""
Compare feature flags between product_property and property tables in crm.salesforce
"""
import os
from databricks import sql
import pandas as pd

# Define queries directly
QUERIES = {
    "Summary Statistics": """
WITH product_features AS (
  SELECT
    sf_property_id_c as property_sf_id,
    snappt_property_id_c as product_snappt_id,
    short_id_c,
    id_verification_enabled_c as idv_enabled,
    bank_linking_enabled_c as bank_linking_enabled,
    connected_payroll_enabled_c as connected_payroll_enabled,
    income_verification_enabled_c as income_verification_enabled,
    fraud_detection_enabled_c as fraud_detection_enabled
  FROM crm.salesforce.product_property
  WHERE sf_property_id_c IS NOT NULL
),

property_features AS (
  SELECT
    id as property_sf_id,
    snappt_property_id_c as property_snappt_id,
    id_verification_enabled_c as idv_enabled,
    bank_linking_enabled_c as bank_linking_enabled,
    connected_payroll_enabled_c as connected_payroll_enabled,
    income_verification_enabled_c as income_verification_enabled,
    fraud_detection_enabled_c as fraud_detection_enabled
  FROM crm.salesforce.property
)

SELECT
  'Total Properties in product_property' as metric,
  COUNT(DISTINCT p.property_sf_id) as count
FROM product_features p

UNION ALL

SELECT
  'Total Properties in property' as metric,
  COUNT(DISTINCT pr.property_sf_id) as count
FROM property_features pr

UNION ALL

SELECT
  'Properties in Both Tables' as metric,
  COUNT(DISTINCT p.property_sf_id) as count
FROM product_features p
INNER JOIN property_features pr ON p.property_sf_id = pr.property_sf_id

UNION ALL

SELECT
  'Properties Only in product_property' as metric,
  COUNT(DISTINCT p.property_sf_id) as count
FROM product_features p
LEFT JOIN property_features pr ON p.property_sf_id = pr.property_sf_id
WHERE pr.property_sf_id IS NULL

UNION ALL

SELECT
  'Properties Only in property' as metric,
  COUNT(DISTINCT pr.property_sf_id) as count
FROM property_features pr
LEFT JOIN product_features p ON p.property_sf_id = pr.property_sf_id
WHERE p.property_sf_id IS NULL

UNION ALL

SELECT
  'IDV Flag Mismatches' as metric,
  COUNT(DISTINCT p.property_sf_id) as count
FROM product_features p
INNER JOIN property_features pr ON p.property_sf_id = pr.property_sf_id
WHERE p.idv_enabled != pr.idv_enabled

UNION ALL

SELECT
  'Bank Linking Flag Mismatches' as metric,
  COUNT(DISTINCT p.property_sf_id) as count
FROM product_features p
INNER JOIN property_features pr ON p.property_sf_id = pr.property_sf_id
WHERE p.bank_linking_enabled != pr.bank_linking_enabled

UNION ALL

SELECT
  'Connected Payroll Flag Mismatches' as metric,
  COUNT(DISTINCT p.property_sf_id) as count
FROM product_features p
INNER JOIN property_features pr ON p.property_sf_id = pr.property_sf_id
WHERE p.connected_payroll_enabled != pr.connected_payroll_enabled

UNION ALL

SELECT
  'Income Verification Flag Mismatches' as metric,
  COUNT(DISTINCT p.property_sf_id) as count
FROM product_features p
INNER JOIN property_features pr ON p.property_sf_id = pr.property_sf_id
WHERE p.income_verification_enabled != pr.income_verification_enabled

UNION ALL

SELECT
  'Fraud Detection Flag Mismatches' as metric,
  COUNT(DISTINCT p.property_sf_id) as count
FROM product_features p
INNER JOIN property_features pr ON p.property_sf_id = pr.property_sf_id
WHERE p.fraud_detection_enabled != pr.fraud_detection_enabled
""",

    "Mismatch Details": """
WITH product_features AS (
  SELECT
    sf_property_id_c as property_sf_id,
    snappt_property_id_c as product_snappt_id,
    short_id_c,
    id_verification_enabled_c as idv_enabled,
    bank_linking_enabled_c as bank_linking_enabled,
    connected_payroll_enabled_c as connected_payroll_enabled,
    income_verification_enabled_c as income_verification_enabled,
    fraud_detection_enabled_c as fraud_detection_enabled,
    id_verification_start_date_c as idv_start_date,
    bank_linking_start_date_c as bank_linking_start_date,
    connected_payroll_start_date_c as connected_payroll_start_date
  FROM crm.salesforce.product_property
  WHERE sf_property_id_c IS NOT NULL
),

property_features AS (
  SELECT
    id as property_sf_id,
    snappt_property_id_c as property_snappt_id,
    name as property_name,
    id_verification_enabled_c as idv_enabled,
    bank_linking_enabled_c as bank_linking_enabled,
    connected_payroll_enabled_c as connected_payroll_enabled,
    income_verification_enabled_c as income_verification_enabled,
    fraud_detection_enabled_c as fraud_detection_enabled,
    idv_start_date_c as idv_start_date,
    bank_linking_start_date_c as bank_linking_start_date,
    connected_payroll_start_date_c as connected_payroll_start_date
  FROM crm.salesforce.property
)

SELECT
  pr.property_sf_id,
  pr.property_snappt_id,
  p.product_snappt_id,
  p.short_id_c,
  pr.property_name,
  CASE WHEN p.idv_enabled != pr.idv_enabled
    THEN CONCAT('IDV: product_property=', CAST(p.idv_enabled AS STRING), ' vs property=', CAST(pr.idv_enabled AS STRING))
    ELSE NULL
  END as idv_mismatch,
  CASE WHEN p.bank_linking_enabled != pr.bank_linking_enabled
    THEN CONCAT('Bank: product_property=', CAST(p.bank_linking_enabled AS STRING), ' vs property=', CAST(pr.bank_linking_enabled AS STRING))
    ELSE NULL
  END as bank_mismatch,
  CASE WHEN p.connected_payroll_enabled != pr.connected_payroll_enabled
    THEN CONCAT('Payroll: product_property=', CAST(p.connected_payroll_enabled AS STRING), ' vs property=', CAST(pr.connected_payroll_enabled AS STRING))
    ELSE NULL
  END as payroll_mismatch,
  CASE WHEN p.income_verification_enabled != pr.income_verification_enabled
    THEN CONCAT('Income: product_property=', CAST(p.income_verification_enabled AS STRING), ' vs property=', CAST(pr.income_verification_enabled AS STRING))
    ELSE NULL
  END as income_mismatch,
  CASE WHEN p.fraud_detection_enabled != pr.fraud_detection_enabled
    THEN CONCAT('Fraud: product_property=', CAST(p.fraud_detection_enabled AS STRING), ' vs property=', CAST(pr.fraud_detection_enabled AS STRING))
    ELSE NULL
  END as fraud_mismatch,
  p.idv_start_date as product_property_idv_start,
  pr.idv_start_date as property_idv_start,
  p.bank_linking_start_date as product_property_bank_start,
  pr.bank_linking_start_date as property_bank_start,
  p.connected_payroll_start_date as product_property_payroll_start,
  pr.connected_payroll_start_date as property_payroll_start
FROM product_features p
INNER JOIN property_features pr ON p.property_sf_id = pr.property_sf_id
WHERE
  p.idv_enabled != pr.idv_enabled
  OR p.bank_linking_enabled != pr.bank_linking_enabled
  OR p.connected_payroll_enabled != pr.connected_payroll_enabled
  OR p.income_verification_enabled != pr.income_verification_enabled
  OR p.fraud_detection_enabled != pr.fraud_detection_enabled
ORDER BY pr.property_name
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
    print("PRODUCT_PROPERTY vs PROPERTY FEATURE FLAG COMPARISON")
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
