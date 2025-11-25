# Fraud Detection Workflow - Document Verification System

**Generated:** 2025-11-25
**Database:** fraud_postgresql (Production)
**Tables Documented:** 7 fraud detection tables

---

## Overview

The Fraud Detection Workflow represents Snappt's core fraud screening process. When an applicant submits documents (paystubs, bank statements) for verification, these tables track the fraud analysis from document upload through ML/AI analysis to final human review and determination.

### Workflow Summary

```
1. Entry Created (Core Entity)
2. Applicant Submits Documents → applicant_submission
3. Documents Stored → proof table
4. Document Sources Tracked → applicant_submission_document_sources
5. Fraud Analysis Initiated → fraud_submissions
6. Human Review (if needed) → fraud_reviews
7. Document-level Results → fraud_document_reviews
8. Final Determination → fraud_results
9. Entry Result Updated (Core Entity)
```

---

## Table Inventory

### Document Management (2 tables)
- **proof** - Uploaded documents (files, metadata, ML analysis results)
- **applicant_submission_document_sources** - Links submissions to documents, tracks source type

### Fraud Detection Flow (5 tables)
- **fraud_submissions** - Fraud analysis requests for specific documents
- **fraud_reviews** - Human review of fraud submissions
- **fraud_document_reviews** - Document-level review results within a fraud review
- **fraud_results** - Final fraud determination for the entire submission
- **fraud_result_types** - Lookup table for result codes (CLEAN, FRAUD, EDITED, etc.)

---

## Integration with Core Entities

```
entries (Core)
  └─> applicants (Core)
       └─> applicant_submissions (Core)
            ├─> applicant_submission_document_sources (Fraud)
            │    └─> proof (documents) (Fraud)
            │         └─> fraud_submissions (Fraud)
            │              └─> fraud_reviews (Fraud)
            │                   └─> fraud_document_reviews (Fraud)
            └─> fraud_results (Fraud - final determination)
```

---

## Detailed Table Documentation

## 1. PROOF

**Purpose:** Stores uploaded documents (paystubs, bank statements, ID, etc.) with ML/AI analysis results.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| entry_id | uuid | YES | **FK → entries.id** |
| short_id | varchar(255) | YES | Human-readable ID |
| file | text | YES | File URL/path in storage |
| thumb | text | YES | Thumbnail URL/path |
| type | USER-DEFINED (enum) | NO | Document type (paystub, bank_statement, etc.) |
| result | USER-DEFINED (enum) | NO | Final ruling (PENDING, CLEAN, FRAUD, EDITED, etc.) (default: PENDING) |
| suggested_ruling | USER-DEFINED (enum) | NO | ML/AI suggested result (default: NOT_RUN) |
| automatic_ruling_result | varchar(255) | YES | Automated system result |
| note | text | YES | Reviewer notes |
| extracted_meta | jsonb | YES | Metadata extracted from document (OCR, dates, amounts) |
| test_extracted_meta | jsonb | YES | Test/experimental metadata extraction |
| meta_data_flags | array (varchar) | NO | Fraud indicators/flags detected (default: []) |
| test_meta_data_flags | jsonb | NO | Test/experimental flags (default: {}) |
| test_suggested_ruling | USER-DEFINED (enum) | NO | Test ruling (default: NOT_RUN) |
| text_breakups | jsonb | YES | Text analysis/segmentation (default: []) |
| text_breakups_file | varchar(255) | YES | File path for text analysis |
| similarity_check | array (jsonb) | NO | Duplicate/similar document detection (default: []) |
| has_text | boolean | YES | Whether document contains extractable text |
| has_password_protection | boolean | YES | Password-protected PDF flag |
| has_exceeded_page_limit | boolean | YES | Too many pages flag |
| jobs_error | array (jsonb) | NO | Processing errors (default: []) |
| result_edited_reason | array (varchar) | NO | Reasons for EDITED result (default: []) |
| result_insufficient_reason | varchar(255) | YES | Reason for INSUFFICIENT result |
| result_clean_proceed_with_caution_reason | varchar(255) | NO | Caution flags for CLEAN result (default: NONE) |
| is_automatic_review | boolean | YES | Automated review flag (default: false) |
| manual_review_recommended | boolean | YES | Flag to escalate to human review |
| inserted_at | timestamp | NO | Upload timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** entries (via entry_id)
- **Referenced by:** applicant_submission_document_sources (indirectly)
- **Referenced by:** fraud_submissions (indirectly via document sources)

