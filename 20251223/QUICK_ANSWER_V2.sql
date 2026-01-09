-- ============================================
-- QUICK ANSWER V2: Active Properties (Filtered)
-- ============================================
-- Improved IDV detection: Finds properties that ONLY have
-- identity_verification enabled (no other features)
-- ============================================

WITH idv_only_properties AS (
    -- Find properties that have ONLY IDV features enabled (no other features)
    SELECT property_id
    FROM (
        SELECT
            property_id,
            -- Count total enabled features
            COUNT(DISTINCT feature_code) as feature_count,
            -- Count non-IDV features
            SUM(CASE
                WHEN feature_code NOT LIKE '%identity%'
                     AND feature_code NOT LIKE '%idv%'
                THEN 1
                ELSE 0
            END) as non_idv_feature_count
        FROM rds.pg_rds_public.property_features
        WHERE state = 'enabled'
        GROUP BY property_id
    )
    WHERE
        feature_count > 0           -- Has at least one feature
        AND non_idv_feature_count = 0  -- But NO non-IDV features
)
SELECT
    COUNT(DISTINCT p.id) as active_properties,
    COUNT(DISTINCT p.company_id) as companies_with_active_properties,
    SUM(p.unit) as total_units
FROM rds.pg_rds_public.properties p
LEFT JOIN idv_only_properties idv
    ON idv.property_id = p.id
WHERE
    p.status = 'ACTIVE'

    -- Exclude IDV-only properties (properties with ONLY identity verification)
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
