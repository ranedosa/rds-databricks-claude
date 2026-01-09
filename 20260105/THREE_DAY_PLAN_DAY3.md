# THREE-DAY PLAN: DAY 3 - FULL ROLLOUT & MONITORING

**Continuation of:** THREE_DAY_IMPLEMENTATION_PLAN.md

---

## 📋 DAY 3: FULL ROLLOUT & MONITORING

**Duration:** 6-8 hours
**Goal:** Execute full syncs (1,081 + 7,980) and validate
**Risk:** Medium-High (large-scale production writes)

### Pre-Flight Checklist

- [ ] Day 2 pilot completed successfully
- [ ] All pilot checkpoints passed
- [ ] Stakeholder approval obtained for full rollout
- [ ] Calendar clear for 6-8 hours
- [ ] Rollout window scheduled (recommend: Tuesday-Thursday, 10am-2pm)
- [ ] On-call contact identified (you or teammate)
- [ ] Salesforce status page checked: https://status.salesforce.com (all green)

---

### **MORNING (9:00 AM - 12:00 PM): Pre-Rollout & Sync A**

#### 9:00-9:30: Final Pre-Rollout Checks

```sql
-- ============================================================================
-- PRE-ROLLOUT VALIDATION
-- ============================================================================

-- Check 1: View health
SELECT * FROM crm.sfdc_dbx.sync_health_dashboard;
-- Expected:
-- Properties to Create: ~1,031 (50 pilot already created)
-- Properties to Update: ~7,930 (50 pilot already updated)
-- Multi-Property Cases: ~2,410

-- Check 2: Census sync health (from yesterday)
-- Verify pilot syncs completed successfully
-- Check error logs - should be minimal

-- Check 3: Salesforce API limits
-- Login to SF → Setup → System Overview → API Usage
-- Should have plenty of quota available (>50%)

-- Check 4: Databricks cluster health
-- Ensure cluster is running and responsive

-- Check 5: Take baseline snapshot
CREATE OR REPLACE TABLE crm.sfdc_dbx.rollout_snapshot_day3 AS
SELECT
  'Before Full Rollout' AS snapshot_stage,
  CURRENT_TIMESTAMP() AS snapshot_time,
  (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create) AS to_create,
  (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update) AS to_update,
  (SELECT COUNT(*) FROM crm.salesforce.product_property WHERE is_deleted = FALSE) AS total_in_sf;

SELECT * FROM crm.sfdc_dbx.rollout_snapshot_day3;
```

**✅ Pre-Rollout Checkpoint:**
- [ ] All views healthy
- [ ] Salesforce status green
- [ ] API quota sufficient
- [ ] Databricks responsive
- [ ] Baseline snapshot saved

**GO/NO-GO Decision:**
- ✅ GO if all checks pass
- ❌ NO-GO if any critical issues
  - Salesforce outage
  - API limits near exhaustion
  - Databricks cluster issues
  - Census sync errors from yesterday unresolved

---

#### 9:30-9:45: Prepare Census Sync A for Full Rollout

**Step 1: Remove Pilot Filter**

- Go to Census workspace → Sync A
- Navigate to Filters section
- **Remove** the `WHERE rds_property_id IN (...)` filter
- **Verify:** Source should now show ~1,031 properties (full queue minus pilot)
- **Save** configuration

**Step 2: Final verification**

```sql
-- Verify how many will sync
SELECT COUNT(*) as will_sync
FROM crm.sfdc_dbx.properties_to_create;
-- Expected: ~1,031 (1,081 original - 50 pilot)

-- Double-check no pilot properties in queue (already created)
SELECT COUNT(*) as pilot_already_created
FROM crm.sfdc_dbx.properties_to_create
WHERE rds_property_id IN (<your 50 pilot create IDs>);
-- Expected: 0 (they're not in queue anymore)
```

---

#### 9:45-10:00: Stakeholder Communication

```bash
# Send notification

Subject: Property Sync Full Rollout Starting Now

Team,

Beginning full rollout of property sync at [TIME].

What's happening:
- Sync A (create): ~1,031 properties → Salesforce
- Expected duration: 20-30 minutes
- Then Sync B (update): ~7,930 properties
- Expected duration: 60-90 minutes

Monitoring:
- Will send updates every hour
- Dashboard: [link to sync_health_dashboard]

Status: STARTED - Sync A in progress

[Your name]
```

---

#### 10:00-10:05: TRIGGER SYNC A (Full Rollout - CREATE)

**⚠️ POINT OF NO RETURN**

- Go to Census → Sync A
- **Final check:** Verify filter is removed
- **Final check:** Verify sync mode is "Create Only"
- Click **"Trigger Sync Now"**
- **Record exact start time:** _______________

**Expected duration:** 20-30 minutes for ~1,031 properties

---

#### 10:05-10:35: Monitor Sync A (30 minutes)

**Every 5 minutes, check:**

1. **Census dashboard:**
   - Records processed: should climb steadily
   - Error count: should stay low (<3%)
   - Current rate: properties/minute

2. **Databricks query:**
```sql
-- Run every 5 minutes
SELECT COUNT(*) as remaining_to_create
FROM crm.sfdc_dbx.properties_to_create;

-- Should decrease as properties get created
-- Log results:
-- 10:05 AM: [COUNT]
-- 10:10 AM: [COUNT]
-- 10:15 AM: [COUNT]
-- etc.
```

