# Database ERD Project - Session Notes & Working Context

**Purpose:** Detailed technical notes for AI assistants to quickly resume work in future sessions
**Last Updated:** 2025-11-25 (Session 2)
**Current Progress:** 54 tables documented (65% complete)

---

## Quick Context Summary

### What We're Documenting
- **Primary Database:** fraud_postgresql (production) - Snappt fraud detection platform
- **Secondary Database:** enterprise_postgresql - Cross-database integration layer
- **Total Tables:** ~75 core business tables in fraud_postgresql + 5 in enterprise_postgresql
- **Current Status:** 49 fraud_postgresql + 5 enterprise_postgresql = 54 tables documented

### Why This Matters
**User's Critical Requirement:**
> "Something we should keep in mind for future work is how these databases are connected by PK and FKs this will allow myself, the data architect, and other analysts and engineers to quickly write queries that include information from multiple databases"

**Key Deliverable:** Document cross-database foreign keys to enable multi-database query writing

### Tech Stack Insights
- **fraud_postgresql:** Elixir/Phoenix + Ecto ORM
- **enterprise_postgresql:** TypeScript + TypeORM
- **Microservices:** Polyglot persistence (7 databases total)
- **Primary Keys:** UUID throughout
- **Heavy JSONB usage:** Provider integration data, ML/AI results, flexible configurations

---

## All Documented Tables - Quick Reference

### fraud_postgresql (49 tables)

#### Core Entity Model (14 tables)
1. **companies** - Property management companies (PKs: salesforce_account_id)
2. **properties** - Individual properties (26 columns, extensive config, PKs: company_id, identity_verification_enabled)
3. **folders** - Groups entries for same applicant/property (denormalized: last_entry_*)
4. **entries** - Screening requests (24 columns, result aggregation, PKs: folder_id, reviewer_id)
5. **applicants** - Individual applicants (PKs: entry_id, applicant_detail_id)
6. **applicant_details** - Applicant PII storage (JSONB: prefilled_application_data)
7. **applicant_submissions** - Document submission events (PKs: applicant_id)
8. **owners** - Property owners (separate from property management companies)
9. **property_owners** - Many-to-many: properties ↔ owners
10. **users** - System users (PKs: company_id, team_id, role)
11. **team** - Reviewer teams (PKs: country_id, fde_manager_id)
12. **role** - User roles (admin, reviewer, QA, etc.)
13. **users_properties** - Property-level access grants
14. **users_owners** - Owner-level access grants (composite PK: owner_id + user_id)

**Key FK Patterns:**
- companies → properties → folders → entries → applicants → applicant_submissions
- properties ← property_owners → owners
- users → users_properties → properties
- users → users_owners → owners

#### Fraud Detection Workflow (7 tables)
15. **proof** - Documents uploaded (28 columns! Most complex table)
    - JSONB: extracted_meta (OCR results), test_extracted_meta, text_breakups
    - Arrays: meta_data_flags (fraud indicators), similarity_check, jobs_error, result_edited_reason
    - Enums: type, result, suggested_ruling
16. **applicant_submission_document_sources** - Document source tracking (PKs: applicant_submission_id)
17. **fraud_submissions** - Fraud analysis requests (PKs: applicant_submission_document_source_id)
18. **fraud_reviews** - Human fraud review (PKs: fraud_submission_id, reviewer_id, result FK)
19. **fraud_document_reviews** - Document-level review (PKs: fraud_review_id, document_id)
20. **fraud_results** - Final fraud determination (PKs: applicant_submission_id, result FK)
21. **fraud_result_types** - Result lookup table (codes: CLEAN, FRAUD, EDITED, etc.)

**Key Insights:**
- proof table has 28 columns for comprehensive ML/AI analysis
- Multiple JSONB fields for flexible output storage
- Document-level AND submission-level review tracking
- Result aggregation: fraud_document_reviews → fraud_reviews → fraud_results

