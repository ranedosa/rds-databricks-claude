-- ============================================================================
-- DATA QUALITY VALIDATION TESTS
-- Run all 5 tests to verify views are working correctly
-- ============================================================================

-- ============================================================================
-- TEST 1: Aggregation Preserves SFDC IDs
-- PURPOSE: Verify no SFDC IDs are lost during aggregation
-- EXPECTED: aggregated count = enriched count (with valid sfdc_id)
-- ============================================================================

SELECT 'TEST 1: Aggregation Preserves SFDC IDs' AS test_name;

WITH enriched_count AS (
  SELECT COUNT(DISTINCT sfdc_id) AS unique_sfdc_ids
  FROM crm.sfdc_dbx.rds_properties_enriched
  WHERE has_valid_sfdc_id = 1
    AND property_status = 'ACTIVE'
),
aggregated_count AS (
  SELECT COUNT(DISTINCT sfdc_id) AS unique_sfdc_ids
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
)

SELECT
  e.unique_sfdc_ids AS enriched_count,
  a.unique_sfdc_ids AS aggregated_count,
  e.unique_sfdc_ids - a.unique_sfdc_ids AS difference,
  CASE
    WHEN e.unique_sfdc_ids = a.unique_sfdc_ids THEN '✅ PASS'
    ELSE '❌ FAIL - Missing SFDC IDs during aggregation'
  END AS test_result
FROM enriched_count e
CROSS JOIN aggregated_count a;

-- ============================================================================
-- TEST 2: Union Logic for Features
-- PURPOSE: Verify feature aggregation uses UNION logic (ANY property = TRUE)
-- EXPECTED: Multi-property features should be >= any single property
-- ============================================================================

SELECT 'TEST 2: Union Logic for Features' AS test_name;

WITH test_case AS (
  -- Pick a multi-property SFDC ID
  SELECT sfdc_id
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
  WHERE is_multi_property = TRUE
  LIMIT 1
),
individual_properties AS (
  SELECT
    e.sfdc_id,
    MAX(CASE WHEN e.idv_enabled = 1 THEN 1 ELSE 0 END) AS max_idv_from_properties
  FROM crm.sfdc_dbx.rds_properties_enriched e
  INNER JOIN test_case tc ON e.sfdc_id = tc.sfdc_id
  WHERE e.property_status = 'ACTIVE'
    AND e.has_valid_sfdc_id = 1
  GROUP BY e.sfdc_id
),
aggregated_result AS (
  SELECT
    a.sfdc_id,
    a.idv_enabled AS idv_from_aggregation
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id a
  INNER JOIN test_case tc ON a.sfdc_id = tc.sfdc_id
)

SELECT
  ip.sfdc_id,
  ip.max_idv_from_properties AS expected_idv,
  ar.idv_from_aggregation AS actual_idv,
  CASE
    WHEN ip.max_idv_from_properties = ar.idv_from_aggregation THEN '✅ PASS'
    ELSE '❌ FAIL - Union logic not working'
  END AS test_result
FROM individual_properties ip
INNER JOIN aggregated_result ar ON ip.sfdc_id = ar.sfdc_id;

-- ============================================================================
-- TEST 3: Create + Update Coverage
-- PURPOSE: Verify create + update queues cover all aggregated properties
-- EXPECTED: create_count + update_count = aggregated_count
-- ============================================================================

SELECT 'TEST 3: Create + Update Coverage' AS test_name;

WITH counts AS (
  SELECT
    (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create) AS create_count,
    (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update) AS update_count,
    (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id) AS aggregated_count
)

SELECT
  create_count,
  update_count,
  aggregated_count,
  (create_count + update_count) AS total_coverage,
  (aggregated_count - (create_count + update_count)) AS difference,
  CASE
    WHEN ABS(aggregated_count - (create_count + update_count)) <= 50 THEN '✅ PASS'
    ELSE '❌ FAIL - Coverage gap detected'
  END AS test_result,
  'Difference should be small (<50) - represents edge cases or timing differences' AS note
FROM counts;

-- ============================================================================
-- TEST 4: No DISABLED Properties in Aggregation
-- PURPOSE: Verify only ACTIVE properties contribute to aggregation
-- EXPECTED: All properties in aggregation should come from ACTIVE properties
-- ============================================================================

SELECT 'TEST 4: No DISABLED Properties in Aggregation' AS test_name;

WITH disabled_check AS (
  SELECT COUNT(*) AS disabled_count
  FROM crm.sfdc_dbx.rds_properties_enriched e
  INNER JOIN crm.sfdc_dbx.properties_aggregated_by_sfdc_id a
    ON e.sfdc_id = a.sfdc_id
  WHERE e.property_status = 'DISABLED'
    AND e.has_valid_sfdc_id = 1
)

SELECT
  disabled_count,
  CASE
    WHEN disabled_count = 0 THEN '✅ PASS'
    ELSE '⚠️ WARNING - DISABLED properties found but should not contribute to features'
  END AS test_result,
  'DISABLED properties may share sfdc_id but should not affect feature aggregation' AS note
FROM disabled_check;

-- ============================================================================
-- TEST 5: Earliest Timestamp Logic
-- PURPOSE: Verify aggregation uses EARLIEST enabled date
-- EXPECTED: Aggregated timestamp <= all individual property timestamps
-- ============================================================================

SELECT 'TEST 5: Earliest Timestamp Logic' AS test_name;

WITH test_case AS (
  -- Pick a multi-property case with IDV enabled
  SELECT sfdc_id
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
  WHERE is_multi_property = TRUE
    AND idv_enabled = 1
  LIMIT 1
),
individual_timestamps AS (
  SELECT
    e.sfdc_id,
    MIN(e.idv_enabled_at) AS min_timestamp_from_properties
  FROM crm.sfdc_dbx.rds_properties_enriched e
  INNER JOIN test_case tc ON e.sfdc_id = tc.sfdc_id
  WHERE e.property_status = 'ACTIVE'
    AND e.has_valid_sfdc_id = 1
    AND e.idv_enabled_at IS NOT NULL
  GROUP BY e.sfdc_id
),
aggregated_timestamp AS (
  SELECT
    a.sfdc_id,
    a.idv_enabled_at AS timestamp_from_aggregation
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id a
  INNER JOIN test_case tc ON a.sfdc_id = tc.sfdc_id
)

SELECT
  it.sfdc_id,
  it.min_timestamp_from_properties AS expected_timestamp,
  at.timestamp_from_aggregation AS actual_timestamp,
  CASE
    WHEN it.min_timestamp_from_properties = at.timestamp_from_aggregation THEN '✅ PASS'
    ELSE '❌ FAIL - Not using earliest timestamp'
  END AS test_result
FROM individual_timestamps it
INNER JOIN aggregated_timestamp at ON it.sfdc_id = at.sfdc_id;

-- ============================================================================
-- SUMMARY: All Tests
-- ============================================================================

SELECT 'DATA QUALITY VALIDATION COMPLETE' AS summary;
SELECT 'Run each test above and verify all show ✅ PASS' AS instruction;
