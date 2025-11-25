# Review & Queue System - Workflow Management

**Generated:** 2025-11-25
**Database:** fraud_postgresql (Production)
**Tables Documented:** 6 review and queue management tables

---

## Overview

The Review & Queue System is the central workflow management infrastructure that routes entries, fraud submissions, and verification reviews to human reviewers. This system handles reviewer assignment, workload balancing, escalations, audit trails, and reporting.

**Key Functions:**
- **Queue Management** - Routes review items to available reviewers
- **State Tracking** - Monitors items through scheduled → assigned → completed lifecycle
- **Workload Balancing** - Distributes work across reviewer teams
- **Audit Trail** - Logs all entry state changes
- **Escalation Management** - Handles complex cases requiring senior review
- **Priority Configuration** - Role-based queue sorting

---

## Table Inventory

### Queue Management (2 tables)
- **review_items** - Queue items awaiting review (generic, workflow-agnostic)
- **reviewer_queue** - Reviewer work requests and assignments

### Audit & Reporting (2 tables)
- **entry_log** - Audit trail of entry state changes and reviewer actions
- **entry_report** - Generated reports for completed entries

### Escalation & Configuration (2 tables)
- **entry_review_escalation** - Escalation tracking for complex entries
- **role_entry_status_sort_priority** - Queue sorting priority by user role

---

## Integration with Core Workflows

```
Entries/Reviews → review_items → reviewer_queue → Assigned Reviewer
     ↓                                                      ↓
entry_log (audit trail)                            Complete Review
     ↓                                                      ↓
entry_report (final report)                        Update Entry Status
     ↓
Optional: entry_review_escalation (if complex)
```

**Supported Workflows:**
- Entry reviews (fraud detection)
- Fraud submission reviews
- Income verification reviews
- Asset verification reviews
- Any future review workflows

---

## Detailed Table Documentation

## 1. REVIEW_ITEMS

**Purpose:** Central queue table for all review workflows. Tracks items awaiting assignment and completion.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| state | varchar(255) | NO | Item state (scheduled, assigned, completed, cancelled) (default: 'scheduled') |
| workflow | varchar(255) | NO | Workflow type (entry_review, fraud_review, income_review, asset_review) |
| entity_id | uuid | NO | ID of entity being reviewed (entry_id, fraud_submission_id, etc.) |
| assignable_at | timestamp | YES | When item becomes available for assignment |
| assigned_at | timestamp | YES | When item was assigned to reviewer |
| completed_at | timestamp | YES | When review was completed |
| reviewer_queue_item_id | bigint | YES | **FK → reviewer_queue.id** |

### Relationships
- **Belongs to:** reviewer_queue (via reviewer_queue_item_id)
- **Polymorphic association:** entity_id links to different tables based on workflow

### Business Logic

**State Machine:**
```
scheduled → assigned → completed
     ↓           ↓
cancelled ← cancelled
```

**States:**
- **scheduled** - Item created, waiting to be assignable
- **assigned** - Item assigned to reviewer via reviewer_queue
- **completed** - Review finished
- **cancelled** - Item cancelled (entity deleted, workflow changed)

**Workflow Types:**
- **entry_review** - Entry-level fraud screening review
- **fraud_review** - Fraud submission document review
- **income_review** - Income verification review
- **asset_review** - Asset verification review
- **identity_review** - Identity verification review (if manual)
- **rent_review** - Rent verification review (if manual)

**Polymorphic Entity References:**
- `workflow = 'entry_review'` → `entity_id` references `entries.id`
- `workflow = 'fraud_review'` → `entity_id` references `fraud_submissions.id`
- `workflow = 'income_review'` → `entity_id` references `income_verification_submissions.id`
- `workflow = 'asset_review'` → `entity_id` references `asset_verification_submissions.id`

**Assignment Flow:**
1. Review item created with state = 'scheduled'
2. `assignable_at` set based on business rules (immediate, delayed, SLA-based)
3. When `assignable_at` reached, item eligible for assignment
4. System matches item with available reviewer in `reviewer_queue`
5. `reviewer_queue_item_id` set, state → 'assigned', `assigned_at` set
6. Reviewer completes review
7. State → 'completed', `completed_at` set

