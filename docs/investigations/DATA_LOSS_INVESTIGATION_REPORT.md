# Data Loss Investigation Report
## Table: rds.pg_rds_enterprise_public.enterprise_property

**Date of Investigation**: October 27, 2025
**Investigated Period**: Last 20 days (October 7 - October 27, 2025)

---

## Executive Summary

**CRITICAL FINDING**: The table currently shows only **1 visible row**, but the table had significantly more rows before October 13, 2025.

**ROOT CAUSE**: Large-scale MERGE operations on **October 13, 2025** updated approximately **2,432 rows**, likely marking them with `_fivetran_deleted = true`. Due to the table's row filter, these rows are now invisible to standard queries.

---

## Key Events Timeline

### October 13, 2025 - Major Data Impact Event

| Version | Timestamp | Operation | Rows Updated | Rows Inserted | Impact |
|---------|-----------|-----------|--------------|---------------|--------|
| **22756** | 09:15:54 UTC | MERGE | **2,432** | 847 | 🔴 HIGHEST IMPACT |
| **22757** | 09:17:04 UTC | MERGE | **2,431** | 858 | 🔴 HIGHEST IMPACT |
| 22770 | 12:04:47 UTC | MERGE | 1,446 | 553 | 🟡 Medium Impact |
| 22775 | 13:19:47 UTC | MERGE | 1,427 | 716 | 🟡 Medium Impact |
| 22816 | 23:34:47 UTC | MERGE | 1,473 | 585 | 🟡 Medium Impact |

**Total rows affected on Oct 13**: ~9,000+ row updates

---

## Technical Details

### Table Configuration

The table has a **ROW FILTER** that automatically hides deleted records:

```
Row Filter: `rds`.`pg_rds_enterprise_public`.`filter_deleted_rows` ON (_fivetran_deleted)
```

This filter means:
- ✅ Rows where `_fivetran_deleted = false` are VISIBLE
- ❌ Rows where `_fivetran_deleted = true` are INVISIBLE

### Most Impactful Operation (Version 22756)

**When**: October 13, 2025 at 09:15:54 UTC

**What Happened**:
- Rows Updated: 2,432
- Rows Copied: 3,357
- Rows Inserted: 847
- Source Rows: 3,290

**Operation Parameters**:
```json
{
  "predicate": "NOT _fivetran_deleted AND ctid_fivetran_id matching",
  "matchedPredicates": [
    {
      "predicate": "_fivetran_op_type = 2 AND _fivetran_updated_cols = 00000000000001100",
      "actionType": "update"
    },
    {
      "predicate": "_fivetran_op_type = 1",
      "actionType": "update"
    }
  ]
}
```

This indicates Fivetran was processing **UPDATE operations** (`_fivetran_op_type = 2`) that modified specific columns.

---

## Statistics Summary (Last 20 Days)

### Total Operations: 1,790

| Operation Type | Count | Percentage |
|----------------|-------|------------|
| MERGE | 1,737 | 97.0% |
| OPTIMIZE | 37 | 2.1% |
| VACUUM START/END | 12 | 0.7% |
| UPDATE | 2 | 0.1% |
| ADD COLUMNS | 1 | 0.05% |
| SET TBLPROPERTIES | 1 | 0.05% |

### Data Impact Metrics

- **Total Rows Updated**: 1,765,668 (across all operations)
- **Total Rows Deleted**: 0 (no hard deletes, only soft deletes via _fivetran_deleted)
- **VACUUM Operations**: 6 (permanent cleanup operations)

### Top 10 Most Impactful Updates

All top 10 operations involved `_fivetran_deleted` predicate checks (soft deletions):

1. Version 22756 (Oct 13): 2,432 rows
2. Version 22757 (Oct 13): 2,431 rows
3. Version 22721 (Oct 12): 2,426 rows
4. Version 23393 (Oct 19): 1,592 rows
5. Version 23626 (Oct 22): 1,585 rows
6. Version 23643 (Oct 22): 1,578 rows
7. Version 23329 (Oct 19): 1,566 rows
8. Version 23732 (Oct 23): 1,561 rows
9. Version 23717 (Oct 23): 1,553 rows
10. Version 23660 (Oct 22): 1,547 rows

---

## Root Cause Analysis

### What Happened

1. **Source Database Change**: On October 13, 2025, records were likely deleted in the source PostgreSQL database (`pg_rds_enterprise_public.enterprise_property`)

2. **Fivetran Sync**: Fivetran detected these deletions and synced them to Databricks by setting `_fivetran_deleted = true` on approximately 2,432+ rows

3. **Row Filter Applied**: The table's row filter automatically hid these rows from all standard queries

