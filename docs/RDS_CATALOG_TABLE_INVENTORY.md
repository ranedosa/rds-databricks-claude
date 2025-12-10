# RDS Catalog - Table Inventory

**Generated:** 2025-12-08
**Source:** Databricks Unity Catalog REST API
**Catalog:** `rds`

---

## Overview

- **Total Schemas:** 9
- **Total Tables:** 144

---

## Schema Breakdown

### 1. pg_rds_public (72 tables)
**Primary production schema** - Core Snappt application data

#### Core Entities
- `applicants` - Applicant records
- `applicant_details` - Additional applicant information
- `applicant_submissions` - Submission records
- `applicant_submission_document_sources` - Document source tracking
- `companies` - Company/client records
- `properties` - Property records
- `property_owners` - Property ownership mapping
- `owners` - Owner entities
- `users` - User accounts
- `users_properties` - User-property relationships
- `users_owners` - User-owner relationships

#### Verification & Results
- `fraud_submissions` - Fraud detection submissions
- `fraud_results` - Fraud detection results
- `fraud_result_types` - Result type codes
- `fraud_reviews` - Manual fraud reviews
- `fraud_document_reviews` - Document-level fraud reviews
- `income_verification_submissions` - Income verification submissions
- `income_verification_results` - Income verification results
- `income_verification_reviews` - Income verification reviews
- `asset_verification_submissions` - Asset verification submissions
- `asset_verification_results` - Asset verification results
- `asset_verification_reviews` - Asset verification reviews
- `id_verifications` - ID verification records
- `rent_verifications` - Rent verification records
- `rent_verification_events` - Rent verification event tracking

#### Features & Configuration
- `features` - Feature flags/configuration
- `property_features` - Property-specific feature settings
- `property_feature_events` - Feature activation/change events
- `user_features` - User-specific feature settings
- `settings` - Application settings

#### Review & Quality
- `entries` - Review entries
- `entry_log` - Entry change log
- `entry_report` - Entry reporting data
- `entry_review_escalation` - Escalated reviews
- `review_items` - Review item records
- `reviewer_queue` - Reviewer work queue
- `matching_entries` - Entry matching/deduplication

#### Disputes & Fraud Detection
- `disputes` - Dispute records
- `dispute_categories` - Dispute categorization
- `dispute_emails` - Dispute communication
- `frequent_flyer_variations` - Frequent flyer detection data
- `frequent_flyer_matched_confidences` - Confidence scores for matches

#### Integration & External Systems
- `api_keys` - API key management
- `webhooks` - Webhook configurations
- `webhook_delivery_attempts` - Webhook delivery tracking
- `sfdc_updates` - Salesforce update tracking
- `yardi_integrations` - Yardi PMS integration
- `yardi_properties` - Yardi property mapping
- `yardi_entries` - Yardi entry data
- `yardi_invites` - Yardi invitation tracking

#### Access & Security
- `invitations` - User invitations
- `invitations_properties` - Invitation property scope
- `role` - User roles
- `team` - Team management
- `unauthenticated_session` - Unauthenticated session tracking

#### Content & Communication
- `announcement` - System announcements
- `announcement_role` - Announcement targeting by role
- `folders` - Document folder organization
- `proof` - Proof/documentation records

#### Data Management
- `activation_history` - Feature activation history
- `staging_activation_backfill` - Activation backfill staging
- `voi_reprocessing` - Verification of income reprocessing
- `whitelist_info` - Whitelist data
- `analytics_reports` - Analytics/reporting data
- `country` - Country reference data
- `schema_migrations` - Database migration tracking
- `oban_peers` - Oban job queue peer tracking
- `_quality_monitoring_summary` - Data quality monitoring

#### Backup Tables
- `applicant_submission_backup` - Submission backups
- `applicant_submissions_cleanup_backup` - Cleanup backup
- `applicant_submission_document_sources_cleanup_backup` - Document source cleanup backup
- `review_items_cleanup_backup` - Review items cleanup backup

---

### 2. pg_rds_ax_public (13 tables)
**Argyle Integration** - Connected payroll and employment verification

#### Core Tables
- `applicants` - Argyle applicant records
- `applicant_submissions` - Argyle submission records
- `applicant_submission_document_sources` - Document tracking

#### Argyle-Specific
- `argyle_users` - Argyle user accounts
- `argyle_accounts` - Connected payroll accounts
- `argyle_employments` - Employment records from Argyle
- `argyle_documents` - Documents retrieved via Argyle

#### Exhibits & Evidence
- `exhibits` - Exhibit/evidence records
- `exhibit_data` - Exhibit data storage
- `exhibit_statuses` - Exhibit status tracking

#### System
- `api_keys` - API key management
- `migrations` - Database migrations
- `typeorm_metadata` - TypeORM framework metadata

---

### 3. pg_rds_av_av (10 tables)
**Asset Verification (AV)** - Document verification and fraud detection models

#### Document Analysis
- `document_rulings` - ML model rulings on documents
- `document_ruling_codes` - Ruling type codes
- `document_ruling_audits` - Audit trail for rulings
- `document_scores` - Document fraud scores
- `document_errors` - Document processing errors
- `document_error_codes` - Error type codes
- `document_properties` - Document metadata/properties

#### Training & Quality
- `document_properties_training` - Training data for ML models
- `training_documents` - Training document corpus
- `audit_decision_codes` - Audit decision classification

---

### 4. pg_rds_dp_di_di (8 tables)
**Document Intelligence (DI)** - AI-powered document processing

#### Asset Verification
- `asset_verifications` - Asset verification records
- `asset_verification_status_codes` - Status code lookup
- `asset_verification_status_details` - Detailed status information
- `asset_verification_review` - Manual review records

