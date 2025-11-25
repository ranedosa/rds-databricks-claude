# Verification Workflows - Multi-Type Verification System

**Generated:** 2025-11-25
**Database:** fraud_postgresql (Production)
**Tables Documented:** 9 verification tables

---

## Overview

Beyond fraud detection, Snappt provides additional verification services to help property managers assess applicant eligibility. These workflows verify income sufficiency, asset liquidity, identity authenticity, and rental payment history using third-party integrations and automated calculations.

### Verification Types

```
1. Income Verification → Can applicant afford rent?
2. Asset Verification → Does applicant have sufficient liquid assets?
3. Identity Verification → Is applicant who they claim to be?
4. Rent Verification → Does applicant have good rental payment history?
```

---

## Table Inventory

### Income Verification (3 tables)
- **income_verification_submissions** - Income analysis requests
- **income_verification_reviews** - Human review of income calculations
- **income_verification_results** - Final income eligibility determination

### Asset Verification (3 tables)
- **asset_verification_submissions** - Asset analysis requests
- **asset_verification_reviews** - Human review of asset calculations
- **asset_verification_results** - Final asset eligibility determination

### Identity Verification (1 table)
- **id_verifications** - Third-party identity verification (Incode, Persona)

### Rent Verification (2 tables)
- **rent_verifications** - Rental payment history checks (via third-party APIs)
- **rent_verification_events** - Event log for rent verification workflow

---

## Integration with Core Entities

```
entries (Core)
  └─> applicants (Core)
       ├─> applicant_submissions (Core)
       │    ├─> applicant_submission_document_sources
       │    │    ├─> income_verification_submissions
       │    │    │    └─> income_verification_reviews
       │    │    │         └─> income_verification_results
       │    │    └─> asset_verification_submissions
       │    │         └─> asset_verification_reviews
       │    │              └─> asset_verification_results
       │    └─> id_verifications (via applicant_detail_id)
       └─> rent_verifications
            └─> rent_verification_events
```

---

# Income Verification Workflow

## Overview

Income verification analyzes submitted documents (paystubs, bank statements, tax returns) to calculate total income and determine if applicant meets property's income requirements (typically 2.5-3x monthly rent).

### Workflow Steps

1. Documents uploaded and fraud-checked
2. Income calculation triggered
3. Automated system extracts income amounts and calculates totals
4. Review eligibility determined (APPROVED/REJECTED/NEEDS_REVIEW)
5. If needs review → assigned to human reviewer
6. Final determination stored in results table
7. Result propagates to entry

---

## 1. INCOME_VERIFICATION_SUBMISSIONS

**Purpose:** Initiates income calculation for a document set.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| entry_id | uuid | NO | **FK → entries.id** |
| applicant_submission_document_source_id | uuid | YES | **FK → applicant_submission_document_sources.id** |
| review_eligibility | varchar(255) | NO | Eligibility status (APPROVED, REJECTED, NEEDS_REVIEW) |
| rejection_reason | varchar(255) | YES | Why rejected (if applicable) |
| inserted_at | timestamp | NO | Submission timestamp |

### Relationships
- **Belongs to:** entries (via entry_id)
- **Belongs to:** applicant_submission_document_sources (via applicant_submission_document_source_id)
- **Has many:** income_verification_reviews

### Business Logic

**Review Eligibility Values:**
- **APPROVED** - Income meets requirements, no human review needed
- **REJECTED** - Income insufficient or cannot calculate
- **NEEDS_REVIEW** - Edge case requiring human judgment

**Rejection Reasons:**
- "insufficient_income" - Total income below property requirement
- "cannot_calculate" - Documents unclear, can't extract amounts
- "mismatched_documents" - Income sources don't align
- "employment_gap" - Recent employment gaps detected
- "inconsistent_income" - Highly variable income patterns

**Automated Approval:**
- Income ≥ 3x monthly rent
- Consistent income sources
- No fraud flags on documents
- Clear document quality

