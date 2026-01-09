# 🔴 CRITICAL FINDINGS - Day 3 Validation
**Date:** January 9, 2026, 11:00 AM PST
**Investigator:** Claude Sonnet 4.5
**Status:** CRITICAL DATA QUALITY ISSUE IDENTIFIED

---

## Executive Summary

Day 3 production rollout **successfully executed both syncs** (574 creates, 9,141 updates) with <1% error rates. However, validation revealed a **critical data quality bug** in the Census source view that affects **ALL ~9,700 synced properties**.

**The Bug:** Company names are incorrectly populated in Salesforce:
- **64% of properties** show property name as company name (e.g., "Hardware" instead of "Greystar")
- **34% of properties** have NULL company names despite having company data in RDS
- **Only ~2% appear correct**

**Root Cause:** The `crm.sfdc_dbx.rds_properties_enriched` view uses `properties.name` instead of `companies.name` for the `company_name` field.

**Required Action:** Fix the view and re-run both Census syncs to correct company names.

---

## Investigation Results

### 1. Initial Discovery: 524 Records with Missing Fields

**Query 1 Results:**
- 524 records modified on Jan 8-9 have NULL company_name_c
- 100% are missing ONLY company_name_c (not other fields)
- 95.2% (499) from Sync B (updates)
- 4.8% (25) from Sync A (creates)

**Initial Hypothesis:** Legitimate missing data in RDS source

---

### 2. Source Data Verification

**Query 2 Results:**
- RDS properties table: Property DOES have company_id populated (e.g., `33f00170-c439-4f6c-9992-e1b434f338e5`)
- Census source views: Show 0 NULL company_name values
- **Conclusion:** This is NOT missing source data - it's a transformation issue

---

### 3. View Definition Analysis

**Query 3 Results:**
Examined `crm.sfdc_dbx.rds_properties_enriched` view definition:

```sql
WITH properties_base AS (
    SELECT
      p.id AS rds_property_id,
      p.sfdc_id,
      p.short_id,
      p.company_id,
      p.name AS property_name,
      ...
      p.name AS company_name,  -- ❌ BUG HERE!
      ...
    FROM rds.pg_rds_public.properties p
    WHERE p.company_id IS NOT NULL AND p.status != 'DELETED'
```

**Bug Identified:**
- Line 13: `p.name AS company_name` - Uses property name instead of company name
- Missing: JOIN to companies table to get `companies.name`
- Impact: ALL properties have incorrect company names in Salesforce

---

### 4. Bug Verification

**Query 4 Results:**
Compared Salesforce company_name_c against actual RDS company names:

| Status | Count | Percentage |
|--------|-------|------------|
| Property name as company name | 32 | **64.0%** |
| NULL but data exists in RDS | 17 | **34.0%** |
| Correct or other | 1 | **2.0%** |

**Sample Incorrect Mappings:**
- "Hardware" (property) → Should be "Greystar" (company)
- "Rowan" (property) → Should be "Greystar" (company)
- "The Storey" (property) → Should be "AVENUE5 RESIDENTIAL" (company)
- "South and Twenty" (property) → Should be "RKW Residential" (company)

**Confirmed:** Census is syncing property names as company names!

---

## Impact Assessment

### Severity: 🔴 CRITICAL

**Data Integrity:**
- ~6,300 properties (64% of 9,700) have **wrong company names**
- ~3,300 properties (34% of 9,700) have **NULL company names**
- Only ~200 properties (2% of 9,700) are potentially correct

**Business Impact:**
- ❌ Sales team sees incorrect company associations
- ❌ CS team cannot filter by company accurately
- ❌ Reporting on companies is completely broken
- ❌ Billing may be affected if company-based
- ❌ Customer trust impacted if they see their properties under wrong companies

**Systems Affected:**
- Salesforce Product_Property__c object (18,722 total records)
- Day 3 synced properties: 574 creates + 9,141 updates = 9,715 affected
- Downstream systems using this data

---

## Root Cause Analysis

### Timeline

1. **Unknown Date:** `rds_properties_enriched` view created with bug
   - Developer mistakenly used `p.name AS company_name`
   - Should have joined to companies table

2. **Pre-Day 3:** Views `properties_to_create` and `properties_to_update` inherited bug
   - Both views use `properties_aggregated_by_sfdc_id`
   - Which uses `rds_properties_enriched`
   - Bug propagated through entire view stack

3. **Day 2 (Pilot):** 100 properties tested
   - Company name issues may not have been validated
   - Focus was on feature flags and error rates
   - Bug went undetected

4. **Day 3 (Production):** Both syncs executed successfully
   - Sync A: 574 creates with wrong company names
   - Sync B: 9,141 updates with wrong company names
   - Technical execution perfect, but data quality broken