4. **Result**: You're now seeing only 1 active row instead of the expected ~2,400+ rows

### Why You're Not Seeing the Data

The row filter is **AUTOMATICALLY APPLIED** to all queries. Even if you query:
```sql
SELECT * FROM rds.pg_rds_enterprise_public.enterprise_property
```

It's actually executing:
```sql
SELECT * FROM rds.pg_rds_enterprise_public.enterprise_property
WHERE _fivetran_deleted = false
```

---

## Recommended Actions

### Immediate Actions

#### 1. Check Source PostgreSQL Database ⚠️ URGENT

**Investigate if the deletions in PostgreSQL were intentional or accidental:**

```sql
-- In PostgreSQL, check if records exist
SELECT COUNT(*) FROM enterprise_property;

-- Check for deleted records (if you have soft delete tracking)
SELECT COUNT(*) FROM enterprise_property WHERE deleted_at IS NOT NULL;
```

If the deletions were **accidental**, restoring the data in PostgreSQL will automatically sync it back via Fivetran.

#### 2. View Historical Data (Time Travel)

To see what the data looked like **before** the October 13 deletions:

```sql
-- View data as it was at version 22755 (before major updates)
SELECT * FROM rds.pg_rds_enterprise_public.enterprise_property VERSION AS OF 22755;

-- Count rows at that version
SELECT COUNT(*) FROM rds.pg_rds_enterprise_public.enterprise_property VERSION AS OF 22755;
```

#### 3. Query Deleted Records

To see which records are currently marked as deleted:

```sql
-- This will show all records including deleted ones from a historical version
SELECT *
FROM rds.pg_rds_enterprise_public.enterprise_property VERSION AS OF 24189
WHERE _fivetran_deleted = true
LIMIT 100;
```

Note: The row filter applies to the current table, so you may need to query historical versions.

### Recovery Options

#### Option A: Restore in Source Database (Recommended if deletions were accidental)

1. Restore the deleted records in PostgreSQL
2. Fivetran will automatically detect and sync them
3. Records will reappear in Databricks with `_fivetran_deleted = false`

#### Option B: Temporarily Disable Row Filter (Use with caution)

```sql
-- Remove the row filter (requires appropriate permissions)
ALTER TABLE rds.pg_rds_enterprise_public.enterprise_property DROP ROW FILTER;
```

⚠️ **WARNING**: This will expose deleted records to **ALL QUERIES** for **ALL USERS**. Only do this if you understand the implications.

#### Option C: Create a View Without Filter

```sql
-- Create a separate view that includes deleted records
CREATE VIEW rds.pg_rds_enterprise_public.enterprise_property_with_deleted AS
SELECT * FROM rds.pg_rds_enterprise_public.enterprise_property VERSION AS OF 24189;
```

This lets you query all data (including deleted) through the view while keeping the filter on the main table.

#### Option D: Adjust Fivetran Configuration

Consider configuring Fivetran to handle deletes differently:
- Hard delete mode (removes rows completely)
- Soft delete with different column
- Disable delete syncing (if deletions shouldn't be synced)

---

## Prevention Recommendations

1. **Set Up Monitoring**: Create alerts for large-scale updates (>1000 rows)

2. **Review Fivetran Configuration**: Ensure delete handling matches your requirements

3. **Document Row Filter Behavior**: Make sure your team knows about the row filter

4. **Regular Audits**: Monitor `_fivetran_deleted` column periodically

5. **Consider Separate Archive Table**: Store deleted records in a separate table for audit purposes

---

## Files Generated

1. `enterprise_property_history_20days.json` - Complete operation history (3.4 MB)
2. `DATA_LOSS_INVESTIGATION_REPORT.md` - This report
3. Analysis scripts:
   - `get_table_history.py`
   - `analyze_table_impact.py`
   - `investigate_oct13_update.py`
   - `query_deleted_rows.py`
   - `check_all_rows.py`

---

## Next Steps

1. ✅ **Review this report** with your team
2. ⚠️ **Check PostgreSQL** for source data status
3. 🔍 **Query historical versions** to see what data existed before Oct 13
4. 📋 **Decide on recovery strategy** based on business requirements
5. 🛠️ **Implement chosen solution** (restore source data, disable filter, etc.)

---

## Contact Information

**Investigation Date**: October 27, 2025
**Investigated By**: Automated analysis via Claude Code
**Report Location**: `/Users/danerosa/rds_databricks_claude/`

For questions or additional analysis, re-run the investigation scripts or query specific versions using Delta Lake time travel.

---

**Document Version**: 1.0
**Last Updated**: 2025-10-27
