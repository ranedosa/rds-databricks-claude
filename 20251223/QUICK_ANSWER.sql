-- ============================================
-- QUICK ANSWER: Active Properties (Filtered)
-- ============================================
-- Copy and paste this directly into Databricks
-- This query excludes:
--   - IDV Only properties (using property_features table)
--   - Test/demo properties
--   - Phased buildings
-- ============================================

WITH idv_properties AS (
    -- Identify IDV-only properties from property_features table
    SELECT DISTINCT property_id
    FROM rds.pg_rds_public.property_features
    WHERE state = 'enabled'
      AND (feature_code LIKE '%idv%' OR feature_code LIKE '%identity_verification%')
)
SELECT
    COUNT(DISTINCT p.id) as active_properties,
    COUNT(DISTINCT p.company_id) as companies_with_active_properties,
    SUM(p.unit) as total_units
FROM rds.pg_rds_public.properties p
LEFT JOIN idv_properties idv
    ON idv.property_id = p.id
WHERE
    p.status = 'ACTIVE'

    -- Exclude IDV Only properties (from property_features)
    AND idv.property_id IS NULL

    -- Exclude test/demo properties
    AND LOWER(p.name) NOT LIKE '%test%'
    AND LOWER(p.name) NOT LIKE '%demo%'
    AND LOWER(p.name) NOT LIKE '%sample%'

    -- Exclude phased buildings
    AND LOWER(p.name) NOT LIKE '%phase 1%'
    AND LOWER(p.name) NOT LIKE '%phase 2%'
    AND LOWER(p.name) NOT LIKE '%phase 3%'
    AND NOT REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9]');