**SLA Tracking:**
```sql
-- Time in queue before assignment
assigned_at - assignable_at

-- Time to complete review
completed_at - assigned_at

-- Total review time
completed_at - assignable_at
```

---

## 2. REVIEWER_QUEUE

**Purpose:** Reviewer availability and work assignment management. Tracks when reviewers request work and what they're assigned.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| state | varchar(255) | YES | Queue state (available, assigned, cancelled) (default: 'available') |
| reviewer_id | uuid | YES | **FK → users.id** (reviewer requesting work) |
| requested_at | timestamp | YES | When reviewer requested next item |
| assigned_at | timestamp | YES | When work was assigned |
| cancelled_at | timestamp | YES | When request was cancelled |
| assigned_entry_id | uuid | YES | **FK → entries.id** (entry assigned to reviewer) |

### Relationships
- **Belongs to:** users (reviewer, via reviewer_id)
- **Belongs to:** entries (via assigned_entry_id)
- **Has one:** review_items (via review_items.reviewer_queue_item_id)

### Business Logic

**State Machine:**
```
available → assigned → (deleted after completion)
     ↓
cancelled
```

**States:**
- **available** - Reviewer ready for work, waiting for assignment
- **assigned** - Reviewer has been assigned work
- **cancelled** - Request cancelled (reviewer logged out, went offline)

**Work Request Flow:**
1. Reviewer clicks "Get Next Item" in UI
2. `reviewer_queue` record created with state = 'available'
3. `requested_at` timestamp set
4. System finds highest priority `review_items` where state = 'scheduled' and `assignable_at` <= NOW()
5. Match made: `reviewer_queue.state` → 'assigned'
6. `assigned_at` timestamp set
7. `assigned_entry_id` set (for quick reference)
8. `review_items.reviewer_queue_item_id` set to link back
9. Reviewer completes work
10. `reviewer_queue` record typically deleted or marked complete

**Assignment Algorithm (Conceptual):**
```sql
-- Find next assignable review item
SELECT ri.*
FROM review_items ri
WHERE ri.state = 'scheduled'
  AND ri.assignable_at <= NOW()
  AND ri.workflow IN (
      -- Workflows this reviewer has permissions for
      SELECT workflow FROM reviewer_permissions WHERE reviewer_id = ?
  )
ORDER BY
  -- Priority based on role_entry_status_sort_priority
  priority ASC,
  ri.assignable_at ASC
LIMIT 1;
```

**Workload Balancing:**
- Reviewers pull work (not pushed to them)
- Items distributed on first-come-first-served basis
- Priority sorting ensures critical items reviewed first
- No reviewer gets multiple items until they complete current work

---

## 3. ENTRY_LOG

**Purpose:** Audit trail of entry state changes and reviewer actions. Comprehensive log of all entry workflow events.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| entry_id | uuid | NO | **FK → entries.id** |
| reviewer_id | uuid | NO | **FK → users.id** (user who triggered action) |
| type | varchar(255) | NO | Event type (status_change, result_change, assignment, etc.) |
| entry_result | varchar(255) | YES | Entry result at time of event |
| proofs | array(uuid) | YES | Array of proof IDs involved in event |
| inserted_at | timestamp | NO | Event timestamp |
| workflow | varchar(255) | NO | Workflow type (entry_review, fraud_review, etc.) |

### Relationships
- **Belongs to:** entries (via entry_id)
- **Belongs to:** users (via reviewer_id)
- **References:** proof (via proofs array)

### Business Logic

**Event Types:**
- **entry_created** - Entry initially created
- **status_change** - Entry status changed (pending → in_review → completed)
- **result_change** - Entry result changed (pending → clean/fraud/edited)
- **assignment** - Entry assigned to reviewer
- **unassignment** - Entry unassigned (reviewer unavailable)
- **review_started** - Reviewer opened entry for review
- **review_completed** - Reviewer submitted review
- **escalation** - Entry escalated to senior reviewer
- **auto_reviewed** - Entry automatically reviewed by ML/AI
- **manual_override** - Reviewer overrode automated result

**Audit Trail Examples:**

