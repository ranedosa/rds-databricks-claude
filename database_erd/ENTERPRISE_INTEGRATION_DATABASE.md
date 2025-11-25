# Enterprise Integration Database (Cross-Database Integration)

**Generated:** 2025-11-25
**Database:** enterprise_postgresql
**Tables Documented:** 5 enterprise integration tables
**Purpose:** Cross-database integration layer for enterprise PMS/CRM systems

---

## Overview

The **enterprise_postgresql** database serves as an integration layer between Snappt's fraud_postgresql database and external enterprise systems (Property Management Systems, CRMs, applicant tracking systems). This database enables bidirectional data sync while keeping enterprise-specific logic separate from core fraud detection.

**Key Functions:**
- **Cross-Database Links** - Maps enterprise data to fraud_postgresql entities
- **Enterprise Applicant Tracking** - Links applicants across systems
- **Property Integration** - Links properties to external systems
- **Email Delivery** - Manages transactional email via Postmark
- **Inbound Webhooks** - Receives events from external systems
- **Integration Configuration** - Stores enterprise system credentials

---

## ⚠️ CRITICAL: Cross-Database Relationships

This database is designed to **bridge multiple databases**. For multi-database queries, these are the key foreign key relationships:

### Cross-Database Links

```sql
-- ENTERPRISE → FRAUD DATABASE LINKS

enterprise_postgresql.enterprise_applicant.snappt_applicant_detail_id
    → fraud_postgresql.applicant_details.id

enterprise_postgresql.enterprise_property.snappt_property_id
    → fraud_postgresql.properties.id
```

### Multi-Database Query Patterns

**Example 1: Get all enterprise applicants with their Snappt screening results**
```sql
-- Run on fraud_postgresql database
SELECT
    ea.id as enterprise_applicant_id,
    ea.integration_id as external_id,
    ea.application_status,
    ad.id as snappt_applicant_detail_id,
    a.full_name,
    a.email,
    e.result as screening_result,
    e.status as screening_status
FROM enterprise_postgresql.enterprise_applicant ea
JOIN applicant_details ad ON ea.snappt_applicant_detail_id = ad.id
JOIN applicants a ON a.applicant_detail_id = ad.id
JOIN entries e ON a.entry_id = e.id
WHERE ea.inserted_at > NOW() - interval '30 days';
```

**Example 2: Get properties with enterprise integration status**
```sql
-- Run on fraud_postgresql database
SELECT
    p.name as property_name,
    p.short_id,
    ep.id as enterprise_property_id,
    ep.integration_details,
    ep.integration_activation_date,
    ep.integration_deactivation_date,
    COUNT(e.id) as total_entries
FROM properties p
LEFT JOIN enterprise_postgresql.enterprise_property ep
    ON ep.snappt_property_id = p.id
LEFT JOIN entries e ON e.id IN (
    SELECT entry_id FROM folders WHERE property_id = p.id
)
WHERE p.inserted_at > NOW() - interval '90 days'
GROUP BY p.id, p.name, p.short_id, ep.id, ep.integration_details,
         ep.integration_activation_date, ep.integration_deactivation_date;
```

---

## Table Inventory

### Cross-Database Integration (2 tables)
- **enterprise_applicant** - Links external applicants to Snappt applicant_details
- **enterprise_property** - Links external properties to Snappt properties

### Communication (2 tables)
- **email_delivery_attempts** - Transactional email delivery (Postmark)
- **inbound_webhooks** - Inbound webhooks from external systems

### Configuration (1 table)
- **enterprise_integration_configuration** - Enterprise system credentials and settings

---

## Detailed Table Documentation

## 1. ENTERPRISE_APPLICANT

**Purpose:** Links external enterprise system applicants to Snappt applicant records. Enables cross-database queries and status synchronization.

**Primary Key:** `id` (UUID)

