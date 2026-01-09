# Implementation Plan: Phases 2-6

**Continuation of:** IMPLEMENTATION_PLAN_NEW_SYNC_ARCHITECTURE.md

---

## 📊 PHASE 2: VALIDATION & TESTING

**Duration:** 2 days
**Risk Level:** Low
**Prerequisites:** Phase 1 completed, all views created

---

### Step 2.1: Data Quality Validation

**File:** `sql/validation/01_data_quality_checks.sql`

```sql
-- ============================================================================
-- DATA QUALITY VALIDATION SUITE
-- Run these queries to validate the aggregation logic
-- ============================================================================

-- TEST 1: Row counts consistency
-- ================================================================
SELECT 'TEST 1: Row Count Consistency' AS test_name;

WITH counts AS (
  SELECT
    COUNT(DISTINCT rds_property_id) AS total_rds_properties,
    COUNT(DISTINCT CASE WHEN property_status = 'ACTIVE' THEN rds_property_id END) AS active_rds_properties,
    COUNT(DISTINCT CASE WHEN has_valid_sfdc_id = 1 AND property_status = 'ACTIVE' THEN sfdc_id END) AS unique_sfdc_ids
  FROM crm.sfdc_dbx.rds_properties_enriched
)
SELECT
  *,
  CASE
    WHEN unique_sfdc_ids BETWEEN active_rds_properties * 0.8 AND active_rds_properties * 1.0
    THEN '✓ PASS'
    ELSE '✗ FAIL: Unexpected SFDC ID count'
  END AS validation_status
FROM counts;

-- Expected: unique_sfdc_ids should be slightly less than active_rds_properties
-- (because some properties share SFDC IDs)

-- ================================================================
-- TEST 2: Aggregation preserves all SFDC IDs
-- ================================================================
SELECT 'TEST 2: Aggregation Preserves SFDC IDs' AS test_name;

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
    WHEN s.count = a.count THEN '✓ PASS'
    ELSE '✗ FAIL: Lost SFDC IDs during aggregation'
  END AS validation_status
FROM source_sfdc_ids s, aggregated_sfdc_ids a;

-- Expected: Counts should match exactly

-- ================================================================
-- TEST 3: Union logic for features works correctly
-- ================================================================
SELECT 'TEST 3: Feature Union Logic' AS test_name;

-- Case: Multiple properties with same SFDC ID, at least one has IDV enabled
WITH test_case AS (
  SELECT
    sfdc_id,
    COUNT(*) AS property_count,
    MAX(idv_enabled::INT) AS any_idv_enabled  -- 1 if any property has it
  FROM crm.sfdc_dbx.rds_properties_enriched
  WHERE property_status = 'ACTIVE' AND has_valid_sfdc_id = 1
  GROUP BY sfdc_id
  HAVING COUNT(*) > 1  -- Only multi-property SFDC IDs
    AND MAX(idv_enabled::INT) = 1  -- At least one has IDV
),
aggregated_result AS (
  SELECT
    sfdc_id,
    idv_enabled
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
)
SELECT
  COUNT(*) AS total_test_cases,
  SUM(CASE WHEN agg.idv_enabled = TRUE THEN 1 ELSE 0 END) AS passed_cases,
  CASE
    WHEN COUNT(*) = SUM(CASE WHEN agg.idv_enabled = TRUE THEN 1 ELSE 0 END)
    THEN '✓ PASS: All multi-property cases correctly aggregated features'
    ELSE '✗ FAIL: Some features not aggregated correctly'
  END AS validation_status
FROM test_case tc
JOIN aggregated_result agg ON tc.sfdc_id = agg.sfdc_id;

-- Expected: All test cases should pass (100% passed_cases)

-- ================================================================
-- TEST 4: Properties to create + properties to update = all active properties
-- ================================================================
SELECT 'TEST 4: Create + Update Coverage' AS test_name;

WITH counts AS (
  SELECT
    (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create) AS to_create,
    (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update) AS to_update,
    (SELECT COUNT(*)
     FROM crm.sfdc_dbx.rds_properties_enriched
     WHERE property_status = 'ACTIVE' AND has_valid_sfdc_id = 1) AS total_active_with_sfdc_id
)
SELECT
  *,
  CASE
    -- to_create + to_update should approximately equal total_active_with_sfdc_id
    -- (Some properties might not match if they're in a weird state)
    WHEN to_update BETWEEN total_active_with_sfdc_id * 0.7 AND total_active_with_sfdc_id * 0.95
    THEN '✓ PASS'
    ELSE '⚠ WARNING: Coverage gap detected'
  END AS validation_status
FROM counts;

-- ================================================================
-- TEST 5: No DISABLED properties in sync queues
-- ================================================================
SELECT 'TEST 5: No DISABLED Properties' AS test_name;

WITH disabled_check AS (
  SELECT COUNT(*) AS disabled_in_create
  FROM crm.sfdc_dbx.properties_to_create ptc
  JOIN crm.sfdc_dbx.rds_properties_enriched rpe
    ON ptc.rds_property_id = rpe.rds_property_id
  WHERE rpe.property_status != 'ACTIVE'
)
SELECT
  disabled_in_create,
  CASE
    WHEN disabled_in_create = 0 THEN '✓ PASS'
    ELSE '✗ FAIL: DISABLED properties found in create queue'
  END AS validation_status
FROM disabled_check;

-- Expected: 0 disabled properties

-- ================================================================
-- TEST 6: Earliest timestamp logic works correctly
-- ================================================================
SELECT 'TEST 6: Earliest Timestamp Logic' AS test_name;

WITH multi_property_timestamps AS (
  SELECT
    sfdc_id,
    MIN(idv_enabled_at) AS expected_earliest_idv
  FROM crm.sfdc_dbx.rds_properties_enriched
  WHERE property_status = 'ACTIVE'
    AND has_valid_sfdc_id = 1
    AND idv_enabled = TRUE
  GROUP BY sfdc_id
  HAVING COUNT(*) > 1  -- Only multi-property cases
),
aggregated_timestamps AS (
  SELECT
    sfdc_id,
    idv_enabled_at AS actual_idv
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
  WHERE idv_enabled = TRUE
)
SELECT
  COUNT(*) AS total_test_cases,
  SUM(CASE
    WHEN mp.expected_earliest_idv = agg.actual_idv THEN 1
    ELSE 0
  END) AS passed_cases,
  CASE
    WHEN COUNT(*) = SUM(CASE WHEN mp.expected_earliest_idv = agg.actual_idv THEN 1 ELSE 0 END)
    THEN '✓ PASS: Timestamps correctly aggregated'
    ELSE '✗ FAIL: Timestamp aggregation incorrect'
  END AS validation_status
FROM multi_property_timestamps mp
JOIN aggregated_timestamps agg ON mp.sfdc_id = agg.sfdc_id;

-- ================================================================
-- SUMMARY: All Tests
-- ================================================================
SELECT
  '==================' AS separator,
  'VALIDATION SUMMARY' AS summary_title,
  '==================' AS separator2;

-- Run all tests and collect results
-- (In practice, you'd run each test individually and collect results)
```

