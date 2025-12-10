# Databricks notebook source
# MAGIC %md
# MAGIC # Pegasus Residential Bank Linking Beta - Applicant Level Report
# MAGIC
# MAGIC This notebook provides a comprehensive **applicant-level** view of Pegasus Residential's bank linking beta program.
# MAGIC
# MAGIC ## Report Sections:
# MAGIC 1. **Applicant-Level Detail** - Complete view of each applicant's journey
# MAGIC 2. **Executive Summary** - High-level KPIs and metrics
# MAGIC 3. **Issue Detection** - Glitches and anomalies flagged for review
# MAGIC 4. **Property Performance** - Comparison across Pegasus properties
# MAGIC
# MAGIC ## Requirements Met:
# MAGIC - ✅ Clear view of bank linking adoption and usage
# MAGIC - ✅ Number of applications through bank linking
# MAGIC - ✅ Number of applications through ID verification (correlation tracked)
# MAGIC - ✅ Pass/Fail recommendations tied to outcomes
# MAGIC - ✅ Clear indication of whether program is used as intended
# MAGIC - ✅ Visibility into decisions made
# MAGIC - ✅ Callouts for glitches or issues
# MAGIC - ✅ **Data at applicant level** (not aggregated)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. APPLICANT-LEVEL DETAIL
# MAGIC
# MAGIC This is the **primary report** showing each individual applicant's bank linking journey, ID verification status, pass/fail outcomes, and any issues detected.

# COMMAND ----------

