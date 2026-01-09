-- ============================================================================
-- TEST: Verify rds_properties_enriched view fix
-- Run this AFTER applying the view fix
-- ============================================================================

-- TEST 1: Verify company_name is different from property_name
-- Expected: Should return rows where company_name != property_name
-- ============================================================================
SELECT
    rds_property_id,
    property_name,
    company_name,
    company_id,
    CASE
        WHEN property_name = company_name THEN '❌ STILL BROKEN'
        WHEN property_name != company_name THEN '✅ FIXED'
        WHEN company_name IS NULL THEN '⚠️ NULL'
        ELSE '❓ OTHER'
    END as status
FROM crm.sfdc_dbx.rds_properties_enriched
LIMIT 20;


-- TEST 2: Check for NULL company names
-- Expected: Should be minimal (only if company doesn't exist in companies table)
-- ============================================================================
SELECT
    COUNT(*) as total_records,
    SUM(CASE WHEN company_name IS NULL THEN 1 ELSE 0 END) as null_company_names,
    SUM(CASE WHEN company_name IS NOT NULL THEN 1 ELSE 0 END) as has_company_names,
    ROUND(100.0 * SUM(CASE WHEN company_name IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as null_percentage
FROM crm.sfdc_dbx.rds_properties_enriched;


-- TEST 3: Compare property vs company names for known properties
-- Expected: Should show company names like "Greystar", "RPM Living", etc.
--           NOT property names like "Hardware", "Rowan", etc.
-- ============================================================================
SELECT
    property_name,
    company_name,
    CASE
        WHEN company_name IN ('Greystar', 'RPM Living', 'AVENUE5 RESIDENTIAL', 'RKW Residential', 'First Communities')
            THEN '✅ LOOKS CORRECT'
        WHEN company_name = property_name
            THEN '❌ STILL BROKEN'
        WHEN company_name IS NULL
            THEN '⚠️ NULL'
        ELSE '✅ PROBABLY CORRECT'
    END as validation
FROM crm.sfdc_dbx.rds_properties_enriched
WHERE property_name IN (
    'Hardware',
    'Rowan',
    'Skymor Wesley Chapel',
    'The Storey',
    'South and Twenty'
)
LIMIT 10;


-- TEST 4: Verify properties_to_create inherits the fix
-- Expected: company_name should be correct in downstream view too
-- ============================================================================
SELECT
    rds_property_id,
    property_name,
    company_name,
    CASE
        WHEN property_name != company_name THEN '✅ FIXED'
        WHEN property_name = company_name THEN '❌ BROKEN'
        ELSE '❓ OTHER'
    END as status
FROM crm.sfdc_dbx.properties_to_create
LIMIT 20;


-- TEST 5: Verify properties_to_update inherits the fix
-- Expected: company_name should be correct in downstream view too
-- ============================================================================
SELECT
    rds_property_id,
    property_name,
    company_name,
    CASE
        WHEN property_name != company_name THEN '✅ FIXED'
        WHEN property_name = company_name THEN '❌ BROKEN'
        ELSE '❓ OTHER'
    END as status
FROM crm.sfdc_dbx.properties_to_update
LIMIT 20;


-- ============================================================================
-- SUCCESS CRITERIA:
-- ============================================================================
-- ✅ TEST 1: >95% of records show property_name != company_name
-- ✅ TEST 2: <5% NULL company names (only legitimate missing data)
-- ✅ TEST 3: Known properties show correct company names (not property names)
-- ✅ TEST 4: properties_to_create view shows correct company names
-- ✅ TEST 5: properties_to_update view shows correct company names
-- ============================================================================