**Requires Human Review:**
- Income between 2.5x-3x rent (edge case)
- Self-employed/variable income
- Multiple income sources requiring verification
- Recent employment changes

---

## 2. INCOME_VERIFICATION_REVIEWS

**Purpose:** Human review of income verification when automated system cannot make determination.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| income_verification_submission_id | uuid | NO | **FK → income_verification_submissions.id** |
| reviewer_id | uuid | NO | **FK → users.id** |
| status | varchar(255) | NO | Review status (PENDING, IN_PROGRESS, COMPLETED) |
| type | varchar(255) | NO | Review type (INITIAL, ESCALATION) (default: INITIAL) |
| review_method | USER-DEFINED (enum) | NO | How reviewed (AUTOMATED, MANUAL) (default: AUTOMATED) |
| calculation_id | uuid | YES | Links to external calculation service |
| rejection_reason | varchar(255) | YES | Reason for rejection |
| assigned_date | timestamp | YES | When assigned to reviewer |
| completed_date | timestamp | YES | When review completed |
| inserted_at | timestamp | NO | Review creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** income_verification_submissions (via income_verification_submission_id)
- **Belongs to:** users (reviewer, via reviewer_id)

### Business Logic

**Review Method (Enum):**
- **AUTOMATED** - System made determination without human input
- **MANUAL** - Human reviewer examined documents and made decision

**Review Types:**
- **INITIAL** - First review of income submission
- **ESCALATION** - Escalated to senior reviewer or manager

**Review Workflow:**
1. Income submission marked NEEDS_REVIEW
2. Review created and assigned to reviewer
3. Reviewer examines:
   - Extracted income amounts from documents
   - Employment stability
   - Income consistency
   - Document authenticity (fraud check results)
4. Reviewer makes determination (approve/reject)
5. Sets rejection_reason if rejecting
6. Status → COMPLETED

**calculation_id:**
- May link to external income calculation service
- Could reference calculation results stored elsewhere
- Provides audit trail for how income was calculated

---

## 3. INCOME_VERIFICATION_RESULTS

**Purpose:** Final income verification determination for an applicant submission.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| applicant_submission_id | uuid | NO | **FK → applicant_submissions.id** |
| calculation_id | uuid | YES | Links to external calculation service |
| review_eligibility | varchar(255) | YES | Final eligibility (APPROVED, REJECTED) |
| rejected_reasons | array (varchar) | NO | List of rejection reasons (default: []) |
| type | varchar(255) | YES | Income verification type |
| inserted_at | timestamp | NO | Result timestamp |

### Relationships
- **Belongs to:** applicant_submissions (via applicant_submission_id)

### Business Logic
- **One income_verification_result per applicant_submission**
- Aggregates results from reviews and automated calculations
- `rejected_reasons` array can contain multiple reasons:
  ```
  ["insufficient_income", "employment_gap", "inconsistent_income"]
  ```
- Result propagates to entry.result
- Final determination for property manager dashboard

**Type Values:**
- May indicate income verification method:
  - "automated" - Fully automated calculation
  - "manual" - Human-reviewed calculation
  - "hybrid" - Combination of automated + manual review

---

# Asset Verification Workflow

## Overview

Asset verification confirms applicant has sufficient liquid assets (bank accounts, investment accounts) to cover move-in costs or serve as financial backup. Typically requires 2-6 months of rent in liquid assets.

---

## 4. ASSET_VERIFICATION_SUBMISSIONS

**Purpose:** Initiates asset calculation for submitted bank/investment statements.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| entry_id | uuid | NO | **FK → entries.id** |
| applicant_submission_document_source_id | uuid | YES | **FK → applicant_submission_document_sources.id** |
| review_eligibility | varchar(255) | NO | Eligibility status (APPROVED, REJECTED, NEEDS_REVIEW) |
| rejection_reason | varchar(255) | YES | Why rejected (if applicable) |
| inserted_at | timestamp | NO | Submission timestamp |