# DBTITLE 1,Main Applicant-Level Report
applicant_report = spark.sql("""
-- APPLICANT-LEVEL DETAIL FOR PEGASUS RESIDENTIAL BANK LINKING BETA

WITH bal_enabled_properties AS (
    -- Get all properties where bank linking is enabled
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

applicant_details AS (
    -- Get core applicant and entry information
    SELECT
        e.id as entry_id,
        e.submission_time,
        e.inserted_at,
        f.id as folder_id,
        f.property_id,
        prop.name as property_name,
        c.name as company_name,
        a.id as applicant_id,
        a.first_name,
        a.last_name,
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

bank_linking_usage AS (
    -- Identify which applicants used bank linking
    SELECT
        ad.applicant_id,
        ad.entry_id,
        MAX(CASE WHEN asds.source_type = 'BANK_LINKING' THEN 1 ELSE 0 END) as used_bank_linking,
        MAX(CASE WHEN asds.source_type = 'CONNECTED_PAYROLL' THEN 1 ELSE 0 END) as used_connected_payroll,
        MAX(CASE WHEN asds.source_type = 'DOCUMENT_UPLOAD' THEN 1 ELSE 0 END) as used_document_upload,
        COUNT(DISTINCT aps.id) as total_submissions,
        COUNT(DISTINCT CASE WHEN asds.source_type = 'BANK_LINKING' THEN aps.id END) as bank_linking_submissions,
        MIN(CASE WHEN asds.source_type = 'BANK_LINKING' THEN aps.created_at END) as first_bank_linking_time,
        MAX(CASE WHEN asds.source_type = 'BANK_LINKING' THEN aps.created_at END) as last_bank_linking_time
    FROM applicant_details ad
    LEFT JOIN rds.pg_rds_public.applicant_submissions aps ON aps.applicant_id = ad.applicant_id
    LEFT JOIN rds.pg_rds_public.applicant_submission_document_sources asds ON asds.applicant_submission_id = aps.id
    GROUP BY ad.applicant_id, ad.entry_id
),

id_verification_status AS (
    -- Track ID verification for correlation
    SELECT
        ad.applicant_id,
        ad.entry_id,
        COUNT(DISTINCT idv.id) as id_verification_count,
        MAX(idv.status) as id_verification_status,
        MAX(idv.created_at) as id_verification_time,
        MAX(CASE WHEN idv.status = 'SUCCESS' THEN 1 ELSE 0 END) as id_verified_successfully
    FROM applicant_details ad
    LEFT JOIN rds.pg_rds_public.id_verifications idv ON idv.applicant_detail_id = ad.applicant_id
    GROUP BY ad.applicant_id, ad.entry_id
),

income_verification_results AS (
    -- Get income verification outcomes
    SELECT
        ad.applicant_id,
        COUNT(DISTINCT ivs.id) as income_verification_count,
        MAX(CASE WHEN ivs.review_eligibility = 'ACCEPTED' THEN 1 ELSE 0 END) as income_accepted,
        MAX(CASE WHEN ivs.review_eligibility = 'REJECTED' THEN 1 ELSE 0 END) as income_rejected,
        MAX(ivs.review_eligibility) as income_review_status,
        CONCAT_WS(', ', COLLECT_SET(ivs.rejection_reason)) as income_rejection_reasons
    FROM applicant_details ad
    LEFT JOIN rds.pg_rds_public.applicant_submissions aps ON aps.applicant_id = ad.applicant_id
    LEFT JOIN rds.pg_rds_public.applicant_submission_document_sources asds ON asds.applicant_submission_id = aps.id
    LEFT JOIN rds.pg_rds_public.income_verification_submissions ivs ON ivs.applicant_submission_document_source_id = asds.id
    WHERE asds.source_type = 'BANK_LINKING' OR asds.source_type IS NULL
    GROUP BY ad.applicant_id
),

asset_verification_results AS (
    -- Get asset verification outcomes
    SELECT
        ad.applicant_id,
        COUNT(DISTINCT avs.id) as asset_verification_count,
        MAX(CASE WHEN avs.review_eligibility = 'ACCEPTED' THEN 1 ELSE 0 END) as asset_accepted,
        MAX(CASE WHEN avs.review_eligibility = 'REJECTED' THEN 1 ELSE 0 END) as asset_rejected,
        MAX(avs.review_eligibility) as asset_review_status,
        CONCAT_WS(', ', COLLECT_SET(avs.rejection_reason)) as asset_rejection_reasons
    FROM applicant_details ad
    LEFT JOIN rds.pg_rds_public.applicant_submissions aps ON aps.applicant_id = ad.applicant_id
    LEFT JOIN rds.pg_rds_public.applicant_submission_document_sources asds ON asds.applicant_submission_id = aps.id
    LEFT JOIN rds.pg_rds_public.asset_verification_submissions avs ON avs.applicant_submission_document_source_id = asds.id
    WHERE asds.source_type = 'BANK_LINKING' OR asds.source_type IS NULL
    GROUP BY ad.applicant_id
),

issue_detection AS (
    -- Detect potential issues or anomalies
    SELECT
        ad.applicant_id,
        CASE
            WHEN bal.used_bank_linking = 1 AND idv.id_verification_count = 0 THEN 'NO_ID_VERIFICATION'
            WHEN bal.used_bank_linking = 1 AND ivr.income_verification_count = 0 AND avr.asset_verification_count = 0 THEN 'NO_VERIFICATION_RESULTS'
            WHEN bal.bank_linking_submissions > 3 THEN 'MULTIPLE_ATTEMPTS'
            WHEN (UNIX_TIMESTAMP(bal.last_bank_linking_time) - UNIX_TIMESTAMP(bal.first_bank_linking_time)) / 60 > 60 THEN 'LONG_COMPLETION_TIME'
            ELSE NULL
        END as issue_flag,
        CASE
            WHEN bal.used_bank_linking = 1 AND idv.id_verification_count = 0 THEN 'Bank linking used but no ID verification found - possible data sync issue'
            WHEN bal.used_bank_linking = 1 AND ivr.income_verification_count = 0 AND avr.asset_verification_count = 0 THEN 'Bank linking used but no income/asset verification results - possible processing failure'
            WHEN bal.bank_linking_submissions > 3 THEN 'More than 3 bank linking submissions - user may be experiencing difficulties'
            WHEN (UNIX_TIMESTAMP(bal.last_bank_linking_time) - UNIX_TIMESTAMP(bal.first_bank_linking_time)) / 60 > 60 THEN 'Took more than 60 minutes to complete - possible abandonment and return'
            ELSE NULL
        END as issue_description
    FROM applicant_details ad
    LEFT JOIN bank_linking_usage bal ON ad.applicant_id = bal.applicant_id
    LEFT JOIN id_verification_status idv ON ad.applicant_id = idv.applicant_id
    LEFT JOIN income_verification_results ivr ON ad.applicant_id = ivr.applicant_id
    LEFT JOIN asset_verification_results avr ON ad.applicant_id = avr.applicant_id
)

-- Final applicant-level report
SELECT
    -- Applicant Identification
    ad.entry_id,
    ad.applicant_id,
    ad.applicant_name,
    ad.applicant_email,
    ad.property_name,
    DATE(ad.submission_time) as submission_date,
    ad.submission_time,

    -- Bank Linking Adoption
    CASE WHEN bal.used_bank_linking = 1 THEN 'YES' ELSE 'NO' END as used_bank_linking,
    bal.bank_linking_submissions,
    bal.first_bank_linking_time,
    ROUND((UNIX_TIMESTAMP(bal.last_bank_linking_time) - UNIX_TIMESTAMP(bal.first_bank_linking_time)) / 60, 2) as bank_linking_duration_minutes,

    -- Alternative Methods Used
    CASE WHEN bal.used_connected_payroll = 1 THEN 'YES' ELSE 'NO' END as used_connected_payroll,
    CASE WHEN bal.used_document_upload = 1 THEN 'YES' ELSE 'NO' END as used_document_upload,
    bal.total_submissions as total_applicant_submissions,

    -- ID Verification Correlation
    idv.id_verification_count,
    idv.id_verification_status,
    CASE WHEN idv.id_verified_successfully = 1 THEN 'YES' ELSE 'NO' END as id_verified,
    CASE
        WHEN bal.used_bank_linking = 1 AND idv.id_verification_count > 0 THEN 'CORRELATED'
        WHEN bal.used_bank_linking = 1 AND idv.id_verification_count = 0 THEN 'MISSING_ID_VERIFICATION'
        WHEN bal.used_bank_linking = 0 AND idv.id_verification_count > 0 THEN 'ID_ONLY'
        ELSE 'NO_VERIFICATION'
    END as correlation_status,

    -- Income Verification Results
    ivr.income_verification_count,
    ivr.income_review_status,
    CASE WHEN ivr.income_accepted = 1 THEN 'PASS' ELSE 'FAIL' END as income_pass_fail,
    ivr.income_rejection_reasons,

    -- Asset Verification Results
    avr.asset_verification_count,
    avr.asset_review_status,
    CASE WHEN avr.asset_accepted = 1 THEN 'PASS' ELSE 'FAIL' END as asset_pass_fail,
    avr.asset_rejection_reasons,

    -- Overall Recommendation
    CASE
        WHEN ivr.income_accepted = 1 OR avr.asset_accepted = 1 THEN 'PASS'
        WHEN ivr.income_rejected = 1 OR avr.asset_rejected = 1 THEN 'FAIL'
        WHEN ivr.income_verification_count > 0 OR avr.asset_verification_count > 0 THEN 'PENDING'
        ELSE 'NO_DECISION'
    END as overall_recommendation,

    -- Program Usage Validation
    CASE
        WHEN bal.used_bank_linking = 1 AND idv.id_verification_count > 0 AND (ivr.income_verification_count > 0 OR avr.asset_verification_count > 0) THEN 'PROPER_USAGE'
        WHEN bal.used_bank_linking = 1 AND idv.id_verification_count = 0 THEN 'INCOMPLETE_WORKFLOW'
        WHEN bal.used_bank_linking = 0 THEN 'NOT_USING_BANK_LINKING'
        ELSE 'PARTIAL_USAGE'
    END as usage_assessment,

    -- Issue Detection
    iss.issue_flag,
    iss.issue_description,

    -- Timing Analysis
    ROUND((UNIX_TIMESTAMP(CURRENT_TIMESTAMP()) - UNIX_TIMESTAMP(ad.submission_time)) / 3600, 2) as hours_since_submission,
    CASE
        WHEN (UNIX_TIMESTAMP(CURRENT_TIMESTAMP()) - UNIX_TIMESTAMP(ad.submission_time)) / 3600 > 48 THEN 'DELAYED'
        ELSE 'TIMELY'
    END as processing_timeliness

FROM applicant_details ad
LEFT JOIN bank_linking_usage bal ON ad.applicant_id = bal.applicant_id
LEFT JOIN id_verification_status idv ON ad.applicant_id = idv.applicant_id
LEFT JOIN income_verification_results ivr ON ad.applicant_id = ivr.applicant_id
LEFT JOIN asset_verification_results avr ON ad.applicant_id = avr.applicant_id
LEFT JOIN issue_detection iss ON ad.applicant_id = iss.applicant_id

ORDER BY ad.submission_time DESC, ad.applicant_name
""")

