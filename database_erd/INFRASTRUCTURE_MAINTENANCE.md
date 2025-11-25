# Infrastructure & Maintenance

**Generated:** 2025-11-25
**Database:** fraud_postgresql (Production)
**Tables Documented:** 3 tables

---

## Overview

This document covers infrastructure and maintenance tables used for database migrations, activation tracking, and document reprocessing. These tables support operational needs and system maintenance rather than core business workflows.

**Categories:**
1. **Database Migrations (1 table):** schema_migrations
2. **Activation Tracking (1 table):** activation_history
3. **Document Reprocessing (1 table):** voi_reprocessing

---

## Table of Contents

1. [Database Migrations](#1-database-migrations-1-table)
   - schema_migrations
2. [Activation Tracking](#2-activation-tracking-1-table)
   - activation_history
3. [Document Reprocessing](#3-document-reprocessing-1-table)
   - voi_reprocessing

---

## 1. Database Migrations (1 Table)

### schema_migrations

**Purpose:** Ecto migrations tracking table - records which database migrations have been applied

**Primary Key:** version (bigint)

**Framework:** Elixir Ecto ORM migration system

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| version | bigint | NO | - | Migration version number (timestamp format: YYYYMMDDHHMMSS) |
| inserted_at | timestamp | YES | - | When migration was applied |

#### Business Logic

**Purpose:**
- Track applied database migrations
- Prevent duplicate migration execution
- Enable rollback to previous schema versions
- Audit trail of schema changes

**Migration Version Format:**
```
20241115103045  →  2024-11-15 10:30:45
YYYYMMDDHHMMSS  →  Year-Month-Day Hour:Minute:Second
```

**Migration Workflow:**

1. **Developer creates migration:**
   ```bash
   mix ecto.gen.migration add_identity_verification_enabled_to_properties
   # Creates: priv/repo/migrations/20241115103045_add_identity_verification_enabled_to_properties.exs
   ```

2. **Migration file contains:**
   ```elixir
   defmodule Snappt.Repo.Migrations.AddIdentityVerificationEnabledToProperties do
     use Ecto.Migration

     def change do
       alter table(:properties) do
         add :identity_verification_enabled, :boolean, default: false
       end
     end
   end
   ```

3. **Migration executed:**
   ```bash
   mix ecto.migrate
   ```

4. **Record inserted:**
   ```sql
   INSERT INTO schema_migrations (version, inserted_at)
   VALUES (20241115103045, NOW());
   ```

5. **Ecto checks before each migration:**
   ```sql
   SELECT version FROM schema_migrations WHERE version = 20241115103045;
   -- If exists: Skip migration (already applied)
   -- If not exists: Run migration
   ```

**Common Migration Types:**
- **Add column:** Add new field to existing table
- **Create table:** Add new table
- **Add index:** Performance optimization
- **Add constraint:** Data integrity (FK, unique, check)
- **Alter column:** Change data type or nullability
- **Drop column/table:** Remove deprecated structures

#### Query Examples

```sql
-- List all applied migrations
SELECT
    version,
    inserted_at,
    TO_TIMESTAMP(version::text, 'YYYYMMDDHH24MISS') as migration_timestamp
FROM schema_migrations
ORDER BY version DESC;

-- Recent migrations (last 30 days)
SELECT
    version,
    inserted_at
FROM schema_migrations
WHERE inserted_at > NOW() - interval '30 days'
ORDER BY version DESC;

-- Check if specific migration applied
SELECT EXISTS (
    SELECT 1 FROM schema_migrations
    WHERE version = 20241115103045
);

-- Migration history timeline
SELECT
    DATE(inserted_at) as migration_date,
    COUNT(*) as migrations_applied
FROM schema_migrations
WHERE inserted_at IS NOT NULL
GROUP BY DATE(inserted_at)
ORDER BY migration_date DESC;
```

#### Migration Management

**Rollback:**
```bash
# Rollback last migration
mix ecto.rollback

# Deletes record from schema_migrations
# Executes down() or reverses change() in migration file
```

**Check migration status:**
```bash
mix ecto.migrations

# Output:
# up   20241015120000  create_companies
# up   20241015120100  create_properties
# up   20241115103045  add_identity_verification_enabled_to_properties
# down 20241116090000  add_frequent_flyer_tables
```

**Best Practices:**
- Never modify applied migrations (version exists in schema_migrations)
- Always test migrations on staging first
- Use reversible migrations when possible
- Document breaking changes in migration comments

---

## 2. Activation Tracking (1 Table)

### activation_history

**Purpose:** Audit trail for entity activation/deactivation events across the platform

**Primary Key:** id (uuid, auto-generated)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| entity_type | varchar(255) | NO | - | Type of entity (property, company, feature, user) |
| status_change | varchar(255) | NO | - | Status transition (activated, deactivated, suspended) |
| changed_at | timestamp | NO | NOW() | When status changed |
| entity_id | uuid | NO | - | ID of the entity that changed status |

#### Business Logic

**Purpose:**
- Track when entities are activated/deactivated
- Audit trail for compliance
- Debug activation issues
- Analytics on platform usage patterns

**Entity Types:**

1. **property:**
   - Activated: Property onboarded and accepting entries
   - Deactivated: Property offboarded or temporarily suspended
   - Suspended: Temporary suspension (payment issue, contract renewal)

2. **company:**
   - Activated: New customer onboarded
   - Deactivated: Customer churned
   - Suspended: Payment delinquent

3. **feature:**
   - Activated: Feature enabled for property/company
   - Deactivated: Feature disabled

4. **user:**
   - Activated: User account enabled
   - Deactivated: User left company
   - Suspended: Security suspension

5. **integration:**
   - Activated: Yardi/RealPage integration enabled
   - Deactivated: Integration removed

**Status Changes:**
- **activated:** Entity turned on
- **deactivated:** Entity turned off (permanent)
- **suspended:** Entity temporarily disabled
- **reactivated:** Entity turned back on after suspension

**Use Cases:**

**Property Lifecycle Tracking:**
```sql
-- Property activation history
SELECT
    entity_id as property_id,
    status_change,
    changed_at
FROM activation_history
WHERE entity_type = 'property'
    AND entity_id = 'property-uuid-here'
ORDER BY changed_at DESC;
```

**Churn Analysis:**
```sql
-- Companies that churned this month
SELECT
    entity_id as company_id,
    changed_at as churned_at
FROM activation_history
WHERE entity_type = 'company'
    AND status_change = 'deactivated'
    AND changed_at >= DATE_TRUNC('month', NOW())
ORDER BY changed_at DESC;
```

**Feature Adoption:**
```sql
-- Track feature activation over time
SELECT
    DATE_TRUNC('month', changed_at) as month,
    COUNT(*) as activations
FROM activation_history
WHERE entity_type = 'feature'
    AND status_change = 'activated'
GROUP BY DATE_TRUNC('month', changed_at)
ORDER BY month DESC;
```

#### Query Examples

```sql
-- Recent activation events
SELECT
    entity_type,
    entity_id,
    status_change,
    changed_at
FROM activation_history
WHERE changed_at > NOW() - interval '7 days'
ORDER BY changed_at DESC;

-- Entity status history
SELECT
    status_change,
    changed_at,
    changed_at - LAG(changed_at) OVER (ORDER BY changed_at) as time_in_status
FROM activation_history
WHERE entity_type = 'property'
    AND entity_id = 'uuid-here'
ORDER BY changed_at DESC;

-- Activation patterns by entity type
SELECT
    entity_type,
    status_change,
    COUNT(*) as event_count,
    MAX(changed_at) as most_recent
FROM activation_history
WHERE changed_at > NOW() - interval '30 days'
GROUP BY entity_type, status_change
ORDER BY entity_type, status_change;

-- Find suspended entities
SELECT DISTINCT
    entity_type,
    entity_id,
    changed_at as suspended_at
FROM activation_history ah1
WHERE status_change = 'suspended'
    AND NOT EXISTS (
        SELECT 1 FROM activation_history ah2
        WHERE ah2.entity_id = ah1.entity_id
            AND ah2.entity_type = ah1.entity_type
            AND ah2.changed_at > ah1.changed_at
            AND ah2.status_change IN ('activated', 'reactivated')
    )
ORDER BY changed_at DESC;
```

#### Integration Points

**With properties table:**
```sql
-- Properties with activation history
SELECT
    p.name,
    p.status as current_status,
    ah.status_change as last_change,
    ah.changed_at as last_changed_at
FROM properties p
LEFT JOIN LATERAL (
    SELECT status_change, changed_at
    FROM activation_history
    WHERE entity_type = 'property'
        AND entity_id = p.id
    ORDER BY changed_at DESC
    LIMIT 1
) ah ON true
WHERE p.status != 'active';
```

**With companies table:**
```sql
-- Company lifecycle duration
SELECT
    c.name,
    MIN(ah.changed_at) FILTER (WHERE ah.status_change = 'activated') as activated_at,
    MAX(ah.changed_at) FILTER (WHERE ah.status_change = 'deactivated') as deactivated_at,
    MAX(ah.changed_at) FILTER (WHERE ah.status_change = 'deactivated')
        - MIN(ah.changed_at) FILTER (WHERE ah.status_change = 'activated') as lifetime
FROM companies c
LEFT JOIN activation_history ah
    ON ah.entity_type = 'company'
    AND ah.entity_id = c.id
GROUP BY c.id, c.name
HAVING MAX(ah.changed_at) FILTER (WHERE ah.status_change = 'deactivated') IS NOT NULL;
```

---

## 3. Document Reprocessing (1 Table)

### voi_reprocessing

**Purpose:** Queue for reprocessing Verification of Income (VOI) documents with corrected data or improved extraction algorithms

**Primary Key:** id (bigint, auto-incrementing)

**VOI:** Verification of Income - income/paystub analysis

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| file | text | NO | - | S3/storage file URL |
| proof_id | uuid | NO | - | Proof/document ID (implicit FK → proof.id) |
| company_name | varchar(255) | NO | '' | Employer name |
| applicant_name | varchar(255) | NO | - | Applicant name |
| start_date | timestamp | YES | - | Income period start |
| end_date | timestamp | YES | - | Income period end |
| income_source | varchar(255) | YES | - | Income source type (W2, 1099, self-employed) |
| gross_income | numeric | NO | - | Gross income amount |
| processing_status | text | NO | '0' | Processing state (0=queued, 1=processing, 2=completed, 3=error) |
| processed_at | timestamp | YES | - | Processing completion timestamp |
| error_message | varchar(255) | YES | - | Error details if processing failed |

#### Business Logic

**Purpose:**
- Reprocess income documents with improved OCR
- Correct extraction errors from initial processing
- Apply updated income calculation logic
- Bulk reprocessing after algorithm improvements

**Reprocessing Triggers:**

1. **OCR Improvements:**
   - New OCR model deployed
   - Better text extraction accuracy
   - Queue all documents processed before deployment date

2. **Calculation Logic Updates:**
   - Income calculation formula changed
   - Variable income handling improved
   - Reprocess affected documents

3. **Manual Corrections:**
   - Reviewer identifies extraction error
   - Support team corrects applicant data
   - Queue document for reprocessing with corrected data

4. **Bulk Fixes:**
   - Bug fix in income extraction
   - Reprocess all documents affected by bug

**Processing Status Values:**
- **'0':** Queued (waiting to be processed)
- **'1':** Processing (currently being processed)
- **'2':** Completed (successfully reprocessed)
- **3':** Error (reprocessing failed)

**Reprocessing Workflow:**

1. **Queue Creation:**
   ```sql
   INSERT INTO voi_reprocessing (
       file, proof_id, company_name, applicant_name,
       start_date, end_date, income_source, gross_income,
       processing_status
   )
   SELECT
       p.file,
       p.id,
       p.extracted_meta->>'employer' as company_name,
       a.full_name,
       (p.extracted_meta->>'pay_period_start')::timestamp,
       (p.extracted_meta->>'pay_period_end')::timestamp,
       'W2',
       (p.extracted_meta->>'gross_pay')::numeric,
       '0'  -- Queued
   FROM proof p
   JOIN entries e ON p.entry_id = e.id
   JOIN applicants a ON e.id = a.entry_id
   WHERE p.type = 'paystub'
       AND p.inserted_at < '2024-11-01'  -- Before OCR v2 deployment
       AND p.result = 'CLEAN';
   ```

2. **Background Job Processes Queue:**
   ```sql
   -- Pick next queued item
   UPDATE voi_reprocessing
   SET processing_status = '1', processed_at = NOW()
   WHERE id = (
       SELECT id FROM voi_reprocessing
       WHERE processing_status = '0'
       ORDER BY id ASC
       LIMIT 1
       FOR UPDATE SKIP LOCKED
   )
   RETURNING *;
   ```

3. **Reprocess Document:**
   - Fetch file from S3
   - Run improved OCR
   - Extract income data
   - Calculate updated income verification result
   - Update proof.extracted_meta
   - Update income_verification_results

4. **Mark Complete:**
   ```sql
   -- Success
   UPDATE voi_reprocessing
   SET processing_status = '2', processed_at = NOW()
   WHERE id = 123;

   -- Error
   UPDATE voi_reprocessing
   SET processing_status = '3', error_message = 'OCR failed: timeout'
   WHERE id = 123;
   ```

#### Query Examples

```sql
-- Reprocessing queue status
SELECT
    processing_status,
    COUNT(*) as count
FROM voi_reprocessing
GROUP BY processing_status
ORDER BY processing_status;

-- Failed reprocessing items
SELECT
    id,
    proof_id,
    applicant_name,
    company_name,
    error_message,
    processed_at
FROM voi_reprocessing
WHERE processing_status = '3'
ORDER BY processed_at DESC;

-- Processing performance
SELECT
    DATE(processed_at) as process_date,
    COUNT(*) as total_processed,
    COUNT(*) FILTER (WHERE processing_status = '2') as successful,
    COUNT(*) FILTER (WHERE processing_status = '3') as failed,
    AVG(EXTRACT(EPOCH FROM (processed_at - start_date))) / 60 as avg_processing_minutes
FROM voi_reprocessing
WHERE processed_at IS NOT NULL
GROUP BY DATE(processed_at)
ORDER BY process_date DESC;

-- Pending reprocessing by company
SELECT
    company_name,
    COUNT(*) as pending_count
FROM voi_reprocessing
WHERE processing_status = '0'
GROUP BY company_name
ORDER BY pending_count DESC;

-- Reprocessing for specific applicant
SELECT
    vr.id,
    vr.file,
    vr.gross_income,
    vr.processing_status,
    vr.processed_at,
    vr.error_message
FROM voi_reprocessing vr
WHERE vr.applicant_name LIKE '%Smith%'
ORDER BY vr.id DESC;
```

#### Retry Logic

```sql
-- Retry failed reprocessing (reset to queued)
UPDATE voi_reprocessing
SET processing_status = '0',
    processed_at = NULL,
    error_message = NULL
WHERE processing_status = '3'
    AND error_message LIKE '%timeout%'  -- Only retry timeouts
    AND processed_at > NOW() - interval '1 day';
```

#### Integration with Core Tables

```sql
-- Compare original vs reprocessed income
SELECT
    vr.proof_id,
    vr.applicant_name,
    p.extracted_meta->>'gross_pay' as original_gross_pay,
    vr.gross_income as reprocessed_gross_income,
    vr.gross_income - (p.extracted_meta->>'gross_pay')::numeric as difference
FROM voi_reprocessing vr
JOIN proof p ON vr.proof_id = p.id
WHERE vr.processing_status = '2'
    AND ABS(vr.gross_income - (p.extracted_meta->>'gross_pay')::numeric) > 100  -- Significant difference
ORDER BY ABS(vr.gross_income - (p.extracted_meta->>'gross_pay')::numeric) DESC;
```

---

## Performance Considerations

### Recommended Indexes

**schema_migrations:**
- Primary key on version (already exists)
- Index on inserted_at for timeline queries

**activation_history:**
- Composite index (entity_type, entity_id, changed_at) for entity history lookups
- Index on changed_at for recent events queries
- Index on status_change for filtering by status type

**voi_reprocessing:**
- Index on processing_status for queue polling
- Index on proof_id for document lookup
- Index on processed_at for performance analytics
- Composite index (processing_status, id) for efficient queue processing

---

## Summary

### Key Features

**Database Migrations:**
- Ecto migration tracking
- Prevents duplicate migrations
- Audit trail of schema changes
- Supports rollback

**Activation Tracking:**
- Entity lifecycle audit trail
- Churn analysis
- Feature adoption tracking
- Compliance and debugging

**Document Reprocessing:**
- Income document reprocessing queue
- Improved OCR application
- Error correction and retry logic
- Bulk reprocessing support

### Use Cases

**Operations:**
- Track database schema evolution
- Debug migration issues
- Monitor entity activation patterns
- Reprocess documents after improvements

**Analytics:**
- Customer churn analysis
- Feature adoption rates
- Entity lifecycle duration
- Reprocessing success rates

**Maintenance:**
- Apply database migrations safely
- Retry failed document processing
- Audit activation/deactivation events
- Track processing performance

---

## Related Documentation

- [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md) - Entities referenced in activation_history
- [FRAUD_DETECTION_WORKFLOW.md](FRAUD_DETECTION_WORKFLOW.md) - Documents reprocessed in voi_reprocessing
- [VERIFICATION_WORKFLOWS.md](VERIFICATION_WORKFLOWS.md) - Income verification context
- [README.md](README.md) - Project overview

---

**Generated:** 2025-11-25
**Database:** fraud_postgresql
**Tables Documented:** 3 (schema_migrations, activation_history, voi_reprocessing)
