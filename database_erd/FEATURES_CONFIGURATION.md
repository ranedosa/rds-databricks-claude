# Features & Configuration System

**Generated:** 2025-11-25
**Database:** fraud_postgresql (Production)
**Tables Documented:** 7 feature flag and configuration tables

---

## Overview

The Features & Configuration System provides flexible feature flag management, A/B testing, gradual rollout capabilities, and system-wide configuration. This system enables property-level and user-level feature control, allowing Snappt to safely test and deploy new functionality incrementally.

**Key Functions:**
- **Feature Flags** - Enable/disable features per property or user
- **Gradual Rollout** - Deploy features to subset of properties for testing
- **A/B Testing** - Compare feature variants across properties
- **Permission Control** - User-level feature access
- **Audit Trail** - Track all feature enablement/disablement events
- **Global Configuration** - System-wide settings management

---

## Table Inventory

### Feature Management (4 tables)
- **features** - Master feature catalog
- **property_features** - Property-level feature enablement
- **user_features** - User-level feature access
- **property_feature_events** - Feature change event log

### Configuration & Reference (3 tables)
- **settings** - Global system settings/toggles
- **country** - Country reference data (ISO codes)
- **whitelist_info** - Document metadata whitelists for fraud detection

---

## Feature Flag Architecture

```
features (Master List)
    ├─> property_features (Property Enablement)
    │       └─> property_feature_events (Change History)
    └─> user_features (User Access)
```

**Feature Check Logic:**
```
Is feature X available for user Y reviewing property Z?
1. Check features.code exists
2. Check property_features: property_id=Z, feature_code=X, state='enabled'
3. Check user_features: user_id=Y, feature_code=X, state='enabled' (if feature requires user opt-in)
4. If both enabled → Feature available
```

---

## Detailed Table Documentation

## 1. FEATURES

**Purpose:** Master catalog of all available features in the system. Defines feature codes and names.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| name | varchar(255) | YES | Human-readable feature name |
| code | varchar(255) | YES | Feature code identifier (unique, used in code) |

### Relationships
- **Has many:** property_features (via feature_code)
- **Has many:** user_features (via feature_code)
- **Has many:** property_feature_events (via feature_code)

### Business Logic

**Feature Catalog Examples:**

| ID | Code | Name |
|----|------|------|
| 1 | identity_verification | Identity Verification (Incode/Persona) |
| 2 | income_verification | Automated Income Verification |
| 3 | asset_verification | Automated Asset Verification |
| 4 | rent_verification | Rent Payment History Check |
| 5 | batch_review | Batch Review Mode |
| 6 | auto_approval | Automatic Approval (ML confidence >95%) |
| 7 | expedited_review | Expedited Review (2-hour SLA) |
| 8 | multi_applicant | Multiple Applicants per Entry |
| 9 | api_access | API Integration Access |
| 10 | webhook_delivery | Webhook Result Delivery |

**Feature Types:**
- **Verification Features** - New verification workflows (identity, income, asset, rent)
- **Workflow Features** - Process improvements (batch review, auto-approval)
- **Integration Features** - External system access (API, webhooks)
- **UI Features** - New dashboard capabilities
- **Beta Features** - Experimental functionality

**Feature Code Conventions:**
- `snake_case` format
- Descriptive and concise
- Unique across all features
- Used directly in application code for feature checks

---

## 2. PROPERTY_FEATURES

**Purpose:** Property-level feature enablement. Controls which features are available for each property.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| feature_code | varchar(255) | NO | **FK → features.code** |
| property_id | uuid | NO | **FK → properties.id** |
| state | varchar(255) | NO | Feature state (enabled, disabled, testing) |
| inserted_at | timestamp | NO | When feature was added to property |
| updated_at | timestamp | NO | Last state change timestamp |

### Relationships
- **Belongs to:** features (via feature_code)
- **Belongs to:** properties (via property_id)

### Business Logic

**Feature States:**
- **enabled** - Feature active and available for property
- **disabled** - Feature turned off (but configuration retained)
- **testing** - Feature in A/B test mode (may have limited functionality)

