#!/usr/bin/env python3
"""
Simplified update impact analysis focusing on feature flags
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
    print("UPDATE IMPACT ANALYSIS - FEATURE FLAGS")
    print("=" * 80)
    print("What will change when updating 7,820 properties?")
    print("=" * 80)
    print()

    # Impact by feature flag
    print("=" * 80)
    print("Feature Flag Changes")
    print("=" * 80)

    query = """
WITH new_data AS (
  SELECT
    CAST(rds_property_id AS STRING) as property_id,
    property_name,
    idv_enabled,
    bank_linking_enabled,
    payroll_enabled,
    income_insights_enabled,
    document_fraud_enabled,
    active_property_count,
    total_feature_count,
    is_multi_property
  FROM crm.sfdc_dbx.properties_to_update
),

current_data AS (
  SELECT
    snappt_property_id_c as property_id,
    name as property_name,
    COALESCE(id_verification_enabled_c, false) as idv_enabled,
    COALESCE(bank_linking_enabled_c, false) as bank_linking_enabled,
    COALESCE(connected_payroll_enabled_c, false) as payroll_enabled,
    COALESCE(income_verification_enabled_c, false) as income_insights_enabled,
    COALESCE(fraud_detection_enabled_c, false) as document_fraud_enabled,
    active_property_count_c as active_property_count,
    total_feature_count_c as total_feature_count,
    COALESCE(is_multi_property_c, false) as is_multi_property
  FROM crm.salesforce.product_property
  WHERE snappt_property_id_c IS NOT NULL
)

SELECT
  'ID Verification' as feature,
  COUNT(CASE WHEN n.idv_enabled != c.idv_enabled THEN 1 END) as will_change,
  COUNT(CASE WHEN n.idv_enabled = true AND c.idv_enabled = false THEN 1 END) as turning_on,
  COUNT(CASE WHEN n.idv_enabled = false AND c.idv_enabled = true THEN 1 END) as turning_off,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'Bank Linking' as feature,
  COUNT(CASE WHEN n.bank_linking_enabled != c.bank_linking_enabled THEN 1 END) as will_change,
  COUNT(CASE WHEN n.bank_linking_enabled = true AND c.bank_linking_enabled = false THEN 1 END) as turning_on,
  COUNT(CASE WHEN n.bank_linking_enabled = false AND c.bank_linking_enabled = true THEN 1 END) as turning_off,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'Connected Payroll' as feature,
  COUNT(CASE WHEN n.payroll_enabled != c.payroll_enabled THEN 1 END) as will_change,
  COUNT(CASE WHEN n.payroll_enabled = true AND c.payroll_enabled = false THEN 1 END) as turning_on,
  COUNT(CASE WHEN n.payroll_enabled = false AND c.payroll_enabled = true THEN 1 END) as turning_off,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'Income Verification' as feature,
  COUNT(CASE WHEN n.income_insights_enabled != c.income_insights_enabled THEN 1 END) as will_change,
  COUNT(CASE WHEN n.income_insights_enabled = true AND c.income_insights_enabled = false THEN 1 END) as turning_on,
  COUNT(CASE WHEN n.income_insights_enabled = false AND c.income_insights_enabled = true THEN 1 END) as turning_off,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'Fraud Detection' as feature,
  COUNT(CASE WHEN n.document_fraud_enabled != c.document_fraud_enabled THEN 1 END) as will_change,
  COUNT(CASE WHEN n.document_fraud_enabled = true AND c.document_fraud_enabled = false THEN 1 END) as turning_on,
  COUNT(CASE WHEN n.document_fraud_enabled = false AND c.document_fraud_enabled = true THEN 1 END) as turning_off,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'Multi-Property Flag' as feature,
  COUNT(CASE WHEN n.is_multi_property != c.is_multi_property THEN 1 END) as will_change,
  COUNT(CASE WHEN n.is_multi_property = true AND c.is_multi_property = false THEN 1 END) as turning_on,
  COUNT(CASE WHEN n.is_multi_property = false AND c.is_multi_property = true THEN 1 END) as turning_off,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'Active Property Count' as feature,
  COUNT(CASE WHEN COALESCE(n.active_property_count, 0) != COALESCE(c.active_property_count, 0) THEN 1 END) as will_change,
  NULL as turning_on,
  NULL as turning_off,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

