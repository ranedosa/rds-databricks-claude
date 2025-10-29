# Partner Name Change: ResidentIQ → Inhabit

**Date**: 2024-10-29
**Requestor**: Data Team
**Issue**: Partner name "ResidentIQ" needs to be updated to "Inhabit" across all dashboards and data

---

## Summary

The partner name change from **ResidentIQ** to **Inhabit** is not reflected in dashboards because the company name exists in the **source data**, not in pipeline code. This requires a data update, not a code change.

## Investigation Findings

### 1. Codebase Analysis

✓ **No hardcoded "ResidentIQ" references** found in:
- DLT pipeline code (`scripts/pipeline/dlt_fde_pipeline.py`)
- Validation scripts
- Analysis scripts
- Documentation (except this doc)

### 2. Data Source

The company name comes from the **RDS PostgreSQL database** via **Fivetran sync**:

```
Source: RDS PostgreSQL (production database)
  ↓ (Fivetran sync)
Unity Catalog: rds.pg_rds_public.companies
  ↓ (DLT pipeline)
Gold Table: product.fde.dim_fde
  ↓ (Dashboards query this)
Dashboard: Edited Submissions Dashboard
```

### 3. Where the Name Exists

The company name is stored in multiple places:

| Location | Table | Column | Action Required |
|----------|-------|--------|-----------------|
| **RDS (Source)** | `companies` | `name` | ✅ **Primary - Update here** |
| **Unity Catalog** | `rds.pg_rds_public.companies` | `name` | 🔄 Auto-synced by Fivetran |
| **Gold Table** | `product.fde.dim_fde` | `company_name` | 🔄 Auto-updated by DLT |
| **Dashboards** | N/A | Queries `company_name` | 🔄 Auto-reflects data changes |

---

## Action Plan

### Option 1: Update at Source (Recommended)

**Best practice**: Update the company name in your production application database.

1. **Update in Production Application**
   - Log into your application admin panel
   - Find "ResidentIQ" company record
   - Update company name to "Inhabit"
   - Save changes

2. **Wait for Fivetran Sync**
   - Fivetran will automatically sync the change
   - Check Fivetran sync frequency (typically every 5-30 minutes)
   - Verify sync: https://fivetran.com/dashboard

3. **DLT Pipeline Updates Automatically**
   - The DLT pipeline will pick up the new name on next run
   - 00_RDS workflow runs every 6 hours
   - Or manually trigger the workflow

4. **Dashboards Update Automatically**
   - Once data is updated, dashboards will show "Inhabit"
   - No code changes needed

**Timeline**:
- Application update: Immediate
- Fivetran sync: 5-30 minutes
- DLT pipeline: Next 6-hour run (or manual trigger)
- **Total**: Within 1 hour to 6 hours

---

### Option 2: Direct Database Update (If No Application Access)

If you can't update through the application, update the RDS database directly:

```sql
-- RUN THIS ON RDS PostgreSQL (production)
-- IMPORTANT: Get the exact company ID first

-- Step 1: Find the company
SELECT id, name, short_id, inserted_at
FROM companies
WHERE name = 'ResidentIQ';

-- Step 2: Update the name (replace UUID with actual ID from Step 1)
UPDATE companies
SET name = 'Inhabit',
    updated_at = NOW()
WHERE name = 'ResidentIQ'
  AND id = '<COMPANY_ID_FROM_STEP_1>';

-- Step 3: Verify the update
SELECT id, name, short_id, updated_at
FROM companies
WHERE name = 'Inhabit';
```

**After running this**:
1. Fivetran will sync the change automatically
2. Wait for DLT pipeline to run (every 6 hours) or trigger manually
3. Dashboards will reflect the change

---

### Option 3: Update in Unity Catalog (Not Recommended)

⚠️ **Warning**: This will be overwritten by Fivetran on next sync!

Only use this for temporary testing:

```sql
-- RUN IN DATABRICKS SQL EDITOR
-- This will be OVERWRITTEN by Fivetran!

-- Find the company in Unity Catalog
SELECT company_id, company_name, company_short_id
FROM product.fde.dim_fde
WHERE company_name = 'ResidentIQ'
GROUP BY ALL;

-- You cannot update Unity Catalog tables synced by Fivetran
-- They are read-only and will revert on next sync
```

**This option is not viable** because Fivetran-synced tables are managed externally.

---

## Verification Steps

After making the update at the source:

### 1. Verify in RDS (Source)

```sql
-- Check RDS database
SELECT name, updated_at
FROM companies
WHERE name LIKE '%Inhabit%';
```

### 2. Verify in Fivetran

1. Go to Fivetran dashboard
2. Check sync status for your RDS connector
3. Verify last sync timestamp > your update time

### 3. Verify in Unity Catalog

```sql
-- Check Unity Catalog (Databricks)
SELECT DISTINCT name
FROM rds.pg_rds_public.companies
WHERE name LIKE '%Inhabit%';
```

### 4. Verify in Gold Table

```sql
-- Check the gold table that dashboards use
SELECT DISTINCT company_name
FROM product.fde.dim_fde
WHERE company_name LIKE '%Inhabit%';
```

### 5. Verify in Dashboard

1. Open "Edited Submissions Dashboard - All Companies"
2. Check company filter dropdown
3. Search for "Inhabit"
4. Verify "ResidentIQ" is gone (unless historical data exists)

---

## Why Dashboards Don't Show "Inhabit" Yet

The dashboard queries the `product.fde.dim_fde` table, which gets its data from:

