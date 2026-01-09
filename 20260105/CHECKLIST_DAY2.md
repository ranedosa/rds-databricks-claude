# DAY 2 CHECKLIST: Census Configuration & Pilot

**Date:** ____________
**Start Time:** ____________
**Implementer:** ____________

**Duration:** 6-8 hours
**Goal:** Configure Census syncs and pilot test on 100 properties

---

## ☕ PRE-FLIGHT (Before 9:00 AM)

**Day 1 Completion Verification:**
- [ ] Day 1 completed successfully
- [ ] All 6 views/tables created and working
- [ ] Pilot property IDs ready (50 CREATE + 50 UPDATE)
  - CREATE IDs file: ____________
  - UPDATE IDs file: ____________

**Access Verification:**
- [ ] Census workspace access (ID: 33026)
- [ ] Salesforce access verified
- [ ] Can query Salesforce tables from Databricks
- [ ] Calendar blocked for 6-8 hours
- [ ] Implementation plan open: `THREE_DAY_IMPLEMENTATION_PLAN.md`
- [ ] Pilot IDs file open and ready to copy

**GO/NO-GO:** All boxes checked? → **GO** | Any NO? → Stop, fix first

---

## 🏗️ MORNING SESSION (9:00 AM - 12:00 PM)

### Configure Census Sync A - Create (9:00-10:30)

**Navigate to Census workspace → Create New Sync**

- [ ] Sync created, name: "RDS → SF product_property (CREATE)"

**Source Configuration:**
- [ ] Connection: Databricks (Snappt Production)
- [ ] Database: crm
- [ ] Schema: sfdc_dbx
- [ ] Table: properties_to_create

**Destination Configuration:**
- [ ] Connection: Salesforce (Snappt Production)
- [ ] Object: product_property__c

**Sync Behavior:**
- [ ] Mode: "Create Only" ← CRITICAL, verify this!

**Sync Key:**
- [ ] Source: rds_property_id
- [ ] Destination: snappt_property_id__c
- [ ] ⚠️ Double-check this mapping!

**Field Mappings (check each one):**
- [ ] rds_property_id → snappt_property_id__c (SYNC KEY)
- [ ] short_id → Short_ID__c
- [ ] company_id → Company_ID__c
- [ ] property_name → Name
- [ ] address → Property_Address_Street__c
- [ ] city → Property_Address_City__c
- [ ] state → Property_Address_State__c
- [ ] postal_code → Property_Address_Postal_Code__c
- [ ] country → Property_Address_Country__c
- [ ] company_name → Company_Name__c
- [ ] idv_enabled → IDV_Enabled__c
- [ ] bank_linking_enabled → Bank_Linking_Enabled__c
- [ ] payroll_enabled → Payroll_Enabled__c
- [ ] income_insights_enabled → Income_Insights_Enabled__c
- [ ] document_fraud_enabled → Document_Fraud_Enabled__c
- [ ] idv_enabled_at → IDV_Enabled_At__c
- [ ] bank_linking_enabled_at → Bank_Linking_Enabled_At__c
- [ ] payroll_enabled_at → Payroll_Enabled_At__c
- [ ] income_insights_enabled_at → Income_Insights_Enabled_At__c
- [ ] document_fraud_enabled_at → Document_Fraud_Enabled_At__c
- [ ] created_at → RDS_Created_At__c
- [ ] updated_at → RDS_Updated_At__c

**Filters (FOR PILOT ONLY):**
- [ ] Add filter: `WHERE rds_property_id IN ('id1', 'id2', ...)`
- [ ] Paste your 50 pilot CREATE IDs
- [ ] Verify Census shows ~50 properties in source

