-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Active Properties Analysis - SQL Only Version
-- MAGIC
-- MAGIC ## Objective
-- MAGIC Count active properties, companies, and units while excluding:
-- MAGIC - IDV Only properties (duplicates)
-- MAGIC - Test/demo properties
-- MAGIC - Phased buildings (e.g., "Phase 1", "Phase 2")
-- MAGIC
-- MAGIC **Note**: This version assumes you've already loaded the Customer Log CSV
-- MAGIC into a Delta table called `customer_log` in your catalog

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Option 1: If Customer Log is Already in Delta Table
-- MAGIC **Best Approach**: Uses SFDC ID for reliable joins

-- COMMAND ----------

-- Final query with all exclusions using SFDC ID join
WITH idv_properties AS (
    -- Identify IDV-only properties from property_features
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
INNER JOIN rds.pg_rds_public.customer_log cl
    ON p.sfdc_id = cl.sfdc_property_id  -- Use SFDC ID for reliable matching
LEFT JOIN idv_properties idv
    ON idv.property_id = p.id
WHERE
    p.status = 'ACTIVE'
    AND cl.status = 'Live'
    AND cl.sfdc_property_id IS NOT NULL
    AND cl.sfdc_property_id != ''

    -- Exclude IDV Only properties (using property_features table)
    AND idv.property_id IS NULL

    -- Exclude test/demo properties
    AND LOWER(p.name) NOT LIKE '%test%'
    AND LOWER(p.name) NOT LIKE '%demo%'
    AND LOWER(p.name) NOT LIKE '%sample%'

    -- Exclude phased buildings
    AND LOWER(p.name) NOT LIKE '%phase 1%'
    AND LOWER(p.name) NOT LIKE '%phase 2%'
    AND LOWER(p.name) NOT LIKE '%phase 3%'
    AND NOT REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9]')
;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Option 2: Simplified Version (Without Customer Log Join)
-- MAGIC Use this if you want to exclude based on naming patterns only

-- COMMAND ----------

-- Simplified query - excludes using property_features and name patterns
WITH idv_properties AS (
    -- Identify IDV-only properties from property_features
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

    -- Exclude IDV Only properties (using property_features table)
    AND idv.property_id IS NULL

    -- Exclude test/demo properties
    AND LOWER(p.name) NOT LIKE '%test%'
    AND LOWER(p.name) NOT LIKE '%demo%'
    AND LOWER(p.name) NOT LIKE '%sample%'

    -- Exclude phased buildings
    AND LOWER(p.name) NOT LIKE '%phase 1%'
    AND LOWER(p.name) NOT LIKE '%phase 2%'
    AND LOWER(p.name) NOT LIKE '%phase 3%'
    AND NOT REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9]')
;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Comparison: Before and After Filtering

-- COMMAND ----------

-- Side by side comparison
WITH idv_properties AS (
    SELECT DISTINCT property_id
    FROM rds.pg_rds_public.property_features
    WHERE state = 'enabled'
      AND (feature_code LIKE '%idv%' OR feature_code LIKE '%identity_verification%')
),
original AS (
    SELECT
        'Before Filtering' as metric_type,
        COUNT(DISTINCT p.id) as active_properties,
        COUNT(DISTINCT p.company_id) as companies_with_active_properties,
        SUM(p.unit) as total_units
    FROM rds.pg_rds_public.properties p
    WHERE p.status = 'ACTIVE'
),
filtered AS (
    SELECT
        'After Filtering' as metric_type,
        COUNT(DISTINCT p.id) as active_properties,
        COUNT(DISTINCT p.company_id) as companies_with_active_properties,
        SUM(p.unit) as total_units
    FROM rds.pg_rds_public.properties p
    LEFT JOIN idv_properties idv ON idv.property_id = p.id
    WHERE
        p.status = 'ACTIVE'
        AND idv.property_id IS NULL
        AND LOWER(p.name) NOT LIKE '%test%'
        AND LOWER(p.name) NOT LIKE '%demo%'
        AND LOWER(p.name) NOT LIKE '%sample%'
        AND LOWER(p.name) NOT LIKE '%phase 1%'
        AND LOWER(p.name) NOT LIKE '%phase 2%'
        AND LOWER(p.name) NOT LIKE '%phase 3%'
        AND NOT REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9]')
),
delta AS (
    SELECT
        'Delta (Excluded)' as metric_type,
        o.active_properties - f.active_properties as active_properties,
        o.companies_with_active_properties - f.companies_with_active_properties as companies_with_active_properties,
        o.total_units - f.total_units as total_units
    FROM original o
    CROSS JOIN filtered f
)

