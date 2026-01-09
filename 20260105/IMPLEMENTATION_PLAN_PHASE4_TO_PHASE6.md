# Implementation Plan: Phases 4-6 (Final)

**Continuation of:** IMPLEMENTATION_PLAN_PHASE2_TO_PHASE6.md

---

## 🧪 PHASE 4: PILOT ROLLOUT

**Duration:** 2 days
**Risk Level:** Medium
**Prerequisites:** Phase 3 completed, Census syncs tested on 10 records each

**Goal:** Test on larger subset (50-100 properties) to validate end-to-end flow including Salesforce workflow triggers

---

### Step 4.1: Select Pilot Properties

**Criteria for Pilot Selection:**

```sql
-- ============================================================================
-- PILOT PROPERTY SELECTION
-- Select diverse set of 50 properties for create + 50 for update
-- ============================================================================

-- ================================================================
-- PILOT SET A: Properties to Create (50 total)
-- ================================================================

CREATE OR REPLACE TEMP VIEW pilot_properties_create AS

-- 10 properties WITH features (high priority)
SELECT *, 'Has Features' AS pilot_reason, 1 AS priority
FROM crm.sfdc_dbx.properties_to_create
WHERE idv_enabled = TRUE OR bank_linking_enabled = TRUE
  OR payroll_enabled = TRUE OR income_insights_enabled = TRUE
ORDER BY RANDOM()
LIMIT 10

UNION ALL

-- 10 properties WITHOUT features (baseline test)
SELECT *, 'No Features' AS pilot_reason, 2 AS priority
FROM crm.sfdc_dbx.properties_to_create
WHERE idv_enabled = FALSE AND bank_linking_enabled = FALSE
  AND payroll_enabled = FALSE AND income_insights_enabled = FALSE
ORDER BY RANDOM()
LIMIT 10

UNION ALL

-- 10 recently created properties (< 30 days old)
SELECT *, 'Recently Created' AS pilot_reason, 3 AS priority
FROM crm.sfdc_dbx.properties_to_create
WHERE created_at >= CURRENT_TIMESTAMP() - INTERVAL 30 DAYS
ORDER BY RANDOM()
LIMIT 10

UNION ALL

-- 10 older properties (> 1 year old)
SELECT *, 'Old Properties' AS pilot_reason, 4 AS priority
FROM crm.sfdc_dbx.properties_to_create
WHERE created_at < CURRENT_TIMESTAMP() - INTERVAL 1 YEAR
ORDER BY RANDOM()
LIMIT 10

UNION ALL

-- 10 properties from diverse companies
SELECT *, 'Diverse Companies' AS pilot_reason, 5 AS priority
FROM crm.sfdc_dbx.properties_to_create
WHERE company_id IN (
  SELECT company_id
  FROM crm.sfdc_dbx.properties_to_create
  GROUP BY company_id
  ORDER BY RANDOM()
  LIMIT 10
)
LIMIT 10;

-- Export pilot list
SELECT
  rds_property_id,
  property_name,
  short_id,
  company_id,
  city,
  state,
  idv_enabled,
  bank_linking_enabled,
  pilot_reason,
  priority
FROM pilot_properties_create
ORDER BY priority, property_name;

-- ================================================================
-- PILOT SET B: Properties to Update (50 total)
-- ================================================================

CREATE OR REPLACE TEMP VIEW pilot_properties_update AS

-- 10 single-property cases (is_multi_property = FALSE)
SELECT *, 'Single Property' AS pilot_reason, 1 AS priority
FROM crm.sfdc_dbx.properties_to_update
WHERE is_multi_property = FALSE
  AND idv_enabled = TRUE
ORDER BY RANDOM()
LIMIT 10

UNION ALL

-- 15 multi-property cases (2 properties)
SELECT *, 'Multi-Property (2)' AS pilot_reason, 2 AS priority
FROM crm.sfdc_dbx.properties_to_update
WHERE active_property_count = 2
ORDER BY RANDOM()
LIMIT 15

UNION ALL

-- 5 multi-property cases (3+ properties)
SELECT *, 'Multi-Property (3+)' AS pilot_reason, 3 AS priority
FROM crm.sfdc_dbx.properties_to_update
WHERE active_property_count >= 3
ORDER BY RANDOM()
LIMIT 5

UNION ALL

-- 10 properties with feature mismatches (will change from FALSE to TRUE)
SELECT *, 'Feature Mismatch' AS pilot_reason, 4 AS priority
FROM crm.sfdc_dbx.properties_to_update
WHERE has_any_features_enabled = TRUE
  AND has_changes_since_last_sync = TRUE
ORDER BY RANDOM()
LIMIT 10

UNION ALL

-- 10 properties without features (baseline)
SELECT *, 'No Features' AS pilot_reason, 5 AS priority
FROM crm.sfdc_dbx.properties_to_update
WHERE has_any_features_enabled = FALSE
ORDER BY RANDOM()
LIMIT 10;

-- Export pilot list
SELECT
  snappt_property_id_c,
  sfdc_id,
  property_name,
  active_property_count,
  is_multi_property,
  idv_enabled,
  bank_linking_enabled,
  has_any_features_enabled,
  pilot_reason,
  priority
FROM pilot_properties_update
ORDER BY priority, property_name;
```

---

### Step 4.2: Execute Pilot Sync A (Create)

**Pre-Flight Checklist:**

- [ ] 50 pilot properties selected and exported
- [ ] Baseline captured (none should exist in product_property yet)
- [ ] Census Sync A configured correctly
- [ ] Error monitoring active
- [ ] Salesforce sandbox available for testing (if using sandbox)
- [ ] Stakeholder notified of pilot start time

