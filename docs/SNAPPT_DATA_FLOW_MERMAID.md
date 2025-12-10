# Snappt Data Flow - Mermaid Diagrams
## Visual Data Flow Architecture

**Last Updated:** December 10, 2025
**Purpose:** Customer-facing visual data flow diagrams using Mermaid

---

## How to View These Diagrams

These Mermaid diagrams can be viewed in:
- **GitHub** - Renders automatically in markdown files
- **Mermaid Live Editor** - https://mermaid.live
- **VS Code** - With Mermaid extension
- **Confluence/Notion** - Many platforms support Mermaid
- **Documentation sites** - MkDocs, Docusaurus, etc.

---

## Diagram 1: High-Level Platform Architecture

```mermaid
graph TB
    subgraph "Data Ingestion Layer"
        PMS[Property Management Systems<br/>Yardi, RealPage]
        Portal[Customer Portal<br/>Direct API]
        Email[Email Invitation<br/>Applicant Link]
        External[External Systems<br/>Salesforce, Custom]
    end

    subgraph "Snappt Core Platform"
        Core[Central Application Database<br/>Applicants, Properties, Entries, Documents]

        subgraph "Verification Services"
            Fraud[Fraud Detection Service<br/>ML/AI Document Analysis]
            Income[Income Verification Service<br/>Paystub & Bank Statement Analysis]
            Asset[Asset Verification Service<br/>Bank Account & Liquid Assets]
            Identity[Identity Verification Service<br/>Government ID & Biometrics]
            Rent[Rent History Service<br/>Payment History & Evictions]
        end

        AI[AI Agent Services<br/>LangGraph Orchestration]
        ThirdParty[Third-Party Providers<br/>Incode, Persona, Argyle]
    end

    subgraph "Results & Integration Layer"
        Webhooks[Real-time Webhooks<br/>HTTP POST to Customer]
        SF[Salesforce Sync<br/>Census Daily Sync]
        Yardi[Yardi Integration<br/>Bidirectional SOAP]
        Analytics[Analytics Dashboard<br/>Databricks Lakehouse]
    end

    subgraph "Customer Systems"
        CustInternal[Customer Internal Systems]
        SalesforceCRM[Salesforce CRM]
        YardiPMS[Yardi Voyager PMS]
        BI[Customer BI Tools<br/>Tableau, Looker, Power BI]
    end

    PMS --> Core
    Portal --> Core
    Email --> Core
    External --> Core

    Core --> Fraud
    Core --> Income
    Core --> Asset
    Core --> Identity
    Core --> Rent

    Fraud --> AI
    Income --> AI
    Asset --> AI
    Identity --> ThirdParty
    Rent --> ThirdParty

    AI --> Core
    ThirdParty --> Core

    Core --> Webhooks
    Core --> SF
    Core --> Yardi
    Core --> Analytics

    Webhooks --> CustInternal
    SF --> SalesforceCRM
    Yardi --> YardiPMS
    Analytics --> BI

    style Core fill:#4A90E2,color:#fff
    style Fraud fill:#E94B3C,color:#fff
    style Income fill:#50C878,color:#fff
    style Asset fill:#FFB347,color:#fff
    style Identity fill:#9B59B6,color:#fff
    style AI fill:#34495E,color:#fff
    style Webhooks fill:#27AE60,color:#fff
```

---

## Diagram 2: Applicant Verification Journey (Detailed Flow)