---

### Step 2.2: Business Case Validation

**File:** `sql/validation/02_business_case_validation.sql`

```sql
-- ============================================================================
-- BUSINESS CASE VALIDATION
-- Validate specific known scenarios
-- ============================================================================

-- ================================================================
-- CASE 1: Park Kennedy (Known Multi-Property Case)
-- ================================================================
SELECT 'CASE 1: Park Kennedy Property' AS test_case;

SELECT
  sfdc_id,
  property_name,
  active_property_count,
  contributing_rds_property_ids,

  -- Features should be enabled (from ACTIVE property only)
  idv_enabled,
  bank_linking_enabled,
  payroll_enabled,
  income_insights_enabled,

  -- Verify correct property metadata used
  primary_rds_property_id,

  -- Audit trail
  is_multi_property,
  has_any_features_enabled

FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
WHERE sfdc_id = 'a01Dn00000HHUanIAH';

-- EXPECTED RESULTS:
-- - active_property_count: 1 or 2 (depending on data)
-- - idv_enabled: TRUE
-- - bank_linking_enabled: TRUE
-- - payroll_enabled: TRUE
-- - income_insights_enabled: TRUE
-- - primary_rds_property_id: The ACTIVE property's ID
-- - is_multi_property: TRUE (if 2 properties)

-- ================================================================
-- CASE 2: Properties in "Create" Queue with Features
-- ================================================================
SELECT 'CASE 2: P1 Critical Properties (Features but Not in SF)' AS test_case;

-- Should match the 507 properties identified in earlier analysis
SELECT
  COUNT(*) AS properties_with_features_to_create,
  COUNT(DISTINCT company_id) AS distinct_companies,

  -- Feature breakdown
  SUM(CASE WHEN idv_enabled THEN 1 ELSE 0 END) AS with_idv,
  SUM(CASE WHEN bank_linking_enabled THEN 1 ELSE 0 END) AS with_bank,
  SUM(CASE WHEN payroll_enabled THEN 1 ELSE 0 END) AS with_payroll,
  SUM(CASE WHEN income_insights_enabled THEN 1 ELSE 0 END) AS with_income

FROM crm.sfdc_dbx.properties_to_create
WHERE idv_enabled = TRUE
   OR bank_linking_enabled = TRUE
   OR payroll_enabled = TRUE
   OR income_insights_enabled = TRUE;

-- EXPECTED: ~507 properties (from P1 critical analysis)

-- Sample 10 of these critical properties
SELECT
  rds_property_id,
  property_name,
  short_id,
  company_id,
  idv_enabled,
  bank_linking_enabled,
  payroll_enabled,
  income_insights_enabled,
  created_at
FROM crm.sfdc_dbx.properties_to_create
WHERE idv_enabled = TRUE
   OR bank_linking_enabled = TRUE
   OR payroll_enabled = TRUE
   OR income_insights_enabled = TRUE
LIMIT 10;

-- ================================================================
-- CASE 3: Blocked Properties (Duplicate SFDC IDs)
-- ================================================================
SELECT 'CASE 3: Previously Blocked Multi-Property Cases' AS test_case;

-- Properties that were blocked due to duplicate SFDC IDs
-- Should now be aggregated and ready to sync
SELECT
  active_property_count AS num_rds_properties,
  COUNT(*) AS num_sfdc_ids,
  SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS with_features

FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
WHERE is_multi_property = TRUE
GROUP BY active_property_count
ORDER BY active_property_count;

-- EXPECTED: ~2,410 SFDC IDs with multiple properties (from earlier analysis)

-- ================================================================
-- CASE 4: Feature Mismatch Cases (799 properties)
-- ================================================================
SELECT 'CASE 4: IDV Enabled in RDS but FALSE in SF' AS test_case;

-- Properties where features should update
WITH sf_current_state AS (
  SELECT
    pp.snappt_property_id_c,
    pp.idv_enabled_c AS sf_idv_enabled
  FROM crm.salesforce.product_property pp
  WHERE pp.is_deleted = FALSE
)
SELECT
  COUNT(*) AS properties_with_mismatch,
  SUM(CASE WHEN ptu.idv_enabled = TRUE AND sf.sf_idv_enabled = FALSE THEN 1 ELSE 0 END) AS idv_to_be_updated

FROM crm.sfdc_dbx.properties_to_update ptu
JOIN crm.sfdc_dbx.rds_properties_enriched rpe
  ON ptu.primary_rds_property_id = rpe.rds_property_id
LEFT JOIN sf_current_state sf
  ON ptu.snappt_property_id_c = sf.snappt_property_id_c

WHERE ptu.idv_enabled = TRUE
  AND (sf.sf_idv_enabled = FALSE OR sf.sf_idv_enabled IS NULL);

-- EXPECTED: ~799 properties (from earlier analysis)

-- ================================================================
-- CASE 5: Complete Pipeline Coverage
-- ================================================================
SELECT 'CASE 5: End-to-End Pipeline Coverage' AS test_case;

SELECT
  'Active RDS Properties' AS stage,
  COUNT(*) AS count,
  1 AS sort_order
FROM crm.sfdc_dbx.rds_properties_enriched
WHERE property_status = 'ACTIVE' AND has_valid_sfdc_id = 1

UNION ALL

SELECT
  'Aggregated SFDC IDs' AS stage,
  COUNT(*) AS count,
  2 AS sort_order
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id

UNION ALL

SELECT
  'Properties to Create' AS stage,
  COUNT(*) AS count,
  3 AS sort_order
FROM crm.sfdc_dbx.properties_to_create

UNION ALL

SELECT
  'Properties to Update' AS stage,
  COUNT(*) AS count,
  4 AS sort_order
FROM crm.sfdc_dbx.properties_to_update

UNION ALL

SELECT
  'Total Coverage (Create + Update)' AS stage,
  (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create) +
  (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update) AS count,
  5 AS sort_order

ORDER BY sort_order;
```

