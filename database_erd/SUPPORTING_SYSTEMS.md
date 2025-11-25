# Supporting Systems - Infrastructure & Background Processing

**Generated:** 2025-11-25
**Database:** fraud_postgresql (Production)
**Tables Documented:** 8 tables

---

## Overview

This document covers the supporting infrastructure tables that enable background processing, API access, user onboarding, session management, duplicate detection, and analytics reporting. These tables provide essential system functionality but are not part of the core verification workflows.

**Categories:**
1. **Duplicate Detection (1 table):** matching_entries
2. **User Onboarding (2 tables):** invitations, invitations_properties
3. **Background Jobs (2 tables):** oban_jobs, oban_peers
4. **API Authentication (1 table):** api_keys
5. **Session Management (1 table):** unauthenticated_session
6. **Analytics (1 table):** analytics_reports

---

## Table of Contents

1. [Duplicate Detection](#1-duplicate-detection-1-table)
   - matching_entries
2. [User Onboarding & Invitations](#2-user-onboarding--invitations-2-tables)
   - invitations
   - invitations_properties
3. [Background Job Processing](#3-background-job-processing-2-tables)
   - oban_jobs
   - oban_peers
4. [API Authentication](#4-api-authentication-1-table)
   - api_keys
5. [Session Management](#5-session-management-1-table)
   - unauthenticated_session
6. [Analytics & Reporting](#6-analytics--reporting-1-table)
   - analytics_reports

---

## 1. Duplicate Detection (1 Table)

### matching_entries

**Purpose:** Identifies potential duplicate or similar entries to prevent duplicate processing and detect repeated applicants

**Primary Key:** id (bigint, auto-incrementing)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| entry_id | uuid | NO | - | Entry being compared (FK → entries.id) |
| matching_entry_id | uuid | NO | - | Entry that matches (FK → entries.id) |
| match_percentage | integer | NO | - | Similarity score 0-100 |
| inserted_at | timestamp | NO | - | Match detection timestamp |
| updated_at | timestamp | NO | - | Last update timestamp |

#### Relationships

**Belongs to:**
- **entries** (entry_id) - The current entry being checked
- **entries** (matching_entry_id) - The previously existing entry that matches

**Pattern:** Self-referential many-to-many through entries table

#### Business Logic

**Purpose:**
- Detect duplicate submissions (same applicant submitting to same property multiple times)
- Identify similar entries (same applicant, different properties)
- Prevent fraud attempts using similar but not identical information
- Support auto-merging of duplicate entries

**Match Detection Algorithm:**
Matches are likely based on:
- Applicant name similarity (fuzzy matching)
- Email/phone matches
- Document similarity
- Property/company matches

**Match Percentage Ranges:**
- **90-100%:** Very high confidence duplicate (auto-merge candidate)
- **70-89%:** High confidence match (flag for review)
- **50-69%:** Moderate match (informational)
- **<50%:** Low match (may not be stored)

**Common Scenarios:**
1. **Duplicate submission:** Applicant submits to same property twice (100% match)
2. **Resubmission:** Applicant rejected at Property A, applies to Property B (80-90% match)
3. **Similar applicants:** Different people with similar names at same property (50-70% match)
4. **Fraud attempt:** Same documents used for different applicant identities (70-90% match)

#### Query Examples

```sql
-- Find all matches for a specific entry
SELECT
    e1.short_id as current_entry,
    e2.short_id as matching_entry,
    me.match_percentage,
    me.inserted_at as detected_at
FROM matching_entries me
JOIN entries e1 ON me.entry_id = e1.id
JOIN entries e2 ON me.matching_entry_id = e2.id
WHERE me.entry_id = 'uuid-here'
ORDER BY me.match_percentage DESC;

-- Find high-confidence duplicates across all entries
SELECT
    e1.short_id as entry_1,
    e2.short_id as entry_2,
    me.match_percentage,
    p1.name as property_1,
    p2.name as property_2
FROM matching_entries me
JOIN entries e1 ON me.entry_id = e1.id
JOIN folders f1 ON e1.folder_id = f1.id
JOIN properties p1 ON f1.property_id = p1.id
JOIN entries e2 ON me.matching_entry_id = e2.id
JOIN folders f2 ON e2.folder_id = f2.id
JOIN properties p2 ON f2.property_id = p2.id
WHERE me.match_percentage >= 90
ORDER BY me.match_percentage DESC;

-- Detect potential fraud: high matches across different properties
SELECT
    COUNT(*) as match_count,
    e1.short_id as suspicious_entry,
    AVG(me.match_percentage) as avg_match
FROM matching_entries me
JOIN entries e1 ON me.entry_id = e1.id
JOIN entries e2 ON me.matching_entry_id = e2.id
JOIN folders f1 ON e1.folder_id = f1.id
JOIN folders f2 ON e2.folder_id = f2.id
WHERE me.match_percentage >= 70
    AND f1.property_id != f2.property_id  -- Different properties
GROUP BY e1.short_id
HAVING COUNT(*) >= 3  -- Matches 3+ different entries
ORDER BY match_count DESC;
```

#### Performance Considerations

- **Index on entry_id:** Fast lookup of matches for specific entry
- **Index on match_percentage:** Filter by similarity threshold
- **Index on inserted_at:** Track when duplicates were detected
- **Composite index (entry_id, match_percentage):** Optimized match queries

#### Integration with Workflows

**Auto-merge logic:**
- If match_percentage = 100 AND same property → auto-merge entries
- Consolidate documents from both entries
- Mark one entry as primary, other as merged

**Review flagging:**
- If match_percentage >= 70 → flag entry for manual review
- Display matching entry details to reviewer
- Allow reviewer to confirm duplicate or mark as different applicant

**Fraud investigation:**
- High matches across different properties → potential fraud
- Same documents reused for different identities
- Escalate to fraud investigation team

---

## 2. User Onboarding & Invitations (2 Tables)

### invitations

**Purpose:** Manages invitation system for onboarding new users to the platform

**Primary Key:** id (uuid)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | - | Primary key |
| company_short_id | varchar(255) | YES | - | Company identifier (denormalized) |
| email | varchar(255) | YES | - | Invitee email address |
| first_name | varchar(255) | YES | - | Invitee first name |
| last_name | varchar(255) | YES | - | Invitee last name |
| role | varchar(255) | YES | - | Role to assign upon acceptance |
| inserted_at | timestamp | NO | - | Invitation creation timestamp |
| updated_at | timestamp | NO | - | Last update timestamp |
| skip_email_sending | boolean | NO | false | Skip sending invitation email |
| company_id | uuid | YES | - | Company FK → companies.id |
| team_id | uuid | YES | - | Team FK → team.id |
| owner_id | uuid | YES | - | Owner FK → owners.id |

#### Relationships

**Belongs to:**
- **companies** (company_id) - Company the user is being invited to
- **team** (team_id) - Team the user will join
- **owners** (owner_id) - Owner context for invitation

**Has many:**
- **invitations_properties** - Properties the user will have access to

#### Business Logic

**Invitation Types:**

1. **Company User Invitation:**
   - company_id + team_id set
   - User will have access to all company properties
   - Role: admin, property_manager, user

2. **Team Member Invitation:**
   - team_id set
   - User joins specific reviewer team
   - Role: reviewer, qa, senior_reviewer

3. **Owner-Level Invitation:**
   - owner_id set
   - User gets access to all properties owned by specific owner
   - Role: owner_admin, owner_viewer

**Invitation Flow:**
1. Admin creates invitation with email + role
2. System sends invitation email (unless skip_email_sending = true)
3. Invitee clicks link, creates account
4. System creates user record with specified role
5. Assigns property access based on invitations_properties
6. Marks invitation as consumed (likely via deleted_at or accepted_at field not shown)

**skip_email_sending Use Cases:**
- Bulk user imports
- Testing/staging environments
- Manual account setup by support team
- Pre-created accounts for specific integrations

#### Query Examples

```sql
-- Find pending invitations for a company
SELECT
    i.email,
    i.first_name,
    i.last_name,
    i.role,
    c.name as company_name,
    t.name as team_name,
    i.inserted_at
FROM invitations i
LEFT JOIN companies c ON i.company_id = c.id
LEFT JOIN team t ON i.team_id = t.id
WHERE i.company_id = 'uuid-here'
ORDER BY i.inserted_at DESC;

-- Find invitations with property access
SELECT
    i.email,
    i.role,
    COUNT(ip.property_id) as property_count
FROM invitations i
LEFT JOIN invitations_properties ip ON i.id = ip.invitation_id
GROUP BY i.id, i.email, i.role
HAVING COUNT(ip.property_id) > 0;

-- Bulk invitation report
SELECT
    c.name as company_name,
    COUNT(*) as pending_invitations,
    COUNT(*) FILTER (WHERE i.skip_email_sending = true) as manual_invitations
FROM invitations i
JOIN companies c ON i.company_id = c.id
GROUP BY c.name
ORDER BY pending_invitations DESC;
```

---

### invitations_properties

**Purpose:** Many-to-many junction table linking invitations to specific properties for granular access control

**Primary Key:** id (bigint, auto-incrementing)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| property_short_id | varchar(255) | YES | - | Property identifier (denormalized) |
| invitation_id | uuid | NO | - | Invitation FK → invitations.id |
| property_id | uuid | YES | - | Property FK → properties.id |
| inserted_at | timestamp | NO | - | Record creation timestamp |
| updated_at | timestamp | NO | - | Last update timestamp |

#### Relationships

**Belongs to:**
- **invitations** (invitation_id) - The invitation
- **properties** (property_id) - The property to grant access to

#### Business Logic

**Purpose:**
- Grant property-specific access to invited users
- Support multi-property management companies with restricted access
- Enable property managers to only see their assigned properties

**Access Grant Scenarios:**

1. **Single Property Access:**
   - Property manager invited to manage 1 property
   - 1 invitation → 1 invitations_properties record

2. **Multi-Property Access:**
   - Regional manager invited to manage 10 properties
   - 1 invitation → 10 invitations_properties records

3. **Full Company Access:**
   - Company admin invited
   - NO invitations_properties records (access all properties)

**Processing Flow:**
1. Invitation created
2. Properties selected for access
3. invitations_properties records created for each property
4. Upon invitation acceptance:
   - User account created
   - users_properties records created from invitations_properties
   - Invitation consumed/deleted

#### Query Examples

```sql
-- Properties included in an invitation
SELECT
    p.name as property_name,
    p.short_id,
    p.address,
    p.city,
    p.state
FROM invitations_properties ip
JOIN properties p ON ip.property_id = p.id
WHERE ip.invitation_id = 'uuid-here';

-- Invitations for a specific property
SELECT
    i.email,
    i.first_name,
    i.last_name,
    i.role,
    i.inserted_at
FROM invitations_properties ip
JOIN invitations i ON ip.invitation_id = i.id
WHERE ip.property_id = 'uuid-here'
ORDER BY i.inserted_at DESC;
```

---

## 3. Background Job Processing (2 Tables)

### oban_jobs

**Purpose:** Oban background job queue for asynchronous task processing (Elixir library)

**Primary Key:** id (bigint, auto-incrementing)

**Oban:** Robust job processing library for Elixir with persistence, retries, scheduling, and observability

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | bigint | NO | AUTO | Primary key |
| state | enum | NO | 'available' | Job state: available, scheduled, executing, retryable, completed, discarded, cancelled |
| queue | text | NO | 'default' | Queue name for job routing |
| worker | text | NO | - | Worker module name (Elixir module) |
| args | jsonb | NO | {} | Job arguments/parameters |
| errors | jsonb[] | NO | [] | Array of error records from failed attempts |
| attempt | integer | NO | 0 | Current attempt number (0-indexed) |
| max_attempts | integer | NO | 20 | Maximum retry attempts before discard |
| inserted_at | timestamp | NO | UTC NOW | Job creation timestamp |
| scheduled_at | timestamp | NO | UTC NOW | When job should be executed |
| attempted_at | timestamp | YES | - | Last execution attempt timestamp |
| completed_at | timestamp | YES | - | Job completion timestamp |
| attempted_by | text[] | YES | - | Array of node names that attempted job |
| discarded_at | timestamp | YES | - | Job discard timestamp (max attempts exceeded) |
| priority | integer | NO | 0 | Job priority (lower = higher priority) |
| tags | varchar[] | YES | [] | Job categorization tags |
| meta | jsonb | YES | {} | Additional job metadata |
| cancelled_at | timestamp | YES | - | Job cancellation timestamp |

#### Job States

**State Machine:**
```
available → executing → completed
         ↓
         retryable → available (retry with backoff)
         ↓
         discarded (max attempts exceeded)
         ↓
         cancelled (manual cancellation)
```

**State Descriptions:**
- **available:** Ready to be picked up by a worker
- **scheduled:** Job scheduled for future execution (delayed job)
- **executing:** Currently being processed by a worker
- **retryable:** Failed but will be retried
- **completed:** Successfully finished
- **discarded:** Failed max_attempts times, given up
- **cancelled:** Manually cancelled by admin or system

#### Business Logic

**Job Types (Common Workers):**

1. **Fraud Detection Jobs:**
   - `Snappt.FraudDetection.AnalyzeDocumentWorker` - ML/AI fraud analysis
   - `Snappt.FraudDetection.SimilarityCheckWorker` - Document duplicate detection
   - `Snappt.OCR.ExtractDataWorker` - OCR processing

2. **Verification Jobs:**
   - `Snappt.Income.CalculateIncomeWorker` - Income calculation
   - `Snappt.Assets.CalculateAssetsWorker` - Asset calculation
   - `Snappt.Identity.ProcessVerificationWorker` - Identity verification webhook processing

3. **Integration Jobs:**
   - `Snappt.Webhooks.DeliverWebhookWorker` - Send results to customer webhooks
   - `Snappt.Yardi.PollProspectsWorker` - Import prospects from Yardi
   - `Snappt.Yardi.SubmitResultsWorker` - Send results back to Yardi

4. **Notification Jobs:**
   - `Snappt.Notifications.SendEmailWorker` - Transactional emails
   - `Snappt.Notifications.SendSMSWorker` - SMS notifications
   - `Snappt.Notifications.SendSlackAlertWorker` - Internal alerts

5. **Maintenance Jobs:**
   - `Snappt.Cleanup.DeleteOldSessionsWorker` - Session cleanup
   - `Snappt.Reports.GenerateReportWorker` - Analytics reports
   - `Snappt.Archival.ArchiveOldEntriesWorker` - Data archival

**Queue Types:**
- **default:** Standard priority jobs
- **high_priority:** Time-sensitive jobs (webhook delivery)
- **low_priority:** Background cleanup, archival
- **ml_analysis:** ML/AI processing (may use GPU workers)
- **external_api:** Third-party API calls (rate-limited)

**Retry Strategy:**
- **Exponential backoff:** Attempts spaced increasingly far apart
- **Typical backoff:** 15s, 1m, 5m, 15m, 1h, 4h, 12h, 24h...
- **max_attempts = 20:** Up to 20 retries before discarding
- **Error tracking:** errors array stores failure details for debugging

#### Query Examples

```sql
-- Job queue status by queue
SELECT
    queue,
    state,
    COUNT(*) as job_count,
    MIN(inserted_at) as oldest_job
FROM oban_jobs
WHERE state IN ('available', 'executing', 'scheduled')
GROUP BY queue, state
ORDER BY queue, state;

-- Failed jobs needing attention
SELECT
    worker,
    args,
    attempt,
    max_attempts,
    errors[array_length(errors, 1)] as latest_error,
    attempted_at
FROM oban_jobs
WHERE state = 'retryable'
    AND attempt >= 5  -- Already failed 5+ times
ORDER BY attempt DESC, attempted_at ASC;

-- Job processing performance
SELECT
    worker,
    COUNT(*) as total_jobs,
    COUNT(*) FILTER (WHERE state = 'completed') as completed,
    COUNT(*) FILTER (WHERE state = 'discarded') as failed,
    AVG(EXTRACT(EPOCH FROM (completed_at - inserted_at))) as avg_duration_seconds
FROM oban_jobs
WHERE inserted_at > NOW() - interval '24 hours'
GROUP BY worker
ORDER BY total_jobs DESC;

-- High-priority jobs waiting
SELECT
    id,
    worker,
    args,
    priority,
    inserted_at,
    NOW() - inserted_at as waiting_time
FROM oban_jobs
WHERE state = 'available'
    AND priority < 0  -- Negative priority = higher priority
ORDER BY priority ASC, inserted_at ASC;

-- Jobs for specific entry
SELECT
    worker,
    state,
    attempt,
    scheduled_at,
    completed_at
FROM oban_jobs
WHERE args->>'entry_id' = 'uuid-here'
ORDER BY inserted_at DESC;
```

#### Performance Considerations

- **Indexes on state and queue:** Fast queue polling
- **Index on scheduled_at:** Efficient delayed job scheduling
- **Index on (state, queue, priority):** Optimized job selection
- **Partial indexes:** Only index active jobs (state not in completed/discarded)

---

### oban_peers

**Purpose:** Oban cluster coordination table for distributed job processing across multiple application servers

**Primary Key:** Composite (name, node)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| name | text | NO | - | Oban instance name (e.g., 'Oban') |
| node | text | NO | - | Node name (e.g., 'app@hostname') |
| started_at | timestamp | NO | - | Node registration timestamp |
| expires_at | timestamp | NO | - | Node lease expiration timestamp |

#### Business Logic

**Purpose:**
- **Cluster coordination:** Track active Oban nodes in the cluster
- **Leader election:** Select leader node for scheduled jobs
- **Health monitoring:** Detect dead nodes via expired leases
- **Load balancing:** Distribute jobs across available nodes

**Lease Mechanism:**
- Each node registers itself in oban_peers
- Node updates expires_at every N seconds (heartbeat)
- If expires_at passes without update → node considered dead
- Other nodes take over dead node's jobs

**Typical Lifespan:**
- Node starts → inserts oban_peers record
- Node runs → updates expires_at every 30s
- Node stops → either deletes record OR lease expires
- Cluster sees expired lease → removes node from pool

#### Query Examples

```sql
-- Active Oban nodes
SELECT
    node,
    started_at,
    expires_at,
    NOW() - started_at as uptime,
    expires_at - NOW() as expires_in
FROM oban_peers
WHERE expires_at > NOW()
ORDER BY started_at ASC;

-- Detect stale/dead nodes
SELECT
    node,
    started_at,
    expires_at,
    NOW() - expires_at as expired_ago
FROM oban_peers
WHERE expires_at < NOW()
ORDER BY expires_at DESC;
```

---

## 4. API Authentication (1 Table)

### api_keys

**Purpose:** API authentication and authorization for programmatic access to Snappt platform

**Primary Key:** id (uuid)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | - | Primary key |
| description | varchar(255) | YES | - | Human-readable key description |
| key | varchar(255) | YES | - | API key (encrypted/hashed) |
| inserted_at | timestamp | NO | - | Key creation timestamp |
| updated_at | timestamp | NO | - | Last update timestamp |
| master | boolean | YES | false | Master key with full access |
| role_id | bigint | YES | - | Role FK → role.id |
| company_id | uuid | YES | - | Company FK → companies.id |
| is_active | boolean | YES | true | Key enabled/disabled |
| property_id | uuid | YES | - | Property FK → properties.id |

#### Relationships

**Belongs to:**
- **companies** (company_id) - Company this API key belongs to
- **properties** (property_id) - Property-specific API key
- **role** (role_id) - Role determining permissions

#### Business Logic

**API Key Types:**

1. **Master Key:**
   - master = true
   - Full platform access (admin operations)
   - Used by internal services, admin tools
   - Very limited number (1-5 keys)

2. **Company Key:**
   - company_id set, property_id NULL
   - Access all properties within company
   - Used by PMC integrations, dashboards
   - Role determines read vs write permissions

3. **Property Key:**
   - property_id set
   - Access limited to single property
   - Used by property-level integrations
   - Common for small property managers

**Access Control:**
- **role_id determines permissions:**
  - read_only: Get entry status, results
  - write: Create entries, submit documents
  - admin: Full CRUD operations

**Key Lifecycle:**
1. Admin creates API key with description
2. System generates random key, stores hash
3. Key shown to user ONCE (cannot retrieve later)
4. Key used in API requests: `Authorization: Bearer {key}`
5. System validates key, checks is_active
6. System enforces company/property scope
7. Admin can disable key (is_active = false)
8. Admin can delete key (soft delete or hard delete)

**Security Features:**
- Keys stored encrypted/hashed (not plaintext)
- is_active allows instant revocation without deletion
- description tracks key purpose for audit
- Company/property scoping prevents unauthorized access

#### Query Examples

```sql
-- Active API keys by company
SELECT
    ak.description,
    ak.inserted_at as created_at,
    c.name as company_name,
    r.name as role,
    CASE
        WHEN ak.master THEN 'Master Key'
        WHEN ak.property_id IS NOT NULL THEN 'Property Key'
        ELSE 'Company Key'
    END as key_type
FROM api_keys ak
LEFT JOIN companies c ON ak.company_id = c.id
LEFT JOIN role r ON ak.role_id = r.id
WHERE ak.is_active = true
ORDER BY ak.inserted_at DESC;

-- Property-specific API keys
SELECT
    ak.description,
    p.name as property_name,
    c.name as company_name,
    ak.inserted_at as created_at
FROM api_keys ak
JOIN properties p ON ak.property_id = p.id
JOIN companies c ON p.company_id = c.id
WHERE ak.is_active = true
ORDER BY p.name;

-- Audit: All API keys with last usage (would need API request log)
SELECT
    ak.description,
    ak.inserted_at as created_at,
    ak.is_active,
    c.name as company_name
FROM api_keys ak
LEFT JOIN companies c ON ak.company_id = c.id
ORDER BY ak.inserted_at DESC;
```

---

## 5. Session Management (1 Table)

### unauthenticated_session

**Purpose:** Temporary session storage for applicants submitting documents without creating user accounts

**Primary Key:** id (uuid), with unique token for session lookup

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | - | Primary key |
| token | uuid | NO | - | Session token (unique) |
| ip_address | varchar(255) | NO | - | Applicant IP address |
| inserted_at | timestamp | NO | - | Session creation timestamp |
| application | jsonb | NO | - | Applicant application data |
| property | jsonb | NO | - | Property information |
| proofs | jsonb[] | NO | [] | Uploaded document references |
| external | boolean | YES | false | External applicant (not logged in) |
| applicant_detail_id | uuid | YES | - | Links to applicant_details.id when converted |
| identity_id | uuid | YES | - | Identity verification session ID |

#### Relationships

**Belongs to (optional):**
- **applicant_details** (applicant_detail_id) - Created when session converts to real entry

#### Business Logic

**Purpose:**
- Allow applicants to upload documents WITHOUT creating account
- Support "guest checkout" style document submission
- Temporary storage before entry creation
- Session-based workflow for better UX

**Session Flow:**

1. **Session Creation:**
   - Applicant receives invitation link with embedded property info
   - System creates unauthenticated_session with unique token
   - Token included in URL for subsequent requests

2. **Document Upload:**
   - Applicant uploads paystubs, bank statements
   - Files stored temporarily in S3
   - proofs array stores document references
   - application JSONB stores form data (name, email, phone)

3. **Session Completion:**
   - Applicant submits all documents
   - System creates real entry + applicant + applicant_details records
   - Documents moved to permanent storage
   - Session marked complete (or deleted)
   - applicant_detail_id links session to created applicant

4. **Session Expiration:**
   - Sessions expire after N hours/days
   - Cleanup job deletes expired sessions
   - Temporary documents deleted from S3

**JSONB Field Structures:**

```json
application: {
  "first_name": "John",
  "last_name": "Smith",
  "email": "john@example.com",
  "phone": "555-123-4567",
  "unit": "Apt 301",
  "move_in_date": "2024-02-01"
}

property: {
  "id": "uuid",
  "name": "Sunset Apartments",
  "address": "123 Main St",
  "required_documents": ["paystub", "bank_statement"]
}

proofs: [
  {
    "id": "uuid",
    "type": "paystub",
    "file_url": "s3://temp/...",
    "uploaded_at": "2024-01-15T10:30:00Z"
  },
  {
    "id": "uuid",
    "type": "bank_statement",
    "file_url": "s3://temp/...",
    "uploaded_at": "2024-01-15T10:32:00Z"
  }
]
```

**Security Considerations:**
- **token is UUID:** Unguessable session identifier
- **IP tracking:** Detect potential abuse
- **Expiration:** Sessions auto-expire to prevent stale data
- **Rate limiting:** Prevent spam uploads
- **external flag:** Clearly marks untrusted sessions

#### Query Examples

```sql
-- Active sessions awaiting completion
SELECT
    token,
    application->>'email' as applicant_email,
    property->>'name' as property_name,
    array_length(proofs, 1) as documents_uploaded,
    inserted_at,
    NOW() - inserted_at as session_age
FROM unauthenticated_session
WHERE applicant_detail_id IS NULL  -- Not yet converted
ORDER BY inserted_at DESC;

-- Sessions ready for conversion
SELECT
    id,
    token,
    application->>'first_name' as first_name,
    application->>'last_name' as last_name,
    application->>'email' as email,
    array_length(proofs, 1) as documents_count
FROM unauthenticated_session
WHERE applicant_detail_id IS NULL
    AND array_length(proofs, 1) >= 2  -- Minimum documents uploaded
ORDER BY inserted_at ASC;

-- Completed sessions (converted to entries)
SELECT
    us.token,
    us.application->>'email' as email,
    ad.id as applicant_detail_id,
    us.inserted_at as session_started,
    ad.inserted_at as applicant_created
FROM unauthenticated_session us
JOIN applicant_details ad ON us.applicant_detail_id = ad.id
WHERE us.applicant_detail_id IS NOT NULL
ORDER BY ad.inserted_at DESC;

-- Session cleanup: Find expired sessions
SELECT
    id,
    token,
    inserted_at,
    NOW() - inserted_at as age
FROM unauthenticated_session
WHERE applicant_detail_id IS NULL  -- Incomplete
    AND inserted_at < NOW() - interval '48 hours'  -- Older than 48 hours
ORDER BY inserted_at ASC;
```

---

## 6. Analytics & Reporting (1 Table)

### analytics_reports

**Purpose:** Scheduled analytics report generation and tracking

**Primary Key:** id (uuid)

#### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | - | Primary key |
| type | varchar(255) | YES | - | Report type identifier |
| references | uuid[] | YES | - | Array of reference IDs (entries, properties, etc.) |
| all_references | boolean | NO | false | Include all available references |
| from | date | YES | - | Report start date |
| to | date | YES | - | Report end date |
| user_id | uuid | YES | - | User who requested report (FK → users.id) |
| inserted_at | timestamp | NO | - | Report creation timestamp |
| updated_at | timestamp | NO | - | Last update timestamp |

#### Relationships

**Belongs to:**
- **users** (user_id) - User who requested the report

#### Business Logic

**Report Types:**

1. **Entry Performance Reports:**
   - type = 'entry_performance'
   - Metrics: Submission rate, approval rate, avg review time
   - references = array of entry IDs
   - Date range: from → to

2. **Property Performance Reports:**
   - type = 'property_performance'
   - Metrics: Entry volume, fraud rate, verification success rate
   - references = array of property IDs
   - Date range: from → to

3. **Reviewer Performance Reports:**
   - type = 'reviewer_performance'
   - Metrics: Reviews completed, avg review time, quality scores
   - references = array of user IDs (reviewers)
   - Date range: from → to

4. **Company-Wide Reports:**
   - type = 'company_summary'
   - all_references = true (all properties)
   - Aggregate metrics across entire company

5. **Fraud Detection Reports:**
   - type = 'fraud_analysis'
   - Metrics: Fraud detection rate, false positive rate, fraud types
   - references = array of entry IDs flagged for fraud

**Report Generation Flow:**

1. **Report Request:**
   - User clicks "Generate Report" in dashboard
   - System creates analytics_reports record
   - Queues background job for report generation

2. **Background Processing:**
   - Oban job picks up report request
   - Queries database for specified date range and references
   - Calculates metrics, generates charts
   - Exports to PDF/Excel

3. **Report Delivery:**
   - Email sent to user_id with download link
   - Report stored in S3
   - Link expires after 7 days

4. **Scheduled Reports:**
   - Weekly/monthly reports auto-generated
   - all_references = true for company-wide
   - Emailed to admins automatically

**references Array Usage:**
- **Specific entities:** [uuid1, uuid2, uuid3] for targeted reports
- **Empty + all_references=true:** Include everything
- **Empty + all_references=false:** User's accessible entities only

#### Query Examples

```sql
-- Recent reports by type
SELECT
    type,
    COUNT(*) as report_count,
    MAX(inserted_at) as latest_report
FROM analytics_reports
WHERE inserted_at > NOW() - interval '30 days'
GROUP BY type
ORDER BY report_count DESC;

-- User report history
SELECT
    ar.type,
    ar.from,
    ar.to,
    ar.inserted_at,
    u.email as requested_by
FROM analytics_reports ar
JOIN users u ON ar.user_id = u.id
WHERE ar.user_id = 'uuid-here'
ORDER BY ar.inserted_at DESC;

-- Company-wide reports
SELECT
    type,
    from,
    to,
    inserted_at
FROM analytics_reports
WHERE all_references = true
ORDER BY inserted_at DESC;

-- Property-specific reports
SELECT
    ar.type,
    ar.from,
    ar.to,
    ar.references,
    COUNT(*) as property_count
FROM analytics_reports ar
WHERE ar.type = 'property_performance'
GROUP BY ar.id, ar.type, ar.from, ar.to, ar.references
ORDER BY ar.inserted_at DESC;
```

---

## Performance Considerations

### Recommended Indexes

**matching_entries:**
- Index on entry_id (FK lookup)
- Index on matching_entry_id (FK lookup)
- Index on match_percentage (filtering)
- Composite index (entry_id, match_percentage) for common queries

**invitations:**
- Index on company_id (FK lookup)
- Index on team_id (FK lookup)
- Index on email (user lookup)

**invitations_properties:**
- Index on invitation_id (FK lookup)
- Index on property_id (FK lookup)

**oban_jobs:**
- Composite index (state, queue, priority, scheduled_at) for job selection
- Partial index on state WHERE state IN ('available', 'scheduled', 'executing')
- Index on worker for performance analytics

**api_keys:**
- Unique index on key (authentication lookup)
- Index on company_id (FK lookup)
- Index on is_active (filtering)

**unauthenticated_session:**
- Unique index on token (session lookup)
- Index on applicant_detail_id (completion tracking)
- Index on inserted_at (cleanup queries)

**analytics_reports:**
- Index on user_id (FK lookup)
- Index on type (filtering)
- Index on (from, to) (date range queries)

---

## Summary

### Key Features

**Duplicate Detection:**
- Automatic entry matching with confidence scores
- Fraud prevention via duplicate detection
- Auto-merge support for 100% matches

**User Onboarding:**
- Invitation-based user provisioning
- Property-level access grants
- Role assignment during invitation

**Background Processing:**
- Robust job queue with retries
- Distributed processing across cluster
- Job monitoring and error tracking

**API Access:**
- Flexible API key scoping (master/company/property)
- Role-based permissions
- Instant key revocation

**Session Management:**
- Guest document submission without login
- Temporary storage with auto-expiration
- Secure session tokens

**Analytics:**
- Scheduled report generation
- Flexible date ranges and entity selection
- User-requested and automated reports

### Integration Points

**With Core Workflows:**
- matching_entries links duplicate entries
- unauthenticated_session converts to applicants/entries
- oban_jobs processes all async tasks (fraud analysis, webhooks, etc.)

**With External Systems:**
- api_keys authenticate external integrations
- analytics_reports provide business intelligence

**With User Management:**
- invitations onboard new platform users
- invitations_properties grant property access

---

## Related Documentation

- [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md) - Foundation entities
- [FRAUD_DETECTION_WORKFLOW.md](FRAUD_DETECTION_WORKFLOW.md) - Fraud detection details
- [INTEGRATION_LAYER.md](INTEGRATION_LAYER.md) - External integrations
- [README.md](README.md) - Project overview

---

**Generated:** 2025-11-25
**Database:** fraud_postgresql
**Tables Documented:** 8 (matching_entries, invitations, invitations_properties, oban_jobs, oban_peers, api_keys, unauthenticated_session, analytics_reports)
