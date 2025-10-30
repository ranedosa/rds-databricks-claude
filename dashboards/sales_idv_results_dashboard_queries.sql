-- Sales-Focused IDV Results Dashboard
-- Purpose: Customer-facing dashboard for sales demos showing ID verification results
-- Created: 2025-10-30

-- ============================================================================
-- QUERY 1: Executive Summary Metrics
-- ============================================================================
-- Widget: Counter Cards (Total Scans, Pass Rate, Active Properties)
SELECT
    COUNT(*) AS total_idv_scans,
    COUNT(DISTINCT property_id) AS active_properties,
    COUNT(DISTINCT company_id) AS active_companies,
    SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) AS passed_scans,
    SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) AS failed_scans,
    SUM(CASE WHEN status = 'NEEDS REVIEW' THEN 1 ELSE 0 END) AS needs_review_scans,
    ROUND(SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pass_rate_percentage,
    ROUND(SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS fail_rate_percentage
FROM rds.pg_rds_public.id_verifications
WHERE results_provided_at IS NOT NULL
    AND inserted_at BETWEEN :start_date AND :end_date
    AND (:company_filter IS NULL OR company_id = :company_filter)
    AND (:property_filter IS NULL OR property_id = :property_filter);

-- ============================================================================
-- QUERY 2: Company Overview with Filtering
-- ============================================================================
-- Widget: Table with company-level aggregates
SELECT
    c.name AS company_name,
    c.short_id AS company_id,
    COUNT(DISTINCT p.id) AS num_properties,
    COUNT(DISTINCT iv.id) AS total_scans,
    SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) AS passed,
    SUM(CASE WHEN iv.status = 'FAIL' THEN 1 ELSE 0 END) AS failed,
    SUM(CASE WHEN iv.status = 'NEEDS REVIEW' THEN 1 ELSE 0 END) AS needs_review,
    ROUND(SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) * 100.0 / COUNT(iv.id), 1) AS pass_rate,
    MIN(iv.inserted_at) AS first_scan_date,
    MAX(iv.inserted_at) AS most_recent_scan_date
FROM rds.pg_rds_public.companies c
JOIN rds.pg_rds_public.properties p ON c.id = p.company_id
JOIN rds.pg_rds_public.id_verifications iv ON p.id = iv.property_id
WHERE iv.results_provided_at IS NOT NULL
    AND iv.inserted_at BETWEEN :start_date AND :end_date
    AND p.identity_verification_enabled = TRUE
GROUP BY c.name, c.short_id
ORDER BY total_scans DESC;

-- ============================================================================
-- QUERY 3: Property-Level Performance
-- ============================================================================
-- Widget: Detailed property table with drill-down capability
SELECT
    p.name AS property_name,
    c.name AS company_name,
    p.state AS property_state,
    p.city AS property_city,
    p.identity_verification_provider AS idv_provider,
    COUNT(iv.id) AS total_scans,
    SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) AS passed,
    SUM(CASE WHEN iv.status = 'FAIL' THEN 1 ELSE 0 END) AS failed,
    SUM(CASE WHEN iv.status = 'NEEDS REVIEW' THEN 1 ELSE 0 END) AS needs_review,
    ROUND(SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) * 100.0 / COUNT(iv.id), 1) AS pass_rate,
    MIN(iv.inserted_at) AS first_scan_date,
    MAX(iv.inserted_at) AS most_recent_scan_date,
    DATEDIFF(CURRENT_DATE, MAX(iv.inserted_at)) AS days_since_last_scan
FROM rds.pg_rds_public.properties p
JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
JOIN rds.pg_rds_public.id_verifications iv ON p.id = iv.property_id
WHERE iv.results_provided_at IS NOT NULL
    AND iv.inserted_at BETWEEN :start_date AND :end_date
    AND (:company_filter IS NULL OR c.id = :company_filter)
GROUP BY p.name, c.name, p.state, p.city, p.identity_verification_provider
ORDER BY total_scans DESC;

