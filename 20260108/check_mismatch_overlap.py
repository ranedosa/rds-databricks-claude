#!/usr/bin/env python3
"""
Check overlap between mismatched properties and Census update queue
Will the Day 3 rollout fix the mismatches automatically?
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
    print("MISMATCH OVERLAP ANALYSIS")
    print("=" * 80)
    print("Question: Will Day 3 Census rollout fix the existing mismatches?")
    print("=" * 80)
    print()

    # Get the mismatched properties
    print("=" * 80)
    print("Step 1: Identifying Mismatched Properties")
    print("=" * 80)

    query = """
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
),

mismatched_properties AS (
  SELECT
    r.property_id,
    r.idv_enabled as rds_idv,
    s.idv_enabled as sf_idv,
    r.bank_linking_enabled as rds_bank,
    s.bank_linking_enabled as sf_bank,
    r.payroll_enabled as rds_payroll,
    s.payroll_enabled as sf_payroll,
    r.income_enabled as rds_income,
    s.income_enabled as sf_income
  FROM rds_features r
  INNER JOIN salesforce_features s ON r.property_id = s.property_id
  WHERE r.idv_enabled != s.idv_enabled
     OR r.bank_linking_enabled != s.bank_linking_enabled
     OR r.payroll_enabled != s.payroll_enabled
     OR r.income_enabled != s.income_enabled
)

SELECT COUNT(DISTINCT property_id) as total_mismatched_properties
FROM mismatched_properties
    """

    cursor.execute(query)
    total_mismatched = cursor.fetchall()[0][0]
    print(f"Total mismatched properties: {total_mismatched}")
    print()

    # Check overlap with Census update queue
    print("=" * 80)
    print("Step 2: Checking Overlap with Census Update Queue")
    print("=" * 80)

    query = """
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
),

mismatched_properties AS (
  SELECT
    r.property_id
  FROM rds_features r
  INNER JOIN salesforce_features s ON r.property_id = s.property_id
  WHERE r.idv_enabled != s.idv_enabled
     OR r.bank_linking_enabled != s.bank_linking_enabled
     OR r.payroll_enabled != s.payroll_enabled
     OR r.income_enabled != s.income_enabled
),

census_update_queue AS (
  SELECT CAST(rds_property_id AS STRING) as property_id
  FROM crm.sfdc_dbx.properties_to_update
)

SELECT
  COUNT(DISTINCT m.property_id) as total_mismatched,
  COUNT(DISTINCT c.property_id) as in_census_queue,
  ROUND(COUNT(DISTINCT c.property_id) * 100.0 / COUNT(DISTINCT m.property_id), 1) as pct_will_be_fixed
FROM mismatched_properties m
LEFT JOIN census_update_queue c ON m.property_id = c.property_id
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)

    total = df['total_mismatched'][0]
    in_queue = df['in_census_queue'][0]
    pct = df['pct_will_be_fixed'][0]
    orphaned = total - in_queue

    print(f"Total mismatched properties: {total}")
    print(f"In Census update queue: {in_queue}")
    print(f"Will be fixed by Day 3: {pct}%")
    print(f"Orphaned (won't be fixed): {orphaned}")
    print()

    # Breakdown by feature
    print("=" * 80)
    print("Step 3: Mismatch Breakdown by Feature Type")
    print("=" * 80)

    query = """
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
),

census_update_queue AS (
  SELECT CAST(rds_property_id AS STRING) as property_id
  FROM crm.sfdc_dbx.properties_to_update
)

SELECT
  'ID Verification' as feature,
  COUNT(DISTINCT CASE WHEN r.idv_enabled != s.idv_enabled THEN r.property_id END) as mismatches,
  COUNT(DISTINCT CASE WHEN r.idv_enabled != s.idv_enabled AND c.property_id IS NOT NULL THEN r.property_id END) as will_be_fixed
FROM rds_features r
INNER JOIN salesforce_features s ON r.property_id = s.property_id
LEFT JOIN census_update_queue c ON r.property_id = c.property_id

UNION ALL

SELECT
  'Bank Linking' as feature,
  COUNT(DISTINCT CASE WHEN r.bank_linking_enabled != s.bank_linking_enabled THEN r.property_id END) as mismatches,
  COUNT(DISTINCT CASE WHEN r.bank_linking_enabled != s.bank_linking_enabled AND c.property_id IS NOT NULL THEN r.property_id END) as will_be_fixed
FROM rds_features r
INNER JOIN salesforce_features s ON r.property_id = s.property_id
LEFT JOIN census_update_queue c ON r.property_id = c.property_id

UNION ALL

SELECT
  'Connected Payroll' as feature,
  COUNT(DISTINCT CASE WHEN r.payroll_enabled != s.payroll_enabled THEN r.property_id END) as mismatches,
  COUNT(DISTINCT CASE WHEN r.payroll_enabled != s.payroll_enabled AND c.property_id IS NOT NULL THEN r.property_id END) as will_be_fixed
FROM rds_features r
INNER JOIN salesforce_features s ON r.property_id = s.property_id
LEFT JOIN census_update_queue c ON r.property_id = c.property_id

UNION ALL

SELECT
  'Income Verification' as feature,
  COUNT(DISTINCT CASE WHEN r.income_enabled != s.income_enabled THEN r.property_id END) as mismatches,
  COUNT(DISTINCT CASE WHEN r.income_enabled != s.income_enabled AND c.property_id IS NOT NULL THEN r.property_id END) as will_be_fixed
FROM rds_features r
INNER JOIN salesforce_features s ON r.property_id = s.property_id
LEFT JOIN census_update_queue c ON r.property_id = c.property_id
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    df = pd.DataFrame(results, columns=columns)
    df['pct_fixed'] = (df['will_be_fixed'] / df['mismatches'] * 100).round(1)
    print(df.to_string(index=False))
    print()

    # Sample orphaned properties
    print("=" * 80)
    print("Step 4: Sample of Orphaned Properties (Won't Be Fixed)")
    print("=" * 80)

    query = """
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
),

