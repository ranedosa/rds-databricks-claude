# THREE-DAY Implementation Plan: RDS → Salesforce Sync Architecture

**Timeline:** 3 days (6-8 hours per day)
**Risk Level:** MEDIUM (balanced approach)
**Best For:** Most production implementations

---

## 🎯 WHY 3 DAYS?

### **Compared to 1-Day Plan:**
| Factor | 1-Day | 3-Day | Benefit |
|--------|-------|-------|---------|
| Validation | 30 min | 4 hours | Catch 80% of issues before prod |
| Pilot test | Skip | 50+50 properties | Safety net before full rollout |
| Execution pace | Intense (8hr focus) | Sustainable (6-8hr/day) | Less fatigue, fewer mistakes |
| Error tolerance | 5-10% | 2-3% | Higher quality |
| Recovery time | None | Built-in | Can fix issues between days |

### **Compared to 4-Week Plan:**
| Factor | 4-Week | 3-Day | Tradeoff |
|--------|--------|-------|----------|
| Timeline | 20 days | 3 days | 85% faster |
| Documentation | Comprehensive | Minimal | Can document later |
| Team training | Full session | Skip | Train after rollout |
| Monitoring setup | Automated alerts | Manual checks | Add automation later |
| Error tolerance | <1% | 2-3% | Slightly higher risk |

### **Sweet Spot:**
✅ Comprehensive validation (catch issues early)
✅ Pilot test (safety net)
✅ Sustainable pace (not burned out)
✅ Fast enough for business urgency
✅ Good enough for most production use cases

---

## 📅 THREE-DAY OVERVIEW

```
DAY 1: FOUNDATION & VALIDATION (6-8 hours)
├─ Morning: Build all Databricks views
├─ Afternoon: Comprehensive validation
└─ End of Day: Views proven correct, ready for Census

DAY 2: CENSUS & PILOT (6-8 hours)
├─ Morning: Configure both Census syncs
├─ Afternoon: Pilot test on 50+50 properties
└─ End of Day: Pilot successful, ready for full rollout

DAY 3: FULL ROLLOUT & MONITORING (6-8 hours)
├─ Morning: Execute full syncs (1,081 + 7,980)
├─ Afternoon: Validation & issue resolution
└─ End of Day: All properties synced, monitoring enabled
```

---

## 📋 DAY 1: FOUNDATION & VALIDATION

**Duration:** 6-8 hours
**Goal:** Build all views and validate aggregation logic thoroughly
**Risk:** Low (read-only operations)

### Pre-Flight Checklist (Do Before Starting)

- [ ] Databricks workspace access verified
- [ ] Can create views in `crm.sfdc_dbx` schema
- [ ] Source tables accessible (rds.pg_rds_public.properties, property_features)
- [ ] Salesforce table accessible (crm.salesforce.product_property)
- [ ] Calendar clear for 6-8 hours
- [ ] Implementation plans downloaded and open

---

### **MORNING (9:00 AM - 12:00 PM): Build All Views**

#### 9:00-9:30: View 1 - `rds_properties_enriched`

**Purpose:** Join properties with all feature data

```sql
-- ============================================================================
-- VIEW: rds_properties_enriched
-- PURPOSE: Properties + features, one row per RDS property
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

  -- Company Info
  p.company_name,

  -- Feature Flags (default to FALSE if no feature record)
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
  CASE WHEN p.status = 'ACTIVE' THEN 1 ELSE 0 END AS is_active,
  CASE WHEN p.sfdc_id IS NOT NULL AND p.sfdc_id != 'XXXXXXXXXXXXXXX' THEN 1 ELSE 0 END AS has_valid_sfdc_id

FROM rds.pg_rds_public.properties p
LEFT JOIN rds.pg_rds_public.property_features pf
  ON p.id = pf.property_id

WHERE p.company_id IS NOT NULL
  AND p.status != 'DELETED';

-- Validation
SELECT
  COUNT(*) AS total_properties,
  COUNT(DISTINCT rds_property_id) AS unique_properties,
  SUM(is_active) AS active_properties,
  SUM(has_valid_sfdc_id) AS properties_with_sfdc_id,
  SUM(CASE WHEN idv_enabled THEN 1 ELSE 0 END) AS with_idv_enabled
FROM crm.sfdc_dbx.rds_properties_enriched;

-- Expected: ~20,000 total, ~12,000 active
```

**✅ Checkpoint:** View created, validation query returns reasonable numbers

---

#### 9:30-10:30: View 2 - `properties_aggregated_by_sfdc_id` (CORE LOGIC)

**Purpose:** Aggregate multiple RDS properties → single SFDC ID

```sql
-- ============================================================================
-- VIEW: properties_aggregated_by_sfdc_id
-- PURPOSE: Handle many-to-1 relationships with union logic
-- BUSINESS RULES:
--   1. Only ACTIVE properties contribute
--   2. Feature flags: ANY active property has feature → TRUE
--   3. Timestamps: Earliest enabled date
--   4. Property metadata: From most recently updated property
--   5. Full audit trail
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
    -- RULE 1: Property Metadata (from most recently updated ACTIVE property)
    -- ====================================================================

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
    -- RULE 2: Feature Flags - UNION Logic (any ACTIVE property → TRUE)
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

COMMENT ON VIEW crm.sfdc_dbx.properties_aggregated_by_sfdc_id IS
'Aggregates multiple RDS properties by SFDC ID. Union logic for features. One row per SFDC ID.';

-- Validation
SELECT
  active_property_count,
  COUNT(*) AS sfdc_id_count,
  SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS with_features
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
GROUP BY active_property_count
ORDER BY active_property_count;

-- Expected: Most have count=1, ~2,410 have count>1
```

**✅ Checkpoint:** Aggregation view created, distribution looks correct

---

#### 10:30-11:00: View 3 - `properties_to_create`