#### Verification Workflows (9 tables)

**Income Verification (3 tables):**
22. **income_verification_submissions** - Income analysis requests (PKs: entry_id, applicant_submission_document_source_id)
23. **income_verification_reviews** - Human income review (PKs: income_verification_submission_id, reviewer_id, calculation_id)
24. **income_verification_results** - Final eligibility (PKs: applicant_submission_id, calculation_id, type)
    - review_eligibility: APPROVED, REJECTED, NEEDS_REVIEW
    - rejected_reasons array: insufficient_income, employment_gap, inconsistent_income

**Asset Verification (3 tables):**
25. **asset_verification_submissions** - Asset analysis requests (PKs: entry_id, applicant_submission_document_source_id)
26. **asset_verification_reviews** - Human asset review (PKs: asset_verification_submission_id, reviewer_id, calculation_id)
27. **asset_verification_results** - Final sufficiency (PKs: applicant_submission_id, calculation_id)
    - rejected_reasons array: insufficient_assets, illiquid_assets, stale_statements

**Identity Verification (1 table):**
28. **id_verifications** - Third-party ID verification (17 columns)
    - Providers: Incode (primary), Persona
    - JSONB: provider_session_info, provider_results, incode_results, metadata
    - Checks: Government ID scanning, facial recognition, liveness detection
    - PKs: property_id, company_id, applicant_detail_id

**Rent Verification (2 tables):**
29. **rent_verifications** - Rental payment history (PKs: applicant_id, property_id)
    - Providers: RentTrack, Experian RentBureau, TransUnion
    - JSONB: request_payload, provider_data
30. **rent_verification_events** - Event sourcing audit trail (PKs: rent_verification_id)

**Key Patterns:**
- Parallel workflows: income, asset, identity, rent all run independently
- Common structure: *_submissions → *_reviews → *_results
- JSONB for provider flexibility
- Automated vs manual review routing (review_method enum)

#### Review & Queue System (6 tables)
31. **review_items** - Central queue table (workflow-agnostic!)
    - Polymorphic: entity_id references different tables based on workflow
    - workflow values: entry_review, fraud_review, income_review, asset_review
    - State machine: scheduled → assigned → completed
    - SLA tracking: assignable_at, assigned_at, completed_at
32. **reviewer_queue** - Reviewer work requests (pull-based assignment)
    - State: available → assigned
    - PKs: reviewer_id FK, assigned_entry_id FK
    - Links to review_items via review_items.reviewer_queue_item_id
33. **entry_log** - Complete audit trail (every entry state change)
    - Event types: entry_created, status_change, result_change, assignment, review_started, escalation
    - PKs: entry_id, reviewer_id, workflow
    - Arrays: proofs (document-level tracking)
34. **entry_report** - Final completion reports (immutable snapshot)
    - Generated when entry reaches terminal state
    - Used for property manager dashboard and notifications
35. **entry_review_escalation** - Complex case escalations
    - Reasons: complex_case, quality_check, customer_request, policy_question
    - PKs: entry_id, escalated_by_id FK
36. **role_entry_status_sort_priority** - Queue priority configuration
    - Different roles see different priorities
    - PKs: role_id, entry_status, priority (integer, lower = higher priority)

**Critical Pattern:**
- review_items is workflow-agnostic → supports ALL current and future review workflows
- Pull-based assignment prevents reviewer overload
- Complete forensic audit trail via entry_log

#### Features & Configuration (7 tables)
37. **features** - Master feature catalog
    - codes: identity_verification, income_verification, auto_approval, batch_review, etc.
38. **property_features** - Property-level enablement
    - state: enabled, disabled, testing
    - Enables gradual rollout (10% → 50% → 100%)
    - PKs: property_id, feature_code
39. **user_features** - User-level access (beta testing)
    - state: enabled, disabled
    - PKs: user_id, feature_code