**Execution Steps:**

1. **Filter Sync A to Pilot Properties Only**

   ```sql
   -- Temporarily modify properties_to_create view to include only pilot
   CREATE OR REPLACE VIEW crm.sfdc_dbx.properties_to_create AS
   SELECT ptc.*
   FROM crm.sfdc_dbx.properties_to_create_full ptc  -- Rename original view
   INNER JOIN pilot_properties_create pilot
     ON ptc.rds_property_id = pilot.rds_property_id;
   ```

   **OR** configure Census filter:
   ```
   Census Sync A > Filters > Add Filter:
   WHERE rds_property_id IN (<comma-separated pilot IDs>)
   ```

2. **Trigger Sync A Manually**
   - Go to Census workspace
   - Find "RDS Properties → SF product_property (CREATE NEW)"
   - Click "Trigger Sync Now"
   - Monitor execution

3. **Wait for Completion**
   - Expected duration: 2-5 minutes for 50 records
   - Watch Census logs for errors

4. **Validate Results in Salesforce**

   ```soql
   -- Query Salesforce (via Workbench or Salesforce Query Editor)
   SELECT
     Id,
     snappt_property_id__c,
     Name,
     Short_ID__c,
     Company_ID__c,
     IDV_Enabled__c,
     Bank_Linking_Enabled__c,
     Payroll_Enabled__c,
     Income_Insights_Enabled__c,
     RDS_Created_At__c,
     CreatedDate
   FROM product_property__c
   WHERE snappt_property_id__c IN (<pilot IDs>)
   ORDER BY CreatedDate DESC
   ```

5. **Verify Salesforce Workflow Triggered**

   Check if `sf_property_id__c` field gets populated (this indicates the SF workflow ran and created production record):

   ```soql
   SELECT
     Id,
     snappt_property_id__c,
     Name,
     sf_property_id__c  -- Should be NULL initially, then populated by workflow
   FROM product_property__c
   WHERE snappt_property_id__c IN (<pilot IDs>)
   ```

   **Expected Timeline:**
   - Immediately after sync: `sf_property_id__c` = NULL
   - After 5-10 minutes: `sf_property_id__c` = Production ID (if workflow runs)
   - If still NULL after 1 hour: Investigate workflow

---

### Step 4.3: Execute Pilot Sync B (Update)

**Pre-Flight Checklist:**

- [ ] 50 pilot properties selected and exported
- [ ] Baseline captured (current values in product_property)
- [ ] Census Sync B configured correctly
- [ ] Error monitoring active
- [ ] Stakeholder notified

**Execution Steps:**

1. **Capture Baseline (BEFORE sync)**

   ```sql
   -- Export current state in Salesforce for comparison
   -- Run via Databricks (pulls from Salesforce table)
   CREATE OR REPLACE TEMP VIEW pilot_baseline_update AS
   SELECT
     pp.id,
     pp.snappt_property_id_c,
     pp.name,
     pp.sf_property_id_c,
     pp.idv_enabled_c,
     pp.bank_linking_enabled_c,
     pp.payroll_enabled_c,
     pp.active_property_count_c,
     pp.is_multi_property_c,
     pp.last_modified_date,
     CURRENT_TIMESTAMP() AS baseline_captured_at
   FROM crm.salesforce.product_property pp
   WHERE pp.snappt_property_id_c IN (
     SELECT snappt_property_id_c FROM pilot_properties_update
   )
     AND pp.is_deleted = FALSE;

   SELECT * FROM pilot_baseline_update;
   -- SAVE THIS OUTPUT
   ```

2. **Filter Sync B to Pilot Properties Only**

   ```sql
   -- Option 1: Temporarily modify view
   CREATE OR REPLACE VIEW crm.sfdc_dbx.properties_to_update AS
   SELECT ptu.*
   FROM crm.sfdc_dbx.properties_to_update_full ptu
   INNER JOIN pilot_properties_update pilot
     ON ptu.snappt_property_id_c = pilot.snappt_property_id_c;
   ```

   **OR** configure Census filter:
   ```
   Census Sync B > Filters > Add Filter:
   WHERE snappt_property_id_c IN (<comma-separated pilot IDs>)
   ```

3. **Trigger Sync B Manually**
   - Census workspace → "RDS Properties → SF product_property (UPDATE EXISTING)"
   - Click "Trigger Sync Now"
   - Monitor execution

4. **Wait for Completion**
   - Expected duration: 2-5 minutes for 50 records

5. **Validate Results (AFTER sync)**

   ```sql
   -- Query Salesforce via Databricks
   SELECT
     pp.id,
     pp.snappt_property_id_c,
     pp.name,
     pp.sf_property_id_c,
     pp.idv_enabled_c AS current_idv_enabled,
     pp.bank_linking_enabled_c AS current_bank_enabled,
     pp.active_property_count_c,
     pp.is_multi_property_c,
     pp.last_modified_date,

     -- Compare with expected values from RDS
     ptu.idv_enabled AS expected_idv_enabled,
     ptu.bank_linking_enabled AS expected_bank_enabled,
     ptu.active_property_count AS expected_property_count,

     -- Flags for validation
     CASE WHEN pp.idv_enabled_c = ptu.idv_enabled THEN '✓' ELSE '✗' END AS idv_match,
     CASE WHEN pp.bank_linking_enabled_c = ptu.bank_linking_enabled THEN '✓' ELSE '✗' END AS bank_match,
     CASE WHEN pp.active_property_count_c = ptu.active_property_count THEN '✓' ELSE '✗' END AS count_match

   FROM crm.salesforce.product_property pp
   INNER JOIN pilot_properties_update ptu
     ON pp.snappt_property_id_c = ptu.snappt_property_id_c
   WHERE pp.is_deleted = FALSE;
   ```