display(applicant_report)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. EXECUTIVE SUMMARY
# MAGIC
# MAGIC High-level KPIs showing bank linking adoption, ID verification correlation, pass/fail rates, and issue detection.

# COMMAND ----------

# DBTITLE 1,Executive Summary Metrics
summary_metrics = spark.sql("""
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

applicant_details AS (
    SELECT
        e.id as entry_id,
        e.submission_time,
        e.inserted_at,
        f.id as folder_id,
        f.property_id,
        prop.name as property_name,
        c.name as company_name,
        a.id as applicant_id,
        a.first_name,
        a.last_name,
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

bank_linking_usage AS (
    SELECT
        ad.applicant_id,
        ad.entry_id,
        MAX(CASE WHEN asds.source_type = 'BANK_LINKING' THEN 1 ELSE 0 END) as used_bank_linking
    FROM applicant_details ad
    LEFT JOIN rds.pg_rds_public.applicant_submissions aps ON aps.applicant_id = ad.applicant_id
    LEFT JOIN rds.pg_rds_public.applicant_submission_document_sources asds ON asds.applicant_submission_id = aps.id
    GROUP BY ad.applicant_id, ad.entry_id
),

id_verification_status AS (
    SELECT
        ad.applicant_id,
        ad.entry_id,
        COUNT(DISTINCT idv.id) as id_verification_count
    FROM applicant_details ad
    LEFT JOIN rds.pg_rds_public.id_verifications idv ON idv.applicant_detail_id = ad.applicant_id
    GROUP BY ad.applicant_id, ad.entry_id
),

income_verification_results AS (
    SELECT
        ad.applicant_id,
        COUNT(DISTINCT ivs.id) as income_verification_count,
        MAX(CASE WHEN ivs.review_eligibility = 'ACCEPTED' THEN 1 ELSE 0 END) as income_accepted,
        MAX(CASE WHEN ivs.review_eligibility = 'REJECTED' THEN 1 ELSE 0 END) as income_rejected
    FROM applicant_details ad
    LEFT JOIN rds.pg_rds_public.applicant_submissions aps ON aps.applicant_id = ad.applicant_id
    LEFT JOIN rds.pg_rds_public.applicant_submission_document_sources asds ON asds.applicant_submission_id = aps.id
    LEFT JOIN rds.pg_rds_public.income_verification_submissions ivs ON ivs.applicant_submission_document_source_id = asds.id
    WHERE asds.source_type = 'BANK_LINKING' OR asds.source_type IS NULL
    GROUP BY ad.applicant_id
),

asset_verification_results AS (
    SELECT
        ad.applicant_id,
        COUNT(DISTINCT avs.id) as asset_verification_count,
        MAX(CASE WHEN avs.review_eligibility = 'ACCEPTED' THEN 1 ELSE 0 END) as asset_accepted,
        MAX(CASE WHEN avs.review_eligibility = 'REJECTED' THEN 1 ELSE 0 END) as asset_rejected
    FROM applicant_details ad
    LEFT JOIN rds.pg_rds_public.applicant_submissions aps ON aps.applicant_id = ad.applicant_id
    LEFT JOIN rds.pg_rds_public.applicant_submission_document_sources asds ON asds.applicant_submission_id = aps.id
    LEFT JOIN rds.pg_rds_public.asset_verification_submissions avs ON avs.applicant_submission_document_source_id = asds.id
    WHERE asds.source_type = 'BANK_LINKING' OR asds.source_type IS NULL
    GROUP BY ad.applicant_id
),

issue_detection AS (
    SELECT
        ad.applicant_id,
        CASE
            WHEN bal.used_bank_linking = 1 AND idv.id_verification_count = 0 THEN 'NO_ID_VERIFICATION'
            WHEN bal.used_bank_linking = 1 AND ivr.income_verification_count = 0 AND avr.asset_verification_count = 0 THEN 'NO_VERIFICATION_RESULTS'
            ELSE NULL
        END as issue_flag
    FROM applicant_details ad
    LEFT JOIN bank_linking_usage bal ON ad.applicant_id = bal.applicant_id
    LEFT JOIN id_verification_status idv ON ad.applicant_id = idv.applicant_id
    LEFT JOIN income_verification_results ivr ON ad.applicant_id = ivr.applicant_id
    LEFT JOIN asset_verification_results avr ON ad.applicant_id = avr.applicant_id
),

applicant_summary AS (
    SELECT
        COUNT(DISTINCT ad.applicant_id) as total_applicants,
        COUNT(DISTINCT CASE WHEN bal.used_bank_linking = 1 THEN ad.applicant_id END) as bank_linking_applicants,
        COUNT(DISTINCT CASE WHEN idv.id_verification_count > 0 THEN ad.applicant_id END) as id_verification_applicants,
        COUNT(DISTINCT CASE WHEN bal.used_bank_linking = 1 AND idv.id_verification_count > 0 THEN ad.applicant_id END) as correlated_applicants,
        COUNT(DISTINCT CASE WHEN ivr.income_accepted = 1 OR avr.asset_accepted = 1 THEN ad.applicant_id END) as passed_applicants,
        COUNT(DISTINCT CASE WHEN ivr.income_rejected = 1 OR avr.asset_rejected = 1 THEN ad.applicant_id END) as failed_applicants,
        COUNT(DISTINCT CASE WHEN iss.issue_flag IS NOT NULL THEN ad.applicant_id END) as applicants_with_issues
    FROM applicant_details ad
    LEFT JOIN bank_linking_usage bal ON ad.applicant_id = bal.applicant_id
    LEFT JOIN id_verification_status idv ON ad.applicant_id = idv.applicant_id
    LEFT JOIN income_verification_results ivr ON ad.applicant_id = ivr.applicant_id
    LEFT JOIN asset_verification_results avr ON ad.applicant_id = avr.applicant_id
    LEFT JOIN issue_detection iss ON ad.applicant_id = iss.applicant_id
)

SELECT
    'Total Applicants' as metric,
    total_applicants as count,
    '100%' as percentage,
    NULL as notes
FROM applicant_summary

UNION ALL

SELECT
    'Bank Linking Adoption',
    bank_linking_applicants,
    CONCAT(ROUND(bank_linking_applicants * 100.0 / NULLIF(total_applicants, 0), 2), '%'),
    'Applicants who used bank linking feature'
FROM applicant_summary

UNION ALL

SELECT
    'ID Verification Adoption',
    id_verification_applicants,
    CONCAT(ROUND(id_verification_applicants * 100.0 / NULLIF(total_applicants, 0), 2), '%'),
    'Applicants who completed ID verification'
FROM applicant_summary

UNION ALL

SELECT
    'Bank Linking + ID Verification',
    correlated_applicants,
    CONCAT(ROUND(correlated_applicants * 100.0 / NULLIF(bank_linking_applicants, 0), 2), '%'),
    'Percentage of bank linking users who also have ID verification'
FROM applicant_summary

UNION ALL

SELECT
    'Passed Recommendations',
    passed_applicants,
    CONCAT(ROUND(passed_applicants * 100.0 / NULLIF(bank_linking_applicants, 0), 2), '%'),
    'Bank linking applicants who passed verification'
FROM applicant_summary

UNION ALL

SELECT
    'Failed Recommendations',
    failed_applicants,
    CONCAT(ROUND(failed_applicants * 100.0 / NULLIF(bank_linking_applicants, 0), 2), '%'),
    'Bank linking applicants who failed verification'
FROM applicant_summary

UNION ALL

SELECT
    'Applicants with Issues',
    applicants_with_issues,
    CONCAT(ROUND(applicants_with_issues * 100.0 / NULLIF(total_applicants, 0), 2), '%'),
    'Applicants flagged with potential issues'
FROM applicant_summary
""")