3. **Census logs:**
   - Watch for error patterns
   - Common errors:
     - "Required field missing" → Data issue
     - "API limit exceeded" → Slow down or wait
     - "Duplicate value" → Shouldn't happen (different sync key)

**If error rate >5%:**
- Don't panic, but investigate immediately
- Check Census error details
- Identify pattern (same field? same company?)
- Document but don't pause unless >10% error rate

**If error rate >10%:**
- **PAUSE SYNC** immediately
- Investigate root cause
- Check Salesforce validation rules
- Check field mappings
- Fix issue
- Resume or restart sync

---

#### 10:35-11:00: Validate Sync A Completion

```sql
-- ============================================================================
-- SYNC A VALIDATION
-- ============================================================================

-- Check 1: Census final statistics
-- Go to Census → Sync A → Latest Run
-- Record:
-- - Created: _____
-- - Errors: _____
-- - Error Rate: _____%

-- Check 2: Final queue size
SELECT COUNT(*) as remaining_to_create
FROM crm.sfdc_dbx.properties_to_create;
-- Target: <100 (allowing for errors and edge cases)
-- If >200: Investigate why so many didn't sync

-- Check 3: Properties created in Salesforce
SELECT COUNT(*) as created_today
FROM crm.salesforce.product_property
WHERE created_date >= '<sync_a_start_time>'
  AND is_deleted = FALSE;
-- Expected: ~1,000+ (close to queue size)

-- Check 4: P1 Critical properties (507 with features)
SELECT COUNT(*) as p1_created
FROM crm.salesforce.product_property
WHERE created_date >= '<sync_a_start_time>'
  AND is_deleted = FALSE
  AND (idv_enabled_c = TRUE
       OR bank_linking_enabled_c = TRUE
       OR payroll_enabled_c = TRUE
       OR income_insights_enabled_c = TRUE);
-- Expected: ~450-500 (the P1 critical properties)

-- Check 5: Spot-check 20 random created properties
SELECT
  snappt_property_id_c,
  name,
  city,
  state,
  idv_enabled_c,
  bank_linking_enabled_c,
  company_id_c,
  created_date
FROM crm.salesforce.product_property
WHERE created_date >= '<sync_a_start_time>'
  AND is_deleted = FALSE
ORDER BY RANDOM()
LIMIT 20;

-- Manually review: Do these look correct?

-- Check 6: Error analysis (if any)
-- Review Census error logs
-- Document common error patterns
```

**✅ Sync A Completion Checkpoint:**
- [ ] ~1,000+ properties created
- [ ] Remaining queue <100
- [ ] Error rate <5%
- [ ] P1 properties created (~450-500)
- [ ] Spot-check looks good
- [ ] No critical errors

**If checkpoint fails:**
- Document issues
- If error rate >10%: Fix before Sync B
- If <1,000 created: Investigate missing properties
- Don't proceed to Sync B if critical issues

**Update stakeholders:**
```
Status Update - 11:00 AM

Sync A Complete:
✓ [X] properties created
✓ Error rate: [X]%
✓ P1 critical properties now in Salesforce

Next: Sync B starting at 11:30 AM (30min break)
```

---

#### 11:00-11:30: Break & Prepare for Sync B

**Take a 30-minute break:**
- Stretch, coffee, snack
- Review Sync A results
- Check Salesforce status
- Prepare for Sync B

**During break, prepare Sync B:**

```sql
-- Verify Sync B queue is correct
SELECT COUNT(*) as will_update
FROM crm.sfdc_dbx.properties_to_update;
-- Expected: ~7,930 (7,980 original - 50 pilot)

-- Check multi-property cases
SELECT COUNT(*) as multi_property_cases
FROM crm.sfdc_dbx.properties_to_update
WHERE is_multi_property = TRUE;
-- Expected: ~2,410

-- Sample properties to update
SELECT
  snappt_property_id_c,
  sfdc_id,
  property_name,
  active_property_count,
  is_multi_property,
  idv_enabled,
  bank_linking_enabled
FROM crm.sfdc_dbx.properties_to_update
ORDER BY RANDOM()
LIMIT 10;
```

---

### **MIDDAY (11:30 AM - 2:00 PM): Sync B Execution**

#### 11:30-11:40: Prepare Census Sync B for Full Rollout

**Step 1: Remove pilot filter**

- Go to Census workspace → Sync B
- Navigate to Filters section
- **Remove** the `WHERE snappt_property_id_c IN (...)` filter
- **Verify:** Source should show ~7,930 properties
- **Save** configuration

**Step 2: Final checks**

```sql
-- Verify count
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update;
-- Expected: ~7,930

-- Capture baseline (BEFORE update)
CREATE OR REPLACE TEMP VIEW sync_b_baseline AS
SELECT
  snappt_property_id_c,
  sf_property_id_c,
  name,
  idv_enabled_c,
  bank_linking_enabled_c,
  active_property_count_c,
  is_multi_property_c,
  last_modified_date
FROM crm.salesforce.product_property
WHERE is_deleted = FALSE
  AND sf_property_id_c IN (
    SELECT sfdc_id FROM crm.sfdc_dbx.properties_to_update
  );

-- Count captured
SELECT COUNT(*) as baseline_captured FROM sync_b_baseline;
-- Should be ~7,930
```