census_update_queue AS (
  SELECT CAST(rds_property_id AS STRING) as property_id
  FROM crm.sfdc_dbx.properties_to_update
)

SELECT
  s.property_id,
  s.short_id_c,
  s.name,
  CASE WHEN r.idv_enabled != s.idv_enabled THEN 'IDV' ELSE NULL END as idv_mismatch,
  CASE WHEN r.bank_linking_enabled != s.bank_linking_enabled THEN 'Bank' ELSE NULL END as bank_mismatch,
  CASE WHEN r.payroll_enabled != s.payroll_enabled THEN 'Payroll' ELSE NULL END as payroll_mismatch,
  CASE WHEN r.income_enabled != s.income_enabled THEN 'Income' ELSE NULL END as income_mismatch
FROM rds_features r
INNER JOIN salesforce_features s ON r.property_id = s.property_id
LEFT JOIN census_update_queue c ON r.property_id = c.property_id
WHERE c.property_id IS NULL
  AND (r.idv_enabled != s.idv_enabled
    OR r.bank_linking_enabled != s.bank_linking_enabled
    OR r.payroll_enabled != s.payroll_enabled
    OR r.income_enabled != s.income_enabled)
LIMIT 20
    """

    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()

    if results:
        df = pd.DataFrame(results, columns=columns)
        print(f"Showing {len(df)} of {orphaned} orphaned properties:")
        print()
        print(df.to_string(index=False))
    else:
        print("✅ No orphaned properties found! All mismatches will be fixed by Day 3.")
    print()

    # Decision tree
    print("=" * 80)
    print("DECISION TREE")
    print("=" * 80)
    print()

    if pct >= 90:
        print("✅ RECOMMENDATION: PROCEED WITH DAY 3")
        print()
        print(f"Why: {pct}% of mismatches will be automatically fixed by Census rollout")
        print(f"Impact: Only {orphaned} orphaned properties need separate attention")
        print()
        print("Next Steps:")
        print("1. Proceed with Day 3 rollout (follow CHECKLIST_DAY3.md)")
        print("2. After Day 3 completes, re-run this analysis")
        print("3. Address remaining orphaned properties if needed")
    elif pct >= 50:
        print("⚠️ RECOMMENDATION: YOUR CALL")
        print()
        print(f"Why: {pct}% will be fixed, but {orphaned} orphaned properties remain")
        print()
        print("Options:")
        print("A. Proceed with Day 3 and fix orphans later")
        print("B. Investigate orphaned properties first")
        print()
        print("Consider: How critical are the orphaned properties?")
    else:
        print("🛑 RECOMMENDATION: INVESTIGATE FIRST")
        print()
        print(f"Why: Only {pct}% will be fixed, {orphaned} orphaned properties")
        print(f"Risk: Too many mismatches won't be addressed by Day 3")
        print()
        print("Next Steps:")
        print("1. Investigate why so many properties are orphaned")
        print("2. Check if Census views are missing these properties")
        print("3. Fix data issues before Day 3 rollout")

    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

finally:
    cursor.close()
    connection.close()
