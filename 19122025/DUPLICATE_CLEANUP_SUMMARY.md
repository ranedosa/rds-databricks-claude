# Duplicate sfdc_id Cleanup - Executive Summary

**Date:** December 19, 2025
**Investigation:** Databricks Job 1061000314609635 Feature Sync Issue

---

## THE PROBLEM

**Park Kennedy** features not syncing → Investigation revealed **MASSIVE systematic issue**

### Scale:
- **2,541 duplicate sfdc_id groups**
- **6,068 properties affected** (3,391 DISABLED + 2,677 ACTIVE)
- **79% of duplicates** = DISABLED properties blocking ACTIVE properties from syncing
- **Park Kennedy is just 1 of ~2,500 ACTIVE properties blocked**

---

## ROOT CAUSE

When properties are **migrated or recreated**, the old DISABLED property keeps its `sfdc_id`. This causes:

1. **New property can't sync** (has sfdc_id, filtered from "new properties" workflow)
2. **Feature sync fails** (Salesforce join fails because wrong property in SF)
3. **Features don't appear** in Salesforce for customers

---

## IMPACT

### Customer-Facing:
- Properties with features enabled (fraud, income verification, bank linking) **not visible in Salesforce**
- Sales/CS teams can't see which features are active
- Reporting inaccurate

### Estimated Affected Properties:
- **P1 (Urgent):** 200-500 ACTIVE properties with features, not in Salesforce
- **P2 (High):** 2,000+ ACTIVE properties blocked from future feature sync
- **P3 (Low):** 3,400 DISABLED properties causing data clutter

---

## THE SOLUTION

### 3-Phase Approach:

#### **Phase 1: Quick Win (Automated) - Week 1**
**Clear sfdc_id from all DISABLED properties**

- **Impact:** Resolves ~2,000 duplicate groups (79%)
- **Risk:** LOW (only touches DISABLED properties)
- **Effort:** 2 hours
- **Outcome:** 2,500+ ACTIVE properties unblocked immediately

```sql
-- One SQL script clears ~3,400 DISABLED properties
UPDATE properties SET sfdc_id = NULL
WHERE status = 'DISABLED' AND <in duplicate group>;
```

#### **Phase 2: Manual Review - Week 2**
**Investigate ~150-200 cases with TWO ACTIVE properties**

- **Impact:** Resolves remaining complex cases
- **Risk:** MEDIUM (requires case-by-case decisions)
- **Effort:** 10-15 hours
- **Outcome:** Clear resolution path for each edge case

Examples needing review:
- Bell Lighthouse Point + Advenir Lighthouse Point (both ACTIVE)
- NOVEL West Midtown + MAA West Midtown (both ACTIVE)
- Territory properties with different names

#### **Phase 3: Prevention - Week 3-4**
**Add safeguards to prevent recurrence**

- Database constraint (unique sfdc_id)
- Application validation
- Daily monitoring query
- Documentation

---

## RECOMMENDED IMMEDIATE ACTIONS

### TODAY:
1. ✅ **Review this summary** with team
2. ✅ **Get approval** for Phase 1 cleanup

### THIS WEEK:
3. ✅ **Test Phase 1 script** on staging
4. ✅ **Execute Phase 1** on production
5. ✅ **Verify Park Kennedy** starts syncing
6. ✅ **Monitor** other properties start syncing

### NEXT WEEK:
7. ✅ **Start Phase 2 manual review**
8. ✅ **Create resolution plan** for ACTIVE+ACTIVE cases

---

## FILES CREATED

### Analysis & Planning:
1. **DUPLICATE_CLEANUP_ANALYSIS.md** - Complete analysis (this file)
2. **DUPLICATE_SFDC_ID_RESOLUTION_STRATEGY.md** - General strategy guide
3. **DUPLICATE_CLEANUP_SUMMARY.md** - Executive summary