6. **Validate Specific Test Cases**

   ```sql
   -- Test Case 1: Park Kennedy (if in pilot)
   SELECT
     pp.snappt_property_id_c,
     pp.name,
     pp.sf_property_id_c,
     pp.active_property_count_c,
     pp.idv_enabled_c,
     pp.bank_linking_enabled_c,
     pp.is_multi_property_c
   FROM crm.salesforce.product_property pp
   WHERE pp.sf_property_id_c = 'a01Dn00000HHUanIAH';

   -- Expected:
   -- active_property_count_c: 2 (or however many active properties)
   -- idv_enabled_c: TRUE
   -- bank_linking_enabled_c: TRUE
   -- is_multi_property_c: TRUE

   -- Test Case 2: Feature Mismatch Properties
   -- Compare baseline vs current - IDV should change from FALSE to TRUE
   ```

---

### Step 4.4: Pilot Validation & Sign-Off

**Validation Checklist:**

**Sync A (Create) Validation:**
- [ ] All 50 properties created in product_property
- [ ] No duplicate records created
- [ ] All field values match source data (spot-check 10 records)
- [ ] Feature flags correct (compare with RDS source)
- [ ] No errors in Census logs
- [ ] Salesforce workflow triggered (sf_property_id__c populated within 1 hour)
- [ ] Production Salesforce Property records created (if workflow ran)

**Sync B (Update) Validation:**
- [ ] All 50 properties updated in product_property
- [ ] No records inadvertently created
- [ ] Feature flags updated correctly (100% match expected values)
- [ ] Multi-property cases aggregated correctly
- [ ] Park Kennedy case correct (if in pilot)
- [ ] Feature mismatch cases resolved (FALSE → TRUE)
- [ ] active_property_count__c field populated correctly
- [ ] is_multi_property__c flag correct
- [ ] No errors in Census logs

**Overall Validation:**
- [ ] No data corruption in Salesforce
- [ ] No impact on other records (only pilot records changed)
- [ ] Census syncs completed in reasonable time (< 5 min)
- [ ] Error rate: 0%
- [ ] Stakeholder review completed
- [ ] Sign-off to proceed to full rollout

**If Issues Found:**
1. Document issue details
2. Pause syncs
3. Investigate root cause
4. Fix configuration or view logic
5. Re-run pilot on new batch
6. Do not proceed to Phase 5 until pilot is 100% successful

---

## 🚀 PHASE 5: FULL ROLLOUT

**Duration:** 5 days (including monitoring)
**Risk Level:** Medium-High
**Prerequisites:** Pilot successful, stakeholder sign-off obtained

**Goal:** Sync all properties using new architecture

---

### Step 5.1: Pre-Rollout Preparation

**Checklist:**

- [ ] Pilot results reviewed and approved
- [ ] All stakeholders notified (Sales, CS, Data, Eng)
- [ ] Rollout window scheduled (recommend: Tuesday-Thursday, 10am-12pm PT)
- [ ] Avoid Fridays, holidays, or end-of-quarter
- [ ] On-call engineer identified
- [ ] Rollback plan reviewed and understood
- [ ] Monitoring dashboard ready
- [ ] Alert channels configured (Slack, email)
- [ ] Incident response plan documented

**Communication Template:**

```
Subject: RDS → Salesforce Property Sync - Full Rollout on [DATE]

Team,

We're proceeding with full rollout of the new property sync architecture
on [DATE] at [TIME].

What's happening:
- ~1,081 new properties will be created in Salesforce product_property
- ~7,980 existing properties will be updated with latest data
- 507 properties with enabled features will finally appear in Salesforce
- 799 feature mismatches will be resolved

Expected timeline:
- Sync A (creates): 15-30 minutes
- Sync B (updates): 30-60 minutes
- Salesforce workflow processing: 1-2 hours
- Total: ~2-3 hours for complete propagation

Impact:
- Sales/CS will see more properties in Salesforce
- Property features will be accurate and up-to-date
- No downtime expected

Monitoring:
- Data team will monitor sync progress
- Dashboard available at: [Databricks link]
- Issues will be reported in #data-incidents

Contact:
- On-call: [Name] - [Email/Slack]

[Your name]
Data Team
```

---

### Step 5.2: Remove Pilot Filters

**Restore Full Views:**

```sql
-- ============================================================================
-- RESTORE FULL VIEWS (Remove pilot filters)
-- ============================================================================

-- If you temporarily modified views for pilot, restore them:

-- Option 1: Drop and recreate from original definitions
DROP VIEW IF EXISTS crm.sfdc_dbx.properties_to_create;
DROP VIEW IF EXISTS crm.sfdc_dbx.properties_to_update;

-- Then re-run the original CREATE VIEW statements from Phase 1
-- (sql/03_create_properties_to_create.sql)
-- (sql/04_create_properties_to_update.sql)

-- Option 2: If you renamed original views, rename them back
-- ALTER VIEW crm.sfdc_dbx.properties_to_create_full
--   RENAME TO crm.sfdc_dbx.properties_to_create;

-- Verify row counts
SELECT
  'properties_to_create' AS view_name,
  COUNT(*) AS row_count
FROM crm.sfdc_dbx.properties_to_create

UNION ALL

SELECT
  'properties_to_update' AS view_name,
  COUNT(*) AS row_count
FROM crm.sfdc_dbx.properties_to_update;

-- Expected:
-- properties_to_create: ~1,081 (minus any created during pilot)
-- properties_to_update: ~7,980
```

