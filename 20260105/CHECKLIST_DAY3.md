# DAY 3 CHECKLIST: Full Rollout & Monitoring

**Date:** ____________
**Start Time:** ____________
**Implementer:** ____________

**Duration:** 6-8 hours
**Goal:** Execute full syncs (1,081 + 7,980) and validate

⚠️ **THIS IS PRODUCTION ROLLOUT - POINT OF NO RETURN**

---

## ☕ PRE-FLIGHT (Before 9:00 AM)

**Day 2 Completion Verification:**
- [ ] Day 2 pilot completed successfully
- [ ] All pilot checkpoints passed
- [ ] Stakeholder approval obtained for full rollout
- [ ] Issues from pilot documented and resolved

**Final Checks:**
- [ ] Rollout window scheduled: ____________
  - Recommended: Tuesday-Thursday, 10am-2pm
  - Today is: ____________ (good day? ✓ / ✗)
- [ ] Calendar completely clear for 6-8 hours
- [ ] On-call contact: ____________ (name/phone)
- [ ] Salesforce status: https://status.salesforce.com
  - Status: 🟢 All green / 🔴 Issues
- [ ] Implementation plan open: `THREE_DAY_PLAN_DAY3.md`

**GO/NO-GO:** All boxes checked + SF green? → **GO** | Any NO? → Abort

---

## 🔍 MORNING SESSION (9:00 AM - 12:00 PM)

### Final Pre-Rollout Checks (9:00-9:30)

**Check 1: View Health**
```sql
SELECT * FROM crm.sfdc_dbx.sync_health_dashboard;
```
- [ ] Properties to Create: ~1,031 _(Actual: ______)_
- [ ] Properties to Update: ~7,930 _(Actual: ______)_
- [ ] Multi-Property Cases: ~2,410 _(Actual: ______)_

**Check 2: Salesforce API Limits**
- [ ] Login to SF → Setup → System Overview → API Usage
- [ ] API quota available: ______% (need >50%)

**Check 3: Databricks Cluster**
- [ ] Cluster running and responsive: ✓ YES / ✗ NO

**Check 4: Take Baseline Snapshot**
```sql
-- Run snapshot query from plan
SELECT COUNT(*) FROM crm.salesforce.product_property WHERE is_deleted = FALSE;
```
- [ ] Baseline SF count: ______ (RECORD THIS!)

- [ ] ✅ **CHECKPOINT 1:** All pre-flight checks passed

**GO/NO-GO:** All checks pass? → **GO** | Any issues? → **STOP, fix first**

---

### Prepare Sync A for Full Rollout (9:30-9:45)

**Remove Pilot Filter:**
- [ ] Go to Census → Sync A → Filters
- [ ] **Remove** the `WHERE rds_property_id IN (...)` filter
- [ ] Census now shows ~1,031 properties (full queue)
- [ ] **SAVE** configuration

**Verification:**
```sql
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create;
```
- [ ] Will sync: ______ properties (should be ~1,031)

- [ ] ✅ **CHECKPOINT 2:** Sync A ready for full rollout

---

### Stakeholder Notification (9:45-10:00)

- [ ] Send notification (use template from plan)
- [ ] Subject: "Property Sync Full Rollout Starting Now"
- [ ] Include: What's happening, timeline, monitoring link
- [ ] Sent to: ____________________________
- [ ] Sent at: ____________

---

### 🚀 TRIGGER SYNC A - Full Rollout (10:00)

⚠️ **POINT OF NO RETURN - You're writing to production**

**Final Checks:**
- [ ] Filter removed from Sync A
- [ ] Sync mode is "Create Only"
- [ ] Source shows ~1,031 properties
- [ ] Ready to proceed: ✓ YES / ✗ NO

**TRIGGER:**
- [ ] Go to Census → Sync A
- [ ] Click "Trigger Sync Now"
- [ ] **START TIME:** ____________ (record exact time!)
- [ ] Expected duration: 20-30 minutes

