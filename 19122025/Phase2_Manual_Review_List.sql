-- ============================================================================
-- PHASE 2: MANUAL REVIEW - TWO ACTIVE PROPERTIES WITH SAME SFDC_ID
-- ============================================================================
--
-- Purpose: Identify cases where TWO OR MORE ACTIVE properties share the same sfdc_id
-- These require manual investigation to determine the correct resolution
--
-- ============================================================================

-- Query 1: List all sfdc_ids with multiple ACTIVE properties
-- ============================================================================

WITH active_duplicates AS (
    SELECT
        sfdc_id,
        COUNT(*) as active_property_count,
        COLLECT_LIST(STRUCT(
            id,
            name,
            short_id,
            identity_verification_enabled,
            inserted_at,
            updated_at
        )) as properties
    FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
      AND sfdc_id != 'XXXXXXXXXXXXXXX'
      AND status = 'ACTIVE'
    GROUP BY sfdc_id
    HAVING COUNT(*) > 1
)

SELECT
    sfdc_id,
    active_property_count,
    properties
FROM active_duplicates
ORDER BY active_property_count DESC, sfdc_id;

-- ============================================================================
-- Query 2: Detailed view - One row per property for review
-- ============================================================================

WITH active_duplicate_sfdc_ids AS (
    SELECT sfdc_id
    FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
      AND sfdc_id != 'XXXXXXXXXXXXXXX'
      AND status = 'ACTIVE'
    GROUP BY sfdc_id
    HAVING COUNT(*) > 1
)

SELECT
    p.id,
    p.name,
    p.short_id,
    p.sfdc_id,
    p.identity_verification_enabled as idv_enabled,
    p.inserted_at,
    p.updated_at,
    -- Check if in Salesforce
    CASE
        WHEN sf.id IS NOT NULL THEN '✓ In Salesforce'
        ELSE '✗ NOT in Salesforce'
    END as salesforce_status,
    sf.id as salesforce_record_id,
    -- Count features enabled
    (
        SELECT COUNT(*)
        FROM rds.pg_rds_public.property_feature_events pfe
        WHERE pfe.property_id = p.id
          AND pfe.event_type = 'enabled'
          AND pfe._fivetran_deleted = false
          AND pfe.inserted_at = (
              SELECT MAX(inserted_at)
              FROM rds.pg_rds_public.property_feature_events pfe2
              WHERE pfe2.property_id = p.id
                AND pfe2.feature_code = pfe.feature_code
          )
    ) as enabled_features_count
FROM rds.pg_rds_public.properties p
INNER JOIN active_duplicate_sfdc_ids ad ON p.sfdc_id = ad.sfdc_id
LEFT JOIN crm.salesforce.product_property sf
    ON CAST(p.id AS STRING) = sf.snappt_property_id_c
WHERE p.status = 'ACTIVE'
ORDER BY p.sfdc_id, p.inserted_at DESC;

-- ============================================================================
-- Query 3: Categorized by likely issue type
-- ============================================================================

WITH active_duplicates AS (
    SELECT
        sfdc_id,
        COLLECT_LIST(STRUCT(id, name, short_id, inserted_at)) as properties
    FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
      AND sfdc_id != 'XXXXXXXXXXXXXXX'
      AND status = 'ACTIVE'
    GROUP BY sfdc_id
    HAVING COUNT(*) > 1
)

SELECT
    sfdc_id,
    SIZE(properties) as property_count,
    properties,
    -- Categorize the issue
    CASE
        -- Similar names = likely migration/name change
        WHEN SIZE(COLLECT_SET(LOWER(REGEXP_REPLACE(properties.name, '[^a-z0-9]', '')))) = 1
        THEN 'LIKELY_MIGRATION'

        -- Very different names = could be different properties
        WHEN SIZE(COLLECT_SET(LOWER(REGEXP_REPLACE(properties.name, '[^a-z0-9]', '')))) > 1
        THEN 'DIFFERENT_NAMES'

        ELSE 'UNKNOWN'
    END as issue_category
FROM active_duplicates
ORDER BY property_count DESC, sfdc_id;

-- ============================================================================
-- Query 4: Priority ranking - Which to review first
-- ============================================================================

WITH active_duplicates AS (
    SELECT
        p.sfdc_id,
        p.id,
        p.name,
        p.short_id,
        p.inserted_at,
        -- Check features
        (
            SELECT COUNT(*)
            FROM rds.pg_rds_public.property_feature_events pfe
            WHERE pfe.property_id = p.id
              AND pfe.event_type = 'enabled'
              AND pfe._fivetran_deleted = false
        ) as features_enabled,
        -- Check if in Salesforce
        CASE WHEN sf.id IS NOT NULL THEN 1 ELSE 0 END as in_salesforce
    FROM rds.pg_rds_public.properties p
    LEFT JOIN crm.salesforce.product_property sf
        ON CAST(p.id AS STRING) = sf.snappt_property_id_c
    WHERE p.sfdc_id IN (
        SELECT sfdc_id
        FROM rds.pg_rds_public.properties
        WHERE sfdc_id IS NOT NULL
          AND sfdc_id != 'XXXXXXXXXXXXXXX'
          AND status = 'ACTIVE'
        GROUP BY sfdc_id
        HAVING COUNT(*) > 1
    )
    AND p.status = 'ACTIVE'
)