**Remove Census Filters:**

- [ ] Go to Census Sync A configuration
- [ ] Remove any `WHERE rds_property_id IN (...)` filters
- [ ] Save configuration
- [ ] Go to Census Sync B configuration
- [ ] Remove any `WHERE snappt_property_id_c IN (...)` filters
- [ ] Save configuration

---

### Step 5.3: Execute Full Sync A (Create All Properties)

**T-minus 30 minutes:**
- [ ] Send final notification to stakeholders
- [ ] Confirm on-call engineer ready
- [ ] Open monitoring dashboard
- [ ] Clear Census error logs (for clean tracking)

**T-minus 5 minutes:**
- [ ] Take snapshot of current state

   ```sql
   CREATE OR REPLACE TABLE crm.sfdc_dbx.rollout_snapshot_before AS
   SELECT
     'properties_to_create' AS metric,
     COUNT(*) AS count,
     CURRENT_TIMESTAMP() AS snapshot_time
   FROM crm.sfdc_dbx.properties_to_create

   UNION ALL

   SELECT
     'properties_to_update' AS metric,
     COUNT(*) AS count,
     CURRENT_TIMESTAMP() AS snapshot_time
   FROM crm.sfdc_dbx.properties_to_update

   UNION ALL

   SELECT
     'product_property_current' AS metric,
     COUNT(*) AS count,
     CURRENT_TIMESTAMP() AS snapshot_time
   FROM crm.salesforce.product_property
   WHERE is_deleted = FALSE;
   ```

**T-0: Launch Sync A**

1. Go to Census workspace
2. Navigate to "RDS Properties → SF product_property (CREATE NEW)"
3. Click "Trigger Sync Now"
4. Record start time: _______________

**Monitor Progress:**

```sql
-- Run this query every 5 minutes during sync
SELECT
  COUNT(*) AS total_in_queue,
  SUM(CASE WHEN idv_enabled OR bank_linking_enabled OR payroll_enabled
           OR income_insights_enabled THEN 1 ELSE 0 END) AS with_features,
  MIN(created_at) AS oldest_property,
  MAX(created_at) AS newest_property
FROM crm.sfdc_dbx.properties_to_create;

-- As sync progresses, total_in_queue should decrease
-- (because newly created properties will no longer appear in this view)
```

**Monitor Census:**
- Watch sync progress in Census UI
- Check "Records Processed" counter
- Monitor error rate (should be 0% or near-0%)
- Review any errors immediately

**Expected Duration:** 15-30 minutes for ~1,081 properties

**After Sync Completes:**

```sql
-- Verify properties were created
SELECT
  COUNT(*) AS properties_created,
  MIN(created_date) AS first_created,
  MAX(created_date) AS last_created
FROM crm.salesforce.product_property
WHERE created_date >= '<sync_start_time>'  -- Use actual start time
  AND snappt_property_id_c IN (
    -- Check specific properties that WERE in the create queue
    SELECT rds_property_id FROM crm.sfdc_dbx.rollout_snapshot_create_queue
  );

-- Expected: ~1,081 properties (or total from queue)
```

**Validation:**

```sql
-- Check remaining properties in create queue
SELECT COUNT(*) AS remaining_to_create
FROM crm.sfdc_dbx.properties_to_create;

-- Expected: ~0 to 50 (allowing for very recent additions or edge cases)

-- If > 100: Investigate why properties weren't created
```

---

### Step 5.4: Execute Full Sync B (Update All Properties)

**Wait 15 minutes after Sync A completes** (allow Salesforce to settle)

**Pre-Sync Check:**

```sql
-- Verify no ongoing Salesforce issues
-- Check Salesforce status page
-- Confirm API limits not exceeded
```

**T-0: Launch Sync B**

1. Go to Census workspace
2. Navigate to "RDS Properties → SF product_property (UPDATE EXISTING)"
3. Click "Trigger Sync Now"
4. Record start time: _______________

**Monitor Progress:**

```sql
-- Run every 5 minutes
SELECT
  COUNT(*) AS total_to_update,
  SUM(CASE WHEN has_changes_since_last_sync THEN 1 ELSE 0 END) AS with_pending_changes,
  SUM(CASE WHEN is_multi_property THEN 1 ELSE 0 END) AS multi_property_cases,
  SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS with_features
FROM crm.sfdc_dbx.properties_to_update;
```

**Monitor Census:**
- Watch sync progress
- Check "Records Updated" counter
- Monitor error rate
- Review any errors immediately

**Expected Duration:** 30-60 minutes for ~7,980 properties

**After Sync Completes:**

```sql
-- Verify updates were applied
SELECT
  COUNT(*) AS properties_updated,
  MIN(last_modified_date) AS first_updated,
  MAX(last_modified_date) AS last_updated
FROM crm.salesforce.product_property
WHERE last_modified_date >= '<sync_start_time>'  -- Use actual start time
  AND last_modified_by_id = '<Census user ID>';  -- Census service account

-- Expected: ~7,980 properties
```

---

### Step 5.5: Post-Rollout Validation

**Immediate Validation (T+30 minutes):**

