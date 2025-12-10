-- ============================================================================
-- PEGASUS RESIDENTIAL - SIMPLE "CHECKBOX" VIEW (Daniel Cooper's Vision)
-- ============================================================================
-- This matches Daniel Cooper's "dream state" from the JIRA discussion:
-- "each applicant would show:
--   IDV: ✓
--   Bank Linking: ✓
--   Connected Payroll: ✗
--   Bank Statements: ✗
--   Pay Stubs: ✓
--   Ruling: Pass/Fail and a reason"
-- ============================================================================

WITH bal_enabled_properties AS (
    SELECT
        prop.id as property_id,
        prop.name as property_name,
        pf.updated_at AS date_bal_enabled
    FROM rds.pg_rds_public.properties prop
    JOIN rds.pg_rds_public.property_features pf ON prop.id = pf.property_id
    WHERE pf.feature_code = 'bank_linking'
      AND pf.state = 'enabled'
      AND prop.id NOT IN ('e7215b95-52aa-4593-8f1b-fd8d45de53fa', '09fba77e-a5b3-48cf-af34-662d65809b48')
),

applicant_base AS (
    SELECT
        e.id as entry_id,
        e.submission_time,
        f.property_id,
        prop.name as property_name,
        c.name as company_name,
        a.id as applicant_id,
        CONCAT(a.first_name, ' ', a.last_name) as applicant_name,
        a.email as applicant_email
    FROM rds.pg_rds_public.entries e
    JOIN rds.pg_rds_public.folders f ON f.id = e.folder_id
    JOIN rds.pg_rds_public.companies c ON c.id = f.company_id
    JOIN rds.pg_rds_public.properties prop ON prop.id = f.property_id
    JOIN bal_enabled_properties bal ON prop.id = bal.property_id
    JOIN rds.pg_rds_public.applicants a ON a.entry_id = e.id
    WHERE c.name = 'Pegasus Residential'
      AND e.submission_time >= bal.date_bal_enabled
      AND e.inserted_at >= current_date() - INTERVAL 7 DAYS
),

-- Detect which features each applicant used
feature_usage AS (
    SELECT
        ab.applicant_id,
        -- Bank Linking checkbox
        MAX(CASE WHEN asds.source_type = 'BANK_LINKING' THEN 1 ELSE 0 END) as used_bank_linking,

        -- Connected Payroll checkbox
        MAX(CASE WHEN asds.source_type = 'CONNECTED_PAYROLL' THEN 1 ELSE 0 END) as used_connected_payroll,

        -- Document Upload checkbox (bank statements, pay stubs, etc.)
        MAX(CASE WHEN asds.source_type = 'DOCUMENT_UPLOAD' THEN 1 ELSE 0 END) as used_document_upload,

        -- ID Verification checkbox
        MAX(CASE WHEN idv.id IS NOT NULL THEN 1 ELSE 0 END) as completed_id_verification,
        MAX(CASE WHEN idv.status = 'SUCCESS' THEN 1 ELSE 0 END) as id_verification_passed
    FROM applicant_base ab
    LEFT JOIN rds.pg_rds_public.applicant_submissions aps ON aps.applicant_id = ab.applicant_id
    LEFT JOIN rds.pg_rds_public.applicant_submission_document_sources asds ON asds.applicant_submission_id = aps.id
    LEFT JOIN rds.pg_rds_public.id_verifications idv ON idv.applicant_detail_id = ab.applicant_id
    GROUP BY ab.applicant_id
),

-- Get verification outcomes (pass/fail + reason)
verification_outcome AS (
    SELECT
        ab.applicant_id,
        -- Income verification
        MAX(CASE WHEN ivs.review_eligibility = 'ACCEPTED' THEN 1 ELSE 0 END) as income_passed,
        MAX(CASE WHEN ivs.review_eligibility = 'REJECTED' THEN 1 ELSE 0 END) as income_failed,
        STRING_AGG(DISTINCT ivs.review_eligibility, ', ') as income_review_statuses,
        STRING_AGG(DISTINCT ivs.rejection_reason, ', ') as income_rejection_reasons,

        -- Asset verification
        MAX(CASE WHEN avs.review_eligibility = 'ACCEPTED' THEN 1 ELSE 0 END) as asset_passed,
        MAX(CASE WHEN avs.review_eligibility = 'REJECTED' THEN 1 ELSE 0 END) as asset_failed,
        STRING_AGG(DISTINCT avs.review_eligibility, ', ') as asset_review_statuses,
        STRING_AGG(DISTINCT avs.rejection_reason, ', ') as asset_rejection_reasons
    FROM applicant_base ab
    LEFT JOIN rds.pg_rds_public.applicant_submissions aps ON aps.applicant_id = ab.applicant_id
    LEFT JOIN rds.pg_rds_public.applicant_submission_document_sources asds ON asds.applicant_submission_id = aps.id
    LEFT JOIN rds.pg_rds_public.income_verification_submissions ivs ON ivs.applicant_submission_document_source_id = asds.id
    LEFT JOIN rds.pg_rds_public.asset_verification_submissions avs ON avs.applicant_submission_document_source_id = asds.id
    GROUP BY ab.applicant_id
)

-- Final "checkbox" view matching Daniel Cooper's vision
SELECT
    ab.applicant_name,
    ab.applicant_email,
    ab.property_name,
    DATE(ab.submission_time) as submission_date,

    -- Feature checkboxes (✓ or ✗)
    CASE WHEN fu.completed_id_verification = 1 THEN '✓' ELSE '✗' END as idv_checkbox,
    CASE WHEN fu.used_bank_linking = 1 THEN '✓' ELSE '✗' END as bank_linking_checkbox,
    CASE WHEN fu.used_connected_payroll = 1 THEN '✓' ELSE '✗' END as connected_payroll_checkbox,
    CASE WHEN fu.used_document_upload = 1 THEN '✓' ELSE '✗' END as documents_checkbox,

    -- Ruling (Pass/Fail)
    CASE
        WHEN vo.income_passed = 1 OR vo.asset_passed = 1 THEN 'PASS'
        WHEN vo.income_failed = 1 OR vo.asset_failed = 1 THEN 'FAIL'
        WHEN fu.used_bank_linking = 1 OR fu.used_connected_payroll = 1 OR fu.used_document_upload = 1 THEN 'PENDING'
        ELSE 'NO SUBMISSION'
    END as ruling,

    -- Reason for ruling
    CASE
        WHEN vo.income_passed = 1 THEN 'Income verification accepted'
        WHEN vo.asset_passed = 1 THEN 'Asset verification accepted'
        WHEN vo.income_failed = 1 THEN CONCAT('Income rejected: ', COALESCE(vo.income_rejection_reasons, 'See details'))
        WHEN vo.asset_failed = 1 THEN CONCAT('Assets rejected: ', COALESCE(vo.asset_rejection_reasons, 'See details'))
        WHEN fu.used_bank_linking = 1 OR fu.used_connected_payroll = 1 OR fu.used_document_upload = 1 THEN 'Verification in progress'
        ELSE 'No financial data submitted'
    END as reason,

    -- Additional helpful fields
    CASE WHEN fu.id_verification_passed = 1 THEN 'YES' ELSE 'NO' END as id_verified_successfully,
    ab.entry_id as entry_id_for_lookup,
    ab.applicant_id as applicant_id_for_lookup

FROM applicant_base ab
LEFT JOIN feature_usage fu ON ab.applicant_id = fu.applicant_id
LEFT JOIN verification_outcome vo ON ab.applicant_id = vo.applicant_id

ORDER BY ab.submission_time DESC, ab.applicant_name;


-- ============================================================================
-- SUMMARY METRICS (for "first page" per Daniel Cooper's vision)
-- ============================================================================

WITH applicant_counts AS (
    SELECT
        COUNT(*) as total_applicants,
        SUM(CASE WHEN fu.completed_id_verification = 1 THEN 1 ELSE 0 END) as used_idv,
        SUM(CASE WHEN fu.used_bank_linking = 1 THEN 1 ELSE 0 END) as used_bank_linking,
        SUM(CASE WHEN fu.used_connected_payroll = 1 THEN 1 ELSE 0 END) as used_connected_payroll,
        SUM(CASE WHEN fu.used_document_upload = 1 THEN 1 ELSE 0 END) as used_documents,
        SUM(CASE WHEN vo.income_passed = 1 OR vo.asset_passed = 1 THEN 1 ELSE 0 END) as passed_count,
        SUM(CASE WHEN vo.income_failed = 1 OR vo.asset_failed = 1 THEN 1 ELSE 0 END) as failed_count
    FROM applicant_base ab
    LEFT JOIN feature_usage fu ON ab.applicant_id = fu.applicant_id
    LEFT JOIN verification_outcome vo ON ab.applicant_id = vo.applicant_id
)

SELECT
    'Total Applicants' as metric,
    total_applicants as count,
    '100%' as percentage
FROM applicant_counts

UNION ALL

SELECT
    'Used ID Verification',
    used_idv,
    CONCAT(ROUND(used_idv * 100.0 / NULLIF(total_applicants, 0), 1), '%')
FROM applicant_counts

UNION ALL

SELECT
    'Used Bank Linking',
    used_bank_linking,
    CONCAT(ROUND(used_bank_linking * 100.0 / NULLIF(total_applicants, 0), 1), '%')
FROM applicant_counts

UNION ALL

SELECT
    'Used Connected Payroll',
    used_connected_payroll,
    CONCAT(ROUND(used_connected_payroll * 100.0 / NULLIF(total_applicants, 0), 1), '%')
FROM applicant_counts

UNION ALL

SELECT
    'Used Document Upload',
    used_documents,
    CONCAT(ROUND(used_documents * 100.0 / NULLIF(total_applicants, 0), 1), '%')
FROM applicant_counts

UNION ALL

SELECT
    'PASSED Verification',
    passed_count,
    CONCAT(ROUND(passed_count * 100.0 / NULLIF(total_applicants, 0), 1), '%')
FROM applicant_counts

UNION ALL

SELECT
    'FAILED Verification',
    failed_count,
    CONCAT(ROUND(failed_count * 100.0 / NULLIF(total_applicants, 0), 1), '%')
FROM applicant_counts;
