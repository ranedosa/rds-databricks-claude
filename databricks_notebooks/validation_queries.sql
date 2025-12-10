-- VALIDATION QUERIES: Compare Dashboard Data vs My Notebook Queries
-- Run these in Databricks to identify discrepancies
-- Each query below will return a separate result table

-- ============================================================================
-- VALIDATION 1a: Count from pre-aggregated table (what dashboard uses)
-- ============================================================================
SELECT 'Pre-Aggregated Table' as source
    , COUNT(DISTINCT fde_submission_id) as total_submissions
    , COUNT(DISTINCT CASE WHEN fde_company_name = 'Pegasus Residential' THEN fde_submission_id END) as pegasus_submissions
FROM product.iv.unity_calc_iv_cp_submission_level_results
WHERE fde_submission_time >= current_date() - INTERVAL 7 DAYS;

-- ============================================================================
-- VALIDATION 1b: Count from raw tables (what my notebook uses)
-- ============================================================================
SELECT 'Raw Tables' as source
    , COUNT(DISTINCT e.id) as total_submissions
    , COUNT(DISTINCT CASE WHEN c.name = 'Pegasus Residential' THEN e.id END) as pegasus_submissions
FROM rds.pg_rds_public.entries e
JOIN rds.pg_rds_public.folders f ON f.id = e.folder_id
JOIN rds.pg_rds_public.companies c ON c.id = f.company_id
WHERE e.inserted_at >= current_date() - INTERVAL 7 DAYS;

-- ============================================================================
-- VALIDATION 2: Check bank linking detection differences
-- ============================================================================
WITH dashboard_bal AS (
    SELECT DISTINCT e.id AS entry_id
    FROM rds.pg_rds_public.applicant_submission_document_sources ds
    JOIN rds.pg_rds_public.applicant_submissions app_sub ON ds.applicant_submission_id = app_sub.id
    JOIN rds.pg_rds_public.applicants app ON app_sub.applicant_id = app.id
    JOIN rds.pg_rds_public.entries e ON e.id = app.entry_id
    WHERE ds.source_type = 'BANK_LINKING'
),
my_notebook_bal AS (
    SELECT DISTINCT e.id AS entry_id
    FROM rds.pg_rds_public.entries e
    JOIN rds.pg_rds_public.applicants a ON a.entry_id = e.id
    JOIN rds.pg_rds_public.applicant_submissions aps ON aps.applicant_id = a.id
    JOIN rds.pg_rds_public.applicant_submission_document_sources asds ON asds.applicant_submission_id = aps.id
    WHERE asds.source_type = 'BANK_LINKING'
),
comparison AS (
    SELECT 'In Dashboard but not Notebook' as category, COUNT(*) as count
    FROM dashboard_bal WHERE entry_id NOT IN (SELECT entry_id FROM my_notebook_bal)

    UNION ALL

    SELECT 'In Notebook but not Dashboard' as category, COUNT(*) as count
    FROM my_notebook_bal WHERE entry_id NOT IN (SELECT entry_id FROM dashboard_bal)

    UNION ALL

    SELECT 'In Both' as category, COUNT(*) as count
    FROM dashboard_bal WHERE entry_id IN (SELECT entry_id FROM my_notebook_bal)
)
SELECT * FROM comparison;

-- ============================================================================
-- VALIDATION 3: Check date field differences (submission_time vs inserted_at)
-- ============================================================================
SELECT
    e.id as entry_id,
    e.inserted_at,
    e.submission_time,
    DATEDIFF(e.submission_time, e.inserted_at) as day_difference
FROM rds.pg_rds_public.entries e
JOIN rds.pg_rds_public.folders f ON f.id = e.folder_id
JOIN rds.pg_rds_public.companies c ON c.id = f.company_id
WHERE c.name = 'Pegasus Residential'
  AND e.inserted_at >= current_date() - INTERVAL 7 DAYS
ORDER BY day_difference DESC
LIMIT 100;