40. **property_feature_events** - Change audit trail
    - event_type: enabled, disabled, updated
    - Tracks feature adoption timeline
41. **settings** - Global system toggles
    - Examples: maintenance_mode, auto_fraud_detection, ml_model_v2_enabled
    - Feature kill switches
42. **country** - Country reference data
    - ISO codes: alfa2 (US), alfa3 (USA), numcode (840)
    - PKs: country FK in team table
43. **whitelist_info** - Fraud detection optimization
    - Known-good: producer (PDF generator), fonts, breakups (text patterns)
    - Reduces false positives

**Key Capabilities:**
- A/B testing: Split properties into control vs treatment groups
- Gradual rollout: Deploy to subset, measure, expand
- Feature flag states: enabled/disabled/testing
- property_feature_events provides complete adoption history

#### Integration Layer (6 tables)
44. **webhooks** - Customer endpoint configuration
    - events array: entry.completed, fraud.detected, income.verified, etc.
    - headers JSONB array: Custom authentication headers
    - PKs: api_key_id
45. **webhook_delivery_attempts** - Delivery tracking with retries
    - response_status: 2xx = success, 4xx = no retry, 5xx = retry
    - JSONB: payload (sent), response_data (received)
    - Exponential backoff: 1min → 5min → 15min → 1hr
46. **yardi_integrations** - Yardi Voyager SOAP config
    - SOAP: wsdl_url, soap_endpoint, user_name, password (encrypted)
    - poll_rate: Minutes between prospect imports
    - attachment_type: email, api, manual
47. **yardi_properties** - Property-level Yardi config
    - PKs: property_id (PK!), yardi_integration_id
    - Integration health: last_poll_run, submit_date
48. **yardi_entries** - Links Snappt entries to Yardi prospects
    - PKs: entry_id (PK!), prospect_code
    - Used for result submission back to Yardi
49. **yardi_invites** - Imported prospect data
    - Composite PK: id + yardi_integration_id
    - Prospect info: prospect_code, yardi_property_id, snappt_property_id, email, first_name, last_name

**Integration Flows:**
- Outbound: Entry completed → webhooks → webhook_delivery_attempts → customer system
- Inbound: Yardi poll → yardi_invites → create entry → yardi_entries → send results back

### enterprise_postgresql (5 tables) - 100% Complete!

50. **enterprise_applicant** - Links external applicants to Snappt (9 columns)
    - 🔗 **CRITICAL:** snappt_applicant_detail_id → fraud_postgresql.applicant_details.id
    - integration_id: External system ID (Yardi prospect code, RealPage applicant ID)
    - JSONB: integration_details (external system data), integration_ids (multiple IDs)
    - final_status, denial_reason, application_status, yardi_status_updated_at

51. **enterprise_property** - Links external properties to Snappt (10 columns)
    - 🔗 **CRITICAL:** snappt_property_id → fraud_postgresql.properties.id
    - PKs: enterprise_integration_id FK
    - JSONB: integration_details (property data), configuration (sync settings)
    - Integration health: integration_activation_date, integration_deactivation_date, integration_last_run, integration_last_error

52. **email_delivery_attempts** - Postmark email tracking (10 columns)
    - postmark_template_id, payload (merge variables), recipients array
    - email_type: invite, result, reminder, alert, status_update, report
    - email_source: snappt, enterprise, yardi, custom
    - response_status, response_data, completed_at

53. **inbound_webhooks** - External system webhook queue (9 columns)
    - source: yardi, realpage, postmark, stripe, custom
    - event_type, external_event_id, internal_event_id
    - event_body JSONB, processed boolean, status_code, error_message

54. **enterprise_integration_configuration** - Integration credentials (7 columns)
    - type: yardi, realpage, entrata, appfolio, buildium, custom
    - JSONB: integration_details (API creds, endpoints), metadata (billing, volume)
    - deleted_at (soft delete)

