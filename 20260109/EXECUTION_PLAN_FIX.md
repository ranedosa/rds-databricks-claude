# Execution Plan - Fix Company Name Bug
**Date:** January 9, 2026
**Duration:** Estimated 3-4 hours
**Status:** Ready to Execute

---

## Overview

This plan fixes the critical bug where company names are incorrectly populated in Salesforce, affecting all ~9,700 properties synced in Day 3.

**Root Cause:** View uses `properties.name` instead of `companies.name`
**Fix:** Add JOIN to companies table and correct field reference
**Impact:** Will correct company names for all affected properties

---

## Pre-Flight Checklist

Before starting, ensure:

- [ ] You have Databricks SQL edit permissions
- [ ] You have Census admin access
- [ ] Stakeholders are aware maintenance is in progress
- [ ] Backup of current view definition saved (already done: `/tmp/original_view.sql`)
- [ ] You have ~3-4 hours available to complete all steps

---

## Step 1: Apply View Fix (15 minutes)

### 1.1 Execute the Fix SQL

**File:** `fix_rds_properties_enriched_view.sql`

**Method A: Databricks SQL Editor (Recommended)**
```bash
# Navigate to Databricks SQL Editor
# URL: https://[your-databricks-workspace]/sql/editor

# Copy contents of fix_rds_properties_enriched_view.sql
# Paste into SQL Editor
# Click "Run"
```

**Method B: Databricks CLI**
```bash
# Execute via CLI
databricks sql execute \
  --warehouse-id 95a8f5979c3f8740 \
  -f fix_rds_properties_enriched_view.sql
```

**Expected Output:**
```
View crm.sfdc_dbx.rds_properties_enriched replaced successfully
```

**If Error Occurs:**
- Check for syntax errors
- Verify you have permissions
- Confirm warehouse is running

### 1.2 Verify View Was Updated

**Query:**
```sql
DESCRIBE EXTENDED crm.sfdc_dbx.rds_properties_enriched;
```

**Check:**
- View definition should include JOIN to companies table
- Last modified timestamp should be today

---

## Step 2: Test the Fix (20 minutes)

### 2.1 Run Test Queries

**File:** `test_view_fix.sql`

Execute all 5 test queries in Databricks SQL Editor.

**Test 1 - Property vs Company Names:**
```bash
# Expected: >95% show different names
# If still seeing property_name = company_name, fix didn't apply
```

**Test 2 - NULL Company Names:**
```bash
# Expected: <5% NULL
# These are legitimate missing data, not the bug
```

**Test 3 - Known Properties:**
```bash
# Expected: "Hardware" → "Greystar", "Rowan" → "Greystar"
# If still seeing "Hardware" → "Hardware", fix didn't work
```

**Test 4 & 5 - Downstream Views:**
```bash
# Expected: Both views show correct company names
# These inherit from rds_properties_enriched
```

### 2.2 Validation Script

**Alternative: Run automated test**
```bash
python3 test_view_fix_automated.py
```

**Expected Output:**
```
✅ TEST 1: PASSED - 98% have different property/company names
✅ TEST 2: PASSED - 2% NULL company names
✅ TEST 3: PASSED - Known properties show correct companies
✅ TEST 4: PASSED - properties_to_create correct
✅ TEST 5: PASSED - properties_to_update correct

All tests passed! View fix successful.
```

**If Any Test Fails:**
- STOP - Do not proceed to Census syncs
- Review error messages
- Check view definition was applied correctly
- Consult with team before proceeding

---

## Step 3: Refresh Census Data (10 minutes)

Census needs to pull the updated view data before syncing.

### 3.1 Option A: Trigger Manual Refresh (Recommended)

**Steps:**
1. Go to Census: https://app.getcensus.com
2. Navigate to **Data Sources** → Select your Databricks connection
3. Find datasets:
   - `properties_to_create`
   - `properties_to_update`
4. Click **"Refresh Schema"** or **"Preview Data"** for each
5. Verify company_name values look correct in preview

### 3.2 Option B: Wait for Auto-Refresh

Census may auto-refresh every 1-24 hours depending on config.

**Not recommended:** Too slow for immediate fix

---

## Step 4: Re-run Sync A (CREATE) (30-60 minutes)

### 4.1 Navigate to Sync A

**URL:** https://app.getcensus.com/syncs/3394022

### 4.2 Execute Sync

**Options:**

**Option A: Manual Trigger (Recommended)**
1. Click **"Run Sync"** button
2. Select **"Full Sync"** (not incremental)
3. Confirm execution

