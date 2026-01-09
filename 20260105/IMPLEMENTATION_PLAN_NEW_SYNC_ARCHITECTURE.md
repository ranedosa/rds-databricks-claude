# Implementation Plan: New RDS → Salesforce Sync Architecture

**Date:** January 6, 2026
**Author:** Claude Code
**Status:** Ready for Implementation
**Estimated Timeline:** 3-4 weeks

---

## 📋 EXECUTIVE SUMMARY

### Goal
Implement a ground-up redesign of the RDS → Salesforce property sync that:
- Handles many-to-1 relationships (multiple RDS properties → single SFDC ID)
- Eliminates the chicken-and-egg problem with production IDs
- Separates create vs update logic cleanly
- Provides clear business rules for feature aggregation
- Enables full auditability and monitoring

### Architecture Overview
```
RDS Properties (Source)
    ↓
Databricks Aggregation Layer (NEW)
    ├─ Enrich properties with features
    ├─ Aggregate by SFDC ID (many-to-1)
    └─ Stratify: Create vs Update
    ↓
Census Reverse ETL (2 Separate Syncs)
    ├─ Sync A: Create new properties
    └─ Sync B: Update existing properties
    ↓
Salesforce product_property (Staging)
    ↓
Salesforce Property (Production) - via SF workflow
```

### Expected Outcomes
- **1,081 properties** currently missing from Salesforce will be created
- **2,410 properties** blocked by duplicate SFDC IDs will start syncing correctly
- **507 P1 critical properties** with features will appear in Salesforce
- **799 feature mismatches** will be resolved
- **Ongoing sync accuracy**: 99%+ (up from ~90%)

---

## 🎯 IMPLEMENTATION PHASES

### Phase 1: Foundation - Build Databricks Views (Week 1, Days 1-3)
**Goal:** Create the aggregation layer that handles many-to-1 relationships

**Deliverables:**
- View: `rds_properties_enriched` (properties + features)
- View: `properties_aggregated_by_sfdc_id` (core aggregation logic)
- View: `properties_to_create` (net new properties)
- View: `properties_to_update` (existing properties)
- Table: `property_sync_audit_log` (audit trail)

**Duration:** 3 days
**Risk Level:** Low (read-only views)

---

### Phase 2: Validation & Testing (Week 1, Days 4-5)
**Goal:** Validate aggregation logic and view correctness

**Deliverables:**
- Validation queries confirming correct behavior
- Test cases for known scenarios (Park Kennedy, etc.)
- Data quality report

**Duration:** 2 days
**Risk Level:** Low (testing only)

---

### Phase 3: Census Configuration (Week 2, Days 1-3)
**Goal:** Set up two separate Census syncs with correct configurations

**Deliverables:**
- Census Sync A: Create New Properties (configured & tested)
- Census Sync B: Update Existing Properties (configured & tested)
- Sync schedules and error handling

**Duration:** 3 days
**Risk Level:** Medium (requires Census access and testing)

---

### Phase 4: Pilot Rollout (Week 2, Days 4-5)
**Goal:** Test on small subset to validate end-to-end flow

**Deliverables:**
- 50 properties synced via Sync A (creates)
- 50 properties synced via Sync B (updates)
- Validation of SF workflow trigger
- Bug fixes and refinements

**Duration:** 2 days
**Risk Level:** Medium (real data, limited scope)

---

### Phase 5: Full Rollout (Week 3)
**Goal:** Sync all properties with new architecture

**Deliverables:**
- Full Sync A execution (1,081+ properties)
- Full Sync B execution (7,980+ properties)
- 48-hour monitoring period
- Issue resolution

**Duration:** 5 days (includes monitoring)
**Risk Level:** Medium-High (production impact)

---

### Phase 6: Monitoring & Documentation (Week 4)
**Goal:** Ensure ongoing health and document new system

**Deliverables:**
- Databricks monitoring dashboard
- Automated alerts for sync failures
- Runbook for common issues
- Architecture documentation updates

