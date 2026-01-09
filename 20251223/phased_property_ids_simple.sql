-- ============================================
-- SIMPLE: Get All Phased Property IDs
-- ============================================
-- Returns all properties that are part of phased buildings
-- Example: "123 Main St Phase 1", "456 Oak Ave Phase 2"
-- ============================================

-- Option 1: All properties with "Phase" in name or address
SELECT DISTINCT p.id as property_id
FROM rds.pg_rds_public.properties p
WHERE
    -- Phase with numbers (1-9)
    LOWER(p.name) LIKE '%phase 1%'
    OR LOWER(p.name) LIKE '%phase 2%'
    OR LOWER(p.name) LIKE '%phase 3%'
    OR LOWER(p.name) LIKE '%phase 4%'
    OR LOWER(p.name) LIKE '%phase 5%'
    OR LOWER(p.name) LIKE '%phase 6%'
    OR LOWER(p.name) LIKE '%phase 7%'
    OR LOWER(p.name) LIKE '%phase 8%'
    OR LOWER(p.name) LIKE '%phase 9%'

    -- Phase with Roman numerals
    OR LOWER(p.name) LIKE '%phase i%'
    OR LOWER(p.name) LIKE '%phase ii%'
    OR LOWER(p.name) LIKE '%phase iii%'
    OR LOWER(p.name) LIKE '%phase iv%'
    OR LOWER(p.name) LIKE '%phase v%'

    -- Regex pattern for any phase number
    OR REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9]+')

    -- Check address field too
    OR LOWER(p.street_address) LIKE '%phase%'
ORDER BY property_id;

-- COMMAND ----------

-- Option 2: OLD phases only (not the latest phase)
-- Use this to exclude duplicate/old phases from your count
WITH properties_with_phases AS (
    SELECT
        p.id as property_id,
        -- Extract numeric phase
        CASE
            WHEN LOWER(p.name) LIKE '%phase 1%' THEN 1
            WHEN LOWER(p.name) LIKE '%phase 2%' THEN 2
            WHEN LOWER(p.name) LIKE '%phase 3%' THEN 3
            WHEN LOWER(p.name) LIKE '%phase 4%' THEN 4
            WHEN LOWER(p.name) LIKE '%phase 5%' THEN 5
            WHEN REGEXP_LIKE(LOWER(p.name), 'phase\\s*([0-9]+)') THEN
                CAST(REGEXP_EXTRACT(LOWER(p.name), 'phase\\s*([0-9]+)', 1) AS INT)
            WHEN LOWER(p.name) LIKE '%phase i%' THEN 1
            WHEN LOWER(p.name) LIKE '%phase ii%' THEN 2
            WHEN LOWER(p.name) LIKE '%phase iii%' THEN 3
            ELSE 0
        END as phase_number,
        -- Create base identifier (property name without phase)
        TRIM(REGEXP_REPLACE(
            REGEXP_REPLACE(LOWER(p.name), 'phase\\s*[0-9ivx]+', '', 1),
            '[^a-z0-9]',
            ''
        )) as base_identifier
    FROM rds.pg_rds_public.properties p
    WHERE LOWER(p.name) LIKE '%phase%'
),
phase_analysis AS (
    SELECT
        property_id,
        phase_number,
        base_identifier,
        -- Get max phase for each base property
        MAX(phase_number) OVER (PARTITION BY base_identifier) as max_phase,
        -- Count phases per base property
        COUNT(*) OVER (PARTITION BY base_identifier) as total_phases
    FROM properties_with_phases
    WHERE base_identifier != ''
)

-- Return only old phases from multi-phase buildings
SELECT DISTINCT property_id
FROM phase_analysis
WHERE
    total_phases > 1           -- Property has multiple phases
    AND phase_number < max_phase  -- This is not the latest phase
ORDER BY property_id;