### Relationships
- **Belongs to:** entries (via entry_id)
- **Belongs to:** applicant_submission_document_sources (via applicant_submission_document_source_id)
- **Has many:** asset_verification_reviews

### Business Logic

**Review Eligibility Values:**
- **APPROVED** - Sufficient liquid assets verified
- **REJECTED** - Insufficient assets or cannot verify
- **NEEDS_REVIEW** - Requires human judgment

**Rejection Reasons:**
- "insufficient_assets" - Total assets below requirement
- "illiquid_assets" - Only non-liquid assets (real estate, retirement accounts)
- "cannot_verify" - Documents don't clearly show account balances
- "stale_statements" - Documents too old (>30 days)
- "zero_balance" - Account balance at or near zero

**Automated Approval:**
- Total liquid assets ≥ 6 months rent
- Recent statements (<30 days old)
- Clear account balances
- No fraud flags on documents

**Requires Human Review:**
- Assets between 2-6 months rent (edge case)
- Mix of liquid and illiquid assets
- Multiple accounts requiring totaling
- Foreign currency accounts
- Joint accounts (need to verify ownership)

---

## 5. ASSET_VERIFICATION_REVIEWS

**Purpose:** Human review of asset verification when automated system requires assistance.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| asset_verification_submission_id | uuid | NO | **FK → asset_verification_submissions.id** |
| reviewer_id | uuid | NO | **FK → users.id** |
| status | varchar(255) | NO | Review status (PENDING, IN_PROGRESS, COMPLETED) |
| type | varchar(255) | NO | Review type (INITIAL, ESCALATION) (default: INITIAL) |
| review_method | USER-DEFINED (enum) | NO | How reviewed (AUTOMATED, MANUAL) (default: AUTOMATED) |
| calculation_id | uuid | YES | Links to external calculation service |
| rejection_reason | varchar(255) | YES | Reason for rejection |
| assigned_date | timestamp | YES | When assigned to reviewer |
| completed_date | timestamp | YES | When review completed |
| inserted_at | timestamp | NO | Review creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** asset_verification_submissions (via asset_verification_submission_id)
- **Belongs to:** users (reviewer, via reviewer_id)

### Business Logic

Similar to income verification reviews, but focused on asset verification:

**Reviewer Examines:**
- Account types (checking, savings, investment, money market)
- Account balances and available funds
- Statement dates (ensure recent)
- Account ownership (individual vs joint)
- Fraud check results on statements

**Approval Criteria:**
- Sufficient liquid assets for property requirements
- Accounts in applicant's name
- Recent statements validating current balances
- No fraud detected on statements

---

## 6. ASSET_VERIFICATION_RESULTS

**Purpose:** Final asset verification determination for an applicant submission.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| applicant_submission_id | uuid | NO | **FK → applicant_submissions.id** |
| calculation_id | uuid | NO | Links to external calculation service |
| review_eligibility | varchar(255) | YES | Final eligibility (APPROVED, REJECTED) |
| rejected_reasons | array (varchar) | NO | List of rejection reasons (default: []) |
| inserted_at | timestamp | NO | Result timestamp |

### Relationships
- **Belongs to:** applicant_submissions (via applicant_submission_id)

### Business Logic
- **One asset_verification_result per applicant_submission**
- `rejected_reasons` array examples:
  ```
  ["insufficient_assets", "illiquid_assets", "stale_statements"]
  ```
- Result propagates to entry.result
- Used in combination with income verification for full financial picture

---

# Identity Verification Workflow

## Overview

Identity verification uses third-party services (Incode, Persona) to verify applicant identity through government ID scanning, facial recognition, and liveness detection. Prevents identity theft and ensures applicant is who they claim to be.

---

## 7. ID_VERIFICATIONS