**State Transitions:**
```
(created) → enabled → disabled → enabled
              ↓
           testing → enabled
```

**Use Cases:**

**1. Gradual Rollout:**
```sql
-- Enable identity verification for 10% of properties (pilot)
INSERT INTO property_features (feature_code, property_id, state)
SELECT 'identity_verification', id, 'enabled'
FROM properties
WHERE company_id IN (SELECT id FROM companies WHERE tier = 'enterprise')
ORDER BY RANDOM()
LIMIT (SELECT COUNT(*) * 0.1 FROM properties)::int;
```

**2. A/B Testing:**
```sql
-- 50% get auto_approval, 50% get manual review (control)
INSERT INTO property_features (feature_code, property_id, state)
SELECT 'auto_approval', id, 'testing'
FROM properties
WHERE id IN (
    SELECT id FROM properties ORDER BY RANDOM() LIMIT (SELECT COUNT(*) / 2 FROM properties)::int
);
```

**3. Feature Deprecation:**
```sql
-- Disable old feature, enable replacement
UPDATE property_features SET state = 'disabled' WHERE feature_code = 'old_income_calc';
INSERT INTO property_features (feature_code, property_id, state)
SELECT 'new_income_calc', property_id, 'enabled'
FROM property_features WHERE feature_code = 'old_income_calc';
```

**Feature Access Check:**
```sql
-- Is identity_verification enabled for property X?
SELECT EXISTS(
    SELECT 1 FROM property_features
    WHERE property_id = :property_id
      AND feature_code = 'identity_verification'
      AND state = 'enabled'
);
```

**Unique Constraint (Implied):**
- One row per (property_id, feature_code) combination
- Property can't have duplicate feature entries

---

## 3. USER_FEATURES

**Purpose:** User-level feature access control. Enables features for specific users (beta testers, internal staff, power users).

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| feature_code | varchar(255) | NO | Feature code identifier (not FK, allows unknown features) |
| user_id | uuid | NO | **FK → users.id** |
| state | varchar(255) | NO | Feature state (enabled, disabled) |
| inserted_at | timestamp | NO | When feature was granted to user |
| updated_at | timestamp | NO | Last state change timestamp |

### Relationships
- **Belongs to:** users (via user_id)
- **Implicitly references:** features (via feature_code, but not enforced)

### Business Logic

**User Feature States:**
- **enabled** - User has access to feature
- **disabled** - User access revoked

**Use Cases:**

**1. Beta Testing:**
```sql
-- Grant new dashboard feature to beta testers
INSERT INTO user_features (feature_code, user_id, state)
SELECT 'new_dashboard_v2', id, 'enabled'
FROM users
WHERE email IN ('beta_tester1@example.com', 'beta_tester2@example.com');
```

**2. Internal Staff Features:**
```sql
-- Enable admin tools for internal staff
INSERT INTO user_features (feature_code, user_id, state)
SELECT 'admin_tools', id, 'enabled'
FROM users
WHERE role IN ('admin', 'engineer', 'qa');
```

**3. Power User Features:**
```sql
-- Enable API access for specific power users
INSERT INTO user_features (feature_code, user_id, state)
SELECT 'api_access', id, 'enabled'
FROM users
WHERE company_id IN (SELECT id FROM companies WHERE api_enabled = true);
```

**Feature Check (Property + User):**
```sql
-- Can user Y access feature X on property Z?
SELECT
    pf.state as property_state,
    uf.state as user_state,
    CASE
        WHEN pf.state = 'enabled' AND (uf.state = 'enabled' OR uf.state IS NULL)
        THEN true
        ELSE false
    END as feature_available
FROM property_features pf
LEFT JOIN user_features uf ON uf.feature_code = pf.feature_code AND uf.user_id = :user_id
WHERE pf.feature_code = :feature_code AND pf.property_id = :property_id;
```

**Note on feature_code:**
- Not a foreign key to `features.code` (intentionally flexible)
- Allows user features for features not yet in catalog
- Enables experimental/temporary feature flags

---

