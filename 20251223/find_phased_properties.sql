-- ============================================
-- Find Phased Properties (Multi-Phase Buildings)
-- ============================================
-- Identifies properties that are part of phased developments
-- Example: "123 Main St Phase 1", "123 Main St Phase 2"
-- ============================================

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 1: Identify Properties with Phase Numbers

-- COMMAND ----------

WITH properties_with_phases AS (
    SELECT
        p.id as property_id,
        p.name as property_name,
        p.street_address,
        p.city,
        p.state,
        p.zip,
        p.company_id,
        p.status,
        p.unit,
        p.created_at,
        -- Extract phase information
        CASE
            WHEN LOWER(p.name) LIKE '%phase 1%' OR LOWER(p.name) LIKE '%phase i%' THEN 'Phase 1'
            WHEN LOWER(p.name) LIKE '%phase 2%' OR LOWER(p.name) LIKE '%phase ii%' THEN 'Phase 2'
            WHEN LOWER(p.name) LIKE '%phase 3%' OR LOWER(p.name) LIKE '%phase iii%' THEN 'Phase 3'
            WHEN LOWER(p.name) LIKE '%phase 4%' OR LOWER(p.name) LIKE '%phase iv%' THEN 'Phase 4'
            WHEN LOWER(p.name) LIKE '%phase 5%' OR LOWER(p.name) LIKE '%phase v%' THEN 'Phase 5'
            WHEN REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9]+') THEN
                REGEXP_EXTRACT(LOWER(p.name), 'phase\\s*([0-9]+)', 1)
            ELSE NULL
        END as phase_number,
        -- Extract base name (remove phase information)
        REGEXP_REPLACE(
            REGEXP_REPLACE(
                LOWER(p.name),
                'phase\\s*[0-9ivx]+',
                '',
                1
            ),
            '[\\s-]+$',  -- Remove trailing spaces/dashes
            ''
        ) as base_name,
        -- Also check street address for phase info
        CASE
            WHEN LOWER(p.street_address) LIKE '%phase%' THEN 1
            ELSE 0
        END as has_phase_in_address
    FROM rds.pg_rds_public.properties p
    WHERE
        -- Property name has phase information
        (
            LOWER(p.name) LIKE '%phase%'
            OR REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9ivx]+')
        )
        -- Or street address has phase information
        OR LOWER(p.street_address) LIKE '%phase%'
)

SELECT
    property_id,
    property_name,
    street_address,
    city,
    state,
    phase_number,
    base_name,
    status,
    unit,
    company_id
FROM properties_with_phases
ORDER BY base_name, phase_number;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 2: Group Properties by Base Address

-- COMMAND ----------

-- Find multi-phase buildings (same base address/name with multiple phases)
WITH properties_with_phases AS (
    SELECT
        p.id as property_id,
        p.name as property_name,
        p.street_address,
        p.company_id,
        p.status,
        p.unit,
        p.created_at,
        -- Extract phase number
        CASE
            WHEN LOWER(p.name) LIKE '%phase 1%' THEN '1'
            WHEN LOWER(p.name) LIKE '%phase 2%' THEN '2'
            WHEN LOWER(p.name) LIKE '%phase 3%' THEN '3'
            WHEN LOWER(p.name) LIKE '%phase 4%' THEN '4'
            WHEN LOWER(p.name) LIKE '%phase 5%' THEN '5'
            WHEN REGEXP_LIKE(LOWER(p.name), 'phase\\s*([0-9]+)') THEN
                REGEXP_EXTRACT(LOWER(p.name), 'phase\\s*([0-9]+)', 1)
            WHEN LOWER(p.name) LIKE '%phase i%' THEN '1'
            WHEN LOWER(p.name) LIKE '%phase ii%' THEN '2'
            WHEN LOWER(p.name) LIKE '%phase iii%' THEN '3'
            WHEN LOWER(p.name) LIKE '%phase iv%' THEN '4'
            WHEN LOWER(p.name) LIKE '%phase v%' THEN '5'
            ELSE 'unknown'
        END as phase_number,
        -- Create normalized base identifier (remove phase info and normalize)
        TRIM(REGEXP_REPLACE(
            REGEXP_REPLACE(LOWER(p.name), 'phase\\s*[0-9ivx]+', '', 1),
            '[^a-z0-9]',
            ''
        )) as base_identifier
    FROM rds.pg_rds_public.properties p
    WHERE
        LOWER(p.name) LIKE '%phase%'
        OR REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9ivx]+')
),
grouped_phases AS (
    SELECT
        base_identifier,
        -- Get representative info from first property
        FIRST(property_name) as example_property_name,
        FIRST(street_address) as street_address,
        FIRST(company_id) as company_id,
        -- Count and collect phases
        COUNT(DISTINCT property_id) as total_phases,
        COUNT(DISTINCT phase_number) as unique_phase_numbers,
        COLLECT_LIST(STRUCT(
            property_id,
            property_name,
            phase_number,
            status,
            unit,
            created_at
        )) as all_phases,
        CONCAT_WS(', ', COLLECT_SET(phase_number)) as phase_list
    FROM properties_with_phases
    WHERE base_identifier != ''  -- Exclude empty base identifiers
    GROUP BY base_identifier
    HAVING COUNT(DISTINCT property_id) > 1  -- Only multi-phase properties
)

