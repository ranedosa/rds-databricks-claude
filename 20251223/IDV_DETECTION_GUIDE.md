# IDV Property Detection Guide

## Understanding "IDV-Only" Properties

There are two ways to interpret "IDV-only" properties:

### Option 1: Properties with ANY IDV Feature Enabled
Properties that have identity verification features enabled (but may also have other features).

```sql
WITH idv_properties AS (
    SELECT DISTINCT property_id
    FROM rds.pg_rds_public.property_features
    WHERE state = 'enabled'
      AND (feature_code LIKE '%idv%' OR feature_code LIKE '%identity_verification%')
)
```

**Use Case**: Exclude all properties with IDV capability, regardless of other features.

---

### Option 2: Properties with ONLY IDV Features (No Other Features)
Properties where identity verification is the **only** enabled feature (true duplicates/IDV-only accounts).

```sql
WITH idv_only_properties AS (
    SELECT property_id
    FROM (
        SELECT
            property_id,
            COUNT(DISTINCT feature_code) as feature_count,
            SUM(CASE
                WHEN feature_code NOT LIKE '%identity%'
                     AND feature_code NOT LIKE '%idv%'
                THEN 1 ELSE 0
            END) as non_idv_feature_count
        FROM rds.pg_rds_public.property_features
        WHERE state = 'enabled'
        GROUP BY property_id
    )
    WHERE feature_count > 0 AND non_idv_feature_count = 0
)
```

**Use Case**: Exclude only the duplicate properties that exist solely for IDV (more precise).

---

## Recommended Approach

**Use Option 2** (properties with ONLY IDV features) because:

✅ More accurate - identifies true "IDV-only" duplicates
✅ Won't exclude legitimate properties that happen to have IDV as one of many features
✅ Aligns with the business requirement of excluding "duplicate properties"

---

## Query Files Available

| File | IDV Detection Method | Description |
|------|---------------------|-------------|
| `QUICK_ANSWER.sql` | Option 1 (Any IDV) | Original - excludes any property with IDV features |
| `QUICK_ANSWER_V2.sql` | Option 2 (Only IDV) | **Recommended** - excludes only true IDV-only properties |
| `find_idv_only_properties.sql` | Both options | Analysis query to explore both approaches |

---

## How to Verify Which Approach to Use

Run this query to see the difference:

```sql
-- Compare the two approaches
WITH any_idv AS (
    SELECT DISTINCT property_id
    FROM rds.pg_rds_public.property_features
    WHERE state = 'enabled'
      AND (feature_code LIKE '%idv%' OR feature_code LIKE '%identity%')
),
only_idv AS (
    SELECT property_id
    FROM (
        SELECT
            property_id,
            COUNT(DISTINCT feature_code) as feature_count,
            SUM(CASE WHEN feature_code NOT LIKE '%identity%'
                         AND feature_code NOT LIKE '%idv%'
                    THEN 1 ELSE 0 END) as non_idv_count
        FROM rds.pg_rds_public.property_features
        WHERE state = 'enabled'
        GROUP BY property_id
    )
    WHERE feature_count > 0 AND non_idv_count = 0
)

SELECT
    'Any IDV Feature' as method,
    COUNT(*) as property_count
FROM any_idv

UNION ALL

SELECT
    'Only IDV Features' as method,
    COUNT(*) as property_count
FROM only_idv;
```

The difference between these two counts represents properties that have IDV **plus** other features. These would be excluded by Option 1 but included by Option 2.

---

## Sample Properties by Type

```sql
WITH property_types AS (
    SELECT
        p.id,
        p.name,
        COUNT(DISTINCT pf.feature_code) as feature_count,
        CONCAT_WS(', ', COLLECT_LIST(pf.feature_code)) as features,
        CASE
            WHEN COUNT(DISTINCT pf.feature_code) = 0 THEN 'No Features'
            WHEN SUM(CASE WHEN pf.feature_code NOT LIKE '%identity%'
                              AND pf.feature_code NOT LIKE '%idv%'
                         THEN 1 ELSE 0 END) = 0
                 THEN 'IDV Only'
            WHEN SUM(CASE WHEN pf.feature_code LIKE '%identity%'
                              OR pf.feature_code LIKE '%idv%'
                         THEN 1 ELSE 0 END) > 0
                 THEN 'IDV + Other Features'
            ELSE 'Non-IDV Features'
        END as property_type
    FROM rds.pg_rds_public.properties p
    LEFT JOIN rds.pg_rds_public.property_features pf
        ON p.id = pf.property_id AND pf.state = 'enabled'
    WHERE p.status = 'ACTIVE'
    GROUP BY p.id, p.name
)

SELECT
    property_type,
    COUNT(*) as count
FROM property_types
GROUP BY property_type
ORDER BY count DESC;
```

---

## Decision Matrix

| Your Requirement | Use This File |
|-----------------|---------------|
| "Exclude properties that are duplicates created only for IDV" | `QUICK_ANSWER_V2.sql` ✅ |
| "Exclude any property with IDV capability" | `QUICK_ANSWER.sql` |
| "I want to see both and decide" | `find_idv_only_properties.sql` |

---

## Example Scenarios

### Scenario A: Property with Multiple Features
```
Property: "Main Street Apartments"
Features: fraud_detection, identity_verification, bank_linking
Result:
  - Option 1: EXCLUDED (has IDV)
  - Option 2: INCLUDED (has other features besides IDV)
```

### Scenario B: True IDV-Only Property
```
Property: "Main Street Apartments - IDV"
Features: identity_verification
Result:
  - Option 1: EXCLUDED (has IDV)
  - Option 2: EXCLUDED (only has IDV)
```

---

## Recommendation

**Start with `QUICK_ANSWER_V2.sql`** (Option 2 - Only IDV) as it's more conservative and accurate for identifying true duplicate/IDV-only properties.
