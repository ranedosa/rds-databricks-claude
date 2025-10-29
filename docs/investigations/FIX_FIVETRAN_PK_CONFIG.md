# FIX: Configure Correct Primary Key in Fivetran

## Problem
Fivetran is using `ctid_fivetran_id` as the primary key instead of the actual primary key column (`id`).

## Root Cause
- Fivetran uses `ctid` as a fallback PK when no primary key is detected
- This causes MERGE operations to fail because `ctid_fivetran_id` is empty/invalid
- The actual primary key should be `id` (UUID column)

---

## Step 1: Verify Primary Key in PostgreSQL

Run in PostgreSQL:

```sql
-- Check current primary key definition
SELECT
    tc.constraint_name,
    kcu.column_name,
    tc.constraint_type
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_schema = 'pg_rds_enterprise_public'
    AND tc.table_name = 'enterprise_property'
    AND tc.constraint_type = 'PRIMARY KEY';

-- Check if 'id' is unique and not null
SELECT
    COUNT(*) as total_rows,
    COUNT(DISTINCT id) as unique_ids,
    COUNT(*) - COUNT(DISTINCT id) as duplicates,
    SUM(CASE WHEN id IS NULL THEN 1 ELSE 0 END) as null_ids
FROM pg_rds_enterprise_public.enterprise_property;
```

### Expected Results:

**If `id` is NOT the PK in PostgreSQL:**
- First query returns NO ROWS or shows different column
- You need to add PK constraint in PostgreSQL (see Step 2)

**If `id` IS the PK in PostgreSQL:**
- First query shows: `column_name = 'id'`
- Fivetran just didn't detect it
- Skip to Step 3

---

## Step 2: Add Primary Key in PostgreSQL (If Missing)

**ONLY if PostgreSQL doesn't have a PK defined:**

```sql
-- Add primary key constraint on 'id' column
ALTER TABLE pg_rds_enterprise_public.enterprise_property
ADD CONSTRAINT enterprise_property_pkey PRIMARY KEY (id);
```

**⚠️ WARNING:** This will fail if:
- `id` has NULL values (fix: UPDATE NULL ids first)
- `id` has duplicates (fix: deduplicate first)

Check the results from Step 1 queries to ensure:
- unique_ids = total_rows (no duplicates)
- null_ids = 0 (no nulls)

---

## Step 3: Configure Fivetran to Use Correct Primary Key

### Option A: Via Fivetran Dashboard (Recommended)

1. **Log into Fivetran Dashboard**
   - Go to https://fivetran.com/dashboard

2. **Navigate to Your Connector**
   - Find your RDS PostgreSQL → Databricks connector
   - Click to open connector details

3. **Go to Schema Tab**
   - Click on "Schema" in the top navigation

4. **Find enterprise_property Table**
   - Scroll to `pg_rds_enterprise_public.enterprise_property`
   - Click on the table name to expand

5. **Change Primary Key Configuration**
   - Look for "Primary Key" or "Key Columns" setting
   - **Uncheck** `ctid_fivetran_id` (if checked)
   - **Check** `id` as the primary key
   - Click "Save" or "Apply Changes"

6. **Reset Table**
   - Click the **three dots (...)** menu next to the table
   - Select **"Reset table"**
   - Confirm the reset

7. **Start Sync**
   - The connector will re-sync the table using `id` as PK
   - Monitor the sync progress

### Option B: Via Fivetran API

If you prefer to use the API:

```bash
# Get connector ID
curl -X GET 'https://api.fivetran.com/v1/connectors' \
  -u 'YOUR_API_KEY:YOUR_API_SECRET' \
  | jq '.data.items[] | select(.schema == "pg_rds_enterprise_public")'

# Update table primary key configuration
curl -X PATCH 'https://api.fivetran.com/v1/connectors/{connector_id}/schemas/pg_rds_enterprise_public/tables/enterprise_property' \
  -u 'YOUR_API_KEY:YOUR_API_SECRET' \
  -H 'Content-Type: application/json' \
  -d '{
    "columns": {
      "id": {
        "primary_key": true
      },
      "ctid_fivetran_id": {
        "primary_key": false
      }
    }
  }'

# Reset the table
curl -X POST 'https://api.fivetran.com/v1/connectors/{connector_id}/schemas/pg_rds_enterprise_public/tables/enterprise_property/resync' \
  -u 'YOUR_API_KEY:YOUR_API_SECRET'
```

---

## Step 4: Drop Corrupted Table in Databricks

Before Fivetran re-syncs, drop the corrupted table:

```sql
-- In Databricks SQL
DROP TABLE IF EXISTS rds.pg_rds_enterprise_public.enterprise_property;
```

This ensures Fivetran recreates it with the correct schema.

---

## Step 5: Monitor Fivetran Sync

1. **Watch the Fivetran dashboard**
   - Status should change to "Syncing"
   - Look for "Rows synced" counter

2. **Expected behavior:**
   - Fivetran recreates the table in Databricks
   - Uses `id` as the primary key
   - Syncs all 3,398 rows
   - MERGE operations use `id` for matching

3. **Sync completion:**
   - Status: "Synced"
   - Rows synced: 3,398
   - No errors

---

## Step 6: Verify in Databricks

