# Databricks Genie Instructions - Snappt Multi-Database Platform

## Overview

This Genie has access to 7 interconnected PostgreSQL databases that form the Snappt fraud detection and verification platform. The databases are **physically separate** but logically connected through shared identifiers (UUIDs).

### Database Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│ fraud_postgresql│────▶│enterprise_postgresql │     │   ax_postgres   │
│  (Core DB)      │     │  (Integrations)      │     │ (Applicant UX)  │
└─────────────────┘     └──────────────────────┘     └─────────────────┘
        │                                                      │
        ├──────────────────────┬───────────────────────────────┘
        │                      │
        ▼                      ▼
┌─────────────────┐    ┌─────────────────────┐
│  av_postgres    │    │ dp_income_validation│
│ (ML Scoring)    │    │ (Income Calc)       │
└─────────────────┘    └─────────────────────┘
        │                      │
        ▼                      ▼
┌─────────────────────────────────────────────┐
│      dp_document_intelligence               │
│      (AI Document Analysis)                 │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│          dp_ai_services                     │
│      (AI Agent Orchestration)               │
└─────────────────────────────────────────────┘
```

---

## Instructions for Query Generation

### 1. Database Selection Strategy

**When to query each database:**

- **fraud_postgresql**: Core business queries (applicants, properties, entries, submissions, reviews, results)
- **ax_postgres**: Applicant experience, Argyle connections (CONNECTED_PAYROLL, BANK_LINKING sources)
- **enterprise_postgresql**: Integration status, external system sync, email delivery
- **dp_income_validation**: Income calculation details, document parsing for income
- **dp_document_intelligence**: AI document analysis, tampering detection, OCR results
- **av_postgres**: ML model scores, fraud indicators, model performance
- **dp_ai_services**: AI agent execution logs, costs, checkpoints

### 2. Cross-Database Join Patterns

**Critical**: These databases are separate. You **cannot** use SQL joins across databases. Instead:

1. Query one database to get IDs
2. Use those IDs in a subsequent query to another database
3. Join results in application logic or use UNION patterns

Example workflow:
```sql
-- Step 1: Get applicant submission IDs from fraud_postgresql
SELECT id, applicant_id FROM applicant_submissions WHERE ...;

-- Step 2: Use those IDs to query ax_postgres
SELECT * FROM ax_postgres.applicant_submission_document_sources
WHERE submission_id IN (...);
```

### 3. Key Identifier Mapping

Understanding how entities relate across databases:

| Entity | Primary DB | Related Identifiers |
|--------|-----------|---------------------|
| Applicant | fraud_postgresql.applicants.id | ax_postgres.applicants.id |
| Submission | fraud_postgresql.applicant_submissions.id | ax_postgres.applicant_submissions.id |
| Document | fraud_postgresql.proof.id | dp_document_intelligence.*.document_id |
| Fraud Check | fraud_postgresql.fraud_submissions.id | av_postgres.fraud_scoring_requests.fraud_submission_id |
| Income Report | fraud_postgresql.income_verification_results.id | dp_income_validation.income_reports.id |

### 4. Temporal Considerations

**Most tables have timestamps:**
- `inserted_at` - Record creation (always present)
- `updated_at` - Last modification (always present)
- Status-specific timestamps: `submitted_at`, `reviewed_at`, `completed_at`

**Performance tip**: Always include date filters for large tables (>1M rows):
```sql
WHERE inserted_at >= '2025-01-01'  -- Significantly improves query speed
```

### 5. Multi-Tenant Architecture

**fraud_postgresql uses multi-tenancy:**
- Companies → Properties → Entries → Applicants
- Always consider property/company context when querying
- Use property_id or company_id filters for customer-specific queries

### 6. Status Workflows

Understand status progression:
```
Applicant Submission Flow:
  pending → processing → completed → reviewed → finalized

Fraud Detection Flow:
  submitted → ml_scoring → human_review → determination