```sql
-- ============================================================================
-- POST-ROLLOUT VALIDATION QUERIES
-- ============================================================================

-- 1. Overall sync success metrics
SELECT
  'Total Properties in SF' AS metric,
  COUNT(*) AS count
FROM crm.salesforce.product_property
WHERE is_deleted = FALSE

UNION ALL

SELECT
  'Created in Last 2 Hours' AS metric,
  COUNT(*) AS count
FROM crm.salesforce.product_property
WHERE created_date >= CURRENT_TIMESTAMP() - INTERVAL 2 HOURS

UNION ALL

SELECT
  'Updated in Last 2 Hours' AS metric,
  COUNT(*) AS count
FROM crm.salesforce.product_property
WHERE last_modified_date >= CURRENT_TIMESTAMP() - INTERVAL 2 HOURS
  AND created_date < CURRENT_TIMESTAMP() - INTERVAL 2 HOURS;

-- 2. Feature sync accuracy
WITH rds_expected AS (
  SELECT
    sfdc_id,
    idv_enabled AS expected_idv,
    bank_linking_enabled AS expected_bank
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
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
  COUNT(*) AS total_compared,
  SUM(CASE WHEN rds.expected_idv = sf.actual_idv THEN 1 ELSE 0 END) AS idv_match_count,
  SUM(CASE WHEN rds.expected_bank = sf.actual_bank THEN 1 ELSE 0 END) AS bank_match_count,
  ROUND(100.0 * SUM(CASE WHEN rds.expected_idv = sf.actual_idv THEN 1 ELSE 0 END) / COUNT(*), 2) AS idv_match_pct,
  ROUND(100.0 * SUM(CASE WHEN rds.expected_bank = sf.actual_bank THEN 1 ELSE 0 END) / COUNT(*), 2) AS bank_match_pct
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id;

-- Expected: >99% match rate

-- 3. Multi-property aggregation check
SELECT
  active_property_count,
  COUNT(*) AS sfdc_id_count
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
GROUP BY active_property_count
ORDER BY active_property_count;

-- Verify multi-property cases are correctly represented in SF

-- 4. P1 Critical Properties (507 with features)
SELECT
  COUNT(DISTINCT pp.id) AS p1_properties_now_in_sf
FROM crm.salesforce.product_property pp
WHERE pp.is_deleted = FALSE
  AND (pp.idv_enabled_c = TRUE
    OR pp.bank_linking_enabled_c = TRUE
    OR pp.payroll_enabled_c = TRUE
    OR pp.income_insights_enabled_c = TRUE)
  AND pp.created_date >= '<rollout_start_time>';

-- Expected: ~507 (the P1 critical properties)

-- 5. Properties still missing from SF (should be minimal)
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

-- Expected: <50 (should be near-zero)
```

**Extended Validation (T+2 hours):**

```sql
-- Check Salesforce workflow completion
SELECT
  COUNT(*) AS total_staging_records,
  SUM(CASE WHEN sf_property_id_c IS NOT NULL THEN 1 ELSE 0 END) AS with_production_id,
  SUM(CASE WHEN sf_property_id_c IS NULL THEN 1 ELSE 0 END) AS awaiting_workflow,
  ROUND(100.0 * SUM(CASE WHEN sf_property_id_c IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS workflow_completion_pct
FROM crm.salesforce.product_property
WHERE is_deleted = FALSE
  AND created_date >= '<rollout_start_time>';

-- Expected: >80% with production ID (workflow has processed them)
-- If <50%: Investigate Salesforce workflow
```

---

### Step 5.6: 48-Hour Monitoring Period

**Monitoring Schedule:**

| Time | Check | Query | Threshold |
|------|-------|-------|-----------|
| T+4h | Workflow completion | `sf_property_id_c` populated | >90% |
| T+8h | Feature accuracy | Compare RDS vs SF | >99% |
| T+24h | Sync stability | Census error rate | <1% |
| T+48h | End-to-end health | Dashboard metrics | All green |

**Daily Monitoring Query (Run 2x per day):**

```sql
-- ============================================================================
-- DAILY HEALTH CHECK (Post-Rollout)
-- ============================================================================

SELECT * FROM crm.sfdc_dbx.sync_monitoring_dashboard
WHERE dashboard_refreshed_at >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR;

-- Review all metrics:
-- - Properties to Create: Should be <50
-- - Properties to Update: Should be stable (~7,980)
-- - Last 24h Successful Syncs: Should be >0
-- - Last 24h Failed Syncs: Should be 0 or very low
```

**Issue Escalation:**

| Severity | Condition | Action |
|----------|-----------|--------|
| **P0 - Critical** | Error rate >10% | Page on-call engineer immediately |
| **P1 - High** | Properties missing features | Investigate within 2 hours |
| **P2 - Medium** | Sync lag >1 hour | Investigate during business hours |
| **P3 - Low** | <1% errors | Review in weekly meeting |

---

### Step 5.7: Rollout Success Criteria

**Declare Rollout Successful if:**

- [ ] ✅ Sync A completed with <2% error rate
- [ ] ✅ Sync B completed with <2% error rate
- [ ] ✅ >1,000 properties created in product_property
- [ ] ✅ >7,500 properties updated in product_property
- [ ] ✅ Feature match rate >99%
- [ ] ✅ P1 critical properties (507) now visible in SF
- [ ] ✅ Multi-property cases aggregated correctly (spot-check 20)
- [ ] ✅ No data corruption detected
- [ ] ✅ Salesforce workflow processing normally (>80% completion)
- [ ] ✅ Census syncs running on schedule (15min/30min)
- [ ] ✅ Zero P0/P1 incidents during 48h monitoring
- [ ] ✅ Stakeholder sign-off obtained

**If Success Criteria Not Met:**
- Do NOT proceed to Phase 6
- Execute rollback procedure
- Investigate root cause
- Fix issues
- Re-run Phase 5

---

## ✅ PHASE 5 COMPLETION CHECKLIST

- [ ] Full Sync A executed successfully
- [ ] Full Sync B executed successfully
- [ ] All validation queries passed
- [ ] 48-hour monitoring completed
- [ ] Success criteria met
- [ ] No rollback required
- [ ] Stakeholder communication sent
- [ ] Incident report filed (even if no incidents)
- [ ] Lessons learned documented

