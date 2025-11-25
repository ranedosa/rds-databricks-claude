# Phase 1 Quick Start: New Properties View

**Goal:** Create Databricks view that Census can use to sync new properties with feature data

**Time Required:** 30 minutes

**Status:** ✅ Assets created and ready

---

## What Was Created

### 1. Databricks Notebook
**Location:** `/Users/dane@snappt.com/new_properties_with_features_view`

**What it does:**
- Creates schema `crm.sfdc_dbx` if needed
- Creates view `crm.sfdc_dbx.new_properties_with_features`
- Includes validation queries
- Shows sample data

**View contents:**
- All ACTIVE properties from RDS not yet in Salesforce
- Complete feature data (all 23 feature fields)
- All property fields needed for Salesforce (21 fields)
- Total: 45 fields ready for Census sync

### 2. Validation Script
**Location:** `/scripts/validate_new_properties_view.py`

**What it does:**
- Verifies view was created correctly
- Counts new properties
- Checks feature data statistics
- Validates data quality
- Shows sample records
- Confirms no overlap with existing Salesforce properties

---

## Step-by-Step Implementation

### Step 1: Run the Databricks Notebook (10 minutes)

**Option A: In Databricks UI**
1. Go to Databricks workspace
2. Navigate to `/Users/dane@snappt.com/new_properties_with_features_view`
3. Click "Run All" button
4. Wait for all cells to complete (should take ~1-2 minutes)
5. Review the output:
   - Cell 4 shows count of new properties
   - Cell 5 shows sample data
   - Cell 6 shows data quality check

**Option B: Via API** (if you want to automate)
```bash
# Not needed for now - just use UI
```

### Step 2: Validate the View (5 minutes)

Run the validation script:

```bash
source venv/bin/activate
export DATABRICKS_TOKEN="YOUR_DATABRICKS_TOKEN"
python scripts/validate_new_properties_view.py
```

**Expected output:**
```
✅ View exists with 45 columns
✅ Found X properties ready to sync
✅ Feature enablement breakdown shows correct percentages
✅ No data quality issues found
✅ No overlap with existing Salesforce properties
```

**What the validation checks:**
1. View exists and is accessible
2. Record count is reasonable
3. Feature data is present
4. No missing required fields
5. Sample records look correct
6. No properties already in Salesforce

### Step 3: Review the Data (5 minutes)

In the notebook output or validation script, review:

**Key metrics:**
- **Total new properties:** Should be reasonable (not thousands)
- **Feature breakdown:** Shows how many have each product
- **Sample records:** Names and locations look correct

**Common scenarios:**

**If count = 0:**
✅ Great! All properties are already in Salesforce
- View is ready for future use
- Skip to Phase 2 setup (configure Census)
- When new properties appear, Census will sync them

**If count = 1-100:**
✅ Perfect! Normal amount of missing properties
- These will be synced when Census is configured
- Proceed to Phase 2

**If count > 1000:**
⚠️ Investigate why so many are missing
- Could be legitimate backlog
- Or could indicate sync issues
- Consider syncing in batches

### Step 4: Document Current State (5 minutes)

Record these numbers for future reference:

```
View created: [DATE]
Properties ready to sync: [COUNT]
Feature data present: [YES/NO]
Sample property names: [LIST A FEW]
Next action: Configure Census (Phase 2)
```

---

## What You Have Now

✅ **View created:** `crm.sfdc_dbx.new_properties_with_features`
✅ **View tested:** Validation passed
✅ **Data verified:** Records and features look correct
✅ **Ready for Census:** View can be connected to Census model

---

## Troubleshooting

### Issue: Notebook fails to run

**Error: "Table or view not found"**

**Check:**
- Is `rds.pg_rds_public.properties` accessible?
- Is `crm.sfdc_dbx.product_property_w_features` accessible?
- Is `hive_metastore.salesforce.product_property_c` accessible?

**Fix:**
- Verify table paths in notebook
- Check warehouse has access to these schemas
- Contact data team if tables are missing

---

### Issue: View is empty (0 records)

**Possible causes:**
1. All properties already in Salesforce (good!)
2. Warehouse doesn't have access to RDS tables
3. Query filter too restrictive

