# Phased Properties Detection Guide

## Understanding Phased Properties

**Phased properties** are developments where a single building/complex is divided into multiple phases. Common patterns:
- "Sunset Apartments Phase 1", "Sunset Apartments Phase 2"
- "123 Main St Phase I", "123 Main St Phase II"
- "Oak Ridge - Phase 1", "Oak Ridge - Phase 2"

## Two Approaches to Exclusion

### Option 1: Exclude ALL Phased Properties
Exclude any property with "Phase X" in the name.

```sql
SELECT DISTINCT p.id
FROM properties p
WHERE LOWER(p.name) LIKE '%phase%'
```

**Use Case**: Conservative approach, exclude anything with phase numbering.

---

### Option 2: Exclude Only OLD Phases (Recommended) ⭐
Identify multi-phase buildings and exclude only the **old phases** (Phase 1, Phase 2 when Phase 3 exists).

```sql
-- Find properties where newer phases exist
WITH phase_analysis AS (
    SELECT
        property_id,
        phase_number,
        base_name,
        MAX(phase_number) OVER (PARTITION BY base_name) as max_phase
    FROM properties_with_phase_info
)
SELECT property_id
FROM phase_analysis
WHERE phase_number < max_phase  -- Old phases only
```

**Use Case**: More accurate - keeps the latest phase, excludes duplicates/old phases.

---

## How It Works

### Example: Sunset Apartments

| Property Name | Phase # | Status | Should Exclude? |
|--------------|---------|--------|----------------|
| Sunset Apartments Phase 1 | 1 | ACTIVE | ✅ Yes (old phase) |
| Sunset Apartments Phase 2 | 2 | ACTIVE | ✅ Yes (old phase) |
| Sunset Apartments Phase 3 | 3 | ACTIVE | ❌ No (latest phase) |

**Result**: Only count "Phase 3" in active properties, exclude Phase 1 & 2 as duplicates.

---

## Query Files

| File | Purpose | Exclusion Logic |
|------|---------|-----------------|
| `phased_property_ids_simple.sql` | Quick export of phased property IDs | Option 1: All phases OR Option 2: Old phases only |
| `find_phased_properties.sql` | Deep analysis of phase patterns | Comprehensive breakdown with grouping |
| `QUICK_ANSWER_V3_FINAL.sql` | Final answer query | Uses Option 2 (old phases only) |

---

## Detection Patterns

### Numeric Phases
```sql
'%phase 1%', '%phase 2%', '%phase 3%', etc.
REGEXP_LIKE(name, 'phase\\s*[0-9]+')
```

### Roman Numeral Phases
```sql
'%phase i%', '%phase ii%', '%phase iii%', etc.
```

### Address-Based Detection
```sql
LOWER(street_address) LIKE '%phase%'
```

---

## Key Concepts

### Base Identifier
The property name with phase information removed:
- "Sunset Apartments Phase 2" → "sunsetapartments"
- "Oak Ridge - Phase 1" → "oakridge"

Used to **group** properties that are phases of the same building.

### Phase Number Extraction
Convert phase identifiers to numbers for comparison:
- "Phase 1" → 1
- "Phase II" → 2
- "Phase 3" → 3

### Multi-Phase Detection
Count how many phases exist for each base identifier:
```sql
COUNT(*) OVER (PARTITION BY base_identifier)
```

If count > 1, it's a multi-phase property.

---

## What Gets Excluded?

### Scenario A: Single Phase Property
```
Property: "Downtown Lofts Phase 1"
Analysis: Only one phase exists
Result: NOT EXCLUDED (it's not a duplicate)
```

### Scenario B: Multi-Phase Property
```
Properties:
  - "Riverside Phase 1" (created 2020)
  - "Riverside Phase 2" (created 2022)
  - "Riverside Phase 3" (created 2024)

Analysis: Phase 3 is latest
Result:
  ✅ EXCLUDE Phase 1 (old)
  ✅ EXCLUDE Phase 2 (old)
  ❌ KEEP Phase 3 (latest)
```

### Scenario C: Inactive Old Phase
```
Properties:
  - "Park View Phase 1" (INACTIVE)
  - "Park View Phase 2" (ACTIVE)

Analysis: Phase 2 is latest
Result:
  ✅ EXCLUDE Phase 1 (old + inactive)
  ❌ KEEP Phase 2 (latest)
```

---

## Summary Statistics Available

Run `find_phased_properties.sql` to see:

1. **Total properties with phase in name**
2. **Multi-phase buildings** (2+ phases)
3. **Old phases still active** (potential duplicates)
4. **Old phases inactive** (properly phased out)

---

## Recommended Approach

**Use Option 2** (old phases only) in `QUICK_ANSWER_V3_FINAL.sql` because:

✅ More accurate - doesn't exclude legitimate single-phase properties
✅ Identifies true duplicates - old phases of multi-phase buildings
✅ Keeps latest phase - the current active property
✅ Aligns with business need - exclude "phased out" properties

---

## Example Query

```sql
-- Get old phase property IDs to exclude
WITH properties_with_phases AS (
    SELECT
        id,
        CAST(REGEXP_EXTRACT(name, 'phase\\s*([0-9]+)', 1) AS INT) as phase_num,
        REGEXP_REPLACE(LOWER(name), 'phase\\s*[0-9]+', '') as base_name
    FROM properties
    WHERE LOWER(name) LIKE '%phase%'
),
phase_groups AS (
    SELECT
        id,
        phase_num,
        MAX(phase_num) OVER (PARTITION BY base_name) as max_phase,
        COUNT(*) OVER (PARTITION BY base_name) as total_phases
    FROM properties_with_phases
)
SELECT id as property_id
FROM phase_groups
WHERE total_phases > 1 AND phase_num < max_phase;
```

This identifies **old phases** from **multi-phase buildings** - exactly what needs to be excluded!

---

## Validation

To verify the logic is working:

```sql
-- Show phase groupings
SELECT
    base_name,
    COUNT(*) as phase_count,
    MIN(phase_num) as first_phase,
    MAX(phase_num) as latest_phase,
    GROUP_CONCAT(CONCAT('Phase ', phase_num, ': ', status))
FROM properties_with_phases
GROUP BY base_name
HAVING COUNT(*) > 1
ORDER BY phase_count DESC
LIMIT 10;
```

Review to ensure the "latest" phase makes sense!