Review Queue:
  available → assigned → in_review → completed
```

---

## Common Table Relationships (Joins)

### Core Entity Relationships (fraud_postgresql)

```sql
-- Applicant full journey
SELECT
    c.name as company_name,
    p.name as property_name,
    e.id as entry_id,
    a.full_name as applicant_name,
    asub.submitted_time,
    fs.status as fraud_status,
    fr.result as fraud_result
FROM companies c
JOIN properties p ON p.company_id = c.id
JOIN entries e ON e.property_id = p.id
JOIN applicants a ON a.entry_id = e.id
JOIN applicant_submissions asub ON asub.applicant_id = a.id
LEFT JOIN fraud_submissions fs ON fs.applicant_submission_id = asub.id
LEFT JOIN fraud_results fr ON fr.fraud_submission_id = fs.id;
```

```sql
-- Document verification chain
SELECT
    a.full_name,
    asub.submitted_time,
    p.original_filename,
    p.file_type,
    asds.source_type,
    fs.status as fraud_status,
    ivs.status as income_status,
    avs.status as asset_status
FROM applicants a
JOIN applicant_submissions asub ON asub.applicant_id = a.id
JOIN applicant_submission_document_sources asds ON asds.applicant_submission_id = asub.id
JOIN proof p ON p.id = asds.proof_id
LEFT JOIN fraud_submissions fs ON fs.applicant_submission_id = asub.id
LEFT JOIN income_verification_submissions ivs ON ivs.applicant_submission_id = asub.id
LEFT JOIN asset_verification_submissions avs ON avs.applicant_submission_id = asub.id;
```

```sql
-- Review workflow and performance
SELECT
    u.email as reviewer_email,
    COUNT(DISTINCT ri.id) as total_reviews,
    COUNT(DISTINCT CASE WHEN ri.status = 'completed' THEN ri.id END) as completed_reviews,
    AVG(EXTRACT(EPOCH FROM (ri.updated_at - ri.inserted_at))/60) as avg_review_time_minutes
FROM users u
JOIN review_items ri ON ri.reviewer_id = u.id
WHERE ri.inserted_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY u.email;
```

### Cross-Database Relationships

```sql
-- Argyle connection analysis (ax_postgres)
-- First get submission IDs from fraud_postgresql, then:
SELECT
    asub.id as submission_id,
    asds.source_type,
    au.argyle_id,
    ae.employments->>'employer_name' as employer,
    ad.document->>'type' as document_type,
    COUNT(ad.id) as document_count
FROM applicant_submissions asub
JOIN applicant_submission_document_sources asds ON asds.submission_id = asub.id
LEFT JOIN argyle_users au ON au.applicant_id = asub.applicant_id
LEFT JOIN argyle_employments ae ON ae.argyle_user_id = au.argyle_id::varchar
LEFT JOIN argyle_documents ad ON ad.argyle_user_id = au.id
WHERE asds.source_type IN ('CONNECTED_PAYROLL', 'BANK_LINKING')
GROUP BY asub.id, asds.source_type, au.argyle_id, employer, ad.document->>'type';
```

```sql
-- ML fraud scoring details (av_postgres)
-- After getting fraud_submission_id from fraud_postgresql:
SELECT
    fsr.fraud_submission_id,
    ml.model_name,
    ml.version as model_version,
    fs.fraud_probability,
    fs.confidence_score,
    fr.ruling,
    fi.indicator_type,
    fi.severity,
    fi.description as fraud_indicator
FROM fraud_scoring_requests fsr
JOIN fraud_scores fs ON fs.scoring_request_id = fsr.id
JOIN ml_models ml ON ml.id = fs.model_id
JOIN fraud_rulings fr ON fr.fraud_submission_id = fsr.fraud_submission_id
LEFT JOIN fraud_indicators fi ON fi.fraud_score_id = fs.id
WHERE fsr.status = 'completed';
```

```sql
-- Income calculation breakdown (dp_income_validation)
-- After getting applicant_submission_id from fraud_postgresql:
SELECT
    ir.id as income_report_id,
    ir.total_monthly_income,
    ir.meets_requirements,
    isr.source_type,
    isr.monthly_amount,
    isr.verified,
    id.document_type,
    id.extracted_amounts
