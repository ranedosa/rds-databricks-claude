# Disputes Workflow - Screening Result Challenges

**Generated:** 2025-11-25
**Database:** fraud_postgresql (Production)
**Tables Documented:** 3 dispute management tables

---

## Overview

The Disputes Workflow manages challenges to screening results from applicants or property managers. When someone believes a screening result is incorrect, they can open a dispute with a specific category and description. The system tracks all dispute communications via email and maintains a complete audit trail.

**Key Functions:**
- **Dispute Creation** - Track who opened dispute, when, and why
- **Categorization** - Classify disputes by issue type for analysis
- **Email Communication** - Log all email correspondence related to disputes
- **Resolution Tracking** - Monitor dispute lifecycle from opening to resolution
- **Analytics** - Understand common dispute reasons and resolution patterns

---

## Table Inventory

### Dispute Management (3 tables)
- **disputes** - Core dispute records with category and description
- **dispute_categories** - Dispute reason categories (lookup table)
- **dispute_emails** - Email communication log for disputes

---

## Dispute Workflow Architecture

```
Applicant/Property Manager → Opens Dispute → disputes (created)
                                               ↓
                                     dispute_categories (classify)
                                               ↓
                              Email Communication (back and forth)
                                               ↓
                                     dispute_emails (logged)
                                               ↓
                                     Resolution (Snappt updates records)
```

---

## Detailed Table Documentation

## 1. DISPUTES

**Purpose:** Core dispute tracking table. Records when someone challenges a screening result, who opened it, what category, and detailed description.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key (auto-generated) |
| application_submission_id | uuid | NO | **FK → applicant_submissions.id** (submission being disputed) |
| opened_by_user_id | uuid | NO | **FK → users.id** (user who opened dispute) |
| opened_at | timestamp | NO | When dispute was opened |
| dispute_category_id | uuid | NO | **FK → dispute_categories.id** (dispute reason) |
| description | text | YES | Detailed description of dispute issue |
| inserted_at | timestamp | NO | Record creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** applicant_submissions (via application_submission_id)
- **Belongs to:** users (via opened_by_user_id)
- **Belongs to:** dispute_categories (via dispute_category_id)
- **Has many:** dispute_emails

### Business Logic

**Who Can Open Disputes:**
- **Property Managers** - Challenge screening results they believe are incorrect
- **Applicants** - Challenge results they believe are unfair or based on wrong information
- **Snappt Support Staff** - Open disputes on behalf of users

**Common Dispute Scenarios:**

1. **Fraud Detection False Positive:**
   - Legitimate document flagged as fraudulent
   - Poor scan quality mistaken for manipulation
   - Category: "Bank Statement Issue" or "Incorrect or Missing Documents"

2. **Income Verification Error:**
   - Income calculation incorrect
   - Wrong documents analyzed
   - Employment status misunderstood
   - Category: "Income Verification Dispute"

3. **Identity Mismatch:**
   - Name variations (maiden name, hyphenated names)
   - Nickname vs legal name
   - Category: "Name or Info Doesn't Match"

4. **Technical Issues:**
   - Document upload failed but marked as incomplete
   - System error during processing
   - Category: "Upload or File Error"

5. **Applicant Declined Incorrectly:**
   - Automated rejection that should have been approved
   - Policy misapplication
   - Category: "Application Declined in Error"

**Dispute Creation Flow:**
```
1. User identifies issue with screening result
2. User clicks "Open Dispute" in UI
3. System creates dispute record:
   - application_submission_id: Links to submission
   - opened_by_user_id: Tracks who opened it
   - opened_at: Timestamp for SLA tracking
   - dispute_category_id: Classification
   - description: Detailed explanation
4. Email sent to Snappt support team
5. dispute_emails record created
```

**SLA Tracking:**
- `opened_at` provides dispute age
- Can calculate: NOW() - opened_at for time open
- Target response time (typically 24-48 hours)

**Resolution Process (Conceptual):**
1. Dispute opened
2. Snappt support reviews original screening
3. If valid dispute:
   - Update entry result
   - Update applicant_submission result
   - Notify property manager and applicant
4. If invalid dispute:
   - Respond with explanation
   - No changes to screening results
5. Close dispute (likely status field in future or inferred from resolution)

### Example Queries