-- ============================================================================
-- QUERY 4: IDV Volume Trends Over Time
-- ============================================================================
-- Widget: Stacked bar chart showing pass/fail trends
SELECT
    DATE_TRUNC('day', iv.inserted_at) AS scan_date,
    iv.status,
    COUNT(*) AS scan_count
FROM rds.pg_rds_public.id_verifications iv
JOIN rds.pg_rds_public.properties p ON iv.property_id = p.id
JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
WHERE iv.results_provided_at IS NOT NULL
    AND iv.inserted_at BETWEEN :start_date AND :end_date
    AND (:company_filter IS NULL OR c.id = :company_filter)
    AND (:property_filter IS NULL OR p.id = :property_filter)
GROUP BY DATE_TRUNC('day', iv.inserted_at), iv.status
ORDER BY scan_date ASC, iv.status;

-- ============================================================================
-- QUERY 5: Pass/Fail Distribution
-- ============================================================================
-- Widget: Pie chart showing overall status distribution
SELECT
    iv.status,
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM rds.pg_rds_public.id_verifications iv
JOIN rds.pg_rds_public.properties p ON iv.property_id = p.id
JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
WHERE iv.results_provided_at IS NOT NULL
    AND iv.inserted_at BETWEEN :start_date AND :end_date
    AND (:company_filter IS NULL OR c.id = :company_filter)
    AND (:property_filter IS NULL OR p.id = :property_filter)
GROUP BY iv.status
ORDER BY count DESC;

-- ============================================================================
-- QUERY 6: Failure Reasons Breakdown
-- ============================================================================
-- Widget: Bar chart showing why verifications fail
SELECT
    iv.score_reason AS failure_reason,
    COUNT(*) AS failure_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage_of_failures
FROM rds.pg_rds_public.id_verifications iv
JOIN rds.pg_rds_public.properties p ON iv.property_id = p.id
JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
WHERE iv.results_provided_at IS NOT NULL
    AND iv.status = 'FAIL'
    AND iv.inserted_at BETWEEN :start_date AND :end_date
    AND (:company_filter IS NULL OR c.id = :company_filter)
    AND (:property_filter IS NULL OR p.id = :property_filter)
GROUP BY iv.score_reason
ORDER BY failure_count DESC
LIMIT 10;

-- ============================================================================
-- QUERY 7: Recent Submissions Detail
-- ============================================================================
-- Widget: Detailed table of recent individual submissions
SELECT
    iv.inserted_at AS scan_date,
    c.name AS company_name,
    p.name AS property_name,
    p.state AS property_state,
    iv.status,
    iv.score_reason,
    iv.provider AS idv_provider,
    CASE
        WHEN iv.provider = 'clear' THEN
            CASE
                WHEN get_json_object(iv.provider_session_info, '$.flowType') = 'full' THEN 'Enhanced'
                WHEN get_json_object(iv.provider_session_info, '$.flowType') = 'lite' THEN 'Basic'
                ELSE 'N/A'
            END
        ELSE 'N/A'
    END AS verification_level,
    DATEDIFF(CURRENT_DATE, DATE(iv.inserted_at)) AS days_ago
FROM rds.pg_rds_public.id_verifications iv
JOIN rds.pg_rds_public.properties p ON iv.property_id = p.id
JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
WHERE iv.results_provided_at IS NOT NULL
    AND iv.inserted_at BETWEEN :start_date AND :end_date
    AND (:company_filter IS NULL OR c.id = :company_filter)
    AND (:property_filter IS NULL OR p.id = :property_filter)
ORDER BY iv.inserted_at DESC
LIMIT 100;

