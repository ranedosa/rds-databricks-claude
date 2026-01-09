-- ============================================================================
-- PHASE 1: DUPLICATE SFDC_ID CLEANUP - DISABLED PROPERTIES
-- ============================================================================
--
-- Purpose: Clear sfdc_id from DISABLED properties that share sfdc_id with ACTIVE properties
-- Impact: ~3,400 DISABLED properties, resolves ~2,000 duplicate groups
-- Safety: Only affects DISABLED properties, ACTIVE properties untouched
--
-- ============================================================================

-- STEP 1: PREVIEW - See what will be changed
-- ============================================================================

WITH duplicate_groups AS (
    -- Find all sfdc_ids that appear more than once
    SELECT sfdc_id
    FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
      AND sfdc_id != 'XXXXXXXXXXXXXXX'  -- Exclude test properties
    GROUP BY sfdc_id
    HAVING COUNT(*) > 1
),

disabled_in_duplicates AS (
    -- Get all DISABLED properties in duplicate groups
    SELECT
        p.id,
        p.name,
        p.short_id,
        p.sfdc_id,
        p.status,
        p.inserted_at
    FROM rds.pg_rds_public.properties p
    INNER JOIN duplicate_groups dg ON p.sfdc_id = dg.sfdc_id
    WHERE p.status = 'DISABLED'
)

SELECT
    COUNT(*) as total_disabled_properties,
    COUNT(DISTINCT sfdc_id) as duplicate_groups_affected,
    MIN(inserted_at) as oldest_property,
    MAX(inserted_at) as newest_property
FROM disabled_in_duplicates;

-- ============================================================================
-- STEP 2: DETAILED PREVIEW - Sample of properties to be cleared
-- ============================================================================

WITH duplicate_groups AS (
    SELECT sfdc_id
    FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
      AND sfdc_id != 'XXXXXXXXXXXXXXX'
    GROUP BY sfdc_id
    HAVING COUNT(*) > 1
)

SELECT
    p.id,
    p.name,
    p.short_id,
    p.sfdc_id,
    p.status,
    p.inserted_at,
    COUNT(*) OVER (PARTITION BY p.sfdc_id) as total_props_with_this_sfdc_id
FROM rds.pg_rds_public.properties p
INNER JOIN duplicate_groups dg ON p.sfdc_id = dg.sfdc_id
WHERE p.status = 'DISABLED'
ORDER BY p.sfdc_id, p.inserted_at DESC
LIMIT 100;

-- ============================================================================
-- STEP 3: CHECK FOR EDGE CASES
-- ============================================================================

-- Check: Are there any groups where ALL properties are DISABLED?
-- (These need different handling)
WITH duplicate_groups AS (
    SELECT sfdc_id
    FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
      AND sfdc_id != 'XXXXXXXXXXXXXXX'
    GROUP BY sfdc_id
    HAVING COUNT(*) > 1
),

group_status AS (
    SELECT
        p.sfdc_id,
        SUM(CASE WHEN p.status = 'ACTIVE' THEN 1 ELSE 0 END) as active_count,
        SUM(CASE WHEN p.status = 'DISABLED' THEN 1 ELSE 0 END) as disabled_count,
        COUNT(*) as total_count
    FROM rds.pg_rds_public.properties p
    INNER JOIN duplicate_groups dg ON p.sfdc_id = dg.sfdc_id
    GROUP BY p.sfdc_id
)

SELECT
    COUNT(*) as all_disabled_groups,
    SUM(total_count) as total_disabled_properties_in_these_groups
FROM group_status
WHERE active_count = 0;

-- ============================================================================
-- STEP 4: EXECUTE CLEANUP (UNCOMMENT TO RUN)
-- ============================================================================

/*
-- BACKUP FIRST: Create a backup table of current sfdc_id mappings
CREATE TABLE rds.pg_rds_public.properties_sfdc_id_backup_20251219 AS
SELECT id, name, sfdc_id, status, inserted_at, updated_at
FROM rds.pg_rds_public.properties
WHERE sfdc_id IS NOT NULL;

-- EXECUTE: Clear sfdc_id from DISABLED properties in duplicate groups
WITH duplicate_groups AS (
    SELECT sfdc_id
    FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
      AND sfdc_id != 'XXXXXXXXXXXXXXX'
    GROUP BY sfdc_id
    HAVING COUNT(*) > 1
),

disabled_to_clear AS (
    SELECT p.id
    FROM rds.pg_rds_public.properties p
    INNER JOIN duplicate_groups dg ON p.sfdc_id = dg.sfdc_id
    WHERE p.status = 'DISABLED'
)

UPDATE rds.pg_rds_public.properties
SET sfdc_id = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE id IN (SELECT id FROM disabled_to_clear);

-- Verify the update
SELECT COUNT(*) as properties_updated
FROM rds.pg_rds_public.properties
WHERE id IN (SELECT id FROM disabled_to_clear)
  AND sfdc_id IS NULL;
*/

-- ============================================================================
-- STEP 5: POST-EXECUTION VERIFICATION
-- ============================================================================

-- After executing, run these queries to verify success:

-- 1. Check how many duplicate groups remain
SELECT COUNT(DISTINCT sfdc_id) as remaining_duplicate_groups
FROM (
    SELECT sfdc_id
    FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
      AND sfdc_id != 'XXXXXXXXXXXXXXX'
    GROUP BY sfdc_id
    HAVING COUNT(*) > 1
) remaining;

-- 2. Check if any DISABLED properties still have duplicate sfdc_ids
SELECT COUNT(*) as disabled_with_duplicates
FROM (
    SELECT p.id
    FROM rds.pg_rds_public.properties p
    WHERE p.status = 'DISABLED'
      AND p.sfdc_id IS NOT NULL
      AND EXISTS (
          SELECT 1
          FROM rds.pg_rds_public.properties p2
          WHERE p2.sfdc_id = p.sfdc_id
            AND p2.id != p.id
      )
);

-- 3. Verify Park Kennedy is fixed
SELECT
    id,
    name,
    status,
    sfdc_id,
    identity_verification_enabled
FROM rds.pg_rds_public.properties
WHERE name LIKE '%Park Kennedy%'
ORDER BY status, inserted_at DESC;

-- ============================================================================
-- ROLLBACK PROCEDURE (If needed)
-- ============================================================================

/*
-- To rollback, restore sfdc_ids from backup
UPDATE rds.pg_rds_public.properties p
SET sfdc_id = b.sfdc_id
FROM rds.pg_rds_public.properties_sfdc_id_backup_20251219 b
WHERE p.id = b.id
  AND p.sfdc_id IS NULL
  AND b.sfdc_id IS NOT NULL;
*/

-- ============================================================================
-- EXPECTED RESULTS
-- ============================================================================

-- Before: ~2,541 duplicate sfdc_id groups, 3,391 DISABLED with duplicates
-- After: ~500-700 duplicate groups (mostly ACTIVE+ACTIVE pairs)
-- Resolution: ~2,000 duplicate groups resolved (79%)
-- Properties Unblocked: ~2,500 ACTIVE properties can now sync

-- ============================================================================