**Open disputes by category:**
```sql
SELECT
    dc.name as dispute_category,
    COUNT(d.id) as open_disputes,
    AVG(EXTRACT(EPOCH FROM (NOW() - d.opened_at)) / 3600) as avg_hours_open
FROM disputes d
JOIN dispute_categories dc ON d.dispute_category_id = dc.id
WHERE d.opened_at > NOW() - interval '30 days'
GROUP BY dc.name
ORDER BY open_disputes DESC;
```

**Disputes for specific applicant submission:**
```sql
SELECT
    d.id,
    d.opened_at,
    dc.name as category,
    d.description,
    u.email as opened_by,
    COUNT(de.id) as email_count
FROM disputes d
JOIN dispute_categories dc ON d.dispute_category_id = dc.id
JOIN users u ON d.opened_by_user_id = u.id
LEFT JOIN dispute_emails de ON de.dispute_id = d.id
WHERE d.application_submission_id = :submission_id
GROUP BY d.id, d.opened_at, dc.name, d.description, u.email;
```

**Properties with highest dispute rates:**
```sql
SELECT
    p.name as property_name,
    COUNT(DISTINCT d.id) as dispute_count,
    COUNT(DISTINCT asub.id) as submission_count,
    COUNT(DISTINCT d.id) * 100.0 / COUNT(DISTINCT asub.id) as dispute_rate
FROM applicant_submissions asub
JOIN applicants a ON asub.applicant_id = a.id
JOIN entries e ON a.entry_id = e.id
JOIN folders f ON e.folder_id = f.id
JOIN properties p ON f.property_id = p.id
LEFT JOIN disputes d ON d.application_submission_id = asub.id
WHERE asub.inserted_at > NOW() - interval '90 days'
GROUP BY p.name
HAVING COUNT(DISTINCT asub.id) > 10
ORDER BY dispute_rate DESC
LIMIT 20;
```

---

## 2. DISPUTE_CATEGORIES

**Purpose:** Lookup table for dispute reason categories. Enables consistent classification and analytics.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key (auto-generated) |
| name | text | NO | Category name (user-facing) |
| active | boolean | NO | Category is available for selection (default: true) |
| inserted_at | timestamp | NO | Category creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Has many:** disputes (via dispute_category_id)

### Business Logic

**Current Active Categories:**
1. **Application Declined in Error** - Automated rejection that should be approved
2. **Bank Statement Issue** - Problems with bank statement analysis
3. **Income Verification Dispute** - Income calculation or eligibility errors
4. **Incorrect or Missing Documents** - Wrong documents analyzed or documents missing
5. **Name or Info Doesn't Match** - Identity information discrepancies
6. **Other** - Catch-all for uncategorized disputes
7. **Upload or File Error** - Technical issues with document upload

**Category Management:**
- `active = true` - Category appears in UI dropdowns
- `active = false` - Category deprecated but preserved for historical disputes
- New categories can be added without code changes

**Category Usage Analytics:**
```sql
-- Most common dispute categories
SELECT
    dc.name,
    dc.active,
    COUNT(d.id) as dispute_count,
    COUNT(d.id) * 100.0 / SUM(COUNT(d.id)) OVER () as percentage
FROM dispute_categories dc
LEFT JOIN disputes d ON d.dispute_category_id = dc.id
    AND d.opened_at > NOW() - interval '90 days'
GROUP BY dc.id, dc.name, dc.active
ORDER BY dispute_count DESC;
```

**Category Trends Over Time:**
```sql
-- Dispute category trends by month
SELECT
    DATE_TRUNC('month', d.opened_at) as month,
    dc.name as category,
    COUNT(d.id) as disputes
FROM disputes d
JOIN dispute_categories dc ON d.dispute_category_id = dc.id
WHERE d.opened_at > NOW() - interval '12 months'
GROUP BY DATE_TRUNC('month', d.opened_at), dc.name
ORDER BY month DESC, disputes DESC;
```

**Suggested Category Additions (Future):**
- Asset Verification Issue
- Identity Verification Failed
- Rent History Dispute
- Document Quality Issue
- Policy Exception Request

---

## 3. DISPUTE_EMAILS

**Purpose:** Email communication log for disputes. Tracks all emails sent/received related to each dispute for audit trail.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key (auto-generated) |
| dispute_id | uuid | NO | **FK → disputes.id** (dispute this email relates to) |
| email | varchar(255) | NO | Email address (sender or recipient) |
| email_id | varchar(255) | YES | External email system ID (Postmark, SendGrid, etc.) |
| inserted_at | timestamp | NO | Email timestamp |