---

#### 11:40-11:45: TRIGGER SYNC B (Full Rollout - UPDATE)

**⚠️ CRITICAL SYNC - Updates production data**

- Go to Census → Sync B
- **Final check:** Filter removed
- **Final check:** Sync mode is "Update Only"
- **Final check:** Update mode is "Replace" (not Merge)
- Click **"Trigger Sync Now"**
- **Record exact start time:** _______________

**Expected duration:** 60-90 minutes for ~7,930 properties

---

#### 11:45-1:15 PM: Monitor Sync B (90 minutes)

**Every 10 minutes, check:**

1. **Census dashboard:**
   - Records updated: should climb steadily
   - Error count: monitor closely
   - Estimate completion time

2. **Databricks query:**
```sql
-- Run every 10 minutes
SELECT
  COUNT(*) as recently_updated,
  MIN(sf_last_updated_at) as oldest_update,
  MAX(sf_last_updated_at) as newest_update
FROM crm.sfdc_dbx.properties_to_update
WHERE has_changes_since_last_sync = TRUE;

-- Also check SF directly
SELECT COUNT(*) as updated_so_far
FROM crm.salesforce.product_property
WHERE last_modified_date >= '<sync_b_start_time>'
  AND is_deleted = FALSE;

-- Log progress:
-- 11:45 AM: [COUNT]
-- 11:55 AM: [COUNT]
-- 12:05 PM: [COUNT]
-- etc.
```

3. **Sample validation (every 30 min):**
```sql
-- Check 10 random updated properties
SELECT
  pp.snappt_property_id_c,
  pp.name,
  pp.active_property_count_c,
  pp.is_multi_property_c,
  pp.idv_enabled_c,
  pp.last_modified_date,
  ptu.idv_enabled AS expected_idv
FROM crm.salesforce.product_property pp
INNER JOIN crm.sfdc_dbx.properties_to_update ptu
  ON pp.snappt_property_id_c = ptu.snappt_property_id_c
WHERE pp.last_modified_date >= '<sync_b_start_time>'
  AND pp.is_deleted = FALSE
ORDER BY RANDOM()
LIMIT 10;

-- Verify: idv_enabled_c should match expected_idv
```

**If error rate >5%:**
- Investigate immediately
- Check error patterns
- Review Update mode setting (should be "Replace")
- Document errors

**If error rate >10%:**
- Consider pausing to investigate
- Check if errors are concentrated (one company? one field?)
- May need to fix and re-trigger for failed properties

---

#### 1:15-2:00 PM: Validate Sync B Completion

```sql
-- ============================================================================
-- SYNC B VALIDATION
-- ============================================================================

-- Check 1: Census final statistics
-- Record:
-- - Updated: _____
-- - Errors: _____
-- - Skipped: _____
-- - Error Rate: _____%

-- Check 2: Properties updated
SELECT COUNT(*) as updated_today
FROM crm.salesforce.product_property
WHERE last_modified_date >= '<sync_b_start_time>'
  AND is_deleted = FALSE;
-- Expected: ~7,500-7,900 (close to queue size)

-- Check 3: Park Kennedy validation
SELECT
  snappt_property_id_c,
  sf_property_id_c,
  name,
  active_property_count_c,
  is_multi_property_c,
  idv_enabled_c,
  bank_linking_enabled_c,
  payroll_enabled_c,
  income_insights_enabled_c,
  last_modified_date
FROM crm.salesforce.product_property
WHERE sf_property_id_c = 'a01Dn00000HHUanIAH';

-- Expected:
-- active_property_count_c: 2 (or correct from aggregation)
-- is_multi_property_c: TRUE
-- Features: Should all be TRUE (from ACTIVE property)
-- last_modified_date: Today

-- Check 4: Feature sync accuracy (sample 1000)
WITH rds_expected AS (
  SELECT
    sfdc_id,
    idv_enabled,
    bank_linking_enabled,
    payroll_enabled
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
  WHERE sfdc_id IN (
    SELECT sf_property_id_c
    FROM crm.salesforce.product_property
    WHERE last_modified_date >= '<sync_b_start_time>'
      AND is_deleted = FALSE
    LIMIT 1000
  )
),
sf_actual AS (
  SELECT
    sf_property_id_c AS sfdc_id,
    idv_enabled_c AS idv_enabled,
    bank_linking_enabled_c AS bank_linking_enabled,
    payroll_enabled_c AS payroll_enabled
  FROM crm.salesforce.product_property
  WHERE last_modified_date >= '<sync_b_start_time>'
    AND is_deleted = FALSE
    AND sf_property_id_c IS NOT NULL
  LIMIT 1000
)
SELECT
  'IDV' AS feature,
  COUNT(*) AS sample_size,
  SUM(CASE WHEN rds.idv_enabled = sf.idv_enabled THEN 1 ELSE 0 END) AS matches,
  ROUND(100.0 * SUM(CASE WHEN rds.idv_enabled = sf.idv_enabled THEN 1 ELSE 0 END) / COUNT(*), 2) AS accuracy_pct
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id

UNION ALL

SELECT
  'Bank Linking' AS feature,
  COUNT(*),
  SUM(CASE WHEN rds.bank_linking_enabled = sf.bank_linking_enabled THEN 1 ELSE 0 END),
  ROUND(100.0 * SUM(CASE WHEN rds.bank_linking_enabled = sf.bank_linking_enabled THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id

UNION ALL

SELECT
  'Payroll' AS feature,
  COUNT(*),
  SUM(CASE WHEN rds.payroll_enabled = sf.payroll_enabled THEN 1 ELSE 0 END),
  ROUND(100.0 * SUM(CASE WHEN rds.payroll_enabled = sf.payroll_enabled THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id;

-- Target: All features >97% accuracy

-- Check 5: Multi-property cases
SELECT COUNT(*) as multi_property_updated
FROM crm.salesforce.product_property
WHERE is_multi_property_c = TRUE
  AND last_modified_date >= '<sync_b_start_time>'
  AND is_deleted = FALSE;
-- Expected: ~2,400 (the blocked properties)

-- Sample multi-property cases
SELECT
  sf_property_id_c,
  name,
  active_property_count_c,
  is_multi_property_c,
  idv_enabled_c,
  bank_linking_enabled_c
FROM crm.salesforce.product_property
WHERE is_multi_property_c = TRUE
  AND last_modified_date >= '<sync_b_start_time>'
ORDER BY active_property_count_c DESC
LIMIT 20;

-- Manually review: Do these look correct?
```

