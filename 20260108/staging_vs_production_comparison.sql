-- ============================================================================
-- STAGING vs PRODUCTION Feature Flag Comparison
-- ============================================================================
-- This query compares feature flags between staging and production
-- to identify discrepancies
-- ============================================================================

WITH staging_features AS (
  SELECT
    property_id__c as property_id,
    property_name__c as property_name,
    ID_Verification_Enabled__c as idv_enabled,
    Bank_Linking_Enabled__c as bank_linking_enabled,
    Connected_Payroll_Enabled__c as connected_payroll_enabled,
    Income_Verification_Enabled__c as income_verification_enabled,
    Fraud_Detection_Enabled__c as fraud_detection_enabled,
    ID_Verification_Start_Date__c as idv_start_date,
    Bank_Linking_Start_Date__c as bank_linking_start_date,
    Connected_Payroll_Start_Date__c as connected_payroll_start_date
  FROM salesforce_staging.product_property__c
  WHERE property_id__c IS NOT NULL
),

production_features AS (
  SELECT
    property_id_c as property_id,
    name as property_name,
    id_verification_enabled_c as idv_enabled,
    bank_linking_enabled_c as bank_linking_enabled,
    connected_payroll_enabled_c as connected_payroll_enabled,
    income_verification_enabled_c as income_verification_enabled,
    fraud_detection_enabled_c as fraud_detection_enabled,
    idv_start_date_c as idv_start_date,
    bank_linking_start_date_c as bank_linking_start_date,
    connected_payroll_start_date_c as connected_payroll_start_date
  FROM salesforce_production.property_c
  WHERE property_id_c IS NOT NULL
)

SELECT
  COALESCE(s.property_id, p.property_id) as property_id,
  COALESCE(s.property_name, p.property_name) as property_name,

  -- Data source indicators
  CASE
    WHEN s.property_id IS NOT NULL AND p.property_id IS NOT NULL THEN 'BOTH'
    WHEN s.property_id IS NOT NULL THEN 'STAGING_ONLY'
    WHEN p.property_id IS NOT NULL THEN 'PRODUCTION_ONLY'
  END as data_source,

  -- ID Verification comparison
  s.idv_enabled as staging_idv_enabled,
  p.idv_enabled as prod_idv_enabled,
  CASE WHEN s.idv_enabled != p.idv_enabled THEN '⚠️ MISMATCH' ELSE '✅ MATCH' END as idv_status,

  -- Bank Linking comparison
  s.bank_linking_enabled as staging_bank_linking,
  p.bank_linking_enabled as prod_bank_linking,
  CASE WHEN s.bank_linking_enabled != p.bank_linking_enabled THEN '⚠️ MISMATCH' ELSE '✅ MATCH' END as bank_linking_status,

  -- Connected Payroll comparison
  s.connected_payroll_enabled as staging_connected_payroll,
  p.connected_payroll_enabled as prod_connected_payroll,
  CASE WHEN s.connected_payroll_enabled != p.connected_payroll_enabled THEN '⚠️ MISMATCH' ELSE '✅ MATCH' END as connected_payroll_status,

  -- Income Verification comparison
  s.income_verification_enabled as staging_income_verification,
  p.income_verification_enabled as prod_income_verification,
  CASE WHEN s.income_verification_enabled != p.income_verification_enabled THEN '⚠️ MISMATCH' ELSE '✅ MATCH' END as income_verification_status,

  -- Fraud Detection comparison
  s.fraud_detection_enabled as staging_fraud_detection,
  p.fraud_detection_enabled as prod_fraud_detection,
  CASE WHEN s.fraud_detection_enabled != p.fraud_detection_enabled THEN '⚠️ MISMATCH' ELSE '✅ MATCH' END as fraud_detection_status,

  -- Start Dates comparison
  s.idv_start_date as staging_idv_start_date,
  p.idv_start_date as prod_idv_start_date,
  s.bank_linking_start_date as staging_bank_linking_start_date,
  p.bank_linking_start_date as prod_bank_linking_start_date,
  s.connected_payroll_start_date as staging_connected_payroll_start_date,
  p.connected_payroll_start_date as prod_connected_payroll_start_date

