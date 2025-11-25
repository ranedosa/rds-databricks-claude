# Entity Relationship Diagrams - Visual Database Schema

**Generated:** 2025-11-25
**Database:** fraud_postgresql (Production)
**Tables Visualized:** 30 tables across 3 major workflows

---

## How to View These Diagrams

These diagrams use Mermaid syntax, which renders automatically in:
- GitHub (when viewing this file in a repository)
- GitLab
- Many markdown editors (VS Code with Mermaid extension)
- [Mermaid Live Editor](https://mermaid.live/) (paste the diagram code)

---

## Table of Contents

1. [Core Entity Model](#1-core-entity-model-14-tables)
2. [Fraud Detection Workflow](#2-fraud-detection-workflow-7-tables)
3. [Verification Workflows](#3-verification-workflows-9-tables)
4. [Complete Integration Overview](#4-complete-integration-overview-30-tables)

---

## 1. Core Entity Model (14 Tables)

**Purpose:** Foundation entities for the entire system - applicants, properties, companies, users, and access control.

### 1.1 Property Hierarchy & Applicant Flow

```mermaid
erDiagram
    companies ||--o{ properties : "manages"
    companies ||--o{ users : "employs"
    companies ||--o{ folders : "owns"

    properties ||--o{ folders : "contains"
    properties ||--o{ users_properties : "grants_access"
    properties }o--|| companies : "belongs_to"

    folders ||--o{ entries : "groups"
    folders }o--|| properties : "belongs_to"
    folders }o--o| users : "assigned_reviewer"

    entries ||--o{ applicants : "screens"
    entries }o--|| folders : "belongs_to"
    entries }o--o| users : "reviewer"
    entries }o--o| users : "assigned_to"

    applicants ||--o{ applicant_submissions : "submits"
    applicants }o--|| entries : "belongs_to"
    applicants }o--o| applicant_details : "has_details"

    companies {
        uuid id PK
        varchar name
        varchar salesforce_account_id "Salesforce integration"
        varchar short_id
        timestamp inserted_at
    }

    properties {
        uuid id PK
        uuid company_id FK
        varchar name
        varchar sfdc_id "Salesforce integration"
        varchar short_id
        jsonb supported_doctypes
        boolean identity_verification_enabled
        timestamp inserted_at
    }

    folders {
        uuid id PK
        uuid property_id FK
        uuid company_id FK
        uuid last_entry_id FK
        uuid review_assigned_to_id FK
        varchar name
        varchar status
        varchar result
        varchar dynamic_ruling
        timestamp ruling_time
    }

    entries {
        uuid id PK
        uuid folder_id FK
        uuid reviewer_id FK
        uuid review_assigned_to_id FK
        varchar short_id
        varchar status
        varchar result
        varchar review_status
        text note
        jsonb metadata
        timestamp submission_time
        timestamp report_complete_time
    }

    applicants {
        uuid id PK
        uuid entry_id FK
        uuid applicant_detail_id FK
        varchar full_name
        varchar email
        varchar phone
        boolean notification
        timestamp inserted_at
    }

    applicant_details {
        uuid id PK
        jsonb prefilled_application_data
        timestamp inserted_at
    }

    applicant_submissions {
        uuid id PK
        uuid applicant_id FK
        timestamp submitted_time
        boolean should_notify_applicant
        timestamp inserted_at
    }
```

### 1.2 Ownership & Access Control

```mermaid
erDiagram
    owners ||--o{ property_owners : "owns"
    properties ||--o{ property_owners : "owned_by"

    users ||--o{ users_properties : "has_access"
    properties ||--o{ users_properties : "grants_access"

    users ||--o{ users_owners : "manages"
    owners ||--o{ users_owners : "managed_by"

    users }o--o| companies : "works_for"
    users }o--o| team : "belongs_to"
    team }o--o| users : "managed_by"

    owners {
        uuid id PK
        varchar name
        varchar salesforce_id "Salesforce integration"
        varchar address
        varchar status
        timestamp inserted_at
    }

    property_owners {
        uuid id PK
        uuid property_id FK
        uuid owner_id FK
        timestamp ownership_start
        timestamp ownership_end "NULL means current"
        timestamp inserted_at
    }

    users {
        uuid id PK
        uuid company_id FK
        uuid team_id FK
        varchar email
        varchar role
        varchar first_name
        varchar last_name
        boolean is_archived
        timestamp inserted_at
    }

    team {
        uuid id PK
        uuid fde_manager_id FK
        integer country_id FK
        varchar name
        varchar timezone
        timestamp inserted_at
    }

    role {
        bigint id PK
        varchar name
    }

    users_properties {
        bigint id PK
        uuid user_id FK
        uuid property_id FK
        timestamp inserted_at
    }

    users_owners {
        uuid owner_id FK "Composite PK"
        uuid user_id FK "Composite PK"
        timestamp inserted_at
    }
```

---

## 2. Fraud Detection Workflow (7 Tables)

**Purpose:** Document authenticity verification using ML/AI analysis and human review.

### 2.1 Complete Fraud Detection Flow

```mermaid
erDiagram
    entries ||--o{ proof : "uploads"

    applicant_submissions ||--o{ applicant_submission_document_sources : "contains"
    applicant_submission_document_sources ||--o{ fraud_submissions : "triggers"

    fraud_submissions ||--o{ fraud_reviews : "requires_review"
    fraud_reviews ||--o{ fraud_document_reviews : "reviews"
    fraud_reviews }o--|| users : "assigned_to"
    fraud_reviews }o--|| fraud_result_types : "has_result"

    fraud_document_reviews }o--|| fraud_result_types : "has_result"

    applicant_submissions ||--o{ fraud_results : "determines"
    fraud_results }o--|| fraud_result_types : "has_result"

    proof {
        uuid id PK
        uuid entry_id FK
        varchar short_id
        text file "S3/storage URL"
        text thumb "Thumbnail URL"
        enum type "paystub, bank_statement, etc"
        enum result "PENDING, CLEAN, FRAUD, EDITED"
        enum suggested_ruling "ML/AI suggestion"
        jsonb extracted_meta "OCR results"
        array meta_data_flags "Fraud indicators"
        array similarity_check "Duplicate detection"
        boolean has_text
        boolean manual_review_recommended
        timestamp inserted_at
    }

    applicant_submission_document_sources {
        uuid id PK
        uuid applicant_submission_id FK
        varchar source_type "manual_upload, yardi, email, api"
        timestamp inserted_at
    }

    fraud_submissions {
        uuid id PK
        uuid applicant_submission_document_source_id "Implicit FK"
        timestamp inserted_at
    }

    fraud_reviews {
        uuid id PK
        uuid fraud_submission_id FK
        uuid reviewer_id FK
        integer result FK
        varchar fraud_type "document_manipulation, identity_theft"
        varchar status "PENDING, IN_PROGRESS, COMPLETED"
        varchar review_type "INITIAL, ESCALATION, QA"
        varchar result_reason
        timestamp assigned_date
        timestamp completed_date
    }

    fraud_document_reviews {
        uuid id PK
        uuid fraud_review_id FK
        uuid document_id "Links to proof.id"
        integer result FK
        varchar source_type
        timestamp inserted_at
    }

    fraud_results {
        bigint id PK
        uuid applicant_submission_id FK
        integer result FK
        timestamp inserted_at
    }

    fraud_result_types {
        bigint id PK
        varchar code "CLEAN, FRAUD, EDITED, INSUFFICIENT"
    }
```

### 2.2 ML/AI Analysis Details

**Key JSONB Fields in `proof` Table:**

```
extracted_meta (JSONB):
{
  "employer": "Acme Corporation",
  "pay_period_start": "2024-01-01",
  "pay_period_end": "2024-01-15",
  "gross_pay": 3500.00,
  "net_pay": 2650.00,
  "employee_name": "John Smith"
}

meta_data_flags (Array):
["copy_move_forgery", "font_manipulation", "metadata_mismatch"]

similarity_check (Array of JSONB):
[{
  "entry_id": "uuid-123",
  "similarity_score": 0.95,
  "matching_proof_id": "uuid-456"
}]
```

---

## 3. Verification Workflows (9 Tables)

**Purpose:** Income, asset, identity, and rent verification beyond fraud detection.

### 3.1 Income & Asset Verification

```mermaid
erDiagram
    entries ||--o{ income_verification_submissions : "initiates"
    entries ||--o{ asset_verification_submissions : "initiates"

    applicant_submission_document_sources ||--o{ income_verification_submissions : "sources"
    applicant_submission_document_sources ||--o{ asset_verification_submissions : "sources"

    income_verification_submissions ||--o{ income_verification_reviews : "requires_review"
    income_verification_reviews }o--|| users : "assigned_to"

    asset_verification_submissions ||--o{ asset_verification_reviews : "requires_review"
    asset_verification_reviews }o--|| users : "assigned_to"

    applicant_submissions ||--o{ income_verification_results : "determines"
    applicant_submissions ||--o{ asset_verification_results : "determines"

    income_verification_submissions {
        uuid id PK
        uuid entry_id FK
        uuid applicant_submission_document_source_id FK
        varchar review_eligibility "APPROVED, REJECTED, NEEDS_REVIEW"
        varchar rejection_reason
        timestamp inserted_at
    }

    income_verification_reviews {
        uuid id PK
        uuid income_verification_submission_id FK
        uuid reviewer_id FK
        uuid calculation_id "External calculation service"
        varchar status "PENDING, IN_PROGRESS, COMPLETED"
        varchar type "INITIAL, ESCALATION"
        enum review_method "AUTOMATED, MANUAL"
        varchar rejection_reason
        timestamp assigned_date
        timestamp completed_date
    }

    income_verification_results {
        bigint id PK
        uuid applicant_submission_id FK
        uuid calculation_id
        varchar review_eligibility "APPROVED, REJECTED"
        array rejected_reasons
        varchar type
        timestamp inserted_at
    }

    asset_verification_submissions {
        uuid id PK
        uuid entry_id FK
        uuid applicant_submission_document_source_id FK
        varchar review_eligibility "APPROVED, REJECTED, NEEDS_REVIEW"
        varchar rejection_reason
        timestamp inserted_at
    }

    asset_verification_reviews {
        uuid id PK
        uuid asset_verification_submission_id FK
        uuid reviewer_id FK
        uuid calculation_id
        varchar status "PENDING, IN_PROGRESS, COMPLETED"
        varchar type "INITIAL, ESCALATION"
        enum review_method "AUTOMATED, MANUAL"
        varchar rejection_reason
        timestamp assigned_date
        timestamp completed_date
    }

    asset_verification_results {
        bigint id PK
        uuid applicant_submission_id FK
        uuid calculation_id
        varchar review_eligibility "APPROVED, REJECTED"
        array rejected_reasons
        timestamp inserted_at
    }
```

### 3.2 Identity & Rent Verification

```mermaid
erDiagram
    properties ||--o{ id_verifications : "initiates"
    companies ||--o{ id_verifications : "initiates"

    applicants ||--o{ rent_verifications : "checks"
    properties ||--o{ rent_verifications : "requires"

    rent_verifications ||--o{ rent_verification_events : "logs"

    id_verifications {
        uuid id PK
        uuid property_id FK
        uuid company_id FK
        uuid applicant_detail_id "Links to applicant_details"
        text first_name
        text last_name
        text email
        text status "pending, in_progress, completed, approved, rejected"
        text score "HIGH, MEDIUM, LOW or numeric"
        text score_reason
        text provider "incode, persona"
        jsonb provider_session_info "Session creation data"
        jsonb provider_results "Full verification results"
        jsonb metadata
        timestamp results_provided_at
        timestamp inserted_at
    }

    rent_verifications {
        uuid id PK
        uuid applicant_id FK
        uuid property_id FK
        varchar provider "renttrack, experian_rentbureau"
        text external_id "Provider's verification ID"
        varchar status "pending, processing, completed, failed"
        text report_url
        jsonb request_payload "Data sent to provider"
        jsonb provider_data "Full report from provider"
        timestamp inserted_at
    }

    rent_verification_events {
        uuid id PK
        uuid rent_verification_id FK
        text event_type "request_created, webhook_received, etc"
        jsonb event_data "Event details"
        timestamp inserted_at
    }
```

### 3.3 Third-Party Provider Integration

**Identity Verification Providers:**
- **Incode** (default): Government ID scan + facial recognition + liveness detection
- **Persona**: Alternative identity verification provider

**Rent Verification Providers:**
- **RentTrack**: Rental payment reporting
- **Experian RentBureau**: Rental credit reporting
- **TransUnion ResidentCredit**: Rental history reports

**JSONB Field Examples:**

```
id_verifications.provider_results:
{
  "id_check": {"status": "passed", "document_type": "drivers_license"},
  "face_match": {"status": "passed", "confidence": 98.5},
  "liveness": {"status": "passed", "checks_performed": ["blink", "head_turn"]}
}

rent_verifications.provider_data:
{
  "rental_history": [{
    "address": "456 Oak St",
    "monthly_rent": 1500,
    "payment_history": {"on_time_payments": 34, "late_payments": 2}
  }],
  "evictions": [],
  "overall_rating": "good"
}
```

---

## 4. Complete Integration Overview (30 Tables)

**Purpose:** High-level view showing how all workflows integrate.

### 4.1 Data Flow: Entry Creation to Final Determination

```mermaid
graph TB
    subgraph "Core Entities"
        Company[companies]
        Property[properties]
        Folder[folders]
        Entry[entries]
        Applicant[applicants]
        Submission[applicant_submissions]
    end

    subgraph "Document Management"
        Proof[proof<br/>Documents]
        DocSource[applicant_submission_document_sources]
    end

    subgraph "Fraud Detection"
        FraudSub[fraud_submissions]
        FraudReview[fraud_reviews]
        FraudResult[fraud_results]
    end

    subgraph "Income Verification"
        IncomeSub[income_verification_submissions]
        IncomeReview[income_verification_reviews]
        IncomeResult[income_verification_results]
    end

    subgraph "Asset Verification"
        AssetSub[asset_verification_submissions]
        AssetReview[asset_verification_reviews]
        AssetResult[asset_verification_results]
    end

    subgraph "Identity Verification"
        IDVerify[id_verifications]
    end

    subgraph "Rent Verification"
        RentVerify[rent_verifications]
        RentEvents[rent_verification_events]
    end

    Company --> Property
    Property --> Folder
    Folder --> Entry
    Entry --> Applicant
    Applicant --> Submission

    Entry --> Proof
    Submission --> DocSource

    DocSource --> FraudSub
    FraudSub --> FraudReview
    Submission --> FraudResult

    DocSource --> IncomeSub
    IncomeSub --> IncomeReview
    Submission --> IncomeResult

    DocSource --> AssetSub
    AssetSub --> AssetReview
    Submission --> AssetResult

    Property --> IDVerify
    Applicant --> RentVerify
    RentVerify --> RentEvents

    FraudResult --> Entry
    IncomeResult --> Entry
    AssetResult --> Entry
    IDVerify --> Entry
    RentVerify --> Entry

    style Entry fill:#f9f,stroke:#333,stroke-width:4px
    style FraudResult fill:#ff9,stroke:#333,stroke-width:2px
    style IncomeResult fill:#ff9,stroke:#333,stroke-width:2px
    style AssetResult fill:#ff9,stroke:#333,stroke-width:2px
    style IDVerify fill:#ff9,stroke:#333,stroke-width:2px
    style RentVerify fill:#ff9,stroke:#333,stroke-width:2px
```

### 4.2 Result Aggregation Logic

```mermaid
graph LR
    subgraph "Verification Results"
        Fraud[Fraud Detection<br/>CLEAN/FRAUD/EDITED]
        Income[Income Verification<br/>APPROVED/REJECTED]
        Asset[Asset Verification<br/>APPROVED/REJECTED]
        Identity[Identity Verification<br/>APPROVED/REJECTED]
        Rent[Rent Verification<br/>GOOD/BAD]
    end

    subgraph "Aggregation Logic"
        Check{Any FRAUD?}
        Check2{Any REJECTED?}
        Check3{Any NEEDS_REVIEW?}
        AllPass[All Passed]
    end

    subgraph "Final Entry Result"
        ResultReject[REJECTED]
        ResultReview[NEEDS_REVIEW]
        ResultApprove[APPROVED]
    end

    Fraud --> Check
    Income --> Check
    Asset --> Check
    Identity --> Check
    Rent --> Check

    Check -->|Yes| ResultReject
    Check -->|No| Check2

    Check2 -->|Yes| ResultReject
    Check2 -->|No| Check3

    Check3 -->|Yes| ResultReview
    Check3 -->|No| AllPass

    AllPass --> ResultApprove

    style Check fill:#fcc,stroke:#333
    style Check2 fill:#fcc,stroke:#333
    style Check3 fill:#fcc,stroke:#333
    style ResultReject fill:#f66,stroke:#333,stroke-width:3px
    style ResultReview fill:#fc6,stroke:#333,stroke-width:3px
    style ResultApprove fill:#6f6,stroke:#333,stroke-width:3px
```

### 4.3 User Access Control Model

```mermaid
graph TB
    subgraph "Users & Teams"
        User[users]
        Team[team]
        Role[role]
    end

    subgraph "Organizations"
        Company[companies]
        Owner[owners]
    end

    subgraph "Properties & Entries"
        Property[properties]
        Folder[folders]
        Entry[entries]
    end

    subgraph "Access Junction Tables"
        UserProp[users_properties<br/>User can access Property]
        UserOwner[users_owners<br/>User can access all<br/>properties of Owner]
        PropOwner[property_owners<br/>Owner owns Property]
    end

    User --> Company
    User --> Team
    Team --> Role

    User --> UserProp
    Property --> UserProp

    User --> UserOwner
    Owner --> UserOwner

    Owner --> PropOwner
    Property --> PropOwner

    Company --> Property
    Property --> Folder
    Folder --> Entry

    User -.->|Reviewer| Entry
    User -.->|Assigned To| Entry
    User -.->|Reviewer| Folder

    style User fill:#9cf,stroke:#333,stroke-width:3px
    style UserProp fill:#fc9,stroke:#333
    style UserOwner fill:#fc9,stroke:#333
```

---

## Diagram Legend

### Relationship Symbols

- `||--o{` : One-to-many (one parent, many children)
- `}o--||` : Many-to-one (many children, one parent)
- `}o--o{` : Many-to-many
- `}o--o|` : Many-to-zero-or-one (optional relationship)

### Table Structure

Each table shows:
- **PK** = Primary Key
- **FK** = Foreign Key
- Key columns with data types
- Important JSONB/array fields
- Enum values in quotes

### Color Coding (in flow diagrams)

- **Pink (#f9f)** = Central/important tables
- **Yellow (#ff9)** = Result/determination tables
- **Red (#f66)** = Rejection/failure states
- **Orange (#fc6)** = Review required states
- **Green (#6f6)** = Approval/success states
- **Blue (#9cf)** = User/access control

---

## Using These Diagrams

### For Developers

1. **Understanding relationships:** Follow the FK arrows to see data flow
2. **Finding dependencies:** See what tables must exist before creating records
3. **Query planning:** Visualize joins needed for complex queries
4. **Feature planning:** See what tables new features will interact with

### For Database Administrators

1. **Schema migrations:** Understand foreign key constraints before altering tables
2. **Performance tuning:** Identify high-traffic join paths
3. **Backup strategies:** Understand table dependencies for backup order
4. **Replication:** See cross-database relationships

### For Product Managers

1. **Feature scope:** Understand data requirements for new features
2. **Integration planning:** See third-party provider integration points
3. **User flows:** Visualize how data flows through verification workflows
4. **Access control:** Understand permission models

### For Data Analysts

1. **Query planning:** See what tables to join for analytics
2. **Metric sources:** Identify tables containing key metrics
3. **Data lineage:** Trace how data flows from entry to final result
4. **Reporting:** Understand aggregation points (folders, entries, results)

---

## Notes on Diagram Accuracy

**These diagrams are based on:**
- Direct schema queries from fraud_postgresql database
- Foreign key constraint analysis
- Business logic documented in workflow files
- Implicit relationships identified during documentation

**Known limitations:**
- Some implicit relationships (not enforced by FK constraints) shown with notes
- JSONB field structures are examples, not exhaustive schemas
- Enum values are representative, not complete lists
- Some intermediate tables may be omitted in flow diagrams for clarity

**For complete details, see:**
- [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md) - Full schema details
- [FRAUD_DETECTION_WORKFLOW.md](FRAUD_DETECTION_WORKFLOW.md) - Fraud workflow details
- [VERIFICATION_WORKFLOWS.md](VERIFICATION_WORKFLOWS.md) - Verification workflow details
- [README.md](README.md) - Project summary and findings

---

**Generated:** 2025-11-25
**Last Updated:** 2025-11-25
**Version:** 1.0
**Tables Visualized:** 30 of 75 core tables (40% complete)