---

## 📊 PHASE 6: MONITORING & DOCUMENTATION

**Duration:** 5 days
**Risk Level:** Low
**Prerequisites:** Phase 5 successful

**Goal:** Establish ongoing monitoring, documentation, and operational procedures

---

### Step 6.1: Create Operational Dashboard

**File:** `databricks_dashboards/property_sync_health_dashboard.json`

```sql
-- ============================================================================
-- OPERATIONAL DASHBOARD QUERIES
-- These queries power the Databricks/Tableau dashboard
-- ============================================================================

-- WIDGET 1: Sync Queue Sizes (Last 24 Hours Trend)
CREATE OR REPLACE VIEW crm.sfdc_dbx.sync_queue_sizes_24h AS
SELECT
  DATE_TRUNC('hour', measurement_time) AS hour,
  AVG(properties_to_create) AS avg_create_queue,
  AVG(properties_to_update) AS avg_update_queue,
  MAX(properties_to_create) AS max_create_queue,
  MAX(properties_to_update) AS max_update_queue
FROM (
  SELECT
    CURRENT_TIMESTAMP() AS measurement_time,
    (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create) AS properties_to_create,
    (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update) AS properties_to_update
  -- This would be logged to a table periodically
)
WHERE measurement_time >= CURRENT_TIMESTAMP() - INTERVAL 24 HOURS
GROUP BY DATE_TRUNC('hour', measurement_time)
ORDER BY hour DESC;

-- WIDGET 2: Feature Sync Accuracy (Real-Time)
CREATE OR REPLACE VIEW crm.sfdc_dbx.feature_sync_accuracy AS
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
  COUNT(*) AS total_properties,
  SUM(CASE WHEN rds.idv_enabled != sf.idv_enabled THEN 1 ELSE 0 END) AS mismatches
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id

UNION ALL

SELECT
  'Bank Linking' AS feature,
  ROUND(100.0 * SUM(CASE WHEN rds.bank_linking_enabled = sf.bank_linking_enabled THEN 1 ELSE 0 END) / COUNT(*), 2),
  COUNT(*),
  SUM(CASE WHEN rds.bank_linking_enabled != sf.bank_linking_enabled THEN 1 ELSE 0 END)
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id

UNION ALL

SELECT
  'Payroll' AS feature,
  ROUND(100.0 * SUM(CASE WHEN rds.payroll_enabled = sf.payroll_enabled THEN 1 ELSE 0 END) / COUNT(*), 2),
  COUNT(*),
  SUM(CASE WHEN rds.payroll_enabled != sf.payroll_enabled THEN 1 ELSE 0 END)
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id

UNION ALL

SELECT
  'Income Insights' AS feature,
  ROUND(100.0 * SUM(CASE WHEN rds.income_insights_enabled = sf.income_insights_enabled THEN 1 ELSE 0 END) / COUNT(*), 2),
  COUNT(*),
  SUM(CASE WHEN rds.income_insights_enabled != sf.income_insights_enabled THEN 1 ELSE 0 END)
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id;

-- TARGET: All features >99% accuracy

-- WIDGET 3: Multi-Property Aggregation Stats
CREATE OR REPLACE VIEW crm.sfdc_dbx.multi_property_stats AS
SELECT
  active_property_count AS num_rds_properties,
  COUNT(*) AS num_sfdc_ids,
  SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) AS with_features,
  ROUND(100.0 * SUM(CASE WHEN has_any_features_enabled THEN 1 ELSE 0 END) / COUNT(*), 2) AS features_pct
FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
GROUP BY active_property_count
ORDER BY active_property_count;

-- WIDGET 4: Census Sync Health (Last 7 Days)
CREATE OR REPLACE VIEW crm.sfdc_dbx.census_sync_health_7d AS
SELECT
  DATE(sync_timestamp) AS sync_date,
  sync_operation,
  COUNT(*) AS total_syncs,
  SUM(CASE WHEN sync_status = 'SUCCESS' THEN 1 ELSE 0 END) AS successful,
  SUM(CASE WHEN sync_status = 'FAILED' THEN 1 ELSE 0 END) AS failed,
  ROUND(100.0 * SUM(CASE WHEN sync_status = 'SUCCESS' THEN 1 ELSE 0 END) / COUNT(*), 2) AS success_rate_pct
FROM crm.sfdc_dbx.property_sync_audit_log
WHERE sync_timestamp >= CURRENT_TIMESTAMP() - INTERVAL 7 DAYS
GROUP BY DATE(sync_timestamp), sync_operation
ORDER BY sync_date DESC, sync_operation;

-- WIDGET 5: Properties Missing from Salesforce (Alert if >100)
CREATE OR REPLACE VIEW crm.sfdc_dbx.properties_missing_from_sf AS
SELECT
  COUNT(*) AS missing_property_count,
  SUM(CASE WHEN idv_enabled OR bank_linking_enabled OR payroll_enabled
           OR income_insights_enabled THEN 1 ELSE 0 END) AS with_features_missing,
  CASE
    WHEN COUNT(*) > 100 THEN '🔴 CRITICAL: >100 properties missing'
    WHEN COUNT(*) > 50 THEN '🟡 WARNING: >50 properties missing'
    ELSE '🟢 OK: <50 properties missing'
  END AS status
FROM crm.sfdc_dbx.rds_properties_enriched rds
WHERE rds.property_status = 'ACTIVE'
  AND rds.has_valid_sfdc_id = 1
  AND NOT EXISTS (
    SELECT 1
    FROM crm.salesforce.product_property pp
    WHERE CAST(rds.rds_property_id AS STRING) = pp.snappt_property_id_c
      AND pp.is_deleted = FALSE
  );
```