**Duration:** 5 days
**Risk Level:** Low

---

## 📝 PHASE 1: BUILD DATABRICKS VIEWS

### Pre-Flight Checklist

- [ ] Confirm Databricks workspace access: `dbc-9ca0f5e0-2208.cloud.databricks.com`
- [ ] Verify database permissions for `crm.sfdc_dbx` schema
- [ ] Backup existing views (if any need to be modified)
- [ ] Confirm source table availability:
  - [ ] `rds.pg_rds_public.properties`
  - [ ] `rds.pg_rds_public.property_features`
  - [ ] `crm.salesforce.product_property`

---

### Step 1.1: Create Base Enrichment View

**File:** `sql/01_create_rds_properties_enriched.sql`

```sql
-- ============================================================================
-- VIEW: rds_properties_enriched
-- PURPOSE: Join RDS properties with all feature data
-- DEPENDENCIES: rds.pg_rds_public.properties, property_features
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.rds_properties_enriched AS

SELECT
  -- Property Identifiers
  p.id AS rds_property_id,
  p.sfdc_id,
  p.short_id,
  p.company_id,

  -- Property Attributes
  p.name AS property_name,
  p.status AS property_status,
  p.address_street AS address,
  p.address_city AS city,
  p.address_state AS state,
  p.address_postal_code AS postal_code,
  p.address_country AS country,

  -- Timestamps
  p.created_at,
  p.updated_at,

  -- Company Info (if needed)
  p.company_name,

  -- Feature Flags (COALESCE to FALSE if no feature record)
  COALESCE(pf.idv_enabled, FALSE) AS idv_enabled,
  COALESCE(pf.bank_linking_enabled, FALSE) AS bank_linking_enabled,
  COALESCE(pf.payroll_enabled, FALSE) AS payroll_enabled,
  COALESCE(pf.income_insights_enabled, FALSE) AS income_insights_enabled,
  COALESCE(pf.document_fraud_enabled, FALSE) AS document_fraud_enabled,

  -- Feature Enabled Timestamps
  pf.idv_enabled_at,
  pf.bank_linking_enabled_at,
  pf.payroll_enabled_at,
  pf.income_insights_enabled_at,
  pf.document_fraud_enabled_at,

  -- Feature Metadata
  pf.feature_count,
  pf.last_feature_update_at,

  -- Calculated Fields
  CASE
    WHEN p.status = 'ACTIVE' THEN 1
    ELSE 0
  END AS is_active,

  CASE
    WHEN p.sfdc_id IS NOT NULL AND p.sfdc_id != 'XXXXXXXXXXXXXXX' THEN 1
    ELSE 0
  END AS has_valid_sfdc_id

FROM rds.pg_rds_public.properties p
LEFT JOIN rds.pg_rds_public.property_features pf
  ON p.id = pf.property_id

WHERE p.company_id IS NOT NULL  -- Must have a company
  AND p.status != 'DELETED';     -- Exclude soft-deleted properties

-- Add comment for documentation
COMMENT ON VIEW crm.sfdc_dbx.rds_properties_enriched IS
'Enriched view of RDS properties with all feature data joined. One row per RDS property.';
```

**Validation Query:**

```sql
-- Verify row count matches expectations
SELECT
  COUNT(*) AS total_properties,
  COUNT(DISTINCT rds_property_id) AS unique_properties,
  SUM(is_active) AS active_properties,
  SUM(has_valid_sfdc_id) AS properties_with_sfdc_id,
  SUM(CASE WHEN idv_enabled THEN 1 ELSE 0 END) AS with_idv_enabled,
  SUM(CASE WHEN bank_linking_enabled THEN 1 ELSE 0 END) AS with_bank_enabled
FROM crm.sfdc_dbx.rds_properties_enriched;

-- Expected results (approximately):
-- total_properties: ~20,000
-- active_properties: ~12,000
-- properties_with_sfdc_id: ~11,000
```

---