### Relationships
- **Belongs to:** disputes (via dispute_id)

### Business Logic

**Email Types (Inferred from email field):**
1. **Dispute Opened Notification** - Email to Snappt support when dispute created
2. **Support Response** - Snappt support replies to user
3. **Resolution Notification** - Email when dispute is resolved
4. **Follow-up Communication** - Additional back-and-forth

**Email Flow:**
```
Dispute Opened → Email to support@snappt.com → dispute_emails (logged)
                                                       ↓
Support Responds → Email to user@example.com → dispute_emails (logged)
                                                       ↓
User Replies → Email to support@snappt.com → dispute_emails (logged)
                                                       ↓
Resolution → Email to user@example.com → dispute_emails (logged)
```

**External Email System Integration:**
- `email_id` stores external system message ID
- Enables lookup in email provider (Postmark, SendGrid) for full email content
- Useful for debugging delivery issues

**Email Audit Trail:**
```sql
-- Complete email thread for dispute
SELECT
    de.inserted_at,
    de.email,
    de.email_id,
    CASE
        WHEN de.email LIKE '%@snappt.com' THEN 'Snappt Support'
        ELSE 'User'
    END as sender_type
FROM dispute_emails de
WHERE de.dispute_id = :dispute_id
ORDER BY de.inserted_at ASC;
```

**Dispute Communication Metrics:**
```sql
-- Average email count per dispute
SELECT
    AVG(email_count) as avg_emails_per_dispute,
    MIN(email_count) as min_emails,
    MAX(email_count) as max_emails
FROM (
    SELECT dispute_id, COUNT(*) as email_count
    FROM dispute_emails
    GROUP BY dispute_id
) subquery;
```

**Response Time Tracking:**
```sql
-- Time between dispute opened and first support response
SELECT
    d.id,
    d.opened_at,
    MIN(de.inserted_at) as first_response_at,
    MIN(de.inserted_at) - d.opened_at as response_time
FROM disputes d
JOIN dispute_emails de ON de.dispute_id = d.id
WHERE de.email LIKE '%@snappt.com'
GROUP BY d.id, d.opened_at
ORDER BY response_time DESC;
```

---

## Integration Points

### Links to Other Workflows

**applicant_submissions:**
- disputes.application_submission_id → applicant_submissions.id
- Links dispute to specific document submission
- Enables navigation: dispute → submission → applicant → entry → property

**users:**
- disputes.opened_by_user_id → users.id
- Tracks who opened dispute (property manager, applicant, support)
- Enables user-level dispute analytics

**Complete Data Flow:**
```sql
-- Full dispute context query
SELECT
    -- Dispute Info
    d.id as dispute_id,
    d.opened_at,
    dc.name as dispute_category,
    d.description,

    -- Who Opened It
    u.email as opened_by,
    u.role as opener_role,

    -- What Was Disputed
    asub.id as submission_id,
    a.full_name as applicant_name,
    a.email as applicant_email,

    -- Entry Context
    e.short_id as entry_id,
    e.result as entry_result,
    e.status as entry_status,

    -- Property Context
    p.name as property_name,
    c.name as company_name,

    -- Email Communication
    COUNT(de.id) as email_count,
    MAX(de.inserted_at) as last_email_at

FROM disputes d
JOIN dispute_categories dc ON d.dispute_category_id = dc.id
JOIN users u ON d.opened_by_user_id = u.id
JOIN applicant_submissions asub ON d.application_submission_id = asub.id
JOIN applicants a ON asub.applicant_id = a.id
JOIN entries e ON a.entry_id = e.id
JOIN folders f ON e.folder_id = f.id
JOIN properties p ON f.property_id = p.id
JOIN companies c ON p.company_id = c.id
LEFT JOIN dispute_emails de ON de.dispute_id = d.id
GROUP BY d.id, dc.name, d.description, u.email, u.role, asub.id,
         a.full_name, a.email, e.short_id, e.result, e.status,
         p.name, c.name, d.opened_at;
```

---

## Performance Considerations

### Indexes Recommended