**🔗 CRITICAL CROSS-DATABASE LINK:**
```
enterprise_applicant.snappt_applicant_detail_id → fraud_postgresql.applicant_details.id
```

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key (enterprise_postgresql) |
| enterprise_property_id | uuid | NO | FK → enterprise_property.id (same DB) |
| snappt_applicant_detail_id | uuid | NO | **CROSS-DB FK → fraud_postgresql.applicant_details.id** |
| integration_id | varchar | NO | Applicant ID in external system (Yardi, RealPage, etc.) |
| integration_details | jsonb | NO | Additional external system data |
| integration_ids | jsonb | YES | Multiple external IDs (default: {}) |
| final_status | varchar | YES | Screening final status (approved, denied, etc.) |
| denial_reason | varchar | YES | Reason for denial (if applicable) |
| application_status | varchar(50) | YES | External system application status |
| yardi_status_updated_at | timestamp | YES | Last Yardi status update timestamp |
| created_at | timestamp with time zone | YES | Record creation timestamp (default: now()) |
| inserted_at | timestamp with time zone | NO | TypeORM insertion timestamp (default: now()) |
| updated_at | timestamp with time zone | NO | Last update timestamp (default: now()) |

### Relationships
- **Belongs to:** enterprise_property (via enterprise_property_id, same DB)
- **CROSS-DB:** Links to fraud_postgresql.applicant_details (via snappt_applicant_detail_id)
- **CROSS-DB:** Transitively links to fraud_postgresql.applicants, entries

### Business Logic

**Integration Flow:**
1. External system (Yardi, RealPage) sends applicant data via webhook/API
2. Snappt creates applicant in fraud_postgresql:
   - applicant_details created
   - applicant created (linked to applicant_details)
3. enterprise_applicant created linking:
   - integration_id (external system ID)
   - snappt_applicant_detail_id (Snappt ID)
   - enterprise_property_id (property link)

**Status Synchronization:**
- Snappt screening completes → final_status updated
- If denied → denial_reason populated
- Status synced back to external system via API/webhook

**Integration IDs (JSONB):**
```json
{
  "yardi_prospect_code": "PROS-12345",
  "realpage_applicant_id": "APP-67890",
  "custom_tracking_id": "XYZ-999"
}
```

**Integration Details (JSONB):**
```json
{
  "external_system": "yardi",
  "property_code": "PROP-789",
  "move_in_date": "2024-06-01",
  "lease_term": 12,
  "monthly_rent": 2500,
  "applicant_type": "primary"
}
```

**Cross-Database Query Example:**
```sql
-- Get all applicants from Yardi with screening results
SELECT
    ea.integration_id as yardi_prospect_code,
    a.full_name,
    a.email,
    e.result as screening_result,
    ea.final_status,
    ea.application_status
FROM enterprise_applicant ea
JOIN applicant_details ad ON ea.snappt_applicant_detail_id = ad.id
JOIN applicants a ON a.applicant_detail_id = ad.id
JOIN entries e ON a.entry_id = e.id
WHERE ea.integration_details->>'external_system' = 'yardi';
```

---

## 2. ENTERPRISE_PROPERTY

**Purpose:** Links external enterprise system properties to Snappt properties. Enables property-level integration configuration.

**Primary Key:** `id` (UUID)

**🔗 CRITICAL CROSS-DATABASE LINK:**
```
enterprise_property.snappt_property_id → fraud_postgresql.properties.id
```

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key (enterprise_postgresql) |
| snappt_property_id | uuid | NO | **CROSS-DB FK → fraud_postgresql.properties.id** |
| enterprise_integration_id | uuid | YES | FK → enterprise_integration_configuration.id |
| integration_details | jsonb | YES | External system property data (default: {}) |
| configuration | jsonb | YES | Property-specific integration config (default: {}) |
| integration_activation_date | timestamp with time zone | YES | When integration was enabled |
| integration_deactivation_date | timestamp with time zone | YES | When integration was disabled (NULL = active) |
| integration_last_run | timestamp with time zone | YES | Last sync/poll timestamp |
| integration_last_error | varchar | YES | Last integration error message |
| created_at | timestamp with time zone | YES | Record creation timestamp (default: now()) |
| inserted_at | timestamp with time zone | NO | TypeORM insertion timestamp (default: now()) |
| updated_at | timestamp with time zone | NO | Last update timestamp (default: now()) |