```
Entry Lifecycle:
1. type='entry_created', reviewer_id=system, entry_result=NULL
2. type='assignment', reviewer_id=reviewer_123, entry_result=NULL
3. type='review_started', reviewer_id=reviewer_123, entry_result=NULL
4. type='result_change', reviewer_id=reviewer_123, entry_result='CLEAN'
5. type='review_completed', reviewer_id=reviewer_123, entry_result='CLEAN'
6. type='status_change', reviewer_id=system, entry_result='CLEAN'
```

**Proofs Array:**
- Contains UUIDs of proof documents involved in the event
- Used for document-level audit trails
- Example: `[uuid1, uuid2, uuid3]` when reviewing multiple documents

**Usage:**
- Compliance and audit requirements
- Debugging entry workflow issues
- Reviewer performance metrics
- SLA tracking
- Forensic analysis of decisions

---

## 4. ENTRY_REPORT

**Purpose:** Final generated reports for completed entries. Snapshot of entry state at completion time.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| entry_status | varchar(255) | NO | Entry status at report generation |
| entry_result | varchar(255) | NO | Final entry result (CLEAN, FRAUD, EDITED, etc.) |
| reviewer_id | uuid | NO | **FK → users.id** (reviewer who completed) |
| entry_id | uuid | NO | **FK → entries.id** |
| proofs | array(uuid) | NO | Array of all proof IDs in entry |
| inserted_at | timestamp | NO | Report generation timestamp |

### Relationships
- **Belongs to:** entries (via entry_id)
- **Belongs to:** users (via reviewer_id)
- **References:** proof (via proofs array)

### Business Logic

**Report Generation:**
- Created when entry reaches terminal state (completed, rejected, cancelled)
- Captures snapshot of entry data for historical record
- Used for property manager dashboard and applicant notifications

**Report Contents:**
- Final entry result and status
- All documents reviewed (proofs array)
- Reviewer who made determination
- Timestamp of completion

**Use Cases:**
1. **Property Manager Dashboard** - Display completed entry results
2. **Applicant Notifications** - Send results to applicant
3. **Historical Record** - Entry state at completion (immutable)
4. **Analytics** - Entry completion metrics
5. **Dispute Resolution** - Reference for contested decisions

**Report Delivery:**
- Report data used to generate PDF/email notifications
- Stored as permanent record even if entry is later modified
- May trigger webhooks to external systems

---

## 5. ENTRY_REVIEW_ESCALATION

**Purpose:** Tracks escalations of entries to senior reviewers or QA teams for complex cases.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| reason | varchar(255) | YES | Escalation reason (complex_case, quality_check, customer_request) |
| notes | text | YES | Additional notes explaining escalation |
| escalated_by_id | uuid | NO | **FK → users.id** (user who escalated) |
| entry_id | uuid | NO | **FK → entries.id** |
| inserted_at | timestamp | NO | Escalation timestamp |

### Relationships
- **Belongs to:** entries (via entry_id)
- **Belongs to:** users (escalated_by, via escalated_by_id)

### Business Logic

**Escalation Reasons:**
- **complex_case** - Unusual document characteristics, unclear determination
- **quality_check** - Random QA sampling
- **customer_request** - Property manager requested second review
- **policy_question** - Reviewer unsure about policy application
- **high_value** - High-stakes decision (expensive property, high rent)
- **dispute** - Applicant or property manager disputed result
- **training** - New reviewer needs QA oversight

**Escalation Flow:**
1. Reviewer identifies need for escalation during review
2. Escalation record created with reason and notes
3. New `review_items` record created with workflow = 'entry_review'
4. Entry assigned to senior reviewer or QA team
5. Senior reviewer examines original review and escalation notes
6. Senior reviewer makes final determination
7. Original reviewer may receive feedback

**Escalation Tracking:**
```sql
-- Entries with escalations
SELECT e.*, ere.reason, ere.notes
FROM entries e
JOIN entry_review_escalation ere ON e.id = ere.entry_id;

-- Escalation rate by reviewer
SELECT
    u.email,
    COUNT(*) as escalations,
    COUNT(*) * 100.0 / total_reviews.count as escalation_rate
FROM entry_review_escalation ere
JOIN users u ON ere.escalated_by_id = u.id
CROSS JOIN (
    SELECT COUNT(*) as count FROM entry_log WHERE type = 'review_completed'
) total_reviews
GROUP BY u.email, total_reviews.count;
```