FROM income_reports ir
JOIN income_sources isr ON isr.income_report_id = ir.id
JOIN income_documents id ON id.income_report_id = ir.id
ORDER BY isr.monthly_amount DESC;
```

```sql
-- Document AI analysis (dp_document_intelligence)
-- After getting document_id (proof.id) from fraud_postgresql:
SELECT
    dcr.predicted_type as classified_type,
    dcr.confidence_score as classification_confidence,
    tdr.tampering_detected,
    tdr.confidence_score as tampering_confidence,
    tdr.indicators_found,
    oer.extracted_text,
    dqs.quality_score,
    dqs.is_processable
FROM document_classification_results dcr
LEFT JOIN tampering_detection_results tdr ON tdr.document_id = dcr.document_id
LEFT JOIN ocr_extraction_results oer ON oer.document_id = dcr.document_id
LEFT JOIN document_quality_scores dqs ON dqs.document_id = dcr.document_id
WHERE dcr.document_id = 'uuid-here';
```

---

## Common SQL Expressions (Business Concepts)

### Approval Rates

```sql
-- Overall approval rate
SELECT
    COUNT(CASE WHEN fr.result = 'pass' THEN 1 END)::float /
    NULLIF(COUNT(*), 0) * 100 as approval_rate_pct
FROM fraud_results fr
WHERE fr.inserted_at >= CURRENT_DATE - INTERVAL '30 days';
```

### Fraud Detection Rate

```sql
-- Fraud detection rate by source type
SELECT
    asds.source_type,
    COUNT(DISTINCT CASE WHEN fr.result = 'fail' THEN fs.id END)::float /
    NULLIF(COUNT(DISTINCT fs.id), 0) * 100 as fraud_detection_rate_pct
FROM fraud_submissions fs
JOIN applicant_submissions asub ON asub.id = fs.applicant_submission_id
JOIN applicant_submission_document_sources asds ON asds.applicant_submission_id = asub.id
LEFT JOIN fraud_results fr ON fr.fraud_submission_id = fs.id
WHERE fs.inserted_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY asds.source_type;
```

### Average Review Time

```sql
-- Average time from submission to review completion
SELECT
    AVG(EXTRACT(EPOCH FROM (fr.reviewed_at - fs.submitted_at))/3600) as avg_hours_to_review
FROM fraud_submissions fs
JOIN fraud_reviews fr ON fr.fraud_submission_id = fs.id
WHERE fr.reviewed_at IS NOT NULL
  AND fs.submitted_at >= CURRENT_DATE - INTERVAL '30 days';
```

### Income-to-Rent Ratio

```sql
-- Calculate income-to-rent ratio (typically 3x rent required)
SELECT
    p.name as property_name,
    e.monthly_rent,
    ivr.calculated_income as monthly_income,
    ivr.calculated_income / NULLIF(e.monthly_rent, 0) as income_to_rent_ratio,
    CASE
        WHEN ivr.calculated_income >= e.monthly_rent * 3 THEN 'Qualified'
        ELSE 'Not Qualified'
    END as income_qualification