---

### Step 2.3: Edge Case Testing

**File:** `sql/validation/03_edge_case_testing.sql`

```sql
-- ============================================================================
-- EDGE CASE TESTING
-- Test unusual scenarios that could break sync
-- ============================================================================

-- ================================================================
-- EDGE CASE 1: Properties with NULL sfdc_id
-- ================================================================
SELECT 'EDGE CASE 1: Properties with NULL sfdc_id' AS test_name;

SELECT
  COUNT(*) AS null_sfdc_id_count,
  COUNT(DISTINCT company_id) AS companies_affected
FROM crm.sfdc_dbx.rds_properties_enriched
WHERE property_status = 'ACTIVE'
  AND (sfdc_id IS NULL OR sfdc_id = 'XXXXXXXXXXXXXXX');

-- These properties should appear in properties_to_create
-- Verify they're NOT in aggregated view (which requires valid sfdc_id)

-- ================================================================
-- EDGE CASE 2: Properties with features but no company
-- ================================================================
SELECT 'EDGE CASE 2: Features but No Company' AS test_name;

SELECT COUNT(*) AS orphaned_properties_count
FROM crm.sfdc_dbx.rds_properties_enriched
WHERE property_status = 'ACTIVE'
  AND company_id IS NULL
  AND (idv_enabled = TRUE OR bank_linking_enabled = TRUE
       OR payroll_enabled = TRUE OR income_insights_enabled = TRUE);

-- Expected: 0 (these should be filtered out)

-- ================================================================
-- EDGE CASE 3: SFDC ID shared by 3+ properties
-- ================================================================
SELECT 'EDGE CASE 3: High-Cardinality SFDC IDs (3+ properties)' AS test_name;

SELECT
  sfdc_id,
  active_property_count,
  contributing_rds_property_ids,
  property_name,
  idv_enabled,
  bank_linking_enabled,
  payroll_enabled
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
WHERE active_property_count >= 3
ORDER BY active_property_count DESC
LIMIT 20;

-- Review these manually to ensure aggregation logic makes sense

-- ================================================================
-- EDGE CASE 4: Very old properties (created > 2 years ago)
-- ================================================================
SELECT 'EDGE CASE 4: Old Properties (> 2 years)' AS test_name;

SELECT
  COUNT(*) AS old_properties,
  SUM(CASE WHEN idv_enabled OR bank_linking_enabled OR payroll_enabled
           OR income_insights_enabled THEN 1 ELSE 0 END) AS with_features
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
WHERE earliest_property_created_at < CURRENT_TIMESTAMP() - INTERVAL 2 YEARS;

-- These should still sync correctly

-- ================================================================
-- EDGE CASE 5: Recently updated properties (< 24 hours)
-- ================================================================
SELECT 'EDGE CASE 5: Recently Updated Properties' AS test_name;

SELECT
  COUNT(*) AS recently_updated,
  SUM(CASE WHEN has_changes_since_last_sync THEN 1 ELSE 0 END) AS with_pending_changes
FROM crm.sfdc_dbx.properties_to_update
WHERE rds_last_updated_at >= CURRENT_TIMESTAMP() - INTERVAL 1 DAY;

-- These should be prioritized in sync

-- ================================================================
-- EDGE CASE 6: Properties in both create AND update queues (should be 0)
-- ================================================================
SELECT 'EDGE CASE 6: Overlap Between Create and Update' AS test_name;

SELECT COUNT(*) AS overlap_count
FROM crm.sfdc_dbx.properties_to_create ptc
WHERE EXISTS (
  SELECT 1
  FROM crm.sfdc_dbx.properties_to_update ptu
  WHERE ptu.primary_rds_property_id = ptc.rds_property_id
);

-- Expected: 0 (no overlap - mutually exclusive)
```