### Relationships
- **Belongs to:** enterprise_integration_configuration (via enterprise_integration_id, same DB)
- **CROSS-DB:** Links to fraud_postgresql.properties (via snappt_property_id)
- **CROSS-DB:** Transitively links to fraud_postgresql.folders, entries, companies

### Business Logic

**Property Integration Setup:**
1. Property created in fraud_postgresql (properties table)
2. Enterprise integration configured
3. enterprise_property created linking:
   - snappt_property_id (Snappt property)
   - enterprise_integration_id (integration config)
   - integration_details (external property data)

**Integration Details (JSONB):**
```json
{
  "external_system": "yardi",
  "property_code": "PROP-789",
  "property_name": "Sunset Apartments",
  "management_company": "ABC Properties",
  "units": 250,
  "yardi_database": "ABC_PROP_DB"
}
```

**Configuration (JSONB):**
```json
{
  "sync_frequency": "15 minutes",
  "enabled_workflows": ["fraud_detection", "income_verification"],
  "notification_settings": {
    "send_to_pms": true,
    "include_documents": false
  },
  "custom_fields_mapping": {
    "screening_status": "CustomField1",
    "fraud_result": "CustomField2"
  }
}
```

**Active Integration Check:**
```sql
-- Properties with active enterprise integration
SELECT
    p.name,
    p.short_id,
    ep.integration_details->>'external_system' as system,
    ep.integration_activation_date,
    ep.integration_last_run
FROM properties p
JOIN enterprise_property ep ON ep.snappt_property_id = p.id
WHERE ep.integration_deactivation_date IS NULL;
```

**Cross-Database Query Example:**
```sql
-- Properties with integration health status
SELECT
    p.name as property_name,
    c.name as company_name,
    ep.integration_details->>'external_system' as integration_type,
    ep.integration_last_run,
    NOW() - ep.integration_last_run as time_since_last_sync,
    ep.integration_last_error,
    COUNT(e.id) as total_entries_last_30_days
FROM properties p
JOIN companies c ON p.company_id = c.id
LEFT JOIN enterprise_property ep ON ep.snappt_property_id = p.id
LEFT JOIN folders f ON f.property_id = p.id
LEFT JOIN entries e ON e.folder_id = f.id
    AND e.inserted_at > NOW() - interval '30 days'
WHERE ep.integration_deactivation_date IS NULL
GROUP BY p.name, c.name, ep.integration_details,
         ep.integration_last_run, ep.integration_last_error;
```

---

## 3. EMAIL_DELIVERY_ATTEMPTS

**Purpose:** Tracks transactional email delivery via Postmark API. Audit trail for all system-generated emails.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key (auto-generated) |
| postmark_template_id | varchar | NO | Postmark template identifier |
| payload | jsonb | NO | Email template data (merge variables) |
| recipients | array(varchar) | NO | Email recipient addresses (default: []) |
| email_type | varchar | NO | Email category (invite, result, reminder, etc.) |
| email_source | varchar | NO | Source system (snappt, enterprise, etc.) |
| response_status | integer | YES | HTTP status code from Postmark |
| response_data | jsonb | YES | Response from Postmark API |
| completed_at | timestamp with time zone | YES | When email delivery completed |
| created_at | timestamp with time zone | YES | Email request timestamp (default: now()) |
| updated_at | timestamp with time zone | YES | Last update timestamp (default: now()) |

### Relationships
- None (standalone email delivery log)

### Business Logic

**Email Types:**
- **invite** - Applicant screening invitation
- **result** - Screening result notification
- **reminder** - Document submission reminder
- **alert** - Fraud alert notification
- **status_update** - Application status change
- **report** - Scheduled report delivery

**Email Sources:**
- **snappt** - Core Snappt platform emails
- **enterprise** - Enterprise integration emails
- **yardi** - Yardi-specific notifications
- **custom** - Customer-specific templates

**Postmark Integration:**
- Postmark is a transactional email service
- Templates stored in Postmark
- payload contains template merge variables
- response_data contains Postmark delivery status