**Verify:**
```sql
-- Check RDS has ACTIVE properties
SELECT COUNT(*) FROM rds.pg_rds_public.properties
WHERE status = 'ACTIVE';

-- Check Salesforce has properties
SELECT COUNT(*) FROM hive_metastore.salesforce.product_property_c;

-- Check for properties NOT in Salesforce
SELECT COUNT(*) FROM rds.pg_rds_public.properties rds
LEFT JOIN hive_metastore.salesforce.product_property_c sf
ON CAST(rds.id AS STRING) = sf.snappt_property_id_c
WHERE sf.snappt_property_id_c IS NULL
AND rds.status = 'ACTIVE';
```

---

### Issue: Feature data all False

**Check:**
```sql
-- Verify product_property_w_features has data
SELECT COUNT(*)
FROM crm.sfdc_dbx.product_property_w_features
WHERE fraud_enabled = TRUE OR iv_enabled = TRUE;
```

If this returns 0, the source table might be empty or not synced yet.

---

### Issue: Validation script fails

**Error: "Cannot connect to Databricks"**

**Fix:**
- Check `DATABRICKS_TOKEN` environment variable is set
- Verify token hasn't expired
- Check network connectivity

**Error: "View doesn't exist"**

**Fix:**
- Run the notebook first
- Check view name is correct
- Verify schema `crm.sfdc_dbx` exists

---

## View Query Explained

### The JOIN logic:

```sql
FROM rds.pg_rds_public.properties rds          -- Source: RDS properties
LEFT JOIN product_property_w_features feat      -- Add: Feature data
LEFT JOIN salesforce.product_property_c sf      -- Check: Already in SF?
WHERE sf.snappt_property_id_c IS NULL           -- Filter: NOT in SF
```

**Why LEFT JOIN?**
- Not all properties have feature data (new properties)
- We want to include them anyway (with all False flags)

**Why check Salesforce?**
- Ensures we don't try to insert duplicates
- View automatically shrinks as properties get synced

**Self-filtering:**
- As Census syncs properties to Salesforce
- They automatically disappear from this view
- View always shows "what's left to sync"

---

## Monitoring Query

After Phase 2 (Census setup), run this periodically:

```sql
-- How many properties waiting to sync?
SELECT COUNT(*) FROM crm.sfdc_dbx.new_properties_with_features;
```

**Expected behavior:**
- Should decrease over time as Census syncs
- Should stay near 0 between syncs
- Should increase slightly when new properties created

**Alert if:**
- Number keeps growing (Census not running?)
- Number stays high (Census errors?)
- Sudden spike (backlog created?)

---

## Next Steps

After Phase 1 is complete:

**Phase 2: Configure Census (1 hour)**
1. Create Census model from this view
2. Set up INSERT sync to Salesforce
3. Map all 45 fields
4. Test with first 10 records
5. Schedule daily sync at 2am

**See:** `/docs/FUTURE_ARCHITECTURE_automated_property_sync.md` for Phase 2 details

---

## Quick Commands Reference

**Run notebook in Databricks:**
```
1. Open: /Users/dane@snappt.com/new_properties_with_features_view
2. Click: "Run All"
3. Wait: ~2 minutes
```

**Validate the view:**
```bash
source venv/bin/activate
export DATABRICKS_TOKEN="YOUR_DATABRICKS_TOKEN"
python scripts/validate_new_properties_view.py
```

**Check view manually:**
```sql
-- In Databricks SQL editor
SELECT COUNT(*) FROM crm.sfdc_dbx.new_properties_with_features;
SELECT * FROM crm.sfdc_dbx.new_properties_with_features LIMIT 10;
```

---

## Assets Created

| Asset | Location | Purpose |
|-------|----------|---------|
| Databricks notebook | `/Users/dane@snappt.com/new_properties_with_features_view` | Creates the view |
| Local notebook copy | `/notebooks/new_properties_with_features_view.py` | Backup/reference |
| Validation script | `/scripts/validate_new_properties_view.py` | Tests the view |
| This guide | `/docs/PHASE_1_QUICKSTART.md` | Implementation steps |

---

## Success Criteria

✅ **View exists:** `crm.sfdc_dbx.new_properties_with_features`
✅ **View has data:** Count > 0 or confirmed all properties already synced
✅ **Feature data present:** At least some properties have features enabled
✅ **No data quality issues:** Required fields populated
✅ **No overlap:** Properties in view are NOT in Salesforce
✅ **Validation passes:** Script completes without errors

**When all criteria met: Phase 1 Complete! ✅**

Proceed to Phase 2: Census Configuration

---

**Questions?** See `/docs/FUTURE_ARCHITECTURE_automated_property_sync.md` for complete architecture details.