display(summary_metrics)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. ISSUE DETECTION
# MAGIC
# MAGIC Detailed breakdown of any glitches or anomalies detected in the bank linking workflow.

# COMMAND ----------

# DBTITLE 1,Issue Breakdown
issue_breakdown = spark.sql("""
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

applicant_details AS (
    SELECT
        e.id as entry_id,
        e.submission_time,
        e.inserted_at,
        f.id as folder_id,
        f.property_id,
        prop.name as property_name,
        c.name as company_name,
        a.id as applicant_id,
        a.first_name,
        a.last_name
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

bank_linking_usage AS (
    SELECT
        ad.applicant_id,
        ad.entry_id,
        MAX(CASE WHEN asds.source_type = 'BANK_LINKING' THEN 1 ELSE 0 END) as used_bank_linking,
        COUNT(DISTINCT CASE WHEN asds.source_type = 'BANK_LINKING' THEN aps.id END) as bank_linking_submissions,
        MIN(CASE WHEN asds.source_type = 'BANK_LINKING' THEN aps.created_at END) as first_bank_linking_time,
        MAX(CASE WHEN asds.source_type = 'BANK_LINKING' THEN aps.created_at END) as last_bank_linking_time
    FROM applicant_details ad
    LEFT JOIN rds.pg_rds_public.applicant_submissions aps ON aps.applicant_id = ad.applicant_id
    LEFT JOIN rds.pg_rds_public.applicant_submission_document_sources asds ON asds.applicant_submission_id = aps.id
    GROUP BY ad.applicant_id, ad.entry_id
),

id_verification_status AS (
    SELECT
        ad.applicant_id,
        ad.entry_id,
        COUNT(DISTINCT idv.id) as id_verification_count
    FROM applicant_details ad
    LEFT JOIN rds.pg_rds_public.id_verifications idv ON idv.applicant_detail_id = ad.applicant_id
    GROUP BY ad.applicant_id, ad.entry_id
),

income_verification_results AS (
    SELECT
        ad.applicant_id,
        COUNT(DISTINCT ivs.id) as income_verification_count
    FROM applicant_details ad
    LEFT JOIN rds.pg_rds_public.applicant_submissions aps ON aps.applicant_id = ad.applicant_id
    LEFT JOIN rds.pg_rds_public.applicant_submission_document_sources asds ON asds.applicant_submission_id = aps.id
    LEFT JOIN rds.pg_rds_public.income_verification_submissions ivs ON ivs.applicant_submission_document_source_id = asds.id
    WHERE asds.source_type = 'BANK_LINKING' OR asds.source_type IS NULL
    GROUP BY ad.applicant_id
),

asset_verification_results AS (
    SELECT
        ad.applicant_id,
        COUNT(DISTINCT avs.id) as asset_verification_count
    FROM applicant_details ad
    LEFT JOIN rds.pg_rds_public.applicant_submissions aps ON aps.applicant_id = ad.applicant_id
    LEFT JOIN rds.pg_rds_public.applicant_submission_document_sources asds ON asds.applicant_submission_id = aps.id
    LEFT JOIN rds.pg_rds_public.asset_verification_submissions avs ON avs.applicant_submission_document_source_id = asds.id
    WHERE asds.source_type = 'BANK_LINKING' OR asds.source_type IS NULL
    GROUP BY ad.applicant_id
),

issue_detection AS (
    SELECT
        ad.applicant_id,
        ad.property_name,
        ad.submission_time,
        CASE
            WHEN bal.used_bank_linking = 1 AND idv.id_verification_count = 0 THEN 'NO_ID_VERIFICATION'
            WHEN bal.used_bank_linking = 1 AND ivr.income_verification_count = 0 AND avr.asset_verification_count = 0 THEN 'NO_VERIFICATION_RESULTS'
            WHEN bal.bank_linking_submissions > 3 THEN 'MULTIPLE_ATTEMPTS'
            WHEN (UNIX_TIMESTAMP(bal.last_bank_linking_time) - UNIX_TIMESTAMP(bal.first_bank_linking_time)) / 60 > 60 THEN 'LONG_COMPLETION_TIME'
            ELSE NULL
        END as issue_flag,
        CASE
            WHEN bal.used_bank_linking = 1 AND idv.id_verification_count = 0 THEN 'Bank linking used but no ID verification found - possible data sync issue'
            WHEN bal.used_bank_linking = 1 AND ivr.income_verification_count = 0 AND avr.asset_verification_count = 0 THEN 'Bank linking used but no income/asset verification results - possible processing failure'
            WHEN bal.bank_linking_submissions > 3 THEN 'More than 3 bank linking submissions - user may be experiencing difficulties'
            WHEN (UNIX_TIMESTAMP(bal.last_bank_linking_time) - UNIX_TIMESTAMP(bal.first_bank_linking_time)) / 60 > 60 THEN 'Took more than 60 minutes to complete - possible abandonment and return'
            ELSE NULL
        END as issue_description
    FROM applicant_details ad
    LEFT JOIN bank_linking_usage bal ON ad.applicant_id = bal.applicant_id
    LEFT JOIN id_verification_status idv ON ad.applicant_id = idv.applicant_id
    LEFT JOIN income_verification_results ivr ON ad.applicant_id = ivr.applicant_id
    LEFT JOIN asset_verification_results avr ON ad.applicant_id = avr.applicant_id
)

SELECT
    issue_flag,
    issue_description,
    COUNT(DISTINCT applicant_id) as applicant_count,
    CONCAT_WS(', ', COLLECT_SET(property_name)) as affected_properties,
    MIN(submission_time) as first_occurrence,
    MAX(submission_time) as last_occurrence
FROM issue_detection
WHERE issue_flag IS NOT NULL
GROUP BY issue_flag, issue_description
ORDER BY applicant_count DESC
""")

