# 🔴 CRITICAL BUG FOUND - Census View Definition

**Discovered:** January 9, 2026, 10:45 AM
**Severity:** HIGH
**Impact:** 524 records have NULL company_name_c in Salesforce

---

## Bug Description

The `crm.sfdc_dbx.rds_properties_enriched` view has a critical bug in how it populates `company_name`:

**Current (BROKEN) Code:**
```sql
WITH properties_base AS (
    SELECT
      p.id AS rds_property_id,
      p.sfdc_id,
      p.short_id,
      p.company_id,
      p.name AS property_name,
      ...
      p.name AS company_name,  -- ❌ BUG: Using property name as company name!
      ...
    FROM rds.pg_rds_public.properties p
    WHERE p.company_id IS NOT NULL AND p.status != 'DELETED'
```

**Problem:**
- Line 13 aliases `p.name` (property name) as `company_name`
- This is incorrect - it should join to the `companies` table
- The view filters to `company_id IS NOT NULL`, so it only includes properties with companies
- But it never actually fetches the company name from the companies table!

---

## Why We See NULL Company Names

The 524 records with NULL `company_name_c` in Salesforce likely occur because:

1. Properties have `company_id` populated in RDS (so they pass the WHERE filter)
2. But the property `name` field itself is NULL (hence NULL company_name)
3. Census syncs the NULL value to Salesforce as `company_name_c`

**Evidence:**
- All 524 records are missing ONLY company_name_c (not other fields)
- Source views show 0 NULL company_name values... but that's the view's bug!
- Properties in RDS DO have company_id populated (we confirmed this)
- But we're syncing property.name instead of companies.name

---

## Correct Fix

The view should be fixed to properly join to the companies table:

**Fixed Code:**
```sql
WITH properties_base AS (
    SELECT
      p.id AS rds_property_id,
      p.sfdc_id,
      p.short_id,
      p.company_id,
      p.name AS property_name,
      p.status AS property_status,
      p.address AS address,
      p.city AS city,
      p.state AS state,
      p.zip AS postal_code,
      p.inserted_at as created_at,
      p.updated_at,
      c.name AS company_name,  -- ✅ FIXED: Get company name from companies table
      CASE WHEN p.status = 'ACTIVE' THEN 1 ELSE 0 END AS is_active,
      CASE WHEN p.sfdc_id IS NOT NULL AND p.sfdc_id != 'XXXXXXXXXXXXXXX' THEN 1 ELSE 0 END AS has_valid_sfdc_id
    FROM rds.pg_rds_public.properties p
    LEFT JOIN rds.pg_rds_public.companies c
      ON p.company_id = c.id
      AND c._fivetran_deleted = false  -- ✅ ADDED: Filter deleted companies
    WHERE p.company_id IS NOT NULL AND p.status != 'DELETED'
```

**Changes:**
1. Add `LEFT JOIN` to companies table
2. Change `p.name AS company_name` to `c.name AS company_name`
3. Add filter for non-deleted companies
4. Keep LEFT JOIN (not INNER) to handle edge cases

---

## Impact Assessment

### Current State (With Bug)
- 524 properties synced with NULL company_name_c
- These represent properties where property.name is NULL
- Company information exists in RDS but isn't being synced

### After Fix
- All properties will have correct company names from companies table
- Need to re-run both Sync A and Sync B to populate company names
- Estimated: ~524 records will be updated with correct company names

---

## Root Cause Timeline

1. **View Creation:** Someone created `rds_properties_enriched` view with incorrect company_name logic
2. **Development:** Views `properties_to_create` and `properties_to_update` inherited this bug
3. **Day 2 Pilot:** 100 records tested - company_name issues may not have been noticed
4. **Day 3 Production:** 574 creates + 9,141 updates - 524 have NULL company_name_c
5. **Discovery:** January 9, 2026 during validation

---

## Immediate Actions Required

### 1. Verify the Bug (URGENT)
Query to confirm property names are being used as company names:

```sql
-- Check if Salesforce company_name_c matches property name instead of company name
SELECT
    sf.name as salesforce_property_name,
    sf.company_name_c as salesforce_company_name,
    p.name as rds_property_name,
    c.name as actual_company_name,
    CASE
        WHEN sf.company_name_c = p.name THEN 'BUG_CONFIRMED'
        WHEN sf.company_name_c = c.name THEN 'CORRECT'
        WHEN sf.company_name_c IS NULL AND p.name IS NULL THEN 'PROPERTY_NAME_NULL'
        ELSE 'OTHER'
    END as status
FROM crm.salesforce.product_property sf
INNER JOIN rds.pg_rds_public.properties p
    ON sf.snappt_property_id_c = p.id
LEFT JOIN rds.pg_rds_public.companies c
    ON p.company_id = c.id
WHERE DATE(sf.created_date) = '2026-01-08'
   OR DATE(sf.last_modified_date) = '2026-01-09'
LIMIT 100
```

### 2. Fix the View (HIGH PRIORITY)
- Update `crm.sfdc_dbx.rds_properties_enriched` with correct JOIN
- Test the updated view
- Verify company_name is now populated correctly

### 3. Re-run Census Syncs (AFTER FIX)
- Re-run Sync A (CREATE) - will update existing records via UPSERT
- Re-run Sync B (UPDATE) - will populate missing company names
- Validate that company_name_c is now populated

### 4. Validate Fix
- Confirm 524 records now have company names
- Spot-check that company names are correct (not property names)
- Re-run data quality validation

---

## Long-term Improvements

1. **Add Unit Tests** - Test views with sample data before production
2. **Data Quality Checks** - Alert on NULL company names in views
3. **Code Review** - Require review of view definitions before deployment
4. **Documentation** - Document expected schema and joins for all views

---

## Questions to Answer

1. **When was this view created?** - Check git history or Databricks history
2. **Did this bug exist during pilot?** - Review Day 2 results for company names
3. **Are other fields similarly broken?** - Audit all field mappings in view
4. **Who owns this view?** - Identify responsible team for fix

---

## Decision Point

**Should we:**
1. ✅ **Fix immediately** - Update view, re-run syncs, notify stakeholders of delay
2. ⏸️ **Fix later** - Accept 524 NULL companies, fix in next maintenance window
3. ⚠️ **Rollback** - Revert Day 3 changes, fix view, re-run from scratch

**Recommendation:** Option 1 - Fix immediately
- Impact is moderate (524 records)
- Fix is straightforward (add JOIN)
- Re-syncing is fast (<30 min)
- Better to fix now than let bad data persist

---

**Discovered by:** Claude Sonnet 4.5
**Investigation File:** `investigate_missing_fields.py`
**Timestamp:** January 9, 2026, 10:45 AM PST