FROM entries e
JOIN properties p ON p.id = e.property_id
JOIN applicants a ON a.entry_id = e.id
JOIN applicant_submissions asub ON asub.applicant_id = a.id
JOIN income_verification_results ivr ON ivr.applicant_submission_id = asub.id
WHERE e.monthly_rent > 0;
```

### Document Verification Completion Rate

```sql
-- Percentage of required verifications completed
WITH verification_summary AS (
    SELECT
        asub.id as submission_id,
        COUNT(DISTINCT CASE WHEN fs.status = 'completed' THEN 1 END) as fraud_completed,
        COUNT(DISTINCT CASE WHEN ivs.status = 'completed' THEN 1 END) as income_completed,
        COUNT(DISTINCT CASE WHEN avs.status = 'completed' THEN 1 END) as asset_completed,
        COUNT(DISTINCT CASE WHEN idv.status = 'completed' THEN 1 END) as id_completed
    FROM applicant_submissions asub
    LEFT JOIN fraud_submissions fs ON fs.applicant_submission_id = asub.id
    LEFT JOIN income_verification_submissions ivs ON ivs.applicant_submission_id = asub.id
    LEFT JOIN asset_verification_submissions avs ON avs.applicant_submission_id = asub.id
    LEFT JOIN id_verifications idv ON idv.applicant_id = asub.applicant_id
    GROUP BY asub.id
)
SELECT
    submission_id,
    (fraud_completed + income_completed + asset_completed + id_completed)::float / 4.0 * 100
        as completion_percentage
FROM verification_summary;
```

### ML Model Performance Metrics

```sql
-- Model accuracy comparison (av_postgres)
SELECT
    ml.model_name,
    ml.version,
    mpm.accuracy,
    mpm.precision,
    mpm.recall,
    mpm.f1_score,
    COUNT(DISTINCT ffl.id) as feedback_count,
    COUNT(DISTINCT CASE WHEN ffl.was_correct THEN ffl.id END)::float /
        NULLIF(COUNT(DISTINCT ffl.id), 0) * 100 as human_agreement_rate
FROM ml_models ml
JOIN model_performance_metrics mpm ON mpm.model_id = ml.id
LEFT JOIN fraud_scores fs ON fs.model_id = ml.id
LEFT JOIN fraud_feedback_loop ffl ON ffl.fraud_score_id = fs.id
WHERE ml.is_active = true
GROUP BY ml.model_name, ml.version, mpm.accuracy, mpm.precision, mpm.recall, mpm.f1_score;
```

### Argyle Connection Success Rate

```sql
-- Argyle integration success metrics (ax_postgres)
SELECT
    DATE_TRUNC('week', asds.inserted_at) as week,
    asds.source_type,
    COUNT(DISTINCT asds.id) as total_attempts,
    COUNT(DISTINCT CASE WHEN au.id IS NOT NULL THEN asds.id END) as successful_connections,
    COUNT(DISTINCT CASE WHEN au.id IS NOT NULL THEN asds.id END)::float /
        NULLIF(COUNT(DISTINCT asds.id), 0) * 100 as success_rate_pct,
    AVG(ad.document_count) as avg_documents_per_connection
FROM applicant_submission_document_sources asds
LEFT JOIN applicants a ON a.id = (
    SELECT applicant_id FROM applicant_submissions
    WHERE id = asds.submission_id LIMIT 1
)
LEFT JOIN argyle_users au ON au.applicant_id = a.id
LEFT JOIN (
    SELECT argyle_user_id, COUNT(*) as document_count
    FROM argyle_documents
    GROUP BY argyle_user_id
) ad ON ad.argyle_user_id = au.id
WHERE asds.source_type IN ('CONNECTED_PAYROLL', 'BANK_LINKING')
  AND asds.inserted_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY DATE_TRUNC('week', asds.inserted_at), asds.source_type
ORDER BY week DESC, source_type;
```

---

## Example SQL Queries & Functions

### Example 1: Top Fraud Indicators by Property

```sql
-- Identify most common fraud indicators for a specific property
SELECT
    p.name as property_name,
    fi.indicator_type,
    fi.severity,
    COUNT(*) as occurrence_count,
    AVG(fs.fraud_probability) as avg_fraud_score