---

### Monitor Sync A (10:05-10:35)

**Every 5 minutes, log:**

| Time | Census Records Processed | Census Errors | Queue Remaining |
|------|-------------------------|---------------|-----------------|
| 10:05 | ______ | ______ | ______ |
| 10:10 | ______ | ______ | ______ |
| 10:15 | ______ | ______ | ______ |
| 10:20 | ______ | ______ | ______ |
| 10:25 | ______ | ______ | ______ |
| 10:30 | ______ | ______ | ______ |

**Watch for:**
- [ ] Error rate stays <5%
- [ ] Progress is steady (not stalled)
- [ ] No API limit errors

**If error rate >5%:** Document errors, continue monitoring
**If error rate >10%:** ⚠️ **PAUSE SYNC**, investigate immediately

- [ ] Sync completed at: ____________
- [ ] Final error rate: ______%

---

### Validate Sync A Completion (10:35-11:00)

**Census Statistics:**
- [ ] Created: ______/1,031
- [ ] Errors: ______
- [ ] Error rate: ______%

**Query Salesforce:**
```sql
-- Properties created today
SELECT COUNT(*) FROM crm.salesforce.product_property
WHERE created_date >= '<sync_start_time>' AND is_deleted = FALSE;
```
- [ ] Created in SF: ______ (should be ~1,000+)

```sql
-- Queue remaining
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create;
```
- [ ] Queue remaining: ______ (target: <100)

```sql
-- P1 Critical properties created
SELECT COUNT(*) FROM crm.salesforce.product_property
WHERE created_date >= '<sync_start_time>'
  AND is_deleted = FALSE
  AND (idv_enabled_c = TRUE OR bank_linking_enabled_c = TRUE
       OR payroll_enabled_c = TRUE OR income_insights_enabled_c = TRUE);
```
- [ ] P1 created: ______ (target: ~450-500)

**Spot-check 10 properties:**
- [ ] Run query from plan
- [ ] Names look correct: ✓ YES / ✗ NO
- [ ] Features look correct: ✓ YES / ✗ NO
- [ ] No corruption: ✓ YES / ✗ NO

- [ ] ✅ **CHECKPOINT 3:** Sync A validation passed
  - [ ] ~1,000+ properties created
  - [ ] Queue remaining <100
  - [ ] Error rate <5%
  - [ ] Spot-check good

**If checkpoint fails:**
- Document issues: ______________________________
- If error rate >10% or <1,000 created: Investigate before Sync B
- Decision: Continue to Sync B? ✓ YES / ✗ NO

**Update stakeholders:**
- [ ] Sent at: ____________
- [ ] Status: Sync A complete, [X] created, starting Sync B at 11:30

---

### Break & Prepare Sync B (11:00-11:30)

**Take 30-minute break:**
- [ ] Review Sync A results
- [ ] Any issues to address?
- [ ] Check Salesforce status
- [ ] Coffee/water break

**Prepare Sync B:**
```sql
-- Verify count
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update;
```
- [ ] Will update: ______ (should be ~7,930)

```sql
-- Multi-property count
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update
WHERE is_multi_property = TRUE;
```
- [ ] Multi-property: ______ (should be ~2,410)

---

## 🔄 MIDDAY SESSION (11:30 AM - 2:00 PM)

### Prepare Sync B for Full Rollout (11:30-11:40)

**Remove Pilot Filter:**
- [ ] Go to Census → Sync B → Filters
- [ ] **Remove** the `WHERE snappt_property_id_c IN (...)` filter
- [ ] Census now shows ~7,930 properties
- [ ] **SAVE** configuration

**Final Checks:**
- [ ] Filter removed
- [ ] Sync mode is "Update Only" (NOT Create!)
- [ ] Update mode is "Replace" (NOT Merge!)
- [ ] Source shows ~7,930 properties