```sql
-- ============================================================================
-- VIEW: properties_to_create
-- PURPOSE: Properties NOT in product_property yet (need to be created)
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.properties_to_create AS

SELECT
  -- Identifiers
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

WHERE NOT EXISTS (
  SELECT 1
  FROM crm.salesforce.product_property pp
  WHERE CAST(rds.rds_property_id AS STRING) = pp.snappt_property_id_c
    AND pp.is_deleted = FALSE
)

AND rds.property_status = 'ACTIVE'
AND rds.company_id IS NOT NULL;

COMMENT ON VIEW crm.sfdc_dbx.properties_to_create IS
'RDS properties that need to be created in product_property. Source for Census Sync A.';

-- Validation
SELECT
  COUNT(*) AS total_to_create,
  SUM(CASE WHEN idv_enabled OR bank_linking_enabled OR payroll_enabled
           OR income_insights_enabled THEN 1 ELSE 0 END) AS with_features,
  COUNT(DISTINCT company_id) AS distinct_companies
FROM crm.sfdc_dbx.properties_to_create;

-- Expected: ~1,081 total, ~507 with features
```

**✅ Checkpoint:** Create queue view working, counts match expectations

---

#### 11:00-11:30: View 4 - `properties_to_update`

```sql
-- ============================================================================
-- VIEW: properties_to_update
-- PURPOSE: Properties that already exist and need updates (uses aggregated data)
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.properties_to_update AS

SELECT
  -- Link to existing SF record
  pp.snappt_property_id_c,
  pp.id AS product_property_staging_id,
  pp.sf_property_id_c AS production_salesforce_id,

  -- Aggregated data from RDS
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

  -- Aggregated Feature Flags
  agg.idv_enabled,
  agg.bank_linking_enabled,
  agg.payroll_enabled,
  agg.income_insights_enabled,
  agg.document_fraud_enabled,

  -- Feature Timestamps
  agg.idv_enabled_at,
  agg.bank_linking_enabled_at,
  agg.payroll_enabled_at,
  agg.income_insights_enabled_at,
  agg.document_fraud_enabled_at,

  -- Aggregation Metadata
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

INNER JOIN crm.salesforce.product_property pp
  ON agg.sfdc_id = pp.sf_property_id_c

WHERE pp.is_deleted = FALSE;

COMMENT ON VIEW crm.sfdc_dbx.properties_to_update IS
'Properties already in product_property that need updates. Uses aggregated data. Source for Census Sync B.';

-- Validation
SELECT
  COUNT(*) AS total_to_update,
  SUM(CASE WHEN is_multi_property THEN 1 ELSE 0 END) AS multi_property_records,
  SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS with_features
FROM crm.sfdc_dbx.properties_to_update;

-- Expected: ~7,980 total, ~2,410 multi-property
```

**✅ Checkpoint:** Update queue view working, counts reasonable

---

#### 11:30-12:00: Create Audit Table & Monitoring View

```sql
-- ============================================================================
-- TABLE: property_sync_audit_log
-- ============================================================================

CREATE TABLE IF NOT EXISTS crm.sfdc_dbx.property_sync_audit_log (
  audit_id BIGINT GENERATED ALWAYS AS IDENTITY,
  sync_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  sync_operation STRING NOT NULL,
  census_sync_name STRING,
  rds_property_id STRING,
  snappt_property_id_c STRING,
  sfdc_id STRING,
  product_property_staging_id STRING,
  property_name STRING,
  company_id STRING,
  active_property_count INT,
  contributing_rds_property_ids ARRAY<STRING>,
  idv_enabled BOOLEAN,
  bank_linking_enabled BOOLEAN,
  payroll_enabled BOOLEAN,
  income_insights_enabled BOOLEAN,
  document_fraud_enabled BOOLEAN,
  sync_status STRING,
  sync_error_message STRING,
  created_by STRING DEFAULT CURRENT_USER(),
  CONSTRAINT pk_audit_log PRIMARY KEY (audit_id)
)
USING DELTA
PARTITIONED BY (DATE(sync_timestamp));

-- ============================================================================
-- VIEW: sync_health_dashboard
-- ============================================================================

CREATE OR REPLACE VIEW crm.sfdc_dbx.sync_health_dashboard AS

SELECT
  'Properties to Create' AS metric,
  COUNT(*) AS count,
  SUM(CASE WHEN idv_enabled OR bank_linking_enabled OR payroll_enabled
           OR income_insights_enabled THEN 1 ELSE 0 END) AS with_features
FROM crm.sfdc_dbx.properties_to_create

UNION ALL

SELECT
  'Properties to Update' AS metric,
  COUNT(*) AS count,
  SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS with_features
FROM crm.sfdc_dbx.properties_to_update

UNION ALL

SELECT
  'Multi-Property Cases' AS metric,
  COUNT(*) AS count,
  SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS with_features
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
WHERE is_multi_property = TRUE;

-- Quick check
SELECT * FROM crm.sfdc_dbx.sync_health_dashboard;
```

**✅ MORNING CHECKPOINT (12:00 PM):**
- [ ] All 4 views created successfully
- [ ] Audit table created
- [ ] Monitoring view working
- [ ] All row counts match expectations (±10%)
- [ ] No SQL errors

**Take lunch break (30 minutes)**

---

### **AFTERNOON (12:30 PM - 5:00 PM): Comprehensive Validation**

#### 12:30-1:30: Data Quality Validation