**Purpose:** Third-party identity verification sessions and results.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key (auto-generated) |
| first_name | text | NO | Applicant first name (default: '') |
| last_name | text | NO | Applicant last name (default: '') |
| name | text | YES | Full name (default: '') |
| email | text | NO | Applicant email (default: '') |
| status | text | YES | Verification status (default: '') |
| score | text | YES | Verification confidence score (default: '') |
| score_reason | text | YES | Why score given (default: '') |
| property_id | uuid | YES | **FK → properties.id** |
| company_id | uuid | YES | **FK → companies.id** |
| applicant_detail_id | uuid | YES | Links to applicant_details |
| provider | text | NO | Provider name ('incode', 'persona', etc.) (default: 'incode') |
| provider_session_info | jsonb | NO | Session creation data from provider |
| provider_results | jsonb | YES | Full results from provider |
| incode_id | text | YES | **DEPRECATED** Incode session ID |
| incode_token | text | YES | **DEPRECATED** Incode session token |
| incode_url | text | YES | **DEPRECATED** Incode verification URL |
| incode_results | jsonb | YES | **DEPRECATED** Incode results |
| results_provided_at | timestamp | YES | When provider returned results |
| metadata | jsonb | YES | Additional metadata |
| inserted_at | timestamp | NO | Record creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** properties (via property_id)
- **Belongs to:** companies (via company_id)
- **Implicitly belongs to:** applicant_details (via applicant_detail_id)

### Business Logic

**Identity Verification Flow:**

1. **Session Creation:**
   - Applicant starts entry, selects identity verification
   - System calls provider API to create session
   - `provider_session_info` stores session URL, token, expiration
   - Applicant redirected to provider's verification portal

