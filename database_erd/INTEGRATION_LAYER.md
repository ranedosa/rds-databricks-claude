# Integration Layer - External System Communication

**Generated:** 2025-11-25
**Database:** fraud_postgresql (Production)
**Tables Documented:** 6 integration and webhook tables

---

## Overview

The Integration Layer manages external system communication for result delivery and Property Management System (PMS) integration. This system handles webhook notifications to customer systems, Yardi PMS bidirectional integration, and delivery reliability through retry logic and event tracking.

**Key Functions:**
- **Webhook Delivery** - Send screening results to customer endpoints
- **Retry Logic** - Automatic retry with exponential backoff
- **Yardi Integration** - Bidirectional sync with Yardi Voyager PMS
- **Poll-Based Import** - Import prospects from Yardi
- **Result Export** - Send screening results back to Yardi
- **Event Tracking** - Complete audit trail of integration events

---

## Table Inventory

### Webhook System (2 tables)
- **webhooks** - Webhook endpoint configuration
- **webhook_delivery_attempts** - Delivery attempts, retries, and responses

### Yardi PMS Integration (4 tables)
- **yardi_integrations** - Yardi SOAP endpoint configuration
- **yardi_properties** - Property-level Yardi integration settings
- **yardi_entries** - Links Snappt entries to Yardi prospects
- **yardi_invites** - Screening invites imported from Yardi

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ OUTBOUND: Webhook Result Delivery                          │
└─────────────────────────────────────────────────────────────┘

Entry Completed → webhooks (find endpoints for events)
                      ↓
                  Build Payload (entry results, applicant info)
                      ↓
                  webhook_delivery_attempts (POST to customer URL)
                      ↓
                  Success (2xx) → Done
                  Failure (4xx/5xx) → Retry with backoff

┌─────────────────────────────────────────────────────────────┐
│ INBOUND: Yardi Prospect Import                             │
└─────────────────────────────────────────────────────────────┘

yardi_integrations (SOAP connection config)
        ↓
Poll Yardi API (every N minutes based on poll_rate)
        ↓
Fetch new prospects → yardi_invites (store prospect data)
        ↓
Create Snappt entry → yardi_entries (link prospect to entry)
        ↓
Applicant completes screening
        ↓
Send results back to Yardi
```

---

## Detailed Table Documentation

## 1. WEBHOOKS

**Purpose:** Webhook endpoint configuration for customers. Defines where to send event notifications.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| method | varchar(255) | YES | HTTP method (typically "POST") |
| url | varchar(255) | YES | Customer webhook endpoint URL |
| headers | array(jsonb) | NO | Custom HTTP headers (default: []) |
| events | array(varchar) | NO | Event types to trigger webhook (default: []) |
| is_active | boolean | YES | Webhook enabled/disabled (default: true) |
| api_key_id | uuid | NO | **FK → api_keys.id** |
| inserted_at | timestamp | NO | Webhook creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** api_keys (via api_key_id)
- **Has many:** webhook_delivery_attempts

### Business Logic

**Webhook Events:**
- **entry.completed** - Entry screening completed
- **entry.in_review** - Entry assigned to human reviewer
- **entry.result_updated** - Entry result changed
- **fraud.detected** - Fraud detected in documents
- **income.verified** - Income verification completed
- **asset.verified** - Asset verification completed
- **identity.verified** - Identity verification completed

**HTTP Method:**
- Typically "POST"
- Could support "PUT" for idempotent operations

**Custom Headers (JSONB Array):**
```json
[
  {"name": "Authorization", "value": "Bearer customer_secret_token"},
  {"name": "X-Custom-Header", "value": "custom_value"},
  {"name": "Content-Type", "value": "application/json"}
]
```

**Event Filtering:**
- Customers subscribe to specific events
- Only subscribed events trigger webhooks
- Example: `['entry.completed', 'fraud.detected']`

**Active/Inactive:**
- `is_active = true` - Webhook will be triggered
- `is_active = false` - Webhook disabled (config preserved)

**Multiple Webhooks:**
- One customer (api_key) can have multiple webhooks
- Different webhooks for different events
- Example: One for completions, one for alerts

---

## 2. WEBHOOK_DELIVERY_ATTEMPTS

**Purpose:** Tracks webhook delivery attempts, retries, responses, and failures. Complete audit trail of integration events.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key (auto-generated) |
| webhook_id | uuid | NO | **FK → webhooks.id** |
| payload | jsonb | NO | JSON payload sent to customer |
| response_data | jsonb | NO | Response body from customer endpoint |
| response_status | integer | NO | HTTP status code (200, 404, 500, etc.) |
| created_at | timestamp with time zone | YES | Delivery attempt timestamp (default: now()) |

### Relationships
- **Belongs to:** webhooks (via webhook_id)

### Business Logic

**Delivery Attempt Flow:**
1. Event occurs (entry completed)
2. System finds webhooks subscribed to event
3. Build payload with entry data
4. POST payload to webhook URL
5. Record delivery attempt:
   - payload (what was sent)
   - response_status (HTTP code)
   - response_data (response body)
   - created_at (timestamp)

**HTTP Status Interpretation:**
- **2xx (200-299)** - Success, no retry
- **4xx (400-499)** - Client error, no retry (invalid endpoint, auth failure)
- **5xx (500-599)** - Server error, retry with backoff

**Retry Logic (Conceptual):**
```
Attempt 1: Immediate
Attempt 2: Wait 1 minute
Attempt 3: Wait 5 minutes
Attempt 4: Wait 15 minutes
Attempt 5: Wait 1 hour
Attempt 6+: Give up, alert customer
```

**Payload Structure Example:**
```json
{
  "event": "entry.completed",
  "entry_id": "abc-123",
  "short_id": "SNAP-12345",
  "property_id": "prop-456",
  "result": "CLEAN",
  "applicant": {
    "full_name": "John Smith",
    "email": "john@example.com"
  },
  "fraud_result": "CLEAN",
  "income_result": "APPROVED",
  "asset_result": "APPROVED",
  "identity_result": "APPROVED",
  "completed_at": "2024-01-15T10:30:00Z",
  "report_url": "https://app.snappt.com/reports/abc-123"
}
```

**Response Data Examples:**
```json
// Success
{
  "status": "received",
  "message": "Screening result processed successfully"
}

