# DAY 1 CHECKLIST: Foundation & Validation

**Date:** ____________
**Start Time:** ____________
**Implementer:** ____________

**Duration:** 6-8 hours
**Goal:** Build all Databricks views and validate aggregation logic

---

## ☕ PRE-FLIGHT (Before 9:00 AM)

- [ ] Databricks workspace access verified
- [ ] Can create views in `crm.sfdc_dbx` schema
- [ ] Source tables accessible (rds.pg_rds_public.properties, property_features)
- [ ] Salesforce table accessible (crm.salesforce.product_property)
- [ ] Calendar blocked for 6-8 hours (no meetings)
- [ ] Implementation plan open: `THREE_DAY_IMPLEMENTATION_PLAN.md`
- [ ] Slack status: "Do Not Disturb"
- [ ] Coffee/water ready ☕

**GO/NO-GO:** All boxes checked? → **GO** | Any NO? → Stop, fix first

---

## 🏗️ MORNING SESSION (9:00 AM - 12:00 PM)

### View 1: rds_properties_enriched (9:00-9:30)

- [ ] Open Databricks SQL editor
- [ ] Copy SQL from plan (Step 1.1, lines ~60-140)
- [ ] Run CREATE VIEW statement
- [ ] View created successfully (no errors)
- [ ] Run validation query: `SELECT COUNT(*) FROM crm.sfdc_dbx.rds_properties_enriched;`
- [ ] Result: ~20,000 properties _(Actual: ______)_
- [ ] ✅ **CHECKPOINT 1:** View working, count reasonable

**If errors:** Don't proceed. Check table names, column names, permissions.

---

### View 2: properties_aggregated_by_sfdc_id (9:30-10:30) ⭐ MOST IMPORTANT

- [ ] Copy SQL from plan (Step 1.2, lines ~160-320)
- [ ] Run CREATE VIEW statement
- [ ] View created successfully (no errors)
- [ ] Run validation query (aggregation distribution)
- [ ] Result shows: Most count=1, some count=2+ _(Actual distribution: ______)_
- [ ] ✅ **CHECKPOINT 2:** Aggregation view working

**Note:** This is the core innovation. If this fails, stop and fix.

---

### View 3: properties_to_create (10:30-11:00)

- [ ] Copy SQL from plan (Step 1.3)
- [ ] Run CREATE VIEW statement
- [ ] View created successfully
- [ ] Run validation: `SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_create;`
- [ ] Result: ~1,081 properties _(Actual: ______)_
- [ ] ✅ **CHECKPOINT 3:** Create queue correct

---

### View 4: properties_to_update (11:00-11:30)

- [ ] Copy SQL from plan (Step 1.4)
- [ ] Run CREATE VIEW statement
- [ ] View created successfully
- [ ] Run validation: `SELECT COUNT(*) FROM crm.sfdc_dbx.properties_to_update;`
- [ ] Result: ~7,980 properties _(Actual: ______)_
- [ ] ✅ **CHECKPOINT 4:** Update queue correct

---

### Audit Table & Monitoring (11:30-12:00)

- [ ] Create audit log table (Step 1.5)
- [ ] Create monitoring view (Step 1.6)
- [ ] Run: `SELECT * FROM crm.sfdc_dbx.sync_health_dashboard;`
- [ ] Results look reasonable
- [ ] ✅ **MORNING COMPLETE:** All views created

**Status check:**
- Total views created: ___/4
- All checkpoints passed: YES / NO
- Any critical errors: YES / NO

---

## 🍕 LUNCH BREAK (12:00-12:30 PM)

- [ ] Take 30-minute break
- [ ] Review morning results
- [ ] Any issues to address?
- [ ] Ready for afternoon validation

---

## 🔍 AFTERNOON SESSION (12:30 PM - 5:00 PM)

### Data Quality Validation (12:30-1:30)

- [ ] **TEST 1:** Aggregation preserves SFDC IDs (run query from plan)
  - Result: ✓ PASS / ✗ FAIL _(Notes: ______)_

- [ ] **TEST 2:** Union logic for features (run query from plan)
  - Result: ✓ PASS / ✗ FAIL _(Notes: ______)_

- [ ] **TEST 3:** Create + Update coverage (run query from plan)
  - Result: ✓ PASS / ✗ FAIL _(Notes: ______)_

- [ ] **TEST 4:** No DISABLED properties (run query from plan)
  - Result: ✓ PASS / ✗ FAIL _(Notes: ______)_

- [ ] **TEST 5:** Earliest timestamp logic (run query from plan)
  - Result: ✓ PASS / ✗ FAIL _(Notes: ______)_

- [ ] ✅ **CHECKPOINT 5:** All data quality tests passed (or issues documented)

**If any FAIL:** Document issue, investigate, decide if blocking for Day 2.

---

### Business Case Validation (1:30-2:30)