**Payload Example:**
```json
{
  "applicant_name": "John Smith",
  "property_name": "Sunset Apartments",
  "screening_url": "https://app.snappt.com/screen/abc-123",
  "expiration_date": "2024-06-15",
  "custom_message": "Please complete screening by June 15"
}
```

**Response Data Example:**
```json
{
  "MessageID": "pm-12345-67890",
  "SubmittedAt": "2024-05-01T10:30:00Z",
  "To": "applicant@example.com",
  "ErrorCode": 0,
  "Message": "OK"
}
```

**Email Delivery Monitoring:**
```sql
-- Failed email deliveries
SELECT
    email_type,
    email_source,
    recipients,
    response_status,
    response_data->>'Message' as error_message,
    created_at
FROM email_delivery_attempts
WHERE response_status >= 400
  AND created_at > NOW() - interval '24 hours'
ORDER BY created_at DESC;

-- Email delivery success rate
SELECT
    email_type,
    COUNT(*) as total_sent,
    COUNT(*) FILTER (WHERE response_status = 200) as delivered,
    COUNT(*) FILTER (WHERE response_status >= 400) as failed,
    COUNT(*) FILTER (WHERE response_status = 200) * 100.0 / COUNT(*) as success_rate
FROM email_delivery_attempts
WHERE created_at > NOW() - interval '7 days'
GROUP BY email_type
ORDER BY success_rate ASC;
```

---

## 4. INBOUND_WEBHOOKS

**Purpose:** Receives and processes webhooks from external systems. Queue for asynchronous webhook processing.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key (auto-generated) |
| source | varchar | NO | External system source (yardi, realpage, postmark, etc.) |
| event_type | varchar | YES | Event type from external system |
| external_event_id | varchar | YES | Event ID from external system |
| internal_event_id | uuid | YES | Snappt internal event ID (if created) |
| event_body | jsonb | YES | Full webhook payload |
| processed | boolean | YES | Whether webhook has been processed (default: false) |
| status_code | integer | YES | Processing status code |
| error_message | text | YES | Error message if processing failed |
| received_at | timestamp with time zone | YES | Webhook receipt timestamp (default: now()) |

### Relationships
- None (webhook queue table)

### Business Logic

**Webhook Processing Flow:**
1. External system sends webhook to Snappt endpoint
2. inbound_webhooks record created:
   - event_body stored (full payload)
   - processed = false
   - received_at = now()
3. Background worker processes webhook:
   - Parse event_body
   - Create/update records in fraud_postgresql or enterprise_postgresql
   - Set internal_event_id (reference to created/updated record)
   - Set processed = true
   - Set status_code (200 = success, 400/500 = error)
4. Webhook acknowledgment sent to external system

**Webhook Sources:**
- **yardi** - Yardi Voyager prospect updates, status changes
- **realpage** - RealPage applicant events
- **postmark** - Email delivery status updates (bounces, opens, clicks)
- **stripe** - Payment processing events
- **custom** - Custom enterprise integrations

**Event Types (Yardi Example):**
- **prospect.created** - New prospect/guest card
- **prospect.updated** - Prospect info changed
- **prospect.status_changed** - Application status updated
- **document.received** - Document uploaded in Yardi

**Event Body Example (Yardi Prospect Created):**
```json
{
  "event_id": "evt_yardi_12345",
  "event_type": "prospect.created",
  "timestamp": "2024-05-01T10:30:00Z",
  "property_code": "PROP-789",
  "prospect": {
    "prospect_code": "PROS-12345",
    "first_name": "John",
    "last_name": "Smith",
    "email": "john@example.com",
    "phone": "555-123-4567",
    "desired_move_in": "2024-06-01",
    "unit_type": "2BR-2BA"
  }
}
```

**Processing Status:**
- **status_code = 200** - Successfully processed
- **status_code = 400** - Invalid webhook data
- **status_code = 422** - Validation error (missing required fields)
- **status_code = 500** - Internal processing error

