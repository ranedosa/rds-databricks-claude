-- ============================================
-- SIMPLE: Get All Test Property IDs
-- ============================================
-- Run this to get a complete list of test property IDs
-- ============================================

SELECT DISTINCT p.id as property_id
FROM rds.pg_rds_public.properties p
WHERE
    -- Core test keywords
    LOWER(p.name) LIKE '%test%'
    OR LOWER(p.name) LIKE '%demo%'
    OR LOWER(p.name) LIKE '%sample%'

    -- Development/staging keywords
    OR LOWER(p.name) LIKE '%staging%'
    OR LOWER(p.name) LIKE '%qa%'
    OR LOWER(p.name) LIKE '%dev%'
    OR LOWER(p.name) LIKE '%sandbox%'

    -- Training/temporary keywords
    OR LOWER(p.name) LIKE '%training%'
    OR LOWER(p.name) LIKE '%dummy%'
    OR LOWER(p.name) LIKE '%fake%'
    OR LOWER(p.name) LIKE '%temporary%'
    OR LOWER(p.name) LIKE '%temp%'

    -- Action keywords (properties marked for removal)
    OR LOWER(p.name) LIKE '%do not%'
    OR LOWER(p.name) LIKE '%delete%'
    OR LOWER(p.name) LIKE '%remove%'
    OR LOWER(p.name) LIKE '%duplicate%'

    -- Pattern-based detection
    OR REGEXP_LIKE(LOWER(p.name), '^test[_\\s-]')    -- Starts with "test"
    OR REGEXP_LIKE(LOWER(p.name), '^demo[_\\s-]')    -- Starts with "demo"
    OR REGEXP_LIKE(LOWER(p.name), '[_\\s-]test$')    -- Ends with "test"
    OR REGEXP_LIKE(LOWER(p.name), '[_\\s-]demo$')    -- Ends with "demo"
ORDER BY property_id;