---

## ✅ PHASE 2 COMPLETION CHECKLIST

- [ ] All data quality tests pass
- [ ] Park Kennedy case validates correctly
- [ ] 507 P1 critical properties identified in "to create" queue
- [ ] 799 feature mismatch properties identified in "to update" queue
- [ ] 2,410 multi-property SFDC IDs correctly aggregated
- [ ] No edge cases discovered that break assumptions
- [ ] All validation queries documented
- [ ] Test results reviewed by stakeholder

**If any tests fail:** Investigate root cause, fix view logic, and re-run Phase 2

---

## 🔧 PHASE 3: CENSUS CONFIGURATION

**Duration:** 3 days
**Risk Level:** Medium
**Prerequisites:** Phase 2 validation passed

---

### Step 3.1: Prepare Census Workspace

**Pre-requisites:**
- [ ] Census workspace ID: `33026` (confirmed)
- [ ] Census API access token available
- [ ] Databricks connection verified in Census
- [ ] Salesforce connection verified in Census
- [ ] Appropriate permissions in Salesforce (Insert, Update on product_property)

---

### Step 3.2: Configure Census Sync A - Create New Properties

**Sync Configuration:**

```yaml
Sync Name: "RDS Properties → SF product_property (CREATE NEW)"
Sync ID: TBD (generated by Census)

Source:
  Connection: Databricks (Snappt Production)
  Database: crm
  Schema: sfdc_dbx
  Table/View: properties_to_create

Destination:
  Connection: Salesforce (Snappt Production)
  Object: product_property__c  # Custom object name in SF

Sync Behavior:
  Mode: Create Only

  "When a record exists in the source but not in the destination:"
    → Create new record

  "When a record exists in both source and destination:"
    → Skip (do not update)

Sync Key (Unique Identifier):
  Source Field: rds_property_id
  Destination Field: snappt_property_id__c

  Operation: Match on this field to determine if record exists

Field Mappings:
  # Identifiers
  rds_property_id        → snappt_property_id__c       (SYNC KEY)
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

Sync Schedule:
  Frequency: Every 15 minutes

  Reasoning: New properties should be created quickly to minimize lag
  between RDS creation and SF availability

Error Handling:
  On Error: Log and continue (don't halt entire sync)
  Notifications: Email to data-team@snappt.com
  Retry Logic: 3 retries with exponential backoff

Filters:
  None (already filtered in source view)

Advanced Settings:
  Batch Size: 1000 records per API call
  Rate Limiting: Respect Salesforce API limits
  Deduplication: Use sync key (snappt_property_id__c)
```