// Error
{
  "error": "Invalid authentication token",
  "code": "AUTH_FAILED"
}
```

**Monitoring & Debugging:**
```sql
-- Failed deliveries in last 24 hours
SELECT
    w.url,
    wda.response_status,
    wda.response_data,
    COUNT(*) as failures
FROM webhook_delivery_attempts wda
JOIN webhooks w ON wda.webhook_id = w.id
WHERE wda.created_at > NOW() - interval '24 hours'
  AND wda.response_status >= 400
GROUP BY w.url, wda.response_status, wda.response_data
ORDER BY failures DESC;

-- Webhook reliability by endpoint
SELECT
    w.url,
    COUNT(*) as total_attempts,
    COUNT(*) FILTER (WHERE wda.response_status BETWEEN 200 AND 299) as successes,
    COUNT(*) FILTER (WHERE wda.response_status >= 400) as failures,
    COUNT(*) FILTER (WHERE wda.response_status BETWEEN 200 AND 299) * 100.0 / COUNT(*) as success_rate
FROM webhooks w
JOIN webhook_delivery_attempts wda ON w.id = wda.webhook_id
WHERE wda.created_at > NOW() - interval '7 days'
GROUP BY w.url
ORDER BY success_rate ASC;
```

---

## 3. YARDI_INTEGRATIONS

**Purpose:** Yardi Voyager SOAP API connection configuration. Stores credentials and endpoints for Yardi PMS integration.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| wsdl_url | varchar(255) | YES | Yardi WSDL URL (SOAP service definition) |
| soap_endpoint | varchar(255) | YES | Yardi SOAP endpoint URL |
| user_name | varchar(255) | YES | Yardi API username |
| password | varchar(255) | YES | Yardi API password (encrypted) |
| database_name | varchar(255) | YES | Yardi database name |
| platform | varchar(255) | YES | Yardi platform (Voyager, etc.) |
| server_name | varchar(255) | YES | Yardi server name |
| activation_date | timestamp | YES | When integration was activated |
| deactivation_date | timestamp | YES | When integration was deactivated (NULL = active) |
| alias | varchar(255) | YES | Customer-friendly integration name |
| custom_message | varchar(255) | YES | Custom message for applicants |
| poll_rate | integer | YES | Minutes between polls for new prospects |
| attachment_type | varchar(255) | YES | How to handle document attachments |
| short_id | varchar(255) | YES | Human-readable integration ID |
| inserted_at | timestamp | NO | Integration creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Has many:** yardi_properties (via yardi_integration_id)
- **Has many:** yardi_invites (via yardi_integration_id)

### Business Logic

**Yardi Integration Types:**
Yardi Voyager is a Property Management System (PMS) used by many large property management companies. Integration allows:
- **Inbound:** Import prospects from Yardi → Create Snappt entries
- **Outbound:** Send screening results back to Yardi

**SOAP/WSDL Configuration:**
- **wsdl_url** - SOAP service definition URL
- **soap_endpoint** - Actual SOAP API endpoint
- **Credentials** - user_name, password for authentication
- **database_name** - Yardi customer's database instance

**Poll-Based Import:**
- `poll_rate` defines minutes between imports (e.g., 15 = every 15 minutes)
- Snappt polls Yardi API for new prospects
- New prospects → yardi_invites → Snappt entries

**Active/Inactive:**
- Active: `activation_date` set, `deactivation_date` NULL
- Inactive: `deactivation_date` set

**Attachment Handling:**
- `attachment_type` options:
  - "email" - Documents emailed separately
  - "api" - Documents fetched via API
  - "manual" - Applicant uploads manually

**Example Integration:**
```
alias='ABC Property Management Yardi'
platform='Voyager'
server_name='yardi-prod-01.yardipcx.com'
database_name='ABC_PROP_DB'
poll_rate=15  (poll every 15 minutes)
activation_date='2024-01-01'
deactivation_date=NULL  (currently active)
```

---

## 4. YARDI_PROPERTIES

**Purpose:** Property-level Yardi integration configuration. Links Snappt properties to Yardi integration instances.

**Primary Key:** `property_id` (UUID, FK to properties)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| property_id | uuid | NO | **PK, FK → properties.id** |
| yardi_integration_id | uuid | YES | **FK → yardi_integrations.id** |
| yardi_property_id | varchar(255) | YES | Property ID in Yardi system |
| activation_date | timestamp | YES | When Yardi enabled for this property |
| deactivation_date | timestamp | YES | When Yardi disabled (NULL = active) |
| last_poll_run | timestamp | YES | Last time prospects were imported |
| submit_date | timestamp | YES | Last time results were submitted to Yardi |
| inserted_at | timestamp | NO | Record creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** properties (via property_id)
- **Belongs to:** yardi_integrations (via yardi_integration_id)

### Business Logic

**Property-Level Activation:**
- One yardi_integration can serve multiple properties
- Each property can enable/disable Yardi independently
- `yardi_property_id` maps Snappt property to Yardi property

**Polling Workflow:**
1. Cron job runs every `poll_rate` minutes
2. For each active yardi_property (deactivation_date = NULL):
   - Call Yardi API with yardi_property_id
   - Fetch prospects since last_poll_run
   - Create yardi_invites for new prospects
   - Update last_poll_run timestamp

**Result Submission:**
- When entry completes, check if property has Yardi integration
- If yes, send results to Yardi via SOAP API
- Update submit_date timestamp

**Active Status:**
```sql
-- Active Yardi properties
SELECT p.name, yp.yardi_property_id
FROM yardi_properties yp
JOIN properties p ON yp.property_id = p.id
WHERE yp.deactivation_date IS NULL;
```

**Integration Health:**
```sql
-- Properties overdue for polling
SELECT
    p.name,
    yp.last_poll_run,
    EXTRACT(EPOCH FROM (NOW() - yp.last_poll_run)) / 60 as minutes_since_last_poll,
    yi.poll_rate as expected_poll_minutes
