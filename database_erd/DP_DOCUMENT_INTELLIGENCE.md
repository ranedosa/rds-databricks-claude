# Document Intelligence Database (dp_document_intelligence)

**Generated:** 2025-11-25
**Database:** dp_document_intelligence (Microservice)
**Schema Documented:** di (Document Intelligence)
**Tables Documented:** 8 tables

---

## Overview

This database is part of the asset verification microservice that extracts and analyzes financial data from bank statements using AI/ML models. It provides asset sufficiency calculations, account aggregation, and document-level analysis to determine if applicants have sufficient liquid assets (typically 2-6 months rent).

**Purpose:** Standalone AI-powered asset verification service with cross-database integration to fraud_postgresql

**Key Features:**
- AI/ML document extraction (LLM-based inference)
- Multi-account asset aggregation
- Bank statement period analysis
- Status workflow management
- AI operation tracking and metrics
- Human review sampling and quality assurance

**Technology Stack:**
- Temporal workflow orchestration
- LLM inference (model versioning and prompt tracking)
- JSONB for flexible data storage

---

## Table of Contents

1. [Asset Verification Schema (di)](#asset-verification-schema-di)
   - asset_verifications
   - accounts
   - statements
   - asset_verification_status_codes
   - asset_verification_status_details
   - asset_verification_review
2. [AI Operations Tracking](#ai-operations-tracking)
   - ai_operations
   - inferences
3. [Cross-Database Relationships](#cross-database-relationships)

---

## Asset Verification Schema (di)

### Entity Relationship Diagram

```
asset_verifications (1) ←→ (N) accounts
     ↓                           ↓
asset_verification_status_details    statements (N)
     ↓
asset_verification_status_codes

asset_verifications (1) ←→ (N) asset_verification_review
asset_verifications (1) ←→ (N) ai_operations
```

---

### asset_verifications

**Purpose:** Aggregated asset verification calculations for an applicant's submission

**Primary Key:** id (uuid, auto-generated)

**Cross-Database Link:** applicant_id → fraud_postgresql.applicants.id (stored as varchar!)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| applicant_id | varchar(255) | NO | - | **Cross-DB reference** to fraud_postgresql.applicants.id |
| applicant_name | varchar(255) | NO | - | Applicant name (denormalized for convenience) |
| calculation_date | timestamp with time zone | NO | - | When asset calculation was performed |
| total_verified_assets | numeric(10) | YES | - | Sum of verified assets across all accounts |
| status | enum | NO | - | Verification status (PENDING, COMPLETED, ERROR) |
| status_details | jsonb | YES | - | Additional status information |
| source | enum | NO | 'AUTOMATED' | Processing source (AUTOMATED, MANUAL) |
| created_at | timestamp with time zone | NO | CURRENT_TIMESTAMP | Record creation timestamp |
| updated_at | timestamp with time zone | NO | CURRENT_TIMESTAMP | Record update timestamp |

#### Relationships

**Belongs to:**
- **fraud_postgresql.applicants** (applicant_id) - Applicant being verified (cross-DB)

**Has many:**
- **accounts** (asset_verification_id) - Individual bank accounts
- **asset_verification_status_details** (asset_verification_id) - Status change history
- **asset_verification_review** (asset_verification_id) - Human review records
- **ai_operations** (asset_verification_id) - AI processing operations

#### Business Logic

**Asset Verification Requirements:**
- **Minimum Assets:** Typically 2-6 months rent in liquid assets
- **Account Types:** Checking, savings, money market (liquid)
- **Excluded Assets:** Retirement accounts (401k, IRA), investment accounts (illiquid)
- **Recency:** Statements must be <30 days old

**Automated vs Manual Review:**
- **Auto-approve:** Assets ≥6 months rent, all statements recent, clear account holder match
- **Manual review:** Assets 2-6 months rent, mixed liquid/illiquid, joint accounts, name mismatches

**Status Values (Inferred):**
- **PENDING:** Verification queued or in progress
- **COMPLETED:** Verification finished successfully
- **ERROR:** Processing failed
- **NEEDS_REVIEW:** Requires human review

#### Query Examples

```sql
-- Get asset verification with all accounts
SELECT
    av.id,
    av.applicant_id,
    av.applicant_name,
    av.total_verified_assets,
    av.status,
    av.source,
    COUNT(a.id) as account_count,
    SUM(a.verified_assets) as sum_account_assets
FROM di.asset_verifications av
LEFT JOIN di.accounts a ON av.id = a.asset_verification_id
WHERE av.applicant_id = 'applicant-id-here'
GROUP BY av.id, av.applicant_id, av.applicant_name,
         av.total_verified_assets, av.status, av.source;

-- Asset sufficiency check
SELECT
    av.applicant_id,
    av.applicant_name,
    av.total_verified_assets,
    av.status,
    CASE
        WHEN av.total_verified_assets >= 10000 THEN 'Excellent (6+ months)'
        WHEN av.total_verified_assets >= 5000 THEN 'Good (3-6 months)'
        WHEN av.total_verified_assets >= 3000 THEN 'Borderline (2-3 months)'
        ELSE 'Insufficient (<2 months)'
    END as asset_rating
FROM di.asset_verifications av
WHERE av.status = 'COMPLETED';
```

---

### accounts

**Purpose:** Individual bank accounts extracted from documents

**Primary Key:** id (uuid, auto-generated)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| asset_verification_id | uuid | NO | - | FK → asset_verifications.id |
| institution_name | varchar | YES | - | Bank name (Chase, Bank of America, etc.) |
| account_type | enum | YES | - | Account type (checking, savings, money_market) |
| account_holder_name | varchar | YES | - | Name on account |
| account_number_last_four | varchar(4) | YES | - | Last 4 digits of account number |
| verified_assets | numeric(10) | YES | - | Verified liquid assets in this account |
| created_at | timestamp with time zone | YES | CURRENT_TIMESTAMP | Record creation timestamp |
| updated_at | timestamp with time zone | YES | CURRENT_TIMESTAMP | Record update timestamp |

#### Relationships

**Belongs to:**
- **asset_verifications** (asset_verification_id) - Parent verification

**Has many:**
- **statements** (account_id) - Bank statements for this account

#### Business Logic

**Account Types:**
- **checking:** Liquid, fully counted toward assets
- **savings:** Liquid, fully counted toward assets
- **money_market:** Liquid, fully counted toward assets
- **retirement:** Illiquid, excluded from verification (401k, IRA, Roth IRA)
- **investment:** Semi-liquid, may require manual review (stocks, bonds, brokerage)

**Name Matching:**
- Account holder name must match applicant name (fuzzy matching for variations)
- Joint accounts require special handling (only applicant's share counted)

**Balance Calculation:**
- Uses most recent statement end_balance
- If multiple statements provided, takes latest
- Aggregates across all accounts for same applicant

#### Query Examples

```sql
-- Accounts for verification
SELECT
    a.id,
    a.institution_name,
    a.account_type,
    a.account_holder_name,
    a.account_number_last_four,
    a.verified_assets,
    COUNT(s.id) as statement_count,
    MAX(s.end_date) as most_recent_statement
FROM di.accounts a
LEFT JOIN di.statements s ON a.id = s.account_id
WHERE a.asset_verification_id = 'uuid-here'
GROUP BY a.id, a.institution_name, a.account_type,
         a.account_holder_name, a.account_number_last_four, a.verified_assets;

-- Assets by account type
SELECT
    account_type,
    COUNT(*) as account_count,
    SUM(verified_assets) as total_assets,
    AVG(verified_assets) as avg_per_account
FROM di.accounts
WHERE asset_verification_id = 'uuid-here'
GROUP BY account_type
ORDER BY total_assets DESC;
```

---

### statements

**Purpose:** Individual bank statement documents with extracted balance data

**Primary Key:** id (uuid, auto-generated)

**Cross-Database Link:** document_id → fraud_postgresql.proof.id

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| asset_verification_id | uuid | NO | - | FK → asset_verifications.id |
| account_id | uuid | NO | - | FK → accounts.id |
| document_id | varchar | NO | - | **Cross-DB reference** to fraud_postgresql.proof.id |
| start_date | timestamp with time zone | YES | - | Statement period start date |
| start_balance | numeric(10) | YES | - | Beginning balance |
| end_date | timestamp with time zone | YES | - | Statement period end date |
| end_balance | numeric(10) | YES | - | Ending balance (used for asset verification) |
| reason_codes | jsonb | YES | '[]' | Issues detected (stale_statement, low_balance, etc.) |
| created_at | timestamp with time zone | YES | CURRENT_TIMESTAMP | Record creation timestamp |
| updated_at | timestamp with time zone | YES | CURRENT_TIMESTAMP | Record update timestamp |

#### Relationships

**Belongs to:**
- **asset_verifications** (asset_verification_id) - Parent verification
- **accounts** (account_id) - Associated account
- **fraud_postgresql.proof** (document_id) - Source document (cross-DB)

#### Business Logic

**Statement Period:**
- Typically monthly (30-31 days)
- Must be recent (<30 days from submission date)
- Multiple statements can be provided for same account

**Balance Verification:**
- end_balance used for asset calculation
- start_balance vs end_balance comparison for consistency check
- Large discrepancies flag for manual review

**Reason Codes (JSONB Array):**
- **stale_statement:** Statement older than 30 days
- **low_balance:** Balance below threshold
- **name_mismatch:** Account holder doesn't match applicant
- **incomplete_statement:** Missing required fields
- **duplicate_statement:** Same statement uploaded multiple times

#### Query Examples

```sql
-- Statements for verification
SELECT
    s.id,
    s.document_id,
    a.institution_name,
    a.account_type,
    s.start_date,
    s.end_date,
    s.start_balance,
    s.end_balance,
    s.end_balance - s.start_balance as balance_change,
    s.reason_codes
FROM di.statements s
JOIN di.accounts a ON s.account_id = a.id
WHERE s.asset_verification_id = 'uuid-here'
ORDER BY s.end_date DESC;

-- Statements with issues
SELECT
    s.id,
    s.document_id,
    a.institution_name,
    s.end_date,
    s.end_balance,
    s.reason_codes
FROM di.statements s
JOIN di.accounts a ON s.account_id = a.id
WHERE jsonb_array_length(s.reason_codes) > 0
ORDER BY s.end_date DESC;

-- Statement recency check
SELECT
    s.id,
    s.document_id,
    a.institution_name,
    s.end_date,
    NOW() - s.end_date as days_old,
    CASE
        WHEN s.end_date > NOW() - interval '30 days' THEN 'Recent'
        WHEN s.end_date > NOW() - interval '60 days' THEN 'Acceptable'
        ELSE 'Stale'
    END as recency_status
FROM di.statements s
JOIN di.accounts a ON s.account_id = a.id
WHERE s.asset_verification_id = 'uuid-here';
```

---

### asset_verification_status_codes

**Purpose:** Lookup table for asset verification processing status codes

**Primary Key:** code (integer)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| code | integer | NO | - | Primary key (status code) |
| name | text | NO | - | Status name/description |
| created_at | timestamp with time zone | YES | CURRENT_TIMESTAMP | Record creation timestamp |

#### Common Status Codes (Inferred)

| Code | Name | Description |
|------|------|-------------|
| 100 | Pending | Verification queued |
| 200 | Completed | Verification successful |
| 300 | In Progress | Currently processing |
| 400 | Error | Verification failed |
| 500 | Insufficient Data | Not enough documents |
| 600 | Needs Review | Manual review required |

**Note:** Actual codes may differ - query table for authoritative list

#### Query Examples

```sql
-- List all status codes
SELECT code, name, created_at
FROM di.asset_verification_status_codes
ORDER BY code;

-- Verification status distribution
SELECT
    asc.name,
    COUNT(av.id) as verification_count
FROM di.asset_verifications av
JOIN di.asset_verification_status_details avsd ON av.id = avsd.asset_verification_id
JOIN di.asset_verification_status_codes asc ON avsd.status_code = asc.code
GROUP BY asc.name
ORDER BY verification_count DESC;
```

---

### asset_verification_status_details

**Purpose:** Audit trail of asset verification status changes over time

**Primary Key:** id (uuid, auto-generated)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| asset_verification_id | uuid | NO | - | FK → asset_verifications.id |
| status_code | integer | NO | - | FK → asset_verification_status_codes.code |
| created_at | timestamp with time zone | NO | CURRENT_TIMESTAMP | Status change timestamp |

#### Relationships

**Belongs to:**
- **asset_verifications** (asset_verification_id) - Verification being tracked
- **asset_verification_status_codes** (status_code) - Status at this point

#### Business Logic

**Status Workflow:**
```
Pending (100) → In Progress (300) → Completed (200)
                      ↓
                   Error (400)
                      ↓
                 Retry → In Progress
                      ↓
              Needs Review (600) → Manual Review → Completed
```

**Use Cases:**
- Track verification processing time
- Debug failed verifications
- Monitor retry attempts
- SLA compliance tracking
- Performance metrics

#### Query Examples

```sql
-- Status history for verification
SELECT
    avsd.id,
    asc.name as status,
    avsd.created_at as status_changed_at,
    LAG(avsd.created_at) OVER (ORDER BY avsd.created_at) as previous_status_time,
    avsd.created_at - LAG(avsd.created_at) OVER (ORDER BY avsd.created_at) as time_in_status
FROM di.asset_verification_status_details avsd
JOIN di.asset_verification_status_codes asc ON avsd.status_code = asc.code
WHERE avsd.asset_verification_id = 'uuid-here'
ORDER BY avsd.created_at ASC;

-- Average verification processing time
SELECT
    AVG(EXTRACT(EPOCH FROM (completed.created_at - pending.created_at))) / 60 as avg_minutes
FROM di.asset_verification_status_details pending
JOIN di.asset_verification_status_details completed
    ON pending.asset_verification_id = completed.asset_verification_id
WHERE pending.status_code = 100  -- Pending
    AND completed.status_code = 200  -- Completed
    AND completed.created_at > pending.created_at;
```

---

### asset_verification_review

**Purpose:** Human review records for asset verifications requiring manual QA

**Primary Key:** id (uuid, auto-generated)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| asset_verification_id | uuid | NO | - | FK → asset_verifications.id |
| applicant_id | uuid | NO | - | **Cross-DB reference** to fraud_postgresql.applicants.id |
| review_type | enum | NO | - | Review type (INITIAL, QA, ESCALATION) |
| review_status | enum | NO | - | Review outcome (APPROVED, REJECTED, NEEDS_INFO) |
| reviewer | varchar(255) | YES | - | Reviewer username/ID |
| review_date | timestamp | YES | - | When review was completed |
| created_at | timestamp with time zone | NO | CURRENT_TIMESTAMP | Record creation timestamp |

#### Business Logic

**Review Types:**
- **INITIAL:** First manual review by standard reviewer
- **QA:** Quality assurance check
- **ESCALATION:** Escalated to senior reviewer

**Review Status:**
- **APPROVED:** Assets sufficient, verification passed
- **REJECTED:** Insufficient assets or failed requirements
- **NEEDS_INFO:** Additional documents or clarification required

**Review Triggers:**
- Total assets in borderline range (2-6 months rent)
- Name mismatches between applicant and account holder
- Joint accounts requiring interpretation
- Stale statements (>30 days old)
- Mixed liquid/illiquid assets
- AI confidence score below threshold

#### Query Examples

```sql
-- Reviews for verification
SELECT
    avr.id,
    avr.review_type,
    avr.review_status,
    avr.reviewer,
    avr.review_date,
    av.total_verified_assets
FROM di.asset_verification_review avr
JOIN di.asset_verifications av ON avr.asset_verification_id = av.id
WHERE avr.asset_verification_id = 'uuid-here'
ORDER BY avr.review_date DESC;

-- Review workload by reviewer
SELECT
    reviewer,
    review_type,
    COUNT(*) as review_count,
    AVG(EXTRACT(EPOCH FROM (review_date - created_at))) / 3600 as avg_review_hours
FROM di.asset_verification_review
WHERE review_date IS NOT NULL
GROUP BY reviewer, review_type
ORDER BY review_count DESC;

-- Reviews by status
SELECT
    review_status,
    COUNT(*) as count
FROM di.asset_verification_review
GROUP BY review_status
ORDER BY count DESC;
```

---

## AI Operations Tracking

### ai_operations

**Purpose:** Track AI/LLM operations for asset verification processing with model and cost metrics

**Primary Key:** id (uuid, auto-generated)

**Temporal Workflow Integration:** Links to Temporal workflow orchestration

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| asset_verification_id | uuid | NO | - | FK → asset_verifications.id |
| temporal_workflow_id | varchar | NO | - | Temporal workflow identifier |
| temporal_run_id | varchar | NO | - | Temporal run identifier |
| operation_type | varchar | NO | - | Operation type (extract_accounts, analyze_statements, etc.) |
| model_id | varchar | NO | - | AI model used (gpt-4, claude-3-opus, etc.) |
| prompt_version | varchar | NO | - | Prompt version identifier |
| input_tokens | integer | YES | - | Token count for input |
| output_tokens | integer | YES | - | Token count for output |
| success | boolean | NO | - | Whether operation succeeded |
| error_message | text | YES | - | Error details if failed |
| created_at | timestamp | NO | CURRENT_TIMESTAMP | Operation timestamp |

#### Business Logic

**Operation Types:**
- **extract_accounts:** Extract account information from statements
- **analyze_statements:** Analyze statement periods and balances
- **verify_assets:** Calculate total verified assets
- **name_matching:** Match account holder to applicant name
- **fraud_check:** Check for statement manipulation

**Model Tracking:**
- Track which AI models used for each operation
- Monitor model performance and accuracy
- Cost tracking via token counts
- A/B testing different models/prompts

**Temporal Integration:**
- Distributed workflow orchestration
- Retry logic and fault tolerance
- Workflow versioning and rollback

#### Query Examples

```sql
-- AI operations for verification
SELECT
    ao.id,
    ao.operation_type,
    ao.model_id,
    ao.prompt_version,
    ao.input_tokens,
    ao.output_tokens,
    ao.success,
    ao.error_message,
    ao.created_at
FROM di.ai_operations ao
WHERE ao.asset_verification_id = 'uuid-here'
ORDER BY ao.created_at DESC;

-- Model performance metrics
SELECT
    model_id,
    operation_type,
    COUNT(*) as total_operations,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
    AVG(input_tokens) as avg_input_tokens,
    AVG(output_tokens) as avg_output_tokens,
    SUM(input_tokens + output_tokens) as total_tokens
FROM di.ai_operations
GROUP BY model_id, operation_type
ORDER BY total_operations DESC;

-- Failed operations
SELECT
    ao.id,
    ao.asset_verification_id,
    ao.operation_type,
    ao.model_id,
    ao.error_message,
    ao.created_at
FROM di.ai_operations ao
WHERE ao.success = false
ORDER BY ao.created_at DESC;

-- Cost estimation (assuming $0.03 per 1K input tokens, $0.06 per 1K output tokens)
SELECT
    model_id,
    SUM(input_tokens) / 1000.0 * 0.03 as input_cost,
    SUM(output_tokens) / 1000.0 * 0.06 as output_cost,
    (SUM(input_tokens) / 1000.0 * 0.03) + (SUM(output_tokens) / 1000.0 * 0.06) as total_cost
FROM di.ai_operations
WHERE created_at >= DATE_TRUNC('month', NOW())
GROUP BY model_id;
```

---

### inferences

**Purpose:** Individual AI inference records with confidence scoring and review sampling

**Primary Key:** id (uuid, auto-generated)

**Cross-Database Links:**
- document_id → fraud_postgresql.proof.id
- applicant_id → fraud_postgresql.applicants.id

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| temporal_workflow_id | varchar | NO | - | Temporal workflow identifier |
| temporal_run_id | varchar | NO | - | Temporal run identifier |
| inference_type | varchar | NO | - | Type of inference (account_extraction, balance_extraction, etc.) |
| model_id | varchar | NO | - | AI model identifier |
| prompt_version | varchar | NO | - | Prompt version |
| document_id | varchar | YES | - | **Cross-DB reference** to fraud_postgresql.proof.id |
| applicant_id | varchar | YES | - | **Cross-DB reference** to fraud_postgresql.applicants.id |
| input_tokens | integer | YES | - | Input token count |
| output_tokens | integer | YES | - | Output token count |
| success | boolean | NO | - | Whether inference succeeded |
| error_message | text | YES | - | Error details if failed |
| confidence_score | numeric(5) | YES | - | Confidence score (0-100) |
| sampled_for_review | boolean | NO | false | Whether sampled for human review (QA) |
| review_reason | varchar | YES | - | Why sampled (low_confidence, random_sample, etc.) |
| run_type | varchar | YES | - | Run type (production, test, backfill) |
| created_at | timestamp | NO | now() | Inference timestamp |

#### Business Logic

**Inference Types:**
- **account_extraction:** Extract bank account details
- **balance_extraction:** Extract statement balances
- **date_extraction:** Extract statement period dates
- **institution_detection:** Identify bank/institution
- **name_extraction:** Extract account holder name

**Confidence Scoring:**
- 90-100: High confidence, auto-approve
- 70-89: Medium confidence, proceed with caution
- 50-69: Low confidence, sample for review
- <50: Very low confidence, always review

**Review Sampling Strategy:**
- **Random sampling:** 5-10% of high-confidence inferences for QA
- **Low confidence:** 100% of inferences with confidence <70
- **Error patterns:** Specific document types or institutions with known issues
- **Model evaluation:** New model versions sampled heavily initially

**Review Reasons:**
- **low_confidence:** Confidence score below threshold
- **random_sample:** Random QA sampling
- **new_model:** New model version evaluation
- **error_prone_institution:** Known problematic bank
- **complex_document:** Multi-page or unusual format

#### Query Examples

```sql
-- Inferences for document
SELECT
    i.id,
    i.inference_type,
    i.model_id,
    i.confidence_score,
    i.success,
    i.sampled_for_review,
    i.review_reason,
    i.error_message
FROM di.inferences i
WHERE i.document_id = 'document-id-here'
ORDER BY i.created_at DESC;

-- Confidence score distribution
SELECT
    inference_type,
    CASE
        WHEN confidence_score >= 90 THEN 'High (90-100)'
        WHEN confidence_score >= 70 THEN 'Medium (70-89)'
        WHEN confidence_score >= 50 THEN 'Low (50-69)'
        ELSE 'Very Low (<50)'
    END as confidence_tier,
    COUNT(*) as count,
    AVG(confidence_score) as avg_confidence
FROM di.inferences
WHERE confidence_score IS NOT NULL
GROUP BY inference_type, confidence_tier
ORDER BY inference_type, confidence_tier;

-- Sampled inferences for review
SELECT
    i.id,
    i.inference_type,
    i.confidence_score,
    i.review_reason,
    i.document_id,
    i.applicant_id,
    i.created_at
FROM di.inferences i
WHERE i.sampled_for_review = true
ORDER BY i.created_at DESC;

-- Model accuracy metrics
SELECT
    model_id,
    inference_type,
    COUNT(*) as total_inferences,
    AVG(confidence_score) as avg_confidence,
    SUM(CASE WHEN success THEN 1 ELSE 0 END)::float / COUNT(*) * 100 as success_rate
FROM di.inferences
GROUP BY model_id, inference_type
ORDER BY success_rate DESC;
```

---

## Cross-Database Relationships

### Primary Integration Point: fraud_postgresql

**asset_verifications.applicant_id → fraud_postgresql.applicants.id**

**Note:** applicant_id stored as varchar(255) in this database, but references UUID in fraud_postgresql

Likely links to:
- `applicants.id` (primary link)
- Used in joins with `asset_verification_submissions` in fraud_postgresql

**asset_verification_review.applicant_id → fraud_postgresql.applicants.id**

Direct link for review tracking:
- Links reviews to specific applicants
- Enables reviewer dashboard queries

**statements.document_id → fraud_postgresql.proof.id**

Direct link to source documents:
- Bank statements uploaded to fraud detection platform
- PDF/image files stored in S3
- Enables document retrieval for review

**inferences.document_id → fraud_postgresql.proof.id**
**inferences.applicant_id → fraud_postgresql.applicants.id**

Inference tracking links:
- Per-document AI inference results
- Applicant-level inference aggregation

### Multi-Database Query Pattern

```sql
-- Complete asset verification across databases
SELECT
    -- From fraud_postgresql
    a.id as applicant_id,
    a.full_name as applicant_name,
    e.short_id as entry_id,
    p.name as property_name,

    -- From dp_document_intelligence
    av.total_verified_assets,
    av.status as verification_status,
    av.source as verification_source,

    -- Aggregated account count
    (SELECT COUNT(*) FROM di.accounts acc WHERE acc.asset_verification_id = av.id) as account_count,

    -- Aggregated statement count
    (SELECT COUNT(*) FROM di.statements s WHERE s.asset_verification_id = av.id) as statement_count

FROM di.asset_verifications av

-- Cross-database join to fraud_postgresql
JOIN fraud_postgresql.applicants a ON av.applicant_id::uuid = a.id
JOIN fraud_postgresql.entries e ON a.entry_id = e.id
JOIN fraud_postgresql.folders f ON e.folder_id = f.id
JOIN fraud_postgresql.properties p ON f.property_id = p.id

WHERE av.status = 'COMPLETED'
ORDER BY av.created_at DESC;
```

```sql
-- Asset verification with AI metrics
SELECT
    av.applicant_id,
    av.applicant_name,
    av.total_verified_assets,
    av.status,

    -- AI operation metrics
    COUNT(DISTINCT ao.id) as ai_operations,
    SUM(ao.input_tokens + ao.output_tokens) as total_tokens,
    AVG(CASE WHEN ao.success THEN 1.0 ELSE 0.0 END) as ai_success_rate,

    -- Inference metrics
    COUNT(DISTINCT i.id) as total_inferences,
    AVG(i.confidence_score) as avg_confidence,
    SUM(CASE WHEN i.sampled_for_review THEN 1 ELSE 0 END) as sampled_count

FROM di.asset_verifications av
LEFT JOIN di.ai_operations ao ON av.id = ao.asset_verification_id
LEFT JOIN di.inferences i ON av.applicant_id = i.applicant_id

WHERE av.created_at > NOW() - interval '30 days'
GROUP BY av.applicant_id, av.applicant_name, av.total_verified_assets, av.status
ORDER BY av.created_at DESC;
```

---

## Performance Considerations

### Recommended Indexes

**asset_verifications:**
- Index on applicant_id (cross-DB lookup - CRITICAL)
- Index on status (filtering)
- Index on calculation_date (time-based queries)

**accounts:**
- Index on asset_verification_id (FK lookup)
- Composite index (asset_verification_id, account_type)

**statements:**
- Index on asset_verification_id (FK lookup)
- Index on account_id (FK lookup)
- Index on document_id (cross-DB lookup)
- Index on end_date (recency checks)

**asset_verification_status_details:**
- Composite index (asset_verification_id, created_at) for status history

**asset_verification_review:**
- Index on asset_verification_id (FK lookup)
- Index on applicant_id (cross-DB lookup)
- Index on reviewer (workload queries)

**ai_operations:**
- Index on asset_verification_id (FK lookup)
- Composite index (model_id, created_at) for metrics
- Index on temporal_workflow_id (workflow tracking)

**inferences:**
- Index on document_id (document-level queries)
- Index on applicant_id (applicant-level queries)
- Composite index (sampled_for_review, created_at) for QA sampling
- Index on confidence_score (low-confidence queries)

---

## Summary

### Key Features

**Asset Verification Service:**
- Standalone microservice for asset sufficiency analysis
- AI/ML-powered document extraction
- Multi-account aggregation
- Statement period and recency validation
- Liquid vs illiquid asset classification

**AI/ML Integration:**
- LLM-based document inference
- Model versioning and prompt tracking
- Confidence scoring for quality control
- Human review sampling for model evaluation
- Token usage and cost tracking

**Temporal Workflow:**
- Distributed workflow orchestration
- Fault-tolerant processing
- Retry logic for failures
- Workflow versioning

**Status Tracking:**
- Verification-level status workflow
- Complete audit trail
- Processing time metrics
- Error tracking and retry support

### Integration Points

**With fraud_postgresql:**
- asset_verifications.applicant_id → applicants.id
- asset_verification_review.applicant_id → applicants.id
- statements.document_id → proof (documents)
- inferences.document_id → proof (documents)
- Enables complete asset verification journey tracking

**Microservice Architecture:**
- Independent database for scalability
- Asynchronous processing via Temporal
- Status-based workflow
- Cross-database queries for reporting

---

## Related Documentation

- [DP_INCOME_VALIDATION.md](DP_INCOME_VALIDATION.md) - Income verification microservice
- [VERIFICATION_WORKFLOWS.md](VERIFICATION_WORKFLOWS.md) - Asset verification in fraud_postgresql
- [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md) - Applicants and entries
- [README.md](README.md) - Project overview

---

**Generated:** 2025-11-25
**Database:** dp_document_intelligence
**Tables Documented:** 8 (asset_verifications, accounts, statements, asset_verification_status_codes, asset_verification_status_details, asset_verification_review, ai_operations, inferences)
**Cross-Database Links:** 4 identified (applicant_id, document_id in multiple tables)
