# Database Schema Summary - Entity Relationship Documentation

**Generated:** 2025-11-19
**Source:** RDS PostgreSQL Databases via MCP Connections

## Overview

This document summarizes the schema structure for 7 PostgreSQL databases connected via MCP. The databases support various aspects of the Snappt fraud detection and verification platform.

---

## Database Inventory

### 1. **fraud_postgresql** (Production Fraud Database)
**Status:** ✅ Active - Largest schema
**Tables:** 155 tables
**Purpose:** Core fraud detection application database

**Key Table Groups:**
- **Applicant Management**: `applicants`, `applicant_details`, `applicant_submissions`
- **Document Processing**: `proof`, `applicant_submission_document_sources`
- **Fraud Detection**: `fraud_submissions`, `fraud_reviews`, `fraud_results`, `fraud_document_reviews`
- **Income Verification**: `income_verification_submissions`, `income_verification_reviews`, `income_verification_results`
- **Asset Verification**: `asset_verification_submissions`, `asset_verification_reviews`, `asset_verification_results`
- **Identity Verification**: `id_verifications`
- **Rent Verification**: `rent_verifications`, `rent_verification_events`
- **Property & Company Management**: `properties`, `companies`, `owners`, `property_owners`
- **User Management**: `users`, `team`, `role`, `invitations`
- **Review Workflow**: `entries`, `folders`, `review_items`, `reviewer_queue`, `entry_log`
- **Integrations**: `yardi_integrations`, `yardi_properties`, `yardi_entries`, `webhooks`
- **Disputes**: `disputes`, `dispute_categories`, `dispute_emails`
- **Features**: `features`, `property_features`, `user_features`
- **Background Jobs**: `oban_jobs`, `oban_peers`
- **Deleted Records**: Multiple `deleted_*` tables for soft deletes/audit
- **Frequent Flyer Detection**: `frequent_flyer_variations`, `frequent_flyer_matched_confidences`

**Notable Characteristics:**
- Uses UUID primary keys extensively
- Implements soft deletes with dedicated backup tables
- Complex review and workflow management system
- Multiple verification types (fraud, income, asset, identity, rent)
- Integration with external systems (Yardi, webhooks)

---

### 2. **av_postgresql** (Automated Validation Database)
**Status:** ⚠️ Minimal - Schema migration only
**Tables:** 1 table
**Purpose:** Automated validation services

**Tables:**
- `schema_migrations` - Database migration tracking only

**Analysis:** This database appears to be either newly initialized or the tables are in a different schema. Only migration tracking table exists in public schema.

---

### 3. **dp_income_validation** (Document Processing - Income Validation)
**Status:** ⚠️ Empty
**Tables:** 0 tables in public schema
**Purpose:** Income validation document processing

**Analysis:** No tables found in public schema. Tables may exist in a different schema or database is not yet populated.

---

### 4. **dp_ai_services** (Document Processing - AI Services)
**Status:** ✅ Active - Small schema
**Tables:** 2 tables
**Purpose:** AI-powered document processing services

**Tables:**
- `alembic_version` - Database migration tracking (Alembic/Python)
- `checkpoint_analytics_view` - AI agent execution analytics
  - Tracks thread_id, agent_type, variant_name
  - Records execution duration, status, error messages
  - Created timestamp tracking

**Notable Characteristics:**
- Uses Python/Alembic for migrations (vs Elixir/Ecto in fraud DB)
- Analytics-focused schema for AI agent monitoring
- Lightweight structure focused on ML/AI workflow tracking

---

### 5. **dp_document_intelligence** (Document Processing - Document Intelligence)
**Status:** ⚠️ Empty
**Tables:** 0 tables in public schema
**Purpose:** Document intelligence processing

**Analysis:** No tables found in public schema. May use a different schema or be in development.

---

### 6. **dp_inception_fraud** (Document Processing - Inception Fraud)
**Status:** ⚠️ Empty
**Tables:** 0 tables in public schema
**Purpose:** Advanced fraud detection at inception

**Analysis:** No tables found in public schema. May use a different schema or be in development.

---

### 7. **enterprise_postgresql** (Enterprise Services)
**Status:** ✅ Active - Medium schema
**Tables:** 6 tables
**Purpose:** Enterprise integration and communication services

**Tables:**
- `email_delivery_attempts` - Email delivery tracking and logging
  - Postmark template integration
  - Payload and response tracking
  - Status codes and completion timestamps

- `enterprise_applicant` - Enterprise applicant management
  - Links to snappt_applicant_detail_id
  - Integration details and IDs (jsonb)
  - Application status tracking
  - Yardi status updates
  - Final status and denial reasons

- `enterprise_integration_configuration` - Integration configuration management
  - Type and name fields
  - Integration details (jsonb)
  - Metadata (jsonb)
  - Soft delete support (deleted_at)

