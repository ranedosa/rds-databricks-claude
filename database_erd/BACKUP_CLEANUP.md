# Backup & Cleanup Tables

**Generated:** 2025-11-25
**Database:** fraud_postgresql (Production)
**Tables Documented:** 5 tables

---

## Overview

This document covers backup and cleanup tables created during database maintenance operations, data migrations, and cleanup scripts. These tables preserve data before deletion or modification to enable recovery if needed.

**Purpose:** Data safety nets for cleanup operations and migrations

**Categories:**
1. **Submission Backups (3 tables):** applicant_submission_backup, applicant_submission_document_sources_cleanup_backup, applicant_submissions_cleanup_backup
2. **Review Queue Backup (1 table):** review_items_cleanup_backup
3. **Migration Data (1 table):** staging_activation_backfill

---

## Table of Contents

1. [Submission Backups](#1-submission-backups-3-tables)
   - applicant_submission_backup
   - applicant_submission_document_sources_cleanup_backup
   - applicant_submissions_cleanup_backup
2. [Review Queue Backup](#2-review-queue-backup-1-table)
   - review_items_cleanup_backup
3. [Migration Data](#3-migration-data-1-table)
   - staging_activation_backfill

---

## 1. Submission Backups (3 Tables)

### applicant_submission_backup

**Purpose:** Backup of applicant submission relationships before cleanup operation

**Primary Key:** None (backup table)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| submission_id | uuid | YES | - | applicant_submissions.id |
| document_source_id | uuid | YES | - | applicant_submission_document_sources.id |
| folder_id | uuid | YES | - | Related folder ID |
| applicant_id | uuid | YES | - | Related applicant ID |
| source_inserted_at | timestamp | YES | - | Original creation timestamp |
| backup_timestamp | timestamp | YES | NOW() | When backup was created |

#### Business Logic

**Purpose:**
- Preserve submission relationships before orphan cleanup
- Enable recovery if cleanup script errors
- Audit trail of cleanup operations
- Verify cleanup script correctness

**Common Cleanup Scenarios:**

1. **Orphaned Submissions:**
   ```sql
   -- Backup before deleting orphaned submissions
   INSERT INTO applicant_submission_backup (
       submission_id,
       document_source_id,
       folder_id,
       applicant_id,
       source_inserted_at,
       backup_timestamp
   )
   SELECT
       asub.id as submission_id,
       asds.id as document_source_id,
       e.folder_id,
       asub.applicant_id,
       asub.inserted_at,
       NOW()
   FROM applicant_submissions asub
   LEFT JOIN applicant_submission_document_sources asds ON asub.id = asds.applicant_submission_id
   LEFT JOIN applicants a ON asub.applicant_id = a.id
   LEFT JOIN entries e ON a.entry_id = e.id
   WHERE a.id IS NULL  -- Orphaned: applicant no longer exists
       OR e.id IS NULL;  -- Orphaned: entry no longer exists
   ```

2. **Data Quality Cleanup:**
   - Remove duplicate submissions
   - Clean up test data
   - Remove submissions with missing documents

**Recovery Pattern:**
```sql
-- Verify backup exists
SELECT COUNT(*) FROM applicant_submission_backup
WHERE DATE(backup_timestamp) = CURRENT_DATE;

-- Restore if needed (requires manual recreation of relationships)
SELECT
    submission_id,
    document_source_id,
    applicant_id,
    folder_id
FROM applicant_submission_backup
WHERE backup_timestamp > NOW() - interval '7 days'
ORDER BY backup_timestamp DESC;
```

#### Query Examples

```sql
-- Recent backups
SELECT
    DATE(backup_timestamp) as backup_date,
    COUNT(*) as records_backed_up
FROM applicant_submission_backup
GROUP BY DATE(backup_timestamp)
ORDER BY backup_date DESC;

-- Backup details for specific submission
SELECT *
FROM applicant_submission_backup
WHERE submission_id = 'uuid-here'
ORDER BY backup_timestamp DESC;
```

---

### applicant_submission_document_sources_cleanup_backup

**Purpose:** Backup of document sources deleted during cleanup operations

**Primary Key:** Composite (run_id, id)

**run_id:** Unique identifier for each cleanup operation run

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| run_id | uuid | NO | - | Cleanup run identifier (groups related deletions) |
| id | uuid | NO | - | Original document source ID |
| applicant_submission_id | uuid | NO | - | Related applicant submission |
| source_type | varchar(255) | NO | - | Document source type (manual_upload, yardi, email, api) |
| inserted_at | timestamp | NO | - | Original creation timestamp |
| updated_at | timestamp | NO | - | Original update timestamp |

#### Business Logic

**Purpose:**
- Backup document sources before deletion
- Track cleanup operations via run_id
- Enable bulk restore if needed
- Audit deleted records

**Cleanup Workflow:**

1. **Generate run_id:**
   ```sql
   SET @run_id = gen_random_uuid();
   ```

2. **Backup before delete:**
   ```sql
   INSERT INTO applicant_submission_document_sources_cleanup_backup (
       run_id,
       id,
       applicant_submission_id,
       source_type,
       inserted_at,
       updated_at
   )
   SELECT
       @run_id,
       asds.id,
       asds.applicant_submission_id,
       asds.source_type,
       asds.inserted_at,
       asds.updated_at
   FROM applicant_submission_document_sources asds
   LEFT JOIN applicant_submissions asub ON asds.applicant_submission_id = asub.id
   WHERE asub.id IS NULL;  -- Orphaned document sources
   ```

3. **Perform deletion:**
   ```sql
   DELETE FROM applicant_submission_document_sources
   WHERE id IN (
       SELECT id FROM applicant_submission_document_sources_cleanup_backup
       WHERE run_id = @run_id
   );
   ```

4. **Verify:**
   ```sql
   SELECT COUNT(*) FROM applicant_submission_document_sources_cleanup_backup
   WHERE run_id = @run_id;
   ```

**Recovery by run_id:**
```sql
-- Find cleanup runs
SELECT
    run_id,
    COUNT(*) as records_deleted,
    MIN(inserted_at) as oldest_record,
    MAX(inserted_at) as newest_record
FROM applicant_submission_document_sources_cleanup_backup
GROUP BY run_id
ORDER BY MIN(inserted_at) DESC;

-- Restore specific run (manual process)
SELECT *
FROM applicant_submission_document_sources_cleanup_backup
WHERE run_id = 'run-uuid-here';
```

#### Query Examples

```sql
-- Cleanup operations summary
SELECT
    run_id,
    source_type,
    COUNT(*) as deleted_count
FROM applicant_submission_document_sources_cleanup_backup
GROUP BY run_id, source_type
ORDER BY run_id;

-- Most recent cleanup
SELECT
    run_id,
    COUNT(*) as records,
    MIN(inserted_at) as oldest_deleted
FROM applicant_submission_document_sources_cleanup_backup
GROUP BY run_id
ORDER BY oldest_deleted DESC
LIMIT 1;
```

---

### applicant_submissions_cleanup_backup

**Purpose:** Backup of applicant submissions deleted during cleanup operations

**Primary Key:** Composite (run_id, id)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| run_id | uuid | NO | - | Cleanup run identifier |
| id | uuid | NO | - | Original submission ID |
| applicant_id | uuid | NO | - | Related applicant |
| submitted_time | timestamp | NO | - | When submission occurred |
| inserted_at | timestamp | NO | - | Record creation timestamp |
| updated_at | timestamp | NO | - | Record update timestamp |
| identity_id | uuid | YES | - | Identity verification session |
| should_notify_applicant | boolean | NO | - | Notification flag |

#### Business Logic

**Purpose:**
- Backup submissions before cleanup
- Preserve full submission records
- Track cleanup operations
- Enable recovery

**Common Cleanup Reasons:**

1. **Orphaned Submissions:**
   - Submissions with deleted applicants
   - Submissions with no document sources

2. **Duplicate Submissions:**
   - Same applicant submitted multiple times
   - System error created duplicates

3. **Test Data:**
   - Development/staging test submissions in production
   - Load testing data

**Cleanup Pattern:**

```sql
-- Backup orphaned submissions
INSERT INTO applicant_submissions_cleanup_backup (
    run_id,
    id,
    applicant_id,
    submitted_time,
    inserted_at,
    updated_at,
    identity_id,
    should_notify_applicant
)
SELECT
    gen_random_uuid(),  -- Same run_id for all in this batch
    asub.id,
    asub.applicant_id,
    asub.submitted_time,
    asub.inserted_at,
    asub.updated_at,
    asub.identity_id,
    asub.should_notify_applicant
FROM applicant_submissions asub
LEFT JOIN applicants a ON asub.applicant_id = a.id
WHERE a.id IS NULL;  -- Applicant deleted

-- Delete after backup
DELETE FROM applicant_submissions
WHERE id IN (
    SELECT id FROM applicant_submissions_cleanup_backup
    WHERE run_id IN (
        SELECT run_id FROM applicant_submissions_cleanup_backup
        GROUP BY run_id
        HAVING MAX(inserted_at) > NOW() - interval '5 minutes'  -- Recent backups only
    )
);
```

#### Query Examples

```sql
-- Cleanup summary by run
SELECT
    run_id,
    COUNT(*) as submissions_deleted,
    MIN(submitted_time) as earliest_submission,
    MAX(submitted_time) as latest_submission
FROM applicant_submissions_cleanup_backup
GROUP BY run_id
ORDER BY MIN(submitted_time) DESC;

-- Find submissions for specific applicant
SELECT
    run_id,
    id,
    submitted_time,
    identity_id
FROM applicant_submissions_cleanup_backup
WHERE applicant_id = 'uuid-here'
ORDER BY submitted_time DESC;
```

---

## 2. Review Queue Backup (1 Table)

### review_items_cleanup_backup

**Purpose:** Backup of review queue items deleted during cleanup operations

**Primary Key:** Composite (run_id, entity_id, workflow)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| run_id | uuid | NO | - | Cleanup run identifier |
| state | varchar(255) | NO | - | Review item state (scheduled, assigned, completed) |
| workflow | varchar(255) | NO | - | Workflow type (entry_review, fraud_review, income_review) |
| entity_id | uuid | NO | - | Entity being reviewed (polymorphic) |
| assignable_at | timestamp | YES | - | When item became assignable |
| assigned_at | timestamp | YES | - | When item was assigned |
| completed_at | timestamp | YES | - | When review completed |
| reviewer_queue_item_id | bigint | YES | - | Related reviewer queue item |

#### Business Logic

**Purpose:**
- Backup review items before deletion
- Clean up completed/old review items
- Preserve queue state history
- Enable recovery of accidentally deleted items

**Cleanup Scenarios:**

1. **Completed Item Archival:**
   ```sql
   -- Backup completed review items older than 90 days
   INSERT INTO review_items_cleanup_backup (
       run_id,
       state,
       workflow,
       entity_id,
       assignable_at,
       assigned_at,
       completed_at,
       reviewer_queue_item_id
   )
   SELECT
       gen_random_uuid(),
       state,
       workflow,
       entity_id,
       assignable_at,
       assigned_at,
       completed_at,
       reviewer_queue_item_id
   FROM review_items
   WHERE state = 'completed'
       AND completed_at < NOW() - interval '90 days';
   ```

2. **Orphaned Item Cleanup:**
   - Review items for deleted entries
   - Review items in invalid states

3. **Performance Optimization:**
   - Archive old data to keep review_items table lean
   - Improve query performance

**Recovery:**
```sql
-- Find recent cleanup runs
SELECT
    run_id,
    workflow,
    state,
    COUNT(*) as items_deleted
FROM review_items_cleanup_backup
GROUP BY run_id, workflow, state
ORDER BY MIN(completed_at) DESC;

-- Restore specific items (requires manual recreation)
SELECT *
FROM review_items_cleanup_backup
WHERE run_id = 'run-uuid-here'
    AND workflow = 'fraud_review';
```

#### Query Examples

```sql
-- Cleanup operations summary
SELECT
    DATE(completed_at) as cleanup_date,
    workflow,
    COUNT(*) as items_cleaned
FROM review_items_cleanup_backup
WHERE completed_at IS NOT NULL
GROUP BY DATE(completed_at), workflow
ORDER BY cleanup_date DESC;

-- Review time analysis from backups
SELECT
    workflow,
    AVG(EXTRACT(EPOCH FROM (completed_at - assigned_at))) / 3600 as avg_review_hours
FROM review_items_cleanup_backup
WHERE completed_at IS NOT NULL
    AND assigned_at IS NOT NULL
GROUP BY workflow;

-- Find backed up items for specific entity
SELECT *
FROM review_items_cleanup_backup
WHERE entity_id = 'uuid-here'
ORDER BY assignable_at DESC;
```

---

## 3. Migration Data (1 Table)

### staging_activation_backfill

**Purpose:** Staging table for backfilling activation_history data during migration

**Primary Key:** id (uuid)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | - | Primary key |
| entity_type | text | YES | - | Type of entity (property, company, feature, user) |
| status_change | text | YES | - | Status transition (activated, deactivated) |
| changed_at | timestamp | YES | - | When status changed |
| entity_id | uuid | YES | - | Entity identifier |

#### Business Logic

**Purpose:**
- Stage activation history data before migration
- Validate data before inserting into activation_history
- Batch process large migrations
- Preserve data if migration fails

**Migration Workflow:**

1. **Extract activation events from various sources:**
   ```sql
   -- Stage property activations from property status history
   INSERT INTO staging_activation_backfill (
       id,
       entity_type,
       status_change,
       changed_at,
       entity_id
   )
   SELECT
       gen_random_uuid(),
       'property',
       CASE
           WHEN status = 'active' THEN 'activated'
           WHEN status = 'inactive' THEN 'deactivated'
           ELSE status
       END,
       updated_at,
       id
   FROM properties
   WHERE updated_at IS NOT NULL;
   ```

2. **Validate staged data:**
   ```sql
   -- Check for duplicates
   SELECT
       entity_id,
       entity_type,
       changed_at,
       COUNT(*)
   FROM staging_activation_backfill
   GROUP BY entity_id, entity_type, changed_at
   HAVING COUNT(*) > 1;

   -- Check for invalid entity_types
   SELECT DISTINCT entity_type
   FROM staging_activation_backfill
   WHERE entity_type NOT IN ('property', 'company', 'feature', 'user', 'integration');
   ```

3. **Migrate to production table:**
   ```sql
   INSERT INTO activation_history (
       id,
       entity_type,
       status_change,
       changed_at,
       entity_id
   )
   SELECT
       id,
       entity_type,
       status_change,
       changed_at,
       entity_id
   FROM staging_activation_backfill
   WHERE id NOT IN (SELECT id FROM activation_history)  -- Avoid duplicates
   ORDER BY changed_at ASC;
   ```

4. **Verify migration:**
   ```sql
   -- Compare counts
   SELECT
       COUNT(*) as staging_count
   FROM staging_activation_backfill;

   SELECT
       COUNT(*) as production_count
   FROM activation_history;

   -- Check for unmigrated records
   SELECT *
   FROM staging_activation_backfill
   WHERE id NOT IN (SELECT id FROM activation_history);
   ```

5. **Cleanup after successful migration:**
   ```sql
   TRUNCATE staging_activation_backfill;
   ```

**Data Sources for Backfill:**
- Property status changes from properties.updated_at
- Company onboarding from companies.inserted_at
- Feature activation from property_features.inserted_at
- User creation from users.inserted_at
- Integration activation from yardi_integrations, etc.

#### Query Examples

```sql
-- Staging summary
SELECT
    entity_type,
    status_change,
    COUNT(*) as staged_count
FROM staging_activation_backfill
GROUP BY entity_type, status_change
ORDER BY entity_type, status_change;

-- Timeline of staged activations
SELECT
    DATE(changed_at) as activation_date,
    entity_type,
    COUNT(*) as activations
FROM staging_activation_backfill
WHERE status_change = 'activated'
GROUP BY DATE(changed_at), entity_type
ORDER BY activation_date DESC;

-- Unmigrated records
SELECT *
FROM staging_activation_backfill
WHERE id NOT IN (SELECT id FROM activation_history)
ORDER BY changed_at ASC;
```

---

## Performance Considerations

### Recommended Indexes

**Backup tables generally don't need indexes** as they are write-once, rarely queried. However, for recovery scenarios:

**applicant_submission_backup:**
- Index on submission_id (recovery lookup)
- Index on backup_timestamp (time-based queries)

**applicant_submission_document_sources_cleanup_backup:**
- Index on run_id (recovery by cleanup run)
- Composite index (run_id, id) for efficient lookups

**applicant_submissions_cleanup_backup:**
- Index on run_id (recovery by cleanup run)
- Index on applicant_id (find submissions for applicant)

**review_items_cleanup_backup:**
- Index on run_id (recovery by cleanup run)
- Index on entity_id (find reviews for entity)

**staging_activation_backfill:**
- Index on entity_id (validation queries)
- Index on changed_at (chronological processing)

---

## Maintenance Recommendations

### Backup Table Lifecycle

**Short-term backups (7-30 days):**
- Keep recent cleanup backups for immediate recovery
- Monitor for accidental deletions
- Verify cleanup scripts worked correctly

**Long-term archival:**
- Export backups to S3/cold storage after 30 days
- Truncate backup tables after archival
- Maintain metadata about archived backups

**Cleanup:**
```sql
-- Archive and truncate old backups (quarterly)
-- Export to S3 first, then:
DELETE FROM applicant_submission_backup
WHERE backup_timestamp < NOW() - interval '90 days';

DELETE FROM applicant_submission_document_sources_cleanup_backup
WHERE run_id IN (
    SELECT DISTINCT run_id
    FROM applicant_submission_document_sources_cleanup_backup
    GROUP BY run_id
    HAVING MIN(inserted_at) < NOW() - interval '90 days'
);

-- Similar for other backup tables
```

### Monitoring

**Monitor backup table sizes:**
```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE tablename LIKE '%backup%'
    OR tablename LIKE '%cleanup%'
    OR tablename LIKE '%staging%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Summary

### Key Features

**Data Protection:**
- Backup before cleanup operations
- Enable recovery if errors occur
- Track cleanup operations via run_id
- Audit deleted records

**Migration Support:**
- Stage data before migrations
- Validate before production insert
- Rollback capability
- Batch processing support

### Use Cases

**Recovery:**
- Restore accidentally deleted records
- Rollback cleanup operations
- Verify cleanup correctness

**Auditing:**
- Track what was deleted and when
- Analyze cleanup patterns
- Compliance and forensics

**Migration:**
- Safe data transformation
- Validation before commit
- Performance optimization through staging

---

## Related Documentation

- [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md) - Tables being backed up
- [REVIEW_QUEUE_SYSTEM.md](REVIEW_QUEUE_SYSTEM.md) - review_items source
- [INFRASTRUCTURE_MAINTENANCE.md](INFRASTRUCTURE_MAINTENANCE.md) - activation_history destination
- [README.md](README.md) - Project overview

---

**Generated:** 2025-11-25
**Database:** fraud_postgresql
**Tables Documented:** 5 (applicant_submission_backup, applicant_submission_document_sources_cleanup_backup, applicant_submissions_cleanup_backup, review_items_cleanup_backup, staging_activation_backfill)