FROM yardi_properties yp
JOIN properties p ON yp.property_id = p.id
JOIN yardi_integrations yi ON yp.yardi_integration_id = yi.id
WHERE yp.deactivation_date IS NULL
  AND yp.last_poll_run < NOW() - (yi.poll_rate * 2 || ' minutes')::interval;
```

---

## 5. YARDI_ENTRIES

**Purpose:** Links Snappt entries to Yardi prospects. Tracks which entries originated from Yardi.

**Primary Key:** `entry_id` (UUID, FK to entries)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| entry_id | uuid | NO | **PK, FK → entries.id** |
| prospect_code | varchar(255) | YES | Yardi prospect/guest card code |
| inserted_at | timestamp | NO | Link creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** entries (via entry_id)
- **Implicitly links to:** yardi_invites (via prospect_code)

### Business Logic

**Purpose:**
- When prospect imported from Yardi → yardi_invite created
- When entry created for that prospect → yardi_entry created
- Links Snappt entry back to Yardi prospect

**Prospect Code:**
- Unique identifier in Yardi system (guest card code)
- Used to update prospect record in Yardi with screening results

**Result Submission Flow:**
```
1. Entry completed
2. Check if yardi_entries record exists
3. If yes, get prospect_code
4. Lookup yardi_integration via property
5. Call Yardi SOAP API: UpdateProspect(prospect_code, screening_results)
6. Update yardi_properties.submit_date
```

**Tracking Yardi-Originated Entries:**
```sql
-- Percentage of entries from Yardi
SELECT
    COUNT(*) FILTER (WHERE ye.entry_id IS NOT NULL) as yardi_entries,
    COUNT(*) as total_entries,
    COUNT(*) FILTER (WHERE ye.entry_id IS NOT NULL) * 100.0 / COUNT(*) as pct_from_yardi