**Webhook Queue Monitoring:**
```sql
-- Unprocessed webhooks
SELECT
    source,
    event_type,
    received_at,
    NOW() - received_at as age
FROM inbound_webhooks
WHERE processed = false
ORDER BY received_at ASC;

-- Failed webhooks
SELECT
    source,
    event_type,
    status_code,
    error_message,
    received_at
FROM inbound_webhooks
WHERE processed = true AND status_code >= 400
ORDER BY received_at DESC
LIMIT 50;

-- Webhook processing latency
SELECT
    source,
    AVG(EXTRACT(EPOCH FROM (updated_at - received_at))) as avg_processing_seconds,
    MAX(EXTRACT(EPOCH FROM (updated_at - received_at))) as max_processing_seconds
FROM inbound_webhooks
WHERE processed = true
  AND received_at > NOW() - interval '24 hours'
GROUP BY source;
```

---

## 5. ENTERPRISE_INTEGRATION_CONFIGURATION

**Purpose:** Stores enterprise system credentials, endpoints, and configuration. Centralized integration settings.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| type | varchar | NO | Integration type (yardi, realpage, entrata, etc.) (default: '') |
| name | varchar | NO | Human-readable integration name (default: '') |
| integration_details | jsonb | YES | API credentials, endpoints, config (default: {}) |
| metadata | jsonb | YES | Additional metadata (default: {}) |
| inserted_at | timestamp with time zone | NO | Creation timestamp (default: now()) |
| updated_at | timestamp with time zone | NO | Last update timestamp (default: now()) |
| deleted_at | timestamp with time zone | YES | Soft delete timestamp (NULL = active) |

### Relationships
- **Has many:** enterprise_property (via enterprise_integration_id)

### Business Logic

**Integration Types:**
- **yardi** - Yardi Voyager PMS
- **realpage** - RealPage OneSite PMS
- **entrata** - Entrata PMS
- **appfolio** - AppFolio Property Manager
- **buildium** - Buildium property management
- **custom** - Custom enterprise integrations

**Integration Details (JSONB) - Yardi Example:**
```json
{
  "api_type": "soap",
  "wsdl_url": "https://yardi.example.com/itfwebservices?wsdl",
  "soap_endpoint": "https://yardi.example.com/itfwebservices",
  "username": "snappt_api_user",
  "password": "encrypted_password_here",
  "database_name": "CLIENT_PROD_DB",
  "platform": "Voyager",
  "server_name": "yardi-prod-01.yardipcx.com",
  "poll_rate_minutes": 15,
  "timeout_seconds": 30
}
```

**Integration Details (JSONB) - RealPage Example:**
```json
{
  "api_type": "rest",
  "base_url": "https://api.realpage.com/v1",
  "api_key": "rp_api_key_here",
  "client_id": "snappt_client_id",
  "client_secret": "encrypted_secret_here",
  "webhook_url": "https://api.snappt.com/webhooks/realpage",
  "webhook_secret": "webhook_verification_secret",
  "enabled_events": ["applicant.created", "applicant.status_changed"]
}
```

**Metadata (JSONB):**
```json
{
  "company_name": "ABC Property Management",
  "contact_email": "integrations@abcproperties.com",
  "activation_date": "2024-01-15",
  "billing_tier": "enterprise",
  "properties_count": 15,
  "monthly_volume": 500
}
```

**Active Integrations:**
```sql
-- All active enterprise integrations
SELECT
    id,
    type,
    name,
    metadata->>'company_name' as company,
    metadata->>'properties_count' as properties,
    inserted_at
FROM enterprise_integration_configuration
WHERE deleted_at IS NULL
ORDER BY type, name;
```

---

## Cross-Database Query Patterns

### Pattern 1: Full Applicant Journey (Enterprise → Fraud DB)

