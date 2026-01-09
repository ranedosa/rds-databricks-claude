-- ============================================================================
-- BUSINESS CASE VALIDATION
-- Run these queries to validate key business cases
-- ============================================================================

-- ============================================================================
-- CASE 1: Park Kennedy (Known Multi-Property Test Case)
-- Expected: Should show aggregated features from all active properties
-- ============================================================================

SELECT
  'CASE 1: Park Kennedy' AS test_case,
  sfdc_id,
  property_name,
  active_property_count,
  is_multi_property,
  idv_enabled,
  bank_linking_enabled,
  payroll_enabled,
  income_insights_enabled,
  document_fraud_enabled,
  total_feature_count,
  rds_property_ids_list
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
WHERE sfdc_id = 'a01Dn00000HHUanIAH';

-- Expected: Features should be TRUE if ANY active property has them enabled
-- Status: ✓ PASS / ✗ FAIL _____________

-- ============================================================================
-- CASE 2: P1 Critical Properties (Properties with Features Not in SF)
-- Expected: ~507 properties that have features enabled but missing from SF
-- ============================================================================

SELECT
  'CASE 2: P1 Critical Properties' AS test_case,
  COUNT(*) AS p1_property_count,
  SUM(CASE WHEN idv_enabled = 1 THEN 1 ELSE 0 END) AS with_idv,
  SUM(CASE WHEN bank_linking_enabled = 1 THEN 1 ELSE 0 END) AS with_bank_linking,
  SUM(CASE WHEN payroll_enabled = 1 THEN 1 ELSE 0 END) AS with_payroll
FROM crm.sfdc_dbx.properties_to_create
WHERE has_any_features_enabled = TRUE;

-- Expected: ~500-700 properties (these are P1 critical - need to be created ASAP)
-- Status: ✓ PASS / ✗ FAIL _____________

-- Sample 10 P1 properties for spot check
SELECT
  sfdc_id,
  property_name,
  city,
  state,
  idv_enabled,
  bank_linking_enabled,
  total_feature_count
FROM crm.sfdc_dbx.properties_to_create
WHERE has_any_features_enabled = TRUE
LIMIT 10;

-- Spot check: Do these properties look valid? ✓ YES / ✗ NO

-- ============================================================================
-- CASE 3: Multi-Property Cases (Blocked Properties)
-- Expected: ~1,458 SFDC IDs with multiple RDS properties
-- ============================================================================

SELECT
  'CASE 3: Multi-Property Cases' AS test_case,
  COUNT(*) AS multi_property_count,
  SUM(active_property_count) AS total_properties_aggregated,
  MAX(active_property_count) AS max_properties_per_sfdc_id,
  AVG(active_property_count) AS avg_properties_per_sfdc_id
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
WHERE is_multi_property = TRUE;

-- Expected: ~1,458 multi-property cases (from health check)
-- Status: ✓ PASS / ✗ FAIL _____________

-- Sample 20 multi-property cases for review
SELECT
  sfdc_id,
  property_name,
  active_property_count,
  total_feature_count,
  idv_enabled,
  bank_linking_enabled,
  rds_property_ids_list
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
WHERE is_multi_property = TRUE
ORDER BY active_property_count DESC
LIMIT 20;

-- Spot check: Does aggregation look correct? ✓ YES / ✗ NO

-- ============================================================================
-- CASE 4: Feature Mismatches (RDS TRUE, SF FALSE)
-- Expected: Properties where RDS has features enabled but SF doesn't
-- ============================================================================

WITH sf_features AS (
  SELECT
    sf_property_id_c AS sfdc_id,
    COALESCE(idv_enabled_c, FALSE) AS sf_idv_enabled,
    COALESCE(bank_linking_enabled_c, FALSE) AS sf_bank_linking_enabled
  FROM crm.salesforce.product_property
  WHERE is_deleted = FALSE
)

SELECT
  'CASE 4: Feature Mismatches' AS test_case,
  COUNT(*) AS mismatch_count,
  SUM(CASE WHEN agg.idv_enabled = 1 AND sf.sf_idv_enabled = FALSE THEN 1 ELSE 0 END) AS idv_mismatches,
  SUM(CASE WHEN agg.bank_linking_enabled = 1 AND sf.sf_bank_linking_enabled = FALSE THEN 1 ELSE 0 END) AS bank_linking_mismatches
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id agg
INNER JOIN sf_features sf ON agg.sfdc_id = sf.sfdc_id
WHERE (agg.idv_enabled = 1 AND sf.sf_idv_enabled = FALSE)
   OR (agg.bank_linking_enabled = 1 AND sf.sf_bank_linking_enabled = FALSE);

-- Expected: ~799 properties with feature mismatches (from original discovery)
-- Status: ✓ PASS / ✗ FAIL _____________

-- Sample 10 feature mismatches
WITH sf_features AS (
  SELECT
    sf_property_id_c AS sfdc_id,
    COALESCE(idv_enabled_c, FALSE) AS sf_idv_enabled,
    COALESCE(bank_linking_enabled_c, FALSE) AS sf_bank_linking_enabled
  FROM crm.salesforce.product_property
  WHERE is_deleted = FALSE
)

SELECT
  agg.sfdc_id,
  agg.property_name,
  agg.idv_enabled AS rds_idv,
  sf.sf_idv_enabled AS sf_idv,
  agg.bank_linking_enabled AS rds_bank_linking,
  sf.sf_bank_linking_enabled AS sf_bank_linking
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id agg
INNER JOIN sf_features sf ON agg.sfdc_id = sf.sfdc_id
WHERE (agg.idv_enabled = 1 AND sf.sf_idv_enabled = FALSE)
   OR (agg.bank_linking_enabled = 1 AND sf.sf_bank_linking_enabled = FALSE)
LIMIT 10;

-- Spot check: Mismatches look legitimate? ✓ YES / ✗ NO

-- ============================================================================
-- SUMMARY: All Business Cases
-- ============================================================================

SELECT 'BUSINESS CASE VALIDATION SUMMARY' AS summary;
SELECT '1. Park Kennedy: Check manual result above' AS case_1;
SELECT '2. P1 Properties: Expected ~500-700 with features' AS case_2;
SELECT '3. Multi-Property: Expected ~1,458 cases' AS case_3;
SELECT '4. Feature Mismatches: Expected ~799 mismatches' AS case_4;