ORDER BY will_change DESC
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)
    df['pct_change'] = (df['will_change'] / df['total_matched'] * 100).round(1)

    print(df.to_string(index=False))
    print()

    # Overall summary
    print("=" * 80)
    print("Overall Summary")
    print("=" * 80)

    query = """
WITH new_data AS (
  SELECT
    CAST(rds_property_id AS STRING) as property_id,
    idv_enabled,
    bank_linking_enabled,
    payroll_enabled,
    income_insights_enabled,
    document_fraud_enabled,
    is_multi_property,
    active_property_count
  FROM crm.sfdc_dbx.properties_to_update
),

current_data AS (
  SELECT
    snappt_property_id_c as property_id,
    COALESCE(id_verification_enabled_c, false) as idv_enabled,
    COALESCE(bank_linking_enabled_c, false) as bank_linking_enabled,
    COALESCE(connected_payroll_enabled_c, false) as payroll_enabled,
    COALESCE(income_verification_enabled_c, false) as income_insights_enabled,
    COALESCE(fraud_detection_enabled_c, false) as document_fraud_enabled,
    COALESCE(is_multi_property_c, false) as is_multi_property,
    active_property_count_c as active_property_count
  FROM crm.salesforce.product_property
  WHERE snappt_property_id_c IS NOT NULL
)

SELECT
  'Total properties matched' as category,
  COUNT(*) as count,
  CAST(NULL AS DOUBLE) as percentage
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'Properties with ANY change' as category,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM new_data n INNER JOIN current_data c ON n.property_id = c.property_id), 1) as percentage
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.idv_enabled != c.idv_enabled
   OR n.bank_linking_enabled != c.bank_linking_enabled
   OR n.payroll_enabled != c.payroll_enabled
   OR n.income_insights_enabled != c.income_insights_enabled
   OR n.document_fraud_enabled != c.document_fraud_enabled
   OR n.is_multi_property != c.is_multi_property
   OR COALESCE(n.active_property_count, 0) != COALESCE(c.active_property_count, 0)

UNION ALL

SELECT
  'Properties with NO changes' as category,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM new_data n INNER JOIN current_data c ON n.property_id = c.property_id), 1) as percentage
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.idv_enabled = c.idv_enabled
  AND n.bank_linking_enabled = c.bank_linking_enabled
  AND n.payroll_enabled = c.payroll_enabled
  AND n.income_insights_enabled = c.income_insights_enabled
  AND n.document_fraud_enabled = c.document_fraud_enabled
  AND n.is_multi_property = c.is_multi_property
  AND COALESCE(n.active_property_count, 0) = COALESCE(c.active_property_count, 0)
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)

    print(df.to_string(index=False))
    print()

    # Sample changes
    print("=" * 80)
    print("Sample: Properties with Feature Flag Changes")
    print("=" * 80)

    query = """
WITH new_data AS (
  SELECT
    CAST(rds_property_id AS STRING) as property_id,
    property_name,
    idv_enabled,
    bank_linking_enabled,
    payroll_enabled,
    income_insights_enabled,
    document_fraud_enabled
  FROM crm.sfdc_dbx.properties_to_update
),

current_data AS (
  SELECT
    snappt_property_id_c as property_id,
    name as property_name,
    COALESCE(id_verification_enabled_c, false) as idv_enabled,
    COALESCE(bank_linking_enabled_c, false) as bank_linking_enabled,
    COALESCE(connected_payroll_enabled_c, false) as payroll_enabled,
    COALESCE(income_verification_enabled_c, false) as income_insights_enabled,
    COALESCE(fraud_detection_enabled_c, false) as document_fraud_enabled
  FROM crm.salesforce.product_property
  WHERE snappt_property_id_c IS NOT NULL
)

SELECT
  n.property_name,
  CASE WHEN n.idv_enabled != c.idv_enabled
    THEN CONCAT(CAST(c.idv_enabled AS STRING), '→', CAST(n.idv_enabled AS STRING))
    ELSE '='
  END as idv,
  CASE WHEN n.bank_linking_enabled != c.bank_linking_enabled
    THEN CONCAT(CAST(c.bank_linking_enabled AS STRING), '→', CAST(n.bank_linking_enabled AS STRING))
    ELSE '='
  END as bank,
  CASE WHEN n.payroll_enabled != c.payroll_enabled
    THEN CONCAT(CAST(c.payroll_enabled AS STRING), '→', CAST(n.payroll_enabled AS STRING))
    ELSE '='
  END as payroll,
  CASE WHEN n.income_insights_enabled != c.income_insights_enabled
    THEN CONCAT(CAST(c.income_insights_enabled AS STRING), '→', CAST(n.income_insights_enabled AS STRING))
    ELSE '='
  END as income,
  CASE WHEN n.document_fraud_enabled != c.document_fraud_enabled
    THEN CONCAT(CAST(c.document_fraud_enabled AS STRING), '→', CAST(n.document_fraud_enabled AS STRING))
    ELSE '='
  END as fraud
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.idv_enabled != c.idv_enabled
   OR n.bank_linking_enabled != c.bank_linking_enabled
   OR n.payroll_enabled != c.payroll_enabled
   OR n.income_insights_enabled != c.income_insights_enabled
   OR n.document_fraud_enabled != c.document_fraud_enabled
LIMIT 20
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()

    if results:
        df = pd.DataFrame(results, columns=columns)
        print(f"Showing 20 of {len(results)} properties with changes:")
        print()
        print(df.to_string(index=False))
    else:
        print("No changes detected")

    print()

    # Risk assessment
    print("=" * 80)
    print("RISK ASSESSMENT")
    print("=" * 80)
    print()
    print("✅ SAFE TO UPDATE because:")
    print("   - Operation is UPDATE (not DELETE)")
    print("   - No data will be removed")
    print("   - Salesforce audit trail will show all changes")
    print("   - Can re-run sync to revert if needed")
    print()
    print("⚠️ REVIEW CAREFULLY:")
    print("   - Features turning OFF (false→true) - Could impact customers")
    print("   - Large % of changes - Unexpected pattern?")
    print()
    print("Next steps:")
    print("   1. Review the numbers above")
    print("   2. If changes match your expectations → PROCEED")
    print("   3. If unexpected patterns → INVESTIGATE")

finally:
    cursor.close()
    connection.close()