SELECT * FROM original
UNION ALL
SELECT * FROM filtered
UNION ALL
SELECT * FROM delta
ORDER BY
    CASE metric_type
        WHEN 'Before Filtering' THEN 1
        WHEN 'After Filtering' THEN 2
        WHEN 'Delta (Excluded)' THEN 3
    END;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Detailed View: What Properties Were Excluded?

-- COMMAND ----------

-- Show excluded properties with reasons
WITH idv_properties AS (
    SELECT DISTINCT property_id
    FROM rds.pg_rds_public.property_features
    WHERE state = 'enabled'
      AND (feature_code LIKE '%idv%' OR feature_code LIKE '%identity_verification%')
),
excluded_properties AS (
    SELECT
        p.id,
        p.name,
        p.company_id,
        p.unit,
        CASE
            WHEN idv.property_id IS NOT NULL
                THEN 'IDV Only (from property_features)'
            WHEN LOWER(p.name) LIKE '%test%' OR LOWER(p.name) LIKE '%demo%' OR LOWER(p.name) LIKE '%sample%'
                THEN 'Test/Demo'
            WHEN REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9]')
                THEN 'Phased Building'
            ELSE 'Other Pattern'
        END as exclusion_reason
    FROM rds.pg_rds_public.properties p
    LEFT JOIN idv_properties idv ON idv.property_id = p.id
    WHERE
        p.status = 'ACTIVE'
        AND (
            idv.property_id IS NOT NULL
            OR LOWER(p.name) LIKE '%test%'
            OR LOWER(p.name) LIKE '%demo%'
            OR LOWER(p.name) LIKE '%sample%'
            OR REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9]')
        )
)

SELECT
    exclusion_reason,
    COUNT(*) as excluded_count,
    SUM(unit) as excluded_units
FROM excluded_properties
GROUP BY exclusion_reason
ORDER BY excluded_count DESC;

-- COMMAND ----------

-- View sample of excluded properties
WITH idv_properties AS (
    SELECT DISTINCT property_id
    FROM rds.pg_rds_public.property_features
    WHERE state = 'enabled'
      AND (feature_code LIKE '%idv%' OR feature_code LIKE '%identity_verification%')
)
SELECT
    p.name,
    p.company_id,
    p.unit,
    p.status,
    CASE
        WHEN idv.property_id IS NOT NULL
            THEN 'IDV Only (from property_features)'
        WHEN LOWER(p.name) LIKE '%test%' OR LOWER(p.name) LIKE '%demo%' OR LOWER(p.name) LIKE '%sample%'
            THEN 'Test/Demo'
        WHEN REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9]')
            THEN 'Phased Building'
        ELSE 'Other Pattern'
    END as exclusion_reason
FROM rds.pg_rds_public.properties p
LEFT JOIN idv_properties idv ON idv.property_id = p.id
WHERE
    p.status = 'ACTIVE'
    AND (
        idv.property_id IS NOT NULL
        OR LOWER(p.name) LIKE '%test%'
        OR LOWER(p.name) LIKE '%demo%'
        OR LOWER(p.name) LIKE '%sample%'
        OR REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9]')
    )
ORDER BY exclusion_reason, p.name
LIMIT 100;
