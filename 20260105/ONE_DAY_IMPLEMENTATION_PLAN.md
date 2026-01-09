# ONE-DAY Implementation Plan: RDS → Salesforce Sync Architecture

**Timeline:** 8 hours (single day, focused work)
**Risk Level:** HIGH (compressed timeline)
**Prerequisites:** Must have all access/permissions ready BEFORE starting

---

## ⚠️ CRITICAL WARNINGS

### What You're Trading for Speed

| Full Plan (4 weeks) | 1-Day Plan | Risk |
|---------------------|------------|------|
| Extensive validation (2 days) | Basic validation (30 min) | 🔴 **HIGH** - May miss edge cases |
| Pilot test (50+50 properties) | Skip pilot, go straight to prod | 🔴 **HIGH** - No safety net |
| 48-hour monitoring | Monitor during implementation only | 🟠 **MEDIUM** - Issues may surface later |
| Full documentation | Minimal notes only | 🟡 **LOW** - Can document later |
| Team training | Skip training | 🟡 **LOW** - Can train later |

### When NOT to Use This Plan

**DO NOT proceed with 1-day plan if:**
- ❌ This is your first time doing Census syncs
- ❌ You don't have direct Databricks + Census + Salesforce access
- ❌ You can't dedicate 8 uninterrupted hours
- ❌ Stakeholders need extensive validation before rollout
- ❌ You're risk-averse or in a compliance-heavy environment
- ❌ It's a Friday or day before holiday

### When This Plan Makes Sense

**✅ Proceed with 1-day plan if:**
- ✅ You're experienced with Databricks, Census, and Salesforce
- ✅ You have all access/permissions pre-verified
- ✅ You can dedicate full day without interruptions
- ✅ You have stakeholder buy-in for aggressive timeline
- ✅ You're comfortable with higher risk
- ✅ You can monitor closely for 1 week after
- ✅ It's Tuesday-Thursday (allows recovery time if issues)

---

## 🎯 ONE-DAY SUCCESS CRITERIA (Reduced)

**Minimum viable success:**
- [ ] All 6 views created and queryable
- [ ] Both Census syncs configured and tested on 5 properties each
- [ ] Full sync executed (1,081 + 7,980 properties)
- [ ] Spot-check validation passes (20 properties)
- [ ] Error rate <5% (vs <1% in full plan)
- [ ] Basic monitoring query documented