```mermaid
flowchart TD
    Start([Applicant Application<br/>Initiated]) --> Source{Application Source}

    Source -->|Yardi API Poll| Yardi[Yardi Prospect Import<br/>SOAP API Polling]
    Source -->|Direct Entry| Portal[Customer Portal<br/>API Submission]
    Source -->|Email Invite| Email[Email Invitation<br/>Applicant Link Click]

    Yardi --> CreateEntry[Create Entry in Database<br/>Applicant Record Created]
    Portal --> CreateEntry
    Email --> CreateEntry

    CreateEntry --> SendInvite[Send Invitation Email<br/>to Applicant]

    SendInvite --> ApplicantAction{Applicant Chooses<br/>Verification Method}

    ApplicantAction -->|Traditional| UploadDocs[Upload Documents<br/>Paystubs, Bank Statements, etc.]
    ApplicantAction -->|Modern| BankLink[Bank Account Linking<br/>Connect via Argyle]

    UploadDocs --> DocStore[Document Storage<br/>Encrypted at Rest]
    BankLink --> BankAuth[Secure Bank Authentication<br/>Read-Only Access]

    BankAuth --> TransactionData[Transaction Data Retrieved<br/>90 Days History]

    DocStore --> ParallelProc[Trigger Parallel Processing]
    TransactionData --> ParallelProc

    ParallelProc --> Fraud[Fraud Detection<br/>ML/AI Analysis]
    ParallelProc --> Income[Income Verification<br/>Paystub/Transaction Analysis]
    ParallelProc --> Asset[Asset Verification<br/>Account Balance Analysis]

    Fraud --> FraudResult{Fraud Score}
    Income --> IncomeResult{Income Adequate?}
    Asset --> AssetResult{Assets Sufficient?}

    FraudResult -->|Clean| FraudClean[✓ CLEAN]
    FraudResult -->|Suspected| FraudSuspected[⚠ SUSPECTED]
    FraudResult -->|Fraud| FraudDetected[✗ FRAUD]

    IncomeResult -->|Yes| IncomeApproved[✓ APPROVED<br/>Income 3x+ Rent]
    IncomeResult -->|Edge Case| IncomeReview[⚠ NEEDS REVIEW<br/>2.5-3x Rent]
    IncomeResult -->|No| IncomeRejected[✗ REJECTED<br/>Insufficient Income]

    AssetResult -->|Yes| AssetApproved[✓ APPROVED<br/>6+ Months Reserves]
    AssetResult -->|Edge Case| AssetReview[⚠ NEEDS REVIEW<br/>2-6 Months]
    AssetResult -->|No| AssetRejected[✗ REJECTED<br/>Insufficient Assets]

    FraudClean --> IDV[Identity Verification<br/>Incode/Persona]
    FraudSuspected --> IDV
    FraudDetected --> Aggregate

    IncomeApproved --> Aggregate[Aggregate All Results]
    IncomeReview --> Aggregate
    IncomeRejected --> Aggregate

    AssetApproved --> Aggregate
    AssetReview --> Aggregate
    AssetRejected --> Aggregate

    IDV --> IDVResult{Identity Verified?}
    IDVResult -->|Yes| IDVSuccess[✓ VERIFIED<br/>High Confidence]
    IDVResult -->|No| IDVFailed[✗ FAILED<br/>Low Confidence]

    IDVSuccess --> Aggregate
    IDVFailed --> Aggregate

    Aggregate --> Decision{Overall Decision<br/>Worst Case Logic}

    Decision -->|All Approved| Approved[✓ APPROVED<br/>Proceed with Lease]
    Decision -->|Any Critical Fail| Rejected[✗ REJECTED<br/>Do Not Lease]
    Decision -->|Review Needed| Review[⚠ NEEDS REVIEW<br/>Manual Review Required]

    Approved --> Deliver[Deliver Results]
    Rejected --> Deliver
    Review --> HumanReview[Human Reviewer<br/>Final Decision]

    HumanReview --> Deliver

    Deliver --> Webhook[Webhook Notification<br/>Real-time POST]
    Deliver --> YardiSync[Yardi PMS Update<br/>SOAP API Push]
    Deliver --> Dashboard[Customer Dashboard<br/>UI Update]
    Deliver --> SFSync[Salesforce Sync<br/>Census Daily]

    Webhook --> CustomerSys([Customer Systems<br/>Updated])
    YardiSync --> CustomerSys
    Dashboard --> CustomerSys
    SFSync --> CustomerSys

    CustomerSys --> End([Application<br/>Complete])

    style CreateEntry fill:#4A90E2,color:#fff
    style FraudClean fill:#50C878,color:#fff
    style FraudDetected fill:#E94B3C,color:#fff
    style IncomeApproved fill:#50C878,color:#fff
    style IncomeRejected fill:#E94B3C,color:#fff
    style AssetApproved fill:#50C878,color:#fff
    style AssetRejected fill:#E94B3C,color:#fff
    style Approved fill:#50C878,color:#fff
    style Rejected fill:#E94B3C,color:#fff
    style Review fill:#FFB347,color:#fff
```

---

## Diagram 3: Microservices Database Architecture