### Business Logic

**Document Types (type enum):**
- paystub
- bank_statement
- tax_transcript
- utility_bill
- credit_debit_card_statement
- social_security_statement
- investment_account
- cash_app_statement
- etc.

**Result Types (result enum):**
- PENDING - Not yet reviewed
- CLEAN - No fraud detected
- FRAUD - Fraud detected
- EDITED - Document has been altered/manipulated
- INSUFFICIENT - Cannot determine (poor quality, missing pages)
- PROCEED_WITH_CAUTION - Suspicious but not definitive fraud

**ML/AI Analysis:**
- `extracted_meta` (JSONB) contains OCR results, dates, amounts, employer names, etc.
- `meta_data_flags` array contains fraud indicators:
  - "copy_move_forgery" - Cloning within document
  - "metadata_mismatch" - File metadata doesn't match content
  - "font_manipulation" - Inconsistent fonts
  - "number_sequence_anomaly" - Suspicious number patterns
  - "date_inconsistency" - Date logic errors
- `suggested_ruling` is ML/AI recommendation
- `result` is final determination (after human review if needed)
- `similarity_check` detects duplicate submissions across different entries

**Review Workflow:**
- If `suggested_ruling` is high confidence CLEAN → automatic approval
- If fraud indicators detected → human review required
- `manual_review_recommended` flag escalates to fraud detection team
- Reviewer can override `suggested_ruling` with final `result`
- `note` field captures reviewer reasoning

---

## 2. APPLICANT_SUBMISSION_DOCUMENT_SOURCES

**Purpose:** Links applicant submissions to specific documents, tracking document source type.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| applicant_submission_id | uuid | NO | **FK → applicant_submissions.id** |
| source_type | varchar(255) | NO | Document source (manual_upload, yardi, email, etc.) |
| inserted_at | timestamp | NO | Link creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** applicant_submissions (via applicant_submission_id)
- **Implicitly links to:** proof table (via external reference, not direct FK)

### Business Logic
- Tracks **how** documents were received
- `source_type` values:
  - "manual_upload" - Applicant uploaded via web form
  - "yardi" - Imported from Yardi integration
  - "email" - Emailed documents
  - "api" - Third-party API integration
- Multiple documents can belong to one submission
- Critical for audit trail and integration tracking

---

## 3. FRAUD_SUBMISSIONS

**Purpose:** Represents a fraud analysis request for a specific document/document set.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| applicant_submission_document_source_id | uuid | NO | Links to document source (note: not a declared FK in schema) |
| inserted_at | timestamp | NO | Fraud analysis start timestamp |

### Relationships
- **Implicitly belongs to:** applicant_submission_document_sources (via applicant_submission_document_source_id)
- **Has many:** fraud_reviews

### Business Logic
- Created when documents need fraud analysis
- One fraud_submission per document set submitted
- Triggers ML/AI analysis pipeline
- May result in multiple fraud_reviews (initial review + escalations)

**Note:** The FK constraint may not be explicitly declared in the database but the relationship exists via `applicant_submission_document_source_id`.

---

## 4. FRAUD_REVIEWS

**Purpose:** Human review of a fraud submission. Tracks reviewer assignment, status, and final determination.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| fraud_submission_id | uuid | NO | **FK → fraud_submissions.id** |
| reviewer_id | uuid | YES | **FK → users.id** (reviewer who completed this) |
| fraud_type | varchar(255) | NO | Type of fraud detected/suspected |
| status | varchar(255) | NO | Review status (PENDING, IN_PROGRESS, COMPLETED) |
| result | integer | YES | **FK → fraud_result_types.id** (final determination) |
| result_reason | varchar(255) | YES | Reason/explanation for result |
| review_type | varchar(255) | NO | Review type (INITIAL, ESCALATION, QA) (default: INITIAL) |
| assigned_date | timestamp | YES | When assigned to reviewer |
| completed_date | timestamp | YES | When review was completed |
| inserted_at | timestamp | NO | Review creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** fraud_submissions (via fraud_submission_id)
- **Belongs to:** users (reviewer, via reviewer_id)
- **Belongs to:** fraud_result_types (via result)
- **Has many:** fraud_document_reviews

