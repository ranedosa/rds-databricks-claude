-- ============================================
-- FINAL ANSWER: Active Properties (Comprehensive Filtering)
-- ============================================
-- This is the most comprehensive and accurate query
--
-- Excludes:
--   1. IDV-only properties (from property_features)
--   2. Test/demo/staging properties (comprehensive patterns)
--   3. Phased buildings
-- ============================================

WITH idv_only_properties AS (
    -- Properties that have ONLY IDV features (no other features)
    SELECT property_id
    FROM (
        SELECT
            property_id,
            COUNT(DISTINCT feature_code) as feature_count,
            SUM(CASE
                WHEN feature_code NOT LIKE '%identity%'
                     AND feature_code NOT LIKE '%idv%'
                THEN 1 ELSE 0
            END) as non_idv_feature_count
        FROM rds.pg_rds_public.property_features
        WHERE state = 'enabled'
        GROUP BY property_id
    )
    WHERE feature_count > 0 AND non_idv_feature_count = 0
),
test_properties AS (
    -- Comprehensive test/demo/staging property detection
    SELECT DISTINCT p.id as property_id
    FROM rds.pg_rds_public.properties p
    WHERE
        -- Core test keywords
        LOWER(p.name) LIKE '%test%'
        OR LOWER(p.name) LIKE '%demo%'
        OR LOWER(p.name) LIKE '%sample%'

        -- Development/staging keywords
        OR LOWER(p.name) LIKE '%staging%'
        OR LOWER(p.name) LIKE '%qa%'
        OR LOWER(p.name) LIKE '%dev%'
        OR LOWER(p.name) LIKE '%sandbox%'

        -- Training/temporary keywords
        OR LOWER(p.name) LIKE '%training%'
        OR LOWER(p.name) LIKE '%dummy%'
        OR LOWER(p.name) LIKE '%fake%'
        OR LOWER(p.name) LIKE '%temporary%'

        -- Action keywords
        OR LOWER(p.name) LIKE '%do not%'
        OR LOWER(p.name) LIKE '%delete%'
        OR LOWER(p.name) LIKE '%remove%'

        -- Pattern-based detection
        OR REGEXP_LIKE(LOWER(p.name), '^test[_\\s-]')
        OR REGEXP_LIKE(LOWER(p.name), '^demo[_\\s-]')
        OR REGEXP_LIKE(LOWER(p.name), '[_\\s-]test$')
        OR REGEXP_LIKE(LOWER(p.name), '[_\\s-]demo$')
),
phased_properties AS (
    -- OLD phases only (not latest phase) - these are the duplicates to exclude
    SELECT property_id
    FROM (
        SELECT
            p.id as property_id,
            CASE
                WHEN LOWER(p.name) LIKE '%phase 1%' THEN 1
                WHEN LOWER(p.name) LIKE '%phase 2%' THEN 2
                WHEN LOWER(p.name) LIKE '%phase 3%' THEN 3
                WHEN LOWER(p.name) LIKE '%phase 4%' THEN 4
                WHEN REGEXP_LIKE(LOWER(p.name), 'phase\\s*([0-9]+)') THEN
                    CAST(REGEXP_EXTRACT(LOWER(p.name), 'phase\\s*([0-9]+)', 1) AS INT)
                ELSE 0
            END as phase_number,
            TRIM(REGEXP_REPLACE(
                REGEXP_REPLACE(LOWER(p.name), 'phase\\s*[0-9ivx]+', '', 1),
                '[^a-z0-9]',
                ''
            )) as base_identifier
        FROM rds.pg_rds_public.properties p
        WHERE LOWER(p.name) LIKE '%phase%'
    ) phases
    WHERE base_identifier != ''
      AND phase_number > 0
      -- Only select old phases (not the latest)
      AND phase_number < (
          SELECT MAX(CASE
              WHEN LOWER(p2.name) LIKE '%phase 1%' THEN 1
              WHEN LOWER(p2.name) LIKE '%phase 2%' THEN 2
              WHEN LOWER(p2.name) LIKE '%phase 3%' THEN 3
              WHEN LOWER(p2.name) LIKE '%phase 4%' THEN 4
              WHEN REGEXP_LIKE(LOWER(p2.name), 'phase\\s*([0-9]+)') THEN
                  CAST(REGEXP_EXTRACT(LOWER(p2.name), 'phase\\s*([0-9]+)', 1) AS INT)
              ELSE 0
          END)
          FROM rds.pg_rds_public.properties p2
          WHERE TRIM(REGEXP_REPLACE(
              REGEXP_REPLACE(LOWER(p2.name), 'phase\\s*[0-9ivx]+', '', 1),
              '[^a-z0-9]',
              ''
          )) = phases.base_identifier
      )
)