```sql
-- Complete applicant screening data across databases
SELECT
    -- Enterprise System Info
    ea.integration_id as external_applicant_id,
    ea.integration_details->>'external_system' as pms_system,
    ea.application_status as pms_status,

    -- Snappt Applicant Info
    a.full_name,
    a.email,
    a.phone,

    -- Screening Info
    e.short_id as screening_id,
    e.status as screening_status,
    e.result as screening_result,
    e.submission_time,
    e.report_complete_time,

    -- Property Info
    p.name as property_name,
    ep.integration_details->>'property_code' as external_property_code,

    -- Verification Results
    (SELECT result FROM fraud_results fr
     JOIN applicant_submissions asub ON fr.applicant_submission_id = asub.id
     WHERE asub.applicant_id = a.id LIMIT 1) as fraud_result,
    (SELECT review_eligibility FROM income_verification_results ivr
     JOIN applicant_submissions asub ON ivr.applicant_submission_id = asub.id
     WHERE asub.applicant_id = a.id LIMIT 1) as income_result

FROM enterprise_applicant ea
-- Cross-database joins
JOIN applicant_details ad ON ea.snappt_applicant_detail_id = ad.id
JOIN applicants a ON a.applicant_detail_id = ad.id
JOIN entries e ON a.entry_id = e.id
JOIN folders f ON e.folder_id = f.id
JOIN properties p ON f.property_id = p.id
LEFT JOIN enterprise_property ep ON ep.snappt_property_id = p.id
WHERE ea.inserted_at > NOW() - interval '7 days';
```

### Pattern 2: Property Integration Health

```sql
-- Property integration status and performance
SELECT
    p.name as property_name,
    p.short_id,
    c.name as company_name,

    -- Integration Status
    ep.id IS NOT NULL as has_enterprise_integration,
    eic.type as integration_type,
    eic.name as integration_name,
    ep.integration_activation_date,
    ep.integration_deactivation_date,
    CASE
        WHEN ep.integration_deactivation_date IS NULL THEN 'Active'
        ELSE 'Inactive'
    END as integration_status,

    -- Integration Health
    ep.integration_last_run,
    NOW() - ep.integration_last_run as time_since_last_sync,
    ep.integration_last_error,

    -- Volume Metrics
    COUNT(DISTINCT e.id) as total_entries,
    COUNT(DISTINCT e.id) FILTER (WHERE e.result = 'CLEAN') as clean_results,
    COUNT(DISTINCT e.id) FILTER (WHERE e.result = 'FRAUD') as fraud_results,

    -- Enterprise Applicants
    COUNT(DISTINCT ea.id) as enterprise_applicants

FROM properties p
JOIN companies c ON p.company_id = c.id
LEFT JOIN enterprise_property ep ON ep.snappt_property_id = p.id
LEFT JOIN enterprise_integration_configuration eic
    ON ep.enterprise_integration_id = eic.id
LEFT JOIN folders f ON f.property_id = p.id
LEFT JOIN entries e ON e.folder_id = f.id
    AND e.inserted_at > NOW() - interval '30 days'
LEFT JOIN applicants a ON a.entry_id = e.id
LEFT JOIN applicant_details ad ON a.applicant_detail_id = ad.id
LEFT JOIN enterprise_applicant ea ON ea.snappt_applicant_detail_id = ad.id
WHERE p.inserted_at > NOW() - interval '90 days'
GROUP BY p.id, p.name, p.short_id, c.name, ep.id, eic.type, eic.name,
         ep.integration_activation_date, ep.integration_deactivation_date,
         ep.integration_last_run, ep.integration_last_error;
```

### Pattern 3: Integration Performance Metrics

