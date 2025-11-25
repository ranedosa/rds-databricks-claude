# Database ERD Documentation - Project Summary

**Project:** Snappt Fraud Detection Database Entity-Relationship Documentation
**Database:** fraud_postgresql (Production)
**Started:** 2025-11-19
**Last Updated:** 2025-11-25
**Status:** 40% Complete (30 of ~75 core tables documented)

---

## Executive Summary

This project provides comprehensive documentation of the Snappt fraud detection platform's PostgreSQL database schema. The database supports a multi-verification screening system that helps property managers assess rental applicants through fraud detection, income/asset verification, identity checks, and rental history validation.

**Key Findings:**
- **104 active tables** in fraud_postgresql database (excluding deleted/backup tables)
- **~75 core business tables** (after excluding audit/infrastructure tables)
- **30 tables fully documented** with complete schema details, relationships, and business logic
- **Microservices architecture** with 7 databases total (only fraud_postgresql actively documented)
- **Multi-verification workflow** supporting 4 verification types per applicant

---

## Documentation Overview

### Files Created

| File | Size | Tables | Description |
|------|------|--------|-------------|
| **CORE_ENTITY_MODEL.md** | 24KB | 14 | Foundation entities: applicants, properties, companies, users, access control |
| **FRAUD_DETECTION_WORKFLOW.md** | 24KB | 7 | Document fraud detection with ML/AI analysis and human review |
| **VERIFICATION_WORKFLOWS.md** | 26KB | 9 | Income, asset, identity, and rent verification workflows |
| **ERD_DIAGRAMS.md** | 18KB | 30 | **Visual ERD diagrams** for all documented tables (8 Mermaid diagrams) |
| **DATABASE_SCHEMA_SUMMARY.md** | 9.7KB | - | High-level overview of all 7 databases |
| **extract_schemas.py** | 1.6KB | - | Schema extraction utility script |
| **README.md** (this file) | 23KB | - | Project summary and findings |

**Total Documentation:** 126KB across 7 files

### Visual Diagrams

**📊 [ERD_DIAGRAMS.md](ERD_DIAGRAMS.md)** - 8 visual diagrams using Mermaid syntax:

1. **Core Entity Model** (2 diagrams)
   - Property Hierarchy & Applicant Flow
   - Ownership & Access Control Model

2. **Fraud Detection Workflow** (2 diagrams)
   - Complete Fraud Detection Flow
   - ML/AI Analysis Details

3. **Verification Workflows** (2 diagrams)
   - Income & Asset Verification
   - Identity & Rent Verification

4. **Integration Overview** (3 diagrams)
   - Complete Data Flow (Entry → Result)
   - Result Aggregation Logic
   - User Access Control Model

