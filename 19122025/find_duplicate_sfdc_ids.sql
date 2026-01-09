-- Find all properties with duplicate sfdc_id values
-- Grouped by sfdc_id, ordered by most recent insert date

WITH duplicate_sfdc_ids AS (
    -- Find all sfdc_ids that appear more than once
    SELECT
        sfdc_id,
        COUNT(*) as duplicate_count,
        MAX(inserted_at) as most_recent_insert
    FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
    GROUP BY sfdc_id
    HAVING COUNT(*) > 1
),

properties_with_duplicates AS (
    -- Get all properties that have duplicate sfdc_ids
    SELECT
        p.id,
        p.name,
        p.short_id,
        p.status,
        p.sfdc_id,
        p.identity_verification_enabled,
        p.inserted_at,
        p.updated_at,
        d.duplicate_count,
        d.most_recent_insert as group_most_recent
    FROM rds.pg_rds_public.properties p
    INNER JOIN duplicate_sfdc_ids d ON p.sfdc_id = d.sfdc_id
)

-- Return results ordered by group (newest duplicates first),
-- then by inserted_at within each group
SELECT
    id,
    name,
    short_id,
    status,
    sfdc_id,
    identity_verification_enabled,
    inserted_at,
    updated_at,
    duplicate_count
FROM properties_with_duplicates
ORDER BY
    group_most_recent DESC,  -- Newest duplicate groups first
    sfdc_id,                  -- Group by sfdc_id
    inserted_at DESC;         -- Newest property first within each group