### Step 1.2: Create Aggregation View (Core Innovation)

**File:** `sql/02_create_properties_aggregated_by_sfdc_id.sql`

```sql
-- ============================================================================
-- VIEW: properties_aggregated_by_sfdc_id
-- PURPOSE: Aggregate multiple RDS properties into single SFDC ID
-- BUSINESS RULES:
--   1. Only ACTIVE properties contribute to aggregation
--   2. Feature flags use UNION logic (any TRUE -> TRUE)
--   3. Timestamps use earliest enabled date
--   4. Property metadata from primary ACTIVE property
--   5. Full audit trail of contributing properties
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.properties_aggregated_by_sfdc_id AS

WITH active_properties AS (
  -- Filter to only ACTIVE properties with valid SFDC IDs
  SELECT *
  FROM crm.sfdc_dbx.rds_properties_enriched
  WHERE property_status = 'ACTIVE'
    AND has_valid_sfdc_id = 1
),

aggregated AS (
  SELECT
    sfdc_id,

    -- ====================================================================
    -- RULE 1: Property Metadata (from primary/most recent ACTIVE property)
    -- ====================================================================

    -- Use the most recently updated property as "primary"
    MAX_BY(rds_property_id, updated_at) AS primary_rds_property_id,
    MAX_BY(property_name, updated_at) AS property_name,
    MAX_BY(short_id, updated_at) AS short_id,
    MAX_BY(address, updated_at) AS address,
    MAX_BY(city, updated_at) AS city,
    MAX_BY(state, updated_at) AS state,
    MAX_BY(postal_code, updated_at) AS postal_code,
    MAX_BY(country, updated_at) AS country,
    MAX_BY(company_id, updated_at) AS company_id,
    MAX_BY(company_name, updated_at) AS company_name,

    -- ====================================================================
    -- RULE 2: Feature Flags - UNION Logic (any ACTIVE property has it -> TRUE)
    -- ====================================================================

    MAX(idv_enabled) AS idv_enabled,
    MAX(bank_linking_enabled) AS bank_linking_enabled,
    MAX(payroll_enabled) AS payroll_enabled,
    MAX(income_insights_enabled) AS income_insights_enabled,
    MAX(document_fraud_enabled) AS document_fraud_enabled,

    -- ====================================================================
    -- RULE 3: Feature Timestamps - Earliest enabled date
    -- ====================================================================

    MIN(CASE WHEN idv_enabled THEN idv_enabled_at END) AS idv_enabled_at,
    MIN(CASE WHEN bank_linking_enabled THEN bank_linking_enabled_at END) AS bank_linking_enabled_at,
    MIN(CASE WHEN payroll_enabled THEN payroll_enabled_at END) AS payroll_enabled_at,
    MIN(CASE WHEN income_insights_enabled THEN income_insights_enabled_at END) AS income_insights_enabled_at,
    MIN(CASE WHEN document_fraud_enabled THEN document_fraud_enabled_at END) AS document_fraud_enabled_at,

    -- ====================================================================
    -- RULE 4: Calculated Metrics
    -- ====================================================================

    COUNT(DISTINCT rds_property_id) AS active_property_count,
    SUM(feature_count) AS total_feature_count,
    MAX(last_feature_update_at) AS last_feature_update_at,

    -- ====================================================================
    -- RULE 5: Audit Trail - Which properties contributed?
    -- ====================================================================

    COLLECT_LIST(rds_property_id) AS contributing_rds_property_ids,
    COLLECT_LIST(STRUCT(
      rds_property_id,
      property_name,
      short_id,
      updated_at,
      idv_enabled,
      bank_linking_enabled,
      payroll_enabled,
      income_insights_enabled,
      document_fraud_enabled
    )) AS contributing_properties_detail,

    -- ====================================================================
    -- Metadata
    -- ====================================================================

    MIN(created_at) AS earliest_property_created_at,
    MAX(updated_at) AS most_recent_property_updated_at,
    CURRENT_TIMESTAMP() AS aggregated_at

  FROM active_properties
  GROUP BY sfdc_id
)

SELECT
  *,

  -- Flags for monitoring
  CASE WHEN active_property_count > 1 THEN TRUE ELSE FALSE END AS is_multi_property,
  CASE
    WHEN idv_enabled OR bank_linking_enabled OR payroll_enabled
         OR income_insights_enabled OR document_fraud_enabled
    THEN TRUE
    ELSE FALSE
  END AS has_any_features_enabled

FROM aggregated;

-- Add comment for documentation
COMMENT ON VIEW crm.sfdc_dbx.properties_aggregated_by_sfdc_id IS
'Aggregates multiple RDS properties sharing the same SFDC ID. Implements union logic for features (any ACTIVE property with feature enabled → aggregated record shows enabled). One row per SFDC ID.';
```

