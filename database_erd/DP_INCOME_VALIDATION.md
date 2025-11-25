# Income Validation Database (dp_income_validation)

**Generated:** 2025-11-25
**Database:** dp_income_validation (Microservice)
**Schemas Documented:** iv (Income Verification), icfr (Fraud Prevention)
**Tables Documented:** 7 tables (5 business + 2 fraud prevention)

---

## Overview

This database is part of the income validation microservice that calculates and validates applicant income from uploaded documents (paystubs, bank statements, tax returns). It provides income calculations in daily, monthly, and yearly formats and tracks document-level processing status.

**Purpose:** Standalone income calculation service with cross-database integration to fraud_postgresql

**Key Features:**
- Income calculation aggregation (gross & net)
- Document-level income tracking
- Status workflow management
- Banned company name filtering (fraud prevention)

---

## Table of Contents

1. [Income Verification Schema (iv)](#income-verification-schema-iv)
   - calculations
   - calculation_documents
   - calculation_status_codes
   - calculation_status_details
   - calculation_document_status_details
2. [Fraud Prevention Schema (icfr)](#fraud-prevention-schema-icfr)
   - banned_company_names
   - banned_company_name_submissions
3. [Cross-Database Relationships](#cross-database-relationships)

---

## Income Verification Schema (iv)

### Entity Relationship Diagram

```
calculations (1) ←→ (N) calculation_documents
     ↓                        ↓
calculation_status_details  calculation_document_status_details
     ↓                        ↓
calculation_status_codes ←───┘
```

---

### calculations

**Purpose:** Aggregated income calculations for an applicant's submission

**Primary Key:** id (bigint, auto-increment)

**Cross-Database Link:** reference_id → fraud_postgresql (likely income_verification_submissions.id or applicant_submissions.id)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| reference_id | uuid | NO | - | **Cross-DB reference** to fraud_postgresql |
| gross_daily_income | numeric | NO | - | Calculated gross daily income |
| gross_monthly_income | numeric | NO | - | Calculated gross monthly income |
| gross_yearly_income | numeric | NO | - | Calculated gross yearly income |
| consecutive_days | integer | NO | - | Number of consecutive employment days |
| total_days | integer | NO | - | Total employment days in period |
| inserted_at | timestamp | NO | CURRENT_TIMESTAMP | Calculation creation timestamp |
| status_code | integer | NO | - | FK → calculation_status_codes.code |
| net_daily_income | numeric | NO | 0 | Calculated net daily income (after taxes) |
| net_monthly_income | numeric | NO | 0 | Calculated net monthly income |
| net_yearly_income | numeric | NO | 0 | Calculated net yearly income |

#### Relationships

**Belongs to:**
- **calculation_status_codes** (status_code) - Current calculation status

**Has many:**
- **calculation_documents** (calculation_id) - Individual documents used in calculation
- **calculation_status_details** (calculation_id) - Status change history

**Cross-Database:**
- **fraud_postgresql** (reference_id) - Links to income verification submission

#### Business Logic

**Income Calculation:**
- Aggregates income across multiple documents (paystubs, bank statements)
- Provides daily, monthly, and yearly projections
- Tracks both gross and net income
- Considers employment consistency (consecutive_days vs total_days)

**Use Cases:**
1. **Regular Employment:** Consistent paystubs → high consecutive_days
2. **Variable Income:** Gig work, seasonal → lower consecutive_days ratio
3. **Multiple Sources:** W2 + 1099 income combined
4. **Gap Analysis:** total_days - consecutive_days = employment gaps

#### Query Examples

```sql
-- Get calculation with all documents
SELECT
    c.id,
    c.reference_id,
    c.gross_monthly_income,
    c.net_monthly_income,
    c.consecutive_days,
    c.total_days,
    scs.name as status,
    COUNT(cd.id) as document_count,
    SUM(cd.gross_income) as total_document_income
FROM iv.calculations c
JOIN iv.calculation_status_codes scs ON c.status_code = scs.code
LEFT JOIN iv.calculation_documents cd ON c.id = cd.calculation_id
WHERE c.reference_id = 'uuid-here'
GROUP BY c.id, c.reference_id, c.gross_monthly_income, c.net_monthly_income,
         c.consecutive_days, c.total_days, scs.name;

-- Income consistency check
SELECT
    c.id,
    c.gross_monthly_income,
    c.consecutive_days,
    c.total_days,
    ROUND(c.consecutive_days::numeric / c.total_days * 100, 2) as consistency_pct,
    CASE
        WHEN c.consecutive_days = c.total_days THEN 'Consistent'
        WHEN c.consecutive_days::numeric / c.total_days >= 0.8 THEN 'Mostly Consistent'
        WHEN c.consecutive_days::numeric / c.total_days >= 0.5 THEN 'Some Gaps'
        ELSE 'Inconsistent'
    END as income_stability
FROM iv.calculations c
WHERE c.status_code = 200;  -- Completed calculations
```

---

### calculation_documents

**Purpose:** Individual document-level income data used in aggregated calculation

**Primary Key:** id (bigint, auto-increment)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| calculation_id | bigint | NO | AUTO | FK → calculations.id |
| document_id | uuid | YES | - | **Cross-DB reference** to fraud_postgresql.proof.id |
| start_date | timestamp | YES | - | Income period start date |
| end_date | timestamp | YES | - | Income period end date |
| gross_income | numeric | YES | - | Gross income from this document |
| applicant_name | text | YES | - | Name on document |
| income_source | text | YES | - | Employer or income source name |
| net_income | numeric | NO | 0 | Net income (after taxes/deductions) |
| income_source_type | text | YES | - | W2, 1099, self-employed, benefits |
| issue_date | timestamp | YES | - | Document issue/pay date |

#### Relationships

**Belongs to:**
- **calculations** (calculation_id) - Parent calculation
- **fraud_postgresql.proof** (document_id) - Source document (cross-DB)

**Has many:**
- **calculation_document_status_details** - Status history for this document

#### Business Logic

**Document Types:**
- **Paystubs:** Weekly/biweekly income periods
- **Bank Statements:** Monthly deposit analysis
- **Tax Returns:** Annual income verification
- **1099 Forms:** Contract/gig income

**Income Source Types:**
- W2: Traditional employment
- 1099: Contract/freelance work
- self-employed: Business income
- benefits: SSI, disability, unemployment
- other: Alimony, child support, investments

#### Query Examples

```sql
-- Documents for a calculation
SELECT
    cd.id,
    cd.document_id,
    cd.income_source,
    cd.income_source_type,
    cd.gross_income,
    cd.net_income,
    cd.start_date,
    cd.end_date,
    (cd.end_date - cd.start_date) as period_days
FROM iv.calculation_documents cd
WHERE cd.calculation_id = 123
ORDER BY cd.start_date ASC;

-- Income by source type
SELECT
    cd.income_source_type,
    COUNT(*) as document_count,
    SUM(cd.gross_income) as total_gross,
    AVG(cd.gross_income) as avg_per_document
FROM iv.calculation_documents cd
WHERE cd.calculation_id = 123
GROUP BY cd.income_source_type;

-- Find gaps in employment
SELECT
    cd1.id,
    cd1.end_date as period_1_end,
    cd2.start_date as period_2_start,
    cd2.start_date - cd1.end_date as gap_days
FROM iv.calculation_documents cd1
JOIN iv.calculation_documents cd2
    ON cd1.calculation_id = cd2.calculation_id
    AND cd2.start_date > cd1.end_date
WHERE cd1.calculation_id = 123
    AND cd2.start_date - cd1.end_date > interval '7 days'
ORDER BY cd1.end_date;
```

---

### calculation_status_codes

**Purpose:** Lookup table for calculation processing status codes

**Primary Key:** code (integer)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| code | integer | NO | - | Primary key (status code) |
| name | text | NO | - | Status name/description |
| inserted_at | timestamp | NO | CURRENT_TIMESTAMP | Record creation timestamp |

#### Common Status Codes (Inferred)

| Code | Name | Description |
|------|------|-------------|
| 100 | Pending | Calculation queued |
| 200 | Completed | Calculation successful |
| 300 | In Progress | Currently processing |
| 400 | Error | Calculation failed |
| 500 | Insufficient Data | Not enough documents |

**Note:** Actual codes may differ - query table for authoritative list

#### Query Examples

```sql
-- List all status codes
SELECT code, name, inserted_at
FROM iv.calculation_status_codes
ORDER BY code;

-- Calculation status distribution
SELECT
    scs.name,
    COUNT(c.id) as calculation_count
FROM iv.calculations c
JOIN iv.calculation_status_codes scs ON c.status_code = scs.code
GROUP BY scs.name
ORDER BY calculation_count DESC;
```

---

### calculation_status_details

**Purpose:** Audit trail of calculation status changes over time

**Primary Key:** id (bigint, auto-increment)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| calculation_id | bigint | NO | AUTO | FK → calculations.id |
| status_code | integer | NO | - | FK → calculation_status_codes.code |
| inserted_at | timestamp | NO | CURRENT_TIMESTAMP | Status change timestamp |

#### Relationships

**Belongs to:**
- **calculations** (calculation_id) - Calculation being tracked
- **calculation_status_codes** (status_code) - Status at this point

#### Business Logic

**Status Workflow:**
```
Pending (100) → In Progress (300) → Completed (200)
                      ↓
                   Error (400)
                      ↓
                 Retry → In Progress
```

**Use Cases:**
- Track calculation processing time
- Debug failed calculations
- Monitor retry attempts
- SLA compliance tracking

#### Query Examples

```sql
-- Status history for calculation
SELECT
    csd.id,
    scs.name as status,
    csd.inserted_at as status_changed_at,
    LAG(csd.inserted_at) OVER (ORDER BY csd.inserted_at) as previous_status_time,
    csd.inserted_at - LAG(csd.inserted_at) OVER (ORDER BY csd.inserted_at) as time_in_status
FROM iv.calculation_status_details csd
JOIN iv.calculation_status_codes scs ON csd.status_code = scs.code
WHERE csd.calculation_id = 123
ORDER BY csd.inserted_at ASC;

-- Average calculation processing time
SELECT
    AVG(EXTRACT(EPOCH FROM (completed.inserted_at - pending.inserted_at))) / 60 as avg_minutes
FROM iv.calculation_status_details pending
JOIN iv.calculation_status_details completed
    ON pending.calculation_id = completed.calculation_id
WHERE pending.status_code = 100  -- Pending
    AND completed.status_code = 200  -- Completed
    AND completed.inserted_at > pending.inserted_at;
```

---

### calculation_document_status_details

**Purpose:** Document-level status tracking (similar to calculation_status_details but per document)

**Primary Key:** id (bigint, auto-increment)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| calculation_document_id | bigint | NO | - | FK → calculation_documents.id |
| status_code | integer | NO | - | FK → calculation_status_codes.code |
| inserted_at | timestamp | NO | CURRENT_TIMESTAMP | Status change timestamp |

#### Relationships

**Belongs to:**
- **calculation_documents** (calculation_document_id) - Document being tracked
- **calculation_status_codes** (status_code) - Status at this point

#### Business Logic

**Per-Document Processing:**
- Track which documents processed successfully
- Identify problematic documents causing calculation failures
- Monitor OCR extraction success rates

#### Query Examples

```sql
-- Document processing status
SELECT
    cd.document_id,
    cd.income_source,
    scs.name as current_status,
    cdsd.inserted_at as status_time
FROM iv.calculation_document_status_details cdsd
JOIN iv.calculation_documents cd ON cdsd.calculation_document_id = cd.id
JOIN iv.calculation_status_codes scs ON cdsd.status_code = scs.code
WHERE cd.calculation_id = 123
ORDER BY cdsd.inserted_at DESC;

-- Failed documents
SELECT
    cd.document_id,
    cd.applicant_name,
    cd.income_source,
    COUNT(*) as failure_count
FROM iv.calculation_document_status_details cdsd
JOIN iv.calculation_documents cd ON cdsd.calculation_document_id = cd.id
WHERE cdsd.status_code = 400  -- Error
GROUP BY cd.document_id, cd.applicant_name, cd.income_source
ORDER BY failure_count DESC;
```

---

## Fraud Prevention Schema (icfr)

### banned_company_names

**Purpose:** List of known fraudulent or problematic company names to flag during income verification

**Primary Key:** (inferred - need to query)

**Note:** Minimal schema information available. Likely contains:
- Company name pattern
- Reason for ban (fraud, test data, etc.)
- Active/inactive flag
- Timestamps

### banned_company_name_submissions

**Purpose:** Track submissions that match banned company names for fraud investigation

**Primary Key:** (inferred - need to query)

**Note:** Likely links to:
- banned_company_names table
- Submission reference (cross-DB to fraud_postgresql)
- Detection timestamp
- Action taken (flagged, rejected, reviewed)

---

## Cross-Database Relationships

### Primary Integration Point: fraud_postgresql

**calculations.reference_id → fraud_postgresql**

Likely links to:
- `income_verification_submissions.id` (most likely)
- `applicant_submissions.id` (alternative)
- `income_verification_reviews.calculation_id` (reference stored in both DBs)

**calculation_documents.document_id → fraud_postgresql.proof.id**

Direct link to source documents:
- Paystubs uploaded to fraud detection platform
- Bank statements
- Tax returns

### Multi-Database Query Pattern

```sql
-- Complete income verification across databases
SELECT
    -- From fraud_postgresql
    ivs.id as submission_id,
    a.full_name as applicant_name,
    e.short_id as entry_id,
    p.name as property_name,

    -- From dp_income_validation
    c.gross_monthly_income,
    c.net_monthly_income,
    c.consecutive_days,
    c.total_days,
    scs.name as calculation_status,

    -- Aggregated document count
    (SELECT COUNT(*) FROM iv.calculation_documents cd WHERE cd.calculation_id = c.id) as document_count

FROM iv.calculations c
JOIN iv.calculation_status_codes scs ON c.status_code = scs.code

-- Cross-database join to fraud_postgresql
-- Assuming reference_id links to income_verification_submissions.id
JOIN fraud_postgresql.income_verification_submissions ivs ON c.reference_id = ivs.id::uuid
JOIN fraud_postgresql.entries e ON ivs.entry_id = e.id
JOIN fraud_postgresql.folders f ON e.folder_id = f.id
JOIN fraud_postgresql.properties p ON f.property_id = p.id
JOIN fraud_postgresql.applicants a ON e.id = (
    SELECT entry_id FROM fraud_postgresql.applicants WHERE id = (
        SELECT applicant_id FROM fraud_postgresql.applicant_submissions
        WHERE id = ivs.applicant_submission_id
        LIMIT 1
    )
    LIMIT 1
)

WHERE c.status_code = 200  -- Completed calculations
ORDER BY c.inserted_at DESC;
```

---

## Performance Considerations

### Recommended Indexes

**calculations:**
- Index on reference_id (cross-DB lookup - CRITICAL)
- Index on status_code (filtering)
- Index on inserted_at (time-based queries)

**calculation_documents:**
- Index on calculation_id (FK lookup)
- Index on document_id (cross-DB lookup)
- Index on income_source_type (grouping)

**calculation_status_details:**
- Composite index (calculation_id, inserted_at) for status history

**calculation_document_status_details:**
- Composite index (calculation_document_id, inserted_at)

---

## Summary

### Key Features

**Income Calculation Service:**
- Standalone microservice for income validation
- Aggregates multiple documents into single calculation
- Provides daily, monthly, yearly projections
- Tracks gross and net income
- Employment consistency analysis

**Status Tracking:**
- Calculation-level and document-level status
- Complete audit trail
- Processing time metrics
- Error tracking and retry support

**Fraud Prevention:**
- Banned company name filtering
- Submission flagging
- Investigation support

### Integration Points

**With fraud_postgresql:**
- calculations.reference_id → income_verification_submissions
- calculation_documents.document_id → proof (documents)
- Enables complete income verification journey tracking

**Microservice Architecture:**
- Independent database for scalability
- Asynchronous processing
- Status-based workflow
- Cross-database queries for reporting

---

## Related Documentation

- [VERIFICATION_WORKFLOWS.md](VERIFICATION_WORKFLOWS.md) - Income verification in fraud_postgresql
- [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md) - Applicants and entries
- [README.md](README.md) - Project overview

---

**Generated:** 2025-11-25
**Database:** dp_income_validation
**Tables Documented:** 5 core tables (calculations, calculation_documents, calculation_status_codes, calculation_status_details, calculation_document_status_details)
**Cross-Database Links:** 2 identified (reference_id, document_id)