```mermaid
graph TB
    subgraph "Central Hub"
        FraudDB[(fraud_postgresql<br/>155 Tables<br/><br/>Core Entities:<br/>• Applicants<br/>• Properties<br/>• Entries<br/>• Documents<br/>• Users<br/>• Workflow State)]
    end

    subgraph "Verification Microservices"
        IncomeDB[(Income Validation<br/>PostgreSQL<br/><br/>• Income Calculations<br/>• Paystub Parsing<br/>• Bank Statement Analysis<br/>• Employment Verification)]

        AssetDB[(Asset Verification<br/>PostgreSQL<br/><br/>• Bank Statements<br/>• Account Balances<br/>• Asset Totals<br/>• Liquidity Analysis)]

        FraudMLDB[(ML Fraud Detection<br/>av_postgres<br/><br/>• ML Scores<br/>• Document Properties<br/>• Rulings<br/>• Training Data)]
    end

    subgraph "Supporting Services"
        AgentDB[(AI Agent Services<br/>dp_ai_services<br/><br/>• LangGraph Checkpoints<br/>• Workflow State<br/>• Agent Configs<br/>• Execution Logs)]

        EnterpriseDB[(Enterprise Integration<br/>enterprise_postgresql<br/><br/>• Customer Mapping<br/>• Webhook Config<br/>• Yardi Sync<br/>• Email Delivery)]
    end

    subgraph "Analytics Platform"
        Databricks[(Databricks Lakehouse<br/>Delta Lake<br/><br/>• Data Warehouse<br/>• Reporting Tables<br/>• Dashboards<br/>• Business Intelligence)]
    end

    FraudDB -->|applicant_id| IncomeDB
    FraudDB -->|document_id| AssetDB
    FraudDB -->|document_id| FraudMLDB
    FraudDB -->|execution_context| AgentDB
    FraudDB -->|property_id<br/>applicant_id| EnterpriseDB

    IncomeDB -.->|results| FraudDB
    AssetDB -.->|results| FraudDB
    FraudMLDB -.->|scores| FraudDB
    AgentDB -.->|outputs| FraudDB
    EnterpriseDB -.->|webhooks| FraudDB

    FraudDB -->|Fivetran<br/>Real-time Sync| Databricks
    EnterpriseDB -->|Fivetran<br/>Real-time Sync| Databricks
    IncomeDB -->|Fivetran<br/>Real-time Sync| Databricks
    AssetDB -->|Fivetran<br/>Real-time Sync| Databricks
    FraudMLDB -->|Fivetran<br/>Real-time Sync| Databricks

    style FraudDB fill:#4A90E2,color:#fff
    style IncomeDB fill:#50C878,color:#fff
    style AssetDB fill:#FFB347,color:#fff
    style FraudMLDB fill:#E94B3C,color:#fff
    style AgentDB fill:#9B59B6,color:#fff
    style EnterpriseDB fill:#34495E,color:#fff
    style Databricks fill:#FF6B6B,color:#fff
```

---

## Diagram 4: Bank Account Linking Flow (Argyle Integration)

```mermaid
sequenceDiagram
    participant Applicant
    participant SnapptUI as Snappt Portal
    participant SnapptCore as Snappt Backend
    participant Argyle as Argyle Service
    participant Bank as Bank Online Banking
    participant IncomeService as Income Service
    participant AssetService as Asset Service
    participant Results as Results Engine

    Applicant->>SnapptUI: Click "Connect Bank Account"
    SnapptUI->>SnapptCore: Request bank linking session
    SnapptCore->>Argyle: Create Link session
    Argyle-->>SnapptCore: Return session token & URL
    SnapptCore-->>SnapptUI: Return Argyle Link widget
    SnapptUI->>Applicant: Display bank selection screen

    Applicant->>SnapptUI: Select bank (Chase, BofA, etc.)
    SnapptUI->>Argyle: Open Argyle Link widget
    Argyle->>Applicant: Display bank login form

    Note over Applicant,Bank: Secure Authentication<br/>(No credentials stored by Snappt)

    Applicant->>Bank: Enter username/password
    Bank->>Bank: Validate credentials
    Bank-->>Argyle: Authentication successful

    Argyle->>Bank: Request read-only access<br/>(Last 90 days transactions)
    Bank-->>Argyle: Return transaction data

    Note over Argyle: Data Retrieved:<br/>• Transactions (90 days)<br/>• Account balances<br/>• Direct deposits<br/>• Recurring payments

    Argyle-->>SnapptCore: Webhook: Data ready
    SnapptCore->>Argyle: Fetch transaction data (API)
    Argyle-->>SnapptCore: Return encrypted transaction data

    par Parallel Processing
        SnapptCore->>IncomeService: Analyze income
        IncomeService->>IncomeService: Identify direct deposits
        IncomeService->>IncomeService: Calculate monthly income
        IncomeService->>IncomeService: Verify employment consistency
        IncomeService-->>SnapptCore: Income result (3.2x rent ✓)
    and
        SnapptCore->>AssetService: Analyze assets
        AssetService->>AssetService: Sum account balances
        AssetService->>AssetService: Verify liquid assets
        AssetService->>AssetService: Calculate reserve months
        AssetService-->>SnapptCore: Asset result (8 months ✓)
    end

    SnapptCore->>Results: Aggregate results
    Results->>Results: Apply decision logic
    Results-->>SnapptCore: Overall decision: APPROVED

    SnapptCore-->>SnapptUI: Update application status
    SnapptUI-->>Applicant: ✓ Verification Complete!<br/>(No documents needed)

    Note over Applicant,Results: Total Time: 30-60 seconds<br/>vs. 24-48 hours traditional
```