display(issue_breakdown)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. PROPERTY-LEVEL PERFORMANCE
# MAGIC
# MAGIC Compare bank linking adoption and success rates across different Pegasus properties.

# COMMAND ----------

# DBTITLE 1,Property Performance Comparison
property_performance = spark.sql("""
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

applicant_details AS (
    SELECT
        e.id as entry_id,
        e.submission_time,
        e.inserted_at,
        f.id as folder_id,
        f.property_id,
        prop.name as property_name,
        c.name as company_name,
        a.id as applicant_id
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

bank_linking_usage AS (
    SELECT
        ad.applicant_id,
        MAX(CASE WHEN asds.source_type = 'BANK_LINKING' THEN 1 ELSE 0 END) as used_bank_linking
    FROM applicant_details ad
    LEFT JOIN rds.pg_rds_public.applicant_submissions aps ON aps.applicant_id = ad.applicant_id
    LEFT JOIN rds.pg_rds_public.applicant_submission_document_sources asds ON asds.applicant_submission_id = aps.id
    GROUP BY ad.applicant_id
),

id_verification_status AS (
    SELECT
        ad.applicant_id,
        COUNT(DISTINCT idv.id) as id_verification_count
    FROM applicant_details ad
    LEFT JOIN rds.pg_rds_public.id_verifications idv ON idv.applicant_detail_id = ad.applicant_id
    GROUP BY ad.applicant_id
),

income_verification_results AS (
    SELECT
        ad.applicant_id,
        COUNT(DISTINCT ivs.id) as income_verification_count,
        MAX(CASE WHEN ivs.review_eligibility = 'ACCEPTED' THEN 1 ELSE 0 END) as income_accepted
    FROM applicant_details ad
    LEFT JOIN rds.pg_rds_public.applicant_submissions aps ON aps.applicant_id = ad.applicant_id
    LEFT JOIN rds.pg_rds_public.applicant_submission_document_sources asds ON asds.applicant_submission_id = aps.id
    LEFT JOIN rds.pg_rds_public.income_verification_submissions ivs ON ivs.applicant_submission_document_source_id = asds.id
    WHERE asds.source_type = 'BANK_LINKING' OR asds.source_type IS NULL
    GROUP BY ad.applicant_id
),

asset_verification_results AS (
    SELECT
        ad.applicant_id,
        COUNT(DISTINCT avs.id) as asset_verification_count,
        MAX(CASE WHEN avs.review_eligibility = 'ACCEPTED' THEN 1 ELSE 0 END) as asset_accepted
    FROM applicant_details ad
    LEFT JOIN rds.pg_rds_public.applicant_submissions aps ON aps.applicant_id = ad.applicant_id
    LEFT JOIN rds.pg_rds_public.applicant_submission_document_sources asds ON asds.applicant_submission_id = aps.id
    LEFT JOIN rds.pg_rds_public.asset_verification_submissions avs ON avs.applicant_submission_document_source_id = asds.id
    WHERE asds.source_type = 'BANK_LINKING' OR asds.source_type IS NULL
    GROUP BY ad.applicant_id
),

issue_detection AS (
    SELECT
        ad.applicant_id,
        CASE
            WHEN bal.used_bank_linking = 1 AND idv.id_verification_count = 0 THEN 'NO_ID_VERIFICATION'
            WHEN bal.used_bank_linking = 1 AND ivr.income_verification_count = 0 AND avr.asset_verification_count = 0 THEN 'NO_VERIFICATION_RESULTS'
            ELSE NULL
        END as issue_flag
    FROM applicant_details ad
    LEFT JOIN bank_linking_usage bal ON ad.applicant_id = bal.applicant_id
    LEFT JOIN id_verification_status idv ON ad.applicant_id = idv.applicant_id
    LEFT JOIN income_verification_results ivr ON ad.applicant_id = ivr.applicant_id
    LEFT JOIN asset_verification_results avr ON ad.applicant_id = avr.applicant_id
)

SELECT
    ad.property_name,
    COUNT(DISTINCT ad.applicant_id) as total_applicants,
    COUNT(DISTINCT CASE WHEN bal.used_bank_linking = 1 THEN ad.applicant_id END) as bank_linking_users,
    ROUND(COUNT(DISTINCT CASE WHEN bal.used_bank_linking = 1 THEN ad.applicant_id END) * 100.0 /
          NULLIF(COUNT(DISTINCT ad.applicant_id), 0), 2) as adoption_rate_pct,
    ROUND(COUNT(DISTINCT CASE WHEN bal.used_bank_linking = 1 AND idv.id_verification_count > 0 THEN ad.applicant_id END) * 100.0 /
          NULLIF(COUNT(DISTINCT CASE WHEN bal.used_bank_linking = 1 THEN ad.applicant_id END), 0), 2) as id_correlation_pct,
    ROUND(COUNT(DISTINCT CASE WHEN ivr.income_accepted = 1 OR avr.asset_accepted = 1 THEN ad.applicant_id END) * 100.0 /
          NULLIF(COUNT(DISTINCT CASE WHEN bal.used_bank_linking = 1 THEN ad.applicant_id END), 0), 2) as success_rate_pct,
    COUNT(DISTINCT CASE WHEN iss.issue_flag IS NOT NULL THEN ad.applicant_id END) as issues_detected
FROM applicant_details ad
LEFT JOIN bank_linking_usage bal ON ad.applicant_id = bal.applicant_id
LEFT JOIN id_verification_status idv ON ad.applicant_id = idv.applicant_id
LEFT JOIN income_verification_results ivr ON ad.applicant_id = ivr.applicant_id
LEFT JOIN asset_verification_results avr ON ad.applicant_id = avr.applicant_id
LEFT JOIN issue_detection iss ON ad.applicant_id = iss.applicant_id
GROUP BY ad.property_name
ORDER BY adoption_rate_pct DESC
""")

display(property_performance)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. EXPORT OPTIONS
# MAGIC
# MAGIC Use the following cells to export data for further analysis or sharing.

# COMMAND ----------

# DBTITLE 1,Save Applicant Report to Table (Optional)
# Uncomment to save the applicant-level report to a Delta table
# applicant_report.write.mode("overwrite").saveAsTable("pegasus_bank_linking_applicant_report")

# COMMAND ----------

# DBTITLE 1,Export to CSV (Optional)
# Uncomment to export to CSV
# applicant_report.coalesce(1).write.mode("overwrite").option("header", "true").csv("/tmp/pegasus_applicant_report.csv")
