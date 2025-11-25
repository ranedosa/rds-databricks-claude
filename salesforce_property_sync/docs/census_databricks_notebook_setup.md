# Census + Databricks Notebook Setup

**Notebook Uploaded:** ✅ `/Users/dane@snappt.com/product_property_feature_sync`

---

## Quick Start

Your Databricks notebook is ready to use! Here's how to connect it to Census:

### Databricks Notebook Location

```
/Users/dane@snappt.com/product_property_feature_sync
```

**Direct Link:**
```
https://dbc-9ca0f5e0-2208.cloud.databricks.com/#notebook/XXXXX
```
(Replace XXXXX with the notebook ID - you'll see it when you open the notebook in Databricks)

---

## What's In The Notebook

The notebook has **3 query options** you can choose from:

### Option 1: One-Time Backfill (Today's Properties)
- **Use for:** Fixing the 1,296 properties synced today
- **Query:** `WHERE DATE(sf.created_date) = CURRENT_DATE()`
- **When to run:** Right now (one-time)

### Option 2: Ongoing Sync (Mismatched Feature Data) ⭐ **RECOMMENDED**
- **Use for:** Regular scheduled sync
- **Query:** Only syncs properties where SF data != actual data
- **When to run:** Hourly or daily on cron
- **Benefit:** Efficient - only updates what needs updating

### Option 3: Recent Updates (Last 7 Days)
- **Use for:** Daily catch-up sync
- **Query:** Properties created/updated in last week
- **When to run:** Daily at 2am

---

## Census Configuration

### Step 1: Create Census Model

1. Go to Census → Models → New Model
2. **Model Name:** `Product Property Feature Sync`
3. **Connection:** Your Databricks connection
4. **Source Type:** Notebook or SQL
5. **Notebook Path:** `/Users/dane@snappt.com/product_property_feature_sync`
6. **Cell to Execute:** Choose Option 1, 2, or 3 (I recommend **Option 2**)

If using SQL instead of notebook:
- Copy the SQL from the notebook cell you want to use
- Paste into Census SQL model

### Step 2: Create Census Sync

1. Go to Census → Syncs → New Sync
2. **Source:** The model you created above
3. **Destination:** Salesforce → `Product_Property__c`

### Step 3: Configure Sync Settings

**Sync Key:**
- Salesforce Field: `Reverse_ETL_ID__c` (External ID)
- Model Field: `reverse_etl_id_c`

**Sync Behavior:**
- **UPDATE** existing records (NOT insert or upsert)
- **Do NOT** create new records

**Why UPDATE only?**
- These properties already exist in Salesforce
- We're just fixing the feature data fields

### Step 4: Field Mappings

Map all 23 feature fields:

| Source Field (Databricks) | Destination Field (Salesforce) |
|---------------------------|-------------------------------|
| `snappt_property_id_c` | `snappt_property_id_c` |
| `reverse_etl_id_c` | `reverse_etl_id_c` |
| `fraud_detection_enabled_c` | `fraud_detection_enabled_c` |
| `fraud_detection_start_date_c` | `fraud_detection_start_date_c` |
| `fraud_detection_updated_date_c` | `fraud_detection_updated_date_c` |
| `income_verification_enabled_c` | `income_verification_enabled_c` |
| `income_verification_start_date_c` | `income_verification_start_date_c` |
| `income_verification_updated_date_c` | `income_verification_updated_date_c` |
| `id_verification_enabled_c` | `id_verification_enabled_c` |
| `id_verification_start_date_c` | `id_verification_start_date_c` |
| `id_verification_updated_date_c` | `id_verification_updated_date_c` |
| `idv_only_enabled_c` | `idv_only_enabled_c` |
| `idv_only_start_date_c` | `idv_only_start_date_c` |
| `idv_only_updated_date_c` | `idv_only_updated_date_c` |
| `connected_payroll_enabled_c` | `connected_payroll_enabled_c` |
| `connected_payroll_start_date_c` | `connected_payroll_start_date_c` |
| `connected_payroll_updated_date_c` | `connected_payroll_updated_date_c` |
| `bank_linking_enabled_c` | `bank_linking_enabled_c` |
| `bank_linking_start_date_c` | `bank_linking_start_date_c` |
| `bank_linking_updated_date_c` | `bank_linking_updated_date_c` |
| `verification_of_rent_enabled_c` | `verification_of_rent_enabled_c` |
| `vor_start_date_c` | `vor_start_date_c` |
| `vor_updated_date_c` | `vor_updated_date_c` |

**Quick Tip:** Census can usually auto-map fields with identical names!

### Step 5: Schedule

**For Option 1 (Backfill):**
- Run manually one time
- No schedule needed

**For Option 2 (Ongoing - Recommended):**
- Schedule: Every 1 hour (or daily)
- This will automatically fix any mismatches
- Safe to run frequently (only syncs what needs updating)

**For Option 3 (Recent Updates):**
- Schedule: Daily at 2:00 AM
- Catches new/updated properties from last week

---

## Testing Before Full Rollout

**Recommended:** Test with Option 1 first (today's properties)

1. Create sync using Option 1 query
2. Run manually
3. Check first 50 records succeed
4. If successful, let it complete
5. Validate results (see below)
6. Then switch to Option 2 for ongoing sync

---

## Validation

After running the sync, validate it worked:

```bash
source venv/bin/activate
export DATABRICKS_TOKEN="YOUR_DATABRICKS_TOKEN"
python scripts/validate_feature_data.py
```

**Expected result:**
```
✅ RESULT: 0 properties with mismatched feature data
```

Or run the validation query in the notebook:
- Open notebook in Databricks
- Scroll to "Validation Query" cell
- Run it
- Should show 0 mismatches after sync completes

---

## Troubleshooting

### Issue: "Reverse_ETL_ID__c not found in dropdown"

**Solution:** Use `snappt_property_id_c` as sync key instead
- Both fields have the same value (property UUID)
- Both are marked as External ID in Salesforce

### Issue: "Flow governor limit exceeded"

**Solution:** Sync is trying to update too many records at once

**Options:**
1. Ask Salesforce admin to temporarily disable "Product Property | After | Rollup Flow"
2. Use the batch CSV files instead:
   - `/output/sync_payloads/feature_backfill_batches/`
   - Upload 50 records at a time
3. Use Option 2 query (only syncs mismatches - fewer records)

### Issue: "Field not found in Salesforce"

**Problem:** Feature fields may not exist in Salesforce

**Solution:** Work with Salesforce admin to add custom fields
- See field list in `/docs/product_features_sync_plan.md`
- Or verify fields exist: `/scripts/analyze_product_property_features.py` confirmed they exist

---

## Going Forward

### For Immediate Backfill (Today)

1. Use **Option 1** query to fix today's 1,296 properties
2. Run once manually
3. Validate results

### For Long-Term Maintenance (This Week)

1. Switch to **Option 2** query for ongoing sync
2. Schedule to run hourly or daily
3. Will automatically catch and fix any future mismatches

### For New Property Syncs (Permanent Fix)

Update your main property sync to include feature data from the start:
- See `/scripts/generate_sync_with_features.py` for full query
- Add `LEFT JOIN crm.sfdc_dbx.product_property_w_features` to your Census property sync
- Future new properties will have correct feature data from day 1

---

## Files Reference

**Databricks Notebook:**
- `/Users/dane@snappt.com/product_property_feature_sync` (in Databricks)
- `/notebooks/product_property_feature_sync.py` (local copy)

**CSV Backup (if needed):**
- `/output/sync_payloads/feature_backfill_20251121.csv` (full dataset)
- `/output/sync_payloads/feature_backfill_batches/` (26 batch files)

**Documentation:**
- `/docs/URGENT_feature_backfill_required.md` (detailed problem analysis)
- `/docs/product_features_sync_plan.md` (implementation plan)
- `/BACKFILL_QUICKSTART.md` (quick reference)

**Scripts:**
- `/scripts/validate_feature_data.py` (validation)
- `/scripts/generate_feature_backfill.py` (CSV generator)

---

## Summary

✅ Databricks notebook created and uploaded
✅ 3 query options available (choose based on your needs)
✅ Ready to connect to Census
✅ CSV backups available if needed

**Recommended Path:**
1. Open notebook in Databricks to familiarize yourself
2. Create Census model using Option 2 (ongoing sync)
3. Test sync with a few records first
4. Schedule to run hourly/daily
5. Monitor for a few days
6. Update main property sync to include features going forward

**Need help?** The notebook has detailed comments and documentation in each cell!