SELECT
    sfdc_id,
    id,
    name,
    short_id,
    features_enabled,
    in_salesforce,
    inserted_at,
    -- Priority score (higher = more urgent)
    (features_enabled * 10) + (CASE WHEN in_salesforce = 0 THEN 5 ELSE 0 END) as priority_score,
    CASE
        WHEN features_enabled > 0 AND in_salesforce = 0 THEN 'P1 - URGENT'
        WHEN features_enabled > 0 AND in_salesforce = 1 THEN 'P2 - HIGH'
        WHEN features_enabled = 0 AND in_salesforce = 0 THEN 'P3 - MEDIUM'
        ELSE 'P4 - LOW'
    END as priority_level
FROM active_duplicates
ORDER BY priority_score DESC, sfdc_id, inserted_at DESC;

-- ============================================================================
-- Query 5: Export for spreadsheet review
-- ============================================================================

-- CSV-friendly format for manual review in Excel/Sheets

WITH active_duplicate_sfdc_ids AS (
    SELECT sfdc_id
    FROM rds.pg_rds_public.properties
    WHERE sfdc_id IS NOT NULL
      AND sfdc_id != 'XXXXXXXXXXXXXXX'
      AND status = 'ACTIVE'
    GROUP BY sfdc_id
    HAVING COUNT(*) > 1
)

SELECT
    p.sfdc_id,
    p.id as property_id,
    p.name as property_name,
    p.short_id,
    p.inserted_at,
    p.updated_at,
    CASE WHEN sf.id IS NOT NULL THEN 'YES' ELSE 'NO' END as in_salesforce,
    sf.id as salesforce_record_id,
    '' as review_notes,
    '' as action_decision,
    '' as keep_or_clear
FROM rds.pg_rds_public.properties p
INNER JOIN active_duplicate_sfdc_ids ad ON p.sfdc_id = ad.sfdc_id
LEFT JOIN crm.salesforce.product_property sf
    ON CAST(p.id AS STRING) = sf.snappt_property_id_c
WHERE p.status = 'ACTIVE'
ORDER BY p.sfdc_id, p.inserted_at DESC;

-- ============================================================================
-- DECISION FRAMEWORK FOR MANUAL REVIEW
-- ============================================================================

/*
For each duplicate group, answer these questions:

1. Are the properties the same entity?
   - Same property, just renamed? → Mark older as DISABLED, clear sfdc_id
   - Property migrated to new record? → Clear sfdc_id from old
   - Different properties entirely? → One needs new Salesforce record

2. Which property has the most activity?
   - More features enabled?
   - In Salesforce already?
   - More recent insert date?
   → This one should probably keep the sfdc_id

3. Which property should be in Salesforce?
   - Customer-facing property?
   - Has active users?
   - Has recent submissions?
   → This one should keep sfdc_id

4. Document your decision:
   - Property A: Keep sfdc_id (reason)
   - Property B: Clear sfdc_id (reason)
   - OR Property B: Mark DISABLED (reason)

5. Create resolution SQL:
   UPDATE rds.pg_rds_public.properties
   SET sfdc_id = NULL
   WHERE id = '<property-to-clear>';
*/

-- ============================================================================
-- COMMON SCENARIOS & RESOLUTIONS
-- ============================================================================

/*
SCENARIO 1: Property Name Change
  Example: "The Morgan" → "Morgan"
  Resolution: Keep sfdc_id on newer property, clear from older

SCENARIO 2: Management Company Change
  Example: "Bell Lighthouse Point" → "Advenir Lighthouse Point"
  Resolution: Both are ACTIVE and different, one needs new Salesforce record

SCENARIO 3: Guarantor/Employee Variants
  Example: "Water Oak" + "Water Oak - Guarantor"
  Resolution: These are different product types, need separate Salesforce records

SCENARIO 4: Test Property Cleanup
  Example: Property created by mistake, never used
  Resolution: Mark as DISABLED, clear sfdc_id

SCENARIO 5: Migration During Onboarding
  Example: Property created, found errors, recreated
  Resolution: Mark old as DISABLED, clear sfdc_id
*/

-- ============================================================================
-- NEXT STEPS
-- ============================================================================

/*
1. Run Query 4 (Priority ranking) to get the list ordered by urgency
2. Export Query 5 to spreadsheet for review
3. For each P1/P2 case:
   - Research the properties
   - Make a decision
   - Document in spreadsheet
4. Generate cleanup SQL for each decision
5. Execute in batches
6. Monitor sync workflow to verify fixes
*/

-- ============================================================================