```sql
-- ============================================================================
-- VALIDATION SUITE (Run all of these)
-- ============================================================================

-- TEST 1: Aggregation preserves all SFDC IDs
-- ================================================================

WITH source_sfdc_ids AS (
  SELECT COUNT(DISTINCT sfdc_id) AS count
  FROM crm.sfdc_dbx.rds_properties_enriched
  WHERE property_status = 'ACTIVE' AND has_valid_sfdc_id = 1
),
aggregated_sfdc_ids AS (
  SELECT COUNT(DISTINCT sfdc_id) AS count
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
)
SELECT
  s.count AS source_count,
  a.count AS aggregated_count,
  CASE
    WHEN s.count = a.count THEN '✓ PASS: All SFDC IDs preserved'
    ELSE '✗ FAIL: Lost SFDC IDs during aggregation'
  END AS validation_status
FROM source_sfdc_ids s, aggregated_sfdc_ids a;

-- Expected: Counts match exactly

-- TEST 2: Union logic for features works correctly
-- ================================================================

-- Find multi-property cases where at least one has IDV enabled
WITH multi_property_with_idv AS (
  SELECT
    sfdc_id,
    MAX(idv_enabled::INT) AS any_has_idv
  FROM crm.sfdc_dbx.rds_properties_enriched
  WHERE property_status = 'ACTIVE' AND has_valid_sfdc_id = 1
  GROUP BY sfdc_id
  HAVING COUNT(*) > 1 AND MAX(idv_enabled::INT) = 1
),
aggregated_result AS (
  SELECT sfdc_id, idv_enabled
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
)
SELECT
  COUNT(*) AS total_test_cases,
  SUM(CASE WHEN agg.idv_enabled = TRUE THEN 1 ELSE 0 END) AS passed_cases,
  CASE
    WHEN COUNT(*) = SUM(CASE WHEN agg.idv_enabled = TRUE THEN 1 ELSE 0 END)
    THEN '✓ PASS: Union logic working'
    ELSE '✗ FAIL: Some features not aggregated correctly'
  END AS validation_status
FROM multi_property_with_idv mp
JOIN aggregated_result agg ON mp.sfdc_id = agg.sfdc_id;

-- Expected: 100% passed

-- TEST 3: Create + Update = All Active Properties
-- ================================================================

WITH counts AS (
  SELECT
    (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create) AS to_create,
    (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update) AS to_update,
    (SELECT COUNT(DISTINCT sfdc_id)
     FROM crm.sfdc_dbx.rds_properties_enriched
     WHERE property_status = 'ACTIVE' AND has_valid_sfdc_id = 1) AS total_active_sfdc_ids
)
SELECT
  to_create,
  to_update,
  total_active_sfdc_ids,
  CASE
    WHEN to_update BETWEEN total_active_sfdc_ids * 0.7 AND total_active_sfdc_ids * 0.95
    THEN '✓ PASS: Coverage looks good'
    ELSE '⚠ WARNING: Coverage gap detected'
  END AS validation_status
FROM counts;

-- TEST 4: No DISABLED properties in queues
-- ================================================================

SELECT
  COUNT(*) AS disabled_in_create_queue,
  CASE
    WHEN COUNT(*) = 0 THEN '✓ PASS: No disabled properties'
    ELSE '✗ FAIL: DISABLED properties found'
  END AS validation_status
FROM crm.sfdc_dbx.properties_to_create ptc
JOIN crm.sfdc_dbx.rds_properties_enriched rpe
  ON ptc.rds_property_id = rpe.rds_property_id
WHERE rpe.property_status != 'ACTIVE';

-- Expected: 0 disabled

-- TEST 5: Earliest timestamp logic works
-- ================================================================

WITH multi_property_timestamps AS (
  SELECT
    sfdc_id,
    MIN(idv_enabled_at) AS expected_earliest_idv
  FROM crm.sfdc_dbx.rds_properties_enriched
  WHERE property_status = 'ACTIVE'
    AND has_valid_sfdc_id = 1
    AND idv_enabled = TRUE
  GROUP BY sfdc_id
  HAVING COUNT(*) > 1
  LIMIT 100  -- Sample for performance
),
aggregated_timestamps AS (
  SELECT
    sfdc_id,
    idv_enabled_at AS actual_idv
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
  WHERE idv_enabled = TRUE
)
SELECT
  COUNT(*) AS sample_size,
  SUM(CASE WHEN mp.expected_earliest_idv = agg.actual_idv THEN 1 ELSE 0 END) AS matches,
  CASE
    WHEN COUNT(*) = SUM(CASE WHEN mp.expected_earliest_idv = agg.actual_idv THEN 1 ELSE 0 END)
    THEN '✓ PASS: Timestamps correct'
    ELSE '✗ FAIL: Timestamp aggregation incorrect'
  END AS validation_status
FROM multi_property_timestamps mp
JOIN aggregated_timestamps agg ON mp.sfdc_id = agg.sfdc_id;

-- Expected: 100% matches
```

**Document results:** Note any failed tests, investigate before proceeding

---

#### 1:30-2:30: Business Case Validation

```sql
-- ============================================================================
-- BUSINESS CASE VALIDATION
-- ============================================================================

-- CASE 1: Park Kennedy (Known Multi-Property Case)
-- ================================================================

SELECT
  sfdc_id,
  property_name,
  active_property_count,
  contributing_rds_property_ids,
  idv_enabled,
  bank_linking_enabled,
  payroll_enabled,
  income_insights_enabled,
  is_multi_property
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
WHERE sfdc_id = 'a01Dn00000HHUanIAH';

-- EXPECTED RESULTS:
-- active_property_count: 1 or 2 (depending on how many active)
-- idv_enabled: TRUE
-- bank_linking_enabled: TRUE
-- payroll_enabled: TRUE
-- income_insights_enabled: TRUE
-- is_multi_property: TRUE (if count > 1)

-- ⚠️ IF FEATURES ARE FALSE OR NULL: STOP - Debug aggregation logic

-- CASE 2: P1 Critical Properties (507 with features)
-- ================================================================

SELECT
  COUNT(*) AS p1_critical_count,
  SUM(CASE WHEN idv_enabled THEN 1 ELSE 0 END) AS with_idv,
  SUM(CASE WHEN bank_linking_enabled THEN 1 ELSE 0 END) AS with_bank,
  SUM(CASE WHEN payroll_enabled THEN 1 ELSE 0 END) AS with_payroll,
  SUM(CASE WHEN income_insights_enabled THEN 1 ELSE 0 END) AS with_income
FROM crm.sfdc_dbx.properties_to_create
WHERE idv_enabled = TRUE
   OR bank_linking_enabled = TRUE
   OR payroll_enabled = TRUE
   OR income_insights_enabled = TRUE;

-- EXPECTED: ~507 properties
-- If way off (>20% difference): Investigate but don't block

-- Sample 10 for manual review
SELECT
  rds_property_id,
  property_name,
  company_id,
  city,
  state,
  idv_enabled,
  bank_linking_enabled,
  payroll_enabled
FROM crm.sfdc_dbx.properties_to_create
WHERE idv_enabled = TRUE OR bank_linking_enabled = TRUE
ORDER BY created_at DESC
LIMIT 10;

-- CASE 3: Blocked Properties (2,410 Multi-Property Cases)
-- ================================================================

SELECT
  active_property_count,
  COUNT(*) AS num_sfdc_ids,
  SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS with_features
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
WHERE is_multi_property = TRUE
GROUP BY active_property_count
ORDER BY active_property_count;

-- EXPECTED: ~2,410 SFDC IDs with multiple properties

-- Sample multi-property cases
SELECT
  sfdc_id,
  property_name,
  active_property_count,
  contributing_rds_property_ids,
  idv_enabled,
  bank_linking_enabled,
  is_multi_property
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
WHERE is_multi_property = TRUE
ORDER BY active_property_count DESC
LIMIT 20;

-- Manually review: Do these look reasonable?

-- CASE 4: Feature Mismatch Properties (799 properties)
-- ================================================================

WITH sf_current_state AS (
  SELECT
    pp.snappt_property_id_c,
    pp.idv_enabled_c AS sf_idv_enabled
  FROM crm.salesforce.product_property pp
  WHERE pp.is_deleted = FALSE
)
SELECT
  COUNT(*) AS properties_with_idv_mismatch
FROM crm.sfdc_dbx.properties_to_update ptu
WHERE ptu.idv_enabled = TRUE
  AND EXISTS (
    SELECT 1 FROM sf_current_state sf
    WHERE ptu.snappt_property_id_c = sf.snappt_property_id_c
      AND sf.sf_idv_enabled = FALSE
  );

-- EXPECTED: ~799 properties with mismatches
```

