# Cross-Database Relationships

**Generated:** 2025-11-25
**Purpose:** Comprehensive mapping of foreign key relationships across all Snappt databases
**Databases Covered:** 6 databases (fraud_postgresql, enterprise_postgresql, dp_income_validation, dp_document_intelligence, av_postgres, dp_ai_services)

---

## Overview

Snappt uses a microservices architecture with separate databases for different services. While these databases are physically separate, they maintain logical relationships through application-enforced foreign keys. This document maps all cross-database relationships to enable multi-database query writing.

**Key Insight:** Cross-database foreign keys are NOT enforced by database constraints but must be maintained by application code.

---

## Table of Contents

1. [Relationship Summary](#relationship-summary)
2. [fraud_postgresql as Central Hub](#fraud_postgresql-as-central-hub)
3. [Detailed Relationship Mappings](#detailed-relationship-mappings)
4. [Multi-Database Query Patterns](#multi-database-query-patterns)
5. [Data Flow Diagrams](#data-flow-diagrams)

---

## Relationship Summary

### Database Dependency Graph

```
                    fraud_postgresql (CENTRAL HUB)
                            ↑    ↑    ↑    ↑
                            │    │    │    │
        ┌───────────────────┴────┴────┴────┴───────────────────┐
        │                   │    │    │    │                   │
        │                   │    │    │    │                   │
enterprise_postgresql  dp_income_validation  dp_document_intelligence  av_postgres  dp_ai_services
    (integration)        (income calc)      (asset calc)         (ML fraud)   (agents)
```

**Central Hub:** fraud_postgresql serves as the primary database with core entities (applicants, documents, entries, properties)

**Satellite Services:** All microservice databases reference fraud_postgresql entities

---

## fraud_postgresql as Central Hub

### Core Entities Referenced by Other Databases

**1. applicants (fraud_postgresql.applicants)**
Referenced by:
- enterprise_postgresql.enterprise_applicant.snappt_applicant_detail_id → applicant_details.id → applicants.applicant_detail_id
- dp_document_intelligence.asset_verifications.applicant_id → applicants.id
- dp_document_intelligence.asset_verification_review.applicant_id → applicants.id
- dp_document_intelligence.inferences.applicant_id → applicants.id
- dp_ai_services (implicit via agent execution)

**2. proof / documents (fraud_postgresql.proof)**
Referenced by:
- dp_income_validation.calculation_documents.document_id → proof.id
- dp_document_intelligence.statements.document_id → proof.id
- dp_document_intelligence.inferences.document_id → proof.id
- av_postgres.document_properties.upload_identifier → proof.id
- av_postgres.document_errors.upload_identifier → proof.id
- av_postgres.training_documents.proof_id → proof.id
- dp_ai_services (implicit via agent execution)

**3. properties (fraud_postgresql.properties)**
Referenced by:
- enterprise_postgresql.enterprise_property.snappt_property_id → properties.id

**4. income_verification_submissions (fraud_postgresql.income_verification_submissions)**
Referenced by:
- dp_income_validation.calculations.reference_id → income_verification_submissions.id

---

## Detailed Relationship Mappings

### 1. enterprise_postgresql ↔ fraud_postgresql

**Purpose:** Enterprise integration layer for external PMS/CRM systems

#### Relationships

| Source Table | Source Column | Target Database | Target Table | Target Column | Data Type | Description |
|--------------|---------------|-----------------|--------------|---------------|-----------|-------------|
| enterprise_applicant | snappt_applicant_detail_id | fraud_postgresql | applicant_details | id | uuid | Links external applicant to Snappt applicant |
| enterprise_property | snappt_property_id | fraud_postgresql | properties | id | uuid | Links external property to Snappt property |

#### Query Example

```sql
-- Complete applicant journey across enterprise and fraud databases
SELECT
    -- External system
    ea.integration_id as external_applicant_id,
    ea.integration_details->>'external_system' as pms_system,

    -- Snappt system
    ad.id as snappt_applicant_detail_id,
    a.id as snappt_applicant_id,
    a.full_name,
    a.email,

    -- Screening result
    e.short_id as entry_id,
    e.result as screening_result,
    p.name as property_name

FROM enterprise_postgresql.enterprise_applicant ea
JOIN fraud_postgresql.applicant_details ad
    ON ea.snappt_applicant_detail_id = ad.id
JOIN fraud_postgresql.applicants a
    ON a.applicant_detail_id = ad.id
JOIN fraud_postgresql.entries e
    ON a.entry_id = e.id
JOIN fraud_postgresql.folders f
    ON e.folder_id = f.id
JOIN fraud_postgresql.properties p
    ON f.property_id = p.id
WHERE ea.inserted_at > NOW() - interval '7 days';
```

---

### 2. dp_income_validation ↔ fraud_postgresql

**Purpose:** Income calculation microservice

#### Relationships

| Source Table | Source Column | Target Database | Target Table | Target Column | Data Type | Description |
|--------------|---------------|-----------------|--------------|---------------|-----------|-------------|
| calculations | reference_id | fraud_postgresql | income_verification_submissions | id | uuid | Links calculation to income verification request |
| calculation_documents | document_id | fraud_postgresql | proof | id | uuid | Links calculation document to source document |

**Note:** reference_id likely links to income_verification_submissions.id but could also link to applicant_submissions.id depending on implementation.

#### Query Example

```sql
-- Income calculation with source documents
SELECT
    -- Income calculation
    c.id as calculation_id,
    c.gross_monthly_income,
    c.net_monthly_income,
    c.consecutive_days,
    c.total_days,

    -- Source verification request
    ivs.id as verification_id,
    ivs.review_method,

    -- Applicant
    a.full_name as applicant_name,
    a.email,

    -- Documents used
    COUNT(cd.id) as document_count,
    STRING_AGG(p.type::text, ', ') as document_types

FROM dp_income_validation.iv.calculations c
JOIN fraud_postgresql.income_verification_submissions ivs
    ON c.reference_id = ivs.id::uuid
JOIN fraud_postgresql.applicant_submissions asub
    ON ivs.applicant_submission_id = asub.id
JOIN fraud_postgresql.applicants a
    ON asub.applicant_id = a.id
LEFT JOIN dp_income_validation.iv.calculation_documents cd
    ON c.id = cd.calculation_id
LEFT JOIN fraud_postgresql.proof p
    ON cd.document_id = p.id
WHERE c.inserted_at > NOW() - interval '30 days'
GROUP BY c.id, c.gross_monthly_income, c.net_monthly_income,
         c.consecutive_days, c.total_days, ivs.id, ivs.review_method,
         a.full_name, a.email;
```

---

### 3. dp_document_intelligence ↔ fraud_postgresql

**Purpose:** Asset verification microservice with AI/ML document analysis

#### Relationships

| Source Table | Source Column | Target Database | Target Table | Target Column | Data Type | Description |
|--------------|---------------|-----------------|--------------|---------------|-----------|-------------|
| asset_verifications | applicant_id | fraud_postgresql | applicants | id | varchar(255) → uuid | Links asset verification to applicant |
| asset_verification_review | applicant_id | fraud_postgresql | applicants | id | uuid | Links review to applicant |
| statements | document_id | fraud_postgresql | proof | id | varchar → uuid | Links bank statement to source document |
| inferences | document_id | fraud_postgresql | proof | id | varchar → uuid | Links AI inference to source document |
| inferences | applicant_id | fraud_postgresql | applicants | id | varchar → uuid | Links AI inference to applicant |

**Data Type Note:** applicant_id and document_id stored as varchar in dp_document_intelligence but reference UUID in fraud_postgresql. Cast required for joins.

#### Query Example

```sql
-- Asset verification with AI metrics
SELECT
    -- Asset verification
    av.id as verification_id,
    av.applicant_name,
    av.total_verified_assets,
    av.status as verification_status,

    -- Applicant details
    a.id as applicant_id,
    a.email,
    e.short_id as entry_id,

    -- AI processing metrics
    COUNT(DISTINCT ao.id) as ai_operations,
    SUM(ao.input_tokens + ao.output_tokens) as total_tokens,
    AVG(CASE WHEN ao.success THEN 1.0 ELSE 0.0 END) as ai_success_rate,

    -- Document analysis
    COUNT(DISTINCT s.id) as statements_analyzed,
    COUNT(DISTINCT acc.id) as accounts_identified

FROM dp_document_intelligence.di.asset_verifications av
JOIN fraud_postgresql.applicants a
    ON av.applicant_id::uuid = a.id
JOIN fraud_postgresql.entries e
    ON a.entry_id = e.id
LEFT JOIN dp_document_intelligence.di.ai_operations ao
    ON av.id = ao.asset_verification_id
LEFT JOIN dp_document_intelligence.di.statements s
    ON av.id = s.asset_verification_id
LEFT JOIN dp_document_intelligence.di.accounts acc
    ON av.id = acc.asset_verification_id
WHERE av.created_at > NOW() - interval '30 days'
GROUP BY av.id, av.applicant_name, av.total_verified_assets,
         av.status, a.id, a.email, e.short_id;
```

---

### 4. av_postgres ↔ fraud_postgresql

**Purpose:** ML fraud detection scoring and rulings

#### Relationships

| Source Table | Source Column | Target Database | Target Table | Target Column | Data Type | Description |
|--------------|---------------|-----------------|--------------|---------------|-----------|-------------|
| document_properties | upload_identifier | fraud_postgresql | proof | id | uuid | Links ML analysis to source document |
| document_errors | upload_identifier | fraud_postgresql | proof | id | uuid | Links processing error to source document |
| training_documents | proof_id | fraud_postgresql | proof | id | uuid | Links training data to source document |

#### Query Example

```sql
-- Complete fraud detection pipeline
SELECT
    -- Document
    p.id as proof_id,
    p.type as document_type,
    p.result as final_result,

    -- Applicant
    a.full_name as applicant_name,
    e.short_id as entry_id,

    -- ML fraud analysis
    dp.embedded_properties->>'producer' as pdf_producer,
    ds.score as ml_fraud_score,
    ds.scoring_api_version as model_version,
    ds.predictions->>'fraud_indicators' as fraud_indicators,
    drc.name as automated_ruling,

    -- Processing errors
    COALESCE(errors.error_count, 0) as processing_errors

FROM fraud_postgresql.proof p
JOIN fraud_postgresql.entries e ON p.entry_id = e.id
JOIN fraud_postgresql.applicants a ON e.id = (
    SELECT entry_id FROM fraud_postgresql.applicants WHERE id = a.id LIMIT 1
)
-- Cross-database joins
LEFT JOIN av_postgres.av.document_properties dp
    ON p.id = dp.upload_identifier
LEFT JOIN av_postgres.av.document_scores ds
    ON dp.id = ds.document_id
LEFT JOIN av_postgres.av.document_rulings dr
    ON dp.id = dr.document_id
LEFT JOIN av_postgres.av.document_ruling_codes drc
    ON dr.ruling = drc.code
LEFT JOIN (
    SELECT upload_identifier, COUNT(*) as error_count
    FROM av_postgres.av.document_errors
    GROUP BY upload_identifier
) errors ON p.id = errors.upload_identifier
WHERE p.inserted_at > NOW() - interval '7 days'
ORDER BY ds.score DESC NULLS LAST;
```

---

### 5. dp_ai_services ↔ fraud_postgresql

**Purpose:** AI agent configuration and workflow state management

#### Relationships

**Implicit Relationships (via agent execution):**
- Agents process documents: document_id references fraud_postgresql.proof.id
- Agents process applicants: applicant_id references fraud_postgresql.applicants.id
- Agent execution metadata stored in checkpoint.checkpoints.metadata (JSONB)

**Note:** No explicit foreign keys. Relationships maintained through:
1. Message queue payloads (document_id, applicant_id)
2. Checkpoint metadata (JSONB fields)
3. MLflow experiment tags

#### Query Example

```sql
-- Agent execution with checkpoint state
SELECT
    -- Agent configuration
    a.name as agent_name,
    av.variant_name,
    av.is_champion,

    -- Workflow state
    c.thread_id,
    c.checkpoint_id,
    c.checkpoint->>'current_node' as current_node,
    c.metadata->>'timestamp' as last_checkpoint,

    -- Execution context (from metadata)
    c.metadata->>'document_id' as document_id,
    c.metadata->>'applicant_id' as applicant_id,

    -- Link to fraud_postgresql (if IDs present)
    p.type as document_type,
    a_fraud.full_name as applicant_name

FROM dp_ai_services.agent.checkpoints c
JOIN dp_ai_services.agent.agent_variants av
    ON c.metadata->>'agent_variant_id' = av.id::text
JOIN dp_ai_services.agent.agents a
    ON av.agent_id = a.id
-- Optional joins to fraud_postgresql if IDs in metadata
LEFT JOIN fraud_postgresql.proof p
    ON (c.metadata->>'document_id')::uuid = p.id
LEFT JOIN fraud_postgresql.applicants a_fraud
    ON (c.metadata->>'applicant_id')::uuid = a_fraud.id
WHERE c.checkpoint_ns = 'income_extraction'
    AND c.metadata->>'document_id' IS NOT NULL
ORDER BY c.checkpoint_id DESC
LIMIT 100;
```

---

## Multi-Database Query Patterns

### Pattern 1: Complete Applicant Journey

**Across all databases: Enterprise → Fraud → Income → Assets → ML → Agents**

```sql
SELECT
    -- External system
    ea.integration_id as external_id,
    ea.integration_details->>'external_system' as source_system,

    -- Core applicant
    a.id as applicant_id,
    a.full_name,
    a.email,
    e.short_id as entry_id,
    e.result as final_result,
    p.name as property_name,

    -- Income verification
    ic.gross_monthly_income,
    ic.net_monthly_income,
    ivr.review_eligibility as income_eligibility,

    -- Asset verification
    av_di.total_verified_assets,
    av_di.status as asset_status,

    -- Fraud detection
    ds.score as fraud_score,
    drc.name as fraud_ruling,

    -- Processing metrics
    COUNT(DISTINCT ic_docs.id) as income_documents,
    COUNT(DISTINCT av_accts.id) as asset_accounts,
    COUNT(DISTINCT dp.id) as fraud_analyzed_documents

FROM enterprise_postgresql.enterprise_applicant ea
JOIN fraud_postgresql.applicant_details ad
    ON ea.snappt_applicant_detail_id = ad.id
JOIN fraud_postgresql.applicants a
    ON a.applicant_detail_id = ad.id
JOIN fraud_postgresql.entries e
    ON a.entry_id = e.id
JOIN fraud_postgresql.folders f
    ON e.folder_id = f.id
JOIN fraud_postgresql.properties p
    ON f.property_id = p.id

-- Income verification
LEFT JOIN fraud_postgresql.applicant_submissions asub
    ON a.id = asub.applicant_id
LEFT JOIN fraud_postgresql.income_verification_submissions ivs
    ON asub.id = ivs.applicant_submission_id
LEFT JOIN dp_income_validation.iv.calculations ic
    ON ivs.id::uuid = ic.reference_id
LEFT JOIN fraud_postgresql.income_verification_results ivr
    ON asub.id = ivr.applicant_submission_id
LEFT JOIN dp_income_validation.iv.calculation_documents ic_docs
    ON ic.id = ic_docs.calculation_id

-- Asset verification
LEFT JOIN dp_document_intelligence.di.asset_verifications av_di
    ON a.id::text = av_di.applicant_id
LEFT JOIN dp_document_intelligence.di.accounts av_accts
    ON av_di.id = av_accts.asset_verification_id

-- Fraud detection
LEFT JOIN fraud_postgresql.proof proof
    ON e.id = proof.entry_id
LEFT JOIN av_postgres.av.document_properties dp
    ON proof.id = dp.upload_identifier
LEFT JOIN av_postgres.av.document_scores ds
    ON dp.id = ds.document_id
LEFT JOIN av_postgres.av.document_rulings dr
    ON dp.id = dr.document_id
LEFT JOIN av_postgres.av.document_ruling_codes drc
    ON dr.ruling = drc.code

WHERE ea.inserted_at > NOW() - interval '30 days'
GROUP BY ea.integration_id, ea.integration_details, a.id, a.full_name,
         a.email, e.short_id, e.result, p.name, ic.gross_monthly_income,
         ic.net_monthly_income, ivr.review_eligibility, av_di.total_verified_assets,
         av_di.status, ds.score, drc.name
ORDER BY ea.inserted_at DESC;
```

### Pattern 2: Document Processing Pipeline

**Track a document through all processing stages**

```sql
WITH document_analysis AS (
    SELECT
        -- Source document
        p.id as proof_id,
        p.type as document_type,
        p.file as document_path,
        p.inserted_at as uploaded_at,

        -- Applicant context
        a.full_name as applicant_name,
        e.short_id as entry_id,

        -- Income processing (if paystub/bank statement)
        ic_doc.gross_income as extracted_income,
        ic_doc.start_date as income_period_start,
        ic_doc.end_date as income_period_end,

        -- Asset processing (if bank statement)
        stmt.end_balance as statement_balance,
        stmt.end_date as statement_date,

        -- ML fraud analysis
        dp.embedded_properties->>'producer' as pdf_producer,
        ds.score as fraud_score,
        drc.name as fraud_ruling,

        -- AI inference
        inf.confidence_score as ai_confidence,
        inf.sampled_for_review,

        -- Processing errors
        de.error_message as processing_error

    FROM fraud_postgresql.proof p
    JOIN fraud_postgresql.entries e ON p.entry_id = e.id
    JOIN fraud_postgresql.applicants a ON e.id = (
        SELECT entry_id FROM fraud_postgresql.applicants WHERE id = a.id LIMIT 1
    )

    -- Income document analysis
    LEFT JOIN dp_income_validation.iv.calculation_documents ic_doc
        ON p.id = ic_doc.document_id

    -- Asset document analysis
    LEFT JOIN dp_document_intelligence.di.statements stmt
        ON p.id::text = stmt.document_id

    -- ML fraud detection
    LEFT JOIN av_postgres.av.document_properties dp
        ON p.id = dp.upload_identifier
    LEFT JOIN av_postgres.av.document_scores ds
        ON dp.id = ds.document_id
    LEFT JOIN av_postgres.av.document_rulings dr
        ON dp.id = dr.document_id
    LEFT JOIN av_postgres.av.document_ruling_codes drc
        ON dr.ruling = drc.code

    -- AI inference
    LEFT JOIN dp_document_intelligence.di.inferences inf
        ON p.id::text = inf.document_id

    -- Processing errors
    LEFT JOIN av_postgres.av.document_errors de
        ON p.id = de.upload_identifier

    WHERE p.inserted_at > NOW() - interval '7 days'
)
SELECT * FROM document_analysis
ORDER BY uploaded_at DESC;
```

### Pattern 3: Service Health Dashboard

**Monitor processing across all microservices**

```sql
SELECT
    'Income Validation' as service,
    COUNT(DISTINCT c.id) as total_processed,
    COUNT(DISTINCT CASE WHEN c.status_code = 200 THEN c.id END) as successful,
    COUNT(DISTINCT CASE WHEN c.status_code != 200 THEN c.id END) as failed,
    AVG(EXTRACT(EPOCH FROM (
        SELECT MAX(created_at) - MIN(created_at)
        FROM dp_income_validation.iv.calculation_status_details csd
        WHERE csd.asset_verification_id = c.id
    ))) / 60 as avg_processing_minutes
FROM dp_income_validation.iv.calculations c
WHERE c.inserted_at > NOW() - interval '24 hours'

UNION ALL

SELECT
    'Asset Verification' as service,
    COUNT(DISTINCT av.id) as total_processed,
    COUNT(DISTINCT CASE WHEN av.status = 'COMPLETED' THEN av.id END) as successful,
    COUNT(DISTINCT CASE WHEN av.status != 'COMPLETED' THEN av.id END) as failed,
    AVG(EXTRACT(EPOCH FROM (av.updated_at - av.created_at))) / 60 as avg_processing_minutes
FROM dp_document_intelligence.di.asset_verifications av
WHERE av.created_at > NOW() - interval '24 hours'

UNION ALL

SELECT
    'Fraud Detection' as service,
    COUNT(DISTINCT dp.id) as total_processed,
    COUNT(DISTINCT CASE WHEN ds.score IS NOT NULL THEN dp.id END) as successful,
    COUNT(DISTINCT de.id) as failed,
    NULL as avg_processing_minutes
FROM av_postgres.av.document_properties dp
LEFT JOIN av_postgres.av.document_scores ds ON dp.id = ds.document_id
LEFT JOIN av_postgres.av.document_errors de ON dp.upload_identifier = de.upload_identifier
WHERE dp.inserted_at > NOW() - interval '24 hours';
```

---

## Data Flow Diagrams

### Complete Verification Flow

```
1. APPLICANT ONBOARDING
   ┌────────────────────────────────────────┐
   │ enterprise_postgresql                  │
   │ - enterprise_applicant created         │
   │ - snappt_applicant_detail_id stored    │
   └───────────────┬────────────────────────┘
                   │
                   ▼
   ┌────────────────────────────────────────┐
   │ fraud_postgresql                       │
   │ - applicant_details created            │
   │ - applicants created                   │
   │ - entry created                        │
   │ - applicant_submissions created        │
   └───────────────┬────────────────────────┘
                   │
                   ▼
2. DOCUMENT UPLOAD & ANALYSIS
   ┌────────────────────────────────────────┐
   │ fraud_postgresql                       │
   │ - proof (document) created             │
   │ - Triggers microservice processing     │
   └─────┬──────────┬──────────┬────────────┘
         │          │          │
         │          │          └──────────────────┐
         │          │                             │
         ▼          ▼                             ▼
   ┌─────────┐  ┌──────────────┐      ┌──────────────────┐
   │ ML      │  │ Income       │      │ Asset            │
   │ Fraud   │  │ Extraction   │      │ Extraction       │
   │         │  │              │      │                  │
   │ av_     │  │ dp_income_   │      │ dp_document_     │
   │ postgres│  │ validation   │      │ intelligence     │
   └─────┬───┘  └──────┬───────┘      └────────┬─────────┘
         │             │                        │
         │             │                        │
         ▼             ▼                        ▼
   [ML Score]   [Income Calc]           [Asset Calc]
   [Ruling]     [Status]                [Status]
         │             │                        │
         │             │                        │
         └─────────────┴────────────────────────┘
                       │
                       ▼
3. RESULTS AGGREGATION
   ┌────────────────────────────────────────┐
   │ fraud_postgresql                       │
   │ - fraud_results aggregated             │
   │ - income_verification_results          │
   │ - asset_verification_results           │
   │ - entry.result = worst case            │
   └───────────────┬────────────────────────┘
                   │
                   ▼
4. REPORTING & INTEGRATION
   ┌────────────────────────────────────────┐
   │ enterprise_postgresql                  │
   │ - enterprise_applicant updated         │
   │ - final_status, denial_reason          │
   └────────────────────────────────────────┘
```

### Agent Processing Flow

```
┌─────────────────────────────────────────────┐
│ fraud_postgresql                            │
│ - proof (document) available                │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ dp_ai_services                              │
│ - agent receives document_id                │
│ - agent_variant selected (champion/test)    │
│ - workflow starts, checkpoint created       │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ Processing Nodes (LangGraph)         │
│ 1. Parse document                    │
│ 2. Extract data (LLM inference)      │
│ 3. Validate extraction               │
│ 4. Format results                    │
│                                      │
│ (Checkpoints saved after each node)  │
└──────────────┬───────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ Results written to target microservice DB:  │
│ - dp_income_validation (income results)     │
│ - dp_document_intelligence (asset results)  │
│ - av_postgres (fraud scores)                │
└─────────────────────────────────────────────┘
```

---

## Summary

### Key Takeaways

**1. fraud_postgresql is the Central Hub**
- All microservices reference core entities (applicants, documents, properties)
- Provides master data for distributed processing
- Results aggregated back into fraud_postgresql

**2. Data Type Consistency**
- UUIDs primary throughout fraud_postgresql
- Some microservices store UUIDs as varchar/text (requires casting)
- Always cast when joining: `varchar_field::uuid = uuid_field`

**3. Query Performance Considerations**
- Cross-database queries can be expensive
- Consider caching frequently accessed relationships
- Use materialized views for complex multi-database reports
- Denormalize when necessary (e.g., enterprise_applicant stores external ID)

**4. Application-Level Integrity**
- No database-enforced foreign key constraints across databases
- Application code must maintain referential integrity
- Test cross-database relationships thoroughly
- Monitor orphaned records regularly

**5. Microservice Independence**
- Each service can be deployed/scaled independently
- Database failures isolated to specific services
- Eventual consistency model for cross-service data

### Total Cross-Database Relationships

- **enterprise_postgresql → fraud_postgresql:** 2 relationships
- **dp_income_validation → fraud_postgresql:** 2 relationships
- **dp_document_intelligence → fraud_postgresql:** 5 relationships
- **av_postgres → fraud_postgresql:** 3 relationships
- **dp_ai_services → fraud_postgresql:** Implicit via execution context

**Total: 12+ explicit cross-database foreign key relationships**

---

## Related Documentation

- [README.md](README.md) - Project overview and all databases
- [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md) - fraud_postgresql core entities
- [ENTERPRISE_INTEGRATION_DATABASE.md](ENTERPRISE_INTEGRATION_DATABASE.md) - enterprise_postgresql
- [DP_INCOME_VALIDATION.md](DP_INCOME_VALIDATION.md) - Income calculation microservice
- [DP_DOCUMENT_INTELLIGENCE.md](DP_DOCUMENT_INTELLIGENCE.md) - Asset verification microservice
- [AV_POSTGRES.md](AV_POSTGRES.md) - ML fraud detection microservice
- [DP_AI_SERVICES.md](DP_AI_SERVICES.md) - AI agent management

---

**Generated:** 2025-11-25
**Cross-Database Relationships:** 12+ explicit relationships documented
**Databases Covered:** 6 (fraud_postgresql, enterprise_postgresql, dp_income_validation, dp_document_intelligence, av_postgres, dp_ai_services)