### Investigation Notebooks:
4. **Find_Duplicate_SFDC_IDs.ipynb** - Databricks analysis notebook
5. **Park_Kennedy_Investigation_Report.ipynb** - Detailed Park Kennedy case study

### Cleanup Scripts:
6. **Phase1_Cleanup_Script.sql** - READY TO RUN automated cleanup
7. **Phase2_Manual_Review_List.sql** - Queries to identify edge cases
8. **find_duplicate_sfdc_ids.sql** - Detection query

### Data Exports:
9. **notebook_output_sfdc_dupes/** - All query results from analysis

---

## KEY METRICS

### Before Cleanup:
- Duplicate groups: 2,541
- Properties affected: 6,068
- ACTIVE blocked: ~2,500
- Sync success rate: ~60%

### After Phase 1 (Expected):
- Duplicate groups: ~500 (↓81%)
- Properties affected: ~1,000 (↓83%)
- ACTIVE blocked: ~150 (↓94%)
- Sync success rate: ~95%

### After Phase 2 (Expected):
- Duplicate groups: ~50 (↓98%)
- Properties affected: ~100 (↓98%)
- ACTIVE blocked: 0 (↓100%)
- Sync success rate: ~100%

---

## SUCCESS CRITERIA

**Phase 1 Success:**
- [ ] Script executed without errors
- [ ] ~3,400 DISABLED properties cleared
- [ ] Park Kennedy syncing correctly
- [ ] No new issues reported

**Phase 2 Success:**
- [ ] All ACTIVE+ACTIVE cases reviewed
- [ ] Resolution plan documented for each
- [ ] Top 50 priority cases resolved

**Phase 3 Success:**
- [ ] Database constraint added
- [ ] Monitoring in place
- [ ] No new duplicates detected
- [ ] Documentation complete

---

## RISKS & MITIGATION

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Clear wrong property | Low | Medium | Only touch DISABLED in Phase 1 |
| Break Salesforce links | Low | Low | Clearing sfdc_id doesn't delete SF records |
| Create sync duplicates | Low | Medium | Monitor closely, can manually merge |
| Miss edge cases | Medium | Low | Phase 2 manual review catches these |
| Recurrence | High | Medium | Phase 3 prevention (constraints, monitoring) |

---

## QUESTIONS FOR TEAM

1. **Approval to proceed with Phase 1?**
   - Risk is low (only DISABLED properties)
   - Impact is high (unblocks 2,500 properties)

2. **Who should do Phase 2 manual review?**
   - Needs someone familiar with properties/customers
   - ~10-15 hours of work
   - Can be done over several days

3. **When can we add database constraint?**
   - After cleanup is complete
   - Prevents future duplicates
   - Needs brief downtime or migration window

4. **Should we communicate to customers?**
   - Some will see properties appear in Salesforce
   - Some may have duplicate records (can merge)
   - Recommend: Monitor first, communicate if needed

---

## CONTACTS & RESOURCES

**Documentation:**
- Sync job: Databricks Job 1061000314609635
- Feature aggregation: `/Workspace/Shared/census_pfe`
- Feature sync: `/Repos/dbx_git/dbx/snappt/product_property_feature_sync`

**Notebooks (already in Databricks):**
- Investigation: `/Workspace/Users/dane@snappt.com/Find_Duplicate_SFDC_IDs`
- Park Kennedy: `/Users/dane@snappt.com/investigate_park_kennedy`

**Scripts (ready to run):**
- Phase 1: `Phase1_Cleanup_Script.sql`
- Phase 2: `Phase2_Manual_Review_List.sql`

---

## NEXT STEP

**START HERE:** Review Phase1_Cleanup_Script.sql

```sql
-- Run STEP 1 to preview what will change
-- Run STEP 2 to see sample properties
-- Run STEP 3 to check edge cases
-- If comfortable, uncomment STEP 4 to execute
```

**Questions?** Reference DUPLICATE_CLEANUP_ANALYSIS.md for full details.

---

**Ready to fix 2,500 properties? Let's start with Phase 1! 🚀**
