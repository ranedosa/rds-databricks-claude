# Active Properties Analysis - Refined Query

## Request Summary

**Original Query:**
```sql
SELECT
    COUNT(DISTINCT p.id) as active_properties,
    COUNT(DISTINCT p.company_id) as companies_with_active_properties,
    SUM(p.unit) as total_units
FROM rds.pg_rds_public.properties p
WHERE p.status = 'ACTIVE';
```

**Follow-up Requirements:**
Exclude from the count:
1. IDV Only properties (duplicate properties on the platform)
2. Other partner properties not listed on the Customer Log
3. Test/demo properties that are listed as active
4. Buildings that are phased out (e.g., "123 Main St Phase 1", "123 Main St Phase 2")

## Solution Files

### 1. `active_properties_analysis.py` (Comprehensive PySpark Notebook)

**Features:**
- Loads and validates Customer Log CSV
- Joins properties with Customer Log using **Salesforce ID** (sfdc_id) for reliable matching
- Applies all exclusion filters
- Provides detailed before/after comparison
- Shows exactly what was excluded and why
- Saves excluded properties for audit

**Best For:**
- Complete analysis with Customer Log integration
- Detailed reporting and auditing
- When you need to see what was filtered out

**Usage:**
1. Upload `Snappt Customer Log - Customer Log - Onboarded.csv` to DBFS at:
   `/FileStore/tables/Snappt_Customer_Log_Customer_Log_Onboarded.csv`
2. Import the notebook to Databricks
3. Run all cells sequentially
4. Review the final results in the last cell

### 2. `active_properties_simple_sql.sql` (SQL-Only Notebook)

**Features:**
- Pure SQL implementation
- No CSV upload required (uses pattern matching)
- Faster to run
- Two versions:
  - **Option 1**: With Customer Log join (if already loaded)
  - **Option 2**: Pattern-based exclusions only
- Side-by-side comparison of before/after
- Summary of excluded properties

**Best For:**
- Quick analysis without CSV upload
- When Customer Log is already in a Delta table
- Simple pattern-based exclusions

**Usage:**
1. Import the notebook to Databricks
2. Run **Option 2** for pattern-based filtering (no CSV needed)
3. Or run **Option 1** if you have Customer Log in a table

## Exclusion Logic

### 1. IDV Only Properties (Using property_features table)
```sql
-- Create CTE to identify IDV properties
WITH idv_properties AS (
    SELECT DISTINCT property_id
    FROM rds.pg_rds_public.property_features
    WHERE state = 'enabled'
      AND (feature_code LIKE '%idv%' OR feature_code LIKE '%identity_verification%')
)
-- Then exclude them
LEFT JOIN idv_properties idv ON idv.property_id = p.id
WHERE idv.property_id IS NULL
```
**Note**: This uses the `property_features` table for reliable IDV detection instead of name pattern matching.

### 2. Test/Demo Properties
```sql
LOWER(p.name) NOT LIKE '%test%'
AND LOWER(p.name) NOT LIKE '%demo%'
AND LOWER(p.name) NOT LIKE '%sample%'
```

### 3. Phased Buildings
```sql
LOWER(p.name) NOT LIKE '%phase 1%'
AND LOWER(p.name) NOT LIKE '%phase 2%'
AND LOWER(p.name) NOT LIKE '%phase 3%'
AND NOT REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9]')
```

### 4. Not in Customer Log (Using Salesforce ID)
```sql
INNER JOIN customer_log cl
    ON p.sfdc_id = cl.sfdc_property_id
WHERE
    cl.status = 'Live'
    AND cl.sfdc_property_id IS NOT NULL
```
**Note**: This uses the Salesforce ID (`sfdc_id`) for reliable matching instead of fuzzy name matching. About 80-98% of properties have an sfdc_id populated.

## Quick Start