**Viewing:** Diagrams render automatically in GitHub, GitLab, VS Code (with Mermaid extension), or [Mermaid Live Editor](https://mermaid.live/)

---

## Documented Workflows (30 Tables)

### 1. Core Entity Model (14 Tables) ✅

**Purpose:** Foundation data structures that all other workflows build upon

**Entity Hierarchy:**
```
Companies → Properties → Folders → Entries → Applicants → Applicant Submissions
```

**Tables:**
- **Applicant Management (3):** applicants, applicant_details, applicant_submissions
- **Property Hierarchy (4):** companies, properties, folders, entries
- **Ownership (2):** owners, property_owners
- **Access Control (5):** users, team, role, users_properties, users_owners

**Key Features:**
- UUID primary keys throughout
- Soft delete support via deleted_* tables
- Salesforce integration (salesforce_account_id, sfdc_id)
- Multi-tenancy via company/property scoping
- Role-based access control (RBAC)
- Property-level and owner-level user permissions

**Documentation:** [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md)

---

### 2. Fraud Detection Workflow (7 Tables) ✅

**Purpose:** Document authenticity verification using ML/AI and human review

**Workflow:**
```
Document Upload → ML/AI Analysis → Routing Decision → Human Review (if needed) → Final Determination
```

**Tables:**
- **Document Management (2):** proof, applicant_submission_document_sources
- **Fraud Analysis (5):** fraud_submissions, fraud_reviews, fraud_document_reviews, fraud_results, fraud_result_types

**Key Features:**
- **ML/AI Integration:**
  - Automated fraud detection (OCR, metadata analysis)
  - Fraud indicators: copy_move_forgery, font_manipulation, metadata_mismatch
  - Suggested ruling with confidence scores
- **Review Workflow:**
  - Automatic approval for high-confidence clean documents
  - Human review escalation for suspicious documents
  - Document-level and submission-level results
- **JSONB Usage:**
  - extracted_meta: OCR results, dates, amounts
  - meta_data_flags: Array of fraud indicators
  - similarity_check: Duplicate document detection

**Documentation:** [FRAUD_DETECTION_WORKFLOW.md](FRAUD_DETECTION_WORKFLOW.md)

---

### 3. Verification Workflows (9 Tables) ✅

**Purpose:** Multi-type verification beyond fraud detection

#### 3.1 Income Verification (3 Tables)
**Goal:** Verify applicant income meets property requirements (typically 2.5-3x rent)

**Tables:** income_verification_submissions, income_verification_reviews, income_verification_results

**Features:**
- Automated income extraction from paystubs/bank statements
- Support for variable/self-employment income
- Human review for edge cases (2.5x-3x borderline)
- Rejection reasons: insufficient_income, employment_gap, inconsistent_income

#### 3.2 Asset Verification (3 Tables)
**Goal:** Verify sufficient liquid assets (typically 2-6 months rent)

**Tables:** asset_verification_submissions, asset_verification_reviews, asset_verification_results

**Features:**
- Liquid vs illiquid asset classification
- Multi-account aggregation
- Recency checks (statements must be <30 days old)
- Rejection reasons: insufficient_assets, illiquid_assets, stale_statements

#### 3.3 Identity Verification (1 Table)
**Goal:** Prevent identity theft via third-party ID scanning

**Tables:** id_verifications

**Features:**
- **Multi-provider support:** Incode (default), Persona
- **Verification steps:**
  - Government ID scanning (driver's license, passport)
  - Facial recognition + selfie comparison
  - Liveness detection (blink, head turn)
- **JSONB storage:** provider_session_info, provider_results
- **Webhook-based results:** Asynchronous result delivery

#### 3.4 Rent Verification (2 Tables)
**Goal:** Check rental payment history and evictions

**Tables:** rent_verifications, rent_verification_events

**Features:**
- **Third-party providers:** RentTrack, Experian RentBureau, TransUnion
- **Checks performed:**
  - Payment history (on-time vs late)
  - Eviction records
  - Outstanding balances
  - Lease violations
- **Event sourcing:** rent_verification_events provides audit trail

**Documentation:** [VERIFICATION_WORKFLOWS.md](VERIFICATION_WORKFLOWS.md)

---

## Database Architecture Findings

### Technology Stack

**Primary Database (fraud_postgresql):**
- **Framework:** Elixir/Phoenix + Ecto
- **Primary Keys:** UUID (uuid_generate_v4())
- **Migrations:** Ecto migrations
- **Background Jobs:** Oban (Elixir job queue)

**Other Databases:**
- **dp_ai_services:** Python + Alembic (AI/ML services)
- **enterprise_postgresql:** TypeScript + TypeORM (enterprise integrations)

**Observation:** Microservices architecture with polyglot persistence - each service uses its preferred tech stack.

---

### Data Patterns

#### 1. JSONB Usage (High Flexibility)
Used extensively for:
- **Provider integration data:** Flexible schemas for different third-party services
- **ML/AI results:** Variable analysis outputs
- **Configuration:** Property settings, feature flags
- **Metadata:** Additional context that doesn't warrant dedicated columns

**Examples:**
- `proof.extracted_meta` - OCR extraction results
- `id_verifications.provider_results` - Identity verification results
- `properties.supported_doctypes` - Document type configuration
- `rent_verifications.provider_data` - Rental history reports

#### 2. Soft Deletes
- **Deleted tables:** 20+ `deleted_*` tables for audit trail
- **Backup tables:** 7+ `*_backup` tables for data recovery
- **Pattern:** deleted_at timestamp + dedicated backup tables

#### 3. Denormalization for Performance
- **folders table:** Denormalizes last_entry_* fields for dashboard queries
- **properties table:** Includes company_short_id for faster lookups
- **Pattern:** Trade disk space for query performance

#### 4. Audit & Event Sourcing
- **audit_transaction_event:** Database-level audit trail
- **rent_verification_events:** Workflow event log
- **webhook_delivery_attempts:** Integration event tracking

#### 5. Array Types
Used for multi-value fields:
- `proof.meta_data_flags` - Array of fraud indicators
- `income_verification_results.rejected_reasons` - Multiple rejection reasons
- `proof.result_edited_reason` - List of editing types detected

---

### Cross-Database Integration

**fraud_postgresql ↔ enterprise_postgresql:**
```
enterprise_applicant.snappt_applicant_detail_id → applicant_details.id
enterprise_property.snappt_property_id → properties.id
```

**External Integrations:**
- **Salesforce CRM:** companies.salesforce_account_id, properties.sfdc_id, owners.salesforce_id
- **Yardi PMS:** yardi_integrations, yardi_properties, yardi_entries
- **Identity Providers:** id_verifications (Incode, Persona)
- **Rent History:** rent_verifications (RentTrack, Experian)

---

## Key Business Logic Discoveries

### 1. Multi-Verification Aggregation

Entry results aggregate across all verification types with **worst-case precedence:**

```
Priority (highest to lowest):
1. FRAUD - Any fraud detected → Entry REJECTED
2. REJECTED - Any critical verification failed → Entry REJECTED
3. NEEDS_REVIEW - Any verification requires human review → Entry NEEDS_REVIEW
4. APPROVED - All verifications passed → Entry APPROVED
```

**Example:**
- Fraud: CLEAN
- Income: APPROVED
- Asset: APPROVED
- Identity: APPROVED
- Rent: REJECTED (eviction found)
- **Final Entry Result:** REJECTED

---

### 2. Automated vs Manual Review Logic

**Fraud Detection:**
- **Auto-approve:** ML confidence >95%, no fraud flags, result = CLEAN
- **Manual review:** ML confidence <95%, fraud flags detected, or suggested_ruling = FRAUD/EDITED

**Income Verification:**
- **Auto-approve:** Income ≥3x rent, consistent sources, clear documents
- **Manual review:** Income 2.5x-3x rent, variable income, self-employed, employment gaps

**Asset Verification:**
- **Auto-approve:** Liquid assets ≥6 months rent, recent statements
- **Manual review:** Assets 2-6 months rent, mixed liquid/illiquid, joint accounts

**Identity Verification:**
- **Auto-approve:** High confidence score, all checks passed
- **Manual review:** Medium confidence, partial check failures

---

### 3. Review Types & Escalation

**Review Type Hierarchy:**
1. **INITIAL** - First review by standard reviewer
2. **ESCALATION** - Escalated to senior reviewer or QA team
3. **QA** - Quality assurance check

**Pattern:** Used in fraud_reviews, income_verification_reviews, asset_verification_reviews

---

### 4. Review Method Tracking

```sql
review_method ENUM:
- AUTOMATED: System made determination without human
- MANUAL: Human reviewed and made decision
```

**Purpose:** Track automation effectiveness, reviewer workload, and audit compliance

---

## Data Volume & Scale

### Table Size Estimates (Inferred)

**High-Volume Tables:**
- **entries** - Primary screening requests (thousands/day)
- **applicants** - One per applicant (thousands/day)
- **proof** - Documents uploaded (millions)
- **fraud_submissions** - Fraud analysis requests (millions)
- **applicant_submissions** - Document submissions (millions)

**Medium-Volume Tables:**
- **properties** - Individual properties (~10,000s)
- **companies** - Property management companies (~1,000s)
- **users** - System users (~1,000s)

**Low-Volume Tables:**
- **owners** - Property owners (~100s-1,000s)
- **team** - Organizational teams (~10s)
- **role** - User roles (~5-10)
- **fraud_result_types** - Result lookup (~5 rows)

---

## Remaining Work

### Undocumented Tables (~45 tables remaining)

#### High Priority (19 tables)

**Review & Queue System (6 tables):**
- review_items, reviewer_queue
- entry_log, entry_report
- entry_review_escalation
- role_entry_status_sort_priority

**Features & Configuration (7 tables):**
- features, property_features, user_features, property_feature_events
- settings, country, whitelist_info

**Integrations (6 tables):**
- webhooks, webhook_delivery_attempts
- yardi_integrations, yardi_properties, yardi_entries, yardi_invites

#### Medium Priority (13 tables)

**Disputes (3 tables):**
- disputes, dispute_categories, dispute_emails

**Fraud Detection - Advanced (2 tables):**
- frequent_flyer_variations, frequent_flyer_matched_confidences

**Supporting Systems (8 tables):**
- matching_entries
- invitations, invitations_properties
- oban_jobs, oban_peers
- api_keys, unauthenticated_session
- analytics_reports

#### Low Priority (13 tables)

**User Experience (5 tables):**
- announcement, announcement_role, announcement_user_was_shown
- user_role_sort_priority, user_tab_role_sort_priority

**Document Processing (1 table):**
- voi_reprocessing

**Infrastructure (2 tables):**
- schema_migrations
- activation_history

**Cleanup/Backup (5 tables):**
- applicant_submission_backup
- applicant_submission_document_sources_cleanup_backup
- applicant_submissions_cleanup_backup
- review_items_cleanup_backup
- staging_activation_backfill

---

## Other Databases (Not Yet Documented)

### enterprise_postgresql (6 tables)
**Priority:** Medium - Important for cross-database integration

**Tables:**
- email_delivery_attempts
- enterprise_applicant (links to fraud DB)
- enterprise_property (links to fraud DB)
- enterprise_integration_configuration
- inbound_webhooks
- migrations, typeorm_metadata

### dp_ai_services (2 tables)
**Priority:** Low - Analytics/monitoring only

**Tables:**
- alembic_version (migrations)
- checkpoint_analytics_view (AI agent execution metrics)

### av_postgresql (1 table)
**Priority:** Very Low - Infrastructure only

**Tables:**
- schema_migrations

### Databases Needing Investigation (3 databases)
**Priority:** Medium - May contain important data

- dp_income_validation (0 tables found in public schema)
- dp_document_intelligence (0 tables found in public schema)
- dp_inception_fraud (0 tables found in public schema)

**Action needed:** Check if tables exist in non-public schemas or if databases are unused.

---

## Documentation Quality Metrics

### Completeness

**For each documented table, we provide:**
- ✅ Complete column list with data types
- ✅ Nullable/NOT NULL constraints
- ✅ Default values
- ✅ Primary key identification
- ✅ Foreign key relationships (explicit and implicit)
- ✅ Business logic and usage patterns
- ✅ Integration points (third-party services, cross-database)
- ✅ JSONB field examples and schemas
- ✅ Enum value definitions
- ✅ Data flow examples
- ✅ Performance optimization recommendations
- ✅ Security and compliance considerations

### Documentation Standards

**Markdown formatting:**
- Clear headers and sections
- Tables for column definitions
- Code blocks for SQL/JSON examples
- Visual diagrams using ASCII art
- Cross-references between documents

**Technical depth:**
- Schema-level details (database structure)
- Application-level logic (business rules)
- Integration patterns (external services)
- Performance considerations (indexes, JSONB)
- Security implications (PII, encryption)

---

## How to Use This Documentation

### For Developers

**Understanding the codebase:**
1. Start with [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md) to understand base entities
2. Read workflow-specific docs for features you're working on
3. Reference foreign key relationships to understand data flow

**Adding new features:**
1. Check if similar patterns exist in documented workflows
2. Follow established naming conventions (e.g., *_verification_submissions)
3. Use JSONB for flexible/provider-specific data
4. Implement soft deletes for audit trail

**Debugging:**
1. Use foreign key maps to trace data relationships
2. Check event tables (rent_verification_events) for audit trails
3. Review JSONB fields for provider error messages

### For Database Administrators

**Schema changes:**
1. Understand foreign key dependencies before altering tables
2. Be aware of soft delete patterns (deleted_* tables)
3. Consider denormalized fields that may need updating

**Performance optimization:**
1. Review index recommendations in each workflow doc
2. Consider JSONB GIN indexes for frequently queried JSONB fields
3. Monitor high-volume tables (proof, fraud_submissions, entries)

**Maintenance:**
1. Backup tables provide data recovery options
2. Event tables provide audit trails
3. Soft delete tables support data restoration

### For Product Managers

**Understanding features:**
1. Each workflow doc explains business logic and user experience
2. Review automated vs manual review logic for each verification type
3. Understand multi-verification aggregation for entry results

**Integration capabilities:**
1. Identity verification supports multiple providers (Incode, Persona)
2. Rent verification integrates with RentTrack, Experian, TransUnion
3. Salesforce integration via dedicated ID fields

**Feature configuration:**
1. Properties can enable/disable verification types
2. Properties can set income/asset requirements
3. Properties can choose identity verification provider

### For Data Analysts

**Key metrics tables:**
- `entries` - Overall screening volume and results
- `fraud_reviews` - Manual review workload and turnaround time
- `income_verification_results` - Approval/rejection rates
- `asset_verification_results` - Asset sufficiency trends
- `id_verifications` - Identity verification success rates
- `rent_verifications` - Rental history findings

**Analytics queries:**
- Join entries → folders → properties → companies for property-level metrics
- Use review tables to measure reviewer productivity
- Analyze JSONB fields for fraud indicator trends
- Event tables provide time-series data

---

## Performance Considerations

### Recommended Indexes

**Already Documented:**
- See each workflow doc for specific index recommendations
- JSONB GIN indexes for frequently queried JSONB fields
- Foreign key indexes for join performance
- Status/state indexes for queue queries

### Query Patterns to Optimize

1. **Dashboard queries:** Heavy denormalization in folders table
2. **Review queues:** Compound indexes on (status, assigned_date)
3. **Document searches:** Full-text search indexes on properties
4. **Provider lookups:** Indexes on external_id fields

---

## Security & Compliance

### PII Data Locations

**High-sensitivity PII:**
- `applicants`: full_name, email, phone
- `id_verifications`: First name, last name, email, government ID images (JSONB)
- `proof`: Financial documents (file URLs)
- `income_verification_submissions`: Income amounts
- `asset_verification_submissions`: Asset amounts
- `rent_verifications`: SSN (last 4), DOB, previous addresses

**Protection measures:**
- Encryption at rest for all databases
- TLS for all data in transit
- Role-based access control (RBAC)
- Audit trails (audit_transaction_event, event tables)
- Data retention policies (auto-delete after retention period)
- GDPR/CCPA compliance for data deletion requests

---

## Visual Diagrams ✅

### ERD Diagrams Created

**See:** [ERD_DIAGRAMS.md](ERD_DIAGRAMS.md) for all visual diagrams

**8 Mermaid Diagrams Completed:**

1. **Core Entity Model Diagrams** (2 diagrams)
   - Property Hierarchy & Applicant Flow - Shows the main data flow from companies to applicants
   - Ownership & Access Control Model - User permissions and access grants

2. **Fraud Detection Workflow Diagrams** (2 diagrams)
   - Complete Fraud Detection Flow - Document upload through ML/AI to human review
   - ML/AI Analysis Details - JSONB field structures and fraud indicators

3. **Verification Workflows Diagrams** (2 diagrams)
   - Income & Asset Verification - Parallel verification workflows
   - Identity & Rent Verification - Third-party provider integrations

4. **Integration Overview Diagrams** (3 diagrams)
   - Complete Data Flow - Entry creation to final determination (all 30 tables)
   - Result Aggregation Logic - Multi-verification precedence rules
   - User Access Control Model - Permission hierarchy visualization

**Features:**
- Mermaid syntax (renders in GitHub/GitLab/VS Code)
- Primary/foreign keys clearly marked
- Relationship cardinality shown
- JSONB field examples included
- Color-coded flow diagrams

**Status:** ✅ Completed - 8 diagrams covering all 30 documented tables

---

## Project Timeline

**2025-11-19:**
- Project initiated
- DATABASE_SCHEMA_SUMMARY.md created (high-level overview of 7 databases)

**2025-11-25:**
- CORE_ENTITY_MODEL.md (14 tables)
- FRAUD_DETECTION_WORKFLOW.md (7 tables)
- VERIFICATION_WORKFLOWS.md (9 tables)
- ERD_DIAGRAMS.md (8 visual diagrams for all 30 tables)
- README.md (this summary)

**Total Time:** ~3-4 hours of focused documentation work

---

## Next Steps

### Immediate Priorities

1. **Complete Review & Queue System** (6 tables)
   - How entries flow through review queues
   - Reviewer assignment logic
   - Entry log audit trail

2. **Document Features & Configuration** (7 tables)
   - Feature flag system
   - Property-level feature enablement
   - User-level feature access

3. **Document Integration Layer** (6 tables)
   - Webhook system
   - Yardi integration
   - Webhook delivery and retry logic

### Medium-term Goals

4. **Document enterprise_postgresql** (6 tables)
   - Cross-database integration details
   - Enterprise applicant/property links

5. **Complete Remaining Tables** (~20 supporting tables)
   - Disputes, announcements, frequent flyer detection
   - Background jobs, invitations

### Long-term Goals

6. **Generate Interactive Schema Explorer**
   - Web-based schema browser
   - Clickable table relationships
   - Search across all tables

7. **API Documentation Integration**
   - Link database schema to API endpoints
   - Show which endpoints modify which tables

8. **Data Dictionary**
   - Standardized field definitions
   - Business glossary
   - Column naming conventions

---

## Contributing to This Documentation

### Adding New Table Documentation

**Follow this structure:**
1. Table purpose statement
2. Primary key identification
3. Column table with full details
4. Relationships section
5. Business logic section
6. Examples (JSONB payloads, SQL queries)
7. Performance considerations
8. Security notes (if handling PII)

**Naming convention:**
- Files: `WORKFLOW_NAME.md` (e.g., `REVIEW_QUEUE_SYSTEM.md`)
- Headers: Use `#` for workflow, `##` for tables, `###` for subsections
- Cross-references: `[Link text](FILENAME.md)`

### Updating Existing Documentation

**When schema changes:**
1. Update column definitions in relevant workflow doc
2. Update relationships if foreign keys change
3. Add migration notes in comments
4. Update this README if major structural changes

**When business logic changes:**
1. Update business logic sections
2. Add new examples if behavior changed
3. Note deprecations for old patterns

---

## Questions & Contact

**For questions about this documentation:**
- Review existing workflow docs first
- Check [DATABASE_SCHEMA_SUMMARY.md](DATABASE_SCHEMA_SUMMARY.md) for overview
- Reference this README for findings and patterns

**For questions about the database itself:**
- Contact: dane@snappt.com
- Database: fraud_postgresql (production)
- Location: RDS PostgreSQL via MCP connections

---

## Appendix: Table Count Summary

### Documented Tables by Workflow

| Workflow | Tables | Files |
|----------|--------|-------|
| Core Entity Model | 14 | CORE_ENTITY_MODEL.md |
| Fraud Detection | 7 | FRAUD_DETECTION_WORKFLOW.md |
| Income Verification | 3 | VERIFICATION_WORKFLOWS.md |
| Asset Verification | 3 | VERIFICATION_WORKFLOWS.md |
| Identity Verification | 1 | VERIFICATION_WORKFLOWS.md |
| Rent Verification | 2 | VERIFICATION_WORKFLOWS.md |
| **TOTAL DOCUMENTED** | **30** | **3 workflow docs** |

### Remaining Tables by Priority

| Priority | Tables | Workflows |
|----------|--------|-----------|
| High | 19 | Review/Queue, Features, Integrations |
| Medium | 13 | Disputes, Frequent Flyer, Supporting |
| Low | 13 | User Experience, Infrastructure, Cleanup |
| **TOTAL REMAINING** | **~45** | **~9 workflows** |

### Overall Progress

```
30 tables documented / 75 core tables = 40% complete
```

**Estimated completion:** 60-75 core tables (excluding deleted/backup/audit tables)

---

**End of Summary Document**

*Generated: 2025-11-25*
*Last Updated: 2025-11-25*
*Version: 1.0*