**Testing Plan for Sync A:**

```sql
-- 1. Identify 10 test properties
CREATE OR REPLACE TEMP VIEW test_properties_for_sync_a AS
SELECT *
FROM crm.sfdc_dbx.properties_to_create
WHERE company_id IN (
  SELECT company_id
  FROM crm.sfdc_dbx.properties_to_create
  GROUP BY company_id
  HAVING COUNT(*) >= 2  -- Companies with multiple properties
  ORDER BY RANDOM()
  LIMIT 5
)
LIMIT 10;

-- 2. Export these for manual verification
SELECT
  rds_property_id,
  short_id,
  property_name,
  company_id,
  idv_enabled,
  bank_linking_enabled,
  city,
  state
FROM test_properties_for_sync_a;

-- 3. After sync runs, verify in Salesforce
-- (Query Salesforce via SOQL or Census query tool)
-- SELECT Id, snappt_property_id__c, Name, IDV_Enabled__c, Bank_Linking_Enabled__c
-- FROM product_property__c
-- WHERE snappt_property_id__c IN (<test IDs>)
```

---

### Step 3.3: Configure Census Sync B - Update Existing Properties

**Sync Configuration:**

```yaml
Sync Name: "RDS Properties → SF product_property (UPDATE EXISTING)"
Sync ID: TBD (generated by Census)

Source:
  Connection: Databricks (Snappt Production)
  Database: crm
  Schema: sfdc_dbx
  Table/View: properties_to_update

Destination:
  Connection: Salesforce (Snappt Production)
  Object: product_property__c

Sync Behavior:
  Mode: Update Only

  "When a record exists in the source but not in the destination:"
    → Skip (do not create)

  "When a record exists in both source and destination:"
    → Update destination with source data

Sync Key (Unique Identifier):
  Source Field: snappt_property_id_c  # Already contains the SF identifier
  Destination Field: snappt_property_id__c

  Operation: Match on this field to find existing records

Field Mappings:
  # Identifiers (DO NOT UPDATE THESE - use for matching only)
  snappt_property_id_c   → snappt_property_id__c     (SYNC KEY - match only)

  # Property Information (from aggregated data)
  property_name          → Name
  short_id               → Short_ID__c
  address                → Property_Address_Street__c
  city                   → Property_Address_City__c
  state                  → Property_Address_State__c
  postal_code            → Property_Address_Postal_Code__c
  country                → Property_Address_Country__c
  company_id             → Company_ID__c
  company_name           → Company_Name__c

  # Feature Flags (AGGREGATED via union logic)
  idv_enabled            → IDV_Enabled__c
  bank_linking_enabled   → Bank_Linking_Enabled__c
  payroll_enabled        → Payroll_Enabled__c
  income_insights_enabled → Income_Insights_Enabled__c
  document_fraud_enabled → Document_Fraud_Enabled__c

  # Feature Timestamps (EARLIEST across all contributing properties)
  idv_enabled_at         → IDV_Enabled_At__c
  bank_linking_enabled_at → Bank_Linking_Enabled_At__c
  payroll_enabled_at     → Payroll_Enabled_At__c
  income_insights_enabled_at → Income_Insights_Enabled_At__c
  document_fraud_enabled_at → Document_Fraud_Enabled_At__c

  # Aggregation Metadata (for audit)
  active_property_count  → Active_Property_Count__c
  total_feature_count    → Total_Feature_Count__c
  rds_last_updated_at    → RDS_Last_Updated_At__c

  # Flags for monitoring
  is_multi_property      → Is_Multi_Property__c
  has_any_features_enabled → Has_Any_Features_Enabled__c

Sync Schedule:
  Frequency: Every 30 minutes

  Reasoning: Updates are less urgent than creates. 30min provides good
  balance between freshness and API usage.

Change Detection (Optional - recommended for efficiency):
  Enable: Yes
  Changed Field: rds_last_updated_at

  Only sync records where rds_last_updated_at has changed since last sync
  This reduces API calls for properties that haven't changed

Error Handling:
  On Error: Log and continue
  Notifications: Email to data-team@snappt.com
  Retry Logic: 3 retries with exponential backoff

Filters:
  # Optional: Only sync properties with changes
  has_changes_since_last_sync = true

Advanced Settings:
  Batch Size: 1000 records per API call
  Rate Limiting: Respect Salesforce API limits
  Deduplication: Use sync key

  # IMPORTANT: Set update mode to "Replace"
  # This ensures FALSE values overwrite TRUE (not just NULL overwriting)
  Update Mode: Replace (not Merge)
```