-- ============================================================================
-- VALIDATION 4: Check "bal_enabled_properties" filtering impact
-- ============================================================================
WITH bal_enabled_properties AS (
    SELECT prop.id as property_id, pf.updated_at AS date_bal_enabled
    FROM rds.pg_rds_public.properties prop
    RIGHT JOIN rds.pg_rds_public.property_features pf on prop.id = pf.property_id
    WHERE pf.feature_code = "bank_linking"
    AND pf.state = 'enabled'
    AND prop.id NOT IN ("e7215b95-52aa-4593-8f1b-fd8d45de53fa", "09fba77e-a5b3-48cf-af34-662d65809b48")
),
counts AS (
    SELECT 'Total Pegasus Entries' as category, COUNT(DISTINCT e.id) as count
    FROM rds.pg_rds_public.entries e
    JOIN rds.pg_rds_public.folders f ON f.id = e.folder_id
    JOIN rds.pg_rds_public.companies c ON c.id = f.company_id
    WHERE c.name = 'Pegasus Residential'
      AND e.inserted_at >= current_date() - INTERVAL 7 DAYS

    UNION ALL

    SELECT 'Pegasus Entries (BAL-enabled properties only)' as category, COUNT(DISTINCT e.id) as count
    FROM rds.pg_rds_public.entries e
    JOIN rds.pg_rds_public.folders f ON f.id = e.folder_id
    JOIN rds.pg_rds_public.companies c ON c.id = f.company_id
    JOIN rds.pg_rds_public.properties prop ON prop.id = f.property_id
    JOIN bal_enabled_properties bal ON prop.id = bal.property_id
    WHERE c.name = 'Pegasus Residential'
      AND e.inserted_at >= current_date() - INTERVAL 7 DAYS

    UNION ALL

    SELECT 'Pegasus Entries (after BAL enabled date)' as category, COUNT(DISTINCT e.id) as count
    FROM rds.pg_rds_public.entries e
    JOIN rds.pg_rds_public.folders f ON f.id = e.folder_id
    JOIN rds.pg_rds_public.companies c ON c.id = f.company_id
    JOIN rds.pg_rds_public.properties prop ON prop.id = f.property_id
    JOIN bal_enabled_properties bal ON prop.id = bal.property_id
    WHERE c.name = 'Pegasus Residential'
      AND e.submission_time >= bal.date_bal_enabled
      AND e.inserted_at >= current_date() - INTERVAL 7 DAYS
)
SELECT * FROM counts;

-- ============================================================================
-- VALIDATION 5: Check success rate calculation differences
-- ============================================================================
WITH dashboard_approach AS (
    SELECT
        'Dashboard Approach' as method,
        SUM(CASE WHEN is_calculated_status = 1 THEN 1 ELSE 0 END) as success_count,
        COUNT(*) as total_count,
        ROUND(SUM(CASE WHEN is_calculated_status = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate
    FROM product.iv.unity_calc_iv_cp_submission_level_results base
    LEFT JOIN (
        SELECT DISTINCT e.id AS entry_id
        FROM rds.pg_rds_public.applicant_submission_document_sources ds
        JOIN rds.pg_rds_public.applicant_submissions app_sub ON ds.applicant_submission_id = app_sub.id
        JOIN rds.pg_rds_public.applicants app ON app_sub.applicant_id = app.id
        JOIN rds.pg_rds_public.entries e ON e.id = app.entry_id
        WHERE ds.source_type = 'BANK_LINKING'
    ) bank ON base.fde_submission_id = bank.entry_id
    WHERE base.fde_company_name = 'Pegasus Residential'
      AND base.fde_submission_time >= current_date() - INTERVAL 7 DAYS
      AND bank.entry_id IS NOT NULL
),
notebook_approach AS (
    SELECT
        'Notebook Approach' as method,
        COUNT(DISTINCT CASE WHEN (ivs.review_eligibility = 'ACCEPTED' OR avs.review_eligibility = 'ACCEPTED') THEN e.id END) as success_count,
        COUNT(DISTINCT CASE WHEN asds.source_type = 'BANK_LINKING' THEN e.id END) as total_count,
        ROUND(COUNT(DISTINCT CASE WHEN asds.source_type = 'BANK_LINKING'
                             AND (ivs.review_eligibility = 'ACCEPTED' OR avs.review_eligibility = 'ACCEPTED')
                             THEN e.id END) * 100.0 /
              NULLIF(COUNT(DISTINCT CASE WHEN asds.source_type = 'BANK_LINKING' THEN e.id END), 0), 2) as success_rate
    FROM rds.pg_rds_public.entries e
    JOIN rds.pg_rds_public.folders f ON f.id = e.folder_id
    JOIN rds.pg_rds_public.companies c ON c.id = f.company_id
    LEFT JOIN rds.pg_rds_public.applicants a ON a.entry_id = e.id
    LEFT JOIN rds.pg_rds_public.applicant_submissions aps ON aps.applicant_id = a.id
    LEFT JOIN rds.pg_rds_public.applicant_submission_document_sources asds ON asds.applicant_submission_id = aps.id
    LEFT JOIN rds.pg_rds_public.income_verification_submissions ivs ON ivs.applicant_submission_document_source_id = asds.id
    LEFT JOIN rds.pg_rds_public.asset_verification_submissions avs ON avs.applicant_submission_document_source_id = asds.id
    WHERE c.name = 'Pegasus Residential'
      AND e.inserted_at >= current_date() - INTERVAL 7 DAYS
)
SELECT * FROM dashboard_approach
UNION ALL
SELECT * FROM notebook_approach;

-- ============================================================================
-- VALIDATION 6: Check if Pegasus has bank linking enabled
-- ============================================================================
SELECT
    p.name as property_name,
    pf.feature_code,
    pf.state,
    pf.updated_at as date_enabled
FROM rds.pg_rds_public.properties p
JOIN rds.pg_rds_public.companies c ON c.id = p.company_id
JOIN rds.pg_rds_public.property_features pf ON pf.property_id = p.id
WHERE c.name = 'Pegasus Residential'
  AND pf.feature_code = 'bank_linking'
ORDER BY pf.updated_at DESC;
