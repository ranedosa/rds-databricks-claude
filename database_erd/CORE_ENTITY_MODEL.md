# Core Entity Model - Fraud Detection Database

**Generated:** 2025-11-25
**Database:** fraud_postgresql (Production)
**Tables Documented:** 14 core tables

---

## Overview

The Core Entity Model represents the foundational data structures of the Snappt fraud detection platform. These tables form the base hierarchy that all other workflows (fraud detection, income verification, etc.) build upon.

### Entity Hierarchy

```
Companies
  └─> Properties
       └─> Folders
            └─> Entries
                 └─> Applicants
                      └─> Applicant Submissions
```

### Access Control Model

```
Users
  ├─> belongs to Company
  ├─> belongs to Team
  ├─> has many-to-many Properties (users_properties)
  └─> has many-to-many Owners (users_owners)
```

---

## Table Inventory

### 1. Applicant Tables (3 tables)
- **applicants** - Core applicant information and contact details
- **applicant_details** - Additional applicant data (prefilled application data)
- **applicant_submissions** - Submission events and document uploads

### 2. Property & Organization Tables (6 tables)
- **companies** - Property management companies
- **properties** - Individual properties (apartment buildings, complexes)
- **folders** - Groups multiple entries for the same applicant/property
- **entries** - Individual screening requests/cases
- **owners** - Property owners (external entities, linked to Salesforce)
- **property_owners** - Many-to-many junction between properties and owners

### 3. User & Access Tables (5 tables)
- **users** - System users (staff, reviewers, property managers)
- **team** - Organizational teams
- **role** - User roles/permissions
- **users_properties** - User access to specific properties
- **users_owners** - User access to specific owners

---

## Detailed Table Documentation

## 1. APPLICANTS

**Purpose:** Stores core applicant information for individuals being screened for fraud.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| full_name | varchar(255) | YES | Complete name |
| first_name | varchar(255) | YES | First name |
| middle_initial | varchar(255) | YES | Middle initial |
| last_name | varchar(255) | YES | Last name |
| email | varchar(255) | YES | Email address |
| phone | varchar(255) | YES | Phone number |
| notification | boolean | NO | Whether to notify applicant (default: false) |
| entry_id | uuid | YES | **FK → entries.id** |
| applicant_detail_id | uuid | YES | **FK → applicant_details.id** |
| identity_id | uuid | YES | Identity verification ID (may link to id_verifications) |
| inserted_at | timestamp | NO | Record creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** entries (via entry_id)
- **Belongs to:** applicant_details (via applicant_detail_id)
- **Has many:** applicant_submissions

### Business Logic
- Name can be stored as either `full_name` OR broken into `first_name`, `middle_initial`, `last_name`
- `notification` controls whether applicant receives email notifications
- `identity_id` may reference identity verification records

---

## 2. APPLICANT_DETAILS

**Purpose:** Stores additional applicant information, typically prefilled from external systems.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| prefilled_application_data | jsonb | YES | Flexible JSON storage for application data |
| inserted_at | timestamp | NO | Record creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Has one:** applicant (via applicants.applicant_detail_id)

### Business Logic
- Uses JSONB for flexible schema - can store arbitrary application data
- Likely populated from integrations (Yardi, external PMS systems)

---

## 3. APPLICANT_SUBMISSIONS

**Purpose:** Tracks submission events when applicants upload documents or complete verification steps.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| applicant_id | uuid | NO | **FK → applicants.id** |
| submitted_time | timestamp | NO | When submission occurred |
| identity_id | uuid | YES | Identity verification session ID |
| should_notify_applicant | boolean | NO | Whether to send notification (default: true) |
| inserted_at | timestamp | NO | Record creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** applicants (via applicant_id)

### Business Logic
- Each submission represents a document upload or verification event
- `identity_id` may link to identity verification sessions
- `should_notify_applicant` controls email notifications

---

## 4. COMPANIES

**Purpose:** Represents property management companies that use the Snappt platform.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| name | varchar(255) | YES | Company name |
| address | varchar(255) | YES | Street address |
| city | varchar(255) | YES | City |
| state | varchar(255) | YES | State/province |
| zip | varchar(255) | YES | Postal code |
| phone | varchar(255) | YES | Contact phone |
| website | varchar(255) | YES | Company website |
| logo | varchar(255) | YES | Logo URL/path |
| short_id | varchar(255) | YES | Human-readable ID |
| salesforce_account_id | varchar(255) | YES | **Integration:** Salesforce Account ID |
| inserted_at | timestamp | NO | Record creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Has many:** properties
- **Has many:** users
- **Has many:** folders

### Business Logic
- `short_id` provides a user-friendly identifier
- `salesforce_account_id` links to Salesforce CRM for sales tracking
- Companies are top-level organizational units

---

