-- ============================================
-- Find Properties with ONLY Identity Verification Enabled
-- ============================================
-- This query identifies properties that have identity_verification
-- as their ONLY enabled feature (true "IDV-only" properties)
-- ============================================

-- COMMAND ----------

-- Step 1: Aggregate all features per property
WITH property_feature_groups AS (
    SELECT
        pf.property_id,
        p.name as property_name,
        p.company_id,
        -- Collect all enabled feature codes
        COLLECT_SET(pf.feature_code) as enabled_features,
        -- Count of enabled features
        COUNT(DISTINCT pf.feature_code) as feature_count,
        -- List features as comma-separated string for readability
        CONCAT_WS(', ', COLLECT_LIST(pf.feature_code)) as feature_list
    FROM rds.pg_rds_public.property_features pf
    INNER JOIN rds.pg_rds_public.properties p
        ON p.id = pf.property_id
    WHERE pf.state = 'enabled'
    GROUP BY pf.property_id, p.name, p.company_id
)

-- Step 2: Find properties with ONLY IDV features
SELECT
    property_id,
    property_name,
    company_id,
    feature_count,
    feature_list
FROM property_feature_groups
WHERE
    -- Only has 1 feature enabled
    feature_count = 1
    -- And that feature is identity verification related
    AND (
        ARRAY_CONTAINS(enabled_features, 'identity_verification')
        OR ARRAY_CONTAINS(enabled_features, 'idv')
        OR feature_list LIKE '%identity%'
        OR feature_list LIKE '%idv%'
    )
ORDER BY property_name;

-- COMMAND ----------

-- Alternative: Properties with ONLY identity verification (more flexible)
-- Allows multiple IDV-related features but no other feature types
WITH property_feature_groups AS (
    SELECT
        pf.property_id,
        p.name as property_name,
        p.company_id,
        p.status,
        COLLECT_SET(pf.feature_code) as enabled_features,
        COUNT(DISTINCT pf.feature_code) as feature_count,
        CONCAT_WS(', ', COLLECT_LIST(pf.feature_code)) as feature_list,
        -- Check if any non-IDV features exist
        SUM(CASE
            WHEN pf.feature_code NOT LIKE '%identity%'
                 AND pf.feature_code NOT LIKE '%idv%'
            THEN 1
            ELSE 0
        END) as non_idv_feature_count
    FROM rds.pg_rds_public.property_features pf
    INNER JOIN rds.pg_rds_public.properties p
        ON p.id = pf.property_id
    WHERE pf.state = 'enabled'
    GROUP BY pf.property_id, p.name, p.company_id, p.status
)

SELECT
    property_id,
    property_name,
    company_id,
    status,
    feature_count,
    feature_list
FROM property_feature_groups
WHERE
    -- Has at least one IDV feature
    feature_count > 0
    -- But NO non-IDV features
    AND non_idv_feature_count = 0
ORDER BY property_name;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Detailed Analysis: All Properties with Feature Breakdown

-- COMMAND ----------

-- Show all properties grouped by feature pattern
WITH property_feature_groups AS (
    SELECT
        pf.property_id,
        p.name as property_name,
        p.company_id,
        p.status,
        COUNT(DISTINCT pf.feature_code) as feature_count,
        CONCAT_WS(', ', COLLECT_LIST(pf.feature_code)) as feature_list,
        -- Categorize property type
        CASE
            WHEN COUNT(DISTINCT pf.feature_code) = 0 THEN 'No Features'
            WHEN SUM(CASE WHEN pf.feature_code NOT LIKE '%identity%'
                              AND pf.feature_code NOT LIKE '%idv%'
                         THEN 1 ELSE 0 END) = 0
                 THEN 'IDV Only'
            ELSE 'Mixed Features'
        END as property_type
    FROM rds.pg_rds_public.properties p
    LEFT JOIN rds.pg_rds_public.property_features pf
        ON p.id = pf.property_id
        AND pf.state = 'enabled'
    WHERE p.status = 'ACTIVE'
    GROUP BY pf.property_id, p.name, p.company_id, p.status
)

SELECT
    property_type,
    COUNT(*) as property_count,
    SUM(feature_count) as total_features
FROM property_feature_groups
GROUP BY property_type
ORDER BY property_count DESC;

-- COMMAND ----------

-- Sample of each property type
WITH property_feature_groups AS (
    SELECT
        pf.property_id,
        p.name as property_name,
        p.company_id,
        p.status,
        COUNT(DISTINCT pf.feature_code) as feature_count,
        CONCAT_WS(', ', COLLECT_LIST(pf.feature_code)) as feature_list,
        CASE
            WHEN COUNT(DISTINCT pf.feature_code) = 0 THEN 'No Features'
            WHEN SUM(CASE WHEN pf.feature_code NOT LIKE '%identity%'
                              AND pf.feature_code NOT LIKE '%idv%'
                         THEN 1 ELSE 0 END) = 0
                 THEN 'IDV Only'
            ELSE 'Mixed Features'
        END as property_type
    FROM rds.pg_rds_public.properties p
    LEFT JOIN rds.pg_rds_public.property_features pf
        ON p.id = pf.property_id
        AND pf.state = 'enabled'
    WHERE p.status = 'ACTIVE'
    GROUP BY pf.property_id, p.name, p.company_id, p.status
)

SELECT
    property_type,
    property_name,
    feature_count,
    feature_list
FROM property_feature_groups
WHERE property_type = 'IDV Only'
ORDER BY property_name
LIMIT 20;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Export IDV-Only Property IDs

-- COMMAND ----------

-- Get just the property IDs for use in other queries
WITH property_feature_groups AS (
    SELECT
        pf.property_id,
        COUNT(DISTINCT pf.feature_code) as feature_count,
        SUM(CASE
            WHEN pf.feature_code NOT LIKE '%identity%'
                 AND pf.feature_code NOT LIKE '%idv%'
            THEN 1
            ELSE 0
        END) as non_idv_feature_count
    FROM rds.pg_rds_public.property_features pf
    WHERE pf.state = 'enabled'
    GROUP BY pf.property_id
)

SELECT property_id
FROM property_feature_groups
WHERE
    feature_count > 0
    AND non_idv_feature_count = 0;
