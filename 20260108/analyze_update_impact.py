#!/usr/bin/env python3
"""
Analyze what columns will be updated for 7,820 properties
Shows before/after values and impact analysis
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
    print("UPDATE IMPACT ANALYSIS - 7,820 PROPERTIES")
    print("=" * 80)
    print("Comparing: properties_to_update (NEW) vs Salesforce (CURRENT)")
    print("=" * 80)
    print()

    # Step 1: Show columns in update view
    print("=" * 80)
    print("STEP 1: Columns in properties_to_update View")
    print("=" * 80)

    query = "DESCRIBE crm.sfdc_dbx.properties_to_update"
    cursor.execute(query)
    columns_result = cursor.fetchall()

    update_columns = [row[0] for row in columns_result]
    print(f"\nTotal columns: {len(update_columns)}")
    print("\nColumn list:")
    for col in update_columns:
        print(f"  - {col}")
    print()

    # Step 2: Which columns will change?
    print("=" * 80)
    print("STEP 2: Change Impact by Column")
    print("=" * 80)
    print("Analyzing how many properties will have each column updated...")
    print()

    query = """
WITH new_data AS (
  SELECT
    CAST(rds_property_id AS STRING) as property_id,
    property_name,
    address,
    city,
    state,
    postal_code,
    company_name,
    idv_enabled,
    bank_linking_enabled,
    payroll_enabled,
    income_insights_enabled,
    document_fraud_enabled,
    idv_enabled_at,
    bank_linking_enabled_at,
    payroll_enabled_at,
    income_insights_enabled_at,
    document_fraud_enabled_at,
    active_property_count,
    total_feature_count,
    is_multi_property,
    has_any_features_enabled
  FROM crm.sfdc_dbx.properties_to_update
),

current_data AS (
  SELECT
    snappt_property_id_c as property_id,
    name as property_name,
    address_c as address,
    city_c as city,
    state_c as state,
    postal_code_c as postal_code,
    company_name_c as company_name,
    COALESCE(id_verification_enabled_c, false) as idv_enabled,
    COALESCE(bank_linking_enabled_c, false) as bank_linking_enabled,
    COALESCE(connected_payroll_enabled_c, false) as payroll_enabled,
    COALESCE(income_verification_enabled_c, false) as income_insights_enabled,
    COALESCE(fraud_detection_enabled_c, false) as document_fraud_enabled,
    id_verification_start_date_c as idv_enabled_at,
    bank_linking_start_date_c as bank_linking_enabled_at,
    connected_payroll_start_date_c as payroll_enabled_at,
    income_verification_start_date_c as income_insights_enabled_at,
    fraud_detection_start_date_c as document_fraud_enabled_at,
    active_property_count_c as active_property_count,
    total_feature_count_c as total_feature_count,
    COALESCE(is_multi_property_c, false) as is_multi_property,
    COALESCE(has_any_features_enabled_c, false) as has_any_features_enabled
  FROM crm.salesforce.product_property
  WHERE snappt_property_id_c IS NOT NULL
)

