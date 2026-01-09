-- ============================================
-- Find ALL Test/Demo/Sample Properties
-- ============================================
-- Comprehensive search across properties table
-- to identify any testing-related properties
-- ============================================

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Comprehensive Test Property Detection

-- COMMAND ----------

-- Main query: Find all test properties using multiple detection methods
WITH test_properties_by_method AS (
    SELECT DISTINCT
        p.id as property_id,
        p.name as property_name,
        p.company_id,
        p.status,
        p.created_at,
        p.updated_at,
        -- Categorize by detection method
        CASE
            -- Name-based detection (most common)
            WHEN LOWER(p.name) LIKE '%test%' THEN 'Name contains "test"'
            WHEN LOWER(p.name) LIKE '%demo%' THEN 'Name contains "demo"'
            WHEN LOWER(p.name) LIKE '%sample%' THEN 'Name contains "sample"'
            WHEN LOWER(p.name) LIKE '%staging%' THEN 'Name contains "staging"'
            WHEN LOWER(p.name) LIKE '%qa%' THEN 'Name contains "qa"'
            WHEN LOWER(p.name) LIKE '%dev%' THEN 'Name contains "dev"'
            WHEN LOWER(p.name) LIKE '%training%' THEN 'Name contains "training"'
            WHEN LOWER(p.name) LIKE '%dummy%' THEN 'Name contains "dummy"'
            WHEN LOWER(p.name) LIKE '%fake%' THEN 'Name contains "fake"'
            WHEN LOWER(p.name) LIKE '%sandbox%' THEN 'Name contains "sandbox"'

            -- Pattern-based detection
            WHEN REGEXP_LIKE(LOWER(p.name), '^test[_\\s-]') THEN 'Starts with "test"'
            WHEN REGEXP_LIKE(LOWER(p.name), '^demo[_\\s-]') THEN 'Starts with "demo"'
            WHEN REGEXP_LIKE(LOWER(p.name), '[_\\s-]test$') THEN 'Ends with "test"'
            WHEN REGEXP_LIKE(LOWER(p.name), '[_\\s-]demo$') THEN 'Ends with "demo"'

            -- Common test property patterns
            WHEN LOWER(p.name) LIKE '%test property%' THEN 'Generic test property'
            WHEN LOWER(p.name) LIKE '%do not%' THEN 'Name contains "do not"'
            WHEN LOWER(p.name) LIKE '%delete%' THEN 'Name contains "delete"'
            WHEN LOWER(p.name) LIKE '%remove%' THEN 'Name contains "remove"'

            ELSE 'Other pattern'
        END as detection_method
    FROM rds.pg_rds_public.properties p
    WHERE
        -- Name pattern matching
        LOWER(p.name) LIKE '%test%'
        OR LOWER(p.name) LIKE '%demo%'
        OR LOWER(p.name) LIKE '%sample%'
        OR LOWER(p.name) LIKE '%staging%'
        OR LOWER(p.name) LIKE '%qa%'
        OR LOWER(p.name) LIKE '%dev%'
        OR LOWER(p.name) LIKE '%training%'
        OR LOWER(p.name) LIKE '%dummy%'
        OR LOWER(p.name) LIKE '%fake%'
        OR LOWER(p.name) LIKE '%sandbox%'
        OR LOWER(p.name) LIKE '%do not%'
        OR LOWER(p.name) LIKE '%delete%'
        OR LOWER(p.name) LIKE '%remove%'

        -- Pattern-based
        OR REGEXP_LIKE(LOWER(p.name), '^test[_\\s-]')
        OR REGEXP_LIKE(LOWER(p.name), '^demo[_\\s-]')
        OR REGEXP_LIKE(LOWER(p.name), '[_\\s-]test$')
        OR REGEXP_LIKE(LOWER(p.name), '[_\\s-]demo$')
)

SELECT
    property_id,
    property_name,
    company_id,
    status,
    detection_method,
    created_at,
    updated_at
FROM test_properties_by_method
ORDER BY detection_method, property_name;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Summary Statistics

-- COMMAND ----------