---

### Step 6.2: Set Up Automated Alerts

**Alert Configuration:**

| Alert Name | Trigger Condition | Severity | Notification Channel |
|------------|-------------------|----------|---------------------|
| High Create Queue | properties_to_create > 200 | P2 | Slack: #data-alerts |
| Sync Failure Spike | Failed syncs > 5% in 1 hour | P1 | PagerDuty + Slack |
| Feature Mismatch High | Accuracy < 95% | P2 | Slack: #data-alerts |
| Properties Missing | Missing count > 100 | P1 | Email + Slack |
| Census Sync Down | No syncs in last 2 hours | P0 | PagerDuty |

**Alert Query Examples:**

```sql
-- Alert 1: High Create Queue
SELECT
  COUNT(*) AS queue_size,
  CASE WHEN COUNT(*) > 200 THEN TRUE ELSE FALSE END AS alert_triggered
FROM crm.sfdc_dbx.properties_to_create;

-- Alert 2: Sync Failure Spike
SELECT
  COUNT(*) AS failed_syncs_last_hour,
  ROUND(100.0 * COUNT(*) / (
    SELECT COUNT(*)
    FROM crm.sfdc_dbx.property_sync_audit_log
    WHERE sync_timestamp >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
  ), 2) AS failure_rate_pct,
  CASE
    WHEN ROUND(100.0 * COUNT(*) / (
      SELECT COUNT(*)
      FROM crm.sfdc_dbx.property_sync_audit_log
      WHERE sync_timestamp >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
    ), 2) > 5.0
    THEN TRUE
    ELSE FALSE
  END AS alert_triggered
FROM crm.sfdc_dbx.property_sync_audit_log
WHERE sync_timestamp >= CURRENT_TIMESTAMP() - INTERVAL 1 HOUR
  AND sync_status = 'FAILED';
```

---

### Step 6.3: Create Operational Runbooks

**File:** `docs/RUNBOOK_PROPERTY_SYNC.md`

```markdown
# Property Sync Operational Runbook

## Daily Operations

### Daily Health Check (5 minutes)
Run at 9am daily:

1. Open Databricks dashboard: [link]
2. Check all 5 widgets:
   - Queue sizes: <50 for create, stable for update
   - Feature accuracy: >99%
   - Multi-property stats: Review any anomalies
   - Census health: 100% success rate
   - Missing properties: <50

3. If all green → No action needed
4. If yellow/red → Follow troubleshooting guide below

---

## Troubleshooting Guide

### Issue 1: High Create Queue (>200 properties)

**Symptoms:**
- properties_to_create count increasing
- New RDS properties not appearing in SF

**Root Causes:**
- Census Sync A not running (paused or errored)
- Salesforce API limits exceeded
- View logic changed/broken

**Resolution:**
1. Check Census Sync A status
   - Is it paused? → Resume
   - Is it erroring? → Check error logs
   - Last run time? → If >1 hour, investigate

2. Check Salesforce API limits
   - Login to Salesforce
   - Setup → System Overview → API Usage
   - If >80% → Wait or request limit increase

3. Validate view logic
   ```sql
   SELECT * FROM crm.sfdc_dbx.properties_to_create LIMIT 10;
   ```
   - If query errors → View is broken, fix definition
   - If returns results → View is OK, issue elsewhere

4. Manual sync trigger (if needed)
   - Go to Census workspace
   - Trigger Sync A manually
   - Monitor for 10 minutes

---

### Issue 2: Feature Accuracy <95%

**Symptoms:**
- Dashboard shows feature mismatch %age high
- Customer reports features missing in SF

**Root Causes:**
- Aggregation logic not working
- Census Sync B not running
- Salesforce workflow overwriting data

**Resolution:**
1. Identify which features are mismatched
   ```sql
   -- Run feature_sync_accuracy view
   SELECT * FROM crm.sfdc_dbx.feature_sync_accuracy;
   ```

2. Check sample mismatched properties
   ```sql
   -- Find specific properties with mismatches
   WITH rds_expected AS (...)  -- Full query from view
   SELECT * FROM ... WHERE rds.idv_enabled != sf.idv_enabled LIMIT 20;
   ```

3. Determine pattern
   - All mismatches in same direction (RDS TRUE, SF FALSE)? → Sync B not running
   - Random mismatches? → Data integrity issue
   - Specific companies? → Company-specific issue

4. Trigger Sync B manually
   - Go to Census Sync B
   - Click "Trigger Now"
   - Wait 30 min, re-check accuracy

5. If still mismatched → Escalate to engineering

---

### Issue 3: Census Sync Failing

**Symptoms:**
- Error notifications from Census
- Failed sync count increasing

**Root Causes:**
- Salesforce field validation failing
- Data type mismatches
- Required fields missing
- API authentication expired

**Resolution:**
1. Review error logs in Census
   - Navigate to sync → Runs → Failed runs
   - Read error messages

2. Common errors and fixes:
   - "Required field missing" → Check field mappings
   - "Invalid field value" → Check data types in view
   - "Insufficient access rights" → Check SF permissions
   - "API limit exceeded" → Wait or increase limits

3. Fix data issues in view
   ```sql
   -- Example: Fix NULL required fields
   CREATE OR REPLACE VIEW ... AS
   SELECT
     COALESCE(field, 'DEFAULT') AS field,
     ...
   ```

4. Re-run sync after fix

---

## Weekly Operations

### Weekly Review (30 minutes)
Run every Monday:

1. Review week-over-week trends
2. Check for gradual degradation
3. Review audit logs for patterns
4. Update documentation if needed

**Query:**
```sql
SELECT * FROM crm.sfdc_dbx.census_sync_health_7d;
```

---

## Monthly Operations

### Monthly Architecture Review (2 hours)
Run first Monday of month:

1. Review aggregation rules (still appropriate?)
2. Check for new edge cases
3. Assess performance (sync times increasing?)
4. Review stakeholder feedback
5. Plan improvements

---

## Emergency Procedures

### Emergency Rollback

**When to use:** Critical data corruption detected

**Steps:**
1. **IMMEDIATELY pause both Census syncs**
2. Assess scope of damage
   ```sql
   -- Find recently modified records
   SELECT COUNT(*)
   FROM crm.salesforce.product_property
   WHERE last_modified_date >= '<incident_start_time>'
     AND last_modified_by_id = '<Census user ID>';
   ```
3. If <100 records affected → Manual correction
4. If >100 records affected → Restore from backup
5. Investigate root cause
6. Fix before resuming syncs

---

## Contacts

- **On-Call Engineer:** [Name] - [Email/Slack/Phone]
- **Data Team Lead:** [Name] - [Email]
- **Census Support:** support@getcensus.com
- **Salesforce Admin:** [Name] - [Email]

---

## Related Documentation

- Architecture: IMPLEMENTATION_PLAN_NEW_SYNC_ARCHITECTURE.md
- Business Rules: WORKFLOW_REDESIGN_QUESTIONS.md (answered)
- Historical Context: RDS_SALESFORCE_DISCOVERY_REPORT.md
```