**Option B: API Trigger**
```bash
curl -X POST https://app.getcensus.com/api/v1/syncs/3394022/trigger \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 4.3 Monitor Sync Progress

**Check:**
- Records processed: Expected ~574 (same as original)
- Operation type: Should show UPDATE (not CREATE) for existing records
- Error rate: Expected <1%
- Duration: ~10-30 minutes

**Real-time Monitoring:**
```bash
python3 monitor_sync.py a
```

**Expected Behavior:**
- Census will UPSERT existing records
- Match key: `Snappt_Property_ID__c`
- 574 records will be found and UPDATED with correct company names
- Few/no new creates (records already exist from original sync)

### 4.4 Validate Sync A Results

**Quick Check:**
```sql
-- Check a few known records
SELECT
    name as property_name,
    company_name_c,
    snappt_property_id_c
FROM crm.salesforce.product_property
WHERE snappt_property_id_c IN (
    '23a4b2f6-cb99-4cb3-93cb-970d3ab71473',  -- Was "140B County Rd 3346 799790" with NULL company
    'c2c727a2-5c53-4f54-aba6-8d609fb77ef7',  -- Was "Bulkley 803486" with NULL company
    'fa51749d-211c-4687-9fd4-70a44b488ce5'   -- Was "1 Fon Clair St 347765" with NULL company
)
```

**Expected:** company_name_c should now be populated

---

## Step 5: Re-run Sync B (UPDATE) (30-60 minutes)

### 5.1 Navigate to Sync B

**URL:** https://app.getcensus.com/syncs/3394041

### 5.2 Execute Sync

**Same process as Sync A:**
1. Click **"Run Sync"**
2. Select **"Full Sync"**
3. Confirm execution

### 5.3 Monitor Sync Progress

**Check:**
- Records processed: Expected ~9,141 (same as original)
- Error rate: Expected <1%
- Duration: ~20-45 minutes

**Real-time Monitoring:**
```bash
python3 monitor_sync.py b
```

### 5.4 Validate Sync B Results

**Quick Check:**
```sql
-- Check sample of updated records
SELECT
    name as property_name,
    company_name_c,
    snappt_property_id_c
FROM crm.salesforce.product_property
WHERE snappt_property_id_c IN (
    '5e785cfd-4f0e-496b-b5d6-a4e8894b9bb0',  -- Was "Multiplex 787879" with NULL company
    -- Add more IDs from verification query
)
```

**Expected:** company_name_c populated with actual company names

---

## Step 6: Full Validation (30 minutes)

### 6.1 Run Complete Validation

**Script:**
```bash
python3 validate_company_fix.py
```

This will check:
1. How many records now have correct company names
2. How many still have issues
3. Comparison before/after fix
4. Spot-check sample records

### 6.2 Manual Spot Checks

**Test in Salesforce UI:**
1. Go to Salesforce
2. Search for "Hardware" property
3. Verify company shows "Greystar" (not "Hardware")
4. Search for "Rowan" property
5. Verify company shows "Greystar" (not "Rowan")
6. Check 5-10 random properties from Day 3

### 6.3 Aggregate Validation Query

```sql
SELECT
    CASE
        WHEN sf.company_name_c = c.name THEN 'CORRECT'
        WHEN sf.company_name_c = p.name THEN 'STILL_BROKEN'
        WHEN sf.company_name_c IS NULL AND c.name IS NOT NULL THEN 'SF_NULL_BUT_DATA_EXISTS'
        WHEN sf.company_name_c IS NULL AND c.name IS NULL THEN 'LEGITIMATE_NULL'
        ELSE 'OTHER'
    END as status,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM crm.salesforce.product_property sf
INNER JOIN rds.pg_rds_public.properties p
    ON sf.snappt_property_id_c = p.id
LEFT JOIN rds.pg_rds_public.companies c
    ON p.company_id = c.id
    AND c._fivetran_deleted = false
WHERE (DATE(sf.created_date) = '2026-01-08'
   OR DATE(sf.last_modified_date) >= '2026-01-09')
  AND sf._fivetran_deleted = false
GROUP BY status
ORDER BY count DESC
```

**Success Criteria:**
- ✅ >95% status = 'CORRECT'
- ✅ <5% status = 'LEGITIMATE_NULL'
- ✅ 0% status = 'STILL_BROKEN'

**If Still Broken:**
- View fix may not have applied correctly
- Census may not have refreshed data
- Syncs may have used cached data
- Return to Step 1 and verify

---

## Step 7: Document Results (15 minutes)

### 7.1 Update Validation Report

**File:** `DAY3_VALIDATION_RESULTS.md`

Add section:
```markdown
## CRITICAL BUG FIX - January 9, 2026