-- Count by detection method
WITH test_properties AS (
    SELECT DISTINCT
        p.id as property_id,
        CASE
            WHEN LOWER(p.name) LIKE '%test%' THEN 'test'
            WHEN LOWER(p.name) LIKE '%demo%' THEN 'demo'
            WHEN LOWER(p.name) LIKE '%sample%' THEN 'sample'
            WHEN LOWER(p.name) LIKE '%staging%' THEN 'staging'
            WHEN LOWER(p.name) LIKE '%qa%' THEN 'qa'
            WHEN LOWER(p.name) LIKE '%dev%' THEN 'dev'
            WHEN LOWER(p.name) LIKE '%training%' THEN 'training'
            WHEN LOWER(p.name) LIKE '%dummy%' THEN 'dummy'
            WHEN LOWER(p.name) LIKE '%fake%' THEN 'fake'
            WHEN LOWER(p.name) LIKE '%sandbox%' THEN 'sandbox'
            ELSE 'other'
        END as keyword
    FROM rds.pg_rds_public.properties p
    WHERE
        LOWER(p.name) LIKE '%test%'
        OR LOWER(p.name) LIKE '%demo%'
        OR LOWER(p.name) LIKE '%sample%'
        OR LOWER(p.name) LIKE '%staging%'
        OR LOWER(p.name) LIKE '%qa%'
        OR LOWER(p.name) LIKE '%dev%'
        OR LOWER(p.name) LIKE '%training%'
        OR LOWER(p.name) LIKE '%dummy%'
        OR LOWER(p.name) LIKE '%fake%'
        OR LOWER(p.name) LIKE '%sandbox%'
        OR LOWER(p.name) LIKE '%do not%'
        OR LOWER(p.name) LIKE '%delete%'
)

SELECT
    keyword,
    COUNT(*) as property_count
FROM test_properties
GROUP BY keyword
ORDER BY property_count DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Test Properties by Status

-- COMMAND ----------

WITH test_properties AS (
    SELECT DISTINCT p.id, p.status
    FROM rds.pg_rds_public.properties p
    WHERE
        LOWER(p.name) LIKE '%test%'
        OR LOWER(p.name) LIKE '%demo%'
        OR LOWER(p.name) LIKE '%sample%'
        OR LOWER(p.name) LIKE '%staging%'
        OR LOWER(p.name) LIKE '%qa%'
        OR LOWER(p.name) LIKE '%dev%'
        OR LOWER(p.name) LIKE '%training%'
        OR LOWER(p.name) LIKE '%dummy%'
        OR LOWER(p.name) LIKE '%fake%'
        OR LOWER(p.name) LIKE '%sandbox%'
)

SELECT
    status,
    COUNT(*) as count
FROM test_properties
GROUP BY status
ORDER BY count DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Test Properties with Company Information

-- COMMAND ----------

-- Test properties with company context
WITH test_properties AS (
    SELECT DISTINCT
        p.id as property_id,
        p.name as property_name,
        p.company_id,
        p.status,
        p.created_at
    FROM rds.pg_rds_public.properties p
    WHERE
        LOWER(p.name) LIKE '%test%'
        OR LOWER(p.name) LIKE '%demo%'
        OR LOWER(p.name) LIKE '%sample%'
        OR LOWER(p.name) LIKE '%staging%'
        OR LOWER(p.name) LIKE '%qa%'
        OR LOWER(p.name) LIKE '%dev%'
        OR LOWER(p.name) LIKE '%training%'
        OR LOWER(p.name) LIKE '%dummy%'
        OR LOWER(p.name) LIKE '%fake%'
        OR LOWER(p.name) LIKE '%sandbox%'
)

SELECT
    tp.*,
    c.name as company_name,
    c.status as company_status
FROM test_properties tp
LEFT JOIN rds.pg_rds_public.companies c
    ON c.id = tp.company_id
ORDER BY tp.created_at DESC
LIMIT 100;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Export: Just Property IDs

-- COMMAND ----------