```sql
-- disputes: Lookup by submission
CREATE INDEX idx_disputes_application_submission
  ON disputes(application_submission_id);

-- disputes: Lookup by category for analytics
CREATE INDEX idx_disputes_category_opened
  ON disputes(dispute_category_id, opened_at DESC);

-- disputes: Lookup by opener (user analytics)
CREATE INDEX idx_disputes_opened_by
  ON disputes(opened_by_user_id, opened_at DESC);

-- dispute_emails: Get all emails for dispute
CREATE INDEX idx_dispute_emails_dispute
  ON dispute_emails(dispute_id, inserted_at ASC);

-- dispute_emails: External email system lookup
CREATE INDEX idx_dispute_emails_email_id
  ON dispute_emails(email_id)
  WHERE email_id IS NOT NULL;

-- dispute_categories: Active category lookups
CREATE INDEX idx_dispute_categories_active
  ON dispute_categories(active)
  WHERE active = true;
```

### Query Patterns

**High-volume queries:**
- "Show me all open disputes" - Filter by date range
- "Get dispute details for submission" - Indexed on application_submission_id
- "Show email thread for dispute" - Indexed on dispute_id

**Analytics queries:**
- Dispute rate by property
- Most common dispute categories
- Average resolution time
- Support team response time

---

## Business Metrics & KPIs

### Dispute Rate Tracking

```sql
-- Overall dispute rate
SELECT
    COUNT(DISTINCT asub.id) as total_submissions,
    COUNT(DISTINCT d.id) as disputes,
    COUNT(DISTINCT d.id) * 100.0 / COUNT(DISTINCT asub.id) as dispute_rate
FROM applicant_submissions asub
LEFT JOIN disputes d ON d.application_submission_id = asub.id
WHERE asub.inserted_at > NOW() - interval '30 days';
```

### Category Distribution

```sql
-- Dispute breakdown by category
SELECT
    dc.name,
    COUNT(d.id) as count,
    COUNT(d.id) * 100.0 / SUM(COUNT(d.id)) OVER () as percentage,
    AVG(EXTRACT(EPOCH FROM (NOW() - d.opened_at)) / 86400) as avg_days_open
FROM disputes d
JOIN dispute_categories dc ON d.dispute_category_id = dc.id
WHERE d.opened_at > NOW() - interval '90 days'
GROUP BY dc.name
ORDER BY count DESC;
```

### Resolution Time Tracking

```sql
-- Dispute age distribution
SELECT
    CASE
        WHEN EXTRACT(EPOCH FROM (NOW() - d.opened_at)) / 3600 < 24 THEN '< 24 hours'
        WHEN EXTRACT(EPOCH FROM (NOW() - d.opened_at)) / 3600 < 48 THEN '24-48 hours'
        WHEN EXTRACT(EPOCH FROM (NOW() - d.opened_at)) / 86400 < 7 THEN '2-7 days'
        ELSE '> 7 days'
    END as age_bucket,
    COUNT(*) as dispute_count
FROM disputes d
WHERE d.opened_at > NOW() - interval '30 days'
GROUP BY age_bucket
ORDER BY
    CASE age_bucket
        WHEN '< 24 hours' THEN 1
        WHEN '24-48 hours' THEN 2
        WHEN '2-7 days' THEN 3
        ELSE 4
    END;
```

### Support Team Performance

```sql
-- Average response time by support agent
SELECT
    responding_user.email as support_agent,
    COUNT(DISTINCT d.id) as disputes_handled,
    AVG(EXTRACT(EPOCH FROM (first_response.inserted_at - d.opened_at)) / 3600) as avg_response_hours
FROM disputes d
JOIN (
    SELECT DISTINCT ON (dispute_id)
        dispute_id,
        email,
        inserted_at
    FROM dispute_emails
    WHERE email LIKE '%@snappt.com'
    ORDER BY dispute_id, inserted_at ASC
) first_response ON first_response.dispute_id = d.id
JOIN users responding_user ON responding_user.email = first_response.email
WHERE d.opened_at > NOW() - interval '30 days'
GROUP BY responding_user.email
ORDER BY disputes_handled DESC;
```

---

## Security & Compliance

### PII Considerations

**Sensitive Data:**
- `disputes.description` - May contain applicant PII (names, SSN, income details)
- `dispute_emails.email` - Email addresses (PII)

**Protection Measures:**
- Encrypt descriptions at rest
- Access control: Only support staff and relevant property managers can view
- Audit trail: Log all dispute views
- Data retention: Comply with GDPR/CCPA for dispute data deletion

### Data Retention

**Retention Policy:**
- Active disputes: Indefinite retention
- Resolved disputes: Retain for 2-5 years for compliance
- After retention period: Archive or anonymize