**Quality Assurance:**
- Random sampling: 5-10% of entries escalated for QA
- High escalation rate may indicate reviewer training needs
- Low escalation rate may indicate overconfidence

---

## 6. ROLE_ENTRY_STATUS_SORT_PRIORITY

**Purpose:** Configures queue sorting priority by user role and entry status. Controls which entries reviewers see first.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| role_id | bigint | NO | **FK → role.id** |
| entry_status | varchar(255) | NO | Entry status value |
| priority | integer | NO | Sort priority (lower number = higher priority) |

### Relationships
- **Belongs to:** role (via role_id)

### Business Logic

**Purpose:**
- Different roles see different entry priorities
- Senior reviewers prioritize escalations
- Standard reviewers prioritize normal queue items
- QA team prioritizes quality checks

**Priority Configuration Example:**

```
Reviewer Role (role_id = 1):
- entry_status='needs_review', priority=1
- entry_status='in_review', priority=2
- entry_status='escalated', priority=10

Senior Reviewer Role (role_id = 2):
- entry_status='escalated', priority=1
- entry_status='needs_review', priority=5
- entry_status='in_review', priority=10

QA Team Role (role_id = 3):
- entry_status='qa_review', priority=1
- entry_status='escalated', priority=2
- entry_status='needs_review', priority=10
```

**Usage in Queue Query:**
```sql
SELECT e.*
FROM entries e
JOIN review_items ri ON ri.entity_id = e.id AND ri.workflow = 'entry_review'
JOIN role_entry_status_sort_priority resp
    ON resp.role_id = ? AND resp.entry_status = e.status
WHERE ri.state = 'scheduled'
  AND ri.assignable_at <= NOW()
ORDER BY resp.priority ASC, ri.assignable_at ASC
LIMIT 1;
```

**Configuration Management:**
- Allows flexible queue prioritization without code changes
- Different roles can have completely different queue ordering
- Can be updated dynamically based on business needs

---

## Complete Review Workflow Integration

### Example: Entry Review from Start to Finish

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. ENTRY CREATION                                               │
└─────────────────────────────────────────────────────────────────┘
   Entry created by property manager
   ↓
   entry_log: type='entry_created', reviewer_id=system
   ↓
   Entry status='pending_submission', result=NULL

┌─────────────────────────────────────────────────────────────────┐
│ 2. DOCUMENT SUBMISSION                                          │
└─────────────────────────────────────────────────────────────────┘
   Applicant uploads documents (proof)
   ↓
   ML/AI analysis runs (fraud detection, income/asset extraction)
   ↓
   entry_log: type='status_change', entry_status='pending_review'

┌─────────────────────────────────────────────────────────────────┐
│ 3. QUEUE ITEM CREATION                                          │
└─────────────────────────────────────────────────────────────────┘
   review_items created:
     - workflow='entry_review'
     - entity_id=entry.id
     - state='scheduled'
     - assignable_at=NOW() (or NOW() + delay if batching)

┌─────────────────────────────────────────────────────────────────┐
│ 4. REVIEWER REQUESTS WORK                                       │
└─────────────────────────────────────────────────────────────────┘
   Reviewer clicks "Get Next Item"
   ↓
   reviewer_queue created:
     - reviewer_id=reviewer_123
     - state='available'
     - requested_at=NOW()

┌─────────────────────────────────────────────────────────────────┐
│ 5. ASSIGNMENT                                                   │
└─────────────────────────────────────────────────────────────────┘
   System matches review_items with reviewer_queue:
     - Based on role_entry_status_sort_priority
     - Highest priority item assigned
   ↓
   review_items updated:
     - state='assigned'
     - assigned_at=NOW()
     - reviewer_queue_item_id=queue_item.id
   ↓
   reviewer_queue updated:
     - state='assigned'
     - assigned_at=NOW()
     - assigned_entry_id=entry.id
   ↓
   entry_log: type='assignment', reviewer_id=reviewer_123

┌─────────────────────────────────────────────────────────────────┐
│ 6. REVIEW PROCESS                                               │
└─────────────────────────────────────────────────────────────────┘
   Reviewer examines documents:
     - Reviews fraud analysis (proof.result, meta_data_flags)
     - Reviews income/asset verification results
     - Checks identity verification
     - Reviews rent verification
   ↓
   entry_log: type='review_started', reviewer_id=reviewer_123
   ↓
   Reviewer makes determination or escalates