**Testing Plan for Sync B:**

```sql
-- 1. Identify test cases covering different scenarios
CREATE OR REPLACE TEMP VIEW test_properties_for_sync_b AS

-- Scenario 1: Single property, feature mismatch
SELECT * FROM crm.sfdc_dbx.properties_to_update
WHERE is_multi_property = FALSE
  AND idv_enabled = TRUE
LIMIT 3

UNION ALL

-- Scenario 2: Multi-property aggregation (Park Kennedy)
SELECT * FROM crm.sfdc_dbx.properties_to_update
WHERE sfdc_id = 'a01Dn00000HHUanIAH'

UNION ALL

-- Scenario 3: Multi-property without features
SELECT * FROM crm.sfdc_dbx.properties_to_update
WHERE is_multi_property = TRUE
  AND has_any_features_enabled = FALSE
LIMIT 3

UNION ALL

-- Scenario 4: Multi-property WITH features
SELECT * FROM crm.sfdc_dbx.properties_to_update
WHERE is_multi_property = TRUE
  AND has_any_features_enabled = TRUE
LIMIT 3;

-- 2. Export for verification
SELECT
  snappt_property_id_c,
  sfdc_id,
  property_name,
  active_property_count,
  is_multi_property,
  idv_enabled,
  bank_linking_enabled,
  has_any_features_enabled
FROM test_properties_for_sync_b;

-- 3. Query Salesforce BEFORE sync to capture current state
-- (Save this output for comparison)

-- 4. Run sync

-- 5. Query Salesforce AFTER sync to verify updates
```