**GDPR/CCPA Compliance:**
- Right to access: Users can request all disputes they opened
- Right to deletion: Disputes can be anonymized/deleted upon request
- Right to rectification: Description can be updated if information incorrect

---

## Common Use Cases

### 1. Applicant Disputes Fraud Detection
**Scenario:** Legitimate bank statement flagged as fraudulent

**Workflow:**
1. Property manager receives "FRAUD" result
2. Applicant claims document is legitimate
3. Property manager opens dispute:
   - Category: "Bank Statement Issue"
   - Description: "Applicant states bank statement is legitimate, poor quality scan may have caused false positive"
4. Snappt support reviews:
   - Re-examine OCR results
   - Check fraud detection confidence scores
   - Manual visual inspection
5. Resolution:
   - If valid: Update entry result to CLEAN, notify parties
   - If invalid: Explain fraud indicators found, result stands

### 2. Income Verification Calculation Error
**Scenario:** Income miscalculated, applicant should qualify

**Workflow:**
1. Entry result: REJECTED (insufficient income)
2. Property manager reviews income docs
3. Property manager opens dispute:
   - Category: "Income Verification Dispute"
   - Description: "Applicant shows $5,000/month gross income on paystub, but system calculated $3,500. Please review."
4. Snappt support reviews:
   - Check income extraction OCR
   - Verify calculation logic
   - Identify bug or edge case
5. Resolution:
   - Recalculate income
   - Update income_verification_results
   - Update entry result to APPROVED

### 3. Technical Upload Issue
**Scenario:** Document upload failed, applicant marked incomplete

**Workflow:**
1. Entry status: INCOMPLETE (missing documents)
2. Applicant claims documents were uploaded
3. Property manager opens dispute:
   - Category: "Upload or File Error"
   - Description: "Applicant states paystub was uploaded yesterday but system shows missing"
4. Snappt support reviews:
   - Check upload logs
   - Review applicant_submission_document_sources
   - Identify technical issue (timeout, large file, etc.)
5. Resolution:
   - Request applicant re-upload
   - Or: Manually add documents if found in logs
   - Update entry status

---

## Dispute Resolution Workflow (Conceptual)

**Note:** These tables track dispute opening and communication, but resolution status likely tracked elsewhere (possibly entry_log or separate resolution table not yet documented).

**Typical Resolution Flow:**
```
1. Dispute Opened (disputes record created)
   ↓
2. Support Notified (dispute_emails: notification sent)
   ↓
3. Support Reviews (access original entry, documents, analysis results)
   ↓
4. Support Communicates (dispute_emails: support response)
   ↓
5. User Responds (dispute_emails: user reply)
   ↓ (may repeat)
6. Decision Made:
   - Valid Dispute → Update entry/verification results, entry_log
   - Invalid Dispute → Explain reasoning via email
   ↓
7. Resolution Email (dispute_emails: final notification)
   ↓
8. Dispute Closed (inferred from timestamps or separate status field)
```

---

## Summary

**3 Tables Documented:**
- **disputes** - Core dispute records (8 columns)
- **dispute_categories** - Dispute reason classification (5 columns)
- **dispute_emails** - Email communication audit trail (5 columns)

**Key Features:**
- Dispute tracking with categorization
- Complete email audit trail
- SLA tracking via timestamps
- User and submission linkage
- Analytics-friendly schema

**Integration Points:**
- applicant_submissions (what's being disputed)
- users (who opened dispute)
- entries (screening context)
- properties (property-level metrics)

**Use Cases:**
- Challenge fraud false positives
- Contest income/asset calculations
- Report technical issues
- Request policy exceptions
- Track support team performance

**Business Value:**
- Customer satisfaction (respond to concerns)
- Quality assurance (identify systematic issues)
- Product improvement (common disputes → feature improvements)
- Compliance (audit trail for contested decisions)

---

**Related Documentation:**
- [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md) - applicant_submissions, users, entries
- [FRAUD_DETECTION_WORKFLOW.md](FRAUD_DETECTION_WORKFLOW.md) - fraud results being disputed
- [VERIFICATION_WORKFLOWS.md](VERIFICATION_WORKFLOWS.md) - income/asset results being disputed
- [REVIEW_QUEUE_SYSTEM.md](REVIEW_QUEUE_SYSTEM.md) - entry_log may track dispute resolutions

---

**Generated:** 2025-11-25
**Last Updated:** 2025-11-25
**Version:** 1.0
**Tables Documented:** 3 of 75 core tables