-- ============================================================================
-- QUERY 8: Weekly Performance Summary
-- ============================================================================
-- Widget: Line chart showing weekly pass rate trends
SELECT
    DATE_TRUNC('week', iv.inserted_at) AS week_start,
    COUNT(*) AS total_scans,
    SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) AS passed,
    SUM(CASE WHEN iv.status = 'FAIL' THEN 1 ELSE 0 END) AS failed,
    ROUND(SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pass_rate
FROM rds.pg_rds_public.id_verifications iv
JOIN rds.pg_rds_public.properties p ON iv.property_id = p.id
JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
WHERE iv.results_provided_at IS NOT NULL
    AND iv.inserted_at BETWEEN :start_date AND :end_date
    AND (:company_filter IS NULL OR c.id = :company_filter)
    AND (:property_filter IS NULL OR p.id = :property_filter)
GROUP BY DATE_TRUNC('week', iv.inserted_at)
ORDER BY week_start ASC;

-- ============================================================================
-- QUERY 9: Provider Performance Comparison
-- ============================================================================
-- Widget: Bar chart comparing CLEAR vs Incode performance
SELECT
    CASE
        WHEN iv.provider = 'clear' THEN 'CLEAR'
        WHEN iv.provider = 'incode' THEN 'Incode'
        ELSE 'Other'
    END AS idv_provider,
    COUNT(*) AS total_scans,
    SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) AS passed,
    SUM(CASE WHEN iv.status = 'FAIL' THEN 1 ELSE 0 END) AS failed,
    ROUND(SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pass_rate
FROM rds.pg_rds_public.id_verifications iv
JOIN rds.pg_rds_public.properties p ON iv.property_id = p.id
JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
WHERE iv.results_provided_at IS NOT NULL
    AND iv.inserted_at BETWEEN :start_date AND :end_date
    AND (:company_filter IS NULL OR c.id = :company_filter)
    AND (:property_filter IS NULL OR p.id = :property_filter)
    AND iv.provider IN ('clear', 'incode')
GROUP BY CASE
        WHEN iv.provider = 'clear' THEN 'CLEAR'
        WHEN iv.provider = 'incode' THEN 'Incode'
        ELSE 'Other'
    END
ORDER BY total_scans DESC;

-- ============================================================================
-- QUERY 10: Geographic Performance Distribution
-- ============================================================================
-- Widget: Map or table showing performance by state
SELECT
    p.state AS property_state,
    COUNT(DISTINCT p.id) AS num_properties,
    COUNT(iv.id) AS total_scans,
    SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) AS passed,
    SUM(CASE WHEN iv.status = 'FAIL' THEN 1 ELSE 0 END) AS failed,
    ROUND(SUM(CASE WHEN iv.status = 'PASS' THEN 1 ELSE 0 END) * 100.0 / COUNT(iv.id), 2) AS pass_rate
FROM rds.pg_rds_public.properties p
JOIN rds.pg_rds_public.id_verifications iv ON p.id = iv.property_id
JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
WHERE iv.results_provided_at IS NOT NULL
    AND iv.inserted_at BETWEEN :start_date AND :end_date
    AND (:company_filter IS NULL OR c.id = :company_filter)
    AND p.state IS NOT NULL
GROUP BY p.state
ORDER BY total_scans DESC;

-- ============================================================================
-- QUERY 11: Company List for Filter
-- ============================================================================
-- Widget: Filter dropdown
SELECT DISTINCT
    c.id AS company_id,
    c.name AS company_name
FROM rds.pg_rds_public.companies c
JOIN rds.pg_rds_public.properties p ON c.id = p.company_id
WHERE p.identity_verification_enabled = TRUE
ORDER BY c.name ASC;

-- ============================================================================
-- QUERY 12: Property List for Filter (filtered by company)
-- ============================================================================
-- Widget: Filter dropdown
SELECT DISTINCT
    p.id AS property_id,
    p.name AS property_name,
    c.name AS company_name
FROM rds.pg_rds_public.properties p
JOIN rds.pg_rds_public.companies c ON p.company_id = c.id
WHERE p.identity_verification_enabled = TRUE
    AND (:company_filter IS NULL OR c.id = :company_filter)
ORDER BY c.name ASC, p.name ASC;

-- ============================================================================
-- Parameters for Dashboard:
-- :start_date - Date range start (default: 30 days ago)
-- :end_date - Date range end (default: today)
-- :company_filter - Company ID (optional, for filtering to specific company)
-- :property_filter - Property ID (optional, for filtering to specific property)
-- ============================================================================