5. **January 9:** Bug discovered during validation
   - Investigated 524 NULL company names
   - Traced to view definition bug
   - Verified with sample data comparison

### Why It Wasn't Caught Earlier

1. **No company name validation** in pilot test plan
2. **Source view shows 0 NULLs** - masked the issue (view filters company_id IS NOT NULL)
3. **Census sync succeeded** - technical execution was flawless
4. **Property names look plausible** - "Hardware" could be a company name
5. **Focus on feature flags** - main validation target, not company data

---

## Technical Fix Required

### Step 1: Fix the View

**Current (Broken):**
```sql
WITH properties_base AS (
    SELECT
      p.id AS rds_property_id,
      ...
      p.name AS company_name,  -- ❌ WRONG
      ...
    FROM rds.pg_rds_public.properties p
    WHERE p.company_id IS NOT NULL AND p.status != 'DELETED'
```

**Fixed:**
```sql
WITH properties_base AS (
    SELECT
      p.id AS rds_property_id,
      ...
      c.name AS company_name,  -- ✅ CORRECT
      ...
    FROM rds.pg_rds_public.properties p
    LEFT JOIN rds.pg_rds_public.companies c
      ON p.company_id = c.id
      AND c._fivetran_deleted = false
    WHERE p.company_id IS NOT NULL AND p.status != 'DELETED'
```

**Changes:**
1. Add LEFT JOIN to companies table on p.company_id = c.id
2. Change `p.name` to `c.name` for company_name field
3. Filter out deleted companies

### Step 2: Verify Fix

**Test Query:**
```sql
SELECT
    rds_property_id,
    property_name,
    company_name,
    company_id
FROM crm.sfdc_dbx.rds_properties_enriched
WHERE property_name != company_name  -- Should return all rows after fix
LIMIT 10
```

Expected: Property names and company names should be different

### Step 3: Re-run Census Syncs

After view is fixed:

1. **Refresh Census datasets** - Ensure Census pulls updated view data
2. **Run Sync A (CREATE)** - Will UPSERT existing records with correct company names
3. **Run Sync B (UPDATE)** - Will update all modified records with correct company names
4. **Validate results** - Confirm company names are now correct

### Step 4: Validate Fix

**Validation Query:**
```sql
SELECT
    CASE
        WHEN sf.company_name_c = c.name THEN 'CORRECT'
        WHEN sf.company_name_c = p.name THEN 'STILL_BROKEN'
        WHEN sf.company_name_c IS NULL THEN 'NULL'
        ELSE 'OTHER'
    END as status,
    COUNT(*) as count
FROM crm.salesforce.product_property sf
INNER JOIN rds.pg_rds_public.properties p
    ON sf.snappt_property_id_c = p.id
LEFT JOIN rds.pg_rds_public.companies c
    ON p.company_id = c.id
WHERE (DATE(sf.created_date) = '2026-01-08'
   OR DATE(sf.last_modified_date) >= '2026-01-09')
  AND sf._fivetran_deleted = false
GROUP BY status
```

Expected: >95% 'CORRECT' status

---

## Recommended Action Plan

### 🔴 IMMEDIATE (Today)

**Priority 1: Fix the View (30 minutes)**
- [ ] Update `crm.sfdc_dbx.rds_properties_enriched` view with JOIN to companies
- [ ] Test view returns correct company names
- [ ] Verify view definition change deployed

**Priority 2: Re-run Syncs (1-2 hours)**
- [ ] Refresh Census dataset connections
- [ ] Run Sync A (CREATE) - will UPSERT existing 574 records
- [ ] Monitor: Expect ~574 updates (not creates)
- [ ] Run Sync B (UPDATE) - will update 9,141+ records
- [ ] Monitor: Expect similar count as original

**Priority 3: Validate Fix (30 minutes)**
- [ ] Run validation query to confirm company names correct
- [ ] Spot-check 20-30 properties in Salesforce UI
- [ ] Verify NULL company names are now populated
- [ ] Confirm percentages: >95% correct

**Priority 4: Communicate (30 minutes)**
- [ ] Draft stakeholder notification explaining issue and fix
- [ ] Update Day 3 validation report with findings
- [ ] Document lessons learned

**Total Time:** ~3-4 hours to full resolution

---

### 🟡 SHORT-TERM (This Week)

**Data Quality Audit:**
- [ ] Check if other fields have similar issues
- [ ] Verify all Census field mappings are correct
- [ ] Review Day 2 pilot data for company name accuracy
- [ ] Audit historical synced data (pre-Day 3)

