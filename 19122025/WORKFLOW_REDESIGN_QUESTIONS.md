# Workflow Redesign Questions - Many-to-One Model

**Date:** December 23, 2025
**Context:** New finding that we can have multiple properties with the same SFDC_id (many-to-1 relationship is valid)
**Impact:** The entire duplicate cleanup plan from December 19 needs to be reconsidered

---

## CRITICAL FINDING

**OLD ASSUMPTION (Dec 19 investigation):**
- 1:1 relationship required between `rds.properties.sfdc_id` and `salesforce.product_property`
- Duplicate sfdc_id = data integrity problem requiring cleanup
- Solution = Phase 1-3 cleanup scripts

**NEW MODEL:**
- **Many-to-1 relationship is VALID**: Multiple `rds.properties` can share same `sfdc_id`
- Duplicate sfdc_id = legitimate business case
- Solution = **Aggregate features before syncing to Salesforce**

---

## Questions to Answer (Next Session)

### 1. Feature Aggregation Logic
When multiple properties share an sfdc_id, how should we aggregate their features?
- **Option A:** Union (if ANY property has feature enabled → Salesforce shows enabled)
- **Option B:** ACTIVE properties only (ignore DISABLED properties' features)
- **Option C:** Most recent update wins
- **Option D:** Something else?

**Answer:** _[To be filled in]_

---

### 2. Which Properties Should Contribute?
Should we include features from:
- Only ACTIVE properties?
- Both ACTIVE and DISABLED properties?
- Only the "primary" property (by some criteria)?

**Answer:** _[To be filled in]_

---

### 3. Feature State Conflicts
If two ACTIVE properties have conflicting feature states (one TRUE, one FALSE), which wins?
- Any enabled wins (TRUE)?
- Any disabled wins (FALSE)?
- Most recent `updated_at` wins?
- Flag for manual review?

**Answer:** _[To be filled in]_

---

### 4. Feature Metadata Aggregation
For feature metadata fields like:
- `enabled_at` (timestamp) - which property's date do we use?
- `feature_count` - sum across all properties? max? count distinct?
- `last_updated` - most recent across all properties?

**Answer:** _[To be filled in]_

---

### 5. Salesforce Data Model
- What does one `product_property` record in Salesforce represent?
- What is `sf_property_id_c` vs `snappt_property_id_c`?
- Does one Salesforce property relate to multiple Snappt properties by design?

**Answer:** _[To be filled in]_

---

### 6. Current Workflow Touch Points
- Which step in the current workflow (census_pfe → product_property_feature_sync → Census) assumes 1:1?
- Where should we introduce the aggregation logic?
- Should we create a new intermediate table/view?

**Answer:** _[To be filled in]_

---

### 7. Phase 1 Cleanup Script
Given the new model, should we:
- **Option A:** Abandon cleanup entirely (duplicates are valid)
- **Option B:** Still clean up DISABLED-only groups and test properties
- **Option C:** Pause cleanup until new workflow is implemented

**Answer:** _[To be filled in]_

---

### 8. Implementation Priority
What order should we proceed?
- **Option A:** Fix workflow first, then handle historical data
- **Option B:** Clean up safe cases first, then implement new workflow
- **Option C:** Both simultaneously

**Answer:** _[To be filled in]_

---

### 9. Park Kennedy Validation
For the Park Kennedy case:
```
sfdc_id: a01Dn00000HHUanIAH
├─ Property A: 5eec38f2-85c9-41f2-bac3-e0e350ec1083 (DISABLED, no features)
└─ Property B: 94246cbb-5eec-4fff-b688-553dcb0e3e29 (ACTIVE, IDV+Bank+Payroll+Income enabled)
```

Should Salesforce show:
- Only features from ACTIVE property?
- Features from both?
- Something else?

**Answer:** _[To be filled in]_

---

## Impact on Existing Work

### Files Affected by This Change
- ❌ `Phase1_Cleanup_Script.sql` - May not be needed, or needs different logic
- ❌ `Phase2_Manual_Review_List.sql` - May not be needed
- ⚠️ All analysis files - Based on wrong assumption (1:1 relationship)
- ✅ Investigation notebooks - Still valuable for understanding data patterns
- ✅ CSV exports - Still valuable as baseline data

### Workflow Changes Needed
1. **census_pfe notebook** (`/Workspace/Shared/census_pfe`)
   - Currently joins: `salesforce.product_property pp ON pp.sf_property_id_c = p.sfdc_id`
   - Needs: Aggregation logic BEFORE join

2. **product_property_feature_sync** (`/Repos/dbx_git/dbx/snappt/product_property_feature_sync`)
   - May need to handle multiple properties per sfdc_id

3. **Feature sync logic**
   - Needs aggregation rules for multiple properties

---

## Current Workflow (From Investigation)

```
Step 1: census_pfe notebook
├─ Joins: rds.properties LEFT JOIN salesforce.product_property
├─ Output: product_property_w_features table
└─ Problem: Assumes 1:1 join, may create duplicate rows or miss data

Step 2: product_property_feature_sync
├─ Compares: Current features vs Salesforce features
├─ Output: product_property_feature_sync table (sync queue)
└─ Problem: May not handle multiple properties correctly

Step 3: Census API trigger
├─ Sends: Changes to Salesforce via Census
└─ Problem: May create unexpected behavior with duplicates
```

---

## Proposed New Workflow (High Level)

```
Step 0: NEW AGGREGATION LAYER
├─ Input: rds.properties (with duplicate sfdc_ids)
├─ Logic: Aggregate features by sfdc_id using business rules
├─ Output: properties_aggregated_by_sfdc view/table
└─ This becomes the source for census_pfe

Step 1: census_pfe notebook (UPDATED)
├─ Uses: properties_aggregated_by_sfdc (1:1 with sfdc_id)
├─ Joins: Clean 1:1 join with salesforce.product_property
└─ Output: product_property_w_features (no duplicates)

Step 2: product_property_feature_sync (UNCHANGED or minimal changes)

Step 3: Census API trigger (UNCHANGED)
```

---

## Key Decisions Needed

1. **Aggregation Rules:** How to combine features from multiple properties
2. **ACTIVE vs DISABLED:** Should DISABLED properties contribute to feature state?
3. **Conflict Resolution:** What to do when properties have conflicting states
4. **Metadata Handling:** How to aggregate timestamps and counts
5. **Cleanup Strategy:** What to do with the 2,541 duplicate groups now?

---

## Next Steps (After Questions Answered)

1. ✅ Get answers to all 9 questions
2. ✅ Design aggregation logic based on answers
3. ✅ Update census_pfe notebook with aggregation layer
4. ✅ Create new aggregated view/table
5. ✅ Test with Park Kennedy and other known duplicates
6. ✅ Update product_property_feature_sync if needed
7. ✅ Document new many-to-1 model
8. ✅ Decide fate of Phase 1-3 cleanup scripts

---

## Files to Reference

**Current Investigation Files:**
- `README.md` - Overview of duplicate investigation
- `DUPLICATE_CLEANUP_SUMMARY.md` - Executive summary (now outdated assumption)
- `DUPLICATE_CLEANUP_ANALYSIS.md` - Technical analysis (patterns still valid)
- `Find_Duplicate_SFDC_IDs.ipynb` - Detection notebook (still useful)
- `notebook_output_sfdc_dupes/` - Data exports (still useful as baseline)

**Databricks Assets:**
- Sync Job: 1061000314609635
- Notebook: `/Workspace/Shared/census_pfe`
- Notebook: `/Repos/dbx_git/dbx/snappt/product_property_feature_sync`
- Investigation: `/Workspace/Users/dane@snappt.com/Find_Duplicate_SFDC_IDs`

---

## Status

**Current:** ⏸️ PAUSED - Waiting for answers to clarification questions
**Next:** Design and implement feature aggregation logic
**Timeline:** TBD based on answers and implementation complexity

---

**When resuming, start by filling in the answers to the 9 questions above, then proceed with implementation plan.**