### Business Logic

**Fraud Types (fraud_type):**
- "document_manipulation" - Document has been edited/altered
- "identity_theft" - Fraudulent identity
- "income_inflation" - Exaggerated income
- "synthetic_document" - Fully fabricated document
- "duplicate_submission" - Same documents used for multiple applications

**Status Values:**
- PENDING - Awaiting reviewer assignment
- IN_PROGRESS - Reviewer is actively working
- COMPLETED - Review finished

**Review Types (review_type):**
- INITIAL - First review of submission
- ESCALATION - Escalated for senior review
- QA - Quality assurance check

**Workflow:**
1. fraud_review created when fraud_submission needs human review
2. Assigned to reviewer (reviewer_id set, status → IN_PROGRESS)
3. Reviewer examines documents and fraud_document_reviews
4. Reviewer sets `result` and `result_reason`
5. Status → COMPLETED, `completed_date` set
6. Result propagates to entry-level determination

---

## 5. FRAUD_DOCUMENT_REVIEWS

**Purpose:** Document-level review results within a fraud review. Allows per-document determination.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| fraud_review_id | uuid | NO | **FK → fraud_reviews.id** |
| document_id | uuid | NO | Links to proof.id (note: not a declared FK) |
| result | integer | NO | **FK → fraud_result_types.id** (CLEAN, FRAUD, etc.) |
| source_type | varchar(255) | YES | Document source type |
| inserted_at | timestamp | NO | Review timestamp |

### Relationships
- **Belongs to:** fraud_reviews (via fraud_review_id)
- **Belongs to:** fraud_result_types (via result)
- **Implicitly belongs to:** proof (via document_id)

### Business Logic
- Allows **per-document** fraud determination within a submission
- Example: Applicant submits 2 paystubs + 1 bank statement
  - Paystub 1 → CLEAN
  - Paystub 2 → EDITED (document manipulation detected)
  - Bank statement → CLEAN
  - **Overall fraud_review result → FRAUD** (one bad document fails the submission)
- `source_type` tracks where document came from
- Final entry-level result is **worst case** across all documents

---

## 6. FRAUD_RESULTS

**Purpose:** Final fraud determination for an entire applicant submission.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| applicant_submission_id | uuid | NO | **FK → applicant_submissions.id** |
| result | integer | NO | **FK → fraud_result_types.id** (final determination) |
| inserted_at | timestamp | NO | Result timestamp |

### Relationships
- **Belongs to:** applicant_submissions (via applicant_submission_id)
- **Belongs to:** fraud_result_types (via result)

### Business Logic
- **One fraud_result per applicant_submission**
- Aggregates results from all fraud_reviews and fraud_document_reviews
- This is the **final determination** that updates the entry result
- Result propagates:
  1. fraud_document_reviews (per-document) → fraud_reviews (per-submission)
  2. fraud_reviews → fraud_results (per-applicant_submission)
  3. fraud_results → entries.result (overall entry determination)

---

## 7. FRAUD_RESULT_TYPES

**Purpose:** Lookup table for fraud result codes.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| code | varchar(255) | NO | Result code (CLEAN, FRAUD, EDITED, etc.) |

### Result Codes

| ID | Code | Meaning |
|----|------|---------|
| 1 | CLEAN | No fraud detected, document is authentic |
| 2 | FRAUD | Definitive fraud detected |
| 3 | EDITED | Document has been manipulated/altered |
| 4 | INSUFFICIENT | Cannot determine (poor quality, missing info) |
| 5 | PROCEED_WITH_CAUTION | Suspicious but not definitive |

**Note:** Actual IDs may vary; these are typical values.

---

## Complete Data Flow: Fraud Detection Lifecycle

### Step-by-Step Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. DOCUMENT SUBMISSION                                          │
└─────────────────────────────────────────────────────────────────┘
   Property manager creates entry for applicant
   ↓
   Applicant receives email with submission link
   ↓
   Applicant uploads documents (paystubs, bank statements)
   ↓
   Documents stored in proof table
   ↓
   applicant_submission created
   ↓
   applicant_submission_document_sources created (links submission to documents)