**Document results:** All critical cases should validate correctly

---

#### 2:30-3:30: Edge Case Testing

```sql
-- ============================================================================
-- EDGE CASE TESTING
-- ============================================================================

-- EDGE CASE 1: Properties with NULL sfdc_id
-- ================================================================

SELECT
  COUNT(*) AS null_sfdc_id_active_properties
FROM crm.sfdc_dbx.rds_properties_enriched
WHERE property_status = 'ACTIVE'
  AND (sfdc_id IS NULL OR sfdc_id = 'XXXXXXXXXXXXXXX');

-- These should NOT appear in aggregated view (requires valid sfdc_id)
-- Verify:
SELECT COUNT(*) AS should_be_zero
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
WHERE sfdc_id IS NULL OR sfdc_id = 'XXXXXXXXXXXXXXX';

-- EDGE CASE 2: SFDC ID shared by 3+ properties
-- ================================================================

SELECT
  sfdc_id,
  active_property_count,
  contributing_rds_property_ids,
  property_name,
  idv_enabled,
  bank_linking_enabled
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
WHERE active_property_count >= 3
ORDER BY active_property_count DESC
LIMIT 10;

-- Manually review: Does aggregation make sense for these?

-- EDGE CASE 3: Properties in both create AND update queues (should be 0)
-- ================================================================

SELECT COUNT(*) AS overlap_count
FROM crm.sfdc_dbx.properties_to_create ptc
WHERE EXISTS (
  SELECT 1
  FROM crm.sfdc_dbx.properties_to_update ptu
  WHERE CAST(ptc.rds_property_id AS STRING) = ptu.snappt_property_id_c
);

-- EXPECTED: 0 (mutually exclusive queues)
-- If >0: This is a critical error, investigate immediately

-- EDGE CASE 4: Very recently updated properties
-- ================================================================

SELECT COUNT(*) AS recently_updated_in_last_24h
FROM crm.sfdc_dbx.properties_to_update
WHERE rds_last_updated_at >= CURRENT_TIMESTAMP() - INTERVAL 1 DAY;

-- These should be prioritized in sync
```

**Document any unexpected results**

---

#### 3:30-4:30: Create Test Data Exports

```sql
-- ============================================================================
-- EXPORT TEST DATA FOR DAY 2 PILOT
-- ============================================================================

-- Export 1: Pilot properties to CREATE (50 properties)
-- ================================================================

CREATE OR REPLACE TEMP VIEW day2_pilot_create AS

-- 15 properties WITH features (high priority)
SELECT *, 'Has Features' AS pilot_category, 1 AS priority
FROM crm.sfdc_dbx.properties_to_create
WHERE idv_enabled = TRUE OR bank_linking_enabled = TRUE
  OR payroll_enabled = TRUE OR income_insights_enabled = TRUE
ORDER BY RANDOM()
LIMIT 15

UNION ALL

-- 10 properties WITHOUT features
SELECT *, 'No Features' AS pilot_category, 2 AS priority
FROM crm.sfdc_dbx.properties_to_create
WHERE idv_enabled = FALSE AND bank_linking_enabled = FALSE
  AND payroll_enabled = FALSE AND income_insights_enabled = FALSE
ORDER BY RANDOM()
LIMIT 10

UNION ALL

-- 10 recently created (< 30 days)
SELECT *, 'Recently Created' AS pilot_category, 3 AS priority
FROM crm.sfdc_dbx.properties_to_create
WHERE created_at >= CURRENT_TIMESTAMP() - INTERVAL 30 DAYS
ORDER BY RANDOM()
LIMIT 10

UNION ALL

-- 15 diverse companies
SELECT *, 'Diverse Companies' AS pilot_category, 4 AS priority
FROM crm.sfdc_dbx.properties_to_create
WHERE company_id IN (
  SELECT company_id
  FROM crm.sfdc_dbx.properties_to_create
  GROUP BY company_id
  ORDER BY RANDOM()
  LIMIT 15
)
LIMIT 15;

-- Save IDs for filtering Census sync tomorrow
SELECT
  rds_property_id,
  property_name,
  pilot_category,
  idv_enabled,
  bank_linking_enabled
FROM day2_pilot_create
ORDER BY priority, property_name;

-- Export to CSV or copy IDs

-- Export 2: Pilot properties to UPDATE (50 properties)
-- ================================================================

CREATE OR REPLACE TEMP VIEW day2_pilot_update AS

-- 10 single-property cases
SELECT *, 'Single Property' AS pilot_category, 1 AS priority
FROM crm.sfdc_dbx.properties_to_update
WHERE is_multi_property = FALSE AND idv_enabled = TRUE
ORDER BY RANDOM()
LIMIT 10

UNION ALL

-- 15 multi-property cases (count=2)
SELECT *, 'Multi-Property (2)' AS pilot_category, 2 AS priority
FROM crm.sfdc_dbx.properties_to_update
WHERE active_property_count = 2
ORDER BY RANDOM()
LIMIT 15

UNION ALL

-- 5 multi-property cases (count=3+)
SELECT *, 'Multi-Property (3+)' AS pilot_category, 3 AS priority
FROM crm.sfdc_dbx.properties_to_update
WHERE active_property_count >= 3
ORDER BY RANDOM()
LIMIT 5

UNION ALL

-- Include Park Kennedy if available
SELECT *, 'Park Kennedy' AS pilot_category, 0 AS priority
FROM crm.sfdc_dbx.properties_to_update
WHERE sfdc_id = 'a01Dn00000HHUanIAH'

UNION ALL

-- 20 feature mismatch cases
SELECT *, 'Feature Mismatch' AS pilot_category, 4 AS priority
FROM crm.sfdc_dbx.properties_to_update
WHERE has_any_features_enabled = TRUE
  AND has_changes_since_last_sync = TRUE
ORDER BY RANDOM()
LIMIT 20;

-- Save IDs
SELECT
  snappt_property_id_c,
  sfdc_id,
  property_name,
  pilot_category,
  active_property_count,
  is_multi_property,
  idv_enabled,
  bank_linking_enabled
FROM day2_pilot_update
ORDER BY priority, property_name;

-- Export to CSV or copy IDs
```