**Capture Baseline:**
```sql
-- Run baseline query from plan (sample current SF state)
```
- [ ] Baseline captured: ✓ YES / ✗ NO

- [ ] ✅ **CHECKPOINT 4:** Sync B ready for full rollout

---

### 🚀 TRIGGER SYNC B - Full Rollout (11:45)

⚠️ **CRITICAL SYNC - Updates production data**

**TRIGGER:**
- [ ] Go to Census → Sync B
- [ ] Click "Trigger Sync Now"
- [ ] **START TIME:** ____________
- [ ] Expected duration: 60-90 minutes

---

### Monitor Sync B (11:45-1:15 PM)

**Every 10 minutes, log:**

| Time | Census Records Updated | Census Errors | SF Updated Count |
|------|------------------------|---------------|------------------|
| 11:45 | ______ | ______ | ______ |
| 11:55 | ______ | ______ | ______ |
| 12:05 | ______ | ______ | ______ |
| 12:15 | ______ | ______ | ______ |
| 12:25 | ______ | ______ | ______ |
| 12:35 | ______ | ______ | ______ |
| 12:45 | ______ | ______ | ______ |
| 12:55 | ______ | ______ | ______ |
| 1:05 | ______ | ______ | ______ |
| 1:15 | ______ | ______ | ______ |

**Watch for:**
- [ ] Error rate stays <5%
- [ ] Progress is steady
- [ ] No pattern of errors

**Every 30 minutes, sample validation:**
```sql
-- Check 10 random updated properties (query from plan)
```
- [ ] 12:15 check: Looks good ✓ / Issues ✗
- [ ] 12:45 check: Looks good ✓ / Issues ✗

**If error rate >5%:** Document, continue monitoring
**If error rate >10%:** Consider pausing to investigate

- [ ] Sync completed at: ____________
- [ ] Final error rate: ______%

---

### Validate Sync B Completion (1:15-2:00)

**Census Statistics:**
- [ ] Updated: ______/7,930
- [ ] Errors: ______
- [ ] Skipped: ______
- [ ] Error rate: ______%

**Query Salesforce:**
```sql
-- Properties updated today
SELECT COUNT(*) FROM crm.salesforce.product_property
WHERE last_modified_date >= '<sync_b_start_time>' AND is_deleted = FALSE;
```
- [ ] Updated in SF: ______ (target: ~7,500+)

**Park Kennedy validation:**
```sql
SELECT * FROM crm.salesforce.product_property
WHERE sf_property_id_c = 'a01Dn00000HHUanIAH';
```
- [ ] active_property_count_c: ______ (correct?)
- [ ] is_multi_property_c: TRUE / FALSE (should be TRUE if count>1)
- [ ] idv_enabled_c: TRUE / FALSE (should be TRUE)
- [ ] bank_linking_enabled_c: TRUE / FALSE (should be TRUE)
- [ ] last_modified_date: Today ✓ / Old ✗

**Feature accuracy (sample 1000):**
- [ ] Run query from plan
- [ ] IDV accuracy: ______% (target: >97%)
- [ ] Bank accuracy: ______% (target: >97%)
- [ ] Payroll accuracy: ______% (target: >97%)

**Multi-property cases:**
```sql
SELECT COUNT(*) FROM crm.salesforce.product_property
WHERE is_multi_property_c = TRUE
  AND last_modified_date >= '<sync_b_start_time>' AND is_deleted = FALSE;
```
- [ ] Multi-property updated: ______ (target: ~2,400)

- [ ] ✅ **CHECKPOINT 5:** Sync B validation passed
  - [ ] ~7,500+ updated
  - [ ] Error rate <5%
  - [ ] Park Kennedy correct
  - [ ] Feature accuracy >97%
  - [ ] Multi-property cases working

**Update stakeholders:**
- [ ] Sent at: ____________
- [ ] Status: Sync B complete, [X] updated, validating now

---

## 📊 AFTERNOON SESSION (2:00 PM - 5:00 PM)

