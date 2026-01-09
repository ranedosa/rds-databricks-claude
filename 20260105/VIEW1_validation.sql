-- ============================================================================
-- VALIDATION: View 1 - rds_properties_enriched
-- ============================================================================

-- Test 1: Basic counts and distribution
SELECT
  COUNT(*) AS total_properties,
  COUNT(DISTINCT rds_property_id) AS unique_properties,
  SUM(is_active) AS active_properties,
  SUM(has_valid_sfdc_id) AS properties_with_sfdc_id,
  SUM(CASE WHEN idv_enabled THEN 1 ELSE 0 END) AS with_idv_enabled,
  SUM(CASE WHEN bank_linking_enabled THEN 1 ELSE 0 END) AS with_bank_linking_enabled,
  COUNT(*) - COUNT(DISTINCT rds_property_id) AS potential_duplicates
FROM crm.sfdc_dbx.rds_properties_enriched;

-- Expected:
-- - total_properties: ~24,000
-- - potential_duplicates: Should be 0 (each property_id should appear once)
-- - active_properties: ~12,000-15,000
-- - properties_with_sfdc_id: ~9,000-10,000

-- Test 2: Sample 10 properties to verify data looks correct
SELECT
  rds_property_id,
  property_name,
  city,
  state,
  property_status,
  sfdc_id,
  idv_enabled,
  bank_linking_enabled
FROM crm.sfdc_dbx.rds_properties_enriched
LIMIT 10;

-- Test 3: Check for any NULL critical fields
SELECT
  COUNT(*) AS total,
  COUNT(rds_property_id) AS has_rds_id,
  COUNT(property_name) AS has_name,
  COUNT(company_id) AS has_company_id,
  COUNT(sfdc_id) AS has_sfdc_id
FROM crm.sfdc_dbx.rds_properties_enriched;