## 4. PROPERTY_FEATURE_EVENTS

**Purpose:** Event log for property feature changes. Tracks when features are enabled, disabled, or modified.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| feature_code | varchar(255) | NO | **FK → features.code** |
| property_id | uuid | NO | **FK → properties.id** |
| event_type | varchar(255) | NO | Event type (enabled, disabled, updated) |
| inserted_at | timestamp | NO | Event timestamp |

### Relationships
- **Belongs to:** features (via feature_code)
- **Belongs to:** properties (via property_id)

### Business Logic

**Event Types:**
- **enabled** - Feature turned on for property
- **disabled** - Feature turned off for property
- **updated** - Feature state changed (e.g., enabled → testing)

**Event Log Examples:**
```
property_id=abc-123, feature_code='identity_verification', event_type='enabled'
→ Identity verification was enabled for this property

property_id=abc-123, feature_code='auto_approval', event_type='disabled'
→ Auto-approval was disabled for this property

property_id=abc-123, feature_code='batch_review', event_type='updated'
→ Batch review configuration was updated
```

**Usage:**

**1. Audit Trail:**
```sql
-- When was identity_verification enabled for this property?
SELECT inserted_at
FROM property_feature_events
WHERE property_id = :property_id
  AND feature_code = 'identity_verification'
  AND event_type = 'enabled'
ORDER BY inserted_at DESC
LIMIT 1;
```

**2. Feature Adoption Timeline:**
```sql
-- How many properties enabled income_verification per day?
SELECT
    DATE(inserted_at) as date,
    COUNT(DISTINCT property_id) as properties_enabled
FROM property_feature_events
WHERE feature_code = 'income_verification'
  AND event_type = 'enabled'
GROUP BY DATE(inserted_at)
ORDER BY date;
```

**3. Feature Churn:**
```sql
-- Properties that enabled then disabled a feature
SELECT property_id, COUNT(*) as toggles
FROM property_feature_events
WHERE feature_code = :feature_code
GROUP BY property_id
HAVING COUNT(*) > 1
ORDER BY toggles DESC;
```

---

## 5. SETTINGS

**Purpose:** Global system-wide settings and feature toggles. Controls platform-level configuration.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| name | varchar(255) | YES | Setting name/key |
| enabled | boolean | NO | Setting state (default: false) |
| inserted_at | timestamp | NO | Setting creation timestamp |
| updated_at | timestamp | NO | Last update timestamp |

### Relationships
- None (standalone configuration table)

### Business Logic

**Setting Examples:**

| Name | Enabled | Description |
|------|---------|-------------|
| maintenance_mode | false | System-wide maintenance mode |
| allow_new_registrations | true | Allow new property signups |
| auto_fraud_detection | true | Enable automated fraud detection |
| ml_model_v2_enabled | false | Use new ML model (A/B test) |
| webhook_delivery_retry | true | Enable webhook retry on failure |
| email_notifications | true | Send email notifications to applicants |
| sla_enforcement | true | Enforce review SLAs |
| batch_processing | true | Enable batch entry processing |

**Use Cases:**

**1. Maintenance Mode:**
```sql
-- Enable maintenance mode (disable all non-admin access)
UPDATE settings SET enabled = true WHERE name = 'maintenance_mode';
```

**2. Feature Kill Switch:**
```sql
-- Disable all automated fraud detection (emergency)
UPDATE settings SET enabled = false WHERE name = 'auto_fraud_detection';
```

**3. Gradual Feature Rollout:**
```sql
-- Enable new ML model globally after successful A/B test
UPDATE settings SET enabled = true WHERE name = 'ml_model_v2_enabled';
```

**Configuration Check:**
```sql
-- Is auto fraud detection enabled?
SELECT enabled FROM settings WHERE name = 'auto_fraud_detection';
```

**Difference from Features:**
- **settings** - System-wide toggles (applies to all properties/users)
- **features** - Property/user-specific toggles (granular control)

---

## 6. COUNTRY