- `enterprise_property` - Enterprise property management
  - Links to snappt_property_id
  - Integration details and configuration (jsonb)
  - Activation/deactivation dates
  - Last run timestamps and error tracking

- `inbound_webhooks` - Webhook event processing
  - Source and event type tracking
  - External and internal event IDs
  - Event body (jsonb)
  - Processing status and error handling

- `migrations` - Database migration tracking (TypeORM)
- `typeorm_metadata` - TypeORM framework metadata

**Notable Characteristics:**
- Uses TypeScript/TypeORM for migrations and ORM
- Heavy use of JSONB for flexible configuration storage
- Links between enterprise system and core Snappt systems
- Bidirectional webhook communication
- Email delivery tracking and retry logic

---

## Cross-Database Relationships

### Key Integration Points:

1. **fraud_postgresql ↔ enterprise_postgresql**
   - `enterprise_applicant.snappt_applicant_detail_id` → `fraud_postgresql.applicant_details.id`
   - `enterprise_property.snappt_property_id` → `fraud_postgresql.properties.id`

2. **Document Processing Databases**
   - `dp_income_validation`, `dp_document_intelligence`, `dp_inception_fraud` appear to be separate microservices
   - Likely communicate via events/APIs rather than direct DB relationships
   - `dp_ai_services` provides analytics for AI-powered document processing

3. **Automated Validation**
   - `av_postgresql` likely integrates with fraud detection workflow
   - May contain tables in non-public schema

---

## Technology Stack

### Database Migrations & ORMs:
- **Elixir/Phoenix + Ecto**: fraud_postgresql (primary application)
- **Python + Alembic**: dp_ai_services (AI/ML services)
- **TypeScript + TypeORM**: enterprise_postgresql (enterprise integrations)

### Key Patterns:
- **UUID Primary Keys**: Used consistently across all active databases
- **JSONB for Flexibility**: Extensive use for configuration and metadata
- **Soft Deletes**: Implemented via deleted_at timestamps and backup tables
- **Audit Trails**: audit_transaction_event table in fraud DB
- **Background Jobs**: Oban (Elixir) for async processing
- **Event Sourcing**: webhook_delivery_attempts, inbound_webhooks

---

## Table Count Summary

| Database | Table Count | Status |
|----------|-------------|--------|
| fraud_postgresql | 155 | Active - Full schema |
| av_postgresql | 1 | Minimal - Migration only |
| dp_income_validation | 0 | Empty/Different schema |
| dp_ai_services | 2 | Active - Analytics |
| dp_document_intelligence | 0 | Empty/Different schema |
| dp_inception_fraud | 0 | Empty/Different schema |
| enterprise_postgresql | 6 | Active - Integration layer |
| **TOTAL** | **164** | |

---

## ERD Recommendations

### High Priority ERDs:

1. **Core Fraud Detection Flow**
   - applicants → applicant_submissions → fraud_submissions → fraud_reviews
   - Document flow: proof → applicant_submission_document_sources

2. **Verification Workflows**
   - Income: income_verification_submissions → income_verification_reviews
   - Asset: asset_verification_submissions → asset_verification_reviews
   - Identity: id_verifications → applicants
   - Rent: rent_verifications → rent_verification_events

3. **Review & Queue Management**
   - entries → folders → properties
   - review_items → reviewer_queue → users
   - entry_log (audit trail)

4. **Enterprise Integration**
   - enterprise_property → properties (fraud DB)
   - enterprise_applicant → applicant_details (fraud DB)
   - inbound_webhooks → webhook_delivery_attempts

5. **Property & Company Hierarchy**
   - companies → properties → folders → entries
   - owners → property_owners → properties
   - users → users_properties → properties

### Medium Priority ERDs:

6. **Yardi Integration Flow**
   - yardi_integrations → yardi_properties → properties
   - yardi_invites → yardi_entries

7. **Feature Management**
   - features → property_features, user_features

8. **Dispute Management**
   - disputes → dispute_categories, dispute_emails

---

## Next Steps

1. ✅ Query all database schemas
2. ⏳ Generate detailed table-level documentation for fraud_postgresql
3. ⏳ Create visual ERD diagrams for key workflows
4. ⏳ Document foreign key relationships
5. ⏳ Identify and document business rules from constraints
6. ⏳ Map data flow between microservices

---

## Notes

- **Empty Databases**: Three dp_ databases show no tables in public schema. These may:
  - Use a different schema (e.g., "document_processing")
  - Be new services not yet deployed
  - Store data in external systems (S3, message queues)

- **Schema Differences**: The technology diversity (Elixir/Python/TypeScript) suggests a microservices architecture with polyglot persistence.

- **Data Volume**: fraud_postgresql is clearly the primary transactional database with 155 tables handling the core business logic.