SELECT
    base_identifier,
    example_property_name,
    street_address,
    total_phases,
    unique_phase_numbers,
    phase_list,
    company_id
FROM grouped_phases
ORDER BY total_phases DESC, example_property_name;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 3: Identify Potentially Phased Out Properties

-- COMMAND ----------

-- Find older phases that might be "phased out" (replaced by newer phases)
WITH properties_with_phases AS (
    SELECT
        p.id as property_id,
        p.name as property_name,
        p.street_address,
        p.company_id,
        p.status,
        p.unit,
        p.created_at,
        p.updated_at,
        -- Extract phase number
        CASE
            WHEN LOWER(p.name) LIKE '%phase 1%' THEN 1
            WHEN LOWER(p.name) LIKE '%phase 2%' THEN 2
            WHEN LOWER(p.name) LIKE '%phase 3%' THEN 3
            WHEN LOWER(p.name) LIKE '%phase 4%' THEN 4
            WHEN LOWER(p.name) LIKE '%phase 5%' THEN 5
            WHEN REGEXP_LIKE(LOWER(p.name), 'phase\\s*([0-9]+)') THEN
                CAST(REGEXP_EXTRACT(LOWER(p.name), 'phase\\s*([0-9]+)', 1) AS INT)
            ELSE 0
        END as phase_number,
        -- Create base identifier
        TRIM(REGEXP_REPLACE(
            REGEXP_REPLACE(LOWER(p.name), 'phase\\s*[0-9ivx]+', '', 1),
            '[^a-z0-9]',
            ''
        )) as base_identifier
    FROM rds.pg_rds_public.properties p
    WHERE
        LOWER(p.name) LIKE '%phase%'
        OR REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9ivx]+')
),
phase_groups AS (
    SELECT
        base_identifier,
        property_id,
        property_name,
        street_address,
        status,
        phase_number,
        created_at,
        company_id,
        -- Get max phase for this base property
        MAX(phase_number) OVER (PARTITION BY base_identifier) as max_phase,
        -- Count total phases for this base property
        COUNT(*) OVER (PARTITION BY base_identifier) as total_phases_for_property
    FROM properties_with_phases
    WHERE base_identifier != ''
)

SELECT
    property_id,
    property_name,
    street_address,
    status,
    phase_number,
    max_phase,
    total_phases_for_property,
    company_id,
    created_at,
    -- Flag potentially phased out properties
    CASE
        WHEN phase_number < max_phase AND status = 'ACTIVE' THEN 'Old Phase Still Active'
        WHEN phase_number < max_phase AND status != 'ACTIVE' THEN 'Old Phase Inactive (Phased Out)'
        WHEN phase_number = max_phase THEN 'Latest Phase'
        ELSE 'Unknown'
    END as phase_status_category
FROM phase_groups
WHERE total_phases_for_property > 1  -- Only show multi-phase properties
ORDER BY base_identifier, phase_number;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 4: Summary Statistics

-- COMMAND ----------

