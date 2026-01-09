-- ============================================================================
-- VALIDATION: View 2 - properties_aggregated_by_sfdc_id
-- ============================================================================

-- Test 1: Aggregation distribution (how many SFDC IDs have multiple properties?)
SELECT
  active_property_count,
  COUNT(*) AS sfdc_id_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
GROUP BY active_property_count
ORDER BY active_property_count;

-- Expected:
-- - Most should be count=1 (single property per SFDC ID)
-- - Some count=2, 3, 4+ (multi-property cases like Park Kennedy)
-- - Example: 7000 count=1, 1500 count=2, 100 count=3+

-- Test 2: Multi-property statistics
SELECT
  COUNT(*) AS total_sfdc_ids,
  SUM(CASE WHEN is_multi_property THEN 1 ELSE 0 END) AS multi_property_count,
  SUM(CASE WHEN active_property_count >= 3 THEN 1 ELSE 0 END) AS three_plus_properties,
  MAX(active_property_count) AS max_properties_per_sfdc_id
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id;

-- Expected:
-- - multi_property_count: ~1,500-2,500 (matches our 2,410 blocked properties estimate)

-- Test 3: Feature distribution
SELECT
  COUNT(*) AS total,
  SUM(CASE WHEN idv_enabled = 1 THEN 1 ELSE 0 END) AS idv_enabled_count,
  SUM(CASE WHEN bank_linking_enabled = 1 THEN 1 ELSE 0 END) AS bank_linking_count,
  SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS any_features_count
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id;

-- Test 4: Park Kennedy validation (CRITICAL!)
-- This is our canary - if this fails, aggregation is broken
SELECT
  sfdc_id,
  property_name,
  active_property_count,
  is_multi_property,
  idv_enabled,
  bank_linking_enabled,
  total_feature_count,
  rds_property_ids_list
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
WHERE sfdc_id = 'a01Dn00000HHUanIAH';

-- Expected for Park Kennedy:
-- - active_property_count: 2+ (multiple properties)
-- - is_multi_property: TRUE
-- - idv_enabled: 1 (TRUE)
-- - bank_linking_enabled: 1 (TRUE)
-- - Should show list of RDS property IDs