```sql
-- Check row count
SELECT COUNT(*) as total_rows
FROM rds.pg_rds_enterprise_public.enterprise_property;
-- Expected: 3398

-- Check primary key constraint
DESCRIBE TABLE EXTENDED rds.pg_rds_enterprise_public.enterprise_property;
-- Look for: PRIMARY KEY constraint on 'id'

-- Verify 'id' is populated and unique
SELECT
    COUNT(*) as total_rows,
    COUNT(DISTINCT id) as unique_ids,
    SUM(CASE WHEN id IS NULL OR id = '' THEN 1 ELSE 0 END) as empty_ids
FROM rds.pg_rds_enterprise_public.enterprise_property;
-- Expected: 3398, 3398, 0

-- Check if ctid_fivetran_id still exists (it might, but won't be the PK)
SELECT
    id,
    ctid_fivetran_id,
    _fivetran_deleted,
    _fivetran_synced
FROM rds.pg_rds_enterprise_public.enterprise_property
LIMIT 5;
-- 'id' should have valid UUIDs
-- ctid_fivetran_id might still exist but not be used for MERGE
```

---

## Step 7: Verify Future Syncs Work

After a few Fivetran sync cycles, check:

```sql
-- Monitor row count over time
SELECT COUNT(*) FROM rds.pg_rds_enterprise_public.enterprise_property;

-- Check recent sync activity
SELECT
    MAX(_fivetran_synced) as last_sync,
    COUNT(*) as total_rows
FROM rds.pg_rds_enterprise_public.enterprise_property;
```

---

## Why This Fixes the Issue

### Before (Broken):
```
MERGE on ctid_fivetran_id:
  - Databricks has: ctid_fivetran_id = "" (empty)
  - PostgreSQL has: ctid_fivetran_id = "(x,y)_uuid"
  - No matches → Inserts fail → Only 1 row
```

### After (Fixed):
```
MERGE on id:
  - Databricks has: id = "uuid-1", "uuid-2", ...
  - PostgreSQL has: id = "uuid-1", "uuid-2", ...
  - Perfect matches → Updates work → Inserts work → 3,398 rows ✓
```

---

## Alternative: Keep ctid_fivetran_id as PK (Not Recommended)

If you must keep `ctid_fivetran_id` as the PK:

1. **Fix in PostgreSQL** - Ensure ctid_fivetran_id is populated:
   ```sql
   -- This is NOT standard practice and NOT recommended
   ALTER TABLE pg_rds_enterprise_public.enterprise_property
   ADD COLUMN IF NOT EXISTS ctid_fivetran_id TEXT;

   UPDATE pg_rds_enterprise_public.enterprise_property
   SET ctid_fivetran_id = ctid::text || '_' || id::text;

   ALTER TABLE pg_rds_enterprise_public.enterprise_property
   ADD CONSTRAINT enterprise_property_ctid_pkey PRIMARY KEY (ctid_fivetran_id);
   ```

**⚠️ NOT RECOMMENDED because:**
- `ctid` changes during VACUUM operations
- Breaks referential integrity
- Violates database best practices

---

## Troubleshooting

### Issue: Fivetran won't let me change the PK

**Solution:**
- You may need to "Disconnect" and "Reconnect" the table
- Or contact Fivetran support to reset the schema

### Issue: PostgreSQL says PK already exists on 'id'

**Solution:**
- Great! Just reset the table in Fivetran
- Fivetran should auto-detect the correct PK

### Issue: 'id' has duplicates in PostgreSQL

**Solution:**
```sql
-- Find duplicates
SELECT id, COUNT(*) as count
FROM pg_rds_enterprise_public.enterprise_property
GROUP BY id
HAVING COUNT(*) > 1;

-- Decide which rows to keep, then delete duplicates
-- OR investigate why duplicates exist
```

---

## Prevention

**Best Practices:**

1. **Always define explicit PRIMARY KEYs in PostgreSQL**
   ```sql
   ALTER TABLE your_table ADD PRIMARY KEY (id);
   ```

2. **Verify Fivetran detects correct PK during setup**
   - Check Schema tab after initial sync
   - Ensure PK column shows checkmark

3. **Monitor sync health**
   - Set up alerts for row count discrepancies
   - Compare PostgreSQL vs Databricks counts regularly

4. **Document primary keys**
   - Keep schema documentation updated
   - Note which columns are PKs in each table

---

## Estimated Time

- Check PostgreSQL PK: 2 minutes
- Add PK (if missing): 2 minutes
- Configure Fivetran: 5 minutes
- Drop Databricks table: 1 minute
- Fivetran re-sync: 10-15 minutes
- Verification: 3 minutes

**Total: ~25-30 minutes**

---

## Summary

**The core issue:**
- Fivetran is using the wrong primary key (`ctid_fivetran_id` instead of `id`)
- This causes MERGE failures and missing rows

**The fix:**
1. Verify `id` is the PK in PostgreSQL (or add it if missing)
2. Configure Fivetran to use `id` as the primary key
3. Reset the table in Fivetran
4. Verify 3,398 rows sync successfully

**Result:**
- All 3,398 rows will sync correctly
- Future updates will work properly
- MERGE operations will use the correct key

---

**Issue identified by:** User (excellent troubleshooting!)
**Date:** 2025-10-27
**Status:** Solution provided, awaiting PostgreSQL verification
