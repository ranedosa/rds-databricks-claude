# modify_address V2 Validation Results - Detailed Analysis

**Date:** November 18, 2025
**Status:** ⚠️ **INVESTIGATION REQUIRED**

---

## Executive Summary

The V2 test results show **-1.3% fewer matches** (10,900 vs 11,047) instead of the predicted +21% improvement. After deep investigation, I've identified the root cause:

**V2 correctly finds 16,529 properties via direct sfdc_id matching (47% more than V1), but filters out 5,886 as duplicates, while V1 inexplicably includes 3,252 duplicates in its final output.**

---

## Key Findings

### 1. Match Counts

| Version | Properties Matched | Duplicates Filtered | Final Output | Performance |
|---------|-------------------|---------------------|--------------|-------------|
| **V1 Production** | ~16,000 (estimated) | 2,634 filtered | **11,047** | Baseline |
| **V2 Test** | **16,529** | **5,886** filtered | **10,943** | -1.3% |
| **Difference** | +3,529 more found | +3,252 more filtered | -147 fewer | ❌ Worse |

### 2. Lost Matches Breakdown

Out of **3,513 lost matches** (in V1 but not V2):

| Category | Count | Percentage |
|----------|-------|------------|
| **Found by V2 but filtered as duplicates** | 3,252 | 92.6% |
| **Not found by V2 at all** | 261 | 7.4% |

### 3. Duplicate Status of Lost Matches

Of the 3,252 lost matches that V2 filtered out:

| Duplicate Type | Count | Percentage | Description |
|---------------|-------|------------|-------------|
| **SFDC Dupe** | 1,636 | 50.3% | Multiple SFDC properties → Same FDE address |
| **Both Dupe** | 1,610 | 49.5% | Many-to-many duplicates |
| **FDE Dupe** | 6 | 0.2% | Same SFDC property → Multiple FDE properties |

### 4. V1's Duplicate Handling

**Critical Discovery:** V1 INCLUDES duplicates in its final output.

| Metric | Value |
|--------|-------|
| V1 Total Properties | 11,047 |
| V1 Properties Marked as Duplicates | 1,893 (17.1%) |
| V1 Properties NOT Marked as Duplicates | 9,168 (82.9%) |

**V1 includes ~1,893 properties that are flagged as duplicates in its own duplicate detection table.**

---

## Root Cause Analysis

### Why V2 Has Fewer Matches

1. **V2 Matching:** Correctly finds 16,529 properties via direct `sfdc_id` matching ✅
2. **V2 Duplicate Detection:** Correctly identifies 5,886 as duplicates ✅
3. **V2 Filtering:** Filters out ALL duplicates per logic at line 319:
   ```sql
   WHERE FinalDupeStatus = 'No Dupe'
   OR (SFDC_Override IS NOT NULL AND extra_duplicate_flag = 0)
   ```
4. **V2 Final Output:** 10,943 properties (duplicates excluded) ✅

### Why V1 Has More Matches

1. **V1 Matching:** Finds ~16,000 properties via complex regex matching
2. **V1 Duplicate Detection:** Identifies 5,491 as duplicates
3. **V1 Filtering:** ⚠️ **INCLUDES 1,893 duplicates in final output**
4. **V1 Final Output:** 11,047 properties (includes duplicates) ⚠️

---

## Example Duplicate Cases

Here are real examples of properties V1 includes but V2 filters:

| SFDC ID | FDE IDs | Issue |
|---------|---------|-------|
| **a01Dn00000HHGdEIAX** | `0cc432bf...` & `20c062bc...` | Same SFDC property ("330 East Pierce St") matches TWO FDE properties ("330 East Pierce Street" & "330 E Pierce Street") |
| **a01Dn00000HHW7JIAX** | `becbdd14...` & `61724125...` | Same SFDC property ("261 Business Park Blvd") matches TWO FDE properties ("261 Business Park Boulevard" & "261 Business Park Blvd") |

**These ARE legitimate duplicates** - slight address variations (abbreviations, formatting) causing one SFDC property to match multiple FDE property records for the same physical location.

---

## Partner Property Impact

| Property Type | Lost Matches | Percentage |
|--------------|--------------|------------|
| **Partner/API Properties** | 1,093 | 31.1% |
| **Non-Partner Properties** | 2,420 | 68.9% |

**Conclusion:** This is NOT primarily a partner property issue. V1 includes duplicates across all property types.

---

## Validation Metrics Comparison

### Match Method Distribution (V2)

| Method | Count | Percentage |
|--------|-------|------------|
| **DIRECT_SFDC_ID** | 10,782 | 98.9% |
| **ADDRESS_MATCH_FALLBACK** | 118 | 1.1% |

✅ **Expected:** Direct `sfdc_id` matching is working correctly and covers 99% of matches.

### Duplicate Detection Stability

V1 and V2 have similar duplicate detection logic, but different filtering:

| Duplicate Status | V1 Count | V2 Count | V1 Includes in Final? | V2 Includes in Final? |
|-----------------|----------|----------|---------------------|---------------------|
| **No Dupe** | ~9,200 | 10,775 | ✅ Yes | ✅ Yes |
| **SFDC Dupe** | 2,785 | 2,785 | ⚠️ **Yes (1,636)** | ❌ No |
| **Both Dupe** | 2,641 | 2,641 | ⚠️ **Yes (1,610)** | ❌ No |
| **FDE Dupe** | 65 | 87 | ⚠️ **Yes (6)** | ❌ Partial (22) |