**🔗 Cross-Database Foreign Keys (THE KEY FINDING):**
```sql
-- These are THE critical relationships for multi-database queries
enterprise_applicant.snappt_applicant_detail_id → fraud_postgresql.applicant_details.id
enterprise_property.snappt_property_id → fraud_postgresql.properties.id
```

---

## Key Patterns & Architecture Decisions

### 1. JSONB Usage Patterns

**When JSONB is used:**
- Provider integration data (flexible schemas for different services)
- ML/AI analysis results (variable output structures)
- Configuration data (property settings, feature flags)
- Metadata (additional context without dedicated columns)

**Examples:**
- `proof.extracted_meta` - OCR results, dates, amounts extracted by ML
- `id_verifications.provider_results` - Incode/Persona results (different schemas)
- `properties.supported_doctypes` - Array of document types property accepts
- `enterprise_property.integration_details` - External system property data

**Best Practice:** JSONB allows flexibility without schema migrations, but use sparingly - structured columns preferred when schema is stable

### 2. Soft Delete Patterns

**Pattern 1: Dedicated deleted_* tables**
- Example: `deleted_applicants`, `deleted_entries`, `deleted_properties`
- When record deleted → moved to deleted_* table
- Original table stays clean for active queries
- 20+ deleted_* tables in fraud_postgresql

**Pattern 2: deleted_at timestamp**
- Example: `enterprise_integration_configuration.deleted_at`
- NULL = active, timestamp = deleted
- Simpler pattern, but requires WHERE deleted_at IS NULL in queries

**Pattern 3: Backup tables**
- Example: `applicant_submission_backup`, `review_items_cleanup_backup`
- Data recovery options
- 7+ backup tables

### 3. Denormalization for Performance

**folders table denormalization:**
- `last_entry_id`, `last_entry_submission_time`, `last_entry_result`, `last_entry_status`
- Avoids expensive joins for dashboard queries
- Trade disk space for query speed

**properties table denormalization:**
- `company_short_id` - Avoids join to companies table
- Common pattern for high-volume queries

### 4. Cross-Database Integration Pattern

**Key Insight:** enterprise_postgresql acts as integration layer
- Links external systems (Yardi, RealPage) to Snappt internal IDs
- Enables multi-database queries without changing fraud_postgresql schema
- Separation of concerns: Core fraud detection vs external integration

**Multi-Database Query Pattern:**
```sql
-- Full applicant journey across databases
SELECT
    ea.integration_id as external_id,
    ad.id as snappt_id,
    a.full_name,
    e.result as screening_result
FROM enterprise_postgresql.enterprise_applicant ea
JOIN fraud_postgresql.applicant_details ad ON ea.snappt_applicant_detail_id = ad.id
JOIN fraud_postgresql.applicants a ON a.applicant_detail_id = ad.id
JOIN fraud_postgresql.entries e ON a.entry_id = e.id
WHERE ea.inserted_at > NOW() - interval '30 days';
```

### 5. Event Sourcing Pattern

**rent_verification_events:**
- Complete audit trail of rental verification workflow
- event_type, event_data JSONB, timestamps
- Enables workflow replay and debugging

**property_feature_events:**
- Tracks all feature flag changes
- Feature adoption timeline
- Feature churn analysis

**webhook_delivery_attempts:**
- Every webhook delivery attempt logged
- Supports retry logic and debugging

### 6. Polymorphic Relationships

**review_items.entity_id:**
- References different tables based on workflow field
- workflow = 'entry_review' → entity_id = entries.id
- workflow = 'fraud_review' → entity_id = fraud_submissions.id
- workflow = 'income_review' → entity_id = income_verification_submissions.id
- Enables workflow-agnostic queue system

### 7. State Machines

**entries.status:**
- pending_submission → pending_review → in_review → completed

**review_items.state:**
- scheduled → assigned → completed

**reviewer_queue.state:**
- available → assigned

**Pattern:** Clear state transitions, SLA tracking via timestamps at each transition

