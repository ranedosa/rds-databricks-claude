# SOLUTION: Reset and Re-sync enterprise_property Table

## Problem Summary
- PostgreSQL has 3,398 rows
- Databricks has 1 row with EMPTY `ctid_fivetran_id` primary key
- Fivetran can't MERGE/INSERT because PK matching fails
- Missing: 3,397 rows

## Root Cause
The `ctid_fivetran_id` column in Databricks is empty (""), preventing Fivetran from matching and inserting rows.

---

## SOLUTION: Complete Table Reset

### Step 1: Verify PostgreSQL State

Run in PostgreSQL:
```sql
-- Verify PKs are valid in source
SELECT
    COUNT(*) as total_rows,
    COUNT(DISTINCT ctid_fivetran_id) as unique_pks,
    SUM(CASE WHEN ctid_fivetran_id IS NULL OR ctid_fivetran_id = '' THEN 1 ELSE 0 END) as empty_pks
FROM pg_rds_enterprise_public.enterprise_property;
```

**Expected result**:
- total_rows: 3398
- unique_pks: 3398
- empty_pks: 0

If empty_pks > 0, you need to fix PostgreSQL first!

---

### Step 2: Drop and Recreate Table in Databricks

```sql
-- In Databricks SQL

-- 1. Drop the corrupted table
DROP TABLE IF EXISTS rds.pg_rds_enterprise_public.enterprise_property;

-- Note: This will also remove the row filter
```

---

### Step 3: Reset Table in Fivetran

1. **Log into Fivetran Dashboard**
   - Navigate to your RDS PostgreSQL connector

2. **Reset the enterprise_property table**:
   - Find `enterprise_property` in the list of tables
   - Click the **three dots (...)** menu
   - Select **"Reset table"** or **"Re-sync table"**
   - Confirm the reset

3. **Start the sync**:
   - Fivetran will recreate the table from scratch
   - It will sync all 3,398 rows
   - This may take a few minutes

4. **Monitor the sync**:
   - Watch the Fivetran dashboard
   - Check for "Sync Status: Synced"
   - Verify "Rows synced: 3,398"

---

### Step 4: Verify in Databricks

```sql
-- Check row count
SELECT COUNT(*) as total_rows
FROM rds.pg_rds_enterprise_public.enterprise_property;
-- Expected: 3398

-- Check PK uniqueness
SELECT
    COUNT(*) as total_rows,
    COUNT(DISTINCT ctid_fivetran_id) as unique_pks,
    SUM(CASE WHEN ctid_fivetran_id IS NULL OR ctid_fivetran_id = '' THEN 1 ELSE 0 END) as empty_pks
FROM rds.pg_rds_enterprise_public.enterprise_property;
-- Expected: 3398, 3398, 0

-- Sample data
SELECT ctid_fivetran_id, id, _fivetran_deleted
FROM rds.pg_rds_enterprise_public.enterprise_property
LIMIT 10;
-- Should show valid ctid_fivetran_id values like "(0,1)_uuid"
```

---

### Step 5: Re-apply Row Filter (if needed)

If you need the row filter back:

```sql
-- Create or recreate the filter function
CREATE OR REPLACE FUNCTION rds.pg_rds_enterprise_public.filter_deleted_rows(_fivetran_deleted BOOLEAN)
RETURNS BOOLEAN
RETURN _fivetran_deleted = false;

-- Apply row filter
ALTER TABLE rds.pg_rds_enterprise_public.enterprise_property
SET ROW FILTER rds.pg_rds_enterprise_public.filter_deleted_rows ON (_fivetran_deleted);
```

---

## Alternative: Fix Without Dropping Table

If you can't drop the table, try this:

### Option A: Update the Empty PK Row

```sql
-- In Databricks, update the 1 row with empty PK
-- Set it to a unique value that won't conflict
UPDATE rds.pg_rds_enterprise_public.enterprise_property
SET ctid_fivetran_id = '(747,3)_' || id
WHERE ctid_fivetran_id = '' OR ctid_fivetran_id IS NULL;
```

Then trigger a Fivetran sync.

### Option B: Delete the Corrupted Row

```sql
-- Delete the 1 row with empty PK
DELETE FROM rds.pg_rds_enterprise_public.enterprise_property
WHERE ctid_fivetran_id = '' OR ctid_fivetran_id IS NULL;
```

Then reset the table in Fivetran.

---

## Post-Fix Monitoring

After the fix, monitor for:

1. **Row count stability**:
   ```sql
   SELECT COUNT(*) FROM rds.pg_rds_enterprise_public.enterprise_property;
   ```

2. **No empty PKs**:
   ```sql
   SELECT COUNT(*) FROM rds.pg_rds_enterprise_public.enterprise_property
   WHERE ctid_fivetran_id = '' OR ctid_fivetran_id IS NULL;
   -- Should always return 0
   ```

3. **Fivetran sync status**:
   - Check dashboard regularly
   - Set up alerts for sync failures

---

## Prevention

To prevent this from happening again:

1. **Add data quality checks in Fivetran**:
   - Set up alerts for row count discrepancies
   - Monitor for NULL/empty primary keys

2. **Regular audits**:
   - Compare row counts: PostgreSQL vs Databricks
   - Check for sync lag or errors

3. **Consider adding a CHECK constraint** (if possible):
   ```sql
   ALTER TABLE rds.pg_rds_enterprise_public.enterprise_property
   ADD CONSTRAINT check_pk_not_empty
   CHECK (ctid_fivetran_id IS NOT NULL AND ctid_fivetran_id != '');
   ```

---

## Estimated Time

- Drop table: 1 minute
- Fivetran reset and re-sync: 5-15 minutes (depending on data size)
- Verification: 2 minutes

**Total: ~20 minutes**

---

## Need Help?

If you encounter issues:

1. **Check Fivetran logs** for specific error messages
2. **Check Databricks permissions** - ensure Fivetran can write to the table
3. **Contact Fivetran support** with:
   - Connector ID
   - Table name: enterprise_property
   - Error: "PK column ctid_fivetran_id is empty in destination"

---

**Document created**: 2025-10-27
**Issue**: Missing 3,397 rows due to empty primary key
**Status**: Solution provided, awaiting implementation