FROM entries e
LEFT JOIN yardi_entries ye ON e.id = ye.entry_id
WHERE e.inserted_at > NOW() - interval '30 days';
```

---

## 6. YARDI_INVITES

**Purpose:** Screening invites imported from Yardi. Stores prospect data before entry creation.

**Primary Key:** `id` (UUID) + `yardi_integration_id` (Composite)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key (part of composite) |
| yardi_integration_id | uuid | NO | **PK, FK → yardi_integrations.id** |
| prospect_code | varchar(255) | YES | Yardi prospect/guest card code |
| yardi_property_id | varchar(255) | YES | Yardi property ID |
| snappt_property_id | varchar(255) | YES | Snappt property short_id |
| email | varchar(255) | YES | Applicant email |
| first_name | varchar(255) | YES | Applicant first name |
| last_name | varchar(255) | YES | Applicant last name |
| inserted_at | timestamp | NO | Import timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** yardi_integrations (via yardi_integration_id)
- **Implicitly references:** properties (via snappt_property_id)

### Business Logic

**Import Flow:**
1. Polling job runs for yardi_property
2. Call Yardi API: GetNewProspects(yardi_property_id, since=last_poll_run)
3. For each new prospect:
   ```
   yardi_invites record created:
     - prospect_code (from Yardi)
     - yardi_property_id (from Yardi)
     - snappt_property_id (mapped from yardi_property_id)
     - email, first_name, last_name (applicant info)
   ```
4. Entry creation triggered:
   ```
   - Create entry for snappt_property
   - Create applicant with email/name
   - Send invite to applicant
   - Create yardi_entries link
   ```

**Invite to Entry Conversion:**
```sql
-- Invites not yet converted to entries
SELECT
    yi.prospect_code,
    yi.email,
    yi.first_name,
    yi.last_name,
    yi.inserted_at
FROM yardi_invites yi
LEFT JOIN yardi_entries ye ON yi.prospect_code = ye.prospect_code
WHERE ye.entry_id IS NULL
  AND yi.inserted_at > NOW() - interval '7 days';
```

**Multiple Applicants:**
- One prospect_code may have multiple applicants (roommates)
- yardi_invites table stores each applicant separately
- All link to same Yardi prospect

---

## Integration Workflows

### Workflow 1: Webhook Result Delivery

```
┌─────────────────────────────────────────────────────────┐
│ 1. ENTRY COMPLETION                                     │
└─────────────────────────────────────────────────────────┘
Entry status → 'completed'
Entry result → 'CLEAN'
entry_report generated

┌─────────────────────────────────────────────────────────┐
│ 2. FIND WEBHOOKS                                        │
└─────────────────────────────────────────────────────────┘
Query webhooks:
  WHERE api_key_id = entry.property.company.api_key_id
    AND is_active = true
    AND 'entry.completed' = ANY(events)

Found 2 webhooks:
  - Customer internal system
  - Customer CRM

┌─────────────────────────────────────────────────────────┐
│ 3. BUILD PAYLOAD                                        │
└─────────────────────────────────────────────────────────┘
payload = {
  "event": "entry.completed",
  "entry_id": "abc-123",
  "result": "CLEAN",
  "applicant": {...},
  "report_url": "..."
}