```
RDS companies.name (source)
  → Fivetran sync
  → rds.pg_rds_public.companies.name
  → DLT pipeline processes
  → product.fde.dim_fde.company_name
  → Dashboard displays
```

**The name hasn't propagated through this chain yet.**

---

## Historical Data Consideration

### Question: What about old submissions?

**Scenario**: If ResidentIQ submitted documents before the name change, should those historical records show "Inhabit" or "ResidentIQ"?

**Option A**: Update all historical records to "Inhabit"
- Pro: Consistent company name across all time periods
- Pro: Simpler reporting (one company name)
- Con: Loses historical accuracy

**Option B**: Keep historical records as "ResidentIQ", new records as "Inhabit"
- Pro: Historically accurate
- Con: Appears as two different companies in dashboards
- Con: More complex filtering in reports

**Recommendation**: **Option A** - Update all records to "Inhabit"

This is what happens automatically when you update the source database, because:
1. The company name is stored in the `companies` table (one record)
2. Submissions reference `company_id` (foreign key), not the name
3. Dashboards JOIN to get the current company name
4. All historical submissions will automatically show "Inhabit"

---

## Dashboard-Specific Considerations

### "Edited Submissions Dashboard - All Companies"

This dashboard likely:
1. Queries `product.fde.dim_fde` table
2. Filters by `company_name` column
3. Uses a dropdown or filter widget

**After the update**:
- "Inhabit" will appear in the company filter
- "ResidentIQ" will disappear (since it's the same company, just renamed)
- All historical submissions will show "Inhabit"

### Other Dashboards That May Be Affected

Check these dashboards/reports:
- [ ] Edited Submissions Dashboard - All Companies
- [ ] Company Performance Dashboard
- [ ] Submission Volume by Company
- [ ] Revenue by Partner
- [ ] Any report with company filters

**All will update automatically** once the source data changes.

---

## Code Changes Needed

### ✅ **NONE**

No code changes are required because:
1. Company names are not hardcoded in the pipeline
2. The DLT pipeline dynamically reads from source tables
3. Dashboards dynamically query the gold table
4. Everything updates automatically when source data changes

---

## Timeline & Next Steps

### Immediate Actions (You or Application Team)

1. **Update company name in source system**
   - Application admin panel OR
   - Direct RDS database update

2. **Verify Fivetran sync**
   - Check sync status
   - Wait for sync to complete (5-30 min)

3. **Trigger DLT pipeline** (optional - for faster update)
   ```bash
   # Use Databricks CLI or UI to trigger
   databricks jobs run-now --job-id 314473856953682
   ```

4. **Verify in dashboard**
   - Check "Edited Submissions Dashboard"
   - Look for "Inhabit" in company filter

### Data Engineering Team Actions

**No action required** unless:
- You need help updating the source database
- You want to verify data after the change
- Issues arise during propagation

### Estimated Timeline

| Step | Time | Status |
|------|------|--------|
| Update source database | 5 minutes | ⏳ Pending |
| Fivetran sync | 5-30 minutes | ⏳ Pending |
| DLT pipeline run | Next 6-hour cycle OR manual trigger (10 min) | ⏳ Pending |
| Dashboard reflects change | Immediate after DLT | ⏳ Pending |
| **Total** | **15 minutes - 6.5 hours** | ⏳ Pending |

---

## SQL Scripts for Verification

### Check Current Company Name

```sql
-- In Databricks SQL Editor
SELECT
  company_id,
  company_name,
  company_short_id,
  COUNT(*) as submission_count,
  MIN(submission_datetime) as first_submission,
  MAX(submission_datetime) as last_submission
FROM product.fde.dim_fde
WHERE company_name IN ('ResidentIQ', 'Inhabit')
GROUP BY company_id, company_name, company_short_id
ORDER BY company_name;
```

### Check if Name Exists in Any Form

```sql
-- Search for variations
SELECT DISTINCT company_name
FROM product.fde.dim_fde
WHERE LOWER(company_name) LIKE '%resident%'
   OR LOWER(company_name) LIKE '%inhabit%'
ORDER BY company_name;
```

### After Update - Verify Change

```sql
-- Confirm only "Inhabit" exists
SELECT
  COUNT(*) as total_submissions,
  COUNT(DISTINCT property_id) as unique_properties,
  MIN(submission_datetime) as earliest_submission,
  MAX(submission_datetime) as latest_submission
FROM product.fde.dim_fde
WHERE company_name = 'Inhabit';

-- Confirm "ResidentIQ" is gone
SELECT COUNT(*) as should_be_zero
FROM product.fde.dim_fde
WHERE company_name = 'ResidentIQ';
```

---

## Contact & Support

**For Questions**:
- **Data Engineering**: Review this document with your team
- **Application Team**: They can update the company name in the source system
- **Database Team**: They can run the UPDATE SQL if needed

**For Issues**:
- Dashboard still showing "ResidentIQ" after 6 hours → Check Fivetran sync status
- Both names appearing → Check if there are multiple company records
- Name not updating → Verify DLT pipeline ran successfully

---

## Summary Checklist

For whoever is making this change:

- [ ] Identify the source system (application or RDS database)
- [ ] Update company name from "ResidentIQ" to "Inhabit"
- [ ] Wait for Fivetran sync to complete
- [ ] Trigger DLT pipeline (optional - for faster update)
- [ ] Verify "Inhabit" appears in dashboard
- [ ] Verify "ResidentIQ" is gone from dashboard
- [ ] Test filtering by "Inhabit" in reports
- [ ] Notify stakeholders of completion

---

**Document Version**: 1.0
**Last Updated**: 2024-10-29
**Next Review**: After source data update is complete