## 5. PROPERTIES

**Purpose:** Individual properties (apartment buildings, complexes) managed by companies.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| name | varchar(255) | YES | Property name |
| entity_name | varchar(255) | YES | Legal entity name |
| address | varchar(255) | YES | Street address |
| city | varchar(255) | YES | City |
| state | varchar(255) | YES | State/province |
| zip | varchar(255) | YES | Postal code |
| phone | varchar(255) | YES | Contact phone |
| email | varchar(255) | YES | Contact email |
| website | varchar(255) | YES | Property website |
| logo | varchar(255) | YES | Logo URL/path |
| short_id | varchar(255) | YES | Human-readable ID |
| unit | integer | YES | Number of units |
| company_id | uuid | YES | **FK → companies.id** |
| company_short_id | varchar(255) | YES | Denormalized for performance |
| pmc_name | varchar(255) | YES | Property Management Company name |
| status | varchar(255) | YES | Property status (active/inactive) |
| sfdc_id | varchar(255) | YES | **Integration:** Salesforce Property ID |
| bank_statement | integer | YES | Number required (default: 2) |
| paystub | integer | YES | Number required (default: 2) |
| supported_doctypes | jsonb | YES | Supported document types configuration |
| unit_is_required | boolean | YES | Whether unit field is required (default: true) |
| phone_is_required | boolean | YES | Whether phone is required (default: true) |
| identity_verification_enabled | boolean | YES | Enable IDV (default: false) |
| identity_verification_provider | varchar(255) | YES | IDV provider (default: 'incode') |
| identity_verification_flow_types | jsonb | YES | IDV flow configuration |
| identity_verification_report_image_types | jsonb | YES | IDV report image types |
| textsearchable_index_col | tsvector | YES | Full-text search index |
| inserted_at | timestamp | NO | Record creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** companies (via company_id)
- **Has many:** folders
- **Has many:** users_properties (many-to-many with users)
- **Has many:** property_owners (many-to-many with owners)
- **Has many:** property_features

### Business Logic
- `supported_doctypes` (JSONB) defines which document types are accepted
- `bank_statement` and `paystub` specify required number of documents
- Identity verification settings control IDV feature
- `sfdc_id` links to Salesforce for property tracking
- `textsearchable_index_col` enables fast property search

---

## 6. FOLDERS

**Purpose:** Groups multiple entries (screening requests) for the same applicant/property combination.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| name | varchar(255) | YES | Folder name (usually applicant name) |
| status | varchar(255) | YES | Overall folder status |
| result | varchar(255) | YES | Overall fraud determination |
| dynamic_ruling | varchar(255) | NO | Current ruling (default: 'PENDING') |
| ruling_time | timestamp | YES | When ruling was made |
| property_id | uuid | YES | **FK → properties.id** |
| company_id | uuid | YES | **FK → companies.id** |
| property_short_id | varchar(255) | YES | Denormalized for performance |
| property_name | varchar(255) | YES | Denormalized for performance |
| company_short_id | varchar(255) | YES | Denormalized for performance |
| last_entry_id | uuid | YES | **FK → entries.id** |
| last_entry_submission_time | timestamp | YES | Denormalized latest submission |
| last_entry_result | varchar(255) | YES | Denormalized latest result |
| last_entry_status | varchar(255) | YES | Denormalized latest status |
| review_assigned_to_id | uuid | YES | **FK → users.id** |
| review_assigned_date | timestamp | YES | When review was assigned |
| inserted_at | timestamp | NO | Record creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** properties (via property_id)
- **Belongs to:** companies (via company_id)
- **Belongs to:** users (reviewer, via review_assigned_to_id)
- **Has many:** entries

### Business Logic
- Folders aggregate multiple entries for the same applicant
- Heavy denormalization (`last_entry_*` fields) for dashboard performance
- `dynamic_ruling` updates based on latest entry results
- Can be assigned to reviewers for manual review

---

## 7. ENTRIES