**Validation Queries:**

```sql
-- 1. Check aggregation counts
SELECT
  active_property_count,
  COUNT(*) AS sfdc_id_count,
  SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS with_features
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
GROUP BY active_property_count
ORDER BY active_property_count;

-- Expected: Most SFDC IDs have 1 property, some have 2+

-- 2. Validate Park Kennedy case
SELECT
  sfdc_id,
  primary_rds_property_id,
  property_name,
  active_property_count,
  contributing_rds_property_ids,
  idv_enabled,
  bank_linking_enabled,
  payroll_enabled,
  income_insights_enabled
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
WHERE sfdc_id = 'a01Dn00000HHUanIAH';  -- Park Kennedy

-- Expected: Should show features enabled (from ACTIVE property only)

-- 3. Compare aggregated vs non-aggregated counts
SELECT
  'Distinct SFDC IDs' AS metric,
  COUNT(DISTINCT sfdc_id) AS count
FROM crm.sfdc_dbx.rds_properties_enriched
WHERE has_valid_sfdc_id = 1 AND is_active = 1

UNION ALL

SELECT
  'Aggregated SFDC IDs' AS metric,
  COUNT(*) AS count
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id;

-- These should match (same number of unique SFDC IDs)
```

---

### Step 1.3: Create "Properties to Create" View

**File:** `sql/03_create_properties_to_create.sql`

```sql
-- ============================================================================
-- VIEW: properties_to_create
-- PURPOSE: RDS properties that DO NOT exist in product_property yet
-- USAGE: Source for Census Sync A (Create New Properties)
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.properties_to_create AS

SELECT
  -- Identifiers (RDS.id is the key for new records)
  rds_property_id,
  short_id,
  company_id,

  -- Property Data
  property_name,
  address,
  city,
  state,
  postal_code,
  country,
  company_name,

  -- Feature Flags
  idv_enabled,
  bank_linking_enabled,
  payroll_enabled,
  income_insights_enabled,
  document_fraud_enabled,

  -- Feature Timestamps
  idv_enabled_at,
  bank_linking_enabled_at,
  payroll_enabled_at,
  income_insights_enabled_at,
  document_fraud_enabled_at,

  -- Metadata
  created_at,
  updated_at,

  -- Sync metadata
  CURRENT_TIMESTAMP() AS sync_queued_at,
  'CREATE' AS sync_operation

FROM crm.sfdc_dbx.rds_properties_enriched rds

-- FILTER: Only properties NOT in product_property
WHERE NOT EXISTS (
  SELECT 1
  FROM crm.salesforce.product_property pp
  WHERE CAST(rds.rds_property_id AS STRING) = pp.snappt_property_id_c
    AND pp.is_deleted = FALSE
)

-- Only create ACTIVE properties
AND rds.property_status = 'ACTIVE'

-- Must have valid company
AND rds.company_id IS NOT NULL;

-- Add comment
COMMENT ON VIEW crm.sfdc_dbx.properties_to_create IS
'RDS properties that need to be created in product_property. Source for Census Sync A.';
```

**Validation Query:**

