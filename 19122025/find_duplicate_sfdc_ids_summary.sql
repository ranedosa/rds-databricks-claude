-- Summary view: Show duplicate sfdc_id groups with key info

WITH duplicate_sfdc_ids AS (
    SELECT
        sfdc_id,
        COUNT(*) as duplicate_count,
        MAX(inserted_at) as most_recent_insert,
        MIN(inserted_at) as oldest_insert,
        COLLECT_LIST(STRUCT(
            id,
            name,
            status,
            short_id,
            inserted_at
        )) as properties
    FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
    GROUP BY sfdc_id
    HAVING COUNT(*) > 1
)

SELECT
    sfdc_id,
    duplicate_count,
    most_recent_insert,
    oldest_insert,
    properties
FROM duplicate_sfdc_ids
ORDER BY most_recent_insert DESC;


-- Alternative: Flattened view with all details
-- Uncomment below to use this version instead:

/*
WITH duplicate_groups AS (
    SELECT
        sfdc_id,
        COUNT(*) OVER (PARTITION BY sfdc_id) as dup_count,
        MAX(inserted_at) OVER (PARTITION BY sfdc_id) as group_max_date
    FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
)

SELECT
    p.sfdc_id,
    dg.dup_count as duplicates_found,
    p.id as property_id,
    p.name,
    p.short_id,
    p.status,
    p.identity_verification_enabled,
    p.inserted_at,
    p.updated_at,
    CASE
        WHEN p.inserted_at = dg.group_max_date THEN '⭐ NEWEST'
        ELSE ''
    END as is_newest_in_group
FROM rds.pg_rds_public.properties p
INNER JOIN duplicate_groups dg ON p.sfdc_id = dg.sfdc_id
WHERE dg.dup_count > 1
ORDER BY
    dg.group_max_date DESC,
    p.sfdc_id,
    p.inserted_at DESC;
*/