**✅ Sync B Completion Checkpoint:**
- [ ] ~7,500+ properties updated
- [ ] Error rate <5%
- [ ] Park Kennedy correct
- [ ] Feature accuracy >97%
- [ ] ~2,400 multi-property cases updated
- [ ] No critical data corruption

**Update stakeholders:**
```
Status Update - 2:00 PM

Sync B Complete:
✓ [X] properties updated
✓ Error rate: [X]%
✓ Feature accuracy: [X]%
✓ Multi-property aggregation working

Both syncs complete. Now validating overall results.
```

---

### **AFTERNOON (2:00 PM - 5:00 PM): Comprehensive Validation**

#### 2:00-3:00: Overall Success Metrics

```sql
-- ============================================================================
-- OVERALL SUCCESS METRICS
-- ============================================================================

-- Metric 1: Properties now in Salesforce
WITH baseline AS (
  SELECT count AS before_count
  FROM crm.sfdc_dbx.rollout_snapshot_day3
  WHERE snapshot_stage = 'Before Full Rollout'
),
current AS (
  SELECT COUNT(*) AS after_count
  FROM crm.salesforce.product_property
  WHERE is_deleted = FALSE
)
SELECT
  b.before_count,
  c.after_count,
  c.after_count - b.before_count AS increase,
  ROUND(100.0 * (c.after_count - b.before_count) / 1031.0, 2) AS pct_of_expected
FROM baseline b, current c;
-- Expected: Increase of ~1,000 (from Sync A creates)

-- Metric 2: Properties still missing
SELECT COUNT(*) AS still_missing_from_sf
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

-- Metric 3: P1 Critical properties now visible
SELECT
  COUNT(*) AS p1_total_in_sf,
  SUM(CASE WHEN created_date >= '<today>' THEN 1 ELSE 0 END) AS p1_created_today
FROM crm.salesforce.product_property
WHERE is_deleted = FALSE
  AND (idv_enabled_c = TRUE
       OR bank_linking_enabled_c = TRUE
       OR payroll_enabled_c = TRUE
       OR income_insights_enabled_c = TRUE);
-- Expected: p1_created_today ~500 (the critical properties)

-- Metric 4: Feature sync accuracy (FULL dataset)
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
  'Overall Feature Accuracy' AS metric,
  COUNT(*) AS total_properties,
  ROUND(100.0 * SUM(CASE WHEN rds.idv_enabled = sf.idv_enabled THEN 1 ELSE 0 END) / COUNT(*), 2) AS idv_accuracy,
  ROUND(100.0 * SUM(CASE WHEN rds.bank_linking_enabled = sf.bank_linking_enabled THEN 1 ELSE 0 END) / COUNT(*), 2) AS bank_accuracy,
  ROUND(100.0 * SUM(CASE WHEN rds.payroll_enabled = sf.payroll_enabled THEN 1 ELSE 0 END) / COUNT(*), 2) AS payroll_accuracy,
  ROUND(100.0 * SUM(CASE WHEN rds.income_insights_enabled = sf.income_insights_enabled THEN 1 ELSE 0 END) / COUNT(*), 2) AS income_accuracy
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id;
-- Target: All features >97%

-- Metric 5: Multi-property cases summary
SELECT
  COUNT(*) AS total_multi_property_sfdc_ids,
  AVG(active_property_count_c) AS avg_properties_per_sfdc_id,
  MAX(active_property_count_c) AS max_properties_per_sfdc_id,
  SUM(CASE WHEN idv_enabled_c OR bank_linking_enabled_c OR payroll_enabled_c
           OR income_insights_enabled_c THEN 1 ELSE 0 END) AS with_features
FROM crm.salesforce.product_property
WHERE is_multi_property_c = TRUE
  AND is_deleted = FALSE;
-- Expected: ~2,410 multi-property cases

-- Metric 6: Queue sizes (should be near-zero)
SELECT * FROM crm.sfdc_dbx.sync_health_dashboard;
-- Expected:
-- Properties to Create: <50
-- Properties to Update: ~7,930 (stable, some may have changes)
-- Multi-Property Cases: ~2,410 (should match Metric 5)
```