FROM fraud_submissions fsub
JOIN applicant_submissions asub ON asub.id = fsub.applicant_submission_id
JOIN applicants a ON a.id = asub.applicant_id
JOIN entries e ON e.id = a.entry_id
JOIN properties p ON p.id = e.property_id
-- Cross-reference to av_postgres (conceptually, would need separate query)
-- JOIN fraud_scoring_requests fsr ON fsr.fraud_submission_id = fsub.id
-- JOIN fraud_scores fs ON fs.scoring_request_id = fsr.id
-- JOIN fraud_indicators fi ON fi.fraud_score_id = fs.id
WHERE fsub.inserted_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY p.name, fi.indicator_type, fi.severity
ORDER BY occurrence_count DESC
LIMIT 20;
```

### Example 2: Reviewer Performance Dashboard

```sql
-- Comprehensive reviewer performance metrics
WITH reviewer_stats AS (
    SELECT
        u.id as user_id,
        u.email,
        u.full_name,
        COUNT(DISTINCT ri.id) as total_reviews,
        COUNT(DISTINCT CASE WHEN ri.status = 'completed' THEN ri.id END) as completed_reviews,
        AVG(EXTRACT(EPOCH FROM (ri.updated_at - ri.inserted_at))/60) as avg_review_time_minutes,
        COUNT(DISTINCT CASE
            WHEN ri.review_type = 'fraud' AND fr.result = 'fail' THEN ri.id
        END) as fraud_catches,
        COUNT(DISTINCT re.id) as escalations_received
    FROM users u
    JOIN review_items ri ON ri.reviewer_id = u.id
    LEFT JOIN fraud_reviews fr ON fr.id = ri.reviewable_id AND ri.review_type = 'fraud'
    LEFT JOIN review_escalations re ON re.assigned_to_user_id = u.id
    WHERE ri.inserted_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY u.id, u.email, u.full_name
)
SELECT
    email,
    full_name,
    total_reviews,
    completed_reviews,
    ROUND(completed_reviews::numeric / NULLIF(total_reviews, 0) * 100, 2) as completion_rate_pct,
    ROUND(avg_review_time_minutes::numeric, 2) as avg_review_time_minutes,
    fraud_catches,
    escalations_received,
    CASE
        WHEN avg_review_time_minutes < 10 THEN 'Fast'
        WHEN avg_review_time_minutes < 20 THEN 'Average'
        ELSE 'Needs Improvement'
    END as speed_rating
FROM reviewer_stats
ORDER BY total_reviews DESC;
```

### Example 3: Income Source Breakdown

```sql
-- Income verification breakdown by source type (dp_income_validation)
SELECT
    isr.source_type,
    COUNT(DISTINCT ir.id) as unique_reports,
    SUM(isr.monthly_amount) as total_monthly_income,
    AVG(isr.monthly_amount) as avg_monthly_income,
    MIN(isr.monthly_amount) as min_monthly_income,
    MAX(isr.monthly_amount) as max_monthly_income,
    COUNT(DISTINCT CASE WHEN isr.verified THEN isr.id END)::float /
        NULLIF(COUNT(DISTINCT isr.id), 0) * 100 as verification_rate_pct
FROM income_reports ir
JOIN income_sources isr ON isr.income_report_id = ir.id
WHERE ir.inserted_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY isr.source_type
ORDER BY total_monthly_income DESC;
```

### Example 4: Document Processing Funnel

```sql
-- Track document processing through AI pipeline (dp_document_intelligence)
SELECT
    dcr.predicted_type as document_type,
    COUNT(DISTINCT dcr.document_id) as total_documents,
    COUNT(DISTINCT CASE
        WHEN dqs.is_processable THEN dcr.document_id
    END) as processable_documents,
    COUNT(DISTINCT CASE
        WHEN tdr.tampering_detected THEN dcr.document_id
    END) as tampering_detected,
    COUNT(DISTINCT CASE
        WHEN sde.confidence_score > 0.8 THEN dcr.document_id
    END) as high_confidence_extractions,
    AVG(dqs.quality_score) as avg_quality_score,
    AVG(dcr.confidence_score) as avg_classification_confidence