**Purpose:** Individual screening/verification requests. Core unit of work in the system.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| short_id | varchar(255) | YES | Human-readable ID |
| status | varchar(255) | YES | Entry status (submitted, in_review, completed, etc.) |
| result | varchar(255) | YES | Fraud determination result |
| suggested_ruling | USER-DEFINED | NO | AI/ML suggested result (default: 'NOT_RUN') |
| note | text | YES | Reviewer notes |
| unit | varchar(255) | YES | Property unit number |
| metadata | jsonb | YES | Flexible additional data |
| folder_id | uuid | YES | **FK → folders.id** |
| submission_time | timestamp | YES | When applicant submitted documents |
| report_complete_time | timestamp | YES | When final report was generated |
| notification_email | varchar(255) | YES | Email for notifications |
| has_previously_submitted | boolean | NO | Repeat applicant flag (default: false) |
| auto_merged | boolean | YES | Automatically merged entry (default: false) |
| is_automatic_review | boolean | YES | Automated review flag (default: false) |
| review_status | varchar(255) | NO | Review queue status (default: 'UNASSIGNED') |
| review_date | timestamp | YES | When review was completed |
| review_assigned_date | timestamp | YES | When assigned to reviewer |
| reviewer_id | uuid | YES | **FK → users.id** (who completed review) |
| review_assigned_to_id | uuid | YES | **FK → users.id** (currently assigned) |
| primary_notification_sent_at | timestamp | YES | First notification timestamp |
| secondary_notification_sent_at | timestamp | YES | Follow-up notification timestamp |
| twenty_two_hours_notification_sent_at | timestamp | YES | SLA warning notification |
| sixteen_hours_notification_sent_at | timestamp | YES | SLA warning notification |
| inserted_at | timestamp | NO | Record creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** folders (via folder_id)
- **Belongs to:** users (reviewer_id - who completed)
- **Belongs to:** users (review_assigned_to_id - currently assigned)
- **Has many:** applicants

### Business Logic
- Entries are the core unit of work - each represents a fraud screening request
- `review_status` tracks workflow: UNASSIGNED → ASSIGNED → IN_REVIEW → COMPLETED
- `suggested_ruling` is set by ML/AI models
- Multiple notification timestamps track SLA compliance
- `has_previously_submitted` identifies repeat applicants (potential fraud signal)
- `metadata` (JSONB) stores flexible additional context

---

## 8. OWNERS

**Purpose:** Property owners (external entities like REITs, investment firms). Linked to Salesforce.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| name | varchar(255) | NO | Owner name |
| address | varchar(255) | YES | Street address |
| city | varchar(255) | YES | City |
| state | varchar(255) | YES | State/province |
| zip | varchar(255) | YES | Postal code |
| phone | varchar(255) | YES | Contact phone |
| website | varchar(255) | YES | Website |
| salesforce_id | varchar(255) | NO | **Integration:** Salesforce Owner ID |
| status | varchar(255) | YES | Owner status |
| inserted_at | timestamp | NO | Record creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Has many:** property_owners (many-to-many with properties)
- **Has many:** users_owners (many-to-many with users)

### Business Logic
- Owners are external entities that own multiple properties
- `salesforce_id` is required - synced from Salesforce
- Users can have access to specific owners via `users_owners`

---

## 9. PROPERTY_OWNERS

**Purpose:** Junction table - many-to-many relationship between properties and owners.

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| property_id | uuid | NO | **FK → properties.id** |
| owner_id | uuid | NO | **FK → owners.id** |
| ownership_start | timestamp | YES | When ownership began |
| ownership_end | timestamp | YES | When ownership ended (NULL = current) |
| inserted_at | timestamp | NO | Record creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** properties (via property_id)
- **Belongs to:** owners (via owner_id)

### Business Logic
- Tracks property ownership over time
- `ownership_end` = NULL means current ownership
- Supports ownership history

---

## 10. USERS

**Purpose:** System users (Snappt staff, reviewers, property managers).

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| auth_id | uuid | YES | External authentication service ID |
| short_id | varchar(255) | YES | Human-readable ID |
| first_name | varchar(255) | YES | First name |
| last_name | varchar(255) | YES | Last name |
| email | varchar(255) | YES | Email address |
| role | varchar(255) | YES | User role (admin, reviewer, property_manager, etc.) |
| company_id | uuid | YES | **FK → companies.id** |
| team_id | uuid | YES | **FK → team.id** |
| settings_notification | boolean | NO | Notification preferences (default: true) |
| is_archived | boolean | YES | Soft delete flag (default: false) |
| inserted_at | timestamp | NO | Record creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** companies (via company_id)
- **Belongs to:** team (via team_id)
- **Has many:** users_properties (many-to-many with properties)
- **Has many:** users_owners (many-to-many with owners)
- **Has many:** entries (as reviewer or assignee)

### Business Logic
- `auth_id` links to external authentication (likely Auth0 or similar)
- `role` field stores user's primary role
- `is_archived` provides soft delete functionality
- Users can be scoped to specific companies, teams, properties, or owners

---

## 11. TEAM

**Purpose:** Organizational teams within Snappt (e.g., Fraud Detection Team, QA Team).

**Primary Key:** `id` (UUID)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| name | varchar(255) | NO | Team name |
| timezone | varchar(255) | NO | Team timezone |
| country_id | integer | NO | **FK → country.id** |
| fde_manager_id | uuid | YES | **FK → users.id** (Fraud Detection Manager) |
| inserted_at | timestamp | NO | Record creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** country (via country_id)
- **Belongs to:** users (manager, via fde_manager_id)
- **Has many:** users

