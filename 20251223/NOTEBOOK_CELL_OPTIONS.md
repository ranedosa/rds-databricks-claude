# Final Cell Options for David Exploration.ipynb

## Option 1: Simple Filter (Single Cell) ⭐

Copy this into the last cell of your notebook:

```sql
%sql
-- Final: Remove all excluded properties from active_properties_companies

WITH all_excluded_properties AS (
    -- IDV web portal properties
    SELECT DISTINCT p.id as property_id
    FROM rds.pg_rds_public.properties p
    LEFT JOIN rds.pg_rds_public.property_features pf ON pf.property_id = p.id
    WHERE p.status = 'ACTIVE'
      AND pf.feature_code = 'identity_verification_only_web_portal'

    UNION

    -- IDV only properties
    SELECT DISTINCT property_id FROM idv_only

    UNION

    -- Partner properties
    SELECT DISTINCT id as property_id FROM partner_properties

    UNION

    -- Test properties
    SELECT DISTINCT property_id FROM test_properties

    UNION

    -- Phased out properties
    SELECT DISTINCT property_id FROM phased_out_properties
)
-- Final filtered results
SELECT
    apc.*
FROM active_properties_companies apc
LEFT JOIN all_excluded_properties ex
    ON apc.active_properties = ex.property_id
WHERE ex.property_id IS NULL;  -- Keep only non-excluded properties
```

---

## Option 2: With Summary Stats (Multiple Cells)

### Cell 1: Create Filtered View
```sql
%sql
CREATE OR REPLACE TEMPORARY VIEW all_excluded_properties AS (
    SELECT DISTINCT p.id as property_id, 'IDV Web Portal' as reason
    FROM rds.pg_rds_public.properties p
    LEFT JOIN rds.pg_rds_public.property_features pf ON pf.property_id = p.id
    WHERE p.status = 'ACTIVE' AND pf.feature_code = 'identity_verification_only_web_portal'

    UNION

    SELECT DISTINCT property_id, 'IDV Only' FROM idv_only

    UNION

    SELECT DISTINCT id as property_id, 'Partner Property' FROM partner_properties

    UNION

    SELECT DISTINCT property_id, 'Test Property' FROM test_properties

    UNION

    SELECT DISTINCT property_id, 'Phased Out' FROM phased_out_properties
);

CREATE OR REPLACE TEMPORARY VIEW final_active_properties_companies AS (
    SELECT apc.*
    FROM active_properties_companies apc
    LEFT JOIN all_excluded_properties ex ON apc.active_properties = ex.property_id
    WHERE ex.property_id IS NULL
);

SELECT * FROM final_active_properties_companies;
```

### Cell 2: Summary Statistics
```sql
%sql
-- Summary: Before vs After Filtering
SELECT
    'Before Filtering' as stage,
    COUNT(*) as properties,
    COUNT(DISTINCT companies_with_active_properties) as companies,
    SUM(property_units) as units
FROM active_properties_companies

UNION ALL

SELECT
    'After Filtering' as stage,
    COUNT(*) as properties,
    COUNT(DISTINCT companies_with_active_properties) as companies,
    SUM(property_units) as units
FROM final_active_properties_companies;
```

### Cell 3: Exclusion Breakdown
```sql
%sql
-- What was excluded?
SELECT
    reason,
    COUNT(DISTINCT property_id) as excluded_count
FROM all_excluded_properties
GROUP BY reason
ORDER BY excluded_count DESC;
```

---

## Option 3: In-Line Anti-Join (Most Concise)

```sql
%sql
-- Final filtered properties (one query)
SELECT apc.*
FROM active_properties_companies apc
WHERE apc.active_properties NOT IN (
    -- IDV web portal
    SELECT DISTINCT p.id
    FROM rds.pg_rds_public.properties p
    LEFT JOIN rds.pg_rds_public.property_features pf ON pf.property_id = p.id
    WHERE p.status = 'ACTIVE' AND pf.feature_code = 'identity_verification_only_web_portal'

    UNION

    SELECT property_id FROM idv_only
    UNION
    SELECT id FROM partner_properties
    UNION
    SELECT property_id FROM test_properties
    UNION
    SELECT property_id FROM phased_out_properties
);
```

---

## What Each Exclusion Does

| View/Source | What It Excludes | Column Name |
|-------------|------------------|-------------|
| IDV Web Portal | Properties with `identity_verification_only_web_portal` feature | Calculated from properties + property_features |
| `idv_only` | Properties with ONLY `identity_verification` feature | `property_id` |
| `partner_properties` | Partner properties from enterprise table | `id` |
| `test_properties` | Test/demo/staging properties by name | `property_id` |
| `phased_out_properties` | Phased buildings (Phase 1, Phase 2, etc.) | `property_id` |

---

## Expected Results

After running the filter, you'll see:
- Fewer rows in the result set
- Only properties that don't appear in ANY exclusion list
- Same columns as `active_properties_companies`:
  - `active_properties` (property ID)
  - `property_units` (unit count)
  - `companies_with_active_properties` (company ID)

---

## Validation

To verify the filtering worked:

```sql
%sql
-- Check: No excluded properties should appear in final results
SELECT COUNT(*) as excluded_properties_in_final_results
FROM final_active_properties_companies f
INNER JOIN all_excluded_properties ex
    ON f.active_properties = ex.property_id;
```

Should return: **0** (no excluded properties in final results)

---

## Recommended Approach

Use **Option 1** (Simple Filter) if you just want the filtered data.

Use **Option 2** (With Summary Stats) if you want to see:
- How many properties were excluded
- Why they were excluded
- Before/after comparison