-- Simple list of all test property IDs
SELECT DISTINCT p.id as property_id
FROM rds.pg_rds_public.properties p
WHERE
    LOWER(p.name) LIKE '%test%'
    OR LOWER(p.name) LIKE '%demo%'
    OR LOWER(p.name) LIKE '%sample%'
    OR LOWER(p.name) LIKE '%staging%'
    OR LOWER(p.name) LIKE '%qa%'
    OR LOWER(p.name) LIKE '%dev%'
    OR LOWER(p.name) LIKE '%training%'
    OR LOWER(p.name) LIKE '%dummy%'
    OR LOWER(p.name) LIKE '%fake%'
    OR LOWER(p.name) LIKE '%sandbox%'
    OR LOWER(p.name) LIKE '%do not%'
    OR LOWER(p.name) LIKE '%delete%'
    OR LOWER(p.name) LIKE '%remove%'
ORDER BY property_id;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Export: For Use in Other Queries (CTE Format)

-- COMMAND ----------

-- Ready-to-use CTE for excluding test properties
-- Copy this into your other queries

WITH test_property_ids AS (
    SELECT DISTINCT p.id as property_id
    FROM rds.pg_rds_public.properties p
    WHERE
        LOWER(p.name) LIKE '%test%'
        OR LOWER(p.name) LIKE '%demo%'
        OR LOWER(p.name) LIKE '%sample%'
        OR LOWER(p.name) LIKE '%staging%'
        OR LOWER(p.name) LIKE '%qa%'
        OR LOWER(p.name) LIKE '%dev%'
        OR LOWER(p.name) LIKE '%training%'
        OR LOWER(p.name) LIKE '%dummy%'
        OR LOWER(p.name) LIKE '%fake%'
        OR LOWER(p.name) LIKE '%sandbox%'
)
-- Example usage:
SELECT COUNT(*)
FROM rds.pg_rds_public.properties p
LEFT JOIN test_property_ids t ON t.property_id = p.id
WHERE p.status = 'ACTIVE'
  AND t.property_id IS NULL;  -- Exclude test properties

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Advanced: Potential Test Properties (Heuristics)

-- COMMAND ----------

-- Use heuristics to find potential test properties
-- even if they don't have obvious test keywords
WITH property_metrics AS (
    SELECT
        p.id,
        p.name,
        p.status,
        p.unit,
        p.created_at,
        p.updated_at,
        -- Suspicious patterns
        CASE
            WHEN p.unit = 0 OR p.unit IS NULL THEN 1 ELSE 0
        END as has_zero_units,
        CASE
            WHEN DATEDIFF(p.updated_at, p.created_at) = 0 THEN 1 ELSE 0
        END as never_updated,
        CASE
            WHEN REGEXP_LIKE(p.name, '^[0-9]') THEN 1 ELSE 0
        END as starts_with_number,
        CASE
            WHEN LENGTH(p.name) < 5 THEN 1 ELSE 0
        END as very_short_name
    FROM rds.pg_rds_public.properties p
    WHERE p.status = 'ACTIVE'
)

SELECT
    id,
    name,
    status,
    unit,
    created_at,
    has_zero_units,
    never_updated,
    starts_with_number,
    very_short_name,
    (has_zero_units + never_updated + starts_with_number + very_short_name) as suspicious_score
FROM property_metrics
WHERE (has_zero_units + never_updated + starts_with_number + very_short_name) >= 2
ORDER BY suspicious_score DESC, created_at DESC
LIMIT 100;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Check for Test Companies

-- COMMAND ----------

-- Find companies with test-related names
-- Properties under these companies might also be test properties
WITH test_companies AS (
    SELECT DISTINCT
        c.id as company_id,
        c.name as company_name,
        c.status
    FROM rds.pg_rds_public.companies c
    WHERE
        LOWER(c.name) LIKE '%test%'
        OR LOWER(c.name) LIKE '%demo%'
        OR LOWER(c.name) LIKE '%sample%'
        OR LOWER(c.name) LIKE '%staging%'
        OR LOWER(c.name) LIKE '%internal%'
        OR LOWER(c.name) LIKE '%snappt%'
        OR LOWER(c.name) LIKE '%dev%'
)

SELECT
    tc.company_id,
    tc.company_name,
    tc.status as company_status,
    COUNT(p.id) as property_count,
    SUM(CASE WHEN p.status = 'ACTIVE' THEN 1 ELSE 0 END) as active_property_count
FROM test_companies tc
LEFT JOIN rds.pg_rds_public.properties p
    ON p.company_id = tc.company_id
GROUP BY tc.company_id, tc.company_name, tc.status
ORDER BY property_count DESC;
