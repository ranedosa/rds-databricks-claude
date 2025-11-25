# Fraud Detection ML Database (av_postgres)

**Generated:** 2025-11-25
**Database:** av_postgres (Microservice)
**Schema Documented:** av (Automated Verification)
**Tables Documented:** 10 tables (8 business + 2 training)

---

## Overview

This database is part of the fraud detection ML microservice that analyzes documents for authenticity using machine learning models. It stores ML fraud scores, automated rulings, document metadata extraction, error tracking, and training data for model improvement.

**Purpose:** ML-powered fraud detection scoring and automated ruling system with cross-database integration to fraud_postgresql

**Key Features:**
- ML fraud detection scoring (0-100 scale)
- Automated fraud rulings (CLEAN, FRAUD, EDITED)
- Document metadata extraction (embedded properties)
- Ruling audit trail and decision tracking
- Error logging and processing failure tracking
- Training dataset management for model retraining

**Technology Stack:**
- ML models for fraud detection
- JSONB for flexible metadata storage
- Versioned scoring API for model deployment

---

## Table of Contents

1. [Fraud Detection Core](#fraud-detection-core)
   - document_properties
   - document_scores
   - document_rulings
   - document_ruling_codes
   - document_ruling_audits
   - audit_decision_codes
2. [Error Tracking](#error-tracking)
   - document_errors
   - document_error_codes
3. [Training Data](#training-data)
   - training_documents
   - document_properties_training
4. [Cross-Database Relationships](#cross-database-relationships)

---

## Fraud Detection Core

### Entity Relationship Diagram

```
document_properties (1) ←→ (N) document_scores
     ↓
document_rulings (N)
     ↓
document_ruling_codes (lookup)
     ↓
document_ruling_audits (N)
     ↓
audit_decision_codes (lookup)
```

---

### document_properties

**Purpose:** Core document metadata with embedded properties extracted from PDF/images

**Primary Key:** id (bigint, auto-increment)

**Cross-Database Link:** upload_identifier → fraud_postgresql.proof.id

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| upload_identifier | uuid | NO | - | **Cross-DB reference** to fraud_postgresql.proof.id |
| upload_path | varchar(100) | NO | - | S3/storage file path |
| embedded_properties | jsonb | NO | - | Extracted PDF metadata (producer, creator, dates, etc.) |
| tokens | jsonb | NO | '{}' | Text tokens extracted from document |
| inserted_at | timestamp | NO | - | Record creation timestamp |

#### Relationships

**Belongs to:**
- **fraud_postgresql.proof** (upload_identifier) - Source document (cross-DB)

**Has many:**
- **document_scores** (document_id) - ML fraud scores for this document
- **document_rulings** (document_id) - Fraud rulings assigned

#### Business Logic

**Embedded Properties (JSONB):**
Document metadata extracted from PDF properties, including:
- **producer:** PDF generation software (Adobe Acrobat, Microsoft Word, etc.)
- **creator:** Application that created the original document
- **creation_date:** Document creation timestamp
- **modification_date:** Last modification timestamp
- **author:** Document author metadata
- **title:** Document title
- **pdf_version:** PDF specification version

**Fraud Indicators from Metadata:**
- Mismatched dates (creation > modification)
- Suspicious producers (known forgery tools)
- Missing metadata (stripped for concealment)
- Inconsistent metadata patterns

**Tokens (JSONB):**
Text tokens extracted via OCR or PDF text extraction:
- Used for text-based fraud detection
- Keyword matching (employer names, amounts)
- Pattern recognition (date formats, SSN patterns)

#### Query Examples

```sql
-- Get document properties with fraud scores
SELECT
    dp.id,
    dp.upload_identifier,
    dp.upload_path,
    dp.embedded_properties->>'producer' as producer,
    dp.embedded_properties->>'creator' as creator,
    dp.embedded_properties->>'creation_date' as creation_date,
    ds.score as fraud_score,
    dr.ruling as fraud_ruling
FROM av.document_properties dp
LEFT JOIN av.document_scores ds ON dp.id = ds.document_id
LEFT JOIN av.document_rulings dr ON dp.id = dr.document_id
WHERE dp.upload_identifier = 'uuid-here';

-- Suspicious producers
SELECT
    dp.embedded_properties->>'producer' as producer,
    COUNT(*) as document_count,
    AVG(ds.score) as avg_fraud_score
FROM av.document_properties dp
JOIN av.document_scores ds ON dp.id = ds.document_id
WHERE dp.embedded_properties->>'producer' IS NOT NULL
GROUP BY dp.embedded_properties->>'producer'
ORDER BY avg_fraud_score DESC
LIMIT 20;
```

---

### document_scores

**Purpose:** ML fraud detection scores for documents

**Primary Key:** id (bigint, auto-increment)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| document_id | bigint | NO | - | FK → document_properties.id |
| score | double precision | NO | - | Fraud score (0-100, higher = more fraudulent) |
| scoring_api_version | varchar | NO | - | API/model version used for scoring |
| predictions | jsonb | YES | - | Detailed ML model predictions |
| inserted_at | timestamp | NO | - | Score generation timestamp |

#### Relationships

**Belongs to:**
- **document_properties** (document_id) - Document being scored

#### Business Logic

**Fraud Score Interpretation:**
- **0-20:** Very low risk (CLEAN) - Auto-approve
- **21-40:** Low risk (CLEAN) - Auto-approve with monitoring
- **41-60:** Medium risk (EDITED) - Manual review recommended
- **61-80:** High risk (FRAUD) - Manual review required
- **81-100:** Very high risk (FRAUD) - Auto-reject or escalate

**Scoring API Version:**
- Tracks model version for scoring
- Enables A/B testing of models
- Allows reprocessing with newer models
- Format: "v1.2.3" or "model-2024-11-25"

**Predictions (JSONB):**
Detailed ML model outputs including:
- **confidence:** Model confidence in prediction
- **features:** Feature importance scores
- **fraud_indicators:** Specific fraud patterns detected
  - copy_move_forgery: Cloned regions detected
  - font_manipulation: Inconsistent fonts
  - metadata_mismatch: Suspicious metadata
  - text_overlay: Text added after document creation
- **sub_scores:** Per-feature fraud scores

#### Query Examples

```sql
-- Documents with high fraud scores
SELECT
    ds.id,
    dp.upload_identifier,
    ds.score,
    ds.scoring_api_version,
    ds.predictions->>'confidence' as confidence,
    ds.predictions->>'fraud_indicators' as fraud_indicators
FROM av.document_scores ds
JOIN av.document_properties dp ON ds.document_id = dp.id
WHERE ds.score > 60
ORDER BY ds.score DESC;

-- Score distribution
SELECT
    CASE
        WHEN score <= 20 THEN 'Very Low (0-20)'
        WHEN score <= 40 THEN 'Low (21-40)'
        WHEN score <= 60 THEN 'Medium (41-60)'
        WHEN score <= 80 THEN 'High (61-80)'
        ELSE 'Very High (81-100)'
    END as risk_tier,
    COUNT(*) as count,
    AVG(score) as avg_score
FROM av.document_scores
GROUP BY risk_tier
ORDER BY avg_score;

-- Model version comparison
SELECT
    scoring_api_version,
    COUNT(*) as documents_scored,
    AVG(score) as avg_score,
    MIN(inserted_at) as first_used,
    MAX(inserted_at) as last_used
FROM av.document_scores
GROUP BY scoring_api_version
ORDER BY first_used DESC;
```

---

### document_rulings

**Purpose:** Automated fraud rulings assigned to documents based on ML scores

**Primary Key:** id (bigint, auto-increment)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| document_id | bigint | NO | - | FK → document_properties.id |
| ruling_type | integer | NO | - | Type of ruling (automated, manual, override) |
| ruling | integer | NO | - | FK → document_ruling_codes.code |
| inserted_at | timestamp | NO | - | Ruling assignment timestamp |

#### Relationships

**Belongs to:**
- **document_properties** (document_id) - Document being ruled
- **document_ruling_codes** (ruling) - Ruling type

**Has many:**
- **document_ruling_audits** (document_ruling_id) - Audit trail of ruling changes

#### Business Logic

**Ruling Types (Inferred):**
- **1:** Automated (ML-based ruling)
- **2:** Manual (Human reviewer ruling)
- **3:** Override (Manual override of automated ruling)
- **4:** Escalation (Escalated to senior reviewer)

**Ruling Codes:**
- Link to document_ruling_codes table for ruling definitions
- Likely values: CLEAN, FRAUD, EDITED, NEEDS_REVIEW

**Automated Ruling Logic:**
1. ML model generates score (0-100)
2. Threshold-based ruling assignment:
   - score < 40 → CLEAN
   - 40 ≤ score < 60 → EDITED (requires review)
   - score ≥ 60 → FRAUD (requires review)
3. Human reviewer can override automated ruling
4. Override creates new ruling record with type=3

#### Query Examples

```sql
-- Rulings for document
SELECT
    dr.id,
    dr.ruling_type,
    drc.name as ruling_name,
    dr.inserted_at,
    ds.score as ml_score
FROM av.document_rulings dr
JOIN av.document_ruling_codes drc ON dr.ruling = drc.code
JOIN av.document_scores ds ON dr.document_id = ds.document_id
WHERE dr.document_id = 123
ORDER BY dr.inserted_at DESC;

-- Ruling distribution by type
SELECT
    dr.ruling_type,
    drc.name as ruling_name,
    COUNT(*) as ruling_count
FROM av.document_rulings dr
JOIN av.document_ruling_codes drc ON dr.ruling = drc.code
GROUP BY dr.ruling_type, drc.name
ORDER BY dr.ruling_type, ruling_count DESC;

-- Overridden rulings
SELECT
    dr_original.document_id,
    drc_original.name as original_ruling,
    drc_override.name as override_ruling,
    dr_override.inserted_at as override_time
FROM av.document_rulings dr_original
JOIN av.document_rulings dr_override
    ON dr_original.document_id = dr_override.document_id
    AND dr_override.ruling_type = 3  -- Override
    AND dr_override.inserted_at > dr_original.inserted_at
JOIN av.document_ruling_codes drc_original ON dr_original.ruling = drc_original.code
JOIN av.document_ruling_codes drc_override ON dr_override.ruling = drc_override.code
WHERE dr_original.ruling_type = 1  -- Original automated
ORDER BY dr_override.inserted_at DESC;
```

---

### document_ruling_codes

**Purpose:** Lookup table for fraud ruling types

**Primary Key:** code (integer)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| code | integer | NO | - | Primary key (ruling code) |
| name | varchar | NO | - | Ruling name |
| inserted_at | timestamp | NO | - | Record creation timestamp |

#### Common Ruling Codes (Inferred)

| Code | Name | Description |
|------|------|-------------|
| 1 | CLEAN | Document is authentic, no fraud detected |
| 2 | FRAUD | Document is fraudulent, reject application |
| 3 | EDITED | Document has been modified/altered |
| 4 | NEEDS_REVIEW | Requires human review (borderline score) |
| 5 | INSUFFICIENT | Not enough data to determine authenticity |

**Note:** Actual codes may differ - query table for authoritative list

#### Query Examples

```sql
-- List all ruling codes
SELECT code, name, inserted_at
FROM av.document_ruling_codes
ORDER BY code;

-- Ruling usage statistics
SELECT
    drc.code,
    drc.name,
    COUNT(dr.id) as usage_count,
    COUNT(dr.id)::float / SUM(COUNT(dr.id)) OVER () * 100 as usage_percent
FROM av.document_ruling_codes drc
LEFT JOIN av.document_rulings dr ON drc.code = dr.ruling
GROUP BY drc.code, drc.name
ORDER BY usage_count DESC;
```

---

### document_ruling_audits

**Purpose:** Audit trail of ruling decisions and changes

**Primary Key:** id (bigint, auto-increment)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| document_ruling_id | bigint | NO | - | FK → document_rulings.id |
| decision_code | integer | NO | - | FK → audit_decision_codes.code |
| inserted_at | timestamp | NO | - | Audit event timestamp |

#### Relationships

**Belongs to:**
- **document_rulings** (document_ruling_id) - Ruling being audited
- **audit_decision_codes** (decision_code) - Decision type

#### Business Logic

**Audit Trail Purpose:**
- Track all ruling decisions and changes
- Compliance and regulatory requirements
- Quality assurance and reviewer performance
- Model accuracy measurement
- Dispute resolution support

**Decision Codes:**
Link to audit_decision_codes for decision types:
- **Ruling assigned:** Initial automated ruling
- **Ruling accepted:** Reviewer confirmed automated ruling
- **Ruling overridden:** Reviewer changed automated ruling
- **Ruling escalated:** Case escalated to senior reviewer

#### Query Examples

```sql
-- Audit trail for ruling
SELECT
    dra.id,
    adc.name as decision,
    dra.inserted_at as decision_time,
    dr.ruling_type,
    drc.name as ruling
FROM av.document_ruling_audits dra
JOIN av.audit_decision_codes adc ON dra.decision_code = adc.code
JOIN av.document_rulings dr ON dra.document_ruling_id = dr.id
JOIN av.document_ruling_codes drc ON dr.ruling = drc.code
WHERE dra.document_ruling_id = 123
ORDER BY dra.inserted_at ASC;

-- Decision frequency
SELECT
    adc.name as decision,
    COUNT(*) as frequency
FROM av.document_ruling_audits dra
JOIN av.audit_decision_codes adc ON dra.decision_code = adc.code
GROUP BY adc.name
ORDER BY frequency DESC;
```

---

### audit_decision_codes

**Purpose:** Lookup table for audit decision types

**Primary Key:** code (integer)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| code | integer | NO | - | Primary key (decision code) |
| name | varchar | NO | - | Decision name |
| inserted_at | timestamp | NO | - | Record creation timestamp |

#### Common Decision Codes (Inferred)

| Code | Name | Description |
|------|------|-------------|
| 1 | Ruling Assigned | Automated ruling initially assigned |
| 2 | Ruling Accepted | Reviewer confirmed automated ruling |
| 3 | Ruling Overridden | Reviewer changed automated ruling |
| 4 | Ruling Escalated | Case escalated for review |
| 5 | Ruling Appealed | Applicant disputed ruling |

**Note:** Actual codes may differ - query table for authoritative list

#### Query Examples

```sql
-- List all decision codes
SELECT code, name, inserted_at
FROM av.audit_decision_codes
ORDER BY code;
```

---

## Error Tracking

### document_errors

**Purpose:** Processing errors and failures during document analysis

**Primary Key:** id (bigint, auto-increment)

**Cross-Database Link:** upload_identifier → fraud_postgresql.proof.id

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| upload_identifier | uuid | NO | - | **Cross-DB reference** to fraud_postgresql.proof.id |
| error_code | integer | NO | - | FK → document_error_codes.code |
| error_message | varchar | NO | - | Detailed error message |
| inserted_at | timestamp | NO | - | Error occurrence timestamp |

#### Relationships

**Belongs to:**
- **fraud_postgresql.proof** (upload_identifier) - Document that failed (cross-DB)
- **document_error_codes** (error_code) - Error type

#### Business Logic

**Error Tracking Purpose:**
- Monitor processing failures
- Identify problematic document types
- Track ML model errors
- Support debugging and troubleshooting
- Retry logic for transient failures

**Common Error Scenarios:**
- PDF parsing failures (corrupted files)
- OCR failures (poor image quality)
- ML model timeouts
- Unsupported document formats
- Missing metadata extraction

#### Query Examples

```sql
-- Recent errors
SELECT
    de.id,
    de.upload_identifier,
    dec.name as error_type,
    de.error_message,
    de.inserted_at
FROM av.document_errors de
JOIN av.document_error_codes dec ON de.error_code = dec.code
ORDER BY de.inserted_at DESC
LIMIT 100;

-- Error frequency by type
SELECT
    dec.name as error_type,
    dec.description,
    COUNT(*) as error_count,
    MAX(de.inserted_at) as last_occurrence
FROM av.document_errors de
JOIN av.document_error_codes dec ON de.error_code = dec.code
GROUP BY dec.name, dec.description
ORDER BY error_count DESC;

-- Documents with errors
SELECT
    upload_identifier,
    COUNT(*) as error_count,
    STRING_AGG(DISTINCT dec.name, ', ') as error_types
FROM av.document_errors de
JOIN av.document_error_codes dec ON de.error_code = dec.code
GROUP BY upload_identifier
HAVING COUNT(*) > 1
ORDER BY error_count DESC;
```

---

### document_error_codes

**Purpose:** Lookup table for error types

**Primary Key:** code (integer)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| code | integer | NO | - | Primary key (error code) |
| name | varchar | NO | - | Error name |
| description | varchar | NO | - | Error description |
| inserted_at | timestamp | NO | - | Record creation timestamp |

#### Common Error Codes (Inferred)

| Code | Name | Description |
|------|------|-------------|
| 1 | PDF_PARSE_ERROR | Failed to parse PDF document |
| 2 | OCR_FAILURE | OCR extraction failed |
| 3 | ML_MODEL_TIMEOUT | ML model inference timeout |
| 4 | UNSUPPORTED_FORMAT | Document format not supported |
| 5 | METADATA_EXTRACTION_ERROR | Failed to extract PDF metadata |
| 6 | CORRUPT_FILE | File is corrupted or unreadable |
| 7 | FILE_TOO_LARGE | Document exceeds size limit |

**Note:** Actual codes may differ - query table for authoritative list

#### Query Examples

```sql
-- List all error codes
SELECT code, name, description, inserted_at
FROM av.document_error_codes
ORDER BY code;
```

---

## Training Data

### training_documents

**Purpose:** Training dataset for ML model retraining and improvement

**Primary Key:** None (appears to be a simple reference table)

**Cross-Database Link:** proof_id → fraud_postgresql.proof.id

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| proof_id | uuid | YES | - | **Cross-DB reference** to fraud_postgresql.proof.id |
| file | text | YES | - | S3/storage file path |
| proof_inserted_at | text | YES | - | Original document insertion timestamp (stored as text) |

#### Business Logic

**Training Dataset Purpose:**
- Collect documents for ML model retraining
- Store ground truth labels (CLEAN vs FRAUD)
- Improve model accuracy over time
- A/B test new model versions

**Dataset Selection:**
- Documents with human review (ground truth labels)
- Diverse fraud patterns and clean documents
- Recent documents (within 6-12 months)
- Balanced dataset (50/50 CLEAN vs FRAUD)

**Model Retraining Workflow:**
1. Select documents from training_documents
2. Extract features via document_properties_training
3. Train new ML model version
4. A/B test new vs current model
5. Deploy better performing model

#### Query Examples

```sql
-- Training documents
SELECT
    td.proof_id,
    td.file,
    td.proof_inserted_at
FROM av.training_documents td
ORDER BY td.proof_inserted_at DESC;

-- Training dataset size
SELECT COUNT(*) as training_document_count
FROM av.training_documents;
```

---

### document_properties_training

**Purpose:** Extracted properties from training documents for model retraining

**Primary Key:** id (bigint, auto-increment)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| upload_identifier | uuid | NO | - | Training document identifier |
| upload_path | varchar(100) | NO | - | S3/storage file path |
| embedded_properties | jsonb | NO | - | Extracted PDF metadata |
| tokens | jsonb | NO | '{}' | Text tokens extracted from document |
| inserted_at | timestamp | NO | - | Record creation timestamp |

#### Business Logic

**Purpose:**
- Store feature-extracted data for training
- Separate from production document_properties
- Enables model experimentation without affecting production
- Versioned feature extraction for different model architectures

**Feature Storage:**
Same structure as document_properties but dedicated to training:
- embedded_properties: PDF metadata features
- tokens: Text-based features
- Can include additional experimental features

#### Query Examples

```sql
-- Training document properties
SELECT
    dpt.id,
    dpt.upload_identifier,
    dpt.embedded_properties->>'producer' as producer,
    dpt.tokens
FROM av.document_properties_training dpt
ORDER BY dpt.inserted_at DESC;

-- Training data statistics
SELECT
    COUNT(*) as total_documents,
    COUNT(DISTINCT embedded_properties->>'producer') as unique_producers
FROM av.document_properties_training;
```

---

## Cross-Database Relationships

### Primary Integration Point: fraud_postgresql

**document_properties.upload_identifier → fraud_postgresql.proof.id**

Direct link to source documents:
- Documents uploaded for fraud detection
- PDF/image files stored in S3
- Enables retrieval of original files

**document_errors.upload_identifier → fraud_postgresql.proof.id**

Error tracking link:
- Documents that failed processing
- Enables retry logic
- Support troubleshooting

**training_documents.proof_id → fraud_postgresql.proof.id**

Training dataset link:
- Documents selected for model training
- Ground truth labels from human reviews

### Multi-Database Query Pattern

```sql
-- Complete fraud detection across databases
SELECT
    -- From fraud_postgresql
    p.id as proof_id,
    p.type as document_type,
    p.result as final_result,
    a.full_name as applicant_name,

    -- From av_postgres
    dp.embedded_properties->>'producer' as pdf_producer,
    ds.score as ml_fraud_score,
    ds.scoring_api_version as model_version,
    drc.name as automated_ruling

FROM av.document_properties dp
JOIN av.document_scores ds ON dp.id = ds.document_id
LEFT JOIN av.document_rulings dr ON dp.id = dr.document_id
LEFT JOIN av.document_ruling_codes drc ON dr.ruling = drc.code

-- Cross-database join to fraud_postgresql
JOIN fraud_postgresql.proof p ON dp.upload_identifier = p.id
JOIN fraud_postgresql.entries e ON p.entry_id = e.id
JOIN fraud_postgresql.applicants a ON e.id = (
    SELECT entry_id FROM fraud_postgresql.applicants WHERE id = a.id LIMIT 1
)

WHERE ds.score > 60  -- High fraud risk
ORDER BY ds.score DESC;
```

```sql
-- Error analysis across databases
SELECT
    de.upload_identifier,
    p.type as document_type,
    dec.name as error_type,
    de.error_message,
    de.inserted_at,
    a.full_name as applicant_name
FROM av.document_errors de
JOIN av.document_error_codes dec ON de.error_code = dec.code

-- Cross-database join
JOIN fraud_postgresql.proof p ON de.upload_identifier = p.id
JOIN fraud_postgresql.entries e ON p.entry_id = e.id
JOIN fraud_postgresql.applicants a ON e.id = (
    SELECT entry_id FROM fraud_postgresql.applicants WHERE id = a.id LIMIT 1
)

WHERE de.inserted_at > NOW() - interval '7 days'
ORDER BY de.inserted_at DESC;
```

---

## Performance Considerations

### Recommended Indexes

**document_properties:**
- Index on upload_identifier (cross-DB lookup - CRITICAL)
- Index on inserted_at (time-based queries)

**document_scores:**
- Index on document_id (FK lookup)
- Index on score (filtering by risk level)
- Composite index (scoring_api_version, inserted_at) for model comparison

**document_rulings:**
- Index on document_id (FK lookup)
- Index on ruling (filtering by ruling type)
- Composite index (ruling_type, inserted_at) for audit queries

**document_ruling_audits:**
- Index on document_ruling_id (FK lookup)
- Composite index (decision_code, inserted_at) for decision analysis

**document_errors:**
- Index on upload_identifier (cross-DB lookup)
- Index on error_code (filtering by error type)
- Index on inserted_at (time-based queries)

---

## Summary

### Key Features

**ML Fraud Detection:**
- Automated fraud scoring (0-100 scale)
- Threshold-based automated rulings
- Model versioning and A/B testing
- Detailed predictions and feature importance

**Document Analysis:**
- PDF metadata extraction (embedded_properties)
- Text token extraction for pattern matching
- Fraud indicator detection (copy-move forgery, font manipulation)

**Audit & Compliance:**
- Complete ruling audit trail
- Decision tracking for regulatory compliance
- Override and escalation tracking
- Model accuracy measurement

**Error Tracking:**
- Comprehensive error logging
- Error type categorization
- Support for retry logic
- Troubleshooting and debugging

**Training Data Management:**
- Training dataset curation
- Feature extraction for model training
- Ground truth label collection
- Model improvement workflow

### Integration Points

**With fraud_postgresql:**
- document_properties.upload_identifier → proof.id
- document_errors.upload_identifier → proof.id
- training_documents.proof_id → proof.id
- Enables complete fraud detection journey tracking

**Microservice Architecture:**
- Independent ML service database
- Versioned scoring API
- Asynchronous processing
- Cross-database queries for reporting

---

## Related Documentation

- [DP_INCOME_VALIDATION.md](DP_INCOME_VALIDATION.md) - Income verification microservice
- [DP_DOCUMENT_INTELLIGENCE.md](DP_DOCUMENT_INTELLIGENCE.md) - Asset verification microservice
- [FRAUD_DETECTION_WORKFLOW.md](FRAUD_DETECTION_WORKFLOW.md) - Main fraud detection workflow
- [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md) - Applicants and documents
- [README.md](README.md) - Project overview

---

**Generated:** 2025-11-25
**Database:** av_postgres
**Tables Documented:** 10 (document_properties, document_scores, document_rulings, document_ruling_codes, document_ruling_audits, audit_decision_codes, document_errors, document_error_codes, training_documents, document_properties_training)
**Cross-Database Links:** 3 identified (upload_identifier in document_properties and document_errors, proof_id in training_documents)
