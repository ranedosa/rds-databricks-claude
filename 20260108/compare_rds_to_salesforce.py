#!/usr/bin/env python3
"""
Compare feature flags between RDS (source) and Salesforce product_property (target)
"""
import os
from databricks import sql
import pandas as pd

# Define queries directly
QUERIES = {
    "Summary Statistics": """
WITH rds_features AS (
  SELECT
    property_id,
    MAX(CASE WHEN feature_code = 'identity_verification' AND state = 'enabled' THEN true ELSE false END) as idv_enabled,
    MAX(CASE WHEN feature_code = 'bank_linking' AND state = 'enabled' THEN true ELSE false END) as bank_linking_enabled,
    MAX(CASE WHEN feature_code = 'payroll_linking' AND state = 'enabled' THEN true ELSE false END) as payroll_enabled,
    MAX(CASE WHEN feature_code = 'income_verification' AND state = 'enabled' THEN true ELSE false END) as income_enabled
  FROM rds.pg_rds_public.property_features
  WHERE _fivetran_deleted = false
  GROUP BY property_id
),

salesforce_features AS (
  SELECT
    snappt_property_id_c as property_id,
    COALESCE(id_verification_enabled_c, false) as idv_enabled,
    COALESCE(bank_linking_enabled_c, false) as bank_linking_enabled,
    COALESCE(connected_payroll_enabled_c, false) as payroll_enabled,
    COALESCE(income_verification_enabled_c, false) as income_enabled
  FROM crm.salesforce.product_property
  WHERE snappt_property_id_c IS NOT NULL
)

SELECT
  'Total Properties in RDS' as metric,
  COUNT(DISTINCT r.property_id) as count
FROM rds_features r

UNION ALL

SELECT
  'Total Properties in Salesforce product_property' as metric,
  COUNT(DISTINCT s.property_id) as count
FROM salesforce_features s

UNION ALL

SELECT
  'Properties in Both Systems' as metric,
  COUNT(DISTINCT r.property_id) as count
FROM rds_features r
INNER JOIN salesforce_features s ON r.property_id = s.property_id

UNION ALL

SELECT
  'Properties Only in RDS' as metric,
  COUNT(DISTINCT r.property_id) as count
FROM rds_features r
LEFT JOIN salesforce_features s ON r.property_id = s.property_id
WHERE s.property_id IS NULL

UNION ALL

SELECT
  'Properties Only in Salesforce' as metric,
  COUNT(DISTINCT s.property_id) as count
FROM salesforce_features s
LEFT JOIN rds_features r ON r.property_id = s.property_id
WHERE r.property_id IS NULL

UNION ALL

SELECT
  'ID Verification Flag Mismatches' as metric,
  COUNT(DISTINCT r.property_id) as count
FROM rds_features r
INNER JOIN salesforce_features s ON r.property_id = s.property_id
WHERE r.idv_enabled != s.idv_enabled

UNION ALL

SELECT
  'Bank Linking Flag Mismatches' as metric,
  COUNT(DISTINCT r.property_id) as count
FROM rds_features r
INNER JOIN salesforce_features s ON r.property_id = s.property_id
WHERE r.bank_linking_enabled != s.bank_linking_enabled

UNION ALL

SELECT
  'Connected Payroll Flag Mismatches' as metric,
  COUNT(DISTINCT r.property_id) as count
FROM rds_features r
INNER JOIN salesforce_features s ON r.property_id = s.property_id
WHERE r.payroll_enabled != s.payroll_enabled

UNION ALL

SELECT
  'Income Verification Flag Mismatches' as metric,
  COUNT(DISTINCT r.property_id) as count
FROM rds_features r
INNER JOIN salesforce_features s ON r.property_id = s.property_id
WHERE r.income_enabled != s.income_enabled

UNION ALL

SELECT
  'Properties with ANY Mismatch' as metric,
  COUNT(DISTINCT r.property_id) as count
FROM rds_features r
INNER JOIN salesforce_features s ON r.property_id = s.property_id
WHERE r.idv_enabled != s.idv_enabled
   OR r.bank_linking_enabled != s.bank_linking_enabled
   OR r.payroll_enabled != s.payroll_enabled
   OR r.income_enabled != s.income_enabled
""",

    "Mismatch Details": """
WITH rds_features AS (
  SELECT
    property_id,
    MAX(CASE WHEN feature_code = 'identity_verification' AND state = 'enabled' THEN true ELSE false END) as idv_enabled,
    MAX(CASE WHEN feature_code = 'bank_linking' AND state = 'enabled' THEN true ELSE false END) as bank_linking_enabled,
    MAX(CASE WHEN feature_code = 'payroll_linking' AND state = 'enabled' THEN true ELSE false END) as payroll_enabled,
    MAX(CASE WHEN feature_code = 'income_verification' AND state = 'enabled' THEN true ELSE false END) as income_enabled
  FROM rds.pg_rds_public.property_features
  WHERE _fivetran_deleted = false
  GROUP BY property_id
),

salesforce_features AS (
  SELECT
    snappt_property_id_c as property_id,
    short_id_c,
    name,
    COALESCE(id_verification_enabled_c, false) as idv_enabled,
    COALESCE(bank_linking_enabled_c, false) as bank_linking_enabled,
    COALESCE(connected_payroll_enabled_c, false) as payroll_enabled,
    COALESCE(income_verification_enabled_c, false) as income_enabled
  FROM crm.salesforce.product_property
  WHERE snappt_property_id_c IS NOT NULL
)

SELECT
  r.property_id,
  s.short_id_c,
  s.name as property_name,
  CASE WHEN r.idv_enabled != s.idv_enabled
    THEN CONCAT('IDV: RDS=', CAST(r.idv_enabled AS STRING), ' vs SF=', CAST(s.idv_enabled AS STRING))
    ELSE NULL
  END as idv_mismatch,
  CASE WHEN r.bank_linking_enabled != s.bank_linking_enabled
    THEN CONCAT('Bank: RDS=', CAST(r.bank_linking_enabled AS STRING), ' vs SF=', CAST(s.bank_linking_enabled AS STRING))
    ELSE NULL
  END as bank_mismatch,
  CASE WHEN r.payroll_enabled != s.payroll_enabled
    THEN CONCAT('Payroll: RDS=', CAST(r.payroll_enabled AS STRING), ' vs SF=', CAST(s.payroll_enabled AS STRING))
    ELSE NULL
  END as payroll_mismatch,
  CASE WHEN r.income_enabled != s.income_enabled
    THEN CONCAT('Income: RDS=', CAST(r.income_enabled AS STRING), ' vs SF=', CAST(s.income_enabled AS STRING))
    ELSE NULL
  END as income_mismatch
FROM rds_features r
INNER JOIN salesforce_features s ON r.property_id = s.property_id
WHERE
  r.idv_enabled != s.idv_enabled
  OR r.bank_linking_enabled != s.bank_linking_enabled
  OR r.payroll_enabled != s.payroll_enabled
  OR r.income_enabled != s.income_enabled
ORDER BY s.name
LIMIT 100
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
    print("RDS → SALESFORCE PRODUCT_PROPERTY COMPARISON")
    print("=" * 80)
    print("Comparing source (RDS) to target (Salesforce product_property)")
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