**Document all metrics - these are your success proof**

---

#### 3:00-3:30: Issue Investigation & Resolution

**If properties still missing (>100):**

```sql
-- Identify which properties didn't sync
SELECT
  rds.rds_property_id,
  rds.property_name,
  rds.company_id,
  rds.status,
  rds.idv_enabled,
  rds.bank_linking_enabled
FROM crm.sfdc_dbx.rds_properties_enriched rds
WHERE rds.property_status = 'ACTIVE'
  AND rds.has_valid_sfdc_id = 1
  AND NOT EXISTS (
    SELECT 1
    FROM crm.salesforce.product_property pp
    WHERE CAST(rds.rds_property_id AS STRING) = pp.snappt_property_id_c
      AND pp.is_deleted = FALSE
  )
LIMIT 50;

-- Check Census error logs for these specific IDs
-- Common causes:
-- - Required field missing (company_id NULL?)
-- - Data type mismatch
-- - Salesforce validation rule blocked
-- - API limit exceeded (less likely)

-- Fix and re-trigger Sync A for failed properties only
-- Add filter: WHERE rds_property_id IN (<failed IDs>)
```

**If feature accuracy <95%:**

```sql
-- Find specific mismatches
WITH rds_expected AS (
  SELECT sfdc_id, idv_enabled, bank_linking_enabled
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
),
sf_actual AS (
  SELECT sf_property_id_c AS sfdc_id, idv_enabled_c AS idv_enabled, bank_linking_enabled_c AS bank_linking_enabled
  FROM crm.salesforce.product_property
  WHERE is_deleted = FALSE AND sf_property_id_c IS NOT NULL
)
SELECT
  rds.sfdc_id,
  rds.idv_enabled AS rds_idv,
  sf.idv_enabled AS sf_idv,
  rds.bank_linking_enabled AS rds_bank,
  sf.bank_linking_enabled AS sf_bank
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id
WHERE rds.idv_enabled != sf.idv_enabled
   OR rds.bank_linking_enabled != sf.bank_linking_enabled
LIMIT 50;

-- Check pattern:
-- - All TRUE in RDS but FALSE in SF? → Sync B didn't run or wrong mode
-- - Random mismatches? → Data integrity issue
-- - Specific SFDC IDs? → Salesforce workflow overwriting?

-- May need to re-trigger Sync B with correct settings
```

**Document all issues and resolutions**

---

#### 3:30-4:00: Enable Automated Census Schedules

**Now that full rollout is complete, enable ongoing syncs:**

**Sync A Schedule:**
- Go to Census → Sync A → Schedule
- Change from "Manual" to **"Every 15 minutes"**
- Save
- **Reasoning:** New properties should sync quickly (15min lag max)

**Sync B Schedule:**
- Go to Census → Sync B → Schedule
- Change from "Manual" to **"Every 30 minutes"**
- Save
- **Reasoning:** Updates less urgent, 30min reduces API usage

**Monitor first few automated runs:**
- Check Census dashboard at 3:45, 4:00, 4:15, 4:30
- Verify syncs are running automatically
- Check error rates (should be <1% now)

---

#### 4:00-4:30: Create Ongoing Monitoring Queries