---

### Step 3.4: Census Sync Testing Checklist

**Before Running Any Syncs:**

- [ ] Confirm all field names in Salesforce match exactly (case-sensitive)
- [ ] Verify Salesforce field types match source data types
- [ ] Check Salesforce field permissions (read/write access)
- [ ] Confirm no Salesforce validation rules will block sync
- [ ] Review Salesforce workflow rules (ensure they won't conflict)
- [ ] Test with Census "Dry Run" mode first (if available)

**After Configuring Sync A:**

- [ ] Sync A created in Census workspace
- [ ] Sync key correctly set (rds_property_id → snappt_property_id__c)
- [ ] All field mappings validated
- [ ] Schedule set to 15 minutes
- [ ] Error notifications configured
- [ ] Test sync on 10 properties
- [ ] Verify 10 properties created in Salesforce
- [ ] Verify features match expected values
- [ ] Check no errors in Census logs

**After Configuring Sync B:**

- [ ] Sync B created in Census workspace
- [ ] Sync key correctly set (snappt_property_id_c → snappt_property_id__c)
- [ ] All field mappings validated (including aggregation fields)
- [ ] Schedule set to 30 minutes
- [ ] Change detection enabled
- [ ] Error notifications configured
- [ ] Test sync on 10 properties (covering all test scenarios)
- [ ] Verify updates in Salesforce match aggregated data
- [ ] Verify Park Kennedy case updated correctly
- [ ] Check no errors in Census logs

---

## ✅ PHASE 3 COMPLETION CHECKLIST

- [ ] Both Census syncs configured
- [ ] Test syncs successful (10 records each)
- [ ] Field mappings validated in Salesforce
- [ ] Schedules activated
- [ ] Error monitoring in place
- [ ] Sync A and Sync B don't conflict
- [ ] Documentation updated with Census sync IDs
- [ ] Rollback plan documented (see below)

**Rollback Plan for Phase 3:**

If syncs cause issues:

1. **Pause both syncs immediately** in Census
2. **Identify affected records** (use audit log)
3. **Manual rollback if needed:**
   ```sql
   -- Delete records created by Sync A (if problematic)
   -- DELETE FROM product_property__c
   -- WHERE Sync_Queued_At__c > '2026-01-XX'  -- Date sync started
   --   AND snappt_property_id__c IN (<test IDs>)
   ```
4. **Fix configuration issues**
5. **Re-test on small batch**
6. **Resume syncs**

---

**Next:** [Phase 4: Pilot Rollout](#phase-4-pilot-rollout)