---

## Diagram 5: Yardi PMS Integration (Bidirectional)

```mermaid
sequenceDiagram
    participant Yardi as Yardi Voyager PMS
    participant SnapptPoll as Snappt Polling Service
    participant SnapptCore as Snappt Core Database
    participant SnapptProcess as Screening Workflow
    participant SnapptIntegration as Integration Service

    Note over Yardi,SnapptCore: INBOUND: Prospect Import Flow

    loop Every 15 Minutes
        SnapptPoll->>Yardi: SOAP: GetNewProspects(property_id, since_last_poll)
        Yardi-->>SnapptPoll: Return new prospects list

        alt New Prospects Found
            SnapptPoll->>SnapptCore: Create yardi_invite records
            SnapptPoll->>SnapptCore: Create entry records
            SnapptCore->>SnapptCore: Create applicant records
            SnapptCore->>SnapptCore: Link yardi_entry (prospect_code)
            SnapptCore-->>Applicant: Send invitation email
            SnapptPoll->>SnapptCore: Update last_poll_run timestamp
        else No New Prospects
            SnapptPoll->>SnapptCore: Update last_poll_run timestamp
        end
    end

    Note over Applicant,SnapptProcess: Applicant completes screening

    Applicant->>SnapptProcess: Upload documents / connect bank
    SnapptProcess->>SnapptProcess: Run verifications (fraud, income, asset)
    SnapptProcess->>SnapptCore: Store results
    SnapptCore->>SnapptCore: Update entry status: COMPLETED

    Note over SnapptCore,Yardi: OUTBOUND: Results Push Flow

    SnapptCore->>SnapptIntegration: Trigger: Entry completed
    SnapptIntegration->>SnapptCore: Check if yardi_entry exists

    alt Yardi Entry Found
        SnapptCore-->>SnapptIntegration: Return prospect_code
        SnapptIntegration->>SnapptIntegration: Build results payload
        SnapptIntegration->>Yardi: SOAP: UpdateProspectScreening(prospect_code, results)

        Note over SnapptIntegration,Yardi: Payload Includes:<br/>• Screening status<br/>• Fraud result<br/>• Income result<br/>• Asset result<br/>• Report URL

        alt Update Success
            Yardi-->>SnapptIntegration: 200 OK
            SnapptIntegration->>SnapptCore: Update submit_date timestamp
            SnapptIntegration->>SnapptCore: Log success
        else Update Failed
            Yardi-->>SnapptIntegration: 500 Error
            SnapptIntegration->>SnapptCore: Log error
            SnapptIntegration->>SnapptIntegration: Schedule retry
        end
    else No Yardi Entry
        SnapptIntegration->>SnapptCore: Log: Not a Yardi applicant
    end
```

---

## Diagram 6: Webhook Delivery System with Retry Logic