```sql
-- ============================================================================
-- ONGOING MONITORING QUERIES
-- Save these for daily use
-- ============================================================================

-- Daily Health Check (run every morning)
CREATE OR REPLACE VIEW crm.sfdc_dbx.daily_health_check AS
SELECT
  CURRENT_DATE() AS check_date,
  (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create) AS create_queue_size,
  (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update) AS update_queue_size,
  (SELECT COUNT(*) FROM crm.salesforce.product_property WHERE is_deleted = FALSE) AS total_in_sf,
  (SELECT COUNT(*)
   FROM crm.sfdc_dbx.rds_properties_enriched
   WHERE property_status = 'ACTIVE' AND has_valid_sfdc_id = 1
   AND NOT EXISTS (
     SELECT 1 FROM crm.salesforce.product_property pp
     WHERE CAST(rds_property_id AS STRING) = pp.snappt_property_id_c
       AND pp.is_deleted = FALSE
   )) AS properties_still_missing,
  CASE
    WHEN (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create) > 100
    THEN '🔴 ALERT: High create queue'
    WHEN (SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create) > 50
    THEN '🟡 WARNING: Create queue elevated'
    ELSE '🟢 OK'
  END AS create_queue_status;

-- Feature Accuracy Monitor (run weekly)
CREATE OR REPLACE VIEW crm.sfdc_dbx.feature_accuracy_monitor AS
WITH rds_expected AS (
  SELECT sfdc_id, idv_enabled, bank_linking_enabled, payroll_enabled, income_insights_enabled
  FROM crm.sfdc_dbx.properties_aggregated_by_sfdc_id
  LIMIT 1000  -- Sample for performance
),
sf_actual AS (
  SELECT
    sf_property_id_c AS sfdc_id,
    idv_enabled_c AS idv_enabled,
    bank_linking_enabled_c AS bank_linking_enabled,
    payroll_enabled_c AS payroll_enabled,
    income_insights_enabled_c AS income_insights_enabled
  FROM crm.salesforce.product_property
  WHERE is_deleted = FALSE AND sf_property_id_c IS NOT NULL
  LIMIT 1000
)
SELECT
  'Weekly Feature Accuracy Check' AS metric,
  CURRENT_TIMESTAMP() AS check_time,
  ROUND(100.0 * SUM(CASE WHEN rds.idv_enabled = sf.idv_enabled THEN 1 ELSE 0 END) / COUNT(*), 2) AS idv_accuracy,
  ROUND(100.0 * SUM(CASE WHEN rds.bank_linking_enabled = sf.bank_linking_enabled THEN 1 ELSE 0 END) / COUNT(*), 2) AS bank_accuracy,
  ROUND(100.0 * SUM(CASE WHEN rds.payroll_enabled = sf.payroll_enabled THEN 1 ELSE 0 END) / COUNT(*), 2) AS payroll_accuracy,
  CASE
    WHEN ROUND(100.0 * SUM(CASE WHEN rds.idv_enabled = sf.idv_enabled THEN 1 ELSE 0 END) / COUNT(*), 2) < 95.0
    THEN '🔴 ALERT: Accuracy below threshold'
    WHEN ROUND(100.0 * SUM(CASE WHEN rds.idv_enabled = sf.idv_enabled THEN 1 ELSE 0 END) / COUNT(*), 2) < 98.0
    THEN '🟡 WARNING: Accuracy declining'
    ELSE '🟢 OK'
  END AS status
FROM rds_expected rds
INNER JOIN sf_actual sf ON rds.sfdc_id = sf.sfdc_id;

-- Census Sync Health (run daily)
CREATE OR REPLACE VIEW crm.sfdc_dbx.census_sync_health_daily AS
SELECT
  'Last 24 Hours' AS period,
  COUNT(*) AS total_syncs,
  SUM(CASE WHEN sync_status = 'SUCCESS' THEN 1 ELSE 0 END) AS successful,
  SUM(CASE WHEN sync_status = 'FAILED' THEN 1 ELSE 0 END) AS failed,
  ROUND(100.0 * SUM(CASE WHEN sync_status = 'SUCCESS' THEN 1 ELSE 0 END) / COUNT(*), 2) AS success_rate
FROM crm.sfdc_dbx.property_sync_audit_log
WHERE sync_timestamp >= CURRENT_TIMESTAMP() - INTERVAL 24 HOURS;
```

---

#### 4:30-5:00: Final Report & Documentation

```sql
-- ============================================================================
-- DAY 3 / FINAL ROLLOUT REPORT
-- ============================================================================

SELECT '========================================' AS line;
SELECT 'PROPERTY SYNC ROLLOUT - FINAL REPORT' AS title;
SELECT CURRENT_TIMESTAMP() AS report_time;
SELECT '========================================' AS line;

-- Section 1: Execution Timeline
SELECT '>>> EXECUTION TIMELINE <<<' AS section;
SELECT
  'Sync A Start' AS event,
  '<sync_a_start_time>' AS time;
SELECT
  'Sync A Complete' AS event,
  '<sync_a_end_time>' AS time;
SELECT
  'Sync B Start' AS event,
  '<sync_b_start_time>' AS time;
SELECT
  'Sync B Complete' AS event,
  '<sync_b_end_time>' AS time;

-- Section 2: Success Metrics
SELECT '>>> SUCCESS METRICS <<<' AS section;

WITH metrics AS (
  SELECT
    'Properties Created (Sync A)' AS metric,
    1031 AS target,
    [ACTUAL_CREATED] AS actual,  -- Fill in
    ROUND(100.0 * [ACTUAL] / 1031, 2) AS pct_of_target,
    CASE WHEN [ACTUAL] >= 970 THEN '✓' ELSE '✗' END AS status
  UNION ALL
  SELECT
    'Properties Updated (Sync B)' AS metric,
    7930 AS target,
    [ACTUAL_UPDATED] AS actual,  -- Fill in
    ROUND(100.0 * [ACTUAL] / 7930, 2),
    CASE WHEN [ACTUAL] >= 7500 THEN '✓' ELSE '✗' END
  UNION ALL
  SELECT
    'P1 Critical Properties Synced' AS metric,
    507 AS target,
    [ACTUAL_P1] AS actual,  -- Fill in
    ROUND(100.0 * [ACTUAL] / 507, 2),
    CASE WHEN [ACTUAL] >= 450 THEN '✓' ELSE '✗' END
  UNION ALL
  SELECT
    'Properties Still Missing' AS metric,
    100 AS target,
    [ACTUAL_MISSING] AS actual,  -- Fill in
    NULL AS pct_of_target,
    CASE WHEN [ACTUAL] <= 100 THEN '✓' ELSE '✗' END
  UNION ALL
  SELECT
    'Feature Accuracy (IDV)' AS metric,
    97 AS target,
    [ACTUAL_IDV_PCT] AS actual,  -- Fill in
    NULL,
    CASE WHEN [ACTUAL] >= 97.0 THEN '✓' ELSE '✗' END
  UNION ALL
  SELECT
    'Feature Accuracy (Bank)' AS metric,
    97 AS target,
    [ACTUAL_BANK_PCT] AS actual,  -- Fill in
    NULL,
    CASE WHEN [ACTUAL] >= 97.0 THEN '✓' ELSE '✗' END
)
SELECT * FROM metrics;

-- Section 3: Issues Encountered
SELECT '>>> ISSUES & RESOLUTIONS <<<' AS section;
SELECT
  'Issue #1' AS issue,
  '[Description]' AS description,
  '[Resolution]' AS resolution;
-- Add more issues as needed

-- Section 4: Next Steps
SELECT '>>> NEXT STEPS <<<' AS section;
SELECT 'Monitor for 1 week' AS task, 'Daily health checks' AS details, 'Day 4-10' AS timeline;
SELECT 'Address remaining issues' AS task, '[List specific issues]' AS details, 'By [date]' AS timeline;
SELECT 'Write full documentation' AS task, 'Comprehensive runbook' AS details, 'Week 2' AS timeline;
SELECT 'Train team' AS task, 'Architecture walkthrough' AS details, 'Week 2' AS timeline;

-- Section 5: Contact Info
SELECT '>>> CONTACTS <<<' AS section;
SELECT 'Implementer: [Your name]' AS contact;
SELECT 'Email: [Your email]' AS contact;
SELECT 'Slack: [Your handle]' AS contact;
```