```sql
-- Cross-database integration performance
SELECT
    eic.type as integration_type,
    eic.name as integration_name,

    -- Properties Count
    COUNT(DISTINCT ep.id) as properties_count,

    -- Applicants Count
    COUNT(DISTINCT ea.id) as applicants_count,

    -- Screening Volume
    COUNT(DISTINCT e.id) as screenings_count,

    -- Processing Time
    AVG(EXTRACT(EPOCH FROM (e.report_complete_time - e.submission_time)) / 3600)
        as avg_hours_to_complete,

    -- Email Delivery
    COUNT(DISTINCT eda.id) as emails_sent,
    COUNT(DISTINCT eda.id) FILTER (WHERE eda.response_status = 200) as emails_delivered,

    -- Webhook Processing
    COUNT(DISTINCT iw.id) as webhooks_received,
    COUNT(DISTINCT iw.id) FILTER (WHERE iw.processed = true) as webhooks_processed

FROM enterprise_integration_configuration eic
LEFT JOIN enterprise_property ep ON ep.enterprise_integration_id = eic.id
LEFT JOIN enterprise_applicant ea ON ea.enterprise_property_id = ep.id
LEFT JOIN applicant_details ad ON ea.snappt_applicant_detail_id = ad.id
LEFT JOIN applicants a ON a.applicant_detail_id = ad.id
LEFT JOIN entries e ON a.entry_id = e.id
LEFT JOIN email_delivery_attempts eda
    ON eda.created_at > NOW() - interval '30 days'
LEFT JOIN inbound_webhooks iw
    ON iw.source = eic.type AND iw.received_at > NOW() - interval '30 days'
WHERE eic.deleted_at IS NULL
  AND (ea.inserted_at > NOW() - interval '30 days' OR ea.inserted_at IS NULL)
GROUP BY eic.id, eic.type, eic.name;
```

---

## Performance Considerations

### Indexes Recommended

```sql
-- enterprise_applicant: Cross-database joins
CREATE INDEX idx_enterprise_applicant_snappt_detail
  ON enterprise_applicant(snappt_applicant_detail_id);

CREATE INDEX idx_enterprise_applicant_property
  ON enterprise_applicant(enterprise_property_id);

CREATE INDEX idx_enterprise_applicant_integration_id
  ON enterprise_applicant(integration_id);

-- enterprise_property: Cross-database joins
CREATE INDEX idx_enterprise_property_snappt_property
  ON enterprise_property(snappt_property_id);

CREATE INDEX idx_enterprise_property_integration
  ON enterprise_property(enterprise_integration_id)
  WHERE integration_deactivation_date IS NULL;

-- email_delivery_attempts: Monitoring
CREATE INDEX idx_email_delivery_type_status
  ON email_delivery_attempts(email_type, response_status, created_at DESC);

-- inbound_webhooks: Processing queue
CREATE INDEX idx_inbound_webhooks_unprocessed
  ON inbound_webhooks(source, received_at)
  WHERE processed = false;

CREATE INDEX idx_inbound_webhooks_external_event
  ON inbound_webhooks(external_event_id);

-- JSONB indexes
CREATE INDEX idx_enterprise_applicant_integration_details_gin
  ON enterprise_applicant USING gin(integration_details);

CREATE INDEX idx_enterprise_property_integration_details_gin
  ON enterprise_property USING gin(integration_details);
```

---

## Summary

**5 Tables Documented:**
- **enterprise_applicant** - Cross-DB link to applicant_details
- **enterprise_property** - Cross-DB link to properties
- **email_delivery_attempts** - Postmark email tracking
- **inbound_webhooks** - External system webhooks
- **enterprise_integration_configuration** - Integration credentials

**🔗 Cross-Database Relationships:**
1. `enterprise_applicant.snappt_applicant_detail_id → applicant_details.id`
2. `enterprise_property.snappt_property_id → properties.id`

**Key Features:**
- Cross-database integration layer
- Enterprise PMS/CRM synchronization
- Transactional email delivery
- Inbound webhook processing
- Integration health monitoring
- Multi-database query patterns documented

**Use Cases:**
- Link external applicants to Snappt screenings
- Property-level integration configuration
- Status synchronization with external systems
- Email delivery tracking
- Webhook event processing
- Integration performance monitoring

---

**Related Documentation:**
- [INTEGRATION_LAYER.md](INTEGRATION_LAYER.md) - fraud_postgresql webhooks and Yardi
- [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md) - applicants, properties in fraud DB
- [REVIEW_QUEUE_SYSTEM.md](REVIEW_QUEUE_SYSTEM.md) - entry processing workflow

---

**Generated:** 2025-11-25
**Last Updated:** 2025-11-25
**Version:** 1.0
**Tables Documented:** 5 enterprise integration tables
**Database:** enterprise_postgresql