**Issue:** Company names incorrectly populated (property names synced instead)
**Root Cause:** View definition bug
**Fix Applied:** [timestamp]
**Re-sync Completed:** [timestamp]
**Validation:** [results]
**Status:** ✅ RESOLVED
```

### 7.2 Create Fix Summary

**File:** `FIX_SUMMARY_[timestamp].md`

Document:
- What was wrong
- What was fixed
- Before/after metrics
- Validation results
- Time to resolution

---

## Step 8: Stakeholder Communication (20 minutes)

### 8.1 Draft Communication

**Template:**

```
Subject: Day 3 Sync - Company Name Issue Resolved ✅

Team,

Update on Day 3 property sync:

✅ ISSUE RESOLVED:
We identified and fixed a data quality issue where company names were
incorrectly populated in Salesforce Product_Property records.

📊 WHAT HAPPENED:
- Day 3 syncs executed successfully (574 creates, 9,141 updates)
- Post-sync validation identified incorrect company name mappings
- Root cause: Bug in Census source view definition

🛠️ FIX APPLIED:
- Corrected view definition (added proper JOIN to companies table)
- Re-ran both Census syncs with corrected data
- Validated all ~9,700 properties now have correct company names

⏱️ TIMELINE:
- Issue identified: [time]
- Fix applied: [time]
- Re-sync completed: [time]
- Total resolution time: ~3-4 hours

📈 CURRENT STATE:
- ✅ All properties now show correct company names
- ✅ >95% data quality validation passed
- ✅ Census syncs continue running automatically
- ✅ No action required from your teams

🔒 PREVENTION:
- Added company name validation to test protocols
- Implementing automated view testing framework
- Enhanced code review requirements

Thank you for your patience. Questions? Contact [your name/team]

Detailed report: [link to DAY3_VALIDATION_RESULTS.md]
```

### 8.2 Distribution List

**Send to:**
- [ ] Sales Ops team
- [ ] CS team
- [ ] Salesforce Admin team
- [ ] Data Engineering team
- [ ] Your manager
- [ ] Project stakeholders

---

## Step 9: Final Cleanup (10 minutes)

### 9.1 Update Documentation

- [ ] Update SESSION_SUMMARY.md with fix details
- [ ] Update DAY3_ACTION_PLAN.md mark items complete
- [ ] Archive investigation scripts
- [ ] Commit all files to git

### 9.2 Update Todo List

Mark as complete:
- [x] Fix rds_properties_enriched view
- [x] Test fixed view
- [x] Re-run syncs
- [x] Validate fix
- [x] Document results
- [x] Notify stakeholders

---

## Rollback Plan (If Needed)

**If something goes wrong during fix:**

### Rollback Step 1: Restore Original View
```sql
-- Original view definition saved in /tmp/original_view.sql
CREATE OR REPLACE VIEW crm.sfdc_dbx.rds_properties_enriched AS
[paste original definition]
```

### Rollback Step 2: No Salesforce Rollback Needed
- Salesforce records are not harmed by re-sync
- Company names will just remain incorrect until next fix attempt
- No data loss occurs

### Rollback Step 3: Communicate
- Notify stakeholders fix attempt failed
- Provide revised timeline
- Escalate if needed

---

## Success Metrics

**Fix is successful when:**

1. ✅ View test queries show correct company names
2. ✅ Census syncs complete with <1% error rate
3. ✅ Validation shows >95% correct company names
4. ✅ Manual spot checks confirm fix
5. ✅ Stakeholders notified
6. ✅ Documentation updated

---

## Estimated Timeline

| Step | Duration | Cumulative |
|------|----------|------------|
| 1. Apply View Fix | 15 min | 0:15 |
| 2. Test Fix | 20 min | 0:35 |
| 3. Refresh Census | 10 min | 0:45 |
| 4. Re-run Sync A | 45 min | 1:30 |
| 5. Re-run Sync B | 45 min | 2:15 |
| 6. Full Validation | 30 min | 2:45 |
| 7. Document Results | 15 min | 3:00 |
| 8. Stakeholder Communication | 20 min | 3:20 |
| 9. Final Cleanup | 10 min | 3:30 |

**Total: ~3.5 hours**

---

## Support Contacts

**If issues arise:**

- **Databricks Issues:** [team/contact]
- **Census Issues:** [team/contact]
- **Salesforce Issues:** [SF Admin team]
- **Escalation:** [manager/lead]

---

## Appendix: Files Reference

- `fix_rds_properties_enriched_view.sql` - View fix SQL
- `test_view_fix.sql` - Test queries
- `validate_company_fix.py` - Automated validation
- `monitor_sync.py` - Real-time sync monitoring
- `CRITICAL_FINDINGS_SUMMARY.md` - Complete analysis
- `DAY3_VALIDATION_RESULTS.md` - Validation report

---

**Ready to Execute:** Yes
**Approved by:** [awaiting approval]
**Started at:** [timestamp when you begin]
**Completed at:** [timestamp when you finish]

---

**Next Action:** Execute Step 1 - Apply View Fix