-- Final count excluding all identified properties
SELECT
    COUNT(DISTINCT p.id) as active_properties,
    COUNT(DISTINCT p.company_id) as companies_with_active_properties,
    SUM(p.unit) as total_units
FROM rds.pg_rds_public.properties p
LEFT JOIN idv_only_properties idv ON idv.property_id = p.id
LEFT JOIN test_properties test ON test.property_id = p.id
LEFT JOIN phased_properties phased ON phased.property_id = p.id
WHERE
    p.status = 'ACTIVE'
    AND idv.property_id IS NULL      -- Exclude IDV-only
    AND test.property_id IS NULL      -- Exclude test properties
    AND phased.property_id IS NULL;   -- Exclude phased buildings

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Breakdown: What Was Excluded?

-- COMMAND ----------

-- Show counts for each exclusion category
WITH idv_only_properties AS (
    SELECT property_id
    FROM (
        SELECT
            property_id,
            COUNT(DISTINCT feature_code) as feature_count,
            SUM(CASE WHEN feature_code NOT LIKE '%identity%' AND feature_code NOT LIKE '%idv%'
                THEN 1 ELSE 0 END) as non_idv_feature_count
        FROM rds.pg_rds_public.property_features
        WHERE state = 'enabled'
        GROUP BY property_id
    )
    WHERE feature_count > 0 AND non_idv_feature_count = 0
),
test_properties AS (
    SELECT DISTINCT p.id as property_id
    FROM rds.pg_rds_public.properties p
    WHERE
        LOWER(p.name) LIKE '%test%' OR LOWER(p.name) LIKE '%demo%'
        OR LOWER(p.name) LIKE '%sample%' OR LOWER(p.name) LIKE '%staging%'
        OR LOWER(p.name) LIKE '%qa%' OR LOWER(p.name) LIKE '%dev%'
        OR LOWER(p.name) LIKE '%sandbox%' OR LOWER(p.name) LIKE '%training%'
        OR LOWER(p.name) LIKE '%dummy%' OR LOWER(p.name) LIKE '%fake%'
),
phased_properties AS (
    SELECT DISTINCT p.id as property_id
    FROM rds.pg_rds_public.properties p
    WHERE REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9]')
)

SELECT
    'Total Active Properties' as category,
    COUNT(DISTINCT p.id) as count
FROM rds.pg_rds_public.properties p
WHERE p.status = 'ACTIVE'

UNION ALL

SELECT 'Excluded: IDV Only' as category, COUNT(*) as count
FROM idv_only_properties

UNION ALL

SELECT 'Excluded: Test/Demo/Staging' as category, COUNT(*) as count
FROM test_properties

UNION ALL

SELECT 'Excluded: Phased Buildings' as category, COUNT(*) as count
FROM phased_properties

UNION ALL

SELECT
    'Final Count (After Exclusions)' as category,
    COUNT(DISTINCT p.id) as count
FROM rds.pg_rds_public.properties p
LEFT JOIN idv_only_properties idv ON idv.property_id = p.id
LEFT JOIN test_properties test ON test.property_id = p.id
LEFT JOIN phased_properties phased ON phased.property_id = p.id
WHERE
    p.status = 'ACTIVE'
    AND idv.property_id IS NULL
    AND test.property_id IS NULL
    AND phased.property_id IS NULL

ORDER BY
    CASE category
        WHEN 'Total Active Properties' THEN 1
        WHEN 'Excluded: IDV Only' THEN 2
        WHEN 'Excluded: Test/Demo/Staging' THEN 3
        WHEN 'Excluded: Phased Buildings' THEN 4
        WHEN 'Final Count (After Exclusions)' THEN 5
    END;