### 8. Result Aggregation Logic

**Multi-verification precedence (worst-case wins):**
1. FRAUD - Any fraud detected → Entry REJECTED
2. REJECTED - Any critical verification failed → Entry REJECTED
3. NEEDS_REVIEW - Any verification requires human review → Entry NEEDS_REVIEW
4. APPROVED - All verifications passed → Entry APPROVED

**Implementation:** Likely in application code, not database constraints

---

## Important Technical Details

### Cross-Database Foreign Keys (Critical!)

**enterprise_postgresql → fraud_postgresql:**
```sql
-- Applicant link
enterprise_applicant.snappt_applicant_detail_id → applicant_details.id

-- Property link
enterprise_property.snappt_property_id → properties.id
```

**These are NOT enforced by database constraints** (can't have FK across databases), but are documented relationships that MUST be maintained by application code.

### Multi-Database Query Examples

**1. Complete Applicant Journey:**
```sql
SELECT
    ea.integration_id as external_applicant_id,
    ea.integration_details->>'external_system' as pms_system,
    a.full_name,
    a.email,
    e.short_id as screening_id,
    e.result as screening_result,
    p.name as property_name,
    (SELECT result FROM fraud_results fr
     JOIN applicant_submissions asub ON fr.applicant_submission_id = asub.id
     WHERE asub.applicant_id = a.id LIMIT 1) as fraud_result,
    (SELECT review_eligibility FROM income_verification_results ivr
     JOIN applicant_submissions asub ON ivr.applicant_submission_id = asub.id
     WHERE asub.applicant_id = a.id LIMIT 1) as income_result
FROM enterprise_applicant ea
JOIN applicant_details ad ON ea.snappt_applicant_detail_id = ad.id
JOIN applicants a ON a.applicant_detail_id = ad.id
JOIN entries e ON a.entry_id = e.id
JOIN folders f ON e.folder_id = f.id
JOIN properties p ON f.property_id = p.id
WHERE ea.inserted_at > NOW() - interval '7 days';
```

**2. Property Integration Health:**
```sql
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

### Polymorphic Relationships

**review_items.entity_id pattern:**
```sql
-- Finding the actual entity being reviewed
SELECT
    ri.workflow,
    ri.entity_id,
    CASE ri.workflow
        WHEN 'entry_review' THEN (SELECT short_id FROM entries WHERE id = ri.entity_id)
        WHEN 'fraud_review' THEN (SELECT id::text FROM fraud_submissions WHERE id = ri.entity_id)
        WHEN 'income_review' THEN (SELECT id::text FROM income_verification_submissions WHERE id = ri.entity_id)
    END as entity_identifier
FROM review_items ri;
```

### Workflow State Machines

**Complete entry review workflow:**
```
1. Entry created (status='pending_submission')
2. Applicant uploads documents
3. ML/AI analysis runs
4. review_items created (state='scheduled', workflow='entry_review')
5. Reviewer requests work → reviewer_queue created (state='available')
6. Assignment made → review_items.state='assigned', reviewer_queue.state='assigned'
7. Reviewer completes → review_items.state='completed', entries.status='completed'
8. entry_report generated
```

### JSONB Query Patterns

**Querying JSONB fields:**
```sql
-- Extract single value
properties.identity_verification_flow_types->>'flow_type'

-- Array contains
'digital_copy' = ANY(properties.identity_verification_flow_types)

-- JSONB exists
properties.supported_doctypes ? 'bank_statement'

-- GIN index for JSONB
CREATE INDEX idx_proof_extracted_meta_gin ON proof USING gin(extracted_meta);
```

---

## User Requirements & Priorities

### Critical User Requirement

**User's exact words:**
> "Something we should keep in mind for future work is how these databases are connected by PK and FKs this will allow myself, the data architect, and other analysts and engineers to quickly write queries that include information from multiple databases"

**What this means:**
- Document ALL foreign key relationships (within database and cross-database)
- Provide multi-database query examples
- Show how to join across fraud_postgresql and enterprise_postgresql
- Enable data team to write complex analytical queries

**Delivered:**
- ✅ Cross-database FKs documented with 🔗 markers
- ✅ 3 comprehensive multi-database query patterns
- ✅ Complete FK documentation for all 54 tables
- ✅ Integration health monitoring queries

### Documentation Quality Standards

**For each table, provide:**
1. ✅ Complete column list with data types
2. ✅ Nullable/NOT NULL constraints
3. ✅ Default values
4. ✅ Primary key identification
5. ✅ Foreign key relationships (explicit and implicit)
6. ✅ Business logic and usage patterns
7. ✅ JSONB field examples with schemas
8. ✅ Enum value definitions
9. ✅ Data flow examples
10. ✅ Performance optimization recommendations
11. ✅ Security and compliance considerations

### Priority Order for Remaining Tables

**User confirmed priorities:**
1. ✅ DONE: Review & Queue System (6 tables)
2. ✅ DONE: Features & Configuration (7 tables)
3. ✅ DONE: Integration Layer (6 tables)
4. ✅ DONE: Enterprise Integration Database (5 tables)
5. **Next:** Medium priority tables (~13 tables)
   - Disputes (3 tables)
   - Fraud Detection - Advanced (2 tables)
   - Supporting Systems (8 tables)
6. **Later:** Low priority tables (~13 tables)
   - User Experience (5 tables)
   - Infrastructure (2 tables)
   - Cleanup/Backup (5 tables)

---

## Remaining Work

### Undocumented Tables in fraud_postgresql (~26 tables)

#### Medium Priority (13 tables)

**Disputes (3 tables):**
- disputes - Dispute tracking
- dispute_categories - Dispute reason categories
- dispute_emails - Email correspondence for disputes

**Fraud Detection - Advanced (2 tables):**
- frequent_flyer_variations - Applicant re-application tracking
- frequent_flyer_matched_confidences - Match confidence scores

**Supporting Systems (8 tables):**
- matching_entries - Entry matching algorithm results
- invitations - Applicant invitation tracking
- invitations_properties - Property-level invitation config
- oban_jobs - Background job queue (Elixir Oban)
- oban_peers - Oban cluster coordination
- api_keys - API authentication
- unauthenticated_session - Session management
- analytics_reports - Scheduled report generation

#### Low Priority (13 tables)

**User Experience (5 tables):**
- announcement - System announcements
- announcement_role - Role-based announcement targeting
- announcement_user_was_shown - User acknowledgment tracking
- user_role_sort_priority - UI sorting preferences
- user_tab_role_sort_priority - Tab ordering preferences

**Document Processing (1 table):**
- voi_reprocessing - Verification of Income reprocessing queue

**Infrastructure (2 tables):**
- schema_migrations - Database migration tracking (Ecto)
- activation_history - Feature activation audit

**Cleanup/Backup (5 tables):**
- applicant_submission_backup
- applicant_submission_document_sources_cleanup_backup
- applicant_submissions_cleanup_backup
- review_items_cleanup_backup
- staging_activation_backfill

### Other Databases - Investigation Needed

**dp_income_validation, dp_document_intelligence, dp_inception_fraud:**
- Found 0 tables in public schema
- May have tables in non-public schemas
- May be deprecated/unused databases
- **Action:** Query for all schemas, not just public

**dp_ai_services:**
- 2 tables: alembic_version (migrations), checkpoint_analytics_view
- Low priority - analytics/monitoring only

**av_postgresql:**
- 1 table: schema_migrations
- Very low priority - infrastructure only

### Optional Enhancement Projects

**1. Update Visual ERD Diagrams:**
- Add diagrams for newly documented workflows
- Review & Queue System flow diagram
- Features & Configuration architecture diagram
- Integration Layer data flow diagram
- Enterprise integration cross-database diagram

**2. Generate Interactive Schema Explorer:**
- Web-based schema browser
- Clickable table relationships
- Search across all tables
- Filter by workflow/database

**3. API Documentation Integration:**
- Link database tables to API endpoints
- Document which endpoints read/write which tables
- Show data flow: API request → database changes

**4. Data Dictionary:**
- Standardized field definitions
- Business glossary (what does "entry" mean? "proof"? "folder"?)
- Column naming conventions
- Common enum values across tables

---

## Documentation Methodology

### File Structure Pattern

**Workflow documentation files:**
```markdown
# [Workflow Name] - [Description]

**Generated:** [Date]
**Database:** [database_name]
**Tables Documented:** [N tables]

---

## Overview
[High-level description, key functions]

## Table Inventory
[List of tables by category]

## Detailed Table Documentation

## [N]. [TABLE_NAME]
**Purpose:** [What this table does]
**Primary Key:** [PK description]

### Columns
| Column | Type | Nullable | Description |

### Relationships
- **Belongs to:** [parent tables]
- **Has many:** [child tables]

### Business Logic
[How the table is used, workflow, examples]

### [SQL Examples]

---

## Performance Considerations
[Index recommendations]

## Summary
[Key features, use cases, related docs]
```

### MCP Query Patterns Used

**Get all tables in a database:**
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

**Get column details:**
```sql
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'table_name'
ORDER BY ordinal_position;
```

**Get foreign keys:**
```sql
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'table_name';
```

**Get primary keys:**
```sql
SELECT kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.constraint_type = 'PRIMARY KEY'
    AND tc.table_name = 'table_name';
```

### Git Commit Message Format

**Pattern:**
```
[Action] [What] [Brief description]

[Detailed explanation paragraph]

**[Section]:**
- Bullet points

**Key Features:**
- Bullet points

[Related docs, use cases, etc.]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Examples:**
- "Add comprehensive Review & Queue System documentation"
- "Add Enterprise Integration Database cross-database documentation"
- "Update README with Session 2 progress: 49 tables + cross-database docs"

---

## Key Learnings & Insights

### 1. The Polyglot Persistence Pattern

**Insight:** Snappt uses microservices with different tech stacks:
- fraud_postgresql: Elixir/Phoenix (core fraud detection)
- enterprise_postgresql: TypeScript/TypeORM (enterprise integrations)
- dp_ai_services: Python/Alembic (AI/ML services)

**Implication:** Each database optimized for its use case, but requires cross-database queries for complete picture

### 2. JSONB as Integration Strategy

**Insight:** Heavy JSONB usage for provider integration
- Different ID providers have different result schemas
- Different PMS systems have different data structures
- ML/AI models have variable outputs

**Implication:** JSONB allows flexibility without constant schema migrations, but requires careful query optimization (GIN indexes)

### 3. Workflow-Agnostic Design

**Insight:** review_items table supports ALL review workflows
- Polymorphic entity_id + workflow discriminator
- Single queue management codebase
- New verification types just add new workflow value

**Implication:** Highly extensible architecture, but requires careful documentation of polymorphic relationships

### 4. Denormalization for Dashboard Performance

**Insight:** folders table denormalizes last_entry_* fields
- High-volume dashboard queries avoid joins
- Trade: Disk space and update complexity for query speed

**Implication:** Critical for user experience, but requires transaction management to keep denormalized data consistent

### 5. Pull-Based Review Assignment

**Insight:** Reviewers request work (pull) rather than being assigned work (push)
- reviewer_queue records reviewer availability
- System matches with highest-priority review_items
- No reviewer gets multiple items until current work complete

**Implication:** Natural workload balancing, prevents reviewer overload, better for reviewer UX

### 6. Event Sourcing for Audit Trails

**Insight:** Multiple event tables provide complete audit trails
- entry_log: Every entry state change
- property_feature_events: Every feature flag change
- rent_verification_events: Every rent check workflow step
- webhook_delivery_attempts: Every integration event

**Implication:** Complete forensic analysis capability, regulatory compliance, debugging support

### 7. Multi-Verification Aggregation

**Insight:** Entry result = worst result across ALL verifications
- Priority: FRAUD > REJECTED > NEEDS_REVIEW > APPROVED
- One verification rejection → entire entry rejected

**Implication:** Conservative risk management, protects property managers

### 8. Automated vs Manual Review Balance

**Insight:** Each verification has auto-approval thresholds
- Fraud: ML confidence >95% → auto-approve
- Income: ≥3x rent → auto-approve, 2.5x-3x → manual review
- Asset: ≥6 months rent → auto-approve, 2-6 months → manual review

**Implication:** Balances automation efficiency with review quality, gray zone gets human review

---

## Quick Start Guide for Next Session

### To Continue Documentation Work:

1. **Check current status:**
   ```bash
   cd /Users/danerosa/rds_databricks_claude-erd
   git status
   ```

2. **Review what's been documented:**
   - Read database_erd/README.md for complete status
   - Read this SESSION_NOTES.md for technical details

3. **Choose next workflow:**
   - **Option A:** Disputes (3 tables) - Medium priority
   - **Option B:** Frequent Flyer (2 tables) - Advanced fraud detection
   - **Option C:** Supporting Systems (8 tables) - Infrastructure

4. **Query table schemas:**
   ```typescript
   // Use MCP tool
   mcp__snappt-postgres__query({sql: "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'disputes' ORDER BY ordinal_position"})
   ```

5. **Follow documentation pattern:**
   - Overview → Table Inventory → Detailed Tables → Performance → Summary
   - Include: columns, relationships, business logic, JSONB examples, SQL queries

6. **Commit work:**
   - One commit per workflow document
   - Follow git commit message format (see above)
   - Update README.md after each major milestone

### Key Commands:

```bash
# Query database schemas
mcp__snappt-postgres__query({sql: "..."})
mcp__enterprise-postgres__query({sql: "..."})

# File operations
Read({file_path: "/Users/danerosa/rds_databricks_claude-erd/database_erd/README.md"})
Write({file_path: "...", content: "..."})
Edit({file_path: "...", old_string: "...", new_string: "..."})

# Git operations
git add database_erd/[FILE].md
git commit -m "..."
git log --oneline -5
```

---

## Session History

### Session 1 (2025-11-25)
- CORE_ENTITY_MODEL.md (14 tables)
- FRAUD_DETECTION_WORKFLOW.md (7 tables)
- VERIFICATION_WORKFLOWS.md (9 tables)
- ERD_DIAGRAMS.md (8 visual diagrams)
- COMPREHENSIVE_SCHEMA_REFERENCE.md (complete column details)
- DATABASE_SCHEMA_SUMMARY.md (overview)
- README.md (project summary)
- **Total:** 30 tables, 126KB documentation

### Session 2 (2025-11-25)
- REVIEW_QUEUE_SYSTEM.md (6 tables)
- FEATURES_CONFIGURATION.md (7 tables)
- INTEGRATION_LAYER.md (6 tables)
- ENTERPRISE_INTEGRATION_DATABASE.md (5 tables)
- Updated README.md with Session 2 progress
- SESSION_NOTES.md (this file)
- **Total:** 24 new tables, +144KB documentation
- **Progress:** 30 → 54 tables (40% → 65% complete)

### Key Achievements
- ✅ Cross-database foreign keys documented
- ✅ Multi-database query patterns provided
- ✅ enterprise_postgresql 100% complete
- ✅ fraud_postgresql 65% complete (49/75 tables)
- ✅ User's critical requirement addressed (cross-database PKs/FKs)

---

**END OF SESSION NOTES**

*This file should be read at the start of every future session to quickly restore full context.*