```sql
-- Count of properties to create
SELECT
  COUNT(*) AS properties_to_create,
  SUM(CASE WHEN idv_enabled OR bank_linking_enabled OR payroll_enabled
           OR income_insights_enabled THEN 1 ELSE 0 END) AS with_features_enabled,
  COUNT(DISTINCT company_id) AS distinct_companies
FROM crm.sfdc_dbx.properties_to_create;

-- Expected: ~1,081 properties (from earlier analysis)

-- Sample 10 records
SELECT *
FROM crm.sfdc_dbx.properties_to_create
LIMIT 10;
```

---

### Step 1.4: Create "Properties to Update" View

**File:** `sql/04_create_properties_to_update.sql`

```sql
-- ============================================================================
-- VIEW: properties_to_update
-- PURPOSE: Properties that ALREADY exist in product_property and need updates
-- USAGE: Source for Census Sync B (Update Existing Properties)
-- STRATEGY: Use aggregated data (handles many-to-1)
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.properties_to_update AS

SELECT
  -- Link to existing SF record
  pp.snappt_property_id_c,  -- This is how Census finds the existing record
  pp.id AS product_property_staging_id,  -- For reference
  pp.sf_property_id_c AS production_salesforce_id,  -- For reference

  -- Aggregated data from RDS (may come from multiple RDS properties)
  agg.sfdc_id,
  agg.primary_rds_property_id,
  agg.property_name,
  agg.short_id,
  agg.address,
  agg.city,
  agg.state,
  agg.postal_code,
  agg.country,
  agg.company_id,
  agg.company_name,

  -- Aggregated Feature Flags (union logic applied)
  agg.idv_enabled,
  agg.bank_linking_enabled,
  agg.payroll_enabled,
  agg.income_insights_enabled,
  agg.document_fraud_enabled,

  -- Feature Timestamps (earliest across all contributing properties)
  agg.idv_enabled_at,
  agg.bank_linking_enabled_at,
  agg.payroll_enabled_at,
  agg.income_insights_enabled_at,
  agg.document_fraud_enabled_at,

  -- Aggregation Metadata (for audit trail)
  agg.active_property_count,
  agg.contributing_rds_property_ids,
  agg.total_feature_count,
  agg.is_multi_property,
  agg.has_any_features_enabled,

  -- Timestamps
  agg.most_recent_property_updated_at AS rds_last_updated_at,
  pp.last_modified_date AS sf_last_updated_at,

  -- Change detection
  CASE
    WHEN agg.most_recent_property_updated_at > pp.last_modified_date
    THEN TRUE
    ELSE FALSE
  END AS has_changes_since_last_sync,

  -- Sync metadata
  CURRENT_TIMESTAMP() AS sync_queued_at,
  'UPDATE' AS sync_operation

FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id agg

-- Join to existing product_property records
INNER JOIN crm.salesforce.product_property pp
  ON agg.sfdc_id = pp.sf_property_id_c  -- Match on production SFDC ID

WHERE pp.is_deleted = FALSE

-- Optional: Only sync if there are changes (reduces Census API calls)
-- Uncomment the line below to enable change detection:
-- AND agg.most_recent_property_updated_at > pp.last_modified_date
;

-- Add comment
COMMENT ON VIEW crm.sfdc_dbx.properties_to_update IS
'Properties that already exist in product_property and need updates. Uses aggregated data for many-to-1 relationships. Source for Census Sync B.';
```

**Validation Queries:**