**Save these IDs - you'll need them tomorrow for Census filters**

---

#### 4:30-5:00: Create Day 1 Report

```sql
-- ============================================================================
-- DAY 1 COMPLETION REPORT
-- ============================================================================

SELECT
  '========================================' AS separator,
  'DAY 1 COMPLETION REPORT' AS title,
  CURRENT_TIMESTAMP() AS report_time,
  '========================================' AS separator2;

-- Views Created
SELECT 'Views Created:' AS section;
SELECT
  table_name,
  table_type,
  CASE WHEN table_name IS NOT NULL THEN '✓' ELSE '✗' END AS status
FROM information_schema.tables
WHERE table_schema = 'sfdc_dbx'
  AND table_name IN (
    'rds_properties_enriched',
    'properties_aggregated_by_sfdc_id',
    'properties_to_create',
    'properties_to_update',
    'property_sync_audit_log',
    'sync_health_dashboard'
  );

-- Row Counts
SELECT 'Row Counts:' AS section;
SELECT * FROM crm.sfdc_dbx.sync_health_dashboard;

-- Validation Summary
SELECT 'Validation Summary:' AS section;
SELECT
  'Data Quality Tests' AS test_suite,
  '5/5 passed' AS result,  -- Update with actual results
  '✓' AS status;

-- Update this with your actual test results

-- Pilot Data Ready
SELECT 'Pilot Data:' AS section;
SELECT
  'Create Pilot' AS pilot_type,
  50 AS target_count,
  (SELECT COUNT(*) FROM day2_pilot_create) AS actual_count,
  '✓' AS status;

SELECT
  'Update Pilot' AS pilot_type,
  50 AS target_count,
  (SELECT COUNT(*) FROM day2_pilot_update) AS actual_count,
  '✓' AS status;
```

---

### **✅ END OF DAY 1 CHECKLIST**

- [ ] All 4 views created and validated
- [ ] Audit table created
- [ ] Monitoring view working
- [ ] All data quality tests passed (or issues documented)
- [ ] Park Kennedy case validates correctly
- [ ] P1 critical properties identified (~507)
- [ ] Multi-property cases validated (~2,410)
- [ ] Edge cases tested
- [ ] Pilot data exported (50+50 properties)
- [ ] Day 1 report created
- [ ] No critical blockers for Day 2

**If any critical tests failed:** Investigate and fix before Day 2

**Save your work:**
```bash
# Export pilot IDs to file
# Copy day2_pilot_create and day2_pilot_update query results to a text file
# You'll need these IDs tomorrow for Census filters
```

**Tomorrow:** Census configuration and pilot test

---

## 📋 DAY 2: CENSUS & PILOT

**Duration:** 6-8 hours
**Goal:** Configure Census syncs and pilot test on 50+50 properties
**Risk:** Medium (writing to Salesforce, but small batch)

### Pre-Flight Checklist