┌─────────────────────────────────────────────────────────┐
│ 4. DELIVER TO EACH WEBHOOK                             │
└─────────────────────────────────────────────────────────┘
For each webhook:
  POST webhook.url
  Headers: webhook.headers
  Body: payload

  webhook_delivery_attempts created:
    - webhook_id
    - payload (stored)
    - response_status (200, 500, etc.)
    - response_data (response body)
    - created_at (now)

┌─────────────────────────────────────────────────────────┐
│ 5. RETRY ON FAILURE                                     │
└─────────────────────────────────────────────────────────┘
If response_status >= 500:
  Schedule retry (exponential backoff)
  Create new webhook_delivery_attempts record
  Repeat until success or max attempts
```

---

### Workflow 2: Yardi Prospect Import

```
┌─────────────────────────────────────────────────────────┐
│ 1. POLLING CRON JOB                                     │
└─────────────────────────────────────────────────────────┘
Every yardi_integration.poll_rate minutes:
  Find active yardi_properties (deactivation_date = NULL)

┌─────────────────────────────────────────────────────────┐
│ 2. CALL YARDI API                                       │
└─────────────────────────────────────────────────────────┘
For each yardi_property:
  SOAP request to yardi_integration.soap_endpoint:
    GetNewProspects(
      PropertyCode: yardi_property.yardi_property_id,
      StartDate: yardi_property.last_poll_run
    )

  Response: [{
    ProspectCode: "PROS-12345",
    PropertyCode: "PROP-789",
    FirstName: "John",
    LastName: "Smith",
    Email: "john@example.com"
  }]

┌─────────────────────────────────────────────────────────┐
│ 3. CREATE YARDI_INVITES                                │
└─────────────────────────────────────────────────────────┘
For each prospect in response:
  INSERT INTO yardi_invites (
    yardi_integration_id,
    prospect_code,
    yardi_property_id,
    snappt_property_id (lookup from mapping),
    email,
    first_name,
    last_name
  )

┌─────────────────────────────────────────────────────────┐
│ 4. CREATE SNAPPT ENTRIES                               │
└─────────────────────────────────────────────────────────┘
For each yardi_invite:
  1. Find/create property (via snappt_property_id)
  2. Create entry for property
  3. Create applicant with email/name
  4. Create yardi_entries link (entry_id, prospect_code)
  5. Send invite email to applicant

┌─────────────────────────────────────────────────────────┐
│ 5. APPLICANT COMPLETES SCREENING                       │
└─────────────────────────────────────────────────────────┘
Applicant uploads documents
ML/AI analysis runs
Review completed
Entry result determined

┌─────────────────────────────────────────────────────────┐
│ 6. SEND RESULTS TO YARDI                               │
└─────────────────────────────────────────────────────────┘
Check if yardi_entries record exists
If yes:
  SOAP request to yardi_integration.soap_endpoint:
    UpdateProspectScreening(
      ProspectCode: yardi_entry.prospect_code,
      ScreeningStatus: "Completed",
      FraudResult: "Clean",
      IncomeResult: "Approved",
      ReportURL: "https://app.snappt.com/reports/..."
    )

  Update yardi_properties.submit_date = NOW()
```

---

## Performance Considerations

### Indexes Recommended

```sql
-- webhooks: Event lookups
CREATE INDEX idx_webhooks_api_key_active
  ON webhooks(api_key_id, is_active)
  WHERE is_active = true;

CREATE INDEX idx_webhooks_events_gin
  ON webhooks USING gin(events);

-- webhook_delivery_attempts: Delivery tracking
CREATE INDEX idx_webhook_delivery_attempts_webhook
  ON webhook_delivery_attempts(webhook_id, created_at DESC);

CREATE INDEX idx_webhook_delivery_attempts_status
  ON webhook_delivery_attempts(response_status, created_at DESC)
  WHERE response_status >= 400;

-- yardi_properties: Active integrations
CREATE INDEX idx_yardi_properties_integration
  ON yardi_properties(yardi_integration_id)
  WHERE deactivation_date IS NULL;

CREATE INDEX idx_yardi_properties_poll_overdue
  ON yardi_properties(last_poll_run)
  WHERE deactivation_date IS NULL;

-- yardi_entries: Prospect lookups
CREATE INDEX idx_yardi_entries_prospect
  ON yardi_entries(prospect_code);