┌─────────────────────────────────────────────────────────────────┐
│ 7A. STANDARD COMPLETION                                         │
└─────────────────────────────────────────────────────────────────┘
   Reviewer submits result:
   ↓
   entries updated:
     - result='CLEAN' (or FRAUD/EDITED/etc.)
     - status='completed'
     - review_status='COMPLETED'
   ↓
   entry_log: type='result_change', entry_result='CLEAN'
   entry_log: type='review_completed'
   ↓
   review_items updated:
     - state='completed'
     - completed_at=NOW()
   ↓
   entry_report created:
     - entry_id, reviewer_id, entry_result, proofs[]
   ↓
   Notifications sent to property manager and applicant

┌─────────────────────────────────────────────────────────────────┐
│ 7B. ESCALATION PATH                                             │
└─────────────────────────────────────────────────────────────────┘
   Reviewer clicks "Escalate"
   ↓
   entry_review_escalation created:
     - reason='complex_case'
     - notes='Unclear if document manipulation or poor scan quality'
     - escalated_by_id=reviewer_123
   ↓
   entry_log: type='escalation', reviewer_id=reviewer_123
   ↓
   Original review_items: state='completed'
   ↓
   New review_items created:
     - workflow='entry_review'
     - state='scheduled'
     - (Higher priority for senior reviewers)
   ↓
   Senior reviewer assigned via same flow
   ↓
   Senior reviewer makes final determination
   ↓
   Continue to standard completion flow
```

---

## Cross-Workflow Support

The Review & Queue System is **workflow-agnostic** and supports all verification workflows:

### 1. Entry Review (Fraud Detection)
```sql
review_items: workflow='entry_review', entity_id → entries.id
```

### 2. Fraud Submission Review
```sql
review_items: workflow='fraud_review', entity_id → fraud_submissions.id
```

### 3. Income Verification Review
```sql
review_items: workflow='income_review', entity_id → income_verification_submissions.id
```

### 4. Asset Verification Review
```sql
review_items: workflow='asset_review', entity_id → asset_verification_submissions.id
```

### 5. Custom Future Workflows
The system can easily support new workflows by:
1. Adding new workflow type to `review_items.workflow`
2. Creating review items with appropriate entity_id
3. Configuring priority in `role_entry_status_sort_priority`

---

## Performance Considerations

### Indexes Recommended

```sql
-- review_items: Queue queries
CREATE INDEX idx_review_items_assignable
  ON review_items(state, workflow, assignable_at)
  WHERE state = 'scheduled' AND assignable_at IS NOT NULL;

CREATE INDEX idx_review_items_entity
  ON review_items(entity_id, workflow);

-- reviewer_queue: Active assignments
CREATE INDEX idx_reviewer_queue_reviewer
  ON reviewer_queue(reviewer_id, state)
  WHERE state != 'cancelled';

CREATE INDEX idx_reviewer_queue_entry
  ON reviewer_queue(assigned_entry_id)
  WHERE assigned_entry_id IS NOT NULL;

-- entry_log: Audit queries
CREATE INDEX idx_entry_log_entry
  ON entry_log(entry_id, inserted_at DESC);

CREATE INDEX idx_entry_log_type
  ON entry_log(type, inserted_at DESC);

-- entry_report: Reporting queries
CREATE INDEX idx_entry_report_entry
  ON entry_report(entry_id);

CREATE INDEX idx_entry_report_reviewer
  ON entry_report(reviewer_id, inserted_at DESC);

-- entry_review_escalation: Escalation tracking
CREATE INDEX idx_entry_review_escalation_entry
  ON entry_review_escalation(entry_id);

CREATE INDEX idx_entry_review_escalation_escalated_by
  ON entry_review_escalation(escalated_by_id, inserted_at DESC);

-- role_entry_status_sort_priority: Priority lookups
CREATE UNIQUE INDEX idx_role_entry_status_priority_unique
  ON role_entry_status_sort_priority(role_id, entry_status);