```mermaid
flowchart TD
    Event([Event Occurs]) --> EventType{Event Type}

    EventType -->|entry.completed| Complete[Entry Completed Event]
    EventType -->|fraud.detected| Fraud[Fraud Detected Event]
    EventType -->|entry.in_review| Review[Review Needed Event]
    EventType -->|result.updated| Update[Result Updated Event]

    Complete --> FindWebhooks[Query Webhooks Table]
    Fraud --> FindWebhooks
    Review --> FindWebhooks
    Update --> FindWebhooks

    FindWebhooks --> Filter{Webhooks Found?}

    Filter -->|Yes| BuildPayload[Build JSON Payload<br/>• event type<br/>• entry_id<br/>• results<br/>• applicant info<br/>• report URL]
    Filter -->|No| NoWebhooks[No webhooks configured<br/>Skip delivery]

    BuildPayload --> Webhooks[(webhooks table)]
    Webhooks --> CheckActive{is_active = true?}

    CheckActive -->|No| Skip[Skip inactive webhook]
    CheckActive -->|Yes| CheckEvents{Event in<br/>subscribed events?}

    CheckEvents -->|No| Skip
    CheckEvents -->|Yes| Deliver[HTTP POST to endpoint]

    Deliver --> Response{HTTP Response}

    Response -->|200-299| Success[✓ Success]
    Response -->|400-499| ClientError[✗ Client Error<br/>No Retry]
    Response -->|500-599| ServerError[✗ Server Error<br/>Retry]
    Response -->|Timeout| Timeout[✗ Timeout<br/>Retry]

    Success --> LogSuccess[Log to webhook_delivery_attempts<br/>status: 200<br/>response_data]
    ClientError --> LogClientError[Log to webhook_delivery_attempts<br/>status: 4xx<br/>response_data<br/>NO RETRY]

    ServerError --> LogError[Log to webhook_delivery_attempts<br/>status: 5xx<br/>response_data]
    Timeout --> LogError

    LogError --> RetryLogic{Retry Attempt #}

    RetryLogic -->|1| Wait1[Wait 1 minute]
    RetryLogic -->|2| Wait2[Wait 5 minutes]
    RetryLogic -->|3| Wait3[Wait 15 minutes]
    RetryLogic -->|4| Wait4[Wait 1 hour]
    RetryLogic -->|5+| GiveUp[Give Up<br/>Alert Customer]

    Wait1 --> Deliver
    Wait2 --> Deliver
    Wait3 --> Deliver
    Wait4 --> Deliver

    GiveUp --> Alert[Send alert email<br/>Webhook delivery failed]

    LogSuccess --> End([Complete])
    LogClientError --> End
    Alert --> End
    NoWebhooks --> End
    Skip --> End

    style Success fill:#50C878,color:#fff
    style ClientError fill:#FFB347,color:#fff
    style ServerError fill:#E94B3C,color:#fff
    style Timeout fill:#E94B3C,color:#fff
    style GiveUp fill:#E94B3C,color:#fff
```

---

## Diagram 7: Salesforce Integration via Census

```mermaid
flowchart LR
    subgraph "Source: Snappt RDS"
        RDS[(PostgreSQL<br/>Production Database)]
    end

    subgraph "Fivetran ETL"
        Fivetran[Fivetran Connector<br/>Real-time CDC]
    end

    subgraph "Databricks Data Lakehouse"
        DeltaLake[(Delta Lake Storage<br/>Raw Tables)]
        DLT[Delta Live Tables<br/>Transformation Pipelines]

        Views[Databricks Views<br/>45 Fields Ready]

        DeltaLake --> DLT
        DLT --> Views

        subgraph "Transformed Views"
            NewProps[new_properties_with_features<br/>• Property details 21 fields<br/>• Feature flags 23 fields<br/>• Only properties NOT in Salesforce]

            ProductProps[product_property_w_features<br/>• All active properties<br/>• Feature enablement<br/>• Updated daily]
        end

        Views --> NewProps
        Views --> ProductProps
    end

    subgraph "Census ETL Service"
        CensusModel[Census Model<br/>Connects to Databricks view]
        CensusTransform[Transform & Map<br/>• Field mapping<br/>• Deduplication<br/>• Validation]
        CensusSchedule[Schedule: Daily 2:00 AM]

        CensusModel --> CensusTransform
        CensusTransform --> CensusSchedule
    end

    subgraph "Destination: Salesforce"
        SFAPI[Salesforce Bulk API]
        SFObject[(Product_Property__c<br/>Custom Object)]

        SFAPI --> SFObject
    end

    RDS -->|Real-time Replication| Fivetran
    Fivetran -->|Raw Data| DeltaLake

    NewProps -->|Read| CensusModel
    ProductProps -->|Read| CensusModel

    CensusSchedule -->|Bulk Insert/Update| SFAPI

    SFObject -.->|Query<br/>Check for existing| NewProps

    style RDS fill:#4A90E2,color:#fff
    style DeltaLake fill:#FF6B6B,color:#fff
    style NewProps fill:#50C878,color:#fff
    style SFObject fill:#00A1E0,color:#fff
    style CensusSchedule fill:#FFB347,color:#fff
```