### Fastest Path (SQL Only - No Upload)
```sql
-- Copy this query directly into Databricks SQL Editor
WITH idv_properties AS (
    SELECT DISTINCT property_id
    FROM rds.pg_rds_public.property_features
    WHERE state = 'enabled'
      AND (feature_code LIKE '%idv%' OR feature_code LIKE '%identity_verification%')
)
SELECT
    COUNT(DISTINCT p.id) as active_properties,
    COUNT(DISTINCT p.company_id) as companies_with_active_properties,
    SUM(p.unit) as total_units
FROM rds.pg_rds_public.properties p
LEFT JOIN idv_properties idv ON idv.property_id = p.id
WHERE
    p.status = 'ACTIVE'
    AND idv.property_id IS NULL
    AND LOWER(p.name) NOT LIKE '%test%'
    AND LOWER(p.name) NOT LIKE '%demo%'
    AND LOWER(p.name) NOT LIKE '%sample%'
    AND LOWER(p.name) NOT LIKE '%phase 1%'
    AND LOWER(p.name) NOT LIKE '%phase 2%'
    AND LOWER(p.name) NOT LIKE '%phase 3%'
    AND NOT REGEXP_LIKE(LOWER(p.name), 'phase\\s*[0-9]');
```

## Expected Output

The query will return a single row with three columns:

| active_properties | companies_with_active_properties | total_units |
|-------------------|----------------------------------|-------------|
| [count]           | [count]                          | [sum]       |

## Files in This Directory

### Main Query Files
- `QUICK_ANSWER_V3_FINAL.sql` - ⭐ **Use this!** Most comprehensive and accurate
- `active_properties_analysis.py` - Full PySpark notebook with Customer Log integration
- `active_properties_simple_sql.sql` - SQL-only notebook with pattern matching

### Test Property Detection
- `test_property_ids_simple.sql` - Quick export of all test property IDs
- `find_all_test_properties.sql` - Comprehensive test property analysis
- `TEST_DETECTION_SUMMARY.md` - Documentation of test detection patterns

### Phased Property Detection
- `phased_property_ids_simple.sql` - Quick export of phased property IDs
- `find_phased_properties.sql` - Comprehensive phased property analysis
- `PHASED_PROPERTIES_GUIDE.md` - Guide on phase detection and exclusion logic

### IDV Detection
- `find_idv_only_properties.sql` - Analyze properties by feature groups
- `IDV_DETECTION_GUIDE.md` - Guide on IDV detection approaches
- `QUICK_ANSWER_V2.sql` - Uses "only IDV features" detection

### Notebook Integration
- `SINGLE_CELL_FILTER.txt` - ⭐ Copy/paste cell to filter active_properties_companies
- `AGGREGATED_COUNTS.txt` - Cell to get final aggregated counts
- `final_filtered_cell.sql` - Complete notebook cell with summary stats
- `NOTEBOOK_CELL_OPTIONS.md` - Multiple cell options and approaches

### Reference Data & Documentation
- `request.txt` - Original request and follow-up requirements
- `Snappt Customer Log - Customer Log - Onboarded.csv` - Customer property reference data
- `David Exploration.ipynb` - Working notebook with exclusion views
- `README.md` - This file

## Recommendations

1. **For most accurate results**: Use `QUICK_ANSWER_V3_FINAL.sql` ⭐
   - Includes comprehensive test detection (15+ patterns)
   - Uses property_features for IDV detection
   - Most thorough exclusion logic

2. **For detailed analysis**: Use `find_all_test_properties.sql` or `find_idv_only_properties.sql`
   - See breakdowns by exclusion type
   - Understand what's being filtered

3. **For complete audit trail**: Use `active_properties_analysis.py` with CSV upload
   - Full PySpark notebook
   - Customer Log integration

4. **For ongoing monitoring**: Save the filtered query as a view or scheduled job

## Notes

- The exclusion patterns can be adjusted based on actual data
- Review the "What Was Excluded" section to validate the filters
- Consider saving the filtered property list as a table for future reference
- **Join Strategy**: The Customer Log join uses Salesforce ID (`sfdc_id`) for reliable, accurate matching. This is much more reliable than fuzzy name matching since Salesforce IDs are unique identifiers.