FROM document_classification_results dcr
LEFT JOIN document_quality_scores dqs ON dqs.document_id = dcr.document_id
LEFT JOIN tampering_detection_results tdr ON tdr.document_id = dcr.document_id
LEFT JOIN (
    SELECT document_id, AVG(confidence_score) as confidence_score
    FROM structured_data_extraction
    GROUP BY document_id
) sde ON sde.document_id = dcr.document_id
WHERE dcr.inserted_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY dcr.predicted_type
ORDER BY total_documents DESC;
```

### Example 5: Property Feature Utilization

```sql
-- Analyze which property features are most used
SELECT
    f.name as feature_name,
    f.feature_type,
    COUNT(DISTINCT pf.property_id) as properties_with_feature,
    COUNT(DISTINCT e.id) as entries_using_feature,
    AVG(CASE WHEN fr.result = 'pass' THEN 1.0 ELSE 0.0 END) as approval_rate
FROM features f
JOIN property_features pf ON pf.feature_id = f.id
JOIN entries e ON e.property_id = pf.property_id
LEFT JOIN applicants a ON a.entry_id = e.id
LEFT JOIN applicant_submissions asub ON asub.applicant_id = a.id
LEFT JOIN fraud_submissions fs ON fs.applicant_submission_id = asub.id
LEFT JOIN fraud_results fr ON fr.fraud_submission_id = fs.id
WHERE pf.enabled = true
  AND e.inserted_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY f.name, f.feature_type
ORDER BY entries_using_feature DESC;
```

### Example 6: Integration Sync Health

```sql
-- Monitor integration sync status (enterprise_postgresql)
SELECT
    eic.type as integration_type,
    eic.name as integration_name,
    COUNT(DISTINCT ep.id) as properties_configured,
    COUNT(DISTINCT oia.id) as total_sync_attempts,
    COUNT(DISTINCT CASE WHEN oia.status = 'completed' THEN oia.id END) as successful_syncs,
    COUNT(DISTINCT CASE WHEN oia.status = 'failed' THEN oia.id END) as failed_syncs,
    AVG(oia.attempt_count) as avg_retry_count,
    MAX(oia.last_attempt_at) as most_recent_sync
FROM enterprise_integration_configuration eic
LEFT JOIN enterprise_property ep ON ep.integration_details->>'config_id' = eic.id::text
LEFT JOIN outbound_integration_attempts oia ON oia.integration_type = eic.type
WHERE oia.inserted_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY eic.type, eic.name
ORDER BY failed_syncs DESC;
```

### Example 7: AI Agent Cost Analysis

```sql
-- Track AI agent costs and efficiency (dp_ai_services)
SELECT
    at.agent_type,
    ac.model_provider,
    COUNT(DISTINCT at.id) as total_executions,
    SUM(ac.tokens_used) as total_tokens,
    SUM(ac.estimated_cost_usd) as total_cost_usd,
    AVG(ac.tokens_used) as avg_tokens_per_execution,
    AVG(ac.estimated_cost_usd) as avg_cost_per_execution,
    COUNT(DISTINCT ae.id) as error_count,
    COUNT(DISTINCT CASE WHEN at.status = 'completed' THEN at.id END)::float /
        NULLIF(COUNT(DISTINCT at.id), 0) * 100 as success_rate_pct
FROM agent_threads at
LEFT JOIN agent_cost_tracking ac ON ac.thread_id = at.thread_id
LEFT JOIN agent_errors ae ON ae.thread_id = at.thread_id
WHERE at.inserted_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY at.agent_type, ac.model_provider
ORDER BY total_cost_usd DESC;
```

### Example 8: Frequent Flyer Detection

```sql
-- Identify potential frequent flyer fraud patterns
SELECT
    ffv.variation_type,
    ffv.applicant_count,
    ffv.matched_field,
    ffmc.confidence_level,
    COUNT(DISTINCT a.id) as flagged_applicants,
    AVG(fr.fraud_score) as avg_fraud_score,
    COUNT(DISTINCT CASE WHEN fr.result = 'fail' THEN a.id END) as confirmed_fraud_count