┌─────────────────────────────────────────────────────────────────┐
│ 2. ML/AI ANALYSIS (Automated)                                   │
└─────────────────────────────────────────────────────────────────┘
   fraud_submission created for document set
   ↓
   ML/AI pipeline processes each document (proof):
     - OCR extraction → proof.extracted_meta
     - Fraud detection → proof.meta_data_flags
     - ML model inference → proof.suggested_ruling
   ↓
   Example fraud flags detected:
     - "copy_move_forgery" - Text/numbers duplicated within document
     - "metadata_mismatch" - File creation date doesn't match content dates
     - "font_manipulation" - Inconsistent fonts/styling

┌─────────────────────────────────────────────────────────────────┐
│ 3. ROUTING DECISION                                             │
└─────────────────────────────────────────────────────────────────┘
   IF suggested_ruling = CLEAN AND no fraud flags detected:
     → Automatic approval (skip human review)
     → fraud_results created with result = CLEAN
     → entries.result updated to CLEAN

   ELSE IF fraud flags detected OR low ML confidence:
     → Route to human review
     → fraud_review created
     → Assigned to fraud detection team

┌─────────────────────────────────────────────────────────────────┐
│ 4. HUMAN REVIEW (If needed)                                     │
└─────────────────────────────────────────────────────────────────┘
   fraud_review assigned to reviewer
   ↓
   Reviewer examines:
     - Original documents (proof.file)
     - ML analysis (proof.extracted_meta, proof.meta_data_flags)
     - Similarity checks (proof.similarity_check)
     - Suggested ruling (proof.suggested_ruling)
   ↓
   Reviewer creates fraud_document_reviews for each document:
     - Paystub 1 → CLEAN (authentic)
     - Paystub 2 → EDITED (font inconsistencies, altered amounts)
     - Bank statement → CLEAN (authentic)
   ↓
   Reviewer sets overall fraud_review result = FRAUD
   ↓
   Reviewer adds fraud_review.result_reason: "Paystub 2 shows clear evidence
   of font manipulation and number alteration. Amounts do not match bank
   statement deposits."

┌─────────────────────────────────────────────────────────────────┐
│ 5. FINAL DETERMINATION                                          │
└─────────────────────────────────────────────────────────────────┘
   fraud_results created/updated:
     - applicant_submission_id → links to submission
     - result = FRAUD (worst case across all documents)
   ↓
   entry.result updated to FRAUD
   ↓
   folder.result updated to FRAUD
   ↓
   Property manager receives notification
   ↓
   Applicant receives fraud determination (if configured)

┌─────────────────────────────────────────────────────────────────┐
│ 6. ESCALATION (Optional)                                        │
└─────────────────────────────────────────────────────────────────┘
   IF property manager disputes result:
     → New fraud_review created with review_type = ESCALATION
     → Assigned to senior fraud analyst or QA team
     → Re-review process
     → Final determination binding
```

---

## Key Fraud Indicators

Based on the `proof.meta_data_flags` array, the system detects:

### Document Manipulation
- **copy_move_forgery** - Cloning of text/numbers within document
- **font_manipulation** - Inconsistent fonts or styling
- **splicing** - Document pieced together from multiple sources
- **metadata_mismatch** - File metadata inconsistent with document content

### Content Anomalies
- **number_sequence_anomaly** - Suspicious number patterns or sequences
- **date_inconsistency** - Date logic errors (e.g., paystub date after submission)
- **employer_name_mismatch** - Employer name doesn't match known companies
- **amount_inconsistency** - Income amounts don't reconcile across documents

### Duplicate Detection
- **duplicate_submission** - Same documents used for multiple applications
- **high_similarity_match** - Very similar to other flagged documents

---

## ML/AI Integration Points

### proof Table ML Fields

1. **extracted_meta (JSONB)**
   ```json
   {
     "employer": "Acme Corporation",
     "pay_period_start": "2024-01-01",
     "pay_period_end": "2024-01-15",
     "gross_pay": 3500.00,
     "net_pay": 2650.00,
     "employee_name": "John Smith",
     "employee_address": "123 Main St",
     "dates_found": ["2024-01-01", "2024-01-15", "2024-01-16"]
   }
   ```

2. **meta_data_flags (Array)**
   ```
   ["copy_move_forgery", "font_manipulation"]
   ```

3. **suggested_ruling (Enum)**
   - NOT_RUN - ML not yet executed
   - CLEAN - ML suggests authentic
   - FRAUD - ML suggests fraud
   - EDITED - ML detects manipulation
   - REQUIRES_REVIEW - ML uncertain

4. **similarity_check (Array of JSONB)**
   ```json
   [
     {
       "entry_id": "uuid-123",
       "similarity_score": 0.95,
       "matching_proof_id": "uuid-456"
     }
   ]
   ```

---

## Performance Considerations

### Indexes Recommended

```sql
-- Fraud detection query patterns
CREATE INDEX idx_fraud_submissions_document_source
  ON fraud_submissions(applicant_submission_document_source_id);