#### Document Processing
- `statements` - Financial statement records
- `accounts` - Account information extracted from statements
- `inferences` - AI inference results
- `ai_operations` - AI operation tracking

---

### 5. pg_rds_dp_income_validation_iv (5 tables)
**Income Validation (IV)** - Income calculation engine

#### Calculations
- `calculations` - Income calculation records
- `calculation_status_codes` - Status codes
- `calculation_status_details` - Detailed status information
- `calculation_documents` - Documents used in calculations

---

### 6. pg_rds_enterprise_public (7 tables)
**Enterprise Integration** - Enterprise-level integrations and webhooks

#### Core Entities
- `enterprise_applicant` - Enterprise applicant records
- `enterprise_property` - Enterprise property records
- `enterprise_integration_configuration` - Integration settings

#### Integration Tracking
- `inbound_webhooks` - Inbound webhook records
- `outbound_integration_attempt_item` - Outbound integration attempts
- `email_delivery_attempts` - Email delivery tracking

#### System
- `migrations` - Database migrations

---

### 7. pg_rds_dp_income_validation_icfr (2 tables)
**Income Calculation - Fraud Rules** - Company name fraud detection

- `banned_company_names` - Banned/fraudulent company names
- `banned_company_name_submissions` - Submissions flagged by banned names

---

### 8. pg_rds_dp_income_validation_grate (3 tables)
**Database Migration Framework** - Grate migration tool metadata

- `version` - Migration version tracking
- `scriptsrun` - Migration scripts executed
- `scriptsrunerrors` - Migration script errors

---

### 9. _fivetran_setup_test (24 tables)
**Fivetran Testing** - Fivetran connector test staging tables

- `setup_test_staging_*` - 24 test staging tables (UUID-based names)

---

## Schema Summary Table

| Schema | Tables | Purpose |
|--------|--------|---------|
| `pg_rds_public` | 72 | Main production database |
| `pg_rds_ax_public` | 13 | Argyle integration (payroll) |
| `pg_rds_av_av` | 10 | Asset verification models |
| `pg_rds_dp_di_di` | 8 | Document intelligence AI |
| `pg_rds_dp_income_validation_iv` | 5 | Income calculation engine |
| `pg_rds_enterprise_public` | 7 | Enterprise integrations |
| `pg_rds_dp_income_validation_icfr` | 2 | Company fraud rules |
| `pg_rds_dp_income_validation_grate` | 3 | Migration framework |
| `_fivetran_setup_test` | 24 | Fivetran test staging |
| **TOTAL** | **144** | |

---

## Database Naming Conventions

### Schema Naming Pattern
- `pg_rds_<source>_<schema>` - PostgreSQL RDS source databases
  - `pg_rds_public` - Main Snappt production DB
  - `pg_rds_ax_public` - Argyle service DB
  - `pg_rds_av_av` - Asset Verification service DB
  - `pg_rds_dp_di_di` - Document Intelligence service DB
  - `pg_rds_dp_income_validation_*` - Income Validation service DBs
  - `pg_rds_enterprise_public` - Enterprise service DB

### Service Abbreviations
- `av` = Asset Verification
- `ax` = Argyle (connected payroll)
- `dp` = Data Platform
- `di` = Document Intelligence
- `iv` = Income Validation
- `icfr` = Income Calculation Fraud Rules
- `grate` = Database migration tool

---

## Key Relationships & Data Flow

### Primary Verification Flow
1. **Applicant Creation** → `pg_rds_public.applicants`
2. **Submission** → `pg_rds_public.applicant_submissions`
3. **Document Upload** → `pg_rds_public.applicant_submission_document_sources`

### Fraud Detection Flow
1. **Submission** → `pg_rds_public.fraud_submissions`
2. **Document Analysis** → `pg_rds_av_av.document_rulings`
3. **Results** → `pg_rds_public.fraud_results`
4. **Review** → `pg_rds_public.fraud_reviews`

### Income Verification Flow
1. **Submission** → `pg_rds_public.income_verification_submissions`
2. **Document Processing** → `pg_rds_dp_di_di.statements`
3. **Calculation** → `pg_rds_dp_income_validation_iv.calculations`
4. **Results** → `pg_rds_public.income_verification_results`

### Argyle Integration Flow
1. **Connection** → `pg_rds_ax_public.argyle_users`
2. **Employment Data** → `pg_rds_ax_public.argyle_employments`
3. **Documents** → `pg_rds_ax_public.argyle_documents`
4. **Exhibits** → `pg_rds_ax_public.exhibits`

---

## Notes

- All tables are `MANAGED` type (Delta Lake managed tables)
- Table sizes not available via REST API (would require SQL queries)
- Some schemas have duplicate table names (e.g., `api_keys` in both `pg_rds_public` and `pg_rds_ax_public`)
- Backup tables suggest periodic cleanup operations in production
- Multiple service-oriented databases reflect microservices architecture

---

## Next Steps for Analysis

To get more detailed information, consider:

1. **Row counts** - Query `SELECT COUNT(*) FROM <table>` for sizing
2. **Schema definitions** - Query `DESCRIBE TABLE EXTENDED <table>` for columns
3. **Table statistics** - Query `DESCRIBE DETAIL <table>` for Delta Lake metadata
4. **Data lineage** - Trace relationships between schemas/services
5. **Usage patterns** - Analyze query logs to identify most-accessed tables

---

## Files

- **Query Script:** `/Users/danerosa/rds_databricks_claude/scripts/query_top_tables_api.py`
- **This Document:** `/Users/danerosa/rds_databricks_claude/docs/RDS_CATALOG_TABLE_INVENTORY.md`