**Purpose:** Country reference data with ISO codes. Used for localization, team assignment, and regional settings.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| name | varchar(255) | NO | Country name (e.g., "United States") |
| alfa2 | varchar(255) | NO | ISO 3166-1 alpha-2 code (e.g., "US") |
| alfa3 | varchar(255) | NO | ISO 3166-1 alpha-3 code (e.g., "USA") |
| numcode | integer | NO | ISO 3166-1 numeric code (e.g., 840) |

### Relationships
- **Referenced by:** team (via country_id)

### Business Logic

**Standard Reference Data:**
```
id=1, name='United States', alfa2='US', alfa3='USA', numcode=840
id=2, name='Canada', alfa2='CA', alfa3='CAN', numcode=124
id=3, name='Mexico', alfa2='MX', alfa3='MEX', numcode=484
id=4, name='United Kingdom', alfa2='GB', alfa3='GBR', numcode=826
```

**Use Cases:**

**1. Team Assignment:**
```sql
-- US-based review teams
SELECT t.* FROM team t
JOIN country c ON t.country_id = c.id
WHERE c.alfa2 = 'US';
```

**2. Localization:**
```sql
-- Properties in specific country
SELECT p.* FROM properties p
WHERE p.country_code = (SELECT alfa2 FROM country WHERE id = :country_id);
```

**3. Regional Settings:**
- Date format preferences
- Currency display
- Timezone defaults
- Language selection

**ISO 3166-1 Standard:**
- **alfa2** - 2-letter code (most commonly used)
- **alfa3** - 3-letter code (more readable)
- **numcode** - Numeric code (machine-readable)

---

## 7. WHITELIST_INFO

**Purpose:** Document metadata whitelists for fraud detection. Stores known-good metadata values to reduce false positives.

**Primary Key:** `id` (bigint, auto-increment)

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | bigint | NO | Primary key (auto-increment) |
| key | varchar(255) | YES | Whitelist entry key/identifier |
| producer | varchar(255) | YES | PDF producer software (e.g., "Adobe Acrobat") |
| creator | varchar(255) | YES | PDF creator application |
| author | varchar(255) | YES | Document author field |
| fonts | array(varchar) | YES | Array of legitimate font names |
| breakups | array(varchar) | YES | Array of legitimate text patterns |

### Relationships
- None (reference data for fraud detection algorithms)

### Business Logic

**Purpose:**
Fraud detection algorithms analyze document metadata (PDF properties, fonts, text patterns). Legitimate documents may have variations that look suspicious. Whitelists prevent false positives by marking known-good values.

**Whitelist Entry Examples:**

**1. Payroll Software Producer:**
```
key='adp_paystub'
producer='ADP Payroll System'
creator='ADP Report Generator'
fonts=['Arial', 'Helvetica', 'Times New Roman']
breakups=['Employee ID:', 'Pay Period:', 'Net Pay:']
```

**2. Bank Statement Producer:**
```
key='chase_bank_statement'
producer='JPMorgan Chase Statement Generator'
creator='Chase Online Banking'
fonts=['Chase Sans', 'Arial']
breakups=['Account Number:', 'Statement Period:', 'Beginning Balance:']
```

**3. Accounting Software:**
```
key='quickbooks_report'
producer='QuickBooks'
creator='Intuit QuickBooks Desktop'
fonts=['Arial', 'Calibri']
breakups=['Company Name:', 'Report Date:', 'Total:']
```

**Fraud Detection Integration:**
```python
# Pseudo-code
def check_metadata_fraud(document):
    metadata = extract_metadata(document)

    # Check if producer/creator match whitelist
    whitelist = query_whitelist(metadata.producer, metadata.creator)

    if whitelist:
        # Known-good metadata, reduce fraud score
        if metadata.producer == whitelist.producer:
            fraud_score -= 10
        if metadata.fonts in whitelist.fonts:
            fraud_score -= 5
        if has_expected_patterns(metadata.text, whitelist.breakups):
            fraud_score -= 5
    else:
        # Unknown metadata, increase scrutiny
        if metadata.producer == 'Unknown':
            fraud_score += 5

    return fraud_score
```

**Use Cases:**

