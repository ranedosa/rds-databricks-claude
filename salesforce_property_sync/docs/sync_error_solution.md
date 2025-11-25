# Sync Error Solution
## Salesforce Flow Governor Limit Issue

**Date:** 2025-11-21
**Sync ID:** 3325886
**Run ID:** 404267254

---

## 🚨 Problem Identified

All 1,297 records failed to sync due to a Salesforce Flow hitting governor limits.

### Error Message
```
CANNOT_EXECUTE_FLOW_TRIGGER: We can't save this record because the
"Product Property | After | Rollup Flow" process failed.

Limit Exceeded
Error ID: 1070455769-22115 (1629162666)
```

### What's Happening

When records are inserted into `product_property_c`, a Salesforce Flow called **"Product Property | After | Rollup Flow"** automatically triggers. This flow:

1. Performs calculations or rollups on the data
2. Updates related records
3. Runs queries and DML operations

When trying to process 1,297 records at once, the Flow hits Salesforce governor limits:
- ❌ Too many SOQL queries (>101)
- ❌ Too many DML statements (>150)
- ❌ CPU time exceeded (>10,000ms)
- ❌ Or other Salesforce limits

This causes ALL inserts to fail.

---

## ✅ Solution Options

### Option 1: Sync in Smaller Batches (RECOMMENDED) ⭐

**Pros:**
- No Salesforce changes needed
- Safest approach
- Flow still runs normally

**Cons:**
- Takes longer (multiple sync runs)
- Requires manual management

**How to do it:**

#### Method A: Use Census Batching
1. Go to your Census sync settings
2. Look for batch size or limit settings
3. Set to 50-100 records per sync
4. Run sync multiple times

#### Method B: Upload Smaller CSV Files
I've prepared batch files for you:
- `batch_001_first_50.csv` - First 50 records (test batch)
- Create additional batches as needed

**Steps:**
1. Start with `batch_001_first_50.csv` to test
2. Upload to Census and sync
3. If successful, continue with larger batches
4. Process all 1,297 records in ~13-26 batches (50-100 each)

---

### Option 2: Temporarily Disable the Flow

**Pros:**
- Can sync all records at once
- Fast

**Cons:**
- Requires Salesforce admin access
- Rollup calculations won't run during sync
- Need to re-enable and backfill calculations

**Steps:**
1. Contact Salesforce admin
2. Request to deactivate "Product Property | After | Rollup Flow"
3. Run Census sync with all 1,297 records
4. After sync completes, re-activate Flow
5. Manually trigger rollup calculations if needed

---

### Option 3: Optimize the Flow (Long-term)

**Pros:**
- Fixes root cause
- Better for future syncs
- More efficient

**Cons:**
- Requires Salesforce dev work
- Takes time to implement
- May need testing

**What to optimize:**
- Bulkify SOQL queries (query once for all records, not per record)
- Reduce DML operations
- Move heavy processing to asynchronous context
- Use collection-based processing

Contact your Salesforce admin/developer to review the Flow.

---

### Option 4: Use Asynchronous Processing

**Pros:**
- Higher governor limits for async
- Can process more records

**Cons:**
- Requires Flow modification
- Delayed processing

**Implementation:**
- Modify Flow to use `@InvocableMethod` with `async` callout
- Or create a Platform Event to trigger async processing
- Or use a Queueable/Batch Apex class

---

## 📋 Recommended Next Steps

### Immediate (Try This First)

1. **Test with 50 records:**
   - Upload `batch_001_first_50.csv` to Census
   - Run the sync
   - Verify all 50 records succeed

2. **If successful, increase batch size:**
   - Try 100 records next
   - Then 200 records
   - Find the optimal batch size that doesn't hit limits

3. **Process all 1,297 records:**
   - Split into appropriate batches
   - Sync each batch separately
   - Monitor for failures

### Alternative (If batching is too slow)

1. **Contact Salesforce Admin:**
   - Request to disable "Product Property | After | Rollup Flow"
   - Sync all 1,297 records at once
   - Re-enable Flow after sync

2. **Long-term fix:**
   - Have Salesforce team optimize the Flow
   - Implement better bulkification
   - Consider async processing

---

## 🔍 Validation

After successful sync, verify:

### 1. Check product_property_c
```sql
-- Databricks
SELECT COUNT(*)
FROM hive_metastore.salesforce.product_property_c
WHERE DATE(created_date) = CURRENT_DATE()
  AND reverse_etl_id_c IS NOT NULL
```
Should return your synced record count.

### 2. Verify property_c creation
```sql
-- Databricks (wait 10-15 min after sync for workflows)
SELECT COUNT(*)
FROM hive_metastore.salesforce.product_property_c pp
INNER JOIN hive_metastore.salesforce.property_c p
    ON pp.sf_property_id_c = p.id
WHERE DATE(pp.created_date) = CURRENT_DATE()
```
Should show records flowed to final table.

### 3. Check RDS linkage
```sql
-- Databricks
SELECT
    rds.id,
    rds.name,
    sf.snappt_property_id_c,
    sf.name
FROM rds.pg_rds_public.properties rds
INNER JOIN hive_metastore.salesforce.product_property_c sf
    ON CAST(rds.id AS STRING) = sf.snappt_property_id_c
WHERE DATE(sf.created_date) = CURRENT_DATE()
LIMIT 10
```
Should show matching records.

---

## 📊 Batch Files Available

Location: `/Users/danerosa/rds_databricks_claude/output/sync_payloads/`

- **Full file:** `sync_payload_ACTIVE_only_20251121_104454.csv` (1,297 records)
- **Test batch:** `batch_001_first_50.csv` (50 records)

To create more batches:
```bash
cd /Users/danerosa/rds_databricks_claude/output/sync_payloads/

# Batch 2: Records 51-100
tail -n +52 sync_payload_ACTIVE_only_20251121_104454.csv | head -50 > batch_002_records_51-100.csv

# Batch 3: Records 101-150
tail -n +102 sync_payload_ACTIVE_only_20251121_104454.csv | head -50 > batch_003_records_101-150.csv
```

---

## 🆘 Need Help?

If batching doesn't work or you hit other errors:

1. Check Census sync logs for new error messages
2. Verify batch size isn't still too large
3. Contact Salesforce admin to review Flow
4. Consider temporarily disabling Flow

**Census Run Details:**
https://app.getcensus.com/workspaces/33026/syncs/3325886/sync-runs/404267254

---

## Summary

**Problem:** Salesforce Flow hitting governor limits when processing 1,297 records
**Solution:** Sync in smaller batches (50-100 records at a time)
**Alternative:** Temporarily disable Flow, sync all, re-enable
**Long-term:** Optimize the Flow for better bulkification
