# Test Property Detection Summary

## 🎯 Query Files

| File | Purpose | Use Case |
|------|---------|----------|
| `test_property_ids_simple.sql` | **Quick list** of all test property IDs | Fast export of test property IDs |
| `find_all_test_properties.sql` | **Deep analysis** with statistics and breakdowns | Understanding what test properties exist |
| `QUICK_ANSWER_V3_FINAL.sql` | **Final answer** with all exclusions | Get the accurate active property count |

---

## 📋 Detection Patterns Used

### Core Test Keywords
```sql
LOWER(p.name) LIKE '%test%'
LOWER(p.name) LIKE '%demo%'
LOWER(p.name) LIKE '%sample%'
```
**Examples**: "Test Property", "Demo Account", "Sample Building"

### Development/Staging Keywords
```sql
LOWER(p.name) LIKE '%staging%'
LOWER(p.name) LIKE '%qa%'
LOWER(p.name) LIKE '%dev%'
LOWER(p.name) LIKE '%sandbox%'
```
**Examples**: "Staging Environment", "QA Property", "Dev Testing"

### Training/Temporary Keywords
```sql
LOWER(p.name) LIKE '%training%'
LOWER(p.name) LIKE '%dummy%'
LOWER(p.name) LIKE '%fake%'
LOWER(p.name) LIKE '%temporary%'
LOWER(p.name) LIKE '%temp%'
```
**Examples**: "Training Property", "Dummy Data", "Temporary Test"

### Action Keywords (Marked for Removal)
```sql
LOWER(p.name) LIKE '%do not%'
LOWER(p.name) LIKE '%delete%'
LOWER(p.name) LIKE '%remove%'
LOWER(p.name) LIKE '%duplicate%'
```
**Examples**: "Do Not Use", "Delete This", "Remove - Duplicate"

### Pattern-Based Detection (Regex)
```sql
REGEXP_LIKE(LOWER(p.name), '^test[_\\s-]')    -- Starts with "test"
REGEXP_LIKE(LOWER(p.name), '^demo[_\\s-]')    -- Starts with "demo"
REGEXP_LIKE(LOWER(p.name), '[_\\s-]test$')    -- Ends with "test"
REGEXP_LIKE(LOWER(p.name), '[_\\s-]demo$')    -- Ends with "demo"
```
**Examples**: "test_property1", "property_test", "demo-account"

---

## 🔍 Advanced Detection (Available in find_all_test_properties.sql)

### Heuristic-Based Detection
Identifies suspicious properties that might be tests even without keywords:

```sql
-- Properties with zero units
unit = 0 OR unit IS NULL

-- Properties never updated after creation
DATEDIFF(updated_at, created_at) = 0

-- Properties with very short names
LENGTH(name) < 5

-- Properties starting with numbers
REGEXP_LIKE(name, '^[0-9]')
```

### Test Company Detection
Finds companies with test-related names, which may indicate all their properties are tests:

```sql
LOWER(company_name) LIKE '%test%'
LOWER(company_name) LIKE '%demo%'
LOWER(company_name) LIKE '%internal%'
LOWER(company_name) LIKE '%snappt%'  -- Internal company properties
```

---

## 📊 Expected Results

When you run `test_property_ids_simple.sql`, you'll get:

```
property_id
-----------
uuid-1
uuid-2
uuid-3
...
```

### Typical Breakdown (Example Numbers)
- **Total Active Properties**: 10,000
- **Test/Demo Properties Found**: 150-500
- **By Keyword**:
  - "test": 100-300
  - "demo": 50-100
  - "staging": 10-20
  - "training": 5-10
  - Other patterns: 10-50

---

## 🚀 How to Use

### Quick Export of Test Property IDs
```bash
# Run this query and export to CSV
test_property_ids_simple.sql
```

### Comprehensive Analysis
```bash
# Run this to see breakdown by detection method
find_all_test_properties.sql
```

### Get Final Active Property Count
```bash
# Run this for the accurate answer with all exclusions
QUICK_ANSWER_V3_FINAL.sql
```

---

## ✅ All Exclusions Applied in Final Query

The `QUICK_ANSWER_V3_FINAL.sql` applies:

1. ✅ **IDV-Only Properties** - Using property_features table
2. ✅ **Test/Demo/Staging Properties** - Comprehensive keyword detection (15+ patterns)
3. ✅ **Phased Buildings** - Phase 1, Phase 2, etc.
4. ✅ **Not in Customer Log** (optional) - Using SFDC ID matching

---

## 🔧 Customization

To add more test detection patterns, add to the WHERE clause:

```sql
OR LOWER(p.name) LIKE '%your_pattern%'
OR REGEXP_LIKE(LOWER(p.name), 'your_regex')
```

Common additions:
- `%pilot%` - Pilot programs
- `%trial%` - Trial accounts
- `%example%` - Example properties
- `%poc%` - Proof of concept

---

## 📈 Validation

To verify the test detection is working:

```sql
-- See sample of detected test properties
SELECT name, status
FROM rds.pg_rds_public.properties
WHERE id IN (
    -- paste results from test_property_ids_simple.sql
)
LIMIT 20;
```

Review the names to confirm they're actually test properties!

---

## 💡 Best Practices

1. **Start with comprehensive detection** (test_property_ids_simple.sql)
2. **Review the results** - Check if patterns are too broad
3. **Adjust as needed** - Add/remove patterns based on your data
4. **Document exceptions** - If certain test properties should be included, note why
5. **Use in other queries** - Import the test_property_ids CTE into other analyses

---

## 🎯 Summary

**Most Comprehensive Query**: `QUICK_ANSWER_V3_FINAL.sql`

This query applies ALL exclusions:
- ✅ IDV-only properties (property_features)
- ✅ Test properties (15+ detection patterns)
- ✅ Phased buildings (regex patterns)

**Result**: Most accurate count of legitimate active properties.