```

### Query Patterns

**Get next assignable item for reviewer:**
```sql
SELECT ri.*
FROM review_items ri
JOIN role_entry_status_sort_priority resp
    ON resp.role_id = :role_id
    AND resp.entry_status = (
        SELECT status FROM entries WHERE id = ri.entity_id
    )
WHERE ri.state = 'scheduled'
  AND ri.workflow IN (:allowed_workflows)
  AND ri.assignable_at <= NOW()
ORDER BY resp.priority ASC, ri.assignable_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;  -- Prevent double-assignment
```

**Reviewer workload:**
```sql
SELECT
    u.email,
    COUNT(rq.id) as active_items,
    AVG(EXTRACT(EPOCH FROM (rq.assigned_at - rq.requested_at))) as avg_wait_seconds
FROM users u
LEFT JOIN reviewer_queue rq ON u.id = rq.reviewer_id
WHERE rq.state = 'assigned'
GROUP BY u.email;
```

---

## Business Metrics & KPIs

### Queue Health Metrics

```sql
-- Items waiting in queue
SELECT
    workflow,
    COUNT(*) as pending_items,
    AVG(EXTRACT(EPOCH FROM (NOW() - assignable_at))) as avg_wait_seconds
FROM review_items
WHERE state = 'scheduled' AND assignable_at <= NOW()
GROUP BY workflow;

-- SLA compliance (target: 95% < 2 hours)
SELECT
    workflow,
    COUNT(*) as total_completed,
    COUNT(*) FILTER (
        WHERE assigned_at - assignable_at < interval '2 hours'
    ) * 100.0 / COUNT(*) as pct_within_sla
FROM review_items
WHERE state = 'completed'
  AND completed_at > NOW() - interval '7 days'
GROUP BY workflow;
```

### Reviewer Performance

```sql
-- Reviews per reviewer per day
SELECT
    u.email,
    COUNT(*) as reviews_completed,
    AVG(EXTRACT(EPOCH FROM (ri.completed_at - ri.assigned_at)) / 60) as avg_minutes_per_review
FROM review_items ri
JOIN reviewer_queue rq ON ri.reviewer_queue_item_id = rq.id
JOIN users u ON rq.reviewer_id = u.id
WHERE ri.state = 'completed'
  AND ri.completed_at > NOW() - interval '1 day'
GROUP BY u.email
ORDER BY reviews_completed DESC;
```

### Escalation Analysis

```sql
-- Escalation rates by reviewer
SELECT
    u.email,
    COUNT(ere.id) as escalations,
    COUNT(DISTINCT ere.entry_id) as unique_entries
FROM entry_review_escalation ere
JOIN users u ON ere.escalated_by_id = u.id
WHERE ere.inserted_at > NOW() - interval '30 days'
GROUP BY u.email
ORDER BY escalations DESC;
```

---

## Summary

**6 Tables Documented:**
- **review_items** - Central queue table for all workflows
- **reviewer_queue** - Reviewer work requests and assignments
- **entry_log** - Comprehensive audit trail
- **entry_report** - Final completion reports
- **entry_review_escalation** - Complex case escalations
- **role_entry_status_sort_priority** - Queue priority configuration

**Key Features:**
- Workflow-agnostic queue system
- Pull-based reviewer assignment
- SLA tracking and enforcement
- Complete audit trail
- Escalation management
- Role-based prioritization
- Performance metrics and KPIs

**Integration Points:**
- Entries (core entity)
- Users/Roles (reviewer assignment)
- Fraud submissions (fraud workflow)
- Income/Asset verification submissions (verification workflows)
- All future review workflows

**This system is the glue that connects all our documented workflows** - it's how work moves from creation through review to completion.

---

**Next Documentation:**
- Features & Configuration (7 tables)
- Integration Layer (6 tables)

**See Also:**
- [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md) - entries, users, role tables
- [FRAUD_DETECTION_WORKFLOW.md](FRAUD_DETECTION_WORKFLOW.md) - fraud_submissions, fraud_reviews
- [VERIFICATION_WORKFLOWS.md](VERIFICATION_WORKFLOWS.md) - income/asset verification reviews

---

**Generated:** 2025-11-25
**Last Updated:** 2025-11-25
**Version:** 1.0
**Tables Documented:** 6 of 75 core tables