FROM staging_features s
FULL OUTER JOIN production_features p ON s.property_id = p.property_id
ORDER BY
  CASE
    WHEN s.property_id IS NOT NULL AND p.property_id IS NULL THEN 1
    WHEN s.property_id IS NULL AND p.property_id IS NOT NULL THEN 2
    WHEN s.idv_enabled != p.idv_enabled THEN 3
    WHEN s.bank_linking_enabled != p.bank_linking_enabled THEN 4
    WHEN s.connected_payroll_enabled != p.connected_payroll_enabled THEN 5
    ELSE 6
  END,
  property_id;


-- ============================================================================
-- SUMMARY: Discrepancy Counts
-- ============================================================================

WITH staging_features AS (
  SELECT
    property_id__c as property_id,
    ID_Verification_Enabled__c as idv_enabled,
    Bank_Linking_Enabled__c as bank_linking_enabled,
    Connected_Payroll_Enabled__c as connected_payroll_enabled,
    Income_Verification_Enabled__c as income_verification_enabled,
    Fraud_Detection_Enabled__c as fraud_detection_enabled
  FROM salesforce_staging.product_property__c
  WHERE property_id__c IS NOT NULL
),

production_features AS (
  SELECT
    property_id_c as property_id,
    id_verification_enabled_c as idv_enabled,
    bank_linking_enabled_c as bank_linking_enabled,
    connected_payroll_enabled_c as connected_payroll_enabled,
    income_verification_enabled_c as income_verification_enabled,
    fraud_detection_enabled_c as fraud_detection_enabled
  FROM salesforce_production.property_c
  WHERE property_id_c IS NOT NULL
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
WHERE s.fraud_detection_enabled != p.fraud_detection_enabled;


-- ============================================================================
-- MISMATCH DETAILS: Show only properties with discrepancies
-- ============================================================================

WITH staging_features AS (
  SELECT
    property_id__c as property_id,
    property_name__c as property_name,
    ID_Verification_Enabled__c as idv_enabled,
    Bank_Linking_Enabled__c as bank_linking_enabled,
    Connected_Payroll_Enabled__c as connected_payroll_enabled,
    Income_Verification_Enabled__c as income_verification_enabled,
    Fraud_Detection_Enabled__c as fraud_detection_enabled
  FROM salesforce_staging.product_property__c
  WHERE property_id__c IS NOT NULL
),

production_features AS (
  SELECT
    property_id_c as property_id,
    name as property_name,
    id_verification_enabled_c as idv_enabled,
    bank_linking_enabled_c as bank_linking_enabled,
    connected_payroll_enabled_c as connected_payroll_enabled,
    income_verification_enabled_c as income_verification_enabled,
    fraud_detection_enabled_c as fraud_detection_enabled
  FROM salesforce_production.property_c
  WHERE property_id_c IS NOT NULL
)

SELECT
  s.property_id,
  s.property_name,

  -- Show which flags have mismatches
  CASE WHEN s.idv_enabled != p.idv_enabled
    THEN CONCAT('IDV: ', CAST(s.idv_enabled AS STRING), ' → ', CAST(p.idv_enabled AS STRING))
    ELSE NULL
  END as idv_mismatch,

  CASE WHEN s.bank_linking_enabled != p.bank_linking_enabled
    THEN CONCAT('Bank: ', CAST(s.bank_linking_enabled AS STRING), ' → ', CAST(p.bank_linking_enabled AS STRING))
    ELSE NULL
  END as bank_mismatch,

  CASE WHEN s.connected_payroll_enabled != p.connected_payroll_enabled
    THEN CONCAT('Payroll: ', CAST(s.connected_payroll_enabled AS STRING), ' → ', CAST(p.connected_payroll_enabled AS STRING))
    ELSE NULL
  END as payroll_mismatch,

  CASE WHEN s.income_verification_enabled != p.income_verification_enabled
    THEN CONCAT('Income: ', CAST(s.income_verification_enabled AS STRING), ' → ', CAST(p.income_verification_enabled AS STRING))
    ELSE NULL
  END as income_mismatch,

  CASE WHEN s.fraud_detection_enabled != p.fraud_detection_enabled
    THEN CONCAT('Fraud: ', CAST(s.fraud_detection_enabled AS STRING), ' → ', CAST(p.fraud_detection_enabled AS STRING))
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
ORDER BY s.property_name;