```sql
-- 1. Count of properties to update
SELECT
  COUNT(*) AS properties_to_update,
  SUM(CASE WHEN is_multi_property THEN 1 ELSE 0 END) AS multi_property_records,
  SUM(CASE WHEN has_changes_since_last_sync THEN 1 ELSE 0 END) AS with_pending_changes,
  SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS with_features_enabled
FROM crm.sfdc_dbx.properties_to_update;

-- Expected: ~7,980 properties (from earlier analysis)

-- 2. Multi-property breakdown
SELECT
  active_property_count,
  COUNT(*) AS record_count,
  SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS with_features
FROM crm.sfdc_dbx.properties_to_update
GROUP BY active_property_count
ORDER BY active_property_count;

-- 3. Sample records with multiple contributing properties
SELECT
  sfdc_id,
  property_name,
  active_property_count,
  contributing_rds_property_ids,
  idv_enabled,
  bank_linking_enabled,
  has_any_features_enabled
FROM crm.sfdc_dbx.properties_to_update
WHERE is_multi_property = TRUE
LIMIT 20;
```

---

### Step 1.5: Create Audit Log Table

**File:** `sql/05_create_property_sync_audit_log.sql`

```sql
-- ============================================================================
-- TABLE: property_sync_audit_log
-- PURPOSE: Track every sync operation for auditability
-- ============================================================================

CREATE TABLE IF NOT EXISTS crm.sfdc_dbx.property_sync_audit_log (
  -- Audit identifiers
  audit_id BIGINT GENERATED ALWAYS AS IDENTITY,
  sync_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),

  -- Sync operation details
  sync_operation STRING NOT NULL,  -- 'CREATE' or 'UPDATE'
  census_sync_name STRING,         -- Which Census sync ran

  -- Property identifiers
  rds_property_id STRING,
  snappt_property_id_c STRING,
  sfdc_id STRING,
  product_property_staging_id STRING,

  -- Sync payload summary
  property_name STRING,
  company_id STRING,
  active_property_count INT,
  contributing_rds_property_ids ARRAY<STRING>,

  -- Feature state at time of sync
  idv_enabled BOOLEAN,
  bank_linking_enabled BOOLEAN,
  payroll_enabled BOOLEAN,
  income_insights_enabled BOOLEAN,
  document_fraud_enabled BOOLEAN,

  -- Sync status
  sync_status STRING,              -- 'QUEUED', 'SUCCESS', 'FAILED'
  sync_error_message STRING,

  -- Metadata
  created_by STRING DEFAULT CURRENT_USER(),

  -- Constraints
  CONSTRAINT pk_audit_log PRIMARY KEY (audit_id)
)
USING DELTA
PARTITIONED BY (DATE(sync_timestamp))
COMMENT 'Audit log for all RDS → Salesforce property sync operations';

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_rds_property_id
  ON crm.sfdc_dbx.property_sync_audit_log (rds_property_id);

CREATE INDEX IF NOT EXISTS idx_sfdc_id
  ON crm.sfdc_dbx.property_sync_audit_log (sfdc_id);

CREATE INDEX IF NOT EXISTS idx_sync_timestamp
  ON crm.sfdc_dbx.property_sync_audit_log (sync_timestamp);
```

**Sample Audit Query:**

```sql
-- Query audit history for a specific property
SELECT
  sync_timestamp,
  sync_operation,
  sync_status,
  property_name,
  active_property_count,
  contributing_rds_property_ids,
  idv_enabled,
  bank_linking_enabled
FROM crm.sfdc_dbx.property_sync_audit_log
WHERE sfdc_id = 'a01Dn00000HHUanIAH'  -- Park Kennedy
ORDER BY sync_timestamp DESC;
```

---

### Step 1.6: Create Monitoring Dashboard View

**File:** `sql/06_create_sync_monitoring_dashboard.sql`