2. **Applicant Verification:**
   - Applicant scans government ID (driver's license, passport)
   - Applicant takes selfie for facial recognition
   - Liveness detection (blink, turn head) prevents spoofing
   - Provider analyzes ID authenticity and face match

3. **Results Webhook:**
   - Provider calls webhook with results
   - Results stored in `provider_results` (JSONB)
   - `status`, `score`, `score_reason` extracted from results
   - `results_provided_at` timestamp set

4. **Determination:**
   - HIGH score → Approved
   - MEDIUM score → May require manual review
   - LOW/FAILED → Rejected

**Provider Support:**
- **Incode** (default) - Facial recognition + ID scanning
- **Persona** - Alternative provider
- `provider` field allows multi-provider support
- Legacy `incode_*` fields for backwards compatibility

**Status Values:**
- "pending" - Session created, awaiting applicant
- "in_progress" - Applicant actively completing verification
- "completed" - Verification finished, awaiting results
- "approved" - Identity verified successfully
- "rejected" - Identity could not be verified
- "expired" - Session timed out

**Score Interpretation:**
- Numeric score (0-100) or qualitative (HIGH/MEDIUM/LOW)
- `score_reason` explains score factors:
  - "id_verification_passed_face_match_passed"
  - "id_expired"
  - "face_match_failed"
  - "liveness_check_failed"
  - "document_not_readable"

**provider_results JSONB Example:**
```json
{
  "id_check": {
    "status": "passed",
    "document_type": "drivers_license",
    "issuing_country": "USA",
    "expiration_date": "2028-05-15"
  },
  "face_match": {
    "status": "passed",
    "confidence": 98.5
  },
  "liveness": {
    "status": "passed",
    "checks_performed": ["blink", "head_turn"]
  },
  "address_verification": {
    "address": "123 Main St, City, ST 12345",
    "matches_id": true
  }
}
```

---

# Rent Verification Workflow

## Overview

Rent verification uses third-party services to check applicant's rental payment history. Confirms applicant has history of paying rent on time and doesn't have prior evictions.

---

## 8. RENT_VERIFICATIONS

**Purpose:** Rental payment history checks via third-party APIs.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| applicant_id | uuid | NO | **FK → applicants.id** |
| property_id | uuid | NO | **FK → properties.id** |
| provider | varchar(100) | NO | Provider name (e.g., 'renttrack', 'experian_rentbureau') |
| external_id | text | NO | Provider's verification ID |
| status | varchar(100) | NO | Verification status (default: 'pending') |
| report_url | text | YES | URL to full report (if available) |
| request_payload | jsonb | YES | Data sent to provider |
| provider_data | jsonb | YES | Results from provider |
| inserted_at | timestamp | NO | Request creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** applicants (via applicant_id)
- **Belongs to:** properties (via property_id)
- **Has many:** rent_verification_events

### Business Logic

**Rent Verification Flow:**

1. **Request Creation:**
   - Property manager requests rent verification for applicant
   - System calls provider API with applicant info
   - `request_payload` stores: name, SSN (last 4), DOB, previous addresses
   - `external_id` assigned by provider

2. **Provider Processing:**
   - Provider searches rental databases
   - Checks payment history, evictions, judgments
   - May take 1-5 days for full report

3. **Results Received:**
   - Provider returns report via API or webhook
   - `provider_data` stores full report
   - `report_url` may provide link to detailed report
   - `status` updated to 'completed'

4. **Review:**
   - Property manager reviews rental history
   - Looks for:
     - Late payments
     - Evictions
     - Outstanding balances
     - Lease violations

**Status Values:**
- "pending" - Request submitted, awaiting provider
- "processing" - Provider searching databases
- "completed" - Report available
- "failed" - Provider could not complete check
- "insufficient_data" - No rental history found

**Provider Examples:**
- **RentTrack** - Rental payment reporting
- **Experian RentBureau** - Rental credit reporting
- **TransUnion ResidentCredit** - Rental history reports

**provider_data JSONB Example:**
```json
{
  "rental_history": [
    {
      "address": "456 Oak St, City, ST",
      "landlord": "ABC Property Management",
      "move_in_date": "2021-01-01",
      "move_out_date": "2023-12-31",
      "monthly_rent": 1500,
      "payment_history": {
        "on_time_payments": 34,
        "late_payments": 2,
        "missed_payments": 0
      }
    }
  ],
  "evictions": [],
  "judgments": [],
  "overall_rating": "good"
}
```

---

## 9. RENT_VERIFICATION_EVENTS

**Purpose:** Event log for rent verification workflow tracking.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| rent_verification_id | uuid | NO | **FK → rent_verifications.id** |
| event_type | text | NO | Event type (status change, webhook received, etc.) |
| event_data | jsonb | YES | Event details (default: {}) |
| inserted_at | timestamp | NO | Event timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** rent_verifications (via rent_verification_id)

### Business Logic

**Event Types:**
- "request_created" - Initial rent verification request
- "provider_request_sent" - API call made to provider
- "status_updated" - Status changed
- "webhook_received" - Provider sent webhook with update
- "report_ready" - Full report available
- "error_occurred" - Error during processing

**Event Data Examples:**

```json
// request_created
{
  "provider": "renttrack",
  "applicant_name": "John Smith",
  "previous_addresses": 2
}

// status_updated
{
  "old_status": "pending",
  "new_status": "processing",
  "updated_by": "system"
}

// webhook_received
{
  "webhook_id": "wh_123456",
  "status": "completed",
  "report_available": true
}

// error_occurred
{
  "error_code": "INSUFFICIENT_DATA",
  "error_message": "No rental history found for applicant",
  "retry_allowed": false
}
```

**Usage:**
- Audit trail for rent verification process
- Debugging failed verifications
- SLA tracking (time from request to completion)
- Webhook delivery confirmation

---

## Workflow Integration: Multi-Verification Entry

### Example: Complete Applicant Screening

A property manager can request multiple verifications for a single entry:

```
Entry Created
  ├─> Fraud Detection (documents submitted)
  │    └─> Result: CLEAN (all documents authentic)
  │
  ├─> Income Verification (from same documents)
  │    └─> Result: APPROVED (income 3.2x rent)
  │
  ├─> Asset Verification (bank statements)
  │    └─> Result: APPROVED (8 months liquid assets)
  │
  ├─> Identity Verification (ID scan + selfie)
  │    └─> Result: APPROVED (high confidence match)
  │
  └─> Rent Verification (previous landlord check)
       └─> Result: GOOD (34/36 on-time payments)

Overall Entry Determination: APPROVED
Property Manager Action: Proceed with lease
```

### Entry Result Aggregation

The entry.result field aggregates all verification results:

**Result Priority (worst case wins):**
1. FRAUD - Any fraud detected → Entry REJECTED
2. REJECTED - Any critical verification failed → Entry REJECTED
3. NEEDS_REVIEW - Any verification requires human review → Entry NEEDS_REVIEW
4. APPROVED - All verifications passed → Entry APPROVED

**Property Configuration:**
- Properties can enable/disable specific verifications
- Properties set income/asset requirements
- Properties choose identity verification provider
- Properties decide if rent verification required

---

## Performance Considerations

### Indexes Recommended

```sql
-- Income Verification
CREATE INDEX idx_income_submissions_entry
  ON income_verification_submissions(entry_id);

CREATE INDEX idx_income_reviews_submission
  ON income_verification_reviews(income_verification_submission_id);

CREATE INDEX idx_income_results_applicant_submission
  ON income_verification_results(applicant_submission_id);

-- Asset Verification
CREATE INDEX idx_asset_submissions_entry
  ON asset_verification_submissions(entry_id);

CREATE INDEX idx_asset_reviews_submission
  ON asset_verification_reviews(asset_verification_submission_id);

CREATE INDEX idx_asset_results_applicant_submission
  ON asset_verification_results(applicant_submission_id);

-- Identity Verification
CREATE INDEX idx_id_verifications_property
  ON id_verifications(property_id);

CREATE INDEX idx_id_verifications_applicant_detail
  ON id_verifications(applicant_detail_id);

CREATE INDEX idx_id_verifications_status
  ON id_verifications(status)
  WHERE status IN ('pending', 'in_progress');

-- Rent Verification
CREATE INDEX idx_rent_verifications_applicant
  ON rent_verifications(applicant_id);

CREATE INDEX idx_rent_verifications_status
  ON rent_verifications(status)
  WHERE status != 'completed';

CREATE INDEX idx_rent_verification_events_verification
  ON rent_verification_events(rent_verification_id);
```

### JSONB Optimization

```sql
-- Identity Verification provider results
CREATE INDEX idx_id_verifications_provider_results_gin
  ON id_verifications USING gin(provider_results);

-- Rent Verification provider data
CREATE INDEX idx_rent_verifications_provider_data_gin
  ON rent_verifications USING gin(provider_data);
```

---

## Security & Compliance

### PII Protection

These verification workflows handle highly sensitive PII:
- **SSN** (last 4 digits in rent verification)
- **Date of birth**
- **Previous addresses**
- **Government ID images** (identity verification)
- **Financial account balances**
- **Facial biometric data**

**Security Measures:**
- All PII encrypted at rest
- JSONB fields contain encrypted sensitive data
- Access controlled via role-based permissions
- Audit trail for all PII access
- Data retention policies (auto-delete after X days)
- GDPR/CCPA compliance for data deletion requests

### Third-Party Provider Security

- API keys stored in secure credential management
- Webhook signatures validated
- TLS 1.2+ for all provider communication
- Provider data isolated per-property
- Regular security audits of provider integrations

---

## Summary

**9 Verification Tables Documented:**
- Income Verification: 3 tables (submission → review → result)
- Asset Verification: 3 tables (submission → review → result)
- Identity Verification: 1 table (third-party integration)
- Rent Verification: 2 tables (verification + event log)

**Common Patterns:**
- Submissions trigger automated analysis
- Reviews provide human oversight when needed
- Results store final determinations
- Integration with third-party services for identity/rent checks
- Heavy use of JSONB for flexible provider data storage

**Next Documentation:**
- Review & Queue Management System
- Features & Configuration
- Integration Layer (Yardi, Webhooks)

**See:** REVIEW_QUEUE_SYSTEM.md (to be created next)