### Business Logic
- Teams have timezone and country for scheduling/localization
- `fde_manager_id` identifies the Fraud Detection team manager
- Supports distributed workforce

---

## 12. ROLE

**Purpose:** Defines user roles and permissions.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| name | varchar(255) | NO | Role name (e.g., 'admin', 'reviewer', 'property_manager') |

### Business Logic
- Simple role definition table
- Likely referenced by users.role field (via name, not FK)
- May have associated permissions in application code

---

## 13. USERS_PROPERTIES

**Purpose:** Junction table - many-to-many relationship between users and properties.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| user_id | uuid | NO | **FK → users.id** |
| property_id | uuid | NO | **FK → properties.id** |
| inserted_at | timestamp | NO | Record creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** users (via user_id)
- **Belongs to:** properties (via property_id)

### Business Logic
- Controls which properties a user can access
- Property managers typically have access to specific properties
- Snappt staff may have broader access

---

## 14. USERS_OWNERS

**Purpose:** Junction table - many-to-many relationship between users and owners.

**Primary Key:** Composite (owner_id, user_id)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| owner_id | uuid | NO | **FK → owners.id** (part of composite PK) |
| user_id | uuid | NO | **FK → users.id** (part of composite PK) |
| inserted_at | timestamp | NO | Record creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- **Belongs to:** users (via user_id)
- **Belongs to:** owners (via owner_id)

### Business Logic
- Controls which owners a user can access
- Users associated with an owner can see all properties owned by that owner
- Composite primary key ensures unique user-owner pairs

---

## Relationship Summary

### Primary Relationships

```
companies (1) ─────────────> (∞) properties
companies (1) ─────────────> (∞) users
companies (1) ─────────────> (∞) folders

properties (1) ────────────> (∞) folders
properties (∞) ←───────────> (∞) owners (via property_owners)
properties (∞) ←───────────> (∞) users (via users_properties)

folders (1) ───────────────> (∞) entries
folders (∞) ───────────────> (1) properties
folders (∞) ───────────────> (1) companies
folders (∞) ───────────────> (1) users (reviewer)

entries (1) ───────────────> (∞) applicants
entries (∞) ───────────────> (1) folders
entries (∞) ───────────────> (1) users (reviewer)
entries (∞) ───────────────> (1) users (assigned_to)

applicants (∞) ────────────> (1) entries
applicants (∞) ────────────> (1) applicant_details
applicants (1) ────────────> (∞) applicant_submissions

users (∞) ─────────────────> (1) companies
users (∞) ─────────────────> (1) team
users (∞) ←────────────────> (∞) properties (via users_properties)
users (∞) ←────────────────> (∞) owners (via users_owners)

team (∞) ──────────────────> (1) users (fde_manager)
```

### Key Access Control Patterns

1. **Company-based access:** Users belong to a company and can see company's properties/folders/entries
2. **Property-based access:** Users can be granted access to specific properties via users_properties
3. **Owner-based access:** Users can be granted access to all properties of an owner via users_owners
4. **Review assignment:** Entries can be assigned to specific reviewers for manual review

---

## Data Flow: Creating a New Screening Request

1. **Property Manager creates an entry** for an applicant at a property
2. **System creates/finds a folder** for this applicant+property combination
3. **Entry is created** and linked to folder
4. **Applicant record is created/updated** with contact info
5. **Applicant submits documents** → applicant_submission record created
6. **Entry status updates** as documents are processed
7. **ML/AI generates suggested_ruling** on entry
8. **Entry may be assigned to reviewer** for manual review
9. **Reviewer completes review** → entry status and result finalized
10. **Folder result updated** based on latest entry
11. **Notifications sent** to property manager and applicant

---

## Salesforce Integration Points

The following fields integrate with Salesforce CRM:

- **companies.salesforce_account_id** - Links company to Salesforce Account
- **properties.sfdc_id** - Links property to Salesforce Property
- **owners.salesforce_id** - Links owner to Salesforce Owner

This enables sales tracking, account management, and bi-directional sync.

---

## Performance Optimizations

### Denormalization
- folders table denormalizes company and property names for dashboard performance
- folders denormalizes last entry details to avoid joins

### Full-Text Search
- properties.textsearchable_index_col (tsvector) enables fast property search

### JSONB Fields
- applicant_details.prefilled_application_data - Flexible schema
- entries.metadata - Additional context
- properties.supported_doctypes - Configuration storage
- properties.identity_verification_flow_types - IDV configuration

---

## Next Steps

With the Core Entity Model documented, we can now move to **Fraud Detection Workflow** documentation, which will show how fraud_submissions, fraud_reviews, fraud_results, and fraud_document_reviews tables relate to these core entities.

**See:** FRAUD_DETECTION_WORKFLOW.md (to be created next)