**Save this report and email to stakeholders**

**Create minimal runbook:**

```bash
cat > /Users/danerosa/rds_databricks_claude/QUICK_RUNBOOK.md << 'EOF'
# Property Sync Quick Runbook

## Daily Health Check (5 minutes)

```sql
-- Run every morning
SELECT * FROM crm.sfdc_dbx.daily_health_check;
```

**Expected:**
- create_queue_size: <50
- properties_still_missing: <100
- Status: 🟢 OK

**If 🔴 ALERT or 🟡 WARNING:**
1. Check Census syncs are running (not paused)
2. Check Census error logs
3. Check Salesforce API limits
4. Investigate specific failed properties

## Weekly Feature Accuracy Check

```sql
SELECT * FROM crm.sfdc_dbx.feature_accuracy_monitor;
```

**Expected:** All features >97% accuracy

**If <95%:** Re-trigger Sync B, investigate mismatches

## Common Issues

### Issue: High create queue (>100)
1. Check if Census Sync A is running
2. Verify schedule is active (every 15 minutes)
3. Check for errors in Census logs
4. Verify Salesforce API limits not exceeded

### Issue: Feature mismatches
1. Run feature accuracy query
2. Identify pattern (all FALSE? random?)
3. May need to re-trigger Sync B
4. Check if SF workflow is overwriting data

## Emergency Contacts
- Implementer: [Your name] - [Phone/Email]
- Data Team: [Email]
- Census Support: support@getcensus.com

## Census Syncs
- Sync A (Create): Runs every 15 minutes
- Sync B (Update): Runs every 30 minutes
- Both should have >99% success rate

## Views Created
- crm.sfdc_dbx.rds_properties_enriched
- crm.sfdc_dbx.properties_aggregated_by_sfdc_id
- crm.sfdc_dbx.properties_to_create
- crm.sfdc_dbx.properties_to_update
- crm.sfdc_dbx.daily_health_check
- crm.sfdc_dbx.feature_accuracy_monitor

EOF
```

---

#### 5:00 PM: Final Stakeholder Communication

```bash
# Send final email/Slack

Subject: Property Sync Rollout Complete - [X] Properties Synced ✓

Team,

Completed full rollout of new RDS → Salesforce sync architecture.

FINAL RESULTS:
✓ [X] properties created in Salesforce
✓ [X] properties updated with latest data
✓ [X] P1 critical properties now visible to Sales/CS
✓ Feature accuracy: [X]% (target: >97%)
✓ Multi-property aggregation working: [X] cases
✓ Error rate: [X]% (target: <5%)

WHAT'S DIFFERENT:
- Missing properties now in Salesforce (~1,000 added)
- Feature data accurate and up-to-date
- Multi-property cases handled correctly (2,400+ properties unblocked)
- Automated syncs every 15/30 minutes

KNOWN ISSUES:
- [List any remaining issues and timelines for resolution]

MONITORING:
- Daily health check: [link to daily_health_check view]
- Quick runbook: /Users/danerosa/rds_databricks_claude/QUICK_RUNBOOK.md
- Contact: [Your name] - [Email/Slack]

NEXT WEEK:
- Daily monitoring for any issues
- Full documentation
- Team training session

Thank you for your support during this rollout!

[Your name]
```

---

### **✅ END OF DAY 3 / FULL ROLLOUT CHECKLIST**

- [ ] Sync A completed: ~1,000+ properties created
- [ ] Sync B completed: ~7,500+ properties updated
- [ ] Overall error rate <5%
- [ ] Properties still missing <100
- [ ] P1 critical properties synced (>450)
- [ ] Feature accuracy >97%
- [ ] Park Kennedy case correct
- [ ] Multi-property cases working (~2,400)
- [ ] Census schedules enabled (15min/30min)
- [ ] First automated syncs successful
- [ ] Monitoring queries created
- [ ] Quick runbook documented
- [ ] Final report created
- [ ] Stakeholders notified