### Comprehensive Validation (2:00-3:00)

**Overall Success Metrics:**

**Metric 1: Properties in Salesforce**
```sql
-- Total increase
```
- [ ] Before rollout: ______ (from baseline)
- [ ] After rollout: ______
- [ ] Increase: ______ (target: ~1,000)

**Metric 2: Properties still missing**
```sql
SELECT COUNT(*) FROM crm.sfdc_dbx.rds_properties_enriched rds
WHERE rds.property_status = 'ACTIVE' AND rds.has_valid_sfdc_id = 1
  AND NOT EXISTS (
    SELECT 1 FROM crm.salesforce.product_property pp
    WHERE CAST(rds.rds_property_id AS STRING) = pp.snappt_property_id_c
      AND pp.is_deleted = FALSE
  );
```
- [ ] Still missing: ______ (target: <100, ideally <50)

**Metric 3: P1 Critical properties**
- [ ] P1 in SF now: ______ (target: 500+)
- [ ] P1 created today: ______ (target: 450-500)

**Metric 4: Feature accuracy (FULL dataset - sample)**
- [ ] Run full accuracy query from plan
- [ ] IDV: ______% (target: >97%)
- [ ] Bank: ______% (target: >97%)
- [ ] Payroll: ______% (target: >97%)
- [ ] Income: ______% (target: >97%)

**Metric 5: Multi-property summary**
- [ ] Total multi-property SFDC IDs: ______ (target: ~2,410)
- [ ] With features: ______ (from query)

**Metric 6: Queue health**
```sql
SELECT * FROM crm.sfdc_dbx.sync_health_dashboard;
```
- [ ] Create queue: ______ (target: <50)
- [ ] Update queue: ______ (stable, ~7,930)

---

### Issue Investigation (3:00-3:30)

**If properties still missing (>100):**
- [ ] Run query from plan to identify missing properties
- [ ] Check Census error logs for these IDs
- [ ] Document pattern: ______________________________
- [ ] Fix needed: ✓ YES / ✗ NO
- [ ] If YES, plan: ______________________________

**If feature accuracy <95%:**
- [ ] Run mismatch query from plan
- [ ] Identify pattern: ______________________________
- [ ] Fix needed: ✓ YES / ✗ NO
- [ ] If YES, plan: ______________________________

**All critical issues resolved:** ✓ YES / ✗ NO

---

### Enable Automated Schedules (3:30-4:00)

**Sync A Schedule:**
- [ ] Go to Census → Sync A → Schedule
- [ ] Change from "Manual" to "Every 15 minutes"
- [ ] Save

**Sync B Schedule:**
- [ ] Go to Census → Sync B → Schedule
- [ ] Change from "Manual" to "Every 30 minutes"
- [ ] Save

**Monitor first automated runs:**
- [ ] 3:45 check: Syncs running? ✓ YES / ✗ NO
- [ ] 4:00 check: Any errors? ✓ YES / ✗ NO
- [ ] 4:15 check: Still healthy? ✓ YES / ✗ NO
- [ ] 4:30 check: All good? ✓ YES / ✗ NO

**If issues:** Pause schedules, investigate, fix, resume

---

### Create Ongoing Monitoring (4:00-4:30)

**Daily monitoring queries:**
- [ ] Create `daily_health_check` view (from plan)
- [ ] Create `feature_accuracy_monitor` view (from plan)
- [ ] Create `census_sync_health_daily` view (from plan)

**Test queries:**
- [ ] `SELECT * FROM daily_health_check;`
  - Status: 🟢 OK / 🟡 WARNING / 🔴 ALERT
- [ ] `SELECT * FROM feature_accuracy_monitor;`
  - Accuracy: ______% (target: >95%)

---

### Final Report & Documentation (4:30-5:00)