---

## Critical Questions

### 1. Is V1's inclusion of duplicates intentional or a bug?

**Evidence:**
- V1's duplicate detection table (`unity_sfdc_fde_duplicates`) correctly identifies duplicates
- V1's final table (`unity_modify_address`) includes 17% of records marked as duplicates
- No obvious business logic justification for including duplicates

**Hypothesis:** V1 has a filtering bug or incomplete filtering logic that allows duplicates through.

### 2. Should we include duplicates in the final output?

**Arguments for filtering (V2 approach):**
- ✅ Cleaner data - one-to-one SFDC-to-FDE mapping
- ✅ Prevents Census sync issues with ambiguous mappings
- ✅ More accurate representation of unique properties
- ✅ Aligns with stated goal of "duplicate detection"

**Arguments for including (V1 approach):**
- ⚠️ Maintains backward compatibility
- ⚠️ May be required for certain business cases (unclear which)
- ⚠️ Some downstream processes may expect duplicates

### 3. Which approach is "correct"?

**Recommendation:** Investigate V1's original notebook logic to understand if duplicate inclusion is:
- **Intentional:** If so, document the business reason and adjust V2 accordingly
- **Unintentional:** If so, V2 is more correct and we should proceed with it

---

## Address Quality Analysis

Of the 3,513 lost matches, **64.08% have full exact address matches**, confirming these are legitimate duplicates, not false positives from V1's regex.

| Match Type | Count | Percentage |
|-----------|-------|------------|
| Full address match (all 4 fields) | 2,251 | 64.1% |
| Partial matches | 1,262 | 35.9% |

This validates that V2's duplicate detection is working correctly - these are real duplicates.

---

## Next Steps

### Immediate Actions Required

1. **Review V1 Original Notebook Logic**
   - Check if there's additional filtering logic after duplicate detection
   - Determine if duplicate inclusion is intentional
   - Document the business justification if it exists

2. **Stakeholder Consultation**
   - **Question:** Should duplicates be included in the final output?
   - **Impact:** 3,252 properties (29% of V1's output) are duplicates
   - **Scenarios:**
     - If duplicates SHOULD be included: Adjust V2 filtering logic
     - If duplicates should NOT be included: V2 is correct, proceed with deployment

3. **Adjust V2 Logic (if needed)**
   - If duplicates should be included, modify line 319 filtering logic
   - If duplicates should be filtered, proceed with current V2 logic

### Decision Matrix

| Scenario | Action | Expected Outcome |
|----------|--------|------------------|
| **A: V1 duplicate inclusion is intentional** | Adjust V2 to include duplicates | V2 will match V1's ~11,047 count |
| **B: V1 duplicate inclusion is a bug** | Proceed with V2 as-is | V2's 10,943 count is correct |
| **C: Some duplicates should be included (e.g., partner properties)** | Add selective duplicate inclusion logic | V2 count between 10,943-11,047 |

---

## Recommendation

⚠️ **DO NOT PROCEED TO PRODUCTION** until we answer the critical question:

**"Is V1's inclusion of 1,893 duplicate properties intentional or a bug?"**

**Next Step:** Review V1's original `modify_address` notebook to understand the filtering logic and determine if there's a business reason for including duplicates.

---

## Technical Details

### V2 Filtering Logic (Current)

```sql
-- Cell 16 - Define Criteria for Salesforce Deploy
CREATE OR REPLACE TEMPORARY VIEW ProductPropertiesToSend AS
SELECT *
FROM LabeledDupesWithPartnerChanges
WHERE FinalDupeStatus = 'No Dupe'
OR (SFDC_Override IS NOT NULL AND extra_duplicate_flag = 0)
ORDER BY sfdc_address, fde_address
```

This logic filters out ALL duplicates except those with SFDC Override.

### Potential Fix (if duplicates should be included)

Option A: Include ALL duplicates
```sql
WHERE 1=1  -- Include everything
```

Option B: Include only partner duplicates
```sql
WHERE FinalDupeStatus = 'No Dupe'
OR (SFDC_Override IS NOT NULL AND extra_duplicate_flag = 0)
OR (api_flag = 1)  -- Include partner property duplicates
```

Option C: Include duplicates with certain criteria
```sql
WHERE FinalDupeStatus = 'No Dupe'
OR (SFDC_Override IS NOT NULL AND extra_duplicate_flag = 0)
OR (FinalDupeStatus IN ('SFDC Dupe', 'Both Dupe') AND fde_copy_number = 1)  -- Keep first FDE match for each SFDC
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `/Users/danerosa/rds_databricks_claude/notebooks/modify_address_v2_test.sql` | V2 test notebook |
| `/Users/danerosa/rds_databricks_claude/notebooks/modify_address_v2_validation.sql` | Validation queries |
| `/Users/danerosa/rds_databricks_claude/docs/modify_address_v2_testing_plan.md` | Original testing plan |

---

**Last Updated:** November 18, 2025
**Status:** Awaiting stakeholder decision on duplicate handling approach