**Accept these compromises:**
- Incomplete validation (will catch issues in production)
- No pilot phase (test on 5, then go full)
- Minimal documentation (runbook comes later)
- No team training (you're the expert for now)
- Higher error tolerance (5% vs 1%)

---

## ⏰ HOUR-BY-HOUR TIMELINE

### **HOUR 0: Pre-Flight (BEFORE you start the clock)**

**Do this the day before or early morning before starting:**

```bash
# Verify all access
# 1. Databricks
databricks workspace ls /  # Should list directories

# 2. Census
# Log in to Census workspace 33026, verify can see syncs

# 3. Salesforce
# Log in, verify can query product_property object

# 4. Prepare your environment
cd /Users/danerosa/rds_databricks_claude
ls -la  # Verify all files present

# 5. No meetings on calendar for next 8 hours
# 6. Slack status set to "Do Not Disturb"
# 7. Phone on silent
```

**Pre-flight checklist:**
- [ ] Databricks SQL editor open
- [ ] Census workspace open in browser
- [ ] Salesforce open in another tab
- [ ] Implementation plans open (this file + main plans)
- [ ] Coffee/water ready
- [ ] Backup laptop charged (in case primary dies)
- [ ] Stakeholder notified: "Going dark for 8 hours, implementing sync"

---

### **HOUR 1 (9:00-10:00 AM): Build Core Views**

**Goal:** Create the 3 most critical views

#### 9:00-9:20: Create `rds_properties_enriched`

```sql
-- Copy from IMPLEMENTATION_PLAN_NEW_SYNC_ARCHITECTURE.md
-- Step 1.1, lines ~60-140

CREATE OR REPLACE VIEW crm.sfdc_dbx.rds_properties_enriched AS
SELECT
  p.id AS rds_property_id,
  p.sfdc_id,
  p.short_id,
  p.company_id,
  p.name AS property_name,
  p.status AS property_status,
  p.address_street AS address,
  p.address_city AS city,
  p.address_state AS state,
  p.address_postal_code AS postal_code,
  p.address_country AS country,
  p.created_at,
  p.updated_at,
  p.company_name,

  COALESCE(pf.idv_enabled, FALSE) AS idv_enabled,
  COALESCE(pf.bank_linking_enabled, FALSE) AS bank_linking_enabled,
  COALESCE(pf.payroll_enabled, FALSE) AS payroll_enabled,
  COALESCE(pf.income_insights_enabled, FALSE) AS income_insights_enabled,
  COALESCE(pf.document_fraud_enabled, FALSE) AS document_fraud_enabled,

  pf.idv_enabled_at,
  pf.bank_linking_enabled_at,
  pf.payroll_enabled_at,
  pf.income_insights_enabled_at,
  pf.document_fraud_enabled_at,

  pf.feature_count,
  pf.last_feature_update_at,

  CASE WHEN p.status = 'ACTIVE' THEN 1 ELSE 0 END AS is_active,
  CASE WHEN p.sfdc_id IS NOT NULL AND p.sfdc_id != 'XXXXXXXXXXXXXXX' THEN 1 ELSE 0 END AS has_valid_sfdc_id

FROM rds.pg_rds_public.properties p
LEFT JOIN rds.pg_rds_public.property_features pf ON p.id = pf.property_id
WHERE p.company_id IS NOT NULL
  AND p.status != 'DELETED';

-- Quick validation (30 seconds)
SELECT COUNT(*) FROM crm.sfdc_dbx.rds_properties_enriched;
-- Expected: ~20,000
```

**If errors:** Fix immediately, don't proceed. Common issues:
- Table names wrong → Check spelling
- Column names wrong → Use `DESCRIBE TABLE` to check
- Permission denied → Get access before continuing

#### 9:20-9:45: Create `properties_aggregated_by_sfdc_id` ⭐ (MOST IMPORTANT)

```sql
-- This is the core innovation
-- Copy from IMPLEMENTATION_PLAN_NEW_SYNC_ARCHITECTURE.md
-- Step 1.2, lines ~160-320

CREATE OR REPLACE VIEW crm.sfdc_dbx.properties_aggregated_by_sfdc_id AS

WITH active_properties AS (
  SELECT *
  FROM crm.sfdc_dbx.rds_properties_enriched
  WHERE property_status = 'ACTIVE'
    AND has_valid_sfdc_id = 1
),

aggregated AS (
  SELECT
    sfdc_id,

    -- Property metadata from most recent
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

    -- Feature flags - UNION logic
    MAX(idv_enabled) AS idv_enabled,
    MAX(bank_linking_enabled) AS bank_linking_enabled,
    MAX(payroll_enabled) AS payroll_enabled,
    MAX(income_insights_enabled) AS income_insights_enabled,
    MAX(document_fraud_enabled) AS document_fraud_enabled,

    -- Feature timestamps - earliest
    MIN(CASE WHEN idv_enabled THEN idv_enabled_at END) AS idv_enabled_at,
    MIN(CASE WHEN bank_linking_enabled THEN bank_linking_enabled_at END) AS bank_linking_enabled_at,
    MIN(CASE WHEN payroll_enabled THEN payroll_enabled_at END) AS payroll_enabled_at,
    MIN(CASE WHEN income_insights_enabled THEN income_insights_enabled_at END) AS income_insights_enabled_at,
    MIN(CASE WHEN document_fraud_enabled THEN document_fraud_enabled_at END) AS document_fraud_enabled_at,

    -- Metrics
    COUNT(DISTINCT rds_property_id) AS active_property_count,
    SUM(feature_count) AS total_feature_count,
    MAX(last_feature_update_at) AS last_feature_update_at,

    -- Audit trail
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

    MIN(created_at) AS earliest_property_created_at,
    MAX(updated_at) AS most_recent_property_updated_at,
    CURRENT_TIMESTAMP() AS aggregated_at

  FROM active_properties
  GROUP BY sfdc_id
)

SELECT
  *,
  CASE WHEN active_property_count > 1 THEN TRUE ELSE FALSE END AS is_multi_property,
  CASE WHEN idv_enabled OR bank_linking_enabled OR payroll_enabled
            OR income_insights_enabled OR document_fraud_enabled
       THEN TRUE ELSE FALSE END AS has_any_features_enabled
FROM aggregated;

-- Quick validation (1 minute)
SELECT
  active_property_count,
  COUNT(*) as sfdc_id_count,
  SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) as with_features
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
GROUP BY active_property_count
ORDER BY active_property_count;

-- Should see: Most have count=1, some have count=2+
```

#### 9:45-10:00: Create `properties_to_create` and `properties_to_update`

```sql
-- View 1: Properties to Create
CREATE OR REPLACE VIEW crm.sfdc_dbx.properties_to_create AS
SELECT
  rds_property_id,
  short_id,
  company_id,
  property_name,
  address,
  city,
  state,
  postal_code,
  country,
  company_name,
  idv_enabled,
  bank_linking_enabled,
  payroll_enabled,
  income_insights_enabled,
  document_fraud_enabled,
  idv_enabled_at,
  bank_linking_enabled_at,
  payroll_enabled_at,
  income_insights_enabled_at,
  document_fraud_enabled_at,
  created_at,
  updated_at,
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

-- Quick check
SELECT COUNT(*) as to_create FROM crm.sfdc_dbx.properties_to_create;
-- Expected: ~1,081

-- View 2: Properties to Update
CREATE OR REPLACE VIEW crm.sfdc_dbx.properties_to_update AS
SELECT
  pp.snappt_property_id_c,
  pp.id AS product_property_staging_id,
  pp.sf_property_id_c AS production_salesforce_id,
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
  agg.idv_enabled,
  agg.bank_linking_enabled,
  agg.payroll_enabled,
  agg.income_insights_enabled,
  agg.document_fraud_enabled,
  agg.idv_enabled_at,
  agg.bank_linking_enabled_at,
  agg.payroll_enabled_at,
  agg.income_insights_enabled_at,
  agg.document_fraud_enabled_at,
  agg.active_property_count,
  agg.contributing_rds_property_ids,
  agg.total_feature_count,
  agg.is_multi_property,
  agg.has_any_features_enabled,
  agg.most_recent_property_updated_at AS rds_last_updated_at,
  pp.last_modified_date AS sf_last_updated_at,
  CASE WHEN agg.most_recent_property_updated_at > pp.last_modified_date
       THEN TRUE ELSE FALSE END AS has_changes_since_last_sync,
  CURRENT_TIMESTAMP() AS sync_queued_at,
  'UPDATE' AS sync_operation
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id agg
INNER JOIN crm.salesforce.product_property pp
  ON agg.sfdc_id = pp.sf_property_id_c
WHERE pp.is_deleted = FALSE;

-- Quick check
SELECT COUNT(*) as to_update FROM crm.sfdc_dbx.properties_to_update;
-- Expected: ~7,980
```

**✅ CHECKPOINT 1 (10:00 AM):**
- [ ] All 3 views created
- [ ] Row counts match expectations (±10%)
- [ ] No SQL errors

**If behind schedule:** Skip audit table (can add later)

---

### **HOUR 2 (10:00-11:00 AM): Quick Validation + Audit Table**

**Goal:** Basic validation that logic is correct

#### 10:00-10:15: Validate Park Kennedy Case

```sql
-- Test the known multi-property case
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

-- Expected: Features should be TRUE (from ACTIVE property only)
-- If features are FALSE or NULL → STOP, debug aggregation logic
```

#### 10:15-10:30: Validate P1 Critical Properties

```sql
-- Should find ~507 properties with features that need to be created
SELECT
  COUNT(*) as p1_critical_count,
  SUM(CASE WHEN idv_enabled THEN 1 ELSE 0 END) as with_idv,
  SUM(CASE WHEN bank_linking_enabled THEN 1 ELSE 0 END) as with_bank
FROM crm.sfdc_dbx.properties_to_create
WHERE idv_enabled = TRUE
   OR bank_linking_enabled = TRUE
   OR payroll_enabled = TRUE
   OR income_insights_enabled = TRUE;

-- Expected: ~507 (from earlier analysis)
-- If way off → Investigate, but don't block if close
```

#### 10:30-10:45: Create Audit Table (Optional but Recommended)

```sql
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
```

#### 10:45-11:00: Create Quick Monitoring Query

```sql
-- Save this as a notebook or query for later
CREATE OR REPLACE VIEW crm.sfdc_dbx.sync_health_quick AS
SELECT
  'Properties to Create' AS metric,
  COUNT(*) AS count
FROM crm.sfdc_dbx.properties_to_create

UNION ALL

SELECT
  'Properties to Update' AS metric,
  COUNT(*) AS count
FROM crm.sfdc_dbx.properties_to_update

UNION ALL

SELECT
  'Multi-Property Cases' AS metric,
  COUNT(*) AS count
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
WHERE is_multi_property = TRUE;

-- Run this to check health
SELECT * FROM crm.sfdc_dbx.sync_health_quick;
```

**✅ CHECKPOINT 2 (11:00 AM):**
- [ ] Park Kennedy validates correctly
- [ ] P1 properties count is reasonable
- [ ] Audit table created (or skipped if short on time)
- [ ] Health check query saved

---

### **HOUR 3 (11:00 AM-12:00 PM): Configure Census Sync A**

**Goal:** Create Census sync for new properties

#### 11:00-11:30: Configure Sync A in Census UI

**Navigate to Census workspace → Create New Sync**

```yaml
Sync Name: "RDS → SF product_property (CREATE)"

Source:
  Connection: Databricks
  Database: crm
  Schema: sfdc_dbx
  Table: properties_to_create

Destination:
  Connection: Salesforce
  Object: product_property__c

Sync Mode: Create Only

Sync Key:
  rds_property_id → snappt_property_id__c

Field Mappings (CRITICAL - check each one):
  rds_property_id        → snappt_property_id__c  ✓ SYNC KEY
  short_id               → Short_ID__c
  company_id             → Company_ID__c
  property_name          → Name
  address                → Property_Address_Street__c
  city                   → Property_Address_City__c
  state                  → Property_Address_State__c
  postal_code            → Property_Address_Postal_Code__c
  country                → Property_Address_Country__c
  company_name           → Company_Name__c
  idv_enabled            → IDV_Enabled__c
  bank_linking_enabled   → Bank_Linking_Enabled__c
  payroll_enabled        → Payroll_Enabled__c
  income_insights_enabled → Income_Insights_Enabled__c
  document_fraud_enabled → Document_Fraud_Enabled__c
  idv_enabled_at         → IDV_Enabled_At__c
  bank_linking_enabled_at → Bank_Linking_Enabled_At__c
  payroll_enabled_at     → Payroll_Enabled_At__c
  income_insights_enabled_at → Income_Insights_Enabled_At__c
  document_fraud_enabled_at → Document_Fraud_Enabled_At__c
  created_at             → RDS_Created_At__c
  updated_at             → RDS_Updated_At__c

Schedule: Manual (we'll trigger manually)
```

**Common mistakes to avoid:**
- ❌ Mapping to wrong field (check exact names in SF)
- ❌ Using "Update or Create" instead of "Create Only"
- ❌ Wrong sync key (must be rds_property_id → snappt_property_id__c)

#### 11:30-12:00: Test Sync A on 5 Properties

**Add a filter to test on small batch first:**

```
Filters: WHERE rds_property_id IN (
  SELECT rds_property_id
  FROM properties_to_create
  WHERE idv_enabled = TRUE
  LIMIT 5
)
```

**Or manually add filter in Census:**
```sql
-- Get 5 test IDs
SELECT rds_property_id
FROM crm.sfdc_dbx.properties_to_create
WHERE idv_enabled = TRUE
LIMIT 5;

-- Copy IDs, add to Census filter:
-- rds_property_id IN ('id1', 'id2', 'id3', 'id4', 'id5')
```

**Trigger sync → Wait 2 minutes → Validate in Salesforce**

```sql
-- Check if created in Salesforce (via Databricks query of SF table)
SELECT
  id,
  snappt_property_id_c,
  name,
  idv_enabled_c,
  bank_linking_enabled_c
FROM crm.salesforce.product_property
WHERE snappt_property_id_c IN ('id1', 'id2', 'id3', 'id4', 'id5')
  AND is_deleted = FALSE;

-- Should see 5 records created
-- Feature flags should match what was in RDS
```

**If test fails:**
- Check Census error logs
- Fix issue (usually field mapping or permissions)
- Retry until 5 properties sync successfully

**✅ CHECKPOINT 3 (12:00 PM):**
- [ ] Census Sync A configured
- [ ] Test sync on 5 properties successful
- [ ] Verified records in Salesforce

---

### **LUNCH BREAK (12:00-12:30 PM) - 30 Minutes**

**Take a break! You're halfway done.**

- Eat something
- Stretch
- Check errors from morning work
- Review afternoon plan

**Set reminder for 12:30 PM sharp to resume**

---

### **HOUR 4 (12:30-1:30 PM): Configure Census Sync B**

**Goal:** Create Census sync for updates

#### 12:30-1:00: Configure Sync B in Census UI

```yaml
Sync Name: "RDS → SF product_property (UPDATE)"

Source:
  Connection: Databricks
  Database: crm
  Schema: sfdc_dbx
  Table: properties_to_update

Destination:
  Connection: Salesforce
  Object: product_property__c

Sync Mode: Update Only  ← CRITICAL

Sync Key:
  snappt_property_id_c → snappt_property_id__c  ← DIFFERENT from Sync A

Field Mappings (same as Sync A, but ADD these):
  # All the same mappings as Sync A
  # PLUS these aggregation fields:

  active_property_count  → Active_Property_Count__c
  total_feature_count    → Total_Feature_Count__c
  is_multi_property      → Is_Multi_Property__c
  has_any_features_enabled → Has_Any_Features_Enabled__c
  rds_last_updated_at    → RDS_Last_Updated_At__c

Update Mode: Replace (not Merge)  ← CRITICAL
  # This ensures FALSE overwrites TRUE, not just NULL overwrites

Schedule: Manual
```

#### 1:00-1:30: Test Sync B on 5 Properties

**Filter for test (include Park Kennedy if possible):**

```sql
-- Get test properties including multi-property case
SELECT snappt_property_id_c
FROM crm.sfdc_dbx.properties_to_update
WHERE sfdc_id = 'a01Dn00000HHUanIAH'  -- Park Kennedy

UNION

SELECT snappt_property_id_c
FROM crm.sfdc_dbx.properties_to_update
WHERE is_multi_property = FALSE
  AND idv_enabled = TRUE
LIMIT 4;

-- Add these IDs to Census filter
```

**Trigger sync → Wait 2 minutes → Validate**

```sql
-- Check Park Kennedy specifically
SELECT
  snappt_property_id_c,
  name,
  sf_property_id_c,
  active_property_count_c,
  idv_enabled_c,
  bank_linking_enabled_c,
  is_multi_property_c
FROM crm.salesforce.product_property
WHERE sf_property_id_c = 'a01Dn00000HHUanIAH';

-- Expected:
-- active_property_count_c: 2 (or whatever the aggregation showed)
-- idv_enabled_c: TRUE
-- is_multi_property_c: TRUE
```

**✅ CHECKPOINT 4 (1:30 PM):**
- [ ] Census Sync B configured
- [ ] Test sync on 5 properties successful
- [ ] Park Kennedy case verified correct

---

### **HOUR 5 (1:30-2:30 PM): FULL ROLLOUT - Sync A (Creates)**

**⚠️ POINT OF NO RETURN**

**This is where we go to production. Last chance to abort.**

#### 1:30-1:35: Pre-Flight Check

```sql
-- 1. Count what we're about to create
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create;
-- Note this number

-- 2. Baseline: Current count in SF
SELECT COUNT(*)
FROM crm.salesforce.product_property
WHERE is_deleted = FALSE;
-- Note this number

-- 3. No active incidents in Salesforce
-- Check: https://status.salesforce.com

-- 4. Census API limits OK
-- Check Census dashboard - should have plenty of quota
```

**GO/NO-GO Decision:**
- ✅ Test syncs worked? → GO
- ✅ Counts look reasonable? → GO
- ✅ Salesforce healthy? → GO
- ✅ You have 3 hours left? → GO
- ❌ Any NO above? → STOP, debug first

#### 1:35-1:40: Remove Test Filter from Sync A

- Go to Census Sync A
- Remove any WHERE filters
- Save configuration
- **Double-check:** Mode is still "Create Only"

#### 1:40-1:45: Trigger Full Sync A

- Click "Trigger Sync Now"
- **Record start time:** _______________
- **Estimated duration:** 15-30 minutes for ~1,081 properties

#### 1:45-2:15: Monitor Sync A (30 minutes)

**Watch Census logs every 5 minutes:**
- Records processed: should climb steadily
- Error count: should stay near 0
- If error rate >10% → Pause sync, investigate

**Run this query every 5 minutes:**

```sql
-- Queue should shrink as properties get created
SELECT COUNT(*) as remaining_to_create
FROM crm.sfdc_dbx.properties_to_create;

-- This count should decrease as sync progresses
```

#### 2:15-2:30: Validate Sync A Completion

```sql
-- 1. Final queue size
SELECT COUNT(*) as remaining_to_create
FROM crm.sfdc_dbx.properties_to_create;
-- Expected: 0 to 50 (allowing for errors/edge cases)

-- 2. Check Census final stats
-- Go to Census → Sync Runs → Latest run
-- Record: Created: _____  Errors: _____

-- 3. Validate in Salesforce
SELECT COUNT(*) as new_records_created
FROM crm.salesforce.product_property
WHERE created_date >= '<sync_start_time>'
  AND is_deleted = FALSE;
-- Expected: ~1,000+ (close to what was in queue)

-- 4. Spot-check 10 created properties
SELECT
  snappt_property_id_c,
  name,
  idv_enabled_c,
  bank_linking_enabled_c,
  created_date
FROM crm.salesforce.product_property
WHERE created_date >= '<sync_start_time>'
LIMIT 10;

-- Verify: Names look right, features match what you expect
```

**✅ CHECKPOINT 5 (2:30 PM):**
- [ ] Sync A completed (or nearly completed)
- [ ] ~1,000+ properties created in Salesforce
- [ ] Error rate <10%
- [ ] Spot-check validation passes

**If checkpoint fails:**
- Don't proceed to Sync B
- Investigate errors
- Fix issues
- Consider stopping for the day

---

### **HOUR 6 (2:30-3:30 PM): FULL ROLLOUT - Sync B (Updates)**

**Goal:** Update all existing properties with aggregated data

#### 2:30-2:35: Pre-Flight Check for Sync B

```sql
-- 1. Count what we're about to update
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update;
-- Expected: ~7,980

-- 2. How many are multi-property cases?
SELECT COUNT(*)
FROM crm.sfdc_dbx.properties_to_update
WHERE is_multi_property = TRUE;
-- Expected: ~2,410 (the ones that were blocked)

-- 3. Salesforce still healthy?
-- Check status page again
```

#### 2:35-2:40: Remove Test Filter from Sync B

- Go to Census Sync B
- Remove any WHERE filters
- **Triple-check:** Mode is "Update Only" (not Create)
- **Triple-check:** Update mode is "Replace" (not Merge)
- Save configuration

#### 2:40-2:45: Trigger Full Sync B

- Click "Trigger Sync Now"
- **Record start time:** _______________
- **Estimated duration:** 30-60 minutes for ~7,980 properties

#### 2:45-3:20: Monitor Sync B (35 minutes)

**Watch Census logs every 5 minutes:**
- Records updated: should climb steadily
- Error count: should stay low
- If error rate >10% → Pause sync, investigate

**During monitoring, prepare validation queries:**

```sql
-- Save these to run after sync completes

-- Query 1: Feature accuracy check
WITH rds_expected AS (
  SELECT
    sfdc_id,
    idv_enabled AS expected_idv,
    bank_linking_enabled AS expected_bank
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
  LIMIT 100  -- Sample 100 for speed
),
sf_actual AS (
  SELECT
    sf_property_id_c AS sfdc_id,
    idv_enabled_c AS actual_idv,
    bank_linking_enabled_c AS actual_bank
  FROM crm.salesforce.product_property
  WHERE is_deleted = FALSE
    AND sf_property_id_c IS NOT NULL
)
SELECT
  COUNT(*) AS sample_size,
  SUM(CASE WHEN rds.expected_idv = sf.actual_idv THEN 1 ELSE 0 END) AS idv_match,
  SUM(CASE WHEN rds.expected_bank = sf.actual_bank THEN 1 ELSE 0 END) AS bank_match,
  ROUND(100.0 * SUM(CASE WHEN rds.expected_idv = sf.actual_idv THEN 1 ELSE 0 END) / COUNT(*), 2) AS idv_accuracy,
  ROUND(100.0 * SUM(CASE WHEN rds.expected_bank = sf.actual_bank THEN 1 ELSE 0 END) / COUNT(*), 2) AS bank_accuracy
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id;

-- Expected: >95% accuracy (we're allowing more errors in 1-day plan)
```

#### 3:20-3:30: Validate Sync B Completion

```sql
-- 1. Check Census final stats
-- Census → Sync Runs → Latest run
-- Record: Updated: _____  Errors: _____  Skipped: _____

-- 2. Verify Park Kennedy
SELECT
  sf_property_id_c,
  name,
  active_property_count_c,
  is_multi_property_c,
  idv_enabled_c,
  bank_linking_enabled_c,
  last_modified_date
FROM crm.salesforce.product_property
WHERE sf_property_id_c = 'a01Dn00000HHUanIAH';

-- Expected:
-- active_property_count_c: 2 (or whatever aggregation showed)
-- idv_enabled_c: TRUE
-- bank_linking_enabled_c: TRUE
-- last_modified_date: Should be very recent (today)

-- 3. Run feature accuracy query (from above)
-- Target: >95% accuracy

-- 4. Check multi-property cases
SELECT COUNT(*) as multi_property_updated
FROM crm.salesforce.product_property
WHERE is_multi_property_c = TRUE
  AND last_modified_date >= '<sync_start_time>';

-- Expected: ~2,410 (the blocked properties)
```

**✅ CHECKPOINT 6 (3:30 PM):**
- [ ] Sync B completed
- [ ] ~7,500+ properties updated
- [ ] Park Kennedy correct
- [ ] Feature accuracy >95%
- [ ] Error rate <10%

---

### **HOUR 7 (3:30-4:30 PM): Validation & Troubleshooting**

**Goal:** Comprehensive validation and fix any issues

#### 3:30-4:00: Run Full Validation Suite

```sql
-- ============================================
-- VALIDATION SUITE (run all of these)
-- ============================================

-- 1. Overall sync success
SELECT
  'Before Rollout' AS status,
  '<baseline_count>' AS properties_in_sf  -- Use number from 1:30 PM
UNION ALL
SELECT
  'After Rollout' AS status,
  CAST(COUNT(*) AS STRING)
FROM crm.salesforce.product_property
WHERE is_deleted = FALSE;

-- Should show increase of ~1,081


-- 2. Properties still missing (should be minimal)
SELECT COUNT(*) AS still_missing
FROM crm.sfdc_dbx.rds_properties_enriched rds
WHERE rds.property_status = 'ACTIVE'
  AND rds.has_valid_sfdc_id = 1
  AND NOT EXISTS (
    SELECT 1
    FROM crm.salesforce.product_property pp
    WHERE CAST(rds.rds_property_id AS STRING) = pp.snappt_property_id_c
      AND pp.is_deleted = FALSE
  );

-- Target: <100 (ideally <50)
-- If >200: Investigate which properties didn't sync


-- 3. P1 Critical properties now visible
SELECT COUNT(*) AS p1_now_in_sf
FROM crm.salesforce.product_property pp
WHERE pp.is_deleted = FALSE
  AND (pp.idv_enabled_c = TRUE
       OR pp.bank_linking_enabled_c = TRUE
       OR pp.payroll_enabled_c = TRUE
       OR pp.income_insights_enabled_c = TRUE)
  AND pp.created_date >= '<rollout_start_time>';

-- Expected: ~507 (the P1 critical properties)


-- 4. Feature sync accuracy (full sample)
WITH rds_expected AS (
  SELECT
    sfdc_id,
    idv_enabled,
    bank_linking_enabled,
    payroll_enabled,
    income_insights_enabled
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
),
sf_actual AS (
  SELECT
    sf_property_id_c AS sfdc_id,
    idv_enabled_c AS idv_enabled,
    bank_linking_enabled_c AS bank_linking_enabled,
    payroll_enabled_c AS payroll_enabled,
    income_insights_enabled_c AS income_insights_enabled
  FROM crm.salesforce.product_property
  WHERE is_deleted = FALSE
    AND sf_property_id_c IS NOT NULL
)
SELECT
  'IDV' AS feature,
  ROUND(100.0 * SUM(CASE WHEN rds.idv_enabled = sf.idv_enabled THEN 1 ELSE 0 END) / COUNT(*), 2) AS accuracy_pct,
  SUM(CASE WHEN rds.idv_enabled != sf.idv_enabled THEN 1 ELSE 0 END) AS mismatches
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id

UNION ALL

SELECT
  'Bank Linking',
  ROUND(100.0 * SUM(CASE WHEN rds.bank_linking_enabled = sf.bank_linking_enabled THEN 1 ELSE 0 END) / COUNT(*), 2),
  SUM(CASE WHEN rds.bank_linking_enabled != sf.bank_linking_enabled THEN 1 ELSE 0 END)
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id

UNION ALL

SELECT
  'Payroll',
  ROUND(100.0 * SUM(CASE WHEN rds.payroll_enabled = sf.payroll_enabled THEN 1 ELSE 0 END) / COUNT(*), 2),
  SUM(CASE WHEN rds.payroll_enabled != sf.payroll_enabled THEN 1 ELSE 0 END)
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id;

-- Target: All features >95% accuracy


-- 5. Multi-property aggregation check
SELECT
  pp.sf_property_id_c,
  pp.name,
  pp.active_property_count_c,
  pp.is_multi_property_c,
  pp.idv_enabled_c,
  pp.bank_linking_enabled_c
FROM crm.salesforce.product_property pp
WHERE pp.is_multi_property_c = TRUE
  AND pp.is_deleted = FALSE
ORDER BY pp.active_property_count_c DESC
LIMIT 20;

-- Manually review these - do they look correct?


-- 6. Error properties
-- Check Census error logs for any properties that failed
-- Document error IDs and reasons
```

#### 4:00-4:30: Fix Critical Issues (if any)

**If validation revealed critical issues:**

**Issue: Many properties still missing (>200)**
```sql
-- Identify which properties didn't sync
SELECT rds_property_id, property_name, company_id
FROM crm.sfdc_dbx.properties_to_create
LIMIT 20;

-- Check Census logs for errors on these IDs
-- Common causes:
-- - Required field missing
-- - Data type mismatch
-- - Salesforce validation rule blocking

-- Fix in view, re-trigger Sync A on failed properties only
```

**Issue: Feature accuracy <90%**
```sql
-- Find specific mismatches
WITH rds_expected AS (
  SELECT sfdc_id, idv_enabled AS expected
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
),
sf_actual AS (
  SELECT sf_property_id_c AS sfdc_id, idv_enabled_c AS actual
  FROM crm.salesforce.product_property
  WHERE is_deleted = FALSE
)
SELECT rds.sfdc_id, rds.expected, sf.actual
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id
WHERE rds.expected != sf.actual
LIMIT 20;

-- Check if pattern (all TRUE in RDS but FALSE in SF?)
-- May need to re-trigger Sync B with different settings
```

**If no critical issues:** Move to documentation

**✅ CHECKPOINT 7 (4:30 PM):**
- [ ] All validation queries run
- [ ] Results documented
- [ ] Critical issues fixed (or noted for follow-up)
- [ ] Success criteria mostly met (allowing for 1-day compromises)

---

### **HOUR 8 (4:30-5:30 PM): Documentation & Cleanup**

**Goal:** Minimal documentation to make this maintainable

#### 4:30-4:45: Enable Census Schedules

```
# Now that we've validated, enable ongoing syncs

Census Sync A → Schedule:
- Change from "Manual" to "Every 15 minutes"
- Save

Census Sync B → Schedule:
- Change from "Manual" to "Every 30 minutes"
- Save

# These will now run automatically going forward
```

#### 4:45-5:00: Create Minimal Runbook

```bash
# Create quick reference file
cat > /Users/danerosa/rds_databricks_claude/QUICK_RUNBOOK.md << 'EOF'
# Property Sync Quick Runbook

## Daily Health Check (5 minutes)

```sql
-- Run this query daily
SELECT * FROM crm.sfdc_dbx.sync_health_quick;
```

**Expected:**
- Properties to Create: <50
- Properties to Update: ~7,980 (stable)
- Multi-Property Cases: ~2,410

**If Create queue >100:** Investigate Census Sync A

## Common Issues

### Issue: Sync A failing
1. Check Census logs for error message
2. Query: `SELECT * FROM crm.sfdc_dbx.properties_to_create LIMIT 10;`
3. Look for NULL required fields
4. Fix in view, re-trigger sync

### Issue: Feature mismatches
1. Run feature accuracy query (see validation section)
2. If <95%: Re-trigger Sync B
3. Check if Salesforce workflow is overwriting data

## Emergency: Rollback

If critical data corruption:
1. Pause both Census syncs immediately
2. Identify affected records:
   ```sql
   SELECT COUNT(*) FROM crm.salesforce.product_property
   WHERE last_modified_date >= '<today>';
   ```
3. If <100 affected: Manual correction
4. If >100: Restore from SF backup
5. Contact: [Your name/email]

## Census Sync IDs
- Sync A (Create): [Record ID from Census]
- Sync B (Update): [Record ID from Census]

## Views Created
- crm.sfdc_dbx.rds_properties_enriched
- crm.sfdc_dbx.properties_aggregated_by_sfdc_id
- crm.sfdc_dbx.properties_to_create
- crm.sfdc_dbx.properties_to_update
- crm.sfdc_dbx.sync_health_quick
EOF
```

#### 5:00-5:15: Document Results

```bash
# Record final metrics
cat > /Users/danerosa/rds_databricks_claude/ROLLOUT_RESULTS.md << 'EOF'
# Rollout Results - [DATE]

## Execution Timeline
- Start: [TIME]
- Sync A Complete: [TIME]
- Sync B Complete: [TIME]
- Validation Complete: [TIME]
- Total Duration: [X] hours

## Final Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Properties Created | ~1,081 | [ACTUAL] | [✓/✗] |
| Properties Updated | ~7,980 | [ACTUAL] | [✓/✗] |
| P1 Properties Synced | 507 | [ACTUAL] | [✓/✗] |
| Feature Accuracy (IDV) | >95% | [ACTUAL]% | [✓/✗] |
| Feature Accuracy (Bank) | >95% | [ACTUAL]% | [✓/✗] |
| Properties Still Missing | <100 | [ACTUAL] | [✓/✗] |
| Error Rate | <10% | [ACTUAL]% | [✓/✗] |

## Known Issues
1. [List any issues that need follow-up]
2. [Error patterns observed]
3. [Edge cases discovered]

## Follow-Up Tasks
- [ ] Monitor for 1 week (daily health checks)
- [ ] Address known issues [deadline]
- [ ] Write full runbook [deadline]
- [ ] Train team on new architecture [deadline]
- [ ] Schedule retrospective [date]

## Contact
- Implementer: [Your name]
- Email: [Your email]
- Slack: [Your handle]
EOF

# Fill in the blanks with actual numbers from your validation queries
```

#### 5:15-5:30: Stakeholder Communication

```bash
# Send brief email/Slack to stakeholders

Subject: Property Sync Rollout Complete - [X] Properties Synced

Team,

Completed rollout of new RDS → Salesforce sync architecture today.

Results:
✓ [X] properties created in Salesforce
✓ [X] properties updated with latest data
✓ [X] P1 critical properties now visible
✓ Feature accuracy: [X]%

Known Issues:
- [List if any critical issues]

Next Steps:
- Monitoring daily for 1 week
- Follow-up fixes for [any issues] by [date]
- Full documentation by [date]

Dashboard: [link to sync_health_quick query]

Questions? Slack me or see QUICK_RUNBOOK.md

[Your name]
```

**✅ FINAL CHECKPOINT (5:30 PM):**
- [ ] Census syncs enabled (15min/30min schedules)
- [ ] Quick runbook created
- [ ] Results documented
- [ ] Stakeholders notified
- [ ] You've survived! 🎉

---

## 🎉 ONE-DAY ROLLOUT COMPLETE

**Congratulations!** You've completed an aggressive 1-day implementation.

### What You Accomplished

✅ Built aggregation layer (handles many-to-1 relationships)
✅ Configured two Census syncs (create vs update)
✅ Synced ~1,000+ missing properties to Salesforce
✅ Updated ~7,500+ existing properties with aggregated data
✅ Unblocked ~2,400 multi-property cases
✅ Enabled automated ongoing syncs

### What You Compromised

⚠️ Minimal validation (vs 2 days in full plan)
⚠️ No pilot phase (went straight to prod)
⚠️ Basic documentation only (vs comprehensive runbooks)
⚠️ Higher error tolerance (5-10% vs <1%)
⚠️ No team training yet

### Critical Next Steps (This Week)

**Tomorrow (Day 2):**
- [ ] Run health check query
- [ ] Review Census logs for overnight syncs
- [ ] Fix any critical errors discovered

**Day 3-5:**
- [ ] Daily health checks
- [ ] Address any lingering issues
- [ ] Monitor feature accuracy
- [ ] Watch for edge cases

**Week 2:**
- [ ] Run full validation suite (from 4-week plan)
- [ ] Write comprehensive runbook
- [ ] Create monitoring dashboard
- [ ] Train team on new architecture

**Week 3:**
- [ ] Set up automated alerts
- [ ] Review with stakeholders
- [ ] Document lessons learned
- [ ] Plan improvements

---

## 🚨 EMERGENCY CONTACTS

**If something goes critically wrong tonight/this week:**

1. **Pause both syncs immediately**
   - Census workspace → Find each sync → Click "Pause"

2. **Assess damage**
   ```sql
   -- How many records affected?
   SELECT COUNT(*)
   FROM crm.salesforce.product_property
   WHERE last_modified_date >= '<today>';
   ```

3. **Contact:**
   - Your name: [Phone/Email]
   - Data Team Lead: [Phone/Email]
   - Census Support: support@getcensus.com

4. **Rollback if needed**
   - See QUICK_RUNBOOK.md

---

## 📊 SUCCESS CRITERIA (1-Day Version)

**Minimum success (accept nothing less):**
- ✅ >800 of 1,081 properties created (>75%)
- ✅ >6,000 of 7,980 properties updated (>75%)
- ✅ >400 of 507 P1 properties visible (>80%)
- ✅ Feature accuracy >90% (vs 99% in full plan)
- ✅ Census syncs running automatically
- ✅ No critical data corruption

**If any of these fail:** Schedule time this week to investigate and fix.

---

## 💡 LESSONS LEARNED

**What worked well:**
- [Document after rollout]

**What was challenging:**
- [Document after rollout]

**What we'd do differently:**
- [Document after rollout]

**Recommendations for future:**
- Use the 4-week plan if possible!
- This 1-day approach is for emergencies only
- The validation we skipped would have caught [X] issues

---

## ✅ WEEKLY MONITORING (Next 4 Weeks)

**Monday mornings:**
```sql
-- Run this query
SELECT * FROM crm.sfdc_dbx.sync_health_quick;

-- Review Census sync runs from past week
-- Check error rate: should be <1% after initial shake-out
```

**If issues arise:**
- Check QUICK_RUNBOOK.md for troubleshooting
- Don't let issues accumulate
- Fix small problems before they become big ones

---

**Implementation Date:** _______________
**Implementer:** _______________
**Start Time:** _______________
**End Time:** _______________
**Total Duration:** _______________
**Final Status:** ✅ Complete / ⚠️ Complete with issues / ❌ Incomplete

**Sign-off:** _______________

---

## 📚 FULL DOCUMENTATION REFERENCES

When you have time to review the full plan:
- `NEW_SYNC_ARCHITECTURE_README.md` - Complete overview
- `IMPLEMENTATION_PLAN_NEW_SYNC_ARCHITECTURE.md` - Phase 1 details
- `IMPLEMENTATION_PLAN_PHASE2_TO_PHASE6.md` - Full validation suite
- `IMPLEMENTATION_PLAN_PHASE4_TO_PHASE6.md` - Operational procedures

**These contain all the details we skipped today.**

---

**Good luck! You've got this! 🚀**