---

### Step 6.4: Update Documentation

**Files to Create/Update:**

1. **Architecture Documentation**
   - Update README.md with new architecture diagram
   - Document all views and their purposes
   - Explain business rules clearly

2. **Business Rules Documentation**
   - Answer all 9 questions in WORKFLOW_REDESIGN_QUESTIONS.md
   - Document aggregation logic with examples
   - Include Park Kennedy case study

3. **Operational Documentation**
   - Runbook (created above)
   - Alert definitions
   - Dashboard guide
   - On-call procedures

4. **Historical Documentation**
   - Session notes with "COMPLETED" status
   - Lessons learned
   - Future improvements

---

### Step 6.5: Knowledge Transfer

**Training Session Agenda (1 hour):**

1. **Overview (10 min)**
   - Why we redesigned the architecture
   - What problems we solved

2. **Architecture Walkthrough (20 min)**
   - Show Databricks views
   - Explain aggregation logic
   - Demo Census syncs

3. **Dashboard Demo (15 min)**
   - Walk through all widgets
   - Explain thresholds and alerts
   - Show how to investigate issues

4. **Hands-On Practice (10 min)**
   - Attendees run health check queries
   - Practice troubleshooting scenario

5. **Q&A (5 min)**

**Attendees:**
- Data engineers (all)
- On-call rotation (all)
- Data analysts (optional)
- Sales ops (optional, for context)

---

## ✅ PHASE 6 COMPLETION CHECKLIST

- [ ] Operational dashboard created and published
- [ ] All 5 dashboard widgets working
- [ ] Automated alerts configured and tested
- [ ] Runbook written and reviewed
- [ ] All documentation updated
- [ ] Knowledge transfer session completed
- [ ] Team trained on new architecture
- [ ] On-call rotation updated with runbook
- [ ] Success metrics published to stakeholders
- [ ] Post-mortem completed (if any issues)
- [ ] Future improvements documented

---

## 🎉 PROJECT COMPLETION

**Congratulations!** The new RDS → Salesforce sync architecture is fully implemented and operational.

### Final Success Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Properties in Salesforce | 65% | 95%+ | +30% |
| Feature sync accuracy | 90.1% | 99%+ | +9% |
| Properties missing from SF | 1,081 | <50 | -95% |
| P1 critical properties synced | 0 | 507 | ✓ Complete |
| Multi-property cases handled | 0 | 2,410 | ✓ Complete |
| Sync reliability | ~85% | 99%+ | +14% |

### What We Accomplished

1. ✅ Eliminated chicken-and-egg problem with production IDs
2. ✅ Handled many-to-1 relationships with aggregation layer
3. ✅ Separated create vs update logic cleanly
4. ✅ Provided clear business rules for feature aggregation
5. ✅ Enabled full auditability and monitoring
6. ✅ Resolved 507 P1 critical missing properties
7. ✅ Fixed 799 feature mismatches
8. ✅ Unblocked 2,410 properties with duplicate SFDC IDs

### Long-Term Benefits

- **Scalability:** Architecture handles growth gracefully
- **Maintainability:** Clear, documented business logic
- **Reliability:** 99%+ sync accuracy
- **Auditability:** Full audit trail of all syncs
- **Flexibility:** Easy to modify aggregation rules

---

## 📈 CONTINUOUS IMPROVEMENT

**Quarterly Reviews:**

Schedule quarterly reviews to assess:
1. Are aggregation rules still appropriate?
2. Any new edge cases discovered?
3. Performance optimization opportunities?
4. Stakeholder feedback and feature requests

**Future Enhancements (Backlog):**

1. **Real-time sync:** Reduce sync frequency to 5 minutes
2. **Change data capture:** Only sync changed records
3. **Bi-directional sync:** Sync changes from SF back to RDS
4. **Advanced aggregation:** Weighted features, priority rules
5. **Self-healing:** Automatic recovery from common errors

---

**End of Implementation Plan**

**Questions?** Contact Data Team or refer to runbook.