**Run completion report (from plan):**

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Properties Created | ~1,031 | ______ | ✓ / ✗ |
| Properties Updated | ~7,930 | ______ | ✓ / ✗ |
| P1 Properties | 507 | ______ | ✓ / ✗ |
| IDV Accuracy | >97% | ______% | ✓ / ✗ |
| Bank Accuracy | >97% | ______% | ✓ / ✗ |
| Properties Missing | <100 | ______ | ✓ / ✗ |
| Error Rate | <5% | ______% | ✓ / ✗ |

**Create minimal runbook:**
- [ ] Copy template from plan
- [ ] Save as `QUICK_RUNBOOK.md`
- [ ] Document Census sync IDs
- [ ] Document daily health check process

**Issues encountered:**
1. ______________________________
2. ______________________________
3. ______________________________

**Next steps:**
- [ ] Monitor for 1 week (daily health checks)
- [ ] Address issues by: ____________
- [ ] Full documentation by: ____________
- [ ] Team training by: ____________

---

### Final Stakeholder Communication (5:00 PM)

- [ ] Send final report (use template from plan)
- [ ] Subject: "Property Sync Rollout Complete - [X] Properties Synced ✓"
- [ ] Include: Final metrics, what's different, known issues, monitoring
- [ ] Sent to: ____________________________
- [ ] Sent at: ____________

---

## 🎯 END OF DAY 3 / FULL IMPLEMENTATION

**Success Criteria (ALL must be YES):**

- [ ] Sync A: ~1,000+ properties created
- [ ] Sync B: ~7,500+ properties updated
- [ ] Overall error rate <5%
- [ ] Properties missing <100
- [ ] P1 critical properties synced (>450)
- [ ] Feature accuracy >97%
- [ ] Park Kennedy correct
- [ ] Multi-property cases working (~2,400)
- [ ] Census schedules enabled
- [ ] First automated syncs successful
- [ ] Monitoring queries working
- [ ] Runbook documented
- [ ] Stakeholders notified

**Final Status:**

Implementation: COMPLETE ✓ / INCOMPLETE ✗

Overall Success: SUCCESS ✓ / PARTIAL SUCCESS ⚠️ / NEEDS WORK ✗

End Time: ____________
Total Hours (Day 3): ____________
Total Hours (3 days): ____________

Implementer Signature: ____________________

---

## 📅 NEXT WEEK: MONITORING & FOLLOW-UP

**Days 4-10 (Daily, 5 minutes):**
- [ ] Run: `SELECT * FROM daily_health_check;`
- [ ] Review Census sync logs
- [ ] Check for errors
- [ ] Address issues immediately

**Week 2 Tasks:**
- [ ] Fix remaining issues (if any)
- [ ] Run full validation suite (from 4-week plan)
- [ ] Write comprehensive documentation
- [ ] Set up automated alerts
- [ ] Create Databricks dashboard
- [ ] Schedule team training
- [ ] Retrospective meeting

**Weekly (30 minutes):**
- [ ] Run: `SELECT * FROM feature_accuracy_monitor;`
- [ ] Review trends
- [ ] Update stakeholders

**Monthly (2 hours):**
- [ ] Architecture review
- [ ] Assess aggregation rules
- [ ] Plan improvements

---

## 🎉 CONGRATULATIONS!

**You've successfully implemented the new sync architecture in 3 days!**

### What You Accomplished:

✅ Built aggregation layer (handles many-to-1)
✅ Configured Census syncs (create vs update)
✅ Synced 9,000+ properties to Salesforce
✅ Unblocked 2,400+ multi-property cases
✅ 97%+ feature accuracy
✅ Automated syncs running every 15/30 minutes

### Impact:

- Sales team can see all properties with features
- CS team has accurate customer data
- Billing is correct
- No more manual interventions
- Scalable architecture for future

**Well done!** Now maintain and monitor. 🚀

---

**For questions:** See `THREE_DAY_PLAN_DAY3.md` (detailed instructions) and `QUICK_RUNBOOK.md` (daily operations)