**1. Reduce False Positives:**
- Legitimate paystubs from ADP/Paychex have specific metadata
- Don't flag these as suspicious

**2. Known-Good Fonts:**
- Arial, Helvetica common in legitimate documents
- Custom fonts more suspicious

**3. Expected Text Patterns:**
- "Pay Period:", "Net Pay:" expected in paystubs
- Presence of these patterns reduces fraud likelihood

**Maintenance:**
- Add new whitelists as new payroll/banking software identified
- Remove obsolete entries for deprecated software
- Update based on false positive analysis

---

## Feature Flag Workflow Examples

### Example 1: Launching Identity Verification

**Phase 1: Internal Testing**
```sql
-- Enable for internal test property
INSERT INTO property_features (feature_code, property_id, state)
VALUES ('identity_verification', 'test-property-uuid', 'enabled');

-- Enable for QA team users
INSERT INTO user_features (feature_code, user_id, state)
SELECT 'identity_verification', id, 'enabled'
FROM users WHERE team_id = (SELECT id FROM team WHERE name = 'QA');
```

**Phase 2: Beta (10 Enterprise Properties)**
```sql
-- Enable for select enterprise customers
INSERT INTO property_features (feature_code, property_id, state)
SELECT 'identity_verification', id, 'enabled'
FROM properties
WHERE company_id IN (SELECT id FROM companies WHERE tier = 'enterprise')
ORDER BY RANDOM()
LIMIT 10;

-- Log events
INSERT INTO property_feature_events (feature_code, property_id, event_type)
SELECT 'identity_verification', id, 'enabled'
FROM properties WHERE id IN (...);
```

**Phase 3: General Availability**
```sql
-- Enable for all properties
INSERT INTO property_features (feature_code, property_id, state)
SELECT 'identity_verification', id, 'enabled'
FROM properties
WHERE id NOT IN (SELECT property_id FROM property_features WHERE feature_code = 'identity_verification');
```

---

### Example 2: A/B Testing Auto-Approval

**Setup Test:**
```sql
-- 50% of properties get auto-approval
INSERT INTO property_features (feature_code, property_id, state)
SELECT 'auto_approval', id, 'testing'
FROM properties
WHERE id IN (
    SELECT id FROM properties ORDER BY RANDOM() LIMIT (SELECT COUNT(*) / 2 FROM properties)::int
);

-- Log test start
INSERT INTO property_feature_events (feature_code, property_id, event_type)
SELECT 'auto_approval', property_id, 'enabled'
FROM property_features WHERE feature_code = 'auto_approval';
```

**Analyze Results:**
```sql
-- Compare review times: auto-approval vs manual
SELECT
    CASE WHEN pf.property_id IS NOT NULL THEN 'Auto-Approval' ELSE 'Manual' END as group,
    AVG(EXTRACT(EPOCH FROM (e.report_complete_time - e.submission_time))) / 60 as avg_minutes,
    COUNT(*) as entries
FROM entries e
LEFT JOIN property_features pf ON pf.property_id = (
    SELECT property_id FROM folders WHERE id = e.folder_id
) AND pf.feature_code = 'auto_approval' AND pf.state = 'testing'
WHERE e.submission_time > NOW() - interval '30 days'
GROUP BY group;
```

**Winner Decision:**
```sql
-- Auto-approval wins → enable for all
UPDATE property_features SET state = 'enabled'
WHERE feature_code = 'auto_approval' AND state = 'testing';

INSERT INTO property_features (feature_code, property_id, state)
SELECT 'auto_approval', id, 'enabled'
FROM properties
WHERE id NOT IN (SELECT property_id FROM property_features WHERE feature_code = 'auto_approval');
```

---

## Performance Considerations

### Indexes Recommended