---

## Diagram 8: Data Security & Privacy Architecture

```mermaid
graph TB
    subgraph "Layer 1: Network Security"
        TLS[TLS 1.3 Encryption<br/>All Data in Transit]
        VPC[VPC Isolation<br/>Private Subnets]
        WAF[Web Application Firewall<br/>DDoS Protection]
    end

    subgraph "Layer 2: Data Encryption"
        AtRest[AES-256 Encryption at Rest<br/>All Databases]
        FieldLevel[Field-Level Encryption<br/>PII: SSN, DOB, Financial]
        KeyMgmt[Key Management<br/>AWS KMS / Azure Key Vault<br/>Automatic Rotation]
    end

    subgraph "Layer 3: Access Control"
        RBAC[Role-Based Access Control<br/>Granular Permissions]
        MFA[Multi-Factor Authentication<br/>Required for Admin]
        APIKeys[API Key Authentication<br/>Rate Limiting]
        OAuth[OAuth 2.0<br/>Third-Party Integration]
        AuditLog[Comprehensive Audit Logging<br/>All Data Access Tracked]
    end

    subgraph "Layer 4: Data Lifecycle"
        Retention[Retention Policies<br/>Documents: 90 days<br/>Bank Data: 30 days<br/>PII: Per Policy]
        Deletion[Automatic Deletion<br/>GDPR/CCPA Compliant]
        Anonymize[Data Anonymization<br/>Analytics & Reporting]
    end

    subgraph "Layer 5: Third-Party Security"
        SOC2[SOC 2 Type II Certified<br/>All Critical Partners]
        Audits[Regular Security Audits<br/>Penetration Testing]
        DPA[Data Processing Agreements<br/>GDPR Compliant]
    end

    subgraph "Sensitive Data Types"
        Docs[Documents<br/>PDFs, Images<br/>AES-256 + Access Control]
        BankData[Bank Account Data<br/>Field-Level Encryption<br/>30-day retention]
        SSN[SSN last 4<br/>Field-Level Encryption<br/>60-day retention]
        Bio[Biometric Data<br/>Third-party only<br/>Not stored by Snappt]
        Financial[Financial Balances<br/>Encrypted transit/rest<br/>90-day retention]
    end

    TLS --> AtRest
    VPC --> AtRest
    WAF --> AtRest

    AtRest --> FieldLevel
    FieldLevel --> KeyMgmt

    KeyMgmt --> RBAC
    RBAC --> MFA
    MFA --> APIKeys
    APIKeys --> OAuth
    OAuth --> AuditLog

    AuditLog --> Retention
    Retention --> Deletion
    Deletion --> Anonymize

    Anonymize --> SOC2
    SOC2 --> Audits
    Audits --> DPA

    FieldLevel --> Docs
    FieldLevel --> BankData
    FieldLevel --> SSN
    FieldLevel --> Bio
    FieldLevel --> Financial

    style TLS fill:#27AE60,color:#fff
    style AtRest fill:#27AE60,color:#fff
    style FieldLevel fill:#E74C3C,color:#fff
    style RBAC fill:#3498DB,color:#fff
    style MFA fill:#3498DB,color:#fff
    style Retention fill:#F39C12,color:#fff
    style SOC2 fill:#9B59B6,color:#fff
```

---

## Diagram 9: Analytics Data Flow (Databricks)