```sql
-- ============================================================================
-- VIEW: sync_monitoring_dashboard
-- PURPOSE: Real-time view of sync pipeline health
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.sync_monitoring_dashboard AS

WITH pipeline_counts AS (
  SELECT
    'Properties to Create' AS stage,
    COUNT(*) AS count,
    SUM(CASE WHEN idv_enabled OR bank_linking_enabled OR payroll_enabled
             OR income_insights_enabled THEN 1 ELSE 0 END) AS with_features,
    1 AS sort_order
  FROM crm.sfdc_dbx.properties_to_create

  UNION ALL

  SELECT
    'Properties to Update' AS stage,
    COUNT(*) AS count,
    SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS with_features,
    2 AS sort_order
  FROM crm.sfdc_dbx.properties_to_update

  UNION ALL

  SELECT
    'Multi-Property Aggregations' AS stage,
    COUNT(*) AS count,
    SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS with_features,
    3 AS sort_order
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
  WHERE is_multi_property = TRUE

  UNION ALL

  SELECT
    'Total in product_property' AS stage,
    COUNT(*) AS count,
    NULL AS with_features,
    4 AS sort_order
  FROM crm.salesforce.product_property
  WHERE is_deleted = FALSE

  UNION ALL

  SELECT
    'Active RDS Properties' AS stage,
    COUNT(*) AS count,
    NULL AS with_features,
    5 AS sort_order
  FROM crm.sfdc_dbx.rds_properties_enriched
  WHERE property_status = 'ACTIVE'
),

recent_sync_stats AS (
  SELECT
    'Last 24h: Successful Syncs' AS stage,
    COUNT(*) AS count,
    NULL AS with_features,
    6 AS sort_order
  FROM crm.sfdc_dbx.property_sync_audit_log
  WHERE sync_timestamp >= CURRENT_TIMESTAMP() - INTERVAL 1 DAY
    AND sync_status = 'SUCCESS'

  UNION ALL

  SELECT
    'Last 24h: Failed Syncs' AS stage,
    COUNT(*) AS count,
    NULL AS with_features,
    7 AS sort_order
  FROM crm.sfdc_dbx.property_sync_audit_log
  WHERE sync_timestamp >= CURRENT_TIMESTAMP() - INTERVAL 1 DAY
    AND sync_status = 'FAILED'
)

SELECT
  stage,
  count,
  with_features,
  CURRENT_TIMESTAMP() AS dashboard_refreshed_at
FROM (
  SELECT * FROM pipeline_counts
  UNION ALL
  SELECT * FROM recent_sync_stats
)
ORDER BY sort_order;

COMMENT ON VIEW crm.sfdc_dbx.sync_monitoring_dashboard IS
'Real-time dashboard of sync pipeline health metrics';
```

**Usage:**

```sql
-- View dashboard
SELECT * FROM crm.sfdc_dbx.sync_monitoring_dashboard;

-- Expected output:
-- Stage                          | Count  | With Features | Refreshed At
-- -------------------------------|--------|---------------|-------------
-- Properties to Create           | 1,081  | 507           | 2026-01-06...
-- Properties to Update           | 7,980  | 6,200         | 2026-01-06...
-- Multi-Property Aggregations    | 2,410  | 1,800         | 2026-01-06...
-- ...
```

---

## ✅ PHASE 1 COMPLETION CHECKLIST

After running all scripts in Phase 1:

- [ ] All 6 views/tables created successfully
- [ ] Validation queries run without errors
- [ ] Row counts match expectations (±5%)
- [ ] Park Kennedy case validates correctly (features from ACTIVE property only)
- [ ] Dashboard view shows current state
- [ ] All views have comments/documentation
- [ ] Views are owned by appropriate service account
- [ ] Databricks workspace organized (all objects in `crm.sfdc_dbx` schema)

**Rollback Procedure (if needed):**

```sql
-- Drop all created objects (Phase 1 only - safe since read-only views)
DROP VIEW IF EXISTS crm.sfdc_dbx.sync_monitoring_dashboard;
DROP TABLE IF EXISTS crm.sfdc_dbx.property_sync_audit_log;
DROP VIEW IF EXISTS crm.sfdc_dbx.properties_to_update;
DROP VIEW IF EXISTS crm.sfdc_dbx.properties_to_create;
DROP VIEW IF EXISTS crm.sfdc_dbx.properties_aggregated_by_sfdc_id;
DROP VIEW IF EXISTS crm.sfdc_dbx.rds_properties_enriched;
```

---

**Next:** [Phase 2: Validation & Testing](#phase-2-validation--testing)