-- yardi_invites: Invite processing
CREATE INDEX idx_yardi_invites_integration
  ON yardi_invites(yardi_integration_id, inserted_at DESC);

CREATE INDEX idx_yardi_invites_prospect
  ON yardi_invites(prospect_code);
```

---

## Business Metrics & KPIs

### Webhook Reliability

```sql
-- Webhook success rates by endpoint
SELECT
    w.url,
    w.is_active,
    COUNT(wda.id) as total_attempts,
    COUNT(*) FILTER (WHERE wda.response_status BETWEEN 200 AND 299) as successes,
    COUNT(*) FILTER (WHERE wda.response_status >= 400) as failures,
    AVG(CASE WHEN wda.response_status BETWEEN 200 AND 299 THEN 1 ELSE 0 END) * 100 as success_rate
FROM webhooks w
LEFT JOIN webhook_delivery_attempts wda ON w.id = wda.webhook_id
WHERE wda.created_at > NOW() - interval '7 days'
GROUP BY w.url, w.is_active
ORDER BY success_rate ASC;
```

### Yardi Integration Health

```sql
-- Properties with stale polling
SELECT
    p.name,
    yp.last_poll_run,
    NOW() - yp.last_poll_run as time_since_poll,
    yi.poll_rate as expected_minutes
FROM yardi_properties yp
JOIN properties p ON yp.property_id = p.id
JOIN yardi_integrations yi ON yp.yardi_integration_id = yi.id
WHERE yp.deactivation_date IS NULL
  AND yp.last_poll_run < NOW() - (yi.poll_rate * 2 || ' minutes')::interval;

-- Yardi invite conversion rate
SELECT
    COUNT(*) as total_invites,
    COUNT(ye.entry_id) as converted_to_entries,
    COUNT(ye.entry_id) * 100.0 / COUNT(*) as conversion_rate
FROM yardi_invites yi
LEFT JOIN yardi_entries ye ON yi.prospect_code = ye.prospect_code
WHERE yi.inserted_at > NOW() - interval '30 days';
```

---

## Security Considerations

### Webhook Security

**Outbound Webhooks:**
- HTTPS required for webhook URLs
- Custom headers support authentication tokens
- Payload contains only necessary data (no PII overexposure)
- Response data logged for debugging

**Retry Limits:**
- Max retry attempts prevent infinite loops
- Failed webhooks alert customer
- Manual intervention for persistent failures

### Yardi Integration Security

**Credentials:**
- Passwords encrypted at rest
- SOAP credentials never logged
- Secure credential rotation supported

**Data Transmission:**
- TLS/HTTPS for all Yardi API calls
- Prospect data validated before entry creation
- PII handling compliant with regulations

---

## Summary

**6 Tables Documented:**
- **webhooks** - Customer endpoint configuration
- **webhook_delivery_attempts** - Delivery tracking with retries
- **yardi_integrations** - Yardi SOAP API configuration
- **yardi_properties** - Property-level Yardi settings
- **yardi_entries** - Links entries to Yardi prospects
- **yardi_invites** - Imported prospect data

**Key Features:**
- Webhook result delivery with retry logic
- Event-based webhook triggering
- Yardi PMS bidirectional integration
- Poll-based prospect import
- Automatic entry creation from Yardi
- Result submission back to Yardi
- Complete audit trail of integration events

**Integration Points:**
- Properties (Yardi property mapping)
- Entries (webhook events, Yardi links)
- API Keys (webhook authentication)
- Entry Reports (webhook payloads)

**Use Cases:**
- Real-time result delivery to customer systems
- Automated prospect import from Yardi
- Seamless PMS workflow integration
- Integration reliability monitoring
- Debugging failed deliveries

---

**Next Documentation:**
- enterprise_postgresql (cross-database integration)
- Supporting Systems (remaining tables)

**See Also:**
- [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md) - properties, entries tables
- [REVIEW_QUEUE_SYSTEM.md](REVIEW_QUEUE_SYSTEM.md) - entry completion triggers webhooks
- [FEATURES_CONFIGURATION.md](FEATURES_CONFIGURATION.md) - webhook feature flags

---

**Generated:** 2025-11-25
**Last Updated:** 2025-11-25
**Version:** 1.0
**Tables Documented:** 6 of 75 core tables