-- Count properties by phase status
WITH properties_with_phases AS (
    SELECT
        p.id as property_id,
        CASE
            WHEN LOWER(p.name) LIKE '%phase 1%' THEN 1
            WHEN LOWER(p.name) LIKE '%phase 2%' THEN 2
            WHEN LOWER(p.name) LIKE '%phase 3%' THEN 3
            WHEN LOWER(p.name) LIKE '%phase 4%' THEN 4
            WHEN LOWER(p.name) LIKE '%phase 5%' THEN 5
            WHEN REGEXP_LIKE(LOWER(p.name), 'phase\\s*([0-9]+)') THEN
                CAST(REGEXP_EXTRACT(LOWER(p.name), 'phase\\s*([0-9]+)', 1) AS INT)
            ELSE 0
        END as phase_number,
        TRIM(REGEXP_REPLACE(
            REGEXP_REPLACE(LOWER(p.name), 'phase\\s*[0-9ivx]+', '', 1),
            '[^a-z0-9]',
            ''
        )) as base_identifier,
        p.status
    FROM rds.pg_rds_public.properties p
    WHERE LOWER(p.name) LIKE '%phase%'
),
phase_groups AS (
    SELECT
        property_id,
        phase_number,
        status,
        MAX(phase_number) OVER (PARTITION BY base_identifier) as max_phase,
        COUNT(*) OVER (PARTITION BY base_identifier) as phases_in_group
    FROM properties_with_phases
    WHERE base_identifier != ''
)

SELECT
    'Total Properties with Phase in Name' as metric,
    COUNT(DISTINCT property_id) as count
FROM properties_with_phases

UNION ALL

SELECT
    'Multi-Phase Buildings (2+ phases)' as metric,
    COUNT(DISTINCT property_id) as count
FROM phase_groups
WHERE phases_in_group > 1

UNION ALL

SELECT
    'Old Phases Still Active (Potential Duplicates)' as metric,
    COUNT(DISTINCT property_id) as count
FROM phase_groups
WHERE phase_number < max_phase AND status = 'ACTIVE' AND phases_in_group > 1

UNION ALL

SELECT
    'Old Phases Inactive (Properly Phased Out)' as metric,
    COUNT(DISTINCT property_id) as count
FROM phase_groups
WHERE phase_number < max_phase AND status != 'ACTIVE' AND phases_in_group > 1;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 5: Export - All Phased Property IDs

-- COMMAND ----------

-- Get all property IDs that are part of phased buildings
SELECT DISTINCT p.id as property_id
FROM rds.pg_rds_public.properties p
WHERE
    LOWER(p.name) LIKE '%phase 1%'
    OR LOWER(p.name) LIKE '%phase 2%'
    OR LOWER(p.name) LIKE '%phase 3%'
    OR LOWER(p.name) LIKE '%phase 4%'
    OR LOWER(p.name) LIKE '%phase 5%'
    OR LOWER(p.name) LIKE '%phase i%'
    OR LOWER(p.name) LIKE '%phase ii%'
    OR LOWER(p.name) LIKE '%phase iii%'
    OR LOWER(p.name) LIKE '%phase iv%'
    OR LOWER(p.name) LIKE '%phase v%'
    OR REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9]+')
    OR LOWER(p.street_address) LIKE '%phase%'
ORDER BY property_id;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 6: Export - OLD Phase Properties to Exclude

-- COMMAND ----------

-- Get property IDs of old phases (not the latest phase)
-- These are likely the ones you want to EXCLUDE from counts
WITH properties_with_phases AS (
    SELECT
        p.id as property_id,
        p.name,
        p.status,
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
),
phase_groups AS (
    SELECT
        property_id,
        name,
        status,
        phase_number,
        base_identifier,
        MAX(phase_number) OVER (PARTITION BY base_identifier) as max_phase,
        COUNT(*) OVER (PARTITION BY base_identifier) as phases_in_group
    FROM properties_with_phases
    WHERE base_identifier != ''
)

-- Only return old phases from multi-phase buildings
SELECT
    property_id,
    name,
    status,
    phase_number,
    max_phase,
    'Old Phase - Consider Excluding' as reason
FROM phase_groups
WHERE
    phases_in_group > 1  -- Part of a multi-phase building
    AND phase_number < max_phase  -- Not the latest phase
ORDER BY base_identifier, phase_number;