```mermaid
graph TB
    subgraph "Production Databases"
        ProdDB1[(fraud_postgresql<br/>155 tables)]
        ProdDB2[(enterprise_postgresql<br/>6 tables)]
        ProdDB3[(income_validation<br/>15 tables)]
        ProdDB4[(asset_verification<br/>20 tables)]
        ProdDB5[(av_postgres<br/>ML/Fraud)]
    end

    subgraph "Fivetran Connectors"
        FT1[Fivetran Connector 1<br/>CDC Real-time]
        FT2[Fivetran Connector 2<br/>CDC Real-time]
        FT3[Fivetran Connector 3<br/>CDC Real-time]
        FT4[Fivetran Connector 4<br/>CDC Real-time]
        FT5[Fivetran Connector 5<br/>CDC Real-time]
    end

    subgraph "Databricks Lakehouse"
        subgraph "Bronze Layer - Raw Data"
            Bronze[(Delta Lake Tables<br/>Raw Production Data<br/>Mirrored from RDS)]
        end

        subgraph "Silver Layer - Cleaned & Joined"
            DLT[Delta Live Tables<br/>ETL Pipelines]
            Silver[(Cleaned Tables<br/>• Deduplication<br/>• Data quality checks<br/>• Schema enforcement)]
        end

        subgraph "Gold Layer - Business Logic"
            Gold[(Analytics Views<br/>• Aggregations<br/>• Business metrics<br/>• Report-ready)]
        end
    end

    subgraph "Serving Layer"
        Dashboards[Databricks Dashboards<br/>• Bank Linking Beta<br/>• Fraud Trends<br/>• Property Performance]

        Notebooks[SQL Notebooks<br/>• Ad-hoc Analysis<br/>• Applicant Reports<br/>• Custom Queries]

        BITools[BI Tool Connectors<br/>• Tableau<br/>• Looker<br/>• Power BI]

        Census[Census Reverse ETL<br/>• Salesforce Sync<br/>• Customer Data Platform]
    end

    ProdDB1 -->|5-min latency| FT1
    ProdDB2 -->|5-min latency| FT2
    ProdDB3 -->|5-min latency| FT3
    ProdDB4 -->|5-min latency| FT4
    ProdDB5 -->|5-min latency| FT5

    FT1 --> Bronze
    FT2 --> Bronze
    FT3 --> Bronze
    FT4 --> Bronze
    FT5 --> Bronze

    Bronze --> DLT
    DLT --> Silver
    Silver --> Gold

    Gold --> Dashboards
    Gold --> Notebooks
    Gold --> BITools
    Gold --> Census

    Census -->|Daily 2am| Salesforce[(Salesforce CRM)]

    style Bronze fill:#CD7F32,color:#fff
    style Silver fill:#C0C0C0,color:#000
    style Gold fill:#FFD700,color:#000
    style DLT fill:#4A90E2,color:#fff
    style Dashboards fill:#50C878,color:#fff
    style Census fill:#00A1E0,color:#fff
```

---

## Usage Instructions

### To View in GitHub:
1. Upload this file to your GitHub repository
2. GitHub will automatically render the Mermaid diagrams

### To Edit in Mermaid Live Editor:
1. Go to https://mermaid.live
2. Copy any diagram code block (without the backticks)
3. Paste into the editor
4. Customize colors, labels, and structure
5. Export as PNG/SVG for presentations

### To Embed in Documentation:
```markdown
# Your Documentation Page

## Data Flow Diagram

```mermaid
graph TB
    A[Start] --> B[Process]
    B --> C[End]
```
```

### Color Customization Guide:

The diagrams use these colors:
- **Blue (#4A90E2)** - Core systems/databases
- **Green (#50C878)** - Success states/approved
- **Red (#E94B3C)** - Fraud/rejected/errors
- **Orange (#FFB347)** - Warnings/needs review
- **Purple (#9B59B6)** - AI/ML services
- **Dark Gray (#34495E)** - Integration services

To change colors, add style at the bottom of any diagram:
```mermaid
style NodeName fill:#COLOR,color:#fff
```

---

## Diagram Summary

| Diagram # | Name | Best Use Case |
|-----------|------|---------------|
| 1 | High-Level Platform | Executive overview, sales presentations |
| 2 | Applicant Journey | Customer onboarding, process documentation |
| 3 | Database Architecture | Technical architecture reviews, engineering |
| 4 | Bank Linking Flow | Feature demonstrations, integration docs |
| 5 | Yardi Integration | PMS integration documentation |
| 6 | Webhook System | API documentation, integration guides |
| 7 | Salesforce Sync | CRM integration documentation |
| 8 | Security Architecture | Security reviews, compliance audits |
| 9 | Analytics Flow | Data team documentation, BI integration |

---

**For questions or customization requests, contact:** dane@snappt.com