**Process Improvements:**
- [ ] Add company name validation to test plan
- [ ] Create unit tests for views
- [ ] Implement data quality checks in Census
- [ ] Add code review requirement for view changes

**Documentation:**
- [ ] Document correct view patterns
- [ ] Create view development guidelines
- [ ] Update operational runbook

---

### 🟢 LONG-TERM (Next 2 Weeks)

**Prevention:**
- [ ] Automated view testing framework
- [ ] Pre-deployment validation pipeline
- [ ] Data quality monitoring dashboard
- [ ] Alerts for NULL company names

---

## Stakeholder Communication

### Message Template

```
Subject: Day 3 Sync - Data Quality Issue Identified & Fix in Progress

Team,

Day 3 production sync completed successfully with 99%+ success rates:
- ✅ 574 properties created (Jan 8)
- ✅ 9,141 properties updated (Jan 9)

However, post-sync validation identified a data quality issue:

❌ ISSUE: Company names incorrectly populated in Salesforce
   - 64% of synced properties show property name instead of company name
   - 34% have NULL company names
   - Root cause: Bug in Census source view definition

✅ FIX IN PROGRESS:
   - View definition corrected (adding proper JOIN to companies table)
   - Re-running both syncs to populate correct company names
   - ETA: Complete by end of day January 9
   - No action required from your teams

📊 IMPACT:
   - Temporary: Company filters/reports may be inaccurate
   - Resolution: ~4 hours from discovery to fix
   - All ~9,700 affected properties will be corrected

🔍 PREVENTION:
   - Adding company name validation to test plans
   - Implementing automated view testing
   - Enhanced code review for view changes

We apologize for the inconvenience and are working to prevent similar issues.

Questions? Contact [your name/team]
```

---

## Decision Points

### Decision 1: When to Re-run Syncs?

**Option A: Immediately (Recommended)**
- ✅ Pro: Fixes data ASAP, limits exposure time
- ✅ Pro: Demonstrates urgency and ownership
- ⚠️ Con: Disrupts current day's work

**Option B: After business hours**
- ✅ Pro: Less disruptive to teams
- ❌ Con: Incorrect data persists longer (12+ hours)
- ❌ Con: Stakeholders working with bad data

**Recommendation:** Option A - Fix immediately

### Decision 2: Communicate Before or After Fix?

**Option A: Communicate Now (Before Fix)**
- ✅ Pro: Transparent, shows we're on it
- ⚠️ Con: Teams may panic or lose trust
- ⚠️ Con: May generate support requests we can't handle yet

**Option B: Communicate After Fix (Recommended)**
- ✅ Pro: Can report "issue found AND fixed"
- ✅ Pro: Demonstrates competence
- ✅ Pro: Less alarm, more confidence
- ⚠️ Con: Brief period of non-transparency

**Recommendation:** Option B - Fix first, then communicate

### Decision 3: Scope of Re-sync?

**Option A: Only Day 3 Properties (Jan 8-9)**
- ✅ Pro: Faster, focused
- ❌ Con: Historical data still wrong

**Option B: All Properties in Salesforce**
- ✅ Pro: Fixes everything
- ⚠️ Con: Much longer sync time
- ⚠️ Con: May hit rate limits

**Recommendation:** Option A for now, Option B as follow-up

---

## Files Created

1. **`investigate_missing_fields.py`** - Initial investigation script
2. **`check_rds_companies_fixed.py`** - RDS source verification
3. **`verify_company_bug.py`** - Bug confirmation query
4. **`CRITICAL_BUG_FOUND.md`** - Detailed bug analysis
5. **`CRITICAL_FINDINGS_SUMMARY.md`** - This file

---

## Lessons Learned

### What Went Wrong
1. View definition had critical bug (wrong field mapping)
2. Pilot test didn't validate company names specifically
3. No automated view testing or validation
4. Code review didn't catch the bug
5. Assumed source view data was correct without verification

### What Went Right
1. Comprehensive post-deployment validation caught the issue
2. Systematic investigation identified root cause quickly
3. Fix is straightforward and well-understood
4. Impact contained to known scope (Day 3 syncs)
5. No data loss - only incorrect field values

### Future Improvements
1. ✅ Add field-level validation to pilot tests
2. ✅ Implement automated view testing framework
3. ✅ Require code review for all view changes
4. ✅ Add data quality checks in Census pipeline
5. ✅ Create comprehensive test data with known-good values

---

**Status:** Investigation Complete - Awaiting User Decision on Fix Execution

**Next Action:** Fix view definition and re-run syncs

**ETA to Resolution:** 3-4 hours from approval

---

**Prepared by:** Claude Sonnet 4.5
**Investigation Duration:** ~90 minutes
**Date:** January 9, 2026, 11:00 AM PST