CREATE INDEX idx_fraud_reviews_submission
  ON fraud_reviews(fraud_submission_id);

CREATE INDEX idx_fraud_reviews_reviewer_status
  ON fraud_reviews(reviewer_id, status)
  WHERE status != 'COMPLETED';

CREATE INDEX idx_fraud_document_reviews_review
  ON fraud_document_reviews(fraud_review_id);

CREATE INDEX idx_fraud_results_submission
  ON fraud_results(applicant_submission_id);

-- Proof table query patterns
CREATE INDEX idx_proof_entry
  ON proof(entry_id);

CREATE INDEX idx_proof_result_suggested
  ON proof(result, suggested_ruling);

CREATE INDEX idx_applicant_submission_document_sources_submission
  ON applicant_submission_document_sources(applicant_submission_id);
```

### JSONB Optimization

```sql
-- GIN indexes for JSONB fields
CREATE INDEX idx_proof_extracted_meta_gin
  ON proof USING gin(extracted_meta);

CREATE INDEX idx_proof_similarity_check_gin
  ON proof USING gin(similarity_check);
```

---

## Business Rules & Validations

### Result Determination Logic

**Document-level:**
- Any document with result = FRAUD → Entire submission = FRAUD
- All documents CLEAN → Submission = CLEAN
- Any document EDITED → Submission = EDITED (unless FRAUD present)
- Any document INSUFFICIENT → Submission = INSUFFICIENT (unless FRAUD/EDITED present)

**Priority (highest to lowest):**
1. FRAUD - Definitive fraud detected
2. EDITED - Document manipulation
3. INSUFFICIENT - Cannot determine
4. PROCEED_WITH_CAUTION - Suspicious
5. CLEAN - Authentic

### Review Requirements

**Automatic approval (no human review):**
- ML confidence > 95%
- suggested_ruling = CLEAN
- No fraud flags detected
- No duplicate submissions found

**Requires human review:**
- ML confidence < 95%
- Any fraud flags detected
- suggested_ruling = FRAUD or EDITED
- Duplicate submission detected
- manual_review_recommended = true

### SLA Tracking

- Reviews should be completed within 24 hours
- fraud_reviews.assigned_date → fraud_reviews.completed_date
- Escalations have 4-hour SLA

---

## Security & Compliance

### PII Protection

The proof table contains sensitive financial documents:
- Files stored in encrypted cloud storage (not in database)
- proof.file contains only URL/path reference
- Access controlled via entry-level permissions
- Audit trail via audit_transaction_event table (separate)

### Audit Trail

All fraud determinations tracked:
- fraud_reviews.result_reason - Explanation for decision
- proof.note - Reviewer notes
- fraud_reviews.reviewer_id - Who made the determination
- fraud_reviews.completed_date - When decision was made

---

## Next Steps

With Core Entity Model and Fraud Detection Workflow documented, the next workflows to document are:

1. **Income Verification Workflow** - income_verification_submissions, income_verification_reviews, income_verification_results
2. **Asset Verification Workflow** - asset_verification_submissions, asset_verification_reviews, asset_verification_results
3. **Identity Verification Workflow** - id_verifications, id_verification flow
4. **Rent Verification Workflow** - rent_verifications, rent_verification_events

These follow similar patterns to the fraud detection workflow but with domain-specific logic.

**See:** INCOME_VERIFICATION_WORKFLOW.md (to be created next)