```sql
-- property_features: Feature checks
CREATE UNIQUE INDEX idx_property_features_unique
  ON property_features(property_id, feature_code);

CREATE INDEX idx_property_features_code_state
  ON property_features(feature_code, state)
  WHERE state = 'enabled';

-- user_features: User access checks
CREATE UNIQUE INDEX idx_user_features_unique
  ON user_features(user_id, feature_code);

CREATE INDEX idx_user_features_code_state
  ON user_features(feature_code, state)
  WHERE state = 'enabled';

-- property_feature_events: Event queries
CREATE INDEX idx_property_feature_events_property
  ON property_feature_events(property_id, inserted_at DESC);

CREATE INDEX idx_property_feature_events_feature
  ON property_feature_events(feature_code, event_type, inserted_at DESC);

-- features: Code lookups
CREATE UNIQUE INDEX idx_features_code ON features(code);

-- settings: Name lookups
CREATE UNIQUE INDEX idx_settings_name ON settings(name);

-- country: ISO code lookups
CREATE UNIQUE INDEX idx_country_alfa2 ON country(alfa2);
CREATE UNIQUE INDEX idx_country_alfa3 ON country(alfa3);

-- whitelist_info: Key lookups
CREATE INDEX idx_whitelist_info_key ON whitelist_info(key);
CREATE INDEX idx_whitelist_info_producer ON whitelist_info(producer);
```

---

## Business Metrics & KPIs

### Feature Adoption

```sql
-- Properties with each feature enabled
SELECT
    f.name,
    COUNT(pf.id) as properties_enabled,
    COUNT(pf.id) * 100.0 / (SELECT COUNT(*) FROM properties) as pct_adoption
FROM features f
LEFT JOIN property_features pf ON f.code = pf.feature_code AND pf.state = 'enabled'
GROUP BY f.name
ORDER BY pct_adoption DESC;
```

### Feature Rollout Timeline

```sql
-- Feature enablement over time
SELECT
    DATE(inserted_at) as date,
    feature_code,
    COUNT(*) as properties_enabled_today,
    SUM(COUNT(*)) OVER (PARTITION BY feature_code ORDER BY DATE(inserted_at)) as cumulative_enabled
FROM property_feature_events
WHERE event_type = 'enabled'
GROUP BY DATE(inserted_at), feature_code
ORDER BY date, feature_code;
```

### Feature Churn Rate

```sql
-- Properties that disabled features
SELECT
    feature_code,
    COUNT(DISTINCT property_id) as properties_disabled
FROM property_feature_events
WHERE event_type = 'disabled'
  AND inserted_at > NOW() - interval '30 days'
GROUP BY feature_code
ORDER BY properties_disabled DESC;
```

---

## Summary

**7 Tables Documented:**
- **features** - Master feature catalog (codes and names)
- **property_features** - Property-level feature enablement
- **user_features** - User-level feature access
- **property_feature_events** - Feature change event log
- **settings** - Global system settings
- **country** - Country reference data (ISO codes)
- **whitelist_info** - Document metadata whitelists

**Key Capabilities:**
- Feature flag management (enable/disable per property)
- Gradual rollout (deploy to subset, then expand)
- A/B testing (compare variants)
- User-level permissions (beta testing, internal features)
- Event audit trail (track all changes)
- Global configuration (system-wide toggles)
- Fraud detection optimization (whitelists reduce false positives)

**Integration Points:**
- Properties (feature enablement)
- Users (feature access)
- Team (country-based localization)
- Proof/Fraud Detection (whitelist integration)

**Use Cases:**
- Safe deployment of new verification types
- Customer-specific feature configuration
- A/B testing for optimization
- Emergency feature kill switches
- Regional localization
- Fraud algorithm tuning

---

**Next Documentation:**
- Integration Layer (6 tables): webhooks, Yardi integration
- Supporting Systems (remaining tables)

**See Also:**
- [CORE_ENTITY_MODEL.md](CORE_ENTITY_MODEL.md) - properties, users tables
- [REVIEW_QUEUE_SYSTEM.md](REVIEW_QUEUE_SYSTEM.md) - review workflow integration
- [FRAUD_DETECTION_WORKFLOW.md](FRAUD_DETECTION_WORKFLOW.md) - whitelist_info usage

---

**Generated:** 2025-11-25
**Last Updated:** 2025-11-25
**Version:** 1.0
**Tables Documented:** 7 of 75 core tables