FROM frequent_flyer_variations ffv
JOIN frequent_flyer_matched_confidences ffmc ON ffmc.variation_id = ffv.id
JOIN applicants a ON a.id = ANY(ffv.applicant_ids)
LEFT JOIN applicant_submissions asub ON asub.applicant_id = a.id
LEFT JOIN fraud_submissions fs ON fs.applicant_submission_id = asub.id
LEFT JOIN fraud_results fr ON fr.fraud_submission_id = fs.id
WHERE ffv.inserted_at >= CURRENT_DATE - INTERVAL '90 days'
  AND ffmc.confidence_level IN ('high', 'very_high')
GROUP BY ffv.variation_type, ffv.applicant_count, ffv.matched_field, ffmc.confidence_level
ORDER BY flagged_applicants DESC;
```

---

## Performance Optimization Tips

### 1. Always Use Date Filters
Large tables (>1M rows) require date filtering:
```sql
-- Good ✓
WHERE inserted_at >= '2025-01-01'

-- Bad ✗
WHERE status = 'completed'  -- Full table scan on 10M row table
```

### 2. Index-Friendly Queries
These columns are typically indexed:
- `id` (primary key)
- `inserted_at`, `updated_at`
- Foreign keys (`applicant_id`, `property_id`, `company_id`, etc.)
- Status columns
- `email` on users table

### 3. Avoid SELECT *
Specify only needed columns, especially for tables with JSONB fields:
```sql
-- Good ✓
SELECT id, full_name, status FROM applicants;

-- Bad ✗
SELECT * FROM applicants;  -- Fetches large JSONB metadata fields
```

### 4. Use CTEs for Readability
Break complex queries into Common Table Expressions:
```sql
WITH recent_submissions AS (
    SELECT * FROM applicant_submissions
    WHERE submitted_time >= CURRENT_DATE - INTERVAL '30 days'
),
fraud_results AS (
    SELECT * FROM fraud_submissions fs
    JOIN recent_submissions rs ON rs.id = fs.applicant_submission_id
)
SELECT * FROM fraud_results;
```

### 5. LIMIT Results for Exploratory Queries
Always add LIMIT when exploring:
```sql
SELECT * FROM proof LIMIT 100;
```

---

## Common Pitfalls to Avoid

1. **Cross-database joins**: These databases are separate - you cannot join them directly
2. **Soft deletes**: Check for `deleted_at IS NULL` when needed
3. **UUID vs String**: Some foreign keys are stored as strings (e.g., `argyle_employments.argyle_user_id`)
4. **JSONB field access**: Use `->` for JSON objects, `->>` for text extraction
5. **Timezone awareness**: All timestamps are UTC
6. **Multi-tenancy**: Always consider company/property scope for customer queries

---

## Glossary of Terms

- **Entry**: A screening case for one or more applicants at a property
- **Submission**: Document upload event from an applicant
- **Proof**: Individual document file (PDF, image, etc.)
- **Source Type**: How documents were provided (CONNECTED_PAYROLL, BANK_LINKING, MANUAL_UPLOAD)
- **Argyle**: Third-party service for connected payroll and bank account data
- **Fraud Submission**: Request to analyze documents for fraud
- **Review Item**: Task in reviewer queue requiring human review
- **Ruling**: ML system's final fraud determination
- **Frequent Flyer**: Applicant attempting to use same documents at multiple properties

---

## Need Help?

When the user asks:
- **"How do I find..."** → Start with fraud_postgresql, it's the core database
- **"What's the relationship between..."** → Check the Joins section above
- **"How can I calculate..."** → Look at Common SQL Expressions
- **"Show me an example of..."** → Reference Example Queries section
- **"This query is slow..."** → Apply Performance Optimization tips

Always explain which database(s) are being queried and why!