---

## 🎉 THREE-DAY ROLLOUT COMPLETE!

**Congratulations!** You've successfully implemented the new sync architecture in 3 days.

### What You Accomplished

✅ **Day 1:** Built all views, comprehensive validation
✅ **Day 2:** Configured Census, pilot tested 100 properties
✅ **Day 3:** Full rollout of 9,000+ properties

### Final Success Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Properties Created | ~1,031 | [FILL] | [✓/✗] |
| Properties Updated | ~7,930 | [FILL] | [✓/✗] |
| P1 Properties Synced | 507 | [FILL] | [✓/✗] |
| Feature Accuracy | >97% | [FILL]% | [✓/✗] |
| Properties Missing | <100 | [FILL] | [✓/✗] |
| Error Rate | <5% | [FILL]% | [✓/✗] |

### What's Next (Week 2)

**Daily (Days 4-10):**
- [ ] Run health check query every morning
- [ ] Review Census sync logs
- [ ] Address any issues that arise

**By End of Week:**
- [ ] Fix any remaining issues from rollout
- [ ] Run full validation suite (from 4-week plan)
- [ ] Write comprehensive documentation

**Week 2:**
- [ ] Set up automated alerts (from 4-week plan)
- [ ] Create Databricks dashboard
- [ ] Train team on new architecture
- [ ] Schedule retrospective meeting

---

## 📊 COMPARISON: 3-Day vs Other Plans

| Aspect | 1-Day | 3-Day | 4-Week |
|--------|-------|-------|--------|
| Duration | 8 hours | 3 days | 4 weeks |
| Validation | Minimal | Comprehensive | Extensive |
| Pilot Test | 5+5 | 50+50 | 50+50 + monitoring |
| Risk | HIGH | MEDIUM | LOW |
| Error Tolerance | 5-10% | 2-5% | <1% |
| Documentation | Minimal | Basic | Comprehensive |
| Team Training | Skip | Skip | Full session |
| Success Rate | 75-90% | 90-97% | 97-99%+ |

**The 3-day plan gives you:**
- ✅ Good validation (not minimal)
- ✅ Pilot safety net
- ✅ Sustainable pace
- ✅ Most benefits of 4-week plan
- ✅ 85% faster than 4-week
- ✅ Much safer than 1-day

---

## 📞 ONGOING SUPPORT

**For questions or issues:**
- Implementer: [Your name] - [Contact]
- QUICK_RUNBOOK.md (daily operations)
- Full documentation in 4-week plan (reference)

**Related Documentation:**
- `NEW_SYNC_ARCHITECTURE_README.md` - Architecture overview
- `IMPLEMENTATION_PLAN_NEW_SYNC_ARCHITECTURE.md` - Phase 1 details
- `IMPLEMENTATION_PLAN_PHASE2_TO_PHASE6.md` - Full validation suite
- `IMPLEMENTATION_PLAN_PHASE4_TO_PHASE6.md` - Operational procedures

---

**Implementation Date:** _______________
**Days to Complete:** 3
**Total Properties Synced:** _______________
**Final Status:** ✅ Success / ⚠️ Success with issues / ❌ Incomplete

**Implementer Sign-off:** _______________
**Stakeholder Sign-off:** _______________

---

**Well done! The hard work is complete. Now just monitor and maintain.** 🚀
EOF
```

Perfect! I've created the complete 3-day implementation plan with Day 3 covering:

- **Morning:** Pre-rollout checks, Sync A execution (1,031 creates)
- **Midday:** Sync B execution (7,930 updates)
- **Afternoon:** Comprehensive validation, enable schedules, monitoring setup

## 📁 **Complete 3-Day Plan Files**

You now have:
1. **`THREE_DAY_IMPLEMENTATION_PLAN.md`** - Days 1 & 2
2. **`THREE_DAY_PLAN_DAY3.md`** - Day 3 (just created)

## 🎯 **Why This is the Best Option**

The 3-day plan gives you the **sweet spot**:

| Factor | 1-Day | **3-Day** | 4-Week |
|--------|-------|-----------|--------|
| Speed | ⚡ Fastest | ✅ Fast enough | 🐌 Slow |
| Risk | 🔴 HIGH | 🟡 MEDIUM | 🟢 LOW |
| Validation | ❌ Minimal | ✅ Good | ✅ Extensive |
| Pilot Test | ❌ Skip | ✅ 100 props | ✅ 100 props + monitoring |
| Success Rate | 75-90% | **90-97%** | 97-99% |
| Burnout Risk | 🔴 HIGH | 🟢 LOW | 🟢 LOW |

## 📋 **Quick Reference**

- **Day 1 (6-8hrs):** Build views + comprehensive validation
- **Day 2 (6-8hrs):** Configure Census + pilot 100 properties
- **Day 3 (6-8hrs):** Full rollout 9,000+ properties + monitoring

## 🚀 **Ready to Start?**

Would you like me to:
1. **Help you start Day 1** (begin building the views)?
2. **Create a checklist** to print out for each day?
3. **Answer questions** about any part of the 3-day plan?

The 3-day plan is my recommendation for your situation - fast enough to get it done this week, but safe enough to avoid disasters. Let me know how you'd like to proceed!