**Schedule & Error Handling:**
- [ ] Schedule: Manual (we'll trigger manually)
- [ ] Error handling: Log and continue
- [ ] Retry: 3 attempts

- [ ] **SAVE CONFIGURATION**
- [ ] ✅ **CHECKPOINT 1:** Sync A configured

**Common mistakes to avoid:**
- ❌ Wrong sync mode (Update or Create vs Create Only)
- ❌ Wrong sync key
- ❌ Field name typos (Salesforce is case-sensitive)
- ❌ Forgot pilot filter

---

### Configure Census Sync B - Update (10:30-12:00)

**Navigate to Census workspace → Create New Sync**

- [ ] Sync created, name: "RDS → SF product_property (UPDATE)"

**Source Configuration:**
- [ ] Connection: Databricks (Snappt Production)
- [ ] Database: crm
- [ ] Schema: sfdc_dbx
- [ ] Table: properties_to_update

**Destination Configuration:**
- [ ] Connection: Salesforce (Snappt Production)
- [ ] Object: product_property__c

**Sync Behavior:**
- [ ] Mode: "Update Only" ← CRITICAL (different from Sync A!)

**Sync Key:**
- [ ] Source: snappt_property_id_c ← DIFFERENT from Sync A!
- [ ] Destination: snappt_property_id__c
- [ ] ⚠️ This matches existing records, not creates new ones

**Field Mappings (all from Sync A, PLUS these):**
- [ ] All mappings from Sync A (copy them)
- [ ] active_property_count → Active_Property_Count__c
- [ ] total_feature_count → Total_Feature_Count__c
- [ ] is_multi_property → Is_Multi_Property__c
- [ ] has_any_features_enabled → Has_Any_Features_Enabled__c
- [ ] rds_last_updated_at → RDS_Last_Updated_At__c

**Filters (FOR PILOT ONLY):**
- [ ] Add filter: `WHERE snappt_property_id_c IN (...)`
- [ ] Paste your 50 pilot UPDATE IDs (different from CREATE!)
- [ ] Verify Census shows ~50 properties in source

**Advanced Settings:**
- [ ] Update Mode: "Replace" (not Merge) ← CRITICAL!
  - This ensures FALSE overwrites TRUE

**Schedule & Error Handling:**
- [ ] Schedule: Manual
- [ ] Error handling: Log and continue
- [ ] Retry: 3 attempts

- [ ] **SAVE CONFIGURATION**
- [ ] ✅ **CHECKPOINT 2:** Both syncs configured

---

## 🍕 LUNCH BREAK (12:00-12:30 PM)

- [ ] Take 30-minute break
- [ ] Review configurations
- [ ] Double-check pilot filters are correct
- [ ] Ready for pilot execution

---

## 🧪 AFTERNOON SESSION (12:30 PM - 5:00 PM)

### Pre-Pilot Validation (12:30-1:00)

- [ ] Verify pilot filters working in Databricks:

```sql
-- Create queue filter
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create
WHERE rds_property_id IN (<your 50 pilot IDs>);
-- Expected: 50
```
Actual: ______

```sql
-- Update queue filter
SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update
WHERE snappt_property_id_c IN (<your 50 pilot IDs>);
-- Expected: 50
```
Actual: ______

- [ ] Baseline SF count:
```sql
SELECT COUNT(*) FROM crm.salesforce.product_property WHERE is_deleted = FALSE;
```
Baseline: ______ (record this!)

- [ ] ✅ **CHECKPOINT 3:** Pre-pilot checks complete

---

### Execute Pilot Sync A - Create 50 (1:00-2:00)

**Trigger Sync:**
- [ ] Go to Census → Sync A
- [ ] Verify filter shows 50 properties
- [ ] Click "Trigger Sync Now"
- [ ] Start time: ____________

**Monitor (10-15 minutes):**
- [ ] Watch Census dashboard
- [ ] Records processed: ______
- [ ] Errors: ______
- [ ] Error rate: ______%

**Validate Results:**
- [ ] Sync completed (not still running)
- [ ] Census stats:
  - Created: ______/50
  - Errors: ______
  - Error rate: ______%

- [ ] Query Salesforce:
```sql
SELECT COUNT(*) FROM crm.salesforce.product_property
WHERE created_date >= '<sync_start_time>'
  AND snappt_property_id_c IN (<pilot IDs>);
```
Created in SF: ______/50

- [ ] Spot-check 10 properties (run query from plan)
  - Names look correct: ✓ YES / ✗ NO
  - Features match expectations: ✓ YES / ✗ NO
  - No obvious corruption: ✓ YES / ✗ NO

- [ ] Detailed validation (run comparison query from plan)
  - Match rate: ______% (target: >95%)

- [ ] ✅ **CHECKPOINT 4:** Pilot Sync A successful
  - [ ] 48+ of 50 created
  - [ ] Error rate <5%
  - [ ] Validation passes

**If checkpoint fails:** Fix issues before Sync B. Document:
- Issue: ______________________________
- Resolution: ______________________________

---

### Execute Pilot Sync B - Update 50 (2:00-3:00)

**Capture Baseline:**
- [ ] Run query to save current SF state (from plan)
- [ ] Baseline saved (copy results to file)

**Trigger Sync:**
- [ ] Go to Census → Sync B
- [ ] Verify filter shows 50 properties
- [ ] Click "Trigger Sync Now"
- [ ] Start time: ____________

**Monitor (10-15 minutes):**
- [ ] Watch Census dashboard
- [ ] Records updated: ______
- [ ] Errors: ______
- [ ] Error rate: ______%

**Validate Results:**
- [ ] Sync completed
- [ ] Census stats:
  - Updated: ______/50
  - Errors: ______
  - Error rate: ______%

- [ ] Query Salesforce:
```sql
SELECT COUNT(*) FROM crm.salesforce.product_property
WHERE last_modified_date >= '<sync_start_time>'
  AND snappt_property_id_c IN (<pilot IDs>);
```
Updated in SF: ______/50

- [ ] Park Kennedy check (if in pilot):
```sql
SELECT * FROM crm.salesforce.product_property
WHERE sf_property_id_c = 'a01Dn00000HHUanIAH';
```
  - active_property_count_c: ______ (correct?)
  - is_multi_property_c: TRUE / FALSE (correct?)
  - idv_enabled_c: TRUE / FALSE (should be TRUE)
  - bank_linking_enabled_c: TRUE / FALSE (should be TRUE)
  - last_modified_date: Recent (today)? ✓ YES / ✗ NO

- [ ] Feature accuracy (run comparison query from plan)
  - IDV accuracy: ______% (target: >97%)
  - Bank accuracy: ______% (target: >97%)

- [ ] ✅ **CHECKPOINT 5:** Pilot Sync B successful
  - [ ] 48+ of 50 updated
  - [ ] Error rate <3%
  - [ ] Park Kennedy correct (if in pilot)
  - [ ] Feature accuracy >97%

**If checkpoint fails:** Document and fix before Day 3:
- Issue: ______________________________
- Resolution: ______________________________

---

### Pilot Analysis & Go/No-Go (3:00-4:00)

**Run pilot success analysis query (from plan):**

- [ ] Sync A success: ______/50 (target: 48+)
- [ ] Sync B success: ______/50 (target: 48+)
- [ ] Overall error rate: ______% (target: <3%)

**Review Census error logs:**
- [ ] Error patterns documented
- [ ] Any systematic issues: ✓ YES / ✗ NO
- [ ] If YES, describe: ______________________________

**Overall pilot success:**
- [ ] Sync A: Created 48+ of 50 properties
- [ ] Sync B: Updated 48+ of 50 properties
- [ ] Feature accuracy: >97%
- [ ] Error rate: <3%
- [ ] Park Kennedy: Correct
- [ ] Multi-property cases: Working

**GO/NO-GO DECISION FOR DAY 3:**

All checkpoints passed? → ✅ **GO to Day 3**

Any critical failures? → ❌ **NO-GO**
- Fix issues first
- Re-run pilot on different batch
- Don't proceed until pilot succeeds

**Decision:** GO ✓ / NO-GO ✗

---

### Prepare for Day 3 (4:00-5:00)

**Document plan to remove filters (don't do yet!):**
- [ ] Note: Sync A filter removal process
- [ ] Note: Sync B filter removal process
- [ ] Save current filter definitions (for rollback if needed)

**Create Day 3 monitoring queries:**
- [ ] Run queries from plan to create monitoring views
- [ ] Views created:
  - [ ] day3_create_progress
  - [ ] day3_update_progress
  - [ ] day3_health_check

**Test monitoring queries:**
- [ ] `SELECT * FROM day3_health_check;`
- [ ] Results look reasonable: ✓ YES / ✗ NO

**Stakeholder communication:**
- [ ] Send pilot success email/Slack (use template from plan)
- [ ] Notify Day 3 rollout scheduled for: ____________

---

### Day 2 Report (4:30-5:00)

**Document results:**

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Sync A configured | ✓ | _____ | ✓ / ✗ |
| Sync B configured | ✓ | _____ | ✓ / ✗ |
| Pilot Sync A | 48+/50 | _____/50 | ✓ / ✗ |
| Pilot Sync B | 48+/50 | _____/50 | ✓ / ✗ |
| Feature accuracy | >97% | _____% | ✓ / ✗ |
| Park Kennedy | Correct | ✓ / ✗ | ✓ / ✗ |
| Error rate | <3% | _____% | ✓ / ✗ |

**Issues encountered:**
1. ______________________________
2. ______________________________
3. ______________________________

**All issues resolved:** ✓ YES / ✗ NO

---

## 🎯 END OF DAY 2: GO/NO-GO FOR DAY 3

**Success Criteria (ALL must be YES):**

- [ ] Both Census syncs configured correctly
- [ ] Pilot Sync A: 48+ of 50 created
- [ ] Pilot Sync B: 48+ of 50 updated
- [ ] Feature accuracy >97%
- [ ] Park Kennedy case correct
- [ ] Multi-property cases working
- [ ] Error rate <3%
- [ ] No critical blockers discovered
- [ ] Day 3 monitoring prepared
- [ ] Stakeholders notified

**Final Decision:**

- ✅ **GO to Day 3** if all boxes checked
- ❌ **NO-GO** if any critical failures
  - Fix issues
  - May need to re-pilot
  - Don't proceed until pilot proves the system works

**Sign-off:**

Day 2 Status: COMPLETE ✓ / INCOMPLETE ✗
Ready for Day 3: YES ✓ / NO ✗
End Time: ____________
Total Hours: ____________

Implementer Signature: ____________________

---

## 📋 PREP FOR DAY 3 (FULL ROLLOUT)

**Critical items for tomorrow:**

- [ ] Filters documented (ready to remove)
- [ ] Monitoring queries working
- [ ] Stakeholders notified of rollout time
- [ ] Rollout window scheduled: ____________
  - Recommended: Tuesday-Thursday, 10am-2pm
  - Avoid: Fridays, Mondays, holidays
- [ ] On-call contact identified: ____________
- [ ] Salesforce status page checked: https://status.salesforce.com
- [ ] Day 3 calendar completely clear (6-8 hours)

**Tomorrow you will:**
- ✓ Sync ~1,031 properties (Sync A - creates)
- ✓ Sync ~7,930 properties (Sync B - updates)
- ✓ Monitor and validate
- ✓ Enable automated schedules

**This is the big day. Get good rest tonight!** 💪

---

**For questions:** See `THREE_DAY_IMPLEMENTATION_PLAN.md` and `THREE_DAY_PLAN_DAY3.md`