- [ ] **CASE 1: Park Kennedy** (sfdc_id: a01Dn00000HHUanIAH)
  - [ ] Run query from plan
  - [ ] Features are TRUE (from ACTIVE property): ✓ YES / ✗ NO
  - [ ] active_property_count correct: ✓ YES / ✗ NO
  - [ ] is_multi_property TRUE (if count>1): ✓ YES / ✗ NO
  - **Status:** ✓ PASS / ✗ FAIL _(Notes: ______)_

**⚠️ CRITICAL:** If Park Kennedy fails, STOP. Debug aggregation logic.

- [ ] **CASE 2: P1 Critical Properties** (~507 with features)
  - [ ] Run query from plan
  - [ ] Count: ~507 _(Actual: ______)_
  - [ ] Spot-check 10 properties look correct: ✓ YES / ✗ NO
  - **Status:** ✓ PASS / ✗ FAIL

- [ ] **CASE 3: Blocked Properties** (~2,410 multi-property)
  - [ ] Run query from plan
  - [ ] Multi-property count: ~2,410 _(Actual: ______)_
  - [ ] Sample 20 look correct: ✓ YES / ✗ NO
  - **Status:** ✓ PASS / ✗ FAIL

- [ ] **CASE 4: Feature Mismatches** (~799 properties)
  - [ ] Run query from plan
  - [ ] Count: ~799 _(Actual: ______)_
  - **Status:** ✓ PASS / ✗ FAIL

- [ ] ✅ **CHECKPOINT 6:** All business cases validated

---

### Edge Case Testing (2:30-3:30)

- [ ] **EDGE 1:** Properties with NULL sfdc_id
  - Count: ______ (should be some, but excluded from aggregation)

- [ ] **EDGE 2:** SFDC ID with 3+ properties
  - [ ] Sample 10 cases, aggregation looks correct: ✓ YES / ✗ NO

- [ ] **EDGE 3:** Properties in both create AND update (should be 0)
  - Count: ______ (MUST be 0, critical error if not)

- [ ] **EDGE 4:** Recently updated properties
  - Count in last 24h: ______

- [ ] ✅ **CHECKPOINT 7:** Edge cases tested, no critical issues

---

### Export Pilot Data (3:30-4:30)

- [ ] Run query to select 50 pilot CREATE properties (from plan)
- [ ] Save pilot CREATE IDs to file/spreadsheet
- [ ] File saved: ____________ (location)

- [ ] Run query to select 50 pilot UPDATE properties (from plan)
- [ ] Include Park Kennedy in pilot: ✓ YES / ✗ NO
- [ ] Save pilot UPDATE IDs to file/spreadsheet
- [ ] File saved: ____________ (location)

**⚠️ IMPORTANT:** You MUST have these IDs for Day 2. Save them now!

---

### Day 1 Report (4:30-5:00)

- [ ] Run Day 1 completion report query (from plan)
- [ ] Document all metrics:
  - Views created: ___/6
  - Data quality tests passed: ___/5
  - Business cases passed: ___/4
  - Edge cases tested: ___/4
  - Pilot data exported: ✓ YES / ✗ NO

- [ ] Document any issues found:
  - Issue 1: ______________________________
  - Issue 2: ______________________________
  - Issue 3: ______________________________

- [ ] All critical issues resolved: ✓ YES / ✗ NO

- [ ] ✅ **CHECKPOINT 8:** Day 1 complete

---

## 🎯 END OF DAY 1: GO/NO-GO FOR DAY 2

**Success Criteria (ALL must be YES):**

- [ ] All 6 views/tables created successfully
- [ ] Park Kennedy case validates correctly
- [ ] P1 critical properties identified (~507)
- [ ] Multi-property cases validated (~2,410)
- [ ] All data quality tests passed (or issues non-blocking)
- [ ] Edge case: overlap count = 0 (CRITICAL)
- [ ] Pilot data exported (50+50 property IDs saved)
- [ ] No critical blockers for Day 2

**Final Decision:**

- ✅ **GO to Day 2** if all boxes checked above
- ❌ **NO-GO** if any critical failures
  - Investigate and fix issues
  - May need to restart Day 1 tomorrow

**Sign-off:**

Day 1 Status: COMPLETE ✓ / INCOMPLETE ✗
Ready for Day 2: YES ✓ / NO ✗
End Time: ____________
Total Hours: ____________

Implementer Signature: ____________________

---

## 📋 PREP FOR DAY 2

**Before leaving today:**

- [ ] Pilot property IDs saved and accessible
- [ ] Any blockers documented for tomorrow
- [ ] Census workspace credentials verified
- [ ] Salesforce access verified
- [ ] Day 2 calendar blocked (6-8 hours)

**Tomorrow you'll need:**
- ✓ Pilot CREATE IDs (50 properties)
- ✓ Pilot UPDATE IDs (50 properties)
- ✓ Census workspace access
- ✓ Salesforce permissions

**See you tomorrow for Day 2!** 🚀

---

**For questions:** See `THREE_DAY_IMPLEMENTATION_PLAN.md` (detailed instructions)