- [ ] Day 1 completed successfully
- [ ] Pilot property IDs ready (from yesterday's exports)
- [ ] Census workspace access (ID: 33026)
- [ ] Salesforce access verified
- [ ] Calendar clear for 6-8 hours

---

### **MORNING (9:00 AM - 12:00 PM): Configure Census Syncs**

#### 9:00-10:30: Configure Census Sync A (Create New Properties)

**Navigate to Census workspace → Create New Sync**

```yaml
Sync Name: "RDS → SF product_property (CREATE)"

Source:
  Connection: Databricks (Snappt Production)
  Database: crm
  Schema: sfdc_dbx
  Table/View: properties_to_create

Destination:
  Connection: Salesforce (Snappt Production)
  Object: product_property__c

Sync Behavior:
  Mode: Create Only  ← CRITICAL

  "When record in source but not destination:" → Create
  "When record in both:" → Skip

Sync Key (Unique Identifier):
  Source: rds_property_id
  Destination: snappt_property_id__c

Field Mappings:
  # Identifiers
  rds_property_id        → snappt_property_id__c  ✓ SYNC KEY
  short_id               → Short_ID__c
  company_id             → Company_ID__c

  # Property Information
  property_name          → Name
  address                → Property_Address_Street__c
  city                   → Property_Address_City__c
  state                  → Property_Address_State__c
  postal_code            → Property_Address_Postal_Code__c
  country                → Property_Address_Country__c
  company_name           → Company_Name__c

  # Feature Flags
  idv_enabled            → IDV_Enabled__c
  bank_linking_enabled   → Bank_Linking_Enabled__c
  payroll_enabled        → Payroll_Enabled__c
  income_insights_enabled → Income_Insights_Enabled__c
  document_fraud_enabled → Document_Fraud_Enabled__c

  # Feature Timestamps
  idv_enabled_at         → IDV_Enabled_At__c
  bank_linking_enabled_at → Bank_Linking_Enabled_At__c
  payroll_enabled_at     → Payroll_Enabled_At__c
  income_insights_enabled_at → Income_Insights_Enabled_At__c
  document_fraud_enabled_at → Document_Fraud_Enabled_At__c

  # Metadata
  created_at             → RDS_Created_At__c
  updated_at             → RDS_Updated_At__c
  sync_queued_at         → Sync_Queued_At__c

Filters (FOR PILOT):
  Add filter: WHERE rds_property_id IN (<paste your 50 pilot IDs>)

  # Example:
  # WHERE rds_property_id IN (
  #   'id1', 'id2', 'id3', ...'id50'
  # )

Schedule: Manual (we'll trigger manually)

Error Handling:
  On Error: Log and continue
  Retry: 3 attempts with exponential backoff
```

**⚠️ Common Mistakes:**
- Wrong sync mode (Update or Create vs Create Only)
- Wrong sync key (must be rds_property_id → snappt_property_id__c)
- Field name typos (Salesforce field names are case-sensitive)
- Forgot to add pilot filter

**✅ Checkpoint:** Sync A configured, save configuration

---

#### 10:30-12:00: Configure Census Sync B (Update Existing Properties)

```yaml
Sync Name: "RDS → SF product_property (UPDATE)"

Source:
  Connection: Databricks (Snappt Production)
  Database: crm
  Schema: sfdc_dbx
  Table/View: properties_to_update

Destination:
  Connection: Salesforce (Snappt Production)
  Object: product_property__c

Sync Behavior:
  Mode: Update Only  ← CRITICAL (different from Sync A)

  "When record in source but not destination:" → Skip
  "When record in both:" → Update

Sync Key:
  Source: snappt_property_id_c
  Destination: snappt_property_id__c

  ⚠️ DIFFERENT from Sync A - this matches existing records

Field Mappings:
  # Same as Sync A, PLUS these aggregation fields:

  # Property Information (same as Sync A)
  property_name          → Name
  short_id               → Short_ID__c
  address                → Property_Address_Street__c
  city                   → Property_Address_City__c
  state                  → Property_Address_State__c
  postal_code            → Property_Address_Postal_Code__c
  country                → Property_Address_Country__c
  company_id             → Company_ID__c
  company_name           → Company_Name__c

  # Feature Flags (AGGREGATED)
  idv_enabled            → IDV_Enabled__c
  bank_linking_enabled   → Bank_Linking_Enabled__c
  payroll_enabled        → Payroll_Enabled__c
  income_insights_enabled → Income_Insights_Enabled__c
  document_fraud_enabled → Document_Fraud_Enabled__c

  # Feature Timestamps
  idv_enabled_at         → IDV_Enabled_At__c
  bank_linking_enabled_at → Bank_Linking_Enabled_At__c
  payroll_enabled_at     → Payroll_Enabled_At__c
  income_insights_enabled_at → Income_Insights_Enabled_At__c
  document_fraud_enabled_at → Document_Fraud_Enabled_At__c

  # Aggregation Metadata (NEW - for audit trail)
  active_property_count  → Active_Property_Count__c
  total_feature_count    → Total_Feature_Count__c
  is_multi_property      → Is_Multi_Property__c
  has_any_features_enabled → Has_Any_Features_Enabled__c
  rds_last_updated_at    → RDS_Last_Updated_At__c

Filters (FOR PILOT):
  Add filter: WHERE snappt_property_id_c IN (<paste your 50 pilot IDs>)

Schedule: Manual

Advanced Settings:
  Update Mode: Replace (not Merge)  ← CRITICAL
  # This ensures FALSE overwrites TRUE (not just NULL)

Error Handling:
  On Error: Log and continue
  Retry: 3 attempts
```

**✅ Checkpoint:** Sync B configured, both syncs ready for testing

**Take lunch break (30 minutes)**

---

### **AFTERNOON (12:30 PM - 5:00 PM): Pilot Test**

#### 12:30-1:00: Pre-Pilot Validation

```sql
-- Verify pilot filters are working

-- Test Sync A filter
SELECT COUNT(*) as pilot_create_count
FROM crm.sfdc_dbx.properties_to_create
WHERE rds_property_id IN (<your 50 pilot IDs>);
-- Expected: 50

-- Test Sync B filter
SELECT COUNT(*) as pilot_update_count
FROM crm.sfdc_dbx.properties_to_update
WHERE snappt_property_id_c IN (<your 50 pilot IDs>);
-- Expected: 50

-- Baseline: Current SF count
SELECT COUNT(*) as current_sf_count
FROM crm.salesforce.product_property
WHERE is_deleted = FALSE;
-- Record this number
```

---

#### 1:00-2:00: Execute Pilot Sync A (Create 50 Properties)

**Step 1: Trigger Sync**
- Go to Census → Sync A
- Verify filter is applied (50 properties)
- Click "Trigger Sync Now"
- **Record start time:** _______________

**Step 2: Monitor (10-15 minutes)**
- Watch Census logs
- Check "Records Processed" counter
- Error rate should be 0% or very low

**Step 3: Validate Results**

```sql
-- Check if 50 properties were created
SELECT COUNT(*) as created_in_pilot
FROM crm.salesforce.product_property
WHERE created_date >= '<sync_start_time>'
  AND snappt_property_id_c IN (<your 50 pilot IDs>)
  AND is_deleted = FALSE;
-- Expected: 50 (or close, allowing for minor errors)

-- Spot-check 10 properties
SELECT
  snappt_property_id_c,
  name,
  city,
  state,
  idv_enabled_c,
  bank_linking_enabled_c,
  created_date
FROM crm.salesforce.product_property
WHERE snappt_property_id_c IN (<your 50 pilot IDs>)
  AND is_deleted = FALSE
LIMIT 10;

-- Manually verify:
-- - Names look correct
-- - Feature flags match what you expect
-- - No obvious data corruption
```

**Step 4: Detailed Validation**

```sql
-- Compare RDS source vs SF created records
WITH rds_source AS (
  SELECT
    rds_property_id,
    property_name,
    idv_enabled,
    bank_linking_enabled,
    city,
    state
  FROM crm.sfdc_dbx.properties_to_create
  WHERE rds_property_id IN (<your 50 pilot IDs>)
),
sf_created AS (
  SELECT
    snappt_property_id_c AS rds_property_id,
    name AS property_name,
    idv_enabled_c AS idv_enabled,
    bank_linking_enabled_c AS bank_linking_enabled,
    property_address_city__c AS city,
    property_address_state__c AS state
  FROM crm.salesforce.product_property
  WHERE snappt_property_id_c IN (<your 50 pilot IDs>)
    AND is_deleted = FALSE
)
SELECT
  rds.rds_property_id,
  rds.property_name AS rds_name,
  sf.property_name AS sf_name,
  CASE WHEN rds.property_name = sf.property_name THEN '✓' ELSE '✗' END AS name_match,
  CASE WHEN rds.idv_enabled = sf.idv_enabled THEN '✓' ELSE '✗' END AS idv_match,
  CASE WHEN rds.bank_linking_enabled = sf.bank_linking_enabled THEN '✓' ELSE '✗' END AS bank_match,
  CASE WHEN rds.city = sf.city THEN '✓' ELSE '✗' END AS city_match
FROM rds_source rds
LEFT JOIN sf_created sf ON rds.rds_property_id = sf.rds_property_id;

-- Review results: All should match (✓)
-- If many ✗: Investigate field mappings
```

**✅ Pilot Sync A Checkpoint:**
- [ ] 50 properties created (or very close)
- [ ] Spot-check validation passes
- [ ] Detailed comparison: >95% fields match
- [ ] No critical errors in Census logs

**If checkpoint fails:** Fix issues before proceeding to Sync B

---

#### 2:00-3:00: Execute Pilot Sync B (Update 50 Properties)

**Step 1: Capture Baseline**

```sql
-- Save current state BEFORE sync
CREATE OR REPLACE TEMP VIEW pilot_baseline_before_update AS
SELECT
  snappt_property_id_c,
  sf_property_id_c,
  name,
  idv_enabled_c,
  bank_linking_enabled_c,
  payroll_enabled_c,
  active_property_count_c,
  is_multi_property_c,
  last_modified_date
FROM crm.salesforce.product_property
WHERE snappt_property_id_c IN (<your 50 pilot IDs>)
  AND is_deleted = FALSE;

-- Save this output (copy to spreadsheet or file)
SELECT * FROM pilot_baseline_before_update;
```

**Step 2: Trigger Sync**
- Go to Census → Sync B
- Verify filter applied (50 properties)
- Click "Trigger Sync Now"
- **Record start time:** _______________

**Step 3: Monitor (10-15 minutes)**
- Watch Census logs
- Check "Records Updated" counter
- Error rate should be 0% or very low

**Step 4: Validate Results**

```sql
-- Check how many were updated
SELECT COUNT(*) as updated_in_pilot
FROM crm.salesforce.product_property
WHERE last_modified_date >= '<sync_start_time>'
  AND snappt_property_id_c IN (<your 50 pilot IDs>)
  AND is_deleted = FALSE;
-- Expected: 50 (or close)

-- Verify Park Kennedy (if in pilot)
SELECT
  snappt_property_id_c,
  sf_property_id_c,
  name,
  active_property_count_c,
  is_multi_property_c,
  idv_enabled_c,
  bank_linking_enabled_c,
  payroll_enabled_c,
  last_modified_date
FROM crm.salesforce.product_property
WHERE sf_property_id_c = 'a01Dn00000HHUanIAH';

-- Expected:
-- active_property_count_c: 2 (or correct count from aggregation)
-- is_multi_property_c: TRUE
-- idv_enabled_c: TRUE
-- bank_linking_enabled_c: TRUE
-- last_modified_date: Recent (today)
```

**Step 5: Detailed Validation**

```sql
-- Compare RDS aggregated data vs SF updated records
WITH rds_expected AS (
  SELECT
    primary_rds_property_id,
    sfdc_id,
    property_name,
    active_property_count,
    is_multi_property,
    idv_enabled,
    bank_linking_enabled,
    payroll_enabled
  FROM crm.sfdc_dbx.properties_to_update
  WHERE snappt_property_id_c IN (<your 50 pilot IDs>)
),
sf_actual AS (
  SELECT
    snappt_property_id_c,
    sf_property_id_c AS sfdc_id,
    name AS property_name,
    active_property_count_c AS active_property_count,
    is_multi_property_c AS is_multi_property,
    idv_enabled_c AS idv_enabled,
    bank_linking_enabled_c AS bank_linking_enabled,
    payroll_enabled_c AS payroll_enabled
  FROM crm.salesforce.product_property
  WHERE snappt_property_id_c IN (<your 50 pilot IDs>)
    AND is_deleted = FALSE
)
SELECT
  rds.sfdc_id,
  rds.property_name,
  rds.active_property_count,
  sf.active_property_count AS sf_count,
  CASE WHEN rds.active_property_count = sf.active_property_count THEN '✓' ELSE '✗' END AS count_match,
  rds.is_multi_property,
  sf.is_multi_property AS sf_multi,
  CASE WHEN rds.is_multi_property = sf.is_multi_property THEN '✓' ELSE '✗' END AS multi_match,
  rds.idv_enabled AS rds_idv,
  sf.idv_enabled AS sf_idv,
  CASE WHEN rds.idv_enabled = sf.idv_enabled THEN '✓' ELSE '✗' END AS idv_match,
  rds.bank_linking_enabled AS rds_bank,
  sf.bank_linking_enabled AS sf_bank,
  CASE WHEN rds.bank_linking_enabled = sf.bank_linking_enabled THEN '✓' ELSE '✗' END AS bank_match
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id;

-- Review: All should be ✓
-- Calculate match percentage
SELECT
  COUNT(*) AS total_properties,
  SUM(CASE WHEN idv_match = '✓' THEN 1 ELSE 0 END) AS idv_matches,
  SUM(CASE WHEN bank_match = '✓' THEN 1 ELSE 0 END) AS bank_matches,
  ROUND(100.0 * SUM(CASE WHEN idv_match = '✓' THEN 1 ELSE 0 END) / COUNT(*), 2) AS idv_accuracy,
  ROUND(100.0 * SUM(CASE WHEN bank_match = '✓' THEN 1 ELSE 0 END) / COUNT(*), 2) AS bank_accuracy
FROM (previous query);

-- Target: >97% accuracy
```

**✅ Pilot Sync B Checkpoint:**
- [ ] 50 properties updated
- [ ] Park Kennedy correct (if in pilot)
- [ ] Feature accuracy >97%
- [ ] Multi-property flag correct
- [ ] Active property count correct
- [ ] No critical errors

---

#### 3:00-4:00: Pilot Analysis & Decision

```sql
-- ============================================================================
-- PILOT SUCCESS ANALYSIS
-- ============================================================================

-- Summary statistics
SELECT
  'Pilot Sync A (Create)' AS sync_type,
  50 AS target_count,
  (SELECT COUNT(*)
   FROM crm.salesforce.product_property
   WHERE snappt_property_id_c IN (<pilot create IDs>)
     AND is_deleted = FALSE) AS actual_count,
  CASE
    WHEN (SELECT COUNT(*) FROM crm.salesforce.product_property
          WHERE snappt_property_id_c IN (<pilot create IDs>)) >= 48
    THEN '✓ SUCCESS'
    ELSE '✗ NEEDS FIX'
  END AS status

UNION ALL

SELECT
  'Pilot Sync B (Update)' AS sync_type,
  50 AS target_count,
  (SELECT COUNT(*)
   FROM crm.salesforce.product_property
   WHERE snappt_property_id_c IN (<pilot update IDs>)
     AND last_modified_date >= '<sync_b_start_time>') AS actual_count,
  CASE
    WHEN (SELECT COUNT(*) FROM crm.salesforce.product_property
          WHERE snappt_property_id_c IN (<pilot update IDs>)
            AND last_modified_date >= '<sync_b_start_time>') >= 48
    THEN '✓ SUCCESS'
    ELSE '✗ NEEDS FIX'
  END AS status;

-- Census error logs
-- Check Census UI for any errors
-- Document error rate: _____% (target: <3%)

-- Overall pilot success
-- ✓ Sync A: Created 48+ of 50 properties
-- ✓ Sync B: Updated 48+ of 50 properties
-- ✓ Feature accuracy: >97%
-- ✓ Error rate: <3%
-- ✓ Park Kennedy: Correct
-- ✓ Multi-property cases: Working

-- GO/NO-GO DECISION:
-- ✅ GO if all above checkpoints passed
-- ❌ NO-GO if any critical failures
```

**Document any issues found:**
- Error patterns
- Field mapping problems
- Data quality issues
- Edge cases discovered

**If GO:** Proceed to prep for Day 3
**If NO-GO:** Fix issues, re-run pilot on different batch

---

#### 4:00-5:00: Prepare for Full Rollout (Day 3)

**Task 1: Remove Pilot Filters (prepare for tomorrow)**

Don't actually do this yet, but prepare:
- Note exact steps to remove filters from both syncs
- Save current filter definitions (in case you need to rollback)

**Task 2: Create Day 3 Monitoring Queries**

```sql
-- Save these queries for tomorrow's monitoring

-- Query 1: Track create progress
CREATE OR REPLACE VIEW day3_create_progress AS
SELECT
  COUNT(*) AS remaining_to_create,
  SUM(CASE WHEN idv_enabled OR bank_linking_enabled OR payroll_enabled
           OR income_insights_enabled THEN 1 ELSE 0 END) AS with_features_remaining
FROM crm.sfdc_dbx.properties_to_create;

-- Query 2: Track update progress
CREATE OR REPLACE VIEW day3_update_progress AS
SELECT
  COUNT(*) AS total_to_update,
  SUM(CASE WHEN is_multi_property THEN 1 ELSE 0 END) AS multi_property_remaining,
  SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS with_features_remaining
FROM crm.sfdc_dbx.properties_to_update;

-- Query 3: Quick health check
CREATE OR REPLACE VIEW day3_health_check AS
SELECT
  CURRENT_TIMESTAMP() AS check_time,
  (SELECT remaining_to_create FROM day3_create_progress) AS to_create,
  (SELECT total_to_update FROM day3_update_progress) AS to_update,
  (SELECT COUNT(*) FROM crm.salesforce.product_property WHERE is_deleted = FALSE) AS total_in_sf;
```

**Task 3: Stakeholder Communication**

```bash
# Send email/Slack

Subject: Property Sync Pilot Successful - Ready for Full Rollout Tomorrow

Team,

Completed Day 2 pilot test of new sync architecture.

Pilot Results:
✓ 50 properties created (Sync A)
✓ 50 properties updated (Sync B)
✓ Feature accuracy: [X]%
✓ Error rate: [X]%
✓ Multi-property aggregation working correctly

Tomorrow (Day 3):
- Full rollout: 1,081 creates + 7,980 updates
- Expected duration: 3-4 hours for syncs
- Will monitor closely throughout day
- Expect all missing properties to appear in SF

Questions? [Your contact info]

[Your name]
```

**Task 4: Day 2 Report**

```sql
-- Create completion report
SELECT '===== DAY 2 COMPLETION REPORT =====' AS report;

SELECT
  'Pilot Sync A' AS metric,
  50 AS target,
  [ACTUAL] AS actual,
  '[✓/✗]' AS status;

SELECT
  'Pilot Sync B' AS metric,
  50 AS target,
  [ACTUAL] AS actual,
  '[✓/✗]' AS status;

SELECT
  'Feature Accuracy' AS metric,
  '>97%' AS target,
  '[ACTUAL]%' AS actual,
  '[✓/✗]' AS status;

-- Document any issues
-- - [List any problems encountered]
-- - [Resolutions applied]

-- Ready for Day 3: [YES/NO]
```

---

### **✅ END OF DAY 2 CHECKLIST**

- [ ] Census Sync A configured and tested
- [ ] Census Sync B configured and tested
- [ ] Pilot Sync A: 48+ of 50 properties created
- [ ] Pilot Sync B: 48+ of 50 properties updated
- [ ] Feature accuracy >97%
- [ ] Park Kennedy case correct
- [ ] Multi-property cases working
- [ ] Error rate <3%
- [ ] No critical blockers discovered
- [ ] Day 3 monitoring queries prepared
- [ ] Stakeholders notified
- [ ] Day 2 report completed

**If pilot failed:** Fix issues before Day 3, may need to re-pilot

**Tomorrow:** Full rollout (1,081 + 7,980 properties)

---

## 📋 DAY 3: FULL ROLLOUT & MONITORING

**Duration:** 6-8 hours
**Goal:** Execute full syncs and validate all properties
**Risk:** Medium-High (large-scale production writes)

[Continue in next message due to length...]

Would you like me to complete Day 3 of the 3-day plan?
