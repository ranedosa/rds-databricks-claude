-- ============================================================================
-- EXPORT PILOT DATA FOR DAY 2
-- Select 50 CREATE + 50 UPDATE properties for pilot testing
-- ============================================================================

-- ============================================================================
-- PILOT SET A: 50 CREATE Properties
-- Strategy: Mix of high-priority properties with features
-- ============================================================================

SELECT
  'PILOT_CREATE' AS pilot_group,
  rds_property_id,
  sfdc_id,
  property_name,
  city,
  state,
  idv_enabled,
  bank_linking_enabled,
  payroll_enabled,
  total_feature_count,
  is_multi_property,
  CASE
    WHEN total_feature_count >= 3 THEN 'HIGH_PRIORITY'
    WHEN total_feature_count >= 1 THEN 'MEDIUM_PRIORITY'
    ELSE 'LOW_PRIORITY'
  END AS priority
FROM crm.sfdc_dbx.properties_to_create
WHERE 1=1
  -- Include diverse mix
  AND property_name IS NOT NULL
  AND city IS NOT NULL
ORDER BY
  -- Prioritize properties with features
  total_feature_count DESC,
  created_at DESC
LIMIT 50;

-- Save this result as: pilot_create_properties.csv
-- Expected: 50 properties ready for Census Sync A (CREATE)

-- ============================================================================
-- PILOT SET B: 50 UPDATE Properties
-- Strategy: Include Park Kennedy + diverse feature combinations
-- ============================================================================

SELECT
  'PILOT_UPDATE' AS pilot_group,
  rds_property_id,
  sfdc_id,
  property_name,
  city,
  state,
  idv_enabled,
  bank_linking_enabled,
  payroll_enabled,
  total_feature_count,
  is_multi_property,
  active_property_count,
  CASE
    WHEN is_multi_property = TRUE THEN 'MULTI_PROPERTY'
    WHEN total_feature_count >= 3 THEN 'HIGH_FEATURES'
    WHEN total_feature_count >= 1 THEN 'MEDIUM_FEATURES'
    ELSE 'NO_FEATURES'
  END AS test_type
FROM crm.sfdc_dbx.properties_to_update
WHERE 1=1
  AND property_name IS NOT NULL

  -- Prioritize interesting test cases
  AND (
    sfdc_id = 'a01Dn00000HHUanIAH'  -- Park Kennedy (MUST include)
    OR is_multi_property = TRUE      -- Multi-property cases
    OR total_feature_count >= 2      -- Properties with multiple features
  )

ORDER BY
  -- Park Kennedy first, then multi-property, then features
  CASE WHEN sfdc_id = 'a01Dn00000HHUanIAH' THEN 0 ELSE 1 END,
  is_multi_property DESC,
  total_feature_count DESC,
  rds_last_updated_at DESC
LIMIT 50;

-- Save this result as: pilot_update_properties.csv
-- Expected: 50 properties ready for Census Sync B (UPDATE)
-- MUST include Park Kennedy as validation case

-- ============================================================================
-- VERIFICATION: Pilot Data Summary
-- ============================================================================

WITH create_pilot AS (
  SELECT
    COUNT(*) AS create_count,
    SUM(CASE WHEN total_feature_count >= 1 THEN 1 ELSE 0 END) AS create_with_features,
    SUM(CASE WHEN is_multi_property = TRUE THEN 1 ELSE 0 END) AS create_multi_property
  FROM (
    SELECT *
    FROM crm.sfdc_dbx.properties_to_create
    WHERE property_name IS NOT NULL AND city IS NOT NULL
    ORDER BY total_feature_count DESC, created_at DESC
    LIMIT 50
  )
),
update_pilot AS (
  SELECT
    COUNT(*) AS update_count,
    SUM(CASE WHEN total_feature_count >= 1 THEN 1 ELSE 0 END) AS update_with_features,
    SUM(CASE WHEN is_multi_property = TRUE THEN 1 ELSE 0 END) AS update_multi_property,
    SUM(CASE WHEN sfdc_id = 'a01Dn00000HHUanIAH' THEN 1 ELSE 0 END) AS includes_park_kennedy
  FROM (
    SELECT *
    FROM crm.sfdc_dbx.properties_to_update
    WHERE property_name IS NOT NULL
      AND (sfdc_id = 'a01Dn00000HHUanIAH' OR is_multi_property = TRUE OR total_feature_count >= 2)
    ORDER BY
      CASE WHEN sfdc_id = 'a01Dn00000HHUanIAH' THEN 0 ELSE 1 END,
      is_multi_property DESC,
      total_feature_count DESC
    LIMIT 50
  )
)

SELECT
  'PILOT DATA SUMMARY' AS summary,
  cp.create_count,
  cp.create_with_features,
  cp.create_multi_property,
  up.update_count,
  up.update_with_features,
  up.update_multi_property,
  up.includes_park_kennedy,
  CASE
    WHEN cp.create_count = 50 AND up.update_count = 50 AND up.includes_park_kennedy = 1
    THEN '✅ READY FOR DAY 2'
    ELSE '❌ CHECK PILOT DATA'
  END AS status
FROM create_pilot cp
CROSS JOIN update_pilot up;

-- Expected:
-- - create_count: 50
-- - update_count: 50
-- - includes_park_kennedy: 1
-- - status: ✅ READY FOR DAY 2
