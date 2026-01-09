%sql
-- Final filtered results: Remove all excluded properties from active_properties_companies
-- This cell should be placed at the end of the notebook

-- Step 1: Collect all property IDs to exclude
CREATE OR REPLACE TEMPORARY VIEW all_excluded_properties AS (
    -- IDV web portal properties
    SELECT DISTINCT p.id as property_id, 'IDV Web Portal' as exclusion_reason
    FROM rds.pg_rds_public.properties p
    LEFT JOIN rds.pg_rds_public.property_features pf ON pf.property_id = p.id
    WHERE p.status = 'ACTIVE'
      AND pf.feature_code = 'identity_verification_only_web_portal'

    UNION

    -- IDV only properties (from idv_only view)
    SELECT DISTINCT property_id, 'IDV Only' as exclusion_reason
    FROM idv_only

    UNION

    -- Partner properties (from partner_properties view)
    SELECT DISTINCT id as property_id, 'Partner Property' as exclusion_reason
    FROM partner_properties

    UNION

    -- Test properties (from test_properties view)
    SELECT DISTINCT property_id, 'Test Property' as exclusion_reason
    FROM test_properties

    UNION

    -- Phased out properties (from phased_out_properties view)
    SELECT DISTINCT property_id, 'Phased Out' as exclusion_reason
    FROM phased_out_properties
);

-- Step 2: Filter active_properties_companies to exclude all identified properties
CREATE OR REPLACE TEMPORARY VIEW final_active_properties_companies AS (
    SELECT
        apc.*
    FROM active_properties_companies apc
    LEFT JOIN all_excluded_properties ex
        ON apc.active_properties = ex.property_id
    WHERE ex.property_id IS NULL  -- Keep only properties NOT in exclusion list
);

-- Display final results
SELECT * FROM final_active_properties_companies;

-- COMMAND ----------

-- Summary: Show what was excluded
SELECT
    'Total Active Properties (Before Filtering)' as metric,
    COUNT(*) as count
FROM active_properties_companies

UNION ALL

SELECT
    'Properties Excluded' as metric,
    COUNT(DISTINCT ex.property_id) as count
FROM all_excluded_properties ex

UNION ALL

SELECT
    'Final Active Properties (After Filtering)' as metric,
    COUNT(*) as count
FROM final_active_properties_companies;

-- COMMAND ----------

-- Breakdown by exclusion reason
SELECT
    exclusion_reason,
    COUNT(DISTINCT property_id) as properties_excluded
FROM all_excluded_properties
GROUP BY exclusion_reason
ORDER BY properties_excluded DESC;

-- COMMAND ----------

-- Final aggregated counts (matching original query format)
SELECT
    COUNT(DISTINCT active_properties) as active_properties,
    COUNT(DISTINCT companies_with_active_properties) as companies_with_active_properties,
    SUM(property_units) as total_units
FROM final_active_properties_companies;