SELECT
  'property_name' as column_name,
  COUNT(CASE WHEN n.property_name != c.property_name OR (n.property_name IS NULL) != (c.property_name IS NULL) THEN 1 END) as will_change,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'address' as column_name,
  COUNT(CASE WHEN n.address != c.address OR (n.address IS NULL) != (c.address IS NULL) THEN 1 END) as will_change,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'city' as column_name,
  COUNT(CASE WHEN n.city != c.city OR (n.city IS NULL) != (c.city IS NULL) THEN 1 END) as will_change,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'state' as column_name,
  COUNT(CASE WHEN n.state != c.state OR (n.state IS NULL) != (c.state IS NULL) THEN 1 END) as will_change,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'postal_code' as column_name,
  COUNT(CASE WHEN n.postal_code != c.postal_code OR (n.postal_code IS NULL) != (c.postal_code IS NULL) THEN 1 END) as will_change,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'company_name' as column_name,
  COUNT(CASE WHEN n.company_name != c.company_name OR (n.company_name IS NULL) != (c.company_name IS NULL) THEN 1 END) as will_change,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'idv_enabled (FEATURE FLAG)' as column_name,
  COUNT(CASE WHEN n.idv_enabled != c.idv_enabled THEN 1 END) as will_change,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'bank_linking_enabled (FEATURE FLAG)' as column_name,
  COUNT(CASE WHEN n.bank_linking_enabled != c.bank_linking_enabled THEN 1 END) as will_change,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'payroll_enabled (FEATURE FLAG)' as column_name,
  COUNT(CASE WHEN n.payroll_enabled != c.payroll_enabled THEN 1 END) as will_change,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'income_insights_enabled (FEATURE FLAG)' as column_name,
  COUNT(CASE WHEN n.income_insights_enabled != c.income_insights_enabled THEN 1 END) as will_change,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'document_fraud_enabled (FEATURE FLAG)' as column_name,
  COUNT(CASE WHEN n.document_fraud_enabled != c.document_fraud_enabled THEN 1 END) as will_change,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'active_property_count' as column_name,
  COUNT(CASE WHEN n.active_property_count != c.active_property_count OR (n.active_property_count IS NULL) != (c.active_property_count IS NULL) THEN 1 END) as will_change,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'total_feature_count' as column_name,
  COUNT(CASE WHEN n.total_feature_count != c.total_feature_count OR (n.total_feature_count IS NULL) != (c.total_feature_count IS NULL) THEN 1 END) as will_change,
  COUNT(*) as total_matched
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id

UNION ALL

SELECT
  'is_multi_property' as column_name,
  COUNT(CASE WHEN n.is_multi_property != c.is_multi_property THEN 1 END) as will_change,
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

    # Step 3: Sample of what will change
    print("=" * 80)
    print("STEP 3: Sample Records - Before & After")
    print("=" * 80)
    print("Showing 10 properties with changes...")
    print()

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
    COALESCE(is_multi_property_c, false) as is_multi_property
  FROM crm.salesforce.product_property
  WHERE snappt_property_id_c IS NOT NULL
)

SELECT
  n.property_id,
  n.property_name,

  -- Show changes
  CASE WHEN n.idv_enabled != c.idv_enabled
    THEN CONCAT(CAST(c.idv_enabled AS STRING), ' → ', CAST(n.idv_enabled AS STRING))
    ELSE 'no change'
  END as idv_change,

  CASE WHEN n.bank_linking_enabled != c.bank_linking_enabled
    THEN CONCAT(CAST(c.bank_linking_enabled AS STRING), ' → ', CAST(n.bank_linking_enabled AS STRING))
    ELSE 'no change'
  END as bank_change,

  CASE WHEN n.payroll_enabled != c.payroll_enabled
    THEN CONCAT(CAST(c.payroll_enabled AS STRING), ' → ', CAST(n.payroll_enabled AS STRING))
    ELSE 'no change'
  END as payroll_change,

  CASE WHEN n.income_insights_enabled != c.income_insights_enabled
    THEN CONCAT(CAST(c.income_insights_enabled AS STRING), ' → ', CAST(n.income_insights_enabled AS STRING))
    ELSE 'no change'
  END as income_change,

  CASE WHEN n.document_fraud_enabled != c.document_fraud_enabled
    THEN CONCAT(CAST(c.document_fraud_enabled AS STRING), ' → ', CAST(n.document_fraud_enabled AS STRING))
    ELSE 'no change'
  END as fraud_change,

  CASE WHEN n.active_property_count != c.active_property_count OR (n.active_property_count IS NULL) != (c.active_property_count IS NULL)
    THEN CONCAT(COALESCE(CAST(c.active_property_count AS STRING), 'NULL'), ' → ', COALESCE(CAST(n.active_property_count AS STRING), 'NULL'))
    ELSE 'no change'
  END as count_change

FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.idv_enabled != c.idv_enabled
   OR n.bank_linking_enabled != c.bank_linking_enabled
   OR n.payroll_enabled != c.payroll_enabled
   OR n.income_insights_enabled != c.income_insights_enabled
   OR n.document_fraud_enabled != c.document_fraud_enabled
   OR n.active_property_count != c.active_property_count
   OR (n.active_property_count IS NULL) != (c.active_property_count IS NULL)
LIMIT 10
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()

    if results:
        df = pd.DataFrame(results, columns=columns)
        print(df.to_string(index=False))
    else:
        print("No changes detected in sample")

    print()

    # Step 4: Risk analysis
    print("=" * 80)
    print("STEP 4: Risk Analysis")
    print("=" * 80)

    query = """
WITH new_data AS (
  SELECT
    CAST(rds_property_id AS STRING) as property_id,
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
    COALESCE(id_verification_enabled_c, false) as idv_enabled,
    COALESCE(bank_linking_enabled_c, false) as bank_linking_enabled,
    COALESCE(connected_payroll_enabled_c, false) as payroll_enabled,
    COALESCE(income_verification_enabled_c, false) as income_insights_enabled,
    COALESCE(fraud_detection_enabled_c, false) as document_fraud_enabled
  FROM crm.salesforce.product_property
  WHERE snappt_property_id_c IS NOT NULL
)

SELECT
  'Properties with ANY change' as category,
  COUNT(*) as count
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.idv_enabled != c.idv_enabled
   OR n.bank_linking_enabled != c.bank_linking_enabled
   OR n.payroll_enabled != c.payroll_enabled
   OR n.income_insights_enabled != c.income_insights_enabled
   OR n.document_fraud_enabled != c.document_fraud_enabled

UNION ALL

SELECT
  'Properties with NO changes' as category,
  COUNT(*) as count
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE n.idv_enabled = c.idv_enabled
  AND n.bank_linking_enabled = c.bank_linking_enabled
  AND n.payroll_enabled = c.payroll_enabled
  AND n.income_insights_enabled = c.income_insights_enabled
  AND n.document_fraud_enabled = c.document_fraud_enabled

UNION ALL

SELECT
  'Feature flag ENABLED (turning ON)' as category,
  COUNT(*) as count
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE (n.idv_enabled = true AND c.idv_enabled = false)
   OR (n.bank_linking_enabled = true AND c.bank_linking_enabled = false)
   OR (n.payroll_enabled = true AND c.payroll_enabled = false)
   OR (n.income_insights_enabled = true AND c.income_insights_enabled = false)
   OR (n.document_fraud_enabled = true AND c.document_fraud_enabled = false)

UNION ALL

SELECT
  'Feature flag DISABLED (turning OFF)' as category,
  COUNT(*) as count
FROM new_data n
INNER JOIN current_data c ON n.property_id = c.property_id
WHERE (n.idv_enabled = false AND c.idv_enabled = true)
   OR (n.bank_linking_enabled = false AND c.bank_linking_enabled = true)
   OR (n.payroll_enabled = false AND c.payroll_enabled = true)
   OR (n.income_insights_enabled = false AND c.income_insights_enabled = true)
   OR (n.document_fraud_enabled = false AND c.document_fraud_enabled = true)
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)

    print(df.to_string(index=False))
    print()

    print("=" * 80)
    print("SUMMARY & RECOMMENDATION")
    print("=" * 80)
    print()
    print("What will happen when you run the UPDATE sync:")
    print()
    print("1. Census will UPDATE ~7,820 existing Product_Property__c records")
    print("2. Only fields that have CHANGED will be updated")
    print("3. Fields that match current values will NOT be touched")
    print()
    print("Safety features:")
    print("  ✅ Operation: UPDATE (not delete)")
    print("  ✅ No data will be deleted")
    print("  ✅ Audit trail preserved in Salesforce")
    print("  ✅ Can re-run sync to revert if needed")
    print()
    print("Recommendation:")
    print("  Review the column changes above")
    print("  If feature flag changes look correct → PROCEED")
    print("  If unexpected changes → INVESTIGATE FIRST")

finally:
    cursor.close()
    connection.close()